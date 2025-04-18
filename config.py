import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '3a928948ef40444b2b9f8c11d341c6ea'
    FIREBASE_CREDENTIALS = 'health-care-tracker-3af6a-firebase-adminsdk-fbsvc-d4a783a034.json'
