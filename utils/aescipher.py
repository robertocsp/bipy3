import base64
from Crypto.Cipher import AES
from Crypto import Random


class AESCipher:
    def __init__(self, key=None, bs=32):
        self.block_size = bs
        self.key = key if key is not None else Random.new().read(self.block_size)
        self.pad = lambda s: s + (self.block_size - len(s) % self.block_size) * chr(self.block_size - len(s) %
                                                                                    self.block_size)
        self.unpad = lambda s: s[:-ord(s[len(s)-1:])]

    def encrypt(self, raw):
        raw = self.pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return self.unpad(cipher.decrypt(enc[AES.block_size:]))
