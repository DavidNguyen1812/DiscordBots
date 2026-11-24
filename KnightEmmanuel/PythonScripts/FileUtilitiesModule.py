import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import aiofiles, hashlib, filetype, magic, mimetypes, requests

from typing import Any
from aiocsv import AsyncWriter
from urllib.parse import urlsplit
from contextlib import asynccontextmanager
from RuntimeConfigsModule import *

CHUNK_SIZE = 65_536  # Partial chunk size to read into RAM.

def plotBarCharts(datasets: list[dict], xLabels: list[str], suptitle: str, savePath: str) -> None:
    """
    Description: Plotting three bar charts representing Total Input Tokens, Total Output Tokens and Total Costs
    :param datasets: The list of all y values for each bar chart
    :param xLabels: The x label for each bar chart
    :param suptitle: The Main Title for all the bar charts
    :param savePath: The path to save the bar charts
    :return: None, the bar charts will be saved in the savePath
    """
    def formatFinalValue(val):
        if val == int(val):
            return f"{int(val):,}"
        else:
            return str(val)
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
        if ds["title"] == "Total Input Tokens":
            title = f"Total Input Tokens: {formatFinalValue(sum(values))} tokens"
        elif ds["title"] == "Total Output Tokens":
            title = f"Total Output Tokens: {formatFinalValue(sum(values))} tokens"
        else:
            title = f"Total Cost: ${formatFinalValue(round(sum(values), 5))}"
        ax.set_title(title, fontsize=13, fontweight="bold", color="#1E2A3A", pad=8, loc="left")
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


