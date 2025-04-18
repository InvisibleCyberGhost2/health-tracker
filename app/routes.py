from flask import render_template, request, redirect, session, url_for, current_app, Blueprint, flash
from datetime import datetime
import logging
import pyrebase
from werkzeug.utils import secure_filename
import requests
import base64
import time

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
db = firebase.database()

main = Blueprint('main', __name__)

# Imgur Client ID
IMGUR_CLIENT_ID = 'your_imgur_client_id'

@main.route('/')
def index():
    user_image = session.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')
    email = session.get('email', 'user@example.com')
    return render_template('index.html', user_image=user_image, email=email)

@main.route('/features')
def features():
    user_image = session.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')
    email = session.get('email', 'user@example.com')
    return render_template('features.html', user_image=user_image, email=email)

@main.route('/team')
def team():
    user_image = session.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')
    email = session.get('email', 'user@example.com')
    return render_template('team.html', user_image=user_image, email=email)

@main.route('/about')
def about():
    user_image = session.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')
    email = session.get('email', 'user@example.com')
    return render_template('about.html', user_image=user_image, email=email)

@main.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['uid']
    user_image = session.get('user_image', 'https://randomuser.me/api/portraits/women/44.jpg')
    email = session.get('email', 'user@example.com')

    try:
        # Get user data
        user_ref = db.child("users").child(user_id).get().val()
        user_name = user_ref.get('name', 'User')

        # Get health data
        health_ref = db.child("health").order_by_child("user_id").equal_to(user_id).get()
        health_data = health_ref.val()

        if health_data:
            health_data = list(health_data.values())[-1]  # Get the latest health data
            steps = health_data.get('steps', 0)
            sleep = health_data.get('sleep', 0)
            heart_rate = health_data.get('heart_rate', 0)
            hydration = health_data.get('water', 0)
            mood = health_data.get('mood', 'neutral')
            weight = health_data.get('weight', 0)
        else:
            steps = sleep = heart_rate = hydration = weight = 0
            mood = 'neutral'

        # Get today's activity data
        today = datetime.now().strftime("%Y-%m-%d")
        activities_ref = db.child("activities").order_by_child("user_id").equal_to(user_id).get()
        activities_data = activities_ref.val()

        today_activities = []
        if activities_data:
            for activity_id, activity in activities_data.items():
                if activity.get('date') == today:
                    today_activities.append(activity)

        # Get user goals
        goals = user_ref.get('goals', {})

        return render_template('dashboard.html',
                           user_name=user_name,
                           steps=steps,
                           sleep=sleep,
                           heart_rate=heart_rate,
                           hydration=hydration,
                           weight=weight,
                           mood=mood,
                           goals=goals,
                           today_activities=today_activities,
                           user_image=user_image,
                           email=email)

    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard data', 'error')
        return redirect(url_for('main.index'))

@main.route('/activity')
def activity():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        # Get user's activities, ordered by timestamp
        activities_ref = db.child("activities").order_by_child("user_id").equal_to(session['uid']).get()
        activities = []

        if activities_ref.val():
            # Convert to list and sort by date (newest first)
            activities = list(activities_ref.val().values())
            activities.sort(key=lambda x: x.get('date', ''), reverse=True)

        # Get user data to retrieve user_name
        user_ref = db.child("users").child(session['uid']).get()
        user_data = user_ref.val()
        user_name = user_data.get('name', 'User')

        # Pass the current datetime to the template
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return render_template('activity.html',
                            activities=activities[:5],  # Show only 5 most recent
                            user_name=user_name,  # Pass user_name to the template
                            user_image=session.get('user_image'),
                            email=session.get('email'),
                            datetime=current_datetime)  # Pass datetime to the template
    except Exception as e:
        current_app.logger.error(f"Activity page error: {str(e)}")
        flash('Error loading activities', 'error')
        return redirect(url_for('main.dashboard'))

