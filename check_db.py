import sqlite3

conn = sqlite3.connect("academic.db")
cur = conn.cursor()

print("\nSTUDENTS")
cur.execute("SELECT * FROM students")

for row in cur.fetchall():
    print(row)


print("\nCOURSES")
cur.execute("SELECT * FROM courses")

for row in cur.fetchall():
    print(row)


print("\nREGISTRATIONS")
cur.execute("SELECT * FROM registrations")

for row in cur.fetchall():
    print(row)

print("\nGRADES")
cur.execute("SELECT * FROM grades")

for row in cur.fetchall():
    print(row)

conn.close()