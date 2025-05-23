# System Architecture

## 1. Overview

The Hand-Tracked Musical Interface is a real-time application that processes webcam input to detect hand gestures and translates them into musical interactions. The system is modular, with distinct components responsible for configuration, hand tracking, note layout generation, interaction logic, expression processing, audio output, and UI rendering.

The core idea is to map finger positions and states (extended/retracted) to musical notes and their expressive parameters like pitch bend and intensity/velocity.

## 2. Component Breakdown

The application is primarily orchestrated by the `Application` class (`src/app.py`) and consists of the following key modules and classes:

*   **`ConfigManager` (`src/config_manager.py`)**
    *   **Responsibilities:** Loads application settings from the `config/config.yaml` file. Provides a centralized way for other components to access configuration parameters. Handles potential errors during file loading or parsing. Performs basic validation of critical settings.

*   **`HandDetector` (`src/hand_tracking/detector.py`)**
    *   **Responsibilities:** Uses the MediaPipe library to detect hands in the camera frame. Extracts landmark positions (e.g., fingertips, joints) for each detected hand. Determines the handedness (Left/Right) and the state of each finger (e.g., extended, retracted).
    *   **Key Methods:** `process_frame()` takes an image and returns processed hand data.

*   **`NoteZone` (`src/note_mapping/zone.py`)**
    *   **Responsibilities:** Represents a single interactive area on the screen that corresponds to a musical note. Stores its dimensions, associated note name, MIDI value, and current state (active/inactive).
    *   **Key Methods:** `is_point_inside()`, `activate()`, `deactivate()`.

*   **`LayoutGenerator` (`src/note_mapping/layout_generator.py`)**
    *   **Responsibilities:** Generates a list of `NoteZone` objects based on settings from `ConfigManager` (e.g., screen resolution, starting note, number of octaves, active musical scale). Arranges these zones on the screen, typically in rows. Supports chromatic layouts and layouts based on preset scales.
    *   **Key Methods:** `generate_layout()`, `get_zones()`.

*   **`InteractionManager` (`src/note_mapping/interaction_logic.py`)**
    *   **Responsibilities:** Acts as the bridge between hand tracking data and musical actions. It determines when notes should be triggered (Note On), released (Note Off), or modulated based on finger positions relative to `NoteZone` objects and finger states.
    *   **Key Data:** Maintains a list of `active_notes`, tracking which finger is interacting with which zone.
    *   **Key Methods:** `process_hands_data()` takes hand data and zones, then calls appropriate methods on the `AudioEngine` and updates `NoteZone` states.

*   **`PitchBendProcessor` (`src/expression_control/pitch_bend_processor.py`)**
    *   **Responsibilities:** Calculates MIDI pitch bend values based on the horizontal (X-axis) position of a finger within its active `NoteZone`.
    *   **Key Methods:** `calculate_pitch_bend()`.

*   **`VelocityIntensityProcessor` (`src/expression_control/velocity_intensity_processor.py`)**
    *   **Responsibilities:**
        *   Calculates initial MIDI velocity for a new note based on the vertical (Y-axis) position of the finger when it first activates a `NoteZone`.
        *   Calculates continuous intensity (for MIDI Channel Pressure or a CC) based on the ongoing Y-axis position of the finger within an active zone.
    *   **Key Methods:** `calculate_initial_velocity()`, `calculate_continuous_intensity()`.

*   **`AudioEngine` (`src/audio_output/audio_engine.py`)**
    *   **Responsibilities:** Manages the actual audio output. It acts as a facade, routing audio-related commands (Note On/Off, pitch bend, intensity changes) to either `MidiHandler`, `SynthHandler`, or both, based on the `audio_mode` setting in `config.yaml`.
    *   **Key Methods:** `note_on()`, `note_off()`, `pitch_bend()`, `intensity_update()`, `shutdown()`.

