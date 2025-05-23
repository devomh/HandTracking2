# Configuration File Reference (`config.yaml`)

This document provides a detailed reference for all settings available in the `config/config.yaml` file used by the Hand-Tracked Musical Interface.

## General Settings

### `fullscreen`
*   **Description:** Determines if the application window should attempt to launch in fullscreen mode.
*   **Type:** `boolean`
*   **Possible Values:** `true`, `false`
*   **Default:** `true` (as per initial `config.yaml`)

### `resolution`
*   **Description:** Sets the desired width and height of the application window and the processing resolution for the camera feed.
*   **Type:** `list` of two `integer` values `[width, height]`
*   **Example:** `[1280, 720]`
*   **Default:** `[1280, 720]`

## Audio Settings

### `audio_mode`
*   **Description:** Specifies the audio output method.
*   **Type:** `string`
*   **Possible Values:**
    *   `"midi"`: Output MIDI messages only. Requires a MIDI synthesizer/DAW.
    *   `"direct"`: Output audio directly using the built-in synthesizer.
    *   `"both"`: Output both MIDI messages and direct synthesized audio.
*   **Default:** `"midi"`

### `midi_output_port`
*   **Description:** The name of the MIDI output port to which MIDI messages will be sent. If `null` or an empty string, the system will attempt to use a default MIDI output port.
    *   To find available port names on your system, you can run a simple Python script:
        ```python
        import mido
        print(mido.get_output_names())
        ```
*   **Type:** `string` or `null`
*   **Example:** `"loopMIDI Port"`, `"IAC Driver Bus 1"`
*   **Default:** `"IAC Driver Bus 1"` (Note: this default might be system-specific; `null` is a safer general default if no specific port is pre-configured by the user). The provided `config.yaml` has this example.

### `midi_channel_range`
*   **Description:** Defines the range of MIDI channels (1-16) to be used for MPE-style per-finger note messages. Channel 1 is typically reserved for global/master messages in MPE setups. The range is inclusive.
*   **Type:** `list` of two `integer` values `[start_channel, end_channel]`
*   **Constraints:** `1 <= start_channel <= end_channel <= 16`.
*   **Example:** `[2, 16]` (Channels 2 through 16 will be used for individual finger notes)
*   **Default:** `[2, 16]`

### `pitch_bend_range`
*   **Description:** The maximum pitch bend range in semitones that the application assumes for its calculations (e.g., for the internal synthesizer). For MIDI output, the actual pitch bend interpretation is up to the receiving synthesizer (which should also be configured to match this range for consistent behavior). Standard MIDI pitch bend messages are typically +/- 2 semitones by default on many synths.
*   **Type:** `float` or `integer`
*   **Example:** `2.0` (meaning a full bend maps to +/- 2 semitones)
*   **Default:** `1.0` (Note: `config.yaml` shows `1`, which is an integer, but float is also acceptable.)

### `synth_type`
*   **Description:** Specifies the type of waveform or synthesis method for the `direct` audio mode.
*   **Type:** `string`
*   **Possible Values:**
    *   `"sine"`: Generates sine wave tones. (Currently the only implemented type)
    *   Future options might include: `"square"`, `"sawtooth"`, `"sample_based"`.
*   **Default:** `"sine"`

### `synth.num_mixer_channels` (Example of a nested setting, if used by `SynthHandler`)
*   **Description:** Number of channels to pre-allocate in Pygame's mixer. More channels can help with rapid note playing without sound cutoffs.
*   **Type:** `integer`
*   **Default:** `16` (as used in `SynthHandler` if not specified)

## Note Layout & Mapping Settings

### `starting_note`
*   **Description:** The base musical note from which chromatic layouts are generated. Uses standard pitch notation (e.g., "C4", "F#5").
*   **Type:** `string`
*   **Example:** `"C4"`
*   **Default:** `"C4"`

### `num_octaves`
*   **Description:** The number of octaves to generate for a chromatic layout, starting from `starting_note`.
*   **Type:** `integer`
*   **Example:** `2`
*   **Default:** `2`

### `active_scale`
*   **Description:** The name of a musical scale to use for the note layout. If specified, the layout will use the notes defined in `preset_scales` under this name. If `null` or an empty string, a chromatic layout will be generated based on `starting_note` and `num_octaves`.
*   **Type:** `string` or `null`
*   **Example:** `"C Major Pentatonic"`
*   **Default:** `null`

### `preset_scales`
*   **Description:** A list of predefined musical scales. Each scale is an object with a `name` and a list of `notes`. Notes should be strings in standard pitch notation (e.g., "C4", "Db5", "F#3").
*   **Type:** `list` of `objects`
    *   **Each object contains:**
        *   `name` (string): The display name of the scale (e.g., "C Major Pentatonic").
        *   `notes` (list of strings): The notes in the scale, with octave numbers (e.g., `["C4", "D4", "E4", "G4", "A4", "C5"]`).
