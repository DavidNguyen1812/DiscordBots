import discord
from MultiEncryption import *
import re
import requests
import hashlib
import os
import vigenere

from discord.ext import commands
from discord import app_commands
from typing import Literal
from dotenv import load_dotenv
from io import BytesIO
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from Crypto.Signature import DSS
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.PublicKey import ECC

load_dotenv()

DISCORDAPI = os.environ.get("NEXUSDISCORDAPI")

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', intents=intents)
# Regex pattern to detect URLs in messages
url_pattern = re.compile(r'(https?://\S+)')



@client.event
async def on_ready():
    await client.wait_until_ready()
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("Knight Nexus is ONLINE!")

    #  Synced all commands -> Add new command if not already existed, else update the pre-existing command
    await client.tree.sync()
    SynedCmds = await client.tree.fetch_commands()
    for cmd in SynedCmds:
        print(f"Synced command /{cmd.name}")
    print(f"Commands are updated and ready to use!")


@client.tree.command(
    name="nexus",
    description="Get Information about Knight Nexus"
)
async def Nexus(ctx):
    await ctx.response.send_message \
        ("I am a knight designed by Sir David Nguyen with a some built-in fun Cryptographic commands as shown below."
         " Please note that for security reason, all messages from me are temporary and only visible to user that request"
         " the commands!"
         "\nCommand List:\n"
         "/clear_nexus_dm_messages\n"
         "/david_cipher\n"
         "/rc4\n"
         "/hash\n"
         "/morse_decode\n"
         "/tap_code_decode\n"
         "/rail_fence_cipher\n"
         "/random_string_subs_cipher\n"
         "/vigenere_cipher\n"
         "/square_code\n"
         "/text_book_rsa_key_generation\n"
         "/textbook_rsa_cipher\n"
         "/crypto_rsa_key_generation\n"
         "/crypto_rsa_cipher\n"
         "/crypto_aes_ocb_key_generation\n"
         "/crypto_aes_ocb_cipher\n"
         "/crypto_rsa_digital_signature\n"
         "/crypto_ecc_key_generation\n"
         "/crypto_ecdsa")


@client.tree.command(
    name="clear_nexus_dm_messages",
    description="Delete all direct messages sent by Knight Nexus to you"
)
async def clear_nexus_dm_messages(ctx):
    await ctx.response.defer()
    async for message in ctx.user.history():
        if message.author == client.user:
            await message.delete()
    if str(ctx.channel.type).startswith("private"):
        async for message in ctx.user.history(limit=1):
            if message.author == client.user:
                await message.delete()
    else:
        await ctx.channel.purge(limit=1)


@client.tree.command(
    name="david_cipher",
    description="Applying the symmetric stream cipher. (Not cryptographically secure)"
)
@app_commands.describe(
    userinput="Input the plain text OR the cipher text",
    operation="Select encrypt OR decrypt operations",
    key="Provide the key for decryption process."
)
async def david_cipher(ctx, userinput: str, operation: Literal["encrypt", "decrypt"], key: int=0):
    await ctx.response.defer(ephemeral=True)
    try:
        key = str(key)
        if operation == "encrypt":
            result = DavidEncryption(userinput)
        else:
            if len(key) == 2 or len(key) == 3:
                if len(key) == 2:
                    key = '0' + key
            else:
                await ctx.followup.send(f"Invalid key length!")
                return
            result = DavidDecipher(userinput, key)
        if operation == "encrypt":
            await ctx.followup.send(f"Your Cipher Text is: {result.split(':')[0]}"
                                    f"\nYour Key is: {result.split(':')[1]}")
        else:
            await ctx.followup.send(f"Your Plain Text is: {result}")
    except Exception as error:
        await ctx.followup.send(f"Error processing your request: {error}\nSome of the input format could be not "
                                f"correct!")


