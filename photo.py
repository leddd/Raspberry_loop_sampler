import time
import RPi.GPIO as GPIO
from PIL import Image
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106

# Initialize I2C interface and OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

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

def draw_image(image):
    # Create a new image in portrait mode dimensions
    temp_image = Image.new('1', (64, 128), "black")
    temp_image.paste(image, (0, 0))
    
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
        
        # Draw the current image
        draw_image(beat_images[current_image_index])
    
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
    draw_image(beat_images[current_image_index])
    
    while True:
        handle_rotary_encoder()
        time.sleep(0.01)  # Small delay to prevent CPU overuse
except KeyboardInterrupt:
    GPIO.cleanup()
