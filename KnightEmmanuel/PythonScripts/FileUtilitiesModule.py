from AudioScanModule import *

async def scanningImageWithNudenet(image: str) -> bool:
    """
    Description: Scanning image with Nudenet pre-train NSFW model
    :param image: Path to the image on disk
    :return: Scan result of whether the image is NSFW or not
    """
    detections = await asyncio.to_thread(detector.detect, image)
    print(f"Nudenet scan results: {detections}")
    for result in detections:
        if result['class'] in SEXUAL_TAGS:
            if result['score'] > 0.53:
                return True
    return False


def _getPDFMetadata(PDFFilePath: str) -> tuple[int, int]:
    """
    Description: Retrieve PDF metadata.
    :param PDFFilePath: PDF file path.
    :return: Total PDF pages and file size in bytes.
    """
    with open(PDFFilePath, "rb") as PDFFile:
        PDFReader = PdfReader(PDFFile, strict=False)

        if PDFReader.is_encrypted:
            raise ValueError(
                "Encrypted PDF detected. PDF password is required."
            )

        PDFPageCount = len(PDFReader.pages)

    PDFFileSize = os.path.getsize(PDFFilePath)

    return PDFPageCount, PDFFileSize


def _segmentPDFToBase64(PDFReader: PdfReader, PDFPageCount: int, pagesPerSegment: int = 200) -> dict:
    """
    Description: Segment a PDF into smaller PDF documents and convert them to Base64
    :param PDFReader: The PdfReader object of the original PDF file
    :param PDFPageCount: The total number of pages of the original PDF file
    :param pagesPerSegment: Number of pages per segment
    :return: Base64 data string of each PDF segments
    """
    PDFBase64Datas = {}
    try:
        for startPage in range(0, PDFPageCount, pagesPerSegment):
            endPage = min(startPage + pagesPerSegment, PDFPageCount)
            PDFWriter = PdfWriter()
            for pageIndex in range(startPage, endPage):
                PDFWriter.add_page(PDFReader.pages[pageIndex])
            with io.BytesIO() as PDFBuffer:
                PDFWriter.write(PDFBuffer)
                PDFSegmentBytes = PDFBuffer.getvalue()
            PDFSegmentBase64 = base64.b64encode(PDFSegmentBytes).decode("ascii")
            PDFBase64Datas[f"Pages {startPage + 1} to {endPage}"] = PDFSegmentBase64
            print(f"Successfully obtained Base64 data for PDF pages {startPage + 1} to {endPage}")
        return PDFBase64Datas
    except Exception as e:
        print(f"Encountering error while segmenting the PDF pages: {e}")
        return {}

