# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting


STX = 0x02
ETX = 0x03
ACK = 0x06
NAK = 0x15


# High level analyzers must subclass the HighLevelAnalyzer class.
class AlphaLinerSerialAnalyzer(HighLevelAnalyzer):

    # List of settings that a user can set for this High Level Analyzer.
    com_dir = ChoicesSetting(
        choices=['Controller (Transmit)', 'AlphaLiner (Receive)'],
        label='Communication Direction',)
    show_ack = ChoicesSetting(
        choices=['Yes', 'No'],
        label='Show ACK',)
    show_nak = ChoicesSetting(
        choices=['Yes', 'No'],
        label='Show NAK')

    PACKET_LENGTHS = {
        # PC → AlphaLiner
        0x01: 3 + 0 + 2,   # Manual Mode
        0x02: 3 + 0 + 2,   # Auto Mode
        0x03: 3 + 2 + 2,   # Diagnostic Mode (D1,D2)
        0x05: 3 + 25 + 2,  # Production Config (D1..D25)
        0x06: 3 + 12 + 2,  # Production Order (D1..D12)
        0x07: 3 + 0 + 2,   # Software Stop
        0x08: 3 + 0 + 2,   # Erase Stop
        0x10: 3 + 0 + 2,   # Request Machine Config
        0x11: 3 + 2 + 2,   # Backup Feeder Definition
        0x12: 3 + 3 + 2,   # Consecutive Errors
        0x13: 3 + 2 + 2,   # Pocket/Gripper Silence
        0x14: 3 + 2 + 2,   # Forced Reject
        0x15: 3 + 0 + 2,   # Delete Production Data
        0x16: 3 + 5 + 2,   # Disable Green Lights (5 bytes)
        0x64: 3 + 2 + 2,   # Control Commands (D1,D2)
        0x65: 3 + 7 + 2,   # Parameter Data (D1..D8)

        # AlphaLiner → PC
        0x01: 3 + 2 + 2,   # Status Message
        0x02: 3 + 3 + 2,   # Error Message
        0x03: 3 + 5 + 2,   # Statistic Message
        0x04: 3 + 9 + 2,   # Copy Complete
        0x05: 3 + 10 + 2,  # Copy Failed
        0x06: 3 + 6 + 2,   # Machine Configuration
        0x07: 3 + 0 + 2,   # Copy Inhibit
        0x65: 3 + 7 + 2,   # Configuration Data Feature (same as PC→AL)
        0x78: 3 + 6 + 2,   # Double Detector Test (D1..D6)
    }

    result_types = {
        # Both
        'ACK': {
            'format': 'ACK'
        },
        'NAK': {
            'format': 'NAK'
        },

        # Controller
        'MANUAL_MODE': {
            'format': 'MANUAL MODE {{data.seq}}𝑛'
        },
        'AUTO_MODE': {
            'format': 'AUTO MODE {{data.seq}}𝑛'
        },
        'STOP': {
            'format': 'STOP {{data.seq}}𝑛'
        },
        'ERASE_STOP': {
            'format': 'ERASE STOP {{data.seq}}𝑛'
        },
        'AUTO_MODE': {
            'format': 'AUTO MODE {{data.seq}}𝑛'
        },
        'PROD_CONFIG': {
            'format': 'PRODUCT CONFIG {{data.seq}}𝑛 ({{data.info}})'
        },
        'PROD_ORDER': {
            'format': 'PRODUCT ORDER {{data.seq}}𝑛 ({{data.info}})'
        },
        'CONSECUTIVE_ERRORS': {
            'format': 'CONSECUTIVE ERRORS {{data.seq}}𝑛 ({{data.info}})'
        },

        # AlphaLiner
        'STATUS_MSG': {
            'format': 'STATUS MSG {{data.seq}}𝑛 ({{data.info}})'
        },
        'ERROR_MSG': {
            'format': 'ERROR MSG {{data.seq}}𝑛 ({{data.info}})'
        },
        'STATISTIC_MSG': {
            'format': 'STATISTIC MSG {{data.seq}}𝑛 ({{data.info}})'
        },
        'COPY_COMPLETE': {
            'format': 'COPY COMPLETE {{data.seq}}𝑛 ({{data.info}})'
        },
        'COPY_FAILED': {
            'format': 'COPY FAILED {{data.seq}}𝑛 ({{data.info}})'
        },
        'UNKNOWN': {
            'format': 'Unknown Packet ({{data.info}})'
        },

        # Unknown
        'UNKNOWN': {
            'format': 'UNKNOWN ({{data.info}})'
        },
    }

    def __init__(self):
        self.buffer = []
        self.packet_start_time = None
        self.expected_length = None
        self.controller_side = (self.com_dir == 'Controller (Transmit)')
        self.should_show_ack = (self.show_ack == 'Yes')
        self.should_show_nak = (self.show_nak == 'Yes')

    def compute_bcc(payload):
        bcc = 0
        for b in payload:
            bcc ^= b

        # Apply reserved-character increment rule
        if bcc in (0x00, 0x02, 0x03, 0x06, 0x15):
            bcc = (bcc + 1) & 0xFF

        return bcc

    def get_status_msg(self, data_bytes):
        """
        Converts the first two status bytes to human-readable format.
        
        D1: First status byte bit definitions:
            Bit 0 = 0 AND bit 1 = 0: mode = NotDefined
            Bit 0 = 1 AND bit 1 = 0: mode = Manual
            Bit 0 = 0 AND bit 1 = 1: mode = Automatic
            Bit 0 = 1 AND bit 1 = 1: mode = Diagnosis
            Bit 2 = 1: ReadyToGo
        
        D2: Second status byte bit definitions:
            Bit 0 = 1: [definition appears cut off in your message]
        
        Args:
            data_bytes: list of data bytes from the packet
        
        Returns:
            string: human-readable status message
        """
        if len(data_bytes) < 2:
            return "Insufficient status data"
        
        d1 = data_bytes[0] & 0x7F  # Remove MSB, keep 7 bits
        d2 = data_bytes[1] & 0x7F  # Remove MSB, keep 7 bits
        
        # Decode D1 (first status byte)
        bit0 = d1 & 0x01  # Bit 0
        bit1 = (d1 & 0x02) >> 1  # Bit 1
        bit2 = (d1 & 0x04) >> 2  # Bit 2
        
        # Determine mode from bits 0 and 1
        if bit0 == 0 and bit1 == 0:
            mode = "NotDefined"
        elif bit0 == 1 and bit1 == 0:
            mode = "Manual"
        elif bit0 == 0 and bit1 == 1:
            mode = "Automatic"
        elif bit0 == 1 and bit1 == 1:
            mode = "Diagnosis"
        
        # Check ReadyToGo status
        ready_to_go = "ReadyToGo" if bit2 == 1 else "NotReady"
        
        # Decode D2 (second status byte)
        d2_bit0 = d2 & 0x01
        # Add more D2 bit definitions as needed when you provide the complete definition
        
        # Build status message
        status_parts = [mode, ready_to_go]
        
        if d2_bit0 == 1:
            status_parts.append("DataReady")
        
        return ", ".join(status_parts)


    def get_error_msg(self, data_bytes):
        """
        Converts the first three error bytes to human-readable format.
        
        D1: Fault (Value between 0..99)
        D2: Cause (Value between 0..99) 
        D3: Priority (Value between 0..99)
        
        Special cases:
        - If priority is 0, the error is cleared
        - If all three values are 0, the entire fault pool is cleared
        
        Args:
            data_bytes: list of data bytes from the packet
        
        Returns:
            string: human-readable error message
        """
        if len(data_bytes) < 3:
            return "Insufficient error data"
        
        d1_fault = data_bytes[0] & 0x7F  # Remove MSB, keep 7 bits (0..99)
        d2_cause = data_bytes[1] & 0x7F  # Remove MSB, keep 7 bits (0..99)
        d3_priority = data_bytes[2] & 0x7F  # Remove MSB, keep 7 bits (0..99)
        
        # Check special cases
        if d1_fault == 0 and d2_cause == 0 and d3_priority == 0:
            return "Cleared All Faults"
        elif d3_priority == 0:
            return f"Error cleared - Fault: {d1_fault}, Cause: {d2_cause}, Priority: {d3_priority}"
        else:
            return f"Fault: {d1_fault}, Cause: {d2_cause}, Priority: {d3_priority}"


    def get_statistic_msg(self, data_bytes):
        """
        Converts the first five statistic bytes to human-readable format.
        
        D1: Error type (0-14)
        D2..D3: Error Location (depends on error type)
        D4..D5: CopyID (1-8191)
        
        Args:
            data_bytes: list of data bytes from the packet
        
        Returns:
            string: human-readable statistic message
        """
        if len(data_bytes) < 5:
            return "Insufficient statistic data"
        
        d1_error = data_bytes[0] & 0x7F  # Remove MSB, keep 7 bits
        d2_location_high = data_bytes[1] & 0x7F  # Remove MSB, keep 7 bits
        d3_location_low = data_bytes[2] & 0x7F  # Remove MSB, keep 7 bits
        d4_copy_high = data_bytes[3] & 0x7F  # Remove MSB, keep 7 bits
        d5_copy_low = data_bytes[4] & 0x7F  # Remove MSB, keep 7 bits
        
        # Error type mapping
        error_types = {
            0: "Other Errors",
            1: "Missfeed",
            2: "Doublefeed", 
            3: "Opening Error",
            4: "Profile Error",
            5: "Defective Pocket",
            6: "Defective Gripper",
            7: "Maximum Number of Repair Attempts",
            8: "Gap Errors",
            9: "Controlled Forced Reject",
            10: "Wrongfeed",
            11: "Clutch",
            12: "Package Removed from Gripper Chain",
            13: "Mode Change",
            14: "Empty Pocket Error"
        }
        
        error_name = error_types.get(d1_error, f"Unknown Error ({d1_error})")
        
        # Combine D2..D3 for error location
        error_location = (d2_location_high << 7) | d3_location_low
        
        # Combine D4..D5 for CopyID
        copy_id = (d4_copy_high << 7) | d5_copy_low
        
        # Format location based on error type
        if d1_error in [1, 2, 10]:  # Missfeed, Doublefeed, Wrongfeed
            location_str = f"Feeder: {error_location}"
        elif d1_error in [3, 5, 14]:  # Opening Error, Defective Pocket, Empty Pocket Error
            location_str = f"Pocket: {error_location}"
        elif d1_error in [4, 6, 12]:  # Profile Error, Defective Gripper, Package Removed
            location_str = f"Gripper: {error_location}"
        elif d1_error == 11:  # Clutch
            if error_location == 99:
                location_str = "Location: Pocket Wheel / Jacket Feeder"
            else:
                location_str = f"Insert Feeder Module: {error_location}"
        else:
            location_str = f"Location: {error_location}"
        
        return f"CopyID: {copy_id} ({error_name}), {location_str}"


    def get_bit_positions(self, number, num_bits=31):
        """
        Returns a comma-separated string of bit positions that contain '1' 
        in the first num_bits of the number (0-indexed from the right).
        
        Args:
            number: integer to analyze
            num_bits: number of bits to check from the right (default 31)
        
        Returns:
            string: comma-separated positions of '1' bits
        """
        positions = []
        
        # Check each bit position from 0 to num_bits-1
        for i in range(num_bits):
            if number & (1 << i):  # Check if bit at position i is set
                if i == 0:
                    positions.append('P')  # Replace position 0 with 'P'
                else:
                    positions.append(str(i))
        
        return ','.join(reversed(positions)) if positions else '0'


    def get_copy_complete_msg(self, data_bytes):
        """
        Converts the first nine bytes to human-readable format for copy complete/failed messages.
        
        D1..D2: CopyID (1-8191) with good/faulty indication
        D3..D4: Gripper number (1-4095)
        D5..D9: Table of available inserts
        
        Args:
            data_bytes: list of data bytes from the packet
        
        Returns:
            string: human-readable copy complete message
        """
        if len(data_bytes) < 9:
            return "Insufficient copy data"
        
        # D1..D2: CopyID with good/faulty indication
        d1 = data_bytes[0] & 0x7F  # Remove MSB, keep 7 bits
        d2 = data_bytes[1] & 0x7F  # Remove MSB, keep 7 bits
        
        # Check bit 6 of D1 for good/faulty indication (before masking)
        is_good_copy = (data_bytes[0] & 0x40) != 0  # Bit 6
        
        # Extract CopyID (6 highest bits from D1, 7 lowest bits from D2)
        copy_id_high = d1 & 0x3F  # Keep only lower 6 bits of D1
        copy_id = (copy_id_high << 7) | d2
        
        # D3..D4: Gripper number
        d3 = data_bytes[2] & 0x7F  # Remove MSB, keep 7 bits
        d4 = data_bytes[3] & 0x7F  # Remove MSB, keep 7 bits
        
        # Extract gripper number (5 highest bits from D3, 7 lowest bits from D4)
        gripper_high = d3 & 0x1F  # Keep only lower 5 bits of D3
        gripper_number = (gripper_high << 7) | d4
        
        # D5..D9: Table of available inserts (5 bytes)
        insert_bytes = []
        for i in range(4, 9):  # D5 through D9 (indices 4-8)
            insert_bytes.append(data_bytes[i] & 0x7F)  # Remove MSB from each
        
        # Concatenate the 7-bit values into a single 35-bit number for insert table
        insert_table = 0
        for val in insert_bytes:
            insert_table = (insert_table << 7) | val
        
        # Convert to binary and get bit positions for inserts
        insert_positions = self.get_bit_positions(insert_table)
        
        # Build the message
        copy_status = "Good" if is_good_copy else "Faulty"
        
        return f"CopyID: {copy_id} ({copy_status}), Gripper: {gripper_number}, Inserts: {insert_positions}"


    def format_hp_binary(self, data_bytes, start_index=0):
        """
        Takes 5 bytes from data_bytes starting at start_index,
        removes MSB from each (keeps 7 bits), concatenates them,
        and formats as binary with 'HP' prefix for leading bit if it's 1.
        
        Args:
            data_bytes: list of bytes
            start_index: starting index in the list (default 0)
        
        Returns:
            string: formatted binary representation
        """
        if len(data_bytes) < start_index + 5:
            return "Insufficient data"
        
        # Extract 5 bytes and remove MSB (keep 7 bits each)
        seven_bit_values = []
        for i in range(5):
            byte_val = data_bytes[start_index + i] & 0x7F  # Remove MSB
            seven_bit_values.append(byte_val)
        
        # Concatenate the 7-bit values into a single 35-bit number
        concatenated = 0
        for val in seven_bit_values:
            concatenated = (concatenated << 7) | val
        
        return self.get_bit_positions(concatenated, 31)


    def get_control_type(self, control_code):
        control_types = {
            0x00: 'Missfeed',
            0x01: 'DoubleFeed',
            0x02: 'Opening',
            0x03: 'Profile',
            0x04: 'Tolerance',
            0x05: 'Gap'
        }
        return control_types.get(control_code, 'Unknown Control')


    def get_bit_positions(self, number, num_bits=31):
        """
        Returns a comma-separated string of bit positions that contain '1' 
        in the first num_bits of the number (0-indexed from the right).
        
        Args:
            number: integer to analyze
            num_bits: number of bits to check from the right (default 31)
        
        Returns:
            string: comma-separated positions of '1' bits
        """
        positions = []
        
        # Check each bit position from 0 to num_bits-1
        for i in range(num_bits):
            if number & (1 << i):  # Check if bit at position i is set
                if i == 0:
                    positions.append('J')  # Replace position 0 with 'J'
                else:
                    positions.append(str(i))
        
        return ','.join(reversed(positions)) if positions else 'CEALR'


    def get_copy_id(self, data_bytes, start_index=0):
        """
        Takes the first two bytes from self.buffer, removes MSB from each (keeps 7 bits),
        and combines them into a single number.
        
        Returns:
            int: combined 14-bit number from the two 7-bit values, or 0 if insufficient data
        """
        if len(self.buffer) < 2:
            return 0
        
        # Get first two bytes and remove MSB (keep 7 bits each)
        byte1 = data_bytes[start_index] & 0x7F  # Remove MSB, keep lower 7 bits
        byte2 = data_bytes[start_index + 1] & 0x7F  # Remove MSB, keep lower 7 bits

        # Combine into single number (byte1 is high 7 bits, byte2 is low 7 bits)
        copy_id = (byte1 << 7) | byte2

        return copy_id


    def get_count(self, data_bytes, start_index=0):
        """
        Takes the first two bytes from self.buffer, removes MSB from each (keeps 7 bits),
        and combines them into a single number.
        
        Returns:
            int: combined 14-bit number from the two 7-bit values, or 0 if insufficient data
        """
        if len(self.buffer) < 4:
            return 0
        
        # Get first two bytes and remove MSB (keep 7 bits each)
        byte1 = data_bytes[start_index] & 0x7F  # Remove MSB, keep lower 7 bits
        byte2 = data_bytes[start_index + 1] & 0x7F  # Remove MSB, keep lower 7 bits
        byte3 = data_bytes[start_index + 2] & 0x7F  # Remove MSB, keep lower 7 bits
        byte4 = data_bytes[start_index + 3] & 0x7F  # Remove MSB, keep lower 7 bits

        # Combine into single number (byte1 is high 7 bits, byte2 is low 7 bits)
        count = (byte1 << 21) | (byte2 << 14) | (byte3 << 7) | byte4

        return count


    def handle_packet(self, method, seq, data_bytes, start, end):
        if self.controller_side:
            if method == 0x01:
                return AnalyzerFrame('MANUAL_MODE', start, end, {'seq': seq})
            elif method == 0x02:
                return AnalyzerFrame('AUTO_MODE', start, end, {'seq': seq})
            elif method == 0x05:
                info = "Feeder: {} DoubleFeed: {} Missfeed: {} Backup: {} LowLevel: {}".format(
                    self.format_hp_binary(data_bytes, 0),
                    self.format_hp_binary(data_bytes, 5),
                    self.format_hp_binary(data_bytes, 10),
                    self.format_hp_binary(data_bytes, 15),
                    self.format_hp_binary(data_bytes, 20)
                )
                return AnalyzerFrame('PROD_CONFIG', start, end, {'seq': seq, 'info': info})
            elif method == 0x06:  # Product Order
                info = "CopyID: {}, Inserts: {} Reserved: {}, Copies: {}".format(
                    self.get_copy_id(data_bytes),
                    self.format_hp_binary(data_bytes, 2),
                    data_bytes[7] & 0x7F,
                    self.get_count(data_bytes, 8)
                )
                return AnalyzerFrame('PROD_ORDER', start, end, {
                    'seq': seq,
                    'info': info
                })
            elif method == 0x07:  # Stop
                return AnalyzerFrame('STOP', start, end, {'seq': seq})
            elif method == 0x08:  # Erase Stop
                return AnalyzerFrame('ERASE_STOP', start, end, {'seq': seq})
            elif method == 0x0C:  # Consecutive Errors
                info = "Type: {}, Feeder: {}, Count: {}".format(
                    self.get_control_type(data_bytes[0] & 0x7F),
                    (lambda v: ("ALL" if v == 99 else ("J" if v == 0 else v))) (data_bytes[1] & 0x7F),
                    data_bytes[2] & 0x7F
                )
                return AnalyzerFrame('CONSECUTIVE_ERRORS', start, end, {
                    'seq': seq,
                    'info': info
                })
        else:
            if method == 0x01:
                return AnalyzerFrame('STATUS_MSG', start, end, {'seq': seq, 'info': self.get_status_msg(data_bytes)})
            elif method == 0x02:
                return AnalyzerFrame('ERROR_MSG', start, end, {'seq': seq, 'info': self.get_error_msg(data_bytes)})
            elif method == 0x03:  # Statistic Message
                return AnalyzerFrame('STATISTIC_MSG', start, end, {'seq': seq, 'info': self.get_statistic_msg(data_bytes)})
            elif method == 0x04:  # Copy Complete
                return AnalyzerFrame('COPY_COMPLETE', start, end, {'seq': seq, 'info': self.get_copy_complete_msg(data_bytes)})
            elif method == 0x05:  # Copy Failed
                info = "{}, Inserts: {}".format(self.get_statistic_msg(data_bytes), self.format_hp_binary(data_bytes, 5))
                return AnalyzerFrame('COPY_FAILED', start, end, {'seq': seq, 'info': info})

        return AnalyzerFrame('UNKNOWN', start, end, {'info': f'Method {method} not implemented'})


    def decode(self, frame: AnalyzerFrame):

        if frame.type == "data" and "data" in frame.data:
            byte = frame.data["data"][0]

        start_time = frame.start_time
        end_time = frame.end_time

        # ACK / NAK handling
        if byte == ACK:
            return AnalyzerFrame('ACK', start_time, end_time, None) if self.should_show_ack else None

        if byte == NAK:
            return AnalyzerFrame('NAK', start_time, end_time, None) if self.should_show_nak else None

        # Start of packet
        if byte == STX:
            self.buffer = [byte]
            self.packet_start_time = start_time
            self.expected_length = None
            return None

        # If inside a packet, accumulate bytes
        if self.packet_start_time:
            self.buffer.append(byte)

            # Once we have STX + C1 + C2, determine expected length
            if len(self.buffer) == 3:
                method_raw = self.buffer[2]
                method = method_raw & 0x7F
                self.expected_length = PACKET_LENGTHS.get(method)

            # If we know the expected length and have enough bytes, finalize
            if self.expected_length and len(self.buffer) == self.expected_length:

                # Validate ETX
                if self.buffer[-1] != ETX:
                    info = f"Invalid ETX: expected 0x03, got {hex(self.buffer[-1])}"
                    self._reset_state()
                    return AnalyzerFrame('UNKNOWN', start_time, end_time, {'info': info})

                # Validate BCC
                bcc_received = self.buffer[-2]
                payload = self.buffer[1:-2]  # C1, C2, D1..Dn
                bcc_expected = compute_bcc(payload)

                if bcc_received != bcc_expected:
                    info = f"BCC mismatch: expected {hex(bcc_expected)}, got {hex(bcc_received)}"
                    self._reset_state()
                    return AnalyzerFrame('UNKNOWN', start_time, end_time, {'info': info})

                # Extract fields
                seq_raw = self.buffer[1]
                method_raw = self.buffer[2]
                data_bytes = self.buffer[3:-2]

                seq = seq_raw & 0x7F
                method = method_raw & 0x7F

                frame_start = self.packet_start_time

                # Reset before dispatch
                self._reset_state()

                # Dispatch to existing logic
                return self.handle_packet(method, seq, data_bytes, frame_start, end_time)

        return None


    def _reset_state(self):
        self.buffer = []
        self.packet_start_time = None
        self.expected_length = None
