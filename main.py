from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import uuid
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
import requests

# Create the application instance
app = Flask(__name__)
app.secret_key = uuid.uuid4().hex

load_dotenv()

# Connect to the database
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Register the UK_DATE function for this connection
    def uk_date():
        return datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    conn.create_function('UK_DATE', 0, uk_date)
    
    return conn

def is_logged_in():
    print("Checking login status:", 'user_id' in session)  # Debug line
    return 'user_id' in session

def is_admin():
    if not is_logged_in():
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    print("Checking admin status:", user['admin'])  # Debug line
    
    return user['admin']

@app.route('/')
def index():
    return render_template('index.html', is_logged_in=is_logged_in)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        flash('You are already logged in', 'success')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Collecting form data
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirmPassword = request.form['confirmPassword']

            # Checking if passwords match
            if password != confirmPassword:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('register'))

            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Checking if email is already registered
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Email already registered. Please use a different email or log in.', 'danger')
                conn.close()
                return redirect(url_for('register'))

            # Hashing password and inserting user data into database
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, hashed_password))
            conn.commit()
            conn.close()
            
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login'))
        
        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html', is_logged_in=is_logged_in)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        flash('You are already logged in', 'success')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Collecting form data
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        # Checking if user exists and password is correct
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('You are now logged in', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
            return redirect(url_for('login'))
        
    return render_template('login.html', is_logged_in=is_logged_in)

@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')

    return redirect(url_for('index'))

@app.route('/account', methods=['GET', 'POST'])
def account():
    if not is_logged_in():
        flash('Please log in to view your account', 'danger')
        return redirect(url_for('login'))
    
    show_account_details = True
    show_booking_details = False
    show_admin_panel = False
    show_delete_confirmation = False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    # Collect user data
    user_username = user['username']
    user_email = user['email']
    user_date_joined = user['created_at']
    
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user wants to delete account
        if 'show_delete_confirmation' in request.form:
            show_delete_confirmation = True
        
        # Delete account
        if 'delete_account' in request.form:
            cursor.execute('DELETE FROM users WHERE id = ?', (session['user_id'],))
            conn.commit()
            conn.close()
            session.clear()
            flash('Account deleted successfully', 'success')
            return redirect(url_for('index'))
        
        # Account details
        elif 'account_details' in request.form:
            return render_template('account.html',
                                   is_logged_in=is_logged_in,
                                   is_admin=is_admin(),
                                   user_username=user_username,
                                   user_email=user_email,
                                   user_date_joined=user_date_joined,
                                   show_account_details=True,
                                   show_booking_details=False,
                                   show_admin_panel=False,
                                   show_delete_confirmation=show_delete_confirmation
                                   )
        
        # Enable edit mode
        elif 'enable_edit_mode' in request.form:
            edit_mode = True
            return render_template('account.html',
                                is_logged_in=is_logged_in,
                                is_admin=is_admin(),
                                user_username=user_username,
                                user_email=user_email,
                                user_date_joined=user_date_joined,
                                show_account_details=True,
                                show_booking_details=False,
                                show_admin_panel=False,
                                edit_mode=edit_mode,
                                show_delete_confirmation=show_delete_confirmation
                                )

        # Cancel edit mode
        elif 'cancel_edit' in request.form:
            return redirect(url_for('account'))

        # Save profile changes
        elif 'save_profile' in request.form:
            username = request.form['username']
            email = request.form['email']
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect', 'danger')
                edit_mode = True
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=username,
                                    user_email=email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=True,
                                    show_booking_details=False,
                                    show_admin_panel=False,
                                    edit_mode=edit_mode,
                                    show_delete_confirmation=show_delete_confirmation
                                    )
            
            # Check if username is already in use
            cursor.execute('SELECT * FROM users WHERE username = ? AND id != ?', (username, session['user_id']))
            existing_username = cursor.fetchone()
            if existing_username:
                flash('Username is already in use by another account', 'danger')
                edit_mode = True
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=username,
                                    user_email=email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=True,
                                    show_booking_details=False,
                                    show_admin_panel=False,
                                    edit_mode=edit_mode,
                                    show_delete_confirmation=show_delete_confirmation
                                    )

            # Check if email is already in use
            cursor.execute('SELECT * FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
            existing_email = cursor.fetchone()
            if existing_email:
                flash('Email is already in use by another account', 'danger')
                edit_mode = True
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=username,
                                    user_email=email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=True,
                                    show_booking_details=False,
                                    show_admin_panel=False,
                                    edit_mode=edit_mode,
                                    show_delete_confirmation=show_delete_confirmation
                                    )
            
            cursor.execute('UPDATE users SET username = ?, email = ?, updated_at = UK_DATE() WHERE id = ?',
                        (username, email, session['user_id']))
            
            # Update password if new password is provided
            if new_password:
                if new_password != confirm_password:
                    flash('New password and confirmation do not match', 'danger')
                    edit_mode = True
                    return render_template('account.html',
                                        is_logged_in=is_logged_in,
                                        is_admin=is_admin(),
                                        user_username=username,
                                        user_email=email,
                                        user_date_joined=user_date_joined,
                                        show_account_details=True,
                                        show_booking_details=False,
                                        show_admin_panel=False,
                                        edit_mode=edit_mode,
                                        show_delete_confirmation=show_delete_confirmation
                                        )
                
                hashed_password = generate_password_hash(new_password)
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, session['user_id']))
            
            conn.commit()
            session['username'] = username
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('account'))
        
        # Booking details
        elif 'booking_details' in request.form:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC',
                        (session['user_id'],))
            bookings = cursor.fetchall()
            conn.close()
            
            return render_template('account.html',
                                   is_logged_in=is_logged_in,
                                   is_admin=is_admin(),
                                   user_username=user_username,
                                   user_email=user_email,
                                   user_date_joined=user_date_joined,
                                   show_account_details=False,
                                   show_booking_details=True,
                                   show_admin_panel=False,
                                   bookings=bookings,
                                   show_delete_confirmation=show_delete_confirmation
                                   )
        
        # Cancel booking
        elif 'cancel_booking' in request.form:
            booking_id = request.form['booking_id']
            cursor.execute('DELETE FROM bookings WHERE id = ? AND user_id = ?', 
                        (booking_id, session['user_id']))
            conn.commit()
            conn.close()
            flash('Booking cancelled successfully', 'success')
            return redirect(url_for('account'))
        
        # Admin panel
        elif 'admin_panel' in request.form:
            if is_admin():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
                users = cursor.fetchall()
                cursor.execute('SELECT * FROM bookings ORDER BY created_at DESC')
                bookings = cursor.fetchall()
                conn.close()
                
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=user_username,
                                    user_email=user_email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=False,
                                    show_booking_details=False,
                                    show_admin_panel=True,
                                    users=users,
                                    bookings=bookings,
                                    view_users=False,  # Default to showing bookings
                                    show_delete_confirmation=show_delete_confirmation
                                    )
            else:
                flash('You do not have permission to access the admin panel', 'danger')
                return redirect(url_for('account'))
        
        # View users
        elif 'enable_view_users' in request.form:
            if is_admin():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id != ? ORDER BY created_at DESC', (session['user_id'],))
                users = cursor.fetchall()
                conn.close()
                
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=user_username,
                                    user_email=user_email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=False,
                                    show_booking_details=False,
                                    show_admin_panel=True,
                                    users=users,
                                    view_users=True,
                                    show_delete_confirmation=show_delete_confirmation
                                    )

        # View bookings
        elif 'enable_view_bookings' in request.form:
            if is_admin():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookings ORDER BY created_at DESC')
                bookings = cursor.fetchall()
                conn.close()
                
                return render_template('account.html',
                                    is_logged_in=is_logged_in,
                                    is_admin=is_admin(),
                                    user_username=user_username,
                                    user_email=user_email,
                                    user_date_joined=user_date_joined,
                                    show_account_details=False,
                                    show_booking_details=False,
                                    show_admin_panel=True,
                                    bookings=bookings,
                                    view_users=False,
                                    show_delete_confirmation=show_delete_confirmation
                                    )
        
        # Update user permissions
        elif 'update_user_permissions' in request.form:
            user_id = request.form['user_id']
            new_permissions = request.form['new_permissions']
            
            if is_admin():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET admin = ?, updated_at = UK_DATE() WHERE id = ?', 
                            (new_permissions, user_id))
                conn.commit()
                conn.close()
                flash('User permissions updated successfully', 'success')
            else:
                flash('You do not have permission to update user permissions', 'danger')
            
            return redirect(url_for('account'))
            
        # Update booking status
        elif 'update_booking_status' in request.form:
            booking_id = request.form['booking_id']
            new_status = request.form['new_status']
            
            if is_admin():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE bookings SET status = ?, updated_at = UK_DATE() WHERE id = ?', 
                            (new_status, booking_id))
                conn.commit()
                conn.close()
                flash('Booking status updated successfully', 'success')
            else:
                flash('You do not have permission to update booking status', 'danger')
            
            return redirect(url_for('account'))
            

    return render_template('account.html',
                        is_logged_in=is_logged_in,
                        is_admin=is_admin(),
                        user_username=user_username,
                        user_email=user_email,
                        user_date_joined=user_date_joined,
                        show_delete_confirmation=show_delete_confirmation
                        )

