import unittest
from unittest.mock import patch, MagicMock
import serial # Import the actual serial module to check for its exceptions
from grbl_communicator import GRBLCommunicator, logging

# Disable logging for tests to keep output clean
logging.disable(logging.CRITICAL)

class TestGRBLCommunicatorInit(unittest.TestCase):
    def test_init_stores_port_and_baudrate(self):
        port = "/dev/testport"
        baudrate = 115200
        communicator = GRBLCommunicator(port, baudrate)
        self.assertEqual(communicator.port, port)
        self.assertEqual(communicator.baudrate, baudrate)
        self.assertIsNone(communicator.ser)

class TestGRBLCommunicatorConnect(unittest.TestCase):
    @patch('grbl_communicator.serial.Serial')
    def test_connect_successful(self, mock_serial_class):
        mock_ser_instance = MagicMock()
        mock_ser_instance.is_open = True
        mock_ser_instance.in_waiting = 0 # Default to no data initially
        
        # Simulate GRBL startup message
        grbl_startup_message = b"Grbl 1.1h ['$' for help]\r\n"
        
        # Configure side_effect for readline to simulate GRBL sending data
        # Then no more data (which will make in_waiting effectively 0)
        def readline_side_effect(*args, **kwargs):
            if readline_side_effect.called_once:
                mock_ser_instance.in_waiting = len(grbl_startup_message)
                return grbl_startup_message
            mock_ser_instance.in_waiting = 0
            return b''
        readline_side_effect.called_once = False

        def read_side_effect(size=1):
            nonlocal grbl_startup_message
            if grbl_startup_message:
                data_to_return = grbl_startup_message[:size]
                grbl_startup_message = grbl_startup_message[size:]
                mock_ser_instance.in_waiting = len(grbl_startup_message)
                return data_to_return
            mock_ser_instance.in_waiting = 0
            return b''

        # More robust way to handle readline for startup:
        # Configure readline to return the message then empty bytes.
        # Configure in_waiting to simulate data available then not.
        mock_ser_instance.readline.side_effect = [grbl_startup_message, b"", b""] # Subsequent calls return empty
        
        # This function will be called by the code for self.ser.in_waiting
        # It needs to reflect that data is available for the first readline call.
        # Configure readline to return the message then empty bytes.
        mock_ser_instance.readline.side_effect = [grbl_startup_message, b"", b""] # Subsequent calls return empty
        
        # This function will be called by the code for self.ser.in_waiting
        # It needs to reflect that data is available for the first readline call.
        def in_waiting_side_effect(*args, **kwargs): # Add *args, **kwargs for PropertyMock
            if mock_ser_instance.readline.call_count == 0: # Before first readline call
                return len(grbl_startup_message)
            # After the first call to readline (which consumes the startup message),
            # or if readline has been called multiple times for other reasons.
            return 0 

        # To make in_waiting a callable property that behaves like an attribute:
        # We use a PropertyMock for 'in_waiting'
        type(mock_ser_instance).in_waiting = unittest.mock.PropertyMock(side_effect=in_waiting_side_effect)
        # Ensure 'in_waiting' is treated as a property, not a method.
        # This makes `self.ser.in_waiting` (no parentheses) call in_waiting_side_effect.
        
        mock_serial_class.return_value = mock_ser_instance
        
        communicator = GRBLCommunicator("/dev/testport", 115200)
        
        # Patch time.sleep to avoid actual sleeping during test
        with patch('grbl_communicator.time.sleep'):
            communicator.connect()

        mock_serial_class.assert_called_once_with("/dev/testport", 115200, timeout=2)
        mock_ser_instance.flushInput.assert_called_once()
        mock_ser_instance.write.assert_called_once_with(b'\n')
        # Check readline was called at least once for the startup message,
        # and potentially more until timeout logic is met.
        self.assertGreaterEqual(mock_ser_instance.readline.call_count, 1)
        self.assertIsNotNone(communicator.ser)

    @patch('grbl_communicator.serial.Serial')
    def test_connect_successful_no_startup_message(self, mock_serial_class):
        mock_ser_instance = MagicMock()
        mock_ser_instance.is_open = True
        mock_ser_instance.in_waiting = 0
        mock_ser_instance.readline.return_value = b"" # No startup message
        mock_serial_class.return_value = mock_ser_instance

        communicator = GRBLCommunicator("/dev/testport", 115200)
        # Should not raise an error, but log a warning (logging is disabled for test)
        communicator.connect()

        mock_serial_class.assert_called_once_with("/dev/testport", 115200, timeout=2)
        mock_ser_instance.flushInput.assert_called_once()
        mock_ser_instance.write.assert_called_once_with(b'\n')
        self.assertIsNotNone(communicator.ser)

    @patch('grbl_communicator.serial.Serial', side_effect=serial.SerialException("Connection failed"))
    def test_connect_serial_exception_raises_connection_error(self, mock_serial_class):
        communicator = GRBLCommunicator("/dev/testport", 115200)
        with self.assertRaisesRegex(ConnectionError, "Failed to connect to GRBL on /dev/testport: Connection failed"):
            communicator.connect()
        self.assertIsNone(communicator.ser)

    @patch('grbl_communicator.serial.Serial', side_effect=Exception("Some other error"))
    def test_connect_other_exception_raises_connection_error(self, mock_serial_class):
        # Ensure ser.close is not called if ser is not successfully created
        mock_ser_instance = MagicMock()
        mock_serial_class.return_value = mock_ser_instance # To test closing logic
        mock_serial_class.side_effect = Exception("Some other error")


        communicator = GRBLCommunicator("/dev/testport", 115200)
        with self.assertRaisesRegex(ConnectionError, "An unexpected error occurred on /dev/testport: Some other error"):
            communicator.connect()
        self.assertIsNone(communicator.ser)
        # Check that if self.ser was somehow assigned before the exception, close would be attempted
        # This is tricky because the exception happens during serial.Serial() call itself in this mock.
        # If the exception happened *after* self.ser = serial.Serial(...), then ser.close() would be called.
        # The current code structure in GRBLCommunicator handles this well.

