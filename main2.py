from pyo import *
import time
from gpiozero import Button
from signal import pause
import RPi.GPIO as GPIO

# Initialize Pyo server
s = Server(sr=48000, buffersize=1024, audio='portaudio', nchnls=1, ichnls=1, duplex=1)
s.setInputDevice(1)
s.setOutputDevice(0)
s.boot()
s.start()

# User-defined parameters
bpm = 120
beats_per_bar = 4
total_bars = 4
latency = 0.2  # Latency in seconds

# Initialize GPIO
row_pins = [12, 1]
col_pins = [13, 6, 5]
CLK_PIN = 22
DT_PIN = 27
SW_PIN = 17

# Set up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()
GPIO.setup(CLK_PIN, GPIO.IN)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for col in col_pins:
    GPIO.setup(col, GPIO.OUT)
    GPIO.output(col, GPIO.HIGH)

rows = [Button(pin, pull_up=False) for pin in row_pins]

# Define the GPIO pins for rotary encoder and keypad
key_map = {
    (12, 13): 1, (12, 6): 2, (12, 5): 3,
    (1, 13): 4, (1, 6): 5, (1, 5): 6
}

# Metronome class
class Metronome:
    def __init__(self, bpm, beats_per_bar, total_bars):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.total_bars = total_bars
        self.interval = 60 / bpm
        self.duration = self.interval * beats_per_bar * total_bars
        self.countdown_metro = Metro(time=self.interval)
        self.countdown_counter = Counter(self.countdown_metro, min=1)
        self.metro = Metro(time=self.interval)
        self.current_beat = Counter(self.metro, min=1, max=(total_bars * beats_per_bar) + 1)
        self.fcount = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fcount2 = Adsr(attack=0.01, decay=0.1, sustain=0, release=0, mul=0.2)
        self.fclick = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.fclick2 = Adsr(attack=0.01, decay=0.02, sustain=0, release=0, mul=0.2)
        self.sine2 = Sine(freq=[800], mul=self.fcount).out()
        self.sine = Sine(freq=[600], mul=self.fcount2).out()
        self.click = Noise(self.fclick).out()
        self.click2 = PinkNoise(self.fclick2).out()
        self.clickhp = ButHP(self.click, freq=5000).out()
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

# Track class
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
        self.initialized = False
        self.hp_freq = 650

    def start_recording(self):
        self.recorder.play()
        print("Recording...")

    def start_playback(self):
        self.playback.out()
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
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=1.5, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq).out()
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
            self.playback = Looper(table=self.table, dur=self.metronome.duration, mul=1.5, xfade=0)
            self.highpass = ButHP(self.playback, freq=self.hp_freq).out()
            self.track_trig = CallAfter(self.start_recording, latency)
            self.initialized = True

    def init_track(self, master):
        self.trig_rec = TrigFunc(master.playback['trig'], self.rec_track)

# LoopStation class
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

# Initialize loop station
loop_station = LoopStation(s, bpm, beats_per_bar, total_bars)



def matrix_button_pressed(row_pin):
    for col in col_pins:
        GPIO.output(col, GPIO.LOW)

    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)
        time.sleep(0.01)
        if row_pin.is_pressed:
            key = key_map.get((row_pin.pin.number, col), None)
            if key:
                print(f"Matrix Keypad:: Key pressed: {key}")
                if key == 1:
                    loop_station.init_track(2)
                elif key == 2:
                    loop_station.init_track(3)
                elif key == 3:
                    loop_station.init_track(4)
                elif key == 4:
                    loop_station.init_track(5)
                elif key == 5:
                    loop_station.init_track(6)
        GPIO.output(col, GPIO.LOW)

    for col in col_pins:
        GPIO.output(col, GPIO.HIGH)

# Attach the callback functions
for row in rows:
    row.when_pressed = lambda row=row: matrix_button_pressed(row)

# Main loop
try:
    print("Listening for GPIO input...")
    while True:
        time.sleep(0.01)
except KeyboardInterrupt:
    GPIO.cleanup()
    s.stop()
    s.shutdown()
