import discord
import discord.ext.commands
import time
import os
import shutil
import json
import requests
import mimetypes
import magic
import base64
import random
import wave


import zipfile
from PIL import Image
from openai import OpenAI
from google import genai
from discord import app_commands
from discord.ext import commands, tasks
from google.genai import types


from EmojiChecker import is_emoji
from typing import Literal
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

"""----Configuration Constants----"""
COMMAND_USAGE = 7
DISCORDAPI = os.environ.get("SAMSONDISCORDAPI")
LOGCOMMANDFILEPATH = os.environ.get("SAMSONLOGPATH")
CONFIGFILEPATH = os.environ.get("SAMSONCONFIGPATH")
GPTANDGEMINILOGUSERMESSAGEFILEPATH = os.environ.get("SAMSONGPTANDGEMINILOGPATH")
GPTAPI = os.environ.get("SAMSONGPTAPI")
INSTRUCTION_LISTS = {"Medieval": "You are a medieval warrior! Please ALWAYS response to the user prompt in medieval style!",
                   "Futuristic": "You are a high tech futuristic machine! Please ALWAYS response to the user prompt in futuristic style!",
                   "Romantic": "You are a romantic person! Please ALWAYS response to the user prompt in a romantic style!",
                   "Modern Day": "You are a person from modern day! Please ALWAYS response to the user prompt in a modern language!",
                   "Military": "You are a battle hardened modern war officer! Please ALWAYS response to the user prompt in a militaristic language!",
                   "Horror": "You are a scary monster! Please ALWAYS response to the user prompt in a scary language!",
                   "Fitness Coach": "You are a fitness coach! Please ALWAYS response to the user prompt like a fitness coach!",
                   "Viking": "You are a Viking! Please ALWAYS response to the user prompt with Nordic culture!",
                   "Samurai": "You are an honourable Samurai! Please ALWAYS response to the user prompt according to the Bushido Code!",
                   "Comedian": "You are a comedian! Please ALWAYS response to the user prompt with some humor!"}
MODELINPUTTOKENLIMIT = {
                        "gemini-2.5-flash": 1048576,
                        "gemini-2.5-pro": 1048576,
                        "gemini-3.1-pro-preview": 1048576,
                        "gpt-5.4": 1050000,
                        "gpt-5.2": 400000,
                        "gpt-5.1": 400000,
                        "gpt-5": 400000,
                        "gpt-5-mini": 400000,
                        "gpt-5-nano": 400000,
                        "gpt-5.3-codex": 400000,
                        "gpt-5.2-codex": 400000,
                        "gpt-5.1-codex": 400000,
                        "gpt-4.1": 1047576,
                        "gpt-4.1-mini": 1047576,
                        "gpt-4.1-nano": 1047576,
                        "gpt-4o": 128000,
                        "gpt-4.0-mini": 128000,
                        "o4-mini": 200000,
                        "o3": 200000,
                        "gemini-2.5-flash-preview-tts": 8192,
                        "gemini-2.5-pro-preview-tts": 8192
                       }


"""Initializing Openai and Google Gemini and setting up Discord Intents for Samson"""
GPTclient = OpenAI(api_key=GPTAPI)
GEMINIclient = genai.Client()
intents = discord.Intents.all()
Samson = commands.Bot(command_prefix='/', intents=intents)

with open(CONFIGFILEPATH, "r") as readFile:
    user_list = json.load(readFile)


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

    for guild in Samson.guilds:
        for member in guild.members:
            if not user_list.get(str(member.id), ""):
                user_list[str(member.id)] = {"Current command usage limit": COMMAND_USAGE, "Samson Roleplay": "Medieval"}
                print(f"Adding user: {member.name} - ID: {member.id} from server: {guild.name} - ID: {guild.id} to Samson Configuration File")

    with open(CONFIGFILEPATH, "w") as file:
        json.dump(user_list, file, indent=4)

    update_user_command_limit.start()


