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
import random
import asyncio
import aiohttp
import aiofiles
import math
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from PIL import Image
from better_profanity import profanity
from dotenv import load_dotenv
from discord.ext import commands, tasks
from discord import app_commands
from openai import AsyncOpenAI
from nudenet import NudeDetector
from seleniumwire2 import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
from selenium.common import TimeoutException
from typing import Tuple, Literal
from aiocsv import AsyncWriter
from fpdf import FPDF
from urllib.parse import unquote
from zoneinfo import ZoneInfo

load_dotenv()


"""
                    ---Scan Engine Logic---
Message text content check - Using three detection methods (Profanity Lib, Black Lists and OpenAI)
Images, Gif and PDF Frames check - Image converted to PNG format and scan with Nudenet, if nothing detected, convert all to PDF frames and Using OpenAI to scan
Image Text OCR - Using OpenAI OCR scan
Video Frames - Using cv2 to extract all video frames to scan with Nudenet, if nothing detected converting 40 video frames into a PDF file for OpenAI to scan the frames
Audio transcript - Using GPT-40-Transcribe to extract audio script, then Profanity Lib and OpenAI to analyze the transcript
Archive file - Checking for archive bomb then extracting the image, audio, video, pdf compressed content for scan
"""

"""----Nudenet Inappropriate Classes----"""
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

"""Define all file extensions Emmanuel will scan"""
ALLSCANNABLEFILEFORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns",
                           ".avif", ".odd", ".gif",

                           ".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".ogg",
                           ".wmv", ".dv", ".mts", ".m2ts", ".vob",

                           ".mp3", ".wav", ".oga", ".m4a", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc",
                           ".amr", ".au", ".caf", ".m4b", ".wma", ".opus", ".ogv",

                           ".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz",
                           ".rar", ".bz2", ".xz", ".lzma",
                           
                           ".txt", ".html", ".json", ".yaml")


PICTUREFORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns", ".avif",
                  ".odd", ".gif")

VIDEOFORMATS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".ogg", ".wmv", ".dv",
                ".mts", ".m2ts", ".vob", ".ogv")

AUDIOFORMATS = (".mp3", ".wav", ".oga", ".m4a", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc", ".amr",
                ".au", ".caf", ".dss", ".m4a", ".m4b", ".wma", ".opus", ".webm", ".ogg")

ARCHIVEFORMATS = (".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz", ".rar",
                  ".bz2", ".xz", ".lzma")

DOCUMENTFILES =  (".txt", ".html", ".json", ".yaml")

"""Getting Important File Paths"""
NSFWFILEPATH = os.environ.get("EMMANUELNSFWDATA")
CLEANFILEPATH = os.environ.get("EMMANUELCLEANDATA")
EMMANUELLOGFILEPATH = os.environ.get("EMMANUELLOGPATH")
EMMANUELCONFIG = os.environ.get("EMMANUELCONFIGPATH")
MAINDOWNLOADDIR = os.environ.get("EMMANUELDOWNLOADPATH")
LLMUSAGELOGDIR = os.environ.get("EMMANUELLLMUSAGELOGDIR")

"""Initializing Important Constants"""
DAILYUNCENSORLIMIT = 1
WHITELISTMEMBERS = [1336449459634180106, 1318642836870135840, 1311807435627036733, 1312835282852122636, 1288292461310906409, 1334684058919370752, 1330689636309274665, 1361346209360646295]
FILEDOWNLOADCOUNTER = 0
OWNER_DISCORD_USER_ID = 987765832895594527 # Put your Discord ID here, if you're the owner of the bot

"""Defining selected OpenAI models"""
# https://platform.openai.com/docs/pricing
GPTMODELFORIMAGESCAN = "gpt-5-mini"
GPTMODELFORTEXTSCAN = "gpt-4o-mini"
CURRENTSCANOPERATION = {}
LLMModels = [GPTMODELFORTEXTSCAN, GPTMODELFORIMAGESCAN]
LLMMODELINFORMATION = {
                        GPTMODELFORIMAGESCAN:
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [0.25, 0.25], "Output Token": [2.0, 2.0]},
                                "TPM": 500000
                            },
                        GPTMODELFORTEXTSCAN :
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [0.15, 0.15], "Output Token": [0.6, 0.6]},
                                "TPM": 200000
                            }
                       }

SPECIALTEXT = [
    """⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⠟⠁⠈⣷
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣟⡁⢀⣠⣾⠃
⠀⠀⠀⠀⠀⠀⠀⠀⢠⡾⠈⠉⠉⢁⠗⠀
⠀⠀⠀⠀⠀⠀⢀⣴⠟⠀⢀⡀⢀⡾⠀⠀
⣀⣀⣀⣀⡤⠴⠛⠁⠀⣠⠞⢁⠞⠁⠀⠀
⠉⠉⠉⠁⠀⠀⢀⣤⠞⢋⡴⠋⠀⠀⠀⠀
⠀⠠⠔⠒⠢⢤⣀⣤⡖⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢠⡆⣏⡼⠃⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⣫⠜⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠉⠁⠀""",
    """⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⢀⠠⠀⠐⠐⢒⠖⠢⠄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠚⠁⠈⠀⠀⠀⠀⠀⠀⠀⡸⠀⠀⠀⠀⠀⠀⠉⠉⠒⢢⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢐⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠢⣄⣀⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡄⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠈⠁⠀⠄⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠃⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠝⠉⡇⠉⠉⠹⠁⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠀⠀⠀⠀⠀⠀⠀⠀⠃⠀⡼⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠨⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⡀⠀⢀⠤⠔⠀⠀⠀⠀⠀⠀⠀⠀⡆⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠎⠀⢠⠁⢠⠇⠀⠀⠀⠀⠀⡴⠀⠀⢸⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⢠⠃⢀⡇⠀⠀⠀⠀⠀⠀⠱⠄⠀⠁⠘⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠍⠁⠀⠸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢆⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡠⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠱⡀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⡤⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⡄⠀
⠀⠀⠄⠁⠘⠉⠁⠀⠙⠲⢄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⡀
⢠⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⡹⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡏⠀⠀⠀⣸⠁
⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠂⠀⠀⠀⠀⠀⠀⡀⠀⠀⡆⠀⠀⠀⠀⠠⠆⠀⠀⠀⠀⠳⠀⠀⡐⠁⠀
⠀⠑⠆⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢇⠀⢀⠋⢢⡀⠀⠀⠊⠀⠀⠀⠀⠀⢀⡠⠈⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠁⠁⠐⠀⠤⢀⡀⡀⠀⠀⢀⣀⠬⠋⠀⠀⠀⠀⠈⠉⠑⠀⠂⠒⠚⠉⠀⠀⠀⠀⠀⠀""",
    """Ɑ͞ ̶͞ ̶͞ ̶͞ لں͞""",
    """( ͜.人 ͜.)""",
    """（ ͜.人 ͜.）""",
    "𓂸",
    "𓀐"
]

"""----API Tokens----"""
DISCORDAPI = os.environ.get("EMMANUELDISCORDAPI")
TENORAPI = os.environ.get("EMMANUELTENORAPI")
KLIPHYAPI = os.environ.get("EMMANUELKLIPHYAPI")
GPTclient = AsyncOpenAI(api_key=os.environ.get("EMMANUELOPENAIAPI"))
detector = NudeDetector()


"""Set up Rarfile configurations"""
rarfile.UNRAR_TOOL = "unar"


"""Initialize aiohttp.ClientSession in setUpHook"""
class EmmanuelBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        print("aiohttp ClientSession initialized.")

    async def close(self):
        await super().close()
        await self.session.close()


"""Initializing asyncio locks for Thread-Safe File I/O to prevent race conditions"""
ConfigLock = asyncio.Lock()
CleanDataLock = asyncio.Lock()
NSFWDataLock = asyncio.Lock()
LogLock = asyncio.Lock()
YearlyCSVLock = asyncio.Lock()
MonthlyCSVLock = asyncio.Lock()


"""Initializing data container to load essential files and setting up Discord Intents for Emmanuel"""
intents = discord.Intents.all()
Emmanuel = EmmanuelBot(command_prefix='/', intents=intents)

with open(EMMANUELCONFIG, "r") as configFile:
    configuration = json.load(configFile)
print(f"Configuration file successfully loaded!")

profanity.load_censor_words_from_file(os.environ.get("EMMANUELPROFANITYWORDLISTS"))
with open(os.environ.get("EMMANUELPROFANITYWORDLISTS"), "r") as profanityFile:
    WordList = [word.strip("\n") for word in profanityFile.readlines()]
print("Profanity Wordlist successfully loaded!")

with open(os.environ.get("EMMANUELBLACKLISTPORNDOMAINS"), "r") as pornDomainFile:
    BlackListDomains= {domain.strip("\n") for domain in pornDomainFile.readlines()}
print(f"Black List Porn Domains successfully loaded!")

with open(os.environ.get("EMMANUELBLACKLISTSUBREDDITS"), "r") as subredditFile:
    BlackListSubreddits = {subreddit.strip("\n") for subreddit in subredditFile.readlines()}
print("Black List Subreddits successfully loaded!")

with open(NSFWFILEPATH, "r") as NSFWFile:
    NSFWData = json.load(NSFWFile)
print(f"NSFW Data successfully loaded!")

with open(CLEANFILEPATH, "r") as CLEANFile:
    CLEANData = json.load(CLEANFile)
print(f"Clean Data successfully loaded!")

"""Retrieving 100 ScrapeOps Mobile Browser Headers"""
ScrapeOPSResponse = requests.get(
  url='https://headers.scrapeops.io/v1/browser-headers',
  params={
      'api_key': os.environ.get("EMMANUELSCRAPEOPSAPI"),
      'num_results': '100',
      'mobile': 'true'}
)
SCRAPEOPSMOBILEBROWSERHEADERS = ScrapeOPSResponse.json().get('result',  [])
assert len(SCRAPEOPSMOBILEBROWSERHEADERS) == 100
print(f"Successfully retrieving 100 ScrapeOps Mobile Browser Headers!")


"""Getting Current Time Value"""
ct = time.ctime(time.time()).split()
previousMonth = ct[1]
previousDate = ct[2]
previousYear = ct[4]
if not os.path.exists(f"{LLMUSAGELOGDIR}{previousYear}"):
    os.mkdir(f"{LLMUSAGELOGDIR}{previousYear}")
if not os.path.exists(f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}"):
    os.mkdir(f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}")


"""Setting Path to Chrome Driver Binary"""
# service = Service("/usr/bin/chromedriver")


"""Compiling important regex pattern"""
URLPATTERN = re.compile(r'https?://(?:(?!https?://)\S)+')
WORD = re.compile(r'(\w+)', re.IGNORECASE)
REDDITDOMAINS = re.compile(r'\b(reddit.com|redditinc.com|redd.it|redditmedia.com|redditspace.com)\b', re.IGNORECASE)
SUBREDDITPATTERN = re.compile(r'/?r/+(\w)+')
SUBREDDITPATTERN2 = re.compile(r'r(\w+)')
SANITIZE = re.compile(r'[^a-zA-Z0-9]')