*   **Example:**
    ```yaml
    preset_scales:
      - name: "C Major"
        notes: ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5", "A5", "B5"]
      - name: "C Major Pentatonic"
        notes: ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"]
    ```
*   **Default:** (As defined in the initial `config.yaml`, including "C Major", "C Major Pentatonic", "Blues Minor")

### `layout.padding` (Example of a nested setting)
*   **Description:** Screen padding (in pixels) around the area where note zones are drawn.
*   **Type:** `integer`
*   **Default:** `10` (as used in `LayoutGenerator` if not specified)

## Hand Tracking Settings (Namespace: `hand_detector`)

These settings are typically accessed by `HandDetector` using keys like `hand_detector.setting_name`.

### `hand_detector.static_image_mode`
*   **Description:** Informs MediaPipe whether to treat input images as a batch of static, unrelated images (`true`) or as a video stream (`false`). Setting to `false` allows MediaPipe to leverage temporal information for better tracking.
*   **Type:** `boolean`
*   **Default:** `false`

### `hand_detector.max_num_hands`
*   **Description:** Maximum number of hands to detect in the frame.
*   **Type:** `integer`
*   **Default:** `2`

### `hand_detector.min_detection_confidence`
*   **Description:** Minimum confidence value (0.0 to 1.0) from the hand detection model for the detection to be considered successful.
*   **Type:** `float`
*   **Default:** `0.5`

### `hand_detector.min_tracking_confidence`
*   **Description:** Minimum confidence value (0.0 to 1.0) from the landmark tracking model for the hand landmarks to be considered tracked successfully. Higher values can increase robustness of tracking but may also lead to more frequent loss of tracking if confidence drops.
*   **Type:** `float`
*   **Default:** `0.5`

### `use_all_fingers`
*   **Description:** If `true`, the system will attempt to use all detected fingers (thumb, index, middle, ring, pinky) for interaction. If `false`, it will only use fingers specified in `allowed_fingers`.
*   **Type:** `boolean`
*   **Default:** `true`

### `allowed_fingers`
*   **Description:** A list of finger names to be used for interaction if `use_all_fingers` is `false`. Finger names should match keys in `FINGER_TIP_LANDMARKS` (e.g., "THUMB", "INDEX", "MIDDLE", "RING", "PINKY").
*   **Type:** `list` of `string`
*   **Example:** `["INDEX", "MIDDLE"]`
*   **Default:** `["INDEX"]` (as per `InteractionManager` fallback if `use_all_fingers` is false and this list is empty or invalid)

## UI Settings

### `zone_labels`
*   **Description:** If `true`, displays note names (or custom labels) on the note zones.
*   **Type:** `boolean`
*   **Default:** `true`

### `zone_style`
*   **Description:** Visual style for the note zones.
*   **Type:** `string`
*   **Possible Values:**
    *   `"block"`: Zones are drawn as filled rectangles.
    *   `"outline"`: Zones are drawn as outlines only.
*   **Default:** `"block"`

### `show_hand_landmarks`
*   **Description:** If `true`, draws the detected hand landmarks and connections on the screen.
*   **Type:** `boolean`
*   **Default:** `true`

### `highlight_active_zones`
*   **Description:** If `true`, active (pressed) note zones will be visually highlighted.
*   **Type:** `boolean`
*   **Default:** `true`

### `show_velocity_indicators` (Placeholder for future feature)
*   **Description:** If `true`, displays visual indicators for the Y-axis modulation (velocity/intensity). *Note: This feature might not be fully implemented yet.*
*   **Type:** `boolean`
*   **Default:** `true` (as per initial `config.yaml`)

### `colors` (Namespace: `colors`)
*   **Description:** Defines colors for various UI elements in BGR (Blue, Green, Red) format.
*   **Type:** `object` (dictionary)
*   **Properties (Examples from `Renderer` defaults):**
    *   `zone_fill_default`: `[50, 50, 50]` (Dark Grey)
    *   `zone_border_default`: `[200, 200, 200]` (Light Grey)
    *   `zone_fill_active`: `[0, 80, 0]` (Darker Green)
    *   `zone_border_active`: `[0, 255, 0]` (Bright Green)
    *   `zone_text`: `[255, 255, 255]` (White)
    *   `landmark_point`: `[0, 0, 255]` (Red)
    *   `landmark_connector`: `[0, 255, 0]` (Green)
    *   `velocity_indicator`: `[255, 255, 0]` (Cyan/Aqua)
*   **Note:** Users can override these in `config.yaml` by defining the `colors` object and its specific keys.

## Camera Settings (Namespace: `camera`)

### `camera.index`
*   **Description:** The index of the camera to be used by OpenCV. `0` is typically the default built-in webcam. If you have multiple cameras, you might need to use `1`, `2`, etc.
*   **Type:** `integer`
*   **Default:** `0` (as used in `Application` if not specified)

---

This reference should help in understanding and customizing the application's behavior. For settings not explicitly listed here but found in `config.yaml`, their purpose can often be inferred from their name and the component that uses them.
```
