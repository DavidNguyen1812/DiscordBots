import wave, io, subprocess, aiofiles, asyncio, datetime, os, base64
from google.genai import types
from RuntimeConfigsModule import LLM_ENGINE, LLM_MODEL_PROVIDER, LLM_MODEL_FOR_AUDIO_TRANSCRIPTION
from FileUtilitiesModule import calculateUsageCost


def _getWaveMetadata(waveFilePath: str) -> tuple[int, int]:
    """
    Description: Retrieve WAV metadata without blocking the asyncio event loop.
    This function must be called through asyncio.to_thread().

    :param waveFilePath: WAV file path.
    :return: Sample rate and total audio frames.
    """
    with wave.open(waveFilePath, "rb") as audioFile:
        frameRate = audioFile.getframerate()
        totalFrames = audioFile.getnframes()

    return frameRate, totalFrames


def _readWaveSegmentBytes(waveFilePath: str, segmentStartFrame: int, framesPerSegment: int) -> tuple[bytes, int]:
    """
    Description: Read an individual WAV segment and create an in-memory WAV file.

    :param waveFilePath: Original WAV file path.
    :param segmentStartFrame: Starting frame of the segment.
    :param framesPerSegment: Number of frames to extract.
    :return: Segment WAV bytes and actual segment frame count.
    """
    with wave.open(waveFilePath, "rb") as audioFile:
        audioParams = audioFile.getparams()
        audioFile.setpos(segmentStartFrame)
        frames = audioFile.readframes(framesPerSegment)

    if not frames:
        return b"", 0

    segmentFrameCount = len(frames) // (audioParams.nchannels * audioParams.sampwidth)

    segmentBuffer = io.BytesIO()

    with wave.open(segmentBuffer, "wb") as outfile:
        outfile.setnchannels(audioParams.nchannels)
        outfile.setsampwidth(audioParams.sampwidth)
        outfile.setframerate(audioParams.framerate)
        outfile.setcomptype(
            audioParams.comptype,
            audioParams.compname
        )
        outfile.writeframes(frames)
    return segmentBuffer.getvalue(), segmentFrameCount