*   **`MidiHandler` (`src/audio_output/midi_handler.py`)**
    *   **Responsibilities:** Handles all MIDI-specific output. Opens a MIDI port (specified in config or default). Manages MPE-style channel allocation, assigning a unique MIDI channel per active finger to enable per-note expression. Sends MIDI messages like Note On, Note Off, Pitch Bend, and Channel Pressure.
    *   **Key Methods:** `send_note_on()`, `send_note_off()`, `send_pitch_bend()`, `send_channel_pressure()`.

*   **`SynthHandler` (`src/audio_output/synth_handler.py`)**
    *   **Responsibilities:** Handles direct audio synthesis using Pygame. Initializes the Pygame mixer. Generates sound samples (currently sine waves) for notes. Plays, stops, and modulates these sounds (volume for intensity, re-triggering at a new frequency for pitch bend).
    *   **Key Methods:** `play_note()`, `stop_note()`, `update_note_intensity()`, `update_note_pitch()`.

*   **`Renderer` (`src/ui/renderer.py`)**
    *   **Responsibilities:** Draws all visual elements of the application onto the camera frame. This includes rendering the `NoteZone` objects, displaying hand landmarks (if enabled), and potentially other UI feedback like FPS.
    *   **Key Methods:** `draw_frame()`.

*   **`Application` (`src/app.py`)**
    *   **Responsibilities:** The main class that orchestrates the entire application. It initializes all other components, manages the main application loop (camera capture, processing, rendering, event handling), and handles application shutdown.

## 3. Data Flow

1.  **Initialization:**
    *   `Application` starts `ConfigManager` to load `config.yaml`.
    *   `Application` initializes all other components, passing the `ConfigManager` instance to them so they can retrieve their respective settings.
    *   `LayoutGenerator` creates the initial set of `NoteZone` objects.
    *   `AudioEngine` initializes `MidiHandler` and/or `SynthHandler` based on `audio_mode`.
    *   `Application` initializes the camera.

2.  **Main Loop (per frame):**
    *   `Application` captures a frame from the webcam.
    *   The frame is passed to `HandDetector.process_frame()`.
        *   `HandDetector` uses MediaPipe to find hands and landmarks.
        *   It processes these to produce `hands_data` (a list of dictionaries, one per hand, containing normalized landmarks, handedness, finger states, etc.).
    *   `Application` retrieves the current list of `NoteZone` objects from `LayoutGenerator.get_zones()`.
    *   `hands_data` and `zones` are passed to `InteractionManager.process_hands_data()`.
        *   `InteractionManager` iterates through currently active notes to check for updates (sustain, modulation) or note-offs (finger moved out of zone, finger retracted, hand disappeared).
        *   It then iterates through new hand data to detect new note-on events (extended finger enters an available zone).
        *   For new notes, it uses `VelocityIntensityProcessor` to calculate initial velocity.
        *   For sustained notes, it uses `PitchBendProcessor` and `VelocityIntensityProcessor` to calculate modulation values.
        *   `InteractionManager` calls methods on `AudioEngine` (`note_on`, `note_off`, `pitch_bend`, `intensity_update`) to produce sound.
        *   `InteractionManager` updates the state of `NoteZone` objects (`activate`, `deactivate`).
    *   `Application` passes the original camera frame, `zones`, and `hands_data` to `Renderer.draw_frame()`.
        *   `Renderer` draws the note zones (highlighting active ones).
        *   If enabled, `Renderer` draws hand landmarks and connections on the frame.
    *   `Application` displays the final rendered frame using OpenCV and handles user input (e.g., 'q' to quit, 'r' to reload layout).

3.  **Shutdown:**
    *   When the loop terminates, `Application.shutdown()` calls cleanup methods on `AudioEngine` (which in turn closes `MidiHandler` and `SynthHandler`), `HandDetector`, and releases camera resources.

This data flow enables a continuous loop of capturing hand input, interpreting it musically, generating audio feedback, and updating the visual display.
```
