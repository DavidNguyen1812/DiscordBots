import os
import subprocess
import zipfile
import tarfile
import gzip
import rarfile
import bz2
import lzma
import filetype
import magic
import mimetypes
import hashlib
import uuid
import json
import re
import signal
import tempfile
import time
import requests
from dataclasses import dataclass, field


"""Define all file extensions Emmanuel will scan"""

SUPPORTED_PICTURE_FILE_FORMATS = (".jpg", ".png", ".jpeg", ".raw", ".pdf", ".bmp", ".webp", ".tiff", ".tif", ".ico", ".icns", ".avif",
                                 ".odd", ".gif", ".heic")

SUPPORTED_VIDEO_FILE_FORMATS = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".flv", ".mpeg", ".mpg", ".ts", ".wmv", ".dv", ".mts",
                                ".m2ts", ".vob", ".ogv")

SUPPORTED_AUDIO_FILE_FORMATS = (".mp3", ".wav", ".oga", ".ogg", ".flac", ".weba", ".aac", ".ac3", ".aif", ".aiff", ".aifc", ".amr",
                                ".au", ".caf", ".dss", ".m4a", ".m4b", ".wma", ".opus")

SUPPORTED_ARCHIVE_FILE_FORMATS = (".zip", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tar.lzma", ".tgz", ".tbz2", ".txz", ".gz", ".rar",
                                  ".bz2", ".xz", ".lzma")

SUPPORTED_DISK_IMAGE_FORMATS = (".dmg", ".iso", ".img", ".vhd", ".nrg", ".vhdx", ".vmdk", ".qcow", ".qcow2", ".udf")

SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS = SUPPORTED_DISK_IMAGE_FORMATS + SUPPORTED_ARCHIVE_FILE_FORMATS

SUPPORTED_ASCII_READABLE_FILE_FORMATS =  (".txt", ".html", ".json", ".yaml", ".xml", ".sh", ".zsh", ".c", ".java", "ASCII document or script files")

ALL_SCANNABLE_FILE_FORMATS = SUPPORTED_PICTURE_FILE_FORMATS + SUPPORTED_VIDEO_FILE_FORMATS + SUPPORTED_AUDIO_FILE_FORMATS + SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS + SUPPORTED_ASCII_READABLE_FILE_FORMATS

'''Rule policy set up'''
NESTED_ARCHIVE_SIZE_LIMIT = 1_000_000_000 # Only allow for 1 GB nested archive.
UNCOMPRESSED_SIZE_LIMIT = 50_000_000_000 # Maximum cumulative uncompressed content size
CHUNK_SIZE = 65_536  # Partial chunk size to read into RAM.
DUPLICATED_ARCHIVE_LIMIT = 4 # An archive content with 4 duplicate of other archive content inside it already seem suspicious of recursive archive bomb
MAX_FILE_SCAN_SIZE = 1_000_000_000  # Maximum file size Emmanuel can scan (This also the maximum possible file size Discord user can upload!)
MAX_DISK_IMAGE_STORAGE = 50_000_000_000  # Maximum disk image storage
MAX_VIRTUAL_DISK_SIZE = 50_000_000_000  # Maximum disk image virtual storage
MAX_SNAPSHOTS = 5  # Maximum number of snapshots a disk image is allow
MAX_FILE_COUNT = 100_000 # An archive or Disk Image with more than 100000 files already suspicious, especially sent over Discord.
MAX_ARCHIVE_LAYER = 7 # An archive with 7 nested layers is suspicious.
MAX_SCAN_SECONDS = 300  # Setting maximum archive and disk image extraction duration to be 5 minutes to prevent dead hanging and DOS.
MAX_TERMINAL_OUTPUT_SIZE_IN_MEMORY = 400_000_000  # Maximum terminal command stdout in memory

DISK_ONLY_FORMATS = ('.dmg', '.iso', '.img', '.vhd', '.nrg', '.vhdx', '.vmdk', '.qcow', '.qcow2', '.udf')
QEMU_DISK_FORMATS = {'.qcow2': 'qcow2', '.qcow': 'qcow', '.vhd': 'vpc', '.vhdx': 'vhdx', '.vmdk': 'vmdk'}


class ExtractionSafetyError(Exception):
    def __init__(self, result: str, details: str):
        self.result = result
        super().__init__(details)

