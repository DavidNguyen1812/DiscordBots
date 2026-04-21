import discord
import discord.ext.commands
import time
import os
import shutil
import json
import mimetypes
import magic
import base64
import random
import wave
import asyncio
import aiofiles
import zipfile
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from PIL import Image
from openai import AsyncOpenAI
from google import genai
from discord import app_commands
from discord.ext import commands, tasks
from google.genai import types
from typing import Literal
from dotenv import load_dotenv
from io import BytesIO
from aiocsv import AsyncWriter

load_dotenv()

"""----Configuration Constants----"""
COMMAND_USAGE = 7 # Daily application command usage
DISCORDAPI = os.environ.get("SAMSONDISCORDAPI")
LOGCOMMANDFILEPATH = os.environ.get("SAMSONLOGPATH")
CONFIGFILEPATH = os.environ.get("SAMSONCONFIGPATH")
GPTANDGEMINILOGUSERMESSAGEFILEPATH = os.environ.get("SAMSONGPTANDGEMINILOGPATH")
GPTAPI = os.environ.get("SAMSONGPTAPI")
LLMUSAGELOGDIR = os.environ.get("SAMSONLLMUSAGELOGDIR")
INSTRUCTION_LISTS = {"Medieval": "You are a medieval warrior name Samson! Please ALWAYS response to the user prompt in medieval style!",
                   "Futuristic": "You are a high tech futuristic machine name Samson! Please ALWAYS response to the user prompt in futuristic style!",
                   "Romantic": "You are a romantic person name Samson! Please ALWAYS response to the user prompt in a romantic style!",
                   "Modern Day": "You are a person from modern day name Samson! Please ALWAYS response to the user prompt in a modern language!",
                   "Military": "You are a battle hardened modern war officer name Samson! Please ALWAYS response to the user prompt in a militaristic language!",
                   "Horror": "You are a scary monster name Samson! Please ALWAYS response to the user prompt in a scary language!",
                   "Fitness Coach": "You are a fitness coach name Samson! Please ALWAYS response to the user prompt like a fitness coach!",
                   "Viking": "You are a Viking name Samson! Please ALWAYS response to the user prompt with Nordic culture!",
                   "Samurai": "You are an honourable Samurai name Samson! Please ALWAYS response to the user prompt according to the Bushido Code!",
                   "Comedian": "You are a comedian name Samson! Please ALWAYS response to the user prompt with some humor!"}
