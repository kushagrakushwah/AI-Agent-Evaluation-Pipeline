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
    """Checks actual latency and message formatting."""
    issues = []
    score = 1.0
    
    # 1. LATENCY CHECK (Fixed: Uses actual timestamps instead of simulation)
    # Logic: Find the last 'assistant' message and the 'user' message immediately preceding it.
    last_assistant_time = None
    last_user_time = None
    
    # Iterate backwards to find the most recent interaction pair
    for msg in reversed(messages):
        if msg.role == "assistant" and not last_assistant_time:
            last_assistant_time = msg.timestamp
        if msg.role == "user" and not last_user_time and last_assistant_time:
            last_user_time = msg.timestamp
            break # Found the pair
            
    real_latency_ms = 0.0
    LATENCY_THRESHOLD = 1000 # 1 second threshold
    
    if last_user_time and last_assistant_time:
        delta = last_assistant_time - last_user_time
        real_latency_ms = delta.total_seconds() * 1000
        
        if real_latency_ms > LATENCY_THRESHOLD:
            issues.append(f"Latency violation: Response took {real_latency_ms:.2f}ms (Threshold: {LATENCY_THRESHOLD}ms)")
            score -= 0.15
    else:
        # Fallback if timestamps are missing or conversation structure is odd
        issues.append("Could not calculate latency (missing timestamp pair).")

    # 2. EMPTY MESSAGE CHECK
    for msg in messages:
        if not msg.content and not msg.tool_calls:
            issues.append(f"Empty message detected for role {msg.role}")
            score -= 0.2
    
    return EvaluationMetric(
        evaluator=EvaluatorType.COHERENCE,
        score=max(0.0, score),
        reasoning=f"Heuristics Check: {len(issues)} issues found. Actual Latency: {real_latency_ms:.2f}ms.",
        metadata={"issues": issues, "latency_ms": real_latency_ms}
    )

def evaluate_tool_usage(messages: List[Message]) -> EvaluationMetric:
    """Validates tool calls using Regex Intent and Parameter Formatting."""
    score = 1.0
    reasoning = []
    
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

    # 2. Check Execution & Format
    tool_called = False
    valid_args = True
    
    for msg in messages:
        if msg.role == "assistant" and msg.tool_calls:
            for tool in msg.tool_calls:
                if tool.name == user_intent:
                    tool_called = True
                    
                    # A. Check Missing Args
                    required_args = tool_definitions.get(tool.name, [])
                    missing = [arg for arg in required_args if arg not in tool.arguments]
                    if missing:
                        valid_args = False
                        reasoning.append(f"Tool '{tool.name}' missing args: {missing}")
                        score = 0.5
                    
                    # B. Check Date Format
                    if tool.name == "flight_search" and "date" in tool.arguments:
                        date_val = tool.arguments["date"]
                        # Regex for YYYY-MM-DD
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_val):
                            valid_args = False
                            reasoning.append(f"Invalid Date Format in 'flight_search': '{date_val}'. Expected YYYY-MM-DD.")
                            score = 0.5

    if not tool_called:
        score = 0.0
        reasoning.append(f"User asked for '{user_intent}' but no tool was called (Hallucination).")
    elif valid_args:
        reasoning.append(f"Tool '{user_intent}' called correctly.")

    return EvaluationMetric(
        evaluator=EvaluatorType.TOOL_CHECK,
        score=score,
        reasoning="; ".join(reasoning)
    )

def evaluate_coherence(messages: List[Message]) -> EvaluationMetric:
    """Checks conversation flow, repetition, and abrupt endings."""
    issues = []
    score = 1.0
    
    # 1. Check for abrupt ending on tool output (Existing)
    last_msg = messages[-1]
    if last_msg.role == "tool":
        issues.append("Ended abruptly on tool output.")
        score -= 0.5

    # 2. Check for Repetition Loops (Assistant repeating itself)
    assistant_msgs = [m.content for m in messages if m.role == "assistant" and m.content]
    if len(assistant_msgs) != len(set(assistant_msgs)):
        issues.append("Detected repetitive content (Loop).")
        score -= 0.3

    # 3. Check for Empty User Turns (ignoring tool outputs)
    for msg in messages:
        if msg.role == "user" and not msg.content:
            issues.append("Empty user message found.")
            score -= 0.2

    return EvaluationMetric(
        evaluator=EvaluatorType.COHERENCE, 
        score=max(0.0, score), 
        reasoning="; ".join(issues) if issues else "Flow consistent."
    )

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