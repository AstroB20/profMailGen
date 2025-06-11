import sqlite3

def print_all_tables(db_path='instance/profmailgen_users.db'):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        print(f"Found {len(tables)} tables:\n")

        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            print(f"Table: {table_name}")

            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print("Columns:", col_names)

            # Get rows (limit output to avoid too much data)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
            rows = cursor.fetchall()

            if rows:
                for row in rows:
                    print(row)
            else:
                print("(No data)")

            print("\n" + "-"*40 + "\n")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

    finally:
        if conn:
            conn.close()


# Usage
if __name__ == "__main__":
    print_all_tables('profmailgen_users.db')  
