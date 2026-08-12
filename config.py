import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="yashu020",
    database="ev_charging"
)

cursor = db.cursor()