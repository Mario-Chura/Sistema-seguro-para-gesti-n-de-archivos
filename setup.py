import sqlite3

# Función para inicializar y configurar la base de datos
def start_db():
    # Conexión a la base de datos SQLite llamada 'database.db'
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Crear la tabla 'ValidWorkID' si no existe.
    # Esta tabla almacena los WorkIDs válidos y utiliza el campo WORKID como clave primaria.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ValidWorkID (
            WORKID TEXT PRIMARY KEY
        )
    ''')

    # Abrir el archivo 'workids.txt' para leer los WorkIDs válidos
    with open('workids.txt', 'r') as file:
        lines = file.readlines()  # Leer todas las líneas del archivo
        for line in lines:
            # Verificar si el WORKID ya existe en la tabla 'ValidWorkID'
            cursor.execute(
                "SELECT * FROM ValidWorkID WHERE WORKID=?", (line.strip(),))
            existing_row = cursor.fetchone()
            if not existing_row:
                # Si el WORKID no existe, agregarlo a la tabla 'ValidWorkID'
                cursor.execute(
                    "INSERT INTO ValidWorkID (WORKID) VALUES (?)", (line.strip(),))

        # Confirmar los cambios realizados en la base de datos
        conn.commit()

    # Crear la tabla 'Users' si no existe.
    # Esta tabla almacena la información de los usuarios registrados.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            WORKID TEXT PRIMARY KEY,  -- Clave primaria vinculada con 'ValidWorkID'
            First TEXT,               -- Nombre del usuario
            Last TEXT,                -- Apellido del usuario
            Password TEXT,            -- Contraseña del usuario (almacenada como hash)
            Role TEXT                 -- Rol del usuario (Admin, Manager, User)
        )
    ''')

    # Crear la tabla 'Files' si no existe.
    # Esta tabla almacena los archivos subidos por los usuarios.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            FileId INTEGER PRIMARY KEY AUTOINCREMENT,  -- ID único autoincremental para cada archivo
            FileName TEXT,                             -- Nombre del archivo
            FileData BLOB,                             -- Contenido del archivo almacenado como BLOB
            WorkID TEXT                                -- WorkID del usuario que subió el archivo
        )
    ''')

    # Cerrar el cursor para liberar recursos
    cursor.close()
