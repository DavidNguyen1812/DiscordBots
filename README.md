# Pre-built Discord Bots

## OVERVIEW
Three pre-built Discord bots with unique functionality. All you need just a discord API,other APIs (will be included as you read this README) and a Linux/MacOS system with Python 3.10+ to host and deploy them to your Discord server.

**NOTE: PROJECT STILL UNDER PROGRESSED!!! THERE MIGHT BE EXPLICIT CONTENT IN THE REPO, SO VIEWER DISCRETION IS ADVISED**

## Repo Structure:

```
├── KnightEmmanuel                                          # Discord Bot for NSFW detection        
│   ├── Files                                               # Essential files to run Emmanuel
│   │   ├── Configuration                                   # Configruation
│   │   │   └── EmmanuelConfig.json                         # Essential to keep track of members and channels permitted by the server owner to monitor or not as well as each member daily uncensor limit 
│   │   ├── Log                                             # Log
│   │   │   └── EmmanuelLog.txt                             # Emmanuel log file that log all the detail timestamp of Emmanuel monitoring result                                      
│   │   ├── WordlLists                                      # Word lists to keep track of SHA512 hash of file content that has been scanned as clean or NSFW
│   │   │   ├── CleanData.json                              # SHA512 hashes of file content scanned as clean
│   │   │   ├── NSFWData.json                               # SHA512 hashes of file content scanned as NSFW
│   │   │   └── ProfanityLibWordList.txt                    # Customizable list of profane words
│   ├── PythonScripts                                       # Emmanuel source Code Directory
│   │   └── KnightEmmanuel.py                               # Emmanuel source code in Python, detail commentations are in the code
├── KnightNexus                                             # Discord Bot with Python Cryptography modules
│   ├── KnightNexus.py                                      # Nexus source code in Python
│   └── MultiEncryption.py                                  # Separate Python Code that contains pre-built Crypto functions for Nexus to use
├── KnightSamson                                            # Discord Bot with OpenAI and Google Gemini integration
│   ├── Files                                               # Essential files to run Samson
│   │   ├── CommandUsageLogFile.txt                         # A log file that log detail an event a user calling Samson application command
│   │   ├── GPTandGeminiResponses.txt                       # A log file that log detail an OpenAI and Gemini API call to keep track of API usage
│   │   └── SamsonConfiguration.json                        # Keep track of all members in any server that Knight Samson is in to ensure the member can only execute Samson application command accordance to the preset daily limit.
│   ├── PythonScripts                                       # Samson source Code Directory
│   │   ├── EmojiChecker.py                                 # An external Python code for Samson to check if the emoji UNICODE is valid or not
│   │   └── KnightSamson.py                                 # Samson source code in Python
└──README.md                                                # This file
```

## Knight Emmanuel

**Overview**

Main functionality is scanning Discord text message and media file attachment for any NSFW content utilizing OpenAI LLM vision model via stateless REST API call and open source pre-trained NSFW model Nudenet.

**System Requirements**

```
pip install better-profanity=0.7.0
pip install discord-py==2.5.2
pip install dotenv==0.9.0
pip install filetype==1.2.0
pip install nudenet==3.4.2
pip install openai==2.26.0
pip install opencv-python==4.12.0.88
pip install pillow==11.3.0
pip install python-magic==0.4.27
pip install rarfile==4.2
pip install requests==2.32.4
pip install scikit-learn==1.7.1
pip install selenium-wire==5.1.0
pip install blinker==1.7.0
pip install webdriver-manager==4.0.2
pip install aiofiles == 25.1.0
Need ffmpeg installed
Discord API key
OpenAI API key
Tenor API key
Klipy API key
ScrapeOps API key
```
**Key Features**

```
  1. Checking for a member message text content AND ASCII content in any document file for any profane words pre-defined in the ProfanityLibWordList.txt with better_profanity and OpenAI model.

  2. Utilizing Pillow, Open CV2 module to convert all images/video frames to PNG format for Nudenet model to scan, if nothing detected, PDF conversion is called and REST API request to OpenAI model to analyze the PDF frames.

  3. Audio Transcript extraction from audio file with OpenAI GPT-4o-Transcribe model to scan for NSFW audio.

  4. Archive file extraction safety check for any malicious archive bomb and extracting all the archive content for scan.

  5. Utilizing SHA512 hash to keep record of all file content scan

  6. Comprhensive monitor logging that logs all the event Knight Emmanuel scan the server messages.

  7. Using selenium wire with ScrapeOPS fake browser headers to retrieve website HTML content for NSFW analyzation.

  8. Integration of Tenor and Klipy for authenticated Tenor and Klipy gifs retrieval for scan.

  9. Application commands for the server/bot owner to control which member or chat channel to be monitored or not by Knight Emmanuel.
```

**Limitations**

```
  1. Emmanuel only limited to scan certain file formats as NOTED in the source code.

  2. File content that exceed OpenAI input token limitation per model used WILL NOT BE SCANNED!!

  3. The image, video and archive file scan speed is not very fast.
```

## Knight Nexus
Main functionality is integrating Cryptography command to Discord using Open-Source Python Crypto Library pycryptodome

**System Requirement**
pip install dotenv==0.9.0
pip install discord-py==2.5.2
pip install pycryptodome==3.23.0
pip install vigenere==1.1.0
Discord API key

## Knight Samson

**Overview**

Main functionality is integrating OpenAI and Google Gemini models to Discord.

**Application Commands**

```
/add_command -> Increase/Decrease member current application command usage
/get_user_list_of_permissions -> Get a list of all server permissions assigned to a member (NOTE: Samson must have higher role than the member for this command to work)
/samson -> Introduce the bot and it purpose
/roleplay -> Configure LLM response style of user choice
/clear_last_message -> Delete last specified number of messages (NOTE: Samson must have permission to delete message)
/clear_all_message -> Delete all messages in the past in a server channel (NOTE: Samson must have permission to delete message)
/clear_user_message -> Delete last sepcified number of messages from a specific user ((NOTE: Samson must have permission to delete message)
/react -> Make Samson react with standard Discord emojis to a message
/direct_message -> Make Samson send a customized DM to a user in the server (NOTE: User must enable DM with Samson)
/clear_samson_dm_messages -> Delete all of Samson past DM messages
/openai_gpt_chat -> Integrating OpenAI GPT chat models. This works with picture and text prompt.
/google_gemini_chat -> Integrating Google Gemini chat models. This works with picture and text prompt.
/openai_gpt_audio -> Integrating OpenAI audio models. This works with audio and text prompt.
/google_gemini_audio -> Integrating Google Gemini audio TTS models. This works with ONLY text prompt.
```
**System Requirements**

```
pip install pillow==11.3.0
pip install discord-py==2.5.2
pip install openai==2.26.0
pip install google-genai==1.66.0
pip install aiofiles == 25.1.0
Discord API key
OpenAI API key
Google Gemini API key
```
