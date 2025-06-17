import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create blog table
c.execute('''
    CREATE TABLE IF NOT EXISTS blog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    )
''')

# Create portfolio table (optional, if your app uses it)
c.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        image TEXT,
        video TEXT
    )
''')

# Create admin table (optional, if your app uses it)
c.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
''')

conn.commit()
conn.close()

print("Tables created successfully.")