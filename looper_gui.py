import tkinter as tk
import asyncio

class LooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("6-Track Looper")
        self.root.geometry("500x350")
        self.root.configure(bg='darkgray')

        self.tracks = [Track(i + 1) for i in range(6)]
        self.buttons = []

        for i in range(2):  # Two rows
            root.grid_rowconfigure(i, weight=1)
            for j in range(3):  # Three columns
                root.grid_columnconfigure(j, weight=1)
                button = tk.Button(root, bg='gray', activebackground='lightgray', command=lambda i=i, j=j: self.on_button_press(i, j))
                button.grid(row=i, column=j, padx=10, pady=10, sticky="nsew")
                self.buttons.append(button)

    def on_button_press(self, row, col):
        track_id = row * 3 + col  # Calculate track_id based on row and column
        print(f"Track {track_id + 1} button pressed")
        asyncio.create_task(self.tracks[track_id].toggle_state())

