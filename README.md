# Audio Transcriber

Voice-to-text console background python app for macOS. Records speech and automatically inserts transcribed text into active applications.

## Features

- 🎤 **Global Hotkey**: Start/stop recording with `Option+Command+Space`
- 🔄 **Two API Options**:
  - Realtime API for live transcription
  - Audio API for cost-effective batch processing
- 📋 **Auto-paste**: Automatically inserts transcribed text into the active application
- 🔊 **Audio Feedback**: System sounds for recording start/stop notifications
- � **Smart Audio Modes**: Configurable sound feedback (none/basic/all)
- �🎯 **Voice Activity Detection**: Smart detection of speech vs. silence
- 🧠 **Context-aware Transcription**: Uses previous transcriptions to improve accuracy
- 📼 **Pre-recording Buffer**: Captures speech start for better accuracy
- ⏰ **Auto-stop**: Automatically stops recording after configurable silence timeout
- ⚡ **Async Processing**: Non-blocking transcription with worker threads
- ⚙️ **Configurable**: Customizable VAD threshold, silence duration, auto-stop timeout, and model settings
- � **Smart Logging**: Configurable logging levels (normal/debug) for clean output
- �🛡️ **Error Handling**: Robust error management and resource cleanup

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Setup:**
```bash
cp env.py.example env.py
```

3. **Add your OpenAI API key to `env.py`:**
```python
OPEN_AI_KEY = "your-api-key-here"
```

4. **Run:**
```bash
python transcriber-req.py
```

## How it works

1. Press `Option+Command+Space` to start recording
2. Speak what you need
3. Program automatically transcribes and inserts (CMD+V's) text to where your cursor is
4. Press `Option+Command+Space` again to stop

## Features

- 🎤 **Global hotkey**: `Option+Command+Space` to start/stop
- 📋 **Auto-paste**: Transcribed text automatically inserted into active app
- 🔊 **Audio feedback**: Sound notifications for recording start/stop
- 🎯 **Smart speech detection**: Automatically detects speech vs silence
- ⏰ **Auto-stop**: Stops recording after silence timeout
- ⚙️ **Configurable**: Microphone sensitivity, pause duration, etc.

## Two versions

- **`transcriber-req.py`** - Recommended. Cheaper, supports multiple models, transcribes in chunks
- **`transcriber-ws.py`** - Real-time version. More expensive but faster response

## Main settings

In `env.py` file:

```python
# Transcription model
OPENAI_MODEL_REQ = "whisper-1"  # or "gpt-4o-transcribe"

# Microphone sensitivity
VAD_THRESHOLD = 1000  # Increase if picking up noise, decrease if not hearing speech

# Silence duration before auto sending (seconds)
SILENCE_DURATION = 1

# Auto-stops listening after N seconds of silence (seconds, 0 = disable)
AUTO_STOP_TIMEOUT = 30

# Sound notifications: 'none', 'basic', 'all'
SOUND_MODE = 'basic'

# Debug logs: True for detailed output
DEBUG_LOGS = False
```

## System requirements

- macOS
- Python 3.7+
- OpenAI API key
- Microphone access permission

## Controls

- `Option+Command+Space` - start/stop recording
- `Ctrl+C` in terminal - exit program

Program automatically inserts transcribed text into active application (text editors, browsers, messengers, etc.).
