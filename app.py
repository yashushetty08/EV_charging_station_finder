from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from math import radians, sin, cos, sqrt, atan2


app = Flask(__name__)

app.secret_key = "ev_secret_key"




db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="yashu020",
    database="ev_charging"
)

cursor = db.cursor()




def send_confirmation_email(
    receiver_email,
    station_name,
    booking_date,
    booking_time
):

    sender_email = "YOUR_GMAIL@gmail.com"
    sender_password = "YOUR_APP_PASSWORD"

    subject = "EV Charging Slot Booking Confirmation"

    body = f"""
Hello,

Your charging slot has been booked successfully.

Station: {station_name}
Booking Date: {booking_date}
Booking Time: {booking_time}

Thank you for using EV Charging Station Finder.
"""

    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.send_message(msg)

        server.quit()

    except Exception as e:

        print("Email error:", e)




@app.route('/')
def home():

    return render_template(
        'index.html'
    )




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



# LOGIN


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



# DASHBOARD

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


# SEARCH STATION


@app.route('/search_station', methods=['GET', 'POST'])
def search_station():

    if request.method == 'POST':

        city = request.form['city']

        cursor.execute(
            """
            SELECT *
            FROM stations
            WHERE city LIKE %s
            """,
            ('%' + city + '%',)
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM stations
            """
        )

    stations = cursor.fetchall()

    return render_template(
        'search_station.html',
        stations=stations
    )


# BOOK CHARGING SLOT


@app.route(
    '/book/<int:station_id>',
    methods=['GET', 'POST']
)
def book(station_id):

    if 'fullname' not in session:

        return redirect(
            url_for('login')
        )


    
    # CHECK STATION
    

    cursor.execute(
        """
        SELECT
            available_slots,
            station_name
        FROM stations
        WHERE station_id=%s
        """,
        (station_id,)
    )


    station = cursor.fetchone()


    if not station:

        flash(
            "Station not found!"
        )

        return redirect(
            url_for('search_station')
        )


    available_slots = station[0]

    station_name = station[1]


    
    # CHECK AVAILABLE SLOTS
    

    if available_slots <= 0:

        flash(
            "Sorry! All charging slots are filled!"
        )

        return redirect(
            url_for('search_station')
        )


    
    # BOOKING
  

    if request.method == 'POST':

        vehicle_number = request.form[
            'vehicle_number'
        ]

        booking_date = request.form[
            'booking_date'
        ]

        booking_time = request.form[
            'booking_time'
        ]


       
        # DATE + TIME VALIDATION
        

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


        
        # PREVIOUS DATE / TIME
       

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


        
        # MINIMUM 3 HOURS GAP
        

        minimum_booking_time = (
            current_datetime.timestamp()
            + (3 * 60 * 60)
        )


        if booking_datetime.timestamp() < minimum_booking_time:

            flash(
                "Booking time must be at least 3 hours from the current time."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        
        # CHECK SLOT AGAIN
        

        cursor.execute(
            """
            SELECT available_slots
            FROM stations
            WHERE station_id=%s
            """,
            (station_id,)
        )


        current_slots = cursor.fetchone()


        if not current_slots:

            flash(
                "Station not found!"
            )

            return redirect(
                url_for('search_station')
            )


        if current_slots[0] <= 0:

            flash(
                "Sorry! All charging slots are filled!"
            )

            return redirect(
                url_for('search_station')
            )


        
        # CHECK SAME USER / SAME STATION / SAME TIME
     

        cursor.execute(
            """
            SELECT booking_id
            FROM bookings
            WHERE station_id=%s
            AND booking_date=%s
            AND booking_time=%s
            AND status='Booked'
            """,
            (
                station_id,
                booking_date,
                booking_time
            )
        )


        existing_booking = cursor.fetchone()


        if existing_booking:

            flash(
                "This charging time is already booked. Please choose another time."
            )

            return redirect(
                url_for(
                    'book',
                    station_id=station_id
                )
            )


        
        # INSERT BOOKING
       

        cursor.execute(
            """
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
            """,
            (
                session['email'],
                station_id,
                booking_date,
                booking_time,
                vehicle_number
            )
        )


        
        # REDUCE SLOT
        

        cursor.execute(
            """
            UPDATE stations
            SET available_slots =
                available_slots - 1
            WHERE station_id=%s
            AND available_slots > 0
            """,
            (station_id,)
        )


        db.commit()


       
        # SEND EMAIL
        

        try:

            send_confirmation_email(
                session['email'],
                station_name,
                booking_date,
                booking_time
            )

        except Exception as e:

            print("Confirmation email failed:",e)


        flash("Booking Successful!")


        return redirect(
            url_for('booking_history')
        )


    return render_template(
        'book.html',
        station_id=station_id
    )



# BOOKING HISTORY


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



# CANCEL BOOKING


@app.route(
    '/cancel_booking/<int:booking_id>'
)
def cancel_booking(booking_id):

    if 'email' not in session:

        return redirect(
            url_for('login')
        )


    # Check booking belongs to logged-in user

    cursor.execute(
        """
        SELECT station_id, status
        FROM bookings
        WHERE booking_id=%s
        AND user_email=%s
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


    if status != 'Booked':

        flash(
            "This booking is already cancelled."
        )

        return redirect(
            url_for('booking_history')
        )


    # Cancel booking

    cursor.execute(
        """
        UPDATE bookings
        SET status='Cancelled'
        WHERE booking_id=%s
        AND user_email=%s
        """,
        (
            booking_id,
            session['email']
        )
    )


    # Return slot

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


    flash(
        "Booking Cancelled Successfully!"
    )


    return redirect(
        url_for('booking_history')
    )



# LOGOUT

@app.route('/logout')
def logout():

    session.clear()

    return redirect(
        url_for('login')
    )



# OWNER LOGIN


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



# OWNER DASHBOARD


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



# MANAGE STATION


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



# VIEW BOOKINGS


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



# ADMIN LOGIN


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



# ADMIN DASHBOARD


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



# MANAGE USERS


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



# MANAGE STATIONS


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



# ALL BOOKINGS


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



# REPORTS


@app.route('/reports')
def reports():

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


    return render_template(
        "reports.html",
        total_users=total_users,
        total_stations=total_stations,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        monthly_bookings=monthly_bookings
    )



# DELETE USER


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



# ADD STATION


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



# EDIT STATION


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



# DELETE STATION

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



# PROFILE


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



# EDIT PROFILE


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():

    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']

    if request.method == 'POST':

        fullname = request.form['fullname']
        phone = request.form['phone']
        gender = request.form['gender']
        address = request.form['address']
        vehicle_number = request.form['vehicle_number']

        # Update profile
        cursor.execute("""
            UPDATE users
            SET fullname = %s,
                phone = %s,
                gender = %s,
                address = %s,
                vehicle_number = %s
            WHERE email = %s
        """, (
            fullname,
            phone,
            gender,
            address,
            vehicle_number,
            email
        ))

        db.commit()

        flash("Profile updated successfully!")

        return redirect(url_for('profile'))


    

    cursor.execute("""
        SELECT fullname,
               email,
               phone,
               gender,
               address,
               vehicle_number
        FROM users
        WHERE email = %s
    """, (email,))

    user = cursor.fetchone()

    return render_template(
        'edit_profile.html',
        user=user
    )

# CHANGE PASSWORD


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


        # Password validation

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



# FORGOT PASSWORD


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


        # Validate password

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



# REVIEW


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



# VIEW REVIEWS


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



# NEARBY STATIONS - GPS


@app.route('/nearby_stations')
def nearby_stations():

    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')

    if not latitude or not longitude:
        flash("Location not available.")
        return redirect(url_for('dashboard'))

    latitude = float(latitude)
    longitude = float(longitude)

    cursor.execute("""
        SELECT station_name,
               city,
               address,
               charger_type,
               available_slots,
               price,
               latitude,
               longitude
        FROM stations
    """)

    stations = cursor.fetchall()

    nearby_stations = []

    from math import radians, sin, cos, sqrt, atan2

    for station in stations:

        if station[6] is None or station[7] is None:
            continue

        station_lat = float(station[6])
        station_lon = float(station[7])

        R = 6371

        dlat = radians(station_lat - latitude)
        dlon = radians(station_lon - longitude)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(latitude))
            * cos(radians(station_lat))
            * sin(dlon / 2) ** 2
        )

        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        if distance <= 10:

            nearby_stations.append({
                'station_name': station[0],
                'city': station[1],
                'address': station[2],
                'charger_type': station[3],
                'available_slots': station[4],
                'price': station[5],
                'distance': round(distance, 2)
            })

    nearby_stations.sort(key=lambda x: x['distance'])

    return render_template(
        'nearby_stations.html',
        stations=nearby_stations
    )

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/search_stations', methods=['GET', 'POST'])
def search_stations():

    stations = []

    if request.method == 'POST':

        city = request.form.get('city', '').strip()

        if city:
            cursor.execute("""
                SELECT id,
                       station_name,
                       city,
                       address,
                       charger_type,
                       available_slots,
                       price
                FROM stations
                WHERE city LIKE %s
                ORDER BY station_name
            """, ('%' + city + '%',))

            stations = cursor.fetchall()

        else:
            flash("Please enter a city.")

    else:

        cursor.execute("""
            SELECT id,
                   station_name,
                   city,
                   address,
                   charger_type,
                   available_slots,
                   price
            FROM stations
            ORDER BY station_name
        """)

        stations = cursor.fetchall()

    return render_template(
        'search_stations.html',
        stations=stations
    )

@app.route('/features')
def features():
    return render_template('features.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        cursor.execute("""
            INSERT INTO contact_messages
            (name, subject, message)
            VALUES (%s, %s, %s)
        """, (name, subject, message))

        db.commit()

        flash("Thank you! Your message has been sent successfully.")

        return redirect(url_for('contact'))

    return render_template('contact.html')



@app.route('/contact_messages')
def contact_messages():

    cursor.execute("""
        SELECT message_id, name, subject, message, created_at
        FROM contact_messages
        ORDER BY created_at DESC
    """)

    messages = cursor.fetchall()

    return render_template(
        'contact_messages.html',
        messages=messages
    )

if __name__ == '__main__':

    app.run(
        debug=True
    )