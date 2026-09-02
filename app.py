from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from math import radians, sin, cos, sqrt, atan2
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)

app.secret_key = "ev_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="yashu020",
    database="ev_charging"
)

cursor = db.cursor()


# =========================================================
# GMAIL SETTINGS
# =========================================================

SENDER_EMAIL = "yourgmail@gmail.com"
SENDER_PASSWORD = "YOUR_APP_PASSWORD"


# =========================================================
# COMMON EMAIL FUNCTION
# =========================================================

def send_email(receiver_email, subject, body):

    try:

        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = receiver_email

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            SENDER_EMAIL,
            SENDER_PASSWORD
        )

        server.send_message(msg)

        server.quit()

        print("Email sent successfully to:", receiver_email)

        return True

    except Exception as e:

        print("Email error:", e)

        return False


# =========================================================
# LOGIN EMAIL
# =========================================================

def send_login_email(receiver_email, fullname):

    subject = "EV Charging Station Finder - Login Successful"

    login_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    body = f"""
Hello {fullname},

You have successfully logged in to your EV Charging Station Finder account.

Login Time:
{login_time}

If this login was not performed by you, please change your password immediately.

Thank you for using EV Charging Station Finder.
"""

    return send_email(
        receiver_email,
        subject,
        body
    )


# =========================================================
# BOOKING CONFIRMATION EMAIL
# =========================================================

def send_confirmation_email(
    receiver_email,
    station_name,
    booking_date,
    booking_time
):

    subject = "EV Charging Slot Booking Confirmation"

    body = f"""
Hello,

Your EV charging station booking has been confirmed successfully.

Booking Details
----------------------------

Station:
{station_name}

Booking Date:
{booking_date}

Booking Time:
{booking_time}

Status:
Booked

Please reach the charging station at your scheduled time.

Thank you for using EV Charging Station Finder.
"""

    return send_email(
        receiver_email,
        subject,
        body
    )


# =========================================================
# CANCELLATION EMAIL
# =========================================================

def send_cancellation_email(
    receiver_email,
    station_name,
    booking_date,
    booking_time,
    automatic=False
):

    if automatic:

        subject = "EV Charging Booking Automatically Cancelled"

        reason = """
You did not attend the charging station within 10 minutes
after your scheduled booking time.
"""

    else:

        subject = "EV Charging Booking Cancelled"

        reason = """
Your booking was cancelled by you.
"""


    body = f"""
Hello,

Your EV charging station booking has been cancelled.

Booking Details
----------------------------

Station:
{station_name}

Booking Date:
{booking_date}

Booking Time:
{booking_time}

Reason:
{reason}

Your charging slot has now been released and is available
for other users.

Thank you for using EV Charging Station Finder.
"""

    return send_email(
        receiver_email,
        subject,
        body
    )


# =========================================================
# AUTOMATIC NO-SHOW BOOKING CANCELLATION
# =========================================================

def check_expired_bookings():

    try:

        # Use a separate database connection because
        # this function runs in a background thread.

        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="yashu020",
            database="ev_charging"
        )

        job_cursor = connection.cursor()

        now = datetime.now()


        job_cursor.execute("""
            SELECT
                b.booking_id,
                b.user_email,
                b.station_id,
                s.station_name,
                b.booking_date,
                b.booking_time
            FROM bookings b
            JOIN stations s
            ON b.station_id = s.station_id
            WHERE b.status = 'Booked'
        """)


        expired_bookings = job_cursor.fetchall()


        for booking in expired_bookings:

            booking_id = booking[0]
            user_email = booking[1]
            station_id = booking[2]
            station_name = booking[3]
            booking_date = booking[4]
            booking_time = booking[5]


            # Convert booking date and time into datetime

            booking_datetime = datetime.combine(
                booking_date,
                booking_time
            )


            # Allow user 10 minutes after booking time

            expiry_time = (
                booking_datetime
                + timedelta(minutes=10)
            )


            # Check whether 10 minutes have passed

            if now >= expiry_time:


                # Cancel booking

                job_cursor.execute("""
                    UPDATE bookings
                    SET status = 'Cancelled'
                    WHERE booking_id = %s
                    AND status = 'Booked'
                """, (booking_id,))


                # Make sure only one process cancelled it

                if job_cursor.rowcount == 1:


                    # Return charging slot

                    job_cursor.execute("""
                        UPDATE stations
                        SET available_slots =
                            available_slots + 1
                        WHERE station_id = %s
                    """, (station_id,))


                    connection.commit()


                    # Send automatic cancellation email

                    send_cancellation_email(
                        user_email,
                        station_name,
                        booking_date,
                        booking_time,
                        automatic=True
                    )


                    print(
                        "Booking",
                        booking_id,
                        "automatically cancelled."
                    )


        job_cursor.close()

        connection.close()


    except Exception as e:

        print(
            "Automatic cancellation error:",
            e
        )