async def NSFWScanAudio(audioPath: str, logMessage: str, video: bool=False) -> tuple[bool, str, str]:  # Return True if Audio is NSFW!
    """
    Description: NSFW scan for audio file
    :param audioPath: Path to audio file on disk
    :param logMessage: Current log message
    :param video: Is this an audio of a video?
    :return: Scan result and reason and updated log message
    """
    """Running ffmpeg command to convert the audio/video input file to WAV audio format with data at 16-bit PCM"""
    audioName = os.path.basename(audioPath).split(".")[0]
    if not audioPath.endswith(".wav"):
        if video:
            print("Extracting Audio from video file to WAV file format...")
        else:
            print("Converting Audio to WAV file format...")
        waveFilePath = f"{os.path.dirname(audioName)}/{audioName}.wav"
        try:
            await asyncio.to_thread(subprocess.run, ["ffmpeg", "-i", audioPath, "-acodec", "pcm_s16le", waveFilePath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print("WAV conversion successful!")
            logMessage += f"\t\t+ **Conversion to WAVE audio:** `SUCCESS`\n"
        except Exception as ConversionToWavAudioError:
            logMessage += f"\t\t+ **Conversion to WAVE audio:** `ERROR: {ConversionToWavAudioError}`\n"
            if not video:
                print(f"Error {ConversionToWavAudioError}")
                return False, "NEED MANUAL REVIEW::File Conversion Failure - Can not convert audio file to WAV format!", logMessage
            else:
                print(f"Error {ConversionToWavAudioError} while extracting audio from the video! Proceeding to scan video content...")
                return False, "", logMessage
    else:
        print("Audio file already in .wav format!")
        logMessage += f"\t\t+ **Conversion to WAVE audio:** `SKIPPED: File format already a WAVE audio`\n"
        waveFilePath = audioPath

    """Running LLM audio transcribe model to extract text from audio"""
    transcription = ""
    try:
        frameRate, totalFrames = await asyncio.to_thread(_getWaveMetadata, waveFilePath)
        audioDuration = totalFrames / float(frameRate)
        print(f"Audio duration in second(s): {audioDuration:.2f}")
        audioFileSize = await asyncio.to_thread(os.path.getsize, waveFilePath)
        logMessage += f"\t\t+ **WAVE audio size:** `{audioFileSize:,} bytes`\n"
        logMessage += f"\t\t+ **WAVE audio duration in second(s):** `SKIPPED: {audioDuration:.2f}`\n"

        if LLM_MODEL_PROVIDER == "openai":
            # https://developers.openai.com/api/docs/guides/speech-to-text
            # https://developers.openai.com/api/docs/pricing
            if audioFileSize <= 25_000_000:
                async with aiofiles.open(waveFilePath, "rb") as audioFile:
                    transcriptionResponse = await LLM_ENGINE.audio.transcriptions.create(
                        model=LLM_MODEL_FOR_AUDIO_TRANSCRIPTION,
                        file=(os.path.basename(waveFilePath), await audioFile.read(), "audio/wav"),
                    )
                    totalCost = await calculateUsageCost(LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, transcriptionResponse)
                    print(f"Total Estimated Cost Of LLM Audio Transcription: ${totalCost}")
                    transcription = transcriptionResponse.text
                    logMessage += (f"\t\t+ **WAVE audio LLM transcription cost:** `${totalCost}`\n"
                                   f"\t\t+ **Transcription:** {transcription}\n")
            else:
                print("Audio file size >= 25 MB")
                print("Splitting file into 10 minutes segment...")
                logMessage += f"\t\t+ **WAVE audio size exceeds 25 MB!\n"
                framesPerSegment = frameRate * 600
                segmentIndex = 0
                totalCost = 0
                while segmentIndex * framesPerSegment < totalFrames:
                    segmentStartFrame = segmentIndex * framesPerSegment
                    audioSegmentBytes, segmentFrameCount = await asyncio.to_thread(_readWaveSegmentBytes, waveFilePath, segmentStartFrame, framesPerSegment)
                    if not audioSegmentBytes:
                        break
                    outPutSegmentName = f"{os.path.splitext(os.path.basename(waveFilePath))[0]}_segment_{segmentIndex}.wav"
                    transcriptionResponse = await LLM_ENGINE.audio.transcriptions.create(model=LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, file=(outPutSegmentName, audioSegmentBytes, "audio/wav"))
                    cost = await calculateUsageCost(LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, transcriptionResponse)
                    totalCost += cost
                    transcription += transcriptionResponse.text + " "
                    print(f"Transcription From Audio Segment {str(datetime.timedelta(seconds=segmentIndex * 180))} - {str(datetime.timedelta(seconds=(segmentIndex + 1) * 180))}: {transcriptionResponse.text}")
                    logMessage += (f"\t\t+ **WAVE audio segment {str(datetime.timedelta(seconds=segmentIndex * 180))} - {str(datetime.timedelta(seconds=(segmentIndex + 1) * 180))}:**\n"
                                   f"\t\t\t+ **LLM transcription cost:** `${cost}`\n"
                                   f"\t\t\t+ **Transcription:** `{transcriptionResponse.text}`\n")
                    segmentIndex += 1
                print(f"Total Cumulative Estimated Cost Of LLM Audio Transcription: ${round(totalCost, 5)}")
        elif LLM_MODEL_PROVIDER == "google-gemini":
            # https://aistudio.google.com/docs/transcribe
            # https://aistudio.google.com/docs/pricing#gemini-3.5-transcribe

            if audioDuration < 3600:
                async with aiofiles.open(waveFilePath, "rb") as audioFile:
                    waveFileBytes = await audioFile.read()
                if 4 * ((len(waveFileBytes) + 2) // 3) < 100000000:
                    audioBase64 = (await asyncio.to_thread(base64.b64encode, waveFileBytes)).decode("ascii", errors="replace")
                    transcriptionResponse = await LLM_ENGINE.aio.interactions.create(
                        model=LLM_MODEL_FOR_AUDIO_TRANSCRIPTION,
                        input=[
                            {
                                "type": "audio",
                                "data": audioBase64,
                                "mime_type": "audio/wav"
                            }
                        ]
                    )
                    totalCost = await calculateUsageCost(LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, transcriptionResponse)
                    print(f"Total Estimated Cost Of LLM Audio Transcription: ${totalCost}")
                    transcription = transcriptionResponse.output_text
                    logMessage += (f"\t\t+ **WAVE audio LLM transcription cost:** `${totalCost}`\n"
                                   f"\t\t+ **Transcription:** {transcription}\n")
                else:
                    print("Audio file size >= 100 MB")
                    logMessage += f"\t\t+ **WAVE audio size exceeds 100 MB!**\n"
                    uploadedFile = await LLM_ENGINE.aio.files.upload(file=io.BytesIO(waveFileBytes), config=types.UploadFileConfig(display_name=os.path.basename(waveFilePath), mime_type="audio/wav")         )
                    logMessage += f"\t\t+ **Uploaded WAVE audio size to Google Gemini Server!**\n"
                    print(f"Uploaded Audio File To Google Gemini Server at {uploadedFile.uri}")
                    try:
                        transcriptionResponse = await LLM_ENGINE.aio.interactions.create(
                            model=LLM_MODEL_FOR_AUDIO_TRANSCRIPTION,
                            input=[
                                {
                                    "type": "audio",
                                    "uri": uploadedFile.uri,
                                    "mime_type": uploadedFile.mime_type or "audio/wav"
                                }
                            ]
                        )
                        totalCost = await calculateUsageCost(LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, transcriptionResponse)
                        print(f"Total Estimated Cost Of LLM Audio Transcription: ${totalCost}")
                        transcription = transcriptionResponse.output_text
                        logMessage += (f"\t\t+ **WAVE audio LLM transcription cost:** `${totalCost}`\n"
                                       f"\t\t+ **Transcription:** {transcription}\n")
                    finally:
                        try:
                            await LLM_ENGINE.aio.files.delete(name=uploadedFile.name)
                        except Exception as deleteError:
                            logMessage += f"\t\t+ **Error Deleting Uploaded Audio File:** `{deleteError}`\n"
                            print(f"Unable to delete Gemini uploaded file: {deleteError}")
            else:
                print("Audio file duration exceed 1 hour")
                print("Splitting file into 10 minutes segment...")
                framesPerSegment = frameRate * 600
                segmentIndex = 0
                totalCost = 0
                while segmentIndex * framesPerSegment < totalFrames:
                    segmentStartFrame = segmentIndex * framesPerSegment
                    audioSegmentBytes, segmentFrameCount = await asyncio.to_thread(_readWaveSegmentBytes, waveFilePath, segmentStartFrame, framesPerSegment)
                    if not audioSegmentBytes:
                        break
                    outPutSegmentName = f"{os.path.splitext(os.path.basename(waveFilePath))[0]}_segment_{segmentIndex}.wav"
                    uploadedFile = await LLM_ENGINE.aio.files.upload(file=io.BytesIO(audioSegmentBytes), config=types.UploadFileConfig(display_name=os.path.basename(outPutSegmentName), mime_type="audio/wav"))
                    print(f"Uploaded Audio Segment {str(datetime.timedelta(seconds=segmentIndex * 180))} - {str(datetime.timedelta(seconds=(segmentIndex + 1) * 180))} To Google Gemini Server at {uploadedFile.uri}")
                    try:
                        transcriptionResponse = await LLM_ENGINE.aio.interactions.create(
                            model=LLM_MODEL_FOR_AUDIO_TRANSCRIPTION,
                            input=[
                                {
                                    "type": "audio",
                                    "uri": uploadedFile.uri,
                                    "mime_type": uploadedFile.mime_type or "audio/wav"
                                }
                            ]
                        )
                        cost = await calculateUsageCost(LLM_MODEL_FOR_AUDIO_TRANSCRIPTION, transcriptionResponse)
                        totalCost += cost
                        transcription += transcriptionResponse.output_text + " "
                        print(f"Transcription From Audio Segment {str(datetime.timedelta(seconds=segmentIndex * 180))} - {str(datetime.timedelta(seconds=(segmentIndex + 1) * 180))}: {transcriptionResponse.output_text}")
                        logMessage += (f"\t\t+ **WAVE audio segment {str(datetime.timedelta(seconds=segmentIndex * 180))} - {str(datetime.timedelta(seconds=(segmentIndex + 1) * 180))}:**\n"
                                   f"\t\t\t+ **LLM transcription cost:** `${cost}`\n"
                                   f"\t\t\t+ **Transcription:** `{transcriptionResponse.output_text}`\n")
                    finally:
                        try:
                            await LLM_ENGINE.aio.files.delete(name=uploadedFile.name)
                        except Exception as deleteError:
                            logMessage += f"\t\t\t+ **Error Deleting Uploaded Audio File:** `{deleteError}`\n"
                            print(f"Unable to delete Gemini uploaded file: {deleteError}")
                print(f"Total Cumulative Estimated Cost Of LLM Audio Transcription: ${round(totalCost, 5)}")
    except Exception as Error:
        logMessage += f"\t\t+ **An Error Occur During {LLM_MODEL_FOR_AUDIO_TRANSCRIPTION} Transcription:** `{Error}`\n"
        if not video:
            print(f"An error occur while {LLM_MODEL_FOR_AUDIO_TRANSCRIPTION} transcribing the audio: {Error}")
            return False, f"NEED MANUAL REVIEW::Audio Transcript - An error occur while {LLM_MODEL_FOR_AUDIO_TRANSCRIPTION} transcribing the audio - {Error}", logMessage
        else:
            print(f"An error occur while {LLM_MODEL_FOR_AUDIO_TRANSCRIPTION} transcribing the video audio: {Error}")
            return False, "", logMessage

    if transcription:
        print(f"Final transcription detected from audio file: {transcription}")
        from MainScanEngineModule import NSFWscanMessage
        scanResult, scanResultDetails = await NSFWscanMessage(transcription)
        if scanResult:
            return True, f"NSFW Audio Transcript - {scanResultDetails}", logMessage
        else:
            return False, f"Clean Audio Transcript - {scanResultDetails}", logMessage
    else:
        print("No transcription detected from audio file!")
        return False, f"NEED MANUAL REVIEW::Audio Transcript - No Text Transcription Detected from the audio file by {LLM_MODEL_FOR_AUDIO_TRANSCRIPTION}!", logMessage
