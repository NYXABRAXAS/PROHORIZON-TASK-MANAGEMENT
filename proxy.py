from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
# Database will be created in the same folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prohorizon_tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Task Database Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    assignee = db.Column(db.String(100))
    assigned_by = db.Column(db.String(100))
    priority = db.Column(db.String(20)) 
    status = db.Column(db.String(20), default='Pending')
    deadline = db.Column(db.String(20))
    remark = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize Database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# Fetch and Create Tasks
@app.route('/api/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if request.method == 'POST':
        data = request.json
        new_task = Task(
            subject=data['subject'],
            assignee=data['assignee'],
            assigned_by=data['assigned_by'],
            priority=data['priority'],
            deadline=data['deadline']
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify({"message": "Success"})
    
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    output = []
    for t in tasks:
        age_delta = datetime.utcnow() - t.created_at
        age_str = f"{age_delta.days}d {age_delta.seconds//3600}h"
        output.append({
            "id": t.id, "subject": t.subject, "assignee": t.assignee,
            "assigned_by": t.assigned_by, "priority": t.priority,
            "status": t.status, "deadline": t.deadline,
            "remark": t.remark, "age": age_str
        })
    return jsonify(output)

# Bulk Import from Excel
@app.route('/api/tasks/import', methods=['POST'])
def import_tasks():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    try:
        df = pd.read_excel(file)
        # Required Columns: Subject, Assignee, Assigned_By, Priority, Deadline
        for _, row in df.iterrows():
            new_task = Task(
                subject=str(row['Subject']),
                assignee=str(row['Assignee']),
                assigned_by=str(row['Assigned_By']),
                priority=str(row['Priority']),
                deadline=str(row['Deadline']),
                remark=str(row.get('Remark', ''))
            )
            db.session.add(new_task)
        db.session.commit()
        return jsonify({"message": f"Successfully imported {len(df)} tasks"})
    except Exception as e:
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

# Update Remarks or Assignee
@app.route('/api/tasks/update', methods=['POST'])
def update_task():
    data = request.json
    task = Task.query.get(data['id'])
    if not task: return jsonify({"error": "Not found"}), 404
    if 'remark' in data: task.remark = data['remark']
    if 'status' in data: task.status = data['status']
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)