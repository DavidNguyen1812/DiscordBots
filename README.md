# Pre-built Discord Bots

## OVERVIEW
Three pre-built Discord bots with unique functionality. All you need just a discord API,other APIs (will be included what down the README) and a Linux/MacOS system with Python 3.10+ to host and deploy them to your Discord server.

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
Discord API key
OpenAI API key
Tenor API key
Klipy API key
ScrapeOps API key
```

## Knight Nexus
Main functionality is integrating Cryptography command to Discord using Open-Source Python Crypto Library pycryptodome

**System Requirement**
pip install dotenv==0.9.0
pip install discord-py==2.5.2
pip install pycryptodome==3.23.0
pip install vingere==1.1.0
Discord API key

## Knight Samson
Main functionality is integrating OpenAI and Google Gemini models to Discord

**System Requirements**
pip install pillow==11.3.0
pip install requests==2.32.4
pip install discord-py==2.5.2
pip install openai==2.26.0
pip install google-genai==1.66.0
Discord API key
OpenAI API key
Google Gemini API key
