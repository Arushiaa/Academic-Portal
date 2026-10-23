"""Run with:  python test_portal.py   (uses a temporary copy of the database)"""
import os, shutil, tempfile
import database
tmp = tempfile.mkdtemp()
database.DB_PATH = os.path.join(tmp, "test.db")
shutil.copy(os.path.join(database.BASE_DIR, "academic.db"), database.DB_PATH)

from app import app
from grading import build_transcript

def test_gpa():
    rows = [dict(course_id="A", course_name="a", credits=4, semester=1, grade="A"),
            dict(course_id="B", course_name="b", credits=4, semester=1, grade="B"),
            dict(course_id="C", course_name="c", credits=3, semester=1, grade="S"),
            dict(course_id="D", course_name="d", credits=4, semester=2, grade="F"),
            dict(course_id="D", course_name="d", credits=4, semester=3, grade="B+")]
    sems, cpi, earned = build_transcript(rows)
    assert round(sems[0]["spi"], 2) == 9.00           # S excluded: (40+32)/8
    assert round(sems[1]["spi"], 2) == 0.00
    assert round(sems[1]["cpi"], 2) == 6.00            # (40+32+0)/12
    assert round(cpi, 2) == round((40 + 32 + 36) / 12, 2)  # repeat of D uses latest attempt
    assert earned == 4 + 4 + 3 + 4

def login(c, u, p, role="student"):
    return c.post("/", data=dict(username=u, password=p, role=role), follow_redirects=True)

def test_student_flow():
    c = app.test_client()
    assert b"Invalid" in login(c, "arushia", "wrong").data
    r = login(c, "arushia", "1234")
    assert b"Student Summary" in r.data and b"CS101" in r.data
    # duplicate
    assert b"already registered" in c.post("/register", data={"course_id": "CS101"}, follow_redirects=True).data
    # credit limit: CS101(4)+ME201(3)=7, EE250(4) would be 11
    assert b"Credit limit exceeded" in c.post("/register", data={"course_id": "EE250"}, follow_redirects=True).data
    # completed course
    assert b"already completed" in c.post("/register", data={"course_id": "MA101"}, follow_redirects=True).data
    # drop then register
    c.post("/drop", data={"course_id": "ME201"}, follow_redirects=True)
    assert b"Registered for EE250" in c.post("/register", data={"course_id": "EE250"}, follow_redirects=True).data
    assert b"Grade Sheet" in c.get("/transcript").data
    assert c.get("/instructor").status_code == 302      # role isolation

def test_instructor_flow():
    c = app.test_client()
    login(c, "prof.rao", "teach123", "instructor")
    assert b"CS101" in c.get("/instructor").data
    assert b"Arushia" in c.get("/instructor/course/CS101").data
    assert b"do not teach" in c.get("/instructor/course/MA101", follow_redirects=True).data
    r = c.post("/instructor/grade", data=dict(course_id="CS101", student_id=1, grade="A"), follow_redirects=True)
    assert b"Grade saved" in r.data
    s = app.test_client(); login(s, "arushia", "1234")
    assert b"CS101" in s.get("/transcript").data
    # cannot grade other instructors' courses
    r = c.post("/instructor/grade", data=dict(course_id="MA101", student_id=1, grade="A"), follow_redirects=True)
    assert b"Invalid course" in r.data

if __name__ == "__main__":
    test_gpa(); test_student_flow(); test_instructor_flow()
    print("All tests passed.")
