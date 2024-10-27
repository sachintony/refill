from crypt import methods

import requests
from flask import Flask, jsonify, request, session, render_template, flash, url_for, redirect
import mysql.connector
from mysql.connector import Error


app = Flask(__name__)
app.template_folder = "templates"
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# MySQL connection details
db_config = {
    'host': '127.0.0.1',
    'user': 'main',
    'password': 'easypassword',
    'database': 'REFILLNEW'
}


def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print("Database connected successfully.")
            return conn
        else:
            print("Failed to connect to the database.")
            return None
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


@app.route('/index_for_users')
def index_for_users():
    conn = get_db_connection()
    if conn:
        # Perform some database query if needed
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users LIMIT 5;")
        users = cursor.fetchall()
        cursor.close()
        conn.close()

        # Return data as part of the response
        return jsonify(users)
    else:
        return "Database connection failed", 500

@app.route('/index_for_vehicles')
def index_for_vehicles():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vehicles LIMIT 5;")
        vehicles = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(vehicles)
    else:
        return "Database connection failed", 500


def send_otp(mobile_number):
    url = f"https://cpaas.messagecentral.com/verification/v3/send?countryCode=91&customerId=C-E414ED19519F4B5&flowType=SMS&mobileNumber={mobile_number}"

    headers = {
        'authToken': 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJDLUU0MTRFRDE5NTE5RjRCNSIsImlhdCI6MTcyNzE2MzA0NiwiZXhwIjoxODg0ODQzMDQ2fQ.3Ad_x0tfA49yRXs9KcYnPOOjfZ-O6jzntaydYWM8z5cxDWRFal8pxRVvj4ITPLMIwZgisG5X_PGByMWvRXOrQg'
        # Replace with your actual auth token
    }

    response = requests.post(url, headers=headers)

    print(f"Sending OTP to {mobile_number}: {response.status_code}, Response: {response.text}")

    if response.status_code == 200:
        try:
            response_data = response.json()

            # The 'verificationId' is inside the 'data' object
            data = response_data.get('data')
            if data:
                verification_id = data.get('verificationId')
                if verification_id:
                    return verification_id
                else:
                    print("Verification ID not found in 'data'.")
                    return None
            else:
                print("No 'data' object in the response.")
                return None
        except ValueError:
            print("Failed to parse JSON response.")
            return None
    else:
        print(f"Failed to send OTP, status code: {response.status_code}")
        return None

# Route to handle mobile number submission and OTP sending
@app.route('/submit_mobile', methods=['POST'])
def submit_mobile():
    data = request.get_json()  # Get the JSON data from the request
    if not data or 'mobile_number' not in data:
        return jsonify({"status": "error", "message": "Mobile number is required."}), 400

    mobile_number = data['mobile_number']  # Extract the mobile number
    print(f"Received mobile number: {mobile_number}")

    # Validate mobile number
    if not mobile_number or len(mobile_number) != 10 or not mobile_number.isdigit():
        return jsonify({"status": "error", "message": "Invalid mobile number."}), 400

    # Send the OTP and get verification ID
    verification_id = send_otp(mobile_number)

    if not verification_id:
        return jsonify({"status": "error", "message": "Failed to send OTP."}), 500

    # Store verification ID in the session
    session['verification_id'] = verification_id
    session['mobile_number'] = mobile_number  # Store mobile number as well

    # Return a success response in JSON format
    return jsonify({"status": "success", "message": "OTP sent successfully."}), 200


