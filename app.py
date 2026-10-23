import os
from functools import wraps

from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from database import get_db
from grading import VALID_GRADES, build_transcript

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "academicportal-dev-key")

MAX_CREDITS = 8


# ---------------------------------------------------------------- helpers
def login_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapper
    return deco


def student_transcript(conn, student_id):
    rows = [dict(r) for r in conn.execute(
        """SELECT c.course_id, c.course_name, c.credits, g.semester, g.grade
           FROM grades g JOIN courses c ON g.course_id = c.course_id
           WHERE g.student_id = ?""", (student_id,))]
    return build_transcript(rows)


# ---------------------------------------------------------------- auth
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role", "student")
        table = "instructors" if role == "instructor" else "students"
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(f"SELECT id, name, password FROM {table} WHERE username=?",
                            (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["role"] = role
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("instructor_dashboard" if role == "instructor" else "dashboard"))
        return render_template("login.html", error="Invalid username or password.")

    if session.get("role") == "student":
        return redirect(url_for("dashboard"))
    if session.get("role") == "instructor":
        return redirect(url_for("instructor_dashboard"))
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- student
@app.route("/dashboard")
@login_required("student")
def dashboard():
    sid = session["user_id"]
    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()

    courses = conn.execute(
        """SELECT c.course_id, c.course_name, c.credits, c.capacity,
                  COALESCE(i.name, 'TBA') AS instructor,
                  (SELECT COUNT(*) FROM registrations r WHERE r.course_id = c.course_id) AS enrolled,
                  EXISTS(SELECT 1 FROM registrations r
                         WHERE r.course_id = c.course_id AND r.student_id = :sid) AS registered,
                  EXISTS(SELECT 1 FROM grades g
                         WHERE g.course_id = c.course_id AND g.student_id = :sid
                           AND g.grade NOT IN ('F','X')) AS completed
           FROM courses c LEFT JOIN instructors i ON c.instructor_id = i.id
           ORDER BY c.course_id""", {"sid": sid}).fetchall()

    registered = conn.execute(
        """SELECT c.course_id, c.course_name, c.credits,
                  COALESCE(i.name, 'TBA') AS instructor
           FROM registrations r
           JOIN courses c ON r.course_id = c.course_id
           LEFT JOIN instructors i ON c.instructor_id = i.id
           WHERE r.student_id = ? ORDER BY c.course_id""", (sid,)).fetchall()
    current_credits = sum(r["credits"] for r in registered)

    semesters, cpi, earned = student_transcript(conn, sid)
    conn.close()

    return render_template("dashboard.html", student=student, courses=courses,
                           registered=registered, current_credits=current_credits,
                           max_credits=MAX_CREDITS, semesters=semesters, cpi=cpi,
                           earned=earned)


@app.route("/register", methods=["POST"])
@login_required("student")
def register():
    sid = session["user_id"]
    course_id = request.form.get("course_id", "")
    conn = get_db()

    course = conn.execute("SELECT * FROM courses WHERE course_id=?", (course_id,)).fetchone()
    if not course:
        flash("That course does not exist.", "error")
    elif conn.execute("SELECT 1 FROM registrations WHERE student_id=? AND course_id=?",
                      (sid, course_id)).fetchone():
        flash("You are already registered for this course.", "error")
    elif conn.execute("SELECT 1 FROM grades WHERE student_id=? AND course_id=? AND grade NOT IN ('F','X')",
                      (sid, course_id)).fetchone():
        flash("You have already completed this course.", "error")
    else:
        current = conn.execute(
            """SELECT COALESCE(SUM(c.credits),0) FROM registrations r
               JOIN courses c ON r.course_id=c.course_id WHERE r.student_id=?""", (sid,)).fetchone()[0]
        enrolled = conn.execute("SELECT COUNT(*) FROM registrations WHERE course_id=?",
                                (course_id,)).fetchone()[0]
        if current + course["credits"] > MAX_CREDITS:
            flash(f"Credit limit exceeded. Maximum allowed credits: {MAX_CREDITS}.", "error")
        elif enrolled >= course["capacity"]:
            flash("This course is full.", "error")
        else:
            conn.execute("INSERT INTO registrations(student_id, course_id) VALUES (?,?)", (sid, course_id))
            conn.commit()
            flash(f"Registered for {course_id}.", "success")
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/drop", methods=["POST"])
@login_required("student")
def drop():
    conn = get_db()
    conn.execute("DELETE FROM registrations WHERE student_id=? AND course_id=?",
                 (session["user_id"], request.form.get("course_id", "")))
    conn.commit()
    conn.close()
    flash("Course dropped.", "success")
    return redirect(url_for("dashboard"))


@app.route("/transcript")
@login_required("student")
def transcript():
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (session["user_id"],)).fetchone()
    semesters, cpi, earned = student_transcript(conn, session["user_id"])
    conn.close()
    return render_template("transcript.html", student=student, semesters=semesters,
                           cpi=cpi, earned=earned)


