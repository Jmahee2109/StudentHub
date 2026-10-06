from database import get_db_connection


connection = get_db_connection()

cursor = connection.cursor()


# --------------------------------------------------
# CREATE COURSES TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL UNIQUE

)
""")


# --------------------------------------------------
# CREATE STUDENTS TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,

    email TEXT NOT NULL UNIQUE,

    phone TEXT,

    gender TEXT,

    course_id INTEGER NOT NULL,

    date_of_birth TEXT,

    enrollment_date TEXT DEFAULT CURRENT_DATE,

    status TEXT NOT NULL DEFAULT 'Active',

    FOREIGN KEY (course_id)
        REFERENCES courses(id)

)
""")


# --------------------------------------------------
# INSERT COURSES
# --------------------------------------------------

courses = [

    ("BCA",),

    ("BSc IT",),

    ("MCA",),

    ("BTech Computer Science",),

    ("BBA",),

    ("MCom",)

]


cursor.executemany(
    """
    INSERT OR IGNORE INTO courses (name)
    VALUES (?)
    """,
    courses
)


# --------------------------------------------------
# INSERT STUDENTS
# --------------------------------------------------

students = [

    (
        "Rahul Sharma",
        "rahul@example.com",
        "9876543210",
        "Male",
        1,
        "2002-04-12",
        "2025-06-15",
        "Active"
    ),

    (
        "Ayesha Khan",
        "ayesha@example.com",
        "9123456789",
        "Female",
        2,
        "2003-08-21",
        "2025-06-18",
        "Active"
    ),

    (
        "Arjun Mehta",
        "arjun@example.com",
        "9988776655",
        "Male",
        1,
        "2002-11-10",
        "2025-06-20",
        "Active"
    ),

    (
        "Emily Davis",
        "emily@example.com",
        "9876501234",
        "Female",
        4,
        "2001-05-14",
        "2025-06-22",
        "Inactive"
    ),

    (
        "Chris Wilson",
        "chris@example.com",
        "9765432109",
        "Male",
        3,
        "2002-01-25",
        "2025-06-25",
        "Active"
    ),

    (
        "Sara Patel",
        "sara@example.com",
        "9898989898",
        "Female",
        5,
        "2003-03-17",
        "2025-07-01",
        "Active"
    ),

    (
        "Kabir Shah",
        "kabir@example.com",
        "9000011111",
        "Male",
        2,
        "2002-09-09",
        "2025-07-03",
        "Inactive"
    ),

    (
        "Maya Thomas",
        "maya@example.com",
        "9888877777",
        "Female",
        6,
        "2001-12-04",
        "2025-07-05",
        "Active"
    )

]


cursor.executemany(
    """
    INSERT OR IGNORE INTO students
    (
        name,
        email,
        phone,
        gender,
        course_id,
        date_of_birth,
        enrollment_date,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    students
)


# --------------------------------------------------
# SAVE CHANGES
# --------------------------------------------------

connection.commit()

connection.close()


print("Database setup completed successfully.")
