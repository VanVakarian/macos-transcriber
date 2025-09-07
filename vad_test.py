import sys
import time
import pyaudio
import numpy as np
from env import VAD_THRESHOLD

def detect_voice_activity(audio_data, threshold):
    try:
        audio_np = np.frombuffer(audio_data, dtype=np.int16)

        if len(audio_np) == 0:
            return False, 0

        squared = audio_np.astype(np.float64) ** 2
        mean_squared = np.mean(squared)

        if np.isnan(mean_squared) or mean_squared < 0:
            return False, 0

        rms = np.sqrt(mean_squared)
        return rms > threshold, rms

    except Exception:
        return False, 0

def main():
    threshold = VAD_THRESHOLD

    if len(sys.argv) > 1:
        try:
            threshold = float(sys.argv[1])
        except ValueError:
            print(f"Invalid threshold value. Using default: {VAD_THRESHOLD}")
            threshold = VAD_THRESHOLD

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        print(f"VAD Test (threshold: {threshold})")
        print("Speak to see voice activity detection...")
        print("Press Ctrl+C to exit")
        print()

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                has_voice, rms_value = detect_voice_activity(data, threshold)

                if has_voice:
                    indicator = "🟢"
                    status = "VOICE"
                else:
                    indicator = "❌"
                    status = "QUIET"

                print(f"\r{indicator} {status} (RMS: {rms_value:.1f}, threshold: {threshold})", end="", flush=True)
                time.sleep(0.05)

            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass
        print("\nStopped")

if __name__ == "__main__":
    main()
