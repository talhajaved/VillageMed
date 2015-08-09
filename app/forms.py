from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, DateTimeField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask.ext.pagedown.fields import PageDownField
from wtforms.fields.html5 import DateField

class EditProfileForm(Form):
    name = StringField('Real name', validators=[Required(), Length(0, 64)])
    speciality = StringField('Speciality', validators=[Length(0, 64)])
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    phone_number = StringField('Phone Number', validators=[Length(0, 64)])
    submit = SubmitField('Submit')

class SelectAppointmentForm(Form):
    #appointment_time = DateTimeField('Select Appointment Time', validators=[Required()])
    appointment_time = DateField('Appoinment Schedule', format='%Y-%m-%d')
    submit = SubmitField('Schedule')

class AppointmentCompletedForm(Form):
    submit = SubmitField('Completed')