# Pi Pico W Voltage Controller

## Project Overview
A PWM / frequency controller for BLDC fans or other loads using a Raspberry Pi Pico W (MicroPython). The repository includes:

- `main_PWM.py`: (TODO) Direct PWM duty control (for voltage-like control). Supports a rotary encoder, two physical buttons (A/B), a run/stop button and an IR remote (NEC).
- `main_CLK.py`: Frequency-based control (fan speed control). Supports relays for start/stop and swing, saves last speed to `data.csv`, and supports IR remote (Mitsubishi-style) and rotary encoder.
- `RotateEncoder.py`: Rotary encoder helper with switch, IRQ-based debounce and detent handling.
- `ir_rx/`: IR remote decoding library (NEC, Samsung, Mitsubishi, etc.) with tests and helpers.

## Features
- Adjust PWM duty or frequency with a rotary encoder
- IR remote control support (NEC / Mitsubishi styles)
- Physical push buttons for step changes and Stop
- Save last speed in `main_CLK` mode to `data.csv`

## Required Hardware
- Raspberry Pi Pico W (RP2040)
- Rotary encoder (A/B + switch)
- IR receiver (e.g., TSOP382)
- Relay or driver circuit for BLDC fan start/stop and swing (if applicable)
- Jumper wires, breadboard, and a suitable power supply for the fan

## Pinout (as used in the code)
(main_PWM.py)
- PWM output: `GP20` (Pin 20)
- Run/Break button: `GP0` (Pull-up)
- Button A: `GP6` (Pull-down)
- Button B: `GP7` (Pull-down)
- IR receiver: `GP16`
- Encoder: DT = `GP4`, CLK = `GP5`, SW = `GP2`

(main_CLK.py)
- PWM output (frequency): `GP20`
- Break_Pin (button): `GP0`
- Fan Start/Stop signal (pull to GND): `GP6`
- Fan Swing Relay: `GP7`
- Input LED: `GP8`
- Power LED: `GP9`
- IR receiver: `GP16`
- Encoder: DT = `GP4`, CLK = `GP5`, SW = `GP3` (note: SW pin differs compared to `main_PWM`)

* Note: Double-check your wiring and hardware setup before applying power.

## Setup & Environment
1. Flash MicroPython for the Pico W (RP2) using Thonny or your preferred tool: https://www.raspberrypi.com/documentation/microcontrollers/micropython.html
2. Connect the Pico W to your computer and upload files using Thonny or `mpremote`: `main_PWM.py`, `main_CLK.py`, `RotateEncoder.py`, the `ir_rx/` folder and (optionally) `data.csv`.
3. Run the desired mode by making it `main.py` or importing the module from the REPL: `import main_PWM` or `import main_CLK`.

Example using mpremote:
```
mpremote connect usb cp main_PWM.py :/main.py
mpremote connect usb repl run main.py
```
(Or use Thonny to upload and run the file.)

## Usage
- main_PWM:
  - Rotate the encoder to change `target_value` (duty_u16).
  - Buttons A/B increment/decrement the target value.
  - NEC IR remote buttons are mapped in code to increase/decrease and power toggle.
  - Press the run button (GP0) to break the loop and stop the script.

- main_CLK:
  - Rotate the encoder to change the fan frequency.
  - Press the encoder switch to toggle swing mode.
  - Mitsubishi-style remote mapping supports Power/Increase/Decrease/Swing_ON/Swing_OFF.
  - Last speed is saved to `data.csv` when changed.

## Quick Configuration
- main_PWM.py defaults: `digital_Min = 10535`, `digital_Max = 63535`, `digital_step = 1000`, `freq_value = 5000` (Hz)
- main_CLK.py defaults: `digital_Min = 50`, `digital_Max = 300`, `digital_step = 5`, `duty_count = 32768`

Edit those constants in the source if you need to adapt to your hardware.

## Troubleshooting
- No IR input: verify IR receiver is connected to `GP16` and oriented correctly; try `ir_rx/test.py`.
- Encoder not responding: check pull-ups/pull-downs and that DT/CLK/SW pins are wired correctly.
- Fan does not run: verify relay/driver circuit and that PWM or start/stop signals match your fan control hardware.
- Use `print()` statements (already used in code) to observe variable changes while debugging.

## Contributing & Development
- Open an issue for feature requests or bugs.
- Send a pull request for small fixes with a description of changes and how to test.

## License
The `ir_rx/` code is derived from Peter Hinch's project and is MIT licensed. Add a project-wide `LICENSE` file if you want to explicitly apply MIT or another license to this repo.
