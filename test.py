from pyo import *

# Initialize and boot the server with Jack
s = Server(sr=48000, buffersize=1024,audio='pa').boot()
s.start()

# Create a sine wave and output it
a = Sine(mul=0.1).out()

# Start the GUI
s.gui(locals())
