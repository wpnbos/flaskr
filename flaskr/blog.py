from flask import (
	Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort

from flaskr.auth import login_required, get_user_likes
from flaskr.db import get_db

bp = Blueprint("blog", __name__)

@bp.route('/')
def index():
	db = get_db()
	posts = db.execute(
		"SELECT p.id, title, body, created, author_id, username, likes FROM post p JOIN user u ON p.author_id = u.id ORDER BY created DESC"
	).fetchall()
	return render_template("blog/index.html", posts=posts)

@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
	if request.method == "POST":
		title = request.form["title"]
		body = request.form["body"]
		error = None

		if not title: 
			error = "Title is required."

		if error is not None: 
			flash(error)
		else: 
			db = get_db()
			db.execute(
				"INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)",
				(title, body, g.user["id"])
			)
			db.commit()
			return redirect(url_for("blog.index"))

	return render_template("blog/create.html")

def get_post(id, check_author=True):
	post = get_db().execute(
		"SELECT p.id, title, body, created, author_id, username, likes FROM post p JOIN user u ON p.author_id = u.id WHERE p.id = ?",
		(id,)
	).fetchone()

	if post is None: 
		abort(404, f"Post id {id} doesn't exist.")

	if check_author and post["author_id"] != g.user["id"]:
		abort(403)

	return post

def get_user_likes(id):
	likes = get_db().execute(
		"SELECT post_id FROM likes l WHERE l.user_id = ?", (id,)
	).fetchall()

	return [like["post_id"] for like in likes] 

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
	post = get_post(id)

	if request.method == "POST":
		title = request.form["title"]
		body = request.form["body"]
		error = None

		if not title:
			error = "Title is required."

		if error is not None:
			flash(error)
		else: 
			db = get_db()
			db.execute(
				"UPDATE post SET title = ?, body = ?"
				" WHERE id = ?", 
				(title, body, id)
			)
			db.commit()
			return redirect(url_for("blog.index"))

	return render_template("blog/update.html", post=post)

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
	print('DELETE DELETE DELETE')
	get_post(id)
	db = get_db()
	db.execute("DELETE FROM post WHERE id = ?", (id,))
	db.commit()
	return redirect(url_for("blog.index"))

@bp.route("/<int:id>/detail", methods=("GET",))
def detail(id):
	post = get_post(id, check_author=False)
	return render_template("blog/detail.html", post=post)

@bp.route("/<int:post_id>/like_post", methods=("POST",))
@login_required
def like(post_id):
	likes = get_user_likes(g.user["id"])
	db = get_db()
	print(likes)
	if post_id not in likes: 
		db.execute("UPDATE post SET likes = likes + 1 WHERE id = ?", (post_id,))
		db.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (g.user["id"], post_id))
		db.commit()
	elif post_id in likes:
		db.execute("UPDATE post SET likes = likes - 1 WHERE id = ?", (post_id,))
		db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (g.user["id"], post_id))
		db.commit()
	return redirect(url_for("blog.index"))