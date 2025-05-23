import unittest
from unittest.mock import MagicMock, patch

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.note_mapping.layout_generator import LayoutGenerator
from src.note_mapping.zone import NoteZone
from src.config_manager import ConfigManager # For type hinting and mocking

class TestLayoutGenerator(unittest.TestCase):

    def _create_mock_config_manager(self, config_data):
        mock_cm = MagicMock(spec=ConfigManager)
        def get_setting_side_effect(key, default=None):
            # Basic dot notation access for testing
            if '.' in key:
                keys = key.split('.')
                val = config_data
                try:
                    for k_part in keys: val = val[k_part]
                    return val
                except (KeyError, TypeError, IndexError): return default
            return config_data.get(key, default)
        mock_cm.get_setting.side_effect = get_setting_side_effect
        return mock_cm

    def test_initialization_type_error(self):
        """Test TypeError if config_manager is not a ConfigManager instance."""
        with self.assertRaises(TypeError):
            LayoutGenerator(config_manager="not_a_config_manager")

    def test_midi_conversion_utilities(self):
        """Test _get_midi_value and _get_note_name methods."""
        mock_config_data = {'resolution': [800, 600]} # Minimal config for instantiation
        mock_cm = self._create_mock_config_manager(mock_config_data)
        lg = LayoutGenerator(mock_cm) # Layout will be generated but we focus on helpers

        test_notes = {
            "C4": 60, "C#4": 61, "Db4": 61, "A4": 69, "C5": 72, 
            "B3": 59, "G#7": 104, "F3": 53, "E2": 40
        }
        for name, midi in test_notes.items():
            self.assertEqual(lg._get_midi_value(name), midi, f"MIDI for {name} failed")
            # Our _get_note_name prefers sharps for black keys
            expected_name = name.replace("Db", "C#").replace("Eb", "D#").replace("Gb", "F#").replace("Ab", "G#").replace("Bb", "A#")
            self.assertEqual(lg._get_note_name(midi), expected_name, f"Name for {midi} (from {name}) failed")
        
        with self.assertRaises(ValueError, msg="Invalid note name format: C"):
            lg._get_midi_value("C") # Invalid format
        with self.assertRaises(ValueError, msg="Invalid octave in note name: CX"):
            lg._get_midi_value("CX") # Invalid octave
        with self.assertRaises(ValueError, msg="Invalid note name: H4"):
            lg._get_midi_value("H4") # Invalid note name part
        with self.assertRaises(ValueError, msg="MIDI value must be an integer between 0 and 127."):
            lg._get_note_name(128)
        with self.assertRaises(ValueError, msg="MIDI value must be an integer between 0 and 127."):
            lg._get_note_name(-1)


    def test_generate_chromatic_layout(self):
        """Test generating a chromatic layout."""
        mock_config_data = {
            'resolution': [800, 300],
            'starting_note': "C4",
            'num_octaves': 1, # 12 notes
            'active_scale': None,
            'preset_scales': [],
            'zone_labels': True,
            'layout.padding': 10
        }
        mock_cm = self._create_mock_config_manager(mock_config_data)
        lg = LayoutGenerator(mock_cm)
        zones = lg.get_zones()

        self.assertEqual(len(zones), 12) # C4 to B4
        self.assertEqual(zones[0].note_name, "C4")
        self.assertEqual(zones[0].note_midi_value, 60)
        self.assertEqual(zones[11].note_name, "B4")
        self.assertEqual(zones[11].note_midi_value, 71)
        
        # Check zone properties (example for the first zone)
        # Rows: 12 notes / 2 rows = 6 notes per row
        # Zone area: width=800-20=780, height=300-20=280
        # Row height: 280/2 = 140
        # Zone width (row 1): 780/6 = 130
        self.assertEqual(zones[0].rect, (10, 10, 130, 140)) # x, y, w, h (padding 10)
        self.assertEqual(zones[0].label, "C4")


    def test_generate_scale_layout(self):
        """Test generating a layout based on a preset scale."""
        scale_notes = ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"] # 10 notes
        mock_config_data = {
            'resolution': [1000, 400],
            'starting_note': "C3", # Should be ignored if scale notes are absolute
            'num_octaves': 2,      # Should be ignored if scale notes provide range
            'active_scale': "Test Pentatonic",
            'preset_scales': [
                {'name': "Test Pentatonic", 'notes': scale_notes.copy()}
            ],
            'zone_labels': False, # Test disabled labels
            'layout.padding': 20
        }
        mock_cm = self._create_mock_config_manager(mock_config_data)
        lg = LayoutGenerator(mock_cm)
        zones = lg.get_zones()

        self.assertEqual(len(zones), 10)
        self.assertEqual(zones[0].note_name, "C4")
        self.assertEqual(zones[0].note_midi_value, 60)
        self.assertEqual(zones[9].note_name, "A5")
        self.assertEqual(zones[9].note_midi_value, 81) # A5
        
        # Check zone properties (example for the first zone)
        # Rows: 10 notes / 2 rows = 5 notes per row
        # Zone area: width=1000-40=960, height=400-40=360
        # Row height: 360/2 = 180
        # Zone width (row 1): 960/5 = 192
        self.assertEqual(zones[0].rect, (20, 20, 192, 180))
        self.assertIsNone(zones[0].label) # zone_labels is False

    def test_unknown_scale_defaults_to_chromatic(self):
        """Test fallback to chromatic if active_scale is not found."""
        mock_config_data = {
            'resolution': [800, 300],
            'starting_note': "A3",
            'num_octaves': 1, # 12 notes
            'active_scale': "Unknown Scale",
            'preset_scales': [{'name': "Some Other Scale", 'notes': ["C4", "E4", "G4"]}],
            'zone_labels': True,
            'layout.padding': 0 # No padding
        }
        mock_cm = self._create_mock_config_manager(mock_config_data)
        
        with patch('builtins.print') as mock_print: # Suppress warning print
            lg = LayoutGenerator(mock_cm)
            mock_print.assert_any_call("Warning: Active scale 'Unknown Scale' not found in presets. Defaulting to chromatic.")

        zones = lg.get_zones()
        self.assertEqual(len(zones), 12) # A3 to G#4
        self.assertEqual(zones[0].note_name, "A3") # MIDI 57
        self.assertEqual(zones[0].note_midi_value, 57)
        self.assertEqual(zones[11].note_name, "G#4") # MIDI 68
        self.assertEqual(zones[11].note_midi_value, 68)
        
        # Zone area: width=800, height=300. Row height 150. Zone width 800/6 = 133.33 -> 133
        self.assertEqual(zones[0].rect, (0, 0, 133, 150)) 

    def test_empty_notes_to_display(self):
        """Test behavior when no notes are generated (e.g., num_octaves=0 for chromatic)."""
        mock_config_data = {
            'resolution': [800, 300],
            'starting_note': "C4",
            'num_octaves': 0, # Results in 0 notes for chromatic
            'active_scale': None,
            'zone_labels': True,
            'layout.padding': 10
        }
        mock_cm = self._create_mock_config_manager(mock_config_data)
        with patch('builtins.print') as mock_print: # Suppress warning print
            lg = LayoutGenerator(mock_cm)
            mock_print.assert_any_call("Warning: No notes generated for the layout.")
        
        zones = lg.get_zones()
        self.assertEqual(len(zones), 0)

    def test_invalid_note_in_scale_definition(self):
        """Test that invalid notes in a scale definition are skipped with a warning."""
        scale_notes = ["C4", "InvalidNote", "E4"]
        mock_config_data = {
            'resolution': [800, 300],
            'active_scale': "Test Scale With Invalid",
            'preset_scales': [{'name': "Test Scale With Invalid", 'notes': scale_notes}],
            'zone_labels': True, 'layout.padding': 10
        }
        mock_cm = self._create_mock_config_manager(mock_config_data)
        with patch('builtins.print') as mock_print:
            lg = LayoutGenerator(mock_cm)
            # Check if the warning for "InvalidNote" was printed
            found_warning = any("Warning: Invalid note 'InvalidNote' in scale 'Test Scale With Invalid'" in call_args[0][0]
                                for call_args in mock_print.call_args_list)
            self.assertTrue(found_warning)

        zones = lg.get_zones()
        self.assertEqual(len(zones), 2) # C4 and E4
        self.assertEqual(zones[0].note_name, "C4")
        self.assertEqual(zones[1].note_name, "E4")
        
    def test_regenerate_layout(self):
        """Test that regenerate_layout calls generate_layout again."""
        mock_config_data = {'resolution': [800, 300], 'starting_note': "C4", 'num_octaves': 1}
        mock_cm = self._create_mock_config_manager(mock_config_data)
        lg = LayoutGenerator(mock_cm)
        
        with patch.object(lg, 'generate_layout', wraps=lg.generate_layout) as mock_gen_layout: # Use wraps
            initial_call_count = mock_gen_layout.call_count # Should be 1 from __init__
            lg.regenerate_layout()
            self.assertEqual(mock_gen_layout.call_count, initial_call_count + 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