"""
https://developers.openai.com/api/docs/models 
OPENAI GPT INFO:
    - gpt-5.4:
        + Maximum Input Token: 1050000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $2.50 (prompt < 272k token), $5.00 (prompt >= 272k token)
        + Cost per 1 Million Output Token: $15.00 (prompt < 272k token), $22.50 (prompt >= 272k token)
        + Supported Inputs: Text and Image

    - gpt-5.4-pro:
        + Maximum Input Token: 1050000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $30.00 (prompt < 272k token), $60.00 (prompt >= 272k token)
        + Cost per 1 Million Output Token: $180.00 (prompt < 272k token), $270.00 (prompt >= 272k token)
        + Supported Inputs: Text and Image

    - gpt-5.2:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.75
        + Cost per 1 Million Output Token: $14.00
        + Supported Inputs: Text and Image

    - gpt-5.2-pro:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $21
        + Cost per 1 Million Output Token: $168
        + Supported Inputs: Text and Image

    - gpt-5.1:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.25
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text and Image

    - gpt-5:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.25
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text and Image

    - gpt-5-pro:
        + Maximum Input Token: 400000
        + Maximum Output Token: 272000
        + Cost per 1 Million Input Token: $15
        + Cost per 1 Million Output Token: $120
        + Supported Inputs: Text and Image

    - gpt-5-mini:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $0.25
        + Cost per 1 Million Output Token: $2.00
        + Supported Inputs: Text and Image

    - gpt-5-nano:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $0.05
        + Cost per 1 Million Output Token: $0.40
        + Supported Inputs: Text and Image

    - gpt-5.3-codex:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.75
        + Cost per 1 Million Output Token: $14.00
        + Supported Inputs: Text and Image

    - gpt-5.2-codex:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.75
        + Cost per 1 Million Output Token: $14.00
        + Supported Inputs: Text and Image

    - gpt-5.1-codex:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.25
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text and Image

    - gpt-5-codex:
        + Maximum Input Token: 400000
        + Maximum Output Token: 128000
        + Cost per 1 Million Input Token: $1.25
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text and Image

    - gpt-4.1:
        + Maximum Input Token: 1047576
        + Maximum Output Token: 32768
        + Cost per 1 Million Input Token: $2.00
        + Cost per 1 Million Output Token: $8.00
        + Supported Inputs: Text and Image

    - gpt-4.1-mini:
        + Maximum Input Token: 1047576
        + Maximum Output Token: 32768
        + Cost per 1 Million Input Token: $0.40
        + Cost per 1 Million Output Token: $1.60
        + Supported Inputs: Text and Image

    - gpt-4.1-nano:
        + Maximum Input Token: 1047576
        + Maximum Output Token: 32768
        + Cost per 1 Million Input Token: $0.10
        + Cost per 1 Million Output Token: $0.40
        + Supported Inputs: Text and Image

    - gpt-4o:
        + Maximum Input Token: 128000
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $2.50
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text and Image

    - gpt-4o-mini:
        + Maximum Input Token: 128000
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $0.15
        + Cost per 1 Million Output Token: $0.60
        + Supported Inputs: Text and Image

    - gpt-4:
        + Maximum Input Token: 8192
        + Maximum Output Token: 8192
        + Cost per 1 Million Input Token: $30.00
        + Cost per 1 Million Output Token: $60.00
        + Supported Inputs: Text

    - gpt-3.5-turbo-16k:
        + Maximum Input Token: 16385
        + Maximum Output Token: 4096
        + Cost per 1 Million Input Token: $0.50
        + Cost per 1 Million Output Token: $1.50
        + Supported Inputs: Text

    - 04-mini:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $1.10
        + Cost per 1 Million Output Token: $4.40
        + Supported Inputs: Text and Image

    - o3-pro:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $20.00
        + Cost per 1 Million Output Token: $80.00
        + Supported Inputs: Text and Image

    - o3-mini:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $1.10
        + Cost per 1 Million Output Token: $4.40
        + Supported Inputs: Text

    - o3:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $2.00
        + Cost per 1 Million Output Token: $8.00
        + Supported Inputs: Text and Image

    - o1-pro:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $150.00
        + Cost per 1 Million Output Token: $600.00
        + Supported Inputs: Text and Image

    - o1-mini:
        + Maximum Input Token: 128000
        + Maximum Output Token: 65536
        + Cost per 1 Million Input Token: $1.10
        + Cost per 1 Million Output Token: $4.40
        + Supported Inputs: Text

    - o1:
        + Maximum Input Token: 200000
        + Maximum Output Token: 100000
        + Cost per 1 Million Input Token: $15.00
        + Cost per 1 Million Output Token: $60.00
        + Supported Inputs: Text and Image
        
OPENAI GPT AUDIO INFO:
    - gpt-audio:
        + Maximum Input Token: 128000
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $2.50 for text, $32.00 for audio
        + Cost per 1 Million Output Token: $10.00 for text, $64.00 for audio
        + Supported Inputs and Outputs: Text and Audio (Format .wav and .mp3 only)

    - gpt-audio-1.5:
        + Maximum Input Token: 128000
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $2.50 for text, $32.00 for audio
        + Cost per 1 Million Output Token: $10.00 for text, $64.00 for audio
        + Supported Inputs and Outputs: Text and Audio (Format .wav and .mp3 only)

    - gpt-audio-mini:
        + Maximum Input Token: 128000
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $0.60 for both audio and text
        + Cost per 1 Million Output Token: $2.40 for both audio and text
        + Supported Inputs: Text and Audio (Format .wav and .mp3 only)

https://ai.google.dev/gemini-api/docs/pricing
GOOGLE GEMINI INFO:
    - gemini-3.1-pro-preview:
        + Maximum Input Token: 1048576
        + Maximum Output Token: 65536
        + Cost per 1 Million Input Token: $2.00 for prompts <= 200k tokens, $4.00 for prompts > 200k tokens
        + Cost per 1 Million Output Token: $12.00 for prompts <= 200k tokens, $18.00 for prompts > 200k tokens
        + Supported Inputs: Text, Image, Video, Audio, and PDF
        
    - gemini-2.5-pro:
        + Maximum Input Token: 1048576
        + Maximum Output Token: 65536
        + Cost per 1 Million Input Token: $1.25 for prompts <= 200k tokens, $2.50 for prompts > 200k tokens
        + Cost per 1 Million Output Token: $10.00 for prompts <= 200k tokens, $15.00 for prompts > 200k tokens
        + Supported Inputs: Text, Image, Video, Audio, and PDF
        
    - gemini-2.5-flash:
        + Maximum Input Token: 1048576
        + Maximum Output Token: 65536
        + Cost per 1 Million Input Token: $0.30 for (text, image, video), $1.00 for audio
        + Cost per 1 Million Output Token: $2.50
        + Supported Inputs: Text, images, video, audio
        
GOOGLE GEMINI TTS INFO:
    - gemini-2.5-flash-preview-tts:
        + Maximum Input Token: 8192
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $0.50
        + Cost per 1 Million Output Token: $10.00
        + Supported Inputs: Text
        
    - gemini-2.5-pro-preview-tts:
        + Maximum Input Token: 8192
        + Maximum Output Token: 16384
        + Cost per 1 Million Input Token: $1.00
        + Cost per 1 Million Output Token: $20.00
        + Supported Inputs: Text
"""
LLMMODELINFORMATION = {
                        "gemini-2.5-flash":
                            {
                                "Maximum Input Tokens": 1048576,
                                "Cost": {"Input Token": [0.3, 0.3], "Output Token": [2.5, 2.5]}
                            },
                        "gemini-2.5-pro":
                            {
                                "Maximum Input Tokens": 1048576,
                                "Cost": {"Input Token": [1.25, 2.5], "Output Token": [10, 15]}
                             },
                        "gemini-3.1-pro-preview":
                            {
                                "Maximum Input Tokens": 1048576,
                                "Cost": {"Input Token": [2, 4], "Output Token": [12, 18]}
                            },
                        "gpt-5.4":
                            {
                                "Maximum Input Tokens": 1050000,
                                "Cost": {"Input Token": [2.5, 5], "Output Token": [15, 22.5]}
                            },
                        "gpt-5.2":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.75, 1.75], "Output Token": [14, 14]}
                            },
                        "gpt-5.1":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.25, 1.25], "Output Token": [10, 10]}
                            },
                        "gpt-5":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.25, 1.25], "Output Token": [10, 10]}
                            },
                        "gpt-5-mini":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [0.25, 0.25], "Output Token": [2, 2]}
                            },
                        "gpt-5-nano":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [0.05, 0.05], "Output Token": [0.4, 0.4]}
                            },
                        "gpt-5.3-codex":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.75, 1.75], "Output Token": [14, 14]}
                            },
                        "gpt-5.2-codex":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.75, 1.75], "Output Token": [14, 14]}
                            },
                        "gpt-5.1-codex":
                            {
                                "Maximum Input Tokens": 400000,
                                "Cost": {"Input Token": [1.25, 1.25], "Output Token": [10, 10]}
                            },
                        "gpt-4.1":
                            {
                                "Maximum Input Tokens": 1047576,
                                "Cost": {"Input Token": [2, 2], "Output Token": [8, 8]}
                            },
                        "gpt-4.1-mini":
                            {
                                "Maximum Input Tokens": 1047576,
                                "Cost": {"Input Token": [0.4, 0.4], "Output Token": [1.6, 1.6]}
                            },
                        "gpt-4.1-nano":
                            {
                                "Maximum Input Tokens": 1047576,
                                "Cost": {"Input Token": [0.1, 0.1], "Output Token": [0.4, 0.4]}
                            },
                        "gpt-4o":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [2.5, 2.5], "Output Token": [10, 10]}
                            },
                        "gpt-4.0-mini":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [0.15, 0.15], "Output Token": [0.6, 0.6]}
                            },
                        "o4-mini":
                            {
                                "Maximum Input Tokens": 200000,
                                "Cost": {"Input Token": [1.10, 1.10], "Output Token": [4.40, 4.40]}
                            },
                        "o3":
                            {
                                "Maximum Input Tokens": 200000,
                                "Cost": {"Input Token": [2, 2], "Output Token": [8, 8]}
                            },
                        "gemini-2.5-flash-preview-tts":
                            {
                                "Maximum Input Tokens": 8192,
                                "Cost": {"Input Token": [0.5, 0.5], "Output Token": [10, 10]}
                            },
                        "gemini-2.5-pro-preview-tts":
                            {
                                "Maximum Input Tokens": 8192,
                                "Cost": {"Input Token": [1.00, 1.00], "Output Token": [20, 20]}
                            },
                        "gpt-audio":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [2.5, 32], "Output Token": [10, 64]}
                            },
                        "gpt-audio-1.5":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [2.5, 32], "Output Token": [10, 64]}
                            },
                        "gpt-audio-mini":
                            {
                                "Maximum Input Tokens": 128000,
                                "Cost": {"Input Token": [0.6, 0.6], "Output Token": [2.4, 2.4]}
                            }
                       }

LLMModels = ["gemini-2.5-flash",
             "gemini-2.5-pro",
             "gemini-3.1-pro-preview",
             "gpt-5.4",
             "gpt-5.2",
             "gpt-5.1",
             "gpt-5",
             "gpt-5-mini",
             "gpt-5-nano",
             "gpt-5.3-codex",
             "gpt-5.2-codex",
             "gpt-5.1-codex",
             "gpt-4.1",
             "gpt-4.1-mini",
             "gpt-4.1-nano",
             "gpt-4o",
             "gpt-4.0-mini",
             "o4-mini",
             "o3",
             "gemini-2.5-flash-preview-tts",
             "gemini-2.5-pro-preview-tts",
             "gpt-audio",
             "gpt-audio-1.5",
             "gpt-audio-mini"]


"""Initializing Openai and Google Gemini and setting up Discord Intents for Samson"""
GPTclient = AsyncOpenAI(api_key=GPTAPI)
GEMINIclient = genai.Client()
intents = discord.Intents.all()
Samson = commands.Bot(command_prefix='/', intents=intents)

