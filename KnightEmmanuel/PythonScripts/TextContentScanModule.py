from RuntimeConfigsModule import LLM_MODEL_PROVIDER, LLM_ENGINE, LLM_MODEL_FOR_TEXT_SCAN, LLM_MODEL_INFORMATION, REDDITDOMAINS, WORD, SANITIZE, SUBREDDITPATTERN, BlackListDomains, BlackListSubreddits, BLACK_LIST_SUBREDDITS, SUBREDDITPATTERN2, WordList
import asyncio, openai, re, aiofiles, discord
from better_profanity import profanity
from google.genai import errors
from FileUtilitiesModule import calculateUsageCost
from urllib.parse import unquote


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


async def NSFWscanMessage(checkMessage: str, URL: bool=False) -> tuple[bool, str]:  # Return True if text content is NSFW!
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