from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key'

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS blog (id INTEGER PRIMARY KEY, title TEXT, content TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            image TEXT,
            video TEXT
        )''')
        conn.commit()
        conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    blogs = c.execute('SELECT title, content FROM blog').fetchall()
    portfolios = c.execute('SELECT title, description, image, video FROM portfolio').fetchall()
    conn.close()
    return render_template('index.html', blogs=blogs, portfolio_entries=portfolios)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email') or request.form.get('username')
        password = request.form['password']
        if email == "admin@example.com" and password == "admin123":
            session['admin'] = True
            return redirect('/dashboard')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    blogs = c.execute("SELECT * FROM blog").fetchall()
    portfolios = c.execute("SELECT * FROM portfolio").fetchall()
    conn.close()
    return render_template('dashboard.html', blogs=blogs, portfolios=portfolios)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

# Blog routes
@app.route('/add-blog', methods=['POST'])
def add_blog():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    content = request.form['content']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO blog (title, content) VALUES (?, ?)", (title, content))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/edit-blog/<int:id>', methods=['GET', 'POST'])
def edit_blog(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        c.execute("UPDATE blog SET title = ?, content = ? WHERE id = ?", (title, content, id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    blog = c.execute("SELECT * FROM blog WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('edit_blog.html', blog=blog)

@app.route('/delete-blog/<int:id>')
def delete_blog(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM blog WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

# Portfolio routes
@app.route('/add-portfolio', methods=['POST'])
def add_portfolio():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    description = request.form['description']
    image = request.files['image']
    video = request.files['video']
    img_fn = secure_filename(image.filename)
    vid_fn = secure_filename(video.filename)
    image.save(os.path.join(UPLOAD_FOLDER, img_fn))
    video.save(os.path.join(UPLOAD_FOLDER, vid_fn))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO portfolio (title, description, image, video) VALUES (?, ?, ?, ?)",
        (title, description, img_fn, vid_fn)
    )
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/edit-portfolio/<int:id>', methods=['GET', 'POST'])
def edit_portfolio(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image = request.files.get('image')
        video = request.files.get('video')
        if image and image.filename:
            img_fn = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, img_fn))
            c.execute("UPDATE portfolio SET image = ? WHERE id = ?", (img_fn, id))
        if video and video.filename:
            vid_fn = secure_filename(video.filename)
            video.save(os.path.join(UPLOAD_FOLDER, vid_fn))
            c.execute("UPDATE portfolio SET video = ? WHERE id = ?", (vid_fn, id))
        c.execute(
            "UPDATE portfolio SET title = ?, description = ? WHERE id = ?",
            (title, description, id)
        )
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    portfolio = c.execute("SELECT * FROM portfolio WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('edit_portfolio.html', portfolio=portfolio)

@app.route('/delete-portfolio/<int:id>')
def delete_portfolio(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM portfolio WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True)