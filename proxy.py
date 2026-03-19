import os
from flask import Flask, send_from_directory, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz 
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Folder to store POC files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prohorizon_tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Task Database Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    assignee = db.Column(db.String(100))
    admin = db.Column(db.String(100))
    priority = db.Column(db.String(20)) 
    status = db.Column(db.String(50), default='Pending')
    remark = db.Column(db.Text, default='')
    deadline = db.Column(db.String(50))
    poc_filename = db.Column(db.String(200)) 
    # Captures exact India Time
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API to Fetch and Create Tasks (Supports Manual & Bulk Import)
@app.route('/api/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if request.method == 'POST':
        data = request.json
        tasks_to_add = data if isinstance(data, list) else [data]
        
        for item in tasks_to_add:
            new_task = Task(
                subject=item.get('subject') or item.get('Subject'),
                assignee=item.get('assignee') or item.get('Assignee'),
                admin=item.get('admin') or item.get('Admin'),
                priority=item.get('priority') or item.get('Priority') or 'Normal',
                status=item.get('status') or item.get('Status') or 'Pending',
                remark=item.get('remark') or item.get('Remark') or '',
                deadline=item.get('deadline') or item.get('Deadline') or ''
            )
            db.session.add(new_task)
        
        db.session.commit()
        return jsonify({"message": "Success"})
    
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    output = []
    for t in tasks:
        output.append({
            "id": t.id, 
            "subject": t.subject, 
            "assignee": t.assignee,
            "admin": t.admin, 
            "priority": t.priority,
            "status": t.status, 
            "remark": t.remark,
            "deadline": t.deadline,
            "poc_filename": t.poc_filename,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M") #
        })
    return jsonify(output)

# API to Update Task via Modal
@app.route('/api/tasks/update', methods=['POST'])
def update_task():
    data = request.json
    task = Task.query.get(data['id'])
    if not task: return jsonify({"error": "Not found"}), 404
    
    if 'status' in data: task.status = data['status']
    if 'remark' in data: task.remark = data['remark']
    if 'priority' in data: task.priority = data['priority']
    if 'subject' in data: task.subject = data['subject']
    
    db.session.commit()
    return jsonify({"success": True})

# API to Upload POC
@app.route('/api/tasks/upload/<int:task_id>', methods=['POST'])
def upload_poc(task_id):
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    file = request.files['file']
    task = Task.query.get(task_id)
    if file and task:
        filename = secure_filename(f"POC_{task_id}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        task.poc_filename = filename
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Failed"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
