from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import init_db, get_db
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fitpals-secret-2025")

with app.app_context():
    init_db()

# ─────────────────────────────────────────
#  HOME
# ─────────────────────────────────────────
@app.route("/")
def index():
    db = get_db()
    gyms = db.execute("SELECT * FROM gyms LIMIT 3").fetchall()
    products = db.execute("SELECT * FROM products LIMIT 4").fetchall()
    db.close()
    return render_template("index.html", gyms=gyms, products=products)

# ─────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name  = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]
        city  = request.form.get("city", "Dhaka")
        db    = get_db()
        if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            flash("Email already registered.", "error")
            db.close()
            return redirect(url_for("register"))
        db.execute("INSERT INTO users (name, email, password, city) VALUES (?,?,?,?)",
                   (name, email, pw, city))
        db.commit()
        db.close()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]
        db    = get_db()
        user  = db.execute("SELECT * FROM users WHERE email=? AND password=?",
                           (email, pw)).fetchone()
        db.close()
        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─────────────────────────────────────────
#  GYMS
# ─────────────────────────────────────────
@app.route("/gyms")
def gyms():
    db     = get_db()
    search = request.args.get("q", "").strip()
    city   = request.args.get("city", "")
    filt   = request.args.get("filter", "all")
    query  = "SELECT * FROM gyms WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR address LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if city:
        query += " AND city=?"
        params.append(city)
    if filt == "open":
        query += " AND is_open=1"
    elif filt == "rated":
        query += " ORDER BY rating DESC"
    gym_list = db.execute(query, params).fetchall()
    cities   = [r["city"] for r in db.execute("SELECT DISTINCT city FROM gyms").fetchall()]
    db.close()
    return render_template("gyms.html", gyms=gym_list, cities=cities,
                           search=search, city=city, filt=filt)

@app.route("/gyms/<int:gym_id>")
def gym_detail(gym_id):
    db  = get_db()
    gym = db.execute("SELECT * FROM gyms WHERE id=?", (gym_id,)).fetchone()
    if not gym:
        db.close()
        flash("Gym not found.", "error")
        return redirect(url_for("gyms"))
    plans = db.execute("SELECT * FROM membership_plans WHERE gym_id=?", (gym_id,)).fetchall()
    reviews = db.execute("""
        SELECT r.*, u.name as user_name FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.gym_id=? ORDER BY r.created_at DESC LIMIT 10
    """, (gym_id,)).fetchall()
    db.close()
    return render_template("gym_detail.html", gym=gym, plans=plans, reviews=reviews)

# ─────────────────────────────────────────
#  MEMBERSHIPS
# ─────────────────────────────────────────
@app.route("/purchase/<int:plan_id>", methods=["GET", "POST"])
def purchase(plan_id):
    if "user_id" not in session:
        flash("Please log in to purchase a membership.", "error")
        return redirect(url_for("login"))
    db   = get_db()
    plan = db.execute("""
        SELECT p.*, g.name as gym_name, g.id as gym_id
        FROM membership_plans p JOIN gyms g ON p.gym_id = g.id
        WHERE p.id=?
    """, (plan_id,)).fetchone()
    if not plan:
        db.close()
        return redirect(url_for("gyms"))
    if request.method == "POST":
        method = request.form.get("payment_method", "bkash")
        db.execute("""
            INSERT INTO memberships (user_id, plan_id, gym_id, payment_method, status)
            VALUES (?,?,?,?,'active')
        """, (session["user_id"], plan_id, plan["gym_id"], method))
        db.commit()
        db.close()
        flash(f"Membership purchased! Payment via {method.upper()} confirmed.", "success")
        return redirect(url_for("dashboard"))
    db.close()
    return render_template("purchase.html", plan=plan)

# ─────────────────────────────────────────
#  STORE
# ─────────────────────────────────────────
@app.route("/store")
def store():
    db       = get_db()
    category = request.args.get("cat", "all")
    search   = request.args.get("q", "")
    query    = "SELECT * FROM products WHERE 1=1"
    params   = []
    if category != "all":
        query += " AND category=?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR brand LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    products   = db.execute(query, params).fetchall()
    categories = [r["category"] for r in
                  db.execute("SELECT DISTINCT category FROM products").fetchall()]
    db.close()
    cart_count = sum(session.get("cart", {}).values())
    return render_template("store.html", products=products, categories=categories,
                           current_cat=category, search=search, cart_count=cart_count)

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    cart = session.get("cart", {})
    key  = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "count": sum(cart.values())})

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    key  = str(product_id)
    if key in cart:
        cart[key] -= 1
        if cart[key] <= 0:
            del cart[key]
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "count": sum(cart.values())})

