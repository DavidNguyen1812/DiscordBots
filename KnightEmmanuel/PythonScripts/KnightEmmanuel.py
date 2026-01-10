import os
import re
import time
import json
import shutil
import zipfile
import tarfile
import gzip
import bz2
import lzma
import rarfile
import requests
import cv2
import hashlib
import filetype
import discord
import mimetypes
import magic
import subprocess

from PIL import Image
from better_profanity import profanity
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
from nudenet import NudeDetector

load_dotenv()


"""
                    ---Scan Engine Logic---
Message text content check - Using two detection methods (Profanity Lib and OpenAI)
Images, Gif and PDF Frames check - Image converted to PNG format and scan with Nudenet, if nothing detected, convert all to PDF frames and Using OpenAI to scan
Image Text OCR - Using OpenAI OCR scan
Video Frames - Using cv2 to extract all video frames to scan with Nudenet, if nothing detected converting 40 video frames into a PDF file for OpenAI to scan the frames
Audio transcript - Using GPT-40-Transcribe to extract audio script, then Profanity Lib and OpenAI to analyze the transcript
Archive file - Checking for archive bomb then extracting the image, audio, video, pdf compressed content for scan
"""

"""----Configuration Constants----"""
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

ALLSCANNABLEFILEFORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns",
                           ".avif", ".odd", ".gif",

                           ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".ogg",
                           ".wmv", ".dv", ".mts", ".m2ts", ".vob",

                           ".mp3", ".wav", ".oga", ".m4a", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc",
                           ".amr", ".au", ".caf", ".m4b", ".wma", ".opus", ".ogv",

                           ".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz",
                           ".rar", ".bz2", ".xz", ".lzma")


PICTUREFORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns", ".avif",
                  ".odd", ".gif")

VIDEOFORMATS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".ogg", ".wmv", ".dv",
                ".mts", ".m2ts", ".vob", ".ogv")

AUDIOFORMATS = (".mp3", ".wav", ".oga", ".m4a", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc", ".amr",
                ".au", ".caf", ".dss", ".m4a", ".m4b", ".wma", ".opus", ".webm", ".ogg")

ARCHIVEFORMATS = (".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz", ".rar",
                  ".bz2", ".xz", ".lzma")

NSFWFILEPATH = os.environ.get("EMMANUELNSFWDATA")
CLEANFILEPATH = os.environ.get("EMMANUELCLEANDATA")
GPTFLAGGEDFILEPATH = os.environ.get("EMMANUELGPTFLAGGEDWORDSPATH")
EMMANUELLOGFILEPATH = os.environ.get("EMMANUELLOGPATH")
EMMANUELCONFIG = os.environ.get("EMMANUELCONFIGPATH")
MAINDOWNLOADDIR = os.environ.get("EMMANUELDOWNLOADPATH")
HEADERSFORPARTIALCONTENT = {'User-Agent': 'Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 142.0.0.0 Safari / 537.36', "Range": "bytes=0-1000000"}
MAINHEADERS = {'User-Agent': 'Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 142.0.0.0 Safari / 537.36'}

# https://platform.openai.com/docs/pricing
GPTMODELFORIMAGESCAN = "gpt-5-nano"
GPTMODELFORTEXTSCAN = "gpt-4o-mini"

"""----API Tokens----"""
DISCORDAPI = os.environ.get("EMMANUELDISCORDAPI")
TENORAPI = os.environ.get("EMMANUELTENORAPI")
GPTclient = OpenAI(api_key=os.environ.get("EMMANUELOPENAIAPI"))
detector = NudeDetector()


"""Set up Rarfile configurations"""
rarfile.UNRAR_TOOL = "unar"


"""Initializing data container to load essential files and setting up Discord Intents for Emmanuel"""
intents = discord.Intents.all()
Emmanuel = commands.Bot(command_prefix='/', intents=intents)
with open(EMMANUELCONFIG, "r") as configFile:
    configuration = json.load(configFile)
print(f"Configuration file successfully loaded:\n{configuration}")

profanity.load_censor_words_from_file(os.environ.get("EMMANUELPROFANITYWORDLISTS"))
with open(os.environ.get("EMMANUELPROFANITYWORDLISTS"), "r") as profanityFile:
    WordList = [word.strip("\n") for word in profanityFile.readlines()]
print("Profanity Wordlist successfully loaded!")

with open(NSFWFILEPATH, "r") as NSFWFile:
    NSFWData = json.load(NSFWFile)
print(f"NSFW Data successfully loaded:\n{list(NSFWData.keys())}")

with open(CLEANFILEPATH, "r") as CLEANFile:
    CLEANData = json.load(CLEANFile)
print(f"Clean Data successfully loaded:\n{list(CLEANData.keys())}")


def checkingRealFileExtension(fileURL, filename):
    print("Getting the first 1M bytes content of the file in http RESPONSE...")
    first1MegaBytesResponse = requests.get(fileURL, headers=HEADERSFORPARTIALCONTENT)
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


def writingLog(logData):
    with open(EMMANUELLOGFILEPATH, "a") as txtFile:
        txtFile.write(f"{time.ctime(time.time())}\n")
        txtFile.write(logData)


def AddingNewCleanData(Hash, Reason):
    CLEANData[Hash] = Reason
    print("Content passed the check, Adding to clean data...")
    with open(CLEANFILEPATH, "w") as JSONFile:
        json.dump(CLEANData, JSONFile, indent=4)
    print(f"Clean data updated!")


def AddingNewNSFWData(Hash, Reason):
    NSFWData[Hash] = Reason
    print("Content was flagged NSFW, adding to NSFW data...")
    with open(NSFWFILEPATH, "w") as JSONFile:
        json.dump(NSFWData, JSONFile, indent=4)
    print(f"NSFW data updated!")


def checkServerExistInConfigFile(serverID):
    if configuration.get(serverID) is None:
        configuration[serverID] = {}
        configuration[serverID]["Uncensored-members"] = [1336449459634180106, 1318642836870135840, 1311807435627036733, 1312835282852122636, 1288292461310906409, 1334684058919370752, 1330689636309274665, 1361346209360646295]
        configuration[serverID]["Uncensored-channels"] = []
        with open(EMMANUELCONFIG, "w") as file:
            json.dump(configuration, file, indent=4)
        writingLog(f"New server ID {serverID} added to config file!\n\n")
        print(f"New server ID {serverID} added to config file!")


def getHashValueofAttachmentFileData(filepath):
    with open(filepath, "rb") as file:
        return hashlib.sha512(file.read()).hexdigest()


def scanningImageWithNudenet(image):
    detections = detector.detect(image)
    print(f"Nudenet scan results: {detections}")
    for result in detections:
        if result['class'] in SEXUALTAGS:
            if result['score'] > 0.55:
                return True
    return False