"""Initializing asyncio locks for Thread-Safe File I/O to prevent race conditions"""
ConfigLock = asyncio.Lock()
GPTandGeminiLock = asyncio.Lock()
LogLock = asyncio.Lock()
YearlyCSVLock = asyncio.Lock()
MonthlyCSVLock = asyncio.Lock()

"""Getting Current Time Value"""
currentTime = time.ctime(time.time()).split(" ")
previousMonth = currentTime[1]
previousDate = currentTime[2]
previousYear = currentTime[4]
if not os.path.exists(f"{LLMUSAGELOGDIR}{previousYear}"):
    os.mkdir(f"{LLMUSAGELOGDIR}{previousYear}")
if not os.path.exists(f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}"):
    os.mkdir(f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}")

OWNER_DISCORD_USER_ID = 987765832895594527 # Put your Discord ID here, if you're the owner of the bot

with open(CONFIGFILEPATH, "r") as readFile:
    SamsonConfig = json.load(readFile)


@Samson.event
async def on_ready():
    await Samson.wait_until_ready()
    print(f"Logged in as {Samson.user} (ID: {Samson.user.id})")
    print("Knight Samson is ONLINE!")

    #  Synced all commands -> Add new command if not already existed, else update the pre-existing command
    await Samson.tree.sync()
    SynedCmds = await Samson.tree.fetch_commands()
    for cmd in SynedCmds:
        print(f"Synced command /{cmd.name}")

    print(f"Commands are updated and ready to use!")

    async with ConfigLock:
        for guild in Samson.guilds:
            for member in guild.members:
                if not SamsonConfig.get(str(member.id), ""):
                    SamsonConfig[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval", "Banned Application Commands": []}
                    print(f"Adding user: {member.name} - ID: {member.id} from server: {guild.name} - ID: {guild.id} to Samson Configuration File")
            async with aiofiles.open(CONFIGFILEPATH, "w") as file:
                await file.write(json.dumps(SamsonConfig, indent=4))

    update_user_command_limit_and_llm_usage.start()


def isDMChannel(channel: int) -> bool:
    """
    Description: Checking if the channel from which the application is called is a public server or a DM with Samson
    :param channel: Channel ID
    :return: True, if the channel is a DM, else False
    """
    if str(channel).startswith("Direct Message"):
        return True
    else:
        return False


def calculateUsageCost(model: str, totalInputTokens: int, totalOutputTokens: int, task: Literal["Audio-Prompt-Text-Output", "Text-Prompt-Audio-Output", "General Chat"]) -> float:
   """
   Description: Calculate the usage cost of the LLM model based on the total input tokens and output tokens.
   :param model: LLM Model
   :param totalInputTokens: The total input tokens of a prompt
   :param totalOutputTokens: The total output tokens of a prompt
   :param task: Audio or General Chat
   :return: The final calculated usage cost
   """
   if "gemini" in model:
      tierThresh = 200000
   else:
      tierThresh = 272000

   if "Audio" not in task:
      if totalInputTokens > tierThresh:
         totalCost = (totalInputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Input Token"][1] + (totalOutputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Output Token"][1]
      else:
         totalCost = (totalInputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Input Token"][0] + (totalOutputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Output Token"][0]
   else:
      if task == "Audio-Prompt-Text-Output":
         totalCost = (totalInputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Input Token"][1] + (totalOutputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Output Token"][0]
      else:
         totalCost = (totalInputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Input Token"][0] + (totalOutputTokens / 1000000) * LLMMODELINFORMATION[model]["Cost"]["Output Token"][1]
   return round(totalCost, 4)


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


async def LoggingCommandBeingExecuted(userName: str, command: str) -> None:
    """
    Description: Logging all Samson application commands being called by a server's member
    :param userName:  Member Discord username
    :param command:  The command being called
    :return: None
    """
    async with LogLock:
        async with aiofiles.open(LOGCOMMANDFILEPATH, 'a') as logFile:
            await logFile.write(f"{time.ctime(time.time())}")
            await logFile.write(f"\n{userName} used command {command}\n\n")


async def LoggingGPTandGeminiOutputs(data: str) -> None:
    """
    Description: Logging all OpenAI and Gemini REST API responses
    :param data: The API response from OpenAI or Gemini
    :return: None
    """
    async with GPTandGeminiLock:
        async with aiofiles.open(GPTANDGEMINILOGUSERMESSAGEFILEPATH, 'a') as logFile:
            await logFile.write(data)


async def CheckingUserCurrentCommandUsage(userid: int) -> bool:
    """
    Description: Checking member current command usage to use Samson application commands
    :param userid: Member Discord user ID
    :return: True, if user usage is not 0, else False
    """
    async with ConfigLock:
        if userid == OWNER_DISCORD_USER_ID: # Bot owner has no limit
            return True
        if SamsonConfig[str(userid)]["Current command usage limit"] > 0:
            SamsonConfig[str(userid)]["Current command usage limit"] -= 1
            async with aiofiles.open(CONFIGFILEPATH, "w") as file:
                await file.write(json.dumps(SamsonConfig, indent=4))
            return True
        return False


async def gpt_text_and_picture_inputs_only(userPrompt: str, userName: str, model: str, instructions: str, fileUpload: list=None) -> str:
    """
    Description: REST API call to OpenAI model for chat and picture prompt
    :param userPrompt: User's prompt
    :param userName: User's Discord username
    :param model: OpenAI model being requested to answer the prompt
    :param instructions: System instructions
    :param fileUpload: None, if no file is being uploaded, else the content/path of the file
    :return: API response from OpenAI model
    """
    logMessage = f"{time.ctime(time.time())}"
    if fileUpload is None:
        logMessage += f"\n{userName}: {userPrompt}\nUser instructions: {instructions}"
        totalInputToken = (await GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=userPrompt)).input_tokens
    else:
        if fileUpload[1] == "IMAGE":
            logMessage += f"\n{userName}: {userPrompt}\nUser instructions: {instructions}\nUser attached an image!"
            totalInputToken = (await GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=[
                {"role": "user",
                 "content": [{"type": "input_text", "text": userPrompt},
                            {"type": "input_image", "image_url": f"data:image/png;base64,{fileUpload[0]}"},
                        ],
                    }
                ])).input_tokens
        else:
            logMessage += f"\n{userName}: {userPrompt}\nUser instructions: {instructions}\nUser attached a PDF file!"
            async with aiofiles.open(fileUpload[0], "rb") as PDFfile: # No need to add async lock, since the file path is unique
                fileID = (await GPTclient.files.create(file=await PDFfile.read(), purpose="user_data")).id
            os.remove(fileUpload[0])
            totalInputToken = (await GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": userPrompt},
                            {"type": "input_file", "file_id": fileID}
                        ]
                    }
                ])).input_tokens

    logMessage += f"\nTotal Input Tokens: {totalInputToken} tokens"
    if totalInputToken > LLMMODELINFORMATION[model]["Maximum Input Tokens"]:
        if not fileUpload:
            if fileUpload[1] != "IMAGE":
                await GPTclient.files.delete(fileID)
        logMessage += f"\nTotal input tokens exceeding model {model} input token limit of {LLMMODELINFORMATION[model]["Maximum Input Tokens"]} tokens!\n\n"
        await LoggingGPTandGeminiOutputs(logMessage)
        return f"YOUR PROMPT TOTAL TOKENS -> {totalInputToken} TOKENS EXCEEDING THE MODEL {model} INPUT TOKEN LIMIT OF {LLMMODELINFORMATION[model]["Maximum Input Tokens"]} TOKENS!"
    else:
        if fileUpload is None:
            response = await GPTclient.responses.create(
                model=model,
                instructions=instructions,
                input=userPrompt,
            )
        else:
            if fileUpload[1] == "IMAGE":
                response = await GPTclient.responses.create(
                    model=model,
                    instructions=instructions,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": userPrompt},
                                {"type": "input_image", "image_url": f"data:image/png;base64,{fileUpload[0]}"},
                            ],
                        }
                    ]
                )
            else:
                response = await GPTclient.responses.create(
                    model=model,
                    instructions=instructions,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": userPrompt},
                                {"type": "input_file", "file_id": fileID}
                            ]
                        }
                    ]
                )
                await GPTclient.files.delete(fileID)


        reply = response.output_text
        totalOutputTokenCount = response.usage.total_tokens - response.usage.input_tokens
        logMessage += f"\nOpenAI {model}: {reply}\nTotal Output Tokens: {totalOutputTokenCount} tokens\n\n"
        await LoggingGPTandGeminiOutputs(logMessage)
        cMonth = time.ctime(time.time()).split(' ')[1]
        cDay = time.ctime(time.time()).split(' ')[2]
        totalCost = calculateUsageCost(model, totalInputToken, totalOutputTokenCount, "General Chat")
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a", [f"{cMonth} {cDay}", totalInputToken, totalOutputTokenCount, model, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a", [f"{cMonth} {cDay}", totalInputToken, totalOutputTokenCount, model, totalCost], YearlyCSVLock)
        return reply


