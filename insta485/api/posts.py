"""REST API for posts."""
import hashlib
import flask
import insta485


@insta485.app.route("/api/v1/")
def resource():
    """Hardcoded route."""
    context = {
        "comments": "/api/v1/comments/",
        "likes": "/api/v1/likes/",
        "posts": "/api/v1/posts/",
        "url": "/api/v1/",
    }

    return flask.jsonify(**context)


@insta485.app.route("/api/v1/posts/")
def get_post():
    """Route to grab all the posts."""
    connection = insta485.model.get_db()

    username = flask.session.get("username") or \
        (flask.request.authorization and
         flask.request.authorization["username"])
    password = flask.request.authorization and\
        flask.request.authorization["password"]
    if password:
        authenticate(username, password, connection)
    if not username:
        flask.abort(403)

    most_recent = connection.execute(
        """
        SELECT MAX(postid) as max
        FROM posts
        """
    ).fetchone()["max"]
    url = flask.request.path

    query = flask.request.query_string.decode()

    if query:
        url += "?" + query

    idb = flask.request.args.get("postid_lte",
                                 default=most_recent, type=int)
    p_n = flask.request.args.get("page", default=0, type=int)
    size = flask.request.args.get("size", default=10, type=int)

    if p_n < 0 or idb <= 0 or size < 0:
        response = flask.jsonify({"message": "Bad Request"})
        response.status_code = 400
        return response, 400

    cur = connection.execute(
        """SELECT username2
        FROM following
        WHERE username1 == ?""",
        (username,),
    )
    i_follow = set(following["username2"] for following in
                   cur.fetchall()) | {username}

    posts = connection.execute(
        "SELECT postid "
        "FROM posts "
        f"WHERE owner IN ({','.join('?'*len(i_follow))}) "
        "AND postid <= ? "
        "ORDER BY postid DESC "
        "LIMIT ? "
        "OFFSET ?",
        (*i_follow, idb, size, (p_n * size)),
    ).fetchall()

    results = [
        {"postid": int(post["postid"]),
         "url":f"/api/v1/posts/{post['postid']}/"}
        for post in posts
    ]

    next_url = f"/api/v1/posts/?size={size}&page={p_n + 1}&postid_lte={idb}"\
        if len(posts) >= size else ""

    return flask.jsonify(**{"url": url, "next": next_url, "results": results})


