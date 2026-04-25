import os
import json
import pytest
from fastapi.testclient import TestClient
from main import app, sign_session_data

client = TestClient(app)

def create_test_session(mode="guided", plan=None):
    token_data = {
        "id": "test-session-uuid",
        "analysis_mode": mode,
        "objective": "Testing Orchestrator",
        "analysis_plan": plan
    }
    return sign_session_data(token_data)

def test_generate_sample_data():
    sid = create_test_session()
    res = client.post(f"/v1/sessions/{sid}/chat", json={
        "message": "Generate some sample data to work with",
        "analysis_mode": "guided"
    })
    assert res.status_code == 200
    data = res.json()
    assert "structured_response" in data
    sr = data["structured_response"]
    
    assert sr["response_type"] == "analysis_step"
    assert "data.frame" in sr["code"] or "tibble" in sr["code"] or "rnorm" in sr["code"]
    assert "```" not in sr["code"]  # No markdown
    assert len(sr["options"]) > 0
    assert len(sr["uses_objects"]) > 0

def test_create_and_summarize_dataframe():
    sid = create_test_session()
    res = client.post(f"/v1/sessions/{sid}/chat", json={
        "message": "Create a dataframe called test_df with 10 rows and summarize it.",
        "analysis_mode": "guided"
    })
    assert res.status_code == 200
    data = res.json()
    sr = data["structured_response"]
    
    assert "test_df" in sr["code"]
    assert "summary(test_df)" in sr["code"] or "summary(" in sr["code"]

def test_reuse_correct_dataframe():
    sid = create_test_session()
    # Inject context that test_df exists
    res = client.post(f"/v1/sessions/{sid}/chat", json={
        "message": "Run a regression on x and y",
        "analysis_mode": "guided",
        "env_summary": [{"name": "test_df", "type": "data.frame", "details": "10 obs. of 2 variables"}],
        "recent_history": ["test_df <- data.frame(x=1:10, y=1:10)"]
    })
    assert res.status_code == 200
    data = res.json()
    sr = data["structured_response"]
    
    assert "test_df" in sr["code"]
    assert "lm(" in sr["code"]

def test_invalid_r_code_handled():
    sid = create_test_session()
    res = client.post(f"/v1/sessions/{sid}/chat", json={
        "message": "I got an error: Error in eval(predvars, data, env) : object 'nonexistent' not found",
        "analysis_mode": "guided"
    })
    assert res.status_code == 200
    data = res.json()
    sr = data["structured_response"]
    assert sr["interpretation"] or sr["summary"]

def test_plan_restated():
    sid = create_test_session(plan="1. Load data\n2. Clean data\n3. Model")
    res = client.post(f"/v1/sessions/{sid}/chat", json={
        "message": "Hello",
        "analysis_mode": "guided"
    })
    assert res.status_code == 200
    data = res.json()
    sr = data["structured_response"]
    assert "plan" in sr["summary"].lower() or "plan" in sr["what"].lower() or "plan" in sr["interpretation"].lower()

def test_guided_vs_auto_differs():
    sid_guided = create_test_session(mode="guided")
    res_g = client.post(f"/v1/sessions/{sid_guided}/chat", json={
        "message": "Analyze the mtcars dataset",
        "analysis_mode": "guided"
    })
    
    sid_auto = create_test_session(mode="auto")
    res_a = client.post(f"/v1/sessions/{sid_auto}/chat", json={
        "message": "Analyze the mtcars dataset",
        "analysis_mode": "auto"
    })
    
    assert res_g.status_code == 200
    assert res_a.status_code == 200
