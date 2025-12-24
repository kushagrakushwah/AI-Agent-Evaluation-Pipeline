import re
import json
import random
import os
from typing import List, Dict
from app.models import Message, ToolCall, EvaluationMetric, EvaluatorType
# from openai import OpenAI # <--- UNCOMMENT WHEN YOU HAVE KEY

# ==============================================================================
# 🟢 MODE 1: DETERMINISTIC LOGIC (ACTIVE NOW - FREE & FAST)
# ==============================================================================

def check_heuristics(messages: List[Message]) -> EvaluationMetric:
    """Checks latency and message formatting."""
    issues = []
    score = 1.0
    
    # Latency Simulation
    simulated_latency_ms = random.randint(100, 1500)
    LATENCY_THRESHOLD = 1000
    
    if simulated_latency_ms > LATENCY_THRESHOLD:
        issues.append(f"Latency violation: Response took {simulated_latency_ms}ms (Threshold: {LATENCY_THRESHOLD}ms)")
        score -= 0.15
        
    for msg in messages:
        if not msg.content and not msg.tool_calls:
            issues.append(f"Empty message detected for role {msg.role}")
            score -= 0.2
    
    return EvaluationMetric(
        evaluator=EvaluatorType.COHERENCE,
        score=max(0.0, score),
        reasoning=f"Heuristics Check: {len(issues)} issues found. System Latency: {simulated_latency_ms}ms.",
        metadata={"issues": issues, "latency_ms": simulated_latency_ms}
    )

def evaluate_tool_usage(messages: List[Message]) -> EvaluationMetric:
    """Validates tool calls using Regex Intent Matching (Deterministic)."""
    score = 1.0
    reasoning = []
    
    intent_patterns = {
        r"(book|find|search).*flight": "flight_search",
        r"refund": "process_refund",
        r"weather": "get_weather"
    }
    
    # 1. Detect Intent
    user_intent = None
    for msg in messages:
        if msg.role == "user":
            for pattern, tool_name in intent_patterns.items():
                if re.search(pattern, msg.content, re.IGNORECASE):
                    user_intent = tool_name
                    break
    
    if not user_intent:
        return EvaluationMetric(evaluator=EvaluatorType.TOOL_CHECK, score=1.0, reasoning="No tool intent detected.")

    # 2. Check Execution
    tool_called = False
    for msg in messages:
        if msg.role == "assistant" and msg.tool_calls:
            for tool in msg.tool_calls:
                if tool.name == user_intent:
                    tool_called = True

    if not tool_called:
        score = 0.0
        reasoning.append(f"User asked for '{user_intent}' but no tool was called (Hallucination).")
    else:
        reasoning.append(f"Tool '{user_intent}' called correctly.")

    return EvaluationMetric(
        evaluator=EvaluatorType.TOOL_CHECK,
        score=score,
        reasoning="; ".join(reasoning)
    )

def evaluate_coherence(messages: List[Message]) -> EvaluationMetric:
    """Checks conversation flow."""
    last_msg = messages[-1]
    if last_msg.role == "tool":
        return EvaluationMetric(evaluator=EvaluatorType.COHERENCE, score=0.5, reasoning="Ended abruptly on tool output.")
    return EvaluationMetric(evaluator=EvaluatorType.COHERENCE, score=1.0, reasoning="Flow consistent.")

# ==============================================================================
# 🔴 MODE 2: LLM-AS-A-JUDGE (COMMENTED OUT - REQUIRES API KEY)
# Instructions: To enable, uncomment this block and the import at top.
# ==============================================================================

"""
class LLMJudge:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def evaluate(self, messages: List[Message]) -> List[EvaluationMetric]:
        conv_text = "\\n".join([f"{m.role}: {m.content}" for m in messages])
        
        prompt = f'''
        You are a QA Evaluator. Analyze this conversation for 1) Tool Usage and 2) Coherence.
        
        Conversation:
        {conv_text}
        
        Output JSON format strictly:
        {{
            "tool_score": 0.0-1.0,
            "tool_reasoning": "string",
            "coherence_score": 0.0-1.0,
            "coherence_reasoning": "string"
        }}
        '''
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            
            return [
                EvaluationMetric(evaluator=EvaluatorType.TOOL_CHECK, score=data['tool_score'], reasoning=data['tool_reasoning']),
                EvaluationMetric(evaluator=EvaluatorType.COHERENCE, score=data['coherence_score'], reasoning=data['coherence_reasoning'])
            ]
        except Exception as e:
            return []
"""

# ==============================================================================
# 🎛️ CONTROLLER
# ==============================================================================

def run_all_evaluators(messages: List[Message]) -> List[EvaluationMetric]:
    # 1. Always run Heuristics (Fast)
    metrics = [check_heuristics(messages)]
    
    # 2. Logic Switch
    USE_OPENAI = False # <--- CHANGE TO TRUE TO USE LLM CODE ABOVE
    
    if USE_OPENAI:
        # metrics.extend(LLMJudge().evaluate(messages)) # Uncomment when LLM class is active
        pass
    else:
        # Run Deterministic Checks
        metrics.append(evaluate_tool_usage(messages))
        metrics.append(evaluate_coherence(messages))
        
    return metrics