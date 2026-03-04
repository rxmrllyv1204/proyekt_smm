
import sqlite3
conn = sqlite3.connect("users.db")
sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone()[0]
print(sql)
conn.close()
