#!flask/bin/python
from config import SQLALCHEMY_DATABASE_URI
from app.models import Patient, Appointment, PhoneCalls
from app import db
import os.path
db.create_all()

Patient.generate_fake();
Appointment.generate_fake();
PhoneCalls.generate_fake();