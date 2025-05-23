import unittest
from unittest.mock import MagicMock, patch, call

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.audio_output.midi_handler import MidiHandler
from src.config_manager import ConfigManager # For type hinting and mocking
import mido # For mido.Message

class TestMidiHandler(unittest.TestCase):

    def _create_mock_config_manager(self, port_name=None, channel_range=[2, 16]):
        mock_cm = MagicMock(spec=ConfigManager)
        def get_setting_side_effect(key, default=None):
            if key == 'midi_output_port':
                return port_name
            if key == 'midi_channel_range':
                return channel_range
            return default
        mock_cm.get_setting.side_effect = get_setting_side_effect
        return mock_cm

    @patch('mido.open_output')
    @patch('mido.get_output_names')
    def setUp(self, mock_get_output_names, mock_open_output):
        # Common setup for most tests: successful port opening
        self.mock_get_output_names = mock_get_output_names
        self.mock_open_output = mock_open_output
        
        self.mock_port_instance = MagicMock(spec=mido.ports.BaseOutput)
        self.mock_port_instance.closed = False
        self.mock_port_instance.name = "TestMIDIPort"
        self.mock_open_output.return_value = self.mock_port_instance
        
        self.mock_get_output_names.return_value = ["TestMIDIPort", "OtherPort"]

        self.config_manager_default = self._create_mock_config_manager(port_name="TestMIDIPort")
        self.midi_handler = MidiHandler(config_manager=self.config_manager_default)
        self.midi_handler.port = self.mock_port_instance # Ensure it's set if open_port was mocked

    def test_initialization_and_open_port_success(self):
        """Test MidiHandler initialization and successful port opening."""
        self.mock_open_output.assert_called_once_with("TestMIDIPort")
        self.assertIsNotNone(self.midi_handler.port)
        self.assertEqual(self.midi_handler.port.name, "TestMIDIPort")
        self.assertEqual(self.midi_handler.available_channels, set(range(2, 17))) # Default range
        self.assertEqual(self.midi_handler.master_channel, 1)

    @patch('mido.open_output')
    @patch('mido.get_output_names')
    def test_open_port_no_specified_name_uses_default(self, mock_get_names, mock_open):
        mock_get_names.return_value = ["SomePort"]
        mock_default_port = MagicMock(spec=mido.ports.BaseOutput, name="DefaultPort")
        mock_open.return_value = mock_default_port
        
        cm_no_port = self._create_mock_config_manager(port_name=None)
        handler_no_port = MidiHandler(config_manager=cm_no_port)
        
        mock_open.assert_called_once_with() # Called with no args for default
        self.assertEqual(handler_no_port.port.name, "DefaultPort")

    @patch('mido.open_output')
    @patch('mido.get_output_names')
    def test_open_port_specified_name_not_found(self, mock_get_names, mock_open):
        mock_get_names.return_value = ["OtherPort1", "OtherPort2"]
        mock_open.side_effect = mido.MidiIOError("Port not found") # Simulate error or just return None
        
        cm_bad_port = self._create_mock_config_manager(port_name="NonExistentPort")
        with patch('builtins.print') as mock_print: # Suppress warnings
            handler_bad_port = MidiHandler(config_manager=cm_bad_port)
            self.assertIsNone(handler_bad_port.port)
            # Check if a warning about port not found was printed
            self.assertTrue(any("Warning: Configured MIDI port 'NonExistentPort' not found." in call_args[0][0] 
                                for call_args in mock_print.call_args_list))


    @patch('mido.open_output', side_effect=mido.MidiIOError("Failed to open"))
    @patch('mido.get_output_names')
    def test_open_port_io_error(self, mock_get_names, mock_open_err):
        mock_get_names.return_value = ["TestMIDIPort"] # Port exists
        cm = self._create_mock_config_manager(port_name="TestMIDIPort")
        with patch('builtins.print') as mock_print: # Suppress error prints
            handler_error = MidiHandler(config_manager=cm)
            self.assertIsNone(handler_error.port)
            self.assertTrue(any("Error opening MIDI port 'TestMIDIPort'" in call_args[0][0]
                                for call_args in mock_print.call_args_list))


    def test_close_port(self):
        """Test closing the MIDI port."""
        self.midi_handler.active_note_channels = {'finger1': 2, 'finger2': 3} # Simulate active channels
        initial_available = self.midi_handler.available_channels.copy()
        
        self.midi_handler.close_port()
        
        self.mock_port_instance.close.assert_called_once()
        self.assertIsNone(self.midi_handler.port)
        # Check if channels were reclaimed
        self.assertEqual(len(self.midi_handler.active_note_channels), 0)
        self.assertTrue(initial_available.issubset(self.midi_handler.available_channels))
        self.assertTrue(2 in self.midi_handler.available_channels)
        self.assertTrue(3 in self.midi_handler.available_channels)


    def test_send_note_on_off_mpe_channel_management(self):
        """Test MPE channel allocation and deallocation for note on/off."""
        finger1, finger2 = "f1", "f2"
        note1, note2 = 60, 62
        vel = 100
        
        # Note On f1
        self.midi_handler.send_note_on(note1, vel, finger1)
        self.assertIn(finger1, self.midi_handler.active_note_channels)
        ch_f1 = self.midi_handler.active_note_channels[finger1]
        self.mock_port_instance.send.assert_called_with(mido.Message('note_on', note=note1, velocity=vel, channel=ch_f1 - 1))
        
        # Note On f2
        self.midi_handler.send_note_on(note2, vel, finger2)
        self.assertIn(finger2, self.midi_handler.active_note_channels)
        ch_f2 = self.midi_handler.active_note_channels[finger2]
        self.assertNotEqual(ch_f1, ch_f2) # Different channels for different fingers
        self.mock_port_instance.send.assert_called_with(mido.Message('note_on', note=note2, velocity=vel, channel=ch_f2 - 1))

        # Note Off f1
        self.midi_handler.send_note_off(note1, finger1)
        self.assertNotIn(finger1, self.midi_handler.active_note_channels)
        self.assertIn(ch_f1, self.midi_handler.available_channels)
        self.mock_port_instance.send.assert_called_with(mido.Message('note_off', note=note1, velocity=0, channel=ch_f1 - 1))

        # Note Off f2
        self.midi_handler.send_note_off(note2, finger2)
        self.assertNotIn(finger2, self.midi_handler.active_note_channels)
        self.assertIn(ch_f2, self.midi_handler.available_channels)
        self.mock_port_instance.send.assert_called_with(mido.Message('note_off', note=note2, velocity=0, channel=ch_f2 - 1))

    def test_mpe_channel_exhaustion(self):
        """Test behavior when MPE channels are exhausted."""
        # Configure with a small channel range for easier testing
        small_range_cm = self._create_mock_config_manager(port_name="TestMIDIPort", channel_range=[2, 3]) # Only 2 channels (2, 3)
        handler_small_range = MidiHandler(config_manager=small_range_cm)
        handler_small_range.port = self.mock_port_instance # Assume port opened

        handler_small_range.send_note_on(60, 100, "f1") # Uses channel 2 (or 3)
        handler_small_range.send_note_on(62, 100, "f2") # Uses channel 3 (or 2)
        self.assertEqual(len(handler_small_range.available_channels), 0)
        
        with patch('builtins.print') as mock_print:
            handler_small_range.send_note_on(64, 100, "f3") # No more channels
            mock_print.assert_any_call("Warning: Ran out of MPE channels! Cannot send Note On.")
            # Ensure no message was sent for f3's note on
            # Check the calls to mock_port_instance.send
            # It should have been called twice for f1 and f2, but not for f3.
            self.assertEqual(self.mock_port_instance.send.call_count, 2) 
        self.mock_port_instance.send.reset_mock() # Reset for next tests


    def test_send_pitch_bend(self):
        """Test sending pitch bend messages."""
        finger_id = "myfinger"
        self.midi_handler.send_note_on(60, 100, finger_id) # Assign a channel
        assigned_channel = self.midi_handler.active_note_channels[finger_id]
        
        bend_val = 2048
        self.midi_handler.send_pitch_bend(bend_val, finger_id)
        self.mock_port_instance.send.assert_called_with(
            mido.Message('pitchwheel', pitch=bend_val, channel=assigned_channel - 1)
        )

    def test_send_channel_pressure(self):
        """Test sending channel pressure (aftertouch) messages."""
        finger_id = "anotherfinger"
        self.midi_handler.send_note_on(65, 100, finger_id)
        assigned_channel = self.midi_handler.active_note_channels[finger_id]
        
        pressure_val = 90
        self.midi_handler.send_channel_pressure(pressure_val, finger_id)
        self.mock_port_instance.send.assert_called_with(
            mido.Message('aftertouch', value=pressure_val, channel=assigned_channel - 1)
        )

    def test_send_control_change(self):
        """Test sending control change messages."""
        finger_id = "cc_finger"
        self.midi_handler.send_note_on(70, 100, finger_id)
        assigned_channel = self.midi_handler.active_note_channels[finger_id]
        
        cc_num, cc_val = 11, 75 # Example: CC11 (Expression)
        self.midi_handler.send_control_change(cc_num, cc_val, finger_id)
        self.mock_port_instance.send.assert_called_with(
            mido.Message('control_change', control=cc_num, value=cc_val, channel=assigned_channel - 1)
        )

    def test_send_commands_no_port(self):
        """Test that send commands do nothing if port is not open."""
        self.midi_handler.port = None # Simulate port not opened or closed
        
        self.midi_handler.send_note_on(60, 100, "f1")
        self.midi_handler.send_note_off(60, 100, "f1")
        self.midi_handler.send_pitch_bend(1000, "f1")
        self.midi_handler.send_channel_pressure(50, "f1")
        self.midi_handler.send_control_change(1,1, "f1")
        
        self.mock_port_instance.send.assert_not_called() # Port was self.mock_port_instance, so check its send
        
        # If port was truly None, and a different mock was used for a closed port,
        # that mock's send would also not be called.

    def test_invalid_midi_channel_range_config(self):
        """Test that an invalid midi_channel_range in config defaults to [2,16]."""
        # Test with various invalid ranges
        invalid_ranges = [
            [17, 2], # start > end
            [0, 5],  # start < 1
            [10, 20], # end > 16
            "not_a_list",
            [1], # not length 2
            ["a", "b"] # not integers
        ]
        with patch('builtins.print') as mock_print: # Suppress warnings
            for inv_range in invalid_ranges:
                cm = self._create_mock_config_manager(port_name="TestMIDIPort", channel_range=inv_range)
                handler = MidiHandler(config_manager=cm)
                self.assertEqual(handler.available_channels, set(range(2, 17)), 
                                 f"Failed for invalid range: {inv_range}")
                # Check if a warning about invalid range was printed
                self.assertTrue(any(f"Warning: Invalid 'midi_channel_range' ({inv_range}). Defaulting to [2, 16]." 
                                    in call_arg[0][0] for call_arg in mock_print.call_args_list),
                                f"No warning for invalid range: {inv_range}")
                mock_print.reset_mock()


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
