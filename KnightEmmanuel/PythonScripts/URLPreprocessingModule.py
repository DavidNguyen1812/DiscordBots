import discord
import ipaddress
import socket
from typing import Tuple
from urllib.parse import unquote, urlsplit, urljoin, urlunsplit
from aiohttp.abc import AbstractResolver
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup

import asyncio
import aiohttp
import re
import hashlib
import os
import requests
import random
import time

load_dotenv()

"""----API Tokens----"""
KLIPHY_API = os.environ.get("EMMANUEL_KLIPHY_API")
GIPHY_API = os.environ.get("EMMANUEL_GIPHY_API")

"""URL Inspection Rules"""
MAX_URL_REDIRECTS = 12 # Maximum 12 URL redirect follow for SSRF inspection
MAX_URL_INSPECTION_SECONDS = 15 # URL inspection should not exceed 15 seconds
MAX_URL_DNS_SECONDS = 3 # URL DNS inspection should not exceed 3 seconds
MAX_URL_LENGTH = 4096 # A long URL is already a suspicious sign of malicious URL
MAX_URL_DNS_ADDRESSES = 16 # Allow maximum 16 DNS address for the URL

"""SSRF Deny Lists"""
SSRF_LOCALHOST = [
    "localhost",
    "localhost.localdomain",
    "localhost6",
    "localhost6.localdomain6",
    "ip6-localhost",
    "ip6-loopback",
    "loopback",
    "local",
    "localdomain",
    "localtest.me",
    "lvh.me",
    "vcap.me",
    "nip.io",
    "sslip.io",
    "xip.io"
]

SSRF_CLOUD_METADATA = [
    "169.254.169.254",
    "metadata",
    "metadata.google.internal",
    "metadata.google",
    "metadata.azure.internal",
    "metadata.internal",
    "metadata.tencentyun.com",
    "metadata.tencentyun.com.cn",
    "100.100.100.200"
]

SSRF_CONTAINER = [
    "host.docker.internal",
    "gateway.docker.internal",
    "docker.for.mac.host.internal",
    "docker.for.mac.localhost",
    "docker.for.win.localhost",
    "host.containers.internal",
    "host.kubernetes.internal",
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
    "kubernetes.default.svc.cluster.local",
    "docker",
    "dockerhost",
    "containerhost"
]

"""Retrieving 100 ScrapeOps Mobile Browser Headers"""
ScrapeOPSResponse = requests.get(
  url='http://headers.scrapeops.io/v1/browser-headers',
  params={
      'api_key': os.environ.get("EMMANUEL_SCRAPEOPS_API"),
      'num_results': '100',
      'mobile': 'true'}
)
SCRAPEOPS_MOBILE_BROWSER_HEADERS = ScrapeOPSResponse.json().get('result', [])
assert len(SCRAPEOPS_MOBILE_BROWSER_HEADERS) == 100
print(f"Successfully retrieving 100 ScrapeOps Mobile Browser Headers!")


"""Initialize aiohttp.ClientSession in setUpHook"""
class EmmanuelBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        print("aiohttp ClientSession initialized.")

    async def close(self):
        await super().close()
        await self.session.close()

intents = discord.Intents.all()
Emmanuel = EmmanuelBot(command_prefix='/', intents=intents)


async def getTenorGifURL(gifURL: str) -> str:
    """
    Description: Scrape for final Downloadable Tenor Gif Content
    :param gifURL: Tenor URL
    :return: The final Tenor Gif URL
    """
    print("Scraping for final downloadable Tenor Gif URL")
    if gifURL.startswith("https://c.tenor.com/"):
        return gifURL
    async with Emmanuel.session.get(gifURL, headers=random.choice(SCRAPEOPS_MOBILE_BROWSER_HEADERS)) as response:
        if response.status == 200:
            soup = BeautifulSoup(await response.text(), "html.parser")
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("srcset")
                if src:
                    if src.startswith(("https://media1.tenor.com/m/", "https://c.tenor.com/")):
                        if src.startswith("https://media1.tenor.com/"):
                            url = f"https://c.tenor.com/{src.replace("https://media1.tenor.com/m/", "").split("/")[0]}/tenor.gif"
                        else:
                            url = src
                        return url
            print("Can't locate the final downloadable Tenor Gif URL")
            return "Gif Not Found"
        else:
            print("Can't locate the final downloadable Tenor Gif URL")
            return "Gif Not Found"


