from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import qrcode
import uuid
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"

# crear carpetas si no existen
os.makedirs("static/qr", exist_ok=True)

# crear base de datos
def init_db():

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY,
        nombre TEXT,
        correo TEXT,
        password TEXT,
        puntos INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS rewards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        reward TEXT,
        claimed INTEGER DEFAULT 0
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS citas(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    fecha TEXT,
    hora TEXT,
    servicio TEXT,
    estado TEXT DEFAULT 'pendiente'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# calcular nivel
def calcular_nivel(puntos):

    if puntos >= 30:
        return "ORO"

    elif puntos >= 15:
        return "PLATA"

    else:
        return "BRONCE"

# obtener icono
def obtener_icono(nivel):

    if nivel == "ORO":
        return "oro.png"

    elif nivel == "PLATA":
        return "plata.png"

    else:
        return "bronce.png"

# INDEX
@app.route("/")
def index():
    return render_template("index.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        nombre = request.form["nombre"]
        correo = request.form["correo"]
        password = request.form["password"]

        user_id = str(uuid.uuid4())

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "INSERT INTO users VALUES(?,?,?,?,0)",
            (user_id,nombre,correo,password)
        )

        conn.commit()
        conn.close()

        # generar QR
        img = qrcode.make(user_id)
        img.save(f"static/qr/{user_id}.png")

        return redirect("/login")

    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        correo = request.form["correo"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE correo=? AND password=?",
            (correo,password)
        )

        user = c.fetchone()

        conn.close()

        if user:

            session["user"] = user[0]

            return redirect("/dashboard")

    return render_template("login.html")

# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    c.execute("SELECT * FROM rewards WHERE user_id=? AND claimed=0",(user_id,))
    rewards = c.fetchall()
    c.execute("SELECT * FROM citas WHERE user_id=?", (user_id,))
    citas = c.fetchall()

    conn.close()

    nivel = calcular_nivel(user[4])
    icono = obtener_icono(nivel)

    return render_template(
        "dashboard.html",
        nombre=user[1],
        puntos=user[4],
        qr=user[0],
        nivel=nivel,
        icono=icono,
        rewards=rewards,
        citas=citas
    )
@app.route("/crear_cita", methods=["POST"])
def crear_cita():

    if "user" not in session:
        return redirect("/login")

    fecha = request.form["fecha"]
    hora = request.form["hora"]
    servicio = request.form["servicio"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO citas(user_id, fecha, hora, servicio)
    VALUES(?,?,?,?)
    """,(session["user"], fecha, hora, servicio))

    conn.commit()
    conn.close()

    return redirect("/dashboard")
@app.route("/admin_citas")
def admin_citas():

    if not session.get("admin"):
        return jsonify([])

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    citas = c.execute("""
    SELECT users.nombre, citas.fecha, citas.hora, citas.servicio
    FROM citas
    JOIN users ON citas.user_id = users.id
    """).fetchall()

    conn.close()

    eventos = []

    for cita in citas:

        eventos.append({
            "title": f"{cita[0]} - {cita[3]} ({cita[2]})",
            "start": cita[1],
            "color": "#D4AF37",
            "textColor": "#000000"
        })

    return jsonify(eventos)
@app.route("/admin_stats")
def admin_stats():

    if not session.get("admin"):
        return jsonify({"error":"no autorizado"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    usuarios = c.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    citas = c.execute(
        "SELECT COUNT(*) FROM citas"
    ).fetchone()[0]

    puntos = c.execute(
        "SELECT SUM(puntos) FROM users"
    ).fetchone()[0] or 0

    conn.close()

    return jsonify({
        "usuarios": usuarios,
        "citas": citas,
        "puntos": puntos
    })

@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method == "POST":

        if request.form["password"] == "admin123":

            session["admin"] = True

            return redirect("/admin_panel")

    return render_template("admin_login.html")

# ADMIN PANEL
@app.route("/admin_panel")
def admin_panel():

    if "admin" not in session:
        return redirect("/admin")

    return render_template("admin_panel.html")

# SCAN QR
@app.route("/scan_qr", methods=["POST"])
def scan_qr():

    if "admin" not in session:
        return jsonify({"status":"error"})

    user_id = request.json["data"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute(
        "UPDATE users SET puntos = puntos + 1 WHERE id=?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# ADMIN REWARDS
@app.route("/admin_rewards", methods=["GET","POST"])
def admin_rewards():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        user_id = request.form["user_id"]
        reward = request.form["reward"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute(
            "INSERT INTO rewards(user_id,reward) VALUES(?,?)",
            (user_id,reward)
        )

        conn.commit()
        conn.close()

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM rewards")
    rewards = c.fetchall()

    conn.close()

    return render_template("admin_rewards.html", rewards=rewards)

# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# RUN
if __name__ == "__main__":
    app.run(debug=True)
