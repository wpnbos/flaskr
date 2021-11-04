from flask import (
	Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)

import numpy as np
from werkzeug.exceptions import abort

import json 

from flaskr.auth import login_required, get_user_likes
from flaskr.db import get_db

import datetime 

bp = Blueprint("blog", __name__)

random_decimal = np.random.rand()


def get_children(parent_id):
	db = get_db()
	return [dict(comment) for comment in db.execute("SELECT * FROM comments c JOIN user u ON c.author_id = u.id WHERE parent_id = (?)", (parent_id,)).fetchall()]

def comment_tree(comment, level=0):
	comment["level"] = level
	comment["children"] = get_children(comment["id"])
	comment["elapsed"] = calc_elapsed(comment)
	for child in comment["children"]:
		comment_tree(child, level+1)

def get_comments(id):
	"""find a comment
		find a all children"""
	db = get_db()
	comments = db.execute(
		"SELECT c.id, parent_id, post_id, body, author_id, created, username, likes FROM comments c JOIN user u ON c.author_id = u.id WHERE c.post_id = ? ORDER BY created DESC",
	(id,)).fetchall()

	tmp = []

	for comment in comments: 
		comment = dict(comment)
		
		tmp.append(comment)

	comments = [comment for comment in tmp if not comment["parent_id"]]
	for comment in comments: 
		comment_tree(comment)

	return comments 

def calc_elapsed(post):
	now = datetime.datetime.utcnow()

	elapsed_seconds = (now.timestamp() - post["created"].timestamp())

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

@bp.before_request
def get_user_karma():
	if g.user:
		db = get_db()
		g.karma = db.execute(
			"SELECT COUNT (post_id) FROM post p JOIN likes l ON p.id = l.post_id WHERE p.author_id = (?)", (g.user["id"],)
		).fetchone()[0]
		g.karma += db.execute(
			"SELECT COUNT (comment_id) FROM comments c JOIN c_likes l on c.id = l.comment_id WHERE c.author_id = (?)", (g.user["id"],)
		).fetchone()[0]

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
	parent_id = request.form["parent_id"]
	error = None

	if not body: 
		error = "Comment text is required."

	if error is not None: 
		flash(error)
	else: 
		db = get_db()
		db.execute(
			"INSERT INTO comments (post_id, parent_id, body, author_id) VALUES (?, ?, ?, ?)",
			(id, parent_id, body, g.user["id"])
		)
		db.commit()

@login_required
def save_reply(id, parent):
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
		child = db.execute("SELECT max(id) FROM comments").fetchone()

		db.execute(
			"INSERT INTO children (parent_id, child_id) VALUES (?, ?)",
			(parent, child[0])
		)
		db.commit()

@bp.route("/<int:id>/detail", methods=("GET", "POST"))
def detail(id):
	if request.method == "POST":
		if g.user is None: 
			return jsonify(redirect=url_for("auth.login"))
		comment(id)

		comments = get_comments(id)
		body = render_template("blog/comments.html", id=id, comments=comments)
		return jsonify(body=body)

	post = get_post(id, check_author=False)
	comments = get_comments(id)

	return render_template("blog/detail.html", post=post, comments=comments)


@bp.route("/<int:id>/detail/<int:parent>", methods=("POST",))
def reply(id, parent):
	if g.user is None:
		return redirect(url_for("auth.login"))
	save_reply(id, parent)

	comments = get_comments(id)
	body = render_template("blog/comments.html", id=id, comments=comments)
	return jsonify(body=body)

@bp.route("/<int:post_id>/like_post", methods=("POST",))
def like(post_id):
	print(g.user)
	if g.user is None:
		return jsonify(redirect=url_for("auth.login"))
	likes = get_user_likes(g.user["id"])
	
	db = get_db()

	#like the post
	if post_id not in likes["posts"]: 
		db.execute("UPDATE post SET likes = likes + 1 WHERE id = ?", (post_id,))
		db.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (g.user["id"], post_id))
		db.commit()
	#unlike the post
	elif post_id in likes["posts"]:
		db.execute("UPDATE post SET likes = likes - 1 WHERE id = ?", (post_id,))
		db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (g.user["id"], post_id))
		db.commit()

	g.likes = get_user_likes(g.user["id"])

	body = render_template("blog/like_button.html", post=get_post(post_id, check_author=False))
	print("returns")
	return jsonify(body=body)

@bp.route("/<int:post_id>/comment/<int:comment_id>/like", methods=("POST",))
@login_required
def like_comment(comment_id, post_id):
	likes = get_user_likes(g.user["id"])
	likes = likes["comments"]
	db = get_db()

	#like the post
	if comment_id not in likes: 
		db.execute("UPDATE comments SET likes = likes + 1 WHERE id = ?", (comment_id,))
		db.execute("INSERT INTO c_likes (user_id, comment_id) VALUES (?, ?)", (g.user["id"], comment_id))
		db.commit()
	#unlike the post
	elif comment_id in likes:
		db.execute("UPDATE comments SET likes = likes - 1 WHERE id = ?", (comment_id,))
		db.execute("DELETE FROM c_likes WHERE user_id = ? AND comment_id = ?", (g.user["id"], comment_id))
		db.commit()

	g.likes = get_user_likes(g.user["id"])

	comments = get_comments(post_id)
	body = render_template("blog/comments.html", id=post_id, comments=comments)

	return jsonify(body=body)

