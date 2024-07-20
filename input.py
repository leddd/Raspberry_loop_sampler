from gpiozero import Button
from signal import pause
import RPi.GPIO as GPIO
import time

# Define the GPIO pins for rows and columns of the matrix keypad
row_pins = [12, 1]
col_pins = [13, 6, 5]

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

# Initialize buttons for rows with pull-down resistors
rows = [Button(pin, pull_up=False) for pin in row_pins]

# Set up columns as output and set them to high
for col in col_pins:
    GPIO.setup(col, GPIO.OUT)
    GPIO.output(col, GPIO.HIGH)

# Set up GPIO pins for rotary encoder
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Read the initial state of the rotary encoder's CLK pin
prev_CLK_state = GPIO.input(CLK_PIN)

# Dictionary to hold the key mapping for matrix keypad
key_map = {
    (12, 13): 1, (12, 6): 2, (12, 5): 3,
    (1, 13): 4, (1, 6): 5, (1, 5): 6
}

# Function to handle the button press on the matrix keypad
def matrix_button_pressed(row_pin):
    # Disable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.LOW)

    # Detect which button was pressed
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)
        time.sleep(0.01)  # Debounce delay
        if row_pin.is_pressed:
            key = key_map.get((row_pin.pin.number, col), None)
            if key:
                print(f"Matrix Keypad:: Key pressed: {key}")
        GPIO.output(col, GPIO.LOW)

    # Re-enable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)

# Attach the callback function to the button press event for each row
for row in rows:
    row.when_pressed = lambda row=row: matrix_button_pressed(row)

# Function to handle rotary encoder
def handle_rotary_encoder():
    global counter, direction, prev_CLK_state

    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)

    # If the state of CLK is changed, then pulse occurred
    # React to only the rising edge (from LOW to HIGH) to avoid double count
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        # Decrease the counter
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            counter -= 1
            direction = DIRECTION_CCW
        else:
            # The encoder is rotating in clockwise direction => increase the counter
            counter += 1
            direction = DIRECTION_CW

        print("Rotary Encoder:: direction:", "CLOCKWISE" if direction == DIRECTION_CW else "ANTICLOCKWISE",
              "- count:", counter)

    # Save last CLK state
    prev_CLK_state = CLK_state

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
    print(f"Listening for button presses on matrix keypad and rotary encoder...")
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
