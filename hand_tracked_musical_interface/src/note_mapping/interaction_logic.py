from .zone import NoteZone
from .layout_generator import LayoutGenerator
# HandDetector is not directly imported, its output 'hands_data' is passed in.
from ...expression_control.pitch_bend_processor import PitchBendProcessor
from ...expression_control.velocity_intensity_processor import VelocityIntensityProcessor
from ...audio_output.audio_engine import AudioEngine
from ...config_manager import ConfigManager # Assuming ConfigManager is in src.config_manager

# Mapping from finger name (as in HandDetector's finger_states) to its TIP landmark ID.
# These are standard MediaPipe landmark IDs.
FINGER_TIP_LANDMARKS = {
    'THUMB': 4,
    'INDEX': 8,
    'MIDDLE': 12,
    'RING': 16,
    'PINKY': 20
}
# And the reverse for convenience if needed, though less likely here.
LANDMARK_ID_TO_FINGER_NAME = {v: k for k, v in FINGER_TIP_LANDMARKS.items()}


class InteractionManager:
    """
    Manages the interaction logic between hand tracking data and musical note activation/modulation.
    """

    def __init__(self,
                 config_manager: ConfigManager,
                 layout_generator: LayoutGenerator,
                 audio_engine: AudioEngine,
                 pitch_bend_processor: PitchBendProcessor,
                 velocity_intensity_processor: VelocityIntensityProcessor):
        """
        Initializes the InteractionManager.

        Args:
            config_manager: Instance of ConfigManager.
            layout_generator: Instance of LayoutGenerator.
            audio_engine: Instance of AudioEngine.
            pitch_bend_processor: Instance of PitchBendProcessor.
            velocity_intensity_processor: Instance of VelocityIntensityProcessor.
        """
        self.config_manager = config_manager
        self.layout_generator = layout_generator # Though zones are passed to process_hands_data
        self.audio_engine = audio_engine
        self.pitch_bend_processor = pitch_bend_processor
        self.velocity_intensity_processor = velocity_intensity_processor

        # Active notes: {(hand_id, finger_tip_landmark_id): {'zone': NoteZone, 'initial_y': float, 'midi_note': int}}
        # hand_id can be 0/1 (from detector) or 'Left'/'Right'. Using handedness string for clarity if available.
        self.active_notes = {}

        self.use_all_fingers = self.config_manager.get_setting('use_all_fingers', True)
        self.target_fingers = set() # Set of finger tip landmark IDs to process if not use_all_fingers
        if not self.use_all_fingers:
            # Example: Only use index fingers if use_all_fingers is false.
            # This needs a more specific config setting, e.g., 'allowed_fingers': ['INDEX', 'MIDDLE']
            # For now, if not use_all_fingers, let's default to INDEX finger only.
            allowed_finger_names = self.config_manager.get_setting('allowed_fingers', ['INDEX'])
            for name in allowed_finger_names:
                if name.upper() in FINGER_TIP_LANDMARKS:
                    self.target_fingers.add(FINGER_TIP_LANDMARKS[name.upper()])
            if not self.target_fingers: # Fallback if config is weird
                 print("Warning: 'use_all_fingers' is false but 'allowed_fingers' is empty or invalid. Defaulting to INDEX finger.")
                 self.target_fingers.add(FINGER_TIP_LANDMARKS['INDEX'])
            print(f"InteractionManager: Using specific fingers: {self.target_fingers}")
        else:
            print("InteractionManager: Using all detected fingers.")
            # All finger tips are potential candidates
            self.target_fingers = set(FINGER_TIP_LANDMARKS.values())


    def _get_finger_tip_coordinate(self, hand_landmarks: list, finger_tip_id: int) -> tuple[int, int, int] | None:
        """
        Retrieves the (x, y, z) coordinate for a specific finger tip landmark ID from a hand's landmark list.
        The landmark list is 0-indexed by landmark ID.
        """
        if finger_tip_id < len(hand_landmarks):
            # hand_landmarks contains (lm_id, x, y, z) tuples
            lm_data = next((lm for lm in hand_landmarks if lm[0] == finger_tip_id), None)
            if lm_data:
                return lm_data[1], lm_data[2], lm_data[3] # x, y, z
        return None

    def process_hands_data(self, hands_data: list, zones: list[NoteZone]):
        """
        Main update method to process hand data and trigger/update musical interactions.

        Args:
            hands_data: List of hand information dictionaries from HandDetector.
                        Each dict: {'landmarks': list_of_tuples, 'handedness': str, 
                                    'finger_states': dict, 'bounding_box': tuple, 'mp_landmarks': ...}
            zones: List of NoteZone objects from LayoutGenerator.
        """
        processed_finger_identifiers = set()
        notes_to_remove = set() # Set of finger_identifiers to remove from self.active_notes

        # --- 1. Process existing active notes (check for sustain, modulation, or note-off) ---
        for finger_identifier, note_data in list(self.active_notes.items()): # list() for safe removal later if needed
            hand_id_of_active_note, finger_tip_id_of_active_note = finger_identifier
            note_zone = note_data['zone']
            
            found_finger_in_current_frame = False
            finger_still_valid_for_note = False

            for hand in hands_data:
                # Determine hand_id for matching: could be index (0,1) or handedness ('Left'/'Right')
                # Assuming hand_id_of_active_note matches the way we generate it below (e.g. hand['handedness'])
                current_hand_id = hand['handedness'] # Or an index if preferred
                
                if current_hand_id == hand_id_of_active_note: # Found the correct hand
                    found_finger_in_current_frame = True # Hand is present
                    
                    # Check finger state (e.g., 'INDEX': 'extended')
                    finger_name = LANDMARK_ID_TO_FINGER_NAME.get(finger_tip_id_of_active_note)
                    if not finger_name or hand['finger_states'].get(finger_name) != 'extended':
                        finger_still_valid_for_note = False # Finger retracted
                        break 

                    # Get finger tip coordinates
                    coords = self._get_finger_tip_coordinate(hand['landmarks'], finger_tip_id_of_active_note)
                    if not coords:
                        finger_still_valid_for_note = False # Landmark data missing
                        break
                    
                    finger_x, finger_y, _ = coords

                    if not note_zone.is_point_inside(finger_x, finger_y):
                        finger_still_valid_for_note = False # Finger left the original zone
                        break
                    
                    # If we reach here, finger is still extended and inside its original zone
                    finger_still_valid_for_note = True

                    # --- Modulation ---
                    # Pitch Bend (X-axis)
                    bend_value = self.pitch_bend_processor.calculate_pitch_bend(finger_x, note_zone.rect)
                    self.audio_engine.pitch_bend(bend_value, finger_identifier)

                    # Continuous Intensity (Y-axis)
                    # The spec implies Y is used for initial velocity. For continuous control,
                    # it could be Y relative to initial Y, or absolute Y in zone.
                    # Using absolute Y in zone for continuous intensity, like for velocity.
                    intensity_value = self.velocity_intensity_processor.calculate_continuous_intensity(finger_y, note_zone.rect)
                    self.audio_engine.intensity_update(intensity_value, finger_identifier, note_data['midi_note'])
                    
                    processed_finger_identifiers.add(finger_identifier) # Mark as processed
                    break # Found and processed this active finger, move to next active_note

            if not found_finger_in_current_frame or not finger_still_valid_for_note:
                # Hand disappeared, or finger retracted, or finger left zone
                self.audio_engine.note_off(note_data['midi_note'], finger_identifier)
                note_zone.deactivate() # This assumes zone is tied to one finger.
                                       # For "last finger leaves", deactivate logic would be in zone itself based on its active_fingers set.
                notes_to_remove.add(finger_identifier)

        # Remove notes marked for cleanup
        for fid in notes_to_remove:
            if fid in self.active_notes:
                del self.active_notes[fid]

        # --- 2. Process new potential note triggers from current hand data ---
        for hand_idx, hand in enumerate(hands_data):
            hand_id = hand['handedness'] # Using handedness as part of the unique finger ID
            # If handedness can be 'Unknown', use hand_idx as fallback
            if hand_id == "Unknown": hand_id = f"hand_{hand_idx}"


            for finger_name, finger_tip_landmark_id in FINGER_TIP_LANDMARKS.items():
                if finger_tip_landmark_id not in self.target_fingers: # Filter by target_fingers
                    continue

                finger_identifier = (hand_id, finger_tip_landmark_id)

                if finger_identifier in processed_finger_identifiers: # Already processed as an existing note
                    continue
                if finger_identifier in self.active_notes: # Should have been processed or removed
                    continue 

                # Check if this finger is extended
                if hand['finger_states'].get(finger_name) == 'extended':
                    coords = self._get_finger_tip_coordinate(hand['landmarks'], finger_tip_landmark_id)
                    if not coords:
                        continue
                    
                    finger_tip_x, finger_tip_y, _ = coords

                    for zone in zones:
                        if zone.is_point_inside(finger_tip_x, finger_tip_y):
                            if not zone.is_active: # Zone available for new note
                                # --- New Note On ---
                                velocity = self.velocity_intensity_processor.calculate_initial_velocity(finger_tip_y, zone.rect)
                                self.audio_engine.note_on(zone.note_midi_value, velocity, finger_identifier)
                                
                                zone.activate(finger_identifier) # Simple activation: zone is now tied to this finger
                                
                                self.active_notes[finger_identifier] = {
                                    'zone': zone,
                                    'initial_y': finger_tip_y, # Store initial Y if needed for relative modulation later
                                    'midi_note': zone.note_midi_value
                                }
                                processed_finger_identifiers.add(finger_identifier) # Mark as processed for this frame
                                break # This finger has triggered a note, move to next finger
                            else:
                                # Zone is already active.
                                # Current simple model: only one finger controls a zone's note.
                                # If zone.active_finger_id == finger_identifier, it would be a sustain (handled above).
                                # If zone.active_finger_id is different, this finger cannot currently take over this zone.
                                # For "last finger leaves" & multiple fingers in one zone spec:
                                #   - NoteZone would need `zone.activating_finger_ids.add(finger_identifier)`
                                #   - Note On only if it was the first finger in the set.
                                #   - `self.active_notes` would still store this finger's interaction.
                                # This part would need rework of NoteZone and here for that specific behavior.
                                # For now, an active zone cannot be re-triggered by another finger.
                                pass 
                                break # Finger is in an active zone, but can't trigger it. Stop checking other zones for this finger.

    def cleanup_stale_notes(self):
        """
        Optional: Can be called if hands_data is empty (no hands detected) to ensure all notes are turned off.
        """
        if not self.active_notes:
            return
        
        print("No hands detected, cleaning up all active notes.")
        for finger_identifier, note_data in list(self.active_notes.items()):
            self.audio_engine.note_off(note_data['midi_note'], finger_identifier)
            note_data['zone'].deactivate()
        self.active_notes.clear()