def plotBarCharts(datasets: list[dict], xLabels: list[str], suptitle: str, savePath: str) -> None:
    """
    Description: Plotting three bar charts representing Total Input Tokens, Total Output Tokens and Total Costs
    :param datasets: The list of all y values for each bar chart
    :param xLabels: The x label for each bar chart
    :param suptitle: The Main Title for all the bar charts
    :param savePath: The path to save the bar charts
    :return: None, the bar charts will be saved in the savePath
    """
    x = np.arange(len(xLabels))
    barWidth = 0.55
    fig, axes = plt.subplots(3, 1, figsize=(13, 13))
    fig.patch.set_facecolor("#F7F8FA")
    fig.suptitle(suptitle, fontsize=17, fontweight="bold", color="#1E2A3A", y=0.98)
    for ax, ds in zip(axes, datasets):
        values = ds["values"]
        color = ds["color"]
        max_v = max(values) if any(v > 0 for v in values) else 1
        bars = ax.bar(x, values, width=barWidth, color=color, alpha=0.88, edgecolor="white", linewidth=0.8, zorder=3)
        ax.set_facecolor("#F7F8FA")
        ax.set_title(ds["title"], fontsize=13, fontweight="bold", color="#1E2A3A", pad=8, loc="left")
        ax.set_xticks(x)
        ax.set_xticklabels(xLabels, fontsize=10, color="#444")
        ax.tick_params(axis="y", labelsize=9, colors="#666")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#DDD")
        ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_v * 0.015, f"{val:,}", ha="center", va="bottom", fontsize=7.5, color="#333", fontweight="500")
        for i, val in enumerate(values):
            if val == 0:
                ax.axvspan(i - barWidth / 2, i + barWidth / 2, color="#E8E8E8", alpha=0.5, zorder=1)
    plt.savefig(savePath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plotModelCalls(LLMModelUses: list[int], savePath: str):
    """
    Description: Plotting a single bar chart showing the total calls per LLM models each month
    :param LLMModelUses: The usage value of each LLM models
    :param savePath: The path to save the bar chart
    :return: None, the bar chart will be saved in the savePath
    """

    x = np.arange(len(LLMModels))
    max_val = max(LLMModelUses) if any(LLMModelUses) else 2

    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor("#F7F8FA")

    bars = ax.bar(LLMModels, LLMModelUses, width=0.55, color="Purple", alpha=0.88, edgecolor="white", linewidth=0.8, zorder=3)
    ax.set_facecolor("#F7F8FA")
    ax.set_title("LLM Model Calls", fontsize=13, fontweight="bold", color="#1E2A3A", pad=8, loc="left")
    ax.set_xticks(x)
    ax.set_xticklabels(LLMModels, fontsize=10, color="#444", rotation=40, ha="right")
    ax.tick_params(axis="y", labelsize=9, colors="#666")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#DDD")
    ax.yaxis.grid(True, color="#E0E0E0", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    for bar, val in zip(bars, LLMModelUses):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_val * 0.015,f"{val:,}", ha="center", va="bottom", fontsize=7.5, color="#333", fontweight="500")

    for i, val in enumerate(LLMModelUses):
        if val == 0:
            ax.axvspan(i - 0.55 / 2, i + 0.55 / 2, color="#E8E8E8", alpha=0.5, zorder=1)
    ax.set_ylim(0, max_val * 1.35)
    plt.savefig(savePath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


async def writingLLMUsageCsv(csvPath: str, mode: Literal['w', 'a'], data: list, ObjectLock: asyncio.locks.Lock) -> None:
    """
    Description: Executing read and write only operation on the csv files related to logging Samson LLM Usage
    :param csvPath: The path to the csv file
    :param mode: Must be 'w' or 'a'
    :param data: The data to write
    :param ObjectLock: Object lock on write operation to prevent race condition
    :return: None
    """
    async with ObjectLock:
        async with aiofiles.open(csvPath, mode) as f:
            csvWriter = AsyncWriter(f)
            await csvWriter.writerow(data)


def calculateUsageCost(model: str, totalInputTokens: int, totalOutputTokens: int) -> float:
   """
   Description: Calculate the usage cost of the LLM model based on the total input tokens and output tokens.
   :param model: LLM Model
   :param totalInputTokens: The total input tokens of a prompt
   :param totalOutputTokens: The total output tokens of a prompt
   :return: The final calculated usage cost
   """
   totalCost = (totalInputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Input Token"][0] + (totalOutputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Output Token"][0]
   return round(totalCost, 5)


def SeleniumHTMLRetrieval(browserHeader: dict, url: str) -> Tuple[int, bytes]:
    """
    Description: Opening Headless Selenium browser to fetch url response content with customized browser header
    :param browserHeader: Customized browser header
    :param url: URL to retrieve the response content in bytes
    :return: Status code of the request and the response bytes content
    """
    print("Opening Selenium Webdriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')  # Enable the spider to run web scrape in real life browser.
    chrome_options.add_argument('--disable-dev-shm-usage')  # Disable shared memory feature that could cause the Selenium Chromium session to crash.
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # IMPORTANT: Remove the navigator.webdriver flag that websites use to detect Selenium. Selenium default set this to true.
    chrome_options.add_experimental_option("excludeSwitches",["enable-automation"])  # IMPORTANT: Removes the "Chrome is being controlled by automated test software" banner and prevent Chrome form adding automation-related command -line switches.
    chrome_options.add_experimental_option('useAutomationExtension',False)  # IMPORTANT: Disables Chrome's automation extension that Selenium normally loads. This limit the bot detection surface.
    userAgent = browserHeader.get('user-agent')
    if userAgent:
        chrome_options.add_argument(f'user-agent={userAgent}')
        print(f"Using ScrapeOps fake user agent: {userAgent}")
    # browser = webdriver.Chrome(options=chrome_options, service=service)
    browser = webdriver.Chrome(options=chrome_options)
    if browserHeader and hasattr(browser, 'execute_cdp_cmd'):
        headers_to_set = {}
        for key, value in browserHeader.items():
            if key not in ['user-agent']:
                headers_to_set[key] = value

        if headers_to_set:
            browser.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': headers_to_set})
            print(f"Set {len(headers_to_set)} additional headers via CDP")
            print(f"Using ScrapeOps browser header: {browserHeader}")
    print(f"Making request to URL: {url}")
    browser.set_page_load_timeout(10)
    try:
        browser.get(url)
    except TimeoutException:
        print(f"Page load timed out at 10s for {url}, attempting to proceed...")
    EncodedResponseBody = browser.page_source.encode('utf-8')
    currentUrl = browser.current_url
    statusCode = 200
    for request in reversed(browser.requests):
        if request.response:
            if request.url == currentUrl or (request.url.rstrip('/') == currentUrl.rstrip('/')):
                statusCode = request.response.status_code
                print(f"Final page status for {currentUrl}: {statusCode}")
                break
    print("Closing and Quitting Selenium Webdriver...")
    browser.close()
    browser.quit()
    return statusCode, EncodedResponseBody


def checkingRealFileExtension(BytesContent: bytes, filename: str) -> str:
    """
    Description: Checking file extension based on the file content with Python Magic and filetype modules
    :param BytesContent: The bytes content of the file
    :param filename: The name of the file
    :return: The result file extension from the analyzation process
    """
    print("Checking file extension with Python-Magic module...")
    mime = magic.from_buffer(BytesContent, mime=True)
    fileExt = mimetypes.guess_extension(mime)
    if fileExt:
        if fileExt == ".bin":
            if BytesContent.startswith(b'PK'):
                print(f"Detected file extension .zip")
                return '.zip'
            elif BytesContent.startswith(b'caff'):
                print(f"Detected file extension .caf")
                return '.caf'
        if fileExt == ".webm" and filename.endswith(".weba"):
            print(f"Detected file extension .weba")
            return ".weba"
        elif fileExt == ".webm" and filename.endswith(".wmv"):
            print(f"Detected file extension .wmv")
            return ".wmv"
        elif fileExt == ".wmv" and filename.endswith(".wma"):
            print(f"Detected file extension .wma")
            return ".wma"
        elif fileExt == ".ogv" and filename.endswith(".ogg"):
            print(f"Detected file extension .ogg")
            return ".ogg"
        elif fileExt == ".asf" and filename.endswith(".wmv"):
            print(f"Detected file extension .wmv")
            return ".wmv"
        elif fileExt == ".asf" and filename.endswith(".wma"):
            print(f"Detected file extension .wma")
            return ".wma"
        if fileExt.endswith((".xz", ".bz2", ".gz")) and filename.endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz")):
            fileExt = f".{'.'.join(filename.split(".")[1:])}"
            print(f"Detected extension {fileExt}")
        else:
            print(f"Python-Magic detected file extension {fileExt}")
        return fileExt
    else:
        print("Python-Magic did not detect")
        try:
            if BytesContent.decode("ascii").isascii():
                print(f"Detected file extension as ascii/text file")
                return ".txt"
        except UnicodeDecodeError:
            print("Checking file extension with filetype module...")
            fileExt = filetype.guess(BytesContent)
            if fileExt:
                print(f"Filetype detected file extension {fileExt.extension}")
                return f".{fileExt.extension}"
            else:
                if BytesContent.startswith((b'\x0B\x77', b'\x0bwu\xacT@C')):
                    print(f"Detected file extension .ac3")
                    return ".ac3"
                elif filename.endswith(".lzma"):
                    print(f"Detected file extension .lzma")
                    return ".lzma"
    print(f"File extension can not be determined!")
    return "Can't be determined"

async def writingLog(logData: str) -> None:
    """
    Description: Writing scanning log Emmanuel log file
    :param logData: Log content to be written
    :return: None
    """
    async with LogLock:
        async with aiofiles.open(EMMANUELLOGFILEPATH, "a") as txtFile:
            await txtFile.write(f"{time.ctime(time.time())}\n")
            await txtFile.write(logData)


async def AddingNewCleanData(Hash: str, Reason: str) -> None:
    """
    Description: Adding new SHA512 hash to Emmanuel clean data JSON file and the reason
    :param Hash: SHA512 hash to be added
    :param Reason: Reason why the hash was added to the clean content
    :return: None
    """
    async with CleanDataLock:
        CLEANData[Hash] = Reason
        print("Content passed the check, Adding to clean data...")
        async with aiofiles.open(CLEANFILEPATH, "w") as JSONFile:
            await JSONFile.write(json.dumps(CLEANData, indent=4))
        print(f"Clean data updated!")


async def AddingNewNSFWData(Hash, Reason):
    """
    Description: Adding new SHA512 hash to Emmanuel NSFW data JSON file and the reason
    :param Hash: SHA512 hash to be added
    :param Reason: Reason why the hash was added to the NSFW content
    :return: None
    """
    async with NSFWDataLock:
        NSFWData[Hash] = Reason
        print("Content was flagged NSFW, adding to NSFW data...")
        async with aiofiles.open(NSFWFILEPATH, "w") as JSONFile:
            await JSONFile.write(json.dumps(NSFWData, indent=4))
        print(f"NSFW data updated!")


async def checkServerExistInConfigFile(serverID: str) -> None:
    """
    Description: Check if a server ID already exists in configuration file
    :param serverID: The server ID to be checked
    :return: Nothing is returned. If the server ID does not exist in the configuration file, then it will be automatically created with all the default values.
    """
    async with ConfigLock:
        if configuration.get(serverID) is None:
            configuration[serverID] = {}
            configuration[serverID]["Uncensored-members"] = WHITELISTMEMBERS
            configuration[serverID]["Uncensored-channels"] = []
            members = {}
            server = await Emmanuel.fetch_guild(int(serverID))
            async for member in server.fetch_members(limit=None):
                if member.id not in WHITELISTMEMBERS:
                    members[str(member.id)] = DAILYUNCENSORLIMIT
            configuration[serverID]["User-Uncensor-Limit"] = members
            async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                await file.write(json.dumps(configuration, indent=4))
            await writingLog(f"New server ID {serverID} added to config file!\n\n")
            print(f"New server ID {serverID} added to config file!")


async def getHashValueofAttachmentFileData(filepath: str) -> str:
    """
    Description: Get SHA512 hash of the file bytes content
    :param filepath: Path to the file on disk
    :return: SHA512 hash of the file bytes content
    """
    async with aiofiles.open(filepath, "rb") as file:
        return hashlib.sha512(await file.read()).hexdigest()


async def scanningImageWithNudenet(image: str) -> bool:
    """
    Description: Scanning image with Nudenet pre-train NSFW model
    :param image: Path to the image on disk
    :return: Scan result of whether the image is NSFW or not
    """
    detections = await asyncio.to_thread(detector.detect, image)
    print(f"Nudenet scan results: {detections}")
    for result in detections:
        if result['class'] in SEXUALTAGS:
            if result['score'] > 0.53:
                return True
    return False


async def scanningPDFPagesWithGPT(PDFimagePath: str) -> str:
    """
    Description: Scanning PDF frames with GPT pre-train model
    :param PDFimagePath: Path to the PDF on disk
    :return: GPT scan result
    """
    print(f"Start scanning PDF frames with GPT {GPTMODELFORIMAGESCAN}")
    with open(PDFimagePath, "rb") as PDFfile:
        fileResponse = await GPTclient.files.create(file=PDFfile, purpose="user_data")
        fileID = fileResponse.id
    prompt = ("# ASK\n"
              "Is the following PDF pages have any nude elements, vulgar language, hateful slur, sexual theme, the exposure of animal genitalia,"
              " animal porn, reference to adult or NSFW websites, or even consider NSFW?\n"
              "# IMPORTANT RULE\n"
              "Please taking into account that people in light clothing like thongs and bikini SHOULD BE consider NSFW!\n"
              "# RESPONSE FORMAT\n"
              "Response MUST start with a Yes or No then follow by a COMMA and EXPLAIN the reason NO MORE THAN 30 WORDS!"
              )
    inputPromptTokenCount = (await GPTclient.responses.input_tokens.count(model=GPTMODELFORIMAGESCAN, instructions="You are an NSFW content moderator", input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_file", "file_id": fileID}]}])).input_tokens
    print(f"Input Tokens: {inputPromptTokenCount}")
    if inputPromptTokenCount > LLMMODELINFORMATION[GPTMODELFORIMAGESCAN]["Maximum Input Tokens"] or inputPromptTokenCount > LLMMODELINFORMATION[GPTMODELFORIMAGESCAN]["TPM"]:
        await GPTclient.files.delete(fileID)
        return "MAXIMUM TOKEN LIMIT"
    else:
        response = await GPTclient.responses.create(
            model=GPTMODELFORIMAGESCAN,
            instructions="You are an NSFW content moderator",
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

        await GPTclient.files.delete(fileID)
        os.remove(PDFimagePath)

        print(f"GPT image NSFW scan results: {response.output_text}")
        outputPromptTokenCount = response.usage.total_tokens - inputPromptTokenCount
        cMonth = time.ctime(time.time()).split()[1]
        cDay = time.ctime(time.time()).split()[2]
        totalCost = calculateUsageCost(GPTMODELFORIMAGESCAN, inputPromptTokenCount, outputPromptTokenCount)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a",[f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORIMAGESCAN, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a",[f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORIMAGESCAN, totalCost], YearlyCSVLock)
        return response.output_text


async def scanningTextOnlyWithGPT(textToBeScanned: str) -> str:
    """
    Description: Scanning text content with GPT pre-train model
    :param textToBeScanned: The text content to be scanned
    :return: GPT scan result
    """
    inputPromptTokenCount = (await GPTclient.responses.input_tokens.count(model=GPTMODELFORTEXTSCAN, instructions="You are an NSFW moderator on text messages that may also contains URL", input=textToBeScanned)).input_tokens
    if inputPromptTokenCount > LLMMODELINFORMATION[GPTMODELFORTEXTSCAN]["Maximum Input Tokens"] or inputPromptTokenCount > LLMMODELINFORMATION[GPTMODELFORTEXTSCAN]["TPM"]:
        print("MAXIMUM TOKEN LIMIT")
        return "MAXIMUM TOKEN LIMIT"
    else:
        response = await GPTclient.responses.create(
            model=GPTMODELFORTEXTSCAN,
            instructions="You are an NSFW moderator on text messages that may also contains URL",
            input=textToBeScanned
        )
        outputPromptTokenCount = response.usage.total_tokens - inputPromptTokenCount
        cMonth = time.ctime(time.time()).split()[1]
        cDay = time.ctime(time.time()).split()[2]
        totalCost = calculateUsageCost(GPTMODELFORTEXTSCAN, inputPromptTokenCount, outputPromptTokenCount)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a",[f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORTEXTSCAN, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a",[f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORTEXTSCAN, totalCost],YearlyCSVLock)
        return response.output_text

async def scanWebContentUsingWebSearchWithGPT(url: str) -> str:
    """
    Description: Scanning web content with web search tool
    :param url: The URL to be scanned
    :return: The scan result
    """
    # https://developers.openai.com/api/docs/pricing#built-in-tools

    response = await GPTclient.responses.create(model=GPTMODELFORIMAGESCAN,
                                                tools=[{"type": "web_search",}],
                                                instructions="You are a web content moderator",
                                                input=f"# ACTION\n"
                                                      f"Perform a search on a website url and determine if the website contains NSFW content\n "
                                                      f"# URL\n"
                                                      f"{url}\n"
                                                      f"# RESPONSE FORMAT\n"
                                                      f"1. If the website can not be access, just reply CAN NOT ACCESS WEBSITE.\n"
                                                      f"2. If the website is detected with NSFW content, ALWAYS START your reply with a Yes, then EXPLAIN the reason NO MORE THAN  30 WORDS!\n"
                                                      f"3. If the website does not have any NSFW content, just reply No."
                                                )
    inputPromptTokenCount = response.usage.input_tokens
    outputPromptTokenCount = response.usage.output_tokens
    cMonth = time.ctime(time.time()).split()[1]
    cDay = time.ctime(time.time()).split()[2]
    totalCost = calculateUsageCost(GPTMODELFORIMAGESCAN, inputPromptTokenCount, outputPromptTokenCount) + 0.01 # Web Search cost $10/1K request
    await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a", [f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORTEXTSCAN, totalCost], MonthlyCSVLock)
    await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a",[f"{cMonth} {cDay}", inputPromptTokenCount, outputPromptTokenCount, GPTMODELFORTEXTSCAN, totalCost], YearlyCSVLock)
    return response.output_text


async def isTenorURLValid(gifURL: str) -> str:
    """
    Description: Tenor URL validation
    :param gifURL: Tenor URL
    :return: The correct tenor URL or Invalid if URL is not a tenor URL
    """
    try:
        gifID = gifURL.split('/')[4].split('-')[len(gifURL.split('/')[4].split('-')) - 1]
        gifURL = f"https://tenor.googleapis.com/v2/posts?ids={gifID}&key={TENORAPI}"
        async with Emmanuel.session.get(gifURL) as response:
            if response.status == 200:
                data = await response.json()
                if data["results"]:
                    gifUrl = data["results"][0]["media_formats"]["gif"]["url"]
                    return gifUrl
            return "Invalid"
    except Exception as error:
        print(f"Tenor URL error: {error}")
        return "Invalid"


async def isKlipyURLValid(gifURL: str) -> str:
    """
    Description: Klipy URL validation
    :param gifURL: Klipy URL
    :return: The correct Klipy URL or Invalid if URL is not a Klipy URL
    """
    try:
        gifSlug = os.path.basename(gifURL)
        gifURL = f"https://api.klipy.com/api/v1/{KLIPHYAPI}/gifs/items?slugs={gifSlug}"
        async with Emmanuel.session.get(gifURL) as response:
            if response.status == 200:
                data = await response.json()
                if data["result"]:
                    gifURL = data["data"]["data"][0]["file"]["hd"]["gif"]["url"]
                    return gifURL
            return "Invalid"
    except Exception as error:
        print(f"Klipy URL error: {error}")
        return "Invalid"


def PDFConversion(filePath: str) -> str:
    """
    Description: Convert a file to PDF
    :param filePath: Path of the file on disk to be converted
    :return: The output PDF path of the converted file
    """
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


def AsciiDocumentToPDFConversion(fileData: bytes) -> str:
    """
    Description: Convert a text based file (HTML, .py, .txt, .etc.) to PDF
    :param fileData: The ascii data bytes of the file in memory
    :return: The output PDF path of the converted file
    """
    print(f"Converting ASCII-based file to PDF...")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdfpath = f"{MAINDOWNLOADDIR}{FILEDOWNLOADCOUNTER}.pdf"
    pdf.multi_cell(0, 10, fileData.decode('utf-8', errors="replace").encode("latin-1", errors="replace").decode("latin-1"))
    pdf.output(pdfpath)
    print(f"Conversion successes!")
    return pdfpath


# Return True if NSFW
async def ScanningMedia(mediaName: str, bytesContent: bytes, hashedMediaContent: str, alreadyOnDisk:bool=False) -> Tuple[bool, str]:
    """
    Description: Scanning Media Files (Image, PDF, Video, and Audio)
    :param mediaName: The name of the media file
    :param bytesContent: The bytes content of the media file
    :param hashedMediaContent: The SHA512 hash of the media file content
    :param alreadyOnDisk Specify whether the file is already exist on disk or not
    :return: NSFW Scan result as a boolean and Reasoning of the scan a str
    """

    if not alreadyOnDisk :
        mediaPath = f"{MAINDOWNLOADDIR}{mediaName}"
        async with aiofiles.open(mediaPath, "wb") as mediaFile:
            await mediaFile.write(bytesContent)
            print("Media content downloaded!")
    else:
        mediaPath = mediaName

    if mediaName.endswith(PICTUREFORMATS):
        print(f"Media content is an image file in format .{mediaName.split('.')[1]}!")
        if not mediaPath.endswith((".png", ".pdf", ".gif")):
            print(f"Converting the image format to PNG...")
            outPutPNGPath = f"{os.path.dirname(mediaPath)}/{os.path.basename(mediaPath).split('.')[0]}.png"
            try:
                await asyncio.to_thread(subprocess.run, ["ffmpeg", "-i", mediaPath, outPutPNGPath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as PNGConversionError:
                await AddingNewNSFWData(hashedMediaContent, "File Conversion Failure - Image Format can't be converted to PNG!")
                os.remove(mediaPath)
                print(f"Error: {PNGConversionError}\nError Converting the image format to PNG! Terminating Scan Process!")
                return True, "File Conversion Failure - Image Format can't be converted to PNG for scan, therefore the content is deleted!"
            mediaPath = outPutPNGPath
        else:
            print(f"Image already in PNG or PDF or GIF format!")
        if mediaPath.endswith(".png"):
            print("Scanning PNG image with nudenet...")
            if await scanningImageWithNudenet(mediaPath):  # First check using nudenet
                print(f"Nudenet detected NSFW image!")
                await AddingNewNSFWData(hashedMediaContent, "NSFW Image - Pre-trained NSFW model Nudenet detected NSFW element in the image!")
                os.remove(mediaPath)
                return True, "NSFW Image - Pre-trained NSFW model Nudenet detected NSFW element in the image!"
    elif mediaName.endswith(VIDEOFORMATS):
        print(f"Media content is a video file in format .{mediaName.split('.')[1]}!")
        print(f"Checking audio content from the video {mediaName}...")
        scanResult, scanResultDetails = await NSFWScanAudio(mediaPath, False)
        if scanResult:
            print("Video has NSFW audio content!")
            await AddingNewNSFWData(hashedMediaContent, f"NSFW Video - Video has NSFW audio content: {scanResultDetails}")
            os.remove(mediaPath)
            return True, f"NSFW Video - Video has NSFW audio content: {scanResultDetails}"
        print("Scanning video frame with Nudenet!")
        cap = cv2.VideoCapture(mediaPath)
        frameNum = 0
        totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = math.ceil(totalFrames / 40) # Ensure only 40 frames total is scanned!!!
        print(f"Video has total {totalFrames} frames!")
        while frameNum < totalFrames:
            success, frame = cap.read()
            frameNum += 1

            if success and (frameNum % fps == 0):
                framePath = f"{MAINDOWNLOADDIR}{os.path.basename(mediaPath).split('.')[0]}frame_{frameNum}.png"
                await asyncio.to_thread(cv2.imwrite, framePath, frame)
                HashedFramePath = await getHashValueofAttachmentFileData(framePath)
                if HashedFramePath in CLEANData.keys():
                    print(f"Frame path {framePath} already in clean data!")
                    os.remove(framePath)
                else:
                    if HashedFramePath in NSFWData.keys():
                        print(f"Frame path {framePath} is in NSFW data!")
                        os.remove(framePath)
                        os.remove(mediaPath)
                        cap.release()
                        await AddingNewNSFWData(hashedMediaContent, "NSFW Video - One of the video frame already flagged NSFW by Pre-Trained NSFW model Nudenet!")
                        return True, "NSFW Video - One of the video frame already flagged NSFW by Pre-Trained NSFW model Nudenet!"
                    if await scanningImageWithNudenet(framePath):
                        print(f"Nudenet detected NSFW content at video Frame {frameNum}!")
                        await AddingNewNSFWData(HashedFramePath, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!")
                        os.remove(framePath)
                        os.remove(mediaPath)
                        cap.release()
                        await AddingNewNSFWData(hashedMediaContent, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!")
                        return True, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in a video frame!"
                    await AddingNewCleanData(HashedFramePath, "Nudenet detect video frame as cleaned!")
                    os.remove(framePath)
            await asyncio.sleep(0)
        cap.release()
    elif mediaName.endswith(AUDIOFORMATS):
        print(f"Media content is an audio file in format .{mediaName.split('.')[1]}!")
        scanResult, scanResultDetails = await NSFWScanAudio(mediaPath)
        if scanResult:
            print("Audio is not clean!")
            await AddingNewNSFWData(hashedMediaContent, scanResultDetails)
            return True, scanResultDetails
        else:
            print("Audio is clean!")
            await AddingNewCleanData(hashedMediaContent, scanResultDetails)
            return False, ""
    if not mediaPath.endswith(".pdf"):
        pdfPath = await asyncio.to_thread(PDFConversion, mediaPath)
    else:
        pdfPath = mediaPath
    if pdfPath == "Conversion failed":
        os.remove(mediaPath)
        print("Error converting media content to PDF frames!")
        return False, ""
    mediaScanResult = await scanningPDFPagesWithGPT(pdfPath)
    if mediaScanResult.startswith(("Yes", "yes", "YES")):
        mediaScanResult =  mediaScanResult.strip("Yes, ")
        if mediaName.endswith(PICTUREFORMATS):
            mediaScanResult = f"NSFW Image - {mediaScanResult}"
        elif mediaName.endswith(VIDEOFORMATS):
            mediaScanResult = f"NSFW Video - {mediaScanResult}"
        print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
        await AddingNewNSFWData(hashedMediaContent, mediaScanResult)
        return True, mediaScanResult
    else:
        mediaScanResult = mediaScanResult.strip("No, ")
        if mediaName.endswith(PICTUREFORMATS):
            mediaScanResult = f"Clean Image - {mediaScanResult}"
        elif mediaName.endswith(VIDEOFORMATS):
            mediaScanResult = f"Clean Video - {mediaScanResult}"
        print(f"Content is clean!")
        await AddingNewCleanData(hashedMediaContent, mediaScanResult)
        return False, mediaScanResult


def ArchivesBombAnalysisAndExtraction(filePath: list, archiveLayer: int=0) -> bool:
    """
    Description: Checking if an archive file is safe to extract. If yes, then all content that in Emmanuel scope of scan will be extracted to MAINDOWNLOADDIR
    :param filePath: A list of the path to the archive file on disk
    :param archiveLayer: The layer of the archive file
    :return: True if the archive is not safe to extract, False otherwise
    """

    def checkingFileExtension(fileContent: bytes, fname: str, verbose: bool = True):
        mime = magic.from_buffer(fileContent, mime=True)
        Ext = mimetypes.guess_extension(mime)
        if Ext:
            if Ext == ".bin":
                if fileContent.startswith(b'PK'):
                    if verbose:
                        print(f"Detected file extension .zip")
                    return '.zip'
                else:
                    if verbose:
                        print(f"Python-Magic detect file extension .bin")
                    return ".bin"
            if Ext == ".webm" and fname.endswith(".weba"):
                if verbose:
                    print(f"Detected file extension .weba")
                return ".weba"
            elif Ext == ".webm" and fname.endswith(".wmv"):
                if verbose:
                    print(f"Detected file extension .wmv")
                return ".wmv"
            elif Ext == ".wmv" and fname.endswith(".wma"):
                if verbose:
                    print(f"Detected file extension .wma")
                return ".wma"
            elif Ext == ".ogv" and fname.endswith(".ogg"):
                if verbose:
                    print(f"Detected file extension .ogg")
                return ".ogg"
            elif Ext == ".asf" and fname.endswith(".wmv"):
                if verbose:
                    print(f"Detected file extension .wmv")
                return ".wmv"
            elif Ext == ".asf" and fname.endswith(".wma"):
                if verbose:
                    print(f"Detected file extension .wma")
                return ".wma"
            if Ext.endswith((".xz", ".bz2", ".gz")) and fname.endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz")):
                Ext = f".{'.'.join(fname.split(".")[1:])}"
                if verbose:
                    print(f"Detected extension {Ext}")
            else:
                if verbose:
                    print(f"Python-Magic detect file extension {Ext}")
            return Ext
        else:
            if verbose:
                print(f"Python-Magic did not detect")
            try:
                if fileContent.decode("ascii").isascii():
                    if verbose:
                        print(f"ASCII file detected")
                    return ".txt"
            except UnicodeDecodeError:
                if verbose:
                    print(f"Starting filetype module...")
                Ext = filetype.guess(fileContent)
                if Ext:
                    if verbose:
                        print(f"Filetype detected file extension {Ext.extension}")
                    return f".{Ext.extension}"
                elif fileContent.startswith((b'\x0B\x77', b'\x0bwu\xacT@C')):
                    if verbose:
                        print(f"Detected file extension .ac3")
                    return ".ac3"
                elif fname.endswith(".lzma"):
                    if verbose:
                        print(f"Detected file extension .lzma")
                    return ".lzma"
        if verbose:
            print(f"File extension can not be determined!")
        return "Can't be determined"

    NESTEDARCHIVESIZELIMIT = 1000000000
    UNCOMPRESSEDSIZELIMIT = 32000000000
    CHUNKSIZE = 5000000000  # Read file to RAM content every 5 GB
    DUPLICATEDARCHIVELIMIT = 3
    TempDir = f"{MAINDOWNLOADDIR}{os.path.basename(filePath[0]).split('.')[0]}/"
    os.mkdir(TempDir)
    with open(filePath[0], 'rb') as rootFile:
        DuplicatedFileDetection = [hashlib.sha256(rootFile.read()).hexdigest()]
    uncompressedSize = os.path.getsize(filePath[0])
    totalDuplicatedFile = 0
    totalDuplicatedArchive = 0
    totalFileCount = 0
    while len(filePath) != 0:
        if archiveLayer == 7:
            print(f"The root archive file has 7 or more nested layers, hinted potential archive bomb!")
            return True
        for i in range(len(filePath)):
            if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                print(f"The total uncompressed size has reached the limit threshold!")
                return True
            with open(filePath[i], "rb") as ArchiveSource:
                ArchiveContent = ArchiveSource.read()
            print(f"Checking Archive file: {os.path.basename(filePath[i])} at path {filePath[i]}...")
            fileExt = checkingFileExtension(ArchiveContent, os.path.basename(filePath[i]))
            if fileExt.endswith(".zip"):
                print("Archive is a zip file!")
                with zipfile.ZipFile(filePath[i], 'r') as zipRef:
                    print(f"Creating subdirectories...")
                    """First Extraction Focusing On Checking Extraction Path and Directory Structure"""
                    for entry in zipRef.infolist():
                        totalFileCount += 1
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.filename}")
                        if not DestinationPath.startswith(TempDir):
                            print(f"The uncompressed file name {entry.filename} formed an illegal path {DestinationPath} to cause directory transversal attack!")
                            return True
                        if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.filename:
                            if entry.filename.endswith('/'):
                                os.makedirs(DestinationPath, exist_ok=True)
                                print(f"Directory {entry.filename} created at path {DestinationPath}")
                        if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                            return True

                    print(f"Extracting compressed file contents...")
                    """Second Extraction Focusing On Extracting All the Compressed Files"""
                    for entry in zipRef.infolist():
                        if entry.filename.endswith('/'):
                            continue
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.filename}")
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
                            if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.filename:
                                if checkingFileExtension(fileData, DestinationPath).endswith(ALLSCANNABLEFILEFORMATS):
                                    hashedData = hashlib.sha256(fileData).hexdigest()
                                    if hashedData not in DuplicatedFileDetection:
                                        with open(DestinationPath, 'wb') as f:
                                            f.write(fileData)
                                        print(f"{entry.filename} is written to path {DestinationPath}")
                                        DuplicatedFileDetection.append(hashedData)
                                    else:
                                        totalDuplicatedFile += 1
                                        if checkingFileExtension(fileData, DestinationPath).endswith(ARCHIVEFORMATS):
                                            totalDuplicatedArchive += 1
                                            print(f"Duplicated archive/disk file at path {DestinationPath}")
                                            if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                                return True
                                        else:
                                            print(f"Duplicated file {entry.filename} at path {DestinationPath}")
                            if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                                return True
                        except zipfile.BadZipFile as error:
                            print(f"Bad Zip File: {error}")
                            pass
                        except RuntimeError as e:
                            if 'password required' in str(e).lower():
                                print("Zip file is encrypted!")
                                return True
                            else:
                                print(f"RunTimeError: {e}")
                                pass
                        except OSError as error:
                            print(f"OSError: {error}")
                            pass
            elif fileExt.endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz")):
                print("Archive is a tar file!")
                with tarfile.open(filePath[i], 'r') as tarRef:
                    print(f"Creating subdirectories...")
                    """First Extraction Focusing On Checking Extraction Path and Directory Structure"""
                    for entry in tarRef.getmembers():
                        totalFileCount += 1
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.name}")
                        if not DestinationPath.startswith(TempDir):
                            print(f"The uncompressed file name {entry.name} formed an illegal path {DestinationPath} to cause directory transversal attack!")
                            return True
                        if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.name:
                            if "." not in entry.name:
                                os.makedirs(DestinationPath, exist_ok=True)
                                print(f"Directory {entry.name} created at path {DestinationPath}")
                        if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                            return True

                    print(f"Extracting compressed file contents...")
                    """Second Extraction Focusing On Extracting All the Compressed Files"""
                    for entry in tarRef.getmembers():
                        if "." not in entry.name:
                            continue
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.name}")
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
                                if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.name:
                                    if checkingFileExtension(fileData, DestinationPath).endswith(ALLSCANNABLEFILEFORMATS):
                                        hashedData = hashlib.sha256(fileData).hexdigest()
                                        if hashedData not in DuplicatedFileDetection:
                                            with open(DestinationPath, 'wb') as f:
                                                f.write(fileData)
                                            print(f"{entry.name} is written to path {DestinationPath}")
                                            DuplicatedFileDetection.append(hashedData)
                                        else:
                                            totalDuplicatedFile += 1
                                            if checkingFileExtension(fileData, DestinationPath).endswith(ARCHIVEFORMATS):
                                                totalDuplicatedArchive += 1
                                                print(f"Duplicated archive/disk file at path {DestinationPath}")
                                                if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                                    return True
                                            else:
                                                print(f"Duplicated file at path {DestinationPath}")
                                if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                                    return True
                        except tarfile.TarError as error:
                            print(f"Tar file error: {error}")
                            pass
                        except OSError as error:
                            print(f"OSError: {error}")
                            pass
            elif fileExt.endswith(".rar"):
                print("Archive is a rar file!")
                with rarfile.RarFile(filePath[i], 'r') as rar:
                    if rar.needs_password():
                        print(f"Rar file {filePath[i]} required password!")
                        return True
                    print(f"Creating subdirectories...")
                    """First Extraction Focusing On Checking Extraction Path and Directory Structure"""
                    for entry in rar.infolist():
                        totalFileCount += 1
                        if entry.needs_password():
                            print(f"Compressed file {entry.filename} required password!")
                            return True
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.filename}")
                        if not DestinationPath.startswith(TempDir):
                            print(f"The uncompressed file name {entry.filename} formed an illegal path {DestinationPath} to cause directory transversal attack!")
                            return True
                        if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.filename:
                            if entry.filename.endswith('/'):
                                os.makedirs(DestinationPath, exist_ok=True)
                                print(f"Directory {entry.filename} created at path {DestinationPath}")
                        if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                            return True

                    print(f"Extracting compressed file contents...")
                    """Second Extraction Focusing On Extracting All the Compressed Files"""
                    for entry in rar.infolist():
                        DestinationPath = os.path.abspath(f"{TempDir}{entry.filename}")
                        if entry.filename.endswith('/'):
                            continue
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
                            if "__MACOSX" not in DestinationPath and not os.path.basename(DestinationPath).startswith("._") and not ".DS_Store" in entry.filename:
                                if checkingFileExtension(fileData, DestinationPath).endswith(ALLSCANNABLEFILEFORMATS):
                                    hashedData = hashlib.sha256(fileData).hexdigest()
                                    if hashedData not in DuplicatedFileDetection:
                                        with open(DestinationPath, 'wb') as f:
                                            f.write(fileData)
                                        print(f"{entry.filename} is written to path {DestinationPath}")
                                        DuplicatedFileDetection.append(hashedData)
                                    else:
                                        totalDuplicatedFile += 1
                                        if checkingFileExtension(fileData, DestinationPath).endswith(ARCHIVEFORMATS):
                                            totalDuplicatedArchive += 1
                                            print(f"Duplicated archive/disk file at path {DestinationPath}")
                                            if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                                return True
                                        else:
                                            print(f"Duplicated file {entry.filename} at path {DestinationPath}")
                            if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                                return True
                        except rarfile.BadRarFile as error:
                            print(f"Bad Rar File Error: {error}")
                            pass
                        except rarfile.NotRarFile as error:
                            print(f"Not Rar File Error: {error}")
                            pass
                        except OSError as error:
                            print(f"OSError: {error}")
                            pass
            elif fileExt.endswith((".gz", ".bz2", ".xz", ".lzma")):
                totalFileCount += 1
                try:
                    fileName = os.path.basename(filePath[i]).rsplit(fileExt, 1)[0]
                    DestinationPath = os.path.join(TempDir, fileName)
                    if not DestinationPath.startswith(os.path.abspath(TempDir)):
                        print(f"The uncompressed file name {fileName} formed an illegal path {DestinationPath} to cause directory transversal attack!")
                        return True
                    fileData = b''
                    if fileExt.endswith(".bz2"):
                        print("Archive is a bz2 file!")
                        with bz2.BZ2File(filePath[i], 'rb') as bz2File:
                            while True:
                                dataChunk = bz2File.read(CHUNKSIZE)
                                if not dataChunk or uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                                uncompressedSize += len(dataChunk)
                    elif fileExt.endswith(".gz"):
                        print("Archive is a gzip file!")
                        with gzip.open(filePath[i], 'rb') as gzipRef:
                            while True:
                                dataChunk = gzipRef.read(CHUNKSIZE)
                                if not dataChunk or uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                                uncompressedSize += len(dataChunk)
                    elif fileExt.endswith((".xz", ".lzma")):
                        print("Archive is in xz and lzma category!")
                        with lzma.open(filePath[i], 'rb') as lzFile:
                            while True:
                                dataChunk = lzFile.read(CHUNKSIZE)
                                if not dataChunk or uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                                    break
                                fileData += dataChunk
                                uncompressedSize += len(dataChunk)
                    if uncompressedSize >= UNCOMPRESSEDSIZELIMIT:
                        print(f"The total uncompressed size has reached the limit threshold!")
                        return True
                    fileExt = checkingFileExtension(fileData, fileName, False)
                    if fileExt.endswith(ARCHIVEFORMATS):
                        DestinationPath += fileExt
                    hashedData = hashlib.sha256(fileData).hexdigest()
                    if hashedData not in DuplicatedFileDetection:
                        if checkingFileExtension(fileData, fileName).endswith(ALLSCANNABLEFILEFORMATS):
                            with open(DestinationPath, "wb") as file:
                                file.write(fileData)
                            print(f"{fileName} is written to path {DestinationPath}")
                        DuplicatedFileDetection.append(hashedData)
                    else:
                        totalDuplicatedFile += 1
                        if checkingFileExtension(fileData, fileName).endswith(ARCHIVEFORMATS):
                            totalDuplicatedArchive += 1
                            print(f"Duplicated archive/disk file at path {DestinationPath}")
                            if totalDuplicatedArchive >= DUPLICATEDARCHIVELIMIT:
                                return True
                        else:
                            print(f"Duplicated file at path {DestinationPath}")
                    if totalFileCount // (totalDuplicatedFile + 1) <= 0.10:
                        return True
                except OSError as error:
                    print(f"OSError: {error}")
                    pass
                except lzma.LZMAError:
                    print(f"LZMAError: {error}")
                    pass
            os.remove(filePath[i])
            print("\n\n")

        archiveLayer += 1
        filePath.clear()
        for dirpath, _, filenames in os.walk(TempDir):
            for filename in filenames:
                i = os.path.join(dirpath, filename)
                with open(i, "rb") as file:
                    fileData = file.read()
                fileExt = checkingFileExtension(fileData, i, False)
                if fileExt.endswith(ARCHIVEFORMATS):
                    print(f"Found nested Archive file {filename} at path {i}")
                    if os.path.getsize(i) >= NESTEDARCHIVESIZELIMIT:
                        print(f"The nested file {filename} size is {os.path.getsize(i)}. The number is too large, thus, hinted potential archive bomb!")
                        return True
                    filePath.append(i)
    print(f"Archive content extracted with total uncompressed size of {uncompressedSize} bytes")
    return False


async def ArchiveFileScan(archiveFileName: str, bytesContent: bytes, hashedArchiveFileData: str) -> Tuple[bool, str]:  # Return True if scan is NSFW
    """
    Description: Scanning archive file and its archived content
    :param archiveFileName: Archive file name
    :param bytesContent: The byte content of the archive file
    :param hashedArchiveFileData: SHA512 hash of the archive file
    :return: Result of the scan and reason
    """
    mainArchiveFilePath = f"{MAINDOWNLOADDIR}{archiveFileName}"
    async with aiofiles.open(mainArchiveFilePath, "wb") as file:
        await file.write(bytesContent)
    print(f"Archive name: {archiveFileName}")
    print("Archive attachment downloaded!")
    print(f"Checking if archive is safe to extract!")
    if await asyncio.to_thread(ArchivesBombAnalysisAndExtraction, [mainArchiveFilePath]):
        await AddingNewNSFWData(hashedArchiveFileData, "Archive File - Potential Archive Bomb!")
        print("The Archive File is flagged as potential archive bomb!")
        return False, ""  # Cyber bot will delete the archive bomb!
    TempDir = f"{MAINDOWNLOADDIR}{archiveFileName.split('.')[0]}"
    print(f"Scanning content in temp directory: {TempDir}...\n\n")
    for dirpath, _, filenames in os.walk(TempDir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            async with aiofiles.open(filepath, "rb") as file:
                fileData = await file.read()
                fileExt = checkingRealFileExtension(await file.read(), filename)
            if filename.startswith("._"):  # Remove duplicated ._ file
                os.remove(filepath)
            print(f"Found media file {filename} at path {filepath}")
            hashedFileContent = await getHashValueofAttachmentFileData(filepath)
            if hashedFileContent in CLEANData.keys():
                print("Media file content already pass the scan!\n\n")
            else:
                print(f"Media file content is not in the clean data! Checking if it is in the NSFW data!")
                if hashedFileContent in NSFWData.keys():
                    print("Media file content already flagged NSFW!")
                    shutil.rmtree(TempDir)
                    await AddingNewNSFWData(hashedArchiveFileData, f"The file content {filename} in Archive file has already flagged NSFW! Reason: {NSFWData[hashedFileContent]}")
                    return True, f"NSFW Archive Content - The file content {filename} in Archive file has already flagged NSFW! Reason: {NSFWData[hashedFileContent]}"
                else:
                    if fileExt.endswith(DOCUMENTFILES):
                        pdfPath = await asyncio.to_thread(AsciiDocumentToPDFConversion, fileData)
                        scanResultDetails = await scanningPDFPagesWithGPT(pdfPath)
                        if scanResultDetails.startswith(("Yes", "yes", "YES")):
                            scanResult = True
                            scanResultDetails = scanResultDetails.strip("Yes, ")
                            scanResultDetails = f"NSFW message content in file - {scanResultDetails}"
                            print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
                            await AddingNewNSFWData(hashedFileContent, scanResultDetails)
                        else:
                            scanResult = False
                            await AddingNewCleanData(hashedFileContent, "Document file text is clean!")
                    else:
                        scanResult, scanResultDetails = await ScanningMedia(filepath, b'0x00', hashedFileContent, True)
                    if scanResult:
                        print(f"File content {filename} in Archive file was flagged NSFW!")
                        shutil.rmtree(TempDir)
                        await AddingNewNSFWData(hashedArchiveFileData, f"File content {filename} in Archive file was flagged NSFW! Reason: {scanResultDetails}")
                        return True, f"NSFW Archive Content - File content {filename} in Archive file was flagged NSFW! Reason: {scanResultDetails}"
                    print("\n\n")
    print(f"Archive content is clean!")
    await AddingNewCleanData(hashedArchiveFileData, "Archive contents passed the check!")
    shutil.rmtree(TempDir)
    return False, ""


async def NSFWScanAudio(audioPath: str, delete:bool=True) -> Tuple[bool, str]:  # Return True if Audio is NSFW!
    """
    Description: NSFW scan for audio file
    :param audioPath: Path to audio file on disk
    :param delete: Specify to delete the audio file or not
    :return: Scan result and reason
    """
    audioName = os.path.basename(audioPath).split('.')[0]
    # Running ffmpeg command to convert any input file to specific WAV audio format with data at 16-bit PCM
    if not audioPath.endswith(".wav"):
        print("Converting Audio to WAV file format...")
        waveFilePath = f"{os.path.dirname(audioPath)}/{audioName}.wav"
        try:
            await asyncio.to_thread(subprocess.run, ["ffmpeg", "-i", audioPath, "-acodec", "pcm_s16le", waveFilePath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if delete:
                os.remove(audioPath)
            print("WAV conversion successful!")
        except Exception as ConversionToWavAudioError:
            if delete:
                print(f"Error {ConversionToWavAudioError}")
                os.remove(audioPath)
                return True, "File Conversion Failure - Can not convert audio file to WAV format!"
            else:
                print(f"Error {ConversionToWavAudioError} while extracting audio from the video! Proceeding to scan video content...")
                return False, ""
    else:
        print("Audio file already in .wav format!")
        waveFilePath = audioPath
    try:
        async with aiofiles.open(waveFilePath, "rb") as audioFile:
            transcription = await GPTclient.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=(os.path.basename(waveFilePath), await audioFile.read())
            )
    except Exception as Error:
        print(f"GPT can not transcribe the audio: {Error}")
        os.remove(waveFilePath)
        scanResultDetails = "Audio is not transcribable"
        return False, f"Clean Audio Transcript - {scanResultDetails}"

    print(f"Words detected from audio file: {transcription.text}")
    os.remove(waveFilePath)
    scanResult, scanResultDetails = await NSFWscanMessage(transcription.text)
    if scanResult:
        return True, f"NSFW Audio Transcript - {scanResultDetails}"
    else:
        return False, f"Clean Audio Transcript - {scanResultDetails}"


async def NSFWscanMessage(checkMessage: str, URL: bool=False) -> Tuple[bool, str]:  # Return True if text content is NSFW!
    """
    Description: NSFW scan for ASCII content
    :param checkMessage: ASCII content to be scanned
    :param URL: Specify whether the ASCII content is a URL or not
    :param HTML: Specify whether the ASCII content is an HTML or not
    :return: Scan result and reason
    """
    print("Starting Black List check...")
    if REDDITDOMAINS.findall(unquote(checkMessage).lower()) or SUBREDDITPATTERN.search(unquote(checkMessage).lower()):
        print(f"Detected reddit url: {checkMessage}")
        redditUrl = True
    else:
        redditUrl = False

    for match in WORD.finditer(unquote(checkMessage).lower()):

        print("Checking for blacklisted domain name...")
        if match.group(1) in BlackListDomains:
            print(f"blacklisted domain: {match.group(1)}")
            return True, f"Message contains blacklisted NSFW domain {match.group(1)}"

        if redditUrl:
            print(f"Checking for blacklisted NSFW subreddit...")
            if match.group(1) in BlackListSubreddits:
                print(f"blacklisted subreddit: /r/{match.group(1)}")
                return True, f"Message contains blacklisted NSFW subreddit /r/{match.group(1)}"
    print("Black list check passed!")

    print("Starting Black List check on sophisticated message...")
    resolvedMessage = SANITIZE.sub('', unquote(checkMessage).lower())
    match = SUBREDDITPATTERN2.search(resolvedMessage)
    if match:
        print(f"Detected subreddit: /r/{match.group(1)}")
        if match.group(1) in BlackListSubreddits:
            print(f"blacklisted subreddit: /r/{match.group(1)}")
            return True, f"Message contains blacklisted NSFW subreddit /r/{match.group(1)}"
        print("Subreddit check passed!")
    print(f"Resolved message: {resolvedMessage}")
    for match in WORD.finditer(resolvedMessage):
        print("Checking for blacklisted domain name on sophisticated message...")
        if match.group(1) in BlackListDomains:
            print(f"blacklisted domain: {match.group(1)}")
            return True, f"Message contains blacklisted NSFW domain {match.group(1)}"
    print("Black list check passed!")

    print("Scanning content using Profanity Library...")
    if profanity.contains_profanity(checkMessage):
        print("Profanity Library detected inappropriate message!")
        if redditUrl:
            match = re.search(r'/r/(\w+)', unquote(checkMessage).lower())
            if match:
                newNSFWsubreddit = match.group(1).replace('/r/', '')
                BlackListSubreddits.add(newNSFWsubreddit)
                async with aiofiles.open(os.environ.get("EMMANUELBLACKLISTSUBREDDITS"), "a") as file:
                    await file.write(newNSFWsubreddit + '\n')
        if URL:
            return True, "URL contains keywords in Emmanuel default NSFW wordlist!"
        else:
            return True, "Message contains keywords in Emmanuel default NSFW wordlist!"

    if not URL:
        for text in SPECIALTEXT:
            if text in checkMessage:
                print("Special NSFW character detected!")
                return True, "Message contains keywords in Emmanuel default NSFW wordlist!"
    print("Profanity Library did not detect, starting GPT scan...")

    '''
    # The web search tool is very expensive, so I disable it, if you can afford, then just uncomment this section!
    if URL:
        print("Scanning URL content using web_search tool...")
        scanResult = await scanWebContentUsingWebSearchWithGPT(checkMessage)
        if scanResult.startswith(("Yes", "yes", "YES")):
            print("GPT detected inappropriate content in web content!")
            if redditUrl:
                match = re.search(r'/r/(\w+)', unquote(checkMessage).lower())
                if match:
                    newNSFWsubreddit = match.group(1).replace('/r/', '')
                    BlackListSubreddits.add(newNSFWsubreddit)
                    async with aiofiles.open(os.environ.get("EMMANUELBLACKLISTSUBREDDITS"), "a") as file:
                        await file.write(newNSFWsubreddit + '\n')
            return True, scanResult.strip("Yes,")
    '''

    scanResult = await scanningTextOnlyWithGPT(
        f"# ASK\n"
        f"Analyze the following message and identify any vulgar or inappropriate words.\n"
        f"# MESSAGE\n"
        f"Message: '{checkMessage}'\n"
        f"# IMPORTANT RULE\n"
        f"1. Consider the context—only, flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
        f"2. Taking into measure the text could be written in other language than English.\n"
        f"3. Consider text may be letter emoji or contains a sequence of emojis that can hint NSFW.\n"
        f"# RESPONSE FORMAT\n"
        f"Response MUST start with a Yes or No! If and only if IT'S a YES, follow by a COMMA and EXPLAIN the reason NO MORE THAN 30 WORDS!\n"
    )
    if scanResult.startswith(("Yes", "yes", "YES")):
        print("GPT detected inappropriate content!")
        if redditUrl:
            match = re.search(r'/r/(\w+)', unquote(checkMessage).lower())
            if match:
                newNSFWsubreddit = match.group(1).replace('/r/', '')
                BlackListSubreddits.add(newNSFWsubreddit)
                async with aiofiles.open(os.environ.get("EMMANUELBLACKLISTSUBREDDITS"), "a") as file:
                    await file.write(newNSFWsubreddit + '\n')
        return True, scanResult.strip("Yes,")
    print("GPT scan result is clean!")
    return False, scanResult.strip("No, ")


async def AdvanceBackTrackMessageScan(message: discord.Message) -> None:
    """
    Description: Concatenate the previous 10 message and use a dictionary to check if the concatenation result in a message with NSFW content
    :param message: The most recent message in the server
    :return: None
    """
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
    await ctx.response.defer(ephemeral=True)
    await ctx.followup.send("I'm a knight designed by Sir David Nguyen with a purpose of scanning message, audio, "
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
    await ctx.response.defer(ephemeral=True)
    await ctx.followup.send(
        "Image Formats: .jpg, .png, .jpeg, .raw, .pdf, .bmp, .webp, .tiff, .tif, .ico, .icns, .avif, .odd, .eps, .gif\n"
        "Video Formats: .mp4, .mov, .mkv, .avi, .m4v, .flv, .mpeg, mpg, .ts, .wmv, .dv, .mts, .m2ts, .vob, .ogv\n"
        "Audio Formats: .mp3, .wav, .oga, .m4a, .flac, .weba, .aac, .ac3, .aif, .aiff, .aifc, .amr, .au, .caf, .m4a,"
        " .m4b, .wma, .opus, .webm, .ogg\n"
        "Archive Formats: .zip, .tar, .tar.gz, .tar.bz2, .tar.xz, .tar.lzma, .tgz, .tbz2, .txz, .gz, .rar, .bz2, .xz, .lzma\n"
        "ASCII-based file: .txt, .json, .csv, .yaml, and script files"
    )


@Emmanuel.tree.command(
    name="clear_emmanuel_dm_messages",
    description="Delete all direct messages sent by Knight Emmanuel to you"
)
async def clear_emmanuel_dm_messages(ctx):
    await ctx.response.defer(ephemeral=True)
    async for message in ctx.user.history():
        if message.author == Emmanuel.user:
            await message.delete()
    await ctx.followup.send("All DM messages by me have been deleted.")


@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=ZoneInfo("America/New_York")))  # A task every new day
async def reset_user_uncensor_value_and_update_llm_usage():
    global previousDate, previousMonth, previousYear

    print("\n")
    async with ConfigLock:
        for serverID in configuration:
            server = await Emmanuel.fetch_guild(int(serverID))
            for member in configuration[serverID]["User-Uncensor-Limit"]:
                configuration[serverID]["User-Uncensor-Limit"][member] = DAILYUNCENSORLIMIT
            await writingLog(f"Resetting all members daily uncensor value in server {server.name} ID {server.id} - Status: SUCCESS\n\n")
            print(f"Resetting all members daily uncensor value in server {server.name} ID {server.id} - Status: SUCCESS")
        async with aiofiles.open(EMMANUELCONFIG, "w") as file:
            await file.write(json.dumps(configuration, indent=4))

    currentTime = time.ctime(time.time()).split()

    # Checking new date
    if currentTime[2] != previousDate:
        print(f"New Day of the Month Change: {previousMonth} {previousDate} -> {currentTime[1]} {currentTime[2]}")
        try:
            print(f"Updating LLMMonthlyUsageReport.png...")
            async with MonthlyCSVLock:
                monthlyData = await asyncio.to_thread(pd.read_csv, f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv")
            monthlyTotalInputToken = []
            monthlyTotalOutputToken = []
            monthlyTotalCost = []
            for day in range(1, int(currentTime[2]) + 1):
                dailyTotalInputToken = 0
                dailyTotalOutputToken = 0
                dailyTotalCost = 0
                for _, row in monthlyData.iterrows():
                    if int(row["Date"].split(" ")[1]) == day:
                        dailyTotalInputToken += row["Total Input Tokens"]
                        dailyTotalOutputToken += row["Total Output Tokens"]
                        dailyTotalCost += row["Total Cost"]
                monthlyTotalInputToken.append(dailyTotalInputToken)
                monthlyTotalOutputToken.append(dailyTotalOutputToken)
                monthlyTotalCost.append(dailyTotalCost)
            datasets = [
                {"values": monthlyTotalInputToken, "title": "Total Input Tokens", "color": "Blue"},
                {"values": monthlyTotalOutputToken, "title": "Total Output Tokens", "color": "Green"},
                {"values": monthlyTotalCost, "title": "Total Cost ($)", "color": "Orange"},
            ]
            dates = [str(date) for date in range(1, int(currentTime[2]) + 1)]
            plotBarCharts(datasets, dates, "LLM Usage - Monthly Overview",f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}/LLMMonthlyUsageReport.png")
            print(f"Successfully Updating LLMMonthlyUsageReport.png!")
            await writingLog("Updating LLMMonthlyUsageReport.png\nStatus: Success\n\n")

            try:
                print(f"Updating LLMModelsUsed.png...")
                LLMModelUses = [0 for _ in range(len(LLMModels))]
                for _, row in monthlyData.iterrows():
                    LLMModelUses[LLMModels.index(row["LLM Models"])] += 1
                plotModelCalls(LLMModelUses, f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}/LLMModelsUsed.png")
                print(f"Successfully Updating LLMModelsUsed.png!")
                await writingLog("Updating LLMModelsUsed.png\nStatus: Success\n\n")
            except Exception as error:
                print(f"An error occurs while updating LLMModelsUsed.png\n{error}")
                await writingLog(f"Updating LLMModelsUsed.png\nError: {error}\n\n")

        except Exception as error:
            print(f"An error occurs while updating LLMMonthlyUsageReport.png\n{error}")
            await writingLog(f"Updating LLMMonthlyUsageReport.png\nError: {error}\n\n")

        previousDate = currentTime[2]

    # Checking new year
    if currentTime[4] != previousYear:
        print(f"New Year Change: {previousYear} -> {currentTime[4]}")
        try:
            print(f"Generating LLM Usage Yearly Report...")
            async with YearlyCSVLock:
                yearlyData = await asyncio.to_thread(pd.read_csv, f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv")
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            monthlyTotalInputTokens = []
            monthlyTotalOutputTokens = []
            monthlyTotalCosts = []
            for month in months:
                monthlyTotalInputToken = 0
                monthlyTotalOutputToken = 0
                monthlyTotalCost = 0
                for _, row in yearlyData.iterrows():
                    if row["Date"].split(' ')[0] == month:
                        monthlyTotalInputToken += row["Total Input Tokens"]
                        monthlyTotalOutputToken += row["Total Output Tokens"]
                        monthlyTotalCost += row["Total Cost"]
                monthlyTotalInputTokens.append(monthlyTotalInputToken)
                monthlyTotalOutputTokens.append(monthlyTotalOutputToken)
                monthlyTotalCosts.append(monthlyTotalCost)
            datasets = [
                {"values": monthlyTotalInputTokens, "title": "Total Input Tokens", "color": "Blue"},
                {"values": monthlyTotalOutputTokens, "title": "Total Output Tokens", "color": "Green"},
                {"values": monthlyTotalCosts, "title": "Total Cost ($)", "color": "Orange"},
            ]
            plotBarCharts(datasets, months, "LLM Usage - End of Year Overview",f"{LLMUSAGELOGDIR}{previousYear}/FullYearUsageReport.png")
            print(f"Successfully Generating LLM Usage Yearly Report!")
            await writingLog("Generating LLM Usage Yearly Report\nStatus: Success\n\n")

            try:
                print(f"Resetting LLMYearlyUsage.csv...")
                await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "w",["Date", "Total Input Tokens", "Total Output Tokens", "LLM Models", "Total Cost"], YearlyCSVLock)
                print(f"Successfully resetting LLMYearlyUsage.csv!")
                await writingLog("Resetting LLMYearlyUsage.csv\nStatus: Success\n\n")

                try:
                    print(f"Creating a new year folder...")
                    os.mkdir(f"{LLMUSAGELOGDIR}{currentTime[4]}")
                    print(f"Successfully create a new year folder!")
                    await writingLog("Creating a new year folder\nStatus: Success\n\n")

                except Exception as error:
                    print(f"An error occurs while creating a new year folder\n{error}")
                    await writingLog(f"Creating a new year folder\nError: {error}\n\n")

            except Exception as error:
                print(f"An error occurs while resetting LLMYearlyUsage.csv\n{error}")
                await writingLog(f"Resetting LLMYearlyUsage.csv\nError: {error}\n\n")

        except Exception as error:
            print(f"An error occurs while generating LLM Usage Yearly Report\n{error}")
            await writingLog(f"Generating LLM Usage Yearly Report\nError: {error}\n\n")

        previousYear = currentTime[4]

    # Checking new month
    if currentTime[1] != previousMonth:
        print(f"New Month Change: {previousMonth} -> {currentTime[1]}")
        try:
            print(f"Resetting LLMMonthlyUsage.csv...")
            await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "w",["Date", "Total Input Tokens", "Total Output Tokens", "LLM Models", "Total Cost"], MonthlyCSVLock)
            print(f"Successfully resetting LLMMonthlyUsage.csv!")
            await writingLog("Resetting LLMMonthlyUsage.csv\nStatus: Success\n\n")

            try:
                print(f"Creating a new month folder...")
                os.mkdir(f"{LLMUSAGELOGDIR}{currentTime[4]}/{currentTime[1]}")
                print(f"Successfully create a new month folder!")
                await writingLog("Creating a new month folder\nStatus: Success\n\n")

            except Exception as error:
                print(f"An error occurs while creating a new month folder\n{error}")
                await writingLog(f"Creating a new month folder\nError: {error}\n\n")

        except Exception as error:
            print(f"An error occurs while resetting LLMMonthlyUsage.csv\n{error}")
            await writingLog(f"Resetting LLMMonthlyUsage.csv\nError: {error}\n\n")
        previousMonth = currentTime[1]


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
    reset_user_uncensor_value_and_update_llm_usage.start()


@Emmanuel.event
async def on_member_join(member):
    if member.id != WHITELISTMEMBERS:
        serverID = member.guild.id
        async with ConfigLock:
            if configuration.get(str(serverID), ""):
                if configuration[str(serverID)]["User-Uncensor-Limit"].get(str(member.id), "") == "":
                    configuration[str(serverID)]["User-Uncensor-Limit"][str(member.id)] = DAILYUNCENSORLIMIT
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
                    await writingLog(f"Member {member.name} ID {member.id} join server {member.guild.name} ID {member.guild.id}\n\n")
                    print(f"Member {member.name} ID {member.id} join server {member.guild.name} ID {member.guild.id}")
            else:
                await checkServerExistInConfigFile(serverID)


@Emmanuel.event
async def on_member_remove(member):
    if member.id != WHITELISTMEMBERS:
        serverID = member.guild.id
        async with ConfigLock:
            if configuration.get(str(serverID), ""):
                if configuration[str(serverID)]["User-Uncensor-Limit"].get(str(member.id), ""):
                    del configuration[str(serverID)]["User-Uncensor-Limit"][str(member.id)]
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
                    await writingLog(f"Member {member.name} ID {member.id} left server {member.guild.name} ID {member.guild.id}\n\n")
                    print(f"Member {member.name} ID {member.id} left server {member.guild.name} ID {member.guild.id}")
            else:
                await checkServerExistInConfigFile(serverID)

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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            async with ConfigLock:
                if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                    configuration[str(ctx.guild.id)]["Uncensored-members"].append(member.id)
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            async with ConfigLock:
                if member.id not in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                    await ctx.followup.send(f"{member.name} already removed from the white list!")
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-members"].remove(member.id)
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            async with ConfigLock:
                if ctx.channel.id in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                    await ctx.followup.send(f"{ctx.channel.name} already added to the uncensored list!")
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].append(ctx.channel.id)
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            async with ConfigLock:
                if ctx.channel.id not in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                    await ctx.followup.send(f"{ctx.channel.name} already removed from the uncensored list!")
                else:
                    configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(ctx.channel.id)
                    async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                        await file.write(json.dumps(configuration, indent=4))
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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            members = ""
            async with ConfigLock:
                for memberID in configuration[str(ctx.guild.id)]["Uncensored-members"]:
                    member = Emmanuel.get_user(memberID)
                    if member:
                        members += f"Member ID: {member.id}\tMember name: {member.name}\n"
                    else:
                        configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(memberID)
                        async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                            await file.write(json.dumps(configuration, indent=4))
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
        if ctx.user.id == ctx.guild.owner.id or ctx.user.id == OWNER_DISCORD_USER_ID:
            await checkServerExistInConfigFile(str(ctx.guild.id))
            channels = ""
            async with ConfigLock:
                for channelID in configuration[str(ctx.guild.id)]["Uncensored-channels"]:
                    channel = Emmanuel.get_channel(channelID)
                    if channel:
                        channels += f"Channel ID: {channel.id}\tChannel name: {channel.name}\n"
                    else:
                        configuration[str(ctx.guild.id)]["Uncensored-channels"].remove(channelID)
                        async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                            await file.write(json.dumps(configuration, indent=4))
                await ctx.followup.send(f"Uncensored channels for server {ctx.guild.name} ID {ctx.guild.id}:\n{channels}")
        else:
            await ctx.followup.send("You're not the Server Owner, this command is for the Owner ONLY!")


@Emmanuel.event
async def on_message_edit(before, after):  # Note: media attachment can be embedded via URL in re-edit message!
    # Prioritize Executing commands first!
    global FILEDOWNLOADCOUNTER

    await Emmanuel.process_commands(after)

    # Add new server to the configuration file!
    try:
        await checkServerExistInConfigFile(str(after.guild.id))
    except AttributeError:
        pass

    if str(after.channel) != "Direct Message with Unknown User":
        if after.author.id == Emmanuel.user.id:
            return

        if after.author.id in configuration[str(after.guild.id)]["Uncensored-members"]:
            await writingLog(f"User: {after.author.name} ID {after.author.id} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}\nNOTE: User is on the server uncensored members list\n\n")
            return

        if after.channel.id in configuration[str(after.guild.id)]["Uncensored-channels"]:
            await writingLog(f"User: {after.author.name} ID {after.author.id} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}\nNOTE: The channel is on the server uncensored channels list\n\n")
            return

        if before.content != after.content:
            print("Re-Edit message detected!!!")

            """Logging user message"""
            logUserAction = f"User: {after.author.name} ID {after.author.id} re-edited message '{before.content}' to new message '{after.content}' in channel '{after.channel.name}' - ID {after.channel.id} in Server '{after.guild.name}' - ID {after.guild.id}"
            textContent = after.content

            """Checking if a URL in a message and make sure only one URL"""
            if "https://" in after.content or "http://" in after.content:
                print("Re-Edited Message contains URL link(s)! Checking all the URL(s)...")
                URLs = URLPATTERN.findall(after.content.replace(" ", ""))
                URLs = list(set(URLs))
                for URL in URLs:
                    print(f"Extracting {URL} from message {after.content}")
                    textContent = textContent.replace(URL, '')
                    if "../" in unquote(URL):
                        await after.delete()
                        logUserAction += "\nReedited-Message is deleted for having a URL hinted potential directory transversal attack!!!"
                        try:
                            await after.author.send(f"URL {URL} hinted a potential ../ attack!")
                            logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                        except Exception as error:
                            logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                        await writingLog(logUserAction)
                        # Advance scan previous message for profanity!
                        await AdvanceBackTrackMessageScan(after)
                        print(f"URL {URL} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                        return

                    if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                        BasedURLToSave = hashlib.sha512(URL.split('?')[0].lower().encode()).hexdigest()
                    else:
                        BasedURLToSave = hashlib.sha512(URL.encode()).hexdigest()

                    """Checking if there is another subroutine scanning the same URL"""
                    if CURRENTSCANOPERATION.get(BasedURLToSave, "") == "In Progress":
                        print(f"URL {URL} is currently being scanned by other subroutine!")
                        while True:
                            await asyncio.sleep(0)
                            if not CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                break
                    else:
                        CURRENTSCANOPERATION[BasedURLToSave] = "In Progress"

                    """Checking if URl is in the clean list or already flagged NSFW"""
                    print(f"URL in SHA512 format: {BasedURLToSave}")
                    if BasedURLToSave in CLEANData.keys():
                        print("The URL already passed the check as clean!\n\n")
                    else:
                        if BasedURLToSave in NSFWData.keys():
                            await after.delete()
                            logUserAction += f"\nReedited-Message was deleted for having URL content already flagged NSFW! - {NSFWData[BasedURLToSave]}"
                            try:
                                await after.author.send(f"The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                                logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                            except Exception as error:
                                logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                            await writingLog(logUserAction)
                            # Advance scan previous message for profanity!
                            await AdvanceBackTrackMessageScan(after)
                            print("The URL already flagged NSFW! Terminating Scan Process...\n\n")
                            if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                del CURRENTSCANOPERATION[BasedURLToSave]
                            return
                        else:
                            """Checking any NSFW hint in the URL query"""
                            print("Checking any hinted NSFW in URL name...")
                            scanResult, scanResultDetails = await NSFWscanMessage(URL, True)
                            if scanResult:
                                await after.delete()
                                await AddingNewNSFWData(BasedURLToSave, f"NSFW URL name - {scanResultDetails}")
                                logUserAction += f"\nReedited-Message was deleted for having URL name hinted NSFW!"
                                try:
                                    await after.author.send(f"The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                    logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                except Exception as error:
                                    logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                await writingLog(logUserAction)
                                # Advance scan previous message for profanity!
                                await AdvanceBackTrackMessageScan(after)
                                print(f"URL name hinted NSFW content! Terminating Scan Process...\n\n")
                                if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                    del CURRENTSCANOPERATION[BasedURLToSave]
                                return
                            """Checking Klipy and Tenor Gif"""
                            if URL.startswith(("https://klipy.com/gifs/", "https://tenor.com/view")):
                                if URL.startswith("https://klipy.com/gifs/"):
                                    gifDomain = 'Klipy'
                                    newURL = await isKlipyURLValid(URL)
                                else:
                                    gifDomain = 'Tenor'
                                    newURL = await isTenorURLValid(URL)

                                print(f"URL appear to be a {gifDomain} Gif, checking if {gifDomain} gif is valid...")
                                if newURL != "Invalid":
                                    print(f"{gifDomain} gif URL is valid!")
                                    URL = newURL
                                else:
                                    await after.delete()
                                    print(f"{gifDomain} gif URL {URL} is not a valid {gifDomain} gif!")
                                    logUserAction += f"\nReedited Message was deleted for having invalid {gifDomain} Gif URL {URL}!"
                                    try:
                                        await after.author.send(f"Your message contains an invalid {gifDomain} URL! Please provide a valid URL!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(after)
                                    print("Re-Edit Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                            """Checking if URL is valid!"""
                            try:
                                async with Emmanuel.session.get(URL) as response:
                                    statuscode = response.status
                                    if statuscode in range(400, 500):
                                        statuscode, UrlContent = await asyncio.to_thread(SeleniumHTMLRetrieval, random.choice(SCRAPEOPSMOBILEBROWSERHEADERS), URL) # Setting heavy I/O synchronous Selenium function as thread to allow async operation and prevent blocking.
                                    else:
                                        UrlContent = await response.read()
                            except Exception as URLQueryError:
                                statuscode = 403
                                print(f"Error getting URL: {URLQueryError}.")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                                    await after.delete()
                                    logUserAction += f"\nRe-Edit Message is deleted for having a discord attachment URL {URL} can not be scanned!"
                                    try:
                                        await after.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(after)
                                    print("Re-Edit Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"

                            if statuscode == 200:
                                print(f"URL is valid!")
                                """Analyzing if URL content is an image, video, audio, or archive file"""
                                """Checking if URL content already been scanned"""
                                hashedURLContent = hashlib.sha512(UrlContent).hexdigest()
                                print(f"URL Content in SHA512: {hashedURLContent}")
                                print(f"Checking if URL content is already in a clean list...")
                                if hashedURLContent in CLEANData.keys():
                                    print("URL content already pass the scan!")
                                    print("Adding based URL to clean data!")
                                    await AddingNewCleanData(BasedURLToSave,f"URL content already passed the check - {CLEANData[hashedURLContent]}")
                                else:
                                    print(f"URL content is not in the clean data! Checking if the content is in the NSFW data!")
                                    if hashedURLContent in NSFWData.keys():
                                        await after.delete()
                                        print("URL content already flagged NSFW!")
                                        print(f"Adding based URL to NSFW data!")
                                        await AddingNewNSFWData(BasedURLToSave,f"URL content already flagged NSFW! - {NSFWData[hashedURLContent]}")
                                        logUserAction += f"\nReedited-Message was deleted for having URL content already flagged NSFW! - {NSFWData[hashedURLContent]}"
                                        try:
                                            await after.author.send(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                            logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                        except Exception as error:
                                            logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                        await writingLog(logUserAction)
                                        # Advance scan previous message for profanity!
                                        await AdvanceBackTrackMessageScan(after)
                                        print("Re-Edit Message Content Scan Process Finished!\n\n")
                                        if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                            del CURRENTSCANOPERATION[BasedURLToSave]
                                        return
                                    else:
                                        URLContentExt = checkingRealFileExtension(UrlContent, os.path.basename(URL.split('?')[0].lower()))
                                        FILEDOWNLOADCOUNTER += 1
                                        URLContentName = f'{FILEDOWNLOADCOUNTER}{URLContentExt}'
                                        UrlContentNSFWResult = False
                                        UrlContentNSFWResultDetails = ""
                                        print(f"URL content extension: {URLContentExt}")
                                        if URLContentName.endswith(ALLSCANNABLEFILEFORMATS):
                                            scanContent = True
                                            async with ConfigLock:
                                                if configuration.get(str(after.guild.id), ""):
                                                    if configuration[str(after.guild.id)]["User-Uncensor-Limit"].get(str(after.author.id), ""):
                                                        if configuration[str(after.guild.id)]["User-Uncensor-Limit"][str(after.author.id)] > 0:
                                                            scanContent = False
                                                            logUserAction += f"\nUser {after.author.name} ID {after.author.id} uncensor limit is {configuration[str(after.guild.id)]["User-Uncensor-Limit"][str(after.author.id)]} in server {after.guild.name} ID {after.guild.id}\nFile content is not scanned!!!"
                                                            print(f"User {after.author.name} ID {after.author.id} uncensor limit is {configuration[str(after.guild.id)]["User-Uncensor-Limit"][str(after.author.id)]} in server {after.guild.name} ID {after.guild.id}\nFile content is not scanned!!!")
                                                            configuration[str(after.guild.id)]["User-Uncensor-Limit"][str(after.author.id)] -= 1
                                                            async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                                                                await file.write(json.dumps(configuration, indent=4))
                                            if scanContent:
                                                if URLContentExt.endswith(ARCHIVEFORMATS):
                                                    UrlContentNSFWResult, UrlContentNSFWResultDetails = await ArchiveFileScan(URLContentName, UrlContent, BasedURLToSave)
                                                elif URLContentExt.endswith(DOCUMENTFILES):
                                                    print(f"Scanning ASCII text in URL content...")
                                                    pdfPath = await asyncio.to_thread(AsciiDocumentToPDFConversion,UrlContent)
                                                    UrlContentNSFWResultDetails = await scanningPDFPagesWithGPT(pdfPath)
                                                    if UrlContentNSFWResultDetails.startswith(("Yes", "yes", "YES")):
                                                        UrlContentNSFWResult = True
                                                        UrlContentNSFWResultDetails = UrlContentNSFWResultDetails.strip("Yes, ")
                                                        UrlContentNSFWResultDetails = f"NSFW message content in file - {UrlContentNSFWResultDetails}"
                                                        print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
                                                        await AddingNewNSFWData(BasedURLToSave, UrlContentNSFWResultDetails)
                                                    else:
                                                        UrlContentNSFWResult = False
                                                        await AddingNewCleanData(BasedURLToSave,"Document file text is clean!")
                                                else:
                                                    UrlContentNSFWResult, UrlContentNSFWResultDetails = await ScanningMedia(URLContentName, UrlContent, BasedURLToSave)
                                        else:
                                            await AddingNewCleanData(BasedURLToSave,"URL link is clean or URL content is not in Emmanuel scannable file formats!")
                                        print("Scan Process Finished!\n\n")
                                        if UrlContentNSFWResult:
                                            await after.delete()
                                            logUserAction += f"\nRe-edited Message was deleted for having NSFW URL content {UrlContentNSFWResultDetails}"
                                            try:
                                                await after.author.send(UrlContentNSFWResultDetails)
                                                logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                            except Exception as error:
                                                logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                            await writingLog(logUserAction)
                                            # Advance scan previous message for profanity!
                                            await AdvanceBackTrackMessageScan(after)
                                            if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                                del CURRENTSCANOPERATION[BasedURLToSave]
                                            return
                            else:
                                print(f"URL is invalid with status code {statuscode}!")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/","https://media.discordapp.net/attachments/")):
                                    await after.delete()
                                    logUserAction += f"\nRe-Edit Message is deleted for having a discord attachment URL {URL} can not be scanned!"
                                    try:
                                        await after.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(after)
                                    print("Re-Edit Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"
                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                        del CURRENTSCANOPERATION[BasedURLToSave]

            """Scanning message text content with hyperlink removed"""
            if textContent:
                print(f"Scanning text content with URL already filtered...")
                print(f"Text content: {textContent}")
                scanResult, scanResultDetails = await NSFWscanMessage(textContent)
                if scanResult:
                    await after.delete()
                    logUserAction += f"\nReedited Message was deleted for having NSFW text content! - {scanResultDetails}"
                    try:
                        await after.author.send(scanResultDetails)
                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                    except Exception as error:
                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                else:
                    logUserAction += f"\nReedited Message is cleaned!\n\n"
                    print("Message text content is clean!")
            else:
                logUserAction += f"\nReedited Message is cleaned!\n\n"
            # Advance scan previous message for profanity!
            await AdvanceBackTrackMessageScan(after)
            await writingLog(logUserAction)
            print("Re-Edit Message Content Scan Process Finished!\n\n")


@Emmanuel.event
async def on_message(message):
    global FILEDOWNLOADCOUNTER
    # Prioritize Executing commands first!
    await Emmanuel.process_commands(message)

    # Add new server to the configuration file!
    try:
        await checkServerExistInConfigFile(str(message.guild.id))
    except AttributeError:
        pass

    if str(message.channel) != "Direct Message with Unknown User":
        """Logging user message"""
        logUserAction = f"User: {message.author.name} sent message: {message.content}"
        if len(message.attachments) != 0:
            for attachment in message.attachments:
                logUserAction += f"\nwith file attachment: {attachment.filename}\ntemporary URL: {attachment.url}"
        logUserAction += f"\nFrom channel '{message.channel.name}' - ID {message.channel.id} in Server '{message.guild.name}' - ID {message.guild.id}"

        if message.author.id in configuration[str(message.guild.id)]["Uncensored-members"]:
            logUserAction += f"\nNOTE: User is on the server uncensored members list!\n\n"
            await writingLog(logUserAction)
            return

        if message.channel.id in configuration[str(message.guild.id)]["Uncensored-channels"]:
            logUserAction += f"\nNOTE: The channel is on the server uncensored channels list!\n\n"
            await writingLog(logUserAction)
            return

        if message.content:
            textContent = message.content
            """Checking if a URL in a message and make sure only one URL"""
            if "https://" in message.content or "http://" in message.content:
                print("Message contains URL link(s)! Checking all the URL(s)...")
                URLs = URLPATTERN.findall(message.content.replace(" ", ""))
                URLs = list(set(URLs))
                for URL in URLs:
                    textContent = textContent.replace(URL, '')
                    print(f"Extracting {URL} from message {message.content}")

                    if "../" in unquote(URL):
                        await message.delete()
                        logUserAction += "\nMessage is deleted for having a URL hinted potential directory transversal attack!!!"
                        try:
                            await message.author.send(f"URL {URL} hinted a potential ../ attack!")
                            logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                        except Exception as error:
                            logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                        await writingLog(logUserAction)
                        # Advance scan previous message for profanity!
                        await AdvanceBackTrackMessageScan(message)
                        print(f"URL {URL} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                        return

                    if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                        BasedURLToSave = hashlib.sha512(URL.split('?')[0].lower().encode()).hexdigest()
                    else:
                        BasedURLToSave = hashlib.sha512(URL.encode()).hexdigest()

                    """Checking if there is another subroutine scanning the same URL"""
                    if CURRENTSCANOPERATION.get(BasedURLToSave, "") == "In Progress":
                        print(f"URL {URL} is currently being scanned by other subroutine!")
                        while True:
                            await asyncio.sleep(0)
                            if not CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                break
                    else:
                        CURRENTSCANOPERATION[BasedURLToSave] = "In Progress"

                    """Checking if URl is in the clean list or already flagged NSFW"""
                    print(f"URL in SHA512 format: {BasedURLToSave}")
                    if BasedURLToSave in CLEANData.keys():
                        print("The URL already passed the check as clean!")
                    else:
                        if BasedURLToSave in NSFWData.keys():
                            await message.delete()
                            logUserAction += f"\nMessage was deleted for having URL content already flagged NSFW! - {NSFWData[BasedURLToSave]}"
                            try:
                                await message.author.send(f"The URL <{URL}> has already flagged NSFW! {NSFWData[BasedURLToSave]}")
                                logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                            except Exception as error:
                                logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                            await writingLog(logUserAction)
                            # Advance scan previous message for profanity!
                            await AdvanceBackTrackMessageScan(message)
                            print("The URL already flagged NSFW! Terminating Scan Process...\n\n")
                            return
                        else:
                            """Checking any NSFW hint in the URL query"""
                            print("Checking any hinted NSFW in URL name...")
                            scanResult, scanResultDetails = await NSFWscanMessage(URL, True)
                            if scanResult:
                                await message.delete()
                                await AddingNewNSFWData(BasedURLToSave, f"NSFW URL name - {scanResultDetails}")
                                logUserAction += f"\nMessage was deleted for having URL name hinted NSFW!"
                                try:
                                    await message.author.send(f"The URL <{URL}> was flagged NSFW! Reason: NSFW URL name - {scanResultDetails}")
                                    logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                except Exception as error:
                                    logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                await writingLog(logUserAction)
                                # Advance scan previous message for profanity!
                                await AdvanceBackTrackMessageScan(message)
                                print(f"URL name hinted NSFW content! Terminating Scan Process...\n\n")
                                if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                    del CURRENTSCANOPERATION[BasedURLToSave]
                                return
                            """Checking Klipy and Tenor Gif"""
                            if URL.startswith(("https://klipy.com/gifs/", "https://tenor.com/view")):
                                if URL.startswith("https://klipy.com/gifs/"):
                                    gifDomain = 'Klipy'
                                    newURL = await isKlipyURLValid(URL)
                                else:
                                    gifDomain = 'Tenor'
                                    newURL = await isTenorURLValid(URL)

                                print(f"URL appear to be a {gifDomain} Gif, checking if {gifDomain} gif is valid...")
                                if newURL != "Invalid":
                                    print(f"{gifDomain} gif URL is valid!")
                                    URL = newURL
                                else:
                                    await message.delete()
                                    print(f"{gifDomain} gif URL {URL} is not a valid {gifDomain} gif!")
                                    logUserAction += f"\nMessage was deleted for having invalid {gifDomain} Gif URL {URL}!"
                                    try:
                                        await message.author.send(f"Your message contains an invalid {gifDomain} URL! Please provide a valid URL!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(message)
                                    print("Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                            """Checking if URL is valid!"""
                            try:
                                async with Emmanuel.session.get(URL) as response:
                                    statuscode = response.status
                                    if statuscode in range(400, 500):
                                        statuscode, UrlContent = await asyncio.to_thread(SeleniumHTMLRetrieval, random.choice(SCRAPEOPSMOBILEBROWSERHEADERS), URL)
                                    else:
                                        UrlContent = await response.read()
                            except Exception as URLQueryError:
                                statuscode = 403
                                print(f"Error getting URL: {URLQueryError}.")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                                    await message.delete()
                                    logUserAction += f"\nMessage is deleted for having a discord attachment URL {URL} can not be scanned!"
                                    try:
                                        await message.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(message)
                                    print("Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"
                            if statuscode == 200:
                                print(f"URL is valid!")
                                """Analyzing if URL content is an image, video, audio, or archive file"""
                                """Checking URL content already been scanned"""
                                hashedURLContent = hashlib.sha512(UrlContent).hexdigest()
                                print(f"URL content in SHA512: {hashedURLContent}")
                                print(f"Checking if URL content is already in a clean list...")
                                if hashedURLContent in CLEANData.keys():
                                    print("URL content already pass the scan!")
                                    print(f"Adding based URL to clean data!")
                                    await AddingNewCleanData(BasedURLToSave,f"URL content already passed the check - {CLEANData[hashedURLContent]}")
                                else:
                                    print(f"URL content is not in the clean data! Checking if the content is in the NSFW data!")
                                    if hashedURLContent in NSFWData.keys():
                                        await message.delete()
                                        print("URL content already flagged NSFW!")
                                        print(f"Adding based URL to NSFW data!")
                                        await AddingNewNSFWData(BasedURLToSave,f"URL content already flagged NSFW! - {NSFWData[hashedURLContent]}")
                                        logUserAction += f"\nMessage was deleted for having URL content already flagged NSFW! - {NSFWData[hashedURLContent]}"
                                        try:
                                            await message.author.send(f"The content in URL <{URL}> has already flagged NSFW! Reason: {NSFWData[hashedURLContent]}")
                                            logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                        except Exception as error:
                                            logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                        await writingLog(logUserAction)
                                        # Advance scan previous message for profanity!
                                        await AdvanceBackTrackMessageScan(message)
                                        print("Message Content Scan Process Finished!\n\n")
                                        if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                            del CURRENTSCANOPERATION[BasedURLToSave]
                                        return
                                    else:
                                        URLContentExt = checkingRealFileExtension(UrlContent, os.path.basename(URL.split('?')[0].lower()))
                                        FILEDOWNLOADCOUNTER += 1
                                        URLContentName = f'{FILEDOWNLOADCOUNTER}{URLContentExt}'
                                        UrlContentNSFWResult = False
                                        UrlContentNSFWResultDetails = ""
                                        print(f"URL content extension: {URLContentExt}")
                                        if URLContentExt.endswith(ALLSCANNABLEFILEFORMATS):
                                            scanContent = True
                                            async with ConfigLock:
                                                if configuration.get(str(message.guild.id), ""):
                                                    if configuration[str(message.guild.id)]["User-Uncensor-Limit"].get(str(message.author.id), ""):
                                                        if configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)] > 0:
                                                            scanContent = False
                                                            logUserAction += f"\nUser {message.author.name} ID {message.author.id} uncensor limit is {configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)]} in server {message.guild.name} ID {message.guild.id}\nFile content is not scanned!!!"
                                                            print(f"User {message.author.name} ID {message.author.id} uncensor limit is {configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)]} in server {message.guild.name} ID {message.guild.id}\nFile content is not scanned!!!")
                                                            configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)] -= 1
                                                            async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                                                                await file.write(json.dumps(configuration, indent=4))
                                            if scanContent:
                                                if URLContentExt.endswith(ARCHIVEFORMATS):
                                                    UrlContentNSFWResult, UrlContentNSFWResultDetails = await ArchiveFileScan(URLContentName, UrlContent, BasedURLToSave)
                                                elif URLContentExt.endswith(DOCUMENTFILES):
                                                    print(f"Scanning ASCII text in URL content...")
                                                    pdfPath = await asyncio.to_thread(AsciiDocumentToPDFConversion, UrlContent)
                                                    UrlContentNSFWResultDetails = await scanningPDFPagesWithGPT(pdfPath)
                                                    if UrlContentNSFWResultDetails.startswith(("Yes", "yes", "YES")):
                                                        UrlContentNSFWResult = True
                                                        UrlContentNSFWResultDetails = UrlContentNSFWResultDetails.strip("Yes, ")
                                                        UrlContentNSFWResultDetails = f"NSFW message content in file - {UrlContentNSFWResultDetails}"
                                                        print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
                                                        await AddingNewNSFWData(BasedURLToSave, UrlContentNSFWResultDetails)
                                                    else:
                                                        UrlContentNSFWResult = False
                                                        await AddingNewCleanData(BasedURLToSave, "Document file text is clean!")
                                                else:
                                                    UrlContentNSFWResult, UrlContentNSFWResultDetails = await ScanningMedia(URLContentName, UrlContent, BasedURLToSave)
                                        else:
                                            await AddingNewCleanData(BasedURLToSave,"URL link is clean or URL content is not in Emmanuel scannable file formats!")
                                        print("Scan Process Finished!\n\n")
                                        if UrlContentNSFWResult:
                                            await message.delete()
                                            logUserAction += f"\nMessage was deleted for having NSFW URL content {UrlContentNSFWResultDetails}"
                                            try:
                                                await message.author.send(UrlContentNSFWResultDetails)
                                                logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                            except Exception as error:
                                                logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                            await writingLog(logUserAction)
                                            # Advance scan previous message for profanity!
                                            await AdvanceBackTrackMessageScan(message)
                                            if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                                del CURRENTSCANOPERATION[BasedURLToSave]
                                            return
                            else:
                                print(f"URL is invalid with status code: {statuscode}")
                                if URL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                                    await message.delete()
                                    logUserAction += f"\nMessage is deleted for having a discord attachment URL {URL} can not be scanned!"
                                    try:
                                        await message.author.send(f"The Discord Attachment URL <{URL}> is not presigned and can not be scanned! If I can not scan a Discord URL, I will not trust it to be cleaned!")
                                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                    except Exception as error:
                                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(message)
                                    print("Message Content Scan Process Finished!\n\n")
                                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                                        del CURRENTSCANOPERATION[BasedURLToSave]
                                    return
                                else:
                                    logUserAction += f"\nNOTE: URL {URL} from message can not be scanned!"
                    if CURRENTSCANOPERATION.get(BasedURLToSave, ""):
                        del CURRENTSCANOPERATION[BasedURLToSave]

            """Scanning message text content with hyperlink removed"""
            if textContent:
                print(f"Scanning text content with URL already filtered...")
                print(f"Text content: {textContent}")
                scanResult, scanResultDetails = await NSFWscanMessage(textContent)
                if scanResult:
                    await message.delete()
                    logUserAction += f"\nMessage was deleted for having NSFW text content! - {scanResultDetails}"
                    try:
                        await message.author.send(scanResultDetails)
                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                    except Exception as error:
                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                    await writingLog(logUserAction)
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
                    await message.delete()
                    logUserAction += "\nMessage is deleted for having at least 1 attachment with potential directory transversal attack!!"
                    try:
                        await message.author.send(f"Attachment {attachment.filename} hinted a potential ../ attack!")
                        logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                    except Exception as error:
                        logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                    await writingLog(logUserAction)
                    print(f"Attachment: {attachment.filename} contains a ../ pattern, hinted potential directory transversal attack! Terminating Scan Process!\n\n")
                    # Advance scan previous message for profanity!
                    await AdvanceBackTrackMessageScan(message)
                    return

                """Checking attachment content already been scanned"""
                async with Emmanuel.session.get(attachment.url) as response:
                    attachmentContent = await response.read()
                hashedAttachmentContent = hashlib.sha512(attachmentContent).hexdigest()

                """Checking if there is another subroutine scanning the same attachment"""
                if CURRENTSCANOPERATION.get(hashedAttachmentContent, "") == "In Progress":
                    print(f"Attachment {attachment.filename} is currently being scanned by other subroutine!")
                    while True:
                        await asyncio.sleep(0)
                        if not CURRENTSCANOPERATION.get(hashedAttachmentContent, ""):
                            break
                else:
                    CURRENTSCANOPERATION[hashedAttachmentContent] = "In Progress"

                print(f"Attachment SHA512 content: {hashedAttachmentContent}")
                print(f"Checking if attachment content is already in a clean list...")
                if hashedAttachmentContent in CLEANData.keys():
                    print("Attachment content already pass the scan! Terminating Scan Process...\n\n")
                else:
                    print(f"Attachment content is not in the clean data! Checking if the content is in the NSFW data!")
                    if hashedAttachmentContent in NSFWData.keys():
                        await message.delete()
                        logUserAction += f"\nMessage was deleted for having attachment content already flagged NSFW! - {NSFWData[hashedAttachmentContent]}"
                        try:
                            await message.author.send(f"The attachment {attachment.filename} has already flagged NSFW! - {NSFWData[hashedAttachmentContent]}")
                            logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                        except Exception as error:
                            logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                        print("Attachment content already flagged NSFW! Terminating Scan Process...\n\n")
                        await writingLog(logUserAction)
                        # Advance scan previous message for profanity!
                        await AdvanceBackTrackMessageScan(message)
                        print("Scan Process Finished!\n\n")
                        if CURRENTSCANOPERATION.get(hashedAttachmentContent, ""):
                            del CURRENTSCANOPERATION[hashedAttachmentContent]
                        return
                    else:
                        scanContent = True
                        async with ConfigLock:
                            if configuration.get(str(message.guild.id), ""):
                                if configuration[str(message.guild.id)]["User-Uncensor-Limit"].get(str(message.author.id), ""):
                                    if configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)] > 0:
                                        scanContent = False
                                        logUserAction += f"\nUser {message.author.name} ID {message.author.id} uncensor limit is {configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)]} in server {message.guild.name} ID {message.guild.id}\nFile content is not scanned!!!"
                                        print(f"User {message.author.name} ID {message.author.id} uncensor limit is {configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)]} in server {message.guild.name} ID {message.guild.id}\nFile content is not scanned!!!")
                                        configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)] -= 1
                                        async with aiofiles.open(EMMANUELCONFIG, "w") as file:
                                            await file.write(json.dumps(configuration, indent=4))
                        if scanContent:
                            print(f"Attachment is not in NSFW data! Proceeding to scan the attachment...")
                            attachmentFileExt = checkingRealFileExtension(attachmentContent, attachment.filename.lower())
                            FILEDOWNLOADCOUNTER += 1
                            AttachmentFileName = f"{FILEDOWNLOADCOUNTER}{attachmentFileExt}"
                            attachmentNSFWResult = False
                            attachmentNSFWResultDetails = ""
                            print(f"Attachment file extension: {attachmentFileExt}")
                            if attachmentFileExt.endswith(ALLSCANNABLEFILEFORMATS):
                                if attachmentFileExt.endswith(ARCHIVEFORMATS):
                                    attachmentNSFWResult, attachmentNSFWResultDetails = await ArchiveFileScan(AttachmentFileName, attachmentContent , hashedAttachmentContent)
                                elif attachmentFileExt.endswith(DOCUMENTFILES):
                                    print(f"Scanning ASCII text in URL content...")
                                    pdfPath = await asyncio.to_thread(AsciiDocumentToPDFConversion, UrlContent)
                                    attachmentNSFWResultDetails = await scanningPDFPagesWithGPT(pdfPath)
                                    if attachmentNSFWResultDetails.startswith(("Yes", "yes", "YES")):
                                        attachmentNSFWResult = True
                                        attachmentNSFWResultDetails = attachmentNSFWResultDetails.strip("Yes, ")
                                        attachmentNSFWResultDetails = f"NSFW message content in file - {attachmentNSFWResultDetails}"
                                        print(f"Content flagged NSFW by {GPTMODELFORIMAGESCAN}")
                                        await AddingNewNSFWData(hashedAttachmentContent, attachmentNSFWResultDetails)
                                    else:
                                        attachmentNSFWResult = False
                                        await AddingNewCleanData(hashedAttachmentContent, "Document file text is clean!")
                                else:
                                    attachmentNSFWResult, attachmentNSFWResultDetails  = await ScanningMedia(AttachmentFileName, attachmentContent, hashedAttachmentContent)
                            else:
                                await AddingNewCleanData(hashedAttachmentContent,"Attachment content is not in Emmanuel scannable file formats!")
                            print("Scan Process Finished!\n\n")
                            if attachmentNSFWResult:
                                await message.delete()
                                logUserAction += f"\nMessage is deleted for having at least 1 NSFW attachment! - {attachmentNSFWResultDetails}"
                                try:
                                    await message.author.send(attachmentNSFWResultDetails)
                                    logUserAction += f"\nExplanation message was sent to user to inform why the user message was deleted\n\n"
                                except Exception as error:
                                    logUserAction += f"\nError occur while sending message to user: {error}\nEmmanuel can not send message to inform user why the message was deleted!!!\n\n"
                                    await writingLog(logUserAction)
                                    # Advance scan previous message for profanity!
                                    await AdvanceBackTrackMessageScan(message)
                                    if CURRENTSCANOPERATION.get(hashedAttachmentContent, ""):
                                        del CURRENTSCANOPERATION[hashedAttachmentContent]
                                    return

                if CURRENTSCANOPERATION.get(hashedAttachmentContent, ""):
                    del CURRENTSCANOPERATION[hashedAttachmentContent]

        logUserAction += "\nMessage is cleaned!\n\n"
        await writingLog(logUserAction)
        await AdvanceBackTrackMessageScan(message)


Emmanuel.run(DISCORDAPI)
