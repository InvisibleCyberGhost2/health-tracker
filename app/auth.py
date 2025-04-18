from flask import Blueprint, request, redirect, session, url_for, render_template
import pyrebase
import logging
from datetime import datetime

# Initialize Firebase
firebase_config = {
    "apiKey": "AIzaSyATI6NWXJSD_T-n_FGqAFDcI4KwuQkMxSY",
    "authDomain": "health-care-tracker-3af6a.firebaseapp.com",
    "databaseURL": "https://health-care-tracker-3af6a-default-rtdb.firebaseio.com",
    "projectId": "health-care-tracker-3af6a",
    "storageBucket": "health-care-tracker-3af6a.appspot.com",
    "messagingSenderId": "1076548808106",
    "appId": "1:1076548808106:web:6f3b8d903e8ad824df0fd3",
    "measurementId": "G-ZY6M7TYFMT"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        age = int(request.form['age'])
        gender = request.form['gender']
        user_image = request.form.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')  # Default image

        try:
            # Create user account
            user = auth.create_user_with_email_and_password(email, password)
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]
            session["name"] = full_name
            session["user_image"] = user_image  # Store user image in session

            # Save user data
            data = {
                "name": full_name,
                "email": email,
                "age": age,
                "gender": gender,
                "user_image": user_image,  # Save user image in database
                "weight_goal": 0.0,
                "join_date": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            }
            db.child("users").child(session["uid"]).set(data)

            logging.debug(f"User registered: {email}")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            return f"Error registering user: {e}"

    return render_template('register.html')


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            # Authenticate user
            user = auth.sign_in_with_email_and_password(email, password)
            session["is_logged_in"] = True
            session["email"] = user["email"]
            session["uid"] = user["localId"]

            # Fetch user data
            user_data = db.child("users").child(session["uid"]).get().val()
            if user_data:
                session["name"] = user_data["name"]
                session["user_image"] = user_data.get("user_image", 'https://randomuser.me/api/portraits/women/44.jpg')  # Default image
                # Update last login time
                db.child("users").child(session["uid"]).update({
                    "last_logged_in": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                })
            else:
                session["name"] = "User"
                session["user_image"] = 'https://randomuser.me/api/portraits/women/44.jpg'  # Default image

            logging.debug(f"User logged in: {email}")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            logging.error(f"Invalid email or password: {e}")
            return f"Invalid email or password: {e}"

    return render_template('login.html')


@auth_blueprint.route('/logout')
def logout():
    # Update last logout time
    if "uid" in session:
        db.child("users").child(session["uid"]).update({
            "last_logged_out": datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        })
    session.clear()
    return redirect(url_for('auth.login'))


