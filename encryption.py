import base64
from Crypto.Cipher import AES

import os
#from dotenv import load_dotenv
#load_dotenv()

key=os.getenv("ENCRYPTION_KEY")

# Encrypt a string
def encrypt_string(plain_text: str, key: str) -> str:
    # Convert text to bytes
    data = plain_text.encode('utf-8')
    bkey = base64.b64decode(key.encode('utf-8'))

    # Create AES cipher in GCM mode (generates a random nonce automatically)
    cipher = AES.new(bkey, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    
    # Pack nonce, tag, and ciphertext together, then encode in Base64 for a safe string representation
    result = base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')
    return result

