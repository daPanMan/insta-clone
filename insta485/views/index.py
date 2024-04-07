"""
Insta485 index (main) view.

URLs include:
/
"""
import pathlib
import hashlib
import os
import uuid
import arrow
import flask
import insta485

KEY = b'\xc8\x9eS\x8b\xac\x1d\xde\xfc\x11Gz\xa4 \x12S\x9bwt\xe9`\xb7\xd1 W'
insta485.app.secret_key = KEY


@insta485.app.route('/')
def show_index():
    """Display / route."""
    # flask.session.clear()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    # Connect to database
    connection = insta485.model.get_db()

    # Query database
    logname = flask.session['username']

    i_follow = []
    cur = connection.execute(
        '''
        SELECT username2
        FROM following
        WHERE username1 == ?''',
        (logname,)
    )
    followings = cur.fetchall()
    for following in followings:
        i_follow.append(following['username2'])
    i_follow.append(logname)
    i_follow = [*set(i_follow)]

    input_temp = ','.join('?' * len(i_follow))

    cur = connection.execute(
        "SELECT postid, owner, filename, created "
        "FROM posts "
        f"WHERE owner IN ({input_temp}) "
        "ORDER BY postid DESC",
        i_follow
    )

    posts = cur.fetchall()
    for post in posts:
        cur = connection.execute(
            '''
            SELECT COUNT(*)
            FROM likes
            WHERE postid == ?''',
            (post["postid"],)
        )
        post["created"] = arrow.get(post["created"])
        post["created"] = post["created"].humanize()
        likes = cur.fetchall()
        post["likes"] = likes[0]["COUNT(*)"]
        cur = connection.execute(
            '''
            SELECT COUNT(*)
            FROM likes
            WHERE postid == ? AND owner == ?''',
            (post['postid'], logname)
        )
        lognamelikes = cur.fetchall()
        post["lognamelikes"] = lognamelikes[0]["COUNT(*)"]

        cur = connection.execute(
            '''
            SELECT comments.owner, comments.text
            FROM comments
            WHERE postid == ?''',
            (post["postid"],)
        )
        comments = cur.fetchall()
        post["comments"] = comments
        cur = connection.execute(
            '''
            SELECT filename AS ownerimage
            FROM users
            WHERE username == ?''',
            (post["owner"],)
        )
        ownerimage = cur.fetchall()
        post["ownerimage"] = ownerimage[0]["ownerimage"]

    # Add database info to context
    context = {
            "logname": logname,
            "posts": posts
        }
    return flask.render_template("index.html", **context)


@insta485.app.route('/users/<username>/')
def show_user(username):
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    # Query database
    logname = flask.session['username']
    cur = connection.execute(
        '''SELECT postid, filename, owner
        FROM posts
        WHERE owner == ?''',
        (username,)
    )
    posts = cur.fetchall()

    cur = connection.execute(
        '''SELECT COUNT(*)
        FROM posts
        WHERE owner == ?''',
        (username,)
    )
    num_posts = cur.fetchall()
    num_posts = num_posts[0]["COUNT(*)"]

    cur = connection.execute(
        '''SELECT COUNT(*)
        FROM following
        WHERE username1 == ?''',
        (username,)
    )
    following = cur.fetchall()
    following = following[0]["COUNT(*)"]

    cur = connection.execute(
        '''SELECT COUNT(*)
        FROM following
        WHERE username2 == ?''',
        (username,)
    )
    followers = cur.fetchall()
    followers = followers[0]["COUNT(*)"]

    cur = connection.execute(
        '''SELECT COUNT(*)
        FROM following
        WHERE username2 == ? AND username1 == ?''',
        (username, logname)
    )
    log_follow_user = cur.fetchall()[0]["COUNT(*)"]

    cur = connection.execute(
        '''SELECT fullname
        FROM users
        WHERE username == ?''',
        (username,)
    )
    fullname = cur.fetchall()
    fullname = fullname[0]["fullname"]

    # Add database info to context
    context = {
            "logname": logname,
            "posts": posts,
            "num_posts": num_posts,
            "following": following,
            "followers": followers,
            "fullname": fullname,
            "username": username,
            "log_follow_user": log_follow_user
        }
    return flask.render_template("user.html", **context)


@insta485.app.route('/users/<username>/following/')
def show_user_following(username):
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    # user1 follows user2

    # Query database
    logname = flask.session['username']
    cur = connection.execute(
        '''SELECT DISTINCT f.username2 AS username, u.filename AS userimg
        FROM following f, users u
        WHERE f.username1 == ? AND f.username2 == u.username''',
        (username,)
    )
    followings = cur.fetchall()

    # Add database info to context
    # forced by stying to do this
    context = {
            "logname": logname,
            "followings": followings,
            "username": username
            }
    return flask.render_template("following.html", **context)


