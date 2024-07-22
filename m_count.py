import pygame
from PIL import Image, ImageDraw, ImageFont
import time

# Initialize pygame
pygame.init()
screen_width = 64  # Width of the OLED screen in portrait mode
screen_height = 128  # Height of the OLED screen in portrait mode
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("OLED Beat Countdown")

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

def load_images(paths):
    images = []
    for path in paths:
        image = Image.open(path).convert('RGB')
        pygame_image = pygame.image.fromstring(image.tobytes(), image.size, 'RGB')
        images.append(pygame_image)
    return images

def overlay_text_on_image(image, text):
    pil_image = Image.frombytes('RGB', (image.get_width(), image.get_height()), pygame.image.tostring(image, 'RGB'))
    draw = ImageDraw.Draw(pil_image)

    # Load a custom font
    font_size = 30  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Calculate text position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (pil_image.width - text_width) // 2
    text_y = (pil_image.height - text_height) // 2

    # Draw text on the image
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))  # White text

    # Convert back to a format suitable for pygame
    return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, 'RGB')

def countdown(total_beats, beat_interval, beat_images):
    beat_count = total_beats
    images = load_images(beat_images)

    try:
        while beat_count > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            # Display the current beat image with the countdown number overlay
            image_index = total_beats - beat_count
            screen.blit(images[image_index], (0, 0))
            screen.blit(overlay_text_on_image(images[image_index], str(beat_count)), (0, 0))
            pygame.display.flip()
            time.sleep(beat_interval)

            beat_count -= 1

    except KeyboardInterrupt:
        pygame.quit()

# Run the countdown with the selected time signature
countdown(total_beats, beat_interval, beat_images[time_signature])
pygame.quit()
