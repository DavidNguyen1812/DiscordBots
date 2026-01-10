import random
import math
import string
import base64
# pip install pycryptodome
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import AES

S = ['08', 'a5', 'e9', '09', '45', 'c0', 'ed', 'f1',
     '5d', 'fd', '34', 'c3', '4e', '7b', '9d', '96',
     '38', '76', '7c', '49', '8f', 'd9', '35', 'cc',
     '99', 'b0', '2d', '97', 'e7', '1d', 'a9', '16',
     '7d', '10', '8c', '89', '51', 'a1', 'd7', '5b',
     '3d', '1c', '23', '1e', 'e0', 'b2', '84', 'a8',
     'c5', '24', '86', 'b9', '07', 'ac', 'f0', '52',
     '32', '92', 'da', '06', 'e4', 'd4', '82', 'd5',
     'db', 'ae', '04', '4c', '36', 'c6', '19', '2e',
     'b4', '2c', '69', 'c7', 'ce', '71', '91', 'a6',
     'de', '22', '59', 'f4', '54', '25', '42', '0d',
     'ff', '03', '0a', '44', '87', '37', '8e', '12',
     '30', '33', '58', '3a', '81', 'f3', '8d', '9f',
     'bd', 'c4', '95', '73', '93', '55', '41', 'b6',
     '90', '63', '9c', '18', '77', 'dd', 'e3', 'c9',
     '8a', 'b1', '7f', 'ee', 'e5', 'ad', '05', 'a0',
     '6d', '15', 'c2', 'ab', '7a', 'a4', '3f', '00',
     '48', 'a3', 'd1', '4a', '75', 'b7', '85', 'd8',
     'fb', 'fe', 'f2', 'e6', '13', '56', 'ec', 'a7',
     '9a', 'e2', '64', '53', '5f', '65', 'd3', 'c8',
     '68', '74', '02', 'dc', '6f', '43', 'e1', '8b',
     'bf', 'a2', '2a', '80', 'bb', '6a', '28', '78',
     '17', 'f6', 'fc', '67', 'b3', '9e', 'cb', '31',
     'f9', 'aa', '9b', '2b', 'b8', '1a', '3e', 'f8',
     'd2', '5c', '20', '11', '4b', '3b', '0b', '6e',
     'af', 'ca', '6b', '60', '94', '5a', '61', '27',
     'b5', '7e', '4d', 'be', '57', '26', 'cf', 'ef',
     'bc', '40', '72', '14', '83', '47', 'f7', '1b',
     '79', '50', '1f', '3c', '5e', '0f', 'f5', '62',
     '6c', '21', '70', '4f', 'eb', 'ea', '98', 'fa',
     'ba', '46', '01', 'cd', '88', '0e', '39', 'c1',
     'd0', 'df', '2f', '0c', '29', '66', 'd6', 'e8']

tapList = [['A', 'B', 'C', 'D', 'E'],
           ['F', 'G', 'H', 'I', 'K'],
           ['L', 'M', 'N', 'O', 'P'],
           ['Q', 'R', 'S', 'T', 'U'],
           ['V', 'W', 'X', 'Y', 'Z']]

morseList = ["-----", ".----", "..---", "...--", "....-",
             ".....", "-....", "--...", "---..", "----.",
             ".-", "-...", "-.-.", "-..", ".", "..-.",
             "--.", "....", "..", ".---", "-.-", ".-..",
             "--", "-.", "---", ".--.", "--.-", ".-.",
             "...", "-", "..-", "...-", ".--", "-..-",
             "-.--", "--.."]

T = [s for s in S]


def list_shuffle(option):
    original = [char for char in string.printable]
    new = []
    if option == 3:  # inverse the first half then second half
        n = int(len(original) / 2) - 1
        while n != -1:
            new.append(original[n])
            n -= 1
        n = len(original) - 1
        while n != int(len(original) / 2) - 1:
            new.append(original[n])
            n -= 1
    elif option % 2 == 0 and option > 3:  # inverse the first half
        n = int(len(original) / 2) - 1
        while n != -1:
            new.append(original[n])
            n -= 1
        n = int(len(original) / 2)
        while n != len(original):
            new.append(original[n])
            n += 1
    elif option > 3 and option % 2 == 1:  # inverse the second half
        n = 0
        while n != int(len(original) / 2):
            new.append(original[n])
            n += 1
        n = len(original) - 1
        while n != ((len(original) / 2) - 1):
            new.append(original[n])
            n -= 1

    if option == 1 or option >= 6:  # swap place between two item
        if option >= 6:
            original = new[:]
            new = []
        n = 0
        while n != len(original):
            new.append(original[n + 1])
            new.append(original[n])
            n += 2
        new = new[:]
    if option == 2 or option >= 8:  # inverse the whole list
        if option >= 8:
            original = new[:]
        new = original[::-1]
    return new