@insta485.app.route("/api/v1/posts/<int:postid_url_slug>/")
def get_post_by_id(postid_url_slug):
    """Route to grab a single post and all its content."""
    connection = insta485.model.get_db()
    if "username" in flask.session:
        username = flask.session["username"]
    elif flask.request.authorization:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        authenticate(username, password, connection)
    else:
        flask.abort(403)

    cur = connection.execute(
        """
    SELECT filename, owner, created
    FROM posts
    WHERE postid == ?
    """,
        (postid_url_slug,),
    )
    post = cur.fetchall()

    cur = connection.execute(
        """
    SELECT *
    FROM comments
    WHERE postid == ?
    ORDER BY commentid
    """,
        (postid_url_slug,),
    )
    comments = cur.fetchall()

    cur = connection.execute(
        """
    SELECT COUNT(likeid)
    FROM likes
    WHERE postid = ?
    """,
        (postid_url_slug,),
    )
    likes = cur.fetchone()

    cur = connection.execute(
        """
    SELECT COUNT(likeid)
    FROM likes
    WHERE postid = ?
    AND owner = ?
    """,
        (
            postid_url_slug,
            username,
        ),
    )
    owner_likes = cur.fetchone()

    cur = connection.execute(
        """
    SELECT likeid
    FROM likes
    WHERE postid = ?
    AND owner = ?
    """,
        (
            postid_url_slug,
            username,
        ),
    )
    likeid = cur.fetchall()
    if len(post) == 0:
        response = flask.jsonify({"message": "Bad Request"})
        response.status_code = 404
        return response, 404

    if owner_likes["COUNT(likeid)"] > 0:
        likeid = likeid[0]

    cur = connection.execute(
        """
    SELECT *
    FROM users
    WHERE username = ?
    """,
        (post[0]["owner"],),
    )

    # owner = cur.fetchall()

    comments_list = []
    for comment in comments:
        comment_dict = {
            "commentid": comment["commentid"],
            "lognameOwnsThis": False,
            "owner": comment["owner"],
            "ownerShowUrl": "",
            "text": comment["text"],
            "url": "",
        }
        if comment["owner"] == username:
            comment_dict["lognameOwnsThis"] = True
        comment_dict["ownerShowUrl"] = f"/users/{comment['owner']}/"
        comment_dict["url"] = f"/api/v1/comments/{comment['commentid']}/"
        comments_list.append(comment_dict)

    context = {}
    context["comments"] = comments_list
    context["comments_url"] = f"/api/v1/comments/?postid={postid_url_slug}"
    context["created"] = str(post[0]["created"])
    context["imgUrl"] = f"/uploads/{post[0]['filename']}"
    context["likes"] = {
        "lognameLikesThis": False,
        "numLikes": likes["COUNT(likeid)"],
        "url": None,
    }
    if likeid:
        context["likes"]["lognameLikesThis"] = True
        context["likes"]["url"] = f"/api/v1/likes/{likeid['likeid']}/"
    context["owner"] = post[0]["owner"]
    context["ownerImgUrl"] = f"/uploads/{cur.fetchall()[0]['filename']}"
    context["ownerShowUrl"] = f"/users/{post[0]['owner']}/"
    context["postShowUrl"] = f"/posts/{postid_url_slug}/"
    context["postid"] = postid_url_slug
    context["url"] = f"/api/v1/posts/{postid_url_slug}/"

    # response = flask.jsonify({"message": "OK"})
    # response.status_code = 200

    return flask.jsonify(**context), 200


@insta485.app.route("/api/v1/likes/", methods=["POST"])
def post_like():
    """Route to create a like."""
    connection = insta485.model.get_db()
    if "username" in flask.session:
        username = flask.session["username"]
    elif flask.request.authorization:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        authenticate(username, password, connection)
    else:
        flask.abort(403)
    logname = username

    postid = flask.request.args.get("postid", type=int)

    # Check if the like already exists
    cur = connection.execute(
        """
    SELECT likeid
    FROM likes
    WHERE owner = ? AND postid = ?
    """,
        (
            logname,
            postid,
        ),
    )
    like_exists = cur.fetchall()
    likeid = 0
    cur = connection.execute(
        """
    SELECT COUNT(*)
    FROM posts
    WHERE postid = ?
    """,
        (
            postid,
        ),
    )
    num_posts = cur.fetchone()['COUNT(*)']

    if len(like_exists) > 0:
        likeid = like_exists[0]
        # response = flask.jsonify({"message": "OK"})
        # response.status_code = 200
        status = 200
    elif num_posts <= 0:
        response = flask.jsonify({"message": "ERROR"})
        response.status_code = 404
        return response, 404
    else:
        connection.execute(
            """
            INSERT INTO likes (owner, postid, created)
            VALUES (?, ?, DATETIME('now'))
            """,
            (
                logname,
                postid,
            ),
        )
        cur = connection.execute(
            """
            SELECT likeid
            FROM likes
            WHERE owner = ? AND postid = ?
            """,
            (
                logname,
                postid,
            ),
        )
        like_exists = cur.fetchall()
        likeid = like_exists[0]
        status = 201
        # response = flask.jsonify({"message": "CREATED"})
        # response.status_code = 201

    context = {}
    context["likeid"] = likeid["likeid"]
    context["url"] = f"/api/v1/likes/{likeid['likeid']}/"

    return flask.jsonify(**context), status


