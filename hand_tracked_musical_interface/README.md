# Hand-Tracked Musical Interface

A Python application that allows users to play musical notes and control expressive parameters through real-time hand tracking using a webcam. The interface provides visual feedback and supports multiple audio output modes.

## Overview

This project captures hand movements via a webcam, processes this data to identify finger positions and gestures, and maps these interactions to musical notes and expressive controls. It offers a unique way to create music without traditional instruments.

## Features

*   **Real-time Hand and Finger Tracking:** Utilizes MediaPipe for robust hand landmark detection.
*   **Configurable Note Zone Layouts:**
    *   Supports chromatic scales.
    *   Allows user-defined scales (e.g., pentatonic, blues) via `config.yaml`.
    *   Layout automatically adjusts to the number of notes and screen resolution.
*   **Polyphonic Note Playing:** Each detected finger can potentially trigger and sustain a separate note (MPE-inspired).
*   **Expressive Control:**
    *   **Pitch Bend:** Horizontal (X-axis) movement of a finger within a note zone bends the pitch.
    *   **Velocity & Continuous Intensity:** Vertical (Y-axis) position of a finger at note activation determines initial velocity. Subsequent Y-axis movement controls continuous intensity (e.g., channel pressure or CC).
*   **Multiple Audio Output Modes:**
    *   **MIDI:** Sends MIDI messages to a chosen MIDI output port (virtual or physical).
    *   **Direct Synthesis:** Generates audio directly using Pygame (current default: sine wave).
    *   **Both:** Outputs to both MIDI and direct synthesis simultaneously.
*   **MPE-Inspired MIDI Output:** When in MIDI or Both mode, each active finger is assigned its own MIDI channel (from a configurable range) to allow per-note expression, similar to MIDI Polyphonic Expression (MPE).
*   **Visual Feedback:**
    *   Displays the live camera feed.
    *   Overlays interactive note zones.
    *   Shows detected hand landmarks.
    *   Highlights active note zones.
*   **Configuration via `config.yaml`:** Most application parameters can be customized.

## Project Structure

*   `hand_tracked_musical_interface/`
    *   `main.py`: The main entry point for the application.
    *   `src/`: Contains the core source code.
        *   `app.py`: `Application` class, orchestrates the components.
        *   `config_manager.py`: Loads and manages `config.yaml`.
        *   `hand_tracking/`: Hand detection logic (`detector.py`).
        *   `note_mapping/`: Note zone layout (`layout_generator.py`, `zone.py`) and interaction logic (`interaction_logic.py`).
        *   `expression_control/`: Processors for pitch bend and velocity/intensity.
        *   `audio_output/`: Audio handling (`audio_engine.py`, `midi_handler.py`, `synth_handler.py`).
        *   `ui/`: User interface rendering (`renderer.py`).
        *   `utils/`: Shared utilities (`datatypes.py`, `math_utils.py`).
    *   `config/`:
        *   `config.yaml`: Main configuration file.
    *   `docs/`: Project documentation files (like this one, `architecture.md`, `config_reference.md`).
    *   `tests/`: Unit tests for the project.
    *   `resources/`: Placeholder for future resources like samples or fonts.
    *   `requirements.txt`: Python dependencies.
    *   `README.md`: This file.

## Setup and Installation

### Prerequisites

*   **Python 3.x:** Recommended 3.8 or newer.
*   **Webcam:** Required for hand tracking.
*   **(Optional for MIDI Output)** A MIDI synthesizer or Digital Audio Workstation (DAW).
    *   **Windows:** Consider [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) for creating virtual MIDI ports.
    *   **macOS:** The built-in "IAC Driver" can be enabled in "Audio MIDI Setup".
    *   Examples: GarageBand, Ableton Live, Logic Pro, or software synthesizers like Helm, Surge XT.

### Installation Steps

