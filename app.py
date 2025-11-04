from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random, string, time

app = Flask(__name__)
app.secret_key = 'projectx_secret'

# ------------------- DATABASE CONFIG -------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------- MODELS -------------------
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    address = db.Column(db.String(250))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    diagnosis = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship('Appointment', backref='patient', cascade='all,delete-orphan')
    bills = db.relationship('Bill', backref='patient', cascade='all,delete-orphan')


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    doctor = db.Column(db.String(120))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    reason = db.Column(db.String(300))
    status = db.Column(db.String(40), default='Upcoming')


class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    status = db.Column(db.String(30), default='Pending')
    transaction_id = db.Column(db.String(120))
    description = db.Column(db.String(300))
    date_issued = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------- UTIL -------------------
def random_txn(prefix='TX'):
    """Generate a random transaction ID"""
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ------------------- DATABASE INIT -------------------
with app.app_context():
    db.create_all()

    if Patient.query.count() == 0:
        p1 = Patient(name='John Doe', email='john@example.com', phone='254712345678',
                     address='Embu Campus', age=30, gender='Male', diagnosis='Flu')
        p2 = Patient(name='Mary Jane', email='mary@example.com', phone='254712345679',
                     address='Nairobi', age=25, gender='Female', diagnosis='Allergy')
        db.session.add_all([p1, p2])
        db.session.commit()

        a = Appointment(patient_id=p1.id, doctor='Dr. Wanjiku',
                        date='2025-11-01', time='09:00', reason='Checkup')
        b = Bill(patient_id=p1.id, amount=2500.0, payment_method='Cash',
                 status='Paid', transaction_id=random_txn('CASH'))
        db.session.add_all([a, b])
        db.session.commit()

# ------------------- ROUTES -------------------
@app.route('/')
def dashboard():
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    unpaid_bills = Bill.query.filter_by(status='Pending').count()
    total_billing = sum((b.amount for b in Bill.query.all()), 0)

    recent_appointments = Appointment.query.order_by(Appointment.id.desc()).limit(5).all()
    recent_bills = Bill.query.order_by(Bill.date_issued.desc()).limit(5).all()
    notifications = [{'message': 'Welcome to Project_X', 'time': 'Now'}]

    return render_template('dashboard.html',
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           unpaid_bills=unpaid_bills,
                           total_billing=int(total_billing),
                           recent_appointments=recent_appointments,
                           recent_bills=recent_bills,
                           notifications=notifications)

# -------- Patients --------
@app.route('/patients')
def patients():
    all_patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template('patients.html', patients=all_patients)

@app.route('/patient/add', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        try:
            p = Patient(
                name=request.form.get('name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                age=int(request.form.get('age') or 0),
                gender=request.form.get('gender'),
                diagnosis=request.form.get('diagnosis')
            )
            db.session.add(p)
            db.session.commit()
            flash('Patient added successfully', 'success')
        except Exception as e:
            flash(f'Error adding patient: {e}', 'danger')
        return redirect(url_for('patients'))
    return render_template('add_patient.html')

@app.route('/patient/edit/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    p = Patient.query.get_or_404(id)
    if request.method == 'POST':
        try:
            p.name = request.form.get('name')
            p.email = request.form.get('email')
            p.phone = request.form.get('phone')
            p.address = request.form.get('address')
            p.age = int(request.form.get('age') or 0)
            p.gender = request.form.get('gender')
            p.diagnosis = request.form.get('diagnosis')
            db.session.commit()
            flash('Patient updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating: {e}', 'danger')
        return redirect(url_for('patients'))
    return render_template('edit_patient.html', patient=p)

@app.route('/patient/delete/<int:id>', methods=['POST'])
def delete_patient(id):
    p = Patient.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Patient deleted', 'warning')
    return redirect(url_for('patients'))

@app.route('/api/patient/<int:id>')
def api_patient(id):
    p = Patient.query.get_or_404(id)
    appts = [{'id': a.id, 'doctor': a.doctor, 'date': a.date, 'time': a.time,
              'reason': a.reason, 'status': a.status} for a in p.appointments]
    bills = [{'id': b.id, 'amount': b.amount, 'method': b.payment_method,
              'status': b.status, 'txn': b.transaction_id,
              'desc': b.description, 'date': b.date_issued} for b in p.bills]
    return jsonify({
        'id': p.id, 'name': p.name, 'email': p.email, 'phone': p.phone,
        'address': p.address, 'age': p.age, 'gender': p.gender,
        'diagnosis': p.diagnosis, 'appointments': appts, 'bills': bills
    })

# -------- Appointments --------
@app.route('/appointments')
def appointments():
    return render_template('appointments.html',
                           appointments=Appointment.query.order_by(Appointment.date.asc()).all(),
                           patients=Patient.query.all())

@app.route('/appointment/add', methods=['POST'])
def add_appointment():
    pid = int(request.form.get('patient_id'))
    a = Appointment(
        patient_id=pid,
        doctor=request.form.get('doctor_name'),
        date=request.form.get('date'),
        time=request.form.get('time'),
        reason=request.form.get('reason')
    )
    db.session.add(a)
    db.session.commit()
    flash('Appointment added', 'success')
    return redirect(url_for('appointments'))

@app.route('/appointment/delete/<int:id>', methods=['POST'])
def delete_appointment(id):
    a = Appointment.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    flash('Appointment deleted', 'warning')
    return redirect(url_for('appointments'))

# -------- Billing System --------
@app.route('/billing')
def billing():
    bills = Bill.query.order_by(Bill.date_issued.desc()).all()
    patients = Patient.query.all()
    return render_template('billing.html', bills=bills, patients=patients)

@app.route('/bill/add', methods=['POST'])
def add_bill():
    pid = int(request.form.get('patient_id'))
    amount = float(request.form.get('amount') or 0)
    method = request.form.get('payment_method')
    desc = request.form.get('description')

    b = Bill(patient_id=pid, amount=amount, payment_method=method,
             description=desc, status='Pending')
    db.session.add(b)
    db.session.commit()
    flash('Bill created successfully', 'success')
    return redirect(url_for('billing'))

@app.route('/bill/delete/<int:id>', methods=['POST'])
def delete_bill(id):
    b = Bill.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    flash('Bill deleted', 'warning')
    return redirect(url_for('billing'))

@app.route('/pay/simulate', methods=['POST'])
def simulate_pay():
    data = request.get_json() or {}
    bill_id = int(data.get('bill_id'))
    method = data.get('method')
    phone = data.get('phone')

    time.sleep(2)  # simulate payment delay

    b = Bill.query.get_or_404(bill_id)
    b.payment_method = method
    b.transaction_id = random_txn('MP')
    b.status = 'Paid'
    db.session.commit()
    return jsonify({'status': 'ok', 'txn': b.transaction_id})

# -------- Settings & About --------
@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ------------------- RUN APP -------------------
if __name__ == '__main__':
    app.run(debug=True)
