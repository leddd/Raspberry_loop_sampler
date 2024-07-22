import time
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

# Configuration variables
total_beats = 4  # Change this value for different total beats
beat_interval = 0.5  # Time in seconds between beats, can be changed later
time_signature = "4/4"  # Change this to "2/4", "3/4", or "6/8" as needed

# Dictionary to store image paths for each time signature
beat_images = {
    "2/4": ['screens/2-4_1.png', 'screens/2-4_2.png'],
    "3/4": ['screens/3-4_1.png', 'screens/3-4_2.png', 'screens/3-4_3.png'],
    "4/4": ['screens/4-4_1.png', 'screens/4-4_2.png', 'screens/4-4_3.png', 'screens/4-4_4.png'],
    "6/8": ['screens/6-8_1.png', 'screens/6-8_2.png', 'screens/6-8_3.png', 'screens/6-8_4.png', 'screens/6-8_5.png', 'screens/6-8_6.png']
}

# Load the beat images
beat_images_loaded = {}
for key, paths in beat_images.items():
    beat_images_loaded[key] = [Image.open(path).convert('1') for path in paths]

# Define the GPIO pins for the rotary encoder
CLK_PIN = 22  # GPIO22 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO27 connected to the rotary encoder's DT pin
SW_PIN = 17   # GPIO17 connected to the rotary encoder's SW pin

# Set up GPIO pins for rotary encoder
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

prev_CLK_state = GPIO.input(CLK_PIN)
button_pressed = False

def draw_countdown_image(image, text):
    rotated_image = image.rotate(270, expand=True)
    draw = ImageDraw.Draw(rotated_image)

    # Load a custom font
    font_size = 30  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (rotated_image.width - text_width) // 2
    text_y = (rotated_image.height - text_height) // 2

    # Draw text on the image
    draw.text((text_x, text_y), text, font=font, fill="white")  # White text

    # Display the image on the OLED screen
    device.display(rotated_image)

def countdown(total_beats, beat_interval, beat_images):
    beat_count = total_beats
    images = beat_images_loaded[time_signature]

    try:
        while beat_count > 0:
            # Display the current beat image with the countdown number overlay
            image_index = total_beats - beat_count
            draw_countdown_image(images[image_index], str(beat_count))
            time.sleep(beat_interval)
            beat_count -= 1

    except KeyboardInterrupt:
        GPIO.cleanup()

def handle_rotary_encoder():
    global prev_CLK_state, button_pressed, total_beats, beat_interval, time_signature

    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)

    # If the state of CLK is changed, then pulse occurred
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            total_beats = max(1, total_beats - 1)
        else:
            total_beats = min(8, total_beats + 1)

    # Save last CLK state
    prev_CLK_state = CLK_state

    # Handle button press
    button_state = GPIO.input(SW_PIN)
    if button_state == GPIO.LOW and not button_pressed:
        button_pressed = True
        # Toggle time signature on button press
        ts_index = (list(beat_images.keys()).index(time_signature) + 1) % len(beat_images)
        time_signature = list(beat_images.keys())[ts_index]
    elif button_state == GPIO.HIGH:
        button_pressed = False

try:
    while True:
        handle_rotary_encoder()
        countdown(total_beats, beat_interval, beat_images_loaded)
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()
