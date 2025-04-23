import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "your-database-url"  # Replace with your actual database URL
})

ref = db.reference('Students')

data = {
    "57": {
        "name": "Prabesh Bashyal",
        "starting_year": "2017-01",  # Adjusted format
        "total_attendance": 7,
        "year": 4
        # "last_attendance_time": "2022-12-11 00:54:34"
    },
    "76": {
        "name": "Sandesh Kuikel",
        "starting_year": "2018-06",
        "total_attendance": 10,
        "year": 3
        # "last_attendance_time": "2023-05-15 14:23:50"
    },
    "79": {
        "name": "Saroj Poudel",
        "starting_year": "2019-09",
        "total_attendance": 5,
        "year": 2
        # "last_attendance_time": "2024-02-20 09:12:10"
    }
}


for key, value in data.items():
    ref.child(key).set(value)