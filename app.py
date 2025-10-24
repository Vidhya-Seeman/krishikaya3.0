# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('KRISHI_SECRET', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'krishikaya.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------- MODELS -----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # admin, landowner, labor, machinery
    name = db.Column(db.String(150))
    address = db.Column(db.String(300))
    contact = db.Column(db.String(50))
    district = db.Column(db.String(100))
    acres = db.Column(db.Integer)        # for landowner
    crops = db.Column(db.String(300))   # for landowner
    machine_type = db.Column(db.String(150))  # for machinery
    num_labors = db.Column(db.Integer)  # optional for laborer

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    landowner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_date = db.Column(db.String(50))
    days = db.Column(db.Integer)
    service_type = db.Column(db.String(20))  # 'labor','machinery','both'
    num_labor = db.Column(db.Integer, nullable=True)
    machine_type = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(50), default='Pending')

class BookingResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    response = db.Column(db.String(10))  # Accept / Reject

# ----------------- DB init -----------------
@app.before_first_request
def create_tables():
    db.create_all()
    # seed 3 admin users if missing
    for i in range(1,4):
        uname = f'admin{i}'
        if not User.query.filter_by(username=uname).first():
            db.session.add(User(username=uname, password='adminpass', role='admin', name=f'Admin {i}'))
    db.session.commit()

# ----------------- Helpers -----------------
def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

