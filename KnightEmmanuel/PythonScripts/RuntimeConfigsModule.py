import asyncio, os, re, time, json, rarfile, pathlib, aiohttp, discord
from discord.ext import commands

from dotenv import load_dotenv
from better_profanity import profanity

from openai import AsyncOpenAI
from dataclasses import dataclass
from typing import Literal
from google import genai
from google.genai.types import HttpOptions, HttpRetryOptions


"""Getting Important File Paths"""
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=str(f"{ROOT_DIR}/PythonScripts/.env"))
NSFW_JSON_DB = str(f"{ROOT_DIR}/Files/WordLists/NSFWData.json")
CLEAN_JSON_DB = str(f"{ROOT_DIR}/Files/WordLists/CleanData.json")
PRE_CUSTOMIZED_NSFW_WORDLISTS = str(f"{ROOT_DIR}/Files/WordLists/ProfanityLibWordList.txt")
BLACK_LIST_PORN_DOMAIN = str(f"{ROOT_DIR}/Files/WordLists/BlackListPornDomains.txt")
BLACK_LIST_SUBREDDITS = str(f"{ROOT_DIR}/Files/WordLists/NSFWSubreddits.txt")
EMMANUEL_SCAN_LOG = str(f"{ROOT_DIR}/Files/Log/ScanLogs.md")
EMMANUEL_CONFIG = str(f"{ROOT_DIR}/Files/Configuration/EmmanuelConfig.json")
PENDING_REVIEW_HASHES = str(f"{ROOT_DIR}/Files/Configuration/PendingReviewContentHashes.json")
MAIN_DOWNLOAD_DIR = str(f"{ROOT_DIR}/DownloadDirectory/")
LLM_USAGE_LOG = str(f"{ROOT_DIR}/Files/LLM Usages/")

"""Initializing Important Constants"""
DAILY_UNCENSOR_LIMIT = 1 # Number of time Emmanuel will ignore a user message daily!
WHITE_LIST_MEMBERS = [1336449459634180106, 1318642836870135840, 1311807435627036733, 1312835282852122636, 1288292461310906409, 1334684058919370752, 1330689636309274665, 1361346209360646295]
FILE_DOWNLOAD_COUNTER = 0
OWNER_DISCORD_USER_ID = 987765832895594527 # Put your Discord ID here, if you're the owner of the bot

"""Defining selected OpenAI and Gemini models"""
# https://platform.openai.com/docs/pricing
LLM_MODEL_PROVIDER = "google-gemini" # Select which LLM provider you want to use (Current supported for OpenAI and Gemini)

try:
    assert LLM_MODEL_PROVIDER in ["openai", "google-gemini"]
except AssertionError:
    raise(AssertionError("LLM PROVIDER ERROR: Only openai and google-gemini are supported"))

LLM_MODEL_FOR_AUDIO_TRANSCRIPTION = "gemini-3.5-transcribe"
LLM_MODEL_FOR_IMAGE_SCAN = "gemini-3.8-flash"
LLM_MODEL_FOR_TEXT_SCAN = "gemini-3.8-flash"
LLM_MODEL_FOR_WEB_SEARCH = "gemini-3.8-flash"

# Modify this Dictionary on your own for your choice of LLM model
LLM_MODEL_INFORMATION = {
                        "gpt-6-luna":
                            {
                                "Maximum Input Tokens": 1050000,
                                "Cost": {"Input Token": [0.1, 0.2], "Output Token": [0.5, 0.75], "Cached Read": [0.01, 0.02], "Cached Writes": [0.125, 0.25]},
                                "TPM": 2000000
                            },
                        "gpt-5.6-luna":
                            {
                                "Maximum Input Tokens": 1050000,
                                "Cost": {"Input Token": [0.2, 0.4], "Output Token": [1.2, 1.8], "Cached Read": [0.02, 0.04], "Cached Writes": [0.25, 0.5]},
                                "TPM": 2000000
                            },
                        "gpt-4o-mini":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [0.15, 0.15], "Output Token": [0.6, 0.6], "Cached Read": [0.075, 0.075], "Cached Writes": [0, 0]},
                                "TPM": 2000000
                            },
                        "gemini-3.8-flash":
                            {
                                "Maximum Input Tokens": 1048576,
                                "Cost": {"Input Token": [0.75, 0.75], "Output Token": [3.75, 3.75], "Cached Read": [0.075, 0.075], "Cached Writes": [0.5, 0.5]},
                                "TPM": 2000000
                            },
                        "gemini-3.5-transcribe":
                            {
                                "Maximum Input Tokens": 1048576,
                                "Cost": {"Input Token": [2, 2], "Output Token": [12, 12], "Cached Read": [0, 0], "Cached Writes": [0, 0]},
                                "TPM": 10000
                            }
                       }

