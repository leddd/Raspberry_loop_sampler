import tkinter as tk

class LooperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("6-Track Looper")
        self.root.geometry("500x350")
        self.root.configure(bg='darkgray')

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

def run_gui():
    root = tk.Tk()
    app = LooperApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