@app.route('/information')
def information():
    return render_template('information.html', is_logged_in=is_logged_in)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if not is_logged_in():
        flash('Please log in to proceed', 'danger')
        return redirect(url_for('login'))
    
    booking_stage = 1
    
    # Set stages based on form data
    if request.method == 'POST':
        if 'next_stage' in request.form:
            booking_stage = int(request.form['current_stage']) + 1
        elif 'prev_stage' in request.form:
            booking_stage = int(request.form['current_stage']) - 1

        # Clear data if user changes booking type
        if 'booking_type' in request.form and session.get('booking_booking_type') != request.form['booking_type']:
            session.pop('booking_solar_panels', None)
            session.pop('booking_additional_info', None)
            session.pop('booking_solar_panels_quantity', None)
            session.pop('booking_energy_management', None)
        
        if int(request.form['current_stage']) == 3:
            session.pop('booking_solar_panels', None)
            session.pop('booking_energy_management', None)

        for field in request.form:
            if field not in ['next_stage', 'prev_stage', 'current_stage']:
                if field == 'solar_panels' or field == 'energy_management':
                    session[f'booking_{field}'] = 'yes'
                else:
                    session[f'booking_{field}'] = request.form[field]
        
        # Check if user has selected at least one option for consultation or installation
        if int(request.form['current_stage']) == 3 and 'next_stage' in request.form:
            if session.get('booking_booking_type') == 'consultation':
                if not (session.get('booking_solar_panels') == 'yes' or session.get('booking_energy_management') == 'yes'):
                    flash('For consultation, please select at least one option (Solar Panels or Energy Management System)', 'danger')
                    booking_stage = 3
                    return render_template('booking.html', 
                                        is_logged_in=is_logged_in, 
                                        booking_stage=booking_stage,
                                        progress_percentage=booking_stage*20,
                                        today_date=(date.today() + timedelta(days=1)).isoformat()
                                        )   
                
            elif session.get('booking_booking_type') == 'installation':
                solar_panels_quantity = int(session.get('booking_solar_panels_quantity', 0))
                if not (solar_panels_quantity > 0 or session.get('booking_energy_management') == 'yes'):
                    flash('For installation, please select either solar panels (quantity greater than 0) or energy management system', 'danger')
                    booking_stage = 3 
                    return render_template('booking.html', 
                                        is_logged_in=is_logged_in, 
                                        booking_stage=booking_stage,
                                        progress_percentage=booking_stage*20,
                                        today_date=(date.today() + timedelta(days=1)).isoformat()
                                        )
    
    booking_stage = max(1, min(booking_stage, 5))
    progress_percentage = booking_stage * 20

    # Final stage: Submit booking
    if submit_booking := request.form.get('submit_booking'):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        session['booking_date'] = datetime.strptime(session['booking_date'], '%Y-%m-%d').strftime('%d/%m/%Y')

        try:
            cursor.execute('INSERT INTO bookings (user_id, full_name, address, phone_number, booking_type, solar_panels, solarpanel_amount, energy_management, additional_info, booking_date, booking_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (session['user_id'], session['booking_name'], session['booking_address'], session['booking_phone'], session['booking_booking_type'], session.get('booking_solar_panels', 'no'), session.get('booking_solarpanel_amount', 0),
                            session.get('booking_energy_management', 'no'), session.get('booking_additional_info', ''), session.get('booking_date'), session.get('booking_time')))
            conn.commit()
            conn.close()
            
            # Clear session data
            session.pop('booking_full_name', None)
            session.pop('booking_address', None)
            session.pop('booking_phone_number', None)
            session.pop('booking_booking_type', None)
            session.pop('booking_solar_panels', None)
            session.pop('booking_solarpanel_amount', None)
            session.pop('booking_energy_management', None)
            session.pop('booking_additional_info', None)
            session.pop('booking_date', None)
            session.pop('booking_time', None)
            
            flash('Booking successful', 'success')
            return redirect(url_for('index'))
        
        except sqlite3.IntegrityError as e:
            flash('You already have a booking on this date. Please choose a different date.', 'danger')
            booking_stage = 4
            progress_percentage = 80

        except sqlite3.Error as e:
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('booking'))
    
    return render_template('booking.html', 
                          is_logged_in=is_logged_in, 
                          booking_stage=booking_stage,
                          progress_percentage=progress_percentage,
                          today_date=(date.today() + timedelta(days=1)).isoformat()
                          )

