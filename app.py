# app.py
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class FamilyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    entries = relationship("PlannerEntry", back_populates="family_member", cascade="all, delete-orphan")

class PlannerEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    am = db.Column(db.String(100))
    pm = db.Column(db.String(100))
    overnight = db.Column(db.String(100))
    plans = db.Column(db.String(200))
    family_plans = db.Column(db.String(200))
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=False)
    family_member = relationship("FamilyMember", back_populates="entries")

migrate = Migrate(app, db)

@app.cli.command("init-db")
def init_db():
    with app.app_context():
        db.create_all()
        # Check if there are any family members
        if FamilyMember.query.first() is None:
            default_member = FamilyMember(name="Default Family Member")
            db.session.add(default_member)
            db.session.commit()
            print('Created default family member.')
        else:
            print('Database already initialized.')

@app.route('/')
def index():
    family_members = FamilyMember.query.all()
    return render_template('index.html', family_members=family_members)

@app.route('/settings')
def settings():
    family_members = FamilyMember.query.all()
    return render_template('settings.html', family_members=family_members)

@app.route('/add_family_member', methods=['POST'])
def add_family_member():
    name = request.form.get('name')
    if name:
        new_member = FamilyMember(name=name)
        db.session.add(new_member)
        db.session.commit()
    return redirect(url_for('settings'))

@app.route('/remove_family_member/<int:member_id>', methods=['POST'])
def remove_family_member(member_id):
    member = FamilyMember.query.get_or_404(member_id)
    
    try:
        db.session.delete(member)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Family member {member.name} and all associated entries have been removed.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_week', methods=['POST'])
def get_week():
    data = request.json
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = start_date + timedelta(days=6)
    family_member_id = data.get('family_member_id')
    
    entries = PlannerEntry.query.filter(
        PlannerEntry.date.between(start_date, end_date),
        PlannerEntry.family_member_id == family_member_id
    ).all()
    
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
    family_member_id = data.get('family_member_id')
    
    entry = PlannerEntry.query.filter_by(date=date, family_member_id=family_member_id).first()
    if not entry:
        entry = PlannerEntry(date=date, family_member_id=family_member_id)
    
    for field in ['am', 'pm', 'overnight', 'plans', 'family_plans']:
        if field in data:
            setattr(entry, field, data[field])
    
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/import_csv', methods=['POST'])
@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    family_member_id = request.form.get('family_member_id')
    
    if not family_member_id:
        return jsonify({'success': False, 'error': 'No family member selected'})
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            for row in csv_input:
                date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                entry = PlannerEntry.query.filter_by(date=date, family_member_id=family_member_id).first()
                if not entry:
                    entry = PlannerEntry(date=date, family_member_id=family_member_id)
                
                for field in ['am', 'pm', 'overnight', 'plans', 'family_plans']:
                    setattr(entry, field, row.get(field, ''))
                
                db.session.add(entry)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Invalid file type'})

@app.route('/export_csv')
def export_csv():
    family_member_id = request.args.get('family_member_id')
    if not family_member_id:
        return jsonify({'success': False, 'error': 'No family member selected'})
    
    family_member = FamilyMember.query.get_or_404(family_member_id)
    entries = PlannerEntry.query.filter_by(family_member_id=family_member_id).order_by(PlannerEntry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['date', 'am', 'pm', 'overnight', 'plans', 'family_plans'])
    
    # Write data
    for entry in entries:
        writer.writerow([
            entry.date.strftime('%Y-%m-%d'),
            entry.am,
            entry.pm,
            entry.overnight,
            entry.plans,
            entry.family_plans
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{family_member.name}_planner_data.csv'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))