import os
import pickle
import re
import numpy as np
import pandas as pd
from transformers import AutoTokenizer
from openvino.runtime import Core
from backend.services.typing_metrics.pipeline import analyze_typing_data_dict


minilm_tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
cross_tokenizer = AutoTokenizer.from_pretrained("cross-encoder/stsb-roberta-base")

core = Core()
KW_MODEL_PATH = os.path.join("backend","services","models","openvino_minilm", "model.xml")
kw_model = core.compile_model(KW_MODEL_PATH, "CPU")
kw_input_names = [inp.get_any_name() for inp in kw_model.inputs]
kw_output = kw_model.output(0)

CROSS_MODEL_PATH = os.path.join("backend","services","models","openvino_cross", "model.xml")
cross_model = core.compile_model(CROSS_MODEL_PATH, "CPU")
cross_input_names = [inp.get_any_name() for inp in cross_model.inputs]
cross_output = cross_model.output(0)

def preprocess(text):
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def embed_text_ov(text_list):
    tokens = minilm_tokenizer(text_list, padding=True, truncation=True, return_tensors="np")
    inputs = {name: tokens[name].astype(np.int64) for name in kw_input_names if name in tokens}
    output = kw_model(inputs)[kw_output]
    return output[:, 0, :]  # [CLS] token

def extract_topics(text, top_n=3):
    pre_text = preprocess(text)
    words = list(set(pre_text.split()))
    candidates = [" ".join(words[i:i+2]) for i in range(len(words) - 1)]
    if not candidates:
        return []

    doc_emb = embed_text_ov([pre_text])[0]
    cand_embs = embed_text_ov(candidates)

    norms = np.linalg.norm(cand_embs, axis=1) * np.linalg.norm(doc_emb)
    sims = np.dot(cand_embs, doc_emb) / norms
    sorted_pairs = sorted(zip(candidates, sims), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in sorted_pairs[:top_n]]

def topics_are_similar(lecture_topics, essay_topics):
    return any(lt in et or et in lt for lt in lecture_topics for et in essay_topics)

def compute_similarity(lecture_text, essay_text):
    pair = [(preprocess(lecture_text), preprocess(essay_text))]
    tokens = cross_tokenizer(pair, padding=True, truncation=True, return_tensors="np")
    inputs = {name: tokens[name].astype(np.int64) for name in cross_input_names if name in tokens}
    score = cross_model(inputs)[cross_output]
    return float(score[0])

_rf_bundle = None
def load_rf_model_bundle():
    global _rf_bundle
    if _rf_bundle is None:
        with open("backend/services/models/Typing_metrics_rf.pkl", "rb") as f:
            _rf_bundle = pickle.load(f)
    return _rf_bundle

def classify_thoughtfulness(analysis_report):
    rf_bundle = load_rf_model_bundle()
    model = rf_bundle["model"]
    scaler = rf_bundle["scaler"]
    label_encoder = rf_bundle["label_encoder"]
    feature_names = rf_bundle["feature_names"]

    typing = analysis_report["typing_metrics"]
    grammar = analysis_report["grammar_report"]
    stylometry = analysis_report["stylometry_report"]

    features = [
        typing.get("total_words", 0),
        typing.get("total_time_seconds", 0),
        typing.get("avg_typing_time_per_word", 0),
        typing.get("std_typing_time_per_word", 0),
        typing.get("avg_pause_before_word", 0),
        typing.get("std_pause_before_word", 0),
        typing.get("total_backspaces", 0),
        typing.get("avg_backspaces_per_word", 0),
        typing.get("typing_speed_wpm", 0),
        typing.get("long_thinking_pauses", 0),
        typing.get("total_bursts", 0),
        typing.get("avg_words_per_burst", 0),
        typing.get("longest_burst_length", 0),
        grammar.get("total_issues", 0),
        stylometry.get("total_sentences", 0),
        stylometry.get("avg_sentence_length", 0),
        stylometry.get("avg_word_length", 0),
        stylometry.get("punctuation_count", 0),
        stylometry.get("lexical_diversity", 0),
        stylometry.get("drift_score", 0),
        stylometry.get("avg_semantic_similarity", 0),
        stylometry.get("std_semantic_similarity", 0),
    ]
    df = pd.DataFrame([features], columns=feature_names)
    scaled = scaler.transform(df)
    pred = model.predict(scaled)[0]
    return label_encoder.inverse_transform([pred])[0]  

async def evaluate_engagement(essay_doc):
    analysis_report = analyze_typing_data_dict(essay_doc["typing_data"])
    style = classify_thoughtfulness(analysis_report)

    lecture_text = essay_doc.get("lecture_text", "")
    essay_text = essay_doc.get("essay_text", "")

    similarity_score = 0.0
    if lecture_text and essay_text:
        l_topics = extract_topics(lecture_text)
        e_topics = extract_topics(essay_text)
        if topics_are_similar(l_topics, e_topics):
            similarity_score = compute_similarity(lecture_text, essay_text)

    if style == "copy":
        engagement = -1
    else:
        engagement = 1 if similarity_score > 0.6 else (0 if similarity_score > 0.4 else -1)

    return {
        "engagement_score": engagement,
        "typing_style": style,
        "similarity_score": round(similarity_score, 3),
    }
