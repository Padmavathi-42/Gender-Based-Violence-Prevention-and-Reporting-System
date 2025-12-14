from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import psycopg2
from datetime import datetime
import os
import json
from threading import Thread
import time
from DistressPercent.distress import main

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app)  # Initialize SocketIO

# Disable Flask's default logging of IP addresses
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# PostgreSQL connection configuration
DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'password',  # Replace with your password
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id SERIAL PRIMARY KEY,
            incident_date DATE NOT NULL,
            location VARCHAR(100) NOT NULL,
            incident_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            witness VARCHAR(50) NOT NULL,
            submission_date TIMESTAMP NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending',
            distress_percentage REAL DEFAULT 0.0
        )
    ''')
    cursor.execute("""
        UPDATE reports 
        SET status = CASE WHEN distress_percentage > 60 THEN 'Urgent' ELSE 'Pending' END
    """)
    conn.commit()
    cursor.close()
    conn.close()

def list_to_text(description_list):
    return json.dumps(description_list)

def text_to_list(description_text):
    return json.loads(description_text)

def process_distress_and_notify(report_id, description_list):
    """Background task for distress calculation and WebSocket notification"""
    start = time.time()
    distress_percentage = main(description_list)
    print(f"Distress calculation took: {time.time() - start:.3f} seconds")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reports SET distress_percentage = %s WHERE report_id = %s", 
                   (distress_percentage, report_id))
    if distress_percentage > 60:
        cursor.execute("UPDATE reports SET status = 'Urgent' WHERE report_id = %s", 
                      (report_id,))
        # Emit WebSocket event for urgent report
        cursor.execute("SELECT * FROM reports WHERE report_id = %s", (report_id,))
        report = cursor.fetchone()
        report_data = {
            "report_id": report[0],
            "incident_date": report[1].strftime("%Y-%m-%d"),
            "location": report[2],
            "incident_type": report[3],
            "description": text_to_list(report[4]),
            "witness": report[5],
            "submission_date": report[6].strftime("%Y-%m-%d %H:%M:%S"),
            "status": report[7],
            "distress_percentage": report[8]
        }
        socketio.emit('new_urgent_report', report_data)
    else:
        cursor.execute("UPDATE reports SET status = 'Pending' WHERE report_id = %s", 
                      (report_id,))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        start_time = time.time()
        
        incident_date = request.form['incident_date']
        location = request.form['location']
        incident_type = request.form['incident_type']
        description = request.form['description']
        witness = request.form['witness']

        split_start = time.time()
        description_list = [sentence.strip() for sentence in description.split('.') if sentence.strip()]
        description_text = list_to_text(description_list)
        print(f"Description splitting took: {time.time() - split_start:.3f} seconds")

        submission_date = datetime.now()

        db_start = time.time()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (incident_date, location, incident_type, description, witness, submission_date, distress_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING report_id
        """, (incident_date, location, incident_type, description_text, witness, submission_date, 0.0))
        report_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Database insertion took: {time.time() - db_start:.3f} seconds")

        Thread(target=process_distress_and_notify, args=(report_id, description_list)).start()

        print(f"Total response time: {time.time() - start_time:.3f} seconds")
        flash(f"Report submitted successfully! Your Report ID is {report_id}. Distress calculation is in progress.")
        return redirect(url_for('index'))

    return render_template('report.html')

@app.route('/clear_db', methods=['POST'])
def clear_db():
    if 'logged_in' not in session or not session['logged_in']:
        flash("Admin access required.")
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reports")
        conn.commit()
        cursor.close()
        conn.close()
        flash("Database cleared successfully.")
    except Exception as e:
        print(f"Error clearing database: {e}")
        flash("Failed to clear database.")
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == "admin123":
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Incorrect password.")
            return render_template('admin.html')

    if 'logged_in' not in session or not session['logged_in']:
        return render_template('admin.html')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT report_id, incident_date, location, incident_type, description, witness, submission_date, status, distress_percentage
        FROM reports
        ORDER BY distress_percentage DESC, submission_date DESC
    """)
    reports = cursor.fetchall()
    cursor.close()
    conn.close()

    report_list = []
    for report in reports:
        report_id, incident_date, location, incident_type, description, witness, submission_date, status, distress_percentage = report
        description_list = text_to_list(description)
        report_list.append({
            "report_id": report_id,
            "incident_date": incident_date.strftime("%Y-%m-%d"),
            "location": location,
            "incident_type": incident_type,
            "description": description_list,
            "witness": witness,
            "submission_date": submission_date.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "distress_percentage": distress_percentage
        })

    return render_template('admin.html', reports=report_list)

@app.route('/predictive_analytics', methods=['GET'])
def predictive_analytics():
    if 'logged_in' not in session or not session['logged_in']:
        flash("Admin access required to perform predictive analytics.")
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        query = """
            SELECT report_id, incident_date, location, incident_type, description, witness, submission_date, distress_percentage
            FROM reports
        """
        df = pd.read_sql(query, conn)
        conn.close()
    except Exception as e:
        print(f"Error fetching data for analytics: {e}")
        flash("Failed to fetch data for analytics.")
        return redirect(url_for('admin'))

    df['description_list'] = df['description'].apply(lambda x: json.loads(x))
    df['description_length'] = df['description_list'].apply(len)
    df['incident_month'] = pd.to_datetime(df['incident_date']).dt.month
    df['submission_hour'] = pd.to_datetime(df['submission_date']).dt.hour
    
    le_location = LabelEncoder()
    le_type = LabelEncoder()
    le_witness = LabelEncoder()
    df['location_encoded'] = le_location.fit_transform(df['location'])
    df['incident_type_encoded'] = le_type.fit_transform(df['incident_type'])
    df['witness_encoded'] = le_witness.fit_transform(df['witness'])
    df['high_risk'] = (df['distress_percentage'] > 70).astype(int)

    features = ['location_encoded', 'incident_type_encoded', 'witness_encoded', 
                'incident_month', 'submission_hour', 'description_length', 'distress_percentage']
    X = df[features]
    y = df['high_risk']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)

    risk_probs = model.predict_proba(X)[:, 1]
    df['risk_probability'] = risk_probs
    risk_by_location = df.groupby('location').agg({
        'risk_probability': 'mean',
        'report_id': 'count'
    }).rename(columns={'report_id': 'incident_count'})
    high_risk_areas = risk_by_location[risk_by_location['risk_probability'] > 0.7].to_dict()

    preventive_measures = {}
    for location in high_risk_areas['risk_probability'].keys():
        location_data = df[df['location'] == location]
        common_types = location_data['incident_type'].value_counts().index[0]
        avg_distress = location_data['distress_percentage'].mean()
        
        measures = []
        if common_types in ['Physical', 'Sexual']:
            measures.extend(["Increase security presence", "Conduct staff training"])
        elif common_types == 'Emotional':
            measures.extend(["Implement peer support", "Offer counseling"])
        elif common_types == 'Economic':
            measures.extend(["Provide financial aid", "Educate on reporting"])
        if avg_distress > 80:
            measures.append("Deploy rapid response team")
        
        preventive_measures[location] = {
            'common_type': common_types,
            'avg_distress': round(avg_distress, 2),
            'measures': measures
        }

    return render_template('predictive_analytics.html', 
                           accuracy=accuracy, 
                           high_risk_areas=high_risk_areas, 
                           preventive_measures=preventive_measures)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.")
    return redirect(url_for('index'))

#def insertinitial():
    sample_data = [
        ('2025-02-01', 'Office Break Room', 'Emotional', '["John made rude comments", "I felt humiliated"]', 'Victim', '2025-03-01 08:15:23', 'Pending', 60.0),
('2025-02-02', 'Home', 'Physical', '["My partner hit me", "I''m scared for my life"]', 'Victim', '2025-03-01 09:30:45', 'Reviewed', 90.0),
('2025-02-03', 'Counseling Center', 'Emotional', '["Session was helpful", "Staff were supportive"]', 'Victim', '2025-03-01 10:45:12', 'Pending', 20.0),
('2025-02-04', 'Work Desk', 'Sexual', '["Jane harassed me", "She threatened me after rejection"]', 'Victim', '2025-03-01 11:20:33', 'Pending', 85.0),
('2025-02-05', 'Outside House', 'Emotional', '["Ex-husband was stalking", "I''m terrified"]', 'Victim', '2025-03-01 12:10:56', 'Pending', 75.0),
('2025-02-06', 'Helpline Call', 'Economic', '["I called today", "Need help with complaint"]', 'Victim', '2025-03-01 13:25:17', 'Pending', 30.0),
('2025-02-07', 'Park', 'Physical', '["Someone pushed me", "It hurt a lot"]', 'Witness', '2025-03-01 14:40:28', 'Pending', 70.0),
('2025-02-08', 'Office', 'Emotional', '["Boss yelled at me", "I felt worthless"]', 'Victim', '2025-03-01 15:55:39', 'Pending', 65.0),
('2025-02-09', 'Home', 'Sexual', '["Partner forced me", "I''m in distress"]', 'Victim', '2025-03-01 16:10:50', 'Reviewed', 95.0),
('2025-02-10', 'Street', 'Economic', '["Lost my wallet", "Someone threatened me"]', 'Victim', '2025-03-01 17:25:01', 'Pending', 50.0),
('2025-02-11', 'Work Canteen', 'Emotional', '["Colleague insulted me", "I cried later"]', 'Victim', '2025-03-01 18:40:12', 'Pending', 55.0),
('2025-02-12', 'Apartment', 'Physical', '["Neighbor attacked me", "I need urgent help"]', 'Victim', '2025-03-01 19:55:23', 'Pending', 80.0),
('2025-02-13', 'Online Chat', 'Emotional', '["Received threats", "Feeling anxious"]', 'Victim', '2025-03-01 20:10:34', 'Pending', 60.0),
('2025-02-14', 'Office Lobby', 'Sexual', '["Coworker groped me", "I''m shaken"]', 'Victim', '2025-03-01 21:25:45', 'Pending', 90.0),
('2025-02-15', 'Home', 'Economic', '["Partner took my money", "I can''t leave"]', 'Victim', '2025-03-01 22:40:56', 'Pending', 45.0),
('2025-02-16', 'Office', 'Physical', '["Supervisor pushed me", "I''m in pain"]', 'Victim', '2025-03-02 08:15:07', 'Pending', 75.0),
('2025-02-17', 'Street', 'Emotional', '["Stranger yelled at me", "I''m upset"]', 'Witness', '2025-03-02 09:30:18', 'Pending', 40.0),
('2025-02-18', 'Home', 'Sexual', '["Forced by spouse", "I need help now"]', 'Victim', '2025-03-02 10:45:29', 'Reviewed', 95.0),
('2025-02-19', 'Work', 'Emotional', '["Team mocked me", "I feel low"]', 'Victim', '2025-03-02 11:20:40', 'Pending', 50.0),
('2025-02-20', 'Outside', 'Physical', '["Got hit by a car", "It was intentional"]', 'Victim', '2025-03-02 12:35:51', 'Pending', 85.0),
('2025-02-21', 'Office', 'Economic', '["Colleague stole my project", "I''m stressed"]', 'Victim', '2025-03-02 13:50:02', 'Pending', 35.0),
('2025-02-22', 'Home', 'Emotional', '["Family argued", "I''m exhausted"]', 'Victim', '2025-03-02 15:05:13', 'Pending', 45.0),
('2025-02-23', 'Park', 'Sexual', '["Stranger harassed me", "I''m scared"]', 'Victim', '2025-03-02 16:20:24', 'Pending', 80.0),
('2025-02-24', 'Work', 'Physical', '["Coworker shoved me", "I need support"]', 'Victim', '2025-03-02 17:35:35', 'Pending', 70.0),
('2025-02-25', 'Home', 'Economic', '["Lost my savings", "Partner pressured me"]', 'Victim', '2025-03-02 18:50:46', 'Pending', 40.0),
('2025-02-26', 'Street', 'Emotional', '["Got catcalled", "I feel unsafe"]', 'Victim', '2025-03-02 20:05:57', 'Pending', 55.0),
('2025-02-27', 'Office', 'Sexual', '["Boss made advances", "I''m distressed"]', 'Victim', '2025-03-02 21:21:08', 'Pending', 90.0),
('2025-02-28', 'Home', 'Physical', '["Sibling hit me", "I''m in pain"]', 'Victim', '2025-03-02 22:36:19', 'Pending', 75.0),
('2025-03-01', 'Work', 'Emotional', '["Manager criticized me", "I feel bad"]', 'Victim', '2025-03-03 08:15:30', 'Pending', 50.0),
('2025-03-02', 'Outside', 'Economic', '["Robbed on street", "I''m shaken"]', 'Victim', '2025-03-03 09:30:41', 'Pending', 60.0)
    ]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO reports (incident_date, location, incident_type, description, witness, submission_date, status, distress_percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, sample_data)
        conn.commit()
        cursor.close()
        conn.close()
        print("Sample data inserted")
    except Exception as e:
        print(f"Error inserting sample data: {e}")



# def deleterow():
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         DELETE FROM reports WHERE report_id = 73;
#     """)
#     conn.commit()  # Commit the transaction
#     cursor.close()
#     conn.close()
#     print("Deleted report with ID 73 if it existed.")


if __name__ == "__main__":
    setup_database()
    # deleterow()
    # insertinitial()
    socketio.run(app, debug=True, host='0.0.0.0', port=3000)
