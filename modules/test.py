from pyo import *

# Initialize Pyo server with JACK audio
s = Server(audio='portaudio').boot()
s.start()

# Create an audio effect with a sine wave
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
