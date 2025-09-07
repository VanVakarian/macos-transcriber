OPEN_AI_KEY = 'sk-proj-YOUR-OPEN-AI-KEY-GOES-HERE'

# WS APP
OPENAI_MODEL_WS = 'gpt-4o-realtime-preview'
# OPENAI_MODEL_WS = 'gpt-4o-mini-realtime-preview'
CHUNK_SIZE_MS = 100

# HTTP REQ APP
OPENAI_MODEL_REQ = 'gpt-4o-transcribe'
# OPENAI_MODEL_REQ = 'gpt-4o-mini-transcribe'
# OPENAI_MODEL_REQ = 'whisper-1'

VAD_THRESHOLD = 1000      # Voice Activity Detection threshold
PRE_RECORD_MS = 150       # Pre-record buffer duration in milliseconds to capture speech start
SILENCE_DURATION = 1      # Seconds of silence to consider the end of a chunk
AUDIO_LENGTH_MIN = 0.5    # Minimum length of a single audio chunk in seconds
AUDIO_LENGTH_MAX = 30     # Maximum length of a single audio chunk in seconds
AUTO_STOP_TIMEOUT = 30    # Automatically stop recording after this many seconds of total silence, set to 0 to disable

ENABLE_CONTEXT = False    # Enable/disable sending context prompt to Whisper API
CONTEXT_CHUNKS_COUNT = 3  # Number of previous transcriptions to use as context for Whisper prompt

SOUND_MODE = 'basic'      # Sound playback mode: 'none' - no sounds, 'basic' - start/stop only, 'all' - all sounds

DEBUG_LOGS = False        # Enable/disable debug logging
