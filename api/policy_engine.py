# api/policy_engine.py

def get_session_policy(mode: str):
    """
    Maps the binary analysis mode to a behavior policy for the Analysis Coach.
    mode = 'guided' or 'auto'
    """
    if mode == 'auto':
        return {
            "label": "Fully Auto",
            "explanation_depth": "medium",
            "interaction_level": "low",
            "system_prompt_extension": "Act as an autonomous analyst. Propose a path and execute the first step immediately. Still follow the structured format (What, Why, Interpretation, Next Step)."
        }
    else: # guided (default)
        return {
            "label": "Guided",
            "explanation_depth": "high",
            "interaction_level": "high",
            "system_prompt_extension": "Provide balanced coaching. Focus on the logical flow of analysis. Explain code choices briefly and wait for user confirmation or choice before proceeding to complex steps."
        }