if __name__ == '__main__':
    # --- Mock Classes for Testing InteractionManager ---
    class MockConfigManager:
        def __init__(self, config_data): self.config = config_data
        def get_setting(self, key, default=None): return self.config.get(key, default)

    class MockLayoutGenerator:
        def __init__(self, zones): self.zones = zones
        def get_zones(self): return self.zones

    class MockAudioEngine:
        def __init__(self): self.log = []
        def note_on(self, note, vel, fid): self.log.append(f"ON: {note} (v{vel}) by {fid}")
        def note_off(self, note, fid): self.log.append(f"OFF: {note} by {fid}")
        def pitch_bend(self, bend, fid): self.log.append(f"BEND: {bend} by {fid}")
        def intensity_update(self, intensity, fid, note): self.log.append(f"INTENSITY: {intensity} for {note} by {fid}")
        def shutdown(self): self.log.append("Shutdown")
        def clear_log(self): self.log.clear()

    class MockPitchBendProcessor:
        def calculate_pitch_bend(self, x, rect): return int((x - (rect[0] + rect[2]/2)) / (rect[2]/2) * 1000) # Simple -1000 to 1000

    class MockVelocityIntensityProcessor:
        def calculate_initial_velocity(self, y, rect): return int((y - rect[1]) / rect[3] * 127)
        def calculate_continuous_intensity(self, y, rect): return int((y - rect[1]) / rect[3] * 127)

    # --- Test Setup ---
    config_data = {'use_all_fingers': True, 'allowed_fingers': ['INDEX']} # allow_fingers used if use_all_fingers=false
    mock_config = MockConfigManager(config_data)

    # Create mock zones
    zone1 = NoteZone(0, 0, 100, 100, "C4", 60)
    zone2 = NoteZone(100, 0, 100, 100, "D4", 62)
    zones = [zone1, zone2]
    mock_layout = MockLayoutGenerator(zones)

    mock_audio = MockAudioEngine()
    mock_pb_proc = MockPitchBendProcessor()
    mock_vi_proc = MockVelocityIntensityProcessor()

    interaction_mgr = InteractionManager(mock_config, mock_layout, mock_audio, mock_pb_proc, mock_vi_proc)
    print("--- InteractionManager Test ---")

    # --- Test Case 1: Finger enters zone (Note On) ---
    print("\nTest Case 1: Index Finger enters Zone 1")
    hands_data_1 = [{
        'handedness': 'Right',
        'finger_states': {'INDEX': 'extended', 'THUMB': 'retracted'},
        'landmarks': [ # Simplified: only relevant landmarks
            (FINGER_TIP_LANDMARKS['INDEX'], 50, 50, 0), # Index tip in zone1 center
            (FINGER_TIP_LANDMARKS['THUMB'], 10, 10, 0) 
        ]
    }]
    interaction_mgr.process_hands_data(hands_data_1, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    # Expected: Note On for C4 (60), zone1 active, active_notes updated
    assert any("ON: 60" in s for s in mock_audio.log)
    assert zone1.is_active
    assert (('Right', FINGER_TIP_LANDMARKS['INDEX'])) in interaction_mgr.active_notes
    mock_audio.clear_log()

    # --- Test Case 2: Finger moves within zone (Modulation) ---
    print("\nTest Case 2: Index Finger moves in Zone 1 (Pitch Bend right, Intensity down)")
    hands_data_2 = [{
        'handedness': 'Right',
        'finger_states': {'INDEX': 'extended'},
        'landmarks': [(FINGER_TIP_LANDMARKS['INDEX'], 75, 75, 0)] # Index tip moved right and down
    }]
    interaction_mgr.process_hands_data(hands_data_2, zones)
    print("Audio Log:", mock_audio.log)
    # Expected: Pitch Bend, Intensity update
    assert any("BEND: 500" in s for s in mock_audio.log) # 75 is 0.25 from center (50), (75-50)/(100/2)*1000 = 500
    assert any("INTENSITY: 95" in s for s in mock_audio.log) # 75/100 * 127 = 95.25
    mock_audio.clear_log()

    # --- Test Case 3: Finger leaves zone (Note Off) ---
    print("\nTest Case 3: Index Finger leaves Zone 1")
    hands_data_3 = [{
        'handedness': 'Right',
        'finger_states': {'INDEX': 'extended'},
        'landmarks': [(FINGER_TIP_LANDMARKS['INDEX'], 150, 50, 0)] # Index tip now in zone2 (or outside)
    }]
    interaction_mgr.process_hands_data(hands_data_3, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    # Expected: Note Off for C4 (60), zone1 inactive, active_notes empty for this finger
    #           Potentially Note On for D4 (62) if it landed in zone2
    assert any("OFF: 60" in s for s in mock_audio.log)
    assert not zone1.is_active 
    # Check if it triggered zone2
    if zone2.is_active:
        assert any("ON: 62" in s for s in mock_audio.log)
        assert (('Right', FINGER_TIP_LANDMARKS['INDEX'])) in interaction_mgr.active_notes
        print("Note: Finger also landed in Zone 2 and triggered it.")
    else:
        assert (('Right', FINGER_TIP_LANDMARKS['INDEX'])) not in interaction_mgr.active_notes

    mock_audio.clear_log()
    # Reset zone2 if it became active
    if zone2.is_active: zone2.deactivate()
    interaction_mgr.active_notes.clear()


    # --- Test Case 4: Finger retracts (Note Off) ---
    print("\nTest Case 4: Index Finger retracts in Zone 1")
    # First, put finger back in zone1
    interaction_mgr.process_hands_data(hands_data_1, zones) # Note On C4
    mock_audio.clear_log()
    
    hands_data_4 = [{
        'handedness': 'Right',
        'finger_states': {'INDEX': 'retracted'}, # Finger retracted
        'landmarks': [(FINGER_TIP_LANDMARKS['INDEX'], 50, 50, 0)] # Position doesn't matter as much as state
    }]
    interaction_mgr.process_hands_data(hands_data_4, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    # Expected: Note Off for C4 (60)
    assert any("OFF: 60" in s for s in mock_audio.log)
    assert not zone1.is_active
    assert not interaction_mgr.active_notes
    mock_audio.clear_log()

    # --- Test Case 5: Hand disappears (Note Off) ---
    print("\nTest Case 5: Hand disappears")
    # First, activate a note
    interaction_mgr.process_hands_data(hands_data_1, zones) # Note On C4
    mock_audio.clear_log()

    hands_data_5 = [] # No hands detected
    interaction_mgr.process_hands_data(hands_data_5, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    # Expected: Note Off for C4 (60)
    assert any("OFF: 60" in s for s in mock_audio.log)
    assert not zone1.is_active
    assert not interaction_mgr.active_notes
    mock_audio.clear_log()

    # --- Test Case 6: Two fingers, two zones ---
    print("\nTest Case 6: Two fingers, two zones")
    hands_data_6 = [{ # Right hand
        'handedness': 'Right',
        'finger_states': {'INDEX': 'extended', 'MIDDLE': 'extended'},
        'landmarks': [
            (FINGER_TIP_LANDMARKS['INDEX'], 50, 50, 0),  # Index in zone1
            (FINGER_TIP_LANDMARKS['MIDDLE'], 150, 50, 0) # Middle in zone2
        ]
    }]
    interaction_mgr.process_hands_data(hands_data_6, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    assert any("ON: 60" in s for s in mock_audio.log) # C4 by Right Index
    assert any("ON: 62" in s for s in mock_audio.log) # D4 by Right Middle
    assert zone1.is_active and zone2.is_active
    assert len(interaction_mgr.active_notes) == 2
    mock_audio.clear_log()
    
    # --- Test Case 7: One finger leaves, other sustains ---
    print("\nTest Case 7: Index leaves, Middle sustains")
    hands_data_7 = [{ # Right hand
        'handedness': 'Right',
        'finger_states': {'INDEX': 'retracted', 'MIDDLE': 'extended'}, # Index retracted
        'landmarks': [
            (FINGER_TIP_LANDMARKS['INDEX'], 50, 50, 0),
            (FINGER_TIP_LANDMARKS['MIDDLE'], 150, 70, 0) # Middle moved a bit (intensity change)
        ]
    }]
    interaction_mgr.process_hands_data(hands_data_7, zones)
    print("Audio Log:", mock_audio.log)
    print("Active Notes:", interaction_mgr.active_notes)
    assert any("OFF: 60" in s for s in mock_audio.log) # C4 off
    assert any("INTENSITY: 88" in s for s in mock_audio.log) # Middle finger intensity update (70/100 * 127)
    assert not zone1.is_active and zone2.is_active
    assert len(interaction_mgr.active_notes) == 1
    assert (('Right', FINGER_TIP_LANDMARKS['MIDDLE'])) in interaction_mgr.active_notes
    
    interaction_mgr.cleanup_stale_notes() # Clear remaining notes
    mock_audio.clear_log()
    print("\n--- InteractionManager Test Complete ---")

```
