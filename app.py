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
    dob = db.Column(db.String(50))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    skills = db.Column(db.String(200))
    outstation = db.Column(db.String(10))  # Yes/No
    


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
	    dob=form.get("dob") if role == "labor" else None,
            age=form.get("age") if role == "labor" else None,
            gender=form.get("gender") if role == "labor" else None,
            skills=form.get("skills") if role == "labor" else None,
            outstation=form.get("outstation") if role == "labor" else None
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
# ---------------- LANDOWNER ---------------- #
@app.route("/landowner", methods=["GET", "POST"])
def landowner_dashboard():
    user = current_user()
    if not user or user.role != "landowner":
        flash("Login as landowner first", "danger")
        return redirect(url_for("login"))

    # --- Handle booking creation ---
    if request.method == "POST":
        form = request.form
        b = Booking(
            landowner_id=user.id,
            service_date=form["service_date"],
            days=form["days"],
            service_type=form["service_type"].strip().lower(),
            num_labor=form.get("num_labor"),
            machine_type=form.get("machine_type"),
        )
        db.session.add(b)
        db.session.commit()
        flash("Booking created successfully!", "success")
        return redirect(url_for("landowner_dashboard"))

    # --- Prepare display for existing bookings ---
    bookings = Booking.query.filter_by(landowner_id=user.id).all()
    total_labors = User.query.filter_by(role="labor").count()
    total_machs = User.query.filter_by(role="machinery").count()

    bookings_display = []
    for b in bookings:
        stype = (b.service_type or "").strip().lower()
        num_labor = int(b.num_labor) if b.num_labor else 0

        # accepted/rejected labor responses
        accepted_lab_q = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="labor", response="Accept"
        ).all()
        rejected_lab_count = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="labor", response="Reject"
        ).count()
        accepted_lab_count = len(accepted_lab_q)
        accepted_lab_names = [User.query.get(r.user_id).name for r in accepted_lab_q]

        # accepted/rejected machinery responses
        accepted_mach_q = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="machinery", response="Accept"
        ).all()
        rejected_mach_count = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="machinery", response="Reject"
        ).count()
        accepted_mach_names = [User.query.get(r.user_id).name for r in accepted_mach_q]

        # ---- labor status ----
        if stype == "machinery":
            labor_status = "N/A"
        elif stype in ("labor", "both"):
            if num_labor > 0:
                if accepted_lab_count >= num_labor:
                    labor_status = f"Confirmed ({', '.join(accepted_lab_names)})"
                elif rejected_lab_count >= total_labors and total_labors > 0:
                    labor_status = "Rejected"
                else:
                    labor_status = f"{accepted_lab_count}/{num_labor} Accepted"
            else:
                labor_status = "N/A"
        else:
            labor_status = "N/A"

        # ---- machinery status ----
        if stype == "labor":
            machinery_status = "N/A"
        elif stype in ("machinery", "both"):
            if len(accepted_mach_q) > 0:
                machinery_status = f"Confirmed ({', '.join(accepted_mach_names)})"
            elif rejected_mach_count >= total_machs and total_machs > 0:
                machinery_status = "Rejected"
            else:
                machinery_status = "Pending"
        else:
            machinery_status = "N/A"

        # ---- overall action ----
        if stype == "both":
            labor_closed = labor_status.startswith("Confirmed") or labor_status == "Rejected"
            mach_closed = machinery_status.startswith("Confirmed") or machinery_status == "Rejected"
            action = "Closed" if (labor_closed and mach_closed) else "Pending"
        elif stype == "labor":
            action = "Closed" if labor_status.startswith("Confirmed") or labor_status == "Rejected" else "Pending"
        elif stype == "machinery":
            action = "Closed" if machinery_status.startswith("Confirmed") or machinery_status == "Rejected" else "Pending"
        else:
            action = "Pending"

        bookings_display.append({
            "id": b.id,
            "service_date": b.service_date,
            "days": b.days,
            "service_type": b.service_type,
            "num_labor": b.num_labor,
            "machine_type": b.machine_type,
            "labor_status": labor_status,
            "machinery_status": machinery_status,
            "action": action
        })

    return render_template("landowner_dashboard.html",
                           landowner=user,
                           bookings=bookings_display)




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
        # normalize service_type (defensive)
        stype = (b.service_type or "").strip().lower()

        # safe integer for num_labor
        num_labor = int(b.num_labor) if b.num_labor else 0

        # Get accepted/rejected labors
        accepted_lab_q = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="labor", response="Accept"
        ).all()
        rejected_lab_count = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="labor", response="Reject"
        ).count()
        accepted_lab_count = len(accepted_lab_q)
        accepted_lab_names = [User.query.get(r.user_id).name for r in accepted_lab_q]

        # Get accepted/rejected machinery
        accepted_mach_q = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="machinery", response="Accept"
        ).all()
        rejected_mach_count = BookingResponse.query.filter_by(
            booking_id=b.id, user_role="machinery", response="Reject"
        ).count()
        accepted_mach_names = [User.query.get(r.user_id).name for r in accepted_mach_q]

        # --- Labor status logic ---
        if stype == "machinery":
            labor_status = "N/A"
        elif stype in ("labor", "both"):
            # show progress: x/num Accepted (if num_labor>0) else show N/A
            if num_labor > 0:
                if accepted_lab_count >= num_labor:
                    labor_status = f"Confirmed ({', '.join(accepted_lab_names)})"
                elif rejected_lab_count >= total_labors and total_labors > 0:
                    labor_status = "Rejected"
                else:
                    labor_status = f"{accepted_lab_count}/{num_labor} Accepted"
            else:
                # no quantity asked
                labor_status = "N/A"
        else:
            labor_status = "N/A"

        # --- Machinery status logic ---
        if stype == "labor":
            machinery_status = "N/A"
        elif stype in ("machinery", "both"):
            # machinery considered confirmed when at least one accepts
            if len(accepted_mach_q) > 0:
                machinery_status = f"Confirmed ({', '.join(accepted_mach_names)})"
            elif rejected_mach_count >= total_machs and total_machs > 0:
                machinery_status = "Rejected"
            else:
                machinery_status = "Pending"
        else:
            machinery_status = "N/A"

        # --- Overall action logic ---
        if stype == "both":
            labor_closed = labor_status.startswith("Confirmed") or labor_status == "Rejected"
            mach_closed = machinery_status.startswith("Confirmed") or machinery_status == "Rejected"
            action = "Closed" if (labor_closed and mach_closed) else "Pending"
        elif stype == "labor":
            action = "Closed" if labor_status.startswith("Confirmed") or labor_status == "Rejected" else "Pending"
        elif stype == "machinery":
            action = "Closed" if machinery_status.startswith("Confirmed") or machinery_status == "Rejected" else "Pending"
        else:
            action = "Pending"

        landowner = User.query.get(b.landowner_id)
        bookings_display.append({
            "id": b.id,
            "landowner_name": landowner.name if landowner else "Unknown",
            "landowner_contact": landowner.contact if landowner else "-",
            "landowner_address": landowner.address if landowner else "-",
            "service_type": b.service_type,
            "service_date": b.service_date,
            "days": b.days,
            "labor_status": labor_status,
            "machinery_status": machinery_status,
            "action": action
        })

    return render_template(
        "admin_dashboard.html",
        landowners=landowners,
        labors=labors,
        machineries=machineries,
        bookings=bookings_display
    )


if __name__ == "__main__":
    app.run(debug=True)
