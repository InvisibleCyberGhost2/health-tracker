from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime
import logging
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', '3a928948ef40444b2b9f8c11d341c6ea')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Firebase Admin SDK
try:
    # Use environment variables for Firebase config
    firebase_config = {
        "type": os.environ.get("FIREBASE_TYPE"),
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        "auth_uri": os.environ.get("FIREBASE_AUTH_URI"),
        "token_uri": os.environ.get("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT_URL"),
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL")
    }
    
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.debug("Firestore initialized successfully!")
except Exception as e:
    logging.error(f"Error initializing Firebase: {e}")

# ──────── HELPER FUNCTIONS ────────
def get_current_user_data():
    """Get current user's data from Firestore"""
    if 'user_id' not in session:
        return None
    
    try:
        user_ref = db.collection('users').document(session['user_id'])
        user_data = user_ref.get().to_dict()
        return user_data
    except Exception as e:
        logging.error(f"Error getting user data: {e}")
        return None

def add_health_data(user_id, date, weight, water, steps):
    """Add health metrics to Firestore"""
    try:
        health_data = {
            'user_id': user_id,
            'date': date,
            'weight': float(weight),
            'water': int(water),
            'steps': int(steps),
            'timestamp': datetime.now()
        }
        db.collection('health').add(health_data)
        return True
    except Exception as e:
        logging.error(f"Error adding health data: {e}")
        return False

def add_exercise_data(user_id, date, activity_type, duration, calories_burned, notes):
    """Add exercise log to Firestore"""
    try:
        exercise_data = {
            'user_id': user_id,
            'date': date,
            'activity_type': activity_type,
            'duration': float(duration),
            'calories_burned': float(calories_burned),
            'notes': notes,
            'timestamp': datetime.now()
        }
        db.collection('exercise_logs').add(exercise_data)
        return True
    except Exception as e:
        logging.error(f"Error adding exercise data: {e}")
        return False

def add_meal_data(user_id, date, meal_type, calories, protein, fat, carbs, notes):
    """Add meal log to Firestore"""
    try:
        meal_data = {
            'user_id': user_id,
            'date': date,
            'meal_type': meal_type,
            'calories': float(calories),
            'protein': float(protein),
            'fat': float(fat),
            'carbs': float(carbs),
            'notes': notes,
            'timestamp': datetime.now()
        }
        db.collection('meal_logs').add(meal_data)
        return True
    except Exception as e:
        logging.error(f"Error adding meal data: {e}")
        return False

def add_sleep_data(user_id, date, bed_time, wake_up_time):
    """Add sleep log to Firestore"""
    try:
        sleep_data = {
            'user_id': user_id,
            'date': date,
            'bed_time': bed_time,
            'wake_up_time': wake_up_time,
            'timestamp': datetime.now()
        }
        db.collection('sleep_logs').add(sleep_data)
        return True
    except Exception as e:
        logging.error(f"Error adding sleep data: {e}")
        return False

def generate_feedback(summaries, sleep_logs):
    """Generate user feedback based on their data"""
    feedback = {}
    
    # Sleep feedback
    if sleep_logs:
        latest_sleep = sleep_logs[-1]
        if 'bed_time' in latest_sleep and 'wake_up_time' in latest_sleep:
            try:
                bed_time = datetime.strptime(latest_sleep['bed_time'], '%H:%M:%S')
                wake_time = datetime.strptime(latest_sleep['wake_up_time'], '%H:%M:%S')
                duration = (wake_time - bed_time).total_seconds() / 3600
                feedback['sleep'] = "Great sleep!" if duration >= 7 else "Try to get more sleep."
            except ValueError:
                feedback['sleep'] = "Check your sleep times format."
    
    # Hydration feedback
    avg_water = summaries['health']['water'] / max(1, len(sleep_logs)) if sleep_logs else 0
    feedback['water'] = "Well hydrated!" if avg_water >= 8 else "Drink more water daily."
    
    # Activity feedback
    avg_steps = summaries['health']['steps'] / max(1, len(sleep_logs)) if sleep_logs else 0
    feedback['steps'] = "Very active!" if avg_steps >= 10000 else "Try to walk more."
    
    return feedback

