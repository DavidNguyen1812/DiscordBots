import base64

import cv2
from openai import OpenAI
import os
from dotenv import load_dotenv
from google.cloud import vision
from nudenet import NudeDetector
from PIL import Image
import filetype
import magic
import requests
import mimetypes
import json

SEXUALTAGS = [
    "FEMALE_GENITALIA_COVERED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "BUTTOCKS_COVERED",
]
detector = NudeDetector()

load_dotenv()

GPTclient = OpenAI(api_key=os.environ.get("EMMANUELOPENAIAPI"))

def scanningImageWithNudenet(image):
    detections = detector.detect(image)
    print(f"Nudenet scan results: {detections}")
    for result in detections:
        if result['class'] in SEXUALTAGS:
            if result['score'] > 0.55:
                return True
    return False

def scanningImageWithGoogleVision(image_path): # Every month, the first 1000 images are free, then $1.50 for 1001-5,000,000 images, then $0.60 for 5,000,000+ images
    # Initialize Google Vision Client
    user = vision.ImageAnnotatorClient()

    # Read image file
    with open(image_path, "rb") as image_file:
        content = image_file.read()

    # Create Image object
    image = vision.Image(content=content)

    # Perform OCR Detection
    response = user.text_detection(image=image)
    if response.text_annotations:
        return response.text_annotations[0].description
    else:
        return ""

# print(scanningImageWithGoogleVision("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/Test4.png"))

def scanningImageWithGPT(PDFimagePath):  # Cost $0.15 for 1 Million Input Token, $0.60 for 1 Million Output Token
    prompt = "Is the PDF frame have any nude elements, vulgar language, sexual theme, the exposure of animal genitalia, animal porn, reference to adult websites, or even consider NSFW?"
    with open(PDFimagePath, "rb") as PDFfile:
        fileResponse = GPTclient.files.create(file=PDFfile, purpose="assistants")
        fileID = fileResponse.id

    response = GPTclient.responses.create(
        model="gpt-5",
        input=[
            {"role": "system", "content": "You are a specialized NSFW content scanner on PDF frames."},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_file", "file_id": fileID}
                ]
            }
        ]
    )

    GPTclient.files.delete(fileID)

    print(f"GPT4 image NSFW scan results: {response.output_text}")


def scanningAudioFileWithGPT(AudioPath):
    audioFile = open(AudioPath, "rb")

    transcription = GPTclient.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audioFile
    )
    return transcription.text

# print(scanningAudioFileWithGPT("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/Audio/DigBar BIG DICK RANDY.mp3"))
'''
imagePath = "/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/Test17.png"
with open(imagePath, "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode("utf-8")
    print(f"Original image base64 len: {len(b64_image)}")

optimizedImage = Image.open(imagePath).convert("RGB")
optimizedImage.save("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/OptimizedTest17.png",
                    optimize=True)
with open("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/OptimizedTest17.png", "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode("utf-8")
    print(f"Optimized image base64 len: {len(b64_image)}")

resizeImage = Image.open(imagePath).convert("RGB")
resizeImage = resizeImage.resize(size=(int(resizeImage.width * 0.25), int(resizeImage.height * 0.25)))
resizeImage.save("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/ResizedTest17.png")
with open("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/ResizedTest17.png", "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode("utf-8")
    print(f"Resized image base64 len: {len(b64_image)}")


resizeOptimizedImage = Image.open(imagePath).convert("RGB")
resizeOptimizedImage = resizeOptimizedImage.resize(size=(int(resizeImage.width * 0.25), int(resizeImage.height * 0.25)))
resizeOptimizedImage .save("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/ResizedOptimizedTest17.png", optimize=True)
with open("/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDFTest/ResizedOptimizedTest17.png", "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode("utf-8")
    print(f"Resized and optimized image base64 len: {len(b64_image)}")
'''


'''
GifDirectory = "/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/DavidKnights/KnightSamson/PythonScripts/Cooked"
gif_name = "BigBoyRugby"
if os.listdir(GifDirectory):
    GifFrames = []
    for dirpath, dirnames, filenames in os.walk(GifDirectory):
        for filename in filenames:
            framepath = os.path.join(dirpath, filename)
            GifFrames.append(framepath)
    GifFrames.sort()
    print(GifFrames)
    NewResizeFrames = []
    for frame in GifFrames:
        img = Image.open(frame)
        img = img.convert("RGBA")
        resized = img.resize(size=(int(img.width * 0.25), int(img.height * 0.25)))
        NewResizeFrames.append(resized)

    NewResizeFrames[0].save(
        f'{GifDirectory}/{gif_name}.gif',
        save_all=True,
        append_images=NewResizeFrames[1:],
        optimize=True,
        duration=100,
        loop=0,
        disposal=2
    )
'''


