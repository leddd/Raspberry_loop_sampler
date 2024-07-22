from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont  # Import Image modules for image manipulation
import time  # Import the time module

# Initialize I2C interface
serial = i2c(port=1, address=0x3C)

# Initialize the sh1106 device in landscape mode
device = sh1106(serial)

# Create an image in portrait mode dimensions
image = Image.new('1', (64, 128), "black")
draw = ImageDraw.Draw(image)

# Draw the content in portrait mode
draw.rectangle((0, 0, 64, 128), outline="black", fill="white")
draw.text((10, 60), "Hello World", fill="black")

# Rotate the image by 90 degrees to fit the landscape display
rotated_image = image.rotate(270, expand=True)

# Display the rotated image on the device
device.display(rotated_image)

# Add a delay to keep the graphic on the screen longer
time.sleep(10)  # Delay for 10 seconds
