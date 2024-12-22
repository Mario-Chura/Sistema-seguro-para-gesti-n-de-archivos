# Importaciones necesarias
import sqlite3
from flask import Flask, render_template, redirect, request, make_response, url_for, flash, send_file, session
from io import BytesIO
from werkzeug.utils import secure_filename
import hashlib
import logging
from setup import start_db
from check import generate_token, check_token

# Configuración de la carpeta de subida y tipos de archivos permitidos
UPLOAD_FOLDER = '/home/poisoniv/Code/COP4521/Project1/files'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
            cur.execute("SELECT * FROM Users WHERE WORKID = ? AND Password = ?",
                        (WorkID, hashed_password))
            rows = cur.fetchall()
            if len(rows) == 0:
                return render_template("NoMatchingUser.html")

            # Genera token de autenticación
            token = generate_token(WorkID)
            user[0] = rows[0][0]

            # Redirecciona según el tipo de usuario (Admin, Manager, User)
            if WorkID[0] == 'A':
                response = make_response(redirect("/AdminMainPage"))
                response.set_cookie('AuthToken', token)
            elif WorkID[0] == 'M':
                response = make_response(redirect("/ManagerMainPage"))
                response.set_cookie('AuthToken', token)
            elif WorkID[0] == 'U':
                response = make_response(redirect("/UserMainPage"))
                response.set_cookie('AuthToken', token)

            return response

        except sqlite3.Error as e:
            logging.error(f"Database Error: {e}")
            return render_template("Error.html")
        except Exception as e:
            logging.error(f"Exception Error: {e}")
            return render_template("Error.html")
        except:
            return redirect("/")
        finally:
            con.close()

# Ruta para el formulario de registro
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    return render_template('SignUp.html')

# Ruta para validar y procesar el registro de nuevos usuarios
@app.route('/signupvalid', methods=['POST', 'GET'])
def signupvalid():
    if request.method == 'POST':
        con = sqlite3.connect('database.db')
        try:
            # Obtención de datos del formulario
            firstName = request.form['First']
            lastName = request.form['Last']
            WorkID = request.form['WorkID']
            password = request.form['Password']
            confirm_pass = request.form['ConfirmPassword']
            
            # Determina el rol basado en la primera letra del WorkID
            if WorkID[0] == 'A':
                role = 'Admin'
            elif WorkID[0] == 'M':
                role = 'Manager'
            else:
                role = 'User'
            user[0] = WorkID

            # Hash de la contraseña para almacenamiento seguro
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            with con:
                cur = con.cursor()

                # Verifica si el WorkID es válido
                if not cur.execute("SELECT * FROM ValidWorkID WHERE WORKID = ?", (WorkID,)).fetchall():
                    return render_template('InvalidWorkID.html')

                # Verifica si el WorkID ya existe
                if cur.execute("SELECT * FROM Users WHERE WORKID = ?", (WorkID,)).fetchone():
                    return render_template('InvalidWorkID.html')

                # Si las contraseñas coinciden, inserta el usuario
                if password == confirm_pass:
                    cur.execute("INSERT INTO Users (WORKID, Password, First, Last) VALUES (?,?,?,?)", (
                        WorkID, hashed_password, firstName, lastName))
                    cur.execute(
                        "UPDATE Users SET Role = ? WHERE WORKID = ?", (role, WorkID))

                return redirect("/")

        except Exception as e:
            logging.error(f"Error: {e}")
            con.rollback()
            return render_template('Error.html')
        finally:
            con.close()

# Página principal para usuarios regulares
@app.route('/UserMainPage', methods=['POST', 'GET'])
def UserMain():
    session_token = request.cookies.get('AuthToken')

    # Verifica el token de autenticación
    if not check_token(session_token, user[0]):
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
    if not check_token(session_token, user[0]):
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
    if not check_token(session_token, user[0]):
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

# Ruta para subir archivos
@app.route('/uploadfile', methods=['POST', 'GET'])
def uploadfile():
    if request.method == 'POST':
        session_token = request.cookies.get('AuthToken')
        if not check_token(session_token, user[0]):
            return render_template('TokenError.html')

        # Verifica que se haya enviado un archivo
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        # Verifica que se haya seleccionado un archivo
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        # Procesa el archivo si es válido
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_data = file.read()
            # Guarda el archivo en la base de datos
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Files (FileName, FileData, WorkID) VALUES (?, ?, ?)", (filename, file_data, user[0]))
            conn.commit()
            conn.close()

        # Redirecciona según el tipo de usuario
        if user[0][0] == 'A':
            return redirect(url_for('AdminMain'))
        elif user[0][0] == 'M':
            return redirect(url_for('ManagerMain'))
    return render_template('UploadFile.html')

# Ruta para descargar archivos
@app.route('/download/<int:file_id>')
def downloadfile(file_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Files WHERE FileId=?", (file_id,))
    file = cursor.fetchone()
    return send_file(BytesIO(file[2]), download_name=file[1], as_attachment=True)

# Ruta para eliminar archivos
@app.route('/deletefile/<int:file_id>')
def deletefile(file_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Files WHERE FileId=?", (file_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

# Ruta para editar WorkIDs válidos (función administrativa)
@app.route('/EditWorkID', methods=['POST', 'GET'])
def EditWorkID():
    if request.method == 'POST':
        session_token = request.cookies.get('AuthToken')
        if not check_token(session_token, user[0]):
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

    # Protege contra eliminación del usuario actual
    if work_id == user[0]:
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
        if not check_token(session_token, user[0]):
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
            if user[0][0] == 'A':
                return render_template('AdminMainPage.html', Files=files)
            elif user[0][0] == 'M':
                return render_template('ManagerMainPage.html', Files=files)
            elif user[0][0] == 'U':
                return render_template('UserMainPage.html', Files=files)

        except:
            conn.rollback()
            return render_template('Error.html')
        finally:
            conn.close()

# Punto de entrada de la aplicación
if __name__ == "__main__":
    # Inicializa la base de datos
    start_db()
    # Inicia la aplicación en modo debug
    app.run(debug=True)
