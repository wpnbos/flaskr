from flask import (
	Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)

import numpy as np
from werkzeug.exceptions import abort

from flaskr.auth import login_required, get_user_likes
from flaskr.db import get_db

import datetime 

bp = Blueprint("blog", __name__)

random_decimal = np.random.rand()

@bp.route('/update_decimal', methods=("POST", "GET"))
def update_decimal():
	random_decimal = np.random.rand()
	print("doing the thing")
	print(random_decimal)
	return redirect(url_for("blog.index"))

def get_comments(id):
	db = get_db()
	comments = db.execute(
		"SELECT c.id, parent_id, body, author_id, created, username FROM comments c JOIN user u ON c.author_id = u.id WHERE c.parent_id = ? ORDER BY created DESC",
	(id,)).fetchall()

	return comments 

def calc_elapsed(post):
	now = datetime.datetime.now()

	elapsed_seconds = (now - post["created"]).seconds
	elapsed = str(int(elapsed_seconds)) + " seconds ago "
	seconds_in_day = 60 * 60 * 24
	seconds_in_hour = 60 * 60
	if elapsed_seconds > seconds_in_day:
		elapsed = str(int(elapsed_seconds / seconds_in_day)) + " days ago "
	elif elapsed_seconds > seconds_in_hour:
		elapsed = str(int(elapsed_seconds / seconds_in_hour)) + " hours ago "
	elif elapsed_seconds > 60:
		elapsed = str(int(elapsed_seconds / 60)) + " minutes ago "

	return elapsed

@bp.route('/')
def index():
	db = get_db()
	posts = db.execute(
		"SELECT p.id, title, body, created, author_id, username, likes FROM post p JOIN user u ON p.author_id = u.id ORDER BY created DESC"
	).fetchall()

	post_dicts = [dict(post) for post in posts]
	for post in post_dicts:
		post["elapsed"] = calc_elapsed(post)
		print(type(post["elapsed"]))
		print(type(post["username"]))

	print(type(posts[0]))
	print(type(post_dicts[0]))
	return render_template("blog/index.html", posts=post_dicts, rand=random_decimal)

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

	post = dict(post)

	post["elapsed"] = calc_elapsed(post)

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
	get_post(id)
	db = get_db()
	db.execute("DELETE FROM post WHERE id = ?", (id,))
	db.commit()
	return redirect(url_for("blog.index"))

def comment(id):
	body = request.form["body"]
	error = None

	if not body: 
		error = "Comment text is required."

	if error is not None: 
		flash(error)
	else: 
		db = get_db()
		db.execute(
			"INSERT INTO comments (parent_id, body, author_id) VALUES (?, ?, ?)",
			(id, body, g.user["id"])
		)
		db.commit()

@bp.route("/<int:id>/detail", methods=("GET", "POST"))
def detail(id):
	if request.method == "POST":
		if g.user is None: 
			return redirect(url_for("auth.login"))
		comment(id)

		comments = get_comments(id)
		body = render_template("blog/comments.html", id=id, comments=comments)
		return jsonify(body=body)

	post = get_post(id, check_author=False)
	comments = get_comments(id)
	return render_template("blog/detail.html", post=post, comments=comments)

@bp.route("/<int:post_id>/like_post", methods=("POST",))
@login_required
def like(post_id):
	likes = get_user_likes(g.user["id"])
	
	db = get_db()

	#like the post
	if post_id not in likes: 
		db.execute("UPDATE post SET likes = likes + 1 WHERE id = ?", (post_id,))
		db.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (g.user["id"], post_id))
		db.commit()
	#unlike the post
	elif post_id in likes:
		db.execute("UPDATE post SET likes = likes - 1 WHERE id = ?", (post_id,))
		db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (g.user["id"], post_id))
		db.commit()

	g.likes = get_user_likes(g.user["id"])

	body = render_template("blog/like_button.html", post=get_post(post_id, check_author=False))

	return jsonify(body=body)