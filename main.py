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
    def __init__(self, server, metronome, channels=2, feedback=0.5):
        self.server = server
        self.metronome = metronome
        self.channels = channels
        self.feedback = feedback
        self.master_trig = None

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.playback.out()
        print("Playback...")

    def stop_playback(self):
        self.playback.stop()
        print("Stopped Playback.")
        
    def rec_master_track(self): 
        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar + 1:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.01)
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=0.5, xfade=0)
            self.master_trig = CallAfter(self.start_recording, latency)

        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar * (1 + self.metronome.total_bars) + 1:
            self.start_playback()
            self.metronome.play_clicks = False
            
    def print_countdown(self):
        if self.metronome.countdown_counter.get() <= self.metronome.beats_per_bar:
            print("Countdown counter:", self.metronome.countdown_counter.get())
    
    def print_beat(self):
        print("Current beat:", self.metronome.current_beat.get())
     
    def init_master_track(self):
        self.metronome.init()
        self.trig_rec_master = TrigFunc(self.metronome.countdown_metro, self.rec_master_track)
        self.trig_countdown = TrigFunc(self.metronome.countdown_metro, self.metronome.countdown_click)
        self.trig_click = TrigFunc(self.metronome.metro, self.metronome.regular_click)
        self.trig_print_countdown = TrigFunc(self.metronome.countdown_metro, self.print_countdown)
        self.trig_print_beat = TrigFunc(self.metronome.metro, self.print_beat)


# Initialize metronome and track
metronome = Metronome(bpm, beats_per_bar, total_bars, click_volume)
track = Track(s, metronome)

track.init_master_track()

# Continue running the server
s.gui(locals())