@insta485.app.route('/users/<username>/followers/')
def show_user_followers(username):
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    cur = connection.execute(
        '''SELECT username, fullname
        FROM users
        WHERE username == ?''',
        (username,)
    )
    if not cur:
        flask.abort(404)

    # user1 follows user2

    # Query database
    logname = flask.session['username']
    cur = connection.execute(
        '''SELECT DISTINCT f.username1 AS username
        FROM following f
        WHERE f.username2 == ? ''',
        (username,)
    )
    followers = cur.fetchall()

    cur = connection.execute(
        '''SELECT DISTINCT f.username2 AS username
        FROM following f
        WHERE f.username1 == ? ''',
        (username,)
    )
    i_follow = cur.fetchall()

    for follower in followers:
        if follower in i_follow:
            follower["followed_back"] = True
        elif follower not in i_follow:
            follower["followed_back"] = False
        cur = connection.execute(
            "SELECT filename AS userimg "
            "FROM users "
            "WHERE username = ?",
            (follower['username'],)
        )
        follower['userimg'] = cur.fetchone()['userimg']

    # Add database info to context
    context = {"logname": logname, "followers": followers}
    return flask.render_template("followers.html", **context)


@insta485.app.route('/posts/<postid>/')
def show_post(postid):
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    # Query database
    logname = flask.session['username']
    cur = connection.execute(
        '''SELECT postid, filename, owner, created
        FROM posts
        WHERE postid == ?''',
        (postid,)
    )
    post = cur.fetchall()
    post = post[0]
    post["created"] = arrow.get(post["created"])
    post["created"] = post["created"].humanize()
    cur = connection.execute(
            '''
            SELECT COUNT(*)
            FROM likes
            WHERE postid == ?''',
            (postid,)
        )
    likes = cur.fetchall()
    likes = likes[0]["COUNT(*)"]

    cur = connection.execute(
        '''SELECT filename
        FROM users
        WHERE username == ?''',
        (post['owner'],)
    )
    ownerimg = cur.fetchall()[0]['filename']

    cur = connection.execute(
            '''
            SELECT COUNT(*)
            FROM likes
            WHERE postid == ? AND owner == ?''',
            (postid, logname)
        )
    lognamelikes = cur.fetchall()
    lognamelikes = lognamelikes[0]["COUNT(*)"]

    cur = connection.execute(
        '''
        SELECT comments.commentid, comments.owner, comments.text
        FROM comments
        WHERE postid == ?''',
        (postid,)
    )
    comments = cur.fetchall()
    context = {
            "post": post,
            "comments": comments,
            "likes": likes,
            "logname": logname,
            "lognamelikes": lognamelikes,
            "ownerimg": ownerimg
        }
    return flask.render_template("post.html", **context)


@insta485.app.route('/explore/')
def show_explore():
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))

    # Query database
    logname = flask.session['username']
    cur = connection.execute(
        '''SELECT DISTINCT username
        FROM users
        WHERE username != ?
        ''',
        (logname,)
    )
    not_self = cur.fetchall()

    cur = connection.execute(
        '''SELECT DISTINCT f.username2 AS username
        FROM following f
        WHERE f.username1 == ?
        ''',
        (logname,)
    )
    followings = cur.fetchall()
    not_followings = []
    for selfless in not_self:
        if selfless not in followings:
            not_followings.append(selfless['username'])

    not_followings = [*set(not_followings)]
    input_temp = ','.join('?' * len(not_followings))

    cur = connection.execute(
        "SELECT username, filename AS userimg "
        "FROM users "
        f"WHERE username IN ({input_temp}) ",
        not_followings
    )
    notfollowings = cur.fetchall()

    # Add database info to context
    context = {"logname": logname, "notfollowings": notfollowings}
    return flask.render_template("explore.html", **context)


@insta485.app.route('/uploads/<filename>')
def show_image(filename):
    """Show the image."""
    if 'username' not in flask.session:
        flask.abort(403)
    url = insta485.app.config['UPLOAD_FOLDER']
    return flask.send_from_directory(url, filename)


@insta485.app.route('/accounts/login/', methods=['GET'])
def show_login():
    """Show the login."""
    if 'username' not in flask.session:
        return flask.render_template("login.html")
    return flask.redirect(flask.url_for('show_index'))


