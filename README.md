This project implements a linear-motion test bench for DC arc fault analysis in PV systems.

It includes the following files:
- `main.py`: firmware that goes into the esp32c3-mini. It control's the test bench linear motion.

# Pre-requisits:
- python 3.0
- micropython
- mpremote

# How to comunicate with the control board
To start communication with the esp32, follow these steps:
- connect the esp32 board through an usbc (be sure the usb allows data transfer, not only charging) to the computer. 
- With the mpremote installed, open the terminal and type: `mpremote`. It should be enough to stabilish connection. If not, use `mpremote connect XX`, where XX your serial device.
- Once you are connected, you should see something like in the image below. If not, press, Enter to show the `>` in the terminal. If you still dont get anything, then press CTRL+D, it should soft-reboot the board.

# To power the board
The board is pretty simple. 
- With the 12V supply disconnected, connect the stepper motor four pins to the board. Note that orientation will affect the motion of the linear system.
- After connect the motor to the board, connect the 12V supply.
- Connect the esp devkit to your PC through a usbc cable. just be sure it allows data transfer and not only charging.

# Available commands
You are connected to the board, but how do you manipulate hardware. In the table bellow, are listed the commands available. You just need to type the desired action -- followed by the parameter, if it needs -- and press enter.

* Just make sure the stepper motor is connected to the four pins in the board. Be aware the orientation you had placed the pins will affect the motor orientation, thus the linear motion movement. You can either invert the pins in the board to correct the movement orientation (**make sure the 12V supply is off, when connecting or changing orientation**) or just use a negative sign (-) in the command.

| Command | Parameters | Description | Example | Saved to Flash? |
| :--- | :--- | :--- | :--- | :--- |
| `EN` | *None* | Enables the A4988 driver (sets the `ENABLE` pin to logic LOW), energizing the motor coils. | `EN` | Yes |
| `DIS` | *None* | Disables the A4988 driver (sets the `ENABLE` pin to logic HIGH), releasing the motor shaft. | `DIS` | Yes |
| `ZERO` | *None* | Sets the current mechanical position as the system origin (`0.0000 mm`). | `ZERO` | No (RAM) |
| `DIST` | `<mm>` | Executes a **relative** movement from the current position. Negative values reverse the direction. | `DIST,10.5`<br>`DIST,-5` | No |
| `POS` | `<mm>` | Executes an **absolute** movement to the specified coordinate relative to the `ZERO` point. | `POS,25`<br>`POS,0` | No |
| `MP` | `<divisor>` | Sets the microstepping factor using standard divisors (`1`, `2`, `4`, `8`, or `16`). | `MP,16` | Yes |
| `MP` | `<ms1>,<ms2>,<ms3>` | Sets microstepping by directly configuring the logic levels (`0` or `1`) of pins MS1, MS2, and MS3. | `MP,1,0,0` | Yes |
| `VEL` | `<mm/s>` | Sets the linear travel speed within the safety limit (`VELOCIDADE_MAX`). | `VEL,5.5` | Yes |
| `STATUS` | *None* | Displays the driver state, current position, active microstepping, resolution, speed, and pulse interval. | `STATUS` | No |
| `HELP` | *None* | Lists all available commands and their syntax directly in the terminal. | `HELP` | No |

## Command Chaining

Multiple commands can be sent on the same line separated by a semicolon (`;`). They will be executed sequentially:

```text
EN;ZERO;DIST,15;DIST,-5;POS,0;STATUS
```
