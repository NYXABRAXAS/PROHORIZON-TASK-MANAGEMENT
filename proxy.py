import os
from flask import Flask, send_from_directory, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import pytz 

app = Flask(__name__)
app.secret_key = "prohorizon_secure_key_2026"

# Configuration for POC (Proof) File Uploads
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prohorizon_tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    assignee = db.Column(db.String(100))
    admin = db.Column(db.String(100))
    priority = db.Column(db.String(20)) 
    status = db.Column(db.String(50), default='Pending')
    deadline = db.Column(db.String(50))
    poc_filename = db.Column(db.String(300)) # File path for POC
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

with app.app_context():
    db.create_all()

# --- Auth Helper ---
def is_logged_in():
    return session.get('logged_in', False)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'pro123':
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/logout')
def logout():
    session.pop('logged_in', None)
    return jsonify({"success": True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# --- Main Task APIs ---
@app.route('/api/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        if request.is_json: # For Excel Import
            data_list = request.json if isinstance(request.json, list) else [request.json]
            for item in data_list:
                new_task = Task(
                    subject=item.get('Subject'), assignee=item.get('Assignee'),
                    admin=item.get('Admin') or 'SIMARJEET', priority=item.get('Priority'),
                    status='Pending', deadline=str(item.get('Deadline') or '')
                )
                db.session.add(new_task)
        else: # For Manual Entry with File
            file = request.files.get('poc_file')
            filename = None
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_task = Task(
                subject=request.form.get('subject'), assignee=request.form.get('assignee'),
                admin=request.form.get('admin') or 'SIMARJEET', priority=request.form.get('priority'),
                status='Pending', deadline=request.form.get('deadline'), poc_filename=filename
            )
            db.session.add(new_task)
        db.session.commit()
        return jsonify({"success": True})
    
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        "id": t.id, "subject": t.subject, "assignee": t.assignee, "admin": t.admin,
        "priority": t.priority, "status": t.status, "deadline": t.deadline,
        "poc": t.poc_filename, "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
    } for t in tasks])

@app.route('/api/tasks/update/<int:id>', methods=['POST'])
def update_task(id):
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    task = Task.query.get(id)
    data = request.json
    task.status = data.get('status', task.status)
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