def scanningPDFPagesWithGPT(PDFimagePath):
    with open(PDFimagePath, "rb") as PDFfile:
        fileResponse = GPTclient.files.create(file=PDFfile, purpose="assistants")
        fileID = fileResponse.id
    prompt = ("Is the following PDF pages have any nude elements, vulgar language, sexual theme, the exposure of animal genitalia,"
              " animal porn, reference to adult or NSFW websites, or even consider NSFW? Please taking into account that people in light clothing like thongs and bikini SHOULD BE consider NSFW!\n"
              "Response MUST start with a Yes or No then follow by a COMMA and EXPLAIN the reason NO MORE THAN  30 WORDS!"
              )
    response = GPTclient.responses.create(
        model=GPTMODELFORIMAGESCAN,
        instructions="Strictly follow the prompt for detailed instructions",
        input=[
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

    print(f"GPT image NSFW scan results: {response.output_text}")

    return response.output_text


def ScanningTextOnlyWithGPT(textToBeScanned):
    response = GPTclient.responses.create(
        model=GPTMODELFORTEXTSCAN,
        instructions="Strictly follow the prompt for detailed instructions",
        input=textToBeScanned
    )

    reply = response.output_text
    return reply


def isTenorURLValid(url):
    try:
        gifID = url.split('/')[4].split('-')[len(url.split('/')[4].split('-')) - 1]
        url = f"https://tenor.googleapis.com/v2/posts?ids={gifID}&key={TENORAPI}"
        response = requests.get(url, headers=MAINHEADERS)
        if response.status_code == 200:
            data = response.json()
            gifUrl = data["results"][0]["media_formats"]["gif"]["url"]
            return gifUrl
        else:
            return "Invalid"
    except Exception as error:
        print(f"Tenor URL error: {error}")
        return "Invalid"


async def PDFConversion(filePath):
    PDFPath = filePath.split(".")[0] + ".pdf"
    if filePath.endswith(".png"):
        print("Converting PNG image to PDF...")
        try:
            img = Image.open(filePath)
            img = img.convert("RGB")
            img.save(PDFPath, "PDF", resolution=100.0)
        except Exception as error:
            print(f"Failed to convert '{filePath}' to '{PDFPath}'.\nError:\n{error}")
            return "Conversion failed"
    elif filePath.endswith(".gif"):
        print("Converting GIF frames to PDF...")
        try:
            img = Image.open(filePath)

            GifFrames = []
            for frame in range(0, img.n_frames):
                img.seek(frame)
                GifFrames.append(img.convert("RGB"))
            GifFrames[0].save(
                PDFPath,
                save_all=True,
                append_images=GifFrames[1:],
                resolution=100.0
            )
        except Exception as error:
            print(f"Failed to convert '{filePath}' to '{PDFPath}'.\nError:\n{error}")
            return "Conversion failed"
    elif filePath.endswith(VIDEOFORMATS):
        print("Converting Video frames to PDF...")
        try:
            cap = cv2.VideoCapture(filePath)
            FPS = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 40  # Restrict scan operation to scan 40 frames max
            frameCount = 0
            frameNum = 0
            Videoframes = []
            while frameNum < int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):
                frameNum += 1
                success, frame = cap.read()
                if success and (frameNum % FPS == 0):
                    rgbImgage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    Videoframes.append(Image.fromarray(rgbImgage))
                    frameCount += 1
                if frameCount == 40:
                    break
            cap.release()
            Videoframes[0].save(
                PDFPath,
                save_all=True,
                append_images=Videoframes[1:],
                resolution=100.0
            )
        except Exception as error:
            print(f"Failed to convert '{filePath}' to '{PDFPath}'.\nError:\n{error}")
            return "Conversion failed"
    os.remove(filePath)
    return PDFPath


# Return True if NSFW
async def ScanningMedia(mediaName, mediaUrl, hashedMediaContent, URL=True):
    if URL:
        mediaPath = f"{MAINDOWNLOADDIR}{mediaName}"
        response = requests.get(mediaUrl, headers=MAINHEADERS, stream=True)
        with open(mediaPath, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print("Media content downloaded!")
    else:
        mediaPath = mediaName

    if mediaName.endswith(PICTUREFORMATS):
        print(f"Media content is an image file in format .{mediaName.split('.')[1]}!")
        if not mediaPath.endswith((".png", ".pdf", ".gif")):
            print(f"Converting the image format to PNG...")
            outPutPNGPath = f"{os.path.dirname(mediaPath)}/{os.path.basename(mediaPath).split('.')[0]}.png"
            try:
                subprocess.run(["ffmpeg", "-i", mediaPath, outPutPNGPath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as PNGConversionError:
                AddingNewNSFWData(hashedMediaContent, "File Conversion Failure - Image Format can't be converted to PNG!")
                os.remove(mediaPath)
                print(f"Error: {PNGConversionError}\nError Converting the image format to PNG! Terminating Scan Process!")
                return True, "File Conversion Failure - Image Format can't be converted to PNG for scan, therefore the content is deleted!"
            mediaPath = outPutPNGPath
        else:
            print(f"Image already in PNG or PDF or GIF format!")
        if mediaPath.endswith(".png"):
            print("Scanning PNG image with nudenet...")
            if scanningImageWithNudenet(mediaPath):  # First check using nudenet
                print(f"Nudenet detected NSFW image!")
                AddingNewNSFWData(hashedMediaContent, "NSFW Image - Pre-trained NSFW model Nudenet detected NSFW element in the image!")
                os.remove(mediaPath)
                return True, "NSFW Image - Pre-trained NSFW model Nudenet detected NSFW element in the image!"
    elif mediaName.endswith(VIDEOFORMATS):
        print(f"Media content is a video file in format .{mediaName.split('.')[1]}!")
        print(f"Checking audio content from the video {mediaName}...")
        scanResult, scanResultDetails = await NSFWScanAudio(mediaPath, False)
        if scanResult:
            print("Video has NSFW audio content!")
            AddingNewNSFWData(hashedMediaContent, f"NSFW Video - Video has NSFW audio content: {scanResultDetails}")
            os.remove(mediaPath)
            return True, f"NSFW Video - Video has NSFW audio content: {scanResultDetails}"
        print("Scanning video frame with Nudenet!")
        cap = cv2.VideoCapture(mediaPath)
        frameNum = 0
        print(f"Video has total {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))} frames!")
        while frameNum < int(cap.get(cv2.CAP_PROP_FRAME_COUNT)):
            frameNum += 1
            success, frame = cap.read()
            if success:
                framePath = f"{MAINDOWNLOADDIR}{os.path.basename(mediaPath).split('.')[0]}frame_{frameNum}.png"
                cv2.imwrite(framePath, frame)
                HashedFramePath = getHashValueofAttachmentFileData(framePath)
                if HashedFramePath in CLEANData.keys():
                    print(f"Frame path {framePath} already in clean data!")
                    os.remove(framePath)
                else:
                    if HashedFramePath in NSFWData.keys():
                        print(f"Frame path {framePath} is in NSFW data!")
                        os.remove(framePath)
                        os.remove(mediaPath)
                        cap.release()
                        AddingNewNSFWData(hashedMediaContent, "NSFW Video - One of the video frame already flagged NSFW by Pre-Trained NSFW model Nudenet!")
                        return True, "NSFW Video - One of the video frame already flagged NSFW by Pre-Trained NSFW model Nudenet!"
                    if scanningImageWithNudenet(framePath):
                        print(f"Nudenet detected NSFW content at video Frame {frameNum}!")
                        AddingNewNSFWData(HashedFramePath, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!")
                        os.remove(framePath)
                        os.remove(mediaPath)
                        cap.release()
                        AddingNewNSFWData(hashedMediaContent, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!")
                        return True, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!"
                    AddingNewCleanData(HashedFramePath, "Nudenet detect video frame as cleaned!")
                    os.remove(framePath)
        cap.release()
    elif mediaName.endswith(AUDIOFORMATS):
        print(f"Media content is an audio file in format .{mediaName.split('.')[1]}!")
        scanResult, scanResultDetails = await NSFWScanAudio(mediaPath)
        if scanResult:
            print("Audio is not clean!")
            AddingNewNSFWData(hashedMediaContent, scanResultDetails)
            return True, scanResultDetails
        else:
            print("Audio is clean!")
            AddingNewCleanData(hashedMediaContent, scanResultDetails)
            return False, ""
    if not mediaPath.endswith(".pdf"):
        pdfPath = await PDFConversion(mediaPath)
    else:
        pdfPath = mediaPath
    if pdfPath == "Conversion failed":
        os.remove(mediaPath)
        print("Error converting media content to PDF frames!")
        return False, ""
    mediaScanResult = scanningPDFPagesWithGPT(pdfPath)
    os.remove(pdfPath)
    if mediaScanResult.startswith(("Yes", "yes", "YES")):
        mediaScanResult =  mediaScanResult.strip("Yes, ")
        if mediaName.endswith(PICTUREFORMATS):
            mediaScanResult = f"NSFW Image - {mediaScanResult}"
        elif mediaName.endswith(VIDEOFORMATS):
            mediaScanResult = f"NSFW Video - {mediaScanResult}"
        print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
        AddingNewNSFWData(hashedMediaContent, mediaScanResult)
        return True, mediaScanResult
    else:
        mediaScanResult = mediaScanResult.strip("No, ")
        if mediaName.endswith(PICTUREFORMATS):
            mediaScanResult = f"Clean Image - {mediaScanResult}"
        elif mediaName.endswith(VIDEOFORMATS):
            mediaScanResult = f"Clean Video - {mediaScanResult}"
        print(f"Content is clean!")
        AddingNewCleanData(hashedMediaContent, mediaScanResult)
        return False, mediaScanResult


def ArchivesBombAnalysisAndExtraction(filePath, archiveLayer=0):
    def checkingFileExtension(fileContent: bytes):
        mime = magic.from_buffer(fileContent, mime=True)
        Ext = mimetypes.guess_extension(mime)
        if Ext:
            if Ext == ".bin":
                if fileContent.startswith(b'PK'):
                    return '.zip'
                else:
                    return ".bin"
            return Ext
        else:
            print(f"Python-Magic did not detect")
            try:
                first1MegaBytesToASCII = fileContent.decode("ascii")
                if first1MegaBytesToASCII.isascii():
                    return ".txt"
            except UnicodeDecodeError:
                print(f"Starting filetype module...")
                Ext = filetype.guess(fileContent)
                if Ext:
                    return f".{Ext.extension}"
                else:
                    print(f"File extension can not be determined!")
                    return "Can't be determined"
    NESTEDARCHIVESIZELIMIT = 1000000000
    UNCOMPRESSEDSIZELIMIT = 32000000000
    CHUNKSIZE = 5000000000  # Read file to RAM content every 5 GB
    DUPLICATEDARCHIVELIMIT = 3
    TempDir = f"{MAINDOWNLOADDIR}{os.path.basename(filePath[0]).split('.')[0]}/"
    os.mkdir(TempDir)
    with open(filePath[0], 'rb') as rootFile:
        DuplicatedFileDectection = [hashlib.sha256(rootFile.read()).hexdigest()]
    uncompressedSize = os.path.getsize(filePath[0])
    totalDuplicatedArchive = 0
    while len(filePath) != 0:
        if archiveLayer == 7:
            print(f"The root archive file has 7 or more nested layers, hinted potential archive bomb!")
            return True
        for filepath in range(len(filePath)):
            if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                print(f"The total uncompressed size has reached the limit threshold!")
                return True
            with open(filePath[filepath], "rb") as ArchiveSource:
                ArchiveContent = ArchiveSource.read()
            fileExt = checkingFileExtension(ArchiveContent)
            if fileExt == "Can't be determined" and filePath[filepath].endswith(".lzma"):
                fileExt = ".lzma"
            print(f"Scanning Archive file: {os.path.basename(filePath[filepath])} at path {filePath[filepath]}...")
            if fileExt.endswith(".zip"):
                with zipfile.ZipFile(filePath[filepath], 'r') as zipRef:
                    for entry in zipRef.infolist():
                        DestinationPath = os.path.abspath(os.path.join(TempDir, os.path.basename(entry.filename)))
                        if not DestinationPath.startswith(os.path.abspath(TempDir)):
                            print(f"The uncompressed file name {entry.filename} formed an illegal path"
                                  f" {DestinationPath} to cause directory transversal attack!")
                            return True
                        try:
                            with zipRef.open(entry, 'r') as source:
                                if source is None:
                                    continue
                                fileData = b''
                                while True:
                                    Datachunk = source.read(CHUNKSIZE)
                                    if not Datachunk:
                                        break
                                    fileData += Datachunk
                                    uncompressedSize += len(Datachunk)
                                    if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                        print(f"The total uncompressed size has reached the limit threshold!")
                                        return True
                            if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._"):
                                hashedData = hashlib.sha256(fileData).hexdigest()
                                if hashedData not in DuplicatedFileDectection:
                                    if checkingFileExtension(fileData).endswith(ALLSCANNABLEFILEFORMATS):
                                        with open(DestinationPath, 'wb') as file:
                                            file.write(fileData)
                                        print(f"{entry.filename} is written to path {DestinationPath}")
                                    DuplicatedFileDectection.append(hashedData)
                                else:
                                    if checkingFileExtension(fileData).endswith(ARCHIVEFORMATS):
                                        totalDuplicatedArchive += 1
                                        print(f"Duplicated archive file at path {DestinationPath}")
                                        if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                            return True
                                    else:
                                        print(f"Duplicated file at path {DestinationPath}")
                        except TypeError:
                            print(f"The extracted content of {os.path.basename(filePath[filepath])} is empty!")
                            pass
                        except zipfile.BadZipFile:
                            pass
                        except RuntimeError as e:
                            if 'password required' in str(e).lower():
                                print("Zip file is encrypted!")
                                return True
                            else:
                                pass
                        except OSError:
                            pass
            elif fileExt.endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz")):
                with tarfile.open(filePath[filepath], 'r') as tarRef:
                    for entry in tarRef.getmembers():
                        DestinationPath = os.path.abspath(os.path.join(TempDir, os.path.basename(entry.name)))
                        if not DestinationPath.startswith(os.path.abspath(TempDir)):
                            print(f"The uncompressed file name {entry.name} formed an illegal path"
                                  f" {DestinationPath} to cause directory transversal attack!")
                            return True
                        try:
                            with tarRef.extractfile(entry) as source:
                                if source is None:
                                    continue
                                fileData = b''
                                while True:
                                    Datachunk = source.read(CHUNKSIZE)
                                    if not Datachunk:
                                        break
                                    fileData += Datachunk
                                    uncompressedSize += len(Datachunk)
                                    if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                        print(f"The total uncompressed size has reached the limit threshold!")
                                        return True
                                if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._"):
                                    hashedData = hashlib.sha256(fileData).hexdigest()
                                    if hashedData not in DuplicatedFileDectection:
                                        if checkingFileExtension(fileData).endswith(ALLSCANNABLEFILEFORMATS):
                                            with open(DestinationPath, 'wb') as file:
                                                file.write(fileData)
                                            print(f"{entry.name} is written to path {DestinationPath}")
                                        DuplicatedFileDectection.append(hashedData)
                                    else:
                                        if checkingFileExtension(fileData).endswith(ARCHIVEFORMATS):
                                            totalDuplicatedArchive += 1
                                            print(f"Duplicated archive/disk file at path {DestinationPath}")
                                            if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                                return True
                                        else:
                                            print(f"Duplicated file at path {DestinationPath}")
                        except TypeError:
                            print(f"The extracted content of {os.path.basename(filePath[filepath])} is empty!")
                            pass
                        except (OSError, tarfile.TarError):
                            pass
            elif fileExt.endswith(".rar"):
                with rarfile.RarFile(filePath[filepath], 'r') as rar:
                    if rar.needs_password():
                        print(f"Rar file {filePath[filepath]} required password!")
                        return True
                    for entry in rar.infolist():
                        if entry.needs_password():
                            print(f"Rar file {entry.filename} required password!")
                            return True
                        DestinationPath = os.path.abspath(os.path.join(TempDir, os.path.basename(entry.filename)))
                        if not DestinationPath.startswith(os.path.abspath(TempDir)):
                            print(f"The uncompressed file name {entry.filename} formed an illegal path"
                                  f" {DestinationPath} to cause directory transversal attack!")
                            return True
                        try:
                            with rar.open(entry, 'r') as source:
                                if source is None:
                                    continue
                                fileData = b''
                                while True:
                                    Datachunk = source.read(CHUNKSIZE)
                                    if not Datachunk:
                                        break
                                    fileData += Datachunk
                                    uncompressedSize += len(Datachunk)
                                    if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                        print(f"The total uncompressed size has reached the limit threshold!")
                                        return True
                            if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._"):
                                hashedData = hashlib.sha256(fileData).hexdigest()
                                if hashedData not in DuplicatedFileDectection:
                                    if checkingFileExtension(fileData).endswith(ALLSCANNABLEFILEFORMATS):
                                        with open(DestinationPath, 'wb') as file:
                                            file.write(fileData)
                                        print(f"{entry.filename} is written to path {DestinationPath}")
                                    DuplicatedFileDectection.append(hashedData)
                                else:
                                    if checkingFileExtension(fileData).endswith(ARCHIVEFORMATS):
                                        totalDuplicatedArchive += 1
                                        print(f"Duplicated archive/disk file at path {DestinationPath}")
                                        if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                            return True
                                    else:
                                        print(f"Duplicated file at path {DestinationPath}")
                        except TypeError:
                            print(f"The extracted content of {os.path.basename(filePath[filepath])} is empty!")
                            pass
                        except (rarfile.BadRarFile, OSError, rarfile.NotRarFile):
                            pass
            elif fileExt.endswith((".gz", ".bz2", ".xz", ".lzma")):
                try:
                    fileName = os.path.basename(filePath[filepath]).rsplit(fileExt, 1)[0]
                    DestinationPath = os.path.join(TempDir, fileName)
                    if not DestinationPath.startswith(os.path.abspath(TempDir)):
                        print(f"The uncompressed file name {fileName} formed an illegal path"
                              f" {DestinationPath} to cause directory transversal attack!")
                        return True
                    fileData = b''
                    if fileExt.endswith(".bz2"):
                        with bz2.BZ2File(filePath[filepath], 'rb') as bz2File:
                            while True:
                                dataChunk = bz2File.read(CHUNKSIZE)
                                if not dataChunk or len(fileData) >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                    elif fileExt.endswith(".gz"):
                        with gzip.open(filePath[filepath], 'rb') as gzipRef:
                            while True:
                                dataChunk = gzipRef.read(CHUNKSIZE)
                                if not dataChunk or len(fileData) >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                    elif fileExt.endswith((".xz", ".lzma")):
                        with lzma.open(filePath[filepath], 'rb') as lzFile:
                            while True:
                                dataChunk = lzFile.read(CHUNKSIZE)
                                if not dataChunk or len(fileData) >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                    uncompressedSize += len(fileData)
                    if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                        print(f"The total uncompressed size has reached the limit threshold!")
                        return True
                    fileExt = checkingFileExtension(fileData)
                    if fileExt == "Can't be determined" and filePath[filepath].endswith(".lzma"):
                        fileExt = ".lzma"
                    if fileExt.endswith(ARCHIVEFORMATS):
                        DestinationPath += fileExt
                    hashedData = hashlib.sha256(fileData).hexdigest()
                    if hashedData not in DuplicatedFileDectection:
                        if  checkingFileExtension(fileData).endswith(ALLSCANNABLEFILEFORMATS):
                            with open(DestinationPath, "wb") as file:
                                file.write(fileData)
                            print(f"{fileName} is written to path {DestinationPath}")
                        DuplicatedFileDectection.append(hashedData)
                    else:
                        if checkingFileExtension(fileData).endswith(ARCHIVEFORMATS):
                            totalDuplicatedArchive += 1
                            print(f"Duplicated archive/disk file at path {DestinationPath}")
                            if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                return True
                        else:
                            print(f"Duplicated file at path {DestinationPath}")
                except (OSError, lzma.LZMAError, OSError):
                    pass
            os.remove(filePath[filepath])

        archiveLayer += 1
        filePath.clear()
        for dirpath, dirnames, filenames in os.walk(TempDir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "rb") as file:
                    fileData = file.read()
                fileExt = checkingFileExtension(fileData)
                if fileExt == "Can't be determined" and filepath.endswith(".lzma"):
                    fileExt = ".lzma"
                if fileExt.endswith(ARCHIVEFORMATS):
                    print(f"Found nested Archive file {filename} at path {filepath}")
                    if os.path.getsize(filepath) >= NESTEDARCHIVESIZELIMIT:
                        print(f"The nested file {filename} size is {os.path.getsize(filepath)}. The number is"
                              f" too large, thus, hinted potential archive bomb!")
                        return True
                    filePath.append(filepath)
    print(f"Archive content extracted with total uncompressed size of {uncompressedSize} bytes")
    return False


async def ArchiveFileScan(archiveFileName, fileUrl, hashedArchiveFileData):  # Return True to continue the scan process
    response = requests.get(fileUrl, headers=MAINHEADERS, stream=True)
    mainArchiveFilePath = f"{MAINDOWNLOADDIR}{archiveFileName}"
    with open(mainArchiveFilePath, "wb") as file:
        for chunk in response.iter_content(1024):
            file.write(chunk)
    print(f"Archive name: {archiveFileName}")
    print("Archive attachment downloaded!")
    print(f"Checking if archive is safe to extract!")
    if ArchivesBombAnalysisAndExtraction([mainArchiveFilePath]):
        AddingNewNSFWData(hashedArchiveFileData, "Archive File - Potential Archive Bomb!")
        print("The Archive File is flagged as potential archive bomb!")
        return True, ""  # Cyber bot will delete the archive bomb!
    TempDir = f"{MAINDOWNLOADDIR}{archiveFileName.split('.')[0]}"
    print(f"Scanning content in temp directory: {TempDir}...\n\n")
    for dirpath, _, filenames in os.walk(TempDir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            fixedFileExt = filename.split(".")
            fixedFileExt.pop(0)
            if filename.startswith("._"):  # Remove duplicated ._ file
                os.remove(filepath)
            print(f"Found media file {filename} at path {filepath}")
            hashedFileContent = getHashValueofAttachmentFileData(filepath)
            if hashedFileContent in CLEANData.keys():
                print("Media file content already pass the scan!\n\n")
            else:
                print(f"Media file content is not in the clean data! Checking if it is in the NSFW data!")
                if hashedFileContent in NSFWData.keys():
                    print("Media file content already flagged NSFW!")
                    shutil.rmtree(TempDir)
                    AddingNewNSFWData(hashedArchiveFileData, f"The file content {filename} in Archive file has already flagged NSFW! Reason: {NSFWData[hashedFileContent]}")
                    return False, f"NSFW Archive Content - The file content {filename} in Archive file has already flagged NSFW! Reason: {NSFWData[hashedFileContent]}"
                else:
                    scanResult,  scanResultDetails = await ScanningMedia(filepath, "Blank", hashedFileContent, False)
                    if scanResult:
                        print(f"File content {filename} in Archive file was flagged NSFW!")
                        shutil.rmtree(TempDir)
                        AddingNewNSFWData(hashedArchiveFileData, f"File content {filename} in Archive file was flagged NSFW! Reason: {scanResultDetails}")
                        return False, f"NSFW Archive Content - File content {filename} in Archive file was flagged NSFW! Reason: {scanResultDetails}"
                    print("\n\n")
    print(f"Archive content is clean!")
    AddingNewCleanData(hashedArchiveFileData, "Archive contents passed the check!")
    shutil.rmtree(TempDir)
    return True, ""


async def NSFWScanAudio(inputPath, delete=True):  # Return True if Audio is NSFW!
    audioName = os.path.basename(inputPath).split('.')[0]
    # Running ffmpeg command to convert any input file to specific WAV audio format
    if not inputPath.endswith(".wav"):
        print("Converting Audio to WAV file format...")
        waveFilePath = f"{os.path.dirname(inputPath)}/{audioName}.wav"
        try:
            subprocess.run(["ffmpeg", "-i", inputPath, "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", waveFilePath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if delete:
                os.remove(inputPath)
        except Exception as ConversionToWavAudioError:
            if delete:
                print(f"Error {ConversionToWavAudioError}")
                os.remove(inputPath)
                return True, "File Conversion Failure - Can not convert audio file to WAV format!"
            else:
                print(f"Error {ConversionToWavAudioError} while extracting audio from the video! Proceeding to scan video content...")
                return False, ""
    else:
        print("Audio file already in .wav format!")
        waveFilePath = inputPath

    audioFile = open(waveFilePath, "rb")

    transcription = GPTclient.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audioFile
    )
    print(f"Words detected from audio file: {transcription.text}")
    os.remove(waveFilePath)
    scanResult, scanResultDetails = await NSFWscanMessage(transcription.text)
    if scanResult:
        return True, f"NSFW Audio Transcript - {scanResultDetails}"
    else:
        return False, f"Clean Audio Transcript - {scanResultDetails}"


async def NSFWscanMessage(checkMessage, URL=False):  # Return True if text content is NSFW!
    print("Scanning content using Profanity Library...")
    if profanity.contains_profanity(checkMessage):
        print("Profanity Library detected inappropriate message!")
        if URL:
            return True, "URL contains keywords in Emmanuel default NSFW wordlist!"
        else:
            return True, "Message contains keywords in Emmanuel default NSFW wordlist!"
    print("Profanity Library did not detect, starting GPT scan...")
    if not URL:
        DetectedPhrase = ScanningTextOnlyWithGPT(
            f"Analyze the following message and identify any vulgar or inappropriate words.\n"
            f"Consider the context—only flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
            f"Taking into measure the text could be written in other language than English, this does means that some characters in the text may be another language alphabet or a letter emoji.\n"
            f"Response MUST start with a Yes or No! If and only if IT'S a YES, follow by a COMMA and EXPLAIN the reason NO MORE THAN 30 WORDS!\n"
            f"Message: '{checkMessage}'\n")
    else:
        DetectedPhrase = ScanningTextOnlyWithGPT(
            f"Analyze the following URL query and identify any vulgar or inappropriate words.\n"
            f"Consider the context—only flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
            f"Taking into measure the text could be written in other language than English, this does means that some characters in the text may be another language alphabet or a letter emoji.\n"
            f"Response MUST start with a Yes or No! If and only if IT'S a YES, follow by a COMMA and EXPLAIN the reason NO MORE THAN  30 WORDS!\n"
            f"Message: '{checkMessage}'\n")
    if DetectedPhrase.startswith(("Yes", "yes", "YES")):
        print("GPT detected inappropriate content!")
        return True, DetectedPhrase.strip("Yes,")
    print("GPT scan result is clean!")
    return False, DetectedPhrase.strip("No, ")


async def AdvanceBackTrackMessageScan(message):
    if not str(message.channel) == "Direct Message with Unknown User":  # Only use better_profanity
        scanList = []
        lengthList = []
        indexList = []
        async for text in message.channel.history(limit=10):
            scanList.insert(0, text.content)
        # print(f"Scan list: {scanList}")
        for p in range(len(scanList)):
            if p != 0:
                lengthList.append(len(scanList[p]) + lengthList[p - 1])
            else:
                lengthList.append(len(scanList[p]))
        # print(f"Legnth list: {lengthList}")
        scanList = "".join(scanList)
        # print(f"Lowercase Scan list: {scanList.lower()}")
        position = []

        for word in WordList:
            pattern = re.escape(word)  # Escapes special characters in word
            matches = [[match.start(), match.end()] for match in re.finditer(pattern, scanList, re.IGNORECASE)]
            if matches:
                for Index in matches:
                    position.append(Index)
        position.sort()
        # print(f"Position List: {position}")
        if position:
            for Range in position:
                for p in range(Range[0], Range[1], 1):
                    indexList.append(p)
            # print(f"Index List: {indexList}")
            finalIndexList = []
            for value in indexList:
                try:
                    finalIndexList.append(lengthList.index(value) + 1)
                except ValueError:
                    pass
            # print(f"Final Index: {finalIndexList}")
            counter = 9
            async for text in message.channel.history(limit=10):
                if counter in finalIndexList:
                    await text.delete()
                counter -= 1


@Emmanuel.tree.command(
    name="emmanuel",
    description="Get Information about Knight Emmanuel."
)
async def emmanuel(ctx):
    await ctx.response.send_message("I'm a knight designed by Sir David Nguyen with a purpose of scanning message, audio, "
                                    "photo, gif, and video attachment in Server Channel that I am authorized to detect "
                                    "inappropriate content using OpenAI LLMs, delete them, and annoy you with a DM warning"
                                    " to stop sending NSFW content! I won't response to any Direct Messages!!!\n"
                                    "If you like to delete DM messages from me, use the command /clear_emmanuel_dm_messages.\n"
                                    "I have limitation to certain file formats that I am capable of scanning. The list can be checked "
                                    "by the command /list_supported_file.")


@Emmanuel.tree.command(
    name="list_supported_file",
    description="Get a list of file formats Emmanuel can scan"
)
async def list_supported_file(ctx):
    await ctx.response.send_message(
        "Image Formats: .jpg, .png, .jpeg, .raw, .pdf, .bmp, .webp, .tiff, .tif, .ico, .icns, .avif, .odd, .eps, .gif\n"
        "Video Formats: .mp4, .mov, .mkv, .avi, .m4v, .flv, .mpeg, mpg, .ts, .wmv, .dv, .mts, .m2ts, .vob, .ogv\n"
        "Audio Formats: .mp3, .wav, .oga, .m4a, .flac, .weba, .aac, .ac3, .aif, .aiff, .aifc, .amr, .au, .caf, .m4a,"
        " .m4b, .wma, .opus, .webm, .ogg\n"
        "Archive Formats: .zip, .tar, .tar.gz, .tar.bz2, .tar.xz, .tar.lzma, .tgz, .tbz2, .txz, .gz, .rar, .bz2, .xz, .lzma"
    )


@Emmanuel.tree.command(
    name="clear_emmanuel_dm_messages",
    description="Delete all direct messages sent by Knight Emmanuel to you"
)
async def clear_emmanuel_dm_messages(ctx):
    await ctx.response.defer()
    async for message in ctx.user.history():
        if message.author == Emmanuel.user:
            await message.delete()
    if str(ctx.channel.type).startswith("private"):
        async for message in ctx.user.history(limit=1):
            if message.author == Emmanuel.user:
                await message.delete()
    else:
        await ctx.channel.purge(limit=1)


@Emmanuel.event
async def on_ready():
    await Emmanuel.wait_until_ready()
    print(f"Logged in as {Emmanuel.user} (ID: {Emmanuel.user.id})")
    print("Knight Emmanuel is ONLINE!")

    #  Synced all commands -> Add new command if not already existed, else update the pre-existing command
    await Emmanuel.tree.sync()
    SynedCmds = await Emmanuel.tree.fetch_commands()
    for cmd in SynedCmds:
        print(f"Synced command /{cmd.name}")
    print(f"Commands are updated and ready to use!")
    print("\n\n")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="add_uncensored_member",
    description="Adding a server member to the uncensored list!"
)
@app_commands.describe(member="Please mention a member in the server!")
async def add_uncensored_member(ctx, member: discord.Member):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/add_uncensored_member can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                configuration[str(ctx.guild.id)]["Uncensored-members"].append(member.id)
                with open(EMMANUELCONFIG, "w") as file:
                    json.dump(configuration, file, indent=4)
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{member.name} has been added to the white list!")
            else:
                await ctx.followup.send(f"{member.name} already added to the white list!")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="remove_uncensored_member",
    description="Removing a server member off the uncensored list!"
)
@app_commands.describe(member="Please mention a member in the server!")
async def remove_uncensored_member(ctx, member: discord.Member):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/remove_uncensored_member can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                await ctx.followup.send(f"{member.name} already removed from the white list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-members"].remove(member.id)
                with open(EMMANUELCONFIG, "w") as file:
                    json.dump(configuration, file, indent=4)
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{member.name} has been removed from the white list!")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="add_uncensored_channel",
    description="Adding a server channel to the uncensored list!"
)
async def add_uncensored_channel(ctx):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/add_uncensored_channel can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            if ctx.channel.id in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                await ctx.followup.send(f"{ctx.channel.name} already added to the uncensored list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-channels"].append(ctx.channel.id)
                with open(EMMANUELCONFIG, "w") as file:
                    json.dump(configuration, file, indent=4)
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{ctx.channel.name} has been added from the white list!")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="remove_uncensored_channel",
    description="Removing a server channel off the uncensored list!"
)
async def remove_uncensored_channel(ctx):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/remove_uncensored_channel can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            if ctx.channel.id not in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                await ctx.followup.send(f"{ctx.channel.name} already removed from the uncensored list!")
            else:
                configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(ctx.channel.id)
                with open(EMMANUELCONFIG, "w") as file:
                    json.dump(configuration, file, indent=4)
                print(f"Configuration file updated: {configuration}\n\n")
                await ctx.followup.send(f"{ctx.channel.name} has been removed from the white list!")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="uncensored_members",
    description="List all the member who are not being monitored by Emmanuel in the server")
async def uncensored_members(ctx):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/uncensored_members can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            members = ""
            for memberID in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                member = Emmanuel.get_user(memberID)
                if member:
                    members += f"Member ID: {member.id}\tMember name: {member.name}\n"
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(memberID)
                    with open(EMMANUELCONFIG, "w") as file:
                        json.dump(configuration, file, indent=4)
            await ctx.followup.send(f"Uncensored members for server {ctx.guild.name} ID {ctx.guild.id}:\n{members}")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


# Command for Creator and Server Owner Only!
@Emmanuel.tree.command(
    name="uncensored_channels",
    description="List all the channels not being monitored by Emmanuel in the server")
async def uncensored_channels(ctx):
    await ctx.response.defer(ephemeral=True)
    if str(ctx.channel.type).startswith("private"):
        await ctx.followup.send("/uncensored_channels can only be used in server channels!")
    else:
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == 987765832895594527:
            checkServerExistInConfigFile(str(ctx.guild.id))
            channels = ""
            for channelID in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                channel = Emmanuel.get_channel(channelID)
                if channel:
                    channels += f"Channel ID: {channel.id}\tChannel name: {channel.name}\n"
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(channelID)
                    with open(EMMANUELCONFIG, "w") as file:
                        json.dump(configuration, file, indent=4)
            await ctx.followup.send(f"Uncensored channels for server {ctx.guild.name} ID {ctx.guild.id}:\n{channels}")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


@Emmanuel.event
async def on_message_edit(before, after):  # Note: media attachment can be embedded via URL in re-edit message!
    # Prioritize Executing commands first!
    await Emmanuel.process_commands(after)

    # Add new server to the configuration file!
    try:
        checkServerExistInConfigFile(str(after.guild.id))
    except AttributeError:
        pass

    if str(after.channel) != "Direct Message with Unknown User":
        if after.author.id == Emmanuel.user.id:
            return

        if after.author.id in configuration[str(after.guild.id)]["Uncensored-members"]:
            writingLog(f"User: {after.author.name} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}\nNOTE: User is on the server uncensored members list\n\n")
            return

        if after.channel.id in configuration[str(after.guild.id)]["Uncensored-channels"]:
            writingLog(f"User: {after.author.name} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}\nNOTE: The channel is on the server uncensored channels list\n\n")
            return

        if before.content != after.content:
            print("Re-Edit message detected!!!")

            """Logging user message"""
            logUserAction = f"User: {after.author.name} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}"
            textContent = after.content

            """Checking if a URL in a message and make sure only one URL"""
            if "https://" in after.content or "http://" in after.content:
                print("Re-Edited Message contains URL link(s)! Checking all the URL(s)...")
                URLs = re.findall(r'https?://(?:(?!https?://)\S)+', after.content)

                for URL in URLs:
                    print(f"Extracting {URL} from message {after.content}")
                    textContent = textContent.replace(URL, '')
                    if "../" in URL:
                        try:
                            await after.author.send(f"URL {URL} hinted a potential ../ attack!")
                        except discord.Forbidden:
                            await after.reply(f"{after.author.mention}, URL {URL} hinted a potential ../ attack!")
                        logUserAction += "\nReedited-Message is deleted for having a URL hinted potential directory transversal attack!!\n\n"
                        writingLog(logUserAction)
                        # Advance scan previous message for profanity!
                        await after.delete()
                        await AdvanceBackTrackMessageScan(after)
                        print(f"URL {URL} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                        return

                    """Checking if URl is in the clean list or already flagged NSFW"""

                    if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                        BasedURLToSave = hashlib.sha512(URL.split('?')[0].lower().encode()).hexdigest()
                    else:
                        BasedURLToSave = hashlib.sha512(URL.encode()).hexdigest()
                    print(f"URL in SHA512 format: {BasedURLToSave}")
                    if BasedURLToSave in CLEANData.keys():
                        print("The URL already passed the check as clean!\n\n")
                    else:
                        if BasedURLToSave in NSFWData.keys():
                            try:
                                await after.author.send(
                                    f"The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                            except discord.Forbidden:
                                await after.reply(
                                    f"{after.author.mention}, The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                            await after.delete()
                            logUserAction += f"\nReedited-Message was deleted for having URL content already flagged NSFW!\n\n"
                            writingLog(logUserAction)
                            # Advance scan previous message for profanity!
                            await AdvanceBackTrackMessageScan(after)
                            print("The URL already flagged NSFW! Terminating Scan Process...\n\n")
                            return
                        else:
                            """Checking any NSFW hint in the URL query"""
                            print("Checking any hinted NSFW in URL name...")
                            scanResult, scanResultDetails = await NSFWscanMessage(URL, True)
                            if scanResult:
                                AddingNewNSFWData(BasedURLToSave, f"NSFW URL name - {scanResultDetails}")
                                try:
                                    await after.author.send(f"The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                except discord.Forbidden:
                                    await after.reply(f"{after.author.mention}, The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                await after.delete()
                                logUserAction += f"\nReedited-Message was deleted for having URL name hinted NSFW!\n\n"
                                writingLog(logUserAction)
                                # Advance scan previous message for profanity!
                                await AdvanceBackTrackMessageScan(after)
                                print(f"URL name hinted NSFW content! Terminating Scan Process...\n\n")
                                return
                            """Checking if URL is valid!"""
                            try:
                                response = requests.get(URL, headers=MAINHEADERS)
                                if response.status_code == 200:
                                    print(f"URL is valid!")
                                    """Checking Tenor Gif"""
                                    if URL.startswith("https://tenor.com/view"):
                                        print("URL appear to be a Tenor Gif, checking if Tenor gif is valid...")
                                        TenorURL = isTenorURLValid(URL)
                                        if TenorURL != "Invalid":
                                            print("Tenor gif URL is valid!")
                                            scanResult, scanResultDetails = await ScanningMedia(f"{os.path.basename(TenorURL).split('?')[0]}.gif", TenorURL, BasedURLToSave)
                                            if scanResult:
                                                try:
                                                    await after.author.send(
                                                        f"Tenor URL <{URL}> content flagged NSFW - {scanResultDetails}")
                                                except discord.Forbidden:
                                                    await after.reply(
                                                        f"{after.author.mention}, Tenor URL <{URL}> content flagged NSFW - {scanResultDetails}")
                                                await after.delete()
                                                logUserAction += f"\nReedited Message was deleted for having Tenor Gif URL with NSFW content!\n\n"
                                                writingLog(logUserAction)
                                                # Advance scan previous message for profanity!
                                                await AdvanceBackTrackMessageScan(after)
                                                print("Re-Edit Message Content Scan Process Finished!\n\n")
                                                return
                                            else:
                                                print("Tenor Gif content is clean!")
                                        else:
                                            print(f"Tenor gif URL {URL} is not a valid tenor gif!")
                                            try:
                                                await after.author.send("Your message contains an invalid Tenor URL! Please provide a valid URL!")
                                            except discord.Forbidden:
                                                await after.reply(f"{after.author.mention}, Your message contains an invalid Tenor URL! Please provide a valid URL!")
                                            await after.delete()
                                            logUserAction += f"\nReedited Message was deleted for having invalid Tenor Gif URL!\n\n"
                                            writingLog(logUserAction)
                                            # Advance scan previous message for profanity!
                                            await AdvanceBackTrackMessageScan(after)
                                            print("Re-Edit Message Content Scan Process Finished!\n\n")
                                            return
                                    else:
                                        """Analyzing if URL content is an image, video, audio, or archive file"""
                                        """Checking if URL content already been scanned"""
                                        hashedURLContent = hashlib.sha512(response.content).hexdigest()
                                        print(f"URL Content in SHA512: {hashedURLContent}")
                                        print(f"Checking if URL content is already in a clean list...")
                                        if hashedURLContent in CLEANData.keys():
                                            print("URL content already pass the scan!")
                                            print("Adding based URL to clean data!")
                                            AddingNewCleanData(BasedURLToSave,f"URL content already passed the check - {CLEANData[hashedURLContent]}")
                                        else:
                                            print(f"URL content is not in the clean data! Checking if the content is in the NSFW data!")
                                            if hashedURLContent in NSFWData.keys():
                                                print("URL content already flagged NSFW!")
                                                print(f"Adding based URL to NSFW data!")
                                                AddingNewNSFWData(BasedURLToSave,f"URL content already flagged NSFW! - {NSFWData[hashedURLContent]}")
                                                try:
                                                    await after.author.send(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                                except discord.Forbidden:
                                                    await after.reply(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                                await after.delete()
                                                logUserAction += f"\nReedited-Message was deleted for having URL content already flagged NSFW!\n\n"
                                                writingLog(logUserAction)
                                                # Advance scan previous message for profanity!
                                                await AdvanceBackTrackMessageScan(after)
                                                print("Re-Edit Message Content Scan Process Finished!\n\n")
                                                return
                                            else:
                                                URLContentExt = checkingRealFileExtension(URL, os.path.basename(URL.split('?')[0].lower()))
                                                URLContentName = f"{os.path.basename(URL.split('?')[0]).split('.')[0]}{URLContentExt}"
                                                if URLContentName.endswith(ALLSCANNABLEFILEFORMATS):
                                                    if URLContentExt.endswith(ARCHIVEFORMATS):
                                                        UrlContentNSFWResult, UrlContentNSFWResultDetails = not await ArchiveFileScan(URLContentName, URL, BasedURLToSave)
                                                    else:
                                                        UrlContentNSFWResult, UrlContentNSFWResultDetails = await ScanningMedia(URLContentName, URL, BasedURLToSave)
                                                else:
                                                    UrlContentNSFWResult = False
                                                    UrlContentNSFWResultDetails = ""
                                                    AddingNewCleanData(BasedURLToSave,"URL link is clean or URL content is not in Emmanuel scannable file formats!")
                                                print("Scan Process Finished!\n\n")
                                                if UrlContentNSFWResult:
                                                    try:
                                                        await after.author.send(UrlContentNSFWResultDetails)
                                                    except discord.Forbidden:
                                                        await after.reply(f"{after.author.mention}, {UrlContentNSFWResultDetails}")
                                                    await after.delete()
                                                    logUserAction += f"\nRe-edited Message was deleted for having NSFW URL content\n\n"
                                                    writingLog(logUserAction)
                                                    # Advance scan previous message for profanity!
                                                    await AdvanceBackTrackMessageScan(after)
                                                    return
                                else:
                                    print(f"URL is invalid with status code {response.status_code}!")
                                    if URL.startswith(("https://cdn.discordapp.com/attachments/","https://media.discordapp.net/attachments/")):
                                        try:
                                            await after.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        except discord.Forbidden:
                                            await after.reply(f"{after.author.mention}, The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        await after.delete()
                                        logUserAction += f"\nRe-Edit Message is deleted for having a discord attachment URL {URL} can not be scanned!\n\n"
                                        writingLog(logUserAction)
                                        # Advance scan previous message for profanity!
                                        await AdvanceBackTrackMessageScan(after)
                                        print("Re-Edit Message Content Scan Process Finished!\n\n")
                                        return
                                    else:
                                        logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"
                            except Exception as URLQueryError:
                                print(f"Error getting URL: {URLQueryError}.")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                                    try:
                                        await after.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                    except discord.Forbidden:
                                        await after.reply(f"{after.author.mention}, The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                    await after.delete()
                                    logUserAction += f"\nRe-Edit Message is deleted for having a discord attachment URL {URL} can not be scanned!\n\n"
                                    writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(after)
                                    print("Re-Edit Message Content Scan Process Finished!\n\n")
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"

            """Scanning message text content with hyperlink removed"""
            if textContent:
                print(f"Scanning text content with URL already filtered...")
                print(f"Text content: {textContent}")
                scanResult, scanResultDetails = await NSFWscanMessage(textContent)
                if scanResult:
                    try:
                        await after.author.send(scanResultDetails)
                    except discord.Forbidden:
                        await after.reply(f"{after.author.mention}, {scanResultDetails}")
                    await after.delete()
                    logUserAction += f"\nReedited Message was deleted for having NSFW text content!\n\n"
                else:
                    logUserAction += f"\nReedited Message is cleaned!\n\n"
                    print("Message text content is clean!")
            else:
                logUserAction += f"\nReedited Message is cleaned!\n\n"
            # Advance scan previous message for profanity!
            await AdvanceBackTrackMessageScan(after)
            writingLog(logUserAction)
            print("Re-Edit Message Content Scan Process Finished!\n\n")


@Emmanuel.event
async def on_message(message):

    # Prioritize Executing commands first!
    await Emmanuel.process_commands(message)

    # Add new server to the configuration file!
    try:
        checkServerExistInConfigFile(str(message.guild.id))
    except AttributeError:
        pass

    if str(message.channel) != "Direct Message with Unknown User":
        """Logging user message"""
        logUserAction = f"User: {message.author.name} sent message: {message.content}"
        if len(message.attachments) != 0:
            for attachment in message.attachments:
                logUserAction += f"\nwith file attachment: {attachment.filename}" \
                                 f"\ntemporary URL: {attachment.url}"
        logUserAction += f"\nFrom channel '{message.channel.name}' - ID {message.channel.id} in Server '{message.guild.name}' - ID {message.guild.id}"

        if message.author.id in configuration[str(message.guild.id)]["Uncensored-members"]:
            logUserAction += f"\nNOTE: User is on the server uncensored members list!\n\n"
            writingLog(logUserAction)
            return

        if message.channel.id in configuration[str(message.guild.id)]["Uncensored-channels"]:
            logUserAction += f"\nNOTE: The channel is on the server uncensored channels list!\n\n"
            writingLog(logUserAction)
            return

        if message.content:
            textContent = message.content
            """Checking if a URL in a message and make sure only one URL"""
            if "https://" in message.content or "http://" in message.content:
                print("Message contains URL link(s)! Checking all the URL(s)...")
                URLs = re.findall(r'https?://(?:(?!https?://)\S)+', message.content)

                for URL in URLs:
                    textContent = textContent.replace(URL, '')
                    print(f"Extracting {URL} from message {message.content}")

                    if "../" in URL:
                        print(f"URL {URL} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                        try:
                            await message.author.send(f"URL {URL} hinted a potential ../ attack!")
                        except Exception as error:
                            print(f"Discord Error: {error}")
                        logUserAction += "\nMessage is deleted for having a URL hinted potential directory transversal attack!!\n\n"
                        writingLog(logUserAction)
                        await message.delete()
                        # Advance scan previous message for profanity!
                        await AdvanceBackTrackMessageScan(message)
                        return


                    """Checking if URl is in the clean list or already flagged NSFW"""

                    if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                        BasedURLToSave = hashlib.sha512(URL.split('?')[0].lower().encode()).hexdigest()
                    else:
                        BasedURLToSave = hashlib.sha512(URL.encode()).hexdigest()
                    print(f"URL in SHA512 format: {BasedURLToSave}")
                    if BasedURLToSave in CLEANData.keys():
                        print("The URL already passed the check as clean!")
                    else:
                        if BasedURLToSave in NSFWData.keys():
                            try:
                                await message.author.send(f"The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                            except discord.Forbidden:
                                await message.reply(f"{message.author.mention}, The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                            await message.delete()
                            logUserAction += f"\nMessage was deleted for having URL content already flagged NSFW!\n\n"
                            writingLog(logUserAction)
                            # Advance scan previous message for profanity!
                            await AdvanceBackTrackMessageScan(message)
                            print("The URL already flagged NSFW! Terminating Scan Process...\n\n")
                            return
                        else:
                            """Checking any NSFW hint in the URL query"""
                            print("Checking any hinted NSFW in URL name...")
                            scanResult, scanResultDetails = await NSFWscanMessage(URL, True)
                            if scanResult:
                                AddingNewNSFWData(BasedURLToSave, f"NSFW URL name - {scanResultDetails}")
                                try:
                                    await message.author.send(f"The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                except discord.Forbidden:
                                    await message.reply(f"{message.author.mention}, The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                await message.delete()
                                logUserAction += f"\nMessage was deleted for having URL name hinted NSFW!\n\n"
                                writingLog(logUserAction)
                                # Advance scan previous message for profanity!
                                await AdvanceBackTrackMessageScan(message)
                                print(f"URL name hinted NSFW content! Terminating Scan Process...\n\n")
                                return
                            """Checking if URL is valid!"""
                            try:
                                response = requests.get(URL, headers=MAINHEADERS)
                                if response.status_code == 200:
                                    print(f"URL is valid!")
                                    """Checking Tenor Gif"""
                                    if URL.startswith("https://tenor.com/view"):
                                        print("URL appear to be a Tenor Gif, checking if Tenor gif is valid...")
                                        TenorURL = isTenorURLValid(URL)
                                        if TenorURL != "Invalid":
                                            print("Tenor gif URL is valid!")
                                            scanResult, scanResultDetails = await ScanningMedia(f"{os.path.basename(TenorURL).split('?')[0]}.gif", TenorURL, BasedURLToSave)
                                            if scanResult:
                                                try:
                                                    await message.author.send(f"Tenor URL <{URL}> content flagged NSFW - {scanResultDetails}")
                                                except discord.Forbidden:
                                                    await message.reply(f"{message.author.mention}, Tenor URL <{URL}> content flagged NSFW - {scanResultDetails}")
                                                await message.delete()
                                                logUserAction += f"\nMessage was deleted for having Tenor Gif URL with NSFW content!\n\n"
                                                writingLog(logUserAction)
                                                # Advance scan previous message for profanity!
                                                await AdvanceBackTrackMessageScan(message)
                                                print("Message Content Scan Process Finished!\n\n")
                                                return
                                            else:
                                                print("Tenor Gif Content is clean!")
                                        else:
                                            print(f"Tenor gif URL {URL} is not a valid tenor gif!")
                                            try:
                                                await message.author.send("Your message contains an invalid Tenor URL! Please provide a valid URL!")
                                            except discord.Forbidden:
                                                await message.reply(f"{message.author.mention}, Your message contains an invalid Tenor URL! Please provide a valid URL!")
                                            await message.delete()
                                            logUserAction += f"\nMessage was deleted for having invalid Tenor Gif URL!\n\n"
                                            writingLog(logUserAction)
                                            # Advance scan previous message for profanity!
                                            await AdvanceBackTrackMessageScan(message)
                                            print("Message Content Scan Process Finished!\n\n")
                                            return
                                    else:
                                        """Analyzing if URL content is an image, video, audio, or archive file"""
                                        """Checking URL content already been scanned"""
                                        hashedURLContent = hashlib.sha512(response.content).hexdigest()
                                        print(f"URL content in SHA512: {hashedURLContent}")
                                        print(f"Checking if URL content is already in a clean list...")
                                        if hashedURLContent in CLEANData.keys():
                                            print("URL content already pass the scan!")
                                            print(f"Adding based URL to clean data!")
                                            AddingNewCleanData(BasedURLToSave,f"URL content already passed the check - {CLEANData[hashedURLContent]}")
                                        else:
                                            print(
                                                f"URL content is not in the clean data! Checking if the content is in the NSFW data!")
                                            if hashedURLContent in NSFWData.keys():
                                                print("URL content already flagged NSFW!")
                                                print(f"Adding based URL to NSFW data!")
                                                AddingNewNSFWData(BasedURLToSave,f"URL content already flagged NSFW! - {NSFWData[hashedURLContent]}")
                                                try:
                                                    await message.author.send(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                                except discord.Forbidden:
                                                    await message.reply(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                                await message.delete()
                                                logUserAction += f"\nMessage was deleted for having URL content already flagged NSFW!\n\n"
                                                writingLog(logUserAction)
                                                # Advance scan previous message for profanity!
                                                await AdvanceBackTrackMessageScan(message)
                                                print("Message Content Scan Process Finished!\n\n")
                                                return
                                            else:
                                                URLContentExt = checkingRealFileExtension(URL, os.path.basename(URL.split('?')[0].lower()))
                                                URLContentName = f"{os.path.basename(URL.split('?')[0]).split('.')[0]}{URLContentExt}"
                                                if URLContentExt.endswith(ALLSCANNABLEFILEFORMATS):
                                                    if URLContentExt.endswith(ARCHIVEFORMATS):
                                                        URLContentNSFWResult, UrlContentNSFWResultDetails = not await ArchiveFileScan(URLContentName, URL, BasedURLToSave)
                                                    else:
                                                        URLContentNSFWResult, UrlContentNSFWResultDetails = await ScanningMedia(URLContentName, URL, BasedURLToSave)
                                                else:
                                                    URLContentNSFWResult = False
                                                    UrlContentNSFWResultDetails = ""
                                                    AddingNewCleanData(BasedURLToSave,  "URL link is clean or URL content is not in Emmanuel scannable file formats!")
                                                print("Scan Process Finished!\n\n")
                                                if URLContentNSFWResult:
                                                    try:
                                                        await message.author.send(UrlContentNSFWResultDetails)
                                                    except discord.Forbidden:
                                                        await message.reply(f"{message.author.mention}, {UrlContentNSFWResultDetails}")
                                                    await message.delete()
                                                    logUserAction += f"\nMessage was deleted for having NSFW URL content\n\n"
                                                    writingLog(logUserAction)
                                                    # Advance scan previous message for profanity!
                                                    await AdvanceBackTrackMessageScan(message)
                                                    return
                                else:
                                    print(f"URL is invalid with status code: {response.status_code}")
                                    if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                                        try:
                                            await message.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        except discord.Forbidden:
                                            await message.reply(f"{message.author.mention}, The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        await message.delete()
                                        logUserAction += f"\nMessage is deleted for having a discord attachment URL {URL} can not be scanned!\n\n"
                                        writingLog(logUserAction)
                                        # Advance scan previous message for profanity!
                                        await AdvanceBackTrackMessageScan(message)
                                        print("Message Content Scan Process Finished!\n\n")
                                        return
                                    else:
                                        logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"

                            except Exception as URLQueryError:
                                print(f"Error getting URL: {URLQueryError}.")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/","https://media.discordapp.net/attachments/")):
                                    try:
                                        await message.author.send(
                                            f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                    except discord.Forbidden:
                                        await message.reply(f"{message.author.mention}, The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                    await message.delete()
                                    logUserAction += f"\nMessage is deleted for having a discord attachment URL {URL} can not be scanned!\n\n"
                                    writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(message)
                                    print("Message Content Scan Process Finished!\n\n")
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"

            """Scanning message text content with hyperlink removed"""
            if textContent:
                print(f"Scanning text content with URL already filtered...")
                print(f"Text content: {textContent}")
                scanResult, scanResultDetails = await NSFWscanMessage(textContent)
                if scanResult:
                    try:
                        await message.author.send(scanResultDetails)
                    except discord.Forbidden:
                        await message.reply(f"{message.author.mention}, {scanResultDetails}")
                    await message.delete()
                    logUserAction += "\nMessage was deleted for having NSFW text content!\n\n"
                    writingLog(logUserAction)
                    # Advance scan previous message for profanity!
                    await AdvanceBackTrackMessageScan(message)
                    print("Message Content Scan Process Finished!\n\n")
                    return
                else:
                    print("Message text content is clean!")
            print("Message Text Content Scan Process Finished!\n\n")

        if message.attachments:  # Checking for message attachment content only
            print("Begin Message Attachment Scan!")
            for attachment in message.attachments:
                if "../" in attachment.filename:
                    try:
                        await message.author.send(f"Attachment {attachment.filename} hinted a potential ../ attack!")
                    except discord.Forbidden:
                        await message.reply(f"{message.author.mention}, attachment {attachment.filename} hinted a potential ../ attack!")
                    await message.delete()
                    logUserAction += "\nMessage is deleted for having at least 1 attachment with potential directory transversal attack!!\n\n"
                    writingLog(logUserAction)
                    print(f"Attachment: {attachment.filename} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                    # Advance scan previous message for profanity!
                    await AdvanceBackTrackMessageScan(message)
                    return

                """Checking attachment content already been scanned"""
                response = requests.get(attachment.url, headers=MAINHEADERS)
                hashedAttachmentContent = hashlib.sha512(response.content).hexdigest()
                print(f"Attachment SHA512 content: {hashedAttachmentContent}")
                print(f"Checking if attachment content is already in a clean list...")
                if hashedAttachmentContent in CLEANData.keys():
                    print("Attachment content already pass the scan! Terminating Scan Process...\n\n")
                else:
                    print(f"Attachment content is not in the clean data! Checking if the content is in the NSFW data!")
                    if hashedAttachmentContent in NSFWData.keys():
                        print("Attachment content already flagged NSFW! Terminating Scan Process...\n\n")
                        try:
                            await message.author.send(f"The attachment {attachment.filename} has already flagged NSFW! - {NSFWData[hashedAttachmentContent]}")
                        except discord.Forbidden:
                            await message.reply(f"{message.author.mention}, the attachment {attachment.filename} has already flagged NSFW! - {NSFWData[hashedAttachmentContent]}")
                        await message.delete()
                        logUserAction += "\nMessage was deleted for having attachment content already flagged NSFW!\n\n"
                        writingLog(logUserAction)
                        # Advance scan previous message for profanity!
                        await AdvanceBackTrackMessageScan(message)
                        print("Scan Process Finished!\n\n")
                        return
                    else:
                        print(f"Attachment is not in NSFW data! Proceeding to scan the attachment...")
                        attachmentFileExt = checkingRealFileExtension(attachment.url, attachment.filename.lower())
                        AttachmentFileName = f"{os.path.basename(attachment.url.split('?')[0]).split('.')[0]}{attachmentFileExt}"
                        if attachmentFileExt.endswith(ALLSCANNABLEFILEFORMATS):
                            if attachmentFileExt.endswith(ARCHIVEFORMATS):
                                attachmentNSFWResult, attachmentNSFWResultDetails = not await ArchiveFileScan(AttachmentFileName, attachment.url, hashedAttachmentContent)
                            else:
                                attachmentNSFWResult, attachmentNSFWResultDetails  = await ScanningMedia(AttachmentFileName, attachment.url, hashedAttachmentContent)
                        else:
                            attachmentNSFWResult = False
                            attachmentNSFWResultDetails = ""
                            AddingNewCleanData(hashedAttachmentContent,"Attachment content is not in Emmanuel scannable file formats!")
                        print("Scan Process Finished!\n\n")
                        if attachmentNSFWResult:
                            try:
                                await message.author.send(attachmentNSFWResultDetails)
                            except discord.Forbidden:
                                await message.reply(f"{message.author.mention}, {attachmentNSFWResultDetails}")
                            await message.delete()
                            logUserAction += "\nMessage is deleted for having at least 1 NSFW attachment!\n\n"
                            writingLog(logUserAction)
                            # Advance scan previous message for profanity!
                            await AdvanceBackTrackMessageScan(message)
                            return

        logUserAction += "\nMessage is cleaned!\n\n"
        writingLog(logUserAction)
        await AdvanceBackTrackMessageScan(message)


Emmanuel.run(DISCORDAPI)