def encryption(phrase, OFFSET, shuffled):
    encrypted_phrase = ''
    for i in range(len(phrase)):
        Index = (shuffled.index(phrase[i])) - int(OFFSET[0] + OFFSET[1])
        if Index < 0:
            if not len(str(Index)) > 2:
                Index = '-0' + str(abs(Index))
        if not len(str(Index)) > 1:
            Index = '0' + str(Index)
        encrypted_phrase = encrypted_phrase + str(Index)
    return encrypted_phrase + OFFSET


def decipher(phrase, shuffled):
    off_num = int(phrase[len(phrase) - 3] + phrase[len(phrase) - 2])
    num = 0
    deciphered_phrase = ''
    while num != len(phrase) - 3:
        if phrase[num] != '-':
            Index = int(phrase[num] + phrase[num + 1]) + off_num
            num += 2
        else:
            Index = int(phrase[num] + phrase[num + 1] + phrase[num + 2]) + off_num
            num += 3
        deciphered_phrase = deciphered_phrase + shuffled[Index]
    return deciphered_phrase


def DavidEncryption(plainText):
    shuffle_method = random.randint(1, 9)
    shuffled_list = list_shuffle(shuffle_method)
    Offset = random.randint(1, 99)
    Offset = str(Offset) + str(shuffle_method)
    if len(Offset) == 2:
        Offset = '0' + Offset
    cipherText = f"{encryption(plainText, Offset, shuffled_list)}:{Offset}"
    return cipherText


def DavidDecipher(cipherText, key):
    shuffled_list = list_shuffle(int(key[2]))
    plainText = decipher(cipherText, shuffled_list)
    return plainText


def RC4(encrypt, i, j, Input):
    S = [t for t in T]
    result = ''
    for p in range(len(Input)):
        i = (i + 1) % 256
        j = (j + int(S[i], 16)) % 256
        S[i], S[j] = S[j], S[i]
        t = (int(S[i], 16) + int(S[j], 16)) % 256
        key = S[t]
        if encrypt:
            result += hex(ord(Input[p]) ^ int(key, 16)) + ' '
        else:
            result += chr(int(Input[p], 16) ^ int(key, 16))
    return result


def tapCodeDecoder(message):
    result = ''
    for char in message:
        if '.' in char:
            char = char.split(' ')
            result += tapList[len(char[0]) - 1][len(char[1]) - 1]
    return result


def MorseCodeDecoder(message):
    result = ''
    message = message.split(" ")
    for code in message:
        for i in range(len(morseList)):
            if morseList[i] == code:
                if i <= 9:
                    result += str(i)
                else:
                    result += chr(i + 55).lower()
    return result


def railFenceCipher(rail, message, encrypt=True):
    result = ''
    if encrypt:
        rows = [[] for _ in range(rail)]
        counterUp = True
        row = 0
        for p in range(len(message)):
            rows[row].append(message[p])
            if (row == 0 and p != 0) or row == rail - 1:
                counterUp = not counterUp
            row += 1 if counterUp else -1
        for row in rows:
            result += ''.join(row)
        return result
    else:
        # Decryption
        rail_map = [['\n' for _ in range(len(message))] for _ in range(rail)]
        counterUp = True
        row = 0
        for p in range(len(message)):
            rail_map[row][p] = '*'
            if (row == 0 and p != 0) or row == rail - 1:
                counterUp = not counterUp
            row += 1 if counterUp else -1

        index = 0
        for i in range(rail):
            for j in range(len(message)):
                if rail_map[i][j] == '*' and index < len(message):
                    rail_map[i][j] = message[index]
                    index += 1

        result = ''
        row = 0
        counterUp = True
        for p in range(len(message)):
            result += rail_map[row][p]
            if (row == 0 and p != 0) or row == rail - 1:
                counterUp = not counterUp
            row += 1 if counterUp else -1

        return result


