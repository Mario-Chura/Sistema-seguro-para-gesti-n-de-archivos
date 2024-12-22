import hashlib
secret_mod = 18446744073709551615  # Un número muy grande usado como un módulo para limitar el valor del hash



def generate_token(WorkID):
    """
    Genera un token basado en el ID de trabajo (WorkID).
    El token se genera usando el hash SHA-256 del WorkID, convertido a un entero, 
    y luego reducido utilizando un módulo grande (secret_mod).

    Parámetros:
        WorkID (str): El ID de trabajo del usuario.

    Retorna:
        str: El token generado como una cadena.
    """
    hashed_role = int(hashlib.sha256(WorkID.encode()).hexdigest(), 16) % secret_mod
    return str(hashed_role)

def check_token(token, WorkID):
    """
    Verifica si un token es válido comparándolo con el token generado a partir del WorkID.

    Parámetros:
        token (str): El token a validar.
        WorkID (str): El ID de trabajo asociado al usuario.

    Retorna:
        bool: True si el token es válido, False en caso contrario.
    """
    hashed_role = int(hashlib.sha256(WorkID.encode()).hexdigest(), 16) % secret_mod
    token = int(token)  # Convierte el token recibido a un entero para la comparación
    return hashed_role == token  # Devuelve True si el token coincide, False si no
