import os
import pandas as pd
import requests
from fastapi import FastAPI, Header, HTTPException, Depends
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="YOUTUBE_ANALYSIS SYSTEM")


API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

app = FastAPI(title="YOUTUBE_ANALYSIS SYSTEM")

EXTERNAL_APP_URL = "http://127.0.0.1:8000"
SYSTEM_JSON_URL = f"{EXTERNAL_APP_URL}/openapi.json"

def check_system_integrity():
    """Checks the Auth system's system .json to verify it is online"""
    try:
        response = requests.get(SYSTEM_JSON_URL)
        return response.status_code == 200
    except:
        return False

def validate_external_session(
    user_id: int = Header(..., alias="User-Id"),
    session_id: str = Header(..., alias="Session-Id")
):
    if not check_system_integrity():
        raise HTTPException(status_code=503, detail="Auth System Metadata unreachable")

    try:
        response = requests.post(
            f"{EXTERNAL_APP_URL}/authenticate",
            json={"userid": user_id, "sessionid": session_id}
        )
        
        auth_data = response.json()
     
        if response.status_code == 200 and auth_data.get("success") == "true":
            return auth_data
        
        raise HTTPException(status_code=403, detail="Unauthorized: External session invalid")

    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Auth Service is down")
@app.get("/api/youtube/search-stats")
def search_stats(q: str, max_results: int = 5, user: dict = Depends(validate_external_session)):
    """Search using external app authentication"""
    
  
    s_params = {'part': 'snippet', 'q': q, 'type': 'video', 'maxResults': max_results, 'key': API_KEY}
    response = requests.get(f"{BASE_URL}/search", params=s_params)
    s_res = response.json()
    
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"YouTube API Error: {s_res.get('error', {}).get('message', 'Unknown Error')}")

    items = s_res.get('items', [])
    if not items:
        raise HTTPException(status_code=404, detail=f"No results found for query: {q}")

    ids = [item['id']['videoId'] for item in items]

    v_params = {'part': 'statistics,snippet', 'id': ','.join(ids), 'key': API_KEY}
    v_res = requests.get(f"{BASE_URL}/videos", params=v_params).json()

    return [{
        'title': v['snippet']['title'],
        'video_url': f"https://www.youtube.com/watch?v={v['id']}",
        'views': int(v['statistics'].get('viewCount', 0)),
        'likes': int(v['statistics'].get('likeCount', 0))
    } for v in v_res.get('items', [])]
@app.get("/api/trending")
def get_trending(region: str = "IN", category_id: str = "0", max_results: int = 5, user: dict = Depends(validate_external_session)):
    """Get trending using external app authentication"""
    params = {'part': 'snippet,statistics', 'chart': 'mostPopular', 'regionCode': region, 'videoCategoryId': category_id, 'key': API_KEY, 'maxResults': max_results}
    res = requests.get(f"{BASE_URL}/videos", params=params).json()
    return [{
        'title': i['snippet']['title'],
        'video_url': f"https://www.youtube.com/watch?v={i['id']}",
        'views': int(i['statistics'].get('viewCount', 0)),
        'likes': int(i['statistics'].get('likeCount', 0))
    } for i in res.get('items', [])]

@app.get("/api/search-and-analyze")
def search_and_analyze(query: str, user: dict = Depends(validate_external_session)):
    """Analyze engagement using external app authentication"""
    s_res = requests.get(f"{BASE_URL}/search", params={'part': 'snippet', 'q': query, 'type': 'video', 'maxResults': 5, 'key': API_KEY}).json()
    ids = ",".join([i['id']['videoId'] for i in s_res.get('items', [])])
    v_res = requests.get(f"{BASE_URL}/videos", params={'part': 'statistics,snippet', 'id': ids, 'key': API_KEY}).json()
    
    data = [{'title': i['snippet']['title'], 'url': f"https://www.youtube.com/watch?v={i['id']}", 'views': int(i['statistics'].get('viewCount', 0)), 'likes': int(i['statistics'].get('likeCount', 0))} for i in v_res.get('items', [])]
    
    df = pd.DataFrame(data)
    df['engagement'] = (df['likes'] / df['views'].replace(0, 1)) * 100
    
    return {
        "external_user": user, 
        "metrics": {"avg_engagement": f"{round(df['engagement'].mean(), 2)}%", "total_views": int(df['views'].sum())},
        "top_video": df.loc[df['views'].idxmax()].to_dict()
    }

@app.get("/api/categories")
def get_categories(region: str = "IN", user: dict = Depends(validate_external_session)):
    """Get video categories using external app authentication"""
    res = requests.get(f"{BASE_URL}/videoCategories", params={'part': 'snippet', 'regionCode': region, 'key': API_KEY}).json()
    return [{'id': i['id'], 'name': i['snippet']['title']} for i in res.get('items', [])]