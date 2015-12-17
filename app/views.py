from flask import Response, render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from app import app, db, lm
from .forms import EditProfileForm, SelectAppointmentForm, AppointmentCompletedForm
from .models import Doctor, Appointment, Patient, PhoneCalls
from oauth import OAuthSignIn
import braintree
import plivoxml, calendar

braintree.Configuration.configure(braintree.Environment.Sandbox,
                                merchant_id="v4pp4mjbfjxmyw3s",
                                public_key="bkvv5qm86dyzmvjb",
                                private_key="8b3d99cfccdd4a269cb1179bf9761abc")



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

@app.route('/donate')
def donate():
    return render_template('donate.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/client_token", methods=["GET"])
def client_token():
  return braintree.ClientToken.generate()

result = braintree.Transaction.sale({
    "amount": "1000.00",
    "credit_card": {
        "number": "4111111111111111",
        "expiration_date": "05/2012"
    }
})

# if result.is_success:
#     print("success!: " + result.transaction.id)
# elif result.transaction:
#     print("Error processing transaction:")
#     print("  code: " + result.transaction.processor_response_code)
#     print("  text: " + result.transaction.processor_response_text)
# else:
#     for error in result.errors.deep_errors:
#         print("attribute: " + error.attribute)
#         print("  code: " + error.code)
#         print("  message: " + error.message)

# Plivo
# This file will be played when a caller presses 2.
PLIVO_SONG = "https://s3.amazonaws.com/plivocloud/music.mp3"

# This is the message that Plivo reads when the caller dials in
IVR_MESSAGE = "Welcome to Village Med. If you are experiencing an \
                immediate medical emergency, please hang up and dial \
                your local emergency response."

# This is the message that Plivo reads when the caller does nothing at all
NO_INPUT_MESSAGE = "Sorry, I didn't catch that. Please hangup and try again \
                    later."

# This is the message that Plivo reads when the caller inputs a wrong number.
WRONG_INPUT_MESSAGE = "Sorry, it's wrong input."

# Enter your own joke handy in case reddit goes down
PLIVO_JOKE = "What do you get when you cross a snowman with a vampire? \
            A frostbite"

@app.route('/response/ivr/', methods=['GET', 'POST'])
def ivr():
    response = plivoxml.Response()
    if request.method == 'GET':
        # GetDigit XML Docs - http://plivo.com/docs/xml/getdigits/
        getdigits_action_url = url_for('ivr', _external=True)
        getDigits = plivoxml.GetDigits(action=getdigits_action_url,
                                       method='POST', timeout=10, numDigits=1,
                                       retries=1)

        # getDigits.addSpeak(IVR_MESSAGE)
        # getDigits.addWait(length=1)
        getDigits.addSpeak(body='Press 1 if you are an existing patient')
        getDigits.addWait(length=1)
        getDigits.addSpeak(body='Press 2 if you are a new patient')
        response.add(getDigits)
        response.addSpeak(NO_INPUT_MESSAGE)

        return Response(str(response), mimetype='text/xml')

    elif request.method == 'POST':
        digit = request.form.get('Digits')

        if digit == "1":
            absolute_action_url = url_for('patient_id_input', _external=True)
            response.addRedirect(body=absolute_action_url, method='GET')
        elif digit == "2":
            # Listen to a song
            response.addSpeak(body="We will create a new patient profile for you.")
            absolute_action_url = url_for('new_patient', _external=True)
            response.addRedirect(body=absolute_action_url, method='GET')
        else:
            response.addSpeak(WRONG_INPUT_MESSAGE)

        return Response(str(response), mimetype='text/xml')

@app.route('/response/patient_id_input/', methods=['GET', 'POST'])
def patient_id_input():
    response = plivoxml.Response()
    if request.method == 'GET':
        # GetDigit XML Docs - http://plivo.com/docs/xml/getdigits/
        getdigits_action_url = url_for('patient_id_input', _external=True)
        getDigits = plivoxml.GetDigits(action=getdigits_action_url,
                                       method='POST', timeout=10, numDigits=4,
                                       retries=1)

        getDigits.addSpeak(body='Enter your patient ID, followed by the hash key')
        response.add(getDigits)
        response.addSpeak(NO_INPUT_MESSAGE)

        return Response(str(response), mimetype='text/xml')

    elif request.method == 'POST':
        digit = request.form.get('Digits')

        patient = Patient.query.get_or_404(int(digit))
        patient_response = "Welcome " + patient.name
        response.addSpeak(patient_response)
        absolute_action_url = url_for('existing_patient', _external=True, id=patient.id)
        response.addRedirect(body=absolute_action_url, method='GET')

        return Response(str(response), mimetype='text/xml')

@app.route('/response/new_patient/', methods=['GET', 'POST'])
def new_patient():
    response = plivoxml.Response()
    if request.method == 'GET':
        getdigits_action_url = url_for('new_patient', _external=True,
                                    **{'first_name': None,'last_name': None, 
                                    'age': None, 'gender': None})
        getDigits = plivoxml.GetDigits(action=getdigits_action_url, retries=1,
                                           method='POST', timeout=180, numDigits=30)
        getDigits.addSpeak(body='Please enter your first name by \
            spelling out the letters using the following convention:')
        getDigits.addSpeak(body="Press the number the letter is \
            displayed on , and the place the letter is at on the key.")
        getDigits.addSpeak(body='For example, to enter A, press 2 1')
        getDigits.addSpeak(body='To enter the letter K, press 5 2')
        getDigits.addSpeak(body='Press the hash key when you are done')
        response.add(getDigits)
        return Response(str(response), mimetype='text/xml')

    elif request.method == 'POST':
        if not request.args.get('first_name', None):
            digit = request.form.get('Digits').title()
            response = plivoxml.Response()
            absolute_action_url = url_for('new_patient', _external=True,
                                        **{'first_name': digit,'last_name': None, 
                                        'age': None, 'gender': None})
            getDigits = plivoxml.GetDigits(action=getdigits_action_url, retries=1,
                                           method='POST', timeout=180, numDigits=30)
            getDigits.addSpeak(body='Now enter your last name using the same convention as before.')
            getDigits.addSpeak(body='Press the hash key when you are done')
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        elif not request.args.get('last_name', None):
            digit = request.form.get('Digits').title()
            first_name = request.args.get('first_name', '0')
            response = plivoxml.Response()
            absolute_action_url = url_for('new_patient', _external=True,
                                        **{'first_name': first_name,'last_name': digit, 
                                        'age': None, 'gender': None})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=10, numDigits=2, retries=1)
            getDigits.addSpeak(body="Enter your age using the key pad.")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        elif not request.args.get('age', None):
            digit = request.form.get('Digits')
            first_name = request.args.get('first_name', '0')
            last_name = request.args.get('last_name', '0')
            response = plivoxml.Response()
            absolute_action_url = url_for('new_patient', _external=True,
                                        **{'first_name': first_name,'last_name': last_name, 
                                        'age': digit, 'gender': None})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=10, numDigits=1, retries=1)
            getDigits.addSpeak(body="Press the number corresponding to your gender.\
             1 for female, 2 for male, 3 for other.")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        elif not request.args.get('gender', None):
            digit = request.form.get('Digits')
            first_name = request.args.get('first_name', '0')
            last_name = request.args.get('last_name', '0')
            age = request.args.get('age', '0')
            gender_dict = {"1":"Female","2":"Male", "3":"Other"}
            print first_name, last_name, age, gender_dict[digit]
            response = plivoxml.Response()
            absolute_action_url = url_for('new_patient', _external=True,
                                        **{'first_name': first_name,'last_name': last_name, 
                                        'age': age, 'gender': gender_dict[digit]})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=10, numDigits=1, retries=1)
            getDigits.addSpeak(body="Press the number corresponding to your gender.\
             1 for female, 2 for male, 3 for other.")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        else:
            response = plivoxml.Response()
            response.addSpeak(PLIVO_JOKE)

            # symptoms_string = request.form.get('Digits')
            # symptoms = ''
            # symptoms_dict = {
            # "1":"Cough",
            # "2":"Nausea", 
            # "3":"Vomiting", 
            # "4":"Fatigue",
            # "5":"Sore throat",
            # "6":"Weight loss", 
            # "7":"Abdominal pain",
            # "8":"Heart burn",
            # "9":"Anxiety",
            # "0":"Depressive symptoms"
            # }
            # for i in symptoms_string:
            #     symptoms += symptoms_dict[i] + ", "

            # a=Appointment(patient_id=patient_id,
            #     availability_time= request.args.get('time', '0'),
            #     availability_date= request.args.get('date', '0'),
            #     status="Pending",
            #     )
            # db.session.add(a)
            # db.session.commit()

            # p=PhoneCalls(patient_id=patient_id,
            #     appointment_id=a.id,
            #     symptoms=symptoms[:-2],
            #     case_severity=request.args.get('severity', '0'),
            #     )
            # db.session.add(p)
            # db.session.commit()

            # response.addSpeak("Your request for an appointment has been stored in our\
            #  database with the appointment I D, " + str(a.id))
            # response.addSpeak("We will try to schedule an appointment for you on " 
            #     + calendar.month_name[int(a.availability_date[5:7])] + " " + 
            #     a.availability_date[8:10] + " in the " + a.availability_time + '.')
            # response.addSpeak("You will be contacted soon with further details \
            #     once a doctor has been found for you. ")
            # response.addSpeak("We hope to get you feeling better soon.  Good bye.")
            # response.addWait(length=2)

            return Response(str(response), mimetype='text/xml')