@app.route("/cart")
def cart():
    db    = get_db()
    cart  = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = db.execute("SELECT * FROM products WHERE id=?", (int(pid),)).fetchone()
        if p:
            subtotal = p["price"] * qty
            total   += subtotal
            items.append({"product": p, "qty": qty, "subtotal": subtotal})
    db.close()
    return render_template("cart.html", items=items, total=total)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        flash("Please log in to checkout.", "error")
        return redirect(url_for("login"))
    db   = get_db()
    cart = session.get("cart", {})
    if not cart:
        db.close()
        return redirect(url_for("store"))
    total = 0
    for pid, qty in cart.items():
        p = db.execute("SELECT price FROM products WHERE id=?", (int(pid),)).fetchone()
        if p:
            total += p["price"] * qty
    if request.method == "POST":
        method  = request.form.get("payment_method", "bkash")
        address = request.form.get("address", "").strip()
        order   = db.execute("""
            INSERT INTO orders (user_id, total, payment_method, delivery_address, status)
            VALUES (?,?,?,?,'confirmed')
        """, (session["user_id"], total, method, address))
        order_id = order.lastrowid
        for pid, qty in cart.items():
            p = db.execute("SELECT price FROM products WHERE id=?", (int(pid),)).fetchone()
            if p:
                db.execute("INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?,?,?,?)",
                           (order_id, int(pid), qty, p["price"]))
        db.commit()
        db.close()
        session.pop("cart", None)
        flash(f"Order confirmed! Payment via {method.upper()}. Delivery in 24-48 hrs.", "success")
        return redirect(url_for("dashboard"))
    db.close()
    return render_template("checkout.html", total=total, cart_count=sum(cart.values()))

# ─────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db  = get_db()
    uid = session["user_id"]
    memberships = db.execute("""
        SELECT m.*, g.name as gym_name, p.name as plan_name, p.duration_days
        FROM memberships m
        JOIN gyms g ON m.gym_id = g.id
        JOIN membership_plans p ON m.plan_id = p.id
        WHERE m.user_id=? ORDER BY m.created_at DESC
    """, (uid,)).fetchall()
    orders = db.execute("""
        SELECT o.*, GROUP_CONCAT(pr.name, ', ') as product_names
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products pr ON oi.product_id = pr.id
        WHERE o.user_id=? GROUP BY o.id ORDER BY o.created_at DESC
    """, (uid,)).fetchall()
    db.close()
    return render_template("dashboard.html", memberships=memberships, orders=orders)