@client.tree.command(
    name="rc4",
    description="Applying the legacy symmetric stream cipher algorithm rc4. (Not cryptographically secure)"
)
@app_commands.describe(
    i="What is the value for i?",
    j="What is the value for j?",
    userinput="Input the plain text OR the cipher text",
    operation="Select encrypt OR decrypt operations"
)
async def rc4(ctx, i: int, j: int, userinput: str, operation: Literal["encrypt", "decrypt"]):
    await ctx.response.defer(ephemeral=True)
    try:
        if operation == "encrypt":
            await ctx.followup.send(f"Your Cipher Text in Hex Format is: {RC4(True, i, j, userinput)}\n"
                                    f"Your key is: i = {i} and j = {j}")
        else:
            userinput = ''.join(userinput.split(" ")).split("0x")[1::]
            await ctx.followup.send(f"Your Text is: {RC4(False, i, j, userinput)}")
    except Exception as error:
        await ctx.followup.send(f"Error processing your request: {error}\nSome of the input format could be not "
                                f"correct!")


@client.tree.command(
    name="hash_func",
    description="Experimenting with different cryptographic hash functions."
)
@app_commands.describe(
    hash_type="Select one of the provided hash functions",
    input_text="Provide a message to be hashed"
)
async def hash_func(ctx,
                    hash_type: Literal["md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_256",
                                       "sha3_384", "sha3_512", "shake_128", "shake_256", "blake2b", "blake2s"],
                    input_text: str):
    await ctx.response.defer(ephemeral=True)
    hashText = ''
    if hash_type == "sha1":
        hashText = hashlib.sha1(input_text.encode()).hexdigest()
    elif hash_type == "sha224":
        hashText = hashlib.sha224(input_text.encode()).hexdigest()
    elif hash_type == "sha256":
        hashText = hashlib.sha256(input_text.encode()).hexdigest()
    elif hash_type == "sha384":
        hashText = hashlib.sha384(input_text.encode()).hexdigest()
    elif hash_type == "sha512":
        hashText = hashlib.sha512(input_text.encode()).hexdigest()
    elif hash_type == "sha3_256":
        hashText = hashlib.sha3_256(input_text.encode()).hexdigest()
    elif hash_type == "sha3_384":
        hashText = hashlib.sha3_384(input_text.encode()).hexdigest()
    elif hash_type == "sha3_512":
        hashText = hashlib.sha3_512(input_text.encode()).hexdigest()
    elif hash_type == "shake_128":
        hashText = hashlib.shake_128(input_text.encode()).hexdigest(128)
    elif hash_type == "shake_256":
        hashText = hashlib.shake_256(input_text.encode()).hexdigest(256)
    elif hash_type == "blake2b":
        hashText = hashlib.blake2b(input_text.encode()).hexdigest()
    elif hash_type == "blake2s":
        hashText = hashlib.blake2s(input_text.encode()).hexdigest()
    elif hash_type == "md5":
        hashText = hashlib.md5(input_text.encode()).hexdigest()
    await ctx.followup.send(f"Your hashed text using {hash_type} is: {hashText}")


@client.tree.command(
    name="morse_decode",
    description="Decoding a morse code."
)
@app_commands.describe(
    morse_code="Provide a valid morse code with a space in between character"
)
async def morse_decode(ctx, morse_code: str):
    await ctx.response.defer(ephemeral=True)
    for char in morse_code:
        if char != ' ' and char != '.' and char != '-':
            await ctx.followup.send("INVALID INPUT! PLEASE ENTER DOTS, SPACES, AND DASHES ONLY!!!")
            return
    checkList = morse_code.split(' ')
    for character in checkList:
        if '.' not in character and '-' not in character:
            await ctx.followup.send("INVALID SPACING FORMAT!")
            return
        if len(character) > 5:
            await ctx.followup.send("INVALID MORSE CODE!")
            return
    await ctx.followup.send(f"The message is {MorseCodeDecoder(morse_code)}")


