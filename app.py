import os
from functools import wraps
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_wtf.csrf import CSRFProtect
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime
import logging

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-dev-only')
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are only sent over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate(os.environ.get('FIREBASE_CREDENTIALS_PATH', 'health-care-tracker-3af6a-firebase-adminsdk-fbsvc-d4a783a034.json'))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firestore initialized successfully!")
except Exception as e:
    logger.error(f"Error initializing Firebase: {e}")
    raise

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper Functions
def validate_user_input(data, required_fields):
    """Validate user input data"""
    errors = {}
    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field.replace('_', ' ').title()} is required"
    
    # Additional validations can be added here
    if 'email' in data and '@' not in data['email']:
        errors['email'] = "Invalid email format"
    
    if 'age' in data:
        try:
            age = int(data['age'])
            if age < 0 or age > 120:
                errors['age'] = "Age must be between 0 and 120"
        except ValueError:
            errors['age'] = "Age must be a number"
    
    return errors

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_user_input(form_data, ['email', 'password', 'full_name', 'age', 'gender'])
        
        if errors:
            for field, message in errors.items():
                flash(message, 'error')
            return render_template('register.html', form_data=form_data)
        
        try:
            # Create Firebase auth user
            user = auth.create_user(
                email=form_data['email'],
                password=form_data['password']
            )
            
            # Store additional user data in Firestore
            user_data = {
                'email': form_data['email'],
                'full_name': form_data['full_name'],
                'age': int(form_data['age']),
                'gender': form_data['gender'],
                'weight_goal': 0.0,
                'join_date': firestore.SERVER_TIMESTAMP
            }
            
            db.collection('users').document(user.uid).set(user_data)
            flash('Registration successful! Please log in.', 'success')
            logger.info(f"New user registered: {form_data['email']}")
            return redirect(url_for('login'))
        
        except auth.EmailAlreadyExistsError:
            flash('Email already in use. Please use a different email.', 'error')
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
        
        return render_template('register.html', form_data=form_data)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_user_input(form_data, ['email', 'password'])
        
        if errors:
            for field, message in errors.items():
                flash(message, 'error')
            return render_template('login.html', form_data=form_data)
        
        try:
            # Note: In production, use Firebase client SDK for password verification
            # This is a simplified version for demonstration
            user = auth.get_user_by_email(form_data['email'])
            
            # In a real app, verify password with Firebase client SDK
            # For now, we'll assume password is correct if user exists
            session['user_id'] = user.uid
            session['email'] = user.email
            flash('Login successful!', 'success')
            logger.info(f"User logged in: {user.email}")
            return redirect(url_for('dashboard'))
        
        except auth.UserNotFoundError:
            flash('Invalid email or password', 'error')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
        
        return render_template('login.html', form_data=form_data)
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = session['user_id']
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            flash('User data not found', 'error')
            return redirect(url_for('logout'))
        
        user_data = user.to_dict()
        
        # Get health metrics
        health_data = db.collection('health').where('user_id', '==', user_id).stream()
        health_records = [doc.to_dict() for doc in health_data]
        
        # Get exercise logs
        exercise_data = db.collection('exercise_logs').where('user_id', '==', user_id).stream()
        exercise_logs = [doc.to_dict() for doc in exercise_data]
        
        # Get meal logs
        meal_data = db.collection('meal_logs').where('user_id', '==', user_id).stream()
        meal_logs = [doc.to_dict() for doc in meal_data]
        
        # Get sleep logs
        sleep_data = db.collection('sleep_logs').where('user_id', '==', user_id).stream()
        sleep_logs = [doc.to_dict() for doc in sleep_data]
        
        # Calculate summaries
        summaries = {
            'total_weight': sum(rec.get('weight', 0) for rec in health_records),
            'total_water': sum(rec.get('water', 0) for rec in health_records),
            'total_steps': sum(rec.get('steps', 0) for rec in health_records),
            'total_calories_burned': sum(rec.get('calories_burned', 0) for rec in exercise_logs),
            'total_duration': sum(rec.get('duration', 0) for rec in exercise_logs),
            'total_meals': len(meal_logs),
            'total_calories_consumed': sum(rec.get('calories', 0) for rec in meal_logs)
        }
        
        # Generate feedback
        feedback = generate_feedback(summaries, sleep_logs)
        
        return render_template('dashboard.html',
            user_name=user_data.get('full_name', 'User'),
            join_date=user_data.get('join_date', 'N/A'),
            weight_goal=user_data.get('weight_goal', 0.0),
            summaries=summaries,
            feedback=feedback,
            health_records=health_records,
            exercise_logs=exercise_logs,
            meal_logs=meal_logs,
            sleep_logs=sleep_logs
        )
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard data', 'error')
        return redirect(url_for('index'))

def generate_feedback(summaries, sleep_logs):
    """Generate user feedback based on their data"""
    feedback = {}
    
    # Sleep feedback
    if sleep_logs:
        latest_sleep = sleep_logs[-1]
        try:
            bed_time = datetime.strptime(latest_sleep['bed_time'], '%H:%M:%S')
            wake_up_time = datetime.strptime(latest_sleep['wake_up_time'], '%H:%M:%S')
            sleep_duration = (wake_up_time - bed_time).total_seconds() / 3600
            
            if sleep_duration >= 7:
                feedback['sleep'] = "Good sleep duration!"
            else:
                feedback['sleep'] = f"Only {sleep_duration:.1f} hours of sleep. Aim for 7-9 hours."
        except (ValueError, KeyError):
            feedback['sleep'] = "Could not analyze sleep data"
    
    # Hydration feedback
    if summaries['total_water'] >= 8:
        feedback['hydration'] = "Great hydration!"
    else:
        feedback['hydration'] = f"Only {summaries['total_water']} glasses of water. Aim for 8+."
    
    # Steps feedback
    if summaries['total_steps'] >= 10000:
        feedback['steps'] = "Excellent activity level!"
    else:
        feedback['steps'] = f"{summaries['total_steps']} steps. Try to reach 10,000 daily."
    
    return feedback

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    try:
        user_ref = db.collection('users').document(session['user_id'])
        user = user_ref.get()
        
        if not user.exists:
            flash('User data not found', 'error')
            return redirect(url_for('logout'))
        
        if request.method == 'POST':
            form_data = request.form.to_dict()
            errors = validate_user_input(form_data, ['full_name', 'email', 'weight_goal'])
            
            if errors:
                for field, message in errors.items():
                    flash(message, 'error')
                return render_template('edit_profile.html', form_data=form_data)
            
            try:
                updates = {
                    'full_name': form_data['full_name'],
                    'email': form_data['email'],
                    'weight_goal': float(form_data['weight_goal'])
                }
                
                user_ref.update(updates)
                session['email'] = form_data['email']
                flash('Profile updated successfully!', 'success')
                logger.info(f"User {session['user_id']} updated profile")
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                logger.error(f"Profile update error: {e}")
                flash('Failed to update profile. Please try again.', 'error')
            
            return render_template('edit_profile.html', form_data=form_data)
        
        # GET request - populate form with current data
        user_data = user.to_dict()
        form_data = {
            'full_name': user_data.get('full_name', ''),
            'email': user_data.get('email', ''),
            'weight_goal': str(user_data.get('weight_goal', 0.0))
        }
        
        return render_template('edit_profile.html', form_data=form_data)
    
    except Exception as e:
        logger.error(f"Edit profile error: {e}")
        flash('Error loading profile data', 'error')
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 Error: {e}")
    return render_template('500.html'), 500

# Health Check Endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

# Main Entry Point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')