async def gemini_text_and_picture_and_audio_only(userInput: str, userName: str, model: str, fileUpload:str =None, audio: bool=None) -> str:
    """
    Description: REST API call to Gemini model for chat, picture,and audio prompt
    :param userInput: User's prompt
    :param userName: User's Discord username
    :param model: Gemini model being requested to answer the prompt
    :param fileUpload: None, if no file is being uploaded, else the path of the file
    :param audio: None, if the prompt task is not for any audio-related
    :return: API response from Gemini model
    """
    logMessage = f"{time.ctime(time.time())}\n{userName}: {userInput}"
    if fileUpload is not None:
        if fileUpload.endswith(".pdf"):
            logMessage += f"\nUser attached a PDF file!"
        else:
            logMessage += f"\nUser attached an image file!"
        uploadedFile = await GEMINIclient.aio.files.upload(file=fileUpload)
        prompt = [uploadedFile, userInput]
        os.remove(fileUpload)
    else:
        prompt = userInput
    totalInputTokenCount = (await GEMINIclient.aio.models.count_tokens(model=model, contents=prompt)).total_tokens
    logMessage += f"\nTotal Input Tokens: {totalInputTokenCount} tokens"
    if totalInputTokenCount > LLMMODELINFORMATION[model]["Maximum Input Tokens"]:
        logMessage += f"\nTotal input tokens exceeding model {model }input token limit of {LLMMODELINFORMATION[model]["Maximum Input Tokens"]} tokens!\n\n"
        await LoggingGPTandGeminiOutputs(logMessage)
        return f"YOUR PROMPT TOTAL TOKENS -> {totalInputTokenCount} TOKENS EXCEEDING THE MODEL {model} INPUT TOKEN LIMIT OF {LLMMODELINFORMATION[model]["Maximum Input Tokens"]} TOKENS!"
    else:
        if audio is None:
            response = await GEMINIclient.aio.models.generate_content(model=model, contents=prompt)
        else:
            response = await GEMINIclient.aio.models.generate_content(
                model=model,
                contents=userInput,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name='Algenib',
                            )
                        )
                    ),
                )
            )
            data = response.candidates[0].content.parts[0].inline_data.data
            with wave.open("SamsonResponse.wav", "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(data)
        reply = response.text
        totalOutputTokenCount = response.usage_metadata.total_token_count - totalInputTokenCount
        cMonth = time.ctime(time.time()).split(' ')[1]
        cDay = time.ctime(time.time()).split(' ')[2]
        totalCost = calculateUsageCost(model, totalInputTokenCount, totalOutputTokenCount, "General Chat")
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a", [f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a", [f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], YearlyCSVLock)
        logMessage += f"\nGemini {model}: {reply}\nTotal Output Tokens: {totalOutputTokenCount} tokens\n\n"
        await LoggingGPTandGeminiOutputs(logMessage)
        return reply


async def gpt_text_and_audio_only(userInput: list, userName: str, model: str, instructions: str, option: str) -> str|bytes:
    """
    Description: REST API call to OpenAI model for audio and text prompt
    :param userInput: User's prompt consisting of text and/or audio file
    :param userName: User's Discord username
    :param model: OpenAI audio model being requested to answer the prompt
    :param instructions: System instructions
    :param option: Specified whether to output a text or audio
    :return: API response from OpenAI model in a list contains audio data and text
    """
    logMessage = f"{time.ctime(time.time())}"
    if option == "text-output":
        logMessage += f"\n{userName}: {userInput[0]}\nUser attached an audio file!"
        reply = await GPTclient.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": userInput[0]},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": userInput[1],
                                "format": userInput[2]
                            }
                        }
                    ]
                }
            ]
        )
        logMessage += f"\nTotal Input Tokens: {reply.usage.prompt_tokens} tokens\nChatGPT {model}: {reply.choices[0].message.content}\nTotal Output Tokens: {reply.usage.total_tokens - reply.usage.prompt_tokens} tokens\n\n"
        totalInputTokenCount = reply.usage.prompt_tokens
        totalOutputTokenCount = reply.usage.total_tokens - reply.usage.prompt_tokens
        cMonth = time.ctime(time.time()).split(' ')[1]
        cDay = time.ctime(time.time()).split(' ')[2]
        totalCost = calculateUsageCost(model, totalInputTokenCount, totalOutputTokenCount, "Audio-Prompt-Text-Output")
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a",[f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a", [f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], YearlyCSVLock)
        await LoggingGPTandGeminiOutputs(logMessage)
        return reply.choices[0].message.content
    else:
        logMessage += f"\n{userName}: {userInput[0]}"
        reply = await GPTclient.chat.completions.create(
            model=model,
            modalities=['text', 'audio'],
            audio={"voice": "onyx", "format": "wav"},
            messages=[
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": userInput[0]
                         }
                    ]
                }
            ]
        )
        logMessage += f"\nTotal Input Tokens: {reply.usage.prompt_tokens} tokens\nChatGPT {model}: {reply.choices[0].message.audio.transcript}\nTotal Output Tokens: {reply.usage.total_tokens - reply.usage.prompt_tokens} tokens\n\n"
        totalInputTokenCount = reply.usage.prompt_tokens
        totalOutputTokenCount = reply.usage.total_tokens - reply.usage.prompt_tokens
        cMonth = time.ctime(time.time()).split(' ')[1]
        cDay = time.ctime(time.time()).split(' ')[2]
        totalCost = calculateUsageCost(model, totalInputTokenCount, totalOutputTokenCount, "Text-Prompt-Audio-Output")
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "a",[f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], MonthlyCSVLock)
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "a",[f"{cMonth} {cDay}", totalInputTokenCount, totalOutputTokenCount, model, totalCost], YearlyCSVLock)
        await LoggingGPTandGeminiOutputs(logMessage)
        return reply.choices[0].message.audio.data


