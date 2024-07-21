from pyo import *

# Boot the server
s = Server().boot()

# Start the server
s.start()

# Create an audio object (e.g., a sine wave generator)
f = Fader(fadeout=0.2, dur=0.1, mul=.2)
sine = Sine(freq=[500], mul=f).out()
f.play()
# Keep the script running to allow audio processing
try:
    while True:
        time.sleep(1)  # Sleep to keep the script alive
except KeyboardInterrupt:
    # Graceful shutdown on user interrupt
    print("Stopping Pyo server...")
    s.stop()
    s.shutdown()