# Route to handle OTP verification (verification_id is handled in the backend)
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    mobile_number = session.get('mobile_number')  # Retrieve mobile number from session
    verification_id = session.get('verification_id')  # Retrieve verification ID from session

    if not mobile_number or not verification_id:
        return jsonify({"status": "error", "message": "No mobile number or verification ID found in session."}), 400

    # Get JSON data from the request (OTP sent by frontend)
    data = request.get_json()
    if not data or 'otp' not in data:
        return jsonify({"status": "error", "message": "OTP is required."}), 400

    otp = data['otp']  # Extract OTP from the request

    # Validate the OTP using stored verification ID
    otp_validation_response = validate_otp(mobile_number, verification_id, otp)

    if otp_validation_response['status'] == "success":
        return jsonify(otp_validation_response), 200
    else:
        return jsonify({"status": "error", "message": otp_validation_response.get("message", "Failed to verify OTP.")}), 400


# Function to validate the OTP
def validate_otp(mobile_number, verification_id, code):
    url = f"https://cpaas.messagecentral.com/verification/v3/validateOtp?countryCode=91&mobileNumber={mobile_number}&verificationId={verification_id}&customerId=C-E414ED19519F4B5&code={code}"

    headers = {
        'authToken': 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJDLUU0MTRFRDE5NTE5RjRCNSIsImlhdCI6MTcyNzE2MzA0NiwiZXhwIjoxODg0ODQzMDQ2fQ.3Ad_x0tfA49yRXs9KcYnPOOjfZ-O6jzntaydYWM8z5cxDWRFal8pxRVvj4ITPLMIwZgisG5X_PGByMWvRXOrQg'  # Replace with your actual auth token
    }

    response = requests.get(url, headers=headers)

    print(f"Validating OTP for {mobile_number}: {response.status_code}, Response: {response.text}")

    if response.status_code == 200:
        return {"status": "success", "message": "OTP verified successfully!"}
    else:
        return {"status": "error", "message": response.json()}
import hashlib
import base64
# Function to hash Aadhaar using SHA-256
def hash_aadhaar(aadhaar_number):
    return hashlib.sha256(aadhaar_number.encode()).hexdigest()

# Function to "encode" Aadhaar (simulates reversible hashing, but insecure)
def encode_aadhaar(aadhaar_number):
    aadhaar_bytes = aadhaar_number.encode('utf-8')
    encoded_aadhaar = base64.b64encode(aadhaar_bytes)
    return encoded_aadhaar.decode('utf-8')

# Function to "decode" encoded Aadhaar (simulates reverse hashing)
def decode_aadhaar(encoded_aadhaar):
    decoded_bytes = base64.b64decode(encoded_aadhaar.encode('utf-8'))
    return decoded_bytes.decode('utf-8')
@app.route('/register_users', methods=['POST'])
def register_users():
    if request.method == 'POST':
        # Get JSON data from request
        data = request.get_json()
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        mobile_number = data.get('mobile_number')
        aadhaar_card_number = data.get('aadhaar_card_number')  # Sensitive data
        address = data.get('address')

        # Validate incoming data
        if not first_name or not last_name or not mobile_number or not aadhaar_card_number:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Hash the Aadhaar card number using SHA-256
        hashed_aadhaar = hash_aadhaar(aadhaar_card_number)

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                # Check if the Aadhaar card number already exists in the database
                cursor.execute("SELECT * FROM users WHERE aadhaar_card_number = %s", (hashed_aadhaar,))
                user_exists = cursor.fetchone()

                # Insert user details into the database
                cursor.execute(
                    "INSERT INTO users (first_name, last_name, mobile_number, aadhaar_card_number, address) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (first_name, last_name, mobile_number, hashed_aadhaar, address)
                )
                conn.commit()  # Commit the transaction

                # Get the UID of the newly inserted user
                cursor.execute("SELECT LAST_INSERT_ID();")
                uid = cursor.fetchone()[0]  # Fetch the last inserted ID (UID)
                print("User registered successfully.")
            except Error as e:
                print(f"Error inserting data into users table: {e}")
                conn.rollback()  # Rollback in case of error
                return jsonify({"status": "error", "message": "Database error"}), 500
            finally:
                cursor.close()
                conn.close()

            # Return the UID in the success response
            return jsonify({
                "status": "success",
                "message": "User registered successfully",
                "uid": str(uid)
            }), 201
        else:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500