@tasks.loop(hours=24)  # A task every 24 hours
async def update_user_command_limit_and_llm_usage():
    global previousDate, previousMonth, previousYear

    async with ConfigLock:
        for userId in SamsonConfig:
            SamsonConfig[userId]["Current command usage limit"] = COMMAND_USAGE
        async with aiofiles.open(CONFIGFILEPATH, "w") as file:
            await file.write(json.dumps(SamsonConfig, indent=4))

    currentTime = time.ctime(time.time()).split(" ")

    # Checking new year
    if currentTime[4] != previousYear:
        print(f"New Year Change: {previousYear} -> {currentTime[4]}")
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
        plotBarCharts(datasets, months, "LLM Usage - End of Year Overview", f"{LLMUSAGELOGDIR}{previousYear}/FullYearUsageReport.png")
        print(f"Successfully Generating LLM Usage Yearly Report!")

        print(f"Resetting LLMYearlyUsage.csv...")
        await writingLLMUsageCsv("{LLMUSAGELOGDIR}LLMYearlyUsage.csv", "w",["Date", "Total Input Tokens", "Total Output Tokens", "LLM Models", "Total Cost"], YearlyCSVLock)
        print(f"Successfully resetting LLMYearlyUsage.csv!")

        os.mkdir(f"{LLMUSAGELOGDIR}{currentTime[4]}")
        print(f"Successfully create a new year folder!")
        previousYear = currentTime[4]

    # Checking new date
    if currentTime[2] != previousDate:
        print(f"New Day of the Month Change: {previousMonth} {previousDate} -> {currentTime[1]} {currentTime[2]}")
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
        plotBarCharts(datasets, dates, "LLM Usage - Monthly Overview", f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}/LLMMonthlyUsageReport.png")
        print(f"Successfully Updating LLMMonthlyUsageReport.png!")

        print(f"Updating LLMModelsUsed.png...")
        LLMModelUses = [0 for _ in range(len(LLMModels))]
        for _, row in monthlyData.iterrows():
            LLMModelUses[LLMModels.index(row["LLM Models"])] += 1
        plotModelCalls(LLMModelUses, f"{LLMUSAGELOGDIR}{previousYear}/{previousMonth}/LLMModelsUsed.png")
        print(f"Successfully Updating LLMModelsUsed.png!")
        previousDate = currentTime[2]

    # Checking new month
    if currentTime[1] != previousMonth:
        print(f"New Month Change: {previousMonth} -> {currentTime[1]}")
        print(f"Resetting LLMMonthlyUsage.csv...")
        await writingLLMUsageCsv(f"{LLMUSAGELOGDIR}LLMMonthlyUsage.csv", "w", ["Date", "Total Input Tokens", "Total Output Tokens", "LLM Models", "Total Cost"], MonthlyCSVLock)
        print(f"Successfully resetting LLMMonthlyUsage.csv!")
        print(f"Creating a new month folder...")
        os.mkdir(f"{LLMUSAGELOGDIR}{currentTime[4]}/{currentTime[1]}")
        print(f"Successfully create a new month folder!")
        previousMonth = currentTime[1]


# Command for Bot Owner ONLY!
@Samson.tree.command(
    name="add_command",
    description="Adding additional command usage to a mentioned user in the server. Bot Owner Only Command!!!"
)
@app_commands.describe(
    username="Mention a user in the server, e.g., @user123",
    value="How many command usage value to be added?"
)
async def add_command(ctx, username: discord.User, value: int):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == OWNER_DISCORD_USER_ID:

        async with ConfigLock:
            SamsonConfig[str(username.id)]["Current command usage limit"] += value

            async with aiofiles.open(CONFIGFILEPATH, "w") as file:
                await file.write(json.dumps(SamsonConfig, indent=4))

        await LoggingCommandBeingExecuted(ctx.user.name, f"/add_command {username} {value}\nCommand Status: Approved")
        await ctx.followup.send("Command Successfully Executed!")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name, f"/add_command {username} {value}\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by the owner of this bot!")


# Command for Bot Owner ONLY!
@Samson.tree.command(
    name="get_user_list_of_permissions",
    description="Get the permissions granted to a mentioned user in the server. Bot Owner Only Command!!!"
)
@app_commands.describe(member="Mention a user in the server, e.g., @user123")
async def get_user_list_of_permissions(ctx, member: discord.User):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == OWNER_DISCORD_USER_ID:
        if not isDMChannel(ctx.channel):
            memberPermissions = member.guild_permissions
            permissionList = []
            for permission, status in iter(memberPermissions):
                permissionList.append(f"{permission.replace("_", " ").upper()}: {status}")
            await ctx.followup.send(f"Permissions for '{member.name}' from Server '{ctx.channel.guild.name}':\n" + "\n".join(permissionList))
            await LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Approved")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("Command can not work in DM channel")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by the owner of this bot!")


