from flask import Flask, redirect, render_template, session, url_for, request, flash, send_from_directory
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, validators, TextAreaField, SelectField, DateField, FileField
from passlib.hash import sha256_crypt
from functools import wraps #USE IT FOR SESSION VALIDATION
from datetime import date
import os
from werkzeug.utils import secure_filename
from flask_wtf.file import FileRequired
from werkzeug.datastructures import CombinedMultiDict

#Instantiate Flask and MySQL
app = Flask(__name__)
mysql = MySQL(app)
app.jinja_env.add_extension('jinja2.ext.do')

#App configuration
app.config['SECRET_KEY'] = 'somesecret26'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DB'] = 'poster_wall'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Vimal@1998'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['UPLOAD_FOLDER'] = 'uploads/'

#Routes

#Login Check
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised Access, Login To Continue','danger')
            return redirect(url_for('login'))
    return wrap

#Landing Page Route
@app.route('/')
@app.route('/home')
@app.route('/index')
def index():
    return render_template('index.html')

#Welcome Guide Route
@app.route('/welcome-guide')
def guide():
    return render_template('welcome-guide.html')

#Login Route
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        email = form.email.data
        password = form.password.data
        #Access database
        cur = mysql.connection.cursor()
        #Search the database for actual credentials
        result = cur.execute('SELECT * FROM users WHERE email = %s',[email])
        if result>0:
            data = cur.fetchone()
            password_actual = data['password']
            if password == password_actual:
                session['logged_in'] = True
                session['society'] = data['society']
                session['email'] = data['email']
                if data['name'] == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Incorrect Password','danger')
                return render_template('login.html', form=form)
        else:
            flash('User Doesnot Exists','danger')
            return render_template('login.html', form=form)
        cur.close()
    return render_template('login.html',form=form)

#Request Account Route
@app.route('/add-user', methods=['GET','POST'])
def req_user():
    form = RequestForm(request.form)
    if request.method == 'POST':
        name = form.name.data
        email = form.email.data
        phone = form.phone.data
        society = form.society.data
        #Establish Data Base Connection
        cur = mysql.connection.cursor()
        #Writing into DB tables
        cur.execute('INSERT INTO requests(name,email,phone,society) VALUES (%s,%s,%s,%s)',(name,email,phone,society))
        #Commiting Changes
        cur.connection.commit()
        #Close DB connection
        cur.close()
        flash('Your Request Is Recieved And Is Waiting To Be Verified. You Will Recive A Confirmation Email With Your Password Within 24 Hours. Sit Tight!','success')
        return redirect(url_for('login'))
    else:
        return render_template('registration.html',form=form)

#Dashboard Route
@is_logged_in
@app.route('/dashboard')
def dashboard():
    society = session['society']
    cur = mysql.connection.cursor()
    results = cur.execute('SELECT * FROM events WHERE society = %s',[society])
    if results > 0:
        data = cur.fetchall()
        return render_template('dashboard.html',data=data)
    else:
        flash('No Events Have Been Added Yet','danger')
        return render_template('dashboard.html')

#Event Creation Route
@is_logged_in
@app.route('/create', methods=['GET','POST'])
def create():
    form = EventForm(CombinedMultiDict((request.files,request.form)))
    if request.method == 'POST' and form.validate:
        title = form.title.data
        image = form.image.data
        description = form.description.data
        society = session['society']
        filename = secure_filename(image.filename)
        file_location = os.path.join('static',app.config['UPLOAD_FOLDER'],filename)
        image.save(file_location)
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO events(title,image,description,society) VALUES (%s,%s,%s,%s)',(title,file_location,description,society))
        cur.connection.commit()
        cur.close()
        flash('Event Added Succesfully','success')
        return redirect(url_for('dashboard'))
    return render_template('create.html',form=form)


#Password Change Route
@is_logged_in
@app.route('/change-password', methods = ['GET','POST'])
def password_change():
    form = PasswordChange(request.form)
    if request.method == 'POST' and form.validate:
        current_password = form.current_password.data
        new_password = form.new_password.data
        confirm = form.confirm.data
        society = session['society']
        #Establish database connections
        cur = mysql.connection.cursor()
        #Retriving Data
        results = cur.execute('SELECT * FROM users WHERE society = %s',[society])
        #Updating Database Values
        if results > 0:
            data = cur.fetchone()
            password = data['password']
            if password == current_password:
                if new_password == confirm:
                    cur.execute('UPDATE users SET password = %s WHERE society = %s',(new_password,society))
                    cur.connection.commit()
                    flash('Password Updated Succesfully','success')
                    return redirect(url_for('password_change'))
                else:
                    flash('Passwords Do Not Match. Cannot Confirm New Password','danger')
                    return redirect(url_for('password_change'))
            else:
                flash('You have entered the wrong password','danger')
                return redirect(url_for('password_change'))
            cur.close()
    return render_template('change_password.html', form=form)

#Logout Route
@is_logged_in
@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully','success')
    return redirect(url_for('login'))


# Assets

#Login Form
class LoginForm(Form):
    email = StringField('Email', validators=[validators.required])
    password = PasswordField('Password', validators=[validators.required])

#Request Form
class RequestForm(Form):
    name = StringField('Name', validators=[validators.required])
    email = StringField('Email', validators=[validators.required])
    phone = StringField('Contact Number', validators=[validators.required])
    society = StringField('Society / Student Chapter', validators=[validators.required])

#Event Form
class EventForm(Form):
    title = StringField('Name', validators = [validators.required])
    description = TextAreaField('Description',validators = [validators.required])
    image = FileField(validators = [FileRequired()])
    society = StringField()

#Password Change Form
class PasswordChange(Form):
    current_password = PasswordField('Enter Current Password', validators = [validators.required])
    new_password = PasswordField('Enter New Password', validators = [validators.required])
    confirm = PasswordField('Confirm New Password', validators = [validators.required])

#Sever Startup
if __name__ == '__main__':
    app.run(debug = True)
