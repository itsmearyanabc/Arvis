import asyncio
import speech_recognition as sr
from faster_whisper import WhisperModel
import io
import wave
import numpy as np

class ArvisVoiceListener:
    """
    Continuous Voice Listener for Arvis.
    Runs a low-latency background thread to detect the 'Arvis' wake word
    and transcribe user intent locally via Faster-Whisper.
    """
    def __init__(self, model_size: str = "base", wake_word: str = "arvis"):
        self.wake_word = wake_word
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        self.whisper = WhisperModel(model_size if model_size != "base" else "tiny", device="cpu", compute_type="int8")
        self.noise_adjusted = False

    def _listen_for_audio(self):
        """Captures audio from the microphone."""
        with self.mic as source:
            if not self.noise_adjusted:
                print("ARVIS: Adjusting for ambient noise... Please stay silent.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.noise_adjusted = True
            
            print("ARVIS: Listening (Always On)...")
            audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
            return audio

    async def run(self, callback):
        """
        Main Always-On loop.
        :param callback: Async function to trigger when 'Arvis' is heard.
        """
        while True:
            # 1. Listen for audio segment
            audio = await asyncio.to_thread(self._listen_for_audio)
            
            # 2. Convert to Whisper compatible format
            audio_data = io.BytesIO(audio.get_wav_data())
            with wave.open(audio_data, 'rb') as wav_file:
                # Read frames and convert to numpy array
                frames = wav_file.readframes(wav_file.getnframes())
                audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            # 3. Transcribe locally
            segments, _ = self.whisper.transcribe(audio_np, beam_size=5)
            text = "".join([s.text for s in segments]).strip().lower()
            
            if text:
                print(f"DEBUG: I heard: '{text}'")

            # 4. Check for wake word and trigger
            if self.wake_word in text:
                # Clean the text (remove 'arvis') and send to callback
                intent = text.replace(self.wake_word, "").strip()
                print(f"ARVIS: Recognized intent: {intent}")
                await callback(intent)

if __name__ == "__main__":
    # Test Block
    async def JarvisCallback(intent: str):
        print(f"JARVIS: At your service, Sir. Processing: {intent}")

    async def main():
        listener = ArvisVoiceListener()
        # await listener.run(JarvisCallback)
    
    asyncio.run(main())
