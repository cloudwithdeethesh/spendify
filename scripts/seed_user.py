import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash

from database.db import get_db, init_db

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Rahul", "Kabir", "Ishaan",
    "Karthik", "Siddharth", "Nikhil", "Aniket", "Ananya", "Priya", "Sneha",
    "Meera", "Kavya", "Riya", "Isha", "Divya", "Neha", "Pooja", "Lakshmi",
    "Deepika", "Aishwarya", "Rithika", "Sanjana", "Aryan", "Manav", "Harsh",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Menon", "Reddy", "Rao",
    "Patel", "Shah", "Kulkarni", "Deshpande", "Chatterjee", "Banerjee",
    "Mukherjee", "Bose", "Singh", "Kaur", "Bhat", "Suvarna", "Hegde",
    "Pillai", "Krishnan", "Naidu", "Chowdhury", "Jain", "Agarwal", "Mishra",
]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = random.randint(10, 999)
    name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}{suffix}@gmail.com"
    return name, email


def email_exists(conn, email):
    row = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
    return row is not None


def main():
    init_db()
    conn = get_db()
    try:
        while True:
            name, email = generate_user()
            if not email_exists(conn, email):
                break

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().isoformat(sep=" ", timespec="seconds")

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, email, password_hash, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid

        print("Seeded user:")
        print(f"  id:    {user_id}")
        print(f"  name:  {name}")
        print(f"  email: {email}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
