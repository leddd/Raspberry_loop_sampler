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

# Load the beat images
beat_images = [
    Image.open('/home/vice/main/djavu/screens/test1.png').convert('1'),
    Image.open('/home/vice/main/djavu/screens/test2.png').convert('1'),
    Image.open('/home/vice/main/djavu/screens/test3.png').convert('1'),
    Image.open('/home/vice/main/djavu/screens/test4.png').convert('1')
]

# Define the GPIO pins for the rotary encoder
CLK_PIN = 17  # GPIO22 connected to the rotary encoder's CLK pin
DT_PIN = 27   # GPIO27 connected to the rotary encoder's DT pin
SW_PIN = 22   # GPIO17 connected to the rotary encoder's SW pin

# Set up GPIO pins for rotary encoder
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

prev_CLK_state = GPIO.input(CLK_PIN)
button_pressed = False
current_image_index = 0

def draw_image_with_text(image, text):
    # Create a new image for drawing text in portrait mode dimensions
    temp_image = Image.new('1', (64, 128), "black")
    draw = ImageDraw.Draw(temp_image)
    
    # Paste the beat image onto the temporary image
    temp_image.paste(image, (0, 0))
    
    # Load a custom font
    font_size = 30  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)
    
    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (64 - text_width) // 2
    text_y = (128 - text_height) // 2
    
    # Draw text on the image
    draw.text((text_x, text_y), text, font=font, fill="white")  # White text
    
    # Rotate the image by 90 degrees to fit the landscape display
    rotated_image = temp_image.rotate(270, expand=True)
    
    # Display the rotated image on the device
    device.display(rotated_image)

def handle_rotary_encoder():
    global prev_CLK_state, button_pressed, current_image_index
    
    # Read the current state of the rotary encoder's CLK pin
    CLK_state = GPIO.input(CLK_PIN)
    
    # If the state of CLK is changed, then pulse occurred
    if CLK_state != prev_CLK_state and CLK_state == GPIO.HIGH:
        # If the DT state is HIGH, the encoder is rotating in counter-clockwise direction
        if GPIO.input(DT_PIN) == GPIO.HIGH:
            current_image_index = (current_image_index - 1) % len(beat_images)
        else:
            current_image_index = (current_image_index + 1) % len(beat_images)
        
        # Draw the current image with its index
        draw_image_with_text(beat_images[current_image_index], str(current_image_index + 1))
    
    # Save last CLK state
    prev_CLK_state = CLK_state
    
    # Handle button press
    button_state = GPIO.input(SW_PIN)
    if button_state == GPIO.LOW and not button_pressed:
        button_pressed = True
        # Perform an action on button press if needed
        print("Button pressed")
    elif button_state == GPIO.HIGH:
        button_pressed = False

try:
    # Draw the initial image
    draw_image_with_text(beat_images[current_image_index], str(current_image_index + 1))
    
    while True:
        handle_rotary_encoder()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()