@app.route('/response/patient/<int:id>', methods=['GET', 'POST'])
def existing_patient(id):
    response = plivoxml.Response()
    if request.method == 'GET':
        getdigits_action_url = url_for('existing_patient', _external=True, id=id)
        getDigits = plivoxml.GetDigits(action=getdigits_action_url,
                                       method='POST', timeout=10, numDigits=4,
                                       retries=1)

        getDigits.addSpeak(body='To access a current appointment, \
            enter the appointment ID followed by the hash key')
        getDigits.addWait(length=1)
        getDigits.addSpeak(body='To set up a new appointment, press 0 followed by the hash key')
        response.add(getDigits)
        return Response(str(response), mimetype='text/xml')

    elif request.method == 'POST':
        digit = request.form.get('Digits')
        if digit == "0":
            response.addSpeak(body='You will now be guided through the process of scheduling an appointment')
            absolute_action_url = url_for('new_appointment', _external=True, patient_id=id)
            response.addRedirect(body=absolute_action_url, method='GET')
        else: 
            response.addSpeak(PLIVO_JOKE)
        return Response(str(response), mimetype='text/xml')

@app.route('/response/new_appointment/<int:patient_id>', methods=['GET', 'POST'])
def new_appointment(patient_id):
    response = plivoxml.Response()
    if request.method == 'GET':
        getdigits_action_url = url_for('new_appointment', _external=True, patient_id=patient_id,
                                    **{'date': None,'time': None, 'severity': None})

        getDigits = plivoxml.GetDigits(action=getdigits_action_url,
                                       method='POST', timeout=120, numDigits=6,
                                       retries=1)

        getDigits.addSpeak(body='Please enter the date of your availability in 6 digits in the format m m d d y y.')
        getDigits.addSpeak(body='For example, December, first of twenty fifteen would be 1, 2, 0, 1, 1, 5.')
        response.add(getDigits)
        return Response(str(response), mimetype='text/xml')

    elif request.method == 'POST':
        if not request.args.get('date', None):
            digit = request.form.get('Digits')
            date = '20' + digit[4:6] + '-' + digit[0:2] + '-' + digit[2:4]
            response = plivoxml.Response()
            absolute_action_url = url_for('new_appointment', _external=True, patient_id=patient_id,
                                    **{'date': date,'time': None, 'severity': None})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=10, numDigits=1, retries=1)
            getDigits.addSpeak(body="Enter your ideal time of day. Press 1 \
                for morning, 2 for afternoon, and 3 for evening.")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        elif not request.args.get('time', None):
            digit = request.form.get('Digits')
            date = request.args.get('date', '0')
            time_dict = {
            "1":"Morning",
            "2":"Afternoon", 
            "3":"Evening", 
            }
            response = plivoxml.Response()
            absolute_action_url = url_for('new_appointment', _external=True, patient_id=patient_id,
                                    **{'date': date,'time': time_dict[digit], 'severity': None})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=10, numDigits=1, retries=1)
            getDigits.addSpeak(body="Enter the urgency of your \
                medical needs on an icreasing scale of one to five.")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        elif not request.args.get('severity', None):
            severity = request.form.get('Digits')
            date = request.args.get('date', '0')
            time = request.args.get('time', '0')
            response = plivoxml.Response()
            absolute_action_url = url_for('new_appointment', _external=True, patient_id=patient_id,
                                    **{'date': date,'time': time, 'severity': severity})
            getDigits = plivoxml.GetDigits(action=absolute_action_url, method='POST',
                                        timeout=120, numDigits=10, retries=1)
            getDigits.addSpeak(body="Press the digits corresponding to your symptoms") 
            getDigits.addSpeak(body="1 for cough") 
            getDigits.addSpeak(body="2 for nausea") 
            getDigits.addSpeak(body="3 for vomiting") 
            getDigits.addSpeak(body="4 for fatigue") 
            getDigits.addSpeak(body="5 for sore throat") 
            getDigits.addSpeak(body="6 for weight loss") 
            getDigits.addSpeak(body="7 for abdominal pain")
            getDigits.addSpeak(body="8 for heart burn")  
            getDigits.addSpeak(body="9 for anxiety") 
            getDigits.addSpeak(body="0 for depressive symptoms") 
            getDigits.addSpeak(body="Press the hash key when you have selected all the relevant symptoms")
            response.add(getDigits)
            return Response(str(response), mimetype='text/xml')

        else:
            response = plivoxml.Response()

            symptoms_string = request.form.get('Digits')
            symptoms = ''
            symptoms_dict = {
            "1":"Cough",
            "2":"Nausea", 
            "3":"Vomiting", 
            "4":"Fatigue",
            "5":"Sore throat",
            "6":"Weight loss", 
            "7":"Abdominal pain",
            "8":"Heart burn",
            "9":"Anxiety",
            "0":"Depressive symptoms"
            }
            for i in symptoms_string:
                symptoms += symptoms_dict[i] + ", "

            a=Appointment(patient_id=patient_id,
                availability_time= request.args.get('time', '0'),
                availability_date= request.args.get('date', '0'),
                status="Pending",
                )
            db.session.add(a)
            db.session.commit()

            p=PhoneCalls(patient_id=patient_id,
                appointment_id=a.id,
                symptoms=symptoms[:-2],
                case_severity=request.args.get('severity', '0'),
                )
            db.session.add(p)
            db.session.commit()

            response.addSpeak("Your request for an appointment has been stored in our\
             database with the appointment I D, " + str(a.id))
            response.addSpeak("We will try to schedule an appointment for you on " 
                + calendar.month_name[int(a.availability_date[5:7])] + " " + 
                a.availability_date[8:10] + " in the " + a.availability_time + '.')
            response.addSpeak("You will be contacted soon with further details \
                once a doctor has been found for you. ")
            response.addSpeak("We hope to get you feeling better soon.  Good bye.")
            response.addWait(length=2)

            return Response(str(response), mimetype='text/xml')

                 
