# Audio Transcriber

A real-time audio transcription tool for macOS that uses OpenAI's Realtime API to convert speech to text with global hotkey activation and automatic text insertion.

## Features

- 🎤 **Global Hotkey**: Start/stop recording with `Option+Command+Space`
- 🔄 **Real-time Transcription**: Powered by OpenAI's gpt-4o-mini-realtime-preview model
- 📋 **Auto-paste**: Automatically inserts transcribed text into the active application
- 🔊 **Audio Feedback**: System sounds for recording start/stop notifications
- ⚙️ **Configurable**: Customizable chunk size and model settings
- 🛡️ **Error Handling**: Robust error management and resource cleanup

## Technologies

- **OpenAI Realtime API**: Real-time speech-to-text transcription
- **PyAudio**: Audio capture and processing
- **WebSocket**: Real-time communication with OpenAI API
- **pynput**: Global hotkey detection
- **CoreGraphics**: System-level keyboard simulation for auto-paste
- **Base64**: Audio encoding for API transmission

## Dependencies

```bash
pip install openai pyaudio pynput websocket-client
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

4. Edit `env.py` and add your OpenAI API key:
```python
OPEN_AI_KEY = "your-openai-api-key-here"
OPENAI_MODEL = "gpt-4o-mini-realtime-preview"
CHUNK_SIZE_MS = 100
```

## Usage

1. Start the transcriber:
```bash
python transcriber.py
```

2. Use the hotkey to control recording:
   - Press `Option+Command+Space` to start recording
   - Press `Option+Command+Space` again to stop recording
   - The transcribed text will be automatically pasted into the active application

3. Exit the program:
   - Press `Esc` to quit

## Audio Settings

The transcriber uses the following audio configuration:
- **Sample Rate**: 24,000 Hz
- **Format**: PCM16 (16-bit)
- **Channels**: Mono
- **Chunk Size**: Configurable (default: 100ms)

## System Requirements

- macOS (required for CoreGraphics and system sounds)
- Python 3.7+
- OpenAI API key with access to Realtime API
- Microphone access permissions

## License

MIT License
