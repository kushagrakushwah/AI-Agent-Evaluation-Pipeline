from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# --- Enums for Strict Typing ---
class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class EvaluatorType(str, Enum):
    LLM_JUDGE = "llm_judge"
    TOOL_CHECK = "tool_check"
    COHERENCE = "coherence"

# --- Core Entities ---
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class Message(BaseModel):
    role: Role
    content: Optional[str] = ""
    tool_calls: Optional[List[ToolCall]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ConversationInput(BaseModel):
    id: str
    metadata: Dict[str, Any] = {}
    messages: List[Message]
    created_at: datetime = Field(default_factory=datetime.now)

# --- Evaluation Output ---
class EvaluationMetric(BaseModel):
    evaluator: EvaluatorType
    score: float # Normalized 0.0 to 1.0
    reasoning: str
    metadata: Dict[str, Any] = {}

class ImprovementSuggestion(BaseModel):
    target: str # "prompt" or "tool"
    suggestion: str
    rationale: str
    expected_impact: str

class EvaluationResult(BaseModel):
    conversation_id: str
    metrics: List[EvaluationMetric]
    aggregated_score: float
    issues: List[str]
    suggestions: List[ImprovementSuggestion]
    timestamp: datetime = Field(default_factory=datetime.now)

# --- Feedback & Meta-Eval ---
class HumanAnnotation(BaseModel):
    conversation_id: str
    annotator_id: str
    score: float
    labels: List[str]
    confidence: float # 0.0 to 1.0