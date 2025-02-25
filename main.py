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
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password BLOB, bio TEXT, joined TEXT)")


def get_user(username:str):
    with db_context() as c:
        c.execute("SELECT username, bio, joined FROM users WHERE username = ?", (username,))
        user = c.fetchone()
    if user:
        user_dict: dict = {
            "username": user[0],
            "bio": user[1],
            "joined": user[2]
        }
        return user_dict
    else:
        return None

def update_user(user: dict[str, str], original_username: str):
    # Check if the new username already exists (except for the current user)
    with db_context() as c:
        c.execute("SELECT COUNT(*) FROM users WHERE username = ? AND username != ?", (user["username"], original_username))
        if c.fetchone()[0] > 0:
            raise sqlite3.IntegrityError("Username already exists")

    # If no conflict, proceed with the update
    with db_context() as c:
        c.execute("UPDATE users SET username = ?, bio = ? WHERE username = ?", (user["username"], user["bio"], original_username))



@app.route('/')
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        errors = []
        username = request.form.get("username")
        if username is None:
            errors.append("You need to put a username to log in.")
        password = request.form.get("password")
        if password is None:
            errors.append("You need to put the password to log in.")
        
        if errors:
            return render_template('register.html', errors=errors)
        
        with db_context() as c:
            c.execute("SELECT password FROM users WHERE username = ?", (username,))
            user_pass_hashed = c.fetchone()
            if user_pass_hashed is None:
                errors.clear()
                errors.append("This username does not exist")
                return render_template('login.html', errors=errors)
            else:
                if check_password_hash(user_pass_hashed[0], password):
                    flash("You registered successfully. You can now log in.", "success")
                    session["username"] = username
                    return redirect(url_for("profile"))
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        errors = []
        username = request.form.get("username")
        if username is None:
            errors.append("Username is required to create an account.")
        password = request.form.get("password")
        if password is None:
            errors.append("Password is required to create an account.")
        confirm_password = request.form.get("confirm_password")
        if confirm_password is None:
            errors.append("You must confirm your password.")

        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        if password != confirm_password:
            errors.append("Passwords do not match")

        if errors:
            return render_template('register.html', errors=errors)
        
        hashed_password = generate_password_hash(password)

        with db_context() as c:
            try:
                joined: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO USERS VALUES (?, ?, ?, ?)", (username, hashed_password, "", joined))
            except sqlite3.Error:
                errors.clear()
                errors.append("This username already exists")
                return render_template('register.html', errors=errors)
        flash("You registered successfully. You can now log in.", "success")
        return redirect(url_for("login"))
        
    else:
        return render_template("register.html")


@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for('login'))
    username = session["username"]

    with db_context() as c:
        c.execute("SELECT username, joined, bio FROM users WHERE username != ? ORDER BY RANDOM() LIMIT 1", (username,))
        user = c.fetchone()
    user_dict = {
        "username": user[0],
        "joined": user[1], 
        "bio": user[2]
    }
    
    return render_template("chat.html", user=user_dict)
        


@app.route('/friends')
def friends():
    return render_template('friends.html')

@app.route('/profile')
@app.route("/profile/<username>")
def profile(username=None):
    if username is None:
        if 'username' not in session:
            return redirect(url_for('login'))
        username = session["username"]
    
    user = get_user(username)
    if user is None:
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)


@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'username' not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 403
    
    data = request.json
    field = data.get("field")
    new_value = data.get("value")

    # Ensure field is allowed
    if field not in ["username", "bio"]:
        return jsonify({"success": False, "error": "Invalid field"}), 400

    # Update database
    user = get_user(session['username'])
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    if field == "username":
        user["username"] = new_value
    elif field == "bio":
        user["bio"] = new_value

    try:
        update_user(user, session['username'])  # Function to save changes in DB
        session["username"] = user["username"]
    except sqlite3.IntegrityError as e:
        print(f"Database error: {e}")  # Log the specific error
        return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({"success": True})




@socketio.on('message')
def handle_message(msg):
    print(f"Received: {msg}")
    socketio.send(f"Echo: {msg}")  # Send response to all clients

@socketio.on('custom_event')
def handle_custom_event(data):
    print(f"Received custom event: {data}")
    socketio.emit('response', {'message': 'Message received!'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
