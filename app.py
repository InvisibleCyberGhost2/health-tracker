from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = '3a928948ef40444b2b9f8c11d341c6ea'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate('health-care-tracker-3af6a-firebase-adminsdk-fbsvc-d4a783a034.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logging.debug("Firestore initialized successfully!")
except Exception as e:
    logging.error(f"Error initializing Firebase: {e}")

# ──────── DATABASE ────────
def init_db():
    # Firestore does not require initialization like SQL databases
    logging.debug("Firestore initialized successfully!")

# ──────── ROUTES ────────

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
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        age = int(request.form['age'])
        gender = request.form['gender']

        try:
            user = auth.create_user(email=email, password=password)
            db.collection('users').document(user.uid).set({
                'email': email,
                'full_name': full_name,
                'age': age,
                'gender': gender,
                'weight_goal': 0.0,
                'join_date': firestore.SERVER_TIMESTAMP
            })
            logging.debug(f"User registered: {email}")
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            return f"Error registering user: {e}"

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.get_user_by_email(email)
            # Verify password (Firebase handles this, so we assume it's correct if the user exists)
            session['user_id'] = user.uid
            session['email'] = user.email
            logging.debug(f"User logged in: {email}")
            return redirect(url_for('dashboard'))
        except Exception as e:
            logging.debug("Invalid email or password.")
            return f"Invalid email or password: {e}"

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    user_id = session.get('user_id')

    user_ref = db.collection('users').document(user_id)
    user = user_ref.get()
    if user.exists:
        user_data = user.to_dict()
        user_name = user_data.get('full_name', 'N/A')
        join_date = user_data.get('join_date', 'N/A')
        weight_goal = user_data.get('weight_goal', 'N/A')
    else:
        user_name = 'N/A'
        join_date = 'N/A'
        weight_goal = 'N/A'

    # Health summary
    health_docs = db.collection('health').where('user_id', '==', user_id).stream()
    total_weight = total_water = total_steps = 0
    for doc in health_docs:
        data = doc.to_dict()
        total_weight += data.get('weight', 0)
        total_water += data.get('water', 0)
        total_steps += data.get('steps', 0)

    # Exercise summary
    exercise_docs = db.collection('exercise_logs').where('user_id', '==', user_id).stream()
    total_calories_burned = total_duration = 0
    for doc in exercise_docs:
        data = doc.to_dict()
        total_calories_burned += data.get('calories_burned', 0)
        total_duration += data.get('duration', 0)

    # Meal summary
    meal_docs = db.collection('meal_logs').where('user_id', '==', user_id).stream()
    total_meals = total_calories_consumed = 0
    for doc in meal_docs:
        data = doc.to_dict()
        total_meals += 1
        total_calories_consumed += data.get('calories', 0)

    # Sleep logs
    sleep_docs = db.collection('sleep_logs').where('user_id', '==', user_id).stream()
    sleep_logs = [doc.to_dict() for doc in sleep_docs]

    # Detailed logs
    health_records = [doc.to_dict() for doc in health_docs]
    exercise_logs = [doc.to_dict() for doc in exercise_docs]
    meal_logs = [doc.to_dict() for doc in meal_docs]

    # Feedback logic
    feedback = {}

    # Sleep feedback
    if sleep_logs:
        latest_sleep = sleep_logs[-1]
        bed_time = datetime.strptime(latest_sleep['bed_time'], '%H:%M:%S')
        wake_up_time = datetime.strptime(latest_sleep['wake_up_time'], '%H:%M:%S')
        sleep_duration = wake_up_time - bed_time

        if sleep_duration.total_seconds() / 3600 >= 7:
            feedback['sleep'] = "Good sleep duration!"
        else:
            feedback['sleep'] = "You might need more sleep."

    # Hydration feedback
    if total_water >= 8:
        feedback['hydration'] = "Great hydration!"
    else:
        feedback['hydration'] = "Drink more water."

    # Steps feedback
    if total_steps >= 10000:
        feedback['steps'] = "Excellent activity level!"
    else:
        feedback['steps'] = "Try to walk more."

    if request.method == 'POST':
        if 'weight' in request.form:
            date = request.form['date']
            weight = float(request.form['weight'])
            water = int(request.form['water'])
            steps = int(request.form['steps'])
            db.collection('health').add({
                'user_id': user_id,
                'date': date,
                'weight': weight,
                'water': water,
                'steps': steps
            })
            logging.debug(f"Health data inserted: user_id={user_id}, date={date}, weight={weight}, water={water}, steps={steps}")

        elif 'activity_type' in request.form:
            date = request.form['date']
            activity_type = request.form['activity_type']
            duration = float(request.form['duration'])
            calories_burned = float(request.form['calories_burned'])
            notes = request.form['notes']
            db.collection('exercise_logs').add({
                'user_id': user_id,
                'date': date,
                'activity_type': activity_type,
                'duration': duration,
                'calories_burned': calories_burned,
                'notes': notes
            })
            logging.debug(f"Exercise data inserted: user_id={user_id}, date={date}, activity_type={activity_type}, duration={duration}, calories_burned={calories_burned}, notes={notes}")

        elif 'meal_type' in request.form:
            date = request.form['date']
            meal_type = request.form['meal_type']
            calories = float(request.form['calories'])
            protein = float(request.form['protein'])
            fat = float(request.form['fat'])
            carbs = float(request.form['carbs'])
            notes = request.form['notes']
            db.collection('meal_logs').add({
                'user_id': user_id,
                'date': date,
                'meal_type': meal_type,
                'calories': calories,
                'protein': protein,
                'fat': fat,
                'carbs': carbs,
                'notes': notes
            })
            logging.debug(f"Meal data inserted: user_id={user_id}, date={date}, meal_type={meal_type}, calories={calories}, protein={protein}, fat={fat}, carbs={carbs}, notes={notes}")

        elif 'bed_time' in request.form:
            date = request.form['date']
            bed_time = request.form['bed_time']
            wake_up_time = request.form['wake_up_time']
            db.collection('sleep_logs').add({
                'user_id': user_id,
                'date': date,
                'bed_time': bed_time,
                'wake_up_time': wake_up_time
            })
            logging.debug(f"Sleep data inserted: user_id={user_id}, date={date}, bed_time={bed_time}, wake_up_time={wake_up_time}")

        return redirect(url_for('dashboard'))

    return render_template('dashboard.html',
        email=session.get('email'),
        user_name=user_name,
        join_date=join_date,
        weight_goal=weight_goal,
        total_weight=total_weight,
        total_water=total_water,
        total_steps=total_steps,
        total_calories_burned=total_calories_burned,
        total_duration=total_duration,
        total_meals=total_meals,
        total_calories_consumed=total_calories_consumed,
        sleep_logs=sleep_logs,
        feedback=feedback,
        health_records=health_records,
        exercise_logs=exercise_logs,
        meal_logs=meal_logs
    )

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_ref = db.collection('users').document(session['user_id'])
    user = user_ref.get()
    if user.exists:
        user_data = user.to_dict()

        if request.method == 'POST':
            full_name = request.form['full_name']
            email = request.form['email']
            weight_goal = float(request.form['weight_goal'])
            user_ref.update({
                'full_name': full_name,
                'email': email,
                'weight_goal': weight_goal
            })
            logging.debug(f"Profile updated: user_id={session['user_id']}, full_name={full_name}, email={email}, weight_goal={weight_goal}")
            return redirect(url_for('dashboard'))

        return render_template('edit_profile.html', user_name=user_data['full_name'], email=user_data['email'], weight_goal=user_data['weight_goal'])

    return render_template('edit_profile.html', user_name='', email='', weight_goal=0.0)

@app.route('/logout')
def logout():
    session.clear()
    logging.debug("User logged out.")
    return redirect(url_for('login'))

# Fallback route for client-side routing
@app.route('/<path:path>')
def catch_all(path):
    return render_template('index.html')

# ──────── MAIN ────────
if __name__ == '__main__':
<<<<<<< HEAD
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)


=======
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
>>>>>>> c8309a2a31a1ae6c6cb703ff600776eff7a33daf
