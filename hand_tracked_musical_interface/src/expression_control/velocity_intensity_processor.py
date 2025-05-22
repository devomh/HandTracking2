# Assuming ConfigManager is in src.config_manager
# from ..config_manager import ConfigManager # Use this if part of a package

class VelocityIntensityProcessor:
    """
    Calculates MIDI velocity and continuous intensity values based on vertical
    finger position within a note zone.
    """

    def __init__(self, config_manager): # Type hint later: config_manager: ConfigManager
        """
        Initializes the VelocityIntensityProcessor.

        Args:
            config_manager: An instance of the ConfigManager to access settings.
                            (Currently not used for specific settings in this processor,
                             but good practice to include for future enhancements).
        """
        self.config_manager = config_manager
        self.midi_min_value = 0
        self.midi_max_value = 127


    def _map_value(self, value, from_low, from_high, to_low, to_high):
        """
        Linearly maps a value from one range to another.
        Clamps the output to [to_low, to_high].
        """
        if from_low == from_high:
            # Return the middle of the target range, or to_low, or error
            return to_low if to_low <= to_high else to_high 
            
        percentage = (value - from_low) / (from_high - from_low)
        mapped_value = to_low + percentage * (to_high - to_low)
        
        # Clamp the output value to the target range
        if to_low < to_high:
            return max(to_low, min(mapped_value, to_high))
        else: # Handle inverted to_range (e.g. 127 to 0)
            return max(to_high, min(mapped_value, to_low))


    def calculate_initial_velocity(self, finger_y_position: float, zone_rect: tuple[int, int, int, int]) -> int:
        """
        Calculates the initial MIDI velocity based on the finger's Y-coordinate
        at the moment it enters the zone.
        Higher Y-coordinate (lower on screen) means louder/higher velocity.

        Args:
            finger_y_position (float): The Y-coordinate of the finger.
            zone_rect (tuple): The rectangle (x, y, width, height) of the note zone.

        Returns:
            int: The calculated MIDI velocity value (0-127).
        """
        _zone_x, zone_y, _zone_width, zone_height = zone_rect

        if zone_height == 0: # Avoid division by zero
            return self.midi_min_value # Or a sensible default like mid-velocity (64)

        # relative_y: 0.0 at top edge (zone_y), 1.0 at bottom edge (zone_y + zone_height)
        relative_y = (finger_y_position - zone_y) / zone_height
        
        # Clamp relative_y to [0.0, 1.0]
        relative_y = max(0.0, min(1.0, relative_y))

        # Specification: "Lower Y = softer/less intense, Higher Y = louder/more intense."
        # Screen coordinates: Y increases downwards.
        # So, if finger_y_position is higher (larger value, lower on screen), relative_y is closer to 1.0.
        # This means relative_y directly corresponds to intensity (0.0 soft, 1.0 loud).
        # No inversion needed for relative_y itself if mapping [0,1] to [0,127] for velocity.
        
        # Map relative_y [0.0 (top, softer) to 1.0 (bottom, louder)] to MIDI velocity [0, 127].
        velocity = self._map_value(relative_y, 0.0, 1.0, self.midi_min_value, self.midi_max_value)
        
        return int(round(velocity))

    def calculate_continuous_intensity(self, finger_y_position: float, zone_rect: tuple[int, int, int, int]) -> int:
        """
        Calculates a continuous intensity value (e.g., for Channel Pressure or CC)
        based on the finger's current Y-coordinate within the zone.
        Higher Y-coordinate (lower on screen) means more intense.

        Args:
            finger_y_position (float): The current Y-coordinate of the finger.
            zone_rect (tuple): The rectangle (x, y, width, height) of the note zone.

        Returns:
            int: The calculated intensity value (0-127).
        """
        # The logic is identical to calculate_initial_velocity for mapping Y to 0-127.
        # The difference is primarily in how this value is used (initial note-on vs. continuous control).
        _zone_x, zone_y, _zone_width, zone_height = zone_rect

        if zone_height == 0:
            return self.midi_min_value

        relative_y = (finger_y_position - zone_y) / zone_height
        relative_y = max(0.0, min(1.0, relative_y))
        
        # Map relative_y [0.0 (top, softer) to 1.0 (bottom, louder)] to intensity [0, 127].
        intensity = self._map_value(relative_y, 0.0, 1.0, self.midi_min_value, self.midi_max_value)
        
        return int(round(intensity))


