# generate_key.py
from cryptography.fernet import Fernet

# Generate a key
key = Fernet.generate_key()
print(f"Encryption Key: {key.decode()}")

# Save this key securely, for example, in an environment variable or a secure file
