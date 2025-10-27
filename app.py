from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "krishikaya"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "krishikaya.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20))
    name = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    contact = db.Column(db.String(50))
    address = db.Column(db.String(200))
    acres = db.Column(db.Integer)
    crops = db.Column(db.String(200))
    machine_type = db.Column(db.String(100))
    num_labors = db.Column(db.Integer)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    landowner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    service_date = db.Column(db.String(50))
    days = db.Column(db.Integer)
    service_type = db.Column(db.String(20))
    num_labor = db.Column(db.Integer)
    machine_type = db.Column(db.String(100))
    labor_status = db.Column(db.String(100), default="Pending")
    machinery_status = db.Column(db.String(100), default="Pending")
    action = db.Column(db.String(20), default="Pending")  # Pending/Closed


class BookingResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    response = db.Column(db.String(10))  # Accept/Reject
    user_role = db.Column(db.String(20))  # labor or machinery


# ---------------- HELPERS ---------------- #
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


@app.before_first_request
def setup():
    db.create_all()


# ---------------- ROUTES ---------------- #
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register/<role>", methods=["GET", "POST"])
def register(role):
    if role not in ["admin", "landowner", "labor", "machinery"]:
        flash("Invalid role", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        form = request.form
        username = form["username"]
        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(request.url)

        user = User(
            role=role,
            name=form.get("name"),
            username=username,
            password=form.get("password"),
            contact=form.get("contact"),
            address=form.get("address"),
            acres=form.get("acres") if role == "landowner" else None,
            crops=form.get("crops") if role == "landowner" else None,
            machine_type=form.get("machine_type") if role == "machinery" else None,
            num_labors=form.get("num_labors") if role == "labor" else None,
        )
        db.session.add(user)
        db.session.commit()
        flash(f"{role.capitalize()} registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template(f"register_{role}.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            session["role"] = user.role
            flash(f"Welcome {user.name or user.username}!", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "landowner":
                return redirect(url_for("landowner_dashboard"))
            elif user.role == "labor":
                return redirect(url_for("labor_dashboard"))
            elif user.role == "machinery":
                return redirect(url_for("machinery_dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("home"))


# ---------------- LANDOWNER ---------------- #
@app.route("/landowner", methods=["GET", "POST"])
def landowner_dashboard():
    user = current_user()
    if not user or user.role != "landowner":
        flash("Login as landowner first", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        form = request.form
        # single booking entry even if multiple labors requested
        b = Booking(
            landowner_id=user.id,
            service_date=form["service_date"],
            days=int(form["days"]),
            service_type=form["service_type"],
            num_labor=int(form.get("num_labor")) if form.get("num_labor") else 0,
            machine_type=form.get("machine_type"),
        )
        db.session.add(b)
        db.session.commit()
        flash("Booking created successfully!", "success")
        return redirect(url_for("landowner_dashboard"))

    bookings = Booking.query.filter_by(landowner_id=user.id).all()
    booking_data = []
    total_labors = User.query.filter_by(role="labor").count()
    total_machs = User.query.filter_by(role="machinery").count()

    for b in bookings:
        # labor accepted/rejected counts & names
        lab_accept_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Accept").all()
        lab_reject_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Reject").all()
        accepted_lab_names = [User.query.get(r.user_id).name for r in lab_accept_q]
        rejected_lab_count = len(lab_reject_q)
        accepted_lab_count = len(lab_accept_q)

        # machinery accepted/rejected counts & names
        mach_accept_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Accept").all()
        mach_reject_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Reject").all()
        accepted_mach_names = [User.query.get(r.user_id).name for r in mach_accept_q]
        rejected_mach_count = len(mach_reject_q)
        accepted_mach_count = len(mach_accept_q)

        # labor status string
        if b.num_labor and accepted_lab_count >= b.num_labor:
            labor_status = "Confirmed"
        elif b.num_labor:
            labor_status = f"{accepted_lab_count}/{b.num_labor} Accepted"
            if rejected_lab_count >= total_labors:
                labor_status = "Rejected"
        else:
            labor_status = "N/A"

        # machinery status string: require at least one machinery accept to confirm
        if accepted_mach_count > 0:
            machinery_status = "Confirmed (" + ", ".join(accepted_mach_names) + ")"
        else:
            if rejected_mach_count >= total_machs and total_machs>0:
                machinery_status = "Rejected"
            else:
                machinery_status = "Pending"

        # overall action: closed if both required parts satisfied or rejected fully
        # (landowner asked for both -> both need to be decided)
        if b.service_type == "both":
            labor_closed = (b.num_labor and accepted_lab_count >= b.num_labor) or (rejected_lab_count >= total_labors)
            mach_closed = (accepted_mach_count>0) or (rejected_mach_count >= total_machs)
            action = "Closed" if labor_closed and mach_closed else "Pending"
        elif b.service_type == "labor":
            action = "Closed" if (b.num_labor and accepted_lab_count >= b.num_labor) or (rejected_lab_count >= total_labors) else "Pending"
        elif b.service_type == "machinery":
            action = "Closed" if (accepted_mach_count>0) or (rejected_mach_count >= total_machs) else "Pending"
        else:
            action = "Pending"

        booking_data.append({
            "id": b.id,
            "service_date": b.service_date,
            "days": b.days,
            "service_type": b.service_type,
            "num_labor": b.num_labor,
            "machine_type": b.machine_type,
            "labor_status": labor_status,
            "machinery_status": machinery_status,
            "accepted_lab_names": accepted_lab_names,
            "accepted_mach_names": accepted_mach_names,
            "action": action
        })

    return render_template("landowner_dashboard.html", landowner=user, bookings=booking_data)




# ---------------- LABOR ---------------- #
@app.route("/labor", methods=["GET", "POST"])
def labor_dashboard():
    user = current_user()
    if not user or user.role != "labor":
        flash("Login as labor first", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        booking_id = int(request.form["booking_id"])
        response = request.form["response"]
        booking = Booking.query.get(booking_id)

        # prevent double response
        existing = BookingResponse.query.filter_by(booking_id=booking_id, user_id=user.id).first()
        if existing:
            flash("You have already responded to this booking!", "info")
            return redirect(url_for("labor_dashboard"))

        # save response
        db.session.add(BookingResponse(booking_id=booking_id, user_id=user.id, response=response, user_role="labor"))
        db.session.commit()
        flash(f"You {response.lower()}ed booking {booking_id}", "success")
        return redirect(url_for("labor_dashboard"))

    # Show ALL bookings that requested labor or both — but compute whether this user can still act
    bookings_display = []
    total_labors = User.query.filter_by(role="labor").count()

    for b in Booking.query.filter(Booking.service_type.in_(["labor", "both"])).order_by(Booking.id.desc()).all():
        # count accepted/rejected for labor
        accepted_count = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Accept").count()
        rejected_count = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Reject").count()
        # whether booking still needs labor
        needed = b.num_labor or 0
        open_for_more = True
        if needed > 0 and accepted_count >= needed:
            open_for_more = False

        # whether current user has already responded
        user_resp = BookingResponse.query.filter_by(booking_id=b.id, user_id=user.id).first()
        has_responded = bool(user_resp)

        # compute status display
        if needed > 0:
            if accepted_count >= needed:
                status = "Confirmed"
            elif rejected_count >= total_labors:
                status = "Rejected"
            else:
                status = f"{accepted_count}/{needed} Accepted"
        else:
            # shouldn't normally happen, fallback
            status = "Pending"

        bookings_display.append({
            "id": b.id,
            "landowner_name": User.query.get(b.landowner_id).name,
            "service_date": b.service_date,
            "days": b.days,
            "service_type": b.service_type,
            "num_labor": needed,
            "accepted_count": accepted_count,
            "status": status,
            "open_for_more": open_for_more,
            "has_responded": has_responded
        })

    responses = {r.booking_id: r.response for r in BookingResponse.query.filter_by(user_id=user.id).all()}
    return render_template("labor_dashboard.html", labor=user, bookings=bookings_display, responses=responses)




# ---------------- MACHINERY ---------------- #
@app.route("/machinery", methods=["GET", "POST"])
def machinery_dashboard():
    user = current_user()
    if not user or user.role != "machinery":
        flash("Login as machinery owner first", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        booking_id = int(request.form["booking_id"])
        response = request.form["response"]

        existing = BookingResponse.query.filter_by(booking_id=booking_id, user_id=user.id).first()
        if existing:
            flash("You have already responded!", "info")
            return redirect(url_for("machinery_dashboard"))

        db.session.add(BookingResponse(booking_id=booking_id, user_id=user.id, response=response, user_role="machinery"))
        db.session.commit()
        flash(f"You {response.lower()}ed booking {booking_id}", "success")
        return redirect(url_for("machinery_dashboard"))

    bookings_display = []
    total_machs = User.query.filter_by(role="machinery").count()

    for b in Booking.query.filter(Booking.service_type.in_(["machinery", "both"])).order_by(Booking.id.desc()).all():
        accepted_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Accept").all()
        rejected_count = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Reject").count()
        accepted_names = [User.query.get(r.user_id).name for r in accepted_q]

        # requirement: for machinery we consider confirmed if at least one accepts
        if len(accepted_q) > 0:
            status = "Confirmed"
            open_for_more = False
        elif rejected_count >= total_machs and total_machs>0:
            status = "Rejected"
            open_for_more = False
        else:
            status = "Pending"
            open_for_more = True

        user_resp = BookingResponse.query.filter_by(booking_id=b.id, user_id=user.id).first()
        has_responded = bool(user_resp)

        bookings_display.append({
            "id": b.id,
            "landowner_name": User.query.get(b.landowner_id).name,
            "service_date": b.service_date,
            "days": b.days,
            "machine_type": b.machine_type,
            "accepted_names": accepted_names,
            "status": status,
            "open_for_more": open_for_more,
            "has_responded": has_responded
        })

    responses = {r.booking_id: r.response for r in BookingResponse.query.filter_by(user_id=user.id).all()}
    return render_template("machinery_dashboard.html", machinery=user, bookings=bookings_display, responses=responses)




# ---------------- ADMIN ---------------- #
@app.route("/admin")
def admin_dashboard():
    user = current_user()
    if not user or user.role != "admin":
        flash("Login as admin first", "danger")
        return redirect(url_for("login"))

    landowners = User.query.filter_by(role="landowner").all()
    labors = User.query.filter_by(role="labor").all()
    machineries = User.query.filter_by(role="machinery").all()

    bookings = Booking.query.all()
    total_labors = User.query.filter_by(role="labor").count()
    total_machs = User.query.filter_by(role="machinery").count()

    bookings_display = []
    for b in bookings:
        accepted_lab_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Accept").all()
        rejected_lab_count = BookingResponse.query.filter_by(booking_id=b.id, user_role="labor", response="Reject").count()
        accepted_lab_count = len(accepted_lab_q)
        accepted_lab_names = [User.query.get(r.user_id).name for r in accepted_lab_q]

        accepted_mach_q = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Accept").all()
        rejected_mach_count = BookingResponse.query.filter_by(booking_id=b.id, user_role="machinery", response="Reject").count()
        accepted_mach_names = [User.query.get(r.user_id).name for r in accepted_mach_q]

        # labour status
        if b.num_labor and accepted_lab_count >= b.num_labor:
            labor_status = "Confirmed (" + ", ".join(accepted_lab_names) + ")"
        elif rejected_lab_count >= total_labors and total_labors>0:
            labor_status = "Rejected"
        else:
            labor_status = f"{accepted_lab_count}/{b.num_labor or 0} Accepted"

        # machinery status
        if len(accepted_mach_q) > 0:
            machinery_status = "Confirmed (" + ", ".join(accepted_mach_names) + ")"
        elif rejected_mach_count >= total_machs and total_machs>0:
            machinery_status = "Rejected"
        else:
            machinery_status = "Pending"

        # overall action (for admin display)
        if b.service_type == "both":
            action = "Closed" if (labor_status.startswith("Confirmed") or labor_status=="Rejected") and (machinery_status.startswith("Confirmed") or machinery_status=="Rejected") else "Pending"
        elif b.service_type == "labor":
            action = "Closed" if labor_status.startswith("Confirmed") or labor_status=="Rejected" else "Pending"
        elif b.service_type == "machinery":
            action = "Closed" if machinery_status.startswith("Confirmed") or machinery_status=="Rejected" else "Pending"
        else:
            action = "Pending"

        bookings_display.append({
            "id": b.id,
            "landowner_name": User.query.get(b.landowner_id).name,
            "service_type": b.service_type,
            "service_date": b.service_date,
            "days": b.days,
            "labor_status": labor_status,
            "machinery_status": machinery_status,
            "action": action
        })

    return render_template("admin_dashboard.html",
                           landowners=landowners,
                           labors=labors,
                           machineries=machineries,
                           bookings=bookings_display)


if __name__ == "__main__":
    app.run(debug=True)
