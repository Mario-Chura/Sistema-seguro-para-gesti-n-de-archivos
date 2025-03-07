# Importaciones necesarias
import os
import sqlite3
from flask import Flask, render_template, redirect, request, make_response, url_for, flash, send_file, session
from flask_mail import Mail, Message
from io import BytesIO
from werkzeug.utils import secure_filename
import hashlib
import logging
from dotenv import load_dotenv
from setup import start_db
from check import generate_token, check_token
import random
import datetime


# Importar Fernet para cifrado
from cryptography.fernet import Fernet


# Cargar variables de entorno
load_dotenv()

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Cargar la clave desde el archivo
with open("encryption_key.key", "rb") as key_file:
    encryption_key = key_file.read()

cipher = Fernet(encryption_key)

# Configuración de la carpeta de subida y tipos de archivos permitidos
UPLOAD_FOLDER = '/home/poisoniv/Code/COP4521/Project1/files'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#___________________________________________________________________________________

# Imprimir las variables para verificar que se cargaron correctamente
print("MAIL_USERNAME:", os.getenv('MAIL_USERNAME'))
print("MAIL_PASSWORD:", os.getenv('MAIL_PASSWORD'))

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Desde variables de entorno
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Desde variables de entorno

mail = Mail(app)

@app.route('/test_mail')
def test_mail():
    try:
        msg = Message(
            subject="Prueba de Flask-Mail",
            sender=os.getenv('MAIL_USERNAME'),
            recipients=["correo_destino@gmail.com"],  # Cambia por un correo válido
            body="Este es un mensaje de prueba enviado desde Flask."
        )
        mail.send(msg)
        return "Correo enviado con éxito."
    except Exception as e:
        return f"Error al enviar el correo: {e}"


#___________________________________________________________________________________

# Configuración del sistema de logs
logging.basicConfig(
    filename="admin_logs.log",  # Archivo donde se guardarán los logs
    level=logging.INFO,  # Nivel de logs
    format="%(asctime)s - %(levelname)s - %(message)s"  # Formato del log
)

# Función para registrar acciones
def log_action(action, username):
    """
    Registra una acción realizada por un usuario.
    """
    logging.info(f"Usuario: {username} - Acción: {action}")


#__________________________________________________________________________________
import random

def generate_verification_code():
    """
    Genera un código de verificación aleatorio de 6 dígitos.
    """
    return str(random.randint(100000, 999999))


@app.route('/send_verification', methods=['POST', 'GET'])
def send_verification():
    session_token = request.cookies.get('AuthToken')
    user_id = session.get('user_id')

    if not check_token(session_token, user_id):
        return "Acceso denegado", 403

    con = sqlite3.connect('database.db')
    try:
        cur = con.cursor()
        cur.execute("SELECT Email FROM Users WHERE WORKID = ?", (user_id,))
        user_email = cur.fetchone()[0]

        # Generar y guardar el código de verificación
        verification_code = generate_verification_code()
        session['verification_code'] = verification_code

        # Enviar el correo con el código de verificación
        msg = Message('Código de Verificación', sender=os.getenv('MAIL_USERNAME'), recipients=[user_email])
        msg.body = f'Tu código de verificación es: {verification_code}'
        mail.send(msg)  # Esta línea envía el correo

        return render_template('Verification.html', message="Hemos enviado un código a tu correo.")
    except Exception as e:
        logging.error(f"Error al enviar el código de verificación: {e}")
        return f"Error al enviar el correo: {e}", 500
    finally:
        con.close()



@app.route('/verify_code', methods=['POST'])
def verify_code():
    user_code = request.form['verification_code']
    stored_code = session.get('verification_code')  # Código almacenado en la sesión

    if user_code == stored_code:
        user_role = session.get('user_role', None)  # Obtener el rol de la sesión

        if user_role:
            # Redirigir según el rol obtenido
            if user_role == 'Admin':
                return redirect('/AdminMainPage')
            elif user_role == 'Manager':
                return redirect('/ManagerMainPage')
            elif user_role == 'User':
                return redirect('/UserMainPage')
            else:
                # Caso para manejar si el rol no es válido (no esperado)
                return "Rol de usuario no reconocido", 400
        else:
            return "No se pudo determinar el rol del usuario", 400
    else:
        # Código inválido
        return "Código de verificación incorrecto", 403



#__________________________________________________________________________________







# Configuración del sistema de logging
logging.basicConfig(level=logging.DEBUG)
# Variable global para almacenar el ID del usuario actual
user = ['']

# Ruta principal - Página de inicio
@app.route('/')
def front_page():
    return render_template('Login.html')

