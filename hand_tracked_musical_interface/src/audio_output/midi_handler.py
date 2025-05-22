import mido
# import mido.backends.rtmidi # Not strictly necessary to import explicitly
import time
# Assuming ConfigManager is in src.config_manager
from ..config_manager import ConfigManager


class MidiHandler:
    """
    Handles MIDI output, including MPE channel management for polyphonic expression.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the MidiHandler.

        Args:
            config_manager (ConfigManager): An instance of the ConfigManager.
        """
        self.config_manager = config_manager
        self.midi_output_port_name = self.config_manager.get_setting('midi_output_port', None)
        
        # MPE: Channel 1 is often the master/global channel. Member channels are typically 2-16.
        # Default to channels 2-16 if not specified or invalid.
        mpe_ch_range = self.config_manager.get_setting('midi_channel_range', [2, 16])
        if not (isinstance(mpe_ch_range, list) and len(mpe_ch_range) == 2 and
                isinstance(mpe_ch_range[0], int) and isinstance(mpe_ch_range[1], int) and
                1 <= mpe_ch_range[0] <= 16 and 1 <= mpe_ch_range[1] <= 16 and
                mpe_ch_range[0] <= mpe_ch_range[1]):
            print(f"Warning: Invalid 'midi_channel_range' ({mpe_ch_range}). Defaulting to [2, 16].")
            mpe_ch_range = [2, 16]
        
        # Channels are 1-indexed for users, but 0-indexed for mido messages.
        # self.available_channels stores 1-indexed channels.
        self.available_channels = set(range(mpe_ch_range[0], mpe_ch_range[1] + 1))
        self.master_channel = 1 # Standard MPE master channel for global messages (if any needed later)
        
        self.active_note_channels = {}  # Maps finger_id to its assigned 1-indexed MIDI channel
        self.port = None
        self.open_port()

    def open_port(self):
        """
        Opens the MIDI output port specified in the configuration.
        """
        if self.port is not None and not self.port.closed:
            # print("MIDI port already open.")
            return

        available_ports = mido.get_output_names()
        # print(f"Available MIDI output ports: {available_ports}")

        if self.midi_output_port_name:
            if self.midi_output_port_name not in available_ports:
                print(f"Warning: Configured MIDI port '{self.midi_output_port_name}' not found. "
                      f"Attempting to use first available port if any, or default.")
                # Fallback strategy: try to use a common virtual MIDI port name or first available
                # This part can be platform-dependent.
                # For now, let's try to open by name and let it fail if not specific.
                # Or, if no specific port is given, try to open the default one.
                # If a name is given but not found, it's an issue.
                self.port = None # Ensure port is None if desired one not found
            else:
                try:
                    self.port = mido.open_output(self.midi_output_port_name)
                    print(f"Successfully opened MIDI port: {self.midi_output_port_name}")
                except (IOError, mido.MidiIOError) as e: # mido.MidiIOError for port-specific issues
                    print(f"Error opening MIDI port '{self.midi_output_port_name}': {e}")
                    self.port = None
        else: # No port name specified in config
            print("No MIDI output port specified in configuration. Attempting to open default.")
            try:
                self.port = mido.open_output() # Try to open default output
                if self.port:
                    print(f"Successfully opened default MIDI port: {self.port.name}")
                else:
                    print("Could not open default MIDI port (no ports available or backend issue).")
            except (IOError, mido.MidiIOError) as e:
                print(f"Error opening default MIDI port: {e}")
                self.port = None
        
        if self.port is None:
            print("MIDI output is disabled as no port could be opened.")


    def close_port(self):
        """
        Closes the MIDI output port if it is open.
        """
        if self.port and not self.port.closed:
            print(f"Closing MIDI port: {self.port.name}")
            self.port.close()
            self.port = None
        self.available_channels.update(self.active_note_channels.values()) # Reclaim all channels
        self.active_note_channels.clear()


    def send_note_on(self, note_midi_value: int, velocity: int, finger_id):
        """
        Sends a MIDI Note On message. Manages MPE channels.

        Args:
            note_midi_value (int): The MIDI note number (0-127).
            velocity (int): The note velocity (0-127).
            finger_id (any): A unique identifier for the finger triggering the note.
        """
        if not self.port or self.port.closed:
            # print("MIDI port not open. Cannot send Note On.")
            return

        assigned_channel = None
        if finger_id in self.active_note_channels:
            # This finger is already playing a note. This might be a re-trigger.
            # Use existing channel. Send Note Off first? MPE spec implies new note on new channel or re-use.
            # For simplicity, re-use channel. Some synths might prefer a note-off first.
            assigned_channel = self.active_note_channels[finger_id]
            # print(f"Finger {finger_id} re-triggering note on channel {assigned_channel}.")
        elif self.available_channels:
            assigned_channel = self.available_channels.pop()
            self.active_note_channels[finger_id] = assigned_channel
            # print(f"Assigned channel {assigned_channel} to finger {finger_id}.")
        else:
            print("Warning: Ran out of MPE channels! Cannot send Note On.")
            # Optionally, could send on master channel as a non-MPE note
            # assigned_channel = self.master_channel 
            return

        if assigned_channel is not None:
            # MIDI channels in mido are 0-indexed (0-15 for channels 1-16)
            msg = mido.Message('note_on', note=note_midi_value, velocity=velocity, channel=assigned_channel - 1)
            # print(f"Sending Note On: {msg} (Finger: {finger_id})")
            self.port.send(msg)

    def send_note_off(self, note_midi_value: int, finger_id):
        """
        Sends a MIDI Note Off message. Manages MPE channels.

        Args:
            note_midi_value (int): The MIDI note number (0-127).
            finger_id (any): The unique identifier for the finger that triggered the note.
        """
        if not self.port or self.port.closed:
            # print("MIDI port not open. Cannot send Note Off.")
            return

        if finger_id in self.active_note_channels:
            assigned_channel = self.active_note_channels.pop(finger_id)
            self.available_channels.add(assigned_channel) # Release channel
            
            msg = mido.Message('note_off', note=note_midi_value, velocity=0, channel=assigned_channel - 1)
            # print(f"Sending Note Off: {msg} (Finger: {finger_id}, Channel: {assigned_channel})")
            self.port.send(msg)
        else:
            print(f"Warning: Finger {finger_id} not found for Note Off. No message sent.")

    def send_pitch_bend(self, bend_value: int, finger_id):
        """
        Sends a MIDI Pitch Bend message for a specific finger's channel.

        Args:
            bend_value (int): The pitch bend value (-8192 to 8191).
            finger_id (any): The unique identifier for the finger.
        """
        if not self.port or self.port.closed:
            return
        
        if finger_id in self.active_note_channels:
            assigned_channel = self.active_note_channels[finger_id]
            msg = mido.Message('pitchwheel', pitch=bend_value, channel=assigned_channel - 1)
            # print(f"Sending Pitch Bend: {msg} (Finger: {finger_id})")
            self.port.send(msg)
        # else:
            # print(f"Warning: Finger {finger_id} not active for Pitch Bend.")


    def send_channel_pressure(self, pressure_value: int, finger_id):
        """
        Sends a MIDI Channel Pressure (Aftertouch) message for a specific finger's channel.

        Args:
            pressure_value (int): The pressure value (0-127).
            finger_id (any): The unique identifier for the finger.
        """
        if not self.port or self.port.closed:
            return

        if finger_id in self.active_note_channels:
            assigned_channel = self.active_note_channels[finger_id]
            # Mido uses 'aftertouch' for Channel Pressure.
            # 'polytouch' is for Polyphonic Key Pressure (per-note aftertouch).
            # The subtask specified "Channel Pressure", so 'aftertouch' is correct here.
            msg = mido.Message('aftertouch', value=pressure_value, channel=assigned_channel - 1)
            # print(f"Sending Channel Pressure: {msg} (Finger: {finger_id})")
            self.port.send(msg)
        # else:
            # print(f"Warning: Finger {finger_id} not active for Channel Pressure.")
            
    def send_control_change(self, cc_number: int, cc_value: int, finger_id):
        """
        Sends a MIDI Control Change message for a specific finger's channel.
        Useful if CC is preferred over Channel Pressure for intensity.

        Args:
            cc_number (int): The Control Change number (0-127).
            cc_value (int): The CC value (0-127).
            finger_id (any): The unique identifier for the finger.
        """
        if not self.port or self.port.closed:
            return

        if finger_id in self.active_note_channels:
            assigned_channel = self.active_note_channels[finger_id]
            msg = mido.Message('control_change', control=cc_number, value=cc_value, channel=assigned_channel - 1)
            # print(f"Sending Control Change: {msg} (Finger: {finger_id})")
            self.port.send(msg)