@client.tree.command(
    name="tap_code_decode",
    description="Decoding a tap code."
)
@app_commands.describe(
    tap_code="Provide a valid tap code with a double spaces in between character"
)
async def tap_code_decode(ctx, tap_code: str):
    await ctx.response.defer(ephemeral=True)
    for char in tap_code:
        if char != ' ' and char != '.':
            await ctx.followup.send("INVALID INPUT! PLEASE ENTER DOTS AND SPACES ONLY!!!")
            return
    checkList = tap_code.split('  ')
    for Code in checkList:
        if ' ' not in Code:
            await ctx.followup.send("INVALID INPUT!")
            return
        else:
            spaceCount = 0
            for character in Code:
                if character == " ":
                    spaceCount += 1
            if spaceCount != 1:
                await ctx.followup.send("INVALID SPACING FORMAT!")
                return
            temp = Code.split(" ")
            if len(temp[0]) > 5 or len(temp[1]) > 5:
                await ctx.followup.send("INVALID INPUT! YOU CAN ONLY USE 5 DOTS IN REPETITION!")
                return
    await ctx.followup.send(f"The message is {tapCodeDecoder(tap_code.split('  '))}")


@client.tree.command(
    name="rail_fence_cipher",
    description="Applying the symmetric cryptographic rail-fence stream cipher. (Not cryptographically secure)"
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    rail="How many number of rails?"

)
async def rail_fence_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"],
                            rail: int):
    await ctx.response.defer(ephemeral=True)
    if operation == "encrypt":
        rail = random.randint(2, len(message) // 2)
        await ctx.followup.send(f"The cipher text is {railFenceCipher(rail, message, True)}\n"
                                f"The rail value is {rail}")
    else:
        await ctx.followup.send(f"The plain text is {railFenceCipher(rail, message, False)}")


@client.tree.command(
    name="random_string_subs_cipher",
    description="A symmetric cryptographic stream cipher inspired by Caesar cipher. (Not cryptographically secure)"
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    key_string="A string of all 26 English letters at different random index"

)
async def random_string_subs_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"], key_string: str):
    await ctx.response.defer(ephemeral=True)
    for char in key_string:
        if not (char.isalpha() or char in string.punctuation):
            await ctx.followup.send("ERROR: KEY STRING MUST BE ONLY ENGLISH ALPHABETIC LETTERS!")
            return
    repeatCheck = {}
    for letter in key_string:
        repeatCheck[letter] = 0
    keyString = ''
    for letter in repeatCheck:
        keyString += letter
    if len(keyString) != 26:
        await ctx.followup.send("ERROR: KEY STRING MUST HAVE ALL THE ENGLISH ALPHABET LETTERS")
        return
    if operation == "encrypt":
        await ctx.followup.send(f"The cipher text is {randomSubstitutionCipher(keyString, message, True)}")
    else:
        await ctx.followup.send(f"The plain text is {randomSubstitutionCipher(keyString, message, False)}")


@client.tree.command(
    name="vigenere_cipher",
    description="A symmetric cryptographic stream cipher. (Not cryptographically secure)"
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    key="A string of random words"
)
async def vigenere_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"], key: str):
    await ctx.response.defer(ephemeral=True)
    if operation == "encrypt":
        await ctx.followup.send(f"The cipher text is {vigenere.encrypt(message, key, False)}\n"
                                f"The key is {key}")
    else:
        await ctx.followup.send(f"The plain text is {vigenere.decrypt(message, key, False)}")


@client.tree.command(
    name="square_code",
    description="A symmetric cryptographic stream cipher (Not cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    key="Provide a key to encrypt or decrypt"
)
async def textbook_rsa_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"], key: int):
    await ctx.response.defer(ephemeral=True)
    if operation == "encrypt":
        cipherText = squareCode(message, key, True)
        await ctx.followup.send(f"The cipher text is {cipherText}\nThe key is {key}")
    else:
        plainText = squareCode(message, key, False)
        await ctx.followup.send(f"The plain text is {plainText}")


@client.tree.command(
    name="text_book_rsa_key_generation",
    description="Generating keys for asymmetric cryptographic block cipher RSA."
)
async def text_book_rsa_key_generation(ctx):
    await ctx.response.defer(ephemeral=True)
    e, n, d = TextBookRSAKeyGeneration()
    await ctx.followup.send(f"Your public keys are:\ne\t{e}\nn\t{n}\nYour private key is:\nd\t{d}")


@client.tree.command(
    name="textbook_rsa_cipher",
    description="An asymmetric cryptographic block cipher (Not cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    key="Provide public exponent e for encryption, private key d for decryption",
    public_modulus="Provide public modulus n"
)
async def textbook_rsa_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"],
                              key: str, public_modulus: str):
    await ctx.response.defer(ephemeral=True)
    try:
        key = int(key)
        public_modulus = int(public_modulus)
        if operation == "encrypt":
            await ctx.followup.send(f"Your cipher text is"
                                    f" {TextBookRSAoperation(message, key, public_modulus, True)}")
        else:
            await ctx.followup.send(f"The original text is"
                                    f" {TextBookRSAoperation(message, key, public_modulus, False)}")
    except ValueError:
        await ctx.followup.send(f"Your key values need to be an integer!")