# ─────────────────────────────────────────
#  REVIEWS
# ─────────────────────────────────────────
@app.route("/review/<int:gym_id>", methods=["POST"])
def add_review(gym_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    db     = get_db()
    rating = int(request.form.get("rating", 5))
    body   = request.form.get("body", "").strip()
    if body:
        db.execute("INSERT INTO reviews (user_id, gym_id, rating, body) VALUES (?,?,?,?)",
                   (session["user_id"], gym_id, rating, body))
        db.commit()
    db.close()
    return redirect(url_for("gym_detail", gym_id=gym_id))

# ─────────────────────────────────────────
#  SNAPS
# ─────────────────────────────────────────
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/snaps")
def snaps():
    db   = get_db()
    filt = request.args.get("filter", "all")
    query = """
        SELECT s.*, u.name as user_name, u.city as user_city
        FROM snaps s JOIN users u ON s.user_id = u.id
    """
    if filt == "pr":
        query += " WHERE s.snap_type = 'pr'"
    query += " ORDER BY s.created_at DESC LIMIT 50"
    feed = db.execute(query).fetchall()
    liked = set()
    if "user_id" in session:
        rows  = db.execute("SELECT snap_id FROM snap_likes WHERE user_id=?",
                           (session["user_id"],)).fetchall()
        liked = {r["snap_id"] for r in rows}
    counts = {r["snap_id"]: r["cnt"] for r in
              db.execute("SELECT snap_id, COUNT(*) as cnt FROM snap_comments GROUP BY snap_id").fetchall()}
    db.close()
    return render_template("snaps.html", feed=feed, liked=liked,
                           comment_counts=counts, filt=filt)

@app.route("/snaps/post", methods=["GET", "POST"])
def post_snap():
    if "user_id" not in session:
        flash("Please log in to post a snap.", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        caption     = request.form.get("caption", "").strip()
        snap_type   = request.form.get("snap_type", "general")
        pr_weight   = request.form.get("pr_weight", "").strip() or None
        pr_exercise = request.form.get("pr_exercise", "").strip() or None
        image_filename = None
        if not caption:
            flash("Caption cannot be empty.", "error")
            return redirect(url_for("post_snap"))
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_filename = filename
        db = get_db()
        db.execute("""
            INSERT INTO snaps (user_id, caption, image_filename, snap_type, pr_weight, pr_exercise)
            VALUES (?,?,?,?,?,?)
        """, (session["user_id"], caption, image_filename, snap_type, pr_weight, pr_exercise))
        db.commit()
        db.close()
        flash("Snap posted! 🔥", "success")
        return redirect(url_for("snaps"))
    return render_template("post_snap.html")

@app.route("/snaps/<int:snap_id>")
def snap_detail(snap_id):
    db   = get_db()
    snap = db.execute("""
        SELECT s.*, u.name as user_name, u.city as user_city
        FROM snaps s JOIN users u ON s.user_id = u.id
        WHERE s.id=?
    """, (snap_id,)).fetchone()
    if not snap:
        db.close()
        return redirect(url_for("snaps"))
    comments = db.execute("""
        SELECT c.*, u.name as user_name FROM snap_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.snap_id=? ORDER BY c.created_at ASC
    """, (snap_id,)).fetchall()
    liked = False
    if "user_id" in session:
        liked = bool(db.execute("SELECT 1 FROM snap_likes WHERE user_id=? AND snap_id=?",
                                (session["user_id"], snap_id)).fetchone())
    db.close()
    return render_template("snap_detail.html", snap=snap, comments=comments, liked=liked)

@app.route("/snaps/<int:snap_id>/like", methods=["POST"])
def like_snap(snap_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401
    db  = get_db()
    uid = session["user_id"]
    existing = db.execute("SELECT 1 FROM snap_likes WHERE user_id=? AND snap_id=?",
                          (uid, snap_id)).fetchone()
    if existing:
        db.execute("DELETE FROM snap_likes WHERE user_id=? AND snap_id=?", (uid, snap_id))
        db.execute("UPDATE snaps SET like_count = MAX(0, like_count - 1) WHERE id=?", (snap_id,))
        liked = False
    else:
        db.execute("INSERT INTO snap_likes (user_id, snap_id) VALUES (?,?)", (uid, snap_id))
        db.execute("UPDATE snaps SET like_count = like_count + 1 WHERE id=?", (snap_id,))
        liked = True
    db.commit()
    count = db.execute("SELECT like_count FROM snaps WHERE id=?", (snap_id,)).fetchone()["like_count"]
    db.close()
    return jsonify({"liked": liked, "count": count})

@app.route("/snaps/<int:snap_id>/comment", methods=["POST"])
def comment_snap(snap_id):
    if "user_id" not in session:
        flash("Please log in to comment.", "error")
        return redirect(url_for("login"))
    body = request.form.get("body", "").strip()
    if body:
        db = get_db()
        db.execute("INSERT INTO snap_comments (user_id, snap_id, body) VALUES (?,?,?)",
                   (session["user_id"], snap_id, body))
        db.commit()
        db.close()
    return redirect(url_for("snap_detail", snap_id=snap_id))

@app.route("/snaps/<int:snap_id>/delete", methods=["POST"])
def delete_snap(snap_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db   = get_db()
    snap = db.execute("SELECT user_id FROM snaps WHERE id=?", (snap_id,)).fetchone()
    if snap and snap["user_id"] == session["user_id"]:
        db.execute("DELETE FROM snap_likes WHERE snap_id=?", (snap_id,))
        db.execute("DELETE FROM snap_comments WHERE snap_id=?", (snap_id,))
        db.execute("DELETE FROM snaps WHERE id=?", (snap_id,))
        db.commit()
        flash("Snap deleted.", "success")
    db.close()
    return redirect(url_for("snaps"))

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
