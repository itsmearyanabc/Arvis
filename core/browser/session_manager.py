import json
import os
from typing import List, Dict, Optional

class SessionManager:
    """
    Manages a pool of AI chat accounts (emails/passwords).
    Tracks usage limits and handles rotation for 24/7 autonomous harvesting.
    """
    def __init__(self, accounts_file: str = "arvis_data/accounts.json"):
        self.accounts_file = os.path.abspath(accounts_file)
        os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
        self.accounts = self._load_accounts()

    def _load_accounts(self) -> List[Dict]:
        """Loads account data from a local JSON file."""
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_accounts(self):
        """Persists the current state of accounts and their limits."""
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=4)

    def get_available_account(self, provider: str) -> Optional[Dict]:
        """
        Returns an account for a specific provider (e.g., 'ChatGPT')
        that has not yet reached its limit.
        """
        for acc in self.accounts:
            if acc["provider"] == provider and not acc.get("limit_reached", False):
                return acc
        return None

    def mark_limit_reached(self, email: str, provider: str):
        """Marks an account as exhausted and saves the state."""
        for acc in self.accounts:
            if acc["email"] == email and acc["provider"] == provider:
                acc["limit_reached"] = True
                self.save_accounts()
                return True
        return False

    def reset_limits(self, provider: str = None):
        """Reset accounts (e.g., for a new day/cycle)."""
        for acc in self.accounts:
            if not provider or acc["provider"] == provider:
                acc["limit_reached"] = False
        self.save_accounts()

    def add_account(self, email: str, password: str, provider: str):
        """Adds a new account to the pool."""
        new_acc = {
            "email": email,
            "password": password,
            "provider": provider,
            "limit_reached": False
        }
        self.accounts.append(new_acc)
        self.save_accounts()

if __name__ == "__main__":
    sm = SessionManager()
    # Mock addition
    if not sm.accounts:
        sm.add_account("user1@example.com", "pass123", "ChatGPT")
        sm.add_account("user2@example.com", "pass123", "Claude")
    print(f"Available for ChatGPT: {sm.get_available_account('ChatGPT')}")
