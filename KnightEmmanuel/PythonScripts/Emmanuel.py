import subprocess

print("Checking Essential System Binaries")
systembinaries = ["unar", "ffmpeg", "qemu-img", "7zz"]
for systembinary in systembinaries:
    result = subprocess.run(["which", systembinary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if f"{result.stderr}{result.stdout}":
        if "not found" in f"{result.stderr}{result.stdout}":
            raise ModuleNotFoundError(f"System binary {systembinary} NOT FOUND. Please install the system binary via brew or apt or compiled from source code for Knight Emmanuel to function")
        else:
            print(f"System binary {systembinary} FOUND.")
    else:
        raise ModuleNotFoundError(f"System binary {systembinary} NOT FOUND. Please install the system binary via brew or apt or compiled from source code for Knight Emmanuel to function")

print("Checking Python Dependencies")
dependencies = ["better-profanity", "discord-py", "python-dotenv", "filetype", "nudenet", "openai", "google-genai", "opencv-python", "pillow", "python-magic", "rarfile", "requests", "selenium-wire-2", "blinker", "webdriver-manager", "aiofiles", "aiocsv", "numpy", "pandas", "matplotlib", "fpdf", "pypdf", "beautifulsoup4"]
for dependency in dependencies:
    result = subprocess.run(["pip", "show", dependency], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if "not found" in f"{result.stderr} {result.stdout}":
        raise ModuleNotFoundError(f"Python dependency {dependency} NOT FOUND. Please install the dependency via pip in order for Knight Emmanuel to function")
    else:
        print(f"Python dependency {dependency} FOUND.")

"""
                    ---Scan Engine Logic---
Message text content check - Using three detection methods (Profanity Lib, Black Lists and OpenAI or Gemini)
Images, Gif and PDF Frames check - Image converted to PNG format and scan with Nudenet, if nothing detected, convert all to PDF frames and Using OpenAI to scan
Image Text OCR - Using OpenAI OCR scan
Video Frames - Using cv2 to extract all video frames to scan with Nudenet, if nothing detected converting 40 video frames into a PDF file for OpenAI to scan the frames
Audio transcript - Using GPT-40-Transcribe to extract audio script, then Profanity Lib and OpenAI to analyze the transcript
Archive file - Checking for archive bomb then extracting the image, audio, video, pdf compressed content for scan
"""

import DiscordApplicationCommandsModule
from RuntimeConfigsModule import DISCORD_API, Emmanuel

if __name__ == "__main__":
    Emmanuel.run(DISCORD_API)