try:
    if LLM_MODEL_PROVIDER == "openai":
        assert LLM_MODEL_FOR_IMAGE_SCAN.startswith('gpt')
        assert LLM_MODEL_FOR_AUDIO_TRANSCRIPTION == "gpt-transcribe"
        assert LLM_MODEL_FOR_TEXT_SCAN.startswith('gpt')
        assert LLM_MODEL_FOR_WEB_SEARCH.startswith('gpt')
        LLM_ENGINE = AsyncOpenAI(api_key=os.environ.get("EMMANUEL_OPENAI_API"), timeout=300, max_retries=0)
    elif LLM_MODEL_PROVIDER == "google-gemini":
        assert LLM_MODEL_FOR_IMAGE_SCAN.startswith('gemini')
        assert LLM_MODEL_FOR_AUDIO_TRANSCRIPTION == "gemini-3.5-transcribe"
        assert LLM_MODEL_FOR_TEXT_SCAN.startswith('gemini')
        assert LLM_MODEL_FOR_WEB_SEARCH.startswith('gemini')
        LLM_ENGINE = genai.Client(api_key=os.environ.get("EMMANUEL_GEMENI_API"), http_options=HttpOptions(timeout=300000, api_version='v1beta', retry_options=HttpRetryOptions(attempts=0)))
        assert LLM_MODEL_FOR_AUDIO_TRANSCRIPTION in LLM_MODEL_INFORMATION.keys()
    assert LLM_MODEL_FOR_IMAGE_SCAN in LLM_MODEL_INFORMATION.keys()
    assert LLM_MODEL_FOR_TEXT_SCAN in LLM_MODEL_INFORMATION.keys()
    assert LLM_MODEL_FOR_WEB_SEARCH in LLM_MODEL_INFORMATION.keys()
except AssertionError:
    raise AssertionError("LLM MODEL SELECTION ERROR: Please make sure your selected LLM model matched with their provider AND the model ID exist in LLM_MODEL_INFORMATION!")



CONTENT_SCAN_SEMAPHORE = asyncio.Semaphore(10) # Allow up to 10 concurrent scan at a time
URL_ATTACHMENT_CONTENT_SCAN_SEMAPHORE = asyncio.Semaphore(10)  # Allow up to 10 URL content scan at a time
FILE_HASH_SEMAPHORE = asyncio.Semaphore(8) # Maximum 8 file content hash operation
InFlightFileScans = {}

"""Scan Result dataclass"""
@dataclass
class AttachmentURLScanResult:
    def __init__(self, url: str, fileExt: str, fileSize: int, status: Literal["CLEAN", "NSFW", "MANUAL REVIEW", "UNCENSORED", "SECURITY RISK", "UNVERIFIED"], reason: str, logMessage: str, needManualReviewContent: dict={}):
        self.url = url
        self.fileExt = fileExt
        self.fileSize = fileSize
        self.status = status
        self.reason = reason
        self.logMessage = logMessage
        self.needManualReviewContent = needManualReviewContent


"""----API Tokens----"""
DISCORD_API = os.environ.get("EMMANUEL_DISCORD_API")


"""Set up Rarfile configurations"""
rarfile.UNRAR_TOOL = "unar"


"""Initializing asyncio locks for Thread-Safe File I/O to prevent race conditions"""
ConfigLock = asyncio.Lock()
CleanDataLock = asyncio.Lock()
NSFWDataLock = asyncio.Lock()
LogLock = asyncio.Lock()
PendingReviewLock = asyncio.Lock()
YearlyCSVLock = asyncio.Lock()
MonthlyCSVLock = asyncio.Lock()
CheckServerExistLock = asyncio.Lock()
HashScanLocksGuard = asyncio.Lock()
HashScanLocks = {} # Share an in-flight file scan result by SHA-512; duplicate attachments never create a second disk copy.


with open(EMMANUEL_CONFIG, "r") as configFile:
    configuration = json.load(configFile)
print(f"Configuration file successfully loaded!")

