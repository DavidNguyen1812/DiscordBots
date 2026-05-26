# Pre-Built Discord Bots

> **Viewer Discretion Advised**
> This repository contains explicit and NSFW-related content as part of its detection and testing functionality. Please exercise discretion when browsing the source material.

---

## Overview

This repository contains three independently deployable Discord bots, each designed around a distinct operational domain. All bots are self-hosted and require a Linux or macOS system running **Python 3.11+**, along with their respective API keys as detailed in each bot's system requirements section.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Operating System** | Linux or macOS |
| **Python Version** | `>= 3.11.0` |
| **Discord API Key** | Required by all bots — [Developer Portal](https://docs.discord.com/developers/reference) |
| **Additional API Keys** | Per-bot requirements detailed in each section below |

---

## Repository Structure

```
├── KnightEmmanuel/                         # NSFW Content Detection Bot
│   ├── Files/
│   │   ├── Configuration/
│   │   │   └── EmmanuelConfig.json         # Tracks monitored members, channels, and daily uncensor limits
│   │   ├── LLM Usages/
│   │   │   ├── LLMMonthlyUsage.csv         # Monthly LLM API usage metrics
│   │   │   └── LLMYearlyUsage.csv          # Yearly LLM API usage metrics
│   │   ├── Log/
│   │   │   └── EventLogs.txt               # Timestamped monitoring event log
│   │   └── WordLists/
│   │       ├── CleanData.json              # SHA-512 hashes of file content verified as clean
│   │       ├── NSFWData.json               # SHA-512 hashes of file content flagged as NSFW
│   │       ├── BlackListPornSites.txt       # Blocklist of known adult content domains
│   │       ├── NSFWSubreddits.txt          # Blocklist of known NSFW subreddit communities
│   │       └── ProfanityLibWordList.txt     # Customizable profane word reference list
│   └── PythonScripts/
│       └── KnightEmmanuel.py               # Primary source code (inline documentation included)
│
├── KnightNexus/                            # Cryptography Utilities Bot
│   ├── KnightNexus.py                      # Primary source code
│   └── NexusCryptoUtilities.py             # Cryptographic utility functions and helper modules
│
├── KnightSamson/                           # OpenAI & Google Gemini Integration Bot
│   ├── Files/
│   │   ├── Configuration/
│   │   │   └── SamsonConfiguration.json    # Per-member command usage limits across all servers
│   │   ├── LLM Usages/
│   │   │   ├── LLMMonthlyUsage.csv         # Monthly LLM API usage metrics
│   │   │   └── LLMYearlyUsage.csv          # Yearly LLM API usage metrics
│   │   └── Logs/
│   │       ├── EventLogs.txt               # Application command invocations and scheduled task log
│   │       └── GPTandGeminiResponses.txt   # OpenAI and Gemini API call audit log
│   └── PythonScripts/
│       └── KnightSamson.py                 # Primary source code
│
└── README.md
```

---

## Knight Emmanuel

### Overview

**Knight Emmanuel** is an automated NSFW content moderation bot designed to monitor Discord server text messages and media file attachments. It employs a multi-layered detection pipeline combining the **OpenAI LLM Vision API** and the open-source pre-trained **NudeNet** model to identify and remediate explicit content in real time.

---

### System Requirements

| Dependency | Version | Source |
|-----------|---------|--------|
| Python | `>= 3.11.0` | [python.org](https://www.python.org/downloads) |
| better-profanity | `== 0.7.0` | [GitHub](https://github.com/snguyenthanh/better_profanity) |
| discord-py | `== 2.5.2` | [GitHub](https://github.com/Rapptz/discord.py) |
| dotenv | `== 0.9.9` | [GitHub](https://github.com/pedroburon/dotenv) |
| filetype | `== 1.2.0` | [GitHub](https://github.com/h2non/filetype.py) |
| nudenet | `== 3.4.2` | [GitHub](https://github.com/notAI-tech/nudenet) |
| openai | `== 2.26.0` | [GitHub](https://github.com/openai/openai-python) |
| opencv-python | `== 4.13.0.92` | [GitHub](https://github.com/opencv/opencv-python) |
| pillow | `== 11.3.0` | [python-pillow.github.io](https://python-pillow.github.io) |
| python-magic | `== 0.4.27` | [GitHub](https://github.com/ahupp/python-magic) |
| rarfile | `== 4.2` | [GitHub](https://github.com/markokr/rarfile) |
| requests | `== 2.32.4` | [docs.python-requests.org](https://requests.readthedocs.io) |
| selenium-wire-2 | `== 0.2.1` | [GitHub](https://github.com/7x11x13/selenium-wire-2) |
| blinker | `== 1.9.0` | [GitHub](https://github.com/pallets-eco/blinker) |
| webdriver-manager | `== 4.0.2` | [GitHub](https://github.com/SergeyPirogov/webdriver_manager) |
| aiofiles | `== 25.1.0` | [GitHub](https://github.com/Tinche/aiofiles) |
| aiocsv | `== 1.4.0` | [GitHub](https://github.com/MKuranowski/aiocsv) |
| numpy | `== 2.4.4` | [numpy.org](https://numpy.org) |
| pandas | `== 3.0.2` | [pandas.pydata.org](https://pandas.pydata.org) |
| matplotlib | `== 3.10.8` | [matplotlib.org](https://matplotlib.org) |
| fpdf | `== 1.7.2` | [GitHub](https://github.com/reingart/pyfpdf) |
| ffmpeg | `== 7.1.1` | [ffmpeg.org](https://www.ffmpeg.org/download.html) |
| **Discord API Key** | N/A | [Discord Developer Portal](https://docs.discord.com/developers/reference) |
| **Tenor API Key** | N/A | [Tenor GIF API](https://tenor.com/gifapi/documentation) |
| **Klipy API Key** | N/A | [Klipy](https://klipy.com) |
| **ScrapeOps API Key** | N/A | [ScrapeOps](https://scrapeops.io) |
| **OpenAI API Key** | N/A | [OpenAI Platform](https://openai.com/api/) |

---

### Key Features

1. **Profanity Detection** — Scans message text content and ASCII content embedded in document file attachments for profane language using `better_profanity` and OpenAI GPT model verification.

2. **Image & Video NSFW Analysis** — Leverages Pillow and OpenCV to convert images and video frames to PNG format for NudeNet model inference. If no violations are detected, frames are converted to PDF and submitted to the OpenAI Vision API for secondary analysis.

3. **Audio Transcript NSFW Analysis** — Extracts audio transcripts from audio file attachments using the **OpenAI GPT-4o Transcribe** model and evaluates the transcript for NSFW content.

4. **Archive Bomb Detection & Extraction** — Inspects archive file attachments for decompression bomb patterns prior to extraction, then recursively scans all extracted content for NSFW material.

5. **SHA-512 Hash Signature Store** — Maintains a persistent hash record of all previously scanned file content to enable instantaneous verdict lookups without redundant re-analysis.

6. **Comprehensive Event Logging** — Records detailed timestamped logs of all content monitoring events performed by Knight Emmanuel.

7. **Authenticated Web Content Retrieval** — Utilizes Selenium Wire in conjunction with ScrapeOps fake browser headers to retrieve website HTML content for NSFW analysis, bypassing common bot-detection mechanisms.

8. **Tenor & Klipy GIF Integration** — Supports authenticated retrieval and scanning of GIF content from Tenor and Klipy platforms.

9. **Server Owner Access Control Commands** — Provides application commands enabling the server or bot owner to configure which members and channels are subject to Emmanuel's monitoring.

10. **LLM API Usage Tracking** — Records and aggregates OpenAI API usage metrics for cost monitoring and audit purposes.

---

### Application Commands

| Command | Access Level | Description |
|---------|-------------|-------------|
| `/emmanuel` | All Members | Displays an introduction to the bot and its purpose |
| `/clear_emmanuel_dm_messages` | All Members | Clears all Knight Emmanuel direct messages from the user's DM channel |
| `/list_supported_file` | All Members | Displays all file formats supported by Emmanuel's content analysis pipeline |
| `/uncensored_members` | Server / Bot Owner | Lists all server members currently on the server's uncensored allowlist |
| `/add_uncensored_member` | Server / Bot Owner | Adds a server member to the uncensored allowlist, exempting them from content monitoring |
| `/remove_uncensored_member` | Server / Bot Owner | Removes a server member from the uncensored allowlist |
| `/add_uncensored_channel` | Server / Bot Owner | Adds a server channel to the uncensored allowlist, excluding it from real-time monitoring |
| `/remove_uncensored_channel` | Server / Bot Owner | Removes a server channel from the uncensored allowlist |
| `/uncensored_channels` | Server / Bot Owner | Lists all server channels currently on the uncensored allowlist |

---

### Known Limitations

| # | Limitation |
|---|-----------|
| 1 | Content analysis is restricted to file formats explicitly supported by the scanning pipeline |
| 2 | File content exceeding the OpenAI input token limit for the configured model will not be scanned and will receive a clean verdict by default |
| 3 | Image, video, and archive file analysis throughput is subject to processing latency depending on file size and host hardware |

---

## Knight Nexus

### Overview

**Knight Nexus** is a cryptographic utility bot that integrates a comprehensive suite of classical and modern cryptographic algorithms into Discord, powered by the open-source Python library **PyCryptodome**. It supports symmetric encryption, asymmetric encryption, digital signatures, hash functions, and classical cipher schemes — all accessible as Discord application commands.

---

### System Requirements

| Dependency | Version | Source |
|-----------|---------|--------|
| Python | `>= 3.11.0` | [python.org](https://www.python.org/downloads) |
| discord-py | `== 2.5.2` | [GitHub](https://github.com/Rapptz/discord.py) |
| dotenv | `== 0.9.9` | [GitHub](https://github.com/pedroburon/dotenv) |
| pycryptodome | `== 3.23.0` | [pycryptodome.org](https://www.pycryptodome.org) |
| vigenere | `== 1.1.0` | [GitHub](https://github.com/GuptaAyush19/Vigenere-Cipher) |
| **Discord API Key** | N/A | [Discord Developer Portal](https://docs.discord.com/developers/reference) |

---

### Application Commands

| Command | Type | Description |
|---------|------|-------------|
| `/nexus` | General | Displays an introduction to the bot and its purpose |
| `/david_cipher` | Symmetric | A custom symmetric cipher combining Caesar shift and randomized list shuffling |
| `/rc4` | Symmetric | RC4 stream cipher — a legacy algorithm previously used in TLS/SSL, HTTPS, Wi-Fi WEP, and VPN protocols |
| `/hash_func` | Hashing | Multi-algorithm hash function supporting MD5, SHA-1, SHA-2, SHA-3, SHAKE, and BLAKE families |
| `/morse_decode` | Classical | Decodes a Morse code input string |
| `/tap_code_decode` | Classical | Decodes a Tap code input string |
| `/rail_fence_cipher` | Symmetric | Rail Fence transposition cipher |
| `/random_string_subs_cipher` | Symmetric | Caesar cipher with a randomized shift value |
| `/vigenere_cipher` | Symmetric | Vigenère polyalphabetic substitution cipher |
| `/square_code` | Symmetric | Square Code transposition cipher |
| `/text_book_rsa_key_generation` | Asymmetric | Key derivation for the academic Textbook RSA algorithm |
| `/textbook_rsa_cipher` | Asymmetric | Textbook RSA encryption and decryption |
| `/crypto_rsa_key_generation` | Asymmetric | Key derivation for standard RSA (PKCS#1 OAEP) |
| `/crypto_rsa_pkcs1_oaep_cipher` | Asymmetric | RSA encryption and decryption using PKCS#1 OAEP padding |
| `/crypto_pss_rsa_digital_signature` | Digital Signature | RSA digital signature using PSS padding scheme |
| `/crypto_aes_ocb_key_generation` | Symmetric | Key derivation for AES-OCB (Offset Codebook Mode) — provides both confidentiality and integrity |
| `/crypto_aes_ocb_cipher` | Symmetric | AES encryption and decryption in OCB mode |
| `/crypto_ecc_key_generation` | Asymmetric | Key derivation for Elliptic Curve Cryptography (ECC) |
| `/crypto_ecdsa` | Digital Signature | Elliptic Curve Digital Signature Algorithm (ECDSA) |
| `/clear_nexus_dm_messages` | Utility | Deletes all past direct messages sent by Nexus to the user |

---

## Knight Samson

### Overview

**Knight Samson** is an AI-powered assistant bot that integrates **OpenAI GPT** and **Google Gemini** large language models directly into Discord. In addition to multi-modal AI interactions (text, image, and audio), Samson provides server management utilities including channel message administration and private DM-based conversational AI — all governed by configurable per-member command usage limits.

---

### System Requirements

| Dependency | Version | Source |
|-----------|---------|--------|
| Python | `>= 3.11.0` | [python.org](https://www.python.org/downloads) |
| discord-py | `== 2.5.2` | [GitHub](https://github.com/Rapptz/discord.py) |
| dotenv | `== 0.9.9` | [GitHub](https://github.com/pedroburon/dotenv) |
| openai | `== 2.26.0` | [GitHub](https://github.com/openai/openai-python) |
| google-genai | `== 1.66.0` | [GitHub](https://github.com/googleapis/python-genai) |
| pillow | `== 11.3.0` | [python-pillow.github.io](https://python-pillow.github.io) |
| aiofiles | `== 25.1.0` | [GitHub](https://github.com/Tinche/aiofiles) |
| aiocsv | `== 1.4.0` | [GitHub](https://github.com/MKuranowski/aiocsv) |
| numpy | `== 2.4.4` | [numpy.org](https://numpy.org) |
| pandas | `== 3.0.2` | [pandas.pydata.org](https://pandas.pydata.org) |
| matplotlib | `== 3.10.8` | [matplotlib.org](https://matplotlib.org) |
| **Discord API Key** | N/A | [Discord Developer Portal](https://docs.discord.com/developers/reference) |
| **ScrapeOps API Key** | N/A | [ScrapeOps](https://scrapeops.io) |
| **OpenAI API Key** | N/A | [OpenAI Platform](https://openai.com/api/) |
| **Google Gemini API Key** | N/A | [Google AI Studio](https://ai.google.dev/gemini-api/docs) |

---

### Application Commands

| Command | Description |
|---------|-------------|
| `/samson` | Displays an introduction to the bot and its purpose |
| `/view_application_command_config` | Retrieves the current per-member application command configuration |
| `/application_command_config` | Permanently bans or unbans a member from using specific Samson application commands |
| `/add_command` | Increases or decreases a member's current application command usage allocation |
| `/get_user_list_of_permissions` | Retrieves a complete list of Discord server permissions assigned to a specified member *(Samson must hold a higher server role than the target member)* |
| `/roleplay` | Configures the LLM response style and persona to the user's preference |
| `/clear_last_message` | Deletes the last specified number of messages in a server channel *(requires message deletion permission)* |
| `/clear_all_message` | Deletes all historical messages in a server channel *(requires message deletion permission)* |
| `/clear_user_message` | Deletes the last specified number of messages from a specific user *(requires message deletion permission)* |
| `/direct_message` | Sends a customized direct message to a specified server member *(recipient must have DMs enabled with Samson)* |
| `/clear_samson_dm_messages` | Deletes all past direct messages sent by Samson to the user |
| `/openai_gpt_chat` | Submits a text or image prompt to an OpenAI GPT chat model and returns the model's response |
| `/google_gemini_chat` | Submits a text or image prompt to a Google Gemini chat model and returns the model's response |
| `/openai_gpt_audio` | Submits an audio or text prompt to an OpenAI audio model for processing |
| `/google_gemini_audio` | Submits a text prompt to a Google Gemini TTS model for audio generation *(text prompt only)* |

---

### DM Channel — Contextual AI Conversation

Knight Samson supports private **Direct Message (DM) channel** interactions, functioning as a persistent AI chatbot powered by OpenAI GPT. Conversational context is maintained by chaining the **Latest Response ID** from the preceding exchange, enabling contextually aware multi-turn dialogue.

> **Note:** Enabling conversation context chaining will incrementally increase API token consumption and associated costs with each conversational turn. This should be considered when configuring usage limits for high-volume servers.
