from app.models import ImprovementSuggestion, EvaluationMetric, EvaluatorType
from typing import List
# from openai import OpenAI # <--- UNCOMMENT WHEN YOU HAVE KEY
import os

# ==============================================================================
# 🟢 MODE 1: LOGIC MAPPER (ACTIVE NOW)
# ==============================================================================

def generate_suggestions_logic(metrics: List[EvaluationMetric]) -> List[ImprovementSuggestion]:
    suggestions = []
    
    for metric in metrics:
        if metric.evaluator == EvaluatorType.TOOL_CHECK and metric.score < 0.6:
            if "no tool was called" in metric.reasoning:
                suggestions.append(ImprovementSuggestion(
                    target="prompts",
                    suggestion="Add System Prompt Rule: 'If user intent implies X, you MUST call tool Y.'",
                    rationale="Model hallucinated a text response instead of taking action.",
                    expected_impact="Aligns intent-to-action ratio."
                ))
            elif "missing required args" in metric.reasoning:
                suggestions.append(ImprovementSuggestion(
                    target="tools",
                    suggestion="Update tool schema definition to make missing arguments mandatory.",
                    rationale=f"Model failed to output required args. Error: {metric.reasoning}",
                    expected_impact="Reduces SchemaValidationErrors."
                ))
                
    return suggestions

# ==============================================================================
# 🔴 MODE 2: LLM OPTIMIZER (COMMENTED OUT)
# ==============================================================================

"""
def generate_suggestions_llm(metrics: List[EvaluationMetric]) -> List[ImprovementSuggestion]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    failures = [m.reasoning for m in metrics if m.score < 1.0]
    if not failures:
        return []

    prompt = f'''
    Based on these failures: {failures}
    Suggest a specific System Prompt update.
    '''
    
    # Call OpenAI (Pseudo-code)
    # response = client.chat.completions.create(...)
    # Parse response into ImprovementSuggestion objects
    
    return [] 
"""

# ==============================================================================
# 🎛️ CONTROLLER
# ==============================================================================

def generate_suggestions(metrics: List[EvaluationMetric]) -> List[ImprovementSuggestion]:
    USE_OPENAI = False # <--- CHANGE TO TRUE IF KEY AVAILABLE
    
    if USE_OPENAI:
        # return generate_suggestions_llm(metrics)
        pass
    
    return generate_suggestions_logic(metrics)