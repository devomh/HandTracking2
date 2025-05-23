import unittest
from unittest.mock import MagicMock, patch

# Ensure src is discoverable
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.note_mapping.interaction_logic import InteractionManager, FINGER_TIP_LANDMARKS, LANDMARK_ID_TO_FINGER_NAME
from src.note_mapping.zone import NoteZone
from src.config_manager import ConfigManager
from src.note_mapping.layout_generator import LayoutGenerator
from src.audio_output.audio_engine import AudioEngine
from src.expression_control.pitch_bend_processor import PitchBendProcessor
from src.expression_control.velocity_intensity_processor import VelocityIntensityProcessor


class TestInteractionManager(unittest.TestCase):

    def _create_mock_config_manager(self, use_all_fingers=True, allowed_fingers=['INDEX']):
        mock_cm = MagicMock(spec=ConfigManager)
        def get_setting_side_effect(key, default=None):
            if key == 'use_all_fingers':
                return use_all_fingers
            if key == 'allowed_fingers':
                return allowed_fingers
            return default
        mock_cm.get_setting.side_effect = get_setting_side_effect
        return mock_cm

    def setUp(self):
        self.mock_config_manager = self._create_mock_config_manager()
        self.mock_layout_generator = MagicMock(spec=LayoutGenerator) # Not used directly by IM's methods
        self.mock_audio_engine = MagicMock(spec=AudioEngine)
        self.mock_pitch_bend_processor = MagicMock(spec=PitchBendProcessor)
        self.mock_velocity_intensity_processor = MagicMock(spec=VelocityIntensityProcessor)

        self.interaction_mgr = InteractionManager(
            config_manager=self.mock_config_manager,
            layout_generator=self.mock_layout_generator,
            audio_engine=self.mock_audio_engine,
            pitch_bend_processor=self.mock_pitch_bend_processor,
            velocity_intensity_processor=self.mock_velocity_intensity_processor
        )

        # Mock zones for testing
        self.zone1 = MagicMock(spec=NoteZone)
        self.zone1.rect = (0, 0, 100, 100)
        self.zone1.note_name = "C4"
        self.zone1.note_midi_value = 60
        self.zone1.is_active = False
        self.zone1.active_finger_id = None
        self.zone1.is_point_inside.return_value = False # Default to not inside

        self.zone2 = MagicMock(spec=NoteZone)
        self.zone2.rect = (100, 0, 100, 100)
        self.zone2.note_name = "D4"
        self.zone2.note_midi_value = 62
        self.zone2.is_active = False
        self.zone2.active_finger_id = None
        self.zone2.is_point_inside.return_value = False

        self.zones = [self.zone1, self.zone2]
        
        # Reset mocks for audio engine methods before each test
        self.mock_audio_engine.note_on.reset_mock()
        self.mock_audio_engine.note_off.reset_mock()
        self.mock_audio_engine.pitch_bend.reset_mock()
        self.mock_audio_engine.intensity_update.reset_mock()


    def test_initialization_use_all_fingers_true(self):
        """Test initialization when use_all_fingers is True."""
        self.assertEqual(self.interaction_mgr.target_fingers, set(FINGER_TIP_LANDMARKS.values()))

    def test_initialization_use_all_fingers_false_specific_fingers(self):
        """Test initialization with specific allowed fingers."""
        mock_cm_specific = self._create_mock_config_manager(use_all_fingers=False, allowed_fingers=['INDEX', 'MIDDLE'])
        im_specific = InteractionManager(
            mock_cm_specific, self.mock_layout_generator, self.mock_audio_engine,
            self.mock_pitch_bend_processor, self.mock_velocity_intensity_processor
        )
        expected_fingers = {FINGER_TIP_LANDMARKS['INDEX'], FINGER_TIP_LANDMARKS['MIDDLE']}
        self.assertEqual(im_specific.target_fingers, expected_fingers)

    @patch('builtins.print') # Suppress warning print
    def test_initialization_use_all_fingers_false_invalid_config(self, mock_print):
        """Test fallback if allowed_fingers is empty/invalid when use_all_fingers is False."""
        mock_cm_invalid = self._create_mock_config_manager(use_all_fingers=False, allowed_fingers=['INVALID_FINGER'])
        im_invalid = InteractionManager(
            mock_cm_invalid, self.mock_layout_generator, self.mock_audio_engine,
            self.mock_pitch_bend_processor, self.mock_velocity_intensity_processor
        )
        self.assertEqual(im_invalid.target_fingers, {FINGER_TIP_LANDMARKS['INDEX']}) # Defaults to INDEX
        mock_print.assert_any_call("Warning: 'use_all_fingers' is false but 'allowed_fingers' is empty or invalid. Defaulting to INDEX finger.")


    def test_get_finger_tip_coordinate(self):
        """Test retrieving finger tip coordinates from landmarks list."""
        landmarks = [
            (0, 10, 10, 0), (FINGER_TIP_LANDMARKS['INDEX'], 50, 55, 5), (10, 1,1,1)
        ]
        coord = self.interaction_mgr._get_finger_tip_coordinate(landmarks, FINGER_TIP_LANDMARKS['INDEX'])
        self.assertEqual(coord, (50, 55, 5))
        
        coord_missing = self.interaction_mgr._get_finger_tip_coordinate(landmarks, FINGER_TIP_LANDMARKS['THUMB'])
        self.assertIsNone(coord_missing)
        
        coord_out_of_bounds = self.interaction_mgr._get_finger_tip_coordinate(landmarks, 99) # id 99 not in list
        self.assertIsNone(coord_out_of_bounds) # Should also handle this gracefully if landmark list is shorter


    def test_process_hands_data_new_note_on(self):
        """Test a new note being triggered."""
        self.zone1.is_point_inside.return_value = True # Finger is in zone1
        self.mock_velocity_intensity_processor.calculate_initial_velocity.return_value = 100 # Mock velocity
        
        finger_x, finger_y = 50, 50
        hand_id = 'Right'
        finger_tip_id = FINGER_TIP_LANDMARKS['INDEX']
        finger_identifier = (hand_id, finger_tip_id)

        hands_data = [{
            'handedness': hand_id,
            'finger_states': {'INDEX': 'extended'},
            'landmarks': [(finger_tip_id, finger_x, finger_y, 0)]
        }]
        
        self.interaction_mgr.process_hands_data(hands_data, self.zones)
        
        self.mock_velocity_intensity_processor.calculate_initial_velocity.assert_called_once_with(finger_y, self.zone1.rect)
        self.mock_audio_engine.note_on.assert_called_once_with(self.zone1.note_midi_value, 100, finger_identifier)
        self.zone1.activate.assert_called_once_with(finger_identifier)
        self.assertIn(finger_identifier, self.interaction_mgr.active_notes)
        self.assertEqual(self.interaction_mgr.active_notes[finger_identifier]['zone'], self.zone1)
        self.assertEqual(self.interaction_mgr.active_notes[finger_identifier]['midi_note'], self.zone1.note_midi_value)

    def test_process_hands_data_note_sustain_and_modulation(self):
        """Test sustaining a note with modulation."""
        finger_x, finger_y = 60, 60 # New position for modulation
        hand_id = 'Right'
        finger_tip_id = FINGER_TIP_LANDMARKS['INDEX']
        finger_identifier = (hand_id, finger_tip_id)

        # Setup active note
        self.interaction_mgr.active_notes[finger_identifier] = {
            'zone': self.zone1, 'initial_y': 50, 'midi_note': self.zone1.note_midi_value
        }
        self.zone1.is_active = True # Zone is already active
        self.zone1.active_finger_id = finger_identifier
        self.zone1.is_point_inside.return_value = True # Finger still in zone1
        
        self.mock_pitch_bend_processor.calculate_pitch_bend.return_value = 1024
        self.mock_velocity_intensity_processor.calculate_continuous_intensity.return_value = 80

        hands_data = [{
            'handedness': hand_id,
            'finger_states': {'INDEX': 'extended'},
            'landmarks': [(finger_tip_id, finger_x, finger_y, 0)]
        }]
        
        self.interaction_mgr.process_hands_data(hands_data, self.zones)

        self.mock_audio_engine.note_on.assert_not_called() # No new note on
        self.mock_pitch_bend_processor.calculate_pitch_bend.assert_called_once_with(finger_x, self.zone1.rect)
        self.mock_audio_engine.pitch_bend.assert_called_once_with(1024, finger_identifier)
        self.mock_velocity_intensity_processor.calculate_continuous_intensity.assert_called_once_with(finger_y, self.zone1.rect)
        self.mock_audio_engine.intensity_update.assert_called_once_with(80, finger_identifier, self.zone1.note_midi_value)


    def test_process_hands_data_note_off_finger_leaves_zone(self):
        """Test note off when finger leaves the zone."""
        hand_id = 'Right'
        finger_tip_id = FINGER_TIP_LANDMARKS['INDEX']
        finger_identifier = (hand_id, finger_tip_id)

        self.interaction_mgr.active_notes[finger_identifier] = {
            'zone': self.zone1, 'initial_y': 50, 'midi_note': self.zone1.note_midi_value
        }
        self.zone1.is_active = True
        self.zone1.active_finger_id = finger_identifier
        self.zone1.is_point_inside.return_value = False # Crucial: finger is now outside

        hands_data = [{
            'handedness': hand_id,
            'finger_states': {'INDEX': 'extended'}, # Finger still extended
            'landmarks': [(finger_tip_id, 200, 50, 0)] # Coords don't matter as much as is_point_inside mock
        }]
        
        self.interaction_mgr.process_hands_data(hands_data, self.zones)
        
        self.mock_audio_engine.note_off.assert_called_once_with(self.zone1.note_midi_value, finger_identifier)
        self.zone1.deactivate.assert_called_once()
        self.assertNotIn(finger_identifier, self.interaction_mgr.active_notes)

    def test_process_hands_data_note_off_finger_retracted(self):
        """Test note off when finger is retracted."""
        hand_id = 'Right'
        finger_tip_id = FINGER_TIP_LANDMARKS['INDEX']
        finger_identifier = (hand_id, finger_tip_id)

        self.interaction_mgr.active_notes[finger_identifier] = {
            'zone': self.zone1, 'initial_y': 50, 'midi_note': self.zone1.note_midi_value
        }
        self.zone1.is_active = True
        self.zone1.is_point_inside.return_value = True # Finger still in zone

        hands_data = [{
            'handedness': hand_id,
            'finger_states': {'INDEX': 'retracted'}, # Finger is retracted
            'landmarks': [(finger_tip_id, 50, 50, 0)] 
        }]
        
        self.interaction_mgr.process_hands_data(hands_data, self.zones)
        
        self.mock_audio_engine.note_off.assert_called_once_with(self.zone1.note_midi_value, finger_identifier)
        self.zone1.deactivate.assert_called_once()
        self.assertNotIn(finger_identifier, self.interaction_mgr.active_notes)

    def test_process_hands_data_note_off_hand_disappears(self):
        """Test note off when the hand disappears."""
        hand_id = 'Right'
        finger_tip_id = FINGER_TIP_LANDMARKS['INDEX']
        finger_identifier = (hand_id, finger_tip_id)
        
        self.interaction_mgr.active_notes[finger_identifier] = {
            'zone': self.zone1, 'initial_y': 50, 'midi_note': self.zone1.note_midi_value
        }
        self.zone1.is_active = True
        
        hands_data_empty = [] # No hands detected
        self.interaction_mgr.process_hands_data(hands_data_empty, self.zones)
        
        self.mock_audio_engine.note_off.assert_called_once_with(self.zone1.note_midi_value, finger_identifier)
        self.zone1.deactivate.assert_called_once()
        self.assertNotIn(finger_identifier, self.interaction_mgr.active_notes)

    def test_cleanup_stale_notes(self):
        """Test cleanup_stale_notes when no hands are detected."""
        fid1 = ('Right', FINGER_TIP_LANDMARKS['INDEX'])
        fid2 = ('Left', FINGER_TIP_LANDMARKS['MIDDLE'])
        self.interaction_mgr.active_notes = {
            fid1: {'zone': self.zone1, 'midi_note': self.zone1.note_midi_value},
            fid2: {'zone': self.zone2, 'midi_note': self.zone2.note_midi_value}
        }
        self.zone1.is_active = True # Simulate active state for deactivate call
        self.zone2.is_active = True

        self.interaction_mgr.cleanup_stale_notes()

        self.mock_audio_engine.note_off.assert_any_call(self.zone1.note_midi_value, fid1)
        self.mock_audio_engine.note_off.assert_any_call(self.zone2.note_midi_value, fid2)
        self.assertEqual(self.mock_audio_engine.note_off.call_count, 2)
        self.zone1.deactivate.assert_called_once()
        self.zone2.deactivate.assert_called_once()
        self.assertEqual(len(self.interaction_mgr.active_notes), 0)

    def test_zone_already_active_by_another_finger(self):
        """Test that a finger cannot activate a zone already active by another finger."""
        active_finger_identifier = ('Right', FINGER_TIP_LANDMARKS['INDEX'])
        self.zone1.is_active = True
        self.zone1.active_finger_id = active_finger_identifier
        self.zone1.is_point_inside.return_value = True # Both fingers attempt to be in zone1

        new_finger_id = 'Right'
        new_finger_tip_id = FINGER_TIP_LANDMARKS['MIDDLE'] # Different finger
        new_finger_identifier = (new_finger_id, new_finger_tip_id)
        
        hands_data = [{
            'handedness': new_finger_id,
            'finger_states': {'MIDDLE': 'extended'},
            'landmarks': [(new_finger_tip_id, 50, 50, 0)]
        }]
        
        self.interaction_mgr.process_hands_data(hands_data, self.zones)
        
        # No new note_on should be called for the new finger in the already active zone
        self.mock_audio_engine.note_on.assert_not_called() 
        self.assertNotIn(new_finger_identifier, self.interaction_mgr.active_notes)
        # Ensure the original activate call on zone1 (if any in setup) is the only one
        self.zone1.activate.assert_not_called() # No new activation


if __name__ == '__main__':
    unittest.main(verbosity=2)
```