def plotModelCalls(LLMModels: list[str], LLMModelUses: list[int], savePath: str):
    """
    Description: Plotting a single bar chart showing the total calls per LLM models each month
    :param LLMModels: The list of all the LLM models that has been used at least one
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
    Description: Executing read and write only operation on the csv files related to logging Emmanuel LLM Usage
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


async def calculateUsageCost(model: str, LLMResponse: Any, webSearch: bool=False) -> float:
    """
    Description: Calculate the usage cost of the LLM model based on the model response. If successful, the usage data is updated.
    :param model: LLM Model
    :param LLMResponse: The LLM response Object
    :param webSearch: Whether or not if web search tool was called
    :return: The final calculated usage cost
    """
    if LLM_MODEL_PROVIDER == "openai":
        if getattr(LLMResponse, "usage", None):
            if getattr(LLMResponse.usage, "type", None): # Audio Transcribe Response
                if LLMResponse.usage.type == 'duration':
                    if getattr(LLMResponse.usage, "seconds", None):
                        totalCost = (LLMResponse.usage.seconds / 60) * 0.0045 # OpenAI charges based on the audio duration at 0.0045/minute
                        totalCost = round(totalCost, 5)
                        await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMMonthlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", 0, 0, model, totalCost], MonthlyCSVLock)
                        await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMYearlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", 0, 0, model, totalCost], YearlyCSVLock)
                        return totalCost
                    else:
                        print(f"LLM Model {model} response usage type is duration but no seconds value was provided! Can't update LLM Usage data!")
                        return 0.0
                else:
                    print(f"Can't determine LLM Model {model} response usage type! Can't update LLM Usage data!")
                    return 0.0
            else:
                totalInputTokens = LLMResponse.usage.input_tokens
                totalOutputTokens = LLMResponse.usage.output_tokens
                inputTokenCostIndex = 1 if totalInputTokens > 272000 else 0
                outputTokenCostIndex = 1 if totalOutputTokens > 272000 else 0

                if getattr(LLMResponse.usage, "input_tokens_details", None):
                    if getattr(LLMResponse.usage.input_tokens_details, "cached_tokens", None):
                        totalCachedReadTokens = LLMResponse.usage.input_tokens_details.cached_tokens
                    else:
                        totalCachedReadTokens = 0
                    if getattr(LLMResponse.usage.input_tokens_details, "cached_write_tokens", None):
                        totalCachedWriteTokens = LLMResponse.usage.input_tokens_details.cached_write_tokens
                    else:
                        totalCachedWriteTokens = 0
                else:
                    totalCachedReadTokens = 0
                    totalCachedWriteTokens = 0

                totalRawInputTokens = totalInputTokens - (totalCachedReadTokens + totalCachedWriteTokens)

                totalRawInputTokenCost = (totalRawInputTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Input Token"][inputTokenCostIndex]
                totalCachedReadTokenCost = (totalCachedReadTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Cached Read"][inputTokenCostIndex]
                totalCachedWriteTokenCost = (totalCachedWriteTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Cached Writes"][inputTokenCostIndex]
                totalOutputTokenCost = (totalOutputTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Output Token"][outputTokenCostIndex]
                totalCost = totalRawInputTokenCost + totalCachedReadTokenCost + totalCachedWriteTokenCost + totalOutputTokenCost
                if webSearch:
                    totalCost += 0.1 # OpenAI Web Search cost $10/1K request
                totalCost = round(totalCost, 5)
                await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMMonthlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", totalInputTokens, totalOutputTokens, model, totalCost], MonthlyCSVLock)
                await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMYearlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", totalInputTokens, totalOutputTokens, model, totalCost], YearlyCSVLock)
                return totalCost
        else:
            print(f"LLM Model {model} response has no usage attribute! Can't update LLM Usage data!")
            return 0.0
    else:
        # NOTE: Gemini url_context tool call does not cost additional fee!
        if getattr(LLMResponse, "usage", None):
            totalInputTokens = LLMResponse.usage.total_input_tokens
            totalOutputTokens = LLMResponse.usage.total_output_tokens
            if getattr(LLMResponse.usage, "total_cached_tokens", None):
                totalCachedReadTokens = LLMResponse.usage.total_cached_tokens
            else:
                totalCachedReadTokens = 0
            totalRawInputTokens = totalInputTokens - totalCachedReadTokens
            totalRawInputTokenCost = (totalRawInputTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Input Token"][0]
            totalCachedReadTokenCost = (totalCachedReadTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Cached Read"][0]
            totalOutputTokenCost = (totalOutputTokens / 1000000) * LLM_MODEL_INFORMATION[model]["Cost"]["Output Token"][0]
            totalCost = totalRawInputTokenCost + totalCachedReadTokenCost + totalOutputTokenCost
            totalCost = round(totalCost, 5)
            await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMMonthlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", totalInputTokens, totalOutputTokens, model, totalCost], MonthlyCSVLock)
            await writingLLMUsageCsv(f"{LLM_USAGE_LOG}LLMYearlyUsage.csv", "a", [f"{time.ctime(time.time()).split()[1]} {time.ctime(time.time()).split()[2]}", totalInputTokens, totalOutputTokens, model, totalCost], YearlyCSVLock)
            return totalCost
        else:
            print(f"LLM Model {model} response has no usage attribute! Can't update LLM Usage data!")
            return 0.0


async def writingScanLog(logData: str) -> None:
    """
    Description: Writing scanning log Emmanuel log file
    :param logData: Log content to be written
    :return: None
    """
    async with LogLock:
        async with aiofiles.open(EMMANUEL_SCAN_LOG, "a") as txtFile:
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
        print(f"SHA-512 {Hash} passed the check, Adding to clean data...")
        async with aiofiles.open(CLEAN_JSON_DB, "w") as JSONFile:
            await JSONFile.write(json.dumps(CLEANData, indent=4))
        print(f"Clean data updated!")


async def AddingNewNSFWData(Hash: str, Reason: str) -> None:
    """
    Description: Adding new SHA512 hash to Emmanuel NSFW data JSON file and the reason
    :param Hash: SHA512 hash to be added
    :param Reason: Reason why the hash was added to the NSFW content
    :return: None
    """
    async with NSFWDataLock:
        NSFWData[Hash] = Reason
        print(f"SHA-512 {Hash} was flagged NSFW, adding to NSFW data...")
        async with aiofiles.open(NSFW_JSON_DB, "w") as JSONFile:
            await JSONFile.write(json.dumps(NSFWData, indent=4))
        print(f"NSFW data updated!")


async def checkServerExistInConfigFile(serverID: str) -> None:
    """
    Description: Check if a server ID already exists in configuration file
    :param serverID: The server ID to be checked
    :return: Nothing is returned. If the server ID does not exist in the configuration file, then it will be automatically created with all the default values.
    """
    async with CheckServerExistLock:
        if configuration.get(serverID, None) is None:
            configuration[serverID] = {}
            configuration[serverID]["Uncensored-members"] = WHITE_LIST_MEMBERS
            configuration[serverID]["Uncensored-channels"] = []
            members = {}
            server = await Emmanuel.fetch_guild(int(serverID))
            async for member in server.fetch_members(limit=None):
                if member.id not in WHITE_LIST_MEMBERS:
                    members[str(member.id)] = DAILY_UNCENSOR_LIMIT
            configuration[serverID]["User-Uncensor-Limit"] = members
            async with ConfigLock:
                async with aiofiles.open(EMMANUEL_CONFIG, "w") as file:
                    await file.write(json.dumps(configuration, indent=4))
            print(f"New server ID {serverID} added to config file!\n\n")


async def hashAttachmentWithoutDownload(attachmentUrl: str, urlName: str) -> tuple[str, str, int, bytes | None, bool]:
    """
    Description: Read attachment over HTTPS in bounded chunks without storing content on disk.
    :param attachmentUrl: The URL to GET the attachment content
    :param urlName: The name of the attachment
    :return The file content extension, SHA-512 hash, full content length, full file bytes content currently stored in memory or not and final destination URL and Error getting the attachment content or not
    """
    FullContentLength = 0
    fileHashed = hashlib.sha512()
    fileBytesChunks = []
    parts =urlsplit(attachmentUrl)
    async with FILE_HASH_SEMAPHORE:
        async with Emmanuel.session.get(attachmentUrl, allow_redirects=False) as response:
            if response.status not in range(200, 399):
                if parts.hostname.lower() in ['cdn.discordapp.com', 'media.discordapp.net'] and parts.port in (None, 443) and parts.username is None and parts.path.startswith('/attachments/'):
                    print("Discord Attachment URL can't be retrieved! Begin refreshing the URL...")
                    Headers = {"Authorization": f"Bot {DISCORD_API}"}
                    Payload = {"attachment_urls": [attachmentUrl]}
                    async with Emmanuel.session.post("https://discord.com/api/v10/attachments/refresh-urls", headers=Headers, json=Payload) as refreshResponse:
                        if refreshResponse.status != 200:
                            print("Shit! Can't refresh Discord URL")
                            return '', '', 0, None, True
                        refreshResponseData = await refreshResponse.json()
                    try:
                        downloadURL =  refreshResponseData["refreshed_urls"][0]["refreshed"]
                    except Exception :
                        print("Shit! Can't get the refresh Discord URL")
                        return '', '', 0, None, True
                    print("Successfully getting the refreshed Discord attachment URL!")
                else:
                    print("Can't GET URL content")
                    return '', '', 0, None, True
            else:
                downloadURL = attachmentUrl
    async with Emmanuel.session.get(downloadURL, allow_redirects=False) as response:
        async for fileBytesContent in response.content.iter_chunked(CHUNK_SIZE):
            FullContentLength += len(fileBytesContent)
            fileHashed.update(fileBytesContent)
            if FullContentLength:
                fileBytesChunks.append(fileBytesContent)
    fileBytesContent = b"".join(fileBytesChunks)
    if fileBytesContent:
        fileExt = await asyncio.to_thread(checkingRealFileExtension, fileBytesContent, urlName)
    else:
        fileExt = ''

    return fileExt, fileHashed.hexdigest(), FullContentLength, b"".join(fileBytesChunks), False


@asynccontextmanager
async def hashedScanLock(URLHashed: str):
    """
    Description: Prevent duplicate scan on the same Attachment URL
    :param URLHashed: The hash of the URL currently being scanned
    :return: None
    """
    async with HashScanLocksGuard:
        if URLHashed not in HashScanLocks:
            HashScanLocks[URLHashed] = [asyncio.Lock(), 0]
        scanLock, _ = HashScanLocks[URLHashed]
        HashScanLocks[URLHashed][1] += 1
    try:
        async with scanLock:
            yield
    finally:
        async with HashScanLocksGuard:
            HashScanLocks[URLHashed][1] -= 1
            if HashScanLocks[URLHashed][1] == 0:
                del HashScanLocks[URLHashed]


def checkingRealFileExtension(fileContent: bytes, fname: str, verbose: bool = True):
    """Checking extension by it bytes content in RAM"""
    if verbose:
        print(f"Starting Python-Magic module...")
    mime = magic.from_buffer(fileContent, mime=True)
    Ext = mimetypes.guess_extension(mime)
    if Ext:
        if Ext == ".bin":
            if fileContent[1:4] == b'\64\73\73':
                if verbose:
                    print(f"Detected file extension .dss")
                return '.dss'
            if fileContent.startswith(b'PK'):
                if verbose:
                    print(f"Detected file extension .zip")
                return '.zip'
            if fileContent.startswith(b'caff'):
                if verbose:
                    print(f"Detected file extension .caf")
                return '.caf'
            if len(fileContent) > 512:
                Last512bytes = fileContent[-512:]
                if b'conectix' in Last512bytes:
                    if verbose:
                        print(f"Detected file extension .vhd")
                    return '.vhd'
                if b'koly' in Last512bytes or Last512bytes.startswith(b'EFI PART') or fileContent.startswith(b'EFI PART'):
                    if verbose:
                        print(f"Detected file extension .dmg")
                    return '.dmg'
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
            print(f"Python-Magic can't determine file extension!")
        print("Manual inspecting content header bytes....")
        if fileContent.startswith(
                (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
                 b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')):
            if verbose:
                print("File extension is Mach-O executable!")
            return "Mach-O executable"
        if fileContent.startswith(b'\x7f\x45\x4c\x46'):
            if verbose:
                print("File extension is ELF (Executable and Linkable Format)!")
            return "ELF executable"
        if fileContent.startswith(b'QFI\xfb'):
            if verbose:
                print(f"Detected file extension .qcow2")
            return ".qcow2"
        if fileContent.startswith(b'vhdxfile'):
            if verbose:
                print(f"Detected file extension .vhdx")
            return ".vhdx"
        if fileContent.startswith(b'KDMV'):
            if verbose:
                print(f"Detected file extension .vmdk")
            return ".vmdk"
        if len(fileContent) >= 32768:
            if fileContent[32768:32768 + 5].startswith((b"NSR02", b"NSR03")):
                if verbose:
                    print(f"Detected file extension .udf")
                return '.udf'
        try:
            if fileContent.decode("ascii").isascii():
                if verbose:
                    print(f"ASCII file detected")
                return ".txt"
        except UnicodeDecodeError:
            if verbose:
                print("Manual inspection can't determine file extension!")
                print(f"Starting filetype module...")
            Ext = filetype.guess(fileContent)
            if Ext:
                if verbose:
                    print(f"Filetype detected file extension {Ext.extension}")
                return f".{Ext.extension}"
            else:
                first100BytesHex = fileContent[:100].hex()
                if first100BytesHex.startswith("5d0000"):
                    if verbose:
                        print(f"Detected file extension .lzma")
                    return ".lzma"
                else:
                    try:
                        # https://filesignature.org/api
                        if verbose:
                            print(f"filetype module can't determine file extension!")
                            print(f"Starting filesignature.org /identify search...")
                        response = requests.get("https://filesignature.org/api/v1/identify", params={"hex": first100BytesHex}, timeout=30)
                        response.raise_for_status()
                        result = response.json()
                        if not result.get("success"):
                            raise ValueError(result.get("error", "File identification failed"))
                        else:
                            analysisData = result.get("data", {})
                            if analysisData:
                                analysisDataVerdict = analysisData.get("matches", [])
                                if analysisDataVerdict:
                                    analysisDataVerdict = analysisDataVerdict[0]
                                    fileExtension = analysisDataVerdict.get("ext", "")
                                    if fileExtension:
                                        if verbose:
                                            print(f"filesignature.org detected file extension {fileExtension}")
                                        return f".{fileExtension}"
                                    else:
                                        if verbose:
                                            print(f"filesignature.org can't determine file extension!")
                                else:
                                    raise ValueError("Empty Final Analysis Verdict Data")
                            else:
                                raise ValueError("Empty Analysis Data")
                    except Exception as e:
                        print(f"Error: {str(e)}")
        if verbose:
            print(f"File extension can not be determined!")
        return "Can't be determined"
