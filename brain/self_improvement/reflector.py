import json
import os
import datetime
from typing import List, Dict

class ArvisReflector:
    """
    Performance Monitoring & Self-Criticism Engine for Arvis.
    Logs interactions, identifies logic gaps, and defines 'Next Version' targets.
    """
    def __init__(self, logs_dir: str = "arvis_data/logs"):
        self.logs_dir = os.path.abspath(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)
        self.performance_data = []

    def log_interaction(self, query: str, response: str, success_score: float = 1.0):
        """
        Logs a user interaction with a confidence score.
        :param query: The user's input.
        :param response: Arvis's generated response.
        :param success_score: User-given or self-assessed score (0.0 to 1.0).
        """
        log_entry = {
            "timestamp": str(datetime.datetime.now()),
            "query": query,
            "response": response,
            "score": success_score
        }
        self.performance_data.append(log_entry)
        
        # Save to local file for persistence
        log_file = os.path.join(self.logs_dir, f"usage_{datetime.date.today()}.json")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")

    def identify_evolution_targets(self, threshold: float = 0.7) -> List[Dict]:
        """
        Analyzes logs to find queries where Arvis performed poorly.
        These become 'Reframed Prompts' for the Harvester.
        """
        low_perf_logs = [log for log in self.performance_data if log["score"] < threshold]
        
        targets = []
        for log in low_perf_logs:
            # Reframe the target for a 'Teacher AI'
            reframed_prompt = f"Analyze and improve this solution for: {log['query']}. Current flawed response: {log['response']}"
            targets.append({"prompt": reframed_prompt, "provider": "anthropic"}) # Defaulting to Anthropic for Opus logic
            
        return targets

    def generate_evo_report(self):
        """Generates a summary of system performance for the CLI Monitor."""
        total_interactions = len(self.performance_data)
        if total_interactions == 0:
            return "NO RECENT DATA"
        
        avg_score = sum(log["score"] for log in self.performance_data) / total_interactions
        return f"AVG PERFORMANCE: {avg_score:.2f} | INTERACTIONS: {total_interactions}"

if __name__ == "__main__":
    reflector = ArvisReflector()
    reflector.log_interaction("Write a sorting algorithm.", "Here is bubble sort...", success_score=0.5)
    print(reflector.identify_evolution_targets())