@client.tree.command(
    name="crypto_rsa_key_generation",
    description="Generating Crypto RSA keys in pem file format."
)
@app_commands.describe(
    key_size="Select the key size in bits"
)
async def crypto_rsa_key_generation(ctx, key_size: Literal[2048, 3072, 4096]):
    # https://www.pycryptodome.org/src/examples#generate-an-rsa-key
    await ctx.response.defer(ephemeral=True)
    key = RSA.generate(key_size)
    privateKey = key.export_key(format="PEM")
    publicKey = key.publickey().export_key(format="PEM")
    PrivateKeybuffer = BytesIO()
    PublicKeybuffer = BytesIO()
    PrivateKeybuffer.write(privateKey)
    PublicKeybuffer.write(publicKey)
    PrivateKeybuffer.seek(0)
    PublicKeybuffer.seek(0)
    await ctx.followup.send(file=discord.File(fp=PrivateKeybuffer, filename="CryptoRSAprivateKey.pem"))
    await ctx.followup.send(file=discord.File(fp=PublicKeybuffer, filename="CryptoRSApublicKey.pem"), ephemeral=True)


@client.tree.command(
    name="crypto_rsa_pkcs1_oaep_cipher",
    description="An asymmetric cryptographic with PKCS1_OAEP scheme (Cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text OR cipher text (Text length must be less than 220 characters!)",
    operation="Select encrypt OR decrypt operations",
    key="Upload your RSA public (for encryption) or private (for decryption) PEM file."
)
async def crypto_rsa_pkcs1_oaep_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"],
                                        key: discord.Attachment):
    await ctx.response.defer(ephemeral=True)
    message = message.encode('utf-8')
    try:
        key = RSA.import_key(await key.read())
        if operation == "encrypt":
            if len(message) >= 220:
                await ctx.followup.send("Message too long! RSA encryption is limited to 220 bytes.")
            else:
                cipherText = CryptoRSAOperation(message, key, True)
                await ctx.followup.send(f"Your Cipher Message is:\n{cipherText}")
        else:
            plainText = CryptoRSAOperation(message, key, False)
            await ctx.followup.send(f"Your Original Message is:\n{plainText}")
    except Exception as error:
        await ctx.followup.send(f"Invalid RSA key file or decryption error! Error: {error}")


@client.tree.command(
    name="crypto_aes_ocb_key_generation",
    description="Generating Crypto AES-OCB key."
)
@app_commands.describe(
    key_size="Select the key size in bits"
)
async def crypto_aes_ocb_key_generation(ctx, key_size: Literal[128, 192, 256]):
    # https://www.pycryptodome.org/src/examples#encrypt-and-authenticate-data-in-one-step
    await ctx.response.defer(ephemeral=True)
    await ctx.followup.send(f"Your AES key is: {base64.b64encode(get_random_bytes(key_size // 8)).decode('ascii')}")


