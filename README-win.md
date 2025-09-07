# Windows Audio Transcriber Setup Guide

## Требования
- Python 3.7+
- Windows 10/11
- Микрофон
- Интернет-соединение для API OpenAI

## Установка

### 1. Установка зависимостей
```bash
pip install -r requirements-windows.txt
```

### 2. Дополнительные зависимости (опционально, для лучшей интеграции)
Для более стабильной работы с нажатиями клавиш можно установить:
```bash
pip install pywin32
```

## Настройка

### 1. Скопируйте `example.env.py` в `env.py`
```bash
copy example.env.py env.py
```

### 2. Отредактируйте `env.py`:
- Добавьте ваш OpenAI API ключ в `OPEN_AI_KEY`
- Настройте остальные параметры по необходимости

## Запуск
```bash
python transcriber-windows.py
```

## Управление
- **Ctrl + Alt + Space** - начать/остановить запись
- **Ctrl + C** - выход из программы

## Основные изменения по сравнению с macOS версией

### Горячие клавиши
- macOS: `Cmd + Alt + Space`
- Windows: `Ctrl + Alt + Space`

### Буфер обмена
- Используется библиотека `pyperclip` вместо команды `pbcopy`

### Эмуляция нажатий
- Основной метод: `pyautogui.hotkey('ctrl', 'v')`
- Запасной метод: `win32api` (если установлен pywin32)

### Звуковые уведомления
- Используется встроенный модуль `winsound`
- Системные звуки Windows вместо macOS звуков
- Запасной вариант: простые beep звуки

## Возможные проблемы и решения

### 1. Ошибка установки PyAudio
```bash
# Если возникают проблемы с установкой PyAudio:
pip install pipwin
pipwin install pyaudio
```

### 2. Проблемы с правами доступа
- Запустите терминал от имени администратора
- Убедитесь, что Python имеет доступ к микрофону

### 3. Проблемы с горячими клавишами
- Убедитесь, что программа не заблокирована антивирусом
- Проверьте, что нет конфликтов с другими программами

### 4. Проблемы со звуком
- Проверьте настройки звука в Windows
- Убедитесь, что системные звуки включены

## Тестирование

Для проверки работы каждого компонента:

### Тест микрофона
```python
import pyaudio
audio = pyaudio.PyAudio()
print("Available audio devices:")
for i in range(audio.get_device_count()):
    print(f"  {i}: {audio.get_device_info_by_index(i)['name']}")
```

### Тест буфера обмена
```python
import pyperclip
pyperclip.copy("Test")
print(pyperclip.paste())
```

### Тест горячих клавиш
```python
import pyautogui
pyautogui.hotkey('ctrl', 'v')
```

## Дополнительные настройки

### Настройка чувствительности микрофона
В файле `env.py` измените значение `VAD_THRESHOLD`:
- Увеличьте для менее чувствительного обнаружения голоса
- Уменьшите для более чувствительного

### Отключение звуков
В файле `env.py` установите `SOUND_MODE = 'none'`