async def isKlipyURLValid(gifURL: str) -> str:
    """
    Description: Klipy URL validation
    :param gifURL: Klipy URL
    :return: The correct Klipy URL or Invalid if URL is not a Klipy URL
    """
    try:
        gifSlug = os.path.basename(gifURL)
        gifURL = f"https://api.klipy.com/api/v1/{KLIPHY_API}/gifs/items?slugs={gifSlug}"
        async with Emmanuel.session.get(gifURL) as response:
            if response.status == 200:
                data = await response.json()
                if data["result"]:
                    gifURL = data["data"]["data"][0]["file"]["hd"]["gif"]["url"]
                    return gifURL
            return "Invalid"
    except Exception as error:
        print(f"Klipy URL error: {error}")
        return "Invalid"


async def getGiphyURL(gifURL: str) -> str:
    """
    Description: Giphy URL validation
    :param gifURL: Giphy URL
    :return: Retrieve the correct source Giphy GIF URL
    """
    try:
        gifID = os.path.basename(gifURL).split("-")[-1]
        gifURL = f"https://api.giphy.com/v1/gifs/{gifID}"
        async with Emmanuel.session.get(gifURL,  params={"api_key": GIPHY_API}) as response:
            if response.status == 200:
                data = await response.json()
                gifURL = data.get('data', {}).get('images', {}).get('original', {}).get('url', '')
                if gifURL:
                    return gifURL
            print(f"Can't retrieve GIPHY source url!")
            return "Gif Not Found"
    except Exception as error:
        print(f"Giphy URL error: {error}")
        return "Gif Not Found"


class TerminateURLScan(Exception):
    pass

class URLRedirectSafetyError(Exception):
    def __init__(self, reason: str, redirectPath: list):
        super().__init__(reason)
        self.redirectPath = list(redirectPath)


class URLRedirectInspectionError(Exception):
    def __init__(self, reason: str, redirectPath: list):
        super().__init__(reason)
        self.redirectPath = list(redirectPath)


class _PinnedDNSResolver(AbstractResolver):
    """Checked public IP addresses for the actual HTTP/TLS connection"""

    # https://nhimg.org/glossary/dns-pinning/
    def __init__(self, hostname: str, publicIPs: tuple):
        self.hostname = hostname.encode('idna').decode('ascii').lower().rstrip('.')
        self.publicIPs = publicIPs
        print(f"Begin pinned DNS resolver on hostname {self.hostname} and it Public IPs {self.publicIPs}")

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        checkedHost = host.encode('idna').decode('ascii').lower().rstrip('.')
        if checkedHost != self.hostname:
            raise OSError('Unexpected DNS hostname during pinned URL inspection')
        results = []
        for ip in self.publicIPs:
            address = ipaddress.ip_address(ip)
            addressFamily = socket.AF_INET if address.version == 4 else socket.AF_INET6
            if family not in (0, socket.AF_UNSPEC, addressFamily):
                continue
            results.append({
                'hostname': host, 'host': ip, 'port': port,
                'family': addressFamily, 'proto': 0, 'flags': socket.AI_NUMERICHOST
            })
        if not results:
            raise OSError('No validated IP address for requested address family')
        print("Hostname successfully pinned with the IP addresses!")
        return results

    async def close(self):
        pass


def _CheckURLHasTraversal(url: str) -> bool:
    """Checking for ../ pattern"""
    value = url
    for _ in range(4):
        if '../' in value.replace('\\', '/'):
            return True
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    return '../' in value.replace('\\', '/')


