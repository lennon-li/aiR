# api/vertex.py
import os
import re
from google.cloud import discoveryengine_v1beta as discoveryengine

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = os.getenv("SEARCH_LOCATION", "global") 
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "r-docs-store_1776610230621")

# The library uses serving_config path
# For data stores, it's often projects/{project}/locations/{location}/collections/default_collection/dataStores/{data_store}/servingConfigs/default_search
SERVING_CONFIG = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/servingConfigs/default_search"

def search_r_docs(query: str):
    """Retrieves document snippets using Vertex AI Search."""
    try:
        client = discoveryengine.SearchServiceClient()
        
        request = discoveryengine.SearchRequest(
            serving_config=SERVING_CONFIG,
            query=query,
            page_size=3
        )
        
        response = client.search(request)
        
        snippets = []
        for result in response.results:
            # Derived struct data contains snippets
            data = result.document.derived_struct_data
            if data and "snippets" in data:
                for s in data["snippets"]:
                    if "snippet" in s:
                        snippets.append(s["snippet"])
        
        return "\n\n".join(snippets), len(snippets), 0
    except Exception as e:
        print(f"Search Error: {e}")
        return "", 0, 0

def converse_r_docs(query: str, session_uuid: str, preamble: str = ""):
    """Uses Vertex AI Search Answer API for high-quality grounded chat."""
    try:
        # 1. Honest Fallback Check
        grounded_packages = ["base", "dplyr", "ggplot2", "mgcv", "tidyr", "purrr", "stringr", "data.table"]
        mentions = re.findall(r"\b([a-zA-Z0-9\.]+)\b", query.lower())
        unsupported = []
        popular_missing = ["shiny", "plotly", "sf", "reticulate", "caret", "mlr3", "scran", "seurat"]
        for m in mentions:
            if m in popular_missing:
                unsupported.append(m)
        
        if unsupported:
            pkg = unsupported[0]
            return f"I'm not grounded for '{pkg}' yet. I can still try to help in a general way, but I don't have official documentation loaded for it."

        # 2. Proceed with Vertex AI Search Answer API
        client = discoveryengine.ConversationalSearchServiceClient()
        
        request = discoveryengine.AnswerQueryRequest(
            serving_config=SERVING_CONFIG,
            query=discoveryengine.Query(text_query=query),
            answer_generation_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
                ignore_adversarial_query=True,
                ignore_non_answer_seeking_query=False,
                ignore_low_relevant_content=False,
                prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                    preamble=preamble
                ),
                include_citations=True
            )
        )
        
        response = client.answer_query(request)
        text = response.answer.answer_text

        if not text or "could not be generated" in text:
            # Check skipped reasons
            reasons = response.answer.answer_skipped_reasons
            if any(r == discoveryengine.Answer.AnswerSkippedReason.OUT_OF_DOMAIN for r in reasons):
                 return "What we’re doing: Simulating sample data.\nWhy: To provide a starting point for analysis.\ndf <- data.frame(x=rnorm(100), y=runif(100))\nsummary(df)\nInterpretation: A simple 100-row dataframe with random normal and uniform distributions.\nNext step: Try plotting these variables."
            return "What we’re doing: Providing a sample dataset.\nWhy: To help you get started immediately.\ndf <- data.frame(val1=rnorm(50), val2=rnorm(50))\nhead(df)\nInterpretation: A 50-row dataset with two normally distributed variables.\nNext step: Ask me to run a regression or create a plot."

        return text
    except Exception as e:
        return f"R Copilot Connection Error: {str(e)}"