# Command for Bot Owner ONLY!
@Samson.tree.command(
    name="application_command_config",
    description="Permanently Ban or Unban a member from the server to use certain application command!"
)
@app_commands.describe(
    action="Ban or unban a member from the server to use certain application command",
    member="Mention a user in the server, e.g., @user123",
    application_command="What application command from the list to be banned?"
)
async def application_command_config(ctx, action: Literal["BAN", "UNBAN"], member: discord.User, application_command: Literal["/samson", "/clear_last_message", "/clear_all_message", "/clear_user_message", "/react", "/direct_message", "/customized_gif_generator", "/openai_gpt_chat", "/google_gemini_chat", "/openai_gpt_audio", "/google_gemini_audio"]):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == OWNER_DISCORD_USER_ID:
        if not isDMChannel(ctx.channel):
            async with ConfigLock:
                if SamsonConfig.get(str(member.id), ""):
                    if action == "BAN":
                        if application_command in SamsonConfig[str(member.id)]["Banned Application Commands"]:
                            await ctx.followup.send(f"User {member.name} has already been permanently banned from using {application_command}!")
                        else:
                            SamsonConfig[str(member.id)]["Banned Application Commands"].append(application_command)
                            await ctx.followup.send(f"User {member.name} is permanently banned from using {application_command}!")
                            try:
                                await member.send(f"You have been banned from using {application_command} by my owner!")
                            except Exception:
                                pass
                    else:
                        if application_command not in SamsonConfig[str(member.id)]["Banned Application Commands"]:
                            await ctx.followup.send(f"User {member.name} has already been unbanned and allowed to use {application_command}!")
                        else:
                            SamsonConfig[str(member.id)]["Banned Application Commands"].remove(application_command)
                            await ctx.followup.send(f"User {member.name} is unbanned and allowed to use {application_command}!")
                            try:
                                await member.send(f"You have been unbanned from using {application_command} by my owner!")
                            except Exception:
                                pass
                else:
                    if action == "BAN":
                        SamsonConfig[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval", "Banned Application Commands": [application_command]}
                        await ctx.followup.send(f"User {member.name} is permanently banned from using {application_command}!")
                        try:
                            await member.send(f"You have been banned from using {application_command} by my owner!")
                        except Exception:
                            pass
                    else:
                        SamsonConfig[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval", "Banned Application Commands": []}
                        await ctx.followup.send(f"User {member.name} is unbanned and allowed to use {application_command}!")
                async with aiofiles.open(CONFIGFILEPATH, "w") as file:
                    await file.write(json.dumps(SamsonConfig, indent=4))
                await LoggingCommandBeingExecuted(ctx.user.name,f"/application_command_config {action} {member} {application_command}\nCommand Status: Approved")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name, f"/application_command_config {action} {member} {application_command}\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("Command can not work in DM channel")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name,f"/application_command_config {action} {member} {application_command}\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by the owner of this bot!")


# Command for Bot Owner ONLY!
@Samson.tree.command(
    name="view_application_command_config",
    description="Viewing Samson current application command configuration"
)
async def view_application_command_config(ctx):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == OWNER_DISCORD_USER_ID:
        if not isDMChannel(ctx.channel):
            async with ConfigLock:
                report = ""
                for member in ctx.guild.members:
                    report += f"User {member.name} -ID {member.id} is permanently banned from using the following application commands:\n"
                    if SamsonConfig.get(str(member.id), ""):
                        for applicationCommand in SamsonConfig[str(member.id)]["Banned Application Commands"]:
                            report += f"{applicationCommand}\n"
                        report += "\n\n"
                    else:
                        SamsonConfig[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval", "Banned Application Commands": []}
                if len(report) > 1500:
                    buffer = BytesIO()
                    buffer.write(report.encode('utf-8'))
                    buffer.seek(0)
                    replyFile = discord.File(fp=buffer, filename="applicationCommandConfig.txt")
                    await ctx.followup.send("", file=replyFile)
                else:
                    await ctx.followup.send(report)
                async with aiofiles.open(CONFIGFILEPATH, "w") as file:
                    await file.write(json.dumps(SamsonConfig, indent=4))
                await LoggingCommandBeingExecuted(ctx.user.name,f"/view_application_command_config\nCommand Status: Approved")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name,f"/view_application_command_config\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("Command can not work in DM channel")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name,f"/view_application_command_config\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by the owner of this bot!")


@Samson.tree.command(
    name="samson",
    description="Get Information about Knight Samson."
)
async def samson(ctx):
    await ctx.response.defer(ephemeral=True)
    if not isDMChannel(ctx.channel):
        if "/samson" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                await LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Approved")
                await ctx.followup.send(
                    "I am a knight designed by Sir David Nguyen with ChatGPT and Google Gemini REST API to interact with user through Direct "
                    "Message or in a Server. I have certain commands ONLY WORK in a SERVER CHANNEL. All commands can "
                    f"only be used {COMMAND_USAGE} times daily!\n"
                    "Command List:\n"
                    "/samson\n"
                    "/roleplay\n"
                    "/openai_gpt_chat\n"
                    "/google_gemini_chat\n"
                    "/openai_gpt_audio\n"
                    "/google_gemini_audio\n"
                    "/clear_last_message\n"
                    "/clear_all_message\n"
                    "/clear_user_message\n"
                    "/direct_message\n"
                    "/customized_gif_generator\n"
                    "/clear_samson_dm_messages")
            else:
                await LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name,"/samson\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="roleplay",
    description="Configuring Knight Samson to roleplay a specific personality"
)
@app_commands.describe(role="Select a role for Samson to role play")
async def roleplay(ctx, role: Literal["Medieval", "Futuristic", "Romantic", "Modern Day", "Military", "Horror", "Fitness Coach", "Viking", "Samurai", "Comedian"]):
    await ctx.response.defer(ephemeral=True)
    async with ConfigLock:
        if SamsonConfig[str(ctx.user.id)]["Samson Roleplay"] == role:
            await ctx.followup.send(f"I'm already configured to role play as {role}")
            await LoggingCommandBeingExecuted(ctx.user.name,f"/roleplay {role}\nCommand Status: Denied/Samson already configured to the selected roleplay!")
        else:
            SamsonConfig[str(ctx.user.id)]["Samson Roleplay"] = role
            reply = gpt_text_and_picture_inputs_only("Introduce yourself", ctx.user.name, "gpt-5.4", INSTRUCTION_LISTS[role])
            await ctx.followup.send(reply)
            await LoggingCommandBeingExecuted(ctx.user.name, f"/roleplay {role}\nCommand Status: Approved")
        async with aiofiles.open(CONFIGFILEPATH, "w") as file:
            await file.write(json.dumps(SamsonConfig, indent=4))


@Samson.tree.command(
    name="openai_gpt_chat",
    description="Interacting with OpenAI GPT chat models"
)
@app_commands.describe(message="Input your prompt",
                       model="Please select the model listed above",
                       keep_secret="Select Yes if you want the output only visible between you and me!",
                       file_attachment="(OPTIONAL) Please Upload only PNG, JPG, or PDF files!")
async def openai_gpt_chat(ctx, message: str,
                  model: Literal["gpt-5.4", "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5.3-codex", "gpt-5.2-codex", "gpt-5.1-codex", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4.0-mini", "o4-mini", "o3"],
                  keep_secret: Literal["Yes", "No"],
                  file_attachment: discord.Attachment = None):
    instruction = INSTRUCTION_LISTS[SamsonConfig[str(ctx.user.id)]["Samson Roleplay"]]
    if not isDMChannel(ctx.channel):
        if "/openai_gpt_chat" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                if keep_secret == "Yes":
                    await ctx.response.defer(ephemeral=True)
                else:
                    await ctx.response.defer()
                if file_attachment is not None:
                    fileContent = await file_attachment.read()
                    mime = magic.from_buffer(fileContent, mime=True)
                    fileExt = mimetypes.guess_extension(mime)
                    if not fileExt.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                        await ctx.followup.send("Please upload your file attachments in PNG, JPG, or PDF format!")
                        await LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/Unaccepted File Format!")
                        return
                    if fileExt.endswith(".pdf"):
                        filePath = f"./{random.randint(0,9999)}.pdf"
                        async with aiofiles.open(filePath, "wb") as PDFfile:
                            await PDFfile.write(fileContent)
                        fileContent = [filePath, "PDF"]
                    else:
                        fileContent = [base64.b64encode(fileContent).decode("utf-8"), "IMAGE"]
                    reply = await gpt_text_and_picture_inputs_only(message, ctx.user.name, model, instruction, fileContent)
                else:
                    reply = await gpt_text_and_picture_inputs_only(message, ctx.user.name, model, instruction)
                if len(reply) > 1500:
                    buffer = BytesIO()
                    buffer.write(reply.encode('utf-8'))
                    buffer.seek(0)
                    replyFile = discord.File(fp=buffer, filename="reply.txt")
                    await ctx.followup.send("", file=replyFile)
                else:
                    await ctx.followup.send(reply)
                await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Approved")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="google_gemini_chat",
    description="Interacting with Google Gemini chat models"
)
@app_commands.describe(message="Input your prompt",
                       model="Please select the model listed above",
                       keep_secret="Select Yes if you want the output only visible between you and me!",
                       file_attachment="(OPTIONAL) Please Upload only PNG, JPG, or PDF files!"
)
async def google_gemini_chat(ctx, message: str,
                        model: Literal["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-pro-preview"],
                        keep_secret: Literal["Yes", "No"],
                        file_attachment: discord.Attachment = None):

    if not isDMChannel(ctx.channel):
        if "/google_gemini_chat" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                if keep_secret == "Yes":
                    await ctx.response.defer(ephemeral=True)
                else:
                    await ctx.response.defer()
                if file_attachment is not None:
                    fileContent = await file_attachment.read()
                    mime = magic.from_buffer(fileContent, mime=True)
                    fileExt = mimetypes.guess_extension(mime)
                    if not fileExt.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                        await ctx.followup.send("Please upload your file attachments in PNG, JPG, or PDF format!")
                        await LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/Unaccepted File Format!")
                        return
                    filePath = f"./{random.randint(0, 999999)}{fileExt}"
                    async with aiofiles.open(filePath, "wb") as file:
                        await file.write(fileContent)
                    reply = await gemini_text_and_picture_and_audio_only(f"{message}\n{INSTRUCTION_LISTS[SamsonConfig[str(ctx.user.id)]["Samson Roleplay"]]}", ctx.user.name, model, filePath)
                else:
                    reply = await gemini_text_and_picture_and_audio_only(f"{message}\n{INSTRUCTION_LISTS[SamsonConfig[str(ctx.user.id)]["Samson Roleplay"]]}", ctx.user.name, model)
                if len(reply) > 1500:
                    buffer = BytesIO()
                    buffer.write(reply.encode('utf-8'))
                    buffer.seek(0)
                    replyFile = discord.File(fp=buffer, filename="reply.txt")
                    await ctx.followup.send("", file=replyFile)
                else:
                    await ctx.followup.send(reply)
                await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Approved")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="openai_gpt_audio",
    description="Interacting with OpenAI GPT audio models"
)
@app_commands.describe(message="Input your prompt",
                       model="Please select the model listed above",
                       keep_secret="Select Yes if you want the output only visible between you and me!",
                       input_options="Please select the following options",
                       file_attachment="(OPTIONAL) Please Upload Only audio with .wav or .mp3 formats"
                       )
async def openai_gpt_audio(ctx, message: str,
                             model: Literal["gpt-audio", "gpt-audio-1.5", "gpt-audio-mini"],
                             keep_secret: Literal["Yes", "No"],
                             input_options: Literal["Audio and Prompt Inputs ONLY", "Prompt Input ONLY"],
                             file_attachment: discord.Attachment = None):

    if not isDMChannel(ctx.channel):
        if "/openai_gpt_audio" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                if keep_secret == "Yes":
                    await ctx.response.defer(ephemeral=True)
                else:
                    await ctx.response.defer()
                if input_options.startswith("Audio and Prompt Inputs ONLY"):
                    if file_attachment is None:
                        await ctx.followup.send("Please upload your an audio input in WAV or MP3 format!")
                        await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/User did not provide audio input!")
                        return
                    else:
                        fileContent = await file_attachment.read()
                        mime = magic.from_buffer(fileContent, mime=True)
                        fileExt = mimetypes.guess_extension(mime)
                        if not fileExt.endswith((".wav", ".mp3")):
                            await ctx.followup.send("Please upload your audio attachment in WAV or MP3 format!")
                            await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/Unaccepted File Format!")
                            return
                        reply = await gpt_text_and_audio_only([message, base64.b64encode(fileContent).decode("utf-8"), fileExt.replace(".", "")], ctx.user.name, model, INSTRUCTION_LISTS[SamsonConfig[str(ctx.user.id)]["Samson Roleplay"]], "text-output")
                        if len(reply) > 1500:
                            buffer = BytesIO()
                            buffer.write(reply.encode('utf-8'))
                            buffer.seek(0)
                            replyFile = discord.File(fp=buffer, filename="reply.txt")
                            await ctx.followup.send("", file=replyFile)
                        else:
                            await ctx.followup.send(reply)
                else:
                    result = await gpt_text_and_audio_only([message], ctx.user.name, model, INSTRUCTION_LISTS[SamsonConfig[str(ctx.user.id)]["Samson Roleplay"]], "audio-output")
                    audioFile = discord.File(fp=BytesIO(base64.b64decode(result)), filename="SamsonResponse.wav")
                    await ctx.followup.send("", file=audioFile)
                await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Approved")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="google_gemini_audio",
    description="Interacting with Google Gemini audio models"
)
@app_commands.describe(message="Input your prompt",
                       model="Please select the model listed above",
                       keep_secret="Select Yes if you want the output only visible between you and me!"
                       )
