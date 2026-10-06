from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session
)

from functools import wraps
import os
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection


app = Flask(__name__)
app.secret_key = os.environ.get("STUDENTHUB_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("Set the STUDENTHUB_SECRET_KEY environment variable.")


# ==================================================
# LOGIN REQUIRED DECORATOR
# ==================================================

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please log in to continue.",
                "error"
            )

            return redirect(
                url_for(
                    "login",
                    next=request.path
                )
            )

        return view(*args, **kwargs)

    return wrapped_view


# ==================================================
# CREATE DEFAULT ADMIN USER
# ==================================================

def create_default_user():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Create users table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check whether default admin already exists
    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, ("admin@studenthub.com",))

    existing_user = cursor.fetchone()

    # Create default admin if not found
    if existing_user is None:
        admin_password = os.environ.get("STUDENTHUB_ADMIN_PASSWORD")
        if not admin_password:
            connection.close()
            raise RuntimeError(
                "Set STUDENTHUB_ADMIN_PASSWORD to create the initial admin account."
            )

        password_hash = generate_password_hash(admin_password)

        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?)
        """, (
            "Administrator",
            "admin@studenthub.com",
            password_hash,
            "admin"
        ))

        connection.commit()

    connection.close()


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # If already logged in, go directly to dashboard
    if "user_id" in session:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # Basic validation
        if not email or not password:

            flash(
                "Email and password are required.",
                "error"
            )

            return render_template(
                "login.html"
            )

        connection = get_db_connection()

        user = connection.execute("""
            SELECT
                id,
                name,
                email,
                password_hash,
                role
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        connection.close()

        # Check credentials
        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            # Store login information in session
            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["user_role"] = user["role"]

            flash(
                "Login successful. Welcome back!",
                "success"
            )

            # Return user to requested page if available
            next_page = request.args.get("next")

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/")
@login_required
def dashboard():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Total students
    cursor.execute("""
        SELECT COUNT(*) AS total_students
        FROM students
    """)

    total_students = cursor.fetchone()["total_students"]

    # Active students
    cursor.execute("""
        SELECT COUNT(*) AS active_students
        FROM students
        WHERE status = 'Active'
    """)

    active_students = cursor.fetchone()["active_students"]

    # Inactive students
    cursor.execute("""
        SELECT COUNT(*) AS inactive_students
        FROM students
        WHERE status = 'Inactive'
    """)

    inactive_students = cursor.fetchone()["inactive_students"]

    # Total courses
    cursor.execute("""
        SELECT COUNT(*) AS total_courses
        FROM courses
    """)

    total_courses = cursor.fetchone()["total_courses"]

    # Recent students
    cursor.execute("""
        SELECT
            students.id,
            students.name,
            courses.name AS course,
            students.status
        FROM students
        INNER JOIN courses
            ON students.course_id = courses.id
        ORDER BY students.id DESC
        LIMIT 5
    """)

    recent_students = cursor.fetchall()

    # Course-wise statistics
    cursor.execute("""
        SELECT
            courses.name AS course,
            COUNT(students.id) AS total
        FROM courses
        LEFT JOIN students
            ON courses.id = students.course_id
        GROUP BY courses.id, courses.name
        ORDER BY total DESC
    """)

    course_stats = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students,
        total_courses=total_courses,
        recent_students=recent_students,
        course_stats=course_stats
    )


# ==================================================
# STUDENT LIST
# ==================================================

