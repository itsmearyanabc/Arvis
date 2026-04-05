import edge_tts
import asyncio
import pygame
import os
import tempfile

class ArvisSpeaker:
    """
    High-quality Voice Synthesis for Arvis using edge-tts.
    Provides the sophisticated, British voice for the 'Sovereign' persona.
    """
    def __init__(self, voice: str = "en-GB-RyanNeural"):
        self.voice = voice
        pygame.mixer.init()

    async def speak(self, text: str):
        """
        Converts text to speech and plays it back.
        """
        if not text:
            return

        print(f"ARVIS: {text}")
        
        # Clean text of [CMD] tags for speech
        speech_text = text.replace("[CMD]", "").replace("[/CMD]", "")

        try:
            communicate = edge_tts.Communicate(speech_text, self.voice)
            
            # Use a temporary file for the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_path = temp_file.name
                
            await communicate.save(temp_path)
            
            # Play using pygame
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            pygame.mixer.music.unload()
            os.remove(temp_path)
            
        except Exception as e:
            print(f"ARVIS: (Voice System Error) {e}")

if __name__ == "__main__":
    # Test Block
    async def test():
        speaker = ArvisSpeaker()
        await speaker.speak("Greeting, Sir. The voice systems are now fully operational.")
    
    asyncio.run(test())