# ---------------------------------------------------------------- instructor
@app.route("/instructor")
@login_required("instructor")
def instructor_dashboard():
    conn = get_db()
    courses = conn.execute(
        """SELECT c.course_id, c.course_name, c.credits, c.capacity,
                  (SELECT COUNT(*) FROM registrations r WHERE r.course_id=c.course_id) AS enrolled
           FROM courses c WHERE c.instructor_id=? ORDER BY c.course_id""",
        (session["user_id"],)).fetchall()
    conn.close()
    return render_template("instructor.html", courses=courses)


@app.route("/instructor/course/<course_id>")
@login_required("instructor")
def course_students(course_id):
    conn = get_db()
    course = conn.execute("SELECT * FROM courses WHERE course_id=? AND instructor_id=?",
                          (course_id, session["user_id"])).fetchone()
    if not course:
        conn.close()
        flash("You do not teach that course.", "error")
        return redirect(url_for("instructor_dashboard"))

    enrolled = conn.execute(
        """SELECT s.id, s.name, s.roll_number, s.semester FROM registrations r
           JOIN students s ON r.student_id=s.id WHERE r.course_id=? ORDER BY s.roll_number""",
        (course_id,)).fetchall()
    graded = conn.execute(
        """SELECT s.id, s.name, s.roll_number, g.semester, g.grade FROM grades g
           JOIN students s ON g.student_id=s.id WHERE g.course_id=?
           ORDER BY g.semester DESC, s.roll_number""", (course_id,)).fetchall()
    conn.close()
    return render_template("course_students.html", course=course, enrolled=enrolled,
                           graded=graded, grades=VALID_GRADES)


@app.route("/instructor/grade", methods=["POST"])
@login_required("instructor")
def assign_grade():
    course_id = request.form.get("course_id", "")
    student_id = request.form.get("student_id", type=int)
    grade = request.form.get("grade", "")
    semester = request.form.get("semester", type=int)

    conn = get_db()
    owns = conn.execute("SELECT 1 FROM courses WHERE course_id=? AND instructor_id=?",
                        (course_id, session["user_id"])).fetchone()
    student = conn.execute("SELECT semester FROM students WHERE id=?", (student_id,)).fetchone()

    if not owns or not student:
        flash("Invalid course or student.", "error")
    elif grade not in VALID_GRADES:
        flash("Invalid grade.", "error")
    else:
        # Grading an enrolled student finalises the course: it moves from
        # "registered" to the transcript, in the student's current semester.
        is_enrolled = conn.execute("SELECT 1 FROM registrations WHERE student_id=? AND course_id=?",
                                   (student_id, course_id)).fetchone()
        if is_enrolled:
            semester = student["semester"]
            conn.execute("DELETE FROM registrations WHERE student_id=? AND course_id=?",
                         (student_id, course_id))
        elif semester is None:
            flash("Student is not enrolled in this course.", "error")
            conn.close()
            return redirect(url_for("course_students", course_id=course_id))
        conn.execute(
            """INSERT INTO grades(student_id, course_id, semester, grade) VALUES (?,?,?,?)
               ON CONFLICT(student_id, course_id, semester) DO UPDATE SET grade=excluded.grade""",
            (student_id, course_id, semester, grade))
        conn.commit()
        flash("Grade saved.", "success")
    conn.close()
    return redirect(url_for("course_students", course_id=course_id))


if __name__ == "__main__":
    app.run(debug=True)
