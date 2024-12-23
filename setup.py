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

    # Crear la tabla 'Users' si no existe o actualizar su esquema para incluir el campo Email
    # Esta tabla almacena la información de los usuarios registrados.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            WORKID TEXT PRIMARY KEY,  -- Clave primaria vinculada con 'ValidWorkID'
            First TEXT NOT NULL,      -- Nombre del usuario
            Last TEXT NOT NULL,       -- Apellido del usuario
            Password TEXT NOT NULL,   -- Contraseña del usuario (almacenada como hash)
            Email TEXT NOT NULL,      -- Correo electrónico del usuario
            Role TEXT NOT NULL        -- Rol del usuario (Admin, Manager, User)
        )
    ''')

    # Verificar si la columna 'Email' existe (en caso de actualización de la tabla)
    cursor.execute("PRAGMA table_info(Users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'Email' not in columns:
        # Agregar la columna 'Email' si no existe
        cursor.execute("ALTER TABLE Users ADD COLUMN Email TEXT NOT NULL")

    if 'FailedAttempts' not in columns:
        # Agregar la columna 'FailedAttempts' si no existe
        cursor.execute("ALTER TABLE Users ADD COLUMN FailedAttempts INTEGER DEFAULT 0")

    if 'LockTime' not in columns:
        # Agregar la columna 'LockTime' si no existe
        cursor.execute("ALTER TABLE Users ADD COLUMN LockTime TEXT")

    # Crear la tabla 'Files' si no existe.
    # Esta tabla almacena los archivos subidos por los usuarios.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Files (
            FileId INTEGER PRIMARY KEY AUTOINCREMENT,  -- ID único autoincremental para cada archivo
            FileName TEXT NOT NULL,                   -- Nombre del archivo
            FileData BLOB NOT NULL,                   -- Contenido del archivo almacenado como BLOB
            WorkID TEXT NOT NULL                      -- WorkID del usuario que subió el archivo
        )
    ''')

    # Confirmar cambios y cerrar el cursor
    conn.commit()
    cursor.close()
