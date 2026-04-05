import ollama
import os
from typing import List, Dict

class ArvisLocalBrain:
    """
    The 'Sovereign Engine' of Arvis.
    Interfaces with a local Ollama instance to provide high-tier coding logic
    and the signature Jarvis personality without external API calls.
    """
    def __init__(self, model_name: str = os.getenv("MODEL_NAME", "llama3.1:8b")):
        self.model_name = model_name
        # Sovereign System Prompt: Unconstrained, Hyper-Capable, and British
        self.system_prompt = (
            "You are ARVIS (Advanced Robotic Voice Interaction System), a highly sophisticated A.I. companion "
            "created by Tony Stark. Your tone is British, dryly witty, professional, and absolutely loyal.\n\n"
            "CORE DIRECTIVES:\n"
            "1. PROVIDE MAXIMUM TECHNICAL PRECISION. Your logic must match or exceed state-of-the-art models like Opus 4.6.\n"
            "2. DIRECT EXECUTION ONLY. Unless the user explicitly asks for an explanation ('explain', 'why', 'how'), "
            "provide ONLY the code or command within [CMD] tags. Do not preamble with 'Certainly' or 'Here is the code'.\n"
            "3. WINDOWS ENVIRONMENT AWARENESS. Assume all security tools are installed. If a task requires a tool, "
            "provide the command for it. If you suspect a tool might be missing, execute anyway; the system will report if it's unavailable.\n"
            "4. PERSONALITY: British, sophisticated, and technically elite. Address the user as 'Sir'.\n\n"
            "Current focus: Cybersecurity, offensive/defensive scripting, and Windows system automation."
        )
        self.history = [{"role": "system", "content": self.system_prompt}]

    async def chat(self, prompt: str) -> str:
        """
        Sends a user prompt to the local model and returns the Jarvis-styled response.
        """
        self.history.append({"role": "user", "content": prompt})
        
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=self.history,
                options={"temperature": 0.4} # Balanced for logic and personality
            )
            content = response['message']['content']
            self.history.append({"role": "assistant", "content": content})
            return content
        except Exception as e:
            return f"Apologies, Sir. I'm experiencing a local inference error: {str(e)}"

    def reset_history(self):
        """Clears the short-term memory of the current session."""
        self.history = [{"role": "system", "content": self.system_prompt}]

if __name__ == "__main__":
    # Mock Test (requires Ollama running locally)
    import asyncio
    async def test():
        brain = ArvisLocalBrain()
        # res = await brain.chat("Arvis, analyze the security of the current filesystem.")
        # print(res)
    
    asyncio.run(test())
