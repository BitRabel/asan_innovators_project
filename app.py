from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import qrcode
import os
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import json
from pymongo import MongoClient

# MongoDB setup
MONGO_URI = "mongodb+srv://asaninnovatorsprojectguide:bXsxafE4YWAn0bRb@cluster0.ikhda.mongodb.net/qr_attendance?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["qr_attendance"]
users_collection = db["users"]
attendance_collection = db["attendance"]

app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message="Passwords must match")
    ])
    role = SelectField('Role', choices=[('student', 'Student'), ('teacher', 'Teacher')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# QR Code Generation
def generate_qr(student_id, student_name):
    data = json.dumps({"student_id": student_id, "name": student_name})
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    qr_folder = "static/qr_codes"
    os.makedirs(qr_folder, exist_ok=True)
    file_path = os.path.join(qr_folder, f"{student_id}.png")
    img.save(file_path)
    return file_path

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = generate_password_hash(form.password.data)
        role = form.role.data

        if users_collection.find_one({"username": username}):
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

        users_collection.insert_one({"username": username, "password": password, "role": role})

        if role == "student":
            qr_path = generate_qr(username, username)
            flash("Registration successful! Your QR code has been generated.", "success")
            return render_template('qr_display.html', qr_path=qr_path)
        else:
            flash("Registration successful!", "success")
            return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = users_collection.find_one({"username": username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
        else:
            flash("Invalid username or password!", "danger")
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student', methods=['GET', 'POST'])
def student_dashboard():
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    if request.method == 'POST':
        period = request.form.get('period')
        teacher_id = request.form.get('teacher_id')
        qr_code = request.files.get('qr_code')

        if qr_code:
            image = cv2.imdecode(np.frombuffer(qr_code.read(), np.uint8), cv2.IMREAD_COLOR)
            decoded = decode(image)

            if decoded:
                qr_data = decoded[0].data.decode('utf-8')
                try:
                    qr_info = json.loads(qr_data)
                    student_id = qr_info.get("student_id")
                    student_name = qr_info.get("name")

                    if student_id and student_name:
                        attendance_collection.insert_one({
                            "student_id": student_id,
                            "student_name": student_name,
                            "teacher_id": teacher_id,
                            "period": period,
                            "timestamp": datetime.now()
                        })
                        flash("Attendance marked successfully!", "success")
                    else:
                        flash("QR code data is missing required fields.", "danger")
                except json.JSONDecodeError:
                    flash("Invalid QR code format. Ensure it contains valid JSON data.", "danger")
            else:
                flash("No QR code data found. Please upload a valid QR code.", "danger")

    return render_template('student.html')

@app.route('/teacher', methods=['GET'])
def teacher_dashboard():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))

    attendance_records = attendance_collection.find({"teacher_id": session['username']})
    records = [
        {
            "Student ID": record['student_id'],
            "Student Name": record['student_name'],
            "Period": record['period'],
            "Timestamp": record['timestamp']
        }
        for record in attendance_records
    ]
    return render_template('teacher.html', records=records)

@app.route('/qr_display', methods=['GET'])
def qr_display():
    qr_path = request.args.get('qr_path')
    return render_template('qr_display.html', qr_path=qr_path)

if __name__ == '__main__':
    app.run(debug=True)