async def _CheckURLDestination(url: str, redirectPath: list):
    """
    Description: Inspecting URL hostname and it resolved IP addresses
    :param url: The URL to inspect
    :param redirectPath: Current list of redirect URLs to add on
    :return: The final clean URL format, hostname, and it IP addresses
    """
    print(f"URL length: {len(url):,}")
    if not isinstance(url, str) or len(url) > MAX_URL_LENGTH:
        raise URLRedirectSafetyError('Invalid and overly long URL', redirectPath)

    print(f"Checking directory transversal attempt...")
    if _CheckURLHasTraversal(url):
        raise URLRedirectSafetyError('Directory traversal pattern (../) detected', redirectPath)
    print(f"No ../ pattern detected!")

    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
        print(f"URL hostname: {hostname}, port: {port}")
    except ValueError as error:
        raise URLRedirectSafetyError(f'Malformed URL: {error}', redirectPath) from error

    print("Inspecting URL protocol and checking embedded credentials...")
    if parts.scheme.lower() not in ('http', 'https') or not hostname:
        raise URLRedirectSafetyError('Unsupported URL scheme or missing hostname', redirectPath)
    if parts.username is not None or parts.password is not None:
        raise URLRedirectSafetyError(f'URL contains embedded username {parts.username} and password input {parts.password}. A potential attempt to force the victim browser to authenticate with the provided credentials!', redirectPath)

    # Cyberbot only ensure the URL is from standard web port 80 and 443
    expectedPort = 443 if parts.scheme.lower() == 'https' else 80
    if port not in (None, expectedPort):
        raise URLRedirectSafetyError(f'Disallowed URL port: {port}', redirectPath)
    port = expectedPort
    print(f"Valid URL protocol {parts.scheme.lower()} and no embedded credentials found!")

    print(f"Inspecting URL hostname {hostname}...")
    if '%' in hostname or '\\' in hostname or any(c.isspace() for c in hostname):
        raise URLRedirectSafetyError(f'Ambiguous or encoded hostname {hostname}', redirectPath)
    lowerHostname = hostname.lower().rstrip('.')

    # Checking malicious hostname point to internal IP
    if re.compile("|".join(map(re.escape, SSRF_LOCALHOST))).search(lowerHostname):
        raise URLRedirectSafetyError(f'URL redirect to Local/internal hostname {lowerHostname}', redirectPath)
    if re.compile("|".join(map(re.escape, SSRF_CLOUD_METADATA))).search(lowerHostname):
        raise URLRedirectSafetyError(f'URL redirect to Cloud Metadata Service {lowerHostname}', redirectPath)
    if re.compile("|".join(map(re.escape, SSRF_CONTAINER))).search(lowerHostname):
        raise URLRedirectSafetyError(f'URL redirect to internal container/virtualisation images {lowerHostname} blocked', redirectPath)
    print("Hostname passed SSRF DENY LIST!")

    print("Resolving for the hostname IP addresses...")
    try:
        literalIP = ipaddress.ip_address(lowerHostname)
        addresses = (str(literalIP),)
    except ValueError:
        try:
            infos = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(lowerHostname, port, type=socket.SOCK_STREAM), timeout=MAX_URL_DNS_SECONDS)
        except (OSError, asyncio.TimeoutError) as error:
            raise URLRedirectInspectionError(f'DNS lookup failed: {error}', redirectPath) from error
        addresses = tuple(dict.fromkeys(info[4][0] for info in infos))
        if not addresses or len(addresses) > MAX_URL_DNS_ADDRESSES:
            raise URLRedirectInspectionError('DNS lookup returned no addresses or too many answers', redirectPath)
    print(f"Hostname resolved to IP addresses {addresses}")

    for ip in addresses:
        print(f"Inspecting IP address {ip}...")
        address = ipaddress.ip_address(ip)
        if not address.is_global:
            raise URLRedirectSafetyError(f'URL leads to Non-public destination: {hostname} resolves to {ip}', redirectPath)
        print(f"IP address is a global address!")
    networkURL = urlunsplit((parts.scheme, parts.netloc, parts.path or '/', parts.query, ''))
    return networkURL, hostname, tuple(addresses)


