import os
import io
import threading
import time
import subprocess
import wave
from datetime import datetime
from pynput import keyboard
import pyaudio
import numpy as np
import requests
from env import (
    OPEN_AI_KEY,
    OPENAI_MODEL_REQ,
    VAD_THRESHOLD,
    SILENCE_DURATION,
    AUDIO_LENGTH_MIN,
    AUDIO_LENGTH_MAX,
    AUTO_STOP_TIMEOUT
)
from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand
)

class WhisperTranscriber:
    def __init__(self):
        self.OPENAI_API_KEY = OPEN_AI_KEY

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000

        self.VAD_THRESHOLD = VAD_THRESHOLD
        self.SILENCE_DURATION = SILENCE_DURATION
        self.AUDIO_LENGTH_MIN = AUDIO_LENGTH_MIN
        self.AUDIO_LENGTH_MAX = AUDIO_LENGTH_MAX
        self.AUTO_STOP_TIMEOUT = AUTO_STOP_TIMEOUT

        self.is_recording = False
        self.audio = None
        self.stream = None
        self.current_modifiers = set()
        self.recording_start_time = None

        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speech_detected = False
        self.last_speech_time = 0

        self.OPENAI_MODEL_REQ = OPENAI_MODEL_REQ

        self.chunks_registry = {}
        self.chunk_counter = 0
        self.registry_lock = threading.Lock()
        self.insertion_worker_running = False

        if not self.OPENAI_API_KEY:
            raise ValueError("OPEN_AI_KEY not found in env.py file")

        self.init_audio()
        self.start_insertion_worker()

    def copy_to_clipboard(self, text):
        subprocess.run("pbcopy", text=True, input=text)

    def press_cmd_v_applescript(self):
        applescript = 'tell application "System Events" to keystroke "v" using command down'
        subprocess.run(["osascript", "-e", applescript])

    def press_cmd_v(self):
        try:
            v_keycode = 9
            event_down = CGEventCreateKeyboardEvent(None, v_keycode, True)
            event_up = CGEventCreateKeyboardEvent(None, v_keycode, False)
            CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
            CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
            CGEventPost(kCGHIDEventTap, event_down)
            CGEventPost(kCGHIDEventTap, event_up)
            return True
        except:
            return False

    def insert_transcription(self, text):
        self.copy_to_clipboard(text)
        time.sleep(0.1)
        if not self.press_cmd_v():
            self.press_cmd_v_applescript()

    def play_start_sound(self):
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        except:
            try:
                subprocess.run(["say", "-v", "Alex", "Recording"], check=False)
            except:
                pass

    def play_stop_sound(self):
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
        except:
            try:
                subprocess.run(["say", "-v", "Alex", "Stopped"], check=False)
            except:
                pass

    def play_transcribe_sound(self):
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], check=False)
        except:
            pass

    def init_audio(self):
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            raise Exception(f"Audio initialization error: {e}")

    def on_transcription_complete(self, chunk_id, text):
        with self.registry_lock:
            if chunk_id in self.chunks_registry:
                self.chunks_registry[chunk_id]["status"] = "completed"
                self.chunks_registry[chunk_id]["text"] = text
                self.chunks_registry[chunk_id]["completed_at"] = time.time()

    def start_insertion_worker(self):
        self.insertion_worker_running = True
        worker_thread = threading.Thread(target=self.insertion_worker)
        worker_thread.daemon = True
        worker_thread.start()

    def insertion_worker(self):
        while self.insertion_worker_running:
            try:
                chunk_to_insert = self.find_next_chunk_to_insert()

                if chunk_to_insert:
                    chunk_id = chunk_to_insert["id"]
                    text = chunk_to_insert["text"]

                    if text.strip():
                        print(f"✨ Inserting {chunk_id}: \"{text[:30]}{'...' if len(text) > 30 else ''}\"")
                        self.insert_transcription(text + " ")

                    with self.registry_lock:
                        if chunk_id in self.chunks_registry:
                            del self.chunks_registry[chunk_id]

                    time.sleep(0.1)
                else:
                    time.sleep(0.05)

            except Exception as e:
                print(f"❌ Insertion worker error: {e}")
                time.sleep(0.1)

    def find_next_chunk_to_insert(self):
        with self.registry_lock:
            if not self.chunks_registry:
                return None

            ready_chunks = {
                chunk_id: data for chunk_id, data in self.chunks_registry.items()
                if data["status"] == "completed"
            }

            if not ready_chunks:
                return None

            earliest_ready = min(ready_chunks.items(), key=lambda x: x[1]["record_timestamp"])
            earliest_id, earliest_data = earliest_ready

            if self.can_insert_safely(earliest_data):
                return {
                    "id": earliest_id,
                    "text": earliest_data["text"],
                    "timestamp": earliest_data["record_timestamp"]
                }

            return None

    def can_insert_safely(self, chunk_data):
        target_timestamp = chunk_data["record_timestamp"]

        for other_data in self.chunks_registry.values():
            if (other_data["record_timestamp"] < target_timestamp and
                other_data["status"] == "processing"):
                return False

        return True

    def detect_voice_activity(self, audio_data):
        try:
            audio_np = np.frombuffer(audio_data, dtype=np.int16)

            # Check if we have valid audio data
            if len(audio_np) == 0:
                return False

            # Calculate RMS with safety checks
            squared = audio_np.astype(np.float64) ** 2
            mean_squared = np.mean(squared)

            # Ensure we don't get negative values or NaN
            if np.isnan(mean_squared) or mean_squared < 0:
                return False

            rms = np.sqrt(mean_squared)

            return rms > self.VAD_THRESHOLD

        except Exception as e:
            print(f"⚠️ VAD error: {e}")
            return False

    def transcribe_audio(self, audio_data, chunk_id):
        try:
            audio_io = io.BytesIO()

            with wave.open(audio_io, 'wb') as wav_file:
                wav_file.setnchannels(self.CHANNELS)
                wav_file.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wav_file.setframerate(self.RATE)
                wav_file.writeframes(audio_data)

            audio_io.seek(0)

            print(f"� Sending {chunk_id} to API")
            self.play_transcribe_sound()

            files = {
                'file': ('audio.wav', audio_io, 'audio/wav'),
                'model': (None, self.OPENAI_MODEL_REQ),
                'response_format': (None, 'text'),
            }

            headers = {
                'Authorization': f'Bearer {self.OPENAI_API_KEY}'
            }

            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                files=files,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                transcript = response.text.strip()
                if transcript:
                    print(f"� Completed {chunk_id}: \"{transcript[:50]}{'...' if len(transcript) > 50 else ''}\"")
                    self.on_transcription_complete(chunk_id, transcript)
                else:
                    print(f"⚠️ Empty transcription for {chunk_id}")
                    self.on_transcription_complete(chunk_id, "")
            else:
                print(f"❌ API error for {chunk_id}: {response.status_code} - {response.text}")
                self.on_transcription_complete(chunk_id, "")

        except Exception as e:
            print(f"❌ Transcription error for {chunk_id}: {e}")
            self.on_transcription_complete(chunk_id, "")

    def start_recording(self):
        if self.is_recording:
            return

        try:
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )

            self.is_recording = True
            self.audio_buffer = []
            self.silence_counter = 0
            self.is_speech_detected = False
            self.last_speech_time = time.time()
            self.recording_start_time = time.time()
            self.total_silence_start = time.time()

            print(f"🔴 Recording started (VAD threshold: {self.VAD_THRESHOLD})")
            self.play_start_sound()

            recording_thread = threading.Thread(target=self.record_audio)
            recording_thread.daemon = True
            recording_thread.start()

        except Exception as e:
            print(f"❌ Recording start error: {e}")
            self.is_recording = False

    def record_audio(self):
        while self.is_recording:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                current_time = time.time()

                has_voice = self.detect_voice_activity(data)

                if has_voice:
                    if not self.is_speech_detected:
                        print("🗣️ Voice detected")
                        self.is_speech_detected = True

                    self.last_speech_time = current_time
                    self.silence_counter = 0
                    self.total_silence_start = current_time
                    self.audio_buffer.extend(np.frombuffer(data, dtype=np.int16))

                elif self.is_speech_detected:
                    self.silence_counter += 1
                    self.audio_buffer.extend(np.frombuffer(data, dtype=np.int16))

                    silence_duration = self.silence_counter * self.CHUNK / self.RATE

                    if silence_duration >= self.SILENCE_DURATION:
                        self.process_audio_buffer()

                # Check for auto-stop timeout (total silence since recording started)
                if not self.is_speech_detected and self.AUTO_STOP_TIMEOUT > 0:
                    total_silence_duration = current_time - self.total_silence_start
                    if total_silence_duration >= self.AUTO_STOP_TIMEOUT:
                        print(f"⏰ Auto-stopping after {self.AUTO_STOP_TIMEOUT}s of silence")
                        self.stop_recording()
                        break

                if self.is_speech_detected:
                    buffer_duration = len(self.audio_buffer) / self.RATE
                    if buffer_duration >= self.AUDIO_LENGTH_MAX:
                        print(f"⏰ Maximum length reached ({self.AUDIO_LENGTH_MAX}s)")
                        self.process_audio_buffer()

            except Exception as e:
                print(f"❌ Recording error: {e}")
                break

    def process_audio_buffer(self):
        if not self.audio_buffer:
            return

        buffer_duration = len(self.audio_buffer) / self.RATE

        if buffer_duration >= self.AUDIO_LENGTH_MIN:
            chunk_id = f"chunk_{self.chunk_counter:03d}"
            record_timestamp = time.time()

            with self.registry_lock:
                self.chunks_registry[chunk_id] = {
                    "record_timestamp": record_timestamp,
                    "status": "processing",
                    "text": None,
                    "completed_at": None
                }
                self.chunk_counter += 1

            print(f"🎯 Created {chunk_id} ({buffer_duration:.1f}s, ts: {record_timestamp:.3f})")

            audio_data = np.array(self.audio_buffer, dtype=np.int16).tobytes()

            transcribe_thread = threading.Thread(
                target=self.transcribe_audio,
                args=(audio_data, chunk_id)
            )
            transcribe_thread.daemon = True
            transcribe_thread.start()
        else:
            print(f"⚠️ Audio too short ({buffer_duration:.1f}s)")

        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speech_detected = False

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False

        recording_duration = 0
        if self.recording_start_time:
            recording_duration = time.time() - self.recording_start_time

        print(f"🚫 Recording stopped ({recording_duration:.1f}s)")

        if self.audio_buffer:
            self.process_audio_buffer()

        self.play_stop_sound()

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"❌ Audio closing error: {e}")

    def on_press(self, key):
        if key in {keyboard.Key.cmd, keyboard.Key.alt}:
            self.current_modifiers.add(key)

        if (key == keyboard.Key.space and
            self.current_modifiers == {keyboard.Key.cmd, keyboard.Key.alt}):

            if not self.is_recording:
                self.start_recording()
            else:
                self.stop_recording()

    def on_release(self, key):
        if key in self.current_modifiers:
            self.current_modifiers.remove(key)

    def start_listening(self):
        print(f"🎹 Audio Transcriber ready (model: {self.OPENAI_MODEL_REQ})")
        auto_stop_status = f"{self.AUTO_STOP_TIMEOUT}s" if self.AUTO_STOP_TIMEOUT > 0 else "disabled"
        print(f"   VAD threshold: {self.VAD_THRESHOLD} | Silence: {self.SILENCE_DURATION}s | Auto-stop: {auto_stop_status}")
        print("   Option + Command + Space - start/stop recording")
        print("   Ctrl+C - exit")
        print()

        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\n👋 Program terminated")
                try:
                    self.cleanup()
                except Exception as e:
                    print(f"❌ Cleanup error: {e}")

    def cleanup(self):
        self.insertion_worker_running = False

        try:
            if self.is_recording:
                self.stop_recording()
        except Exception as e:
            print(f"❌ Recording stop error: {e}")

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"❌ Stream closing error: {e}")

        try:
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            print(f"❌ PyAudio termination error: {e}")

        print("⏳ Waiting for pending transcriptions...")
        wait_start = time.time()
        while self.chunks_registry and (time.time() - wait_start) < 5:
            time.sleep(0.1)

        if self.chunks_registry:
            print(f"⚠️ {len(self.chunks_registry)} transcriptions didn't complete")

def main():
    print("🎤 Whisper Transcriber")
    print("=" * 40)

    transcriber = None
    try:
        transcriber = WhisperTranscriber()
        transcriber.start_listening()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Check env.py file and OPEN_AI_KEY variable")
    except Exception as e:
        print(f"❌ Critical error: {e}")
    finally:
        if transcriber:
            try:
                transcriber.cleanup()
            except Exception as e:
                print(f"❌ Final cleanup error: {e}")

if __name__ == "__main__":
    main()
