from flask import Flask, render_template, request, jsonify
import os
import logging
from grbl_communicator import GRBLCommunicator

# Configure basic logging for the app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default GRBL connection parameters
DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"  # Common for Linux, use "COMx" for Windows if needed
DEFAULT_BAUDRATE = 115200

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/send_job', methods=['POST'])
def send_job():
    gcode = request.json.get('gcode', '')

    if not gcode:
        logging.warning("send_job called with no G-code.")
        return jsonify({'status': 'error', 'message': 'No G-code provided.'}), 400

    logging.info(f"Received G-code job. First 50 chars: {gcode[:50]}...")

    communicator = None  # Initialize communicator to None for the finally block
    try:
        communicator = GRBLCommunicator(port=DEFAULT_SERIAL_PORT, baudrate=DEFAULT_BAUDRATE)
        logging.info(f"Attempting to connect to GRBL on {DEFAULT_SERIAL_PORT} at {DEFAULT_BAUDRATE} baud.")
        communicator.connect()
        logging.info("Successfully connected to GRBL.")

        gcode_lines = gcode.strip().split('\n')
        total_lines = len(gcode_lines)
        logging.info(f"Starting to send {total_lines} G-code lines.")

        for i, line in enumerate(gcode_lines):
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('('): # Ignore empty lines and comments
                logging.info(f"Skipping empty line or comment: {line}")
                continue
            
            logging.info(f"Sending line {i+1}/{total_lines}: {line}")
            communicator.send_command(line)
            logging.info(f"Successfully sent line: {line}")

        logging.info("All G-code commands sent successfully.")
        return jsonify({'status': 'success', 'message': 'Job sent to plotter successfully.'})

    except ConnectionError as e:
        logging.error(f"Connection failed: {e}")
        return jsonify({'status': 'error', 'message': f'Connection failed: {str(e)}'}), 500
    except RuntimeError as e: # GRBL reported error
        logging.error(f"GRBL error: {e}")
        return jsonify({'status': 'error', 'message': f'GRBL error: {str(e)}'}), 400
    except TimeoutError as e:
        logging.error(f"GRBL timeout: {e}")
        return jsonify({'status': 'error', 'message': f'GRBL timeout: {str(e)}'}), 400
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred: {e}", exc_info=True) # Log stack trace
        return jsonify({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}), 500
    finally:
        if communicator:
            logging.info("Closing GRBL connection.")
            communicator.close()

if __name__ == '__main__':
    # Use host='0.0.0.0' to make it accessible from the network if needed for testing
    # debug=True is useful for development but should be False in production
    app.run(host='0.0.0.0', port=5000, debug=True)
