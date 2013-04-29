import sqlite3


conn = sqlite3.connect('development.sqlite3')
c = conn.cursor()

c.execute('''SELECT "projects".* FROM "projects" ORDER BY rating DESC, created_at DESC LIMIT 3''')
results = c.fetchone()

print results

conn.close()
