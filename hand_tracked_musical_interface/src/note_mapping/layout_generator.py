from .zone import NoteZone
# Assuming ConfigManager is in src.config_manager
# To avoid circular import issues if ConfigManager might ever import layout related things,
# it's often better to pass config values directly or have a central app/context object.
# For now, direct import is fine as per the instructions.
from ..config_manager import ConfigManager
import math

class LayoutGenerator:
    """
    Generates and manages the layout of NoteZone objects based on configuration.
    """

    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the LayoutGenerator.

        Args:
            config_manager (ConfigManager): An instance of the ConfigManager
                                            to access configuration settings.
        """
        if not isinstance(config_manager, ConfigManager):
            raise TypeError("config_manager must be an instance of ConfigManager.")
        self.config_manager = config_manager
        self.zones = []
        self.generate_layout()

    def _get_midi_value(self, note_name: str) -> int:
        """
        Converts a note name (e.g., "C4", "F#5") to its MIDI value.
        Assumes C4 = 60.
        """
        if not isinstance(note_name, str) or len(note_name) < 2:
            raise ValueError(f"Invalid note name format: {note_name}")

        name_part = note_name[:-1].upper()
        try:
            octave_part = int(note_name[-1])
        except ValueError:
            raise ValueError(f"Invalid octave in note name: {note_name}")

        if name_part not in self.NOTE_NAMES:
            # Handle flats by converting to sharps, e.g., Db -> C#
            if len(name_part) > 1 and name_part[1] == 'B':
                original_note_index = self.NOTE_NAMES.index(name_part[0])
                name_part = self.NOTE_NAMES[(original_note_index - 1 + 12) % 12]
            else: # Unknown note
                raise ValueError(f"Invalid note name: {name_part}")
        
        semitone_offset = self.NOTE_NAMES.index(name_part)
        
        # MIDI formula: C4 is MIDI 60. Octave for C in MIDI standard is octave number + 1 based on some conventions.
        # Scientific pitch notation: C4 is middle C.
        # MIDI standard: Middle C (MIDI note 60) is C4.
        # MIDI note = (octave + 1) * 12 + semitone_index_from_C
        # Example: C4 -> (4+1)*12 + 0 = 60
        # A4 -> (4+1)*12 + 9 = 69
        # C5 -> (5+1)*12 + 0 = 72
        midi_value = (octave_part + 1) * 12 + semitone_offset
        return midi_value

    def _get_note_name(self, midi_value: int) -> str:
        """
        Converts a MIDI value to its note name (e.g., 60 to "C4").
        """
        if not isinstance(midi_value, int) or not (0 <= midi_value <= 127):
            raise ValueError("MIDI value must be an integer between 0 and 127.")
        
        octave = (midi_value // 12) - 1
        note_index = midi_value % 12
        note_name = self.NOTE_NAMES[note_index]
        return f"{note_name}{octave}"

    def _generate_chromatic_notes(self, start_midi: int, num_notes: int) -> list[tuple[str, int]]:
        """
        Generates a list of chromatic notes (name, midi_value) starting from a MIDI note.
        """
        notes = []
        for i in range(num_notes):
            current_midi = start_midi + i
            if 0 <= current_midi <= 127:
                notes.append((self._get_note_name(current_midi), current_midi))
        return notes

    def generate_layout(self):
        """
        Generates the NoteZone layout based on current configuration settings.
        Populates self.zones with NoteZone objects.
        """
        self.zones.clear()

        screen_resolution = self.config_manager.get_setting('resolution', [1280, 720])
        screen_width, screen_height = screen_resolution

        starting_note_name = self.config_manager.get_setting('starting_note', "C4")
        num_octaves = self.config_manager.get_setting('num_octaves', 2)
        active_scale_name = self.config_manager.get_setting('active_scale', None)
        preset_scales = self.config_manager.get_setting('preset_scales', [])
        # zone_labels_enabled = self.config_manager.get_setting('zone_labels', True) # For NoteZone label

        notes_to_display = [] # List of (note_name, midi_value)

        start_midi = self._get_midi_value(starting_note_name)

        if active_scale_name:
            scale_found = False
            for scale in preset_scales:
                if scale.get('name') == active_scale_name:
                    # The spec says preset_scales.notes are like ["C4", "D4", ...]
                    # We need to ensure these notes are used correctly, possibly filtering/extending
                    # to match num_octaves and starting_note if the scale is defined generically.
                    # For now, assume the scale definition in config is comprehensive enough for the range.
                    # Or, it's a base scale that needs to be transposed and extended.
                    
                    # Let's assume the preset scale notes are the *exact* notes to be used if they span the desired range.
                    # If not, we might need to generate them based on root and interval pattern over octaves.
                    # The current spec implies preset_scales has "C4", "D4" etc.
                    
                    # For simplicity, if a scale is chosen, we use its notes.
                    # We might need to make sure these notes are within the octave range or adjust.
                    # The current implementation will just use the notes as listed in the scale.
                    # TODO: A more robust scale handling might be needed:
                    # 1. Get base intervals (e.g., [0, 2, 4, 7, 9] for major pentatonic).
                    # 2. Apply from starting_note_name over num_octaves.
                    
                    # Current interpretation: Use notes from config if they are specified with octaves.
                    # This might not perfectly align with `num_octaves` and `starting_note` if the scale
                    # definition is fixed.
                    # A better approach:
                    scale_notes_raw = scale.get('notes', [])
                    for note_str in scale_notes_raw:
                        try:
                            notes_to_display.append((note_str, self._get_midi_value(note_str)))
                        except ValueError as e:
                            print(f"Warning: Invalid note '{note_str}' in scale '{active_scale_name}': {e}")
                    if notes_to_display:
                        scale_found = True
                    break
            if not scale_found:
                print(f"Warning: Active scale '{active_scale_name}' not found in presets. Defaulting to chromatic.")
                notes_to_display = self._generate_chromatic_notes(start_midi, num_octaves * 12)
        else: # No active scale, generate chromatic
            notes_to_display = self._generate_chromatic_notes(start_midi, num_octaves * 12)

        if not notes_to_display:
            print("Warning: No notes generated for the layout.")
            return

        # Arrange notes into zones (e.g., two rows)
        num_notes_total = len(notes_to_display)
        if num_notes_total == 0:
            return

        # Basic two-row layout
        num_rows = 2
        # Ensure at least one note per row if possible
        notes_per_row_ideal = math.ceil(num_notes_total / num_rows)
        
        # Distribute notes more evenly if possible, rather than one row potentially being very short
        row_counts = [0] * num_rows
        for i in range(num_notes_total):
            row_counts[i % num_rows] += 1
        
        notes_in_row1 = row_counts[0]
        # notes_in_row2 = row_counts[1] # if num_rows == 2

        padding = self.config_manager.get_setting('layout.padding', 10) # Example of a new config option
        zone_area_width = screen_width - 2 * padding
        zone_area_height = screen_height - 2 * padding
        
        row_height = zone_area_height / num_rows
        
        current_note_index = 0
        for i_row in range(num_rows):
            notes_in_current_row = row_counts[i_row]
            if notes_in_current_row == 0:
                continue

            zone_width = zone_area_width / notes_in_current_row
            
            for i_col in range(notes_in_current_row):
                if current_note_index >= num_notes_total:
                    break 
                
                note_name, note_midi = notes_to_display[current_note_index]
                
                x = padding + i_col * zone_width
                y = padding + i_row * row_height
                
                # Use note_name as label by default, can be customized by NoteZone
                zone_label = note_name if self.config_manager.get_setting('zone_labels', True) else None

                zone = NoteZone(
                    x=int(x), y=int(y),
                    width=int(zone_width), height=int(row_height),
                    note_name=note_name,
                    note_midi_value=note_midi,
                    label=zone_label
                )
                # Optional: Set custom colors from config
                # zone.base_color = self.config_manager.get_setting('colors.zone_base', (50,50,50))
                # zone.highlight_color = self.config_manager.get_setting('colors.zone_highlight', (0,255,0))
                # zone.current_color = zone.base_color

                self.zones.append(zone)
                current_note_index += 1
        
        # print(f"Generated {len(self.zones)} zones.") # For debugging

    def get_zones(self) -> list[NoteZone]:
        """
        Returns the list of generated NoteZone objects.
        """
        return self.zones

    def regenerate_layout(self):
        """
        Forces a regeneration of the layout. Useful if settings change.
        """
        self.generate_layout()


if __name__ == '__main__':
    # --- Mock ConfigManager and Config File for Testing ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data

        def get_setting(self, key, default=None):
            keys = key.split('.')
            value = self.config
            try:
                for k in keys:
                    if isinstance(value, dict):
                        value = value[k]
                    elif isinstance(value, list) and k.isdigit(): # Handle list index access
                        value = value[int(k)]
                    else:
                        return default
                return value
            except (KeyError, TypeError, IndexError):
                return default

    # Example config data (mimicking config.yaml)
    mock_config_data_chromatic = {
        'resolution': [800, 300], # Smaller for easier console output review
        'starting_note': "C4",
        'num_octaves': 1, # 12 notes
        'active_scale': None,
        'preset_scales': [
            {
                'name': "C Major Pentatonic",
                'notes': ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"]
            }
        ],
        'zone_labels': True,
        'layout.padding': 5
    }

    mock_config_data_scale = {
        'resolution': [1000, 400],
        'starting_note': "C3", # This will be ignored if scale notes are absolute
        'num_octaves': 2,      # This will be ignored if scale notes are absolute
        'active_scale': "C Major Pentatonic",
        'preset_scales': [
            {
                'name': "C Major Pentatonic", # 10 notes
                'notes': ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"]
            }
        ],
        'zone_labels': True,
        'layout.padding': 10
    }
    
    print("--- Testing LayoutGenerator with Chromatic Scale ---")
    config_manager_chromatic = MockConfigManager(mock_config_data_chromatic)
    layout_gen_chromatic = LayoutGenerator(config_manager_chromatic)
    zones_chromatic = layout_gen_chromatic.get_zones()
    
    print(f"Generated {len(zones_chromatic)} chromatic zones.")
    for i, zone in enumerate(zones_chromatic):
        print(f"  Zone {i+1}: {zone.note_name} (MIDI: {zone.note_midi_value}), Rect: {zone.rect}, Label: {zone.label}")
    # Expected: 12 notes from C4 to B4, split into two rows (6 notes each)

    print("\n--- Testing LayoutGenerator with Pentatonic Scale ---")
    config_manager_scale = MockConfigManager(mock_config_data_scale)
    layout_gen_scale = LayoutGenerator(config_manager_scale)
    zones_scale = layout_gen_scale.get_zones()

    print(f"Generated {len(zones_scale)} scale zones.")
    for i, zone in enumerate(zones_scale):
        print(f"  Zone {i+1}: {zone.note_name} (MIDI: {zone.note_midi_value}), Rect: {zone.rect}, Label: {zone.label}")
    # Expected: 10 notes from the "C Major Pentatonic" scale, split into two rows (5 notes each)

    print("\n--- Testing MIDI Conversion Utilities ---")
    lg_test = LayoutGenerator(config_manager_chromatic) # Dummy for testing helpers
    test_notes = {
        "C4": 60, "C#4": 61, "Db4": 61, "A4": 69, "C5": 72, "B3": 59, "G#7": 104
    }
    for name, midi in test_notes.items():
        assert lg_test._get_midi_value(name) == midi, f"MIDI for {name} failed"
        assert lg_test._get_note_name(midi) == name.replace("Db", "C#"), f"Name for {midi} failed" # Assuming C# preference
    print("MIDI conversions appear correct.")
    
    # Test edge case for MIDI conversion (e.g. B#3 -> C4) - current doesn't handle this directly
    # but it's not standard notation usually input.
    # print(f"MIDI for B#3: {lg_test._get_midi_value('B#3')}") # Expect C4 = 60

    print("\n--- Testing with an unknown scale (should default to chromatic) ---")
    mock_config_data_unknown_scale = mock_config_data_chromatic.copy()
    mock_config_data_unknown_scale['active_scale'] = "Unknown Scale"
    mock_config_data_unknown_scale['starting_note'] = "A3" # Change starting note
    mock_config_data_unknown_scale['num_octaves'] = 1 # 12 notes

    config_manager_unknown_scale = MockConfigManager(mock_config_data_unknown_scale)
    layout_gen_unknown = LayoutGenerator(config_manager_unknown_scale)
    zones_unknown = layout_gen_unknown.get_zones()
    print(f"Generated {len(zones_unknown)} zones for unknown scale (should be 12 chromatic from A3).")
    for i, zone in enumerate(zones_unknown):
        print(f"  Zone {i+1}: {zone.note_name} (MIDI: {zone.note_midi_value}), Rect: {zone.rect}")
    # Expected: 12 notes from A3 to G#4

```
