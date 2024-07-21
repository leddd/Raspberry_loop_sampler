from pyo import *

s = Server(sr=48000, nchnls=2, ichnls=1, audio='portaudio').boot()
s.start()
f = Fader(fadeout=0.2, dur = 0.1 , mul=.2)
sine = Sine(freq=[500], mul=f).out()
f.play()

# GUI for real-time control and visualization
s.gui(locals())