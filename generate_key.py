# generate_key.py
from cryptography.fernet import Fernet

# Generar una clave y guardarla en un archivo
key = Fernet.generate_key()
with open("encryption_key.key", "wb") as key_file:
    key_file.write(key)
print("Clave de cifrado generada y guardada en 'encryption_key.key'.")