@insta485.app.route('/accounts/', methods=['POST'])
def handle_accounts_operations():
    """Display / route."""
    # Connect to database
    connection = insta485.model.get_db()
    operation = flask.request.form['operation']

    if operation == 'login':
        handle_login(connection)

    if operation == 'create':
        handle_create(connection)

    if operation == 'delete':
        handle_delete(connection)

    if operation == 'edit_account':
        handle_edit(connection)

    if operation == 'update_password':
        handle_update_password(connection)

    url = flask.request.args.get("target")
    if url is None:
        url = '/'
    return flask.redirect(url)


def handle_login(connection):
    """Handle the login."""
    username = flask.request.form['username']
    password = flask.request.form['password']

    # If username or password fields are empty, abort(400)
    if username is None or password is None:
        flask.abort(400)

    cur = connection.execute(
        """
        SELECT password
        FROM users
        WHERE users.username = ?
        """,
        (username,)
    )
    db_password = cur.fetchone()
    if db_password is None:
        flask.abort(403)
    algorithm = 'sha512'
    hash_obj = hashlib.new(algorithm)

    db_password = db_password['password']

    salt = db_password.split('$')[1]
    input_password_salted = salt + password
    hash_obj.update(input_password_salted.encode('utf-8'))
    input_password_hash = hash_obj.hexdigest()
    joined = "$".join([algorithm, salt, input_password_hash])
    input_password_hashed = joined

    # If user has an account
    if db_password == input_password_hashed:
        flask.session['username'] = username

    # If user does NOT have an account
    else:
        flask.abort(403)


def handle_create(connection):
    """Handle the create."""
    filename = flask.request.files['file'].filename

    cond1 = flask.request.form['username'] is None
    cond1 = cond1 or flask.request.form['password'] is None
    cond2 = flask.request.form['fullname'] is None
    cond2 = cond2 or flask.request.form['email'] is None or filename is None

    if cond1 or cond2:
        flask.abort(400)

    suffix = pathlib.Path(filename).suffix.lower()
    uuid_basename = f"{uuid.uuid4().hex}{suffix}"

    # Save to disk
    path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
    flask.request.files['file'].save(path)

    connection = insta485.model.get_db()
    cur = connection.execute(
        """
        SELECT username
        FROM users
        """
    )
    all_usernames = cur.fetchall()

    # Abort (409) if there == already an account with that username
    if flask.request.form['username'] in all_usernames:
        flask.abort(409)

    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form['password']
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    connection.execute(
        "INSERT INTO users(username, "
        "fullname, email, filename, password, created) "
        "VALUES (?, ?, ?, ?, ?, DATETIME('now'))",
        (
            flask.request.form['username'],
            flask.request.form['fullname'],
            flask.request.form['email'],
            uuid_basename, password_db_string
        )
    )

    # Log the user in
    flask.session['username'] = flask.request.form['username']


def handle_delete(connection):
    """Handle the delete."""
    # If user is not logged in
    if flask.session.get('username') is None:
        flask.abort(403)
    else:
        # Get the username of the logged in user
        username = flask.session['username']
        # Delete all post files created by user
        cur = connection.execute(
            """
            SELECT filename
            FROM posts
            WHERE owner = ?
            """,
            (username,)
        )
        post_files = cur.fetchall()
        for file in post_files:
            file = pathlib.Path(file['filename'])
            file = insta485.app.config["UPLOAD_FOLDER"]/file
            os.remove(file)

        # Delete user icon file
        cur = connection.execute(
            """
            SELECT filename
            FROM users
            WHERE username = ?
            """,
            (username,)
        )
        user_icon_file = cur.fetchone()['filename']
        user_icon_file = pathlib.Path(user_icon_file)
        upload_path = insta485.app.config["UPLOAD_FOLDER"]
        user_icon_file = upload_path/user_icon_file
        os.remove(user_icon_file)

        # Then delete all related entries to the user
        connection.execute(
            """
            DELETE FROM users
            WHERE username = ?
            """,
            (username,)
        )

        # delete all posts related to user
        connection.execute(
            """
            DELETE FROM posts
            WHERE owner = ?
            """,
            (username,)
        )

        # Clear the user's session
        flask.session.clear()


