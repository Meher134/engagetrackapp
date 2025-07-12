from backend.services.typing_metrics.analyzer import TypingAnalyzer
from backend.services.typing_metrics.spell_grammar import GrammarChecker
from backend.services.typing_metrics.stylometry import StylometryAnalyzer

import tempfile
import json
import os

def analyze_typing_data_dict(data: dict) -> dict:
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    analyzer = TypingAnalyzer(tmp_path)
    typing_metrics = analyzer.analyze()

    grammar = GrammarChecker(tmp_path)
    grammar_report = grammar.check_grammar()

    stylometry = StylometryAnalyzer(tmp_path)
    style_report = stylometry.run()

    os.remove(tmp_path)

    return {
        "typing_metrics": typing_metrics,
        "grammar_report": {
            "total_issues": grammar_report["total_issues"],
            "issues": grammar_report["grammar_issues"]
        },
        "stylometry_report": style_report
    }
