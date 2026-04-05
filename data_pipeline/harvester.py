import asyncio
import aiohttp
import os
from typing import List, Dict

class ArvisHarvester:
    """
    24/7 Data Collection Engine for Arvis.
    Queries various AI APIs to harvest complex reasoning logic, coding best practices,
    and reframed data for self-evolution.
    """
    def __init__(self, api_keys: Dict[str, str]):
        self.api_keys = api_keys
        self.session = None

    async def _init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def query_teacher(self, provider: str, prompt: str) -> str:
        """
        Queries a state-of-the-art model (GPT-4o, Claude 3.5, etc.) for reasoning data.
        :param provider: 'openai' or 'anthropic'.
        :param prompt: The reframed question to harvest logic for.
        :return: The generated response (to be processed for Arvis's training).
        """
        await self._init_session()
        
        if provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_keys.get('openai')}"}
            payload = {
                "model": "gpt-4o-2024-05-13",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3 # Lower temperature for stable reasoning harvesting
            }
            async with self.session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                return data['choices'][0]['message']['content']

        elif provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_keys.get('anthropic'),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
            }
            async with self.session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                return data['content'][0]['text']

        return "Unknown provider."

    async def harvest_batch(self, tasks: List[Dict]):
        """
        Processes a batch of harvesting tasks concurrently.
        Tasks include prompt and provider details.
        """
        tasks_list = [self.query_teacher(t['provider'], t['prompt']) for t in tasks]
        results = await asyncio.gather(*tasks_list)
        return results

    async def close(self):
        if self.session:
            await self.session.close()

if __name__ == "__main__":
    # Test Block
    async def main():
        keys = {"openai": "sk-...", "anthropic": "sk-..."}
        harvester = ArvisHarvester(keys)
        # res = await harvester.query_teacher("openai", "Refactor this linked list implementation for maximum performance.")
        # print(res)
        await harvester.close()
    
    asyncio.run(main())
