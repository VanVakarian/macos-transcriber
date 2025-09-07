import os
import io
import threading
import time
import subprocess
import wave
import queue
from collections import deque
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
    AUTO_STOP_TIMEOUT,
    CONTEXT_CHUNKS_COUNT,
    ENABLE_CONTEXT,
    SOUND_MODE,
    PRE_RECORD_MS
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
        self.CONTEXT_CHUNKS_COUNT = CONTEXT_CHUNKS_COUNT
        self.ENABLE_CONTEXT = ENABLE_CONTEXT
        self.SOUND_MODE = SOUND_MODE if SOUND_MODE in ['none', 'basic', 'all'] else 'all'
        self.PRE_RECORD_MS = PRE_RECORD_MS

        # Calculate pre-recording buffer size (number of chunks)
        chunk_duration_ms = (self.CHUNK / self.RATE) * 1000  # ~64ms per chunk
        self.pre_record_chunks = max(1, int(self.PRE_RECORD_MS / chunk_duration_ms))

        self.is_recording = False
        self.audio = None
        self.stream = None
        self.current_modifiers = set()
        self.recording_start_time = None

        # Pre-recording circular buffer
        self.pre_record_buffer = deque(maxlen=self.pre_record_chunks)

        self.audio_buffer = []
        self.silence_counter = 0
        self.is_speech_detected = False
        self.last_speech_time = 0

        self.OPENAI_MODEL_REQ = OPENAI_MODEL_REQ

        self.chunk_queue = queue.Queue()
        self.chunk_counter = 0
        self.completed_transcriptions = []
        self.worker_running = False

        if not self.OPENAI_API_KEY:
            raise ValueError("OPEN_AI_KEY not found in env.py file")

        self.init_audio()
        self.start_transcription_worker()

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
        if self.SOUND_MODE == 'none':
            return
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        except:
            try:
                subprocess.run(["say", "-v", "Alex", "Recording"], check=False)
            except:
                pass

    def play_stop_sound(self):
        if self.SOUND_MODE == 'none':
            return
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
        except:
            try:
                subprocess.run(["say", "-v", "Alex", "Stopped"], check=False)
            except:
                pass

    def play_transcribe_sound(self):
        if self.SOUND_MODE in ['none', 'basic']:
            return
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
        if text.strip():
            self.completed_transcriptions.append(text)
            if len(self.completed_transcriptions) > self.CONTEXT_CHUNKS_COUNT:
                self.completed_transcriptions.pop(0)

    def start_transcription_worker(self):
        self.worker_running = True
        worker_thread = threading.Thread(target=self.transcription_worker)
        worker_thread.daemon = True
        worker_thread.start()

    def transcription_worker(self):
        while self.worker_running:
            try:
                chunk_data = self.chunk_queue.get(timeout=0.1)
                if chunk_data is None:
                    break

                chunk_id = chunk_data["id"]
                audio_data = chunk_data["audio_data"]

                context_prompt = " ".join(self.completed_transcriptions[-self.CONTEXT_CHUNKS_COUNT:]) if self.ENABLE_CONTEXT else ""

                if context_prompt:
                    print(f"📝 {chunk_id} sending context to API:")
                    print(f"   \"{context_prompt}\"")
                else:
                    print(f"📝 {chunk_id} no context available")

                text = self.transcribe_audio(audio_data, chunk_id, context_prompt)

                if text and text.strip():
                    print(f"✨ Inserting {chunk_id}: \"{text[:30]}{'...' if len(text) > 30 else ''}\"")
                    self.insert_transcription(text + " ")
                    self.on_transcription_complete(chunk_id, text)

                self.chunk_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Transcription worker error: {e}")
                time.sleep(0.1)

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

    def transcribe_audio(self, audio_data, chunk_id, context_prompt):
        try:
            audio_io = io.BytesIO()

            with wave.open(audio_io, 'wb') as wav_file:
                wav_file.setnchannels(self.CHANNELS)
                wav_file.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wav_file.setframerate(self.RATE)
                wav_file.writeframes(audio_data)

            audio_io.seek(0)

            print(f"🌐 Sending {chunk_id} to API")
            self.play_transcribe_sound()

            files = {
                'file': ('audio.wav', audio_io, 'audio/wav'),
                'model': (None, self.OPENAI_MODEL_REQ),
                'response_format': (None, 'text'),
            }

            if context_prompt:
                files['prompt'] = (None, context_prompt)

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
                    print(f"✅ Completed {chunk_id}: \"{transcript[:50]}{'...' if len(transcript) > 50 else ''}\"")
                    return transcript
                else:
                    print(f"⚠️ Empty transcription for {chunk_id}")
                    return ""
            else:
                print(f"❌ API error for {chunk_id}: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            print(f"❌ Transcription error for {chunk_id}: {e}")
            return ""

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
                audio_chunk = np.frombuffer(data, dtype=np.int16)

                # Always add to pre-recording buffer
                self.pre_record_buffer.append(audio_chunk)

                has_voice = self.detect_voice_activity(data)

                if has_voice:
                    if not self.is_speech_detected:
                        print("🗣️ Voice detected")
                        self.is_speech_detected = True

                        # Add pre-recorded chunks to main buffer
                        for pre_chunk in self.pre_record_buffer:
                            self.audio_buffer.extend(pre_chunk)
                    else:
                        # Already recording, just add current chunk
                        self.audio_buffer.extend(audio_chunk)

                    self.last_speech_time = current_time
                    self.silence_counter = 0
                    self.total_silence_start = current_time

                elif self.is_speech_detected:
                    self.silence_counter += 1
                    self.audio_buffer.extend(audio_chunk)

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
            self.chunk_counter += 1

            print(f"🎯 Created {chunk_id} ({buffer_duration:.1f}s)")

            audio_data = np.array(self.audio_buffer, dtype=np.int16).tobytes()

            chunk_data = {
                "id": chunk_id,
                "audio_data": audio_data
            }

            self.chunk_queue.put(chunk_data)
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
        context_status = f"{self.CONTEXT_CHUNKS_COUNT} chunks" if self.CONTEXT_CHUNKS_COUNT > 0 and self.ENABLE_CONTEXT else "disabled"
        print(f"   VAD threshold: {self.VAD_THRESHOLD} | Silence: {self.SILENCE_DURATION}s | Auto-stop: {auto_stop_status}")
        print(f"   Context prompts: {context_status} | Sound mode: {self.SOUND_MODE}")
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
        self.worker_running = False

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
        self.chunk_queue.put(None)
        time.sleep(1)

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
