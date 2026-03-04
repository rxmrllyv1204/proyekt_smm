import database
from sqlalchemy import inspect

def check_table():
    inspector = inspect(database.engine)
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    if "support_tickets" in tables:
        print("Table 'support_tickets' exists.")
    else:
        print("Table 'support_tickets' DOES NOT exist.")

if __name__ == "__main__":
    check_table()