if __name__ == '__main__':
    # --- Mock ConfigManager for Testing ---
    class MockConfigManager:
        def __init__(self, config_data):
            self.config = config_data
        def get_setting(self, key, default=None):
            keys = key.split('.')
            value = self.config
            try:
                for k in keys: value = value[k]
                return value
            except (KeyError, TypeError): return default

    # List available ports for user to choose for testing
    print("Available MIDI output ports for testing:")
    print(mido.get_output_names())
    # Example: use a virtual MIDI port like 'IAC Driver Bus 1' on macOS or 'Microsoft GS Wavetable Synth' on Windows
    # Or loopMIDI on Windows.
    test_port_name = None # Set this to a valid port name on your system for testing
    # If None, it will try to use the default mido port.

    mock_config_data = {
        'midi_output_port': test_port_name,
        'midi_channel_range': [2, 5] # Small range for testing channel exhaustion
    }
    config_manager = MockConfigManager(mock_config_data)
    midi_handler = MidiHandler(config_manager)

    if midi_handler.port:
        print(f"\n--- MidiHandler Test (Port: {midi_handler.port.name}) ---")

        finger1 = "finger_idx_0"
        finger2 = "finger_idx_1"
        finger3 = "finger_idx_2"
        finger4 = "finger_idx_3"
        finger5 = "finger_idx_4" # To test channel exhaustion

        # Test Note On
        print("\nTesting Note On:")
        midi_handler.send_note_on(note_midi_value=60, velocity=100, finger_id=finger1) # C4
        midi_handler.send_note_on(note_midi_value=62, velocity=100, finger_id=finger2) # D4
        midi_handler.send_note_on(note_midi_value=64, velocity=100, finger_id=finger3) # E4
        midi_handler.send_note_on(note_midi_value=65, velocity=100, finger_id=finger4) # F4
        
        print(f"Active note channels: {midi_handler.active_note_channels}")
        print(f"Available channels: {midi_handler.available_channels}")
        
        # Test channel exhaustion
        print("\nTesting channel exhaustion:")
        midi_handler.send_note_on(note_midi_value=67, velocity=100, finger_id=finger5) # G4 - should fail or use master

        # Test Pitch Bend
        print("\nTesting Pitch Bend:")
        midi_handler.send_pitch_bend(bend_value=2000, finger_id=finger1)
        midi_handler.send_pitch_bend(bend_value=-1000, finger_id=finger2)

        # Test Channel Pressure
        print("\nTesting Channel Pressure (Aftertouch):")
        midi_handler.send_channel_pressure(pressure_value=80, finger_id=finger1)
        
        # Test Control Change (e.g., CC11 for Expression)
        print("\nTesting Control Change (CC11):")
        midi_handler.send_control_change(cc_number=11, cc_value=90, finger_id=finger2)

        time.sleep(1) # Allow notes to sound briefly

        # Test Note Off
        print("\nTesting Note Off:")
        midi_handler.send_note_off(note_midi_value=60, finger_id=finger1)
        midi_handler.send_note_off(note_midi_value=62, finger_id=finger2)
        
        print(f"Active note channels after some Note Offs: {midi_handler.active_note_channels}")
        print(f"Available channels: {midi_handler.available_channels}")

        # Test re-assigning released channels
        print("\nTesting re-assigning channels:")
        midi_handler.send_note_on(note_midi_value=67, velocity=110, finger_id=finger5) # Should now get a channel

        time.sleep(0.5)
        midi_handler.send_note_off(note_midi_value=64, finger_id=finger3)
        midi_handler.send_note_off(note_midi_value=65, finger_id=finger4)
        midi_handler.send_note_off(note_midi_value=67, finger_id=finger5)

        print("\n--- Test Complete ---")
        midi_handler.close_port()
    else:
        print("\n--- MidiHandler Test: Port not opened. Cannot run full test. ---")
        print("Please ensure a MIDI port is available and configured if necessary.")

```
