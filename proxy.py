import os
from flask import Flask, send_from_directory, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz 

app = Flask(__name__)
app.secret_key = "prohorizon_secure_key_2026" # Change this for production

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
    remark = db.Column(db.Text, default='')
    deadline = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))

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
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/logout')
def logout():
    session.pop('logged_in', None)
    return jsonify({"success": True})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# --- Task APIs ---
@app.route('/api/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        data = request.json
        tasks_to_add = data if isinstance(data, list) else [data]
        for item in tasks_to_add:
            new_task = Task(
                subject=item.get('subject') or item.get('Subject'),
                assignee=item.get('assignee') or item.get('Assignee'),
                admin='simarjeet',
                priority=item.get('priority') or 'Normal',
                status=item.get('status') or 'Pending',
                remark=item.get('remark') or '',
                deadline=item.get('deadline') or ''
            )
            db.session.add(new_task)
            db.session.add(History(action=f"Created: {new_task.subject}"))
        db.session.commit()
        return jsonify({"success": True})
    
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        "id": t.id, "subject": t.subject, "assignee": t.assignee, "priority": t.priority, 
        "status": t.status, "remark": t.remark, "deadline": t.deadline, 
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
    } for t in tasks])

@app.route('/api/tasks/update/<int:id>', methods=['POST'])
def update_task(id):
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    task = Task.query.get(id)
    if not task: return jsonify({"error": "Not found"}), 404
    data = request.json
    task.subject = data.get('subject', task.subject)
    task.assignee = data.get('assignee', task.assignee)
    task.priority = data.get('priority', task.priority)
    task.status = data.get('status', task.status)
    task.remark = data.get('remark', task.remark)
    task.deadline = data.get('deadline', task.deadline)
    db.session.add(History(action=f"Updated Task #{id}"))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/tasks/delete', methods=['POST'])
def delete_tasks():
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    ids = request.json.get('ids', [])
    Task.query.filter(Task.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/api/history', methods=['GET'])
def get_history():
    if not is_logged_in(): return jsonify({"error": "Unauthorized"}), 401
    logs = History.query.order_by(History.timestamp.desc()).limit(50).all()
    return jsonify([{"action": l.action, "time": l.timestamp.strftime("%Y-%m-%d %H:%M")} for l in logs])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
