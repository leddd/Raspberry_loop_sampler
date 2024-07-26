import time
import RPi.GPIO as GPIO
from gpiozero import Button
from signal import pause

# Define the GPIO pins for the rotary encoder
CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

DIRECTION_CW = 0
DIRECTION_CCW = 1

# Configuration options and initial values
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 4
}
time_signature_options = ["2/4", "3/4", "4/4"]
current_config_option = 0

counter = 0
direction = DIRECTION_CW
prev_CLK_state = GPIO.HIGH

button_pressed = False
prev_button_state = GPIO.HIGH

# Disable GPIO warnings
GPIO.setwarnings(False)

# Reset the GPIO pins
GPIO.cleanup()

# Set up the GPIO mode
GPIO.setmode(GPIO.BCM)

# Set up GPIO pins for rotary encoder
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Read the initial state of the rotary encoder's CLK pin
prev_CLK_state = GPIO.input(CLK_PIN)

# Function to handle rotary encoder
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, current_config_option

    # Read the current state of the rotary encoder's CLK and DT pins
    CLK_state = GPIO.input(CLK_PIN)
    DT_state = GPIO.input(DT_PIN)

    # If the state of CLK is changed, then pulse occurred
    if CLK_state != prev_CLK_state:
        # Determine the direction
        if DT_state != CLK_state:
            direction = DIRECTION_CW
        else:
            direction = DIRECTION_CCW

        counter += 1
        if counter % 2 == 0:  # Only update on every second step
            option = config_options[current_config_option]
            if option == "BPM":
                if direction == DIRECTION_CW:
                    config_option_values[option] += 1
                    if config_option_values[option] > 200:
                        config_option_values[option] = 200
                else:
                    config_option_values[option] -= 1
                    if config_option_values[option] < 40:
                        config_option_values[option] = 40
            elif option == "TIME SIGNATURE":
                index = time_signature_options.index(config_option_values[option])
                if direction == DIRECTION_CW:
                    index = (index + 1) % len(time_signature_options)
                else:
                    index = (index - 1) % len(time_signature_options)
                config_option_values[option] = time_signature_options[index]
            elif option == "TOTAL BARS":
                if direction == DIRECTION_CW:
                    config_option_values[option] += 1
                    if config_option_values[option] > 16:
                        config_option_values[option] = 16
                else:
                    config_option_values[option] -= 1
                    if config_option_values[option] < 1:
                        config_option_values[option] = 1

            print(f"{option}: {config_option_values[option]}")

    # Save last CLK state
    prev_CLK_state = CLK_state

# Function to handle button press on rotary encoder
def handle_encoder_button():
    global button_pressed, prev_button_state, current_config_option

    # State change detection for the button
    button_state = GPIO.input(SW_PIN)
    if button_state != prev_button_state:
        time.sleep(0.01)  # Add a small delay to debounce
        if button_state == GPIO.LOW:
            print("Rotary Encoder Button:: The button is pressed")
            button_pressed = True
            # Move to the next configuration option
            current_config_option = (current_config_option + 1) % len(config_options)
            print(f"Switched to: {config_options[current_config_option]}")
        else:
            button_pressed = False

    prev_button_state = button_state

try:
    print(f"Listening for rotary encoder changes and button presses...")
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.001)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
