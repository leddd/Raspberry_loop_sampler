from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont  # Import Image modules for image manipulation
import time  # Import the time module

# Initialize I2C interface
serial = i2c(port=1, address=0x3C)

# Initialize the sh1106 device in landscape mode
device = sh1106(serial)

# Path to your TTF font file
font_path = 'fonts/InputSansNarrow-Thin.ttf'

# Create an image in portrait mode dimensions
image = Image.new('1', (64, 128), "black")
draw = ImageDraw.Draw(image)

# Load a custom font
font_size = 12  # Adjust the font size as needed
font = ImageFont.truetype(font_path, font_size)

# Draw the content in portrait mode
draw.rectangle((0, 0, 64, 128), outline="black", fill="white")

# Text to display
text = "Hello World"

# Calculate the bounding box of the text to be drawn
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

# Calculate the x position to center the text
text_x = (64 - text_width) // 2
text_y = (128 - text_height) // 2  # Centered vertically as well

# Draw the text
draw.text((text_x, text_y), text, font=font, fill="black")

# Rotate the image by 90 degrees to fit the landscape display
rotated_image = image.rotate(270, expand=True)

# Display the rotated image on the device
device.display(rotated_image)

# Add a delay to keep the graphic on the screen longer
time.sleep(10)  # Delay for 10 seconds
