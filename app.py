from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import math

app = Flask(__name__)
app.secret_key = 'tester'

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="test",
    database="skistays"
)

# Number of items per page for pagination
PER_PAGE = 50


def get_pagination_params():
    """
    Read 'page' from query string, ensure it's at least 1,
    compute offset for SQL LIMIT/OFFSET.
    """
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    offset = (page - 1) * PER_PAGE
    return page, offset


#
# ──────────── RESORT LISTING ────────────
#
@app.route('/', methods=['GET'])
def home():
    page, offset = get_pagination_params()

    cnt = db.cursor()
    cnt.execute("SELECT COUNT(*) FROM Resort;")
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT resort_id,
               resort_name,
               location,
               highest_point,
               lowest_point,
               difficult_slope,
               total_slope,
               total_lifts
        FROM Resort
        ORDER BY resort_id
        LIMIT %s OFFSET %s;
    """, (PER_PAGE, offset))
    resorts = cur.fetchall()

    return render_template(
        'index.html',
        resorts=resorts,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_resort=session.get('fav_resort'),
        view='resorts'
    )

#
# ──────────── DASHBOARD ────────────
#
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))
    page, offset = get_pagination_params()

    cnt = db.cursor()
    cnt.execute("SELECT COUNT(*) FROM Resort;")
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT resort_id,
               resort_name,
               location,
               highest_point,
               lowest_point,
               difficult_slope,
               total_slope,
               total_lifts
        FROM Resort
        ORDER BY resort_id
        LIMIT %s OFFSET %s;
    """, (PER_PAGE, offset))
    resorts = cur.fetchall()

    return render_template(
        'dashboard.html',
        resorts=resorts,
        page=page,
        total_pages=total_pages,
        is_logged_in=True,
        user_name=session.get('user_name'),
        user_fav_resort=session.get('fav_resort'),
        view='resorts'
    )

