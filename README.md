# Voxtarix Applet

![Voxtarix Icon](icon/voxtarix.png)

**Voxtarix** is a voice recognition applet for Linux desktop environments (e.g., GNOME) that allows users to transcribe speech to text locally, copy it to the clipboard, simulate typing, and manage a history of recognized text. It integrates with the system tray and provides a user-friendly interface to toggle features like clipboard integration, typing simulation, and muting.

## Features

- **Voice Recognition**: Transcribes spoken words to text using the Whisper model.
- **Clipboard Integration**: Automatically copies recognized text to the clipboard (toggleable).
- **Typing Simulation**: Simulates keyboard typing of recognized text (toggleable).
- **Mute Functionality**: Allows muting the voice recognition while keeping the engine running (input is discarded when muted).
- **History Management**: Keeps a history of the last 5 recognized texts, accessible via the system tray menu, with the ability to copy them to the clipboard.
- **Language Detection**: Automatically detects the GNOME system language (e.g., `de` for German, `en` for English) and uses it for voice recognition.
- **Voice Commands**: Supports voice commands to control the applet (e.g., "terminate yourself" to terminate, "turn clipboard on" to enable clipboard).
- **System Tray Integration**: Provides a system tray icon with a menu to toggle features and access history.
- **Start Menu Entry**: This README contains an example for a `.desktop` file for easy launching from the Start Menu.

## Requirements

- **Operating System**: Linux (tested on Manjaro with GNOME)
- **Python**: 3.6 or higher
- **Dependencies**:
  - `sounddevice`: For audio input
  - `numpy`: For audio processing
  - `whisper`: For speech recognition
  - `pyperclip`: For clipboard access
  - `pynput`: For typing simulation
  - `pygobject`: For GTK and AppIndicator integration
- **GNOME Desktop Environment**: For system tray integration and language detection
- **Microphone**: A working microphone for voice input
- **NVIDIA RTX**: Recommended for realtime recognition

## Installation

### Clone the Repository
Clone the project from GitHub:
```bash
git clone https://github.com/yourusername/voxtarix.git
cd voxtarix
```

Install Dependencies
Install the required Python packages:

```bash

pip3 install --user sounddevice numpy whisper pyperclip pynput pygobject
```

Edit Configuration Files
Ensure the following configuration files are present in the project directory (/path/to/voxtarix/):

    commands.json: Defines voice commands for different languages. Example:
    ```json

    {
        "terminate": {
            "de": "beende dich",
            "en": "terminate"
        },
        "clipboard_on": {
            "de": "Zwischenablage einschalten",
            "en": "clipboard on"
        },
        "clipboard_off": {
            "de": "Zwischenablage ausschalten",
            "en": "clipboard off"
        },
        "typing_on": {
            "de": "Tippen einschalten",
            "en": "typing on"
        },
        "typing_off": {
            "de": "Tippen ausschalten",
            "en": "typing off"
        }
    }
    ```

    settings.conf: Configures audio and Whisper settings. Example:
    ```ini

    [audio]
    sample_rate=16000
    channels=1
    blocksize=1024
    gain=8.0
    silence_threshold=0.15
    silence_duration=2.0
    min_duration=0.5
    warmup_time 2.0
    type_delay=0.01

    [whisper]
    model_name=medium
    ```

    You can experiment with the base model. I ran a simultaneous test and the base model's result were far behind. The medium model provides near perfect results if you articulate yourself clearly.

## Create a Start Menu Entry (Optional)
To launch the applet from the Start Menu, create a .desktop file:
```bash

mkdir -p ~/.local/share/applications
nano ~/.local/share/applications/voxtarix-applet.desktop
```

Add the following content:
```ini

[Desktop Entry]
Type=Application
Name=Voxtarix Applet
Comment=A voice recognition applet for GNOME
Exec=/usr/bin/python3 /path/to/voxtarix/voxtarix_applet.py
Path=/path/to/voxtarix
Icon=/path/to/voxtarix/icon/voxtarix-white.png
Terminal=false
Categories=Utility;Accessibility;
```

Replace /path/to/voxtarix with the actual path to your project directory (e.g., /home/mpw/gits/voxtarix).
Make the file executable:
```bash

chmod +x ~/.local/share/applications/voxtarix-applet.desktop
```

Update the desktop database (optional):
```bash

update-desktop-database ~/.local/share/applications
```

Usage

    Launch the Applet:
        If you created a Start Menu entry, search for "Voxtarix Applet" in the Activities overview and click to launch.
        Alternatively, run it manually:
        ```bash

        cd /path/to/voxtarix
        python voxtarix_applet.py
        ```

    Interact with the System Tray:
        A system tray icon (using voxtarix-white.png) will appear.
        Click the icon to open the menu, which includes:
            Clipboard: Toggle to enable/disable copying recognized text to the clipboard.
            Typing: Toggle to enable/disable typing simulation of recognized text.
            Mute: Toggle to mute voice recognition (input is discarded while muted).
            History: View the last 5 recognized texts; click an entry to copy it to the clipboard.
            Quit: Exit the applet.
    Voice Commands:
        Speak commands to control the applet (language depends on your GNOME settings):
            German (de): "beende dich", "Zwischenablage einschalten", "Tippen ausschalten", etc.
            English (en): "terminate", "clipboard on", "typing off", etc.
    Mute Functionality:
        When muted, the system tray icon changes to voxtarix_white_muted.png, and voice input is discarded (but the engine continues running).

Project Structure

    voxtarix_applet.py: The main applet script, providing the system tray interface and managing the VoxtarixEngine.
    voxtarix.py: The engine script, handling voice recognition, audio processing, and command execution.
    commands.json: Defines voice commands for different languages.
    settings.conf: Configures audio and Whisper settings.
    icon/:
        voxtarix-white.png: Icon for the unmuted state.
        voxtarix_white_muted.png: Icon for the muted state.

License
This project is licensed under the GPL-3.0 License (LICENSE). See the LICENSE file for details.
Acknowledgments

    Built with Whisper for speech recognition.
    Uses AppIndicator3 for system tray integration.
    Inspired by the need for accessible voice-to-text solutions on Linux.


