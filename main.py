import sqlite3
from flask import Flask, render_template, redirect, request, make_response, url_for, flash, send_file, session
from io import BytesIO
from werkzeug.utils import secure_filename
import hashlib
import logging
from setup import start_db  # Importa la función para inicializar la base de datos
from check import generate_token, check_token  # Funciones para generar y validar tokens

# Configuración inicial
UPLOAD_FOLDER = '/home/poisoniv/Code/COP4521/Project1/files'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)  # Inicializa la aplicación Flask
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'  # Clave secreta para manejo de sesiones
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Carpeta donde se almacenan los archivos subidos

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)
user = ['']  # Variable para almacenar el ID del usuario autenticado

# Ruta principal
@app.route('/')
def front_page():
    return render_template('Login.html')  # Carga la página de inicio de sesión

# Ruta para el inicio de sesión
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        con = sqlite3.connect('database.db')
        try:
            # Obtiene el ID de trabajo y contraseña desde el formulario
            WorkID = request.form['WorkID']
            Password = request.form['Password']

            # Genera el hash de la contraseña para compararla con la base de datos
            hashed_password = hashlib.sha256(Password.encode()).hexdigest()

            cur = con.cursor()

            # Consulta para verificar si el usuario existe
            cur.execute("SELECT * FROM Users WHERE WORKID = ? AND Password = ?", (WorkID, hashed_password))
            rows = cur.fetchall()
            if len(rows) == 0:  # Si no hay resultados, muestra una página de error
                return render_template("NoMatchingUser.html")

            # Genera un token y guarda el ID del usuario
            token = generate_token(WorkID)
            user[0] = rows[0][0]

            # Redirige según el rol del usuario
            if WorkID[0] == 'A':
                response = make_response(redirect("/AdminMainPage"))
            elif WorkID[0] == 'M':
                response = make_response(redirect("/ManagerMainPage"))
            elif WorkID[0] == 'U':
                response = make_response(redirect("/UserMainPage"))
            response.set_cookie('AuthToken', token)  # Guarda el token en una cookie
            return response

        except sqlite3.Error as e:
            logging.error(f"Database Error: {e}")
            return render_template("Error.html")  # Muestra una página de error en caso de problema con la base de datos
        except Exception as e:
            logging.error(f"Exception Error: {e}")
            return render_template("Error.html")  # Manejo genérico de errores
        finally:
            con.close()  # Cierra la conexión con la base de datos

# Ruta para la página de registro
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    return render_template('SignUp.html')

# Ruta para validar el registro
@app.route('/signupvalid', methods=['POST', 'GET'])
def signupvalid():
    if request.method == 'POST':
        con = sqlite3.connect('database.db')
        try:
            # Obtiene los datos del formulario de registro
            firstName = request.form['First']
            lastName = request.form['Last']
            WorkID = request.form['WorkID']
            password = request.form['Password']
            confirm_pass = request.form['ConfirmPassword']

            # Determina el rol del usuario según el prefijo del WorkID
            if WorkID[0] == 'A':
                role = 'Admin'
            elif WorkID[0] == 'M':
                role = 'Manager'
            else:
                role = 'User'
            user[0] = WorkID

            # Genera el hash de la contraseña
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            with con:
                cur = con.cursor()

                # Verifica si el WorkID es válido
                if not cur.execute("SELECT * FROM ValidWorkID WHERE WORKID = ?", (WorkID,)).fetchall():
                    return render_template('InvalidWorkID.html')

                # Verifica si el WorkID ya está en uso
                if cur.execute("SELECT * FROM Users WHERE WORKID = ?", (WorkID,)).fetchone():
                    return render_template('InvalidWorkID.html')

                # Si las contraseñas coinciden, inserta al nuevo usuario en la base de datos
                if password == confirm_pass:
                    cur.execute("INSERT INTO Users (WORKID, Password, First, Last) VALUES (?,?,?,?)", (
                        WorkID, hashed_password, firstName, lastName))
                    cur.execute("UPDATE Users SET Role = ? WHERE WORKID = ?", (role, WorkID))

                return redirect("/")  # Redirige al inicio

        except Exception as e:
            logging.error(f"Error: {e}")
            con.rollback()  # Revierte cambios si ocurre un error
            return render_template('Error.html')
        finally:
            con.close()

# Otras rutas importantes:
# - `/UserMainPage`, `/ManagerMainPage`, `/AdminMainPage`: muestran las páginas principales de cada rol.
# - `/uploadfile`: permite a los usuarios subir archivos.
# - `/deletefile`: permite eliminar archivos.
# - `/EditWorkID`: permite agregar o eliminar WorkIDs válidos.
# - `/DeleteUser`: permite eliminar usuarios.
# - `/search`: permite buscar archivos.

# Lanza la aplicación
if __name__ == "__main__":
    start_db()  # Inicializa la base de datos
    app.run(debug=True)  # Ejecuta la aplicación en modo de depuración