@app.route('/carbon-footprint', methods=['GET', 'POST'])
def carbon_footprint():
    carbon_footprints = []
    calculated = False
    carbon_footprint = 0
    carbon_offset_cost_gbp = 0
    
    # If user is logged in, get their carbon footprint history
    if is_logged_in():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM carbon_footprints WHERE user_id = ? ORDER BY created_at DESC', 
                     (session['user_id'],))
        carbon_footprints = cursor.fetchall()
        conn.close()
    
    # Check if there are stored calculation results from a redirect
    if 'carbon_calculated' in session:
        calculated = True
        carbon_footprint = session.pop('carbon_footprint', 0)
        carbon_offset_cost_gbp = session.pop('carbon_offset_cost_gbp', 0)
        session.pop('carbon_calculated')
    
    if request.method == 'POST':
        try:
            # Check if there is a deletion request
            if 'remove_calculation' in request.form:
                cf_id = request.form['cf_id']
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM carbon_footprints WHERE id = ? AND user_id = ?', 
                            (cf_id, session['user_id']))
                conn.commit()
                conn.close()
                flash('Calculation result removed successfully', 'success')
                return redirect(url_for('energy_usage'))
                
            CARBON_API_KEY = os.getenv('CARBON_INTERFACE_API_KEY')
            
            # Get form data
            electricity = float(request.form['electricity'])
            gas = float(request.form['gas'])
            car_miles = float(request.form['car'])
            bus_miles = float(request.form['bus'])
            train_miles = float(request.form['train'])

            headers = {
                'Authorization': f'Bearer {CARBON_API_KEY}',
                'Content-Type': 'application/json'
            }

            carbon_footprint = 0
            api_success = True # Flag to check if all API calls were successful

            carbon_footprint += bus_miles * 0.03
            carbon_footprint += train_miles * 0.04

            # Electricity, Gas and Car API calls
            if electricity > 0:
                data = {
                    "type": "electricity",
                    "electricity_unit": "kwh",
                    "electricity_value": electricity,
                    "country": "gb"
                }

                response = requests.post('https://www.carboninterface.com/api/v1/estimates', headers=headers, json=data)
                print(f"Electricity API Response: {response.status_code} - {response.text}")
                if response.status_code == 201:
                    result = response.json()
                    carbon_footprint += result['data']['attributes']['carbon_kg']
                else:
                    api_success = False

            if gas > 0:
                data = {
                    "type": "fuel_combustion",
                    "fuel_source_type": "dfo", 
                    "fuel_source_unit": "btu",
                    "fuel_source_value": gas * 0.036 # Convert gas usage to BTU
                }

                response = requests.post('https://www.carboninterface.com/api/v1/estimates', headers=headers, json=data)
                print(f"Gas API Response: {response.status_code} - {response.text}")
                if response.status_code == 201:
                    result = response.json()
                    carbon_footprint += result['data']['attributes']['carbon_kg']
                else:
                    api_success = False

            if car_miles > 0:
                data = {
                    "type": "vehicle",
                    "distance_unit": "mi",
                    "distance_value": car_miles,
                    "vehicle_model_id": "14949244-b6d1-4a11-970f-73f75408f931" # Generic car model
                }

                response = requests.post('https://www.carboninterface.com/api/v1/estimates', headers=headers, json=data)
                print(f"Car API Response: {response.status_code} - {response.text}")
                if response.status_code == 201:
                    result = response.json()
                    carbon_footprint += result['data']['attributes']['carbon_kg']
                else:
                    api_success = False

            if not api_success or carbon_footprint == 0:
                    # Backup calculation
                    electricity_footprint = electricity * 0.233 
                    gas_footprint = gas * 2.03
                    car_footprint = car_miles * 0.404
                    bus_footprint = bus_miles * 0.103
                    train_footprint = train_miles * 0.037
                    
                    carbon_footprint = electricity_footprint + gas_footprint + car_footprint + bus_footprint + train_footprint

            carbon_offset_cost_gbp = carbon_footprint * 0.0117

            carbon_footprint = round(carbon_footprint, 2)
            carbon_offset_cost_gbp = round(carbon_offset_cost_gbp, 2)
            
            # Save to database if user is logged in
            if is_logged_in():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO carbon_footprints (user_id, electricity_usage, gas_usage, car_mileage, bus_mileage, train_mileage, carbon_footprint, carbon_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                            (session['user_id'], electricity, gas, car_miles, bus_miles, train_miles, carbon_footprint, carbon_offset_cost_gbp))
                conn.commit()
                conn.close()
            
            # Store calculation results in session for redirect
            session['carbon_footprint'] = carbon_footprint
            session['carbon_offset_cost_gbp'] = carbon_offset_cost_gbp
            session['carbon_calculated'] = True
            
            # Redirect to GET to prevent form resubmission on refresh
            return redirect(url_for('carbon_footprint'))
            
        except Exception as e:
            print(f"API Error: {str(e)}")
            # Backup calculation 
            electricity_footprint = float(request.form['electricity']) * 0.233 
            gas_footprint = float(request.form['gas']) * 2.03
            car_footprint = float(request.form['car']) * 0.404
            bus_footprint = float(request.form['bus']) * 0.103
            train_footprint = float(request.form['train']) * 0.037
            
            carbon_footprint = electricity_footprint + gas_footprint + car_footprint + bus_footprint + train_footprint
            carbon_offset_cost_gbp = carbon_footprint * 0.0117

            carbon_footprint = round(carbon_footprint, 2)
            carbon_offset_cost_gbp = round(carbon_offset_cost_gbp, 2)

            # Save to database if user is logged in
            if is_logged_in():
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO carbon_footprints (user_id, electricity_usage, gas_usage, car_mileage, bus_mileage, train_mileage, carbon_footprint, carbon_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                            (session['user_id'], request.form['electricity'], request.form['gas'], request.form['car'], request.form['bus'], request.form['train'], carbon_footprint, carbon_offset_cost_gbp))
                conn.commit()
                conn.close()
            
            # Store calculation results in session for redirect
            session['carbon_footprint'] = carbon_footprint
            session['carbon_offset_cost_gbp'] = carbon_offset_cost_gbp
            session['carbon_calculated'] = True
            
            # Redirect to GET to prevent form resubmission on refresh
            return redirect(url_for('carbon_footprint'))
    
    return render_template('carbon-footprint.html', 
                        is_logged_in=is_logged_in,
                        carbon_footprints=carbon_footprints,
                        carbon_footprint=carbon_footprint,
                        carbon_offset_cost_gbp=carbon_offset_cost_gbp,
                        calculated=calculated)

