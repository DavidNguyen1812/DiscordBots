from LLMConfigsModule import *
from FileUtilitiesModule import *
from WebSearchModule import *
from AudioScanModule import *
from ImageVideoGifPDFScanModule import *

async def scanningTextOnlyWithLLM(textToBeScanned: str, retryAttempt: int) -> str:
    """
    Description: Scanning text content with LLM model
    :param textToBeScanned: The text content to be scanned
    :param retryAttempt: Current retry attempt
    :return: Scan result
    """
    if retryAttempt >= 3:
        print("3 retry attempts reached! Abandon scan!")
        return "MAX RETRY REACHED"
    systemPrompt = "You are an NSFW moderator on text messages that may also contains URL"
    if LLM_MODEL_PROVIDER == "openai":
        inputPromptTokenCount = (await LLM_ENGINE.responses.input_tokens.count(model=LLM_MODEL_FOR_TEXT_SCAN, instructions=systemPrompt, input=textToBeScanned)).input_tokens
    else:
        inputPromptTokenCount = (await LLM_ENGINE.aio.models.count_tokens(model=LLM_MODEL_FOR_TEXT_SCAN, contents=f"{systemPrompt}\n{textToBeScanned}")).total_tokens
    print(f"Input Tokens: {inputPromptTokenCount}")
    if inputPromptTokenCount > LLM_MODEL_INFORMATION[LLM_MODEL_FOR_TEXT_SCAN]["Maximum Input Tokens"]:
        print("MAXIMUM TOKEN LIMIT")
        return "MAXIMUM TOKEN LIMIT"
    else:
        try:
            if LLM_MODEL_PROVIDER == "openai":
                response = await LLM_ENGINE.responses.create(
                    model=LLM_MODEL_FOR_TEXT_SCAN,
                    instructions=systemPrompt,
                    input=textToBeScanned,
                    max_output_tokens=1000,
                    store=False
                )
                print(f"Output Tokens: {response.usage.output_tokens}")
                ScanResult = response.output_text
            else:
                response = await LLM_ENGINE.aio.interactions.create(
                    model=LLM_MODEL_FOR_TEXT_SCAN,
                    system_instruction=systemPrompt,
                    input=textToBeScanned,
                    generation_config={"max_output_tokens": 1000},
                    store=True
                )
                print(f"Output Tokens: {response.usage.total_output_tokens}")
                ScanResult = response.output_text
            totalCost = await calculateUsageCost(LLM_MODEL_FOR_TEXT_SCAN, response)
            print(f"Total Cost: ${totalCost}")
            return ScanResult
        except openai.RateLimitError as RateLimitError:
            print(f"Rate Limit Error: {RateLimitError}, attempt retry {retryAttempt + 1} in 1 minute")
            await asyncio.sleep(60)
            return await scanningTextOnlyWithLLM(textToBeScanned, retryAttempt + 1)
        except openai.BadRequestError as BadRequestError:
            print(f"Bad Request Error: {BadRequestError}")
            return f"BAD REQUEST ERROR"
        except openai.APITimeoutError as APITimeoutError:
            print(f"API Timeout Error: {APITimeoutError}, attempt retry {retryAttempt + 1} in 1 minute")
            await asyncio.sleep(60)
            return await scanningTextOnlyWithLLM(textToBeScanned, retryAttempt + 1)
        except errors.APIError as GeminiAPIError:
            if GeminiAPIError.code == 429:
                print(f"Rate Limit Error: {GeminiAPIError.message}, attempt retry {retryAttempt + 1} in 1 minute")
                await asyncio.sleep(60)
                return await scanningTextOnlyWithLLM(textToBeScanned, retryAttempt + 1)
            else:
                print(f"GEMINI ERROR: {GeminiAPIError.message}")
                return f"GEMINI ERROR: {GeminiAPIError.message}"
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"