# Ruta de login - Maneja la autenticación de usuarios
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        con = sqlite3.connect('database.db')
        try:
            WorkID = request.form['WorkID']
            Password = request.form['Password']

            # Hash de la contraseña para comparar con la almacenada
            hashed_password = hashlib.sha256(Password.encode()).hexdigest()

            cur = con.cursor()

            # Busca el usuario en la base de datos
            cur.execute("SELECT * FROM Users WHERE WORKID = ?", (WorkID,))
            user = cur.fetchone()

            if not user:
                log_action("Intento de inicio de sesión fallido", WorkID)
                return render_template("NoMatchingUser.html")

            failed_attempts = user[6]  # Columna 'FailedAttempts'
            lock_time = user[7]  # Columna 'LockTime'

            # Si la cuenta está bloqueada
            if failed_attempts >= 5:
                # Si el bloqueo ha expirado, desbloquear la cuenta
                if lock_time:
                    lock_time = datetime.datetime.strptime(lock_time, '%Y-%m-%d %H:%M:%S')
                    if datetime.datetime.now() > lock_time:
                        cur.execute("UPDATE Users SET FailedAttempts = 0, LockTime = NULL WHERE WORKID = ?", (WorkID,))
                        con.commit()
                        failed_attempts = 0  # Reiniciar intentos fallidos
                    else:
                        return render_template("AccountLocked.html")

            print(f"a: {failed_attempts}, {lock_time}")

            # Verificar la contraseña
            if hashed_password != user[3]:
                # Incrementar el contador de intentos fallidos
                failed_attempts += 1

                print(f"b: {failed_attempts}, {lock_time}")

                if failed_attempts >= 5:

                    # Calcular el tiempo de bloqueo sumando 10 minutos a la hora actual
                    lock_time = datetime.datetime.now() + datetime.timedelta(minutes=1)

                    # Convertir a formato string para guardarlo en la base de datos
                    lock_time_str = lock_time.strftime('%Y-%m-%d %H:%M:%S')

                    # Actualizar la base de datos con el nuevo tiempo de bloqueo
                    cur.execute("UPDATE Users SET FailedAttempts = ?, LockTime = ? WHERE WORKID = ?", 
                                (failed_attempts, lock_time_str, WorkID))

                    print(f"c: {failed_attempts}, {lock_time_str}")

                    con.commit()
                else:
                    cur.execute("UPDATE Users SET FailedAttempts = ? WHERE WORKID = ?", (failed_attempts, WorkID))
                    con.commit()

                log_action("Intento de inicio de sesión fallido", WorkID)
                return render_template("NoMatchingPassword.html")

            # Si la contraseña es correcta, resetear el contador de intentos fallidos
            cur.execute("UPDATE Users SET FailedAttempts = 0 WHERE WORKID = ?", (WorkID,))
            con.commit()

            # Obtén el rol del usuario
            user_role = user[5]  # Columna 'Role'

            # Genera token de autenticación y guarda el ID del usuario en sesión
            token = generate_token(WorkID)

            # Guarda el rol en la sesión
            session['user_role'] = user_role
            session['user_id'] = user[0]

            # Registra inicio de sesión exitoso
            log_action("Inicio de sesión exitoso", WorkID)

            # Redirige a la verificación de token
            response = make_response(redirect("/send_verification"))
            response.set_cookie('AuthToken', token)
            return response

        except sqlite3.Error as e:
            logging.error(f"Database Error: {e}")
            return render_template("Error.html")
        except Exception as e:
            logging.error(f"Exception Error: {e}")
            return render_template("Error.html")
        finally:
            con.close()

# Ruta para el formulario de registro
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    return render_template('SignUp.html')