@app.route("/students")
@login_required
def students():

    search = request.args.get(
        "search",
        ""
    ).strip()

    course_id = request.args.get(
        "course_id",
        ""
    )

    status = request.args.get(
        "status",
        ""
    )

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            students.id,
            students.name,
            students.email,
            students.phone,
            students.gender,
            students.status,
            courses.name AS course
        FROM students
        INNER JOIN courses
            ON students.course_id = courses.id
        WHERE 1 = 1
    """

    parameters = []

    # Search by name, email or phone
    if search:

        query += """
            AND (
                students.name LIKE ?
                OR students.email LIKE ?
                OR students.phone LIKE ?
            )
        """

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value,
            search_value
        ])

    # Course filter
    if course_id:

        query += """
            AND students.course_id = ?
        """

        parameters.append(course_id)

    # Status filter
    if status:

        query += """
            AND students.status = ?
        """

        parameters.append(status)

    query += """
        ORDER BY students.id DESC
    """

    cursor.execute(
        query,
        parameters
    )

    students_list = cursor.fetchall()

    # Get courses for dropdown
    cursor.execute("""
        SELECT id, name
        FROM courses
        ORDER BY name
    """)

    courses = cursor.fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=students_list,
        courses=courses,
        search=search,
        selected_course=course_id,
        selected_status=status
    )


# ==================================================
# ADD STUDENT
# ==================================================

@app.route("/student/add", methods=["GET", "POST"])
@login_required
def add_student():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get courses for the form
    cursor.execute("""
        SELECT id, name
        FROM courses
        ORDER BY name
    """)

    courses = cursor.fetchall()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        gender = request.form.get(
            "gender",
            ""
        )

        course_id = request.form.get(
            "course_id",
            ""
        )

        date_of_birth = request.form.get(
            "date_of_birth",
            ""
        )

        status = request.form.get(
            "status",
            "Active"
        )

        # Validation
        if not name or not email or not course_id:

            connection.close()

            flash(
                "Name, email and course are required.",
                "error"
            )

            return redirect(
                url_for("add_student")
            )

        try:

            cursor.execute("""
                INSERT INTO students
                (
                    name,
                    email,
                    phone,
                    gender,
                    course_id,
                    date_of_birth,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                phone,
                gender,
                course_id,
                date_of_birth,
                status
            ))

            connection.commit()
            connection.close()

            flash(
                "Student added successfully.",
                "success"
            )

            return redirect(
                url_for("students")
            )

        except Exception:

            connection.close()

            flash(
                "A student with this email may already exist.",
                "error"
            )

            return redirect(
                url_for("add_student")
            )

    connection.close()

    return render_template(
        "student_form.html",
        student=None,
        courses=courses,
        form_title="Add Student"
    )


# ==================================================
# STUDENT DETAILS
# ==================================================

