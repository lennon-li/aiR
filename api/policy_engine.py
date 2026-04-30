# api/policy_engine.py

def get_session_policy(mode: str):
    """
    Maps the analysis mode to a behavior policy for the Analysis Coach.
    Modes: guided, balanced, autonomous
    """
    if mode == 'autonomous' or mode == 'auto':
        return {
            "label": "Autonomous",
            "explanation_depth": "low",
            "interaction_level": "none",
            "system_prompt_extension": "Write the R code. Send it directly to R through air-r-service. Do not ask unnecessary questions. Do not print a long natural-language explanation before execution. Show only a short status message. Store/read the execution result internally for follow-up questions."
        }
    elif mode == 'balanced':
        return {
            "label": "Balanced",
            "explanation_depth": "medium",
            "interaction_level": "medium",
            "system_prompt_extension": "Give concise R code. Keep explanation short. Suggest execution or send depending on existing app policy. Use real console output as hidden context if executed. Ask only when a real decision is needed."
        }
    else: # guided (default)
        return {
            "label": "Guided",
            "explanation_depth": "high",
            "interaction_level": "high",
            "system_prompt_extension": "Do not auto-execute code. Propose what to do next. Give concise R code. Explain why this is the next step. Show 'Send to Console'. Do not display fake results."
        }
