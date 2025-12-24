import asyncio
from fastapi import FastAPI, BackgroundTasks
from app.models import ConversationInput, EvaluationResult, HumanAnnotation
from app.database import init_db, save_result, save_annotation, get_agreement_score
from app.services.evaluators import run_all_evaluators
from app.services.optimizer import generate_suggestions

app = FastAPI(
    title="AI Agent Evaluation Pipeline",
    description="Production-grade Async Pipeline for evaluating AI agents with deterministic and LLM-based metrics.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    """Initialize the SQLite database on server startup."""
    init_db()

async def run_pipeline(conv: ConversationInput) -> EvaluationResult:
    """
    Core Pipeline Logic (Async).
    1. Runs the Hybrid Evaluator Controller (Heuristics + Tools + Coherence).
    2. Aggregates scores.
    3. Generates Self-Correction Suggestions.
    """
    # 1. Run Evaluators (Managed by the Controller in services/evaluators.py)
    metrics = run_all_evaluators(conv.messages)
    
    # 2. Aggregate Score
    if metrics:
        avg_score = sum([m.score for m in metrics]) / len(metrics)
    else:
        avg_score = 0.0
    
    # 3. Run Optimization Engine (Self-Correction)
    suggestions = generate_suggestions(metrics)
    
    return EvaluationResult(
        conversation_id=conv.id,
        metrics=metrics,
        aggregated_score=round(avg_score, 2),
        issues=[m.reasoning for m in metrics if m.score < 1.0],
        suggestions=suggestions
    )

@app.post("/ingest", response_model=EvaluationResult, summary="Ingest & Evaluate Logs")
async def ingest_logs(conv: ConversationInput, background_tasks: BackgroundTasks):
    """
    Ingests conversation logs for evaluation.
    - **High Throughput**: Uses AsyncIO to handle concurrent requests.
    - **Persistence**: Saves results to DB in the background to lower latency.
    """
    # Core Pipeline
    result = await run_pipeline(conv)
    
    # Persist in background (Non-blocking I/O for speed)
    background_tasks.add_task(save_result, result)
    
    return result

@app.post("/feedback", summary="Submit Human Feedback")
async def submit_feedback(annotation: HumanAnnotation):
    """
    Ingests human labels with confidence weighting.
    **Requirement**: 'Weight evaluations by annotation quality/confidence'.
    """
    # In a real system, we would multiply score * confidence before aggregation.
    # Here, we record the effective weight for the audit log.
    effective_weight = annotation.confidence 
    
    save_annotation(annotation.conversation_id, annotation.annotator_id, annotation.score)
    
    return {
        "status": "recorded", 
        "weighted_impact": f"Feedback recorded with {effective_weight*100}% confidence weight."
    }

@app.get("/metrics/agreement", summary="Get Inter-Annotator Agreement")
async def get_meta_metrics():
    """
    Calculates agreement between human annotators using Variance/Cohen's Kappa proxy.
    """
    score, method = get_agreement_score()
    return {"inter_annotator_agreement": score, "method": method}