# Academic Portal

A web-based academic management system built with Flask and SQLite, inspired by IIT Kanpur's Pingala portal. It supports student course registration, credit-limit validation, academic records, and instructor-side grade management.

## Features

### Student Portal
- Secure login and logout with session management
- Student dashboard with profile and academic information
- View available courses and their credit requirements
- Register for courses and drop registered courses
- Credit-limit validation and duplicate-registration prevention
- View completed courses and academic records

### Academic Records
- Semester-wise grade sheet
- SPI (Semester Performance Index) calculation
- CPI (Cumulative Performance Index) calculation
- Grade management with support for repeated course attempts

### Instructor Portal
- Instructor authentication and dashboard
- View assigned courses and enrolled students
- Assign and update student grades

### Database
- SQLite database
- Relational tables for students, courses, registrations, and grades
- Primary-key and foreign-key constraints
- SQL queries using joins and aggregate functions

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, Jinja2
- **Testing:** pytest

## Project Structure

```text
AcademicPortal/
├── app.py
├── database.py
├── init_db.py
├── grading.py
├── check_db.py
├── test_portal.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── transcript.html
│   ├── instructor.html
│   ├── course_students.html
│   └── _grade_table.html
└── static/
    └── style.css
```

## Getting Started

### Prerequisites
- Python 3.11 or a compatible Python version
- Git

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd AcademicPortal
```

Replace `<YOUR_REPOSITORY_URL>` with your GitHub repository URL.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Initialize the database

```bash
python init_db.py
```

This creates the local SQLite database and initializes the tables and sample data defined by the project.

### 5. Start the application

```bash
python app.py
```

Open the local URL printed in the terminal, usually `http://127.0.0.1:5000`.

## Running Tests

```bash
python -m pytest
```

## Security Notes

- The local SQLite database is excluded from version control because it may contain student records and password hashes.
- Use password hashing and secure session configuration.
- Change any development credentials before deploying the application.
- Do not commit secrets, private data, or production credentials.

## Current Status

This project is being developed iteratively. Core student registration and academic-record workflows are implemented, with testing and interface improvements ongoing.

## Future Improvements

- Further refine the interface to resemble a modern academic portal
- Improve grade-rule validation and transcript handling
- Add course-management controls and registration windows
- Strengthen authentication and deployment configuration
- Expand automated tests for student and instructor workflows

---

**Built as a learning project** to explore Flask, SQL, relational database design, authentication, and academic workflow management.