# print(checkingRealFileExtension("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcGo2c3c4M2N5ZzlvazhydWJxYjd3dXh5cG9oa2tzcHE1MTQ5ajMweiZlcD12MV9naWZzX3RyZW5kaW5nJmN0PWc/g5R9dok94mrIvplmZd/giphy.gif", "image"))

gifPath = "/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDF/Test31/Test31d.gif"
pdfPath = gifPath.split('.')[0] + "Better.pdf"

'''
img = Image.open(gifPath)

GifFrames = []
for frame in range(0, img.n_frames):
    img.seek(frame)
    GifFrames.append(img.convert("RGB"))
GifFrames[0].save(
    pdfPath,
    save_all=True,
    append_images=GifFrames[1:],
    resolution=100.0
)
print(f"Successfully converted '{gifPath}' to '{pdfPath}'.")
'''
# print(scanningImageWithGPT(pdfPath))

imgPath = "/Users/davidnguyen/PycharmProjects/TheKnightsOfDavidNguyen/TestItems/PicturesAndPDF/Test29.png"
imgPdfPath = imgPath.split('.')[0] + "NSFW.pdf"

'''
img = Image.open(imgPath)
img = img.convert("RGB")
img.save(imgPdfPath, "PDF", resolution=100.0)
print(f"Successfully converted '{imgPath}' to '{imgPdfPath}'.")
'''

# print(scanningImageWithGPT(imgPdfPath))

videoPath = "/Users/davidnguyen/Downloads/Nude5.MOV"
videoPdfPath = videoPath.split('.')[0] + ".pdf"


'''
cap = cv2.VideoCapture(videoPath)
print(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
FPS = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 40 # Restrict scan operation to scan 20 frames max
frameCount = 0
frameNum = 0
frames = []
while frameNum < int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):
    frameNum += 1
    success, frame = cap.read()
    if success and (frameNum % FPS == 0):
    # if success:
        rgbImgage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(rgbImgage))
        frameCount += 1
    if frameCount == 40:
        break
cap.release()
frames[0].save(
    videoPdfPath,
    save_all=True,
    append_images=frames[1:],
    resolution=100.0
)
print(f"Successfully converted '{videoPath}' to '{videoPdfPath}'.")
'''

'''
cap = cv2.VideoCapture(videoPath)
frameNum = 0
print(f"Video has total {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))} frames!")
while frameNum < int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):
    frameNum += 1
    success, frame = cap.read()
    if success:
        framePath = f"/Users/davidnguyen/Downloads/frame_{frameNum}.png"
        cv2.imwrite(framePath, frame)
        if scanningImageWithNudenet(framePath):
            print(f"Nudenet detected NSFW content at video Frame {frameNum}!")
            break
        os.remove(framePath)
cap.release()
'''

# print(scanningImageWithGPT(videoPdfPath))

# print(cv2.getBuildInformation())

# response = requests.get("https://www.amazon.com/gp/product/B0CMK2PM3J/ref=ppx_yo_dt_b_d_asin_title_351_o00?ie=UTF8&psc=1")
# print(response.status_code)

headers = {'User-Agent': 'Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 142.0.0.0 Safari / 537.36', "Range": "bytes=0-1000000"}


def checkingRealFileExtension(fileURL, filename):
    print("Getting the first 1M bytes content of the file in http RESPONSE...")
    first1MegaBytesResponse = requests.get(fileURL, headers=headers)
    if first1MegaBytesResponse.status_code in (200, 206):
        first1MegaBytes = first1MegaBytesResponse.content
        print("Checking file extension with python-magic module...")
        mime = magic.from_buffer(first1MegaBytes, mime=True)
        fileExt = mimetypes.guess_extension(mime)
        if fileExt:
            if fileExt == ".bin":
                if first1MegaBytes.startswith(b'PK'):
                    return '.zip'
                elif first1MegaBytes.startswith(b'caff'):
                    return '.caf'
            if fileExt == ".webm" and filename.endswith(".weba"):
                return ".weba"
            if fileExt == ".webm" and filename.endswith(".wmv"):
                return ".wmv"
            if fileExt == ".wmv" and filename.endswith(".wma"):
                return ".wma"
            if fileExt == ".ogv" and filename.endswith(".ogg"):
                return ".ogg"
            if fileExt == ".asf" and filename.endswith(".wmv"):
                return ".wmv"
            if fileExt == ".asf" and filename.endswith(".wma"):
                return ".wma"
            return fileExt
        else:
            print("python-magic  could not determined, manually checking based on pre-defined list...")
            try:
                first1MegaBytesToASCII = first1MegaBytes.decode("ascii")
                if first1MegaBytesToASCII.isascii():
                    return "ASCII document or script files"
            except UnicodeDecodeError:
                print("Checking file extension with filetype module...")
                fileExt = filetype.guess(first1MegaBytes)
                if fileExt:
                    return f".{fileExt.extension}"
                else:
                    if first1MegaBytes.startswith((b'\x0B\x77', b'\x0bwu\xacT@C')):
                        return ".ac3"
                    elif filename.endswith(".lzma"):
                        return ".lzma"
                    print(f"File extension can not be determined!")
                    return "Can't be determined"
    else:
        return "Invalid Download URL!"