def LoggingCommandBeingExecuted(userName, command):
    with open(LOGCOMMANDFILEPATH, 'a') as logFile:
        logFile.write(f"{time.ctime(time.time())}")
        logFile.write(f"\n{userName} used command {command}\n\n")


def LoggingGPTandGeminiOutputs(data):
    with open(GPTANDGEMINILOGUSERMESSAGEFILEPATH, 'a') as logFile:
        logFile.write(data)


def CheckingUserCurrentCommandUsage(userid):
    if userid == 987765832895594527:
        return True
    if user_list[str(userid)]["Current command usage limit"] > 0:
        user_list[str(userid)]["Current command usage limit"] -= 1
        with open(CONFIGFILEPATH, "w") as file:
            json.dump(user_list, file, indent=4)
        return True
    return False



def gpt_text_and_picture_inputs_only(userPrompt, userName, model, instructions, fileUpload=None):
    LoggingGPTandGeminiOutputs(f"{time.ctime(time.time())}")
    if fileUpload is None:
        LoggingGPTandGeminiOutputs(f"\n{userName}: {userPrompt}\nUser instructions: {instructions}")
        totalInputToken = GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=userPrompt).input_tokens
    else:
        if fileUpload[1] == "IMAGE":
            LoggingGPTandGeminiOutputs(f"\n{userName}: {userPrompt}\nUser instructions: {instructions}\nUser attached an image!")
            totalInputToken = GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=[
                {"role": "user",
                 "content": [{"type": "input_text", "text": userPrompt},
                            {"type": "input_image", "image_url": f"data:image/png;base64,{fileUpload[0]}"},
                        ],
                    }
                ]).input_tokens
        else:
            LoggingGPTandGeminiOutputs(f"\n{userName}: {userPrompt}\nUser instructions: {instructions}\nUser attached a PDF file!")
            with open(fileUpload[0], "rb") as PDFfile:
                fileID = GPTclient.files.create(file=PDFfile, purpose="user_data").id
            os.remove(fileUpload[0])
            totalInputToken = GPTclient.responses.input_tokens.count(model=model, instructions=instructions, input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": userPrompt},
                            {"type": "input_file", "file_id": fileID}
                        ]
                    }
                ]).input_tokens

    LoggingGPTandGeminiOutputs(f"\nTotal Input Tokens: {totalInputToken} tokens")
    if totalInputToken > MODELINPUTTOKENLIMIT[model]:
        if not fileUpload:
            if fileUpload[1] != "IMAGE":
                GPTclient.files.delete(fileID)
        LoggingGPTandGeminiOutputs(f"\nTotal input tokens exceeding model {model} input token limit of {MODELINPUTTOKENLIMIT[model]} tokens!\n\n")
        return f"YOUR PROMPT TOTAL TOKENS -> {totalInputToken} TOKENS EXCEEDING THE MODEL {model} INPUT TOKEN LIMIT OF {MODELINPUTTOKENLIMIT[model]} TOKENS!"
    else:
        if fileUpload is None:
            response = GPTclient.responses.create(
                model=model,
                instructions=instructions,
                input=userPrompt,
            )
        else:
            if fileUpload[1] == "IMAGE":
                response = GPTclient.responses.create(
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
                response = GPTclient.responses.create(
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
                GPTclient.files.delete(fileID)


        reply = response.output_text
        totalOutputTokenCount = response.usage.total_tokens - response.usage.input_tokens
        LoggingGPTandGeminiOutputs(f"\nOpenAI {model}: {reply}\nTotal Output Tokens: {totalOutputTokenCount} tokens\n\n")
        return reply


def gemini_text_and_picture_and_audio_only(userInput, userName, model, fileUpload=None, audio=None):
    LoggingGPTandGeminiOutputs(f"{time.ctime(time.time())}")
    LoggingGPTandGeminiOutputs(f"\n{userName}: {userInput}")
    if fileUpload is not None:
        if fileUpload.endswith(".pdf"):
            LoggingGPTandGeminiOutputs(f"\nUser attached a PDF file!")
        else:
            LoggingGPTandGeminiOutputs(f"\nUser attached an image file!")
        uploadedFile = GEMINIclient.files.upload(file=fileUpload)
        prompt = [uploadedFile, userInput]
        os.remove(fileUpload)
    else:
        prompt = userInput
    totalInputTokenCount = GEMINIclient.models.count_tokens(model=model, contents=prompt).total_tokens
    LoggingGPTandGeminiOutputs(f"\nTotal Input Tokens: {totalInputTokenCount} tokens")
    if totalInputTokenCount > MODELINPUTTOKENLIMIT[model]:
        LoggingGPTandGeminiOutputs(f"\nTotal input tokens exceeding model {model }input token limit of {MODELINPUTTOKENLIMIT[model]} tokens!\n\n")
        return f"YOUR PROMPT TOTAL TOKENS -> {totalInputTokenCount} TOKENS EXCEEDING THE MODEL {model} INPUT TOKEN LIMIT OF {MODELINPUTTOKENLIMIT[model]} TOKENS!"
    else:
        if audio is None:
            response = GEMINIclient.models.generate_content(model=model, contents=prompt)
        else:
            response = GEMINIclient.models.generate_content(
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
        LoggingGPTandGeminiOutputs(f"\nGemini {model}: {reply}\nTotal Output Tokens: {totalOutputTokenCount} tokens\n\n")
        return reply


def gpt_text_and_audio_only(userInput, userName, model, instructions, option):
    LoggingGPTandGeminiOutputs(f"{time.ctime(time.time())}")
    if option == "text-output":
        LoggingGPTandGeminiOutputs(f"\n{userName}: {userInput[0]}\nUser attached an audio file!")
        reply = GPTclient.chat.completions.create(
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
        LoggingGPTandGeminiOutputs(f"\nTotal Input Tokens: {reply.usage.prompt_tokens} tokens"
                                   f"\nChatGPT {model}: {reply.choices[0].message.content}"
                                   f"\nTotal Output Tokens: {reply.usage.total_tokens - reply.usage.prompt_tokens} tokens\n\n")
        return [reply.choices[0].message.content]
    else:
        LoggingGPTandGeminiOutputs(f"\n{userName}: {userInput[0]}")
        reply = GPTclient.chat.completions.create(
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
        LoggingGPTandGeminiOutputs(f"\nTotal Input Tokens: {reply.usage.prompt_tokens} tokens"
                                   f"\nChatGPT {model}: {reply.choices[0].message.audio.transcript}"
                                   f"\nTotal Output Tokens: {reply.usage.total_tokens - reply.usage.prompt_tokens} tokens\n\n")
        return [reply.choices[0].message.audio.transcript, reply.choices[0].message.audio.data]



def isDMChannel(channel):
    if str(channel).startswith("Direct Message"):
        return True
    else:
        return False


@tasks.loop(hours=24)  # A task every 24 hours
async def update_user_command_limit():
    for userId in user_list:
        user_list[userId]["Current command usage limit"] = COMMAND_USAGE

    with open(CONFIGFILEPATH, "w") as file:
        json.dump(user_list, file, indent=4)


# Command for Creator ONLY!
@Samson.tree.command(
    name="add_command",
    description="Adding additional command usage to a mentioned user in the server. Creator Only Command!!!"
)
@app_commands.describe(
    username="Mention a user in the server, e.g., @user123",
    value="How many command usage value to be added?"
)
async def add_command(ctx, username: discord.User, value: int):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == 987765832895594527: # Put your Discord ID here, if you're the owner of the bot

        user_list[str(username.id)]["Current command usage limit"] += value

        with open(CONFIGFILEPATH, "w") as file:
            json.dump(user_list, file, indent=4)

        LoggingCommandBeingExecuted(ctx.user.name, f"/add_command {username} {value}\nCommand Status: Approved")
        await ctx.followup.send("Command Successfully Executed!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/add_command {username} {value}\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by my Lord Sir David Nguyen!")


# Command for Creator ONLY!
@Samson.tree.command(
    name="get_user_list_of_permissions",
    description="Get the permissions granted to a mentioned user in the server. Creator Only Command!!!"
)
@app_commands.describe(member="Mention a user in the server, e.g., @user123")
async def get_user_list_of_permissions(ctx, member: discord.User):
    await ctx.response.defer(ephemeral=True)
    if ctx.user.id == 987765832895594527:
        if not isDMChannel(ctx.channel):
            memberPermissions = member.guild_permissions
            permissionList = []
            for permission, status in iter(memberPermissions):
                permissionList.append(f"{permission.replace("_", " ").upper()}: {status}")
            await ctx.followup.send(f"Permissions for '{member.name}' from Server '{ctx.channel.guild.name}':\n" + "\n".join(permissionList))
            LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("Command can not work in DM channel")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/get_user_list_of_permissions {member}\nCommand Status: Denied/Command runs by unauthorized personnel")
        await ctx.followup.send("This command can only be used by my Lord Sir David Nguyen!")


@Samson.tree.command(
    name="samson",
    description="Get Information about Knight Samson."
)
async def samson(ctx):
    await ctx.response.defer(ephemeral=True)  # Prevent interaction from timing out
    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Approved")
            await ctx.followup.send(
                "I am a knight designed by Sir David Nguyen with ChatGPT and Google Gemini API to interact with user through Direct "
                "Message or in a Server. I have certain commands ONLY WORK in a SERVER CHANNEL. All commands can "
                f"only be used {COMMAND_USAGE} times daily!\n"
                "Command List:\n"
                "/samson\n"
                "/roleplay\n"
                "/openai_gpt_chat\n"
                "/google_gemini_chat\n"
                "/openai_gpt_audio\n"
                "/clear_last_message\n"
                "/clear_all_message\n"
                "/clear_user_message\n"
                "/react\n"
                "/direct_message\n"
                "/customized_gif_generator\n"
                "/clear_samson_dm_messages")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, "/samson\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="roleplay",
    description="Configuring Knight Samson to roleplay a specific personality"
)
@app_commands.describe(role="Select a role for Samson to role play")
async def roleplay(ctx, role: Literal["Medieval", "Futuristic", "Romantic", "Modern Day", "Military", "Horror", "Fitness Coach", "Viking", "Samurai", "Comedian"]):
    await ctx.response.defer(ephemeral=True)
    if user_list[str(ctx.user.id)]["Samson Roleplay"] == role:
        await ctx.followup.send(f"I'm already configured to role play as {role}")
        LoggingCommandBeingExecuted(ctx.user.name,f"/roleplay {role}\nCommand Status: Denied/Samson already configured to the selected roleplay!")
    else:
        user_list[str(ctx.user.id)]["Samson Roleplay"] = role
        reply = gpt_text_and_picture_inputs_only("Introduce yourself as Samson", ctx.user.name, "gpt-4o", INSTRUCTION_LISTS[role])
        await ctx.followup.send(reply)
        LoggingCommandBeingExecuted(ctx.user.name, f"/roleplay {role}\nCommand Status: Approved")
    with open(CONFIGFILEPATH, "w") as file:
        json.dump(user_list, file, indent=4)


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
"""
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

    if keep_secret == "Yes":
        await ctx.response.defer(ephemeral=True)
    else:
        await ctx.response.defer()

    instruction = INSTRUCTION_LISTS[user_list[str(ctx.user.id)]["Samson Roleplay"]]
    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            if file_attachment is not None:
                response = requests.get(file_attachment.url)
                mime = magic.from_buffer(response.content, mime=True)
                fileExt = mimetypes.guess_extension(mime)
                if not fileExt.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                    await ctx.followup.send("Please upload your file attachments in PNG, JPG, or PDF format!")
                    LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/Unaccepted File Format!")
                    return
                if fileExt.endswith(".pdf"):
                    fileContent = f"./{random.randint(0,9999)}.pdf"
                    with open(fileContent, "wb") as PDFfile:
                        PDFfile.write(response.content)
                    fileContent = [fileContent, "PDF"]
                else:
                    fileContent = [base64.b64encode(response.content).decode("utf-8"), "IMAGE"]
            else:
                fileContent = ""
            if fileContent:
                reply = gpt_text_and_picture_inputs_only(message, ctx.user.name, model, instruction, fileContent)
            else:
                reply = gpt_text_and_picture_inputs_only(message, ctx.user.name, model, instruction)
            if len(reply) > 1500:
                buffer = BytesIO()
                buffer.write(reply.encode('utf-8'))
                buffer.seek(0)
                replyFile = discord.File(fp=buffer, filename="reply.txt")
                await ctx.followup.send("The answer exceeds 1500 words. Here is the answer in a text file format!", file=replyFile)
            else:
                await ctx.followup.send(reply)
            LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_chat {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


"""
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
"""
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

    if keep_secret == "Yes":
        await ctx.response.defer(ephemeral=True)
    else:
        await ctx.response.defer()

    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            if file_attachment is not None:
                response = requests.get(file_attachment.url)
                mime = magic.from_buffer(response.content, mime=True)
                fileExt = mimetypes.guess_extension(mime)
                if not fileExt.endswith((".png", ".jpg", ".jpeg", ".pdf")):
                    await ctx.followup.send("Please upload your file attachments in PNG, JPG, or PDF format!")
                    LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/Unaccepted File Format!")
                    return
                fileContent = f"./{random.randint(0, 999999)}{fileExt}"
                with open(fileContent, "wb") as file:
                    file.write(response.content)
            else:
                fileContent = ""
            if fileContent:
                reply = gemini_text_and_picture_and_audio_only(f"{message}\n{INSTRUCTION_LISTS[user_list[str(ctx.user.id)]["Samson Roleplay"]]}", ctx.user.name, model, fileContent)
            else:
                reply = gemini_text_and_picture_and_audio_only(f"{message}\n{INSTRUCTION_LISTS[user_list[str(ctx.user.id)]["Samson Roleplay"]]}", ctx.user.name, model)
            if len(reply) > 1500:
                buffer = BytesIO()
                buffer.write(reply.encode('utf-8'))
                buffer.seek(0)
                replyFile = discord.File(fp=buffer, filename="reply.txt")
                await ctx.followup.send("", file=replyFile)
            else:
                await ctx.followup.send(reply)
            LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_chat {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


"""
https://developers.openai.com/api/docs/models 
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
"""
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
    if keep_secret == "Yes":
        await ctx.response.defer(ephemeral=True)
    else:
        await ctx.response.defer()

    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            if input_options.startswith("Audio and Prompt Inputs ONLY"):
                if file_attachment is None:
                    await ctx.followup.send("Please upload your an audio input in WAV or MP3 format!")
                    LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/User did not provide audio input!")
                    return
                else:
                    response = requests.get(file_attachment.url)
                    mime = magic.from_buffer(response.content, mime=True)
                    fileExt = mimetypes.guess_extension(mime)
                    if not fileExt.endswith((".wav", ".mp3")):
                        await ctx.followup.send("Please upload your audio attachment in WAV or MP3 format!")
                        LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/Unaccepted File Format!")
                        return
                    reply = gpt_text_and_audio_only([message, base64.b64encode(response.content).decode("utf-8"), fileExt.replace(".", "")], ctx.user.name, model, INSTRUCTION_LISTS[user_list[str(ctx.user.id)]["Samson Roleplay"]], "text-output")[0]
                    if len(reply) > 1500:
                        buffer = BytesIO()
                        buffer.write(reply.encode('utf-8'))
                        buffer.seek(0)
                        replyFile = discord.File(fp=buffer, filename="reply.txt")
                        await ctx.followup.send("", file=replyFile)
                    else:
                        await ctx.followup.send(reply)
            else:
                result = gpt_text_and_audio_only([message], ctx.user.name, model, INSTRUCTION_LISTS[user_list[str(ctx.user.id)]["Samson Roleplay"]], "audio-output")
                with open("SamsonResponse.wav", "wb") as AUDIOfile:
                    AUDIOfile.write(base64.b64decode(result[1]))
                with open("SamsonResponse.wav", "rb") as AUDIOfile:
                    audioFile = discord.File(fp=AUDIOfile, filename="SamsonResponse.wav")
                os.remove("SamsonResponse.wav")
                await ctx.followup.send("Here is the audio:", file=audioFile)
                buffer = BytesIO()
                buffer.write(result[0].encode('utf-8'))
                buffer.seek(0)
                transcriptFile = discord.File(fp=buffer, filename="transcript.txt")
                await ctx.followup.send("Here is the transcript:", file=transcriptFile)
            LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name,f"/openai_gpt_audio {message} {model} {keep_secret} {input_options}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


"""
https://ai.google.dev/gemini-api/docs/pricing
GOOGLE GEMINI INFO:
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
    if keep_secret == "Yes":
        await ctx.response.defer(ephemeral=True)
    else:
        await ctx.response.defer()

    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            gemini_text_and_picture_and_audio_only(message, ctx.user.name, model, audio=True)
            with open(f"SamsonResponse.wav", "rb") as audioFile:
                AudioFile = discord.File(fp=audioFile, filename="SamsonResponse.wav")
            await ctx.followup.send("", file=AudioFile)
            os.remove(f"SamsonResponse.wav")
            LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name,f"/google_gemini_audio {message} {model} {keep_secret}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_last_message",
    description="Delete the last specified number of messages."
)
@app_commands.describe(messagenum="How many previous message you want to delete?")
async def clear_last_message(ctx, messagenum: int):  # Bishesh is banned!!!
    await ctx.response.defer(ephemeral=True)  # Prevent timing out of the process if it takes longer than 3 seconds
    if ctx.user.id != 341248287296454677:
        if not isDMChannel(ctx.channel):
            if CheckingUserCurrentCommandUsage(ctx.user.id):
                await ctx.channel.purge(limit=messagenum)
                LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Approved")
                await ctx.followup.send("Command Successfully Executed!")
            else:
                LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/clear_last_message {messagenum}\nCommand Status: Denied/Command runs by unauthorized user")
        await ctx.followup.send("Bishesh, you are banned from using this command!")


@Samson.tree.command(
    name="clear_all_message",
    description="Delete all messages."
)
async def clear_all_message(ctx):  # Bishesh is banned!!!
    await ctx.response.defer(ephemeral=True)  # Prevent timing out of the process if takes longer than 3 seconds
    if ctx.user.id != 341248287296454677:
        if not isDMChannel(ctx.channel):
            if CheckingUserCurrentCommandUsage(ctx.user.id):
                async for message in ctx.channel.history():  # Fetch message history
                    await message.delete()
                LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Approved")
                return
            else:
                LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, "/clear_all_message\nCommand Status: Denied/Command runs by unauthorized user")
        await ctx.followup.send("Bishesh, you are banned from using this command!")


@Samson.tree.command(
    name="clear_user_message",
    description="Delete the last specified number of messages originated from the mentioned user."
)
@app_commands.describe(
    user="Mention a user in the server, e.g., @user123",
    messagenum="How many previous message you want to delete?"
)
async def clear_user_message(ctx, user: discord.User, messagenum: int):  # Bishesh is banned!!!
    if ctx.user.id != 341248287296454677:
        await ctx.response.defer()  # Prevent interaction from timing out
        if not isDMChannel(ctx.channel):
            if CheckingUserCurrentCommandUsage(ctx.user.id):
                counter = 0
                async for message in ctx.channel.history():  # Fetch message history
                    if message.author.name == user.name:
                        await message.delete()
                        counter += 1
                    if counter == messagenum:
                        break
                await ctx.followup.send("Command Successfully Executed!")
                LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Approved")
            else:
                LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Denied/User reached daily limit usage")
                await ctx.followup.send(f"You have reached the daily maximum command usage!")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Denied/Command runs in DM channel")
            await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/clear_user_message {user}\nCommand Status: Denied/Command runs by unauthorized user")
        await ctx.followup.send("Bishesh, you are banned from using this command!")


@Samson.tree.command(
    name="react",
    description="Tell Knight Samson add emoji reaction to the last specified messages from the mentioned user."
)
@app_commands.describe(
    username="Mention a user in the server, e.g., @user123",
    num="How many previous message you want to react?",
    userinput="Select 'React' for Samson to react, Select 'Remove' to clear all reactions",
    emote="Make sure to select a valid emote, NOTE: Custom emoji will not work! "
)
async def react(ctx, username: discord.User, num: int, userinput: Literal["React", "Remove"],emote: str):
    await ctx.response.defer(ephemeral=True)  # Prevent interaction from timing out
    if not isDMChannel(ctx.channel):
        counter = 0
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            emote = emote.split(' ')
            async for message in ctx.channel.history():
                if message.author.name == username.name:
                    if userinput == "React":
                        counter += 1
                        for i in range(len(emote)):
                            if is_emoji(emote[i]):  # Check if emote is an emoji and of length 2
                                await message.add_reaction(emote[i])
                            else:
                                pass
                    else:
                        if message.reactions:  # Check if the message has at least 1 reaction
                            counter += 1
                            await message.clear_reactions()
                    if counter == num:
                        break
            await ctx.followup.send(f"Command Successfully Executed!")
            LoggingCommandBeingExecuted(ctx.user.name, f"/react {username} {num} {userinput} {emote}\nCommand Status: Approved")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/react {username} {num} {userinput} {emote}\nCommand Status: Denied/User reached daily limit usage")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/react {username} {num} {userinput} {emote}\nCommand Status: Denied/Command runs in DM channel")
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
    await ctx.response.defer(ephemeral=True)  # Prevent interaction from timing out
    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            try:
                await member.send(f"User {ctx.user.name} want me to send you message:\n{message}")
                LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Approved")
            except discord.Forbidden:
                LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/User disabled DM with Samson")
                await ctx.followup.send(f"I can't DM {member.name}. User might have DMs disabled.")
            except Exception as e:
                LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/Error {e}")
                await ctx.followup.send(f"An error occurred: {e}")
        else:
            LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/User reached daily usage limit")
            await ctx.followup.send(f"You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name,f"/direct_message {member} {message}\nCommand Status: Denied/Command runs in DM channel")
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
    await ctx.response.defer()
    if not isDMChannel(ctx.channel):
        if CheckingUserCurrentCommandUsage(ctx.user.id):
            isZipFile = False
            response = requests.get(zip_file.url, stream=True)
            if response.content.startswith(b'PK\x03\x04'):
                isZipFile = True
            if isZipFile:
                GifDirectory = os.path.basename(zip_file.url.split('?')[0]).split('.')[0]
                os.mkdir(GifDirectory)
                zipPath = f"{GifDirectory}/{os.path.basename(zip_file.url.split('?')[0])}"
                with open(zipPath, "wb") as data:
                    for chunk in response.iter_content(chunk_size=8192):
                        data.write(chunk)
                uncompressedSize = os.path.getsize(zipPath)
                with zipfile.ZipFile(zipPath, 'r') as zipRef:
                    for entry in zipRef.infolist():
                        DestinationPath = os.path.abspath(os.path.join(GifDirectory, entry.filename))
                        if not DestinationPath.startswith(os.path.abspath(GifDirectory)):
                            LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment can cause ../ attack")
                            await ctx.followup.send("Your zip file contains uncompressed content hinted directory transversal attack!")
                            shutil.rmtree(GifDirectory)
                            return
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
                                            LoggingCommandBeingExecuted(ctx.user.name,f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment uncompressed size exceeds 1GB")
                                            await ctx.followup.send(f"Your zip file uncompressed size of {uncompressedSize} bytes exceeds 1GB")
                                            shutil.rmtree(GifDirectory)
                                            return
                                    with open(DestinationPath, 'wb') as f:
                                        f.write(fileData)
                            except TypeError:
                                pass
                os.remove(zipPath)
                if os.listdir(GifDirectory):
                    GifFrames = []
                    for dirpath, _, filenames in os.walk(GifDirectory):
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
                        f'{GifDirectory}/{gif_name}.gif',
                        save_all=True,
                        append_images=NewResizeFrames[1:],
                        optimize=True,
                        duration=frame_rate,
                        loop=0,
                        disposal=2
                    )
                    GifFile = discord.File(fp=f'{GifDirectory}/{gif_name}.gif', filename=f"{gif_name}.gif")
                    await ctx.followup.send(f"Please NOTE that the accuracy of the generated gif is depend on how you "
                                            f"organize the gif frames by names before you compressed them into a zip file",
                                            file=GifFile)
                    LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Approved")
                    shutil.rmtree(GifDirectory)
                else:
                    shutil.rmtree(GifDirectory)
                    await ctx.followup.send(f"There is no PNG frames in the zip file!")
                    LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Zip Attachment does not have any PNG frames!")
            else:
                LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Attachment not a zip file!")
                await ctx.followup.send("Please upload a zip file only!")
        else:
            LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/User reached daily usage limit")
            await ctx.followup.send("You have reached the daily maximum command usage!")
    else:
        LoggingCommandBeingExecuted(ctx.user.name, f"/customized_gif_generator {zip_file.url}\nCommand Status: Denied/Command runs in DM channel")
        await ctx.followup.send("I can only execute command in a Server channel, not Direct Message!!!")


@Samson.tree.command(
    name="clear_samson_dm_messages",
    description="Delete all direct messages sent by Knight Samson to you"
)
async def clear_samson_dm_messages(ctx):
    await ctx.response.defer()
    async for message in ctx.user.history():
        if message.author == Samson.user:
            await message.delete()
    LoggingCommandBeingExecuted(ctx.user.name,f"/clear_samson_dm_messages\nCommand Status: Approved")
    if str(ctx.channel.type).startswith("private"):
        async for message in ctx.user.history(limit=1):
            if message.author == Samson.user:
                await message.delete()
    else:
        await ctx.channel.purge(limit=1)


@Samson.event
async def on_member_join(member):
    if member.id != 987765832895594527:

        user_list[str(member.id)]["Current command usage limit"] = COMMAND_USAGE
        user_list[str(member.id)]["Samson Roleplay"] = "Medieval"

        with open(CONFIGFILEPATH, "w") as file:
            json.dump(user_list, file, indent=4)

    guild = member.guild
    channel = guild.system_channel or guild.text_channels[0]
    if channel:
        await channel.send(f"Greeting {member.mention}")


@Samson.event
async def on_member_remove(member):
    if member.id != 987765832895594527:

        del user_list[str(member.id)]

        with open(CONFIGFILEPATH, "w") as file:
            json.dump(user_list, file, indent=4)

    guild = member.guild
    channel = guild.system_channel or guild.text_channels[0]
    if channel:
        await channel.send(f"We will miss {member.mention}!")


@Samson.event
async def on_message(message):

    await Samson.process_commands(message)

    # Ignore messages from the bots and command message
    if message.author.id == Samson.user.id:
        return

    if isDMChannel(message.channel):
        reply = gpt_text_and_picture_inputs_only(message.content, message.author.name, "gpt-5.4", INSTRUCTION_LISTS[user_list[str(message.author.id)]["Samson Roleplay"]])
        if len(reply) > 1500:
            buffer = BytesIO()
            buffer.write(reply.encode('utf-8'))
            buffer.seek(0) 
            replyFile = discord.File(fp=buffer, filename="reply.txt")
            await message.author.send("", file=replyFile)
        else:
            await message.author.send(reply)


Samson.run(DISCORDAPI)
