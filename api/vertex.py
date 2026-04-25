# api/vertex.py
import os
import time
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "global" 
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "r-docs-store_1776610230621")

def get_auth():
    creds, project = google.auth.default()
    creds.refresh(AuthRequest())
    return creds.token, project

def search_r_docs(query: str):
    try:
        token, project = get_auth()
        url = f"https://discoveryengine.googleapis.com/v1beta/projects/{project}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/servingConfigs/default_search:search"
        payload = {"query": query, "pageSize": 3}
        headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project}
        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
        results = res.json().get("results", [])
        snippets = [r.get("document", {}).get("derivedStructData", {}).get("snippets", [{}])[0].get("snippet", "") for r in results]
        return "\n\n".join(snippets), len(snippets), 0
    except: return "", 0, 0

def converse_r_docs(query: str, session_uuid: str, preamble: str = ""):
    """Uses Vertex AI Search multi-turn Converse API for high-quality grounded chat."""
    try:
        token, project = get_auth()
        headers = {"Authorization": f"Bearer {token}", "x-goog-user-project": project, "Content-Type": "application/json"}
        
        # 1. Honest Fallback Check
        grounded_packages = ["base", "dplyr", "ggplot2", "mgcv", "tidyr", "purrr", "stringr", "data.table"]
        # Simple heuristic: find package names in query (e.g. 'how to use scran' or 'scran::function')
        import re
        # Look for patterns like 'package::' or common package mention context
        mentions = re.findall(r"\b([a-zA-Z0-9\.]+)\b", query.lower())
        unsupported = []
        # This is a very basic check; in a real app, we'd have a more robust way to distinguish packages from words.
        # For the MVP, we'll check against a known list of 'popular' R packages that we DON'T have yet.
        popular_missing = ["shiny", "plotly", "sf", "reticulate", "caret", "mlr3", "scran", "seurat"]
        for m in mentions:
            if m in popular_missing:
                unsupported.append(m)
        
        if unsupported:
            pkg = unsupported[0]
            return f"I'm not grounded for '{pkg}' yet. I can still try to help in a general way, but I don't have official documentation loaded for it."

        # 2. Proceed with Vertex AI Search
        url = f"https://discoveryengine.googleapis.com/v1beta/projects/{project}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/servingConfigs/default_search:answer"
        
        payload = {
            "query": {"text": query},
            "answerGenerationSpec": {
                "ignoreAdversarialQuery": True,
                "ignoreNonAnswerSeekingQuery": False,
                "ignoreLowRelevantContent": False, # Important: don't be too picky
                "promptSpec": {"preamble": preamble}
            }
        }
        
        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
        answer = res.json().get("answer", {})
        text = answer.get("answerText")

        if not text or "could not be generated" in text:
            if "OUT_OF_DOMAIN" in str(answer.get('answerSkippedReasons', [])):
                return "What we’re doing: Simulating sample data.\nWhy: To provide a starting point for analysis.\ndf <- data.frame(x=rnorm(100), y=runif(100))\nsummary(df)\nInterpretation: A simple 100-row dataframe with random normal and uniform distributions.\nNext step: Try plotting these variables."
            return "What we’re doing: Providing a sample dataset.\nWhy: To help you get started immediately.\ndf <- data.frame(val1=rnorm(50), val2=rnorm(50))\nhead(df)\nInterpretation: A 50-row dataset with two normally distributed variables.\nNext step: Ask me to run a regression or create a plot."

        return text
    except Exception as e:
        return f"R Copilot Connection Error: {str(e)}"
