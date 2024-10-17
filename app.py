from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, case
from datetime import datetime, timedelta
import json
import io
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
db = SQLAlchemy(app)

class PlannerEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    am = db.Column(db.String(100))
    pm = db.Column(db.String(100))
    overnight = db.Column(db.String(100))
    plans = db.Column(db.String(200))
    family_plans = db.Column(db.String(200))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_week', methods=['POST'])
def get_week():
    data = request.json

    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = start_date + timedelta(days=6)
    
    entries = PlannerEntry.query.filter(PlannerEntry.date.between(start_date, end_date)).all()
 
    week_data = []
    for i in range(7):
        current_date = start_date + timedelta(days=i)

        entry = next((e for e in entries if e.date == current_date), None)
        
        if entry:
            week_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'am': entry.am or '',
                'pm': entry.pm or '',
                'overnight': entry.overnight or '',
                'plans': entry.plans or '',
                'family_plans': entry.family_plans or ''
            })
        else:
            week_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'am': '',
                'pm': '',
                'overnight': '',
                'plans': '',
                'family_plans': ''
            })
    
    return jsonify(week_data)

@app.route('/save_entry', methods=['POST'])
def save_entry():
    data = request.json
    date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    
    entry = PlannerEntry.query.filter_by(date=date).first()
    if not entry:
        entry = PlannerEntry(date=date)
    
    if 'am' in data:
        entry.am = data['am']
    if 'pm' in data:
        entry.pm = data['pm']
    if 'overnight' in data:
        entry.overnight = data['overnight']
    if 'plans' in data:
        entry.plans = data['plans']
    if 'family_plans' in data:
        entry.family_plans = data['family_plans']
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            for row in csv_input:
 
                date = datetime.strptime(row['date'], '%Y-%m-%d').date()

                entry = PlannerEntry.query.filter_by(date=date).first()
                if not entry:
                    entry = PlannerEntry(date=date)
                
                entry.am = row.get('am', '')
                entry.pm = row.get('pm', '')
                entry.overnight = row.get('overnight', '')
                entry.plans = row.get('plans', '')
                entry.family_plans = row.get('family_plans', '')

                db.session.add(entry)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Invalid file type'})
   

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)