class TestGRBLCommunicatorSendCommand(unittest.TestCase):
    def setUp(self):
        self.communicator = GRBLCommunicator("/dev/testport", 115200)
        self.mock_ser_instance = MagicMock()
        self.mock_ser_instance.is_open = True
        self.communicator.ser = self.mock_ser_instance # Simulate connected state

    def test_send_command_successful(self):
        gcode_command = "G0 X10"
        expected_encoded_command = b"G0 X10\n"
        
        # Simulate GRBL's response: 'ok\r\n'
        # The send_command reads one char at a time.
        response_chars = list(b'ok\r\n')
        def read_side_effect(size=1):
            if read_side_effect.buffer:
                char = read_side_effect.buffer.pop(0)
                self.mock_ser_instance.in_waiting = len(read_side_effect.buffer)
                return bytes([char]) # Return as bytes
            self.mock_ser_instance.in_waiting = 0
            return b''
        read_side_effect.buffer = list(b'ok\r\n')
        self.mock_ser_instance.read.side_effect = read_side_effect
        self.mock_ser_instance.in_waiting = len(read_side_effect.buffer)

        result = self.communicator.send_command(gcode_command)

        self.mock_ser_instance.write.assert_called_once_with(expected_encoded_command)
        self.assertTrue(result)

    def test_send_command_grbl_error(self):
        gcode_command = "G0 X10"
        
        response_chars = list(b'error: Invalid GCode\r\n')
        def read_side_effect(size=1):
            if read_side_effect.buffer:
                char = read_side_effect.buffer.pop(0)
                self.mock_ser_instance.in_waiting = len(read_side_effect.buffer)
                return bytes([char])
            self.mock_ser_instance.in_waiting = 0
            return b''
        read_side_effect.buffer = list(b'error: Invalid GCode\r\n')
        self.mock_ser_instance.read.side_effect = read_side_effect
        self.mock_ser_instance.in_waiting = len(read_side_effect.buffer)

        with self.assertRaisesRegex(RuntimeError, "GRBL error: error: Invalid GCode"):
            self.communicator.send_command(gcode_command)
        self.mock_ser_instance.write.assert_called_once_with(b"G0 X10\n")

    @patch('grbl_communicator.time.time')
    def test_send_command_timeout(self, mock_time):
        gcode_command = "G0 X10"
        command_timeout = 0.1 # Use a small timeout for testing

        # Simulate time passing beyond timeout.
        # time.time() is called once at the start of the loop, then in each iteration.
        # The loop condition is `time.time() - start_time < command_timeout`
        # So, first call to time.time() is start_time (0).
        # Subsequent calls should make the condition false.
        # Iteration 1: time() -> 0.0 (start_time), time() -> 0.05. 0.05-0 < 0.1 is true.
        # Iteration 2: time() -> 0.11. 0.11-0 < 0.1 is false. Loop terminates.
        mock_time.side_effect = [0.0, 0.05, 0.11] 
        
        self.mock_ser_instance.in_waiting = 0
        self.mock_ser_instance.read.return_value = b'' # No response

        # Patch time.sleep inside send_command
        with patch('grbl_communicator.time.sleep'):
            with self.assertRaisesRegex(TimeoutError, f"Timeout waiting for 'ok' or 'error' from GRBL for command: {gcode_command}"):
                self.communicator.send_command(gcode_command, command_timeout=command_timeout)
        
        self.mock_ser_instance.write.assert_called_once_with(b"G0 X10\n")


    def test_send_command_not_connected(self):
        self.communicator.ser = None # Simulate not connected
        with self.assertRaisesRegex(ConnectionError, "Serial port not open. Connect first."):
            self.communicator.send_command("G0 X10")

        self.communicator.ser = MagicMock()
        self.communicator.ser.is_open = False # Simulate connected but port closed
        with self.assertRaisesRegex(ConnectionError, "Serial port not open. Connect first."):
            self.communicator.send_command("G0 X10")
    
    def test_send_command_serial_exception_on_write(self):
        self.mock_ser_instance.write.side_effect = serial.SerialException("Write failed")
        with self.assertRaisesRegex(ConnectionError, "Serial communication error: Write failed"):
            self.communicator.send_command("G0 X10")
        self.mock_ser_instance.close.assert_called_once() # Ensure port is closed on error

    def test_send_command_serial_exception_on_read(self):
        self.mock_ser_instance.read.side_effect = serial.SerialException("Read failed")
        self.mock_ser_instance.in_waiting = 1 # Simulate data available to trigger read

        with self.assertRaisesRegex(ConnectionError, "Serial communication error: Read failed"):
            self.communicator.send_command("G0 X10")
        self.mock_ser_instance.close.assert_called_once()