def handle_edit(connection):
    """Handle the edit."""
    if flask.session.get('username') is None:
        flask.abort(403)
    else:
        username = flask.session['username']

        fullname = flask.request.form['fullname']
        email = flask.request.form['email']
        fileobj = flask.request.files['file']
        if fullname is None or email is None:
            flask.abort(400)
        # Update user's name and email
        connection.execute(
            """
            UPDATE users
            SET fullname = ?, email = ?
            WHERE username = ?
            """,
            (fullname, email, username)
        )

        # If user supplied new image
        if fileobj is not None:
            filename = fileobj.filename

            stem = uuid.uuid4().hex
            suffix = pathlib.Path(filename).suffix.lower()
            uuid_basename = f"{stem}{suffix}"

            # Save to disk
            path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
            fileobj.save(path)

            # Get name of file to delete
            cur = connection.execute(
                "SELECT filename "
                "FROM users "
                "WHERE username = ?",
                (username,)
            )
            file_to_delete = cur.fetchall()[0]['filename']
            file_to_delete = pathlib.Path(file_to_delete)
            upload_path = insta485.app.config["UPLOAD_FOLDER"]
            file_to_delete = upload_path/file_to_delete
            os.remove(file_to_delete)

            # Update filename to new file's name
            connection.execute(
                "UPDATE users "
                "SET filename = ? "
                "WHERE username = ?",
                (uuid_basename, username,)
            )


def handle_update_password(connection):
    """Handle the update password."""
    # check if there is no input,
    # empty strings are valid btw, if it is abort 400
    if flask.request.form['password'] is None:
        flask.abort(400)
    if flask.request.form['new_password2'] is None:
        flask.abort(400)
    if flask.request.form['new_password1'] is None:
        flask.abort(400)

    if 'username' not in flask.session:
        flask.abort(403)

    # compare password against the user’s password hash in the database
    algorithm = 'sha512'
    hash_obj = hashlib.new(algorithm)

    username = flask.session["username"]
    cur = connection.execute(
            "SELECT * "
            "FROM users "
            "WHERE username == ?",
            (username,)
    )

    # if password == blank
    if cur.rowcount == 0:
        flask.abort(403)
    # seeing if fetched password == same as user entered one
    password_db = cur.fetchone()['password']
    old_salt = password_db.split('$')[1]
    input_password_salted = old_salt + flask.request.form['password']
    hash_obj.update(input_password_salted.encode('utf-8'))
    input_password_hash = hash_obj.hexdigest()
    input_password_db = "$".join([algorithm, old_salt, input_password_hash])

    if password_db != input_password_db:
        flask.abort(403)

    # comparing user entered passwords w eachother
    var = flask.request.form['new_password1']
    if var != flask.request.form['new_password2']:
        flask.abort(401)

    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form['new_password1']
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    # update the hashed password entry into the
    # database,- still not sure if this query == right
    connection.execute(
                "UPDATE users "
                "SET password = ? "
                "WHERE username = ?",
                (password_db_string, username,)
            )


@insta485.app.route('/accounts/logout/', methods=['POST'])
def show_logout():
    """Show the logout."""
    flask.session.clear()
    return flask.redirect(flask.url_for('show_login'))


@insta485.app.route('/accounts/create/')
def show_create():
    """Show the create."""
    if 'username' not in flask.session:
        return flask.render_template("create.html")

    return flask.redirect(flask.url_for('show_edit'))


@insta485.app.route('/accounts/delete/')
def show_delete():
    """Show the delete."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))
    logname = flask.session['username']
    context = {'logname': logname}
    return flask.render_template("delete.html", **context)


@insta485.app.route('/accounts/edit/')
def show_edit():
    """Show the edit."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))
    logname = flask.session['username']
    connection = insta485.model.get_db()

    cur = connection.execute(
        "SELECT filename "
        "FROM users "
        "WHERE username == ?",
        (logname,)
    )
    userimg = cur.fetchone()['filename']
    context = {'logname': logname, 'userimg': userimg}
    return flask.render_template("edit.html", **context)