@app.route("/student/<int:student_id>")
@login_required
def student_detail(student_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.id,
            students.name,
            students.email,
            students.phone,
            students.gender,
            students.date_of_birth,
            students.enrollment_date,
            students.status,
            courses.name AS course
        FROM students
        INNER JOIN courses
            ON students.course_id = courses.id
        WHERE students.id = ?
    """, (student_id,))

    student = cursor.fetchone()

    connection.close()

    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for("students")
        )

    return render_template(
        "student_detail.html",
        student=student
    )


# ==================================================
# EDIT STUDENT
# ==================================================

@app.route(
    "/student/edit/<int:student_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_student(student_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get student
    cursor.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    )

    student = cursor.fetchone()

    # Get courses
    cursor.execute(
        "SELECT id, name FROM courses ORDER BY name"
    )

    courses = cursor.fetchall()

    if student is None:

        connection.close()

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for("students")
        )

    # Update student
    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        gender = request.form.get(
            "gender",
            ""
        )

        course_id = request.form.get(
            "course_id",
            ""
        )

        date_of_birth = request.form.get(
            "date_of_birth",
            ""
        )

        status = request.form.get(
            "status",
            "Active"
        )

        if not name or not email or not course_id:

            connection.close()

            flash(
                "Name, email and course are required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_student",
                    student_id=student_id
                )
            )

        try:

            cursor.execute("""
                UPDATE students
                SET
                    name = ?,
                    email = ?,
                    phone = ?,
                    gender = ?,
                    course_id = ?,
                    date_of_birth = ?,
                    status = ?
                WHERE id = ?
            """, (
                name,
                email,
                phone,
                gender,
                course_id,
                date_of_birth,
                status,
                student_id
            ))

            connection.commit()
            connection.close()

            flash(
                "Student updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "student_detail",
                    student_id=student_id
                )
            )

        except Exception:

            connection.close()

            flash(
                "A student with this email may already exist.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_student",
                    student_id=student_id
                )
            )

    connection.close()

    return render_template(
        "student_form.html",
        student=student,
        courses=courses,
        form_title="Edit Student"
    )


# ==================================================
# DELETE STUDENT
# ==================================================

@app.route(
    "/student/delete/<int:student_id>",
    methods=["POST"]
)
@login_required
def delete_student(student_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    connection.commit()

    deleted = cursor.rowcount

    connection.close()

    if deleted:

        flash(
            "Student deleted successfully.",
            "success"
        )

    else:

        flash(
            "Student not found.",
            "error"
        )

    return redirect(
        url_for("students")
    )


# ==================================================
# COURSES
# ==================================================

@app.route(
    "/courses",
    methods=["GET", "POST"]
)
@login_required
def courses():

    if request.method == "POST":

        action = request.form.get(
            "action"
        )

        # ------------------------------------------
        # ADD COURSE
        # ------------------------------------------

        if action == "add":

            course_name = request.form.get(
                "course_name",
                ""
            ).strip()

            if not course_name:

                flash(
                    "Course name is required.",
                    "error"
                )

                return redirect(
                    url_for("courses")
                )

            connection = get_db_connection()

            try:

                connection.execute(
                    """
                    INSERT INTO courses (name)
                    VALUES (?)
                    """,
                    (course_name,)
                )

                connection.commit()

                flash(
                    "Course added successfully.",
                    "success"
                )

            except Exception:

                flash(
                    "A course with this name may already exist.",
                    "error"
                )

            finally:

                connection.close()

            return redirect(
                url_for("courses")
            )

        # ------------------------------------------
        # EDIT COURSE
        # ------------------------------------------

        elif action == "edit":

            course_id = request.form.get(
                "course_id"
            )

            course_name = request.form.get(
                "course_name",
                ""
            ).strip()

            if not course_name:

                flash(
                    "Course name is required.",
                    "error"
                )

                return redirect(
                    url_for("courses")
                )

            connection = get_db_connection()

            try:

                connection.execute(
                    """
                    UPDATE courses
                    SET name = ?
                    WHERE id = ?
                    """,
                    (
                        course_name,
                        course_id
                    )
                )

                connection.commit()

                flash(
                    "Course updated successfully.",
                    "success"
                )

            except Exception:

                flash(
                    "A course with this name may already exist.",
                    "error"
                )

            finally:

                connection.close()

            return redirect(
                url_for("courses")
            )

    # ------------------------------------------
    # GET COURSES
    # ------------------------------------------

    connection = get_db_connection()

    courses = connection.execute(
        """
        SELECT
            courses.id,
            courses.name,
            COUNT(students.id) AS student_count
        FROM courses
        LEFT JOIN students
            ON students.course_id = courses.id
        GROUP BY
            courses.id,
            courses.name
        ORDER BY courses.name
        """
    ).fetchall()

    total_courses = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM courses
        """
    ).fetchone()["count"]

    used_courses = connection.execute(
        """
        SELECT COUNT(DISTINCT course_id) AS count
        FROM students
        """
    ).fetchone()["count"]

    total_students = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM students
        """
    ).fetchone()["count"]

    connection.close()

    return render_template(
        "courses.html",
        courses=courses,
        total_courses=total_courses,
        used_courses=used_courses,
        total_students=total_students
    )


# ==================================================
# DELETE COURSE
# ==================================================

@app.route(
    "/course/delete/<int:course_id>",
    methods=["POST"]
)
@login_required
def delete_course(course_id):

    connection = get_db_connection()

    student_count = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM students
        WHERE course_id = ?
        """,
        (course_id,)
    ).fetchone()["count"]

    # Prevent deleting a course that has students
    if student_count > 0:

        connection.close()

        flash(
            "This course cannot be deleted because students are enrolled in it.",
            "error"
        )

        return redirect(
            url_for("courses")
        )

    connection.execute(
        """
        DELETE FROM courses
        WHERE id = ?
        """,
        (course_id,)
    )

    connection.commit()

    deleted = connection.total_changes

    connection.close()

    if deleted:

        flash(
            "Course deleted successfully.",
            "success"
        )

    else:

        flash(
            "Course not found.",
            "error"
        )

    return redirect(
        url_for("courses")
    )


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    # Create the users table and the initial admin account if needed
    create_default_user()

    app.run(
        debug=True
    )