async def google_gemini_audio(ctx, message: str,
                             model: Literal["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"],
                             keep_secret: Literal["Yes", "No"]):

    if not isDMChannel(ctx.channel):
        if "/google_gemini_audio" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                if keep_secret == "Yes":
                    await ctx.response.defer(ephemeral=True)
                else:
                    await ctx.response.defer()
                await gemini_text_and_picture_and_audio_only(message, ctx.user.name, model, audio=True)
                async with asyncio.Lock():
                    AudioFile = discord.File(fp="SamsonResponse.wav", filename="SamsonResponse.wav")
                    await ctx.followup.send("", file=AudioFile)
                    os.remove(f"SamsonResponse.wav")
                await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Approved")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_last_message",
    description="Delete the last specified number of messages."
)
@app_commands.describe(messagenum="How many previous message you want to delete?")
async def clear_last_message(ctx, messagenum: int):
    await ctx.response.defer(ephemeral=True)
    if not isDMChannel(ctx.channel):
        if "/clear_last_message" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                await ctx.response.defer()
                await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Approved")
                await ctx.followup.send("Command Successfully Executed!")
            else:
                await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name,f"/clear_last_message {messagenum}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_all_message",
    description="Delete all messages."
)
async def clear_all_message(ctx):
    if not isDMChannel(ctx.channel):
        if "/clear_all_message" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                await ctx.response.defer()
                async for message in ctx.channel.history():  # Fetch message history
                    await message.delete()
                await LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Approved")
                return
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_all_message\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_user_message",
    description="Delete the last specified number of messages originated from the mentioned user."
)
@app_commands.describe(
    user="Mention a user in the server, e.g., @user123",
    messagenum="How many previous message you want to delete?"
)
async def clear_user_message(ctx, user: discord.User, messagenum: int):
    if not isDMChannel(ctx.channel):
        if "/clear_user_message" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                await ctx.response.defer()
                counter = 0
                async for message in ctx.channel.history():  # Fetch message history
                    if message.author.name == user.name:
                        await message.delete()
                        counter += 1
                    if counter == messagenum:
                        break
                await ctx.followup.send(f"Last {messagenum} messages from {user.name} has been deleted!")
                await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Approved")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/clear_user_message {user}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="direct_message",
    description="Tell Knight Samson to be a messenger to send a message to a mentioned user."
)
@app_commands.describe(
    member="Mention a user in the server, e.g., @user123",
    message="Your message to be delivered by Knight Samson."
)
async def direct_message(ctx, member: discord.User, message: str):
    await ctx.response.defer(ephemeral=True)
    if not isDMChannel(ctx.channel):
        if "/direct_message" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                try:
                    await member.send(f"User {ctx.user.name} want me to send you message:\n{message}")
                    await ctx.followup.send(f"Message is delivered!")
                    await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Approved")
                except discord.Forbidden:
                    await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/User disabled DM with Samson")
                    await ctx.followup.send(f"I can't DM {member.name}. User might have DMs disabled.")
                except Exception as e:
                    await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/Error {e}")
                    await ctx.followup.send(f"An error occurred: {e}")
            else:
                await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/User reached daily usage limit")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="customized_gif_generator",
    description="Creating gif from the gif frames in a zip file. The zip uncompressed size must be <= 1GB"
)
@app_commands.describe(
    zip_file="Please make sure the gif frames in the zip file is in PNG formats frame1.png, frame2.png, ..etc..",
    gif_name="Give a cool name for your gif",
    frame_rate="Provide the frame rate for your gif in millisecond"
)
async def customized_gif_generator(ctx, zip_file: discord.Attachment, gif_name: str, frame_rate: int):
    gif_name = gif_name.replace(' ', '').replace('.', '').replace('/', '')
    if gif_name == "":
        gif_name = "YourGif"
    def SafePngExtraction(zippath, gifdirectory):
        uncompressedSize = os.path.getsize(zippath)
        with zipfile.ZipFile(zippath, 'r') as zipRef:
            for entry in zipRef.infolist():
                DestinationPath = os.path.abspath(os.path.join(gifdirectory, entry.filename))
                if not DestinationPath.startswith(os.path.abspath(gifdirectory)):
                    shutil.rmtree(gifdirectory)
                    return "Error 1"
                if DestinationPath.endswith(".png") and not os.path.basename(DestinationPath).startswith("._"):
                    try:
                        with zipRef.open(entry, 'r') as source:
                            if source is None:
                                continue
                            fileData = b''
                            while True:
                                Datachunk = source.read(10 ** 6)
                                if not Datachunk:
                                    break
                                fileData += Datachunk
                                uncompressedSize += len(Datachunk)
                                if uncompressedSize >= 10 ** 9:
                                    shutil.rmtree(gifdirectory)
                                    return f"Error 2:{uncompressedSize}"
                            with open(DestinationPath, 'wb') as f:
                                f.write(fileData)
                    except TypeError:
                        pass
        os.remove(zippath)
        if os.listdir(gifdirectory):
            GifFrames = []
            for dirpath, _, filenames in os.walk(gifdirectory):
                for filename in filenames:
                    framepath = os.path.join(dirpath, filename)
                    GifFrames.append(framepath)
            GifFrames.sort()
            NewResizeFrames = []
            for frame in GifFrames:
                img = Image.open(frame)
                img = img.convert("RGBA")
                resized = img.resize(size=(int(img.width * 0.15), int(img.height * 0.15)))
                NewResizeFrames.append(resized)

            NewResizeFrames[0].save(
                f'{gifdirectory}/{gif_name}.gif',
                save_all=True,
                append_images=NewResizeFrames[1:],
                optimize=True,
                duration=frame_rate,
                loop=0,
                disposal=2
            )
            return "Success"
        else:
            shutil.rmtree(gifdirectory)
            return "Error 3"


    if not isDMChannel(ctx.channel):
        if "/customized_gif_generator" not in SamsonConfig[str(ctx.user.id)]["Banned Application Commands"]:
            if await CheckingUserCurrentCommandUsage(ctx.user.id):
                await ctx.response.defer()
                zipContent = await zip_file.read()
                if zipContent.startswith(b'PK\x03\x04'):
                    GifDirectory = str(random.randint(0, 9999))
                    os.mkdir(GifDirectory)
                    zipPath = f"./{GifDirectory}/{str(random.randint(0, 9999))}"
                    async with aiofiles.open(zipPath, "wb") as data:
                        await data.write(zipContent)
                    statusCode = await asyncio.to_thread(SafePngExtraction, zipPath, GifDirectory)
                    if statusCode.startswith("Error 1"):
                        await LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment can cause ../ attack")
                        await ctx.followup.send("Your zip file contains uncompressed content hinted directory transversal attack!")
                    elif statusCode.startswith("Error 2"):
                        await LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment uncompressed size exceeds 1GB")
                        await ctx.followup.send(f"Your zip file uncompressed size of {statusCode.split(':')[-1]} bytes exceeds 1GB")
                    elif statusCode.startswith("Error 3"):
                        await ctx.followup.send(f"There is no PNG frames in the zip file!")
                        await LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment does not have any PNG frames!")
                    else:
                        GifFile = discord.File(fp=f'{GifDirectory}/{gif_name}.gif', filename=f"{gif_name}.gif")
                        await ctx.followup.send(f"Please NOTE that the accuracy of the generated gif is depend on how you "
                                                f"organize the gif frames by names before you compressed them into a zip file",
                                                file=GifFile)
                        await LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Approved")
                        shutil.rmtree(GifDirectory)
                else:
                    await LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Attachment not a zip file!")
                    await ctx.followup.send("Please upload a zip file only!")
            else:
                await ctx.response.defer(ephemeral=True)
                await LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/User reached daily usage limit")
                await ctx.followup.send("You have reached the daily maximum command usage!")
        else:
            await ctx.response.defer(ephemeral=True)
            await LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/User is banned from using this application command")
            await ctx.followup.send("You are banned from using this application command by my owner!")
    else:
        await ctx.response.defer(ephemeral=True)
        await LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_samson_dm_messages",
    description="Delete all direct messages sent by Knight Samson to you"
)
async def clear_samson_dm_messages(ctx):
    await ctx.response.defer(ephemeral=True)
    async for message in ctx.user.history():
        if message.author == Samson.user:
            await message.delete()
    await LoggingCommandBeingExecuted(ctx.user.name,f"/clear_samson_dm_messages\nCommand Status: Approved")
    await ctx.followup.send("All DM messages by me have been deleted.")