'''
IMPORTANT NOTE:

OpenAI only accept up to 50 MB file data per Response API request.
Google Gemini accept up to 100 MB file data per Interactions API request. For PDF, it's only 50 MB and 1,000 pages.
'''
async def scanningPDFPagesWithLLM(pdfPath: str, logMessage: str) ->Tuple[str, str]:
    """
    Description: Scanning PDF frames with a selected LLM model
    :param pdfPath: The path to the PDF file
    :param logMessage: The current log message
    :return: Scan result and the updated log message
    """
    logMessage += f"\t + **Begin Scanning PDF pages with {LLM_MODEL_FOR_IMAGE_SCAN}**\n"
    systemPrompt = "You are an NSFW content moderator"
    prompt = ("# ASK\n"
              "Is the following PDF pages have any nude elements, vulgar language, hateful slur, sexual theme, the exposure of animal genitalia,"
              " animal porn, reference to adult or NSFW websites, or even consider NSFW?\n"
              "# IMPORTANT RULE\n"
              "Please taking into account that people in light clothing like thongs and bikini SHOULD BE consider NSFW!\n"
              "# RESPONSE FORMAT\n"
              "Response MUST start with a Yes or No then follow by a COMMA and EXPLAIN the reason NO MORE THAN 30 WORDS!"
              )
    PDFBase64Datas = {}
    PDFsize = await asyncio.to_thread(os.path.getsize, pdfPath)
    PDFReader = await asyncio.to_thread(PdfReader, pdfPath, strict=False)
    PDFPageCount = len(PDFReader.pages)
    logMessage += (f"\t\t + **PDF Total Size:** {PDFsize:,} bytes\n"
                   f"\t\t + **PDF Total Pages:** {PDFPageCount:,} pages\n")
    segmentPDF = False
    if PDFsize > 50000000 or PDFPageCount > 1000:
        segmentPDF = True
        if PDFsize > 50000000:
            print("PDF file size exceeds 50 MB!")
            logMessage += f"\t\t + **PDF File Size exceed 50 MB, scanning PDF by page segments**\n"
        else:
            print("PDF pages exceed 1000 pages!")
            logMessage += f"\t\t + **PDF Total Pages exceed 1,000 pages, scanning PDF by page segments**\n"

    print(f"Checking if request will exceed {LLM_MODEL_FOR_IMAGE_SCAN} context windows...")
    async with aiofiles.open(pdfPath, "rb") as PDFfile:
        PDFBase64Data = (await asyncio.to_thread(base64.b64encode, await PDFfile.read())).decode('utf-8')
        await PDFfile.seek(0)
        if LLM_MODEL_PROVIDER == "openai":
            inputTokenCountRequestQuery = [{"role": "user", "content": [{"type": "input_file", "filename": f"{uuid.uuid4().hex[0:5]}.pdf", "file_data": f"data:application/pdf;base64,{PDFBase64Data}"}, {"type": "input_text", "text": prompt}]}]
            inputPromptTokenCount = (await LLM_ENGINE.responses.input_tokens.count(model=LLM_MODEL_FOR_IMAGE_SCAN, instructions=systemPrompt, input=inputTokenCountRequestQuery)).input_tokens
        else:
            inputTokenCountRequestQuery = types.Content(role="user", parts=[types.Part.from_bytes(data= await PDFfile.read(), mime_type="application/pdf"), types.Part.from_text(text=f"{systemPrompt}\n{prompt}")])
            inputPromptTokenCount = (await LLM_ENGINE.aio.models.count_tokens(model=LLM_MODEL_FOR_IMAGE_SCAN, contents=inputTokenCountRequestQuery)).total_tokens
    print(f"Pre-Request Input Tokens: {inputPromptTokenCount}")
    logMessage += f"\t\t + **Pre-Request Input Token Count:** `{inputPromptTokenCount:,} tokens`\n"
    if inputPromptTokenCount > LLM_MODEL_INFORMATION[LLM_MODEL_FOR_IMAGE_SCAN]["Maximum Input Tokens"]:
        segmentPDF = True
        print(f"Request inputs will exceed {LLM_MODEL_FOR_IMAGE_SCAN} context windows!")
        logMessage += f"\t\t + **Input Token Count Exceed {LLM_MODEL_FOR_IMAGE_SCAN} Context Window, scanning PDF by page segments**\n"

    if segmentPDF:
        print("Begin finding the most optimized PDF segment value for partial scan!")
        contextWindowLimit = LLM_MODEL_INFORMATION[LLM_MODEL_FOR_IMAGE_SCAN][ "Maximum Input Tokens"]
        pageSegment = PDFPageCount
        segmentSize = PDFsize
        while inputPromptTokenCount >= contextWindowLimit or pageSegment > 1000 or segmentSize > 50000000:
            pageSegment = math.floor(pageSegment * 0.9)
            print(f"Testing PDF segment value of {pageSegment} pages")
            if (LLM_MODEL_PROVIDER == "google-gemini" and pageSegment < 1000) or LLM_MODEL_PROVIDER == "openai":
                logMessage += f"\t\t + **Testing Input Token Count For Segment Value {pageSegment}**\n"
                PDFWriter = PdfWriter()
                for pageIndex in range(0, pageSegment):
                    PDFWriter.add_page(PDFReader.pages[pageIndex])
                with io.BytesIO() as PDFBuffer:
                    PDFWriter.write(PDFBuffer)
                    PDFSegmentBytes = PDFBuffer.getvalue()
                segmentSize = len(PDFSegmentBytes)
                PDFSegmentBase64 = base64.b64encode(PDFSegmentBytes).decode("utf-8")
                if LLM_MODEL_PROVIDER == "openai":
                    inputTokenCountRequestQuery = [{"role": "user", "content": [{"type": "input_file", "filename": f"{uuid.uuid4().hex[0:5]}.pdf", "file_data": f"data:application/pdf;base64,{PDFSegmentBase64}"}, {"type": "input_text", "text": prompt}]}]
                    inputPromptTokenCount = (await LLM_ENGINE.responses.input_tokens.count(model=LLM_MODEL_FOR_IMAGE_SCAN, instructions=systemPrompt, input=inputTokenCountRequestQuery)).input_tokens
                else:
                    inputTokenCountRequestQuery = types.Content(role="user", parts=[types.Part.from_bytes(data=PDFSegmentBytes, mime_type="application/pdf"), types.Part.from_text(text=f"{systemPrompt}\n{prompt}")])
                    inputPromptTokenCount = (await LLM_ENGINE.aio.models.count_tokens(model=LLM_MODEL_FOR_IMAGE_SCAN, contents=inputTokenCountRequestQuery)).total_tokens
                print(f"Input Token Count For The Segment Value: {inputPromptTokenCount:,}")
                print(f"Total Size For The Segment Value: {segmentSize:,} bytes")
                logMessage += (f"\t\t\t + **Total Input Token Count:** `{inputPromptTokenCount:,}`\n"
                               f"\t\t\t + **Total Size:** `{segmentSize:,} bytes`\n")

        print(f"The optimal PDF segment value is: {pageSegment}")
        logMessage += f"\t\t + **Optimal PDF segment value is:** {pageSegment:,}\n"
        PDFBase64Datas = await asyncio.to_thread(_segmentPDFToBase64, PDFReader, PDFPageCount, pageSegment)
    else:
        PDFBase64Datas["Full PDF Pages"] = PDFBase64Data

    print(f"Start scanning PDF frames with LLM model {LLM_MODEL_FOR_IMAGE_SCAN}")
    for segment, PDFBase64Data in PDFBase64Datas.items():
        print("\n----------------------------------------")
        print(f"Scanning PDF segment: {segment}")
        logMessage += f"\t\t\t + **PDF Segment: {segment}**\n"
        pdfScanResult = ""
        for retryAttempt in range(0, 3):

            print(f"Attempt #{retryAttempt + 1}")
            logMessage += f"\t\t\t + **LLM request attempt:** `{retryAttempt + 1}`\n"
            if LLM_MODEL_PROVIDER == "openai":
                requestQuery = [{"role": "user", "content": [{"type": "input_file", "filename": f"{uuid.uuid4().hex[0:5]}.pdf", "file_data": f"data:application/pdf;base64,{PDFBase64Data}"}, {"type": "input_text", "text": prompt}]}]
            else:
                requestQuery = [{"type": "document", "data": PDFBase64Data, "mime_type": "application/pdf"}, {"type": "text", "text": prompt}]

            try:
                if LLM_MODEL_PROVIDER == "openai":
                    # https://developers.openai.com/api/reference/resources/responses/methods/create/
                    response = await LLM_ENGINE.responses.create(model=LLM_MODEL_FOR_IMAGE_SCAN, instructions=systemPrompt, input=requestQuery, max_output_tokens=2000, store=False)
                    print(f"Input Tokens: {response.usage.input_tokens}")
                    print(f"Output Tokens: {response.usage.output_tokens}")
                    logMessage += (f"\t\t\t + **Input Token Count:** `{response.usage.input_tokens:,} tokens`\n"
                                   f"\t\t\t + **Output Token Count:** `{response.usage.output_tokens:,} tokens`\n")
                else:
                    # https://aistudio.google.com/api-reference/interactions-api/create-interaction
                    response = await LLM_ENGINE.aio.interactions.create(model=LLM_MODEL_FOR_IMAGE_SCAN, input=requestQuery, system_instruction=systemPrompt, generation_config={"max_output_tokens": 2000}, store=True)
                    print(f"Input Tokens: {response.usage.total_input_tokens}")
                    print(f"Output Tokens: {response.usage.total_output_tokens}")
                    logMessage += (f"\t\t\t + **Input Token Count:** `{response.usage.total_input_tokens:,} tokens`\n"
                                   f"\t\t\t + **Output Token Count:** `{response.usage.total_output_tokens:,} tokens`\n")
                pdfScanResult = response.output_text
                print(f"{LLM_MODEL_FOR_IMAGE_SCAN} image NSFW scan results: {pdfScanResult}")
                totalCost = await calculateUsageCost(LLM_MODEL_FOR_IMAGE_SCAN, response)
                print(f"Total Cost: ${totalCost}")
                logMessage += f"\t\t\t + **Total Cost:** `${totalCost}`\n"
                logMessage += f"\t\t\t + **PDF NSFW Scan Results:** `{pdfScanResult}`\n"
                if pdfScanResult:
                    if pdfScanResult.startswith(("Yes", "yes", "YES")):
                        return pdfScanResult, logMessage # Return NSFW report upon an NSFW response
                    else:
                        break
                else:
                    return f"NEED MANUAL REVIEW::Model {LLM_MODEL_FOR_IMAGE_SCAN} RETURN EMPTY RESPONSE", logMessage

            except (openai.RateLimitError, openai.APITimeoutError) as Error:
                print(f"Rate Limit/API Timeout Error: {Error}, attempt retry {retryAttempt + 1} in 1 minute")
                logMessage += f"\t\t\t + **Rate Limit Error:** `{Error}`\n"
                await asyncio.sleep(60)

            except openai.BadRequestError as BadRequestError:
                print(f"Bad Request Error: {BadRequestError}")
                logMessage += f"\t\t\t + **Bad Request Error:** `{BadRequestError}`\n"
                return f"NEED MANUAL REVIEW::Model {LLM_MODEL_FOR_IMAGE_SCAN} API BAD REQUEST ERROR {BadRequestError}", logMessage

            except errors.APIError as GeminiAPIError:
                if GeminiAPIError.code == 429:
                    print(f"Rate Limit Error: {GeminiAPIError.message}, attempt retry {retryAttempt + 1} in 1 minute")
                    logMessage += f"\t\t\t + **Rate Limit Error:** `{GeminiAPIError.message}`\n"
                    await asyncio.sleep(60)
                else:
                    print(f"Error: {GeminiAPIError.message}")
                    logMessage += f"\t\t\t + **LLM Request Error:** `{GeminiAPIError.message}`\n"
                    return f"NEED MANUAL REVIEW::Model {LLM_MODEL_FOR_IMAGE_SCAN} BAD REQUEST ERROR {GeminiAPIError.message}", logMessage

            except Exception as e:
                print(f"Receive Error: {e}")
                logMessage += f"\t\t\t + **LLM Request Error:** `{e}`\n"
                return f"NEED MANUAL REVIEW::Model {LLM_MODEL_FOR_IMAGE_SCAN} ERROR {e}", logMessage

            finally:
                print("----------------------------------------\n")
        if not pdfScanResult:
            print(f"Too Many Retry Attempts!")
            logMessage += f"\t\t\t + **Too Many Retry Attempts!**\n"
            return f"NEED MANUAL REVIEW::Model {LLM_MODEL_FOR_IMAGE_SCAN} ATTEMPT TOO MANY RETRIES!", logMessage
    return f"Final Scan Result: {pdfScanResult}", logMessage # Return the last clean scan result


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
    elif filePath.endswith(SUPPORTED_VIDEO_FILE_FORMATS):
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