async def NSFWscanMessage(checkMessage: str, URL: bool=False) -> Tuple[bool, str]:  # Return True if text content is NSFW!
    """
    Description: NSFW scan for ASCII content
    :param checkMessage: ASCII content to be scanned
    :param URL: Specify whether the ASCII content is a URL or not
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
                async with aiofiles.open(BLACK_LIST_SUBREDDITS, "a") as file:
                    await file.write(newNSFWsubreddit + '\n')
        if URL:
            return True, "URL contains keywords in Emmanuel default NSFW wordlist!"
        else:
            return True, "Message contains keywords in Emmanuel default NSFW wordlist!"
    print("Profanity Library did not detect, starting LLM scan...")
    scanResult = await scanningTextOnlyWithLLM(
        f"# ASK\n"
        f"Analyze the following message and identify any vulgar or inappropriate words.\n"
        f"# MESSAGE\n"
        f"Message: '{checkMessage}'\n"
        f"# IMPORTANT RULE\n"
        f"1. Consider the context—only, flag words as NSFW if they are being used in an inappropriate or sexual manner or even give hint to it.\n"
        f"2. Taking into measure the text could be written in other language than English.\n"
        f"3. Consider text may be letter emoji or contains a sequence of emojis that can hint NSFW.\n"
        f"4. Check wether the text can be a form of ASCII / Braille art. If it is, then ensure the art does not depict any NSFW content.\n"
        f"# RESPONSE FORMAT\n"
        f"Response MUST start with a Yes or No, follow by a COMMA and EXPLAIN the reason NO MORE THAN 30 WORDS!\n"
    , 0)
    if scanResult.startswith(("Yes", "yes", "YES")):
        print("LLM detected inappropriate content!")
        if redditUrl:
            match = re.search(r'/r/(\w+)', unquote(checkMessage).lower())
            if match:
                newNSFWsubreddit = match.group(1).replace('/r/', '')
                BlackListSubreddits.add(newNSFWsubreddit)
                async with aiofiles.open(BLACK_LIST_SUBREDDITS, "a") as file:
                    await file.write(newNSFWsubreddit + '\n')
        return True, scanResult.strip("Yes,")
    print("LLM scan result is clean!")
    return False, scanResult.strip("No, ")


async def AdvanceBackTrackMessageScan(message: discord.Message) -> None:
    """
    Description: Concatenate the previous 10 message and use a dictionary to check if the concatenation result in a message with NSFW content
    :param message: The most recent message in the server
    :return: None
    """
    if not str(message.channel) == "Direct Message with Unknown User":  # Only use better_profanity
        last10Messages = []
        joined10Messages = ""
        msgRanges = []
        currentIdx = 0
        async for text in message.channel.history(limit=10):
            last10Messages.insert(0, text.content)
        # print(f"Last 10 Messages: {last10Messages}")
        for i, msg in enumerate(last10Messages):
            start = currentIdx
            joined10Messages += msg + " "
            end = currentIdx + len(msg)
            msgRanges.append((start, end, i))
            currentIdx += len(msg) + 1
        # print(f"Last 10 messages range: {msgRanges}")
        # print(f"Lowercase joined last 10 messages: {joined10Messages.lower()}")
        messageToDelete = []
        for word in WordList:
            word = word.strip()
            if not word:
                continue
            charPatterns = [re.escape(char) for char in word]
            spacedWordPattern = r"[\W_]*".join(charPatterns)
            # Ensure strict word boundaries.
            # (?<![a-zA-Z0-9]) = The character before the match cannot be a letter or number
            # (?![a-zA-Z0-9])  = The character after the match cannot be a letter or number
            pattern = rf"(?i)(?<![a-zA-Z0-9]){spacedWordPattern}(?![a-zA-Z0-9])"
            for match in re.finditer(pattern, joined10Messages):
                matchStart, matchEnd = match.span()
                for start, end, msgIdx in msgRanges:
                    if matchStart < end and matchEnd > start:
                        messageToDelete.append(last10Messages[msgIdx])
        if messageToDelete:
            async for text in message.channel.history(limit=10):
                if text.content in messageToDelete:
                    await text.delete()


class TerminateURLScan(Exception):
    pass

async def scanOneURL(url: str, url_base_name: str, url_sha512_hash, message: discord.message.Message) -> AttachmentURLScanResult:
    """Scan URLs concurrently, isolate results and avoid duplicate hash work."""
    async with CONTENT_SCAN_SEMAPHORE:
        needManualReviewContent = {}
        UrlScanStartTime = time.perf_counter()
        logMessage = (f"- **URL:** `{url}`\n"
                      f"- **URL SHA-512 Hash:** `{url_sha512_hash}`\n")
        try:
            async with hashedScanLock("url:" + url_sha512_hash):

                """Checking URL SHA-512 hash"""
                AlreadyInCleanDB = CLEANData.get(url_sha512_hash, '')
                if AlreadyInCleanDB:
                    print("The URL already passed the check as clean!")
                    logMessage += (f"- **Scan Result:** `CLEAN`\n"
                                   f"- **Reason:** `URL hash is in Emmanuel clean record! - {AlreadyInCleanDB}`\n")
                    ScanResult = AttachmentURLScanResult(url, "", 0, "CLEAN", "", logMessage)
                    raise TerminateURLScan

                AlreadyInNSFWDB = NSFWData.get(url_sha512_hash, '')
                if AlreadyInNSFWDB:
                    print("The URL already flagged NSFW! Terminating Scan Process...")
                    logMessage += (f"- **Scan Result:** `NSFW`\n"
                                   f"- **Reason:** `URL hash is in Emmanuel NSFW record! - {AlreadyInNSFWDB}`\n")
                    ScanResult = AttachmentURLScanResult(url, "DOES NOT CHECK", 0, "NSFW", f"{AlreadyInNSFWDB}", logMessage)
                    raise TerminateURLScan

                """Checking hinted NSFW keyword in URL string"""
                print("No existing URL hash in Emmanuel scan database!\nChecking any hinted NSFW words in URL string...")
                scanResult, scanResultDetails = await NSFWscanMessage(url, True)
                if scanResult:
                    logMessage += (f"- **Scan Result:** `NSFW`\n"
                                   f"- **Reason:** `URL string contains NSFW keywords - {scanResultDetails}`\n")
                    ScanResult = AttachmentURLScanResult(url, "DOES NOT CHECK", 0, "NSFW", f"URL string contains NSFW keywords - {scanResultDetails}", logMessage)
                    await AddingNewNSFWData(url_sha512_hash, f"URL string contains NSFW keywords - {scanResultDetails}")
                    raise TerminateURLScan
                print("No hinted NSFW words in URL string!\nBegin fingerprinting the URL bytes content...")

                """Checking User Current Uncensored Limit"""
                print("Checking User Current Uncensored Limit in the Server...")
                async with ConfigLock:
                    if configuration.get(str(message.guild.id), ""):
                        if configuration[str(message.guild.id)]["User-Uncensor-Limit"].get(str(message.author.id), 0) > 1:
                            print("User Uncensor Limit still valid! Terminating Scan Process...")
                            logMessage += (f"- **Scan Result:** `UNVERIFIED`\n"
                                           f"- **Reason:** `User uncensored value still valid to skip Emmanuel scan!`\n")
                            ScanResult = AttachmentURLScanResult("", "", 0, "UNCENSORED","", logMessage)
                            print(f"User {message.author.name} ID {message.author.id} uncensor limit is {configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)]} in server {message.guild.name} ID {message.guild.id}\nFile content is not scanned!!!")
                            configuration[str(message.guild.id)]["User-Uncensor-Limit"][str(message.author.id)] -= 1
                            async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                                await file.write(json.dumps(configuration, indent=4))
                            raise TerminateURLScan
                        print("User Uncensor Value is 0\nEmmanuel can still continue the scan...")

                """Checking URL Content Type"""
                UrlContentExt, UrlContentHashed, FullContentLength, CachedFileBytesContent, error = await hashAttachmentWithoutDownload(url, url_base_name)

                if error:
                    print(f"Error Getting URL content!")
                    logMessage += (f"- **Scan Result:** `Unverified`\n"
                                   f"- **Reason:** `Error getting the URL content!`\n")
                    ScanResult = AttachmentURLScanResult(url, "CAN'T CHEKCH", 0, "MANUAL REVIEW", f"NEED MANUAL REVIEW::Error getting the URL content!::{url_sha512_hash}", logMessage)
                    raise TerminateURLScan

                if CachedFileBytesContent:

                    """Logging URL Content Metadata"""
                    logMessage += (f"- **URL Content Extension Format:** `{UrlContentExt}`\n"
                                   f"- **URL Content Size:** `{FullContentLength:,} bytes`\n"
                                   f"- **URL Content SHA-512 Hash:** `{UrlContentHashed}`\n")
                    print(f"URL Content Extension Format: {UrlContentExt}")
                    print(f"URL Content Size: {FullContentLength:,} bytes")
                    print(f"URL Content SHA-512 Hash: {UrlContentHashed}")

                    """Checking URL Format is in Emmanuel Scope"""
                    if UrlContentExt in ALL_SCANNABLE_FILE_FORMATS:

                        """Checking URL Content SHA-512 hash"""
                        print(f"Checking URL Content SHA-512 Hash against Emmanuel scan database...")
                        AlreadyInCleanDB = CLEANData.get(UrlContentHashed, '')
                        if AlreadyInCleanDB:
                            print("The URL content already passed the check as clean!")
                            logMessage += (f"- **Scan Result:** `CLEAN`\n"
                                           f"- **Reason:** `The URL content already passed the check as clean! - {AlreadyInCleanDB}`\n")
                            ScanResult = AttachmentURLScanResult("", "", 0, "CLEAN", "", logMessage)
                            await AddingNewCleanData(url_sha512_hash, AlreadyInCleanDB)
                            raise TerminateURLScan

                        AlreadyInNSFWDB = NSFWData.get(UrlContentHashed, '')
                        if UrlContentHashed in   AlreadyInNSFWDB:
                            print("The URL content already flagged NSFW! Terminating Scan Process!")
                            logMessage += (f"- **Scan Result:** `NSFW`\n"
                                           f"- **Reason:** `The URL content already flagged NSFW! - {AlreadyInNSFWDB}`\n")
                            ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "NSFW", AlreadyInNSFWDB, logMessage)
                            await AddingNewNSFWData(url_sha512_hash, AlreadyInNSFWDB)
                            raise TerminateURLScan

                        """Prevent duplicate scan of the same attachment"""
                        print(f"URL Content SHA-512 Hash does not exists in Emmanuel scan database!")
                        scanFuture = None
                        scanOwner = False
                        async with HashScanLocksGuard:
                            scanFuture = InFlightFileScans.get(UrlContentHashed)
                            if scanFuture is None:
                                scanFuture = asyncio.get_running_loop().create_future()
                                InFlightFileScans[UrlContentHashed] = scanFuture
                                scanOwner = True
                        if not scanOwner:
                            print(f"URL content {url_base_name} is currently being scanned by other subroutine!")
                            sharedResult = await asyncio.shield(scanFuture)
                            return AttachmentURLScanResult(sharedResult.url, sharedResult.fileExt, sharedResult.fileSize, sharedResult.status, sharedResult.reason, sharedResult.logMessage)

                        try:
                            filePaths = {}
                            async with URL_ATTACHMENT_CONTENT_SCAN_SEMAPHORE:

                                """Save the URL content to disk"""
                                os.makedirs(MAIN_DOWNLOAD_DIR, exist_ok=True)
                                scanDir = await asyncio.to_thread(tempfile.mkdtemp, prefix="EmmanuelScan_", dir=MAIN_DOWNLOAD_DIR)
                                filePaths[url_base_name] = os.path.join(scanDir, f"{url_base_name}")
                                async with aiofiles.open(filePaths[url_base_name], "wb") as file:
                                    await file.write(CachedFileBytesContent)
                                print("Successfully saving URL content as file on disk!")
                                CachedFileBytesContent = None # Empty file content to free up RAM

                                """Checking URL content format to determine scan method"""
                                if UrlContentExt.endswith(SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS):
                                    print("URL content is an archive/disk image file!")
                                    tempScanFolder = os.path.join(scanDir, "MainMountPoint") + os.sep
                                    archiveReportPath = f"{scanDir}/{uuid.uuid4().hex[:7]}archive_scan_report.json"
                                    archiveScanResult = await asyncio.to_thread(ArchivesDiskImagesBombAnalysisAndExtraction, [filePaths[url_base_name]], tempScanFolder, archiveReportPath, UrlContentHashed)
                                    ufs = uncompressedFileStructure(archiveReportPath)
                                    with open(archiveReportPath, "r", encoding="utf-8") as archiveReport:
                                        scanReport = json.load(archiveReport)
                                    uncompressedSize = scanReport.get('uncompressedSize', 0)
                                    totalDuplicatedFile = scanReport.get('totalDuplicatedFile', 0)
                                    totalDuplicatedArchive = scanReport.get('totalDuplicatedArchive', 0)
                                    totalFileCount = scanReport.get('totalFileCount', 0)
                                    notes = scanReport.get('notes', [])
                                    notes[0] = f"\t+ {notes[0]}"
                                    notes = f"{"\n\t+ ".join(notes) if len(notes) > 1 else notes[0]}\n"
                                    logMessage += (
                                            f"- **Archive File Uncompressed Content Size:** `{uncompressedSize:,} bytes`\n"
                                            f"- **Total Duplicated File(s):** `{totalDuplicatedFile:,}`\n"
                                            f"- **Total Duplicated Archive(s):** `{totalDuplicatedArchive:,}`\n"
                                            f"- **Total File Count:** `{totalFileCount:,}`\n"
                                            f"- **Uncompression Progress NOTES:**\n{notes}"
                                            f"- **Uncompressed File Structure:**\n```commandline\n{ufs}\n```\n\n")
                                    os.remove(archiveReportPath)
                                    filePaths = {}
                                    if not archiveScanResult == 'Safe Extraction Complete!':
                                        if archiveScanResult.startswith(("Large Cumulative Uncompressed Size!", "Path Transversal Attack", "Too Much File Count", "Potential Recursive Archive Bomb Attack!", "Too many duplicated files!", "Too Large Nested Archive Content!", "Matryoshka Archive")):
                                            logMessage += f"- **Scan Result:** `SECURITY RISK`\n"
                                            reason = ""
                                            if archiveScanResult.startswith("Large Cumulative Uncompressed Size!"):
                                                uncompressedToCompressedRatio =  archiveScanResult.split(":")[2]
                                                reason = f"The archive/disk file {url_base_name} uncompressed content size was unusually large. The uncompressed size is {uncompressedToCompressedRatio} times the compressed size!"
                                            if archiveScanResult.startswith("Path Transversal Attack"):
                                                reason = f"The archive/disk file {url_base_name} contains a file with a malicious naming scheme. {archiveScanResult.replace('Path Transversal Attack', '')}"
                                            if archiveScanResult.startswith("Too Much File Count"):
                                                reason = f"The archive/disk file {url_base_name} contains a unusual large amount of files! Potential archive/disk image bomb!"
                                            if archiveScanResult.startswith("Potential Recursive Archive Bomb Attack!"):
                                                reason = f"The archive/disk file {url_base_name} contains many other embedded archive/disk image! Potential Recursive Archive Bomb Attack"
                                            if archiveScanResult.startswith("Too many duplicated files!"):
                                                reason = f"The archive/disk file {url_base_name} contains too many duplicated file content! Potential Archive Bomb Attack with useless file content to take up disk and memory space!"
                                            if archiveScanResult.startswith("Too Large Nested Archive Content!"):
                                                reason = f"The archive/disk file {url_base_name} contains another embedded archive with an usual large compressed size! If the embedded archive was to be extracted, the uncompress size would be too large! Potential Archive Bomb!"
                                            if archiveScanResult.startswith("Matryoshka Archive"):
                                                reason = f"The archive/disk file {url_base_name} contains many other embedded archives and disk images! A technique known as Matryoshka Doll to attempt to hide malicious payload in many archive layers!"
                                            logMessage += f"- **Reason:** `{reason}`\n"
                                            await AddingNewNSFWData(UrlContentHashed, reason)
                                            await AddingNewNSFWData(url_sha512_hash, reason)
                                            ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "SECURITY RISK", reason, logMessage)
                                        else:
                                            logMessage += f"- **Scan Result:** `UNVERIFIED`\n"
                                            reason = ""
                                            if archiveScanResult.startswith("Scan Too Long!"):
                                                reason = f"The extract and inspect process of the archive/disk file {url_base_name} took too long! Cyberbot can not verify if the content is malicious or not!"
                                            if archiveScanResult.startswith("Disk Image Too Large!"):
                                                reason = f"The disk image file {url_base_name} too large for Cyberbot to scan! Can not verify if the content is malicious or not!"
                                            if archiveScanResult.startswith("Disk Image Error!"):
                                                reason = f"The disk image file {url_base_name} cannot be extracted or inspected. Can not verify if the content is malicious or not!"
                                            if archiveScanResult.startswith("Encrypted Error"):
                                                reason = f"The archive/disk file {url_base_name} is encrypted and its contents cannot be inspected. Can not verify if the content is malicious or not!"
                                            if archiveScanResult.startswith("Overlay Disk Image Error!"):
                                                reason = archiveScanResult.split(":")[1]
                                            if archiveScanResult.startswith("Empty Disk Image Error!"):
                                                reason = f"The disk image file {url_base_name} is empty!"
                                            if archiveScanResult.startswith("Too Many Snap Shots!"):
                                                reason = f"The disk image file {url_base_name} contains too many snapshots, so Cyberbot can not accurately scan the disk image content!"
                                            logMessage += f"- **Reason:** `{reason}`\n"
                                            ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "UNVERIFIED", reason, logMessage)
                                        raise TerminateURLScan
                                    else:
                                        logMessage += f"## Analyzing Uncompressed File Content Within Scope\n"
                                        for dirpath, _, filenames in os.walk(tempScanFolder):
                                            for filename in filenames:
                                                filePaths[filename] = os.path.join(dirpath, filename)
                                else:
                                    if UrlContentExt.endswith(SUPPORTED_PICTURE_FILE_FORMATS):
                                        print("URL content is an image file!")
                                    elif UrlContentExt.endswith(SUPPORTED_VIDEO_FILE_FORMATS):
                                        print("URL content is a video file!")
                                    elif UrlContentExt.endswith(SUPPORTED_AUDIO_FILE_FORMATS):
                                        print("URL content is an audio file!")
                                    elif UrlContentExt.endswith(SUPPORTED_ASCII_READABLE_FILE_FORMATS):
                                        print("URL content is an ASCII readable file!")

                                """Scanning one file at a time"""
                                for filename, filepath in filePaths.items():
                                    async with URL_ATTACHMENT_CONTENT_SCAN_SEMAPHORE:
                                        try:
                                            print("\n------------------------------------")
                                            HashedFileData = hashlib.sha512()
                                            fileBytesContent = b''
                                            async with aiofiles.open(filepath, "rb") as file:
                                                while True:
                                                    fileBytesChunk = await file.read(CHUNK_SIZE)
                                                    if not fileBytesChunk:
                                                        break
                                                    fileBytesContent += fileBytesChunk
                                                    HashedFileData.update(fileBytesChunk)
                                            HashedFileData = HashedFileData.hexdigest()
                                            fileExt = await asyncio.to_thread(checkingRealFileExtension, fileBytesContent, filename)
                                            fileSize = os.path.getsize(filepath)
                                            if HashedFileData != UrlContentHashed:
                                                logMessage += (f"- **Uncompressed File Name:** `{filename.split("_")[-1]}`\n"
                                                           f"- **Uncompressed File Size:** `{fileSize:,} bytes`\n"
                                                           f"- **Uncompressed File SHA-512 Hash:** `{HashedFileData}`\n"
                                                           f"- **Uncompressed File True Extension:** `{fileExt}`\n")
                                                print(f"Scanning Extracted file {filename} | Format: {fileExt} | Size: {fileSize:,} bytes")
                                            else:
                                                print(f"Scanning URL content as file attachment {filename} | Format: {fileExt} | Size: {fileSize:,} bytes")

                                            scanContinue = True

                                            if HashedFileData != UrlContentHashed:
                                                AlreadyInCleanDB = CLEANData.get(HashedFileData, '')
                                                if AlreadyInCleanDB:
                                                    print("The file content already passed the check as clean!")
                                                    logMessage += (f"- **Scan Result:** `CLEAN`\n"
                                                                  f"- **Reason:** `{AlreadyInCleanDB}`\n")
                                                    scanContinue = False
                                                else:
                                                    AlreadyInNSFWDB = NSFWData.get(HashedFileData, '')
                                                    if AlreadyInNSFWDB:
                                                        print("The URL content already flagged NSFW! Terminating Scan Process!")
                                                        logMessage += (f"- **Scan Result:** `NSFW`\n"
                                                                       f"- **Reason:** `{AlreadyInNSFWDB}`\n")
                                                        ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "NSFW", f"A file content inside the archive/disk image was flagged NSFW - {AlreadyInNSFWDB}", logMessage)
                                                        await AddingNewNSFWData(url_sha512_hash, AlreadyInNSFWDB)
                                                        await AddingNewNSFWData(UrlContentHashed, AlreadyInNSFWDB)
                                                        raise TerminateURLScan

                                            if scanContinue:
                                                if fileExt.endswith(SUPPORTED_ASCII_READABLE_FILE_FORMATS):
                                                    print("File is an ASCII text file...")
                                                    pdfPath = os.path.join(scanDir, f"{filename}.pdf")
                                                    if await asyncio.to_thread(AsciiDocumentToPDFConversion, fileBytesContent, pdfPath):
                                                        NSFWScanResultDetails, logMessage = await scanningPDFPagesWithLLM(pdfPath, logMessage)
                                                        if NSFWScanResultDetails.startswith(("Yes", "yes", "YES")):
                                                            NSFWScanResult = True
                                                        elif NSFWScanResultDetails.startswith("NEED MANUAL REVIEW"):
                                                            if HashedFileData == UrlContentHashed:
                                                                NSFWScanResultDetails = await scanWebContentUsingWebSearchWithLLM(url)
                                                                if NSFWScanResultDetails.startswith(("Yes", "yes", "YES")):
                                                                    NSFWScanResult = True
                                                                else:
                                                                    NSFWScanResult = False
                                                            else:
                                                                NSFWScanResult = False
                                                                logMessage += (f"- **Scan Result:** `Unverified`\n"
                                                                               f"- **Reason:** `LLM scan need manual review!`\n")
                                                                shutil.copy(os.path.join(scanDir, url_base_name), os.path.join(MAIN_DOWNLOAD_DIR, url_base_name))
                                                                shutil.copy(filepath, os.path.join(MAIN_DOWNLOAD_DIR, filename))
                                                                needManualReviewContent.update({
                                                                    url_base_name: {
                                                                        "URL Hash": url_sha512_hash,
                                                                        "URL Content Format": UrlContentExt,
                                                                        "URL Content Hash": UrlContentHashed,
                                                                        "URL Content Size": f"{FullContentLength:,} bytes",
                                                                        "URL Content Path": os.path.join(MAIN_DOWNLOAD_DIR, url_base_name),
                                                                        "Is Archive": True,
                                                                        "File Inside Archive": filename,
                                                                        "File Format": fileExt,
                                                                        "File Hash": HashedFileData,
                                                                        "File Size": f"{fileSize:,} bytes",
                                                                        "File Content Path": os.path.join(MAIN_DOWNLOAD_DIR, filename),
                                                                        "Reason": "LLM scan for the ASCII text content is inconclusive!"
                                                                    }
                                                                })
                                                        else:
                                                            NSFWScanResult = False
                                                        if NSFWScanResult:
                                                            logMessage += (f"- **Scan Result:** `NSFW`\n"
                                                                           f"- **Reason:** `NSFW message content in file - {NSFWScanResultDetails.strip("Yes, ")}`\n")
                                                            if HashedFileData == UrlContentHashed:
                                                                NSFWScanResultDetails = f"NSFW message content in file - {NSFWScanResultDetails.strip("Yes, ")}"
                                                            else:
                                                                NSFWScanResultDetails = f"NSFW message content in file {filename} in archive/disk image file {url_base_name} - {NSFWScanResultDetails.strip("Yes, ")}"
                                                                await AddingNewNSFWData(UrlContentHashed, NSFWScanResultDetails)
                                                            ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "NSFW", NSFWScanResultDetails, logMessage)
                                                            await AddingNewNSFWData(HashedFileData, NSFWScanResultDetails)
                                                            await AddingNewNSFWData(url_sha512_hash, NSFWScanResultDetails)
                                                            raise TerminateURLScan
                                                        else:
                                                            logMessage += (f"- **Scan Result:** `CLEAN`\n"
                                                                           f"- **Reason:** `{NSFWScanResultDetails}`\n")
                                                            await AddingNewCleanData(HashedFileData, NSFWScanResultDetails)
                                                    else:
                                                        logMessage += (f"- **Scan Result:** `Unverified`\n"
                                                                       f"- **Reason:** `Error converting Document ASCCI file to PDF file!`\n")
                                                        shutil.copy(os.path.join(scanDir, url_base_name), os.path.join(MAIN_DOWNLOAD_DIR, url_base_name))
                                                        if HashedFileData == UrlContentHashed:
                                                            needManualReviewContent.update({
                                                                url_base_name: {
                                                                    "URL Hash": url_sha512_hash,
                                                                    "URL Content Format": UrlContentExt,
                                                                    "URL Content Hash": UrlContentHashed,
                                                                    "URL Content Size": f"{FullContentLength:,} bytes",
                                                                    "URL Content Path": os.path.join(MAIN_DOWNLOAD_DIR, url_base_name),
                                                                    "Is Archive": False,
                                                                    "Reason": "Error converting to PDF file for LLM text OCR scan engine to scan accurately!"
                                                                }
                                                            })
                                                        else:
                                                            shutil.copy(filepath, os.path.join(MAIN_DOWNLOAD_DIR, filename))
                                                            needManualReviewContent.update({
                                                                url_base_name: {
                                                                    "URL Hash": url_sha512_hash,
                                                                    "URL Content Format": UrlContentExt,
                                                                    "URL Content Hash": UrlContentHashed,
                                                                    "URL Content Size": f"{FullContentLength:,} bytes",
                                                                    "URL Content Path": os.path.join(MAIN_DOWNLOAD_DIR, url_base_name),
                                                                    "Is Archive": True,
                                                                    "File Inside Archive": filename,
                                                                    "File Format": fileExt,
                                                                    "File Hash": HashedFileData,
                                                                    "File Size": f"{fileSize:,} bytes",
                                                                    "File Content Path": os.path.join(MAIN_DOWNLOAD_DIR, filename),
                                                                    "Reason": "Error converting the extracted file to PDF for LLM text OCR scan engine to scan accurately!"
                                                                }
                                                          })
                                                else:
                                                    NSFWScanResult, NSFWScanResultDetails, logMessage = await ScanningMedia(fileExt, filepath, logMessage)
                                                    if NSFWScanResult:
                                                        logMessage += (f"- **Scan Result:** `NSFW`\n"
                                                                       f"- **Reason:** `{NSFWScanResultDetails}`\n")
                                                        if HashedFileData != UrlContentHashed:
                                                            NSFWScanResultDetails = f"File {filename} in archive/disk image file {url_base_name} was flagged NSFW - {NSFWScanResultDetails}"
                                                            await AddingNewNSFWData(UrlContentHashed, NSFWScanResultDetails)
                                                        ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "NSFW", NSFWScanResultDetails, logMessage)
                                                        await AddingNewNSFWData(HashedFileData, NSFWScanResultDetails)
                                                        await AddingNewNSFWData(url_sha512_hash, NSFWScanResultDetails)
                                                        raise TerminateURLScan
                                                    else:
                                                        if NSFWScanResultDetails.startswith("NEED MANUAL REVIEW"):
                                                            reason = NSFWScanResultDetails.replace("NEED MANUAL REVIEW::", '')
                                                            logMessage += (f"- **Scan Result:** `Unverified`\n"
                                                                           f"- **Reason:** `{reason}`\n")
                                                            shutil.copy(os.path.join(scanDir, url_base_name), os.path.join(MAIN_DOWNLOAD_DIR, url_base_name))
                                                            if HashedFileData == UrlContentHashed:
                                                                needManualReviewContent.update({
                                                                    url_base_name: {
                                                                        "URL Hash": url_sha512_hash,
                                                                        "URL Content Format": UrlContentExt,
                                                                        "URL Content Hash": UrlContentHashed,
                                                                        "URL Content Size": f"{FullContentLength:,} bytes",
                                                                        "URL Content Path": os.path.join(MAIN_DOWNLOAD_DIR, url_base_name),
                                                                        "Is Archive": False,
                                                                        "Reason": reason
                                                                    }
                                                                })
                                                            else:
                                                                shutil.copy(filepath, os.path.join(MAIN_DOWNLOAD_DIR, filename))
                                                                needManualReviewContent.update({
                                                                    url_base_name: {
                                                                        "URL Hash": url_sha512_hash,
                                                                        "URL Content Format": UrlContentExt,
                                                                        "URL Content Hash": UrlContentHashed,
                                                                        "URL Content Size": f"{FullContentLength:,} bytes",
                                                                        "URL Content Path": os.path.join(MAIN_DOWNLOAD_DIR, url_base_name),
                                                                        "Is Archive": True,
                                                                        "File Inside Archive": filename,
                                                                        "File Format": fileExt,
                                                                        "File Hash": HashedFileData,
                                                                        "File Size": f"{fileSize:,} bytes",
                                                                        "File Content Path": os.path.join(MAIN_DOWNLOAD_DIR, filename),
                                                                        "Reason": reason
                                                                    }
                                                              })
                                                        else:
                                                            await AddingNewCleanData(HashedFileData, NSFWScanResultDetails)

                                            print(f"File Scan duration: {time.perf_counter() - UrlScanStartTime:.2f}s")
                                            logMessage += f"- **File Scan Duration In Second(s):** {time.perf_counter() - UrlScanStartTime:.2f}s\n\n---\n\n"
                                            print("------------------------------------\n")
                                        finally:
                                            fileBytesContent = None # Free up file content in RAM
                                if needManualReviewContent:
                                    ScanResult = AttachmentURLScanResult("", "", 0, "MANUAL REVIEW", "", logMessage, needManualReviewContent)
                                else:
                                    if HashedFileData != UrlContentHashed:
                                        await AddingNewCleanData(UrlContentHashed, CLEANData[HashedFileData])
                                    await AddingNewCleanData(url_sha512_hash, CLEANData[HashedFileData])
                                    ScanResult = AttachmentURLScanResult("", "", 0, "CLEAN", "", logMessage)
                        except TerminateURLScan:
                            pass
                        finally:
                            print(f"Cleaning up scan folder {scanDir}")
                            await asyncio.to_thread(shutil.rmtree, scanDir, ignore_errors=True)
                            print(f"Cleaning up success!")
                            if not scanFuture.done():
                                scanFuture.set_result(ScanResult)
                            async with HashScanLocksGuard:
                                if InFlightFileScans.get(UrlContentHashed) is scanFuture:
                                    del InFlightFileScans[UrlContentHashed]
                    else:
                        print("The URL Content Extension Format Outside Emmanuel Scope Of Scan!")
                        logMessage += (f"- **Scan Result:** `Unverified`\n"
                                       f"- **Reason:** `URL Content Extension Format Outside Emmanuel Scope Of Scan!`\n")
                        ScanResult = AttachmentURLScanResult(url, UrlContentExt, FullContentLength, "MANUAL REVIEW", f"NEED MANUAL REVIEW::URL Content Extension Format Outside Emmanuel Scope Of Scan!::{url_sha512_hash}", logMessage)
                else:
                    print("The URL Content Is Empty!")
                    logMessage += (f"- **Scan Result:** `Unverified`\n"
                                   f"- **Reason:** `URL content is empty!`\n")
                    ScanResult = AttachmentURLScanResult(url, "DOES NOT CHECK", 0, "MANUAL REVIEW", f"NEED MANUAL REVIEW::URL content is empty!::{url_sha512_hash}", logMessage)
        except TerminateURLScan:
            pass
        finally:
            print(f"Total Scan duration: {time.perf_counter() - UrlScanStartTime:.2f}s")
            ScanResult.logMessage += f"- **Total Scan Duration In Second(s):** {time.perf_counter() - UrlScanStartTime:.2f}s\n\n---\n\n"
        return ScanResult


async def EmmanuelScan(message: discord.message.Message, isEdit:bool=False, before:discord.message.Message|None=None) -> None:
    """
   Description: Emmanuel main NSFW scanning pipeline
   :param message: The Discord message object
   :param isEdit: Is the message scan a re-edit message or not
   :param before: If the message is re-edited, what was it orignal message
   :return: None
    """

    global FILE_DOWNLOAD_COUNTER
    # Prioritize Executing commands first!
    await Emmanuel.process_commands(message)

    # Add new server to the configuration file!
    try:
        await checkServerExistInConfigFile(str(message.guild.id))
    except AttributeError:
        pass

    if str(message.channel) != "Direct Message with Unknown User":

        if message.author.id == Emmanuel.user.id:
            return
        AttachmentUrls = {}

        """Logging user message"""
        logMessage = (
            f"# {time.ctime(time.time())}\n\n---\n\n"
            f"## Discord Message Origin\n"
            f"- **Origin Author:** `{message.author.name}`\n"
            f"- **Author Discord User ID:** `{message.author.id}`\n"
            f"- **Discord Server:** `{message.guild.name}`\n"
            f"- **Discord Server ID:** `{message.guild.id}`\n"
            f"- **Server Channel:** `{message.channel.name}`\n"
            f"- **Channel ID:** `{message.channel.id}`\n"
        )
        if isEdit: # IMPORTANT: A re-edited message can only be a text content, but user can embed attachment with URL link in re-edited message
            print("User Re-Edit message detected!!!")
            logMessage += (f"- **Re-Edited Message Content:**\n"
                              f"\t+ **Original Message:** `{before.content}`\n"
                              f"\t+ **New Message:** `{message.content}`\n\n")
        else:
            print("User sent message detected!!!")
            if message.content:
                logMessage += f"- **User Message Text Content:** `{message.content}`\n"
            if len(message.attachments) != 0:
                print("Message contains at leat 1 file attachment!")
                logMessage += f"- **User Attached {len(message.attachments)} File Attachment(s):**\n"
                for attachment in message.attachments:
                    logMessage += f"\t+ **File attachment name:** `{attachment.filename}`\n"
                    AttachmentUrls[attachment.url] = [attachment.filename, hashlib.sha512(attachment.url.split('?')[0].encode()).hexdigest()]
            logMessage += "\n"

        if message.author.id in configuration[str(message.guild.id)]["Uncensored-members"]:
            print("User is on the server uncensored list! No scan progress!!!\n\n")
            logMessage += f"\n---\n\n## NOTE: User is on the server uncensored members list!\n\n---\n\n"
            await writingScanLog(logMessage)
            return

        if message.channel.id in configuration[str(message.guild.id)]["Uncensored-channels"]:
            print("Channel is on the server uncensored list! No scan progress!!!\n\n")
            logMessage += f"\n---\n\n## NOTE: The channel is on the server uncensored channels list!\n\n---\n\n"
            await writingScanLog(logMessage)
            return

        continueScan = True
        if message.content:
            textContent = message.content

            """Checking if at least one URL in a message"""
            URLs = URLPATTERN.findall(message.content.replace(" ", ""))

            """Security Inspecting all the URL(s) to prevent SSRF"""
            if URLs:
                print("Message contains URL link(s)! Starting Security inspection on all the URL(s)...")
                URLs = list(set(URLs))
                resolvedUrls, logMessage, textContent, continueScan = await processingUrls(URLs, message, logMessage, textContent)
            else:
                resolvedUrls = {}
            AttachmentUrls.update(resolvedUrls)
        else:
            textContent = ''

        if continueScan:

            """Scanning message text content with hyperlink removed"""
            if textContent:
                textContentScanStartTime = time.perf_counter()
                print(f"Scanning text content with URL already filtered...")
                logMessage += "## Scanning Text Content\n"
                logMessage += f"- **Text Content Being Scanned:** `{textContent}`\n"
                print(f"Text content: {textContent}")
                scanResult, scanResultDetails = await NSFWscanMessage(textContent)
                logMessage += f"- **Total Text Content Scan Duration In Second(s):** {time.perf_counter() - textContentScanStartTime:.2f}s\n"
                if scanResult:
                    logMessage += (f"- **Scan Status:** `NSFW`\n"
                                   f"- **Reason:** `{scanResultDetails}`\n")
                    try:
                        await message.delete()
                        await message.author.send(f"# NSFW TEXT CONTENT\n"
                                                  f"**Your Text Content:** `{message.content}`\n"
                                                  f"**Reason:** `{scanResultDetails}`")
                        logMessage += f"- **DM Notification Sent Status:** `DM message was sent to user to inform why the user message was deleted`"
                    except Exception as error:
                        logMessage += (f"- **DM Notification Sent Status:**\n"
                                       f"\t+ **Error:** `{error}`\n"
                                       f"\t+ **Emmanuel can not send message to inform user why the message was deleted!!!**\n")
                    await writingScanLog(logMessage)
                    await AdvanceBackTrackMessageScan(message)
                    print("Message Content Scan Process Finished!\n\n")
                    return
                else:
                    logMessage += (f"- **Scan Status:** `CLEAN`\n"
                                   f"- **Reason:** `Wordlist check and LLM analysis did not detect any hint of NSFW keywords!`\n")
                    print("Message text content is clean!")
                logMessage += "\n"
            else:
                print("No text content in message!")
            print("Message Text Content Scan Process Finished!\n\n")

            """Begin scanning the URLs, including the attachment URLs"""
            if AttachmentUrls:
                print(f"Scanning URLs and Discord attachment URLs...")
                scanTasks = []
                if AttachmentUrls:
                    logMessage += "## Scanning URL Content\n"
                    for url, urlMetaData in AttachmentUrls.items():
                        scanTasks.append(asyncio.create_task(scanOneURL(url, urlMetaData[0], urlMetaData[1], message)))

                alreadyDeleted = False
                """Checking for completed scan tasks"""
                for completedTask in asyncio.as_completed(scanTasks):
                    result = await completedTask
                    logMessage += result.logMessage
                    if result.status in ["NSFW", "SECURITY RISK"]:
                        if not alreadyDeleted:
                            alreadyDeleted = True
                            try:
                                await message.delete()
                                await message.author.send(f"{'# INAPPROPRIATE ATTACHMENT CONTENT' if result.status == "NSFW" else '# UNSAFE ATTACHMENT CONTENT'}\n"
                                                          f"- **ATTACHMENT URL:** `{result.url}`\n"
                                                          f"- **FROM CHANNEL**: `{message.guild.name} - ID ({message.guild.id})`\n"
                                                          f"- **FROM USER**: `{message.author.name} - ID ({message.author.id})`\n"   
                                                          f"- **ATTACHMENT FORMAT:** `{result.fileExt}`\n"
                                                          f"- **ATTACHMENT SIZE:** `{result.fileSize:,} bytes`\n"
                                                          f"- **REASON:** `{result.reason}`")

                            except Exception as error:
                                logMessage += (f"- **DM Notification Sent Status:**\n"
                                               f"\t+ **Error:** `{error}`\n"
                                               f"\t+ **Emmanuel can not send message to inform user why the message was deleted!!!**\n")
                    if result.status in ["UNVERIFIED", "MANUAL REVIEW"]:
                        if result.status == "UNVERIFIED":
                            await message.author.send(f"# ARCHIVE ATTACHMENT CONTENT CAN NOT BE FULLY SCANNED\n"
                                                      f"- **ATTACHMENT URL:** `{result.url}`\n"
                                                      f"- **FROM CHANNEL**: `{message.guild.name} - ID ({message.guild.id})`\n"
                                                      f"- **FROM USER**: `{message.author.name} - ID ({message.author.id})`\n"  
                                                      f"- **ATTACHMENT FORMAT:** `{result.fileExt}`\n"
                                                      f"- **ATTACHMENT SIZE:** `{result.fileSize:,} bytes`\n"
                                                      f"- **REASON:** `{result.reason}`")
                        else:
                            owner = await Emmanuel.fetch_user(message.channel.guild.owner.id)
                            if result.needManualReviewContent:
                                for url, needManualReviewContent in result.needManualReviewContent.items():
                                    if needManualReviewContent.get("URL Content Path", ''):
                                        files = [discord.File(needManualReviewContent.get("URL Content Path"), filename=os.path.basename(needManualReviewContent.get("URL Content Path")))]
                                    else:
                                        files = []
                                    sendMessage = (f"# NEED MANUAL REVIEW\n"
                                                   f"- **ATTACHMENT URL:** `{url}`\n"
                                                   f"- **FROM CHANNEL**: `{message.guild.name} - ID ({message.guild.id})`\n"
                                                   f"- **FROM USER**: `{message.author.name} - ID ({message.author.id})`\n"
                                                   f"- **ATTACHMENT URL HASH:** `{needManualReviewContent.get("URL Hash")}`\n"
                                                   f"- **ATTACHMENT FORMAT:** `{needManualReviewContent.get("URL Content Format")}`\n"
                                                   f"- **ATTACHMENT SIZE:** `{needManualReviewContent.get("URL Content Size")}`\n"
                                                   f"- **ATTACHMENT HASH:** `{needManualReviewContent.get("URL Content Hash")}`\n")
                                    if needManualReviewContent.get("Is Archive"):
                                        if needManualReviewContent.get("File Content Path", ''):
                                            files.append(discord.File(needManualReviewContent.get("File Content Path"), filename=os.path.basename(needManualReviewContent.get("File Content Path"))))
                                        sendMessage += (f"- **FILE INSIDE ARCHIVE/DISK IMAGE ATTACHMENT:** `{needManualReviewContent.get("File Inside Archive")}`\n"
                                                        f"- **FILE FORMAT:** `{needManualReviewContent.get("File Format")}`\n"
                                                        f"- **FILE HASH:** `{needManualReviewContent.get("File Hash")}`\n"
                                                        f"- **FILE SIZE:** `{needManualReviewContent.get("File Size")}`\n")
                                        PENDING_MANUAL_REVIEW_CONTENT[needManualReviewContent.get("File Hash")] = []
                                        note = f"- **NOTE:** Please use Emmanuel command `/update_emmanuel_scan_database` with the `FILE HASH` value to update Emmanuel scan database after review!"
                                    else:
                                        PENDING_MANUAL_REVIEW_CONTENT[needManualReviewContent.get("URL Hash")] = [needManualReviewContent.get("URL Content Hash")]
                                        note = f"- **NOTE:** Please use Emmanuel command `/update_emmanuel_scan_database` with the `ATTACHMENT URL HASH` value to update Emmanuel scan database after review!"
                                    sendMessage += f"- **REASON:** `{needManualReviewContent.get("Reason")}`\n{note}"
                                    try:
                                        await owner.send(sendMessage, files=files)
                                    except Exception:
                                        pass
                                    finally:
                                        for path in ["URL Content Path", "File Content Path"]:
                                            if os.path.exists(needManualReviewContent.get(path, '')):
                                                os.remove(needManualReviewContent.get(path, ''))
                            else:
                                _, reason, url_hash = result.reason.split("::")
                                PENDING_MANUAL_REVIEW_CONTENT[url_hash] = []
                                sendMessage = (f"# NEED MANUAL REVIEW\n"
                                               f"- **ATTACHMENT URL:** `{result.url}`\n"
                                               f"- **FROM CHANNEL**: `{message.guild.name} - ID ({message.guild.id})`\n"
                                               f"- **FROM USER**: `{message.author.name} - ID ({message.author.id})`\n"
                                               f"- **ATTACHMENT URL HASH:** `{url_hash}`\n"
                                               f"- **ATTACHMENT FORMAT:** `{result.fileExt}`\n"
                                               f"- **ATTACHMENT SIZE:** `{result.fileSize:,} bytes`\n"
                                               f"- **REASON:** `{reason}`\n"
                                               f"- **NOTE:** Please use Emmanuel command `/update_emmanuel_scan_database` with the `ATTACHMENT URL HASH` value to update Emmanuel scan database after review!")
                                try:
                                    await owner.send(sendMessage)
                                except Exception:
                                    pass
                            async with aiofiles.open(PENDING_REVIEW_HASHES, "w") as JSONFile:
                                await JSONFile.write(json.dumps(CLEANData, indent=4))
                await writingScanLog(logMessage)
                await AdvanceBackTrackMessageScan(message)
            print("\n\n")


# Module-local counter used by EmmanuelScan.
FILE_DOWNLOAD_COUNTER = 0
