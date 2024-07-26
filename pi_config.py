import time
import threading
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c, spi
from luma.oled.device import sh1106

def setup_rotary_encoder():
    global CLK_PIN, DT_PIN, SW_PIN, DIRECTION_CW, DIRECTION_CCW, prev_CLK_state, lock, direction, counter, button_pressed, prev_button_state

    # Define the GPIO pins for the rotary encoder
    CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
    DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
    SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

    DIRECTION_CW = 0
    DIRECTION_CCW = 1

    counter = 0
    direction = DIRECTION_CW
    prev_CLK_state = GPIO.HIGH
    button_pressed = False
    prev_button_state = GPIO.HIGH

    lock = threading.Lock()
    
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

def setup_matrix_keypad():
    global row_pins, col_pins, rows, key_map, debounce_time
    debounce_time = 0.02  # 50 ms debounce time

    # Define the GPIO pins for rows and columns of the matrix keypad
    row_pins = [12, 1]
    col_pins = [13, 6, 5]

    # Initialize buttons for rows with pull-down resistors
    rows = [Button(pin, pull_up=False) for pin in row_pins]

    # Set up columns as output and set them to high
    for col in col_pins:
        GPIO.setup(col, GPIO.OUT)
        GPIO.output(col, GPIO.HIGH)

    # Dictionary to hold the key mapping for matrix keypad
    key_map = {
        (1, 13): 1, (1, 6): 2, (1, 5): 3,
        (12, 13): 4, (12, 6): 5, (12, 5): 6
    }

    # Attach the callback function to the button press event for each row
    for row in rows:
        row.when_pressed = lambda row=row: matrix_button_pressed(row)

def matrix_button_pressed(row_pin):
    global current_config_option

    # Disable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.LOW)

    # Detect which button was pressed
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)
        time.sleep(debounce_time)  # Debounce delay
        if row_pin.is_pressed:
            key = key_map.get((row_pin.pin.number, col), None)
            if key:
                print(f"Matrix Keypad:: Key pressed: {key}")
                if key == 1:  # Advance configuration option when key 1 is pressed
                    with lock:
                        current_config_option = (current_config_option + 1) % len(config_options)
                        print(f"Switched to: {config_options[current_config_option]}")
        GPIO.output(col, GPIO.LOW)

    # Re-enable all column outputs
    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

# CONFIG options
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 4
}
time_signature_options = ["2/4", "3/4", "4/4"]
current_config_option = 0

# Set up the rotary encoder and matrix keypad
setup_rotary_encoder()
setup_matrix_keypad()

def draw_config_screen():
    global current_config_option
    with lock:
        # Create an image in portrait mode dimensions
        image = Image.new('1', (64, 128), "black")
        draw = ImageDraw.Draw(image)
        
        # Load a custom font
        font_size = 12  # Adjust the font size as needed
        font = ImageFont.truetype(font_path, font_size)

        # Draw config option
        option = config_options[current_config_option]
        if option == "BPM":
            value = f"{config_option_values[option]} BPM"
        elif option == "TIME SIGNATURE":
            value = config_option_values[option]
        elif option == "TOTAL BARS":
            value = f"{config_option_values[option]} BARS"

        # Calculate text position
        bbox = draw.textbbox((0, 0), value, font=font)  # Get bounding box
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (64 - text_width) // 2
        text_y = (128 - text_height) // 2  # Slightly below center, moved 5 pixels up

        # Draw text on the screen
        draw.text((text_x, text_y), value, font=font, fill="white")
        
        # Rotate the image by 90 degrees to fit the landscape display
        rotated_image = image.rotate(270, expand=True)
        
        # Display the rotated image on the device
        device.display(rotated_image)

def handle_rotary_encoder():
    global counter, direction, prev_CLK_state, current_config_option
    while True:
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
                with lock:
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

        time.sleep(0.001)  # Small delay to prevent CPU overuse

def update_screen():
    while True:
        draw_config_screen()
        time.sleep(0.1)  # Update the screen every 0.1 seconds

try:
    print(f"Listening for rotary encoder changes and button presses...")

    # Start threads for handling the rotary encoder, button press, and screen update
    threading.Thread(target=handle_rotary_encoder, daemon=True).start()
    threading.Thread(target=update_screen, daemon=True).start()

    # Keep the main thread running
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
