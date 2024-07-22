import pygame
from PIL import Image, ImageDraw, ImageFont
import time

# Initialize pygame
pygame.init()
screen_width = 64  # Width of the OLED screen in portrait mode
screen_height = 128  # Height of the OLED screen in portrait mode
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("OLED Simulation - CONFIG")

# Path to your TTF font file and metronome images
font_path = 'fonts/InputSansNarrow-Thin.ttf'
metro_images = ['screens/metro1.png', 'screens/metro2.png', 'screens/metro3.png']

# CONFIG options
config_options = ["BPM", "TIME SIGNATURE", "TOTAL BARS"]
config_option_values = {
    "BPM": 120,
    "TIME SIGNATURE": "4/4",
    "TOTAL BARS": 4
}
time_signature_options = ["2/4", "3/4", "4/4", "6/8"]
current_config_option = 0

# Padding and margin variables
settings_padding = 4
highlight_offset = 2  # Offset of the highlight position

def load_images(paths):
    images = []
    for path in paths:
        image = Image.open(path).convert('RGB')
        pygame_image = pygame.image.fromstring(image.tobytes(), image.size, 'RGB')
        images.append(pygame_image)
    return images

def draw_config_screen(current_config_option):
    # Create a blank image and get a drawing context
    image = Image.new('1', (screen_width, screen_height), color=0)  # '1' mode for 1-bit color depth
    draw = ImageDraw.Draw(image)

    # Load a custom font
    font_size = 20  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Draw config option
    option = config_options[current_config_option]
    if option == "BPM":
        value = f"{config_option_values[option]} BPM"
        images = load_images(metro_images)
    elif option == "TIME SIGNATURE":
        value = config_option_values[option]
        images = load_images(metro_images)  # Replace with actual images for time signatures
    elif option == "TOTAL BARS":
        value = f"{config_option_values[option]} BARS"
        images = load_images(metro_images)  # Replace with actual images for total bars

    # Calculate text position
    bbox = draw.textbbox((0, 0), value, font=font)  # Get bounding box
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (screen_width - text_width) // 2
    text_y = (screen_height - text_height) // 2 + 10  # Slightly below center

    # Convert image to a format suitable for pygame
    pygame_image = pygame.image.fromstring(image.convert('RGB').tobytes(), image.size, 'RGB')

    return pygame_image, images, value, text_x, text_y

def overlay_text_on_image(image, text, text_x, text_y):
    pil_image = Image.frombytes('RGB', (image.get_width(), image.get_height()), pygame.image.tostring(image, 'RGB'))
    draw = ImageDraw.Draw(pil_image)

    # Load a custom font
    font_size = 20  # Adjust the font size as needed
    font = ImageFont.truetype(font_path, font_size)

    # Draw text on the image
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))  # White text

    # Convert back to a format suitable for pygame
    return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, 'RGB')

def config_screen(total_beats, beat_interval, metro_images):
    global current_config_option
    screen_image, images, text, text_x, text_y = draw_config_screen(current_config_option)

    try:
        beat_count = total_beats
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:  # Decrease value
                        if current_config_option == 0:  # BPM
                            config_option_values["BPM"] = max(1, config_option_values["BPM"] - 1)
                        elif current_config_option == 1:  # TIME SIGNATURE
                            current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                            config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index - 1) % len(time_signature_options)]
                        elif current_config_option == 2:  # TOTAL BARS
                            config_option_values["TOTAL BARS"] = max(1, config_option_values["TOTAL BARS"] - 1)
                    elif event.key == pygame.K_d:  # Increase value
                        if current_config_option == 0:  # BPM
                            config_option_values["BPM"] = min(300, config_option_values["BPM"] + 1)
                        elif current_config_option == 1:  # TIME SIGNATURE
                            current_ts_index = time_signature_options.index(config_option_values["TIME SIGNATURE"])
                            config_option_values["TIME SIGNATURE"] = time_signature_options[(current_ts_index + 1) % len(time_signature_options)]
                        elif current_config_option == 2:  # TOTAL BARS
                            config_option_values["TOTAL BARS"] = min(8, config_option_values["TOTAL BARS"] + 1)
                    elif event.key == pygame.K_l:  # Move to next config option
                        if current_config_option < len(config_options) - 1:
                            current_config_option += 1
                        else:
                            # Save settings and exit config
                            pygame.quit()
                            exit()
                    # Update screen image and values after a key press
                    screen_image, images, text, text_x, text_y = draw_config_screen(current_config_option)

            # Display the current beat image with the current config value overlay
            image_index = total_beats - beat_count
            screen.blit(images[image_index % len(images)], (0, 0))
            screen.blit(overlay_text_on_image(images[image_index % len(images)], text, text_x, text_y), (0, 0))
            pygame.display.flip()
            time.sleep(beat_interval)

            beat_count -= 1
            if beat_count <= 0:
                beat_count = total_beats

    except KeyboardInterrupt:
        pygame.quit()

# Run the config screen with metronome images
total_beats = 3  # Number of metronome images for BPM
beat_interval = 0.5  # Interval between beats
config_screen(total_beats, beat_interval, metro_images)
pygame.quit()