@insta485.app.route('/accounts/password/')
def show_password():
    """Show the password."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for('show_login'))
    logname = flask.session['username']
    context = {'logname': logname}
    return flask.render_template("password.html", **context)


@insta485.app.route('/likes/', methods=['POST'])
def modify_likes():
    """Modify the likes."""
    target_url = flask.request.args.get('target')
    if not target_url:
        target_url = '/'
    logname = flask.session['username']
    postid = flask.request.form['postid']

    connection = insta485.model.get_db()

    operation = flask.request.form['operation']
    if operation == 'like':
        cur = connection.execute(
            "SELECT COUNT(*) "
            "FROM likes "
            "WHERE owner = ? AND postid = ?",
            (logname, postid)
        )
        likes = cur.fetchall()[0]
        if likes['COUNT(*)'] != 0:
            flask.abort(409)
        connection.execute(
            "INSERT INTO likes(owner, postid, created) "
            "VALUES(?, ?, DATETIME('now'))",
            (logname, postid)
        )
    else:
        cur = connection.execute(
            "SELECT COUNT(*) "
            "FROM likes "
            "WHERE owner = ? AND postid = ?",
            (logname, postid)
        )
        likes = cur.fetchall()[0]
        if likes['COUNT(*)'] == 0:
            flask.abort(409)
        connection.execute(
            "DELETE FROM likes "
            "WHERE owner = ? AND postid = ?",
            (logname, postid)
        )

    return flask.redirect(target_url)


@insta485.app.route('/comments/', methods=['POST'])
def modify_comments():
    """Modify the comments."""
    target_url = flask.request.args.get('target')
    if not target_url:
        target_url = '/'
    connection = insta485.model.get_db()
    logname = flask.session['username']
    operation = flask.request.form['operation']

    if operation == 'create':
        postid = flask.request.form['postid']

        text = flask.request.form['text']
        if text == '':
            flask.abort(400)
        connection.execute(
            """
            INSERT INTO comments(owner, postid, text, created)
            VALUES(?, ?, ?, DATETIME('now'))
            """,
            (logname, postid, text)
        )
    elif operation == 'delete':
        commentid = flask.request.form['commentid']
        cur = connection.execute(
            """
            SELECT COUNT(*)
            FROM comments
            WHERE owner == ? AND commentid == ?
            """,
            (logname, commentid)
        )
        num_comments = cur.fetchall()[0]["COUNT(*)"]
        if num_comments == 0:
            flask.abort(403)

        cur = connection.execute(
            """
            DELETE FROM comments
            WHERE commentid == ? AND owner == ?
            """,
            (commentid, logname)
        )

    return flask.redirect(target_url)


@insta485.app.route('/posts/', methods=['POST'])
def modify_posts():
    """Modify the posts."""
    target_url = flask.request.args.get('target')

    connection = insta485.model.get_db()
    logname = flask.session['username']
    if not target_url:
        target_url = '/users/'+logname+'/'
    operation = flask.request.form['operation']

    if operation == 'create':
        if flask.request.files['file'] == '':
            flask.abort(400)
        file = flask.request.files['file']
        filename = file.name

        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"

        path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
        file.save(path)

        connection.execute(
            "INSERT INTO posts(filename, owner, created) "
            "VALUES (?, ?, DATETIME('now')) ",
            (uuid_basename, logname)
        )
    elif operation == 'delete':
        postid = flask.request.form['postid']
        cur = connection.execute(
            "SELECT * "
            "FROM posts "
            "WHERE postid == ?",
            (postid,)
        )
        if not cur:
            flask.abort(403)

        cur = connection.execute(
            """
            SELECT owner
            FROM posts
            WHERE postid == ?
            """,
            (postid,)
        )
        postowner = cur.fetchone()['owner']
        if postowner != logname:
            flask.abort(403)

        cur = connection.execute(
            "SELECT filename "
            "FROM posts "
            "WHERE postid == ?",
            (postid,)
        )

        remove_path = insta485.app.config["UPLOAD_FOLDER"]
        remove_path = remove_path/cur.fetchone()['filename']

        os.remove(remove_path)
        connection.execute(
            """
            DELETE FROM posts
            WHERE postid == ?
            """,
            (postid,)
        )

    return flask.redirect(target_url)


@insta485.app.route('/following/', methods=['POST'])
def modify_following():
    """Modify the following."""
    operation = flask.request.form['operation']
    username = flask.request.form['username']
    logname = flask.session['username']
    connection = insta485.model.get_db()

    if operation == 'follow':
        cur = connection.execute(
            "SELECT COUNT(username2) "
            "FROM following "
            "WHERE username1 = ? AND username2 = ?",
            (logname, username,)
        )
        if cur.rowcount == 1:
            flask.abort(409)

        connection.execute(
            "INSERT INTO following(username1, username2, created) "
            "VALUES(?, ?, DATETIME('now'))",
            (logname, username,)
        )

    if operation == 'unfollow':
        cur = connection.execute(
            "SELECT COUNT(username2) "
            "FROM following "
            "WHERE username1 = ? AND username2 = ?",
            (logname, username,)
        )
        if cur.rowcount == 0:
            flask.abort(409)
        connection.execute(
            "DELETE FROM following "
            "WHERE username1 = ? AND username2 = ? ",
            (logname, username,)
        )
    url = flask.request.args.get("target")
    if url is None:
        url = '/'
    return flask.redirect(url)
