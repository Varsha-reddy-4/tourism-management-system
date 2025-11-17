from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from dotenv import load_dotenv
import os
load_dotenv() 
password = os.getenv("DB_PASSWORD")  

app = Flask(__name__)
app.secret_key = 'Varsha@2005'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='varsha@2005',
        database='tourweb'
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add-package', methods=['GET', 'POST'])
def add_package():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_file = request.files['image']
        filename = None
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO packages (name, description, price, image) VALUES (%s, %s, %s, %s)",
                    (name, description, price, filename))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/view-packages')
    return render_template('add_package.html')

@app.route('/view-packages', methods=['GET', 'POST'])
def view_packages():
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT * FROM packages WHERE 1=1"
    params = []

    if request.method == 'POST':
        name = request.form.get('name')
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')

        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")
        if min_price:
            query += " AND price >= %s"
            params.append(min_price)
        if max_price:
            query += " AND price <= %s"
            params.append(max_price)

    cur.execute(query, params)
    packages = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_packages.html', packages=packages)

@app.route('/delete/<int:package_id>')
def delete_package(package_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM packages WHERE id = %s", (package_id,))
        conn.commit()
        flash('Package deleted successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting package: {e}', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('view_packages'))


@app.route('/book/<int:package_id>', methods=['GET', 'POST'])
def book(package_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO bookings (name, email, package_id) VALUES (%s, %s, %s)",
                    (name, email, package_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('home'))
    return render_template('book_package.html', package_id=package_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
        admin = cur.fetchone()
        cur.close()
        conn.close()
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/view-bookings')
def view_bookings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bookings.id, bookings.name, bookings.email, packages.name
        FROM bookings JOIN packages ON bookings.package_id = packages.id
    """)
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_bookings.html', bookings=bookings)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            conn.commit()
            flash('Registered successfully! Please log in.', 'success')
            return redirect('/login')
        except:
            flash('Email already exists.', 'danger')
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            flash('Login successful!', 'success')
            return redirect('/user-dashboard')
        else:
            flash('Invalid email or password', 'danger')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM packages")
    packages = cur.fetchall()
    conn.close()
    return render_template('user_dashboard.html', packages=packages, name=session['user_name'])


@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect('/login')
    user_name = session['user_name']
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.id, b.name, b.email, p.name, p.price
        FROM bookings b
        JOIN packages p ON b.package_id = p.id
        WHERE b.name = %s
    """, (user_name,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/enquiry', methods=['GET', 'POST'])
def enquiry():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO enquiry (name, email, subject, message) VALUES (%s, %s, %s, %s)",
                    (name, email, subject, message))
        conn.commit()
        cur.close()
        conn.close()
        flash('Your enquiry has been submitted!', 'success')
        return redirect('/')
    return render_template('enquiry.html')

@app.route('/admin/enquiries')
def view_enquiries():
    if not session.get('admin_logged_in'):
        return redirect('/admin')
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM enquiry")
    enquiries = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_enquiries.html', enquiries=enquiries)

@app.route('/admin/reply/<int:enquiry_id>', methods=['GET', 'POST'])
def reply_enquiry(enquiry_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin')
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        reply = request.form['reply']
        cur.execute("UPDATE enquiry SET reply=%s WHERE id=%s", (reply, enquiry_id))
        conn.commit()
        cur.close()
        conn.close()
        flash('Reply sent successfully!', 'success')
        return redirect('/admin/enquiries')
    cur.execute("SELECT * FROM enquiry WHERE id = %s", (enquiry_id,))
    enquiry = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('reply_enquiry.html', enquiry=enquiry)

@app.route('/my-enquiries')
def my_enquiries():
    if 'user_id' not in session:
        return redirect('/login')
    user_email = session['user_email']
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT subject, message, reply, created_at FROM enquiry WHERE email=%s", (user_email,))
    enquiries = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('my_enquiries.html', enquiries=enquiries)

@app.route('/package/<int:package_id>', methods=['GET', 'POST'])
def package_details(package_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        if request.method == 'POST':
            if 'user_id' not in session:
                flash("Please log in to submit a review.", "warning")
                return redirect(url_for('login'))

            rating = int(request.form['rating'])
            comment = request.form['comment']
            user_id = session['user_id']

            # Insert review
            cur.execute(
                "INSERT INTO reviews (user_id, package_id, rating, comment) VALUES (%s, %s, %s, %s)",
                (user_id, package_id, rating, comment)
            )
            conn.commit()

        # Fetch package details
        cur.execute("SELECT * FROM packages WHERE id = %s", (package_id,))
        package = cur.fetchone()

        if not package:
            flash("Package not found.", "danger")
            return redirect(url_for('view_packages'))

        # Fetch reviews with usernames
        cur.execute("""
            SELECT users.name, reviews.rating, reviews.comment, reviews.created_at
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            WHERE reviews.package_id = %s
            ORDER BY reviews.created_at DESC
        """, (package_id,))
        reviews = cur.fetchall()

    finally:
        conn.close()

    return render_template('package_details.html', package=package, reviews=reviews)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
