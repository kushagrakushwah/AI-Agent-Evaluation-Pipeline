import sqlite3
import json
import pandas as pd
from datetime import datetime
from app.models import EvaluationResult

DB_NAME = "eval_platform.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Logs Table
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id TEXT PRIMARY KEY, logs JSON, timestamp DATETIME)''')
    
    # 2. Evaluations Table
    c.execute('''CREATE TABLE IF NOT EXISTS evaluations 
                 (id TEXT, metrics JSON, aggregated_score REAL, suggestions JSON, timestamp DATETIME,
                  FOREIGN KEY(id) REFERENCES logs(id))''')
                  
    # 3. Annotations Table (For Multi-Annotator Agreement)
    c.execute('''CREATE TABLE IF NOT EXISTS annotations 
                 (conversation_id TEXT, annotator_id TEXT, score REAL, labels JSON,
                  PRIMARY KEY (conversation_id, annotator_id))''')
    
    conn.commit()
    conn.close()

def save_result(result: EvaluationResult):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO logs (id, logs, timestamp) VALUES (?, ?, ?)", 
                 (result.conversation_id, "{}", datetime.now())) # Storing placeholder for raw logs for now
    
    conn.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, ?)",
                 (result.conversation_id, 
                  json.dumps([m.dict() for m in result.metrics]), 
                  result.aggregated_score,
                  json.dumps([s.dict() for s in result.suggestions]),
                  datetime.now()))
    conn.commit()
    conn.close()

def save_annotation(conv_id, annotator, score):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO annotations VALUES (?, ?, ?, ?)", 
                 (conv_id, annotator, score, "[]"))
    conn.commit()
    conn.close()

def get_agreement_score():
    """
    Calculates Variance/Agreement between annotators.
    Requirement: 'Handle disagreement'
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT conversation_id, score FROM annotations", conn)
    conn.close()
    
    if df.empty or len(df) < 2:
        return 0.0, "Insufficient Data"
        
    # Calculate Standard Deviation per conversation (Proxy for disagreement)
    disagreement = df.groupby("conversation_id")['score'].std().mean()
    
    # Invert: Low std-dev = High Agreement (0.0 to 1.0 scale)
    agreement_index = 1.0 / (1.0 + disagreement) if pd.notna(disagreement) else 1.0
    return round(agreement_index, 2), "Variance-Based Agreement Index"