@app.route('/energy-usage', methods=['GET', 'POST'])
def energy_usage():
    energy_usage_calculations = []
    calculated = False
    electricity_usage = 0

    if is_logged_in():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM energy_usage_calculations WHERE user_id = ? ORDER BY created_at DESC', 
                     (session['user_id'],))
        energy_usage_calculations = cursor.fetchall()
        conn.close()
    
    # Check if there are stored calculation results from a redirect
    if 'energy_calculated' in session:
        calculated = True
        electricity_usage = session.pop('electricity_usage', 0)
        session.pop('energy_calculated')

    if request.method == 'POST':
        # Check if there is a deletion request
        if 'remove_calculation' in request.form:
            ec_id = request.form['ec_id']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM energy_usage_calculations WHERE id = ? AND user_id = ?', 
                        (ec_id, session['user_id']))
            conn.commit()
            conn.close()
            flash('Calculation result removed successfully', 'success')
            return redirect(url_for('energy_usage'))
        
        # Get form data
        occupants = int(request.form['occupants'])
        house_size = float(request.form['house_size'])
        num_appliances = int(request.form['appliances'])
        appliance_usage = int(request.form['hours'])
        heating_type = request.form['heating']

        # Calculate electricity usage based on all factors
        base_electricity = 100 
        occupant_factor = occupants * 30 
        size_factor = house_size * 0.5
        appliance_factor = num_appliances * appliance_usage * 0.1

        # Heating kWh factor
        if heating_type == 'electric':
            heating_factor = house_size * 1.2
        else:
            heating_factor = house_size * 0.3 

        # Calculate total electricity usage
        electricity_usage = base_electricity + occupant_factor + size_factor + appliance_factor + heating_factor
        electricity_usage = round(electricity_usage, 2)

        # Save calculation to database if logged in
        if is_logged_in():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO energy_usage_calculations (user_id, occupants, house_size, num_appliances, appliance_usage, heating_type, electricity_usage) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (session['user_id'], occupants, house_size, num_appliances, appliance_usage, heating_type, electricity_usage))
            conn.commit()
            conn.close()
        
        # Store calculation results in session for redirect
        session['electricity_usage'] = electricity_usage
        session['energy_calculated'] = True
        
        # Redirect to GET to prevent form resubmission on refresh
        return redirect(url_for('energy_usage'))

    return render_template('energy-usage.html', 
                      is_logged_in=is_logged_in,
                      energy_usage_calculations=energy_usage_calculations,
                      electricity_usage=electricity_usage,
                      calculated=calculated)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', is_logged_in=is_logged_in), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')