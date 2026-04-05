import asyncio
import os
from interface.voice.listener import ArvisVoiceListener
from interface.voice.speaker import ArvisSpeaker
from core.reasoning.local_brain import ArvisLocalBrain
from core.terminal_agent import TerminalAgent
from interface.cli import ArvisCLI

class ArvisPhase1:
    """
    Main Orchestrator for Arvis Phase 1.
    Ties the Local Brain, Voice Listener, Speaker, and Terminal Agent together.
    Supports DUAL INTERACTION: Voice and Text.
    """
    def __init__(self):
        self.brain = ArvisLocalBrain(model_name="llama3.1:8b")
        self.speaker = ArvisSpeaker()
        self.listener = ArvisVoiceListener(wake_word="arvis")
        self.agent = TerminalAgent()
        self.voice_enabled = True # Runtime toggle

    async def handle_intent(self, intent: str):
        """
        The core reaction loop when 'Arvis' hears a command.
        """
        # 1. Brain processes the intent (Sovereign mode: No explanation unless asked)
        response = await self.brain.chat(intent)
        
        # 2. Extract and execute command if present
        if "[CMD]" in response:
            command = response.split("[CMD]")[1].split("[/CMD]")[0].strip()
            result = self.agent.execute(command)
            
            # 3. Handle Errors (e.g. Missing Tool)
            if "error" in result:
                await self.speaker.speak(result["error"])
            else:
                # Sir requested direct execution, so we only speak if the command produces output 
                # or if an explanation was explicitly requested.
                if "explain" in intent.lower() or "why" in intent.lower():
                    await self.speaker.speak(response.replace(f"[CMD]{command}[/CMD]", ""))
                elif result["stdout"]:
                    # Optional: Speak a short confirmation if output is significant
                    pass
        else:
            # Regular conversation
            await self.speaker.speak(response)

    async def text_input_loop(self):
        """Allows Sir to type commands directly."""
        while True:
            # We use a standard input loop for the V1 prototype
            text = await asyncio.to_thread(input, "SIR: ")
            
            # Internal Commands (Fuzzy matching for voice toggle)
            clean_text = text.lower().strip()
            if any(cmd in clean_text for cmd in ["/voice off", "/voive off", "silence", "mute"]):
                self.voice_enabled = False
                await self.speaker.speak("Voice systems silenced, Sir. Switching to text-only.")
                continue
            elif any(cmd in clean_text for cmd in ["/voice on", "/voive on", "listen", "unmute"]):
                self.voice_enabled = True
                await self.speaker.speak("Voice systems re-activated. Always listening, Sir.")
                continue
            
            if text.strip():
                await self.handle_intent(text)

    async def voice_input_loop(self):
        """Runs the background voice listener."""
        while True:
            if self.voice_enabled:
                try:
                    await self.listener.run(self.handle_intent)
                except Exception as e:
                    # Don't crash the whole app if the mic blips
                    await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)

    async def run(self):
        """Starts the Hybrid Core experience."""
        # Welcome message
        await self.speaker.speak("Greeting, Sir. Arvis Hybrid Core is online. Voice and Text systems ready.")

        # Run text and voice loops simultaneously
        await asyncio.gather(
            self.text_input_loop(),
            self.voice_input_loop()
        )

if __name__ == "__main__":
    arvis = ArvisPhase1()
    asyncio.run(arvis.run())
