import speech_recognition as sr
import time

def test_microphone():
    """
    A simple diagnostic tool to check if Arvis can 'hear' your microphone.
    Run this to verify your hardware settings before starting the main core.
    """
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("--- ARVIS AUDIO DIAGNOSTIC ---")
    print("1. Checking list of available microphones...")
    mics = sr.Microphone.list_microphone_names()
    for i, name in enumerate(mics):
        print(f"   [{i}] {name}")

    print("\n2. Initializing default microphone...")
    try:
        with mic as source:
            print("   (SUCCESS) Microphone initialized.")
            print("   Adjusting for ambient noise... (Please stay silent for 2 seconds)")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print(f"   (SUCCESS) Noise threshold set to: {recognizer.energy_threshold}")

            print("\n3. Testing audio capture...")
            print("   PLEASE SPEAK NOW (I will listen for 5 seconds)...")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            
            print("   (SUCCESS) Audio captured. Analyzing segments...")
            # We don't transcribe here, just check if data exists
            if len(audio.get_wav_data()) > 0:
                print(f"   (SUCCESS) Data detected: {len(audio.get_wav_data())} bytes of audio captured.")
                print("\nFINAL RESULT: Your microphone is working perfectly with Arvis.")
            else:
                print("\nFINAL RESULT: Audio was captured but it is EMPTY (0 bytes). Check your Windows privacy settings for microphone access.")

    except Exception as e:
        print(f"\nFINAL RESULT: ERROR detected during initialization: {e}")
        print("TIP: Ensure 'PyAudio' is correctly installed and no other app is using the mic exclusively.")

if __name__ == "__main__":
    test_microphone()
