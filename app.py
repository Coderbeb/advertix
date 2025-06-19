from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from functools import wraps
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            filename TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            filename TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    blogs = c.execute('SELECT title, content FROM blog').fetchall()
    portfolios = c.execute('SELECT * FROM portfolio').fetchall()
    portfolio_entries = []
    for p in portfolios:
        images = [row['filename'] for row in c.execute("SELECT filename FROM portfolio_images WHERE portfolio_id=?", (p['id'],))]
        videos = [row['filename'] for row in c.execute("SELECT filename FROM portfolio_videos WHERE portfolio_id=?", (p['id'],))]
        portfolio_entries.append({
            'id': p['id'],
            'title': p['title'],
            'description': p['description'],
            'images': images,
            'videos': videos
        })
    conn.close()
    return render_template('index.html', blogs=blogs, portfolio_entries=portfolio_entries)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == "coderbeb@gmail.com" and password == "coderbeb??80":
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
@login_required
def dashboard():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    blogs = c.execute("SELECT * FROM blog").fetchall()
    portfolios = c.execute("SELECT * FROM portfolio").fetchall()
    portfolio_list = []
    for p in portfolios:
        images = [row['filename'] for row in c.execute("SELECT filename FROM portfolio_images WHERE portfolio_id=?", (p['id'],))]
        videos = [row['filename'] for row in c.execute("SELECT filename FROM portfolio_videos WHERE portfolio_id=?", (p['id'],))]
        portfolio_list.append({
            'id': p['id'],
            'title': p['title'],
            'description': p['description'],
            'images': images,
            'videos': videos
        })
    conn.close()
    return render_template('dashboard.html', blogs=blogs, portfolios=portfolio_list)

@app.route('/add-blog', methods=['POST'])
@login_required
def add_blog():
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
@login_required
def add_portfolio():
    title = request.form.get('title')
    description = request.form.get('description')
    images = request.files.getlist('images')
    videos = request.files.getlist('videos')

    if not title or not description:
        return "Title and description required", 400

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO portfolio (title, description) VALUES (?, ?)", (title, description))
    portfolio_id = c.lastrowid

    # Save images if any
    for image in images:
        if image and image.filename and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            c.execute("INSERT INTO portfolio_images (portfolio_id, filename) VALUES (?, ?)", (portfolio_id, filename))

    # Save videos if any
    for video in videos:
        if video and video.filename and allowed_file(video.filename):
            filename = secure_filename(video.filename)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            c.execute("INSERT INTO portfolio_videos (portfolio_id, filename) VALUES (?, ?)", (portfolio_id, filename))

    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/delete-blog/<int:id>')
@login_required
def delete_blog(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM blog WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/delete-portfolio/<int:id>')
@login_required
def delete_portfolio(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Delete images and videos files from disk
    images = c.execute("SELECT filename FROM portfolio_images WHERE portfolio_id=?", (id,)).fetchall()
    for img in images:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], img[0])
        if os.path.exists(img_path):
            os.remove(img_path)
    videos = c.execute("SELECT filename FROM portfolio_videos WHERE portfolio_id=?", (id,)).fetchall()
    for vid in videos:
        vid_path = os.path.join(app.config['UPLOAD_FOLDER'], vid[0])
        if os.path.exists(vid_path):
            os.remove(vid_path)
    # Delete from DB
    c.execute("DELETE FROM portfolio_images WHERE portfolio_id=?", (id,))
    c.execute("DELETE FROM portfolio_videos WHERE portfolio_id=?", (id,))
    c.execute("DELETE FROM portfolio WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/edit-blog/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_blog(id):
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
@login_required
def edit_portfolio(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        images = request.files.getlist('images')
        videos = request.files.getlist('videos')

        if not title or not description:
            return "Title and description required", 400

        c.execute("UPDATE portfolio SET title = ?, description = ? WHERE id = ?", (title, description, id))

        # Optionally add new images
        for image in images:
            if image and image.filename and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                c.execute("INSERT INTO portfolio_images (portfolio_id, filename) VALUES (?, ?)", (id, filename))

        # Optionally add new videos
        for video in videos:
            if video and video.filename and allowed_file(video.filename):
                filename = secure_filename(video.filename)
                video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                c.execute("INSERT INTO portfolio_videos (portfolio_id, filename) VALUES (?, ?)", (id, filename))

        conn.commit()
        conn.close()
        return redirect('/dashboard')

    portfolio = c.execute("SELECT * FROM portfolio WHERE id = ?", (id,)).fetchone()
    images = [row[0] for row in c.execute("SELECT filename FROM portfolio_images WHERE portfolio_id=?", (id,))]
    videos = [row[0] for row in c.execute("SELECT filename FROM portfolio_videos WHERE portfolio_id=?", (id,))]
    conn.close()
    if not portfolio:
        return "Portfolio not found", 404
    return render_template('edit_portfolio.html', portfolio=portfolio, images=images, videos=videos)

@app.route('/delete-portfolio-image/<int:portfolio_id>/<filename>')
@login_required
def delete_portfolio_image(portfolio_id, filename):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM portfolio_images WHERE portfolio_id=? AND filename=?", (portfolio_id, filename))
    conn.commit()
    conn.close()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('edit_portfolio', id=portfolio_id))

@app.route('/delete-portfolio-video/<int:portfolio_id>/<filename>')
@login_required
def delete_portfolio_video(portfolio_id, filename):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM portfolio_videos WHERE portfolio_id=? AND filename=?", (portfolio_id, filename))
    conn.commit()
    conn.close()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('edit_portfolio', id=portfolio_id))

if __name__ == '__main__':
    app.run(debug=True)