from flask import Flask, render_template, request, redirect, session, url_for, make_response
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database initialization (unchanged)
def init_db():
    if not os.path.exists(DATABASE):
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

# Updated index route: Convert tuples to dictionaries
@app.route('/')
def index():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Convert blog tuples to dictionaries
    blogs = [
        {'title': row[0], 'content': row[1]}
        for row in c.execute('SELECT title, content FROM blog').fetchall()
    ]
    # Convert portfolio tuples to dictionaries
    portfolio_entries = [
        {'title': row[0], 'description': row[1], 'image': row[2], 'video': row[3]}
        for row in c.execute('SELECT title, description, image, video FROM portfolio').fetchall()
    ]
    conn.close()
    # Add no-cache headers (optional)
    response = make_response(render_template('index.html', blogs=blogs, portfolio_entries=portfolio_entries))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    return response

# Login route (unchanged)
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

# Dashboard route (unchanged)
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

# Logout route (unchanged)
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

# Updated add-blog route: Redirect to homepage
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
    return redirect('/')  # Changed to redirect to homepage

# Updated add-portfolio route: Handle optional files and fix paths
@app.route('/add-portfolio', methods=['POST'])
def add_portfolio():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    description = request.form['description']
    image_file = request.files.get('image')
    video_file = request.files.get('video')

    image_filename = None
    video_filename = None

    # Handle image upload
    if image_file and image_file.filename:
        image_filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)
        image_file.save(image_path)
        image_filename = f'uploads/{image_filename}'  # Store with uploads/ prefix

    # Handle video upload
    if video_file and video_file.filename:
        video_filename = secure_filename(video_file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        video_file.save(video_path)
        video_filename = f'uploads/{video_filename}'  # Store with uploads/ prefix

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO portfolio (title, description, image, video) VALUES (?, ?, ?, ?)",
              (title, description, image_filename, video_filename))
    conn.commit()
    conn.close()
    return redirect('/')  # Changed to redirect to homepage

# Delete blog route (unchanged)
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

# Delete portfolio route (unchanged)
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

# Updated edit-blog route: Redirect to homepage
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
        return redirect('/')  # Changed to redirect to homepage
    blog = c.execute("SELECT * FROM blog WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('edit_blog.html', blog=blog)

# Updated edit-portfolio route: Handle optional files and fix paths
@app.route('/edit-portfolio/<int:id>', methods=['GET', 'POST'])
def edit_portfolio(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image_file = request.files.get('image')
        video_file = request.files.get('video')

        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)
            image_file.save(image_path)
            c.execute("UPDATE portfolio SET image = ? WHERE id = ?", (f'uploads/{image_filename}', id))

        if video_file and video_file.filename:
            video_filename = secure_filename(video_file.filename)
            video_path = os.path.join(UPLOAD_FOLDER, video_filename)
            video_file.save(video_path)
            c.execute("UPDATE portfolio SET video = ? WHERE id = ?", (f'uploads/{video_filename}', id))

        c.execute("UPDATE portfolio SET title = ?, description = ? WHERE id = ?", (title, description, id))
        conn.commit()
        conn.close()
        return redirect('/')  # Changed to redirect to homepage

    portfolio = c.execute("SELECT * FROM portfolio WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('edit_portfolio.html', portfolio=portfolio)

if __name__ == '__main__':
    app.run(debug=True)