@client.tree.command(
    name="crypto_aes_ocb_cipher",
    description="An authenticated symmetric cryptographic algorithm (Cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text OR cipher text",
    operation="Select encrypt OR decrypt operations",
    key="Provide your AES key (for encryption) or AES:Tag:Nonce (for decryption)."
)
async def crypto_aes_ocb_cipher(ctx, message: str, operation: Literal["encrypt", "decrypt"],
                                key: str):
    await ctx.response.defer(ephemeral=True)
    try:
        if operation == "encrypt":
            cipherText, tag, nonce = AES_OCBOperation(message, key, True)
            if cipherText == "Error":
                await ctx.followup.send("There was an error generating the nonce value, please try the command again.")
            else:
                await ctx.followup.send(f"Your Cipher Message is:\n{cipherText}\n"
                                        f"The decryption key is:\n{key}:{tag}:{nonce}")
        else:
            plainText = AES_OCBOperation(message, key, False)
            if plainText == "#1738175319":
                await ctx.followup.send("The original cipher text was tampered with a different AES key!")
            elif plainText == "#17381753112":
                await ctx.followup.send("Invalid AES key, tag, and nonce format!")
            else:
                await ctx.followup.send(f"Your Original Message is:\n{plainText}")
    except Exception:
        await ctx.followup.send(f"Invalid Key Format!")


@client.tree.command(
    name="crypto_pss_rsa_digital_signature",
    description="Generating or verifying Crypto PKCS#1 PSS RSA-Digital Signature (Cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text message to be signed OR verified",
    signature="Provide the signature to verify the message",
    operation="Select sign OR verify operations",
    key="Provide your private key to sign and public key to verify in PEM file format"
)
async def crypto_pss_rsa_digital_signature(ctx, message: str, operation: Literal["sign", "verify"], key: discord.Attachment, signature: str="Blank", ):
    await ctx.response.defer(ephemeral=True)
    try:
        signerOrVerifierKey = RSA.importKey(await key.read())
        hashed_msg = SHA256.new(message.encode())
        if operation == "sign":
            try:
                signature = pss.new(signerOrVerifierKey).sign(hashed_msg)
                await ctx.followup.send(
                    f"Your RSA Digital Signature is:\n{base64.b64encode(signature).decode('ascii')}")
            except TypeError:
                await ctx.followup.send(f"You must provide a private RSA key PEM file to sign!")
        else:
            verifier = pss.new(signerOrVerifierKey)
            try:
                verifier.verify(hashed_msg, base64.b64decode(signature))
                await ctx.followup.send(f"The RSA Digital Signature is valid!")
            except ValueError:
                await ctx.followup.send(f"The RSA Digital Signature is not valid!")
    except ValueError:
        await ctx.followup.send(f"You must provide an RSA key to sign or verify the message!")


@client.tree.command(
    name="crypto_ecc_key_generation",
    description="Generating Crypto ECC keys in pem file format."
)
@app_commands.describe(
    curve="Select the provided curve options"
)
async def crypto_ecc_key_generation(ctx, curve: Literal["p192", "p224", "p256", "p384", "p521", "ed25519", "ed448", "curve25519", "curve448"]):
    await ctx.response.defer(ephemeral=True)
    eccKey = ECC.generate(curve=curve)
    privateKey = eccKey.export_key(format="PEM")
    publicKey = eccKey.public_key().export_key(format="PEM")
    privateKeybuffer = BytesIO()
    publicKeybuffer = BytesIO()
    privateKeybuffer.write(privateKey.encode())
    publicKeybuffer.write(publicKey.encode())
    privateKeybuffer.seek(0)
    publicKeybuffer.seek(0)
    await ctx.followup.send(file=discord.File(fp=privateKeybuffer, filename=f"CryptoECC-{curve}PrivateKey.pem"))
    await ctx.followup.send(file=discord.File(fp=publicKeybuffer, filename=f"CryptoECC-{curve}PublicKey.pem"), ephemeral=True)


