from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import datetime


class db_context:
    def __enter__(self):
        self.db = sqlite3.connect("db.sqlite3")
        c = self.db.cursor()
        return c
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        self.db.commit()
        self.db.close()


app = Flask(__name__)
app.secret_key = b'\x0c\x17?\xf8\x94j\xab\xfdJP\x04]U,\xf2\x9a'
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app, cors_allowed_origins="*")

with db_context() as c:
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password BLOB NOT NULL,
            bio TEXT,
            joined TEXT
        )
    """)

def get_user_by_username(username: str):
    with db_context() as c:
        c.execute("SELECT id, username, bio, joined FROM users WHERE username = ?", (username,))
        user = c.fetchone()
    if user:
        return {"id": user[0], "username": user[1], "bio": user[2], "joined": user[3]}
    return None

def get_user_by_id(user_id: int):
    with db_context() as c:
        c.execute("SELECT id, username, bio, joined FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
    if user:
        return {"id": user[0], "username": user[1], "bio": user[2], "joined": user[3]}
    return None

def update_user(user: dict, original_id: int):
    with db_context() as c:
        c.execute("SELECT COUNT(*) FROM users WHERE username = ? AND id != ?", (user["username"], original_id))
        if c.fetchone()[0] > 0:
            raise sqlite3.IntegrityError("Username already exists")
        c.execute("UPDATE users SET username = ?, bio = ? WHERE id = ?", (user["username"], user["bio"], original_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template('login.html', errors=["Username and password are required."])
        
        with db_context() as c:
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user or not check_password_hash(user[1], password):
                return render_template('login.html', errors=["Invalid username or password."])
            session["user_id"] = user[0]
        return redirect(url_for("profile"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not password or not confirm_password:
            return render_template('register.html', errors=["All fields are required."])
        if password != confirm_password:
            return render_template('register.html', errors=["Passwords do not match."])

        hashed_password = generate_password_hash(password)
        joined = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with db_context() as c:
            try:
                c.execute("INSERT INTO users (username, password, bio, joined) VALUES (?, ?, ?, ?)", (username, hashed_password, "", joined))
            except sqlite3.IntegrityError:
                return render_template('register.html', errors=["Username already exists."])
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/profile")
@app.route("/profile/<username>")
def profile(username=None):
    if username:
        user = get_user_by_username(username)
    else:
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = get_user_by_id(session["user_id"])
    
    if not user:
        return redirect(url_for("login"))
    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 403
    
    data = request.json
    field = data.get("field")
    new_value = data.get("value")

    if field not in ["username", "bio"]:
        return jsonify({"success": False, "error": "Invalid field"}), 400

    user = get_user_by_id(session['user_id'])
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    user[field] = new_value
    try:
        update_user(user, session['user_id'])
        if field == "username":
            session["username"] = new_value
    except sqlite3.IntegrityError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({"success": True})


@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for('login'))
    user_id = session["user_id"]

    with db_context() as c:
        c.execute("SELECT username, joined, bio FROM users WHERE id != ? ORDER BY RANDOM() LIMIT 1", (user_id,))
        user = c.fetchone()
    user_dict = {
        "username": user[0],
        "joined": user[1], 
        "bio": user[2]
    }
    
    return render_template("chat.html", user=user_dict)


@app.route('/set-user-id', methods=['POST'])
def set_user_id():
    # Check if user is logged in
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 403

    # Get data from the POST request
    data = request.get_json()
    user_id = data.get('id')

    # Ensure that user_id is provided
    if not user_id:
        return jsonify({"success": False, "error": "User ID not provided"}), 400

    session["chat_with_user_id"] = user_id
    session["chat_with_username"] = target_user["username"]

    return jsonify({"success": True, "message": "User ID saved successfully"})



@app.route("/chat/<username>")
def chat_with(username:str):
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_user = get_user_by_id(session["user_id"])

    if not current_user:
        return redirect(url_for("login"))

    target_user = get_user_by_username(username)
    session["chat_with_user_id"] = target_user["id"]
    
    return render_template("chat.html", current_user=current_user, target_user=target_user)


@app.route('/friends')
def friends():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Retrieve the current user from the session
    current_user = get_user_by_id(session["user_id"])
    return render_template('friends.html')


@socketio.on('message')
def handle_message(msg):
    print(f"Received: {msg}")
    socketio.send(f"Echo: {msg}")

@socketio.on('custom_event')
def handle_custom_event(data):
    print(f"Received custom event: {data}")
    socketio.emit('response', {'message': 'Message received!'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
