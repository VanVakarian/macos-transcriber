# Audio Transcriber

A real-time audio transcription tool for macOS that supports both OpenAI's Realtime API and standard Audio API for speech-to-text conversion with global hotkey activation and automatic text insertion.

## Features

- 🎤 **Global Hotkey**: Start/stop recording with `Option+Command+Space`
- 🔄 **Two API Options**:
  - Realtime API for live transcription
  - Audio API for cost-effective batch processing
- 📋 **Auto-paste**: Automatically inserts transcribed text into the active application
- 🔊 **Audio Feedback**: System sounds for recording start/stop notifications
- 🎯 **Voice Activity Detection**: Smart detection of speech vs. silence
- ⚙️ **Configurable**: Customizable VAD threshold, silence duration, and model settings
- 🛡️ **Error Handling**: Robust error management and resource cleanup

## Available Scripts

- **`transcriber-ws.py`**: WebSocket-based transcriber using OpenAI Realtime API - higher cost, real-time processing
- **`transcriber-req.py`**: Request-based transcriber using OpenAI Audio API - lower cost, supports multiple models (whisper-1, gpt-4o-transcribe, etc.)

## Technologies

### Realtime Version (transcriber-ws.py)
- **OpenAI Realtime API**: Real-time speech-to-text transcription
- **WebSocket**: Real-time communication with OpenAI API
- **Server-side VAD**: Voice activity detection handled by OpenAI

### Request-based Version (transcriber-req.py)
- **OpenAI Audio API**: Cost-effective transcription with multiple model options
- **HTTP Requests**: Standard REST API calls
- **Local VAD**: Client-side voice activity detection
- **Smart Buffering**: Accumulates speech and sends complete phrases
- **Model Flexibility**: Supports whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe

### Common Technologies
- **PyAudio**: Audio capture and processing
- **pynput**: Global hotkey detection
- **CoreGraphics**: System-level keyboard simulation for auto-paste
- **NumPy**: Audio processing and VAD calculations

## Dependencies

```bash
pip install openai pyaudio pynput websocket-client numpy requests
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/VanVakarian/transcriber.git
cd transcriber
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
```bash
cp env.py.example env.py
```

4. Edit `env.py` and add your OpenAI API key and settings:
```python
OPEN_AI_KEY = "your-openai-api-key-here"

# For Realtime API (transcriber-ws.py)
OPENAI_MODEL_WS = "gpt-4o-mini-realtime-preview"  # or "gpt-4o-realtime-preview"
CHUNK_SIZE_MS = 100

# For Audio API (transcriber-req.py)
OPENAI_MODEL_REQ = "whisper-1"  # or "gpt-4o-transcribe" or "gpt-4o-mini-transcribe"
VAD_THRESHOLD = 500
SILENCE_DURATION = 1.5
AUDIO_LENGTH_MIN = 0.5
AUDIO_LENGTH_MAX = 30.0
```

## Usage

### Realtime Version (Higher Cost, Live Processing)
```bash
python transcriber-ws.py
```

### Request-based Version (Lower Cost, Smart Buffering)
```bash
python transcriber-req.py
```

### Controls
- Press `Option+Command+Space` to start/stop recording
- The transcribed text will be automatically pasted into the active application
- Press `Ctrl+C` in terminal to exit the program

## Configuration

### VAD Settings (Request-based version only)
- **VAD_THRESHOLD**: Minimum audio level to detect voice (default: 500)
- **SILENCE_DURATION**: Seconds of silence before sending audio (default: 1.5s)
- **AUDIO_LENGTH_MIN**: Minimum audio length to process (default: 0.5s)
- **AUDIO_LENGTH_MAX**: Maximum audio length before auto-send (default: 30.0s)

## Audio Settings

### Realtime Version (transcriber-ws.py)
- **Sample Rate**: 24,000 Hz (optimized for Realtime API)
- **Format**: PCM16 (16-bit)
- **Channels**: Mono
- **Chunk Size**: Configurable (default: 100ms)

### Request-based Version (transcriber-req.py)
- **Sample Rate**: 16,000 Hz (optimized for Audio API)
- **Format**: PCM16 (16-bit)
- **Channels**: Mono
- **VAD-based Processing**: Only sends audio when speech is detected
- **Multiple Models**: Supports whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe

## System Requirements

- macOS (required for CoreGraphics and system sounds)
- Python 3.7+
- OpenAI API key
- Microphone access permissions

## Cost Comparison

- **Realtime API** (transcriber-ws.py): Higher cost, real-time processing, server-side VAD
- **Audio API** (transcriber-req.py): $0.006 per 1M tokens, local VAD, batch processing, multiple model options

Choose the request-based version for cost-effective daily use!

## License

MIT License
