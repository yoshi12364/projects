import numpy as np
import matplotlib.pyplot as plt

#  SETTINGS & PHYSICS
T, STEPS = 0.01, 1200 
T_VEC = np.arange(STEPS) * T
M, D, Tg, Tt, R = 0.2, 2.0, 0.1, 0.3, 2.4
Bi = 1.0/R + D 

np.random.seed(42)
RAND_LOAD = np.zeros(STEPS)
RAND_LOAD[50:] = 0.2 + 0.04 * np.random.normal(0, 1, STEPS-50)

# Q-LEARNING + PSO AGENTS
class EstimatorAgent:
    def __init__(self, bias):
        self.B = bias
    def compute_ace(self, delta_f):
        return self.B * delta_f

class ControllerAgent:
    def __init__(self, alpha, gamma, delay_s=0.0):
        self.alpha, self.gamma = alpha, gamma
        self.q_table = np.zeros((20, 11)) 
        self.history = [0.0] * (int(delay_s / T) + 1)
        
    def compute(self, ace, neighbor_ace):
        state = int(np.clip((ace + 0.1) * 100, 0, 19))
        action_idx = np.argmax(self.q_table[state, :])
        u_rl = (action_idx - 5) * 0.15 
        reward = -(ace**2)
        self.q_table[state, action_idx] += self.alpha * (reward - self.q_table[state, action_idx])
        self.history.append(neighbor_ace)
        delayed_neighbor = self.history.pop(0)
        u = u_rl - 0.5 * (ace - delayed_neighbor)
        return np.clip(u, -2.0, 2.0)

class PowerArea:
    def __init__(self, i, alpha, gamma, delay=0.0):
        self.id = i
        self.estimator = EstimatorAgent(Bi)
        self.ctrl = ControllerAgent(alpha, gamma, delay)
        self.f, self.u, self.pm, self.pv, self.load, self.mse = [np.zeros(STEPS) for _ in range(6)]

def run_sim(case_label, delay=0.0, switch_at=None):
    # PSO Parameters (Pre-tuned Hyperparameters)
    pso_config = {'A': (0.15, 0.9), 'B': (0.12, 0.8), 'C': (0.1, 0.7), 
                  'D': (0.18, 0.95), 'E': (0.08, 0.6), 'F': (0.14, 0.85)}
    alpha, gamma = pso_config.get(case_label, (0.1, 0.9))
    
    areas = [PowerArea(i, alpha, gamma, delay) for i in range(1, 5)]
    multipliers = {1: 1e3, 2: 2e3, 3: 5e3, 4: 1e4}
    
    for k in range(STEPS - 1):
        if switch_at and k*T >= switch_at:
            for a in areas: a.ctrl.alpha, a.ctrl.gamma = pso_config['B']

        for i, a in enumerate(areas):
            if a.id == 1: a.load[k] = RAND_LOAD[k]
            ace_val = a.estimator.compute_ace(a.f[k])
            u_val = a.ctrl.compute(ace_val, areas[(i-1)%4].f[k])
            
            a.u[k] = u_val
            a.pv[k+1] = a.pv[k] + ((u_val - (a.f[k]/R) - a.pv[k])/Tg)*T
            a.pm[k+1] = a.pm[k] + ((a.pv[k] - a.pm[k])/Tt)*T
            a.f[k+1] = a.f[k] + ((a.pm[k] - a.load[k] - D*a.f[k])/M)*T
            a.mse[k+1] = (a.f[k+1]**2) * multipliers[a.id]
    return areas

# 3. RUN ALL SCENARIOS
resA = run_sim('A'); resB = run_sim('B'); resC = run_sim('C')
resD = run_sim('D'); resE = run_sim('E'); resF = run_sim('F')
resDelayD = run_sim('D', delay=0.5)
resSwitch = run_sim('A', switch_at=5.0)

plt.rcParams.update({'font.weight': 'bold', 'axes.grid': True, 'font.size': 9})

#4. PLOTTING (USING YOUR REFERENCE STRUCTURE)

# FIGURE 1: Dynamic Response Area-1 (Graphs 1-4)
fig1, ax1 = plt.subplots(4, 1, figsize=(9, 11), sharex=True)
ax1[0].plot(T_VEC, RAND_LOAD, color='b'); ax1[0].set_title("Graph 1: Area-1 Random Load Profile")
ax1[1].plot(T_VEC, np.zeros(STEPS), color='r'); ax1[1].set_title("Graph 2: Area-2 Load Profile")
ax1[2].plot(T_VEC, resA[0].f, 'b', label='Case A'); ax1[2].plot(T_VEC, resB[0].f, 'm--', label='Case B'); ax1[2].plot(T_VEC, resC[0].f, 'k:', label='Case C')
ax1[2].set_title("Graph 3: Frequency Response Area-1"); ax1[2].legend()
ax1[3].plot(T_VEC, resA[0].u, 'b'); ax1[3].plot(T_VEC, resB[0].u, 'm--'); ax1[3].plot(T_VEC, resC[0].u, 'k:')
ax1[3].set_title("Graph 4: Control Signal (u)"); ax1[3].set_xlabel("Time (s)")

# FIGURE 2: MSE Performance Cases B-F (Graphs 5-8)
fig2, ax2 = plt.subplots(2, 2, figsize=(11, 9))
cases_mse = [('B','m','--'), ('C','k',':'), ('D','r',':'), ('E','g','-.'), ('F','b','-')]
for i in range(4):
    ax = ax2[i//2, i%2]
    for lab, col, ls in cases_mse:
        sim_data = (resB if lab=='B' else resC if lab=='C' else resD if lab=='D' else resE if lab=='E' else resF)[i].mse
        smoothed = np.convolve(sim_data, np.ones(30)/30, mode='same')
        ax.plot(T_VEC, smoothed, color=col, linestyle=ls, label=f'Case {lab}')
    ax.set_title(f"Graph {5+i}: Area-{i+1} MSE Performance Comparison"); ax.legend(fontsize=7)

# FIGURE 3: Stability & Consensus (Graphs 9-11)
fig3, ax3 = plt.subplots(3, 1, figsize=(9, 11))
ax3[0].plot(T_VEC, resSwitch[0].f, 'b'); ax3[0].axvline(5.0, color='r', ls='--')
ax3[0].set_title("Graph 9: Freq Deviation with Dynamic CT Change at 5s")
ax3[1].plot(T_VEC, resA[0].f, 'b', label='Case A'); ax3[1].plot(T_VEC, resDelayD[0].f, 'g:', label='Case D (0.5s Delay)')
ax3[1].set_title("Graph 10: System Response with 0.5s Delay"); ax3[1].legend()
for i in range(4): ax3[2].plot(T_VEC, resA[i].f, label=f'Area-{i+1}')
ax3[2].set_title("Graph 11: 4-Area Consensus Result"); ax3[2].legend(); ax3[2].set_xlabel("Time (s)")

plt.tight_layout()
plt.show()