@app.route('/check_user', methods=['POST'])
def check_if_user_exists():
    if request.method == 'POST':
        # Get JSON data from request
        data = request.get_json()
        mobile_number = data.get('mobile_number')

        # Validate mobile number
        if not mobile_number:
            return jsonify({"status": "error", "message": "Mobile number is required"}), 400

        # Establish a database connection
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(buffered=True)  # Use buffered cursor to fetch all results immediately
            try:
                # Query to check if the mobile number exists
                cursor.execute("SELECT * FROM users WHERE mobile_number = %s", (mobile_number,))
                user = cursor.fetchone()  # Fetch the result

                # If user exists, return an "exists" message
                if user:
                    return jsonify({"status": "exists", "message": "Mobile number already registered"}), 200
                else:
                    return jsonify({"status": "not_found", "message": "Mobile number not found"}), 404

            except Error as e:
                print(f"Database error: {e}")
                return jsonify({"status": "error", "message": "Database error"}), 500
            finally:
                cursor.close()
                conn.close()
        else:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500

@app.route('/register_vehicles', methods=['POST'])
def register_vehicles():
    if request.method == 'POST':
        try:
            # Get JSON data from request
            data = request.get_json()
            vehicle_number = data.get('vehicle_number')
            vehicle_color = data.get('vehicle_color')
            vehicle_type = data.get('vehicle_type')
            chassis_number = data.get('chassis_number')
            fuel_type = data.get('fuel_type')
            vehicle_make_and_model = data.get('vehicle_make_and_model')
            mobile_number = data.get('user_mobile_number')  # Ensure this key matches the frontend
            uid = data.get('uid')

            # Establish database connection
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(buffered=True)

                # Fetch user by mobile number
                cursor.execute("SELECT id FROM users WHERE mobile_number = %s", (mobile_number,))
                user = cursor.fetchone()

                if not user:  # If no user is found
                    return jsonify({"status": "error", "message": "Mobile number not registered"}), 404

                # Now you can directly use the uid from the request
                # Optional UID matching
                '''if uid != user[0]:  # Ensure the uid corresponds to the mobile number
                    return jsonify({"status": "error", "message": "UID does not match the user associated with this mobile number"}), 403'''

                # Insert vehicle details
                try:
                    cursor.execute(
                        "INSERT INTO vehicles (vehicle_number, chassis_number, vehicle_type, fuel_type, vehicle_make_and_model, vehicle_color, uid, mobile_number) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (vehicle_number, chassis_number, vehicle_type, fuel_type, vehicle_make_and_model, vehicle_color, uid, mobile_number)
                    )
                    conn.commit()

                    # Get the Vehicle ID
                    cursor.execute("SELECT LAST_INSERT_ID();")
                    vehicle_id = cursor.fetchone()[0]

                    return jsonify({"status": "success", "message": "Vehicle registered successfully", "vehicle_id": vehicle_id}), 201

                except Exception as e:
                    print(f"Error inserting data into vehicles table: {e}")
                    conn.rollback()
                    return jsonify({"status": "error", "message": f"Database error: {e}"}), 500

                finally:
                    cursor.close()
                    conn.close()
            else:
                return jsonify({"status": "error", "message": "Database connection failed"}), 500

        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({"status": "error", "message": f"Server error: {e}"}), 500



@app.route('/get_user_details', methods=['POST'])
def get_user_details():
    data = request.get_json()
    mobile_number = data.get('mobile_number')

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Fetch user details based on mobile number
            cursor.execute("SELECT * FROM users WHERE mobile_number = %s", (mobile_number,))
            user_details = cursor.fetchone()  # Fetch the result

            if not user_details:
                return jsonify({"status": "error", "message": "User not found."}), 404

            return jsonify({
                "status": "success",
                "user_details": user_details
            }), 200

        except mysql.connector.Error as e:
            print(f"Database error: {e}")  # Print the full database error for debugging
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


