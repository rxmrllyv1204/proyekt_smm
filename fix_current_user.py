
import sqlite3

def fix_and_set_start():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        # 1. Update existing user 1 to 10001
        cursor.execute("SELECT id FROM users WHERE id < 10000")
        users = cursor.fetchall()
        for (uid,) in users:
            new_id = uid + 10000
            print(f"Migrating user {uid} to {new_id}")
            # Update dependencies
            cursor.execute("UPDATE orders SET user_id = ? WHERE user_id = ?", (new_id, uid))
            cursor.execute("UPDATE payment_requests SET user_id = ? WHERE user_id = ?", (new_id, uid))
            cursor.execute("UPDATE users SET id = ? WHERE id = ?", (new_id, uid))
        
        # 2. Check current max ID
        cursor.execute("SELECT MAX(id) FROM users")
        max_id = cursor.fetchone()[0] or 0
        print(f"New Max ID: {max_id}")
        
        # 3. If no users exist, or we want to be sure, we need at least one user at 10000+
        # SQLite will follow the max(id) for the next one.
        
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_and_set_start()