# ──────── ROUTES ────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        age = int(request.form['age'])
        gender = request.form['gender']

        try:
            # Create Firebase auth user
            user = auth.create_user(
                email=email,
                password=password
            )
            
            # Create user document in Firestore
            user_ref = db.collection('users').document(user.uid)
            user_ref.set({
                'email': email,
                'full_name': full_name,
                'age': age,
                'gender': gender,
                'weight_goal': 0.0,
                'join_date': datetime.now()
            })
            
            logging.debug(f"User registered: {email}")
            return redirect(url_for('login'))
        
        except auth.EmailAlreadyExistsError:
            logging.error(f"Email already exists: {email}")
            return render_template('register.html', error="Email already exists.")
        except Exception as e:
            logging.error(f"Registration error: {e}")
            return render_template('register.html', error="Registration failed. Please try again.")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            # In production, use Firebase client-side auth
            # This is simplified for demonstration
            user = auth.get_user_by_email(email)
            
            # Verify password (in production, this would be handled client-side)
            # Here we just check if user exists
            session['user_id'] = user.uid
            session['email'] = email
            logging.debug(f"User logged in: {email}")
            return redirect(url_for('dashboard'))
        
        except auth.UserNotFoundError:
            logging.debug("User not found")
            return render_template('index.html', error="Invalid email or password.")
        except Exception as e:
            logging.error(f"Login error: {e}")
            return render_template('index.html', error="Login failed. Please try again.")

    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_data = get_current_user_data()
    
    if not user_data:
        return redirect(url_for('logout'))

    # Initialize summary data
    summaries = {
        'health': {'weight': 0, 'water': 0, 'steps': 0},
        'exercise': {'calories_burned': 0, 'duration': 0},
        'meals': {'count': 0, 'calories': 0}
    }
    
    try:
        # Health data
        health_docs = db.collection('health').where('user_id', '==', user_id).stream()
        health_records = []
        for doc in health_docs:
            data = doc.to_dict()
            health_records.append(data)
            summaries['health']['weight'] += data.get('weight', 0)
            summaries['health']['water'] += data.get('water', 0)
            summaries['health']['steps'] += data.get('steps', 0)
        
        # Exercise data
        exercise_docs = db.collection('exercise_logs').where('user_id', '==', user_id).stream()
        exercise_logs = []
        for doc in exercise_docs:
            data = doc.to_dict()
            exercise_logs.append(data)
            summaries['exercise']['calories_burned'] += data.get('calories_burned', 0)
            summaries['exercise']['duration'] += data.get('duration', 0)
        
        # Meal data
        meal_docs = db.collection('meal_logs').where('user_id', '==', user_id).stream()
        meal_logs = []
        for doc in meal_docs:
            data = doc.to_dict()
            meal_logs.append(data)
            summaries['meals']['calories'] += data.get('calories', 0)
            summaries['meals']['count'] += 1
        
        # Sleep data
        sleep_docs = db.collection('sleep_logs').where('user_id', '==', user_id).stream()
        sleep_logs = [doc.to_dict() for doc in sleep_docs]
        
    except Exception as e:
        logging.error(f"Error fetching dashboard data: {e}")
        return render_template('error.html', message="An error occurred while loading your dashboard.")

    # Generate feedback
    feedback = generate_feedback(summaries, sleep_logs)
    
    return render_template('dashboard.html',
        email=session.get('email'),
        user_name=user_data.get('full_name'),
        join_date=user_data.get('join_date').strftime('%Y-%m-%d') if user_data.get('join_date') else 'N/A',
        weight_goal=user_data.get('weight_goal', 0),
        summaries=summaries,
        feedback=feedback,
