from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from app import app, db, lm
from .forms import EditProfileForm, SelectAppointmentForm, AppointmentCompletedForm
from .models import Doctor, Appointment
from oauth import OAuthSignIn



@lm.user_loader
def load_user(id):
    return Doctor.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user


''' OAuth Login Views '''

@app.route('/login')
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = Doctor.query.filter_by(social_id=social_id).first()
    if not user:
        user = Doctor(social_id=social_id, username=username, name=username, email=email)
        db.session.add(user)
        db.session.commit()
        login_user(user, True)
        return redirect(url_for('.edit_profile'))
    login_user(user, True)
    return redirect(url_for('index'))

''' OAuth Login Views End '''


@app.route('/')
@app.route('/index')
@login_required
def index():
    user = g.user

    query = Appointment.query.filter(Appointment.status == "Pending")
    appointments = query.order_by(Appointment.timestamp.desc())
    return render_template('index.html',
                           title='Home',
                           user=user,
                           appointments=appointments)

@app.route('/user/')
@login_required
def user():
    user = g.user
    scheduled_query = Appointment.query.filter(Appointment.status == "Scheduled")
    scheduled_appointments = scheduled_query.order_by(Appointment.timestamp.desc())
    completed_query = Appointment.query.filter(Appointment.status == "Completed")
    completed_appointments = completed_query.order_by(Appointment.timestamp.desc())
    return render_template('user.html', user=user, 
        scheduled_appointments=scheduled_appointments, completed_appointments=completed_appointments)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone_number.data
        current_user.speciality = form.speciality.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user'))
    form.name.data = current_user.name
    form.email.data = current_user.email
    form.name.speciality = current_user.speciality
    form.name.phone_number = current_user.phone_number
    return render_template('edit_profile.html', form=form)

@app.route('/appointment/<int:id>', methods=['GET', 'POST'])
@login_required
def appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if appointment.status == "Pending":
        form = SelectAppointmentForm()
        if form.validate_on_submit():
            appointment.status = "Scheduled"
            appointment.appointment_time = form.appointment_time.data
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment has been scheduled.')
            return redirect(url_for('.appointment', id=appointment.id))
        return render_template('appointment.html', appointment=appointment, form=form)
    elif appointment.status == "Scheduled":
        form = AppointmentCompletedForm()
        if form.validate_on_submit():
            appointment.status = "Completed"
            db.session.add(appointment)
            db.session.commit()
            flash('Appointment has been completed.')
            return redirect(url_for('.appointment', id=appointment.id))
        return render_template('appointment.html', appointment=appointment, form=form)
    else:
        return render_template('appointment.html', appointment=appointment)
    
# Twilio     
@app.route("/twilio/", methods=['GET', 'POST'])
def twilio():
    """Respond to incoming calls with a simple text message."""
 
    resp = twilio.twiml.Response()
    resp.message("Hello, Mobile Monkey")
    return str(resp)