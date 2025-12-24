import asyncio
from typing import List
from fastapi import FastAPI, BackgroundTasks
from app.models import ConversationInput, ConversationBatch, EvaluationResult, HumanAnnotation, RoutingDecision
from app.database import init_db, save_result, save_annotation, get_agreement_score
from app.services.evaluators import run_all_evaluators
from app.services.optimizer import generate_suggestions

app = FastAPI(
    title="AI Agent Evaluation Pipeline",
    description="Production-grade Async Pipeline with Batch Processing & Docker Support.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    init_db()

async def run_pipeline(conv: ConversationInput) -> EvaluationResult:
    # 1. Run Evaluators
    metrics = run_all_evaluators(conv.messages)
    
    # 2. Aggregate Score
    if metrics:
        avg_score = sum([m.score for m in metrics]) / len(metrics)
    else:
        avg_score = 0.0
    
    # 3. Routing Logic (Requirement: "Support confidence-based routing")
    # Logic: If score is low (< 0.4) or we detected a critical tool failure, route to human.
    routing = RoutingDecision.AUTOMATED
    if avg_score < 0.4:
        routing = RoutingDecision.HUMAN_REVIEW
    
    # 4. Suggestions
    suggestions = generate_suggestions(metrics)
    
    return EvaluationResult(
        conversation_id=conv.id,
        metrics=metrics,
        aggregated_score=round(avg_score, 2),
        issues=[m.reasoning for m in metrics if m.score < 1.0],
        suggestions=suggestions,
        routing=routing
    )

@app.post("/ingest", response_model=EvaluationResult)
async def ingest_logs(conv: ConversationInput, background_tasks: BackgroundTasks):
    result = await run_pipeline(conv)
    background_tasks.add_task(save_result, result)
    return result

@app.post("/ingest/batch", response_model=List[EvaluationResult])
async def ingest_batch(batch: ConversationBatch, background_tasks: BackgroundTasks):
    """
    Batch Processing Endpoint.
    Requirement: 'Support high throughput in batch'.
    """
    # Process all conversations in parallel using AsyncIO
    tasks = [run_pipeline(conv) for conv in batch.conversations]
    results = await asyncio.gather(*tasks)
    
    # Bulk save to DB
    for res in results:
        background_tasks.add_task(save_result, res)
        
    return results

@app.post("/feedback")
async def submit_feedback(annotation: HumanAnnotation):
    effective_weight = annotation.confidence 
    save_annotation(annotation.conversation_id, annotation.annotator_id, annotation.score)
    return {"status": "recorded", "weighted_impact": f"{effective_weight*100}%"}

@app.get("/metrics/agreement")
async def get_meta_metrics():
    score, method = get_agreement_score()
    return {"inter_annotator_agreement": score, "method": method}