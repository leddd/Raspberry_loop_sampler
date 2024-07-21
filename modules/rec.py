from pyo import *

class Track:
    def __init__(self, server, duration, channels=2, feedback=0.5):
        
        self.server = server
        self.table = NewTable(length=duration, chnls=channels, feedback=feedback)
        self.input = Input([0, 1])
        self.recorder = TableRec(self.input, table=self.table, fadetime=0.01)
        self.playback = Looper(table=self.table, dur=duration, mul=0.5, xfade=0)

    def start_recording(self):

        self.recorder.play()
        print("Recording...")
        

    def start_playback(self):

        self.playback.out()
        print("Playback...")

# Usage
s = Server(duplex=1).boot()
s.start()

# Create a track instance with a specified duration
track = Track(s, duration=2)  # Set loop duration to 2 seconds

# Start recording
track.start_recording()
play_trig = TrigFunc(track.recorder['trig'], track.start_playback)

# Run for 5 seconds
s.sleep(15)

# Stop the server
s.stop()