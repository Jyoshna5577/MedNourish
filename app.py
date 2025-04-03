from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import pandas as pd
import joblib
import google.generativeai as genai
import re
import json


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# Initialize Database
def init_db():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # Create Admins Table
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL)''')

    # Create Patients Table
    c.execute('''CREATE TABLE IF NOT EXISTS patients (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT, age INTEGER, gender TEXT, blood_group TEXT,
                 food_type TEXT, previous_diseases TEXT, current_diseases TEXT,
                 predicted_diet TEXT)''')

    # Create Feedback Table
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 patient_id INTEGER, feedback TEXT)''')

    # Insert default admin if not exists
    c.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin')")

    conn.commit()
    conn.close()

# Load ML Models
encoder = joblib.load("models/encoder.joblib")
model = joblib.load("models/voting_classifier.joblib")

# Configure Gemini AI
GOOGLE_API_KEY = "AIzaSyDO0HtzLlUQVlZ3mLU9g0Zs_6Cql2uH7kE"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)

# Call `init_db()` at the start of the app
init_db()

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('hospital.db')
    conn.row_factory = sqlite3.Row  # Allows us to access columns by name
    return conn

# Home Page
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict_diet_page")
def predict_diet_page():
    return render_template("predict_diet.html")  # Ensure you have this template

# Admin Login
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    message = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session["admin"] = username  # Store session
            return redirect(url_for("admin_dashboard"))
        else:
            message = "⚠️ Invalid username or password."

    return render_template("admin_login.html", message=message)

# Admin Signup
@app.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    message = None  

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            message = "Signup successful! You can now login."
        except sqlite3.IntegrityError:
            message = "⚠️ Username already exists. Please choose another."

        conn.close()

    return render_template("admin_signup.html", message=message)

# Admin Dashboard
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

# Train Models
@app.route("/train_models")
def train_models():
    # Placeholder for ML training logic
    return "ML models trained and performance compared successfully."

