from app.models import ImprovementSuggestion, EvaluationMetric, EvaluatorType
from typing import List, Optional

def generate_suggestions(metrics: List[EvaluationMetric]) -> List[ImprovementSuggestion]:
    suggestions = []
    
    for metric in metrics:
        # STRATEGY 1: Fix Hallucinations (Tool Check Failures)
        if metric.evaluator == EvaluatorType.TOOL_CHECK and metric.score < 0.6:
            if "missing required args" in metric.reasoning:
                suggestions.append(ImprovementSuggestion(
                    target="tools",
                    suggestion="Update tool schema definition in 'tools.json' to make missing arguments mandatory.",
                    rationale=f"Model failed to output required args. Error: {metric.reasoning}",
                    expected_impact="Reduces SchemaValidationErrors by 90%."
                ))
            elif "no tool was called" in metric.reasoning:
                suggestions.append(ImprovementSuggestion(
                    target="prompts",
                    suggestion="Add System Prompt Rule: 'If user intent implies X, you MUST call tool Y.'",
                    rationale="Model hallucinated a text response instead of taking action.",
                    expected_impact="Aligns intent-to-action ratio."
                ))

        # STRATEGY 2: Fix Tone/Heuristics
        if metric.evaluator == EvaluatorType.COHERENCE and metric.score < 0.5:
             suggestions.append(ImprovementSuggestion(
                    target="prompts",
                    suggestion="Inject 'Chain of Thought' instructions for complex flows.",
                    rationale="Conversation lost coherence/context.",
                    expected_impact="Improves context retention."
                ))
                
    return suggestions