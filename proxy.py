import os
from flask import Flask, send_from_directory, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import pytz

app = Flask(__name__)
app.secret_key = "prohorizon_secure_key_2026"

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prohorizon_tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    assignee = db.Column(db.String(100))
    admin = db.Column(db.String(100))
    priority = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Pending')
    remark = db.Column(db.Text)
    deadline = db.Column(db.String(50))
    poc_filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

with app.app_context():
    db.create_all()

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

@app.route('/api/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'POST':
        if request.is_json:
            # Bulk import from Excel
            data_list = request.json if isinstance(request.json, list) else [request.json]
            for item in data_list:
                task = Task(
                    subject=item.get('Subject') or item.get('subject', ''),
                    assignee=item.get('Assignee') or item.get('assignee', ''),
                    admin=item.get('Admin') or item.get('admin', ''),
                    priority=item.get('Priority') or item.get('priority', 'Normal'),
                    deadline=str(item.get('Deadline') or item.get('deadline') or '')
                )
                db.session.add(task)
        else:
            # Manual task (with file)
            file = request.files.get('poc_file')
            filename = None
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            task = Task(
                subject=request.form.get('subject', '').strip(),
                assignee=request.form.get('assignee', '').strip(),
                admin=request.form.get('admin', '').strip(),
                priority=request.form.get('priority', 'Normal'),
                status=request.form.get('status', 'Pending'),
                remark=request.form.get('remark', ''),
                deadline=request.form.get('deadline', ''),
                poc_filename=filename
            )
            db.session.add(task)

        db.session.commit()          # ← FORCE COMMIT
        return jsonify({"success": True})

    # GET all tasks
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        "id": t.id,
        "subject": t.subject,
        "assignee": t.assignee,
        "admin": t.admin,
        "priority": t.priority,
        "status": t.status,
        "remark": t.remark,
        "deadline": t.deadline,
        "poc": t.poc_filename,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
    } for t in tasks])

@app.route('/api/tasks/<int:id>', methods=['PUT', 'DELETE'])
def task_by_id(id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    task = Task.query.get_or_404(id)

    if request.method == 'DELETE':
        if task.poc_filename:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], task.poc_filename))
            except:
                pass
        db.session.delete(task)
        db.session.commit()
        return jsonify({"success": True})

    elif request.method == 'PUT':
        data = request.json
        task.subject = data.get('subject', task.subject)
        task.assignee = data.get('assignee', task.assignee)
        task.admin = data.get('admin', task.admin)
        task.priority = data.get('priority', task.priority)
        task.status = data.get('status', task.status)
        task.remark = data.get('remark', task.remark)
        task.deadline = data.get('deadline', task.deadline)
        db.session.commit()
        return jsonify({"success": True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
