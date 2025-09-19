#!/usr/bin/env python3

# pip3 install vosk sounddevice

# ffmpeg required
# Although we could attach directly to a device, like here (https://github.com/alphacep/vosk-api/blob/master/python/example/test_microphone.py)
# I get "Input overflow" (https://github.com/alphacep/vosk-api/issues/625) although playing with blocksize and samplerate.
# Reading from ffmpeg instead has no issues

import subprocess
import sys
import json
import argparse
import os

from vosk import Model, KaldiRecognizer, SetLogLevel

SAMPLE_RATE = 16000

SetLogLevel(0)

# Set up command-line argument parsing with default values
parser = argparse.ArgumentParser(description="Transcribe live audio from a PulseAudio source using Vosk.")
parser.add_argument("-s", "--source", type=str,
                    default="alsa_output.pci-0000_00_1b.0.analog-stereo.monitor",
                    help="PulseAudio source name (default: 'alsa_output.pci-0000_00_1b.0.analog-stereo.monitor')")
parser.add_argument("-o", "--output", type=str,
                    default="transcription.txt",
                    help="Destination output file name (default: 'transcription.txt')")
parser.add_argument("-m", "--model", type=str,
                    default="it",
                    help="Path to the Vosk language model folder (e.g., 'path/to/vosk-model-en-us-small') or a language code (default: 'it')")

args = parser.parse_args()

# Load the Vosk model
# Check if the provided argument is a language code or a path
if os.path.exists(args.model):
    print(f"Loading model from path: {args.model}")
    model = Model(args.model)
else:
    print(f"Loading model for language: {args.model}")
    try:
        model = Model(lang=args.model)
    except Exception as e:
        print(f"Error: Could not load model for language '{args.model}'. Please ensure you have the correct model files downloaded.")
        sys.exit(1)

rec = KaldiRecognizer(model, SAMPLE_RATE)

# Use the arguments provided by the user
audio_source = args.source
output_filename = args.output

# Use subprocess to run FFmpeg and pipe its output to the script
with subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-f", "pulse",
                       "-i", audio_source, "-ar", str(SAMPLE_RATE),
                       "-ac", "1", "-f", "s16le", "-"],
                      stdout=subprocess.PIPE) as process:

    print(f"Listening on '{audio_source}' and saving transcription to '{output_filename}'...")
    print("Press Ctrl+C to stop.")

    try:
        # Open the output file in write mode
        with open(output_filename, "w") as output_file:
            while True:
                data = process.stdout.read(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    output_file.write(result.get("text", "") + "\n")
                else:
                    partial_result = json.loads(rec.PartialResult())
                    print(f"\r{partial_result.get('partial', '')}", end="", flush=True)

            final_result = json.loads(rec.FinalResult())
            output_file.write(final_result.get("text", "") + "\n")

    except KeyboardInterrupt:
        print("\nStopping transcription...")
        process.terminate()

    print("\nTranscription complete and saved.")

