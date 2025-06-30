import os
import sqlite3
import requests
import io
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from drive_utils import upload_to_drive, delete_file_from_drive, backup_database_to_drive, download_database_from_drive

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://drive.google.com"]}})  # Added for CORS support
DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            filename TEXT,
            file_id TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            filename TEXT,
            file_id TEXT,
            FOREIGN KEY (portfolio_id) REFERENCES portfolio(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS blog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )''')
        conn.commit()

@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM blog ORDER BY id DESC LIMIT 3")
    blogs = c.fetchall()
    c.execute("SELECT * FROM portfolio")
    portfolios = c.fetchall()
    entries = []
    for p in portfolios:
        images = [dict(filename=row['filename'], file_id=row['file_id']) for row in c.execute("SELECT filename, file_id FROM portfolio_images WHERE portfolio_id=?", (p['id'],))]
        videos = [dict(filename=row['filename'], file_id=row['file_id']) for row in c.execute("SELECT filename, file_id FROM portfolio_videos WHERE portfolio_id=?", (p['id'],))]
        entries.append({
            'id': p['id'],
            'title': p['title'],
            'description': p['description'],
            'images': images,  # Now includes file_id for proxy
            'videos': videos
        })
    conn.close()
    return render_template('index.html', blogs=blogs, portfolio_entries=entries)

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM portfolio")
    portfolios = c.fetchall()
    entries = []
    for p in portfolios:
        images = [dict(url=row['filename'], file_id=row['file_id'], id=row['id']) for row in c.execute("SELECT * FROM portfolio_images WHERE portfolio_id=?", (p['id'],))]
        videos = [dict(url=row['filename'], file_id=row['file_id'], id=row['id']) for row in c.execute("SELECT * FROM portfolio_videos WHERE portfolio_id=?", (p['id'],))]
        entries.append({
            'id': p['id'],
            'title': p['title'],
            'description': p['description'],
            'images': images,
            'videos': videos
        })
    c.execute("SELECT * FROM blog")
    blogs = c.fetchall()
    conn.close()
    return render_template('dashboard.html', portfolios=entries, blogs=blogs)

@app.route('/add-portfolio', methods=['POST'])
def add_portfolio():
    title = request.form['title']
    description = request.form['description']
    images = request.files.getlist('images')
    videos = request.files.getlist('videos')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO portfolio (title, description) VALUES (?, ?)", (title, description))
    portfolio_id = c.lastrowid

    for image in images:
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            public_url, file_id = upload_to_drive(filepath, filename, 'image/jpeg')
            if public_url and file_id:
                c.execute("INSERT INTO portfolio_images (portfolio_id, filename, file_id) VALUES (?, ?, ?)",
                         (portfolio_id, public_url, file_id))
            os.remove(filepath)

    for video in videos:
        if video and allowed_file(video.filename):
            filename = secure_filename(video.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video.save(filepath)
            public_url, file_id = upload_to_drive(filepath, filename, 'video/mp4')
            if public_url and file_id:
                c.execute("INSERT INTO portfolio_videos (portfolio_id, filename, file_id) VALUES (?, ?, ?)",
                         (portfolio_id, public_url, file_id))
            os.remove(filepath)

    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/edit-portfolio/<int:id>')
def edit_portfolio(id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM portfolio WHERE id=?", (id,))
    portfolio = c.fetchone()
    images = [dict(id=row['id'], portfolio_id=row['portfolio_id'], filename=row['filename'], file_id=row['file_id'])
              for row in c.execute("SELECT * FROM portfolio_images WHERE portfolio_id=?", (id,))]
    videos = [dict(id=row['id'], portfolio_id=row['portfolio_id'], filename=row['filename'], file_id=row['file_id'])
              for row in c.execute("SELECT * FROM portfolio_videos WHERE portfolio_id=?", (id,))]
    conn.close()
    return render_template('edit_portfolio.html', portfolio=portfolio, images=images, videos=videos)

@app.route('/edit-portfolio/<int:id>', methods=['POST'])
def update_portfolio(id):
    title = request.form['title']
    description = request.form['description']
    images = request.files.getlist('images')
    videos = request.files.getlist('videos')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE portfolio SET title=?, description=? WHERE id=?", (title, description, id))

    for image in images:
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            public_url, file_id = upload_to_drive(filepath, filename, 'image/jpeg')
            if public_url and file_id:
                c.execute("INSERT INTO portfolio_images (portfolio_id, filename, file_id) VALUES (?, ?, ?)",
                         (id, public_url, file_id))
            os.remove(filepath)

    for video in videos:
        if video and allowed_file(video.filename):
            filename = secure_filename(video.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video.save(filepath)
            public_url, file_id = upload_to_drive(filepath, filename, 'video/mp4')
            if public_url and file_id:
                c.execute("INSERT INTO portfolio_videos (portfolio_id, filename, file_id) VALUES (?, ?, ?)",
                         (id, public_url, file_id))
            os.remove(filepath)

    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/delete-portfolio/<int:id>')
def delete_portfolio(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM portfolio_images WHERE portfolio_id=?", (id,))
    image_file_ids = [row[0] for row in c.fetchall()]
    c.execute("SELECT file_id FROM portfolio_videos WHERE portfolio_id=?", (id,))
    video_file_ids = [row[0] for row in c.fetchall()]

    for file_id in image_file_ids + video_file_ids:
        delete_file_from_drive(file_id)

    c.execute("DELETE FROM portfolio_images WHERE portfolio_id=?", (id,))
    c.execute("DELETE FROM portfolio_videos WHERE portfolio_id=?", (id,))
    c.execute("DELETE FROM portfolio WHERE id=?", (id,))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/delete-portfolio-image/<int:image_id>/<int:portfolio_id>')
def delete_portfolio_image(image_id, portfolio_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM portfolio_images WHERE id=?", (image_id,))
    file_id = c.fetchone()[0]
    delete_file_from_drive(file_id)
    c.execute("DELETE FROM portfolio_images WHERE id=?", (image_id,))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('edit_portfolio', id=portfolio_id))

@app.route('/delete-portfolio-video/<int:video_id>/<int:portfolio_id>')
def delete_portfolio_video(video_id, portfolio_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM portfolio_videos WHERE id=?", (video_id,))
    file_id = c.fetchone()[0]
    delete_file_from_drive(file_id)
    c.execute("DELETE FROM portfolio_videos WHERE id=?", (video_id,))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('edit_portfolio', id=portfolio_id))

@app.route('/add-blog', methods=['POST'])
def add_blog():
    title = request.form['title']
    content = request.form['content']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO blog (title, content) VALUES (?, ?)", (title, content))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/edit-blog/<int:id>')
def edit_blog(id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM blog WHERE id=?", (id,))
    blog = c.fetchone()
    conn.close()
    return render_template('edit_blog.html', blog=blog)

@app.route('/edit-blog/<int:id>', methods=['POST'])
def update_blog(id):
    title = request.form['title']
    content = request.form['content']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE blog SET title=?, content=? WHERE id=?", (title, content, id))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/delete-blog/<int:id>')
def delete_blog(id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM blog WHERE id=?", (id,))
    conn.commit()
    conn.close()
    backup_database_to_drive()
    return redirect(url_for('dashboard'))

@app.route('/proxy-image/<file_id>')
def proxy_image(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        return send_file(io.BytesIO(response.content), mimetype='image/jpeg')
    return "Image not found", 404

@app.route('/debug-images')
def debug_images():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    images = c.execute("SELECT filename, file_id FROM portfolio_images").fetchall()
    conn.close()
    return {"images": [{"filename": row["filename"], "file_id": row["file_id"]} for row in images]}

@app.route('/logout')
def logout():
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    download_database_from_drive()
    app.run(debug=True)