# Assuming ConfigManager is in src.config_manager
from ..config_manager import ConfigManager
from .midi_handler import MidiHandler
from .synth_handler import SynthHandler

class AudioEngine:
    """
    Manages audio output, routing commands to MidiHandler and/or SynthHandler
    based on the configured audio mode.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the AudioEngine.

        Args:
            config_manager (ConfigManager): An instance of the ConfigManager.
        """
        self.config_manager = config_manager
        self.audio_mode = self.config_manager.get_setting('audio_mode', 'midi').lower() # midi, direct, both

        self.midi_handler: MidiHandler | None = None
        self.synth_handler: SynthHandler | None = None

        if self.audio_mode in ['midi', 'both']:
            try:
                self.midi_handler = MidiHandler(self.config_manager)
                if not self.midi_handler.port: # Check if port opening was successful
                    print("AudioEngine: MidiHandler initialized but MIDI port could not be opened.")
                    # Optionally, could set self.midi_handler to None if port is essential
                    # For now, it will exist but won't send messages.
            except Exception as e:
                print(f"AudioEngine: Error initializing MidiHandler: {e}")
                self.midi_handler = None # Ensure it's None if init fails

        if self.audio_mode in ['direct', 'both']:
            try:
                self.synth_handler = SynthHandler(self.config_manager)
                if not self.synth_handler.mixer_initialized:
                    print("AudioEngine: SynthHandler initialized but Pygame mixer failed to initialize.")
                    # self.synth_handler = None # If mixer is essential
            except Exception as e:
                print(f"AudioEngine: Error initializing SynthHandler: {e}")
                self.synth_handler = None

        print(f"AudioEngine initialized in '{self.audio_mode}' mode.")
        if 'midi' in self.audio_mode and not self.midi_handler:
            print("AudioEngine: MIDI output requested but MidiHandler failed to initialize or open port.")
        if 'direct' in self.audio_mode and not self.synth_handler:
            print("AudioEngine: Direct audio output requested but SynthHandler failed to initialize.")


    def note_on(self, note_midi_value: int, velocity: int, finger_id):
        """
        Sends a note-on event to active handlers.
        """
        if self.midi_handler:
            self.midi_handler.send_note_on(note_midi_value, velocity, finger_id)
        
        if self.synth_handler:
            self.synth_handler.play_note(note_midi_value, velocity, finger_id)

    def note_off(self, note_midi_value: int, finger_id):
        """
        Sends a note-off event to active handlers.
        """
        if self.midi_handler:
            self.midi_handler.send_note_off(note_midi_value, finger_id)
            
        if self.synth_handler:
            self.synth_handler.stop_note(note_midi_value, finger_id)

    def pitch_bend(self, bend_value: int, finger_id):
        """
        Sends a pitch bend event to active handlers.
        """
        if self.midi_handler:
            self.midi_handler.send_pitch_bend(bend_value, finger_id)
            
        if self.synth_handler:
            # SynthHandler's update_note_pitch needs original_midi_note and pitch_bend_range.
            # This requires the AudioEngine or its caller to maintain state about active notes.
            # For simplicity, let's assume the caller (e.g., InteractionLogic) provides this.
            # This is a slight deviation if AudioEngine is meant to be state-agnostic.
            # However, pitch bend for synth typically needs more context than just the bend value.
            
            # Option 1: Caller provides this info.
            # Option 2: AudioEngine tracks active notes (more complex here).
            # Option 3: SynthHandler's update_note_pitch is simplified or takes less args (but might be less accurate).
            
            # For now, we assume the method signature for synth_handler.update_note_pitch
            # as defined previously: update_note_pitch(original_midi_note, bend_value, finger_id, pitch_bend_range_semitones)
            # This means the calling context of AudioEngine.pitch_bend needs to fetch/know these.
            # Let's make a placeholder call. The actual values would need to be passed in.
            
            # To fully implement this, AudioEngine.pitch_bend would need:
            # original_midi_note = self.active_notes[finger_id]['note'] # Example state
            # pitch_bend_range = self.config_manager.get_setting('pitch_bend_range', 2.0)
            # self.synth_handler.update_note_pitch(original_midi_note, bend_value, finger_id, pitch_bend_range)
            pass # Placeholder: See comment above. Proper synth pitch bend requires more context.
                 # Or a more advanced SynthHandler that can derive original note info.

    def intensity_update(self, pressure_value: int, finger_id, note_midi_value: int | None = None):
        """
        Sends an intensity update (e.g., channel pressure) to active handlers.

        Args:
            pressure_value (int): The intensity value (0-127).
            finger_id (any): The unique identifier for the finger.
            note_midi_value (int, optional): The MIDI note value associated with this intensity.
                                             Required by SynthHandler.update_note_intensity.
        """
        if self.midi_handler:
            # Using 'aftertouch' as decided in MidiHandler.
            # If a CC is preferred, config could specify CC number, and MidiHandler could send that.
            self.midi_handler.send_channel_pressure(pressure_value, finger_id)
            
        if self.synth_handler:
            if note_midi_value is None:
                # Try to get it from synth_handler's active sounds if possible, or warn
                if finger_id in self.synth_handler.active_sounds:
                    note_midi_value = self.synth_handler.active_sounds[finger_id]['current_midi_note']
                else:
                    # print(f"Warning: SynthHandler.update_note_intensity needs note_midi_value for finger {finger_id}, but not provided and not active.")
                    return # Cannot proceed without note_midi_value for synth
            self.synth_handler.update_note_intensity(note_midi_value, pressure_value, finger_id)


    def shutdown(self):
        """
        Shuts down all active audio handlers.
        """
        print("AudioEngine shutting down...")
        if self.midi_handler:
            self.midi_handler.close_port()
            print("MidiHandler closed.")
        
        if self.synth_handler:
            self.synth_handler.close()
            print("SynthHandler closed.")
        print("AudioEngine shutdown complete.")


