# Assuming ConfigManager is in src.config_manager
# from ..config_manager import ConfigManager # Use this if part of a package

class PitchBendProcessor:
    """
    Calculates MIDI pitch bend values based on horizontal finger position within a note zone.
    """

    def __init__(self, config_manager): # Type hint later: config_manager: ConfigManager
        """
        Initializes the PitchBendProcessor.

        Args:
            config_manager: An instance of the ConfigManager to access configuration settings.
        """
        self.config_manager = config_manager
        
        # Retrieve pitch bend range in semitones from config.
        # This value is mostly for user context or advanced synth control;
        # standard MIDI pitch bend messages send a value from -8192 to 8191,
        # and the synth interprets this based on its own pitch bend range setting.
        self.pitch_bend_range_semitones = self.config_manager.get_setting('pitch_bend_range', 1.0) # Default to 1 semitone
        
        # Standard MIDI pitch bend range (14-bit value)
        self.midi_bend_max_abs_value = 8191 # Max positive value, negative is -8192, but often symmetric for mapping.
                                           # Using 8191 for symmetrical mapping around 0.

    def _map_value(self, value, from_low, from_high, to_low, to_high):
        """
        Linearly maps a value from one range to another.
        Helper function to keep calculations clean.
        """
        # Avoid division by zero if from_low == from_high
        if from_low == from_high:
            return to_low # Or (to_low + to_high) / 2, or error, depending on desired behavior
        
        # Calculate the percentage of value in the from_range
        percentage = (value - from_low) / (from_high - from_low)
        
        # Apply that percentage to the to_range
        mapped_value = to_low + percentage * (to_high - to_low)
        return mapped_value

    def calculate_pitch_bend(self, finger_x_position: float, zone_rect: tuple[int, int, int, int]) -> int:
        """
        Calculates the MIDI pitch bend value based on the finger's horizontal position
        within a note zone.

        Args:
            finger_x_position (float): The current X-coordinate of the finger.
            zone_rect (tuple): The rectangle (x, y, width, height) of the note zone
                               the finger is in.

        Returns:
            int: The calculated MIDI pitch bend value (between -8191 and 8191, typically).
                 0 means no bend (center of the zone).
        """
        zone_x, _zone_y, zone_width, _zone_height = zone_rect

        if zone_width == 0: # Avoid division by zero
            return 0 

        # Calculate the relative position of the finger within the zone's width.
        # 0.0 at the left edge, 0.5 at the center, 1.0 at the right edge.
        relative_pos_x = (finger_x_position - zone_x) / zone_width
        
        # Clamp relative_pos_x to [0.0, 1.0] to handle cases where finger might be slightly outside
        # due to detection inaccuracies or fast movements.
        relative_pos_x = max(0.0, min(1.0, relative_pos_x))

        # Map this relative position to the MIDI pitch bend range.
        # Center (0.5) maps to 0 bend.
        # Left edge (0.0) maps to -self.midi_bend_max_abs_value.
        # Right edge (1.0) maps to +self.midi_bend_max_abs_value.
        # This is a linear mapping from [0.0, 1.0] to [-max_bend, +max_bend]
        # However, it's easier to think of it as mapping [0.0, 0.5] to [-max_bend, 0]
        # and [0.5, 1.0] to [0, +max_bend].
        # Or, more simply, map [0.0, 1.0] to [-max_bend, +max_bend] where 0.5 is the midpoint.
        
        # Let's use the helper: map relative_pos_x from [0, 1] to [-max_val, +max_val]
        # The center (0.5) will correctly map to 0.
        bend_value = self._map_value(relative_pos_x, 0.0, 1.0, 
                                     -self.midi_bend_max_abs_value, self.midi_bend_max_abs_value)

        # Ensure the calculated bend value is an integer and clamped.
        # Clamping is implicitly handled if relative_pos_x is clamped and mapping is correct.
        # But an explicit clamp on the final value is safer.
        clamped_bend_value = int(round(bend_value)) # Round to nearest integer
        clamped_bend_value = max(-self.midi_bend_max_abs_value, min(self.midi_bend_max_abs_value, clamped_bend_value))
        
        return clamped_bend_value


if __name__ == '__main__':
    # --- Mock ConfigManager for Testing ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data

        def get_setting(self, key, default=None):
            return self.config.get(key, default)

    # Example config data
    mock_config = {'pitch_bend_range': 2.0} # Semitones
    config_manager = MockConfigManager(mock_config)

    pitch_bend_processor = PitchBendProcessor(config_manager)
    print(f"Pitch Bend Processor Initialized.")
    print(f"Configured semitone range: {pitch_bend_processor.pitch_bend_range_semitones}")
    print(f"MIDI bend absolute max value: {pitch_bend_processor.midi_bend_max_abs_value}")

    # --- Test Cases for calculate_pitch_bend ---
    # Zone rect: (x=100, y=50, width=200, height=100)
    # Zone center_x = 100 + 200/2 = 200
    zone = (100, 50, 200, 100) 
    max_bend = pitch_bend_processor.midi_bend_max_abs_value

    test_cases = [
        ("Finger at left edge", 100.0, -max_bend),
        ("Finger at 1/4 position", 100.0 + 50.0, -max_bend // 2), # Expected: -4095 or -4096
        ("Finger at center", 100.0 + 100.0, 0),
        ("Finger at 3/4 position", 100.0 + 150.0, max_bend // 2),  # Expected: 4095 or 4096
        ("Finger at right edge", 100.0 + 200.0, max_bend),
        ("Finger slightly outside left", 90.0, -max_bend), # Test clamping
        ("Finger slightly outside right", 310.0, max_bend), # Test clamping
    ]

    print("\n--- Testing calculate_pitch_bend ---")
    for description, finger_x, expected_bend in test_cases:
        calculated_bend = pitch_bend_processor.calculate_pitch_bend(finger_x, zone)
        # For fuzzy matching of //2 cases due to rounding
        is_correct = False
        if expected_bend == 0:
            is_correct = (calculated_bend == 0)
        elif abs(calculated_bend - expected_bend) <=1 : # Allow 1 unit tolerance for //2 cases
            is_correct = True
        
        print(f"{description} (X={finger_x}):")
        print(f"  Expected Bend: {expected_bend}, Calculated Bend: {calculated_bend} -> {'Correct' if is_correct else 'INCORRECT'}")

    # Test with zero width zone
    zone_zero_width = (100, 50, 0, 100)
    calculated_bend_zero_width = pitch_bend_processor.calculate_pitch_bend(100, zone_zero_width)
    print(f"\nTest with zero width zone (X=100): Expected 0, Calculated: {calculated_bend_zero_width} -> {'Correct' if calculated_bend_zero_width == 0 else 'INCORRECT'}")

    # Test mapping precision
    # relative_pos_x = (125 - 100) / 200 = 25 / 200 = 0.125
    # map(0.125, 0, 1, -8191, 8191) = -8191 + 0.125 * (8191 - (-8191))
    # = -8191 + 0.125 * 16382 = -8191 + 2047.75 = -6143.25 -> round to -6143
    finger_x_precise = 125.0 
    expected_precise = round(-max_bend + 0.125 * (2 * max_bend)) # -6143
    calculated_precise = pitch_bend_processor.calculate_pitch_bend(finger_x_precise, zone)
    print(f"\nTest precision (X={finger_x_precise}): Expected {expected_precise}, Calculated: {calculated_precise} -> {'Correct' if calculated_precise == expected_precise else 'INCORRECT'}")

```
