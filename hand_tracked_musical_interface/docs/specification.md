# 🎶 Hand-Tracked Musical Interface Specification

## 📌 Overview

This interface uses a camera to detect hand and finger positions and maps them to musical notes displayed on screen. Notes are played using either direct audio synthesis or by sending MIDI messages, supporting expressive control inspired by MPE (MIDI Polyphonic Expression). The system is developed in **Python** and configurable via a simple configuration file.

---

## 1. 🖐️ Interaction Model

### 1.1. Note Triggering

* A note is **triggered** when an **extended finger** **enters a note zone**. An extended finger is one detected as mostly straight and not curled. By default, any extended finger can trigger a note (this can be refined by the `use_all_fingers` configuration setting).
* The note **sustains** while the finger remains **extended** and **inside** the same zone.
* The note **stops** when the finger **retracts** or **leaves** the zone.

### 1.2. Multiple Notes

* **Multiple fingers** can trigger **different notes simultaneously** in **different zones**, allowing polyphonic play.
* Both hands are tracked independently; each hand can trigger and modulate separate notes.
* If multiple fingers enter the **same note zone**, the zone plays only **one instance** of the note. The note is triggered by the first finger entering and stops when the last of these fingers retracts or leaves that specific zone.

---

## 2. 🎹 Note Zone Layout

### 2.1. Structure

* Two rows of **visible rectangular zones** on the screen (unless modified by scale selection).
* Each zone is labeled with the note name (`C4`, `C#4`, etc.).
* Zones cover a configurable number of chromatic octaves (default: `C4–B4` and `C5–B5`).

### 2.2. Layout Type

* **Default Chromatic Linear Row Layout:**
    * Top row: `C4`–`B4` (or as configured by `starting_note` and `num_octaves`)
    * Bottom row: `C5`–`B5` (or as configured by `starting_note` and `num_octaves`)
    * All notes spaced evenly.
* **Scale-Specific Layout (Active when a scale is selected):**
    * If an `active_scale` is defined in the configuration and matches a scale from `preset_scales`, the layout changes.
    * Only the notes from the selected scale are displayed and mapped to the zones.
    * Zones are rearranged to present only these notes, typically maintaining the two-row structure and aiming for even spacing.

---

## 3. 🎧 Expressive Control (MPE-Inspired)

### 3.1. Pitch Bend (X-axis)

* Horizontal motion of the finger inside the zone alters the **pitch** of the note.
* **Range:** Configurable, e.g., ±1 semitone from the zone’s base pitch (default: 1 semitone).
* **Mapping:** Linear — center = base pitch; left = towards -range; right = towards +range.
* Produces a **smooth glissando** effect without retriggering.

### 3.2. Velocity and Continuous Intensity (Y-axis)

* The vertical (Y-axis) position of the finger has a dual role:
    * **Initial Velocity:** The Y-position of the finger **at the moment it enters the zone** determines the initial MIDI `Note On` velocity (or equivalent intensity for direct synthesis).
    * **Continuous Intensity Modulation:** Subsequent vertical motion of the sustained finger **within the zone** modulates a continuous expressive parameter (e.g., volume, timbre brightness).
* **Direction:** Lower Y = softer/less intense, Higher Y = louder/more intense.
* **Mapping:** Linear from min to max for both initial velocity and continuous modulation. For MIDI output, continuous modulation can be mapped to MIDI Channel Pressure or a specific CC (e.g., CC74 for brightness, CC11 for expression).

---

## 4. 🔊 Audio Output

### 4.1. MIDI Output

* Notes send standard **MIDI messages**:
    * `Note On` with velocity (derived from Y-axis entry position)
    * `Note Off`
    * `Pitch Bend` (derived from X-axis position)
    * Continuous expressive messages (e.g., Channel Pressure or CC, derived from Y-axis continuous motion)
* **Per-finger channel assignment** for MPE behavior (e.g., channels 2–16).
* Configurable MIDI output port (e.g., IAC Driver, loopMIDI).

### 4.2. Direct Audio Synthesis (Optional)

* Simple internal sound engine using basic waveforms or samples.
* Possible libraries: `pyo`, `fluidsynth`, `pygame.mixer`.
* Supports initial intensity and continuous intensity modulation analogous to MIDI velocity and expressive messages.

### 4.3. Output Modes

* Configurable via file:
    * `midi`
    * `direct`
    * `both`

---

## 5. 🖥️ Visual Feedback

* **Camera feed** forms the background.
* **Note zones** are overlaid, labeled, and highlighted on activation.
* **Hand landmarks** (fingers, joints) are drawn in real time.
* Optional:
    * Floating note labels near active fingers.
    * Visual pitch bend or velocity/intensity indicators.

---

## 6. ⚙️ Configuration

### 6.1. Config File

* Format: `config.yaml` or `config.json`

### 6.2. Settings Example

```yaml
fullscreen: true
resolution: [1280, 720]

audio_mode: midi # midi, direct, both
midi_output_port: "IAC Driver Bus 1"
synth_type: "sine" # For direct audio mode: e.g., sine, square, sample_based

midi_channel_range: [2, 16] # MPE channels (channel 1 is often global)
pitch_bend_range: 1 # Semitones

use_all_fingers: true # If false, might default to specific fingers (e.g., index only)

starting_note: C4
num_octaves: 2
active_scale: null # e.g., "C Major Pentatonic", null for chromatic
zone_labels: true
zone_style: "block" # e.g., block, outline

preset_scales:
  - name: "C Major"
    notes: ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5", "A5", "B5"]
  - name: "C Major Pentatonic"
    notes: ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"]
  - name: "Blues Minor"
    notes: ["C4", "Eb4", "F4", "Gb4", "G4", "Bb4", "C5", "Eb5", "F5", "Gb5", "G5", "Bb5"]

show_hand_landmarks: true
show_velocity_indicators: true # Visual feedback for Y-axis modulation
highlight_active_zones: true
```

---

## 7. 💻 Development Stack

* **Language**: Python
* **Libraries**:
    * Hand tracking: `mediapipe`
    * Vision/UI: `cv2`, optionally `PyQt` or `pygame`
    * MIDI: `mido`, `python-rtmidi`
    * Audio: `pyo`, `fluidsynth`, `pygame`
* **Platform**: Cross-platform (Windows, macOS, Linux)

---

## 8. ⚠️ Error Handling and Edge Cases

### 8.1. General Principle

* In the event of significant errors or tracking disruptions (e.g., hand tracking loss, critical software errors), all active musical notes should be stopped promptly (sending `Note Off` messages if applicable) to prevent unintended sustained sounds.

### 8.2. Specific Considerations (Examples)

* **Hand Tracking Loss:** If the system can no longer reliably track a hand or specific finger that is sustaining a note, that note should be terminated.
* **MIDI Port Unavailability:** If the configured MIDI output port becomes unavailable, the system should attempt to notify the user (e.g., console message) and cease attempts to send MIDI messages that would cause errors. Active notes linked to MIDI output should be stopped.
* **Configuration Errors:** On startup, if the configuration file is missing, malformed, or contains invalid critical parameters, the system should report the error and avoid starting with an unstable configuration.

---

## ✅ Summary

This interface offers a visually intuitive, musically expressive environment using only a webcam and Python. It supports:

* Two-hand polyphonic control
* Real-time pitch bend and velocity/intensity modulation
* MIDI and/or direct audio output
* Simple, config-file-based customization including note layouts and scales.

