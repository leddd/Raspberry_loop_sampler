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

class Metronome:
    def __init__(self, bpm, beats_per_bar, total_bars, click_volume):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.total_bars = total_bars
        self.click_volume = click_volume

        self.interval = 60 / bpm
        self.duration = self.interval * beats_per_bar * total_bars  # Loop duration in seconds

        self.countdown_metro = Metro(time=self.interval)
        self.countdown_counter = Counter(self.countdown_metro, min=1)
        self.metro = Metro(time=self.interval)
        self.current_beat = Counter(self.metro, min=1, max=(total_bars * beats_per_bar) + 1)

        # Load samples with volume control
        self.click = SfPlayer("samples/click.wav", speed=1, loop=False, mul=self.click_volume)
        self.click_high = SfPlayer("samples/click.wav", speed=1.5, loop=False, mul=self.click_volume)  # High pitch for first countdown beat
        self.click2 = SfPlayer("samples/click2.wav", speed=1, loop=False, mul=self.click_volume)
        self.click2_high = SfPlayer("samples/click2.wav", speed=1.5, loop=False, mul=self.click_volume)  # High pitch for first beat of regular bars

        self.play_clicks = True

        self.metro_trig = None
        self.stop_trig = None

    def init(self):
        self.countdown_metro.play()

        self.metro_trig = TrigFunc(self.countdown_metro, self.start_metro)
        self.stop_trig = TrigFunc(self.countdown_metro, self.stop_metro)

    def start_metro(self):
        if self.countdown_counter.get() > self.beats_per_bar:
            self.metro.play()

    def stop_metro(self):
        if self.countdown_counter.get() > self.beats_per_bar * (1 + self.total_bars) + 1:
            self.countdown_metro.stop()

    def countdown_click(self):
        if self.countdown_counter.get() <= self.beats_per_bar:
            if self.countdown_counter.get() == 1.0:
                self.click_high.out()
            else:
                self.click.out()

    def regular_click(self):
        if self.play_clicks:
            if self.current_beat.get() == 1.0 or (self.current_beat.get() - 1) % self.beats_per_bar == 0:
                self.click2_high.out()
            else:
                self.click2.out()

class Track:
    def __init__(self, server, channels=2, feedback=0.5):
        global metronome
        self.server = server
        self.table = NewTable(length=metronome.duration, chnls=channels, feedback=feedback)
        self.input = Input([0, 1])
        self.recorder = TableRec(self.input, table=self.table, fadetime=0.01)
        self.playback = Looper(table=self.table, dur=metronome.duration, mul=0.5, xfade=0)

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.playback.out()
        print("Playback...")

def record_master_track():
    global track, metronome, beats_per_bar, total_bars, latency, rec_trig
    if metronome.countdown_counter.get() == beats_per_bar + 1:
        track = Track(s)
        rec_trig = CallAfter(track.start_recording, latency)

    if metronome.countdown_counter.get() == beats_per_bar * (1 + total_bars) + 1:
        track.start_playback()
        metronome.play_clicks = False

def print_counter1():
    if metronome.countdown_counter.get() <= beats_per_bar:
        print("Countdown counter:", metronome.countdown_counter.get())

def print_counter2():
    print("Current beat:", metronome.current_beat.get())

# Initialize metronome and track
metronome = Metronome(bpm, beats_per_bar, total_bars, click_volume)
metronome.init()
# Set triggers
trig1 = TrigFunc(metronome.countdown_metro, print_counter1)
trig2 = TrigFunc(metronome.countdown_metro, metronome.countdown_click)
trig3 = TrigFunc(metronome.countdown_metro, record_master_track)
trig4 = TrigFunc(metronome.metro, print_counter2)
trig5 = TrigFunc(metronome.metro, metronome.regular_click)

# Continue running the server
s.gui(locals())