# ----------------- Routes -----------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register/<role>', methods=['GET','POST'])
def register(role):
    if role not in ('landowner','labor','machinery','admin'):
        flash('Invalid role', 'danger')
        return redirect(url_for('home'))
    if request.method == 'POST':
        data = request.form
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not username or not password:
            flash('Provide username and password', 'warning')
            return redirect(request.url)
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'warning')
            return redirect(request.url)
        u = User(
            username=username,
            password=password,
            role=role,
            name=data.get('name'),
            address=data.get('address'),
            contact=data.get('contact'),
            district=data.get('district'),
            acres=int(data.get('acres')) if data.get('acres') else None,
            crops=data.get('crops'),
            machine_type=data.get('machine_type'),
            num_labors=int(data.get('num_labors')) if data.get('num_labors') else None
        )
        db.session.add(u)
        db.session.commit()
        flash(f'{role.capitalize()} registered. Please login.', 'success')
        return redirect(url_for('login'))
    # try role-specific template; fallback to generic if not present
    tpl = f'register_{role}.html'
    try:
        return render_template(tpl, role=role)
    except:
        return render_template('register_generic.html', role=role)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        uname = (request.form.get('username') or '').strip()
        pw = request.form.get('password') or ''
        user = User.query.filter_by(username=uname, password=pw).first()
        if not user:
            flash('Invalid credentials', 'danger')
            return redirect(request.url)
        session['user_id'] = user.id
        session['role'] = user.role
        flash(f'Welcome {user.name or user.username}', 'success')
        if user.role == 'admin': return redirect(url_for('admin_dashboard'))
        if user.role == 'landowner': return redirect(url_for('landowner_dashboard'))
        if user.role == 'labor': return redirect(url_for('labor_dashboard'))
        if user.role == 'machinery': return redirect(url_for('machinery_dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('home'))

# Landowner dashboard & booking
@app.route('/landowner', methods=['GET','POST'])
def landowner_dashboard():
    user = current_user()
    if not user or user.role != 'landowner':
        flash('Please login as landowner', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = request.form
        booking = Booking(
            landowner_id=user.id,
            service_date=data.get('service_date'),
            days=int(data.get('days') or 1),
            service_type=data.get('service_type'),
            num_labor=int(data.get('num_labor')) if data.get('num_labor') else None,
            machine_type=data.get('machine_type') or None,
            status='Pending'
        )
        db.session.add(booking)
        db.session.commit()
        flash(f'Booking created (ID: {booking.id})', 'success')
        return redirect(url_for('landowner_dashboard'))

    bookings = Booking.query.filter_by(landowner_id=user.id).order_by(Booking.id.desc()).all()
    bookings_info = []
    for b in bookings:
        brs = BookingResponse.query.filter_by(booking_id=b.id).all()
        accepted_labors = [ (User.query.get(r.user_id).name or User.query.get(r.user_id).username)
                            for r in brs if r.response=='Accept' and User.query.get(r.user_id).role=='labor' ]
        accepted_machines = [ (User.query.get(r.user_id).name or User.query.get(r.user_id).username)
                            for r in brs if r.response=='Accept' and User.query.get(r.user_id).role=='machinery' ]
        bookings_info.append({
            'id': b.id,
            'service_date': b.service_date,
            'days': b.days,
            'service_type': b.service_type,
            'num_labor': b.num_labor,
            'machine_type': b.machine_type,
            'status': b.status,
            'accepted_labors': accepted_labors,
            'accepted_machines': accepted_machines
        })
    return render_template('landowner_dashboard.html', landowner=user, bookings=bookings_info)

# Labor dashboard (kept as-is; should be working)
@app.route('/labor', methods=['GET','POST'])
def labor_dashboard():
    user = current_user()
    if not user or user.role != 'labor':
        flash('Please login as laborer', 'warning')
        return redirect(url_for('login'))

    raw = Booking.query.filter(Booking.service_type.in_(['labor','both'])).order_by(Booking.id.desc()).all()
    bookings_info = []
    for b in raw:
        lo = User.query.get(b.landowner_id)
        bookings_info.append({
            'id': b.id,
            'landowner_id': b.landowner_id,
            'landowner_name': (lo.name or lo.username) if lo else 'Unknown',
            'service_date': b.service_date,
            'days': b.days,
            'service_type': b.service_type,
            'num_labor': b.num_labor,
            'status': b.status
        })

    if request.method == 'POST':
        booking_id_raw = request.form.get('booking_id')
        response = request.form.get('response')
        try:
            booking_id = int(booking_id_raw)
        except:
            flash('Invalid booking id', 'danger')
            return redirect(url_for('labor_dashboard'))

        if BookingResponse.query.filter_by(booking_id=booking_id, user_id=user.id).first():
            flash('You already responded', 'info')
            return redirect(url_for('labor_dashboard'))

        br = BookingResponse(booking_id=booking_id, user_id=user.id, response=response)
        db.session.add(br)
        db.session.commit()
        flash(f'You {response} booking {booking_id}', 'success')

        # recompute labor acceptance/rejection
        all_responses = BookingResponse.query.filter_by(booking_id=booking_id).all()
        total_labor = User.query.filter_by(role='labor').count()
        labor_accepts = len([r for r in all_responses if User.query.get(r.user_id).role=='labor' and r.response=='Accept'])
        labor_rejects = len([r for r in all_responses if User.query.get(r.user_id).role=='labor' and r.response=='Reject'])
        booking = Booking.query.get(booking_id)
        if labor_accepts > 0:
            if booking.service_type == 'both':
                m_accepts = len([r for r in all_responses if User.query.get(r.user_id).role=='machinery' and r.response=='Accept'])
                booking.status = 'Confirmed' if m_accepts>0 else 'Confirmed (Labor)'
            else:
                booking.status = 'Confirmed'
        else:
            if total_labor>0 and labor_rejects>=total_labor:
                if booking.service_type == 'labor':
                    booking.status = 'Rejected'
                elif booking.service_type == 'both':
                    total_mach = User.query.filter_by(role='machinery').count()
                    mach_rejects = len([r for r in all_responses if User.query.get(r.user_id).role=='machinery' and r.response=='Reject'])
                    if total_mach>0 and mach_rejects>=total_mach:
                        booking.status = 'Rejected'
        db.session.commit()
        return redirect(url_for('labor_dashboard'))

    return render_template('labor_dashboard.html', labor=user, bookings=bookings_info)

# ----------------- ROBUST MACHINERY DASHBOARD -----------------
@app.route('/machinery', methods=['GET','POST'])
def machinery_dashboard():
    user = current_user()
    if not user or user.role != 'machinery':
        flash('Please login as machinery owner', 'warning')
        return redirect(url_for('login'))

    # fetch bookings that request machinery or both
    raw = Booking.query.filter(Booking.service_type.in_(['machinery','both'])).order_by(Booking.id.desc()).all()
    bookings_info = []
    for b in raw:
        lo = User.query.get(b.landowner_id)
        bookings_info.append({
            'id': b.id,
            'landowner_id': b.landowner_id,
            'landowner_name': (lo.name or lo.username) if lo else 'Unknown',
            'service_date': b.service_date,
            'days': b.days,
            'service_type': b.service_type,
            'machine_type': b.machine_type,
            'status': b.status
        })

    if request.method == 'POST':
        booking_id_raw = request.form.get('booking_id')
        response = request.form.get('response')
        if not booking_id_raw or not response:
            flash('Invalid submission', 'danger')
            return redirect(url_for('machinery_dashboard'))
        try:
            booking_id = int(booking_id_raw)
        except:
            flash('Invalid booking id', 'danger')
            return redirect(url_for('machinery_dashboard'))

        # prevent duplicate response
        if BookingResponse.query.filter_by(booking_id=booking_id, user_id=user.id).first():
            flash('You already responded to this booking', 'info')
            return redirect(url_for('machinery_dashboard'))

        # save response
        br = BookingResponse(booking_id=booking_id, user_id=user.id, response=response)
        db.session.add(br)
        db.session.commit()
        flash(f'You {response} booking {booking_id}', 'success')

        # recompute machinery acceptance/rejection
        all_responses = BookingResponse.query.filter_by(booking_id=booking_id).all()
        total_mach = User.query.filter_by(role='machinery').count()
        mach_accepts = len([r for r in all_responses if User.query.get(r.user_id).role=='machinery' and r.response=='Accept'])
        mach_rejects = len([r for r in all_responses if User.query.get(r.user_id).role=='machinery' and r.response=='Reject'])

        booking = Booking.query.get(booking_id)
        if mach_accepts > 0:
            if booking.service_type == 'both':
                labor_accepts = len([r for r in all_responses if User.query.get(r.user_id).role=='labor' and r.response=='Accept'])
                booking.status = 'Confirmed' if labor_accepts>0 else 'Confirmed (Machinery)'
            else:
                booking.status = 'Confirmed'
        else:
            if total_mach>0 and mach_rejects>=total_mach:
                if booking.service_type == 'machinery':
                    booking.status = 'Rejected'
                elif booking.service_type == 'both':
                    total_lab = User.query.filter_by(role='labor').count()
                    lab_rejects = len([r for r in all_responses if User.query.get(r.user_id).role=='labor' and r.response=='Reject'])
                    if total_lab>0 and lab_rejects>=total_lab:
                        booking.status = 'Rejected'
        db.session.commit()
        return redirect(url_for('machinery_dashboard'))

    return render_template('machinery_dashboard.html', machinery=user, bookings=bookings_info)

# Admin dashboard
@app.route('/admin')
def admin_dashboard():
    user = current_user()
    if not user or user.role!='admin':
        flash('Please login as admin', 'warning')
        return redirect(url_for('login'))
    landowners = User.query.filter_by(role='landowner').all()
    labors = User.query.filter_by(role='labor').all()
    machineries = User.query.filter_by(role='machinery').all()
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin_dashboard.html', landowners=landowners, labors=labors, machineries=machineries, bookings=bookings)

if __name__ == '__main__':
    app.run(debug=True)
