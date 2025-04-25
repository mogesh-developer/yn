from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mysql.connector
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Connect to MySQL
db = mysql.connector.connect(
    host=os.environ.get('DB_HOST', 'localhost'),
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_NAME', 'flask')
)

# -------------------- ROUTES --------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def home():
    return redirect(url_for('login_student'))

# ---------- Course Pages ----------
@app.route('/course/<page>')
def course_page(page):
    valid_pages = [
        'catering-hotel-management', 'nursing-health-care', 'dhm', 'dgda', 'dxrt',
        'dmlta', 'dna', 'dhmct', 'dpsm', 'dct', 'difp'
    ]
    if page not in valid_pages:
        return "Page not found", 404
    return render_template(f'{page.replace("-", "_")}.html')

# ---------- Student Registration ----------
@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            msg = 'Student username already exists.'
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            db.commit()
            msg = 'Student registered successfully!'
        cursor.close()
    return render_template('register_student.html', msg=msg)

# ---------- Student Login ----------
@app.route('/login/student', methods=['GET', 'POST'])
def login_student():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        student = cursor.fetchone()
        cursor.close()
        if student and check_password_hash(student['password'], password):
            session['username'] = student['username']
            return redirect(url_for('dashboard_student'))
        else:
            msg = 'Invalid credentials.'
    return render_template('login_student.html', msg=msg)

# ---------- Student Dashboard ----------
@app.route('/dashboard/student')
def dashboard_student():
    if 'username' not in session:
        return redirect(url_for('login_student'))

    username = session['username']
    cursor1 = db.cursor(dictionary=True)
    cursor1.execute("SELECT * FROM courses")
    courses = cursor1.fetchall()
    cursor1.close()

    cursor2 = db.cursor(dictionary=True)
    cursor2.execute("SELECT course_id FROM enrollments WHERE student_username = %s", (username,))
    enrolled = cursor2.fetchall()
    cursor2.close()

    enrolled_course_ids = {e['course_id'] for e in enrolled}
    return render_template('student_dashboard.html', username=username, courses=courses, enrolled_course_ids=enrolled_course_ids)

# ---------- Apply for a Course ----------
@app.route('/apply/<int:course_id>', methods=['POST'])
def apply_course(course_id):
    if 'username' not in session:
        return redirect(url_for('login_student'))

    username = session['username']
    cursor = db.cursor()
    cursor.execute("SELECT * FROM enrollments WHERE student_username = %s AND course_id = %s", (username, course_id))
    existing = cursor.fetchone()

    if not existing:
        cursor.execute("INSERT INTO enrollments (student_username, course_id) VALUES (%s, %s)", (username, course_id))
        db.commit()

    cursor.close()
    return "<script>alert('Enrolled successfully!');window.location.href='/dashboard/student';</script>"

# ---------- Admin Login ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        if admin and check_password_hash(admin['password'], password):
            session['admin_username'] = admin['username']
            return redirect(url_for('dashboard_admin'))
        else:
            msg = 'Invalid credentials. Please try again.'
    return render_template('admin_login.html', msg=msg)

# ---------- Admin Registration ----------
@app.route('/register/admin', methods=['GET', 'POST'])
def register_admin():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        if cursor.fetchone():
            msg = 'Admin username already exists.'
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO admins (username, password) VALUES (%s, %s)", (username, hashed_password))
            db.commit()
            msg = 'Admin registered successfully!'
        cursor.close()
    return render_template('admin_register.html', msg=msg)

# ---------- Admin Dashboard ----------
@app.route('/dashboard/admin')
def dashboard_admin():
    if 'admin_username' not in session:
        return redirect(url_for('admin_login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            e.student_username, 
            c.title AS course_title, 
            c.instructor, 
            e.enrollment_date 
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        ORDER BY e.enrollment_date DESC
    """)
    enrollments = cursor.fetchall()
    cursor.close()

    return render_template('admin_dashboard.html', enrollments=enrollments)

# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_student'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ---------- For Gunicorn ----------
# Don't use `app.run()` — that’s for local dev only
# Gunicorn will run the app using: gunicorn app:app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))