async def _ReadRedirectResponse(url: str, hostname: str, publicIPs: tuple):
    connector = aiohttp.TCPConnector(resolver=_PinnedDNSResolver(hostname, publicIPs), use_dns_cache=False, force_close=True, limit=1, )
    timeout = aiohttp.ClientTimeout(total=7, connect=3, sock_connect=3, sock_read=3)
    print("Begin checking for any URL redirects...")
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, trust_env=False, auto_decompress=False,) as session:
        async with session.get(url, allow_redirects=False, read_until_eof=False, headers=random.choice(SCRAPEOPS_MOBILE_BROWSER_HEADERS), max_line_size=8192, max_field_size=8192, ) as response:
            return response.status, response.headers.get('Location')


async def _InspectURLRedirects(initialURL: str):
    """Walk every redirect and validate its destination BEFORE making the request"""
    redirectPath = []
    visited = set()
    currentURL = initialURL
    redirectStatusCodes = {301, 302, 303, 307, 308}

    async def inspect():
        nonlocal currentURL
        for redirectCount in range(MAX_URL_REDIRECTS + 1):
            print(f"Begin pre-processing URL: {currentURL}")
            redirectPath.append(currentURL)
            networkURL, hostname, publicIPs = await _CheckURLDestination(currentURL, redirectPath)
            if networkURL in visited:
                raise URLRedirectInspectionError('URL creates a Redirect loop detected; cannot safely validate', redirectPath)
            visited.add(networkURL)

            try:
                status, location = await _ReadRedirectResponse(networkURL, hostname, publicIPs)
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError, ValueError) as error:
                raise URLRedirectInspectionError(f'Unable to inspect HTTP redirect: {type(error).__name__}: {error}', redirectPath) from error

            if status in redirectStatusCodes:
                if not location:
                    raise URLRedirectInspectionError(f'HTTP {status} redirect with no Location header', redirectPath)
                print(f"Found redirect URL {location}")

                print(f"Checking directory transversal attempt...")
                if _CheckURLHasTraversal(location):
                    redirectPath.append(location)
                    raise URLRedirectSafetyError(f'Redirect URL {location} contains ../ traversal', redirectPath)
                print(f"No ../ pattern detected!")

                print(f"Redirect URL length: {len(location):,}")
                if len(location) > MAX_URL_LENGTH:
                    redirectPath.append(location[:MAX_URL_LENGTH])
                    raise URLRedirectSafetyError(f'Redirect URL {location} length {len(location)} too long!', redirectPath)
                nextURL = urljoin(networkURL, location)
                if redirectCount >= MAX_URL_REDIRECTS:
                    redirectPath.append(nextURL)
                    raise URLRedirectInspectionError('Maximum redirect count exceeded; cannot safely validate', redirectPath)
                currentURL = nextURL
                continue

            if 300 <= status < 400:
                raise URLRedirectInspectionError(f'Unsupported redirect HTTP status {status}', redirectPath)
            return networkURL, list(redirectPath)

        raise URLRedirectInspectionError('Maximum redirect count exceeded; cannot safely validate', redirectPath)

    try:
        return await asyncio.wait_for(inspect(), timeout=MAX_URL_INSPECTION_SECONDS)
    except asyncio.TimeoutError as error:
        raise URLRedirectInspectionError('Overall redirect inspection timed out', redirectPath) from error


def URLScanMessageFormat(redirectPath: list, reason: str, status: str, url: str):
    displayPath = []
    for idx, value in enumerate(redirectPath, start=1):
        clean = str(value).replace('`', "'").replace('\r', '\\r').replace('\n', '\\n')
        displayPath.append(f'{idx}. {clean}')
    if len(displayPath) > 1:
        sendMessage = (f'**URL:** `{url}`\n'
                  f'**Scan Status:** `{status}`\n'
                  f'**Reason:** `{reason}`\n'
                  f'Redirect Path:\n'
                  f'```text\n'
                  f'{'\n  ->\n'.join(displayPath)}\n'
                  f'```')
    else:
        sendMessage = (f'**URL:** `{url}`\n'
                  f'**Scan Status:** `{status}`\n'
                  f'**Reason:** `{reason}`\n')
    return sendMessage


