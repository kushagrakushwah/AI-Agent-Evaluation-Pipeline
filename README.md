# AI Agent Evaluation Pipeline (Production Design)

## 🏗️ Architecture & Design Decisions

### 1. Throughput Strategy (Requirement: 1000+ cpm)
While the prototype uses **Async FastAPI**, the production design scales via Event-Driven Architecture:
* **Ingestion**: Conversations pushed to **Apache Kafka** topic `conversations.raw`.
* **Processing**: A consumer group of **Celery Workers** (autoscaling on K8s) processes logs asynchronously.
* **Storage**: **TimescaleDB (PostgreSQL)** for logs (write-heavy) + **Redis** for real-time leaderboards.

### 2. Evaluator Framework (No-Compromise)
We implement a hybrid approach:
* **Deterministic Evaluators**: Regex/Schema validation for Tool Calls (Speed: <10ms).
* **LLM-as-a-Judge**: Sampled evaluation (e.g., 5% of traffic) using GPT-4o for qualitative checks (Helpfulness/Tone).
* **Optimization**: Failures map to a Vector DB of "Known Issues" to retrieve prompt patches dynamically.

### 3. Feedback & Meta-Eval
* **Agreement**: We use **Cohen's Kappa** to measure Inter-Annotator Agreement.
* **Calibration**: If `Human_Score` vs `LLM_Score` variance > 0.5, the conversation is flagged for "Gold Set" review to fine-tune the LLM Judge.

## 🚀 Setup (Prototype)

1.  **Install**: `pip install -r requirements.txt`
2.  **Run Backend**: `uvicorn app.main:app --reload`
3.  **Run UI**: `streamlit run frontend/dashboard.py`

## ⚖️ Trade-offs (Gap Analysis)
* **Database**: SQLite used for prototype portability; Production requires PostgreSQL.
* **LLM Integration**: Abstracted to `services/evaluators.py`. Currently uses robust Heuristic/Regex patterns to simulate logic due to budget constraints ($0 budget). Interfaces are ready for `OpenAI` injection.