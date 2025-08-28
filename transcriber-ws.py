import os
import json
import base64
import threading
import time
import subprocess
from datetime import datetime
from pynput import keyboard
import pyaudio
import numpy as np
import websocket
from env import OPEN_AI_KEY, OPENAI_MODEL_WS, CHUNK_SIZE_MS
from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand
)

class AudioTranscriber:
    def __init__(self):
        self.OPENAI_API_KEY = OPEN_AI_KEY
        self.OPENAI_MODEL_WS = OPENAI_MODEL_WS
        self.CHUNK_SIZE_MS = CHUNK_SIZE_MS

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 24000

        self.is_recording = False
        self.audio = None
        self.stream = None
        self.current_modifiers = set()
        self.ws = None
        self.recording_start_time = None

        self.chunk_samples = int(self.RATE * self.CHUNK_SIZE_MS / 1000)
        self.audio_buffer = []

        if not self.OPENAI_API_KEY:
            raise ValueError("OPEN_AI_KEY not found in env.py file")

        self.init_audio()

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

    def init_audio(self):
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            raise Exception(f"Audio initialization error: {e}")

    def init_websocket(self):
        url = f"wss://api.openai.com/v1/realtime?model={self.OPENAI_MODEL_WS}"
        headers = [
            f"Authorization: Bearer {self.OPENAI_API_KEY}",
            "OpenAI-Beta: realtime=v1"
        ]

        self.ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=self.on_ws_open,
            on_message=self.on_ws_message,
            on_error=self.on_ws_error,
            on_close=self.on_ws_close
        )

    def on_ws_open(self, ws):
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You must transcribe audio to text. Respond only with transcription without additional comments.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                }
            }
        }

        ws.send(json.dumps(session_config))

    def on_ws_message(self, ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("type", "unknown")

            if event_type == "conversation.item.input_audio_transcription.completed":
                transcript = data.get("transcript", "")
                if transcript.strip():
                    print(f"📝 {transcript}")
                    self.insert_transcription(transcript)

            elif event_type == "conversation.item.input_audio_transcription.failed":
                error_details = data.get("error", {})
                print(f"\n❌ Transcription error: {error_details}")

            elif event_type == "error":
                error_details = data.get("error", {})
                error_msg = error_details.get("message", "Unknown error")
                error_type = error_details.get("type", "unknown")
                print(f"\n❌ API error [{error_type}]: {error_msg}")

        except json.JSONDecodeError:
            print(f"\n❌ JSON decoding error")
        except Exception as e:
            print(f"\n❌ Message processing error: {e}")

    def on_ws_error(self, ws, error):
        print(f"\n❌ Connection error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        pass

    def send_audio_chunk(self, audio_data):
        if not self.ws or self.ws.sock is None:
            return

        try:
            duration_ms = len(audio_data) / (self.RATE * 2) * 1000

            if duration_ms < 50:
                return

            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }

            self.ws.send(json.dumps(event))

        except Exception as e:
            print(f"\n❌ Audio sending error: {e}")

    def start_recording(self):
        if self.is_recording:
            return

        try:
            self.init_websocket()

            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

            time.sleep(1)

            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )

            self.is_recording = True
            self.audio_buffer = []
            self.recording_start_time = time.time()
            print(f"🔴 Recording started")
            self.play_start_sound()

            recording_thread = threading.Thread(target=self.record_audio)
            recording_thread.daemon = True
            recording_thread.start()

        except Exception as e:
            print(f"\n❌ Recording start error: {e}")
            self.is_recording = False

    def record_audio(self):
        while self.is_recording:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)

                self.audio_buffer.extend(audio_data)

                if len(self.audio_buffer) >= self.chunk_samples:
                    chunk = np.array(self.audio_buffer[:self.chunk_samples], dtype=np.int16)
                    self.audio_buffer = self.audio_buffer[self.chunk_samples:]

                    chunk_bytes = chunk.tobytes()
                    self.send_audio_chunk(chunk_bytes)

            except Exception as e:
                print(f"\n❌ Recording error: {e}")
                break

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False

        recording_duration = 0
        if self.recording_start_time:
            recording_duration = time.time() - self.recording_start_time

        print(f"🚫 Recording stopped ({recording_duration:.1f}s)")
        self.play_stop_sound()

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"❌ Audio closing error: {e}")

        try:
            if self.ws and self.ws.sock:
                if len(self.audio_buffer) > 0:
                    remaining_duration_ms = len(self.audio_buffer) / self.RATE * 1000

                    if remaining_duration_ms >= 100:
                        chunk = np.array(self.audio_buffer, dtype=np.int16)
                        chunk_bytes = chunk.tobytes()
                        self.send_audio_chunk(chunk_bytes)

                        time.sleep(0.1)

                        commit_event = {"type": "input_audio_buffer.commit"}
                        self.ws.send(json.dumps(commit_event))

                time.sleep(0.5)
                self.ws.close()
                self.ws = None
        except Exception as e:
            print(f"❌ Completion error: {e}")

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
        print(f"🎹 Готов к работе (модель: {self.OPENAI_MODEL_WS})")
        print("   Option + Command + Space - начать/остановить транскрипцию")
        print("   Ctrl+C - выход")
        print()

        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\n👋 Программа завершена")
                try:
                    self.cleanup()
                except Exception as e:
                    print(f"❌ Ошибка очистки: {e}")

    def cleanup(self):
        try:
            if self.is_recording:
                self.stop_recording()
        except Exception as e:
            print(f"❌ Ошибка остановки записи: {e}")

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        except Exception as e:
            print(f"❌ Ошибка закрытия потока: {e}")

        try:
            if self.ws:
                self.ws.close()
                self.ws = None
        except Exception as e:
            print(f"❌ Ошибка закрытия WebSocket: {e}")

        try:
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            print(f"❌ Ошибка завершения PyAudio: {e}")
def main():
    print("🎤 OpenAI Realtime Transcriber")
    print("=" * 40)

    transcriber = None
    try:
        transcriber = AudioTranscriber()
        transcriber.start_listening()
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("💡 Проверьте файл env.py и переменную OPEN_AI_KEY")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if transcriber:
            try:
                transcriber.cleanup()
            except Exception as e:
                print(f"❌ Ошибка финальной очистки: {e}")


if __name__ == "__main__":
    main()