@client.tree.command(
    name="crypto_ecdsa",
    description="Generating or verifying Crypto ECC digital signature with NIST curves (Cryptographically secure)."
)
@app_commands.describe(
    message="Provide a plain text message to be signed OR verified",
    signature="Provide the signature to verify the message",
    operation="Select sign OR verify operations",
    key="Provide your private key to sign and public key to verify in PEM file format"
)
async def crypto_ecdsa(ctx, message: str, key: discord.Attachment, operation: Literal["sign", "verify"], signature: str="Blank", ):
    await ctx.response.defer(ephemeral=True)
    try:
        signerOrVerifierKey = ECC.import_key(await key.read())
        hashed_msg = SHA256.new(message.encode())
        if operation == "sign":
            try:
                signature = DSS.new(signerOrVerifierKey, "fips-186-3").sign(hashed_msg)
                await ctx.followup.send(f"Your ecdsa signature is:\n{base64.b64encode(signature).decode('ascii')}")
            except TypeError:
                await ctx.followup.send(f"You must provide an ECC-Nist curve private key PEM file to sign!")
            except ValueError:
                await ctx.followup.send(f"ECC key is not on a NIST P curve")
        else:
            try:
                verifier = DSS.new(signerOrVerifierKey, "fips-186-3")
                try:
                    verifier.verify(hashed_msg, base64.b64decode(signature))
                    await ctx.followup.send(f"The ecdsa signature is valid!")
                except ValueError:
                    await ctx.followup.send(f"The ecdsa signature is not valid!")
            except ValueError:
                await ctx.followup.send(f"ECC key is not on a NIST P curve")
    except ValueError:
        await ctx.followup.send(f"You must provide an ECC with NIST p-curve key to sign or verify the message!")



@client.event
async def on_message(message):
    return
    # Find URLs in the message -> Credit to GPT for 100% of the code
    urls = url_pattern.findall(message.content)
    if urls:
        for url in urls:
            if "gif" not in url:
                try:
                    # Make a request to the URL (this simulates visiting the link)
                    response = requests.get(url)
                    # Check if the link is reachable
                    if response.status_code == 200:
                        await message.channel.send(f'URL is reachable!')
                    else:
                        await message.channel.send(f'Failed to reach the URL (status code: {response.status_code})')
                except requests.exceptions.RequestException as e:
                    await message.channel.send(f'Error reaching URL: ({e})')

        for url in urls:
            if "gif" not in url:
                secureMeasure = 3
                await message.channel.send(f"Analyzing the URL...")

                # Step 1: Check if the URL uses HTTPS (secure)
                if url.startswith('https://'):
                    await message.channel.send(f"The link uses HTTPS (secure).")
                else:
                    secureMeasure -= 1
                    await message.channel.send(f"The link uses HTTP (not secure).")

                try:
                    # Step 2: Make a request to the URL to fetch its SSL certificate information and headers
                    response = requests.get(url, timeout=5, verify=True)  # Verify SSL certificate
                    await message.channel.send(f"Successfully connected to URL")

                    # Step 3: Check if security headers are present (e.g., HSTS)
                    if 'Strict-Transport-Security' in response.headers:
                        await message.channel.send(
                            f"Site enforces HSTS (Strict-Transport-Security): {response.headers['Strict-Transport-Security']}")
                    else:
                        secureMeasure -= 1
                        await message.channel.send(f"Site does not enforce HSTS (Strict-Transport-Security).")

                    # Step 4: Check if SSL certificate is valid (using response history for any redirections)
                    if response.history:
                        await message.channel.send(
                            f"The site was redirected {len(response.history)} time(s), ensure the final URL is "
                            f"also secure.")
                    else:
                        await message.channel.send(f"SSL Certificate is valid and secure.")

                except requests.exceptions.SSLError:
                    await message.channel.send(f"SSL Certificate verification failed! The connection is not"
                                               f" secure.")
                except requests.exceptions.RequestException as e:
                    await message.channel.send(f"Error visiting the link: {e}")

                if secureMeasure != 3:
                    await message.channel.send(f"The URL is not safe to visit!")
                else:
                    await message.channel.send(f"The URL is safe to visit!")

    await client.process_commands(message)


client.run(DISCORDAPI)
