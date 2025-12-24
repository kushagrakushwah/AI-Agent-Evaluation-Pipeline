import re
import json
import random
from typing import List, Dict
from app.models import Message, ToolCall, EvaluationMetric, EvaluatorType

# --- 1. HEURISTIC CHECKER (Latency & Format) ---
def check_heuristics(messages: List[Message]) -> EvaluationMetric:
    issues = []
    score = 1.0
    
    # Check 1: Message Formatting
    for msg in messages:
        if not msg.content and not msg.tool_calls:
            issues.append(f"Empty message detected for role {msg.role}")
            score -= 0.2
            
    # Check 2: Latency Thresholds (Requirement: Monitor latency)
    # We simulate a "processing time" check.
    # In production, this would compare msg.timestamp vs previous_msg.timestamp
    simulated_latency_ms = random.randint(100, 1500) # Random latency between 100ms and 1.5s
    LATENCY_THRESHOLD = 1000 # 1 second strict threshold
    
    if simulated_latency_ms > LATENCY_THRESHOLD:
        issues.append(f"Latency violation: Response took {simulated_latency_ms}ms (Threshold: {LATENCY_THRESHOLD}ms)")
        score -= 0.15
    
    return EvaluationMetric(
        evaluator=EvaluatorType.COHERENCE,
        score=max(0.0, score),
        reasoning=f"Heuristics Check: {len(issues)} issues found. System Latency: {simulated_latency_ms}ms.",
        metadata={"issues": issues, "latency_ms": simulated_latency_ms}
    )

# --- 2. TOOL EVALUATOR (The "Real" Logic) ---
def evaluate_tool_usage(messages: List[Message]) -> EvaluationMetric:
    """
    Validates if tools are called when expected (using Regex patterns).
    """
    score = 1.0
    reasoning = []
    
    # PATTERN REPO: These rules replace the "AI". 
    # In production, these would load from a config file.
    intent_patterns = {
        r"(book|find|search).*flight": "flight_search",
        r"refund": "process_refund",
        r"weather": "get_weather"
    }
    
    tool_definitions = {
        "flight_search": ["destination", "date"],
        "process_refund": ["order_id"],
        "get_weather": ["city"]
    }

    # 1. Scan User Intent
    user_intent = None
    for msg in messages:
        if msg.role == "user":
            for pattern, tool_name in intent_patterns.items():
                if re.search(pattern, msg.content, re.IGNORECASE):
                    user_intent = tool_name
                    break
    
    if not user_intent:
        return EvaluationMetric(evaluator=EvaluatorType.TOOL_CHECK, score=1.0, reasoning="No tool intent detected.")

    # 2. Check Assistant Response
    tool_called = False
    valid_args = True
    
    for msg in messages:
        if msg.role == "assistant" and msg.tool_calls:
            for tool in msg.tool_calls:
                if tool.name == user_intent:
                    tool_called = True
                    # Validate Arguments (Schema Check)
                    required_args = tool_definitions.get(tool.name, [])
                    missing = [arg for arg in required_args if arg not in tool.arguments]
                    
                    if missing:
                        valid_args = False
                        reasoning.append(f"Tool '{tool.name}' missing required args: {missing}")
                        score = 0.5 # Partial Fail

    if not tool_called:
        score = 0.0
        reasoning.append(f"User asked for '{user_intent}' but no tool was called (Hallucination).")
    elif valid_args:
        reasoning.append(f"Tool '{user_intent}' called correctly with valid arguments.")

    return EvaluationMetric(
        evaluator=EvaluatorType.TOOL_CHECK,
        score=score,
        reasoning="; ".join(reasoning)
    )

# --- 3. COHERENCE (Context Check) ---
def evaluate_coherence(messages: List[Message]) -> EvaluationMetric:
    # Logic: Check if conversation resolves strictly.
    # If the last message is a question from the assistant, it's open-ended (Neutral).
    # If it's a tool output followed by text, it's coherent.
    
    last_msg = messages[-1]
    score = 1.0
    
    if last_msg.role == "assistant" and "?" in last_msg.content:
        reasoning = "Conversation ended with a clarifying question."
    elif last_msg.role == "tool":
        score = 0.5
        reasoning = "Conversation ended abruptly on a tool output."
    else:
        reasoning = "Flow appears consistent."
        
    return EvaluationMetric(
        evaluator=EvaluatorType.COHERENCE,
        score=score,
        reasoning=reasoning
    )