async def processingUrls(URLs: list, message: discord.message.Message, logMessage: str, filteredTextContent: str) -> Tuple[dict, str, str, bool]:
    """
    Description: Preprocessing URL by validating URL access code, checking for ../ pattern, and SSRF attempt
    :param URLs: The list of URLs to be pre-processed
    :param message: The Discord message object
    :param logMessage: The current scan log message
    :param filteredTextContent: The filtered text of clean of the URL for Emmanuel to scan the text content only
    :return: A dict of pre-processed URls and it base name and hash content, the final scan log message, and a boolean value to continue the scan or not
    """
    print('Detecting URLs in text content...')
    resolvedUrls = {}
    logMessage += f'## URL Pre-Inspection Summary\n'
    UrlInspectionStartTime = time.perf_counter()
    try:
        for url in URLs:
            print(f'Found URL: {url}')
            filteredTextContent = filteredTextContent.replace(url, '')
            logMessage += f'- **URL:** `{url}`\n'

            """Checking ../ attack pattern"""
            if _CheckURLHasTraversal(url):
                logMessage += (f'- **Inspection Result:** `UNSAFE TO SCAN`\n'
                               f'- **Reason:** `URL name query hinted potential directory transversal attack!`\n')
                print(f'URL {url} contains ../ attack pattern!\n\n')
                sendMessage = URLScanMessageFormat([], 'URL contains a ../ scheme hinted potential directory transversal attack on the host web server!', 'UNSAFE TO VISIT', url)
                try:
                    await message.delete()
                    await message.author.send(sendMessage)
                except Exception:
                    pass
                raise TerminateURLScan
            try:
                finalURL, redirectPath = await _InspectURLRedirects(url)
                print('URL redirect path: ' + ' -> '.join(redirectPath))
                if len(redirectPath) > 1:
                    fullPath = " -> ".join(redirectPath)
                    logMessage += (f'- **URL Redirect Path (Public Only):**\n'
                                   f'```commandline\n'
                                   f'{fullPath}\n'
                                   f'```\n'
                                   f'- **Final Destination Path:** `{finalURL}`\n')

                """Getting Official Klipy GIF URLs directly through the Klipy API"""
                if finalURL.startswith('https://klipy.com/gifs/'):
                    finalKlipyURL = await isKlipyURLValid(finalURL)
                    if finalKlipyURL != "Invalid":
                        print(f'Kliphy GIF URL is valid!')
                        finalURL = finalKlipyURL
                    else:
                        print(f'Kliphy URL is invalid!')
                        sendMessage = URLScanMessageFormat(redirectPath, f'The Kliphy URL {finalURL} is not a valid URL due to failure to authenticate with Kliphy official API!', 'INVALID KLIPHY URL', url)
                        try:
                            await message.delete()
                            await message.author.send(sendMessage)
                        except Exception:
                            pass
                        raise TerminateURLScan

                # Tenor API is deprecated, scraping for Official Downloadable Tenor GIF URL using Beautiful Soup
                elif "tenor.com" in finalURL:
                    finalTenorURL = await getTenorGifURL(finalURL)
                    if finalTenorURL != "Gif Not Found":
                        print(f"Final Tenor URL is {finalTenorURL}")
                        finalURL = finalTenorURL
                    else:
                        print(f'Can not locate final valid Tenor URL!')

                # Getting GIPHY GIF source through the GIPHY API
                elif finalURL.startswith('https://giphy.com/gifs/'):
                    finalGiphyURL = await getGiphyURL(finalURL)
                    if finalGiphyURL != "Gif Not Found":
                        print(f"Final Giphy URL is {finalGiphyURL}")
                        finalURL = finalGiphyURL
                    else:
                        print(f'Can not retrieve final valid Giphy URL!')

                if finalURL.startswith(("https://cdn.discordapp.com/attachments/", "https://media.discordapp.net/attachments/")):
                    finalURLHash = hashlib.sha512(finalURL.split('?')[0].encode()).hexdigest()
                else:
                    finalURLHash = hashlib.sha512(finalURL.encode()).hexdigest()

                logMessage += (f'- **Final URL To Scan:** `{finalURL}`\n'
                               f'- **URL SHA-512 Hash:** `{finalURLHash}`\n')

            except URLRedirectSafetyError as error:
                print(error)
                redirectPath = error.redirectPath
                if len(redirectPath) > 1:
                    fullPath = ' -> '.join(redirectPath)
                    logMessage += (f'- **URL Redirect Path (Public Only):**\n'
                                   f'```commandline\n'
                                   f'{fullPath}\n'
                                   f'```\n'
                                   f'- **Final Destination Path:** `{redirectPath[-1]}`\n')
                logMessage += (f'- **Inspection Result:** `UNSAFE TO SCAN`\n'
                               f'- **Reason:** `{error}`\n')
                sendMessage = URLScanMessageFormat(redirectPath, str(error), 'UNSAFE TO VISIT', url)
                try:
                    await message.delete()
                    await message.author.send(sendMessage)
                except Exception:
                    pass # If uer blocked Emmanuel or the message already deleted before Emmanuel can delete it, then Emmanuel does not need to send any explanation
                raise TerminateURLScan

            except URLRedirectInspectionError as error:
                print(error)
                redirectPath = error.redirectPath
                if len(redirectPath) > 1:
                    fullPath = ' -> '.join(redirectPath)
                    logMessage += (f'- **URL Redirect Path (Public Only):**\n'
                                   f'```commandline\n'
                                   f'{fullPath}\n'
                                   f'```\n'
                                   f'- **Final Destination Path:** `{redirectPath[-1]}`\n')
                logMessage += (f'- **Inspection Result:** `UNVERIFIED`\n'
                               f'- **Reason:** `{error}`\n')
                continue


            """URL access validation"""
            parts = urlsplit(finalURL)
            if parts.scheme not in ('http', 'https') or not parts.hostname:
                logMessage += (f"- **Inspection Result:** `UNVERIFIED`\n"
                               f"- **Reason:** `The Final Destination URL Use Unsupported Web Protocol '{parts.scheme}' OR Have no valid hostname!`\n")
                continue
            if parts.hostname.lower() in ['cdn.discordapp.com', 'media.discordapp.net'] and parts.port in (None, 443) and parts.username is None and parts.path.startswith('/attachments/'):
                print('URL is a Discord attachment!!! Will scan URL as an attachment file!')
                resolvedUrls[finalURL] = [unquote(os.path.basename(parts.path)), finalURLHash]
                logMessage += (f"- **Inspection Result:** `SAFE TO SCAN AS DISCORD ATTACHMENT`\n"
                               f"- **Reason:** `URL is a Discord attachment! Will scan URL as an attachment file!`\n")
            else:
                resolvedUrls[finalURL] = [os.path.basename(finalURL), finalURLHash]
                logMessage += (f"- **Inspection Result:** `SAFE TO SCAN`\n"
                               f"- **Reason:** `URL hostname, IP addresses, and final destination are valid and safe to begin NSFW scan!`\n")

            print(f"URL inspection duration: {time.perf_counter() - UrlInspectionStartTime:.2f}s")
            logMessage += f"- **Inspection Duration In Second(s):** {time.perf_counter() - UrlInspectionStartTime:.2f}s\n"
            logMessage += "\n---\n\n"

    except TerminateURLScan:
        print(f"URL inspection duration: {time.perf_counter() - UrlInspectionStartTime:.2f}s")
        logMessage += f"- **Inspection Duration In Second(s):** {time.perf_counter() - UrlInspectionStartTime:.2f}s\n\n---\n\n"
        return {}, logMessage, '', False

    return resolvedUrls, logMessage, filteredTextContent, True