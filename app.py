from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure tables exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS blog (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            image TEXT,
            video TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    blogs = c.execute('SELECT title, content FROM blog').fetchall()
    portfolio_entries = c.execute('SELECT title, description, image, video FROM portfolio').fetchall()
    conn.close()
    return render_template('index.html', blogs=blogs, portfolio_entries=portfolio_entries)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == "admin@example.com" and password == "admin123":
            session['admin'] = True
            return redirect('/dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

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

@app.route('/add-blog', methods=['POST'])
def add_blog():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form.get('title')
    content = request.form.get('content')
    if not title or not content:
        return "Title and content required", 400
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO blog (title, content) VALUES (?, ?)", (title, content))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/add-portfolio', methods=['POST'])
def add_portfolio():
    if not session.get('admin'):
        return redirect('/login')

    title = request.form.get('title')
    description = request.form.get('description')
    image_file = request.files.get('image')
    video_file = request.files.get('video')

    if not title or not description or not image_file or not video_file:
        return "All fields are required", 400

    if not (allowed_file(image_file.filename) and allowed_file(video_file.filename)):
        return "Invalid file type", 400

    image_filename = secure_filename(image_file.filename)
    video_filename = secure_filename(video_file.filename)

    image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO portfolio (title, description, image, video) VALUES (?, ?, ?, ?)",
              (title, description, image_filename, video_filename))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

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

@app.route('/edit-blog/<int:id>', methods=['GET', 'POST'])
def edit_blog(id):
    if not session.get('admin'):
        return redirect('/login')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            return "Title and content required", 400
        c.execute("UPDATE blog SET title = ?, content = ? WHERE id = ?", (title, content, id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    blog = c.execute("SELECT * FROM blog WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not blog:
        return "Blog not found", 404
    return render_template('edit_blog.html', blog=blog)

@app.route('/edit-portfolio/<int:id>', methods=['GET', 'POST'])
def edit_portfolio(id):
    if not session.get('admin'):
        return redirect('/login')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image_file = request.files.get('image')
        video_file = request.files.get('video')

        if not title or not description:
            return "Title and description required", 400

        if image_file and image_file.filename and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            c.execute("UPDATE portfolio SET image = ? WHERE id = ?", (image_filename, id))

        if video_file and video_file.filename and allowed_file(video_file.filename):
            video_filename = secure_filename(video_file.filename)
            video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))
            c.execute("UPDATE portfolio SET video = ? WHERE id = ?", (video_filename, id))

        c.execute("UPDATE portfolio SET title = ?, description = ? WHERE id = ?", (title, description, id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    portfolio = c.execute("SELECT * FROM portfolio WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not portfolio:
        return "Portfolio not found", 404
    return render_template('edit_portfolio.html', portfolio=portfolio)

if __name__ == '__main__':
    app.run(debug=True)