# Ruta para validar y procesar el registro de nuevos usuarios
@app.route('/signupvalid', methods=['POST'])
def signupvalid():
    if request.method == 'POST':
        con = sqlite3.connect('database.db')
        try:
            # Obtener datos del formulario
            firstName = request.form['First']
            lastName = request.form['Last']
            WorkID = request.form['WorkID']
            email = request.form['Email']  # Nuevo correo
            password = request.form['Password']
            confirm_pass = request.form['ConfirmPassword']

            if WorkID[0] == 'A':
                role = 'Admin'
            elif WorkID[0] == 'M':
                role = 'Manager'
            else:
                role = 'User'

            # Validar contraseñas
            if password != confirm_pass:
                return "Las contraseñas no coinciden", 400

            # Hash de la contraseña
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            with con:
                cur = con.cursor()

                # Verificar si el WorkID ya existe
                cur.execute("SELECT * FROM Users WHERE WORKID = ?", (WorkID,))
                if cur.fetchone():
                    return "El WorkID ya está registrado", 400

                # Insertar usuario en la base de datos
                cur.execute('''
                INSERT INTO Users (WORKID, Password, First, Last, Email, Role)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (WorkID, hashed_password, firstName, lastName, email, role))

                con.commit()

            return redirect("/")
        except Exception as e:
            logging.error(f"Error durante el registro: {e}")
            con.rollback()
            return "Error durante el registro", 500
        finally:
            con.close()

# Página principal para usuarios regulares
@app.route('/UserMainPage', methods=['POST', 'GET'])
def UserMain():
    session_token = request.cookies.get('AuthToken')
    user_id = session.get('user_id')

    if not session_token or not check_token(session_token, user_id):
        return render_template('TokenError.html')

    # Obtiene los archivos para mostrar
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Files ORDER BY FileId DESC")
    files = cur.fetchall()

    return render_template('UserMainPage.html', Files=files)

# Página principal para managers
@app.route('/ManagerMainPage', methods=['POST', 'GET'])
def ManagerMain():
    session_token = request.cookies.get('AuthToken')
    user_id = session.get('user_id')

    if not session_token or not check_token(session_token, user_id):
        return render_template('TokenError.html')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Files ORDER BY FileId DESC")
    files = cur.fetchall()

    return render_template('ManagerMainPage.html', Files=files)

# Página principal para administradores
@app.route('/AdminMainPage', methods=['POST', 'GET'])
def AdminMain():
    session_token = request.cookies.get('AuthToken')
    user_id = session.get('user_id')

    if not session_token or not check_token(session_token, user_id):
        return render_template('TokenError.html')

    # Obtiene tanto usuarios como archivos para mostrar
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Users")
    users = cur.fetchall()
    cur.execute("SELECT * FROM Files ORDER BY FileId DESC")
    files = cur.fetchall()

    return render_template('AdminMainPage.html', Users=users, Files=files)

# Función auxiliar para verificar tipos de archivo permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para subir archivos con cifrado
@app.route('/uploadfile', methods=['POST', 'GET'])
def uploadfile():
    # Obtener el rol del usuario desde la sesión
    user_role = session.get('user_role', None)
    user_id = session.get('user_id')

    if request.method == 'POST':
        session_token = request.cookies.get('AuthToken')
        user_id = session.get('user_id')

        if not session_token or not check_token(session_token, user_id):
            return render_template('TokenError.html')

        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_data = file.read()

            # Cifrar el archivo
            encrypted_data = cipher.encrypt(file_data)

            # Guarda el archivo cifrado en la base de datos
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Files (FileName, FileData, WorkID) VALUES (?, ?, ?)",
                (filename, encrypted_data, user_id)
            )
            conn.commit()
            conn.close()

            # Registrar en los logs
            log_action(f"Subió el archivo cifrado: {filename}", user_id)

        # Redirigir según el tipo de usuario
        if user_role == 'Admin':
            return redirect('/AdminMainPage')
        elif user_role == 'Manager':
            return redirect('/ManagerMainPage')

    return render_template('UploadFile.html', user_role=user_role)


# Ruta para descargar archivos con descifrado
@app.route('/download/<int:file_id>')
def downloadfile(file_id):
    conn = sqlite3.connect('database.db')
    user_id = session.get('user_id')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Files WHERE FileId=?", (file_id,))
    file = cursor.fetchone()
    conn.close()

    if file:
        file_name = file[1]
        encrypted_data = file[2]

        # Descifrar los datos del archivo
        decrypted_data = cipher.decrypt(encrypted_data)
        # Registrar en los logs
        log_action(f"Archivo '{file_name}' descifrado y enviado al usuario.", user_id)

        return send_file(BytesIO(decrypted_data), download_name=file_name, as_attachment=True)
    else:
        flash("Archivo no encontrado")
        return redirect(request.referrer)
    
# Ruta para eliminar archivos
@app.route('/deletefile/<int:file_id>')
def deletefile(file_id):
    conn = sqlite3.connect('database.db')
    user_id = session.get('user_id')
    cursor = conn.cursor()
    cursor.execute("SELECT FileName FROM Files WHERE FileId=?", (file_id,))
    file = cursor.fetchone()
    if file:
        filename = file[0]
        cursor.execute("DELETE FROM Files WHERE FileId=?", (file_id,))
        conn.commit()
        conn.close()

        # Registrar en los logs
        log_action(f"Eliminó el archivo: {filename}", user_id)
    else:
        conn.close()
    return redirect(request.referrer)

# Ruta para editar WorkIDs válidos (función administrativa)
@app.route('/EditWorkID', methods=['POST', 'GET'])
def EditWorkID():
    if request.method == 'POST':
        session_token = request.cookies.get('AuthToken')
        user_id = session.get('user_id')

        if not session_token or not check_token(session_token, user_id):
            return render_template('TokenError.html')

        action = request.form.get('action')
        work_id = request.form.get('work_id')

        # Procesa la acción solicitada
        if action == 'add':
            add_work_id(work_id)
        elif action == 'delete':
            delete_work_id(work_id)

    work_ids = fetch_work_ids()
    return render_template('EditWorkID.html', work_ids=work_ids)

# Función para añadir nuevo WorkID válido
def add_work_id(work_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Verifica si ya existe
    cursor.execute("SELECT * FROM ValidWorkID WHERE WORKID=?", (work_id,))
    existing_row = cursor.fetchone()

    if not existing_row:
        cursor.execute(
            "INSERT INTO ValidWorkID (WORKID) VALUES (?)", (work_id,))
        conn.commit()
    else:
        return

    conn.close()

# Función para eliminar WorkID válido
def delete_work_id(work_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    user_id = session.get('user_id')

    # Protege contra eliminación del usuario actual
    if work_id == user_id:
        return

    cursor.execute("DELETE FROM ValidWorkID WHERE WORKID=?", (work_id,))
    conn.commit()
    conn.close()

# Función para obtener todos los WorkIDs válidos
def fetch_work_ids():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT WORKID FROM ValidWorkID")
    work_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return work_ids

# Ruta para eliminar usuarios (función administrativa)
@app.route('/DeleteUser', methods=['POST', 'GET'])
def DeleteUser():
    if request.method == 'POST':
        session_token = request.cookies.get('AuthToken')
        user_id = session.get('user_id')

        if not session_token or not check_token(session_token, user_id):
            return render_template('TokenError.html')

        work_id = request.form.get('work_id')
        delete_user(work_id)
        return redirect(url_for('AdminMain'))

    users = fetch_user_names()
    return render_template('DeleteUser.html', users=users)

# Función para obtener lista de usuarios
def fetch_user_names():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT WORKID, First, Last FROM Users")
    users = cursor.fetchall()
    conn.close()
    return users

# Función para eliminar usuario
def delete_user(work_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Users WHERE WORKID=?", (work_id,))
    conn.commit()
    conn.close()

# Ruta para búsqueda de archivos
@app.route("/search", methods=['POST', 'GET'])
def searched():
    if request.method == "POST":
        conn = sqlite3.connect('database.db')
        user_id = session.get('user_id')
        try:
            searched = request.form["searched"]
            cur = conn.cursor()
            # Búsqueda en múltiples campos
            query = """
                SELECT * FROM Files
                WHERE FileID LIKE ?
                OR FileName LIKE ? COLLATE NOCASE
                OR WorkID LIKE ?
                ORDER BY FileID DESC"""

            cur.execute(query, ('%' + searched + '%', '%' +
                        searched + '%', '%' + searched + '%'))

            files = cur.fetchall()

            # Redirecciona según el tipo de usuario
            if user_id[0] == 'A':
                return render_template('AdminMainPage.html', Files=files)
            elif user_id[0] == 'M':
                return render_template('ManagerMainPage.html', Files=files)
            elif user_id[0] == 'U':
                return render_template('UserMainPage.html', Files=files)

        except:
            conn.rollback()
            return render_template('Error.html')
        finally:
            conn.close()

#________________________________________________________________________________________
@app.route('/admin/view_logs')
def view_logs():
    session_token = request.cookies.get('AuthToken')
    user_id = session.get('user_id')
    user_role = session.get('user_role', None)

    if not check_token(session_token, user_id) or user_role[0] != 'A':
        print(f"Token inválido o usuario no es administrador: {user_id}")
        return "Acceso denegado", 403

    try:
        log_file_path = os.path.join(os.getcwd(), 'admin_logs.log')
        print(f"Ruta del archivo de logs: {log_file_path}")
        
        # Verificar si el archivo de logs existe
        if not os.path.exists(log_file_path):
            print("El archivo de logs no existe")
            return "Archivo de logs no encontrado", 500
        
        # Leer el contenido del archivo de logs
        with open(log_file_path, "rb") as log_file:
            content = log_file.read()
            decoded_content = content.decode('utf-8', errors='ignore')  # Ignorar caracteres no decodificables
            all_logs = decoded_content.splitlines()  # Leer todas las líneas

        # Filtrar las líneas relevantes
        filtered_logs = [line for line in all_logs if "Usuario:" in line]

        # Renderizar el archivo Logs.html y pasar los logs filtrados como contexto
        return render_template("Logs.html", logs=filtered_logs)
    
    except Exception as e:
        logging.error(f"Error al leer el archivo de logs: {e}")
        return "No se pudo leer el archivo de logs", 500

#________________________________________________________________________________________


# Punto de entrada de la aplicación
if __name__ == "__main__":
    # Inicializa la base de datos
    start_db()
    # Inicia la aplicación en modo debug
    app.run(debug=True)