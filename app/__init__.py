from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from config import Config

# Create db instance at module level
db = None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)

    # Initialize Firebase
    init_firebase(app)

    # Register blueprints
    register_blueprints(app)

    return app

def init_firebase(app):
    """Initialize Firebase Admin SDK"""
    global db
    try:
        cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        app.db = db  # Make db available on app instance
        app.logger.info("Firebase initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing Firebase: {str(e)}")
        raise

def register_blueprints(app):
    """Register Flask blueprints"""
    from .routes import main as main_blueprint
    from .auth import auth_blueprint  # Correct import statement

    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