# =========================================================
# HOME
# =========================================================

@app.route('/')
def home():

    return render_template(
        'index.html'
    )


# =========================================================
# REGISTER
# =========================================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        gender = request.form['gender']
        address = request.form['address']
        vehicle_number = request.form['vehicle_number']
        password = request.form['password']


        # PASSWORD VALIDATION

        if len(password) < 8:

            flash(
                "Password must be at least 8 characters long."
            )

            return redirect(
                url_for('register')
            )


        if not re.search(r'[A-Z]', password):

            flash(
                "Password must contain at least one uppercase letter."
            )

            return redirect(
                url_for('register')
            )


        if not re.search(r'[a-z]', password):

            flash(
                "Password must contain at least one lowercase letter."
            )

            return redirect(
                url_for('register')
            )


        if not re.search(r'[0-9]', password):

            flash(
                "Password must contain at least one number."
            )

            return redirect(
                url_for('register')
            )


        if not re.search(
            r'[^A-Za-z0-9]',
            password
        ):

            flash(
                "Password must contain at least one special character."
            )

            return redirect(
                url_for('register')
            )


        # CHECK EMAIL

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()


        if user:

            flash(
                "Email already exists. Please use another email."
            )

            return redirect(
                url_for('register')
            )


        # INSERT USER

        sql = """
        INSERT INTO users
        (
            fullname,
            email,
            phone,
            gender,
            address,
            vehicle_number,
            password
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            fullname,
            email,
            phone,
            gender,
            address,
            vehicle_number,
            password
        )


        cursor.execute(
            sql,
            values
        )

        db.commit()


        flash(
            "Registration Successful!"
        )


        return redirect(
            url_for('login')
        )


    return render_template(
        'register.html'
    )


# =========================================================
# LOGIN
# =========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            AND password=%s
            """,
            (
                email,
                password
            )
        )


        user = cursor.fetchone()


        if user:

            session['fullname'] = user[1]

            session['email'] = user[2]


            # SEND LOGIN EMAIL

            send_login_email(
                session['email'],
                session['fullname']
            )


            return redirect(
                url_for('dashboard')
            )


        flash(
            "Invalid Email or Password"
        )


        return redirect(
            url_for('login')
        )


    return render_template(
        'login.html'
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route('/dashboard')
def dashboard():

    if 'fullname' not in session:

        return redirect(
            url_for('login')
        )


    return render_template(
        'dashboard.html',
        fullname=session['fullname']
    )


# =========================================================
# SEARCH STATION
# =========================================================

@app.route('/search_station', methods=['GET', 'POST'])
def search_station():

    if request.method == 'POST':

        city = request.form.get('city', '').strip()

        cursor.execute("""
            SELECT
                station_id,
                station_name,
                city,
                address,
                charger_type,
                available_slots,
                price,
                opening_time,
                closing_time,
                latitude,
                longitude
            FROM stations
            WHERE city LIKE %s
        """, ('%' + city + '%',))

    else:

        cursor.execute("""
            SELECT
                station_id,
                station_name,
                city,
                address,
                charger_type,
                available_slots,
                price,
                opening_time,
                closing_time,
                latitude,
                longitude
            FROM stations
        """)

    stations = cursor.fetchall()

    return render_template(
        'search_station.html',
        stations=stations
    )


# =========================================================
# BOOK CHARGING SLOT
# =========================================================

@app.route('/book/<int:station_id>', methods=['GET', 'POST'])
def book(station_id):

    if 'fullname' not in session:
        return redirect(url_for('login'))

    # ==========================================
    # GET STATION DETAILS
    # ==========================================

    cursor.execute("""
        SELECT
            available_slots,
            station_name,
            opening_time,
            closing_time
        FROM stations
        WHERE station_id=%s
    """, (station_id,))

    station = cursor.fetchone()

    if not station:
        flash("Station not found!")
        return redirect(url_for('search_station'))

    station_capacity = station[0]
    station_name = station[1]
    opening_time = station[2]
    closing_time = station[3]

    # If timing is empty in database, use default timing
    if opening_time is None:
        opening_time = datetime.strptime(
            "06:00",
            "%H:%M"
        ).time()

    if closing_time is None:
        closing_time = datetime.strptime(
            "20:00",
            "%H:%M"
        ).time()


    # ==========================================
    # ALLOWED 2-HOUR SLOTS
    # ==========================================

    allowed_slots = [
        "06:00",
        "08:00",
        "10:00",
        "12:00",
        "14:00",
        "16:00",
        "18:00"
    ]


    # ==========================================
    # BOOKING
    # ==========================================

    if request.method == 'POST':

        vehicle_number = request.form.get('vehicle_number')
        booking_date = request.form.get('booking_date')
        booking_time = request.form.get('booking_time')


        # ======================================
        # CHECK EMPTY VALUES
        # ======================================

        if not vehicle_number or not booking_date or not booking_time:

            flash("Please fill all booking details.")

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # CHECK VALID 2-HOUR SLOT
        # ======================================

        if booking_time not in allowed_slots:

            flash(
                "Please select a valid 2-hour charging slot."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # DATE + TIME VALIDATION
        # ======================================

        try:

            booking_datetime = datetime.strptime(
                booking_date + " " + booking_time,
                "%Y-%m-%d %H:%M"
            )

        except ValueError:

            flash(
                "Invalid booking date or time."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        current_datetime = datetime.now()


        # ======================================
        # PREVIOUS DATE / TIME
        # ======================================

        if booking_datetime <= current_datetime:

            flash(
                "You cannot book a previous date or time."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # 3 HOURS ADVANCE BOOKING
        # ======================================

        minimum_booking_time = (
            current_datetime +
            timedelta(hours=3)
        )

        if booking_datetime < minimum_booking_time:

            flash(
                "Booking time must be at least "
                "3 hours from the current time."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # STATION OPENING / CLOSING TIME
        # ======================================

        selected_time = booking_datetime.time()

        if (
            selected_time < opening_time
            or selected_time >= closing_time
        ):

            flash(
                "Booking is available only between "
                f"{opening_time.strftime('%I:%M %p')} and "
                f"{closing_time.strftime('%I:%M %p')}."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # CHECK SAME SLOT BOOKINGS
        # ======================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE station_id=%s
            AND booking_date=%s
            AND booking_time=%s
            AND status='Booked'
        """, (
            station_id,
            booking_date,
            booking_time
        ))

        booked_count = cursor.fetchone()[0]


        # ======================================
        # CHECK SLOT CAPACITY
        # ======================================

        if booked_count >= station_capacity:

            flash(
                "This charging slot is full. "
                "Please select another time slot."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        # ======================================
        # INSERT BOOKING
        # ======================================

        cursor.execute("""
            INSERT INTO bookings
            (
                user_email,
                station_id,
                booking_date,
                booking_time,
                vehicle_number,
                status
            )
            VALUES (%s,%s,%s,%s,%s,'Booked')
        """, (
            session['email'],
            station_id,
            booking_date,
            booking_time,
            vehicle_number
        ))

        db.commit()


        # ======================================
        # BOOKING CONFIRMATION EMAIL
        # ======================================

        try:

            send_confirmation_email(
                session['email'],
                station_name,
                booking_date,
                booking_time
            )

        except Exception as e:

            print(
                "Confirmation email failed:",
                e
            )


        # ======================================
        # SUCCESS MESSAGE
        # ======================================

        flash(
            "Booking Successful!"
        )

        return redirect(
            url_for('booking_history')
        )


    # ==========================================
    # SHOW BOOKING PAGE
    # ==========================================

    return render_template(
        'book.html',
        station_id=station_id,
        station_name=station_name,
        opening_time=opening_time,
        closing_time=closing_time,
        station_capacity=station_capacity
    )

# =========================================================
# BOOKING HISTORY
# =========================================================

@app.route('/booking_history')
def booking_history():

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    cursor.execute(
        """
        SELECT
            b.booking_id,
            b.station_id,
            s.station_name,
            b.booking_date,
            b.booking_time,
            b.vehicle_number,
            b.status
        FROM bookings b
        JOIN stations s
        ON b.station_id = s.station_id
        WHERE b.user_email=%s
        ORDER BY b.booking_date DESC,
                 b.booking_time DESC
        """,
        (session['email'],)
    )


    bookings = cursor.fetchall()


    return render_template(
        "booking_history.html",
        bookings=bookings
    )


# =========================================================
# CANCEL BOOKING
# =========================================================

@app.route(
    '/cancel_booking/<int:booking_id>'
)
def cancel_booking(booking_id):

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    # CHECK BOOKING

    cursor.execute(
        """
        SELECT
            b.station_id,
            b.status,
            b.booking_date,
            b.booking_time,
            s.station_name
        FROM bookings b
        JOIN stations s
        ON b.station_id = s.station_id
        WHERE b.booking_id=%s
        AND b.user_email=%s
        """,
        (
            booking_id,
            session['email']
        )
    )


    booking = cursor.fetchone()


    if not booking:

        flash(
            "Booking not found!"
        )

        return redirect(
            url_for('booking_history')
        )


    station_id = booking[0]

    status = booking[1]

    booking_date = booking[2]

    booking_time = booking[3]

    station_name = booking[4]


    if status != 'Booked':

        flash(
            "This booking is already cancelled."
        )

        return redirect(
            url_for('booking_history')
        )


    # CANCEL BOOKING

    cursor.execute(
        """
        UPDATE bookings
        SET status='Cancelled'
        WHERE booking_id=%s
        AND user_email=%s
        AND status='Booked'
        """,
        (
            booking_id,
            session['email']
        )
    )


    # Only return the slot if the booking
    # was successfully cancelled

    if cursor.rowcount == 1:

        cursor.execute(
            """
            UPDATE stations
            SET available_slots =
                available_slots + 1
            WHERE station_id=%s
            """,
            (station_id,)
        )


        db.commit()


        # SEND MANUAL CANCELLATION EMAIL

        try:

            send_cancellation_email(
                session['email'],
                station_name,
                booking_date,
                booking_time,
                automatic=False
            )

        except Exception as e:

            print(
                "Cancellation email failed:",
                e
            )


        flash(
            "Booking Cancelled Successfully!"
        )

    else:

        flash(
            "Booking could not be cancelled."
        )


    return redirect(
        url_for('booking_history')
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect(
        url_for('login')
    )


# =========================================================
# OWNER LOGIN
# =========================================================

@app.route(
    '/owner_login',
    methods=['GET', 'POST']
)
def owner_login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']


        cursor.execute(
            """
            SELECT *
            FROM station_owners
            WHERE email=%s
            AND password=%s
            """,
            (
                email,
                password
            )
        )


        owner = cursor.fetchone()


        if owner:

            session['owner_name'] = owner[1]

            return redirect(
                url_for('owner_dashboard')
            )


        flash(
            "Invalid Login"
        )


    return render_template(
        "owner_login.html"
    )


# =========================================================
# OWNER DASHBOARD
# =========================================================

@app.route('/owner_dashboard')
def owner_dashboard():

    if 'owner_name' not in session:

        return redirect(
            url_for('owner_login')
        )


    cursor.execute(
        "SELECT COUNT(*) FROM stations"
    )

    total_stations = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COUNT(*) FROM bookings"
    )

    total_bookings = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT IFNULL(
            SUM(available_slots),
            0
        )
        FROM stations
        """
    )

    available_slots = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT COUNT(*)
        FROM bookings
        WHERE status='Completed'
        """
    )

    completed_bookings = cursor.fetchone()[0]


    return render_template(
        'owner_dashboard.html',
        owner_name=session['owner_name'],
        total_stations=total_stations,
        total_bookings=total_bookings,
        available_slots=available_slots,
        completed_bookings=completed_bookings
    )


# =========================================================
# MANAGE STATION
# =========================================================

@app.route('/manage_station')
def manage_station():

    if 'owner_name' not in session:

        return redirect(
            url_for('owner_login')
        )


    cursor.execute(
        "SELECT * FROM stations"
    )

    stations = cursor.fetchall()


    return render_template(
        "manage_station.html",
        stations=stations
    )


# =========================================================
# VIEW BOOKINGS
# =========================================================

@app.route('/view_bookings')
def view_bookings():

    cursor.execute(
        "SELECT * FROM bookings"
    )

    bookings = cursor.fetchall()


    return render_template(
        "view_bookings.html",
        bookings=bookings
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    '/admin_login',
    methods=['GET', 'POST']
)
def admin_login():

    if request.method == 'POST':

        username = request.form['username']

        password = request.form['password']


        cursor.execute(
            """
            SELECT *
            FROM admin
            WHERE username=%s
            AND password=%s
            """,
            (
                username,
                password
            )
        )


        admin = cursor.fetchone()


        if admin:

            session['admin'] = admin[1]

            return redirect(
                url_for('admin_dashboard')
            )


        flash(
            "Invalid Username or Password"
        )


    return render_template(
        'admin_login.html'
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:

        return redirect(
            url_for('admin_login')
        )


    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COUNT(*) FROM stations"
    )

    total_stations = cursor.fetchone()[0]


    cursor.execute(
        "SELECT COUNT(*) FROM bookings"
    )

    total_bookings = cursor.fetchone()[0]


    return render_template(
        "admin_dashboard.html",
        admin=session['admin'],
        total_users=total_users,
        total_stations=total_stations,
        total_bookings=total_bookings
    )


# =========================================================
# MANAGE USERS
# =========================================================

@app.route('/manage_users')
def manage_users():

    cursor.execute(
        "SELECT * FROM users"
    )

    users = cursor.fetchall()


    return render_template(
        "manage_users.html",
        users=users
    )


# =========================================================
# MANAGE STATIONS
# =========================================================

@app.route('/manage_stations')
def manage_stations():

    cursor.execute(
        "SELECT * FROM stations"
    )

    stations = cursor.fetchall()


    return render_template(
        "manage_stations.html",
        stations=stations
    )


# =========================================================
# ALL BOOKINGS
# =========================================================

@app.route(
    '/all_bookings',
    methods=['GET', 'POST']
)
def all_bookings():

    if request.method == 'POST':

        search = request.form['search']


        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.user_email,
                s.station_name,
                b.booking_date,
                b.booking_time,
                b.status
            FROM bookings b
            JOIN stations s
            ON b.station_id=s.station_id
            WHERE b.user_email LIKE %s
            OR s.station_name LIKE %s
            """,
            (
                '%' + search + '%',
                '%' + search + '%'
            )
        )


    else:

        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.user_email,
                s.station_name,
                b.booking_date,
                b.booking_time,
                b.status
            FROM bookings b
            JOIN stations s
            ON b.station_id=s.station_id
            """
        )


    bookings = cursor.fetchall()


    return render_template(
        "all_bookings.html",
        bookings=bookings
    )


# =========================================================
# REPORTS
# =========================================================

@app.route('/reports')
def reports():

    # ==========================================
    # TOTAL USERS
    # ==========================================

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]


    # ==========================================
    # TOTAL STATIONS
    # ==========================================

    cursor.execute(
        "SELECT COUNT(*) FROM stations"
    )

    total_stations = cursor.fetchone()[0]


    # ==========================================
    # TOTAL BOOKINGS
    # ==========================================

    cursor.execute(
        "SELECT COUNT(*) FROM bookings"
    )

    total_bookings = cursor.fetchone()[0]


    # ==========================================
    # TOTAL REVENUE
    # ==========================================

    cursor.execute(
        """
        SELECT IFNULL(
            SUM(s.price),
            0
        )
        FROM bookings b
        JOIN stations s
        ON b.station_id=s.station_id
        WHERE b.status='Booked'
        """
    )

    total_revenue = cursor.fetchone()[0]


    # ==========================================
    # MONTHLY BOOKINGS
    # ==========================================

    cursor.execute(
        """
        SELECT
            MONTH(booking_date) AS month_no,
            MONTHNAME(booking_date) AS month_name,
            COUNT(*) AS total_bookings
        FROM bookings
        GROUP BY
            MONTH(booking_date),
            MONTHNAME(booking_date)
        ORDER BY month_no
        """
    )

    monthly_bookings = cursor.fetchall()


    # ==========================================
    # DATE-WISE BOOKING REPORT
    # ==========================================

    cursor.execute(
        """
        SELECT
            booking_date,
            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN status='Booked'
                    THEN 1
                    ELSE 0
                END
            ) AS booked,

            SUM(
                CASE
                    WHEN status='Cancelled'
                    THEN 1
                    ELSE 0
                END
            ) AS cancelled

        FROM bookings

        GROUP BY booking_date

        ORDER BY booking_date DESC
        """
    )

    date_wise_bookings = cursor.fetchall()


    # ==========================================
    # SEND DATA TO REPORTS PAGE
    # ==========================================

    return render_template(
        "reports.html",

        total_users=total_users,

        total_stations=total_stations,

        total_bookings=total_bookings,

        total_revenue=total_revenue,

        monthly_bookings=monthly_bookings,

        date_wise_bookings=date_wise_bookings
    )

# =========================================================
# DELETE USER
# =========================================================

@app.route(
    '/delete_user/<int:user_id>'
)
def delete_user(user_id):

    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (user_id,)
    )

    db.commit()


    return redirect(
        url_for('manage_users')
    )


# =========================================================
# ADD STATION
# =========================================================

@app.route(
    '/add_station',
    methods=['GET', 'POST']
)
def add_station():

    if 'owner_name' not in session:

        return redirect(
            url_for('owner_login')
        )


    if request.method == 'POST':

        station_name = request.form[
            'station_name'
        ]

        city = request.form[
            'city'
        ]

        address = request.form[
            'address'
        ]

        latitude = request.form[
            'latitude'
        ]

        longitude = request.form[
            'longitude'
        ]

        charger_type = request.form[
            'charger_type'
        ]

        available_slots = request.form[
            'available_slots'
        ]

        price = request.form[
            'price'
        ]


        cursor.execute(
            """
            INSERT INTO stations
            (
                station_name,
                city,
                address,
                latitude,
                longitude,
                charger_type,
                available_slots,
                price
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                station_name,
                city,
                address,
                latitude,
                longitude,
                charger_type,
                available_slots,
                price
            )
        )


        db.commit()


        flash(
            "Station Added Successfully!"
        )


        return redirect(
            url_for('manage_station')
        )


    return render_template(
        "add_station.html"
    )


# =========================================================
# EDIT STATION
# =========================================================

@app.route(
    '/edit_station/<int:station_id>',
    methods=['GET', 'POST']
)
def edit_station(station_id):

    if request.method == 'POST':

        station_name = request.form[
            'station_name'
        ]

        city = request.form[
            'city'
        ]

        address = request.form[
            'address'
        ]

        latitude = request.form[
            'latitude'
        ]

        longitude = request.form[
            'longitude'
        ]

        charger_type = request.form[
            'charger_type'
        ]

        available_slots = request.form[
            'available_slots'
        ]

        price = request.form[
            'price'
        ]


        cursor.execute(
            """
            UPDATE stations
            SET
                station_name=%s,
                city=%s,
                address=%s,
                latitude=%s,
                longitude=%s,
                charger_type=%s,
                available_slots=%s,
                price=%s
            WHERE station_id=%s
            """,
            (
                station_name,
                city,
                address,
                latitude,
                longitude,
                charger_type,
                available_slots,
                price,
                station_id
            )
        )


        db.commit()


        flash(
            "Station Updated Successfully!"
        )


        return redirect(
            url_for('manage_station')
        )


    cursor.execute(
        """
        SELECT *
        FROM stations
        WHERE station_id=%s
        """,
        (station_id,)
    )


    station = cursor.fetchone()


    return render_template(
        "edit_station.html",
        station=station
    )


# =========================================================
# DELETE STATION
# =========================================================

@app.route(
    '/delete_station/<int:station_id>'
)
def delete_station(station_id):

    cursor.execute(
        """
        DELETE FROM stations
        WHERE station_id=%s
        """,
        (station_id,)
    )


    db.commit()


    flash(
        "Station Deleted Successfully!"
    )


    return redirect(
        url_for('manage_station')
    )


# =========================================================
# PROFILE
# =========================================================

@app.route('/profile')
def profile():

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    cursor.execute(
        """
        SELECT
            fullname,
            email,
            phone,
            gender,
            address,
            vehicle_number
        FROM users
        WHERE email=%s
        """,
        (session['email'],)
    )


    user = cursor.fetchone()


    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# EDIT PROFILE
# =========================================================

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    email = session['email']


    if request.method == 'POST':

        fullname = request.form['fullname']

        phone = request.form['phone']

        gender = request.form['gender']

        address = request.form['address']

        vehicle_number = request.form['vehicle_number']


        cursor.execute(
            """
            UPDATE users
            SET fullname=%s,
                phone=%s,
                gender=%s,
                address=%s,
                vehicle_number=%s
            WHERE email=%s
            """,
            (
                fullname,
                phone,
                gender,
                address,
                vehicle_number,
                email
            )
        )


        db.commit()


        # Update session name also

        session['fullname'] = fullname


        flash(
            "Profile updated successfully!"
        )


        return redirect(
            url_for('profile')
        )


    cursor.execute(
        """
        SELECT
            fullname,
            email,
            phone,
            gender,
            address,
            vehicle_number
        FROM users
        WHERE email=%s
        """,
        (email,)
    )


    user = cursor.fetchone()


    return render_template(
        'edit_profile.html',
        user=user
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route(
    '/change_password',
    methods=['GET', 'POST']
)
def change_password():

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    if request.method == 'POST':

        old_password = request.form[
            'old_password'
        ]

        new_password = request.form[
            'new_password'
        ]


        # PASSWORD VALIDATION

        if len(new_password) < 8:

            flash(
                "Password must be at least 8 characters long."
            )

            return redirect(
                url_for('change_password')
            )


        if not re.search(
            r'[A-Z]',
            new_password
        ):

            flash(
                "Password must contain an uppercase letter."
            )

            return redirect(
                url_for('change_password')
            )


        if not re.search(
            r'[a-z]',
            new_password
        ):

            flash(
                "Password must contain a lowercase letter."
            )

            return redirect(
                url_for('change_password')
            )


        if not re.search(
            r'[0-9]',
            new_password
        ):

            flash(
                "Password must contain a number."
            )

            return redirect(
                url_for('change_password')
            )


        if not re.search(
            r'[^A-Za-z0-9]',
            new_password
        ):

            flash(
                "Password must contain a special character."
            )

            return redirect(
                url_for('change_password')
            )


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            AND password=%s
            """,
            (
                session['email'],
                old_password
            )
        )


        user = cursor.fetchone()


        if user:

            cursor.execute(
                """
                UPDATE users
                SET password=%s
                WHERE email=%s
                """,
                (
                    new_password,
                    session['email']
                )
            )


            db.commit()


            flash(
                "Password Changed Successfully!"
            )


            return redirect(
                url_for('dashboard')
            )


        flash(
            "Old Password is Incorrect!"
        )


    return render_template(
        "change_password.html"
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    '/forgot_password',
    methods=['GET', 'POST']
)
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']

        new_password = request.form[
            'new_password'
        ]


        # VALIDATE PASSWORD

        if len(new_password) < 8:

            flash(
                "Password must be at least 8 characters long."
            )

            return redirect(
                url_for('forgot_password')
            )


        if not re.search(
            r'[A-Z]',
            new_password
        ):

            flash(
                "Password must contain an uppercase letter."
            )

            return redirect(
                url_for('forgot_password')
            )


        if not re.search(
            r'[a-z]',
            new_password
        ):

            flash(
                "Password must contain a lowercase letter."
            )

            return redirect(
                url_for('forgot_password')
            )


        if not re.search(
            r'[0-9]',
            new_password
        ):

            flash(
                "Password must contain a number."
            )

            return redirect(
                url_for('forgot_password')
            )


        if not re.search(
            r'[^A-Za-z0-9]',
            new_password
        ):

            flash(
                "Password must contain a special character."
            )

            return redirect(
                url_for('forgot_password')
            )


        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            """,
            (email,)
        )


        user = cursor.fetchone()


        if user:

            cursor.execute(
                """
                UPDATE users
                SET password=%s
                WHERE email=%s
                """,
                (
                    new_password,
                    email
                )
            )


            db.commit()


            flash(
                "Password Reset Successfully!"
            )


            return redirect(
                url_for('login')
            )


        flash(
            "Email not found!"
        )


    return render_template(
        "forgot_password.html"
    )


# =========================================================
# REVIEW
# =========================================================

@app.route(
    '/review/<int:station_id>',
    methods=['GET', 'POST']
)
def review(station_id):

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    if request.method == 'POST':

        rating = request.form[
            'rating'
        ]

        review_text = request.form[
            'review'
        ]


        cursor.execute(
            """
            INSERT INTO reviews
            (
                station_id,
                user_email,
                rating,
                review
            )
            VALUES (%s,%s,%s,%s)
            """,
            (
                station_id,
                session['email'],
                rating,
                review_text
            )
        )


        db.commit()


        flash(
            "Review Submitted Successfully!"
        )


        return redirect(
            url_for('booking_history')
        )


    return render_template(
        "review.html",
        station_id=station_id
    )


# =========================================================
# VIEW REVIEWS
# =========================================================

@app.route('/view_reviews')
def view_reviews():

    cursor.execute(
        """
        SELECT
            station_id,
            user_email,
            rating,
            review,
            created_at
        FROM reviews
        ORDER BY created_at DESC
        """
    )


    reviews = cursor.fetchall()


    return render_template(
        "view_reviews.html",
        reviews=reviews
    )


# =========================================================
# NEARBY STATIONS - GPS
# =========================================================

@app.route('/nearby_stations')
def nearby_stations():

    latitude = request.args.get('latitude')

    longitude = request.args.get('longitude')


    if not latitude or not longitude:

        flash(
            "Location not available."
        )

        return redirect(
            url_for('dashboard')
        )


    latitude = float(latitude)

    longitude = float(longitude)


    cursor.execute(
        """
        SELECT
            station_name,
            city,
            address,
            charger_type,
            available_slots,
            price,
            latitude,
            longitude
        FROM stations
        """
    )


    stations = cursor.fetchall()


    nearby_stations = []


    for station in stations:

        if station[6] is None or station[7] is None:

            continue


        station_lat = float(station[6])

        station_lon = float(station[7])


        R = 6371


        dlat = radians(
            station_lat - latitude
        )

        dlon = radians(
            station_lon - longitude
        )


        a = (
            sin(dlat / 2) ** 2
            + cos(radians(latitude))
            * cos(radians(station_lat))
            * sin(dlon / 2) ** 2
        )


        c = 2 * atan2(
            sqrt(a),
            sqrt(1 - a)
        )


        distance = R * c


        if distance <= 10:

            nearby_stations.append({

                'station_name':
                    station[0],

                'city':
                    station[1],

                'address':
                    station[2],

                'charger_type':
                    station[3],

                'available_slots':
                    station[4],

                'price':
                    station[5],

                'distance':
                    round(distance, 2)

            })


    nearby_stations.sort(
        key=lambda x: x['distance']
    )


    return render_template(
        'nearby_stations.html',
        stations=nearby_stations
    )


# =========================================================
# ABOUT
# =========================================================

@app.route('/about')
def about():

    return render_template(
        'about.html'
    )


# =========================================================
# SEARCH STATIONS
# =========================================================

@app.route(
    '/search_stations',
    methods=['GET', 'POST']
)
def search_stations():

    stations = []


    if request.method == 'POST':

        city = request.form.get(
            'city',
            ''
        ).strip()


        if city:

            cursor.execute(
                """
                SELECT
                    station_id,
                    station_name,
                    city,
                    address,
                    charger_type,
                    available_slots,
                    price
                FROM stations
                WHERE city LIKE %s
                ORDER BY station_name
                """,
                (
                    '%' + city + '%',
                )
            )


            stations = cursor.fetchall()


        else:

            flash(
                "Please enter a city."
            )


    else:

        cursor.execute(
            """
            SELECT
                station_id,
                station_name,
                city,
                address,
                charger_type,
                available_slots,
                price
            FROM stations
            ORDER BY station_name
            """
        )


        stations = cursor.fetchall()


    return render_template(
        'search_stations.html',
        stations=stations
    )


# =========================================================
# FEATURES
# =========================================================

@app.route('/features')
def features():

    return render_template(
        'features.html'
    )


# =========================================================
# CONTACT
# =========================================================

@app.route(
    '/contact',
    methods=['GET', 'POST']
)
def contact():

    if request.method == 'POST':

        name = request.form.get(
            'name'
        )

        email = request.form.get(
            'email'
        )

        subject = request.form.get(
            'subject'
        )

        message = request.form.get(
            'message'
        )


        cursor.execute(
            """
            INSERT INTO contact_messages
            (
                name,
                subject,
                message
            )
            VALUES (%s, %s, %s)
            """,
            (
                name,
                subject,
                message
            )
        )


        db.commit()


        flash(
            "Thank you! Your message has been sent successfully."
        )


        return redirect(
            url_for('contact')
        )


    return render_template(
        'contact.html'
    )


# =========================================================
# CONTACT MESSAGES
# =========================================================

@app.route('/contact_messages')
def contact_messages():

    cursor.execute(
        """
        SELECT
            message_id,
            name,
            subject,
            message,
            created_at
        FROM contact_messages
        ORDER BY created_at DESC
        """
    )


    messages = cursor.fetchall()


    return render_template(
        'contact_messages.html',
        messages=messages
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == '__main__':

    # Create background scheduler

    scheduler = BackgroundScheduler()


    # Check bookings every 1 minute

    scheduler.add_job(
        func=check_expired_bookings,
        trigger='interval',
        minutes=1,
        max_instances=1,
        coalesce=True
    )


    scheduler.start()


    print(
        "Automatic booking cancellation scheduler started."
    )


    @app.route('/test_email')
    def test_email():
        result = send_email(
        SENDER_EMAIL,
        "EV Charging System Test Email",
        """
Hello,

This is a test email from the EV Charging Station Finder.

If you received this email, Gmail notification is working correctly.
"""
    )
        if result:
            return "Test email sent successfully. Check your Gmail inbox."
        else:
            return "Email sending failed. Check the VS Code terminal for the error."



    app.run(
        debug=True,
        use_reloader=False
    )