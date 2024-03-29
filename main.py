from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForms, LoginForms, CommentForms, ContactForms
import time


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)


# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    posts = relationship("BlogPost", back_populates="author")

    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


# TODO: Create a User table for all your registered users. 


with app.app_context():
    db.create_all()


def logged_in_user_only(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You need to Login.")
            return redirect(url_for("login"))
        else:
            return f(*args, **kwargs)
    return decorated_func


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

def is_image_url(url):
    # List of common image file extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']

    # Check if the URL ends with any of the image file extensions
    return any(url.lower().endswith(ext) for ext in image_extensions)




# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForms()
    if request.method == "POST":
        if form.validate_on_submit():
            email = form.data["email"]
            found_user = User.query.filter_by(email=email).first()
            if found_user:
                flash("Email already taken, Please try again.")
                return redirect(url_for("register"))
            hash_salted_pass = generate_password_hash(form.data["password"], method="pbkdf2:sha256", salt_length=10)
            new_user = User(
                email=form.data["email"],
                name=form.data["name"],
                password=hash_salted_pass

            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForms()
    if request.method == "POST":
        if form.validate_on_submit():
            user_email = form.data["email"]
            user_password = form.data["password"]
            found_user = User.query.filter_by(email=user_email).first()
            if found_user and check_password_hash(found_user.password, user_password):
                login_user(found_user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Invalid Credentials! Please try again.")
                return redirect(url_for("login"))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForms()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comment(
            text=form.data["comment_body"],
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@logged_in_user_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        check_image = is_image_url(form.img_url.data)
        if check_image:
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
        else:
            flash("Please enter a valid Image URL. The URL must end with '.jpg', '.jpeg', '.png', '.gif', '.bmp', "
                  "'.svg', '.webp'")
            return redirect(url_for("add_new_post"))

    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@logged_in_user_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, logged_in=current_user.is_authenticated)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@logged_in_user_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/<name>_blogs")
def author_profile(name):
    author_id = int(request.args.get("post_author_id"))
    users_blogs = BlogPost.query.filter_by(author_id=author_id).all()
    return render_template("my_blogs.html", blogs=users_blogs,
                           logged_in=current_user.is_authenticated, author_name=name, author_id=author_id)



@app.route("/contact", methods=["GET", "POST"])
@logged_in_user_only
def contact():
    receivers_id = request.args.get("post_author_id")
    found_user = User.query.get(receivers_id)
    receivers_email = found_user.email
    form = ContactForms(
        name=current_user.name,
        email=current_user.email,
        subject= request.args.get("post_subtitle"),
        to=receivers_email
    )
    if form.validate_on_submit():
        pass
    return render_template("contact.html", form=form, logged_in=current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
