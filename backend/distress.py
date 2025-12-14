# distress.py
import pandas as pd
import numpy as np
from transformers import pipeline
from typing import List, Dict

# Initialize the sentiment analyzer globally (loaded once at startup)
SENTIMENT_ANALYZER = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)

def analyze_sentiment(reports: List[str]) -> List[Dict[str, float]]:
    sentiments = SENTIMENT_ANALYZER(reports)
    results = [
        {"report": report, "label": sentiment['label'], "score": sentiment['score']}
        for report, sentiment in zip(reports, sentiments)
    ]
    return results

def detect_distress_signals(sentiment_results: List[Dict[str, float]], threshold: float = 0.9) -> List[Dict[str, float]]:
    return [result for result in sentiment_results if result["label"] == "NEGATIVE" and result["score"] >= threshold]

def calculate_distress_percentage(total_reports: int, distress_signals: List[Dict[str, float]]) -> float:
    if total_reports == 0:
        return 0.0
    distress_count = len(distress_signals)
    return round((distress_count / total_reports) * 100, 2)

def main(reports: List[str], distress_threshold: float = 0.9) -> float:
    sentiment_results = analyze_sentiment(reports)
    distress_signals = detect_distress_signals(sentiment_results, distress_threshold)
    total_reports = len(reports)
    distress_percentage = calculate_distress_percentage(total_reports, distress_signals)
    return distress_percentage