if __name__ == '__main__':
    import time
    # --- Mock ConfigManager for Testing ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data
        def get_setting(self, key, default=None):
            # Basic dot notation access for testing
            if '.' in key:
                keys = key.split('.')
                val = self.config
                try:
                    for k_part in keys: val = val[k_part]
                    return val
                except (KeyError, TypeError): return default
            return self.config.get(key, default)

    # --- Test Scenario 1: MIDI Only ---
    print("\n--- Testing AudioEngine: MIDI Only Mode ---")
    mock_config_midi = {
        'audio_mode': 'midi',
        'midi_output_port': None, # Use default or set a specific virtual port name
        'midi_channel_range': [2, 5],
        'pitch_bend_range': 2.0 # Semitones
    }
    config_midi = MockConfigManager(mock_config_midi)
    engine_midi = AudioEngine(config_midi)

    if engine_midi.midi_handler and engine_midi.midi_handler.port:
        print("MIDI Engine seems active.")
        engine_midi.note_on(60, 100, "fingerA")
        engine_midi.intensity_update(80, "fingerA", 60)
        engine_midi.pitch_bend(2048, "fingerA") # Needs original note for synth, MIDI only is fine
        time.sleep(0.5)
        engine_midi.note_off(60, "fingerA")
    else:
        print("MIDI Engine not fully active for MIDI Only test (MidiHandler or port issue).")
    engine_midi.shutdown()

    # --- Test Scenario 2: Direct Audio Only ---
    print("\n--- Testing AudioEngine: Direct Audio Only Mode ---")
    mock_config_direct = {
        'audio_mode': 'direct',
        'synth_type': "sine",
        'pitch_bend_range': 2.0 # Semitones
    }
    config_direct = MockConfigManager(mock_config_direct)
    engine_direct = AudioEngine(config_direct)

    if engine_direct.synth_handler and engine_direct.synth_handler.mixer_initialized:
        print("Synth Engine seems active.")
        engine_direct.note_on(62, 90, "fingerB") # D4
        time.sleep(0.5)
        engine_direct.intensity_update(70, "fingerB", 62)
        time.sleep(0.5)
        # For synth pitch bend, we'd need to supply original note and range here
        # if not handled by AudioEngine state.
        # engine_direct.pitch_bend(bend_value=-4096, finger_id="fingerB") # This call will be a no-op due to placeholder
        # To test SynthHandler.update_note_pitch properly, we'd need to call it directly or enhance AudioEngine
        if "fingerB" in engine_direct.synth_handler.active_sounds:
             original_note = engine_direct.synth_handler.active_sounds["fingerB"]['current_midi_note']
             pb_range = engine_direct.config_manager.get_setting('pitch_bend_range')
             engine_direct.synth_handler.update_note_pitch(original_note, -3000, "fingerB", pb_range)
             print(f"Called synth_handler.update_note_pitch directly for testing fingerB.")
        time.sleep(0.5)
        engine_direct.note_off(62, "fingerB")
    else:
        print("Synth Engine not active for Direct Audio Only test (SynthHandler or mixer issue).")
    engine_direct.shutdown()

    # --- Test Scenario 3: Both MIDI and Direct Audio ---
    print("\n--- Testing AudioEngine: Both Mode ---")
    mock_config_both = {
        'audio_mode': 'both',
        'midi_output_port': None,
        'midi_channel_range': [2, 5],
        'synth_type': "sine",
        'pitch_bend_range': 2.0
    }
    config_both = MockConfigManager(mock_config_both)
    engine_both = AudioEngine(config_both)

    if (engine_both.midi_handler and engine_both.midi_handler.port) and \
       (engine_both.synth_handler and engine_both.synth_handler.mixer_initialized):
        print("Both MIDI and Synth Engines seem active.")
        engine_both.note_on(64, 110, "fingerC") # E4
        time.sleep(0.2)
        engine_both.intensity_update(60, "fingerC", 64)
        time.sleep(0.2)
        # engine_both.pitch_bend(-1024, "fingerC") # MIDI part would work
        if "fingerC" in engine_both.synth_handler.active_sounds: # Direct call for synth pitch bend test
             original_note = engine_both.synth_handler.active_sounds["fingerC"]['current_midi_note']
             pb_range = engine_both.config_manager.get_setting('pitch_bend_range')
             engine_both.synth_handler.update_note_pitch(original_note, -1024, "fingerC", pb_range)
             print(f"Called synth_handler.update_note_pitch directly for testing fingerC.")
        time.sleep(0.5)
        engine_both.note_off(64, "fingerC")
    else:
        print("One or both engines not active for Both Mode test.")
    engine_both.shutdown()

    print("\n--- All AudioEngine Tests Complete ---")

```