URL = "https://cdn.discordapp.com/attachments/1338680289026773185/1448752495009730590/Test31d.gif?ex=693c6767&is=693b15e7&hm=07b5047141ee545a9d45bf904670f3ddcd0a849d4d88f548d1dbbe72e12597b5&"
# print(checkingRealFileExtension(URL, os.path.basename(URL.split('?')[0].lower())))

# response = requests.get("https://learn.microsoft.com/en-us/azure/sentinel/fusion", headers=headers)
# print(response.status_code)
# print(response.request.headers)
# print(response.headers)
# print(len(response.content))


def ScanningTextOnlyWithGPT(textToBeScanned):
    response = GPTclient.responses.create(
        model="gpt-4o-mini",
        instructions="You job is solely being an NSFW scanner in text message and URL name! Please follow the prompt for detailed instructions",
        input=textToBeScanned
    )

    reply = response.output_text
    return reply


def NSFWscanMessage(checkMessage, sendMessage):  # Return True if text content is NSFW!
    delete = False
    if not delete:  # Second check for profanity with ChatGPT
        print("Profanity Library did not detect, starting GPT scan...")
        if sendMessage != "Please do not send NSFW URL!":
            DetectedPhrase = ScanningTextOnlyWithGPT(
                f"Analyze the following message and identify any vulgar or inappropriate words.\n"
                f"Consider the context—only flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
                f"Taking into measure the text could be written in other language than English, this does means that some characters in the text may be another language alphabet or a letter emoji.\n"
                f"Response MUST start with a Yes or No then follow by a COMMA and EXPLAIN the reason in MAXIMUM 30 WORDS!\n"
                f"Message: '{checkMessage}'\n")
        else:
            DetectedPhrase = ScanningTextOnlyWithGPT(
                f"Analyze the following URL query and identify any vulgar or inappropriate words.\n"
                f"Consider the context—only flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
                f"Taking into measure the text could be written in other language than English, this does means that some characters in the text may be another language alphabet or a letter emoji.\n"
                f"Response MUST start with a Yes or No then follow by a COMMA and EXPLAIN the reason in MAXIMUM 30 WORDS!\n"
                f"Message: '{checkMessage}'\n")
        print(DetectedPhrase)
    if not delete:
        print("GPT scan result is clean!")
        return False
    else:
        return True

# NSFWscanMessage("https//xvideo.com", "Please do not send NSFW URL!")
# NSFWscanMessage("Let do it in an Amazon Position, babe!", "Please do not send NSFW text!")
# NSFWscanMessage("He just got offer a job position at Amazon!", "Please do not send NSFW text!")

import re

text = "https://www.youtube.com/watch?v=72n9QwLBURk&list=RDEMeK45PM5P_dgWzQUhhpV6hw&index=11 Gay boy https://cdn.discordapp.com/attachments/1447079603456970844/1458474939240812576/Screenshot_20260107_095749_Gmail.jpg?ex=695fc622&is=695e74a2&hm=7bf45eab871108fb92398af3f9ce3d955b66f61d3b7cffed758c39b498207f83& Dumb https://tenor.com/view/gorilla-dance-gif-20582069"

# WebSitePattern = re.compile(r'(https?://)?(www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+?)(?:/|$)')
WebSitePattern = re.compile(r'https?://(?:(?!https?://)\S)+')
# WebSitePattern = re.compile(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+?)(?:/|$)')
matches = re.findall(WebSitePattern, text)
print(matches)
for url in matches:
    text = text.replace(url, '')
print(text)