@insta485.app.route("/api/v1/likes/<likeid>/", methods=["DELETE"])
def delete_like(likeid):
    """Route to delete a like."""
    connection = insta485.model.get_db()
    if "username" in flask.session:
        username = flask.session["username"]
    elif flask.request.authorization:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        authenticate(username, password, connection)
    else:
        flask.abort(403)
    logname = username

    cur = connection.execute(
        """
    SELECT owner
    FROM likes
    WHERE likeid = ?
    """,
        (likeid,),
    )
    owner = cur.fetchall()

    # Check if like id exists
    if len(owner) == 0:
        response = flask.jsonify({"message": "ERROR"})
        response.status_code = 404
        return response, 404
    # Check if the logged in user owns the like they are trying to delete
    if owner[0]["owner"] != logname:
        response = flask.jsonify({"message": "ERROR"})
        response.status_code = 403
        return response, 403

    # Delete the like
    connection.execute(
        """
    DELETE FROM likes
    WHERE likeid = ?
    """,
        (likeid,),
    )
    response = flask.jsonify({"message": "NO CONTENT"})
    response.status_code = 204
    return response, 204


@insta485.app.route("/api/v1/comments/", methods=["POST"])
def post_comment():
    """Route to create a comment."""
    connection = insta485.model.get_db()
    if "username" in flask.session:
        username = flask.session["username"]
    elif flask.request.authorization:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        authenticate(username, password, connection)
    else:
        flask.abort(403)
    logname = username

    postid = flask.request.args.get("postid", type=int)
    text = flask.request.json["text"]

    connection.execute(
        """
    INSERT INTO comments (owner, postid, text, created)
    VALUES (?, ?, ?, DATETIME('now'))
    """,
        (logname, postid, text),
    )
    cur = connection.execute(
        """
    SELECT last_insert_rowid()
    """,
    )
    commentid = cur.fetchone()["last_insert_rowid()"]
    context = {}
    context["commentid"] = commentid
    context["lognameOwnsThis"] = True
    context["owner"] = logname
    context["ownerShowUrl"] = f"/users/{logname}/"
    context["text"] = text
    context["url"] = f"/api/v1/comments/{commentid}/"
    # response = flask.jsonify({"message": "NO CONTENT"})
    # response.status_code = 201
    return flask.jsonify(**context), 201


@insta485.app.route("/api/v1/comments/<commentid>/", methods=["DELETE"])
def delete_comment(commentid):
    """Route to delete a comment."""
    connection = insta485.model.get_db()
    if "username" in flask.session:
        username = flask.session["username"]
    elif flask.request.authorization:
        username = flask.request.authorization["username"]
        password = flask.request.authorization["password"]
        authenticate(username, password, connection)
    else:
        flask.abort(403)
    logname = username

    # Check if the comment exists
    cur = connection.execute(
        """
    SELECT owner
    FROM comments
    WHERE commentid = ?
    """,
        (commentid,),
    )
    comment_exists = cur.fetchall()

    if len(comment_exists) == 0:
        response = flask.jsonify({"message": "COMMENT DOESN'T EXIST"})
        response.status_code = 404
        return response, 404
    comment_exists = comment_exists[0]
    # Check if user owns comment
    if comment_exists["owner"] != logname:
        response = flask.jsonify({"message": "UNABLE TO DELETE\
                                COMMENT YOU DO NOT OWN"})
        response.status_code = 403
        return response, 403

    connection.execute(
        """
    DELETE FROM comments
    WHERE commentid = ?
    """,
        (commentid,),
    )

    response = flask.jsonify({"message": "NO CONTENT"})
    response.status_code = 204
    return response, 204


def authenticate(username, password, connection):
    """Authenticate."""
    cur = connection.execute(
        """
    SELECT password
    FROM users
    WHERE username = ?
    """,
        (username,),
    )

    db_password = cur.fetchone()
    if db_password is None:
        flask.abort(403)
    algorithm = "sha512"
    hash_obj = hashlib.new(algorithm)

    db_password = db_password["password"]

    salt = db_password.split("$")[1]
    input_password_salted = salt + password
    hash_obj.update(input_password_salted.encode("utf-8"))
    input_password_hash = hash_obj.hexdigest()
    joined = "$".join([algorithm, salt, input_password_hash])
    input_password_hashed = joined

    # If user has an account
    if db_password != input_password_hashed:
        flask.abort(403)
