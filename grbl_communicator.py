import serial
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GRBLCommunicator:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        logging.info(f"GRBLCommunicator initialized with port={self.port}, baudrate={self.baudrate}")

    def connect(self):
        logging.info(f"Attempting to connect to GRBL on {self.port} at {self.baudrate} baud.")
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            logging.info("Serial port opened. Waiting for GRBL to initialize...")
            time.sleep(2)  # Wait for GRBL to initialize

            # Wake up GRBL and clear buffer
            # A soft reset (Ctrl-X) or a newline can be used.
            # Ctrl-X is often \x18 in bytes.
            # Sending a newline might be safer initially.
            self.ser.flushInput()  # Clear input buffer before sending commands
            
            # Sending a newline character to ensure GRBL is awake and to clear any partial commands.
            self.ser.write(b'\n') 
            # Alternative: self.ser.write(b'\x18') # Soft reset

            # Read and discard startup messages.
            # GRBL usually sends a welcome message like "Grbl 1.1h ['$' for help]"
            # We'll read for a short period or until no more data comes.
            startup_message = ""
            start_time = time.time()
            while time.time() - start_time < 2: # Read for up to 2 seconds
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        startup_message += line + "\n"
                        logging.info(f"GRBL Startup: {line}")
                else:
                    time.sleep(0.05) # Small delay to avoid busy waiting

            if not startup_message:
                logging.warning("No startup message received from GRBL. This might be okay.")
            
            # A more robust check would be to send a status command '?' and expect 'ok'
            # For now, we assume connection is successful if no serial exception occurred.
            logging.info("GRBL connection established.")

        except serial.SerialException as e:
            logging.error(f"Failed to connect to GRBL: {e}")
            self.ser = None # Ensure ser is None if connection failed
            raise ConnectionError(f"Failed to connect to GRBL on {self.port}: {e}")
        except Exception as e: # Catch any other unexpected errors during connection
            logging.error(f"An unexpected error occurred during connection: {e}")
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None
            raise ConnectionError(f"An unexpected error occurred on {self.port}: {e}")


    def send_command(self, gcode_line, command_timeout=10.0):
        if not self.ser or not self.ser.is_open:
            logging.error("Serial port not open. Cannot send command.")
            raise ConnectionError("Serial port not open. Connect first.")

        try:
            command = gcode_line.strip() + '\n'
            logging.info(f"Sending G-code command: {command.strip()}")
            self.ser.write(command.encode('utf-8'))

            response_buffer = ""
            start_time = time.time()

            while time.time() - start_time < command_timeout:
                if self.ser.in_waiting > 0:
                    char = self.ser.read().decode('utf-8', errors='ignore')
                    response_buffer += char
                    if response_buffer.endswith('ok\r\n'):
                        logging.info(f"Received 'ok' for command: {command.strip()}")
                        return True
                    if response_buffer.strip().startswith('error:'):
                        # Try to read the rest of the error line until a newline
                        # or timeout to capture the full error message.
                        while not response_buffer.endswith('\n') and (time.time() - start_time < command_timeout):
                            if self.ser.in_waiting > 0:
                                char_more = self.ser.read().decode('utf-8', errors='ignore')
                                response_buffer += char_more
                            else:
                                time.sleep(0.005) # Shorter sleep while actively fetching rest of error
                        
                        error_message = response_buffer.strip()
                        logging.error(f"GRBL error for command '{command.strip()}': {error_message}")
                        raise RuntimeError(f"GRBL error: {error_message}")
                else:
                    time.sleep(0.01) # Short sleep to prevent busy-waiting

            logging.error(f"Timeout waiting for response to command: {command.strip()}")
            raise TimeoutError(f"Timeout waiting for 'ok' or 'error' from GRBL for command: {command.strip()}")

        except serial.SerialException as e:
            logging.error(f"Serial communication error during send_command: {e}")
            self.close() # Attempt to close port on error
            raise ConnectionError(f"Serial communication error: {e}")
        except RuntimeError: # Re-raise RuntimeError from GRBL error
            raise
        except TimeoutError: # Re-raise TimeoutError
            raise
        except Exception as e: # Catch any other unexpected errors
            logging.error(f"An unexpected error occurred during send_command: {e}")
            self.close()
            raise RuntimeError(f"An unexpected error occurred sending command: {e}")

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                logging.info("Serial port closed.")
            except serial.SerialException as e:
                logging.error(f"Error closing serial port: {e}")
        else:
            logging.info("Serial port was not open or already closed.")
        self.ser = None

if __name__ == '__main__':
    # This is example usage, not part of the class itself.
    # It's good for basic testing if you have a GRBL device connected.
    # For actual use, this would be imported into another script.
    
    # Replace with your actual port and baudrate
    # On Linux, it might be /dev/ttyUSB0 or /dev/ttyACM0
    # On Windows, it might be COM3, COM4, etc.
    GRBL_PORT = "/dev/ttyUSB0" # Example, change this!
    GRBL_BAUDRATE = 115200

    # Example of how to use the GRBLCommunicator
    # Note: This will try to connect to a real device.
    # If you don't have one, this part will fail.
    
    # communicator = None
    # try:
    #     communicator = GRBLCommunicator(port=GRBL_PORT, baudrate=GRBL_BAUDRATE)
    #     communicator.connect()
        
    #     # Example commands
    #     # Ensure GRBL is in a known state (e.g., by homing or unlocking if needed)
    #     # For testing, simple status commands are safest.
    #     if communicator.send_command("$#"): # View G-code parameters
    #         print("Successfully sent '$#' and got ok")

    #     if communicator.send_command("G0 X1 F100"): # Simple move command
    #         print("Successfully sent 'G0 X1 F100' and got ok")
            
    # except ConnectionError as e:
    #     print(f"Connection Error: {e}")
    # except RuntimeError as e:
    #     print(f"Runtime Error: {e}")
    # except TimeoutError as e:
    #     print(f"Timeout Error: {e}")
    # except Exception as e:
    #     print(f"An unexpected error occurred: {e}")
    # finally:
    #     if communicator:
    #         communicator.close()

    print("GRBLCommunicator class defined. Example usage (commented out) requires a GRBL device.")
    print("To use this class, import it into your main application script.")