#
# ──────────── TOGGLE FAVORITE ────────────
#
@app.route('/toggle_favorite/<int:resort_id>', methods=['POST'])
def toggle_favorite(resort_id):
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))

    user_id = session['user_id']
    cur = db.cursor()
    cur.execute("SELECT fav_resort FROM User WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    current = row[0] if row else None

    if current == resort_id:
        cur.execute("UPDATE User SET fav_resort = NULL WHERE user_id = %s", (user_id,))
        session['fav_resort'] = None
    else:
        cur.execute("UPDATE User SET fav_resort = %s WHERE user_id = %s", (resort_id, user_id))
        session['fav_resort'] = resort_id

    db.commit()
    return redirect(request.referrer or url_for('home'))

#
# ──────────── PRICE COMPARISON ────────────
#
@app.route('/price_comparison', methods=['GET'])
def price_comparison():
    q = request.args.get('query', '').strip()
    page, offset = get_pagination_params()

    cnt = db.cursor()
    if q:
        like = f"%{q}%"
        cnt.execute("""
            SELECT COUNT(DISTINCT r.resort_name)
            FROM Resort r
            JOIN Hotel h ON h.resort_id = r.resort_id
            JOIN Airbnb a ON a.resort_id = r.resort_id
            WHERE CAST(r.resort_id AS CHAR) LIKE %s
               OR r.resort_name LIKE %s
               OR r.location   LIKE %s;
        """, (like, like, like))
    else:
        cnt.execute("""
            SELECT COUNT(DISTINCT r.resort_name)
            FROM Resort r
            JOIN Hotel h ON h.resort_id = r.resort_id
            JOIN Airbnb a ON a.resort_id = r.resort_id;
        """)
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    if q:
        like = f"%{q}%"
        cur.execute("""
            SELECT r.resort_id,
                   r.resort_name,
                   AVG(h.price) AS h_avg,
                   AVG(a.price) AS a_avg
            FROM Resort r
            JOIN Hotel h ON h.resort_id = r.resort_id
            JOIN Airbnb a ON a.resort_id = r.resort_id
            WHERE CAST(r.resort_id AS CHAR) LIKE %s
               OR r.resort_name LIKE %s
               OR r.location   LIKE %s
            GROUP BY r.resort_id, r.resort_name
            ORDER BY h_avg, a_avg
            LIMIT %s OFFSET %s;
        """, (like, like, like, PER_PAGE, offset))
    else:
        cur.execute("""
            SELECT r.resort_id,
                   r.resort_name,
                   AVG(h.price) AS h_avg,
                   AVG(a.price) AS a_avg
            FROM Resort r
            JOIN Hotel h ON h.resort_id = r.resort_id
            JOIN Airbnb a ON a.resort_id = r.resort_id
            GROUP BY r.resort_id, r.resort_name
            ORDER BY h_avg, a_avg
            LIMIT %s OFFSET %s;
        """, (PER_PAGE, offset))
    prices = cur.fetchall()

    return render_template(
        'price_comparison.html',
        prices=prices,
        query=q,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_resort=session.get('fav_resort'),
        view='resorts'
    )

#
# ──────────── POPULAR RESORTS ────────────
#
@app.route('/popular_resorts', methods=['GET'])
def popular_resorts():
    q = request.args.get('query', '').strip()
    page, offset = get_pagination_params()

    cnt = db.cursor()
    if q:
        like = f"%{q}%"
        cnt.execute("""
            SELECT COUNT(DISTINCT r.resort_id)
            FROM Resort r
            LEFT JOIN User u ON u.fav_resort = r.resort_id
            WHERE CAST(r.resort_id AS CHAR) LIKE %s
               OR r.resort_name LIKE %s
               OR r.location   LIKE %s;
        """, (like, like, like))
    else:
        cnt.execute("""
            SELECT COUNT(DISTINCT r.resort_id)
            FROM Resort r
            LEFT JOIN User u ON u.fav_resort = r.resort_id;
        """)
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    if q:
        like = f"%{q}%"
        cur.execute("""
            SELECT r.resort_id,
                   r.resort_name,
                   r.location,
                   COUNT(u.user_id) AS total
            FROM Resort r
            LEFT JOIN User u ON u.fav_resort = r.resort_id
            WHERE CAST(r.resort_id AS CHAR) LIKE %s
               OR r.resort_name LIKE %s
               OR r.location   LIKE %s
            GROUP BY r.resort_id, r.resort_name, r.location
            ORDER BY total DESC, r.resort_name
            LIMIT %s OFFSET %s;
        """, (like, like, like, PER_PAGE, offset))
    else:
        cur.execute("""
            SELECT r.resort_id,
                   r.resort_name,
                   r.location,
                   COUNT(u.user_id) AS total
            FROM Resort r
            LEFT JOIN User u ON u.fav_resort = r.resort_id
            GROUP BY r.resort_id, r.resort_name, r.location
            ORDER BY total DESC, r.resort_name
            LIMIT %s OFFSET %s;
        """, (PER_PAGE, offset))
    popular = cur.fetchall()

    return render_template(
        'popular_resorts.html',
        popular=popular,
        query=q,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_resort=session.get('fav_resort'),
        view='resorts'
    )

#
# ──────────── SEARCH RESORTS ────────────
#
@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('query','').strip()
    if not q:
        return redirect(url_for('home'))

    page, offset = get_pagination_params()
    like = f"%{q}%"

    cnt = db.cursor()
    cnt.execute("""
        SELECT COUNT(*) FROM Resort
        WHERE CAST(resort_id AS CHAR) LIKE %s
           OR resort_name LIKE %s
           OR location   LIKE %s;
    """, (like, like, like))
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT resort_id,
               resort_name,
               location,
               highest_point,
               lowest_point,
               difficult_slope,
               total_slope,
               total_lifts
        FROM Resort
        WHERE CAST(resort_id AS CHAR) LIKE %s
           OR resort_name LIKE %s
           OR location   LIKE %s
        ORDER BY resort_id
        LIMIT %s OFFSET %s;
    """, (like, like, like, PER_PAGE, offset))
    resorts = cur.fetchall()

    return render_template(
        'search_results.html',
        resorts=resorts,
        query=q,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_resort=session.get('fav_resort'),
        view='resorts'
    )


#
# ──────────── HOTEL LISTING & FAVORITE ────────────
#
@app.route('/hotels', methods=['GET'])
def hotels():
    q = request.args.get('query','').strip()
    page, offset = get_pagination_params()

    # count
    cnt = db.cursor()
    if q:
        like = f"%{q}%"
        cnt.execute("""
          SELECT COUNT(*) FROM Hotel
          WHERE CAST(hotel_id AS CHAR) LIKE %s
             OR CAST(resort_id AS CHAR) LIKE %s
             OR room_type LIKE %s;
        """, (like, like, like))
    else:
        cnt.execute("SELECT COUNT(*) FROM Hotel;")
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    if q:
        like = f"%{q}%"
        cur.execute("""
          SELECT hotel_id, resort_id, price, room_type, distance
          FROM Hotel
          WHERE CAST(hotel_id AS CHAR) LIKE %s
             OR CAST(resort_id AS CHAR) LIKE %s
             OR room_type LIKE %s
          ORDER BY hotel_id
          LIMIT %s OFFSET %s;
        """, (like, like, like, PER_PAGE, offset))
    else:
        cur.execute("""
          SELECT hotel_id, resort_id, price, room_type, distance
          FROM Hotel
          ORDER BY hotel_id
          LIMIT %s OFFSET %s;
        """, (PER_PAGE, offset))
    hotels = cur.fetchall()

    return render_template(
        'hotels.html',
        hotels=hotels,
        query=q,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_hotel=session.get('fav_hotel'),
        view='hotels'
    )

@app.route('/toggle_favorite_hotel/<int:hotel_id>', methods=['POST'])
def toggle_favorite_hotel(hotel_id):
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))
    user_id = session['user_id']
    cur = db.cursor()
    cur.execute("SELECT fav_hotel FROM User WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    current = row[0] if row else None

    if current == hotel_id:
        cur.execute("UPDATE User SET fav_hotel = NULL WHERE user_id = %s", (user_id,))
        session['fav_hotel'] = None
    else:
        cur.execute("UPDATE User SET fav_hotel = %s WHERE user_id = %s", (hotel_id, user_id))
        session['fav_hotel'] = hotel_id

    db.commit()
    return redirect(request.referrer or url_for('hotels'))

#
# ──────────── AIRBNB LISTING & FAVORITE ────────────
#
@app.route('/airbnb')
def airbnb_list():
    q = request.args.get('query','').strip()
    page, offset = get_pagination_params()

    cnt = db.cursor()
    if q:
        like = f"%{q}%"
        cnt.execute("""
          SELECT COUNT(*) FROM Airbnb
          WHERE CAST(airbnb_id AS CHAR) LIKE %s
             OR CAST(resort_id AS CHAR) LIKE %s
             OR room_type LIKE %s;
        """, (like, like, like))
    else:
        cnt.execute("SELECT COUNT(*) FROM Airbnb;")
    total = cnt.fetchone()[0]
    total_pages = math.ceil(total / PER_PAGE)

    cur = db.cursor(dictionary=True)
    if q:
        like = f"%{q}%"
        cur.execute("""
          SELECT airbnb_id, resort_id, price, room_type, distance
          FROM Airbnb
          WHERE CAST(airbnb_id AS CHAR) LIKE %s
             OR CAST(resort_id AS CHAR) LIKE %s
             OR room_type LIKE %s
          ORDER BY airbnb_id
          LIMIT %s OFFSET %s;
        """, (like, like, like, PER_PAGE, offset))
    else:
        cur.execute("""
          SELECT airbnb_id, resort_id, price, room_type, distance
          FROM Airbnb
          ORDER BY airbnb_id
          LIMIT %s OFFSET %s;
        """, (PER_PAGE, offset))
    airbnbs = cur.fetchall()

    return render_template(
        'airbnb.html',
        airbnbs=airbnbs,
        query=q,
        page=page,
        total_pages=total_pages,
        is_logged_in=('user_id' in session),
        user_name=session.get('user_name'),
        user_fav_airbnb=session.get('fav_airbnb'),
        view='airbnb'
    )

@app.route('/toggle_favorite_airbnb/<int:airbnb_id>', methods=['POST'])
def toggle_favorite_airbnb(airbnb_id):
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))
    user_id = session['user_id']
    cur = db.cursor()
    cur.execute("SELECT fav_airbnb FROM User WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    current = row[0] if row else None

    if current == airbnb_id:
        cur.execute("UPDATE User SET fav_airbnb = NULL WHERE user_id = %s", (user_id,))
        session['fav_airbnb'] = None
    else:
        cur.execute("UPDATE User SET fav_airbnb = %s WHERE user_id = %s", (airbnb_id, user_id))
        session['fav_airbnb'] = airbnb_id

    db.commit()
    return redirect(request.referrer or url_for('airbnb_list'))

#
# ──────────── SKIGROUP ENTRY ────────────
#
@app.route('/skigroup')
def skigroup():
    if 'user_id' not in session:
        return render_template('need_login.html')
    return redirect(url_for('skigroup_manage'))

#
# ──────────── CREATE & JOIN ────────────
#
@app.route('/skigroup/manage', methods=['GET','POST'])
def skigroup_manage():
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))

    user_id = session['user_id']
    msg_create = None
    err_create = None
    msg_join   = None
    err_join   = None

    # --- Handle CREATE form ---
    if request.method=='POST' and 'create_group_name' in request.form:
        name = request.form['create_group_name'].strip()
        if not name:
            err_create = "Group name cannot be empty."
        else:
            cur = db.cursor()
            # Only refuse if *this same user* already has a group with that name
            cur.execute(
                "SELECT 1 FROM skigroup WHERE creator_id=%s AND group_name=%s",
                (user_id, name)
            )
            if cur.fetchone():
                err_create = f"You already have a SkiGroup named “{name}.”"
            else:
                try:
                    # 1) insert new group
                    cur.execute(
                      "INSERT INTO skigroup (group_name, creator_id) VALUES (%s,%s)",
                      (name, user_id)
                    )
                    db.commit()
                    new_gid = cur.lastrowid

                    # 2) auto-join the creator
                    cur.execute(
                      "INSERT INTO user_skigroup (user_id, group_id) VALUES (%s,%s)",
                      (user_id, new_gid)
                    )
                    db.commit()

                    msg_create = f"SkiGroup “{name}” created (ID #{new_gid})."
                except mysql.connector.Error as e:
                    db.rollback()
                    err_create = f"Could not create group: {e.msg}"

    # --- Handle JOIN form ---
    if request.method=='POST' and 'join_group_id' in request.form:
        gid = request.form['join_group_id']
        if not gid:
            err_join = "Please select a group to join."
        else:
            cur = db.cursor()
            try:
                cur.execute(
                  "INSERT INTO user_skigroup (user_id, group_id) VALUES (%s,%s)",
                  (user_id, gid)
                )
                db.commit()
                msg_join = f"You have joined SkiGroup #{gid}."
            except mysql.connector.Error as e:
                db.rollback()
                err_join = f"Could not join group: {e.msg}"

    # --- Fetch groups available to join (not yet joined) ---
    cur = db.cursor(dictionary=True)
    cur.execute("""
      SELECT group_id, group_name
      FROM skigroup
      WHERE group_id NOT IN (
        SELECT group_id FROM user_skigroup WHERE user_id=%s
      )
    """, (user_id,))
    available = cur.fetchall()

    return render_template('skigroup_manage.html',
        user_name=session.get('user_name'),
        is_logged_in=('user_id' in session),
        view='skigroup',
        skiview='manage',
        available=available,
        msg_create=msg_create,
        err_create=err_create,
        msg_join=msg_join,
        err_join=err_join
    )

#
# ──────────── MY CREATED GROUPS ────────────
#
@app.route('/skigroup/created', methods=['GET','POST'])
def skigroup_created():
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))
    user_id = session['user_id']
    msg = err = None

    # Handle removals or full‐delete
    if request.method == 'POST':
        # delete a single member
        if 'remove_member_group' in request.form:
            gid = request.form['remove_member_group']
            mid = request.form['remove_member_user']
            try:
                cur = db.cursor()
                cur.execute(
                  "DELETE FROM user_skigroup WHERE user_id=%s AND group_id=%s",
                  (mid, gid)
                )
                db.commit()
                msg = f"Removed user #{mid} from group #{gid}."
            except mysql.connector.Error as e:
                db.rollback()
                err = "Could not remove member."
        # delete an entire group
        elif 'delete_group_id' in request.form:
            gid = request.form['delete_group_id']
            try:
                cur = db.cursor()
                # cascade‐delete user_skigroup by FK, then skigroup row
                cur.execute("DELETE FROM skigroup WHERE group_id=%s", (gid,))
                db.commit()
                msg = f"Deleted group #{gid}."
            except mysql.connector.Error:
                db.rollback()
                err = "Could not delete group."

    # 1) fetch all groups this user created
    cur = db.cursor(dictionary=True)
    cur.execute("""
      SELECT group_id, group_name, creation_date
      FROM skigroup
      WHERE creator_id=%s
      ORDER BY creation_date DESC
    """, (user_id,))
    groups = cur.fetchall()

    # 2) fetch members + their favorites for each group
    members_by_group = {}
    for g in groups:
        cur.execute("""
          SELECT
            u.user_id,
            u.user_name,
            u.fav_resort,
            u.fav_hotel,
            u.fav_airbnb
          FROM user_skigroup us
          JOIN user u ON u.user_id = us.user_id
          WHERE us.group_id=%s
        """, (g['group_id'],))
        members_by_group[g['group_id']] = cur.fetchall()

    return render_template(
      'skigroup_created.html',
      user_name=session.get('user_name'),
      is_logged_in=True,
      view='skigroup',
      skiview='created',
      groups=groups,
      members_by_group=members_by_group,
      msg=msg,
      err=err
    )


#
# ──────────── MY JOINED GROUPS ────────────
#
@app.route('/skigroup/joined', methods=['GET','POST'])
def skigroup_joined():
    if 'user_id' not in session:
        return redirect(url_for('sign_in'))
    user_id = session['user_id']
    msg = err = None

    # handle “leave group”
    if request.method=='POST' and 'leave_group_id' in request.form:
        gid = request.form['leave_group_id']
        try:
            cur = db.cursor()
            cur.execute(
              "DELETE FROM user_skigroup WHERE user_id=%s AND group_id=%s",
              (user_id, gid)
            )
            db.commit()
            msg = f"You left SkiGroup #{gid}."
        except mysql.connector.Error:
            db.rollback()
            err = "Could not leave group."

    # fetch groups user belongs to but didn’t create
    cur = db.cursor(dictionary=True)
    cur.execute("""
      SELECT
        s.group_id,
        s.group_name,
        s.creator_id,
        u.user_name AS creator_name
      FROM user_skigroup us
      JOIN skigroup s ON s.group_id = us.group_id
      JOIN user u ON u.user_id = s.creator_id
      WHERE us.user_id=%s
        AND s.creator_id<>%s
      ORDER BY s.creation_date DESC
    """, (user_id, user_id))
    joined = cur.fetchall()

    # 2) fetch members + their favorites for each joined group
    members_by_group = {}
    for g in joined:
        cur.execute("""
          SELECT
            u.user_id,
            u.user_name,
            u.fav_resort,
            u.fav_hotel,
            u.fav_airbnb
          FROM user_skigroup us
          JOIN user u ON u.user_id = us.user_id
          WHERE us.group_id=%s
        """, (g['group_id'],))
        members_by_group[g['group_id']] = cur.fetchall()

    return render_template(
      'skigroup_joined.html',
      user_name=session.get('user_name'),
      is_logged_in=True,
      view='skigroup',
      skiview='joined',
      joined=joined,
      members_by_group=members_by_group,
      msg=msg,
      err=err
    )

#
# ──────────── SIGN IN / SIGN UP / LOGOUT ────────────
#

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    error = None
    if request.method == 'POST':
        uname = request.form['user_name']
        pwd = request.form['password']
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT user_id, user_name, password,
                   fav_resort, fav_hotel, fav_airbnb
            FROM User
            WHERE user_name=%s
        """, (uname,))
        user = cur.fetchone()

        if not user or user['password'] != pwd:
            error = 'Invalid username or password.'
        else:
            session['user_id'] = user['user_id']
            session['user_name'] = user['user_name']
            session['fav_resort']  = user['fav_resort']
            session['fav_hotel']   = user['fav_hotel']
            session['fav_airbnb']  = user['fav_airbnb']
            return redirect(url_for('dashboard'))
    return render_template('sign_in.html', error=error)

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    error = None
    if request.method == 'POST':
        cur = db.cursor()
        try:
            # begin transaction
            # cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;")
            cur.execute("START TRANSACTION;")
            # next user_id
            cur.execute("SELECT MAX(user_id) FROM User;")
            new_id = (cur.fetchone()[0] or 0) + 1
            uname = request.form['user_name']
            pwd = request.form['password']
            conf = request.form['confirm_password']
            if pwd != conf:
                error = 'Passwords do not match.'
                cur.execute("ROLLBACK;")
                return render_template('sign_up.html', error=error)
            # uniqueness check
            cur.execute("SELECT 1 FROM User WHERE user_name=%s", (uname,))
            if cur.fetchone():
                error = 'Username already taken.'
                cur.execute("ROLLBACK;")
                return render_template('sign_up.html', error=error)
            # insert
            cur.execute("""
                INSERT INTO User
                  (user_id, user_name, password, fav_resort, fav_hotel, fav_airbnb)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (new_id, uname, pwd, None, None, None))
            # commit
            cur.execute("COMMIT;")
            return redirect(url_for('sign_in'))
        except Exception as e:
            cur.execute("ROLLBACK;")
            error = f"Registration failed: {e}"
    return render_template('sign_up.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(port=4000)
