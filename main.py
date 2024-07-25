import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from flask_ckeditor import CKEditor
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import date
import datetime as dt
import requests
import re
import smtplib
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

# Direct path to the database
db_path = 'C:/Users/Siris/Desktop/GitHub Projects 100 Days NewB/_24_0071__Day67_RESTful_Blog_with_Editing__240717/NewProject/r20-r29/r25_env_NWY/instance/posts.db'

# Ensure the instance folder exists
instance_folder = os.path.dirname(db_path)
if not os.path.exists(instance_folder):
    os.makedirs(instance_folder)

# Use the direct path to the database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

Bootstrap5(app)
ckeditor = CKEditor(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Models
Base = declarative_base()


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()

# Forms
from forms import CreatePostForm, RegisterForm, UserRegisterForm, LoginForm


# Utility functions
def slugify(value):
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[\s_-]+', '-', value)
    return value


app.jinja_env.filters['slugify'] = slugify


def fetch_posts(limit=3):
    db_posts = BlogPost.query.order_by(BlogPost.date.desc()).limit(limit).all()
    db_posts_list = []
    for post in db_posts:
        if "monty python" in post.title.lower():
            image = "montyPython.jpg"
        elif "lego" in post.title.lower():
            image = "legos.jpg"
        else:
            image = post.img_url

        sanitized_title = re.sub(r'[^\x00-\x7F]+', '', post.title)[:50]
        db_posts_list.append({
            "title": post.title,
            "subtitle": post.subtitle,
            "author": post.author,
            "date": post.date,
            "image": image,
            "body": post.body
        })
    return db_posts_list


def validate_input(name, email, phone, message):
    if not all([name, email, phone, message]):
        return False
    if "@" not in email or "." not in email:
        return False
    return True


def send_email(name, email, phone, message):
    email_subject = "New Contact Form Submission for Siris's Blog"
    email_body = f"Subject:{email_subject}\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}"
    my_from_email1 = os.environ.get('MY_FROM_EMAIL1', 'Custom Message / Email does not exist')
    password = os.environ.get('PASSWORD', 'Custom Message / Password does not exist')
    their_email2 = os.environ.get('THEIR_EMAIL2', 'Custom Message / Email does not exist')

    try:
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=my_from_email1, password=password)
            connection.sendmail(
                from_addr=my_from_email1,
                to_addrs=their_email2,
                msg=email_body
            )
        logging.info("Email sent successfully")
    except smtplib.SMTPException as e:
        logging.error(f"Failed to send email: {e}")


# Routes
@app.route('/')
@app.route('/home')
def home():
    all_posts = fetch_posts(limit=3)
    return render_template("index.html", posts=all_posts, page='home')


@app.route('/post/<slug>')
def post(slug):
    all_posts = fetch_posts()
    post = next((p for p in all_posts if slugify(p['title']) == slug), None)
    if post is None:
        return "Post not found", 404
    return render_template("post.html", post=post)


@app.route('/about')
def about():
    return render_template('about.html', page='about')


@app.route('/contact', methods=["GET", "POST"])
def contact():
    form_submitted = False
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        if validate_input(name, email, phone, message):
            send_email(name, email, phone, message)
            form_submitted = True
            logging.info(f"Contact form submitted: {name}, {email}")
        else:
            logging.warning("Validation failed for contact form submission.")
            return "Invalid input data", 400
    return render_template("contact.html", form_submitted=form_submitted)


@app.route('/new-post', methods=["GET", "POST"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=date.today().strftime("%B %d, %Y"),
            body=form.body.data,
            author=form.author.data,
            img_url=form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form, is_edit=False)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        author=post.author,
        img_url=post.img_url,
        body=post.body
    )
    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.body = form.body.data
        post.author = form.author.data
        post.img_url = form.img_url.data
        db.session.commit()
        return redirect(url_for("post", slug=slugify(post.title)))
    return render_template("make-post.html", form=form, is_edit=True)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get_or_404(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = UserRegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
