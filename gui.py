import tkinter as tk

def button_click(number):
    print(f"Button {number} clicked!")

# Create the main window
root = tk.Tk()
root.title("Loop Station")
root.geometry("300x140")  # Width x Height

# Set background color
root.configure(bg='lightgray')

# Create buttons
buttons = []
for i in range(6):
    btn = tk.Button(root, text=f"Button {i+1}", bg='darkgray', fg='white',
                    command=lambda i=i: button_click(i+1))
    btn.grid(row=i//3, column=i%3, padx=10, pady=10, ipadx=10, ipady=10)
    buttons.append(btn)

# Start the GUI event loop
root.mainloop()
