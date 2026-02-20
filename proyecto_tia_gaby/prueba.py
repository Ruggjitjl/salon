from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import qrcode
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_2026"

DB = "database.db"

# -------------------------
# CREAR BASE DE DATOS
# -------------------------

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        correo TEXT UNIQUE,
        password TEXT,
        puntos INTEGER DEFAULT 0,
        dias INTEGER DEFAULT 0,
        nivel TEXT DEFAULT 'Bronce'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS rewards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        puntos INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------
# HOME
# -------------------------

@app.route("/")
def index():
    return render_template("index.html")

# -------------------------
# REGISTER
# -------------------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        nombre = request.form["nombre"]
        correo = request.form["correo"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        try:

            c.execute("INSERT INTO users(nombre,correo,password) VALUES(?,?,?)",
                      (nombre,correo,password))

            conn.commit()

            user_id = c.lastrowid

            # crear QR
            qr = qrcode.make(str(user_id))

            path = f"static/qr/{user_id}.png"

            os.makedirs("static/qr", exist_ok=True)

            qr.save(path)

        except:
            return "Usuario ya existe"

        conn.close()

        return redirect("/login")

    return render_template("register.html")

# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE correo=? AND password=?",
                  (correo,password))

        user = c.fetchone()

        conn.close()

        if user:

            session["user_id"] = user[0]

            return redirect("/dashboard")

        else:

            return "Login incorrecto"

    return render_template("login.html")

# -------------------------
# DASHBOARD
# -------------------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))

    user = c.fetchone()

    conn.close()

    return render_template("dashboard.html", user=user)

# -------------------------
# ADMIN LOGIN
# -------------------------

@app.route("/admin", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        password = request.form["password"]

        if password == "admin123":

            session["admin"] = True

            return redirect("/admin_panel")

        else:

            return "Password incorrecto"

    return render_template("admin_login.html")

# -------------------------
# ADMIN PANEL
# -------------------------

@app.route("/admin_panel")
def admin_panel():

    if "admin" not in session:
        return redirect("/admin")

    return render_template("admin_panel.html")

# -------------------------
# SCAN QR
# -------------------------

@app.route("/scan_qr", methods=["POST"])
def scan_qr():

    if "admin" not in session:
        return jsonify({"status":"error"})

    user_id = request.json["data"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT dias FROM users WHERE id=?", (user_id,))
    dias = c.fetchone()[0]

    dias += 1
    puntos = dias

    # niveles
    nivel = "Bronce"

    if dias >= 30:
        nivel = "Oro"

    elif dias >= 15:
        nivel = "Plata"

    c.execute("""
    UPDATE users
    SET dias=?, puntos=?, nivel=?
    WHERE id=?
    """,(dias,puntos,nivel,user_id))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":
    app.run(debug=True)