def AsciiDocumentToPDFConversion(fileData: bytes, pdfpath) -> bool:
    """
    Description: Convert a text based file (HTML, .py, .txt, .etc.) to PDF
    :param fileData: The ascii data bytes of the file in memory
    :param pdfpath: The path of the output PDF
    :return: Conversion Successful?
    """
    try:
        print(f"Converting ASCII-based file to PDF...")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, fileData.decode('utf-8', errors="replace").encode("latin-1", errors="replace").decode("latin-1"))
        pdf.output(pdfpath)
        print(f"Conversion successes!")
        return True
    except Exception as error:
        print(f"Failed to convert to PDF.\nError:\n{error}")
        return False


# Return True if NSFW
async def ScanningMedia(mediaExt: str, mediaPath: str, logMessage: str) -> Tuple[bool, str, str]:
    """
    Description: Scanning Media Files (Image, PDF, Video, and Audio)
    :param mediaExt: The extension of the media file
    :param mediaPath: The path to the downloaded media file
    :param logMessage: The current log message
    :return: NSFW Scan result as a boolean and Reasoning of the scan a str and the updated log message
    """
    logMessage += "- **SCANNED FILE CONTENT PROGRESS:**\n"
    if mediaExt.endswith(SUPPORTED_PICTURE_FILE_FORMATS):
        print(f"Media content is an image file in format {mediaExt}")
        if not mediaPath.endswith((".png", ".pdf", ".gif")):
            print(f"Converting the image format to PNG...")
            outPutPNGPath = mediaPath.replace(mediaExt, ".png")
            try:
                await asyncio.to_thread(subprocess.run, ["ffmpeg", "-i", mediaPath, outPutPNGPath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                logMessage += f"\t+ **Conversion from {mediaExt} to PNG:** `SUCCESS`\n"
            except Exception as PNGConversionError:
                print(f"Error: {PNGConversionError}\nError Converting the image format to PNG! Terminating Scan Process!")
                logMessage += f"\t+ **Conversion from {mediaExt} to PNG:** `ERROR: {PNGConversionError}`\n"
                return False, f"NEED MANUAL REVIEW::File Conversion Failure - Image Format can't be converted to PNG for scan, therefore the content is deleted!", logMessage
            mediaPath = outPutPNGPath
        else:
            print(f"Image already in PNG or PDF or GIF format!")
            logMessage += f"\t+ **Conversion from {mediaExt} to PNG:** `SKIPPED: Current File Format does not need conversion!`\n"
        if mediaPath.endswith(".png"):
            print("Scanning PNG image with nudenet...")
            if await scanningImageWithNudenet(mediaPath):  # First check using nudenet
                print(f"Nudenet detected NSFW image!")
                logMessage += f"\t+ **Pre-trained NSFW model Nudenet Scan Result:** `NSFW`\n"
                return True, "NSFW Image - Pre-trained NSFW model Nudenet detected NSFW element in the image!", logMessage
            logMessage += f"\t+ **Pre-trained NSFW model Nudenet Scan Result:** `CLEAN`\n"
    elif mediaExt.endswith(SUPPORTED_VIDEO_FILE_FORMATS):
        print(f"Media content is a video file in format {mediaExt}")
        print(f"Checking audio content from the video...")
        logMessage += f"\t+ **Extracting audio from video file:**\n"
        scanResult, scanResultDetails, logMessage = await NSFWScanAudio(mediaPath, logMessage, True)
        if scanResult:
            print("Video has NSFW audio content!")
            logMessage += f"\t+ **Video File Contains NSFW Audio Content!**\n"
            return True, f"NSFW Video - Video has NSFW audio content: {scanResultDetails}", logMessage
        logMessage += f"\t+ **Video File Audio Content Is CLEAN!**\n"
        print("Scanning video frame with Nudenet!")
        cap = cv2.VideoCapture(mediaPath)
        frameNum = 0
        totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = math.ceil(totalFrames / 40) # Ensure only 40 frames total is scanned!!!
        print(f"Video has total {totalFrames} frames!")
        logMessage += f"\t+ **Video File Has {totalFrames} Frames**\n"
        while frameNum < totalFrames:
            success, frame = cap.read()
            frameNum += 1

            if success and (frameNum % fps == 0):
                logMessage += f"\t+ **Scanning Video Frame {frameNum}**\n"
                framePath = f"{os.path.dirname(mediaPath)}/{uuid.uuid4().hex[0:5]}frame_{frameNum}.png"
                await asyncio.to_thread(cv2.imwrite, framePath, frame)
                HashedFileData = hashlib.sha512()
                fileBytesContent = b''
                async with aiofiles.open(framePath, "rb") as file:
                    while True:
                        fileBytesChunk = await file.read(CHUNK_SIZE)
                        if not fileBytesChunk:
                            break
                        fileBytesContent += fileBytesChunk
                        HashedFileData.update(fileBytesContent)
                HashedFramePath = HashedFileData.hexdigest()
                logMessage += f"\t\t+ **Frame SHA-512 Hash:** `{HashedFramePath}`\n"
                if HashedFramePath in CLEANData.keys():
                    print(f"Frame {frameNum} already in clean data!")
                    logMessage += f"\t\t+ **Frame Already Scanned As CLEAN!**\n"
                else:
                    if HashedFramePath in NSFWData.keys():
                        print(f"Frame {frameNum} is in NSFW data!")
                        cap.release()
                        logMessage += f"\t\t+ **Frame Already Scanned As NSFW:** `{NSFWData[HashedFramePath]}`\n"
                        return True, f"NSFW Video - Video frame {frameNum} already flagged NSFW - {NSFWData[HashedFramePath]}", logMessage
                    if await scanningImageWithNudenet(framePath):
                        print(f"Nudenet detected NSFW content at video Frame {frameNum}")
                        cap.release()
                        logMessage += f"\t\t+ **Frame Flagged NSFW By Pre-Trained NSFW model Nudenet!**\n"
                        await AddingNewNSFWData(HashedFramePath, "NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in the video frame!")
                        return True, f"NSFW Video - Pre-trained NSFW model Nudenet detected NSFW element in video frame {frameNum}", logMessage
                    await AddingNewCleanData(HashedFramePath, "Video frame passed Nudenet scan as cleaned!")
                    logMessage += f"\t\t+ **Frame Passed Pre-Trained NSFW model Nudenet Scanned As CLEAN!**\n"
            await asyncio.sleep(0)
        cap.release()
    elif mediaExt.endswith(SUPPORTED_AUDIO_FILE_FORMATS):
        print(f"Media content is an audio file in format {mediaExt}")
        scanResult, scanResultDetails, logMessage = await NSFWScanAudio(mediaPath, logMessage)
        if scanResult:
            print("Audio is not clean!")
            logMessage += f"\t+ **Audio is NSFW:** `{scanResultDetails}`\n"
            return True, scanResultDetails, logMessage
        elif scanResultDetails.startswith("NEED MANUAL REVIEW"):
            logMessage += f"\t+ **{scanResultDetails}**\n"
            return False, scanResultDetails, logMessage
        else:
            print("Audio is clean!")
            logMessage += f"\t+ **Audio is CLEAN!**\n"
            return False, "", logMessage
    if not mediaPath.endswith(".pdf"):
        pdfPath = await asyncio.to_thread(PDFConversion, mediaPath)
        if pdfPath == "Conversion failed":
            print("Error converting media content to PDF frames!")
            logMessage += f"\t+ **Conversion to PDF File:** `ERROR`\n"
            return False, f"NEED MANUAL REVIEW::Error converting media content to PDF frames!", logMessage
        logMessage += f"\t+ **Conversion to PDF File:** `SUCCESS`\n"
    else:
        pdfPath = mediaPath
        logMessage += f"\t+ **Conversion to PDF File:** `SKIPPED: File already a PDF!`\n"
    mediaScanResult, logMessage = await scanningPDFPagesWithLLM(pdfPath, logMessage)
    if mediaScanResult.startswith("NEED MANUAL REVIEW"):
        return False, mediaScanResult, logMessage
    else:
        if mediaScanResult.startswith(("Yes", "yes", "YES")):
            mediaScanResult =  mediaScanResult.strip("Yes, ")
            if mediaExt.endswith(SUPPORTED_PICTURE_FILE_FORMATS):
                mediaScanResult = f"NSFW Image - {mediaScanResult}"
            elif mediaExt.endswith(SUPPORTED_VIDEO_FILE_FORMATS):
                mediaScanResult = f"NSFW Video - {mediaScanResult}"
            print(f"Media Content flagged NSFW by {LLM_MODEL_FOR_IMAGE_SCAN}")
            return True, mediaScanResult, logMessage
        else:
            mediaScanResult = mediaScanResult.strip("No, ")
            if mediaExt.endswith(SUPPORTED_PICTURE_FILE_FORMATS):
                mediaScanResult = f"Clean Image - {mediaScanResult}"
            elif mediaExt.endswith(SUPPORTED_VIDEO_FILE_FORMATS):
                mediaScanResult = f"Clean Video - {mediaScanResult}"
            print(f"Media Content is clean!")
            return False, mediaScanResult, logMessage