class TestGRBLCommunicatorClose(unittest.TestCase):
    def test_close_closes_open_port(self):
        communicator = GRBLCommunicator("/dev/testport", 115200)
        mock_ser_instance = MagicMock()
        mock_ser_instance.is_open = True
        communicator.ser = mock_ser_instance

        communicator.close()
        mock_ser_instance.close.assert_called_once()
        self.assertIsNone(communicator.ser)

    def test_close_handles_already_closed_port(self):
        communicator = GRBLCommunicator("/dev/testport", 115200)
        mock_ser_instance = MagicMock()
        mock_ser_instance.is_open = False # Port is already closed
        communicator.ser = mock_ser_instance

        communicator.close()
        # ser.close() should not be called if port is not open,
        # but the implementation calls it and serial.Serial handles it gracefully.
        # For strictness, we could check it's not called, but current code calls it.
        # Let's verify it doesn't raise an error.
        mock_ser_instance.close.assert_not_called() # Ideal, but current code might call it.
                                                 # The GRBLCommunicator's close checks `is_open`.
        self.assertIsNone(communicator.ser)


    def test_close_handles_no_serial_object(self):
        communicator = GRBLCommunicator("/dev/testport", 115200)
        communicator.ser = None # No serial object

        communicator.close() # Should not raise any error
        self.assertIsNone(communicator.ser)

    def test_close_serial_exception_on_close(self):
        communicator = GRBLCommunicator("/dev/testport", 115200)
        mock_ser_instance = MagicMock()
        mock_ser_instance.is_open = True
        mock_ser_instance.close.side_effect = serial.SerialException("Failed to close")
        communicator.ser = mock_ser_instance

        # The method should catch the exception and log an error, but not re-raise
        try:
            communicator.close()
        except serial.SerialException:
            self.fail("communicator.close() raised SerialException unexpectedly!")
        
        mock_ser_instance.close.assert_called_once()
        self.assertIsNone(communicator.ser) # ser should still be set to None

if __name__ == '__main__':
    unittest.main(verbosity=2)