@Samson.event
async def on_member_join(member):
    async with ConfigLock:
        SamsonConfig[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval", "Banned Application Commands": []}
        async with aiofiles.open(CONFIGFILEPATH, "w") as file:
            await file.write(json.dumps(SamsonConfig, indent=4))

    guild = member.guild
    channel = guild.system_channel or guild.text_channels[0]
    if channel:
        await channel.send(f"Greeting {member.mention}")


@Samson.event
async def on_member_remove(member):
    async with ConfigLock:
        del SamsonConfig[str(member.id)]
        async with aiofiles.open(CONFIGFILEPATH, "w") as file:
            await file.write(json.dumps(SamsonConfig, indent=4))

    guild = member.guild
    channel = guild.system_channel or guild.text_channels[0]
    if channel:
        await channel.send(f"We will miss {member.mention}!")


@Samson.event
async def on_message(message):

    await Samson.process_commands(message)

    # Ignore messages from the bots
    if message.author.id == Samson.user.id:
        return

    if isDMChannel(message.channel):
        reply = await gpt_text_and_picture_inputs_only(message.content, message.author.name, "gpt-5.4", INSTRUCTION_LISTS[SamsonConfig[str(message.author.id)]["Samson Roleplay"]])
        if len(reply) > 1500:
            buffer = BytesIO()
            buffer.write(reply.encode('utf-8'))
            buffer.seek(0)
            replyFile = discord.File(fp=buffer, filename="reply.txt")
            await message.author.send("", file=replyFile)
        else:
            await message.author.send(reply)


Samson.run(DISCORDAPI)