@app.route('/get_vehicle_details', methods=['POST'])
def get_vehicle_details():
    data = request.get_json()
    mobile_number = data.get('mobile_number')

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Fetch vehicle details based on mobile number
            cursor.execute("""SELECT * FROM vehicles WHERE mobile_number = %s""", (mobile_number,))
            vehicle_details = cursor.fetchall()  # Fetch all vehicle details

            if not vehicle_details:
                return jsonify({"status": "error", "message": "Vehicle details not found."}), 404

            return jsonify({
                "status": "success",
                "vehicle_details": vehicle_details
            }), 200

        except mysql.connector.Error as e:
            print(f"Database error: {e}")  # Print the full database error for debugging
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


@app.route('/insert_order', methods=['POST'])
def insert_order():
    data = request.get_json()

    # Extract data from the request JSON
    fuel_quantity = data.get('FuelQuantity')
    fuel_type = data.get('FuelType')
    mobile_number = data.get('MobileNumber')
    ordered_from = data.get('OrderedFrom')
    ordered_to_lat = data.get('OrderedToLat')
    ordered_to_long = data.get('OrderedToLong')
    price = data.get('Price')

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Insert the data into the FuelOrders table
            insert_query = """
            INSERT INTO FuelOrders (FuelQuantity, FuelType, MobileNumber, OrderedFrom, OrderedToLat, OrderedToLong, Price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
            fuel_quantity, fuel_type, mobile_number, ordered_from, ordered_to_lat, ordered_to_long, price))
            conn.commit()  # Commit the transaction

            cursor.close()  # Close the cursor
            conn.close()  # Close the connection

            return jsonify({"status": "success", "message": "Order inserted successfully"}), 201

        except mysql.connector.Error as e:
            print(f"Database error: {e}")  # Print the database error for debugging
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

@app.route('/get_orders', methods=['POST'])
def get_orders():
    # Get JSON data from the request
    data = request.get_json()
    mobile_number = data.get('MobileNumber')

    # Check if mobile_number is provided
    if not mobile_number:
        return jsonify({"status": "error", "message": "Mobile number is required."}), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # Fetch all orders for the specified mobile number, excluding SerialNumber
            select_query = """
            SELECT FuelQuantity, FuelType, MobileNumber, OrderedFrom, OrderedToLat, OrderedToLong, Price
            FROM FuelOrders
            WHERE MobileNumber = %s
            """
            cursor.execute(select_query, (mobile_number,))  # Use parameterized query to prevent SQL injection
            orders = cursor.fetchall()  # Fetch all order details

            cursor.close()  # Close the cursor
            conn.close()    # Close the connection

            if not orders:
                return jsonify({"status": "error", "message": "No orders found."}), 404

            return jsonify({
                "status": "success",
                "orders": orders
            }), 200

        except mysql.connector.Error as e:
            print(f"Database error: {e}")  # Print the full database error for debugging
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


# Route to delete a vehicle by vehicle_number
@app.route('/delete_vehicle', methods=['POST'])
def delete_vehicle():
    data = request.get_json()
    vehicle_number = data.get('vehicle_number')

    # Check if vehicle_number is provided
    if not vehicle_number:
        return jsonify({"status": "error", "message": "Vehicle number is required."}), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()

            # Delete vehicle based on vehicle_number
            delete_query = "DELETE FROM vehicles WHERE vehicle_number = %s"
            cursor.execute(delete_query, (vehicle_number,))
            conn.commit()

            cursor.close()
            conn.close()

            # Check if any row was deleted
            if cursor.rowcount == 0:
                return jsonify({"status": "error", "message": "Vehicle not found."}), 404

            return jsonify({"status": "success", "message": "Vehicle deleted successfully."}), 200

        except mysql.connector.Error as e:
            print(f"Database error: {e}")
            return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)