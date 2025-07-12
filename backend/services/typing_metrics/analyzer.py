import json
import numpy as np
from statistics import mean, stdev

class TypingAnalyzer:
    def __init__(self, filepath):
        with open(filepath, "r") as f:
            self.data = json.load(f)
        self.words = self.data.get("words", [])
        self.session_start = self.data["session_start_time"]
        self.session_end = self.data["session_end_time"]
        self.duration = self.data["duration_seconds"]

    def analyze(self):
        word_durations = [w["duration"] for w in self.words if "duration" in w]
        pauses = [w["pause_before"] for w in self.words if w.get("pause_before") is not None]
        backspaces = [w["backspaces"] for w in self.words]

        metrics = {
            "total_words": len(self.words),
            "total_time_seconds": self.duration,
            "avg_typing_time_per_word": mean(word_durations) if word_durations else 0,
            "std_typing_time_per_word": stdev(word_durations) if len(word_durations) > 1 else 0,
            "avg_pause_before_word": mean(pauses) if pauses else 0,
            "std_pause_before_word": stdev(pauses) if len(pauses) > 1 else 0,
            "total_backspaces": sum(backspaces),
            "avg_backspaces_per_word": mean(backspaces) if backspaces else 0,
            "typing_speed_wpm": (len(self.words) / self.duration) * 60 if self.duration > 0 else 0,
            "long_thinking_pauses": len([p for p in pauses if p > 2.0]),  
            "typing_bursts": self._get_typing_bursts()
        }

        return metrics

    def _get_typing_bursts(self, threshold=5.0):
        bursts = []
        current_burst = []
        for w in self.words:
            if not current_burst:
                current_burst.append(w)
            else:
                pause = w.get("pause_before", 0)
                if pause > threshold:
                    bursts.append(current_burst)
                    current_burst = [w]
                else:
                    current_burst.append(w)
        if current_burst:
            bursts.append(current_burst)
        return {
            "total_bursts": len(bursts),
            "avg_words_per_burst": mean([len(b) for b in bursts]) if bursts else 0,
            "longest_burst_length": max([len(b) for b in bursts]) if bursts else 0
        }
