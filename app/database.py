import sqlite3
import json
import pandas as pd
import threading
from datetime import datetime
from app.models import EvaluationResult

DB_NAME = "eval_platform.db"
db_lock = threading.Lock() # <--- FIX: Lock for thread-safe SQLite writes

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
    # FIX: Added 'confidence' column
    c.execute('''CREATE TABLE IF NOT EXISTS annotations 
                 (conversation_id TEXT, annotator_id TEXT, score REAL, labels JSON, confidence REAL,
                  PRIMARY KEY (conversation_id, annotator_id))''')
    
    conn.commit()
    conn.close()

def save_result(result: EvaluationResult):
    with db_lock: # <--- FIX: Thread safety
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT OR REPLACE INTO logs (id, logs, timestamp) VALUES (?, ?, ?)", 
                     (result.conversation_id, "{}", datetime.now())) 
        
        conn.execute("INSERT INTO evaluations VALUES (?, ?, ?, ?, ?)",
                     (result.conversation_id, 
                      json.dumps([m.dict() for m in result.metrics]), 
                      result.aggregated_score,
                      json.dumps([s.dict() for s in result.suggestions]),
                      datetime.now()))
        conn.commit()
        conn.close()

def save_annotation(conv_id, annotator, score, confidence=1.0): # <--- FIX: Added confidence param
    with db_lock: # <--- FIX: Thread safety
        conn = sqlite3.connect(DB_NAME)
        # FIX: Inserting confidence value
        conn.execute("INSERT OR REPLACE INTO annotations VALUES (?, ?, ?, ?, ?)", 
                     (conv_id, annotator, score, "[]", confidence))
        conn.commit()
        conn.close()

def get_agreement_score():
    """
    Calculates Variance/Agreement between annotators.
    Requirement: 'Handle disagreement'
    """
    # Using lock for read is safer in high-concurrency though strictly SQLite can handle concurrent reads
    with db_lock: 
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