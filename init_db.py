import sqlite3

def init_db():
    try:
        conn = sqlite3.connect('health.db')
        c = conn.cursor()

        # Enable foreign key constraints
        c.execute("PRAGMA foreign_keys = ON")

        # Create Users table with join_date
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            weight_goal REAL DEFAULT 0.0,
            join_date TEXT DEFAULT (datetime('now'))
        )''')

        # Create Health Data table
        c.execute('''CREATE TABLE IF NOT EXISTS health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weight REAL,
            water INT,
            steps INT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        # Create Exercise Logs table
        c.execute('''CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            activity_type TEXT,
            duration REAL,
            calories_burned REAL,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        # Create Meal Logs table
        c.execute('''CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            meal_type TEXT,
            calories REAL,
            protein REAL,
            fat REAL,
            carbs REAL,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        # Create User Goals table
        c.execute('''CREATE TABLE IF NOT EXISTS user_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_type TEXT,
            target_value REAL,
            current_value REAL,
            date_set TEXT,
            target_date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )''')

        conn.commit()
        print("✅ Database initialized successfully!")

    except sqlite3.Error as e:
        print("❌ Database error:", e)

    except Exception as e:
        print("❌ Other error:", e)

    finally:
        if conn:
            conn.close()

# Call the function
init_db()
