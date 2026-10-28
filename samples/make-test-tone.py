"""Writes samples/test-tone.wav: 5 seconds of a quiet A major chord, stereo, 44.1 kHz.

A synthetic file made for this repository (no rights to worry about), handy to try the Mastering
examples without your own track. Standard library only.

  python3 samples/make-test-tone.py [output.wav]
"""
import math
import struct
import sys
import wave
from pathlib import Path

RATE = 44100
SECONDS = 5
NOTES = (220.0, 277.18, 329.63)  # A3, C#4, E4

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "test-tone.wav"
with wave.open(str(out), "wb") as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(RATE)
    frames = bytearray()
    for i in range(RATE * SECONDS):
        t = i / RATE
        fade = min(1.0, t / 0.05, (SECONDS - t) / 0.2)
        sample = sum(math.sin(2 * math.pi * f * t) for f in NOTES) / len(NOTES) * 0.3 * fade
        value = int(sample * 32767)
        frames += struct.pack("<hh", value, value)
    wav.writeframes(bytes(frames))
print("wrote", out)
