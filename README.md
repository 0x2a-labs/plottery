# Plottery - G-code Visualizer for Pen Plotters

A web-based G-code visualizer and job management tool for pen plotters.

![Plottery Screenshot](./static/images/screenshot.png)

## Features

- Upload or paste G-code files
- 2D top-down visualization using HTML Canvas
- Y-axis flipped (origin at top-left, Y increases downward)
- Support for G0, G1, G2, G3 commands:
  - G0 (rapid moves) shown as dashed gray lines
  - G1 (drawing moves) shown as solid black lines
  - G2/G3 (arc moves) with radius (R) and center (I/J) format support
- Line color based on Z height (lower Z = darker color)
- Bounding box display around drawing area
- Manual jogging controls for X/Y/Z
- Job sending functionality to GRBL-compatible plotters
- Current tool position shown as a red dot

## Setup and Installation

1. Clone this repository
2. Create a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This will install Flask, pyserial, and other necessary packages.
4. Configure Plotter Connection (Optional):
   If you intend to connect to a GRBL plotter, you might need to update the serial port and baud rate settings in `app.py`. See the "Plotter Backend > Configuration" section for details.
5. Run the application:
   ```bash
   python app.py
   ```
6. Open your browser and navigate to `http://127.0.0.1:5000` (or the host/port shown in the terminal, e.g., `http://0.0.0.0:5000`).

## Usage

- Paste G-code into the text area or upload a .gcode file
- Click "Visualize" to render the G-code on the canvas
- Use jogging controls to move the virtual tool (visualization only)
- Click "Send Job" to send the G-code to your configured GRBL plotter.

## Project Structure

- `app.py` - Flask application entry point, includes GRBL communication logic.
- `grbl_communicator.py` - Module for handling serial communication with GRBL devices.
- `requirements.txt` - Python package dependencies.
- `templates/` - HTML templates
- `static/` - Static assets
  - `css/style.css` - Main stylesheet
  - `js/gcode-parser.js` - G-code parsing logic
  - `js/gcode-renderer.js` - Canvas rendering logic
  - `js/visualizer.js` - Main application logic
- `test_grbl_communicator.py` - Unit tests for `grbl_communicator.py`.

## Technical Details

- Built as a Flask web application
- Frontend uses HTML5 Canvas for visualization
- Backend uses `pyserial` for GRBL communication
- Modular JavaScript architecture:
  - GCodeParser class for parsing G-code
  - GCodeRenderer class for canvas rendering
- Modern JavaScript (ES6+)
- Responsive design

## Plotter Backend

This application now supports sending G-code jobs directly to GRBL-compatible pen plotters. The backend uses the `pyserial` library to communicate with the plotter over a serial connection, managed by the `GRBLCommunicator` class found in `grbl_communicator.py`.

### Configuration

To connect to your plotter, you may need to configure the serial port and baud rate:

-   **Location**: These settings are defined as constants at the top of the `app.py` file:
    -   `DEFAULT_SERIAL_PORT`: The serial port your plotter is connected to.
    -   `DEFAULT_BAUDRATE`: The baud rate your plotter uses for communication.
-   **Default Values**:
    -   `DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"`
    -   `DEFAULT_BAUDRATE = 115200`
-   **Finding Your Serial Port**:
    -   **Linux**: Check common device paths like `/dev/ttyUSB*` or `/dev/ttyACM*`. You can use the command `dmesg | grep -i "ttyS\\|ttyUSB\\|ttyACM"` (run as root or with sudo if needed) shortly after connecting your device to see which port it's assigned.
    -   **Windows**: Open Device Manager (search for "Device Manager" in the Start Menu). Look under "Ports (COM & LPT)". Your plotter will likely appear as a "USB Serial Port" or similar, listed with a `COMx` number (e.g., `COM3`).
    -   **macOS**: Check devices starting with `/dev/tty.*`. In the terminal, run `ls /dev/tty.*`. Common names include `/dev/tty.usbmodemXXXX` or `/dev/tty.usbserial-XXXX`.

### Dependencies

Serial communication with the plotter requires the `pyserial` library. This library is listed in the `requirements.txt` file.

To ensure all dependencies, including `pyserial`, are installed, run the following command in your activated virtual environment (as mentioned in the "Setup and Installation" section):
```bash
pip install -r requirements.txt
```

## Future Enhancements

- Real-time job progress and status feedback from the plotter
- Job queue management
- G-code generation from SVG files
- More advanced visualization features (e.g., toolpath simulation)
- Emergency stop / pause / resume functionality for plotter jobs
- Web-based configuration for serial port/baud rate