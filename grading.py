"""Grade rules and SPI / CPI calculation (kept separate so it is easy to test).

Edit the tables below if your institute's rules differ.
"""

# Grade -> grade points (counted in SPI/CPI)
GRADE_POINTS = {
    "A*": 10, "A": 10, "B+": 9, "B": 8, "C+": 7,
    "C": 6, "D": 4, "E": 2, "F": 0,
}
# Pass/non-numeric grades: credits are earned but NOT part of SPI/CPI
NON_GPA_GRADES = {"S"}
# Grades that mean the course was failed / not completed
FAIL_GRADES = {"F", "X"}

VALID_GRADES = list(GRADE_POINTS) + sorted(NON_GPA_GRADES) + ["X"]


def is_passed(grade):
    return grade not in FAIL_GRADES


def _gpa(records):
    """Credit-weighted average over records that carry grade points."""
    credits = sum(r["credits"] for r in records if r["grade"] in GRADE_POINTS)
    points = sum(r["credits"] * GRADE_POINTS[r["grade"]]
                 for r in records if r["grade"] in GRADE_POINTS)
    return (points / credits) if credits else None


def build_transcript(rows):
    """rows: dicts with course_id, course_name, credits, semester, grade.

    Returns (semesters, cpi, earned_credits).
    Each semester: {semester, courses, spi, credits_attempted,
                    credits_earned, cpi}   (cpi = cumulative up to that sem)
    Repeated courses: SPI uses every row of that semester; CPI uses only the
    latest attempt of each course.
    """
    rows = sorted(rows, key=lambda r: (r["semester"], r["course_id"]))
    by_sem = {}
    for r in rows:
        by_sem.setdefault(r["semester"], []).append(r)

    semesters = []
    for sem in sorted(by_sem):
        upto = [r for r in rows if r["semester"] <= sem]
        latest = {}
        for r in upto:                      # rows sorted -> later sem overwrites
            latest[r["course_id"]] = r
        courses = by_sem[sem]
        semesters.append({
            "semester": sem,
            "courses": courses,
            "spi": _gpa(courses),
            "credits_attempted": sum(c["credits"] for c in courses),
            "credits_earned": sum(c["credits"] for c in courses if is_passed(c["grade"])),
            "cpi": _gpa(list(latest.values())),
        })

    final = {}
    for r in rows:
        final[r["course_id"]] = r
    cpi = _gpa(list(final.values()))
    earned = sum(r["credits"] for r in final.values() if is_passed(r["grade"]))
    return semesters, cpi, earned
