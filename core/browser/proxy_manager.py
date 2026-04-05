import random
from typing import Dict, List, Optional

class ProxyManager:
    """
    Manages residential proxy rotation for Arvis's 24/7 harvesting.
    Supports sticky sessions to ensure continuous account stability.
    """
    def __init__(self, proxy_list: List[str] = None):
        """
        :param proxy_list: List of proxy strings in 'http://user:pass@host:port' format.
        """
        self.proxy_list = proxy_list or []
        self.session_map = {} # Maps account identifiers to specific proxies

    def get_proxy_for_account(self, account_id: str) -> Optional[Dict]:
        """
        Returns a 'sticky' proxy for a specific account.
        If no proxy is assigned, it picks a new one from the pool.
        """
        if account_id in self.session_map:
            return self.session_map[account_id]
        
        if not self.proxy_list:
            return None
            
        proxy_url = random.choice(self.proxy_list)
        # Parse the proxy string into Playwright format
        # Expected: http://user:pass@host:port
        try:
            parts = proxy_url.split("@")
            auth = parts[0].replace("http://", "").split(":")
            server = parts[1]
            
            proxy_dict = {
                "server": f"http://{server}",
                "username": auth[0],
                "password": auth[1]
            }
            self.session_map[account_id] = proxy_dict
            return proxy_dict
        except Exception as e:
            print(f"Error parsing proxy: {e}")
            return None

    def add_proxies(self, proxies: List[str]):
        """Adds a batch of new proxies to the pool."""
        self.proxy_list.extend(proxies)

if __name__ == "__main__":
    pm = ProxyManager(["http://user1:pass1@proxy1.com:8080", "http://user2:pass2@proxy2.com:8080"])
    proxy = pm.get_proxy_for_account("user@example.com")
    print(f"Sticky proxy assigned: {proxy}")