profanity.load_censor_words_from_file(PRE_CUSTOMIZED_NSFW_WORDLISTS)
with open(PRE_CUSTOMIZED_NSFW_WORDLISTS, "r") as profanityFile:
    WordList = [word.strip("\n") for word in profanityFile.readlines()]
print("Profanity Wordlist successfully loaded!")

with open(BLACK_LIST_PORN_DOMAIN, "r") as pornDomainFile:
    BlackListDomains= {domain.strip("\n") for domain in pornDomainFile.readlines()}
print(f"Black List Porn Domains successfully loaded!")

with open(BLACK_LIST_SUBREDDITS, "r") as subredditFile:
    BlackListSubreddits = {subreddit.strip("\n") for subreddit in subredditFile.readlines()}
print("Black List Subreddits successfully loaded!")

with open(NSFW_JSON_DB, "r") as NSFWFile:
    NSFWData = json.load(NSFWFile)
print(f"NSFW Data successfully loaded!")

with open(CLEAN_JSON_DB, "r") as CLEANFile:
    CLEANData = json.load(CLEANFile)
print(f"Clean Data successfully loaded!")

with open(PENDING_REVIEW_HASHES, "r") as file:
    PENDING_MANUAL_REVIEW_CONTENT = json.load(file)
print(f"Pending manual review hash content successfully loaded!")


"""Getting Current Time Value"""
ct = time.ctime(time.time()).split()
previousMonth = ct[1]
previousDate = ct[2]
previousYear = ct[4]
if not os.path.exists(f"{LLM_USAGE_LOG}{previousYear}"):
    os.mkdir(f"{LLM_USAGE_LOG}{previousYear}")
if not os.path.exists(f"{LLM_USAGE_LOG}{previousYear}/{previousMonth}"):
    os.mkdir(f"{LLM_USAGE_LOG}{previousYear}/{previousMonth}")


"""Compiling important regex pattern"""
URLPATTERN = re.compile(r'https?://(?:(?!https?://)\S)+')
WORD = re.compile(r'(\w+)', re.IGNORECASE)
REDDITDOMAINS = re.compile(r'\b(reddit.com|redditinc.com|redd.it|redditmedia.com|redditspace.com)\b', re.IGNORECASE)
SUBREDDITPATTERN = re.compile(r'/?r/+(\w)+')
SUBREDDITPATTERN2 = re.compile(r'r(\w+)')
SANITIZE = re.compile(r'[^a-zA-Z0-9]')


"""Define all file extensions Emmanuel will scan"""

SUPPORTED_PICTURE_FILE_FORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns", ".avif",
                                 ".odd", ".gif", ".heic")

SUPPORTED_VIDEO_FILE_FORMATS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".wmv", ".dv", ".mts",
                                ".m2ts", ".vob", ".ogv")

SUPPORTED_AUDIO_FILE_FORMATS = (".mp3", ".wav", ".oga", ".ogg", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc", ".amr",
                                ".au", ".caf", ".dss", ".m4a", ".m4b", ".wma", ".opus")

SUPPORTED_ARCHIVE_FILE_FORMATS = (".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz", ".rar",
                                  ".bz2", ".xz", ".lzma")

SUPPORTED_DISK_IMAGE_FORMATS = (".dmg", ".iso", ".img", ".vhd", ".nrg", ".vhdx", ".vmdk", ".qcow", ".qcow2", ".udf")

SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS = SUPPORTED_DISK_IMAGE_FORMATS + SUPPORTED_ARCHIVE_FILE_FORMATS

SUPPORTED_ASCII_READABLE_FILE_FORMATS =  (".txt", ".html", ".json", ".yaml", ".xml", ".sh", ".zsh", ".c", ".java", "ASCII document or script files")

ALL_SCANNABLE_FILE_FORMATS = SUPPORTED_PICTURE_FILE_FORMATS + SUPPORTED_VIDEO_FILE_FORMATS + SUPPORTED_AUDIO_FILE_FORMATS + SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS + SUPPORTED_ASCII_READABLE_FILE_FORMATS

"""Initialize aiohttp.ClientSession in setUpHook"""
class EmmanuelBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        print("aiohttp ClientSession initialized.")

    async def close(self):
        await super().close()
        await self.session.close()

intents = discord.Intents.all()
Emmanuel = EmmanuelBot(command_prefix='/', intents=intents)
