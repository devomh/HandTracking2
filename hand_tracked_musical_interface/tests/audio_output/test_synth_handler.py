import unittest
from unittest.mock import MagicMock, patch, call
import numpy as np # For asserting sample array structure if needed

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.audio_output.synth_handler import SynthHandler
from src.config_manager import ConfigManager # For type hinting and mocking

class TestSynthHandler(unittest.TestCase):

    def _create_mock_config_manager(self, synth_type="sine", num_mixer_channels=16):
        mock_cm = MagicMock(spec=ConfigManager)
        def get_setting_side_effect(key, default=None):
            if key == 'synth_type':
                return synth_type
            if key == 'synth.num_mixer_channels': # Note: config.yaml uses 'synth.num_mixer_channels'
                return num_mixer_channels
            return default
        mock_cm.get_setting.side_effect = get_setting_side_effect
        return mock_cm

    @patch('pygame.mixer.init')
    @patch('pygame.mixer.quit')
    @patch('pygame.mixer.set_num_channels')
    @patch('pygame.sndarray.make_sound') # Mock make_sound directly
    def setUp(self, mock_make_sound, mock_set_num_channels, mock_mixer_quit, mock_mixer_init):
        # Common setup for most tests: successful mixer initialization
        self.mock_mixer_init = mock_mixer_init
        self.mock_mixer_quit = mock_mixer_quit
        self.mock_set_num_channels = mock_set_num_channels
        self.mock_make_sound = mock_make_sound

        # Simulate successful mixer init by default
        self.mock_mixer_init.return_value = None 
        
        self.mock_sound_instance = MagicMock() # Mock for pygame.mixer.Sound instances
        self.mock_make_sound.return_value = self.mock_sound_instance

        self.config_manager_default = self._create_mock_config_manager()
        self.synth_handler = SynthHandler(config_manager=self.config_manager_default)
        
        # Ensure mixer_initialized is True if init was not supposed to fail
        if self.mock_mixer_init.call_count > 0 and not self.mock_mixer_init.side_effect:
             self.synth_handler.mixer_initialized = True


    def test_initialization_success(self):
        """Test successful SynthHandler initialization and mixer setup."""
        self.mock_mixer_init.assert_called_once_with(
            frequency=SynthHandler.SAMPLE_RATE,
            size=SynthHandler.AUDIO_FORMAT,
            channels=SynthHandler.NUM_CHANNELS,
            buffer=SynthHandler.BUFFER_SIZE
        )
        self.mock_set_num_channels.assert_called_once_with(16) # Default from _create_mock_config_manager
        self.assertTrue(self.synth_handler.mixer_initialized)
        self.assertEqual(self.synth_handler.synth_type, "sine")

    @patch('pygame.mixer.init', side_effect=pygame.error("Mixer init failed!"))
    @patch('pygame.mixer.quit')
    def test_initialization_failure(self, mock_quit, mock_init_fail):
        """Test SynthHandler initialization when pygame.mixer.init fails."""
        with patch('builtins.print') as mock_print:
            handler = SynthHandler(config_manager=self._create_mock_config_manager())
            self.assertFalse(handler.mixer_initialized)
            mock_init_fail.assert_called_once()
            mock_quit.assert_called_once() # Ensure quit is called if init fails
            mock_print.assert_any_call("Error initializing Pygame mixer: Mixer init failed!. SynthHandler will be disabled.")


    def test_frequency_from_midi(self):
        """Test MIDI note to frequency conversion."""
        self.assertAlmostEqual(self.synth_handler._frequency_from_midi(69), 440.0) # A4
        self.assertAlmostEqual(self.synth_handler._frequency_from_midi(57), 220.0) # A3
        self.assertAlmostEqual(self.synth_handler._frequency_from_midi(81), 880.0) # A5
        # Test clamping
        with patch('builtins.print') as mock_print:
            self.assertAlmostEqual(self.synth_handler._frequency_from_midi(130), self.synth_handler._frequency_from_midi(127))
            mock_print.assert_any_call("Warning: MIDI note 130 is out of standard range (0-127). Clamping.")

    def test_generate_sine_wave_sample(self):
        """Test sine wave sample generation."""
        freq = 440.0
        duration = 0.1 # Short duration for faster test
        volume = 0.5
        sample_array = self.synth_handler._generate_sine_wave_sample(freq, duration, volume)
        
        expected_num_samples = int(SynthHandler.SAMPLE_RATE * duration)
        self.assertEqual(sample_array.shape, (expected_num_samples, 2)) # num_samples, stereo channels
        self.assertEqual(sample_array.dtype, np.int16)
        
        # Check if values are within 16-bit range (approx, due to sine wave not always hitting max)
        max_expected_amplitude = volume * (2**15 - 1)
        self.assertTrue(np.max(np.abs(sample_array)) <= max_expected_amplitude)

    def test_play_note_sine_wave(self):
        """Test playing a sine wave note."""
        finger_id = "f1"
        note_midi = 60
        velocity = 100
        
        self.synth_handler.play_note(note_midi, velocity, finger_id)
        
        self.mock_make_sound.assert_called_once() # Sound was created
        self.mock_sound_instance.play.assert_called_once_with(loops=-1)
        self.assertIn(finger_id, self.synth_handler.active_sounds)
        sound_info = self.synth_handler.active_sounds[finger_id]
        self.assertEqual(sound_info['current_midi_note'], note_midi)
        self.assertAlmostEqual(sound_info['initial_volume'], (velocity / 127.0) * 0.5)

    def test_play_note_retrigger(self):
        """Test re-triggering a note for a finger already playing."""
        finger_id = "f_retrigger"
        self.synth_handler.play_note(60, 100, finger_id) # First note
        first_sound_mock = self.synth_handler.active_sounds[finger_id]['sound']
        
        self.synth_handler.play_note(62, 90, finger_id) # Second note for same finger
        
        first_sound_mock.stop.assert_called_once() # Old sound should be stopped
        self.assertIn(finger_id, self.synth_handler.active_sounds)
        self.assertEqual(self.synth_handler.active_sounds[finger_id]['current_midi_note'], 62) # New note active

    def test_stop_note(self):
        """Test stopping an active note."""
        finger_id = "f_stop"
        self.synth_handler.play_note(60, 100, finger_id)
        self.assertIn(finger_id, self.synth_handler.active_sounds)
        sound_to_stop = self.synth_handler.active_sounds[finger_id]['sound']
        
        self.synth_handler.stop_note(60, finger_id)
        sound_to_stop.stop.assert_called_once()
        self.assertNotIn(finger_id, self.synth_handler.active_sounds)

    def test_update_note_intensity(self):
        """Test updating the intensity (volume) of a note."""
        finger_id = "f_intensity"
        self.synth_handler.play_note(60, 100, finger_id)
        sound_to_update = self.synth_handler.active_sounds[finger_id]['sound']
        
        new_intensity = 64 # Roughly half
        expected_volume = (new_intensity / 127.0) * 0.5
        self.synth_handler.update_note_intensity(60, new_intensity, finger_id)
        sound_to_update.set_volume.assert_called_once_with(expected_volume)

    def test_update_note_pitch(self):
        """Test updating the pitch of a note (re-triggers sound)."""
        finger_id = "f_pitch"
        original_note = 60
        pitch_bend_range = 2.0 # semitones
        bend_value = 4096 # Approx +1 semitone if range is 2st (4096/8191 * 2.0)
        
        self.synth_handler.play_note(original_note, 100, finger_id)
        original_sound_info = self.synth_handler.active_sounds[finger_id]
        original_sound_mock = original_sound_info['sound']
        original_base_freq = original_sound_info['base_freq']

        # Mock make_sound again for the new sound created during pitch bend
        new_bent_sound_mock = MagicMock()
        self.mock_make_sound.return_value = new_bent_sound_mock # Subsequent calls to make_sound get this

        self.synth_handler.update_note_pitch(original_note, bend_value, finger_id, pitch_bend_range)

        original_sound_mock.stop.assert_called_once() # Original sound stopped
        self.assertTrue(self.mock_make_sound.call_count >= 2) # Called for original and bent sound
        new_bent_sound_mock.play.assert_called_once_with(loops=-1) # New sound played
        
        self.assertIn(finger_id, self.synth_handler.active_sounds)
        # Check that the new sound is stored, but base_freq and original_midi_note remain for reference
        self.assertEqual(self.synth_handler.active_sounds[finger_id]['sound'], new_bent_sound_mock)
        self.assertEqual(self.synth_handler.active_sounds[finger_id]['base_freq'], original_base_freq)
        self.assertEqual(self.synth_handler.active_sounds[finger_id]['current_midi_note'], original_note)


    def test_unsupported_synth_type(self):
        """Test behavior with an unsupported synth type."""
        cm_other_synth = self._create_mock_config_manager(synth_type="square")
        handler_other = SynthHandler(config_manager=cm_other_synth)
        handler_other.mixer_initialized = True # Assume mixer is fine
        
        with patch('builtins.print') as mock_print:
            handler_other.play_note(60, 100, "f_unsupported")
            mock_print.assert_any_call("Synth type 'square' not supported yet.")
            self.assertNotIn("f_unsupported", handler_other.active_sounds)

    @patch('pygame.mixer.quit') # Mock quit for this specific test of SynthHandler.close()
    def test_close_synth_handler(self, mock_mixer_quit_for_close):
        """Test closing the SynthHandler."""
        # Play a note to have an active sound
        self.synth_handler.play_note(60, 100, "f_close")
        active_sound_mock = self.synth_handler.active_sounds["f_close"]['sound']
        
        self.synth_handler.close()
        
        active_sound_mock.stop.assert_called_once() # Ensure active sounds are stopped
        mock_mixer_quit_for_close.assert_called_once() # Pygame mixer quit
        self.assertFalse(self.synth_handler.mixer_initialized)

    def test_methods_if_mixer_not_initialized(self):
        """Test that methods do nothing if mixer is not initialized."""
        self.synth_handler.mixer_initialized = False # Simulate init failure
        
        self.synth_handler.play_note(60, 100, "f_no_mixer")
        self.assertNotIn("f_no_mixer", self.synth_handler.active_sounds)
        # No assertion for mock_make_sound as it shouldn't be reached
        
        self.synth_handler.stop_note(60, "f_no_mixer") # Should not error
        self.synth_handler.update_note_intensity(60, 50, "f_no_mixer") # Should not error
        self.synth_handler.update_note_pitch(60, 1000, "f_no_mixer", 2.0) # Should not error
        self.synth_handler.close() # Should not error

        # Ensure no sound operations were attempted
        self.mock_sound_instance.play.assert_not_called()
        self.mock_sound_instance.stop.assert_not_called()
        self.mock_sound_instance.set_volume.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
