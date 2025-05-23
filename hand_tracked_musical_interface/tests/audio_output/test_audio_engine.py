import unittest
from unittest.mock import MagicMock, patch

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.audio_output.audio_engine import AudioEngine
from src.config_manager import ConfigManager # For type hinting
from src.audio_output.midi_handler import MidiHandler
from src.audio_output.synth_handler import SynthHandler

class TestAudioEngine(unittest.TestCase):

    def _create_mock_config_manager(self, audio_mode='midi'):
        mock_cm = MagicMock(spec=ConfigManager)
        # Simplified get_setting for audio_mode only, as other settings are handled by mocked handlers
        mock_cm.get_setting.side_effect = lambda key, default=None: audio_mode if key == 'audio_mode' else default
        return mock_cm

    @patch('src.audio_output.audio_engine.SynthHandler')
    @patch('src.audio_output.audio_engine.MidiHandler')
    def setUp(self, MockMidiHandler, MockSynthHandler):
        # Store mock classes for use in tests
        self.MockMidiHandler = MockMidiHandler
        self.MockSynthHandler = MockSynthHandler

        # Create mock instances that will be returned by the constructors
        self.mock_midi_handler_instance = MagicMock(spec=MidiHandler)
        self.mock_midi_handler_instance.port = MagicMock() # Simulate an open port for successful init
        
        self.mock_synth_handler_instance = MagicMock(spec=SynthHandler)
        self.mock_synth_handler_instance.mixer_initialized = True # Simulate successful mixer init

        self.MockMidiHandler.return_value = self.mock_midi_handler_instance
        self.MockSynthHandler.return_value = self.mock_synth_handler_instance
        
        # Default config for setup, can be overridden in tests
        self.default_config_manager = self._create_mock_config_manager(audio_mode='both')


    def test_initialization_midi_mode(self):
        """Test AudioEngine initialization in 'midi' mode."""
        config_manager_midi = self._create_mock_config_manager(audio_mode='midi')
        engine = AudioEngine(config_manager=config_manager_midi)
        
        self.MockMidiHandler.assert_called_once_with(config_manager_midi)
        self.MockSynthHandler.assert_not_called()
        self.assertIsNotNone(engine.midi_handler)
        self.assertIsNone(engine.synth_handler)

    def test_initialization_direct_mode(self):
        """Test AudioEngine initialization in 'direct' mode."""
        config_manager_direct = self._create_mock_config_manager(audio_mode='direct')
        engine = AudioEngine(config_manager=config_manager_direct)
        
        self.MockMidiHandler.assert_not_called()
        self.MockSynthHandler.assert_called_once_with(config_manager_direct)
        self.assertIsNone(engine.midi_handler)
        self.assertIsNotNone(engine.synth_handler)

    def test_initialization_both_mode(self):
        """Test AudioEngine initialization in 'both' mode."""
        config_manager_both = self._create_mock_config_manager(audio_mode='both')
        engine = AudioEngine(config_manager=config_manager_both)
        
        self.MockMidiHandler.assert_called_once_with(config_manager_both)
        self.MockSynthHandler.assert_called_once_with(config_manager_both)
        self.assertIsNotNone(engine.midi_handler)
        self.assertIsNotNone(engine.synth_handler)

    @patch('builtins.print') # Suppress print statements
    def test_initialization_midi_handler_fails_to_open_port(self, mock_print):
        """Test AudioEngine when MidiHandler fails to open a port."""
        self.mock_midi_handler_instance.port = None # Simulate port not opened
        config_manager_midi = self._create_mock_config_manager(audio_mode='midi')
        AudioEngine(config_manager=config_manager_midi) # Init with failing MidiHandler
        mock_print.assert_any_call("AudioEngine: MidiHandler initialized but MIDI port could not be opened.")

    @patch('builtins.print') # Suppress print statements
    def test_initialization_synth_handler_fails_to_init_mixer(self, mock_print):
        """Test AudioEngine when SynthHandler fails to initialize mixer."""
        self.mock_synth_handler_instance.mixer_initialized = False # Simulate mixer init failure
        config_manager_direct = self._create_mock_config_manager(audio_mode='direct')
        AudioEngine(config_manager=config_manager_direct)
        mock_print.assert_any_call("AudioEngine: SynthHandler initialized but Pygame mixer failed to initialize.")


    def test_note_on_routing(self):
        """Test note_on calls are routed correctly based on audio_mode."""
        note, vel, fid = 60, 100, "f1"
        
        # MIDI mode
        engine_midi = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='midi'))
        engine_midi.note_on(note, vel, fid)
        self.mock_midi_handler_instance.send_note_on.assert_called_with(note, vel, fid)
        self.mock_synth_handler_instance.play_note.assert_not_called()
        self.mock_midi_handler_instance.reset_mock()

        # Direct mode
        engine_direct = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='direct'))
        engine_direct.note_on(note, vel, fid)
        self.mock_midi_handler_instance.send_note_on.assert_not_called()
        self.mock_synth_handler_instance.play_note.assert_called_with(note, vel, fid)
        self.mock_synth_handler_instance.reset_mock()
        
        # Both mode
        engine_both = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='both'))
        engine_both.note_on(note, vel, fid)
        self.mock_midi_handler_instance.send_note_on.assert_called_with(note, vel, fid)
        self.mock_synth_handler_instance.play_note.assert_called_with(note, vel, fid)

    def test_note_off_routing(self):
        """Test note_off calls are routed correctly."""
        note, fid = 60, "f1"
        engine_both = AudioEngine(config_manager=self.default_config_manager) # Both mode
        engine_both.note_off(note, fid)
        self.mock_midi_handler_instance.send_note_off.assert_called_with(note, fid)
        self.mock_synth_handler_instance.stop_note.assert_called_with(note, fid)

    def test_pitch_bend_routing(self):
        """Test pitch_bend calls are routed (MIDI only for now as synth part is placeholder)."""
        bend_val, fid = 2048, "f1"
        engine_both = AudioEngine(config_manager=self.default_config_manager)
        engine_both.pitch_bend(bend_val, fid)
        self.mock_midi_handler_instance.send_pitch_bend.assert_called_with(bend_val, fid)
        # SynthHandler.update_note_pitch is not called directly by AudioEngine.pitch_bend in current impl
        self.mock_synth_handler_instance.update_note_pitch.assert_not_called() 

    def test_intensity_update_routing(self):
        """Test intensity_update calls are routed correctly."""
        pressure, fid, note = 80, "f1", 60
        engine_both = AudioEngine(config_manager=self.default_config_manager)
        
        # Mock synth_handler's active_sounds for the case where note_midi_value is None
        self.mock_synth_handler_instance.active_sounds = {fid: {'current_midi_note': note}}
        
        engine_both.intensity_update(pressure, fid, note_midi_value=note)
        self.mock_midi_handler_instance.send_channel_pressure.assert_called_with(pressure, fid)
        self.mock_synth_handler_instance.update_note_intensity.assert_called_with(note, pressure, fid)

    def test_intensity_update_synth_gets_note_from_active_sounds(self):
        """Test intensity_update for synth when note_midi_value is None but finger is active."""
        pressure, fid, active_note = 70, "f2", 62
        engine_direct = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='direct'))
        engine_direct.synth_handler.active_sounds = {fid: {'current_midi_note': active_note}}

        engine_direct.intensity_update(pressure, fid, note_midi_value=None)
        self.mock_synth_handler_instance.update_note_intensity.assert_called_with(active_note, pressure, fid)

    @patch('builtins.print') # Suppress print
    def test_intensity_update_synth_no_note_warning(self, mock_print):
        """Test warning if synth intensity update has no note and finger not active."""
        pressure, fid = 60, "f3"
        engine_direct = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='direct'))
        engine_direct.synth_handler.active_sounds = {} # Finger not active

        engine_direct.intensity_update(pressure, fid, note_midi_value=None)
        self.mock_synth_handler_instance.update_note_intensity.assert_not_called()
        # The warning print is commented out in the source, so can't check mock_print directly for it
        # unless it's uncommented. If it were, it would be:
        # mock_print.assert_any_call(f"Warning: SynthHandler.update_note_intensity needs note_midi_value for finger {fid}, but not provided and not active.")


    def test_shutdown_routing(self):
        """Test shutdown calls are routed to active handlers."""
        engine_both = AudioEngine(config_manager=self.default_config_manager)
        engine_both.shutdown()
        self.mock_midi_handler_instance.close_port.assert_called_once()
        self.mock_synth_handler_instance.close.assert_called_once()

        self.mock_midi_handler_instance.reset_mock()
        self.mock_synth_handler_instance.reset_mock()

        # MIDI only
        engine_midi = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='midi'))
        engine_midi.shutdown()
        self.mock_midi_handler_instance.close_port.assert_called_once()
        self.mock_synth_handler_instance.close.assert_not_called()
        
        self.mock_midi_handler_instance.reset_mock()

        # Direct only
        engine_direct = AudioEngine(config_manager=self._create_mock_config_manager(audio_mode='direct'))
        engine_direct.shutdown()
        self.mock_midi_handler_instance.close_port.assert_not_called()
        self.mock_synth_handler_instance.close.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
