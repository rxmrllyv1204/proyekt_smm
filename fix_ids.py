
import sqlite3

def set_id_start():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        # Check if users table exists and get max id
        cursor.execute("SELECT MAX(id) FROM users")
        max_id = cursor.fetchone()[0] or 0
        
        if max_id < 9999:
            print(f"Current max ID is {max_id}. Setting starting point to 10000.")
            # We can't easily use sqlite_sequence without AUTOINCREMENT keyword
            # But we can insert a dummy user and delete it to 'push' the counter
            # However, simpler if we just update existing users to be 10000+
            cursor.execute("SELECT id FROM users WHERE id < 10000")
            ids = cursor.fetchall()
            for (old_id,) in ids:
                new_id = old_id + 10000
                print(f"Migrating {old_id} to {new_id}")
                cursor.execute("UPDATE orders SET user_id = ? WHERE user_id = ?", (new_id, old_id))
                cursor.execute("UPDATE payment_requests SET user_id = ? WHERE user_id = ?", (new_id, old_id))
                cursor.execute("UPDATE users SET id = ? WHERE id = ?", (new_id, old_id))
        else:
            print(f"Max ID is already {max_id}, no migration needed.")
        
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    set_id_start()
