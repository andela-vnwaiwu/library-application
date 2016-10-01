# app/controllers/public.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_sqlalchemy import SQLAlchemy
from cloudinary.uploader import upload
from cloudinary.api import delete_resources
from cloudinary.utils import cloudinary_url
from app import app
from app.forms import EmailPasswordForm, RegistrationForm, UploadForm
from app.models import Users, Books, Categories, Borrowedbooks, User

db = SQLAlchemy(app)

public = Blueprint('public', __name__)

@app.before_request
def before_request():
    g.user = current_user

"""
    The routes are the routes for the front end of the application
    the user with a role == 'user' can view these routes
"""

@public.route('/')
def index():
    user = g.user
    return render_template('public/index.html', user = user)


@public.route('/register/', methods=['GET', 'POST'])
def register():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('public.index'))
    registerform = RegistrationForm()
    if request.method == 'POST' and registerform.validate():
        firstname = registerform.firstname.data
        lastname =  registerform.lastname.data
        email = registerform.email.data
        password = registerform.password.data

        save_user = Users.create_user(firstname, lastname, email, password)
        if save_user == None: 
            failure = 'This email address already exists in our register. \
            Please enter another one  or go to the login page to login.'
            return render_template('public/signup.html', form = registerform, failure = failure)
        
        #redirects to the dashboard page after successful RegistrationForm
        flash('You have been successfully registered')
        user = User(save_user.id, save_user.firstname, save_user.email, save_user.role)
        login_user(user)
        return redirect(url_for('public.dashboard')) 
    return render_template('public/signup.html', form = registerform)


@public.route('/login/', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('public.dashboard'))
    form = EmailPasswordForm()
    if request.method == 'POST' and form.validate():
        #Check the email and password in the database and log the user in        
        email = form.email.data
        password = form.password.data
        check_user = Users.get_user(email = email, password = password)
        if check_user == None:
            failure = 'Your details are not correct'
            return render_template('public/login.html', form = form, failure = failure)
        user = User(check_user.id, check_user.firstname, check_user.email, check_user.role)
        login_user(user)
        flash('Logged in Successfully')
        next = request.args.get('index')
        if user.role == 'admin':
            return redirect(next or url_for('admin.index'))
        return redirect(next or url_for('public.dashboard'))
    return render_template('public/login.html', form = form, user = g.user)


@public.route('/profile/', methods = ['GET', 'POST'])
@login_required
def profile():
    user = g.user
    person = Users.query.get(user.id)
    form = RegistrationForm(obj=user)
    if request.method == 'POST':
        person.firstname = request.form['firstname']
        person.lastname = request.form['lastname']
        Users.update()
        return redirect(url_for('public.dashboard'))
    return render_template('public/profile.html', person = person, user = user, form = form)

    
@public.route('/profile/upload', methods=['GET', 'POST'])
@login_required
def uploadpic():
    user = g.user
    form  = UploadForm()
    person = Users.query.get(user.id)
    if request.method == 'POST':
        file = request.files['file']
        if file:
            upload_result = upload(file)
            old_url = person.imagepath
            imageurl = upload_result['url']
            if old_url is None:
                person.imagepath = imageurl
                Users.update()
            else:
                old_image_name = old_url.split('/')[-1].split('.')[0]
                delete_old_image = delete_resources([old_image_name])
                person.imagepath = imageurl
                Users.update()
            return redirect(url_for('public.profile'))
    return render_template('public/picture_upload.html', user = user, form = form)



@public.route('/dashboard/')
@login_required
def dashboard():
    user = g.user
    books = Books.query.all()
    categories = Categories.query.all()
    user_borrowed = Borrowedbooks.query.filter_by(userid = user.id)#.order_by(Borrowedbooks.timeborrowed)
    if user_borrowed: 
        return render_template('public/dashboard.html', user = user, books = books, user_borrowed = user_borrowed, categories = categories)
    message = 'You do not have any books in your custody'
    return render_template('public/dashboard.html', user = user, message = message)

@public.route('/books/')
@login_required
def books():
    user = g.user
    books = Books.query.all()
    categories = Categories.query.all()
    return render_template('public/books.html', books = books, categories = categories, user = user)


@public.route('/borrowbook/<string:title>')
@login_required
def borrow(title):
    user = g.user
    book = Books.get_book(title)
    not_returned = Borrowedbooks.check_borrowed(user, book)
    if book.quantity > 0:
        if not_returned:
            failure ='Sorry, you can not borrow this book as you '\
            'have not returned this book you collected before' 
            return render_template('public/books.html', failure = failure, user = user)
            return not_returned.status
        borrow_book = Borrowedbooks.save_borrowed(book, user)
        book.quantity = book.quantity - 1
        book.update()
        success = 'You have succesfully borrowed this book'
        return redirect(url_for('public.dashboard', success = success))
    failure ='Sorry the book is no longer available'
    return render_template('public/books.html', user = user, failure = failure)


@public.route('/returnbook/<string:title>')
@login_required
def replace(title):
    user = g.user
    book = Books.get_book(title)

    ''' 
        checks if a borrowed book returned status is false 
        then sets it to true and increase the quantity by 1
    '''
    returned = Borrowedbooks.return_borrowed(book, user)
    if returned:
        success = 'You have returned this book'
        return redirect(url_for('public.dashboard', success = success))
    return render_template('public/books.html', user = user)

@public.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('public.login'))


# @public.route('/admin/login')
# def admin_login():
#     return redirect(url_for('admin.login'))