if __name__ == '__main__':
    # --- Mock ConfigManager for Testing (not strictly needed for this processor yet) ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data
        def get_setting(self, key, default=None):
            return self.config.get(key, default)

    mock_config = {} # No specific config used by this processor yet
    config_manager = MockConfigManager(mock_config)

    processor = VelocityIntensityProcessor(config_manager)
    print("Velocity/Intensity Processor Initialized.")

    # --- Test Cases ---
    # Zone rect: (x=50, y=100, width=100, height=200)
    # Zone top_y = 100, bottom_y = 300, center_y = 200
    zone = (50, 100, 100, 200)

    test_cases_velocity = [
        ("Finger at top edge (softest)", 100.0, 0),    # relative_y = 0.0
        ("Finger at 1/4 down", 150.0, 32),             # relative_y = 0.25 -> 127*0.25 = 31.75 -> 32
        ("Finger at center", 200.0, 64),               # relative_y = 0.5  -> 127*0.5 = 63.5 -> 64
        ("Finger at 3/4 down", 250.0, 95),             # relative_y = 0.75 -> 127*0.75 = 95.25 -> 95
        ("Finger at bottom edge (loudest)", 300.0, 127),# relative_y = 1.0
        ("Finger slightly above top", 90.0, 0),        # Test clamping
        ("Finger slightly below bottom", 310.0, 127),  # Test clamping
    ]

    print("\n--- Testing calculate_initial_velocity ---")
    for description, finger_y, expected_value in test_cases_velocity:
        calculated_value = processor.calculate_initial_velocity(finger_y, zone)
        print(f"{description} (Y={finger_y}):")
        print(f"  Expected: {expected_value}, Calculated: {calculated_value} -> {'Correct' if calculated_value == expected_value else 'INCORRECT'}")

    print("\n--- Testing calculate_continuous_intensity ---")
    # Test cases are the same as for velocity, as the mapping logic is identical
    for description, finger_y, expected_value in test_cases_velocity:
        calculated_value = processor.calculate_continuous_intensity(finger_y, zone)
        print(f"{description} (Y={finger_y}):")
        print(f"  Expected: {expected_value}, Calculated: {calculated_value} -> {'Correct' if calculated_value == expected_value else 'INCORRECT'}")

    # Test with zero height zone
    zone_zero_height = (50, 100, 100, 0)
    calculated_vel_zero_height = processor.calculate_initial_velocity(100, zone_zero_height)
    calculated_int_zero_height = processor.calculate_continuous_intensity(100, zone_zero_height)
    print(f"\nTest velocity with zero height zone (Y=100): Expected 0, Calculated: {calculated_vel_zero_height} -> {'Correct' if calculated_vel_zero_height == 0 else 'INCORRECT'}")
    print(f"Test intensity with zero height zone (Y=100): Expected 0, Calculated: {calculated_int_zero_height} -> {'Correct' if calculated_int_zero_height == 0 else 'INCORRECT'}")
    
    # Test mapping of _map_value for inverted range (e.g. if we wanted higher Y = softer)
    # mapped_inverted = processor._map_value(0.25, 0.0, 1.0, 127, 0) # 0.25 -> 95
    # print(f"\nTest _map_value inverted: map(0.25, 0,1, 127,0) = {mapped_inverted} (Expected 95)")
    # assert round(mapped_inverted) == 95

```