@main.route('/log_activity', methods=['GET', 'POST'])
def log_activity():
    if 'uid' not in session:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        return redirect(url_for('auth.login'))

    try:
        if request.is_json:
            data = request.get_json()
            activity_data = {
                'user_id': session['uid'],
                'activity_type': data.get('activity_type'),
                'date': data.get('date'),
                'duration': int(data.get('duration', 0)),
                'distance': float(data.get('distance', 0)),
                'calories': int(data.get('calories', 0)),
                'notes': data.get('notes', ''),
                'timestamp': datetime.now().isoformat()
            }
        else:
            activity_data = {
                'user_id': session['uid'],
                'activity_type': request.form.get('activity_type'),
                'date': request.form.get('date'),
                'duration': int(request.form.get('duration', 0)),
                'distance': float(request.form.get('distance', 0)),
                'calories': int(request.form.get('calories', 0)),
                'notes': request.form.get('notes', ''),
                'timestamp': datetime.now().isoformat()
            }

        # Validate required fields
        if not activity_data['activity_type'] or not activity_data['date']:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Activity type and date are required'}), 400
            flash('Activity type and date are required', 'error')
            return redirect(url_for('main.activity'))

        db.child("activities").push(activity_data)

        if request.is_json:
            return jsonify({'success': True})
        flash('Activity logged successfully!', 'success')
    except Exception as e:
        current_app.logger.error(f"Error logging activity: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash('Error logging activity. Please try again.', 'error')

    return redirect(url_for('main.activity'))

@main.route('/log_health', methods=['GET', 'POST'])
def log_health():
    if 'uid' not in session:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                health_data = {
                    'user_id': session['uid'],
                    'date': data.get('date'),
                    'weight': float(data.get('weight', 0)),
                    'steps': int(data.get('steps', 0)),
                    'sleep': float(data.get('sleep', 0)),
                    'water': int(data.get('water', 0)),
                    'heart_rate': int(data.get('heart_rate', 0)),
                    'mood': data.get('mood', 'good'),
                    'notes': data.get('notes', ''),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                health_data = {
                    'user_id': session['uid'],
                    'date': request.form.get('date'),
                    'weight': float(request.form.get('weight', 0)),
                    'steps': int(request.form.get('steps', 0)),
                    'sleep': float(request.form.get('sleep', 0)),
                    'water': int(request.form.get('water', 0)),
                    'heart_rate': int(request.form.get('heart_rate', 0)),
                    'mood': request.form.get('mood', 'good'),
                    'notes': request.form.get('notes', ''),
                    'timestamp': datetime.now().isoformat()
                }

            # Validate required fields
            if not health_data['date']:
                if request.is_json:
                    return jsonify({'success': False, 'error': 'Date is required'}), 400
                flash('Date is required', 'error')
                return redirect(url_for('main.log_health'))

            db.child("health").push(health_data)

            if request.is_json:
                return jsonify({'success': True})
            flash('Health data logged successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            current_app.logger.error(f"Error logging health data: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            flash('Error logging health data. Please try again.', 'error')

    if request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request method'}), 405

    return render_template('health_log.html',
                        user_image=session.get('user_image'),
                        email=session.get('email'))

@main.route('/goals')
def goals():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        # Get user's goals
        user_ref = db.child("users").child(session['uid']).get()
        user_data = user_ref.val()
        goals = user_data.get('goals', {})

        # Get user name
        user_name = user_data.get('name', 'User')

        # Get latest health data for progress tracking
        health_ref = db.child("health").order_by_child("user_id").equal_to(session['uid']).get()
        health_data = health_ref.val()

        current_steps = current_sleep = current_water = current_weight = None
        if health_data:
            latest_health = list(health_data.values())[-1]  # Get most recent entry
            current_steps = latest_health.get('steps')
            current_sleep = latest_health.get('sleep')
            current_water = latest_health.get('water')
            current_weight = latest_health.get('weight')

        return render_template('goals.html',
                            goals=goals,
                            current_steps=current_steps,
                            current_sleep=current_sleep,
                            current_water=current_water,
                            current_weight=current_weight,
                            user_name=user_name,  # Pass user_name to the template
                            user_image=session.get('user_image'),
                            email=session.get('email'))
    except Exception as e:
        current_app.logger.error(f"Goals page error: {str(e)}")
        flash('Error loading goals', 'error')
        return redirect(url_for('main.dashboard'))

@main.route('/update_goals', methods=['POST'])
def update_goals():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        goals_data = {
            'steps': int(request.form.get('steps', 10000)),
            'sleep': float(request.form.get('sleep', 8)),
            'water': int(request.form.get('water', 8)),
            'weight': float(request.form.get('weight', 0)),
            'last_updated': datetime.now().isoformat()
        }

        # Validate at least one goal is set
        if not any(goals_data.values()):
            flash('Please set at least one goal', 'error')
            return redirect(url_for('main.goals'))

        db.child("users").child(session['uid']).child("goals").update(goals_data)
        flash('Goals updated successfully!', 'success')
    except Exception as e:
        current_app.logger.error(f"Error updating goals: {str(e)}")
        flash('Error updating goals. Please try again.', 'error')

    return redirect(url_for('main.goals'))

@main.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        # Get user data with consistent null handling
        user_ref = db.child("users").child(session['uid'])
        user = user_ref.get().val() or {}

        # Get common user data for template
        user_name = user.get('name', 'User')
        user_image = session.get('user_image')
        email = session.get('email')

        if request.method == 'POST':
            # Validate form data
            if not request.form.get('name') or not request.form.get('weight_goal'):
                flash('Name and weight goal are required fields', 'error')
                return redirect(url_for('main.edit_profile'))

            try:
                updated_data = {
                    'name': request.form['name'].strip(),
                    'weight_goal': float(request.form['weight_goal']),
                    'last_updated': datetime.now().isoformat()
                }

                # Validate weight goal is positive
                if updated_data['weight_goal'] <= 0:
                    flash('Weight goal must be a positive number', 'error')
                    return redirect(url_for('main.edit_profile'))

                user_ref.update(updated_data)

                # Update session name if changed
                if 'name' in updated_data:
                    session['name'] = updated_data['name']

                flash('Profile updated successfully!', 'success')
                return redirect(url_for('main.profile'))  # Redirect to profile instead of dashboard

            except ValueError:
                flash('Please enter a valid number for weight goal', 'error')
                return redirect(url_for('main.edit_profile'))
            except Exception as e:
                current_app.logger.error(f"Error updating profile: {str(e)}", exc_info=True)
                flash('Error updating profile. Please try again.', 'error')
                return redirect(url_for('main.edit_profile'))

        # GET request - populate form with current values
        return render_template('edit_profile.html',
                            user_name=user_name,
                            weight_goal=user.get('weight_goal', 0),
                            user_image=user_image,
                            email=email,
                            current_user=user)  # Pass full user object for flexibility

    except Exception as e:
        current_app.logger.error(f"Edit profile error: {str(e)}", exc_info=True)
        flash('Error loading profile editor. Please try again.', 'error')
        return redirect(url_for('main.profile'))

@main.route('/profile')
def profile():

    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        # Get user data (consistent with goals route)
        user_ref = db.child("users").child(session['uid']).get()
        user_data = user_ref.val() or {}

        # Get user name (same pattern as goals route)
        user_name = user_data.get('name', 'User')

        # Process health history (optimized version)
        health_ref = db.child("health").order_by_child("user_id").equal_to(session['uid']).get()
        health_history = {}

        if health_ref.each():
            for entry in health_ref.each():
                entry_data = entry.val()
                if isinstance(entry_data, dict) and 'date' in entry_data:
                    health_history[entry_data['date']] = {
                        'steps': entry_data.get('steps', 0),
                        'sleep': entry_data.get('sleep', 0),
                        'water': entry_data.get('water', 0),
                        'weight': entry_data.get('weight', 0),
                        'heart_rate': entry_data.get('heart_rate', 0)
                    }

        # Process activity history (optimized version)
        activities_ref = db.child("activities").order_by_child("user_id").equal_to(session['uid']).get()
        activity_history = {}

        if activities_ref.each():
            for entry in activities_ref.each():
                entry_data = entry.val()
                if isinstance(entry_data, dict):
                    activity_history[entry.key()] = {
                        'date': entry_data.get('date', 'No date'),
                        'activity_type': entry_data.get('activity_type', 'Unknown'),
                        'duration': entry_data.get('duration', 0),
                        'distance': entry_data.get('distance', 0),
                        'calories': entry_data.get('calories', 0)
                    }

        return render_template('profile.html',
                            user_data=user_data,
                            health_history=health_history,
                            activity_history=activity_history,
                            user_name=user_name,  # Consistent with goals route
                            user_image=session.get('user_image'),
                            email=session.get('email'))

    except Exception as e:
        current_app.logger.error(f"Profile page error: {str(e)}", exc_info=True)
        flash('Error loading profile data. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

@main.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'uid' not in session:
        return redirect(url_for('auth.login'))

    try:
        user_ref = db.child("users").child(session['uid'])
        user_data = user_ref.get().val() or {}

        if request.method == 'POST':
            form_type = request.form.get('form_type')

            if form_type == 'profile_settings':
                name = request.form['name'].strip()
                weight_goal = float(request.form['weight_goal'])
                profile_image = request.files.get('profile_image')

                updated_data = {
                    'name': name,
                    'weight_goal': weight_goal,
                    'last_updated': datetime.now().isoformat()
                }

                if profile_image:
                    filename = secure_filename(profile_image.filename)
                    file_content = profile_image.read()

                    # Upload the file to Imgur with rate limiting
                    headers = {'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'}
                    response = requests.post(
                        'https://api.imgur.com/3/image',
                        headers=headers,
                        data={'image': base64.b64encode(file_content)}
                    )

                    if response.status_code == 429:
                        flash('Too many requests. Please try again later.', 'error')
                        return redirect(url_for('main.settings'))

                    response_data = response.json()

                    if response_data.get('success'):
                        image_url = response_data['data']['link']
                        updated_data['profile_image'] = image_url
                        session['user_image'] = image_url
                    else:
                        flash('Error uploading image. Please try again.', 'error')
                        return redirect(url_for('main.settings'))

                user_ref.update(updated_data)
                flash('Profile updated successfully!', 'success')

            elif form_type == 'app_settings':
                updated_prefs = {
                    'notifications': 'notifications' in request.form,
                    'water_reminders': 'water_reminders' in request.form,
                    'notification_frequency': request.form.get('notification_frequency', 'daily'),
                    'email_notifications': 'email_notifications' in request.form,
                    'units': request.form.get('units', 'metric')
                }
                user_ref.child('preferences').update(updated_prefs)
                flash('Preferences saved!', 'success')

            return redirect(url_for('main.settings'))

        return render_template('settings.html',
                               user_data=user_data,
                               user_name=user_data.get('name', 'User'),
                               weight_goal=user_data.get('weight_goal', 0),
                               preferences=user_data.get('preferences', {}),
                               user_image=session.get('user_image'),
                               email=session.get('email'))

    except Exception as e:
        current_app.logger.error(f"Settings error: {str(e)}", exc_info=True)
        flash('Error processing settings. Please try again.', 'error')
        return redirect(url_for('main.settings'))
