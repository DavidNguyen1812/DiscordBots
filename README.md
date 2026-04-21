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
│   └── NexusCryptoUtilities.py                             # Separate Python Code that contains all the essential crypto utilities for Nexus to use
├── KnightSamson                                            # Discord Bot with OpenAI and Google Gemini integration
│   ├── Files                                               # Essential files to run Samson
│   │   ├── Configuration
│   │   │   └── SamsonConfiguration.json                    # Keep track of all members in any server that Knight Samson is in to ensure the member can only execute Samson application command accordance to the preset daily limit.
│   │   ├── LLM Usages
│   │   │   ├── LLMMontlyUsage.csv                          # Keep track of Samson monthly LLM usage
│   │   │   └── LLMYearlyUsage.csv                          # Keep track of Samson yearly LLM usage
│   │   ├── Logs
│   │   │   ├── CommandUsageLogFile.txt                    # A log file that log detail an event a user calling Samson application command
│   │   │   └── GPTandGeminiResponses.txt                   # A log file that log detail an OpenAI and Gemini API call to keep track of API usage
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
pip install opencv-python==4.13.0.92
pip install pillow==11.3.0
pip install python-magic==0.4.27
pip install rarfile==4.2
pip install requests==2.32.4
pip install scikit-learn==1.7.1
pip install selenium-wire==5.1.0
pip install blinker==1.7.0
pip install webdriver-manager==4.0.2
pip install aiofiles == 25.1.0
pip install aiocsv==1.4.0
pip install numpy==2.4.4
pip install pandas==3.0.2
pip install matplotlib==3.10.8
Need ffmpeg installed
Discord API key
OpenAI API key
Tenor API key
Klipy API key
ScrapeOps API key
```

**Application Commands**

```
/emmanuel -> Introduce the bot and it purpose

/clear_emmanuel_dm_messages -> Clear all Emmanuel DM messages

/list_supported_file -> Show all file formats that Emmanuel can process

The following commands can only be used by the server owner or the bot owner only!

/uncensored_members -> List all server members that are on the server uncensored list

/add_uncensored_member -> Add a server member to the server uncensored list

/remove_uncensored_member -> Remove a server member from the server uncensored list

/add_uncensored_channel -> Add a server channel to the server uncensored list. This tells Emmanuel to not bother monitoring that specific server channel.

/remove_uncensored_channel -> Add a server channel from the server uncensored list.

/uncensored_channels -> List all uncensored channles that are on the server uncensored list
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

  10. Comprehensive logging OpenAI scan usage
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
```
pip install dotenv==0.9.0
pip install discord-py==2.5.2
pip install pycryptodome==3.23.0
pip install vigenere==1.1.0
Discord API key
```

**Application Commands**
```
/nexus -> Introduce the bot and it purpose

/david_cipher -> A symmetric self-made cryptographic algorithm by me with a combination of Ceasar's shift and random list shuffle

/rc4 -> A legacy symmetric encryption used in previous TLS/SSL, HTTPS, WiFi WEP, VPN, and file encryption

/hash_func -> Providing hash multiple hash algorithms from MD5, SHA1, SHA2, SHA3, SHAKE, and BLAKE

/morse_decode -> Decoding a Morse code

/tap_code_decode -> Decoding a Tap code

/rail_fence_cipher -> A symmetric rail fence cryptographic algorithm

/random_string_subs_cipher -> A symmetric Caesar's cipher with random shift

/vigenere_cipher -> A symmetric Vigenere's cipher

/text_book_rsa_key_generation -> A key derivation for the textbook RSA algorithm

/textbook_rsa_cipher -> An assymetric textbook RSA algorithm

/crypto_rsa_key_generation -> A key derivation for standard RSA algorithm

/crypto_aes_ocb_key_generation -> A key derivation for symmetric AES cryptographic algorithm with OCB (Offset Code Block) mode for data confidentiality and integrity

/crypto_aes_ocb_cipher -> A symmetric AES cryptographic with OCB (Offset Code Block) mode for data confidentiality and integrity

/clear_nexus_dm_messages -> Deleting all past DM messages from Nexus (Knight Nexus was designed with no DM functionailty, this command serve in case Nexus send DM to the user about encrytion key, ..etc..)

/crypto_ecc_key_generation -> A key derivation for assymetric ECC cryptographic algorithm

/crypto_rsa_pkcs1_oaep_cipher -> An assymetric RSA cryptographic algorithm in Pkcs1_oaep mode

/crypto_pss_rsa_digital_signature -> A digital signature with RSA

/crypto_ecdsa -> A digital signature for ECC

/square_code -> A symmetric square code cryptographic algorithm 
```

## Knight Samson

**Overview**

Main functionality is integrating OpenAI and Google Gemini models to Discord. Samson can also manage server channel by reacting to user message, deleting channel messages **ONLY WITH GRANTED PERMISSION**, DM user and interacting with user DM with OpenAI chat model **ONLY WHEN USER ENABLE DM WITH SAMSON**.

**System Requirements**

```
pip install pillow==11.3.0
pip install discord-py==2.5.2
pip install openai==2.26.0
pip install google-genai==1.66.0
pip install aiofiles==25.1.0
pip install aiocsv==1.4.0
pip install numpy==2.4.4
pip install pandas==3.0.2
pip install matplotlib==3.10.8
Discord API key
OpenAI API key
Google Gemini API key
```

**Application Commands**

```
/view_application_command_config -> Viewing Samson application command configuration

/application_command_config -> Permanently ban or unban a member in the server to use specific Samson's application command(s)

/add_command -> Increase/Decrease member current application command usage

/get_user_list_of_permissions -> Get a list of all server permissions assigned to a member (NOTE: Samson must have higher role than the member for this command to work)

/samson -> Introduce the bot and it purpose

/roleplay -> Configure LLM response style of user choice

/clear_last_message -> Delete last specified number of messages in a server channel (NOTE: Samson must have permission to delete message)

/clear_all_message -> Delete all messages in the past in a server channel (NOTE: Samson must have permission to delete message)

/clear_user_message -> Delete last sepcified number of messages from a specific user ((NOTE: Samson must have permission to delete message)

/direct_message -> Make Samson send a customized DM to a user in the server (NOTE: User must enable DM with Samson)

/clear_samson_dm_messages -> Delete all of Samson past DM messages

/openai_gpt_chat -> Integrating OpenAI GPT chat models. This works with picture and text prompt.

/google_gemini_chat -> Integrating Google Gemini chat models. This works with picture and text prompt.

/openai_gpt_audio -> Integrating OpenAI audio models. This works with audio and text prompt.

/google_gemini_audio -> Integrating Google Gemini audio TTS models. This works with ONLY text prompt.
```

