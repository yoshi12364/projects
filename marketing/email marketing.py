import os
import json
import pandas as pd
import resend
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from  gptmodel import get_chat_completion, create_personal_poster

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

class MyState(TypedDict):
    csv_text: str
    positive_customers: List[dict]
    email_template: str
    dispatch_results: List[str]

# Nodes

def dataclean_node(state: MyState):
    print("--- [Node 1] Cleaning Data ---")
    path = r'c:\Users\Administrator\Downloads\customer_data_20.csv'
    df = pd.read_csv(path)
    df['Purchase_Amount'] = df['Purchase_Amount'].fillna(0)
    df['Customer_Review'] = df['Customer_Review'].fillna('No review provided')
    return {"csv_text": df.to_csv(index=False)}

def analyst_node(state: MyState):
    print("--- [Node 2] Analyzing Sentiment ---")
    prompt = f"Analyze: {state['csv_text']}. Return ONLY JSON with 'customers' list (name, email, product) for positive reviews."
    raw_response = get_chat_completion(prompt, json_mode=True)
    return {"positive_customers": json.loads(raw_response).get('customers', [])}

def designer_node(state: MyState):
    print("--- [Node 3] Designing Copy ---")
    prompt = "Write a 2-sentence high-energy email intro for wireless earbuds. Use [NAME] and [OLD_PRODUCT] tags."
    return {"email_template": get_chat_completion(prompt)}

def dispatcher_node(state: MyState):
    print("--- [Node 4] Dispatching Emails ---")
    logs = []
    for customer in state['positive_customers']:
        poster_file = create_personal_poster(customer['name'], customer['product'])
        body = state['email_template'].replace("[NAME]", customer['name']).replace("[OLD_PRODUCT]", str(customer['product']))
        
        try:
            with open(poster_file, "rb") as f:
                img_data = list(f.read())
            
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": customer['email'],
                "subject": f"Special Gift for {customer['name']}!",
                "html": f"<p>{body}</p>",
                "attachments": [{"filename": "Offer.png", "content": img_data}]
            })
            logs.append(f"SUCCESS: {customer['name']}")
        except Exception as e:
            logs.append(f"FAILED: {customer['name']} - {str(e)}")
    return {"dispatch_results": logs}

# Build Graph

workflow = StateGraph(MyState)
workflow.add_node("cleaner", dataclean_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("designer", designer_node)
workflow.add_node("dispatcher", dispatcher_node)

workflow.set_entry_point("cleaner")
workflow.add_edge("cleaner", "analyst")
workflow.add_edge("analyst", "designer")
workflow.add_edge("designer", "dispatcher")
workflow.add_edge("dispatcher", END)

app = workflow.compile()

if __name__ == "__main__":
    final_output = app.invoke({"csv_text": "", "positive_customers": [], "email_template": "", "dispatch_results": []})
    print("\n--- FINAL REPORT ---")
    for log in final_output['dispatch_results']:
        print(log)