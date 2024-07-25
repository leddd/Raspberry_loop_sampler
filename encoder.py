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

counter = 0
direction = DIRECTION_CW
CLK_state = 0
prev_CLK_state = 0

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
prev_DT_state = GPIO.input(DT_PIN)

# Function to handle rotary encoder
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, prev_DT_state

    # Read the current state of the rotary encoder's CLK and DT pins
    CLK_state = GPIO.input(CLK_PIN)
    DT_state = GPIO.input(DT_PIN)

    # If the state of CLK is changed, then pulse occurred
    if CLK_state != prev_CLK_state:
        # Determine the direction
        if DT_state != CLK_state:
            counter += 1
            direction = DIRECTION_CW
        else:
            counter -= 1
            direction = DIRECTION_CCW

        print("Rotary Encoder:: direction:", "CLOCKWISE" if direction == DIRECTION_CW else "ANTICLOCKWISE",
              "- count:", counter)

    # Save last CLK and DT state
    prev_CLK_state = CLK_state
    prev_DT_state = DT_state

# Function to handle button press on rotary encoder
def handle_encoder_button():
    global button_pressed, prev_button_state

    # State change detection for the button
    button_state = GPIO.input(SW_PIN)
    if button_state != prev_button_state:
        time.sleep(0.01)  # Add a small delay to debounce
        if button_state == GPIO.LOW:
            print("Rotary Encoder Button:: The button is pressed")
            button_pressed = True
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
