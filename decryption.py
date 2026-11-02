import base64
from Crypto.Cipher import AES
import os
import dotenv
from dotenv import load_dotenv
load_dotenv()

key=os.getenv("key")

#Decrypt the Base64 string back to plaintext
def decrypt_string(encrypted_base64: str) -> str:
    # Decode Base64 string back to raw bytes
    raw_data = base64.b64decode(encrypted_base64.encode('utf-8'))
    key=os.getenv("ENCRYPTION_KEY")    
    bkey = base64.b64decode(key.encode('utf-8'))

    # Extract the nonce (first 16 bytes), tag (next 16 bytes), and ciphertext
    nonce = raw_data[:16]
    tag = raw_data[16:32]
    ciphertext = raw_data[32:]
    
    # Create cipher with the same key and the extracted nonce
    cipher = AES.new(bkey, AES.MODE_GCM, nonce=nonce)
    
    # Decrypt and verify integrity
    decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
    return decrypted_bytes.decode('utf-8')


