import json
import os
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from statistics import mean
from transformers import AutoTokenizer
from openvino.runtime import Core

class StylometryAnalyzer:
    def __init__(self, filepath):
        with open(filepath, "r") as f:
            self.data = json.load(f)
        self.text = self._reconstruct_text()

        openvino_model_path = os.path.join(
            "backend","services","models","openvino_minilm", "model.xml"
        )

        self.core = Core()
        model = self.core.read_model(openvino_model_path)
        self.compiled_model = self.core.compile_model(model, device_name="CPU")
        self.input_layer = self.compiled_model.input(0)
        self.output_layer = self.compiled_model.output(0)
        self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    def _reconstruct_text(self):
        return " ".join([w["word"] for w in self.data.get("words", [])])

    def basic_stylometry(self):
        words = word_tokenize(self.text)
        sentences = sent_tokenize(self.text)

        punctuations = [w for w in words if w in ".,!?;:"]
        avg_sentence_len = mean([len(word_tokenize(s)) for s in sentences]) if sentences else 0
        avg_word_len = mean([len(w) for w in words if w.isalpha()]) if words else 0
        lexical_diversity = len(set(words)) / len(words) if words else 0

        return {
            "total_sentences": len(sentences),
            "total_words": len(words),
            "avg_sentence_length": avg_sentence_len,
            "avg_word_length": avg_word_len,
            "punctuation_count": len(punctuations),
            "lexical_diversity": lexical_diversity
        }

    def _encode_sentences_openvino(self, sentences):
        encoded = self.tokenizer(
            sentences,
            padding=True,
            truncation=True,
            return_tensors="np"
        )

        input_dict = {}
        for input_layer in self.compiled_model.inputs:
            name = input_layer.get_any_name()
            if name in encoded:
                input_dict[name] = encoded[name].astype(np.int64)

        results = self.compiled_model(input_dict)
        output_tensor = results[self.output_layer]

        cls_embeddings = output_tensor[:, 0, :]

        norms = np.linalg.norm(cls_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        cls_embeddings = cls_embeddings / norms

        return cls_embeddings

    

    def _cosine_sim(self, a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


    def drift_analysis(self):
        sentences = sent_tokenize(self.text)
        if len(sentences) < 4:
            return {"drift_score": 0, "note": "Too few sentences to detect drift."}

        chunks = [" ".join(sentences[i:i + 2]) for i in range(0, len(sentences), 2)]

        embeddings = self._encode_sentences_openvino(chunks)
        similarities = [float(self._cosine_sim(embeddings[i], embeddings[i + 1])) for i in range(len(embeddings) - 1)]

        drift_score = 1 - mean(similarities)  
        return {
            "drift_score": drift_score,
            "semantic_similarities": similarities,
            "interpretation": "High drift may indicate copying if style suddenly changes."
        }

    def run(self):
        style = self.basic_stylometry()
        drift = self.drift_analysis()
        return {**style, **drift}

