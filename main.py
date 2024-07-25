from pyo import *
from gpiozero import Button
import RPi.GPIO as GPIO
import time
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw, Image, ImageFont

# Initialize server
s = Server(sr=48000, buffersize=2048, audio='pa', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)
s.boot()
s.start()

# User-defined parameters
bpm = 120
beats_per_bar = 4
total_bars = 2
latency = 0.05  # Latency in seconds

class Metronome:
    def __init__(self, bpm, beats_per_bar, total_bars):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.total_bars = total_bars

        self.interval = 60 / bpm
        self.duration = self.interval * beats_per_bar * total_bars  # Loop duration in seconds

        self.countdown_metro = Metro(time=self.interval)
        self.countdown_counter = Counter(self.countdown_metro, min=1)
        self.metro = Metro(time=self.interval)
        self.current_beat = Counter(self.metro, min=1, max=(total_bars * beats_per_bar) + 1)
        
        # click setup
        self.fcount = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fcount2 = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fclick = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.fclick2 = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.sine2 = Sine(freq=[800], mul=self.fcount).out()
        self.sine = Sine(freq=[600], mul=self.fcount2).out()
        self.click = Noise(self.fclick).out()
        self.click2 = PinkNoise(self.fclick2).out()
        self.clickhp = ButHP(self.click, freq=5000).out()  # Apply highpass filter

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
                self.fcount.play()
            else:
                self.fcount2.play()

    def regular_click(self):
        if self.play_clicks:
            if self.current_beat.get() == 1.0 or (self.current_beat.get() - 1) % self.beats_per_bar == 0:
                self.fclick.play()
            else:
                self.fclick2.play()
class Track:
    def __init__(self, server, metronome, channels=2, feedback=0.5):
        self.server = server
        self.metronome = metronome
        self.channels = channels
        self.feedback = feedback
        self.master_trig = None
        self.track_trig = None
        self.playback = None
        self.recorder = None
        self.initialized = False  # Flag to ensure initialization only happens once
        self.hp_freq = 400  # Highpass filter frequency
        self.lp_freq = 450 # Lowpass filter frequency

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.lowpass.out()
        print("Playback...")

    def stop_playback(self):
        self.playback.stop()
        print("Stopped Playback.")
        
    def print_countdown(self):
        if self.metronome.countdown_counter.get() <= self.metronome.beats_per_bar:
            print("Countdown counter:", self.metronome.countdown_counter.get())
    
    def print_beat(self):
        print("Current beat:", self.metronome.current_beat.get())
        
    def rec_master_track(self): 
        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar + 1:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.005)
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq) # Apply highpass filter
            self.lowpass = ButLP(self.highpass, freq=self.lp_freq)
            self.harm = Harmonizer(self.playback, transpo=-12, winsize=0.05).out()
            self.master_trig = CallAfter(self.start_recording, latency)

        if self.metronome.countdown_counter.get() == self.metronome.beats_per_bar * (1 + self.metronome.total_bars) + 1:
            self.metronome.play_clicks = False

    def init_master_track(self):
        self.metronome.init()
        self.trig_rec_master = TrigFunc(self.metronome.countdown_metro, self.rec_master_track)
        
        self.trig_countdown = TrigFunc(self.metronome.countdown_metro, self.metronome.countdown_click)
        self.trig_print_countdown = TrigFunc(self.metronome.countdown_metro, self.print_countdown)
        
        self.trig_click = TrigFunc(self.metronome.metro, self.metronome.regular_click)
        self.trig_print_beat = TrigFunc(self.metronome.metro, self.print_beat)
        
    def rec_track(self):
        if not self.initialized:
            self.table = NewTable(length=self.metronome.duration, chnls=self.channels, feedback=self.feedback)
            self.input = Input([0, 1])
            self.recorder = TableRec(self.input, table=self.table, fadetime=0.01).out()
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=20, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq).out()  # Apply highpass filter
            self.lowpass = ButLP(self.playback, freq=self.lp_freq).out()
            self.ex = Expand(self.playback, downthresh=30, upthresh=-31, ratio=4, mul=0.5).out()
            self.track_trig = CallAfter(self.start_recording, latency)
            self.initialized = True
        
    def init_track(self, master):
        self.trig_rec = TrigFunc(master.playback['trig'], self.rec_track)
class LoopStation:
    def __init__(self, server, bpm, beats_per_bar, total_bars):
        self.server = server
        self.metronome = Metronome(bpm, beats_per_bar, total_bars)
        self.tracks = []
        
        self.master_track = Track(server, self.metronome)
        self.tracks.append(self.master_track)
        
    def init_master_track(self):
        self.master_track.init_master_track()
        print("Master track initialized")
        
    def init_track(self, track_num):
        track = Track(self.server, self.metronome)
        track.init_track(self.master_track)
        self.tracks.append(track)
        print(f"Track {track_num} initialized")    
class TrackInitializer:
    def __init__(self, loop_station):
        self.loop_station = loop_station

    def init_master_track(self):
        self.loop_station.init_master_track()

    def init_track(self, track_num):
        self.loop_station.init_track(track_num)
class GPIOSetup:
    def __init__(self, track_initializer):
        self.row_pins = [12, 1]
        self.col_pins = [13, 6, 5]

        self.key_map = {
            (1, 13): 1, (1, 6): 2, (1, 5): 3,
            (12, 13): 4, (12, 6): 5, (12, 5): 6
        }

        self.track_initializer = track_initializer

        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)

        self.rows = [Button(pin, pull_up=False, bounce_time=0.1) for pin in self.row_pins]

        for col in self.col_pins:
            GPIO.setup(col, GPIO.OUT)
            GPIO.output(col, GPIO.HIGH)

        for row in self.rows:
            row.when_pressed = lambda row=row: self.on_button_pressed(row)
            row.when_released = lambda row=row: self.on_button_released(row)

    def on_button_pressed(self, row_pin):
        for col in self.col_pins:
            GPIO.output(col, GPIO.LOW)

        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)
            time.sleep(0.01)
            if row_pin.is_pressed:
                key = self.key_map.get((row_pin.pin.number, col), None)
                if key:
                    if key == 1:
                        self.track_initializer.init_master_track()
                    else:
                        self.track_initializer.init_track(key)
            GPIO.output(col, GPIO.LOW)

        for col in self.col_pins:
            GPIO.output(col, GPIO.HIGH)

    def on_button_released(self, row_pin):
        # Additional logic for button release
        pass
    
# Initialize loop station
loop_station = LoopStation(s, bpm, beats_per_bar, total_bars)

# Initialize track initializer
track_initializer = TrackInitializer(loop_station)

# Setup GPIO keys
gpio_setup = GPIOSetup(track_initializer)

try:
    print("Listening for button presses on matrix keypad...")
    while True:
        time.sleep(0.05)
except KeyboardInterrupt:
    GPIO.cleanup()