from flask import Flask, render_template, request, redirect, session, url_for import sqlite3 import os from werkzeug.utils import secure_filename

app = Flask(name) app.secret_key = 'your_secret_key'

DATABASE = 'database.db' UPLOAD_FOLDER = 'static/uploads' os.makedirs(UPLOAD_FOLDER, exist_ok=True)

Ensure the database exists

def init_db(): if not os.path.exists(DATABASE): conn = sqlite3.connect(DATABASE) c = conn.cursor() c.execute('''CREATE TABLE IF NOT EXISTS blog (id INTEGER PRIMARY KEY, title TEXT, content TEXT)''') c.execute('''CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY, title TEXT, description TEXT, image TEXT, video TEXT)''') conn.commit() conn.close()

init_db()

@app.route('/') def index(): conn = sqlite3.connect(DATABASE) c = conn.cursor() blogs = c.execute('SELECT title, content FROM blog').fetchall() portfolio_entries = c.execute('SELECT title, description, image, video FROM portfolio').fetchall() conn.close() return render_template('index.html', blogs=blogs, portfolio_entries=portfolio_entries)

@app.route('/login', methods=['GET', 'POST']) def login(): if request.method == 'POST': email = request.form['email'] password = request.form['password'] if email == "admin@example.com" and password == "admin123": session['admin'] = True return redirect('/dashboard') else: return "Invalid credentials" return render_template('login.html')

@app.route('/dashboard') def dashboard(): if not session.get('admin'): return redirect('/login') conn = sqlite3.connect(DATABASE) c = conn.cursor() blogs = c.execute("SELECT * FROM blog").fetchall() portfolios = c.execute("SELECT * FROM portfolio").fetchall() conn.close() return render_template('dashboard.html', blogs=blogs, portfolios=portfolios)

@app.route('/logout') def logout(): session.pop('admin', None) return redirect('/login')

@app.route('/add-blog', methods=['POST']) def add_blog(): if not session.get('admin'): return redirect('/login') title = request.form['title'] content = request.form['content'] conn = sqlite3.connect(DATABASE) c = conn.cursor() c.execute("INSERT INTO blog (title, content) VALUES (?, ?)", (title, content)) conn.commit() conn.close() return redirect('/dashboard')

@app.route('/add-portfolio', methods=['POST']) def add_portfolio(): if not session.get('admin'): return redirect('/login') title = request.form['title'] description = request.form['description'] image_file = request.files['image'] video_file = request.files['video']

image_filename = secure_filename(image_file.filename)
video_filename = secure_filename(video_file.filename)

image_path = os.path.join(UPLOAD_FOLDER, image_filename)
video_path = os.path.join(UPLOAD_FOLDER, video_filename)

image_file.save(image_path)
video_file.save(video_path)

conn = sqlite3.connect(DATABASE)
c = conn.cursor()
c.execute("INSERT INTO portfolio (title, description, image, video) VALUES (?, ?, ?, ?)",
          (title, description, image_filename, video_filename))
conn.commit()
conn.close()
return redirect('/dashboard')

@app.route('/delete-blog/int:id') def delete_blog(id): if not session.get('admin'): return redirect('/login') conn = sqlite3.connect(DATABASE) c = conn.cursor() c.execute("DELETE FROM blog WHERE id = ?", (id,)) conn.commit() conn.close() return redirect('/dashboard')

@app.route('/delete-portfolio/int:id') def delete_portfolio(id): if not session.get('admin'): return redirect('/login') conn = sqlite3.connect(DATABASE) c = conn.cursor() c.execute("DELETE FROM portfolio WHERE id = ?", (id,)) conn.commit() conn.close() return redirect('/dashboard')

@app.route('/edit-blog/int:id', methods=['GET', 'POST']) def edit_blog(id): if not session.get('admin'): return redirect('/login')

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

@app.route('/edit-portfolio/int:id', methods=['GET', 'POST']) def edit_portfolio(id): if not session.get('admin'): return redirect('/login')

conn = sqlite3.connect(DATABASE)
c = conn.cursor()

if request.method == 'POST':
    title = request.form['title']
    description = request.form['description']

    # Optional file update
    image_filename = request.files['image'].filename
    video_filename = request.files['video'].filename

    if image_filename:
        image_path = os.path.join(UPLOAD_FOLDER, secure_filename(image_filename))
        request.files['image'].save(image_path)
        c.execute("UPDATE portfolio SET image = ? WHERE id = ?", (image_filename, id))

    if video_filename:
        video_path = os.path.join(UPLOAD_FOLDER, secure_filename(video_filename))
        request.files['video'].save(video_path)
        c.execute("UPDATE portfolio SET video = ? WHERE id = ?", (video_filename, id))

    c.execute("UPDATE portfolio SET title = ?, description = ? WHERE id = ?", (title, description, id))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

portfolio = c.execute("SELECT * FROM portfolio WHERE id = ?", (id,)).fetchone()
conn.close()
return render_template('edit_portfolio.html', portfolio=portfolio)

if name == 'main': app.run(debug=True)