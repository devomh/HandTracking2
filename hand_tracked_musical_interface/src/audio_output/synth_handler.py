import pygame.mixer
import numpy as np
import math
import time # For potential debugging or short delays if needed.

# Assuming ConfigManager is in src.config_manager
from ..config_manager import ConfigManager

class SynthHandler:
    """
    Handles basic direct audio synthesis using Pygame.
    """
    SAMPLE_RATE = 44100
    AUDIO_FORMAT = -16  # Signed 16-bit
    NUM_CHANNELS = 2    # Stereo
    BUFFER_SIZE = 512   # Default buffer size

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the SynthHandler.

        Args:
            config_manager (ConfigManager): An instance of the ConfigManager.
        """
        try:
            pygame.mixer.init(
                frequency=self.SAMPLE_RATE,
                size=self.AUDIO_FORMAT,
                channels=self.NUM_CHANNELS,
                buffer=self.BUFFER_SIZE
            )
            print("Pygame mixer initialized successfully.")
        except pygame.error as e:
            print(f"Error initializing Pygame mixer: {e}. SynthHandler will be disabled.")
            pygame.mixer.quit() # Ensure it's not partially initialized.
            self.mixer_initialized = False
            return # Exit if mixer failed to init

        self.mixer_initialized = True
        self.config_manager = config_manager
        self.synth_type = self.config_manager.get_setting('synth_type', "sine")
        
        self.active_sounds = {}  # Maps finger_id to {'sound': pygame.mixer.Sound, 'base_freq': float, 'current_midi_note': int}
        
        # Base frequency for MIDI note 69 (A4)
        self.a4_freq = 440.0
        
        # Pre-allocate mixer channels for smoother playback if many notes are played quickly.
        # Pygame's default is 8. Let's increase it.
        num_mixer_channels = self.config_manager.get_setting('synth.num_mixer_channels', 16)
        pygame.mixer.set_num_channels(num_mixer_channels)


    def _frequency_from_midi(self, midi_note: int) -> float:
        """
        Converts a MIDI note number to its corresponding frequency.
        MIDI note 69 (A4) is 440 Hz.
        """
        if not (0 <= midi_note <= 127):
            # Or return a default frequency, or raise error
            print(f"Warning: MIDI note {midi_note} is out of standard range (0-127). Clamping.")
            midi_note = max(0, min(127, midi_note))
            
        return self.a4_freq * (2.0**((midi_note - 69.0) / 12.0))

    def _generate_sine_wave_sample(self, frequency: float, duration_sec: float = 1.0, volume: float = 0.5) -> np.ndarray:
        """
        Generates a NumPy array representing a sine wave.
        """
        if frequency <= 0: # Avoid issues with log or division by zero in some contexts
            frequency = 1 # Generate a DC offset or silence if freq is invalid
        
        num_samples = int(self.SAMPLE_RATE * duration_sec)
        time_array = np.linspace(0, duration_sec, num_samples, endpoint=False)
        
        # Generate sine wave
        wave = np.sin(2 * np.pi * frequency * time_array)
        
        # Amplitude scaling (volume) and conversion to 16-bit integer format
        amplitude = volume * (2**15 -1) # Max amplitude for 16-bit signed
        wave_scaled = (wave * amplitude).astype(np.int16)
        
        # For stereo, duplicate the mono wave to both channels
        stereo_wave = np.zeros((num_samples, 2), dtype=np.int16)
        stereo_wave[:, 0] = wave_scaled
        stereo_wave[:, 1] = wave_scaled
        
        return stereo_wave

    def _create_sound_from_sample(self, sample_array: np.ndarray) -> pygame.mixer.Sound | None:
        """
        Creates a Pygame Sound object from a NumPy sample array.
        """
        if not self.mixer_initialized: return None
        try:
            sound = pygame.sndarray.make_sound(sample_array)
            return sound
        except Exception as e: # Broad exception to catch potential pygame issues
            print(f"Error creating Pygame sound from sample: {e}")
            return None

    def play_note(self, note_midi_value: int, velocity: int, finger_id):
        """
        Plays a note using the configured synth type.

        Args:
            note_midi_value (int): MIDI note number.
            velocity (int): Note velocity (0-127).
            finger_id (any): Unique identifier for the finger.
        """
        if not self.mixer_initialized: return
        if finger_id in self.active_sounds:
            # Stop existing sound for this finger before starting a new one (re-trigger)
            self.stop_note(self.active_sounds[finger_id]['current_midi_note'], finger_id)

        if self.synth_type == "sine":
            frequency = self._frequency_from_midi(note_midi_value)
            # Map velocity (0-127) to volume (0.0 - 1.0)
            # Non-linear mapping might be better, e.g. ((velocity/127)**2)
            volume = (velocity / 127.0) * 0.5 # Max volume 0.5 to prevent clipping with multiple sounds
            
            # Generate a relatively short sample; it will be looped.
            # Duration doesn't matter much for looped sounds, but affects initial memory.
            sample_array = self._generate_sine_wave_sample(frequency, duration_sec=1.0, volume=volume)
            sound = self._create_sound_from_sample(sample_array)

            if sound:
                # print(f"Playing sound for finger {finger_id}: Note {note_midi_value}, Freq {frequency:.2f} Hz, Vol {volume:.2f}")
                sound.play(loops=-1) # Loop indefinitely until stopped
                self.active_sounds[finger_id] = {
                    'sound': sound, 
                    'base_freq': frequency, 
                    'current_midi_note': note_midi_value,
                    'initial_volume': volume
                }
        else:
            print(f"Synth type '{self.synth_type}' not supported yet.")


    def stop_note(self, _note_midi_value: int, finger_id): # _note_midi_value not strictly needed if finger_id is key
        """
        Stops a note being played by a specific finger.
        """
        if not self.mixer_initialized: return

        if finger_id in self.active_sounds:
            sound_info = self.active_sounds.pop(finger_id) # Remove and get
            sound_info['sound'].stop()
            # print(f"Stopped sound for finger {finger_id}")
        # else:
            # print(f"Warning: No active sound found for finger_id {finger_id} to stop.")


    def update_note_intensity(self, _note_midi_value: int, intensity: int, finger_id):
        """
        Updates the intensity (volume) of a currently playing note.

        Args:
            _note_midi_value (int): The MIDI note value (can be used for reference).
            intensity (int): Intensity value (0-127).
            finger_id (any): The finger whose note intensity to update.
        """
        if not self.mixer_initialized: return

        if finger_id in self.active_sounds:
            sound_info = self.active_sounds[finger_id]
            # Map intensity (0-127) to volume (0.0 - 1.0), similar to velocity
            new_volume = (intensity / 127.0) * 0.5 # Use same max volume as initial
            
            sound_info['sound'].set_volume(new_volume)
            # print(f"Updated intensity for finger {finger_id} to {new_volume:.2f}")


    def update_note_pitch(self, original_midi_note: int, bend_value: int, finger_id, 
                          pitch_bend_range_semitones: float):
        """
        Updates the pitch of a note based on a MIDI-style bend value.
        This is complex for sample-based synths; this implementation will re-trigger
        the sound at the new pitch.

        Args:
            original_midi_note (int): The original MIDI note value when the note was triggered.
            bend_value (int): MIDI pitch bend value (-8191 to 8191).
            finger_id (any): The finger whose note pitch to update.
            pitch_bend_range_semitones (float): The synth's current pitch bend range in semitones
                                                (e.g., if +/-8191 corresponds to +/- N semitones).
        """
        if not self.mixer_initialized: return

        if finger_id in self.active_sounds:
            sound_info = self.active_sounds[finger_id]
            
            # Calculate pitch shift in semitones from bend_value
            # bend_value is from -8191 to +8191.
            # This maps to -pitch_bend_range_semitones to +pitch_bend_range_semitones.
            semitone_shift = (bend_value / 8191.0) * pitch_bend_range_semitones
            
            # Calculate the new, bent frequency
            new_frequency = sound_info['base_freq'] * (2.0**(semitone_shift / 12.0))
            
            # Simple approach: stop current sound, generate new one, play it.
            # This will sound like a re-trigger.
            # print(f"Updating pitch for finger {finger_id}: Bend {bend_value} -> Shift {semitone_shift:.2f} st -> New Freq {new_frequency:.2f} Hz")
            
            current_volume = sound_info['sound'].get_volume() # Maintain current volume
            
            # Stop the old sound
            sound_info['sound'].stop() 
            
            # Generate new sound at the bent pitch
            # Duration doesn't matter much for looped sounds.
            new_sample_array = self._generate_sine_wave_sample(new_frequency, duration_sec=1.0, volume=current_volume)
            new_sound = self._create_sound_from_sample(new_sample_array)
            
            if new_sound:
                new_sound.play(loops=-1)
                self.active_sounds[finger_id]['sound'] = new_sound
                # Note: base_freq and current_midi_note in active_sounds remain the original ones.
                # This is important if further pitch bends are relative to the original note.
            # else:
                # print(f"Failed to create new sound for pitch bend on finger {finger_id}")

    def close(self):
        """
        Stops all sounds and quits the Pygame mixer.
        """
        if not self.mixer_initialized: return

        print("Stopping all sounds and quitting Pygame mixer.")
        for finger_id in list(self.active_sounds.keys()): # list keys because dict changes during iteration
             self.stop_note(0, finger_id) # Note value doesn't matter here
        
        pygame.mixer.quit()
        self.mixer_initialized = False


if __name__ == '__main__':
    # --- Mock ConfigManager for Testing ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data
        def get_setting(self, key, default=None):
            return self.config.get(key, default)

    mock_config_synth = {
        'synth_type': "sine",
        'synth.num_mixer_channels': 16
    }
    config_manager = MockConfigManager(mock_config_synth)
    synth_handler = SynthHandler(config_manager)

    if synth_handler.mixer_initialized:
        print("\n--- SynthHandler Test ---")
        
        finger1 = "finger_1"
        finger2 = "finger_2"

        # Test Play Note
        print("\nTesting Play Note:")
        synth_handler.play_note(note_midi_value=60, velocity=100, finger_id=finger1) # C4
        synth_handler.play_note(note_midi_value=67, velocity=80, finger_id=finger2)  # G4
        time.sleep(1) # Let notes play

        # Test Update Intensity
        print("\nTesting Update Intensity:")
        synth_handler.update_note_intensity(_note_midi_value=60, intensity=30, finger_id=finger1) # Softer C4
        synth_handler.update_note_intensity(_note_midi_value=67, intensity=127, finger_id=finger2) # Louder G4
        time.sleep(1)

        # Test Update Pitch (will re-trigger)
        # Assuming pitch_bend_range_semitones is, for example, 2 semitones for full bend.
        PITCH_BEND_RANGE_SEMITONES_EXAMPLE = 2.0
        print("\nTesting Update Pitch (re-triggers sound):")
        # Bend finger1's C4 up by 1 semitone (approx half of max_bend if range is 2st)
        synth_handler.update_note_pitch(original_midi_note=60, bend_value=4096, finger_id=finger1, 
                                        pitch_bend_range_semitones=PITCH_BEND_RANGE_SEMITONES_EXAMPLE) 
        # Bend finger2's G4 down by 0.5 semitones
        synth_handler.update_note_pitch(original_midi_note=67, bend_value=-2048, finger_id=finger2,
                                        pitch_bend_range_semitones=PITCH_BEND_RANGE_SEMITONES_EXAMPLE)
        time.sleep(1)
        
        # Test re-triggering a note for a finger already playing
        print("\nTesting re-triggering a note:")
        synth_handler.play_note(note_midi_value=62, velocity=90, finger_id=finger1) # D4 on finger1
        time.sleep(1)


        # Test Stop Note
        print("\nTesting Stop Note:")
        synth_handler.stop_note(_note_midi_value=62, finger_id=finger1)
        synth_handler.stop_note(_note_midi_value=67, finger_id=finger2) # Actually G4-ish due to bend
        time.sleep(0.5)

        print("\n--- Test Complete ---")
        synth_handler.close()
    else:
        print("\n--- SynthHandler Test: Pygame Mixer not initialized. Cannot run full test. ---")
        print("Please ensure you have a working audio output device and Pygame is installed correctly.")

```
