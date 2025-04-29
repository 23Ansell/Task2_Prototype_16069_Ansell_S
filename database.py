import sqlite3
from datetime import datetime

# Create a connection to the database
conn = sqlite3.connect('database.db')

# Register a function to format dates in UK format
def uk_date():
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')

conn.create_function('UK_DATE', 0, uk_date)

cursor = conn.cursor()

#cursor.execute('DROP TABLE IF EXISTS users')
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT (UK_DATE()),
    updated_at TIMESTAMP DEFAULT (UK_DATE()),
    UNIQUE(email)
)
''')

#cursor.execute('DROP TABLE IF EXISTS bookings')
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    booking_type TEXT NOT NULL,
    solar_panels TEXT,
    solarpanel_amount NUMBER,
    energy_management TEXT NOT NULL,
    additional_info TEXT,
    booking_date TIMESTAMP NOT NULL,
    booking_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT (UK_DATE()),
    updated_at TIMESTAMP DEFAULT (UK_DATE()),
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, booking_date)
)
''')

#cursor.execute('DROP TABLE IF EXISTS carbon_footprints')
cursor.execute('''
CREATE TABLE IF NOT EXISTS carbon_footprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    electricity_usage TEXT NOT NULL,
    gas_usage TEXT NOT NULL,
    car_mileage TEXT NOT NULL,
    bus_mileage TEXT NOT NULL,
    train_mileage TEXT NOT NULL,
    carbon_footprint TEXT NOT NULL,
    carbon_offset TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT (UK_DATE()),
    FOREIGN KEY (user_id) REFERENCES users (id)
)
''')

#cursor.execute('DROP TABLE IF EXISTS energy_usage_calculations')
cursor.execute('''
CREATE TABLE IF NOT EXISTS energy_usage_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    occupants NUMBER NOT NULL, 
    house_size NUMBER NOT NULL,
    num_appliances NUMBER NOT NULL,
    appliance_usage NUMBER NOT NULL,
    heating_type TEXT NOT NULL,
    electricity_usage NUMBER NOT NULL,
    created_at TIMESTAMP DEFAULT (UK_DATE()),
    FOREIGN KEY (user_id) REFERENCES users (id)              
)
''')

conn.commit()
conn.close()