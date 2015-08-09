from app import db
from flask.ext.login import UserMixin
from datetime import datetime

class Doctor(UserMixin, db.Model):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    username = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    phone_number = db.Column(db.String(64), nullable=True)
    speciality = db.Column(db.String(64), nullable=True)
    location = db.Column(db.String(64), nullable=True)
    appointments = db.relationship('Appointment', backref='doctor', lazy='dynamic')


class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    phone_number = db.Column(db.String(64), nullable=True)
    age = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(64), nullable=False)
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic')
    phone_calls = db.relationship('PhoneCalls', backref='patient', lazy='dynamic')

    @staticmethod
    def generate_fake(count=5):
        from sqlalchemy.exc import IntegrityError
        from random import seed, randint
        import forgery_py

        seed()
        for i in range(count):
            u = Patient(name=forgery_py.name.full_name(),
                     phone_number=forgery_py.forgery.address.phone(),
                     gender=forgery_py.forgery.personal.gender(),
                     age=randint(20, 40))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    appointment_time = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime)
    phone_calls = db.relationship('PhoneCalls', backref='appointments', lazy='dynamic')

    @staticmethod
    def generate_fake(count=10):
        from random import seed, randint
        import forgery_py

        seed()
        patient_count = Patient.query.count()
        for i in range(count):
            p = Patient.query.offset(randint(0, patient_count - 1)).first()
            a = Appointment(status="Pending",
                     timestamp=forgery_py.date.date(True),
                     patient_id=p.id)
            db.session.add(a)
            db.session.commit()


class PhoneCalls(db.Model):
    __tablename__ = 'phone_calls'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    case_severity = db.Column(db.String(64), nullable=True)
    symptoms = db.Column(db.String(64), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))

    @staticmethod
    def generate_fake(count=50):
        from random import seed, randint
        import forgery_py

        seed()
        appointments_count = Appointment.query.count()
        for i in range(count):
        	a = Appointment.query.offset(randint(0, appointments_count - 1)).first()
        	p = a.patient_id
        	pc = PhoneCalls(case_severity= forgery_py.forgery.lorem_ipsum.word(),
            		symptoms=forgery_py.forgery.lorem_ipsum.sentence(),
                     timestamp=forgery_py.date.date(True),
                     patient_id=p,appointment_id=a.id)
        	db.session.add(pc)
        	db.session.commit()

