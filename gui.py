import time
import RPi.GPIO as GPIO
from gpiozero import Button
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

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

# Define the GPIO pins for the rotary encoder
CLK_PIN = 17  # GPIO7 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO8 connected to the rotary encoder's DT pin
SW_PIN = 22   # GPIO25 connected to the rotary encoder's SW pin

counter = 0
direction = 0  # 0: CW, 1: CCW
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
GPIO.setup(CLK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def draw_config_screen():
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
    text_y = (128 - text_height) // 2 + 8  # Slightly below center, moved 5 pixels up

    # Draw text on the screen
    draw.text((text_x, text_y), value, font=font, fill="white")
    
    # Rotate the image by 90 degrees to fit the landscape display
    rotated_image = image.rotate(270, expand=True)
    
    # Display the rotated image on the device
    device.display(rotated_image)
    print(f"Current Config Option: {option} - {value}")

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
            counter += 1
            direction = 0  # CW
        else:
            counter -= 1
            direction = 1  # CCW

        if direction == 0:
            current_config_option = (current_config_option + 1) % len(config_options)
        else:
            current_config_option = (current_config_option - 1) % len(config_options)

        draw_config_screen()

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
            # Toggle through the values for the current configuration option
            option = config_options[current_config_option]
            if option == "BPM":
                config_option_values[option] += 1
                if config_option_values[option] > 200:
                    config_option_values[option] = 60
            elif option == "TIME SIGNATURE":
                index = time_signature_options.index(config_option_values[option])
                index = (index + 1) % len(time_signature_options)
                config_option_values[option] = time_signature_options[index]
            elif option == "TOTAL BARS":
                config_option_values[option] += 1
                if config_option_values[option] > 16:
                    config_option_values[option] = 1

            draw_config_screen()
        else:
            button_pressed = False

    prev_button_state = button_state

try:
    print(f"Listening for rotary encoder changes and button presses...")
    draw_config_screen()  # Draw the initial config screen
    while True:
        handle_rotary_encoder()
        handle_encoder_button()
        time.sleep(0.001)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()  # Clean up GPIO on program exit