@dataclass
class ArchiveScanContext:
    """Very important class to preserve essential scan data"""
    mainScanFolder: str
    scanRoot: str
    scanReportPath: str
    startTime: float = field(default_factory=time.monotonic)
    compressedSize: int = 0
    uncompressedSize: int = 0
    totalDuplicatedFile: int = 0
    totalDuplicatedArchive: int = 0
    totalFileCount: int = 0
    processedHashes: set = field(default_factory=set)
    scannedHashes: set = field(default_factory=set)
    nodes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    scanBytesRetained: int = 0
    workBytesRetained: int = 0
    status: str = 'in_progress'
    error: str = ''

    def checkCurrentExecutionDurationAndCumulativeBytes(self, bytesRead=0):
        # First check in on the current execution duration
        if time.monotonic() - self.startTime > MAX_SCAN_SECONDS:
            raise ExtractionSafetyError('Scan Too Long!', 'The archive/disk image extraction process took too long!')
        # Second check in on if the cumulative bytes exceed the rule for UNCOMPRESSED_SIZE_LIMIT
        if bytesRead:
            self.uncompressedSize += bytesRead
            if self.uncompressedSize > UNCOMPRESSED_SIZE_LIMIT:
                raise ExtractionSafetyError('Large Cumulative Uncompressed Size!', f'Uncompressed to Compressed Size ratio: {(self.uncompressedSize / self.compressedSize):.5f}')

    def appendNode(self, PathParts, NodeType, **metadata):
        """Updating the extracted file structure for later visualization"""
        self.nodes.append({'parts': list(PathParts), 'type': NodeType, **metadata})

    def saveScanReport(self):
        """Save the final data to represent the scan result"""
        data = {
            'scanFolder': self.mainScanFolder,
            'rootFile': self.scanRoot,
            'status': self.status,
            'error': self.error,
            'uncompressedSize': self.uncompressedSize,
            'totalDuplicatedFile': self.totalDuplicatedFile,
            'totalDuplicatedArchive': self.totalDuplicatedArchive,
            'totalFileCount': self.totalFileCount,
            'notes': self.warnings,
            'nodes': self.nodes,
        }
        TempPath = f'{self.scanReportPath}.{uuid.uuid4().hex}.tmp'
        with open(TempPath, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(TempPath, self.scanReportPath)


def _PathTransversalAttackDetection(filepath: str) -> list:
    """
    Description: Checking the self-declared file path from the extraction for any path transversal attack pattern
    :param filepath: The self-declared file path
    :return: list of safe and clean parts to form the final safe path
    """

    filepath = filepath.replace('\\', '/') # Emmanuel is dedicated for Unix-based OS, this would convert Windows based path to Unix.

    # Checking is the path is not empty, contains null bytes, start with a / to create an unexpected sub-folder, and contains a semi-colon
    if not filepath or '\x00' in filepath or filepath.startswith('/') or re.match(r'^[A-Za-z]:', filepath):
        raise ExtractionSafetyError('Path Transversal Attack', f'Unsafe path: {filepath!r}')

    # Now inspect the file path for parts for any .. pattern to form ../ that can contribute to LFI and directory escape attack
    PathParts = filepath.split('/')
    if any(p in ('', '.', '..') for p in PathParts if p != PathParts[-1]):
        raise ExtractionSafetyError('Path Transversal Attack', f'Unsafe path: {filepath!r}')
    PathParts = [p for p in PathParts if p]
    if not PathParts or any(p in ('.', '..') for p in PathParts):
        raise ExtractionSafetyError('Path Transversal Attack', f'Unsafe path: {filepath!r}')
    return PathParts


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


def _runOSCommandWithLimit(Command, timeout, maxOutput=MAX_TERMINAL_OUTPUT_SIZE_IN_MEMORY, outputPath=None, ctx=None):
    """
    Description: Running subprocess command with time bound limit
    :param Command: The command to run
    :param timeout: The timeout in seconds
    :param maxOutput: Capped maximum stdout and stderr output in bytes in memory, a huge stdout characters hinted the disk image is large
    :param outputPath: Output path to save the command stdout
    :param ctx: The context of the scan
    :return:
    """
    import selectors
    print(f"Running Command {Command}")
    Process = subprocess.Popen(Command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=(os.name == 'posix'))
    Data = bytearray() # Store and update the command output stream over time
    selector = selectors.DefaultSelector()
    selector.register(Process.stdout, selectors.EVENT_READ)
    try:
        stop = time.monotonic() + max(1.0, timeout)
        while Process.poll() is None or selector.get_map():
            # Exit on timeout
            if time.monotonic() >= stop:
                raise ExtractionSafetyError('Scan Too Long!', 'External process timed out')

            # Checking for disk container size
            if outputPath and ctx and os.path.exists(outputPath):
                statResult = os.stat(outputPath)
                allocated = statResult.st_blocks * 512 if hasattr(statResult, 'st_blocks') else statResult.st_size
                if allocated + ctx.scanBytesRetained + ctx.workBytesRetained > MAX_DISK_IMAGE_STORAGE:
                    raise ExtractionSafetyError('Disk Image Too Large!', 'QEMU conversion exceeded maximum disk image size for scan')

            events = selector.select(timeout=0.1)
            for key, _ in events:
                Datachunk = os.read(key.fd, 65536)
                if not Datachunk:
                    selector.unregister(key.fileobj)
                else:
                    Data.extend(Datachunk)
                    if len(Data) > maxOutput:
                        raise ExtractionSafetyError('Disk Image Error!', 'Terminal command binary output exceeds safe limit')
        exitCode = Process.wait(timeout=1)
        if exitCode != 0:
            raw = Data.decode('utf-8', errors='replace')
            if any(x in raw.lower() for x in ('wrong password', 'password required', 'encrypted', 'enter password')):
                raise ExtractionSafetyError('Encrypted Error', raw[-500:])
            raise ExtractionSafetyError('Disk Image Error!', f'External command failed ({exitCode}): {raw}')
        return Data.decode('utf-8', errors='replace')
    finally:
        # Cleanup OS resource by closing the subprocess process completely
        selector.close()
        if Process.poll() is None:
            try:
                if os.name == 'posix':
                    os.killpg(Process.pid, signal.SIGKILL)
                else:
                    Process.kill()
            except ProcessLookupError:
                pass
            Process.wait()
        if Process.stdout:
            Process.stdout.close()


def _qemuDiskImageMetaDataInspect(diskImagePath: str, fileExt: str, ctx: ArchiveScanContext):
    """
    Description: Running qemu-img command to inspect QEMU disk image metadata
    :param diskImagePath: The path to the disk image
    :param fileExt: The file extension of the disk image
    :param ctx: The current ArchiveScanContext
    :return: The info and number of snapshots within the disk image
    """
    # CRITICAL: Overlay disk image can not be accurately extracted and measure without it parent backing image
    print("Running qemu-img command to inspect QEMU disk image metadata")
    fmt = QEMU_DISK_FORMATS[fileExt]

    # Checking if QCOW is an overlay image that need an external backing image
    print("Checking for overlay image!")
    if fileExt == '.qcow2':
        with open(diskImagePath, 'rb') as file:
            header = file.read(32)
        if len(header) >= 20 and header[:4] == b'QFI\xfb':
            backingOffset = int.from_bytes(header[8:16], 'big')
            backingSize = int.from_bytes(header[16:20], 'big')
            if backingOffset or backingSize:
                print(f"Detecting a QCOW overlay image at {diskImagePath}")
                ctx.appendNode([ctx.scanRoot, 'QCOW Overlay image (not accessed)'], 'snapshot', label='Overlay QCOW image need an external parent backing image - unverified')
                raise ExtractionSafetyError('Overlay Disk Image Error!', 'The disk image is a QCOW overlay image with an external parent backing image. In order for Emmanuel to accurately measure and scan all the contents inside the image, it would need the official stand a lone backing image of this overlay!')

    # Checking if VMDK is an overlay image that need an external backing image
    elif fileExt == '.vmdk':
        with open(diskImagePath, 'rb') as file:
            header = file.read(min(os.path.getsize(diskImagePath), 131072))
        if re.search(br'(?im)^\s*parentFileNameHint\s*=', header) or re.search(br'(?im)^\s*parentCID\s*=\s*(?!ffffffff\b)[0-9a-f]+', header):
            print(f"Detecting a VMDK overlay image at {diskImagePath}")
            ctx.appendNode([ctx.scanRoot, 'VMDK Overlay image (not accessed)'], 'snapshot', label='Overlay VMDK image need an external parent backing image - unverified')
            raise ExtractionSafetyError('Overlay Disk Image Error!', 'The disk image is a VMDK overlay image with an external parent backing image. In order for Emmanuel to accurately measure and scan all the contents inside the image, it would need the official stand a lone backing image of this overlay!')

    # Checking if VHD is an overlay image that need an external backing image
    elif fileExt == '.vhd':
        with open(diskImagePath, 'rb') as file:
            if os.path.getsize(diskImagePath) >= 512:
                file.seek(-512, os.SEEK_END)
                footer = file.read(512)
                if footer.startswith(b'conectix') and int.from_bytes(footer[60:64], 'big') == 4:
                    print(f"Detecting a VHD overlay image at {diskImagePath}")
                    ctx.appendNode([ctx.scanRoot, 'VHD Overlay image (not accessed)'], 'snapshot', label='Overlay VHD image need an external parent backing image - unverified')
                    raise ExtractionSafetyError('Overlay Disk Image Error!', 'The disk image is a VHD overlay image with an external parent backing image. In order for Emmanuel to accurately measure and scan all the contents inside the image, it would need the official stand a lone backing image of this overlay!')

    ctx.checkCurrentExecutionDurationAndCumulativeBytes()

    # Getting metadata information about the disk image
    output = _runOSCommandWithLimit(['qemu-img', 'info', '-f', fmt, '--output=json', diskImagePath], MAX_SCAN_SECONDS - (time.monotonic() - ctx.startTime))
    try:
        info = json.loads(output)
    except ValueError as error:
        raise ExtractionSafetyError('Disk Image Error!', f'Invalid qemu-img metadata: {error}')

    # Second verification for overlay image to double sure
    for fieldName in ('backing-filename', 'full-backing-filename', 'backing-filename-format'):
        if info.get(fieldName):
            print(f"Detecting a {fmt.upper()} overlay image at {diskImagePath}")
            ctx.appendNode([ctx.scanRoot, f'{fmt.upper()} Overlay image (not accessed)'], 'snapshot', label=f'Overlay {fmt.upper()} image need an external parent backing image - unverified')
            raise ExtractionSafetyError('Overlay Disk Image Error!', f'The disk image is a {fmt.upper()} overlay image with an external parent backing image. In order for Emmanuel to accurately measure and scan all the contents inside the image, it would need the official stand a lone backing image of this overlay!')
    print("No overlay image detected!")

    # Checking disk encryption status
    print("Checking Disk Encryption Status!")
    if info.get('encrypted'):
        print(f"Disk image at {diskImagePath} is encrypted!")
        raise ExtractionSafetyError('Encrypted Error', 'Encrypted disk image')
    print("No Disk Encryption Detected!")

    # Checking virtual size (True Theoretical Disk Image Size)
    print("Checking Virtual Size!")
    virtualSize = info.get('virtual-size')
    print(f"Disk image at {diskImagePath} has a virtual size of {virtualSize}")
    if not isinstance(virtualSize, int) or virtualSize > MAX_VIRTUAL_DISK_SIZE:
        print(f"Virtual size {virtualSize!r} exceeds safe conversion limit")
        raise ExtractionSafetyError("Disk Image Too Large!", f'Virtual disk size {virtualSize!r} exceeds safe conversion limit')

    # Checking if there is actually a filesystem and the disk image is not empty
    print("Checking if disk image is not empty!")
    output = _runOSCommandWithLimit(['qemu-img', 'map', '--output=json', diskImagePath], MAX_SCAN_SECONDS - (time.monotonic() - ctx.startTime))
    try:
        mappingInfo = sorted(json.loads(output), key=lambda extent: extent['start'])
    except ValueError as error:
        raise ExtractionSafetyError('Disk Image Error!', f'Invalid qemu-img metadata: {error}')
    if all (extent["zero"] is True for extent in mappingInfo):
        raise ExtractionSafetyError('Empty Disk Image Error!', f'Disk image is empty!')
    print("Disk image is not empty!")

    # Checking how many snapshots the disk image hold
    print("Checking snapshot info!")
    snapshots = info.get('snapshots') or []
    print(f"Disk image at {diskImagePath} has {len(snapshots)} snapshots!")
    if len(snapshots) > MAX_SNAPSHOTS:
        print(f"Snapshots exceeds safe conversion limit")
        raise ExtractionSafetyError('Too Many Snap Shots!', 'Too many snapshots!')
    return info, snapshots


def _7zDiskImageMetaDataInspect(diskImagePath, ctx: ArchiveScanContext):
    """
    Description: Running 7z command to inspect disk image metadata
    :param diskImagePath: Path to disk image
    :param ctx: ArchiveScanContext
    """
    ctx.checkCurrentExecutionDurationAndCumulativeBytes()
    print("Running 7z command to inspect raw disk image metadata")
    SevenZDiskMetadata = _runOSCommandWithLimit(['7zz', 'l', '-slt', diskImagePath], MAX_SCAN_SECONDS - (time.monotonic() - ctx.startTime))
    print("Successfully inspected 7z disk image metadata")
    if '----------' not in SevenZDiskMetadata:
        raise ExtractionSafetyError('Disk Image Error!', '7z technical file listing is incomplete')
    members = []
    for block in SevenZDiskMetadata.split('----------', 1)[1].strip().split('\n\n'):
        metadata = {}
        for line in block.splitlines():
            if ' = ' in line:
                k, v = line.split(' = ', 1)
                metadata[k.strip()] = v.strip()
        if 'Path' not in metadata:
            continue
        if metadata.get('Encrypted') == '+':
            raise ExtractionSafetyError('Encrypted Error', 'Encrypted disk-image member')
        members.append(metadata)
    return members


def _stream7zDiskExtraction(diskImagePath: str, filename: str, ctx: ArchiveScanContext):
    """
    Description: Run a safe 7z extraction command to extract content from disk image bytes by bytes with no host direct mount
    :param diskImagePath: Path to disk image
    :param filename: The extracted filename
    :param ctx: ArchiveScanContext
    :return: None
    """
    import selectors
    # -so flag tells 7z to extract the content in the disk image to stdout in memory instead of saving on the disk.
    # -spd flag tells 7z to disable wildcard matching ofr file names, this would preserve the content file name as it is
    print(f"Running 7z command to extract file content {os.path.basename(filename)}")
    Command = ['7zz', 'x', '-so', '-spd', '-y', diskImagePath, filename]
    print(f"Running Command: {Command}")
    Process = subprocess.Popen(Command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=(os.name == 'posix'))
    selector = selectors.DefaultSelector()
    selector.register(Process.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            ctx.checkCurrentExecutionDurationAndCumulativeBytes()
            if selector.select(timeout=0.2):
                Datachunk = os.read(Process.stdout.fileno(), CHUNK_SIZE)
                if Datachunk:
                    yield Datachunk
                else:
                    selector.unregister(Process.stdout)
        print(f"Successfully extracting content from {filename}")
        if Process.wait(timeout=max(1.0, MAX_SCAN_SECONDS - (time.monotonic() - ctx.startTime))) != 0:
            raise ExtractionSafetyError('Disk Image Error!', f'7z extraction failed for {filename!r}')
    finally:
        selector.close()
        if Process.poll() is None:
            try:
                if os.name == 'posix':
                    os.killpg(Process.pid, signal.SIGKILL)
                else:
                    Process.kill()
            except ProcessLookupError:
                pass
            Process.wait()
        if Process.stdout:
            Process.stdout.close()


def _iterStream(source):
    """
    Description: Reading and generating file content bytes by bytes
    :param source: The content source
    :return: None
    """
    while True:
        Datachunk = source.read(CHUNK_SIZE)
        if not Datachunk:
            break
        yield Datachunk


def _isMacOSArchiveMetadataFile(PathParts: list) -> bool:
    """
    Description: Analyzing the extracted file content path check for .ds_store or MacOS metadata
    :param PathParts: The file path
    :return:
    """
    filename = PathParts[-1]
    return filename.lower() == '.ds_store' or filename.startswith('._') or any(part.lower() == '__macosx' for part in PathParts)



def _savingFileToDisk(ctx: ArchiveScanContext, PathParts: list, DataStream, declaredSize=None):
    """
    Description: Hash/count every file; retain only unique in-scope files <=300 MB.
    :param ctx: ArchiveScanContext
    :param PathParts: The file path broken into a list. ex /path/to/file.txt -> ["path", "to", "file.txt"]
    :param DataStream: The file data stream
    :param declaredSize: The declared size of the file
    """
    ctx.totalFileCount += 1
    print(f"Current extracted file count: {ctx.totalFileCount}")
    if ctx.totalFileCount > MAX_FILE_COUNT:
        raise ExtractionSafetyError('Too Much File Count', 'The archive/disk image contains too many files!')

    filename = PathParts[-1]
    HashedFileData = hashlib.sha256()
    CurrentSize = 0
    IsMacOSMetadata = _isMacOSArchiveMetadataFile(PathParts)

    # Initialize return values even when the file is excluded.
    retainedPath = None
    temporaryContainer = False

    # Reject files with oversized declared sizes before buffering their content.
    SaveToDisk = declaredSize is None or declaredSize <= MAX_FILE_SCAN_SIZE

    # Buffer only potentially eligible files, up to the maximum scan size.
    # No temporary disk file is created.
    FullFileContentInMemory = bytearray() if SaveToDisk and not IsMacOSMetadata else None

    # Track final files so unsuccessful operations can be rolled back.
    CreatedPath = None
    AddedScanHash = False
    AddedProcessedHash = False
    AccountedBytes = 0
    Completed = False

    try:
        for Datachunk in DataStream:
            # Count every extracted byte and calculate SHA-256 in a single pass.
            ctx.checkCurrentExecutionDurationAndCumulativeBytes(len(Datachunk))
            CurrentSize += len(Datachunk)
            HashedFileData.update(Datachunk)

            # Buffer content in RAM only while the actual size remains eligible.
            if FullFileContentInMemory is not None:
                if CurrentSize <= MAX_FILE_SCAN_SIZE:
                    FullFileContentInMemory.extend(Datachunk)
                else:
                    FullFileContentInMemory = None
                    SaveToDisk = False
                    print("File size exceeds 300 MB! Skip retention.")

        print(f"Begin processing {filename}...")

        # Identify the file format once after the complete stream is processed.
        if FullFileContentInMemory is not None:
            fileExt = checkingRealFileExtension(bytes(FullFileContentInMemory), filename, False)
            print(f"Extracted file extension: {fileExt}")
        else:
            fileExt = "Can't be determined!"

        IsSupported = fileExt in ALL_SCANNABLE_FILE_FORMATS
        isArchive = fileExt in SUPPORTED_DISK_IMAGE_AND_ARCHIVE_FILE_FORMATS
        isDiskImage = fileExt in SUPPORTED_DISK_IMAGE_FORMATS

        if isArchive:
            print(f"Detected nested {'disk image' if isDiskImage else 'archive'}: {filename}")

        if IsMacOSMetadata:
            print("Detected macOS metadata file!")

        if not IsSupported:
            print("File extension outside scan scope!")

        HashedFileData = HashedFileData.hexdigest()
        print(f"Hash Data: {HashedFileData}")
        print("Checking duplicate...")
        duplicate = HashedFileData in ctx.processedHashes
        scanDuplicate = HashedFileData in ctx.scannedHashes
        if duplicate:
            ctx.totalDuplicatedFile += 1
            if isArchive:
                print(f"Duplicate {'disk image' if isDiskImage else 'archive'}!")
                ctx.totalDuplicatedArchive += 1
                if ctx.totalDuplicatedArchive >= DUPLICATED_ARCHIVE_LIMIT:
                    raise ExtractionSafetyError('Potential Recursive Archive Bomb Attack!', 'Too many repeated nested archives')
            else:
                print(f"Duplicate file content!")
        else:
            print(f"Non duplicate content!")
            ctx.processedHashes.add(HashedFileData)
            AddedProcessedHash = True

        if ctx.totalFileCount >= 10 and ctx.totalDuplicatedFile / ctx.totalFileCount >= 0.9:
            raise ExtractionSafetyError('Too many duplicated files!', '90% or more of entries duplicate earlier data')

        # Determine the file's visualization and scanning status.
        if IsMacOSMetadata:
            label = 'macOS metadata file - Emmanuel does not scan'
            if CurrentSize > MAX_FILE_SCAN_SIZE:
                label += ' (File size exceeds 1 GB)'

        elif CurrentSize > MAX_FILE_SCAN_SIZE:
            label = 'File size exceeds 1 GB - Emmanuel does not scan'

        elif not SaveToDisk:
            label = 'Declared file size exceeds 1 GB - Emmanuel does not scan'

        elif not IsSupported:
            label = 'File format outside scope - Emmanuel does not scan'

        elif isArchive:
            TypeName = 'disk image' if isDiskImage else 'archive'
            label = (f'Duplicate nested {TypeName} - Emmanuel does not scan container' if scanDuplicate else f'Nested {TypeName}')

        elif scanDuplicate:
            label = 'Duplicate file content'

        else:
            label = 'Within Emmanuel scan scope'

        metadata = {
            'size': CurrentSize,
            'fileExt': fileExt,
            'sha256': HashedFileData,
            'duplicate': duplicate,
            'label': label,
            'isDiskImage': isDiskImage
        }

        if declaredSize is not None and declaredSize != CurrentSize:
            print(f"Declared size mismatch: {declaredSize} vs {CurrentSize}")
            ctx.warnings.append(f'`Declared size mismatch for {"/".join(PathParts)}: {declaredSize} vs {CurrentSize}`')

        if SaveToDisk and IsSupported and not IsMacOSMetadata and not scanDuplicate:
            if FullFileContentInMemory is None:
                raise ExtractionSafetyError('Disk Image Error!', 'Eligible file content is not available in memory')

            # Check the disk storage limit BEFORE writing the final file.
            if ctx.workBytesRetained + ctx.scanBytesRetained + CurrentSize > MAX_DISK_IMAGE_STORAGE:
                if isDiskImage:
                    raise ExtractionSafetyError('Disk Image Too Large!', 'Maximum disk image storage exceeded')
                else:
                    raise ExtractionSafetyError('Large Cumulative Uncompressed Size!', f'Uncompressed to Compressed Size ratio: {(ctx.uncompressedSize / ctx.compressedSize):.5f}')

            CleanName = re.sub(r'[^A-Za-z0-9._-]+', '_', filename)[:110] or 'file'
            if CleanName in ('.', '..'):
                CleanName = f'file{fileExt}'
            else:
                CleanName = CleanName.split('.')[0] + fileExt

            # Use a unique suffix to avoid overwriting an existing scan target.
            finalPath = os.path.join(ctx.mainScanFolder, f'{HashedFileData[:5]}_{uuid.uuid4().hex[:7]}_{CleanName}')

            with open(finalPath, 'xb') as file:
                CreatedPath = finalPath
                Written = file.write(FullFileContentInMemory)

                if Written != CurrentSize:
                    raise OSError('Incomplete write to final file')

            print(f"File successfully saved to path: {finalPath}")

            ctx.scanBytesRetained += CurrentSize
            AccountedBytes = CurrentSize
            temporaryContainer = isArchive
            retainedPath = finalPath

            if not isArchive:
                metadata['scanFilename'] = os.path.basename(finalPath)
            ctx.scannedHashes.add(HashedFileData)
            AddedScanHash = True

        # Add every file to the visualization, even when it was excluded.
        ctx.appendNode(PathParts, 'file', **metadata)

        Completed = True
        return {
            'size': CurrentSize,
            'fileExt': fileExt,
            'hash': HashedFileData,
            'duplicate': scanDuplicate,
            'path': retainedPath,
            'isArchive': isArchive,
            'temporaryContainer': temporaryContainer,
            'excludedMetadata': IsMacOSMetadata
        }

    finally:
        # Remove an incomplete final file if writing or later processing failed.
        if not Completed:
            if CreatedPath is not None:
                try:
                    os.remove(CreatedPath)
                except FileNotFoundError:
                    pass
                ctx.scanBytesRetained -= AccountedBytes

            # Undo hash registrations if retention/processing did not finish.
            if AddedScanHash:
                ctx.scannedHashes.discard(HashedFileData)
            if AddedProcessedHash:
                ctx.processedHashes.discard(HashedFileData)


def _mainArchiveDiskScanEngine(filePath, fileExt, PathParts, TempDir, ctx, archiveLayer, alreadyScanned):

    def scanArchiveFileContent(name, source, declaredSize=None):
        """
        Description: Use exclusively to scan content in archive files only
        :param name: The extracted file name
        :param source: The file bytes source
        :param declaredSize: The file declared size (Sometimes this value is fake by the attacker)
        :return:
        """
        # Checking malicious file path
        nameParts = _PathTransversalAttackDetection(name)
        entryParts = PathParts + nameParts
        output = _savingFileToDisk(ctx, entryParts, _iterStream(source), declaredSize)
        # Handle any nested archive and disk image
        _nestedArchiveAndDiskimageHandle(output, entryParts)

    def _nestedArchiveAndDiskimageHandle(output, entryParts):
        # Nested archives and disk images are inspected from a temporary workspace only; they are NOT moved into the flat scan folder.
        try:
            if output['isArchive'] and not output['duplicate'] and not output['excludedMetadata']:
                if output['size'] > MAX_DISK_IMAGE_STORAGE and output['isDiskImage']:
                    raise ExtractionSafetyError('Disk Image Error!', 'Nested disk image above 40 GB cannot be inspected')
                if output['size'] > NESTED_ARCHIVE_SIZE_LIMIT and not output['isDiskImage']:
                    raise ExtractionSafetyError('Too Large Nested Archive Content!', 'Nested archive size too large')
                _ArchiveAndDiskImageScan(output['path'], output['fileExt'], entryParts, TempDir, ctx, archiveLayer + 1, alreadyScanned)
        finally:
            # Always remove the nested container
            if output['temporaryContainer'] and output['path']:
                if os.path.exists(output['path']):
                    ctx.workBytesRetained = max(0, ctx.workBytesRetained - os.path.getsize(output['path']))
                    os.remove(output['path'])

    if fileExt == '.zip':
        print('Archive is a zip file!')
        with zipfile.ZipFile(filePath, 'r') as zipRef:
            """First Extraction Focusing On Checking Extraction Path and Directory Structure"""
            PathNames = set()  # Prevent duplicate file paths
            for entry in zipRef.infolist():
                EntryPath = '/'.join(_PathTransversalAttackDetection(entry.filename))
                if EntryPath not in PathNames:
                    PathNames.add(EntryPath)
                if ((entry.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ExtractionSafetyError('Path Transversal Attack', f'ZIP symbolic link: {entry.filename}')
            """Second Extraction Focusing On Extracting All the Compressed Files"""
            for entry in zipRef.infolist():
                if entry.is_dir():
                    ctx.appendNode(PathParts + _PathTransversalAttackDetection(entry.filename), 'directory')
                    continue
                try:
                    with zipRef.open(entry) as source:
                        scanArchiveFileContent(entry.filename, source, entry.file_size)
                except RuntimeError as error:
                    if 'password' in str(error).lower():
                        raise ExtractionSafetyError('Encrypted Error', str(error)) from error
                    raise
    elif fileExt in ('.tar', '.tar.gz', '.tar.bz2', '.tar.xz', '.tar.lzma', '.tgz', '.tbz2', '.txz'):
        print('Archive is a tar file!')
        with tarfile.open(filePath, 'r:*') as tarRef:
            """First Extraction Focusing On Checking Extraction Path and Directory Structure"""
            PathNames = set()
            for entry in tarRef:
                EntryPath = '/'.join(_PathTransversalAttackDetection(entry.name))
                if EntryPath not in PathNames:
                    PathNames.add(EntryPath)
                if entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()):
                    raise ExtractionSafetyError('Path Transversal Attack', f'TAR symbolic link: {entry.name}')
            """Second Extraction Focusing On Extracting All the Compressed Files"""
            for entry in tarRef.getmembers():
                if entry.isdir():
                    ctx.appendNode(PathParts + _PathTransversalAttackDetection(entry.name), 'directory')
                    continue
                source = tarRef.extractfile(entry)
                if source is None:
                    raise ExtractionSafetyError('Disk Image Error!', f'Unable to read TAR member {entry.name}')
                with source:
                    scanArchiveFileContent(entry.name, source, entry.size)
    elif fileExt == '.rar':
        print('Archive is a rar file!')
        with rarfile.RarFile(filePath) as rar:
            if rar.needs_password():
                raise ExtractionSafetyError('Encrypted Error', 'RAR needs password')
            PathNames = set()
            for entry in rar.infolist():
                EntryPath = '/'.join(_PathTransversalAttackDetection(entry.filename))
                if EntryPath not in PathNames:
                    PathNames.add(EntryPath)
                if entry.needs_password():
                    raise ExtractionSafetyError('Encrypted Error', 'RAR encrypted member')
                if getattr(entry, 'is_symlink', lambda: False)():
                    raise ExtractionSafetyError('Path Transversal Attack', f'RAR symbolic link: {entry.filename}')
            for entry in rar.infolist():
                if entry.is_dir():
                    ctx.appendNode(PathParts + _PathTransversalAttackDetection(entry.filename), 'directory')
                    continue
                with rar.open(entry) as source:
                    scanArchiveFileContent(entry.filename, source, entry.file_size)
    elif fileExt in ('.gz', '.bz2', '.xz', '.lzma'):
        print('Archive is a single-file compression stream!')
        filename = PathParts[-1]
        if filename.endswith(fileExt):
            filename = filename[:-len(fileExt)]
        filename = filename or 'decompressed_content'
        opener = gzip.open if fileExt == '.gz' else bz2.open if fileExt == '.bz2' else lzma.open
        with opener(filePath, 'rb') as source:
            scanArchiveFileContent(filename, source)
    else:
        _inspectDiskImage(filePath, fileExt, PathParts, TempDir, ctx, _nestedArchiveAndDiskimageHandle)


def _7zDiskExtraction(filePath, PathParts, ctx, nestedArchiveDiskImageCheckFunction):
    members = _7zDiskImageMetaDataInspect(filePath, ctx)
    NamesSeen = set()
    for entry in members:
        filename = entry['Path']
        NameParts = _PathTransversalAttackDetection(filename)
        if filename in NamesSeen:
            raise ExtractionSafetyError('Disk Image Error!', f'Ambiguous duplicate path: {filename}')
        NamesSeen.add(filename)
        if entry.get('Encrypted') == '+':
            raise ExtractionSafetyError('Encrypted Error', f'Encrypted disk member: {filename}')

        # Reject symlinks and nonregular entries when the archive exposes type metadata.
        kind = (entry.get('Type', '') + ' ' + entry.get('Attributes', '')).lower()
        if 'symbolic link' in kind or 'hard link' in kind or entry.get('Symbolic Link') or entry.get('Hard Link'):
            raise ExtractionSafetyError('Path Transversal Attack', f'{filename} contains symbolic link {entry.get('Symbolic Link')} AND hard link {entry.get('Hard Link')}')
        if entry.get('Folder') == '+' or entry.get('Size') in (None, ''):
            ctx.appendNode(PathParts + NameParts, 'directory')
            continue
        try:
            size = int(entry['Size'])
        except ValueError:
            raise ExtractionSafetyError('Disk Image Error!', f'Invalid 7z Size for {filename}')

        # Stream even oversized/out-of-scope files, without retaining them, for accurate counts.
        CurrentParts = PathParts + NameParts
        print(f"Begin extracting content from {filename}")
        DataStream = _stream7zDiskExtraction(filePath, filename, ctx)
        try:
            output = _savingFileToDisk(ctx, CurrentParts, DataStream, size)
        finally:
            if hasattr(DataStream, "close"):
                DataStream.close()
        nestedArchiveDiskImageCheckFunction(output, CurrentParts)


def _inspectDiskImage(diskImagePath, diskImageExt, PathParts, TempDir, ctx, nestedArchiveDiskImageCheckFunction):
    """
    Description: Exclusively use to analyze disk image
    :param diskImagePath: Path to disk image
    :param diskImageExt: The disk image extension
    :param PathParts: The list of the disk image path. E.g /path/to/test.qcow2 -> ['path', 'to', 'test.qcow2']
    :param TempDir: The Temp folder to extract the disk image content
    :param ctx: ArchiveContextScan
    :param nestedArchiveDiskImageCheckFunction: The function to scan for nested Archive and Disk Image later
    :return:
    """
    print(f'Scanning disk image file: {os.path.basename(diskImagePath)} at path {diskImagePath}...')
    if diskImageExt in QEMU_DISK_FORMATS:
        info, snapshots = _qemuDiskImageMetaDataInspect(diskImagePath, diskImageExt, ctx)

        # Saving snapshots visualization structure
        snapshotVisualisation = [('Active disk state', None)]
        for snapshot in snapshots:
            snapshotID = str(snapshot.get('id', ''))
            if not snapshotID or not re.fullmatch(r'[A-Za-z0-9._-]+', snapshotID):
                raise ExtractionSafetyError('Disk Image Error!', 'Unexpected snapshot identifier')
            snapshotVisualisation.append((f"Snapshot {snapshotID} ({snapshot.get('name', '')})", snapshotID))

        # Record the entire snapshot inventory BEFORE conversion so even a failed snapshot has a visible 'not inspected' label in the report.
        for snapshotLabel, snapshotID in snapshotVisualisation:
            ctx.appendNode(PathParts + [snapshotLabel], 'snapshot' if snapshotID else 'state', label='Not inspected (pending)')

        for snapshotLabel, snapshotID in snapshotVisualisation:
            ctx.checkCurrentExecutionDurationAndCumulativeBytes()
            StateParts = PathParts + [snapshotLabel]
            RawFilePath = os.path.join(TempDir, f'RawDisk_{uuid.uuid4().hex}.img')
            try:
                Command = ['qemu-img', 'convert', '-f', QEMU_DISK_FORMATS[diskImageExt], '-O', 'raw', '-S', '4k']
                if snapshotID:
                    Command += ['-l', snapshotID]
                Command += [diskImagePath, RawFilePath]
                _runOSCommandWithLimit(Command, MAX_SCAN_SECONDS - (time.monotonic() - ctx.startTime), outputPath=RawFilePath, ctx=ctx)
                print(f"Successfully Converting {diskImagePath} to {RawFilePath}")
                if os.path.getsize(RawFilePath) > MAX_VIRTUAL_DISK_SIZE:
                    raise ExtractionSafetyError('Disk Image Too Large!', 'Converted state exceeds virtual-size limit')

                # Recheck allocated bytes after process exit as well as during conversion.
                RawStat = os.stat(RawFilePath)
                RawAllocated = RawStat.st_blocks * 512 if hasattr(RawStat, 'st_blocks') else RawStat.st_size
                if RawAllocated + ctx.scanBytesRetained + ctx.workBytesRetained > MAX_DISK_IMAGE_STORAGE:
                    raise ExtractionSafetyError('Disk Image Too Large!', 'Converted state exceeded physical storage budget')

                print("Begin 7z command to extract the converted raw image!")
                _7zDiskExtraction(RawFilePath, StateParts, ctx, nestedArchiveDiskImageCheckFunction)
                ctx.appendNode(StateParts, 'snapshot' if snapshotID else 'state', label='QCOW internal snapshot inspected' if snapshotID else 'Active disk state inspected')
            finally:
                if os.path.exists(RawFilePath):
                    os.remove(RawFilePath)
    else:
        StateParts = PathParts + ['Active filesystem view']
        ctx.appendNode(StateParts, 'state', label='Current 7z-visible filesystem view')
        _7zDiskExtraction(diskImagePath, StateParts, ctx, nestedArchiveDiskImageCheckFunction)
        if diskImageExt in ('.dmg', '.img', '.udf', '.iso', '.nrg'):
            ctx.appendNode(PathParts + ['Historical snapshots or optical sessions (unverified)'], 'snapshot', label='Not enumerated - Emmanuel cannot certify this disk state')
            ctx.warnings.append(f"`Historical filesystem snapshots / optical sessions not exhaustively inspected: {diskImageExt}`")
            raise ExtractionSafetyError('Disk Image Error!','Historical filesystem snapshots / optical sessions were not exhaustively inspected')


def _ArchiveAndDiskImageScan(ArchiveDiskPath, fileExt, PathParts, TempDir, ctx, archiveLayer, alreadyScanned):
    """
    Description: Scanning archive and disk image
    :param ArchiveDiskPath: Path to the nested container
    :param fileExt: The nested file ext
    :param PathParts: Parts of the file path
    :param TempDir: Temp directory to store
    :param ctx: ArchiveScanContext
    :param archiveLayer: Current nested layer
    :param alreadyScanned: A list of already scanned nested container
    :return:
    """
    if archiveLayer > 1:
        print("---------------------------------------------------")
    print(f"------------------CURRENT LAYER {archiveLayer}------------------")
    ctx.checkCurrentExecutionDurationAndCumulativeBytes()
    if archiveLayer >= MAX_ARCHIVE_LAYER:
        raise ExtractionSafetyError('Matryoshka Archive', 'Maximum nested archive depth reached')
    if os.path.islink(ArchiveDiskPath):
        raise ExtractionSafetyError('Path Transversal Attack', f'Detected filesystem symbolic link {ArchiveDiskPath} points to {os.readlink(ArchiveDiskPath)}')
    with open(ArchiveDiskPath, 'rb') as file:
       HashedFileData = hashlib.sha256(file.read()).hexdigest()
    if HashedFileData in alreadyScanned:
        ctx.appendNode(PathParts, 'container', label='Nested content already inspected (same SHA-256)')
        return
    alreadyScanned.add(HashedFileData)
    _mainArchiveDiskScanEngine(ArchiveDiskPath, fileExt, PathParts, TempDir, ctx, archiveLayer, alreadyScanned)


def ArchivesDiskImagesBombAnalysisAndExtraction(file_path: list, main_scan_folder: str, scan_report_path: str, root_file_ext: str= '') -> str:
    """
    Description: Performing a safe extraction of compressed content inside archive or disk images
    :param file_path: A list of the archive/disk image path
    :param main_scan_folder: The main directory to extract the compressed content
    :param scan_report_path: The path to save the scan results
    :param root_file_ext: The root archive/disk image file ext
    :return: The summary of the extraction
    """
    main_scan_folder = os.path.abspath(os.path.normpath(main_scan_folder))
    archiveLayer = 1
    print(f"Initialize main empty mount point at {main_scan_folder}")
    os.makedirs(main_scan_folder, exist_ok=True)
    print(f"Root archive/disk file is at {file_path[0]}")
    ctx = ArchiveScanContext(mainScanFolder=main_scan_folder, scanRoot=os.path.basename(file_path[0]), scanReportPath=scan_report_path, compressedSize=os.path.getsize(file_path[0]))
    alreadyScanned = set()
    try:
        with tempfile.TemporaryDirectory(prefix='EmmanuelExtract_', dir=os.path.dirname(main_scan_folder)) as TempDir:
            for RootPath in file_path[:]:
                if os.path.islink(RootPath):
                    raise ExtractionSafetyError('Path Transversal Attack', f'Source is a filesystem link pointing to {os.readlink(RootPath)}')
                RootFileSize = os.path.getsize(RootPath)
                ctx.checkCurrentExecutionDurationAndCumulativeBytes(RootFileSize)
                RootParts = [os.path.basename(RootPath)]
                _ArchiveAndDiskImageScan(RootPath, root_file_ext, RootParts, TempDir, ctx, archiveLayer, alreadyScanned)

        skipped = [node for node in ctx.nodes if node.get('type') == 'file' and ('outside scope' in node.get('label', '') or 'exceeds 300 MB' in node.get('label', '') or 'macOS metadata file' in node.get('label', ''))]
        if skipped:
            ctx.warnings.append(f'`{len(skipped)} extracted file(s) excluded from Emmanuel scan`')
        ctx.status = 'partial' if ctx.warnings else 'complete'
        print(f'Archive and Disk Image content extracted with total uncompressed size of {ctx.uncompressedSize:,} bytes')
        print(f'Total file count is: {ctx.totalFileCount:,}')
        print(f'Total duplicated file is: {ctx.totalDuplicatedFile:,}')
        print(f'Total duplicated archive/disk image is: {ctx.totalDuplicatedArchive:,}')
        return 'Safe Extraction Complete!'
    except ExtractionSafetyError as error:
        ctx.status = 'unverified' if error.result in ('Disk Image Error!', 'Disk Image Too Large!', 'Overlay Disk Image Error!', 'Empty Disk Image Error!', 'Too Many Snap Shots!', 'Scan Too Long!', 'Encrypted Error') else 'rejected'
        ctx.error = f'{error.result}: {error}'
        print(ctx.error)
        return ctx.error
    except (zipfile.BadZipFile, tarfile.TarError, rarfile.Error, OSError, EOFError, lzma.LZMAError, ValueError, subprocess.SubprocessError) as error:
        ctx.status = 'unverified'
        ctx.error = f'{type(error).__name__}: {error}'
        print(ctx.error)
        return ctx.error
    finally:
        ctx.saveScanReport()


def uncompressedFileStructure(scan_report_path: str, indent="") -> str:
    """
    Description: Visualizing the uncompressed file structure of an archive/disk file
    :param scan_report_path: The path to the JSON scan report to read the scanned content
    :param indent: Indentation level for better visualization
    :return: The uncompressed file structure
    """
    with open(scan_report_path, 'r', encoding='utf-8') as file:
        scanReport = json.load(file)

    tree = {'children': {}, 'node': None}
    for node in scanReport['nodes']:
        current = tree
        for name in node['parts']:
            current = current['children'].setdefault(name, {'children': {}, 'node': None})

        if current['node'] and current['node'].get('type') == 'file' and node.get('type') == 'container':
            current['node']['containerNote'] = node.get('label', '')
        else:
            current['node'] = node

    result = ''
    def visit(branch, level, name=None, prefix="", isLast=True):
        nonlocal result
        node = branch['node']
        if name is not None:
            if node:
                kind = node.get('type', 'directory')
                if kind == 'file':
                    extra = f" ({node['size']:,} bytes; {node['label']})"
                elif kind in ('state', 'snapshot'):
                    extra = f" ({node.get('label', kind)})"
                else:
                    extra = f" ({node.get('label', 'Directory')})"
                if node.get('containerNote'):
                    extra += f" [Nested: {node['containerNote']}]"
            else:
                extra = ' (Directory)'
            BranchMarker = '└── ' if isLast else '├── '
            result += f"{indent}{prefix}{BranchMarker}{name}{extra}\n"
        ChildNames = sorted(branch['children'])
        ChildPrefix = prefix + ('    ' if isLast else '│   ') if name is not None else prefix
        for ChildIndex, childName in enumerate(ChildNames):
            visit(branch['children'][childName], level + (1 if name is not None else 0), childName, ChildPrefix, ChildIndex == len(ChildNames) - 1)
    visit(tree, 0)
    if scanReport.get('error'):
        result += f"\nSCAN STATUS: {scanReport['status']} — {scanReport['error']}\n"
    return result