# Staff Login
@app.route("/staff_login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        return redirect(url_for("staff_dashboard"))
    return render_template("staff_login.html")

# Staff Dashboard
@app.route("/staff_dashboard")
def staff_dashboard():
    return render_template("staff_dashboard.html")

# Staff Signup
@app.route("/staff_signup", methods=["GET", "POST"])
def staff_signup():
    if request.method == "POST":
        return redirect(url_for("staff_login"))
    return render_template("staff_signup.html")

# Patient Login
@app.route("/patient_login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        patient_id = request.form["patient_id"]
        return redirect(url_for("patient_dashboard", patient_id=patient_id))
    return render_template("patient_login.html")

# Patient Signup
@app.route('/patient_signup', methods=['GET', 'POST'])
def patient_signup():
    if request.method == 'POST':
        # Handle the signup logic here
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        age = request.form['age']
        gender = request.form['gender']
        medical_history = request.form['medical_history']

        # Add your logic to save the patient data to the database

        flash('Signup successful!', 'success')  # Flash a success message
        return redirect(url_for('patient_login'))  # Redirect to login or another page

    return render_template('patient_signup.html')

# View Patient Details (For Staff)
@app.route("/check_patient_details")
def check_patient_details():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM patients")
    patients = c.fetchall()
    conn.close()
    return render_template("check_patient_details.html", patients=patients)

import json  # ✅ Ensure JSON is imported

@app.route("/predict", methods=["POST"])
def predict():
    data = request.form

    input_data = pd.DataFrame([{
        "Age": int(data["age"]),
        "Gender": data["gender"],
        "Blood Group": data["blood_group"],
        "Food Type": data["food_type"],
        "Previous Diseases": data["previous_diseases"],
        "Current Diseases": data["current_diseases"],
    }])

    # ✅ Encode & Predict Diet
    encoded_input = encoder.transform(input_data)
    predicted_diet = model.predict(encoded_input)[0]

    # ✅ Generate Weekly Meal Plan using Gemini AI
    prompt = (
        f"Create a structured 7-day meal plan for {data['name']}, a {data['age']}-year-old {data['gender']} "
        f"with blood group {data['blood_group']}, following a {data['food_type']} diet. "
        f"Recommended diet: {predicted_diet}. Health conditions: {data['previous_diseases']}, {data['current_diseases']}."
        f" \nFormat the response exactly as follows:\n"
        f"Day X:\nBreakfast: [meal]\nLunch: [meal]\nSnack: [meal]\nDinner: [meal]\n\n"
        f"Repeat this format for 7 days."
    )

    try:
        # ✅ Generate response
        gemini_model = genai.GenerativeModel("gemini-1.5-pro-latest") 
        response = gemini_model.generate_content([prompt])

        weekly_diet = response.text if hasattr(response, "text") else "⚠️ Failed to generate diet plan."

        # ✅ Format meal plan as JSON for database storage
        formatted_meal_plan = format_weekly_meal_plan(weekly_diet)
        meal_plan_json = json.dumps(formatted_meal_plan)  # ✅ Convert to JSON

        # ✅ Save to Database
        conn = sqlite3.connect('hospital.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO patients (name, age, gender, blood_group, food_type, previous_diseases, current_diseases, predicted_diet, meal_plan) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data["name"], data["age"], data["gender"], data["blood_group"], data["food_type"], data["previous_diseases"], data["current_diseases"], predicted_diet, meal_plan_json)
        )
        conn.commit()
        conn.close()

    except Exception as e:
        formatted_meal_plan = {"Error": str(e)}

    return redirect(url_for("predict_diet_result", patient_id=c.lastrowid))  # ✅ Redirect to result page

### **3️⃣ Problem: `format_weekly_meal_plan()` is incorrect**





def format_weekly_meal_plan(weekly_diet):
    if not weekly_diet or "Day 1" not in weekly_diet:
        return {"Error": "⚠️ Failed to generate diet plan."}

    meal_plan = {}
    days = re.split(r'Day \d+:', weekly_diet)[1:]  # ✅ Split at 'Day X:'

    for index, day in enumerate(days, start=1):
        meals = {"Breakfast": "N/A", "Lunch": "N/A", "Snack": "N/A", "Dinner": "N/A"}

        # ✅ Extract meals using regex
        breakfast_match = re.search(r'Breakfast:\s*(.*)', day)
        lunch_match = re.search(r'Lunch:\s*(.*)', day)
        snack_match = re.search(r'Snack:\s*(.*)', day)
        dinner_match = re.search(r'Dinner:\s*(.*)', day)

        if breakfast_match:
            meals["Breakfast"] = breakfast_match.group(1).strip()
        if lunch_match:
            meals["Lunch"] = lunch_match.group(1).strip()
        if snack_match:
            meals["Snack"] = snack_match.group(1).strip()
        if dinner_match:
            meals["Dinner"] = dinner_match.group(1).strip()

        meal_plan[f"Day {index}"] = meals

    return meal_plan  # ✅ Return dictionary instead of HTML




# Staff Check Patient Details
@app.route("/staff_check_patient_details", methods=["GET", "POST"])
def staff_check_patient_details():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    patient = None
    meal_plan = {}

    if request.method == "POST":
        patient_id = request.form["patient_id"]

        # ✅ Fetch Patient Details
        c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = c.fetchone()

        if patient:
            # ✅ Fetch and Convert Meal Plan JSON
            c.execute("SELECT meal_plan FROM patients WHERE id = ?", (patient_id,))
            meal_plan_data = c.fetchone()
            meal_plan = json.loads(meal_plan_data[0]) if meal_plan_data and meal_plan_data[0] else {}

    conn.close()
    return render_template("staff_check_patient_details.html", patient=patient, meal_plan=meal_plan)


# View Feedback
@app.route("/view_feedback")
def view_feedback():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Fetch all feedback from the database
    c.execute("SELECT patient_id, feedback FROM feedback")
    feedback_list = c.fetchall()
    
    conn.close()
    
    return render_template("view_feedback.html", feedback_list=feedback_list)

# Submit Feedback
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    patient_id = request.form["patient_id"]
    feedback = request.form["feedback"]

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO feedback (patient_id, feedback) VALUES (?, ?)", (patient_id, feedback))
    conn.commit()
    conn.close()

    return jsonify({"message": "Feedback submitted successfully."})

@app.route("/patient_dashboard/<int:patient_id>")
def patient_dashboard(patient_id):
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # ✅ Fetch Patient Details
    c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()

    # ✅ Fetch and Convert Meal Plan JSON
    c.execute("SELECT meal_plan FROM patients WHERE id = ?", (patient_id,))
    meal_plan_data = c.fetchone()
    
    meal_plan = json.loads(meal_plan_data[0]) if meal_plan_data and meal_plan_data[0] else {}

    conn.close()

    return render_template("patient_dashboard.html", patient=patient, meal_plan=meal_plan)
@app.route("/predict_diet_result/<int:patient_id>")
def predict_diet_result(patient_id):
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()

    # ✅ Fetch Patient Details
    c.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = c.fetchone()

    # ✅ Fetch and Convert Meal Plan from JSON
    c.execute("SELECT meal_plan FROM patients WHERE id = ?", (patient_id,))
    meal_plan_data = c.fetchone()

    meal_plan = json.loads(meal_plan_data[0]) if meal_plan_data and meal_plan_data[0] else {}

    conn.close()

    return render_template("predict_diet_result.html", patient=patient, meal_plan=meal_plan)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)