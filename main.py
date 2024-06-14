from pyo import *

# Initialize server
s = Server(duplex=1).boot()
s.start()

# User-defined parameters
bpm = 128
beats_per_bar = 4
total_bars = 2
click_volume = 0.15  # Control the volume of the clicks

latency = 0.2  # Latency in seconds

# Metro setup
interval = 60 / bpm
duration = interval * beats_per_bar * total_bars  # Loop duration in seconds

countdown_metro = Metro(time=interval)
countdown_counter = Counter(countdown_metro, min=1)

metro = Metro(time=interval)
current_beat = Counter(metro, min=1, max=(total_bars * beats_per_bar)+1)

# Load samples with volume control
click = SfPlayer("samples/click.wav", speed=1, loop=False, mul=click_volume)
click_high = SfPlayer("samples/click.wav", speed=1.5, loop=False, mul=click_volume)  # High pitch for first countdown beat
click2 = SfPlayer("samples/click2.wav", speed=1, loop=False, mul=click_volume)
click2_high = SfPlayer("samples/click2.wav", speed=1.5, loop=False, mul=click_volume)  # High pitch for first beat of regular bars

# Global variables to track the current state
play_clicks = True  # Flag to control click playback
loop_recorded = False
loop_started = False


def metro_init():
    global countdown_counter, countdown_metro, metro, metro_trig, stop_trig
    
    countdown_metro.play()
    
    def metro_start():
        if countdown_counter.get() > beats_per_bar:
            metro.play()
            
    def metro_stop():
        if countdown_counter.get() > beats_per_bar * (1 + total_bars) + 1:
            countdown_metro.stop()

    metro_trig = TrigFunc(countdown_metro, metro_start)   
    stop_trig = TrigFunc(countdown_metro, metro_stop)
    
def countdown_click():
    if countdown_counter.get() <= beats_per_bar:
        if countdown_counter.get() == 1.0:
            click_high.out()
        else:
            click.out()

def regular_click():
    if play_clicks:
        if current_beat.get() == 1.0 or (current_beat.get()-1) % beats_per_bar == 0:
            click2_high.out()
        else:
            click2.out()

class Track: 
    def __init__(self, server, channels=2, feedback=0.5):
        global duration
        
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
             
def record_track():
    global track, countdown_counter, beats_per_bar, countdown_metro, rec_trig, latency, play_clicks
    if countdown_counter.get() == beats_per_bar + 1:
        # Create a track instance with a specified duration
        track = Track(s) 

        # Start recording
        rec_trig = CallAfter(track.start_recording, latency)
        
        # # Setup playback trigger once the track is ready
        # play_trig = TrigFunc(track.recorder['trig'], track.start_playback)
    if countdown_counter.get() == beats_per_bar * (1 + total_bars) + 1:
        track.start_playback()
        play_clicks = False
        

def print_counter1():
    if countdown_counter.get() <= beats_per_bar:
        print("Countdown counter:", countdown_counter.get())
 
def print_counter2():
    print("Current beat:", current_beat.get())



metro_init() # this should be called by the master track init
track = Track(s)  # track init


trig1 = TrigFunc(countdown_metro, print_counter1)
trig2 = TrigFunc(countdown_metro, countdown_click)
trig3 = TrigFunc(countdown_metro, record_track)
trig4 = TrigFunc(metro, print_counter2)
trig5 = TrigFunc(metro, regular_click)


# Continue running the server
s.gui(locals())