def randomSubstitutionCipher(stringKey, message, encrypt):
    result = ''
    alphabet = [letter.lower() for letter in stringKey]
    if not encrypt:
        for letter in message:
            if letter.isalpha() and letter.lower() in alphabet:
                if letter.isupper():
                    result += chr(alphabet.index(letter.lower()) + 97).upper()
                else:
                    result += chr(alphabet.index(letter.lower()) + 97)
            else:
                result += letter
    else:
        for letter in message:
            if letter.isalpha() and letter.lower() in alphabet:
                if letter.isupper():
                    result += alphabet[ord(letter.lower()) - 97].upper()
                else:
                    result += alphabet[ord(letter.lower()) - 97]
            else:
                result += letter
    return result


def isPrime(n, k=5):  # Miller-Rabin test, 100% credited to chatGPT
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2

    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, s, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def TextBookRSAKeyGeneration():
    while True:
        p = random.randint(2 ** 512, 2 ** 1024)
        q = random.randint(2 ** 512, 2 ** 1024)
        if isPrime(p) and isPrime(q):
            break
    n = p * q
    tot_n = (p - 1) * (q - 1)
    e = random.randint(65537, tot_n)

    # Ensure e and tot_n are coprime
    while math.gcd(e, tot_n) != 1:
        e = random.randint(65537, tot_n - 1)
    d = pow(e, -1, tot_n)
    return e, n, d


def TextBookRSAoperation(text, key, n, encrypt):
    # 100% credited to chatGPT

    chunkSize = (n.bit_length() - 1) // 8  # Max safe plaintext size in bytes
    modulusByteSize = (n.bit_length() + 7) // 8  # Full size of RSA block
    if encrypt:

        # Encode plaintext to bytes
        encoded = text.encode('utf-8')

        # Split plaintext into chunks
        chunks = [encoded[i:i + chunkSize] for i in range(0, len(encoded), chunkSize)]

        # Encrypting each chunk
        encryptedChunks = [
            pow(int.from_bytes(chunk, 'big'), key, n).to_bytes(modulusByteSize, 'big')
            for chunk in chunks
        ]

        # Join and base64-encode to get ASCII-friendly ciphertext
        cipherBytes = b''.join(encryptedChunks)
        cipherBase64 = base64.b64encode(cipherBytes).decode('ascii')

        return cipherBase64
    else:
        # Decode base64
        cipherBytes = base64.b64decode(text)

        # Split into encrypted blocks
        encryptedBlocks = [cipherBytes[i:i + chunkSize + 1] for i in
                           range(0, len(cipherBytes), chunkSize + 1)]
        # Decrypt
        decryptedBytes = b''.join(
            pow(int.from_bytes(block, 'big'), key, n).to_bytes(modulusByteSize - 1, 'big')
            for block in encryptedBlocks
        )

        plaintext = decryptedBytes.decode('utf-8', errors='ignore')
        fixedPlainText = ''
        for char in plaintext:
            fixedPlainText += char if char.isprintable() else ''
        return fixedPlainText


def CryptoRSAOperation(text, key, encrypt):
    #  https://www.pycryptodome.org/src/examples#encrypt-data-with-rsa
    cipherRSA = PKCS1_OAEP.new(key)
    if encrypt:
        cipherText = cipherRSA.encrypt(text)
        return base64.b64encode(cipherText).decode('ascii')
    else:
        plainText = cipherRSA.decrypt(base64.b64decode(text))
        return plainText.decode('utf-8')


def AES_OCBOperation(text, key, encrypt):
    if encrypt:
        cipher = AES.new(base64.b64decode(key), AES.MODE_OCB)
        ciphertext, tag = cipher.encrypt_and_digest(text.encode('utf-8'))
        try:
            assert len(cipher.nonce) == 15, "Nonce is not 15 bytes!"
        except AssertionError:
            return "Error", "Error", "Error"
        return base64.b64encode(ciphertext).decode('ascii'), base64.b64encode(tag).decode('ascii'), \
               base64.b64encode(cipher.nonce).decode('ascii')
    else:
        key = key.split(':')
        if len(key) != 3:
            return "#17381753112"
        cipher = AES.new(base64.b64decode(key[0]), AES.MODE_OCB, nonce=base64.b64decode(key[2]))
        try:
            plaintext = cipher.decrypt_and_verify(base64.b64decode(text), base64.b64decode(key[1]))
        except ValueError:
            return "#1738175319"
        return plaintext.decode('utf-8')