1.  **Clone the Repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd hand_tracked_musical_interface
    ```
    (If you downloaded the source as a ZIP, extract it and navigate into the `hand_tracked_musical_interface` directory.)

2.  **Navigate to the Project Directory:**
    ```bash
    cd hand_tracked_musical_interface
    ```
    *(Ensure this is the directory containing `main.py` and `requirements.txt`)*

3.  **Install Dependencies:**
    It's highly recommended to use a virtual environment:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
    Then install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    The key libraries include: `mediapipe`, `opencv-python`, `mido`, `python-rtmidi`, `PyYAML`, `pygame`, `numpy`.

## Configuration

The application is configured through the `config/config.yaml` file. Open this file in a text editor to modify settings. Key settings include:

*   **`resolution`**: `[width, height]` for the application window (e.g., `[1280, 720]`).
*   **`fullscreen`**: `true` or `false`.
*   **`audio_mode`**:
    *   `"midi"`: Output MIDI messages only.
    *   `"direct"`: Output audio directly using the built-in synth.
    *   `"both"`: Output both MIDI and direct audio.
*   **`midi_output_port`**: The name of your MIDI output port.
    *   To find available port names, you can run a simple Python script:
        ```python
        import mido
        print(mido.get_output_names())
        ```
    *   Set this to the exact name shown by the script (e.g., `"loopMIDI Port"` or `"IAC Driver Bus 1"`). If left empty or `null`, the application will try to use a default port.
*   **`midi_channel_range`**: `[start_channel, end_channel]` for MPE-style per-finger MIDI messages (e.g., `[2, 16]`). Channel 1 is often reserved for global messages.
*   **`pitch_bend_range`**: Semitones for maximum pitch bend (e.g., `2.0`). This is for user reference and for the internal synth; actual MIDI pitch bend interpretation depends on the receiving synth's settings.
*   **`synth_type`**: For `direct` audio mode (e.g., `"sine"`). Currently, only sine wave is implemented.
*   **`starting_note`**: E.g., `"C4"`. Defines the base note for layout generation.
*   **`num_octaves`**: Number of octaves to generate for chromatic layouts.
*   **`active_scale`**: Name of a scale defined in `preset_scales` (e.g., `"C Major Pentatonic"`) or `null` for chromatic.
*   **`preset_scales`**: Define custom musical scales.
*   **`show_hand_landmarks`**: `true` or `false` to display hand tracking landmarks.
*   **`zone_labels`**: `true` or `false` to display note names on zones.
*   **`zone_style`**: `"block"` (filled) or `"outline"`.

Refer to `docs/config_reference.md` for a complete list and descriptions of all configuration options.

## Running the Application

1.  Ensure your webcam is connected and any MIDI setup (if using MIDI mode) is complete.
2.  Navigate to the project's root directory (`hand_tracked_musical_interface`).
3.  Run the main script:
    ```bash
    python main.py
    ```
    Alternatively, if you are in the directory *above* `hand_tracked_musical_interface`:
    ```bash
    python -m hand_tracked_musical_interface.main
    ```

### Controls

*   **`q` or `ESC`**: Quit the application.
*   **`r`**: Reload the note zone layout (useful if you modify `config.yaml` related to layout while the app is running).

## Troubleshooting

*   **Camera Not Detected:**
    *   Ensure your webcam is properly connected and not in use by another application.
    *   If you have multiple cameras, you might need to change `camera.index` in `config.yaml` (e.g., from `0` to `1`).
*   **No MIDI Output / MIDI Port Issues:**
    *   Verify the `midi_output_port` name in `config.yaml` matches exactly one of the ports listed by `mido.get_output_names()`.
    *   Ensure your MIDI synthesizer/DAW is running and configured to receive MIDI from the chosen port.
    *   For virtual MIDI ports (loopMIDI, IAC Driver), ensure they are correctly set up and selected in both this application and your synth/DAW.
*   **Library Installation Problems:**
    *   Ensure you are using a compatible Python version (3.8+ recommended).
    *   If `pip install -r requirements.txt` fails, try installing problematic packages individually. Some may have system dependencies (e.g., `opencv-python` can sometimes be tricky).
    *   Using a virtual environment is highly recommended to avoid conflicts.
*   **Low Performance / Low FPS:**
    *   Hand tracking can be CPU intensive. Ensure your system meets reasonable specs.
    *   Try reducing the `resolution` in `config.yaml`.
    *   Close other CPU-heavy applications.

## Future Enhancements / Roadmap

*   **More Synth Options:** Implement square, sawtooth, triangle waves, and basic wavetable/sample-based synthesis for `direct` audio mode.
*   **Advanced Visualizations:** More sophisticated UI feedback for note activation, intensity, pitch bend.
*   **Recording Feature:** Allow recording of performances (MIDI and/or audio).
*   **Configuration UI:** An in-app settings panel for easier configuration changes.
*   **Gesture Controls:** Implement more complex gestures for additional musical controls (e.g., changing scales, octaves, synth parameters).
*   **Refined MPE Support:** Ensure full compliance and more MPE-specific controls.
*   **Documentation:** Continue to expand and refine documentation.
```
