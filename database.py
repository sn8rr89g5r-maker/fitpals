import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fitpals.db")

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    c = db.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        city TEXT DEFAULT 'Dhaka',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS gyms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        city TEXT DEFAULT 'Dhaka',
        rating REAL DEFAULT 4.5,
        review_count INTEGER DEFAULT 0,
        hours TEXT DEFAULT '6am-10pm',
        is_open INTEGER DEFAULT 1,
        emoji TEXT DEFAULT '🏟️',
        amenities TEXT DEFAULT '',
        description TEXT DEFAULT '',
        phone TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS membership_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gym_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        duration_days INTEGER NOT NULL,
        description TEXT DEFAULT '',
        FOREIGN KEY(gym_id) REFERENCES gyms(id)
    );
    CREATE TABLE IF NOT EXISTS memberships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        gym_id INTEGER NOT NULL,
        payment_method TEXT DEFAULT 'bkash',
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(plan_id) REFERENCES membership_plans(id)
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL,
        category TEXT NOT NULL,
        price INTEGER NOT NULL,
        weight TEXT DEFAULT '',
        servings TEXT DEFAULT '',
        emoji TEXT DEFAULT '🥤',
        description TEXT DEFAULT '',
        stock INTEGER DEFAULT 50
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total INTEGER NOT NULL,
        payment_method TEXT DEFAULT 'bkash',
        delivery_address TEXT DEFAULT '',
        status TEXT DEFAULT 'confirmed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        price INTEGER NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        gym_id INTEGER NOT NULL,
        rating INTEGER DEFAULT 5,
        body TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(gym_id) REFERENCES gyms(id)
    );
    CREATE TABLE IF NOT EXISTS snaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        caption TEXT NOT NULL,
        image_filename TEXT DEFAULT NULL,
        snap_type TEXT DEFAULT 'general',
        pr_weight TEXT DEFAULT NULL,
        pr_exercise TEXT DEFAULT NULL,
        like_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS snap_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        snap_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, snap_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(snap_id) REFERENCES snaps(id)
    );
    CREATE TABLE IF NOT EXISTS snap_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        snap_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(snap_id) REFERENCES snaps(id)
    );
    """)

    # ── Seed gyms ──
    if c.execute("SELECT COUNT(*) FROM gyms").fetchone()[0] == 0:
        gyms = [
            ("Iron Zone Fitness",  "Amberkhana, Sylhet",  "Sylhet",     4.8, 312, "24 Hours", 1, "🏟️", "Full Equipment,AC,Parking,Personal Trainer", "Sylhet's most complete gym with state-of-the-art equipment.", "01711-000001"),
            ("ProFit Center",      "Zindabazar, Sylhet",  "Sylhet",     4.6, 208, "6am-10pm", 1, "💪", "Pool,Sauna,Group Classes,AC",                "Premium gym with pool and sauna facilities.",                "01711-000002"),
            ("CrossFit Sylhet",    "Tilagor, Sylhet",     "Sylhet",     4.5, 176, "5am-9pm",  1, "🥊", "CrossFit,Daily Classes,Outdoor Area",        "High-intensity training with certified coaches.",            "01711-000003"),
            ("Zenfit Studio",      "Subhanighat, Sylhet", "Sylhet",     4.7, 94,  "7am-8pm",  1, "🧘", "Yoga,Pilates,Women Friendly,AC",             "Yoga and pilates studio for mind-body wellness.",            "01711-000004"),
            ("Dhaka Muscle Club",  "Gulshan-2, Dhaka",   "Dhaka",      4.9, 520, "24 Hours", 1, "🏋️", "Full Equipment,Protein Bar,Locker,AC",       "Dhaka's flagship strength training center.",                 "01711-000005"),
            ("FitLife Gym",        "Dhanmondi, Dhaka",   "Dhaka",      4.4, 310, "6am-11pm", 1, "⚡", "Cardio,Weights,Spinning,Steam Room",         "Modern gym for all fitness levels.",                         "01711-000006"),
            ("PowerHouse CTG",     "GEC Circle, Ctg",    "Chittagong", 4.6, 280, "5am-10pm", 1, "🦁", "Full Equipment,Boxing,Cardio,AC",            "Chittagong's top powerlifting and boxing gym.",              "01711-000007"),
            ("BodyCraft Fitness",  "Nasirabad, Ctg",     "Chittagong", 4.3, 190, "6am-9pm",  1, "🔥", "Weights,Cardio,Group Classes",               "Affordable quality fitness for everyone.",                   "01711-000008"),
        ]
        c.executemany("""
            INSERT INTO gyms (name,address,city,rating,review_count,hours,is_open,emoji,amenities,description,phone)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, gyms)

        plans = [
            (1,"Day Pass",60,1,"Single visit access"),
            (1,"Weekly Pass",250,7,"7 days unlimited access"),
            (1,"Monthly Pass",800,30,"30 days unlimited access"),
            (1,"3-Month Pass",2100,90,"Best value - 3 months unlimited"),
            (2,"Day Pass",80,1,"Single visit with pool access"),
            (2,"Weekly Pass",320,7,"7 days full access + pool"),
            (2,"Monthly Pass",1200,30,"30 days full access + pool + sauna"),
            (3,"Day Pass",70,1,"Single CrossFit class"),
            (3,"Monthly Pass",900,30,"Unlimited classes for 30 days"),
            (4,"Day Pass",60,1,"Single yoga/pilates session"),
            (4,"Monthly Pass",700,30,"Unlimited sessions for 30 days"),
            (5,"Day Pass",100,1,"Single visit - premium center"),
            (5,"Monthly Pass",1500,30,"Full access to Dhaka Muscle Club"),
            (6,"Monthly Pass",1000,30,"Unlimited access FitLife"),
            (7,"Monthly Pass",1100,30,"Full PowerHouse access"),
            (8,"Monthly Pass",800,30,"BodyCraft unlimited monthly"),
        ]
        c.executemany("""
            INSERT INTO membership_plans (gym_id,name,price,duration_days,description)
            VALUES (?,?,?,?,?)
        """, plans)

    # ── Seed products ──
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        products = [
            ("Gold Standard Whey",      "Optimum Nutrition","Protein",    4800,"2.27 kg","73 servings","🥛","The world's best-selling whey protein. 24g protein per serving."),
            ("Impact Whey Protein",     "Myprotein",        "Protein",    2600,"1 kg",   "40 servings","🍫","High quality whey protein at an unbeatable price."),
            ("Serious Mass Gainer",     "Optimum Nutrition","Mass Gainer",3200,"2.7 kg", "16 servings","🍌","1250 calories per serving for serious muscle gain."),
            ("True Mass 1200",          "BSN",              "Mass Gainer",3800,"2.64 kg","11 servings","💪","Advanced mass gainer with complex carbs."),
            ("C4 Original Pre-Workout", "Cellucor",         "Pre-Workout",2200,"195g",   "30 servings","⚡","Explosive energy and focus for intense workouts."),
            ("Pre-Kaged Elite",         "Kaged",            "Pre-Workout",3500,"312g",   "20 servings","🔥","Premium pre-workout with patented ingredients."),
            ("Creatine Monohydrate",    "Muscletech",       "Creatine",   1400,"400g",   "80 servings","💊","Pure creatine monohydrate for strength and power."),
            ("Micronized Creatine",     "Optimum Nutrition","Creatine",   1600,"300g",   "60 servings","🔬","Micronized for faster absorption."),
            ("BCAA 5000 Powder",        "Optimum Nutrition","BCAA",       1800,"380g",   "75 servings","🟡","Essential amino acids for muscle recovery."),
            ("BCAA Energy",             "EVL Nutrition",    "BCAA",       2000,"270g",   "30 servings","🌊","BCAAs with natural caffeine for energy."),
            ("Omega-3 Fish Oil",        "NOW Sports",       "Vitamins",   900, "500 caps","500 days",  "🐟","High potency omega-3 for heart and joint health."),
            ("Zinc + Magnesium ZMA",    "Optimum Nutrition","Vitamins",   1100,"180 caps","90 days",   "🔵","ZMA formula for recovery and sleep quality."),
            ("Lifting Gloves",          "Harbinger",        "Gear",       850, "One Size","N/A",        "🧤","Full palm padding for heavy lifting."),
            ("Resistance Bands Set",    "FitPals BD",       "Gear",       1200,"5 bands", "N/A",        "🎽","5 resistance levels for home and gym training."),
            ("Shaker Bottle 700ml",     "BlenderBottle",    "Gear",       450, "700ml",   "N/A",        "🥤","Leak-proof shaker with mixing ball."),
        ]
        c.executemany("""
            INSERT INTO products (name,brand,category,price,weight,servings,emoji,description)
            VALUES (?,?,?,?,?,?,?,?)
        """, products)

    # ── Seed demo snaps ──
    if c.execute("SELECT COUNT(*) FROM snaps").fetchone()[0] == 0:
        c.execute("INSERT OR IGNORE INTO users (name,email,password,city) VALUES ('Rafiq H.','rafiq@demo.com','demo123','Sylhet')")
        c.execute("INSERT OR IGNORE INTO users (name,email,password,city) VALUES ('Sadia N.','sadia@demo.com','demo123','Dhaka')")
        c.execute("INSERT OR IGNORE INTO users (name,email,password,city) VALUES ('Tamim M.','tamim@demo.com','demo123','Chittagong')")
        u1 = c.execute("SELECT id FROM users WHERE email='rafiq@demo.com'").fetchone()[0]
        u2 = c.execute("SELECT id FROM users WHERE email='sadia@demo.com'").fetchone()[0]
        u3 = c.execute("SELECT id FROM users WHERE email='tamim@demo.com'").fetchone()[0]
        snaps = [
            (u1,"New PR on deadlift! 180kg — 6 months of hard work paid off! Never give up 🔥","pr","180kg","Deadlift"),
            (u2,"Post-workout selfie 💪 Consistency is key. Day 47 done!","general",None,None),
            (u3,"Hit 100kg bench press for the first time!! CrossFit Sylhet forever 🏋️","pr","100kg","Bench Press"),
            (u1,"Morning session done. 5am grind hits different. Who else trains early? ✅","general",None,None),
            (u2,"Squat PR — 120kg! Legs are shaking but the smile says it all 😄","pr","120kg","Squat"),
            (u3,"Rest day but still came for cardio. The gym is home fr 🏠","general",None,None),
        ]
        c.executemany("INSERT INTO snaps (user_id,caption,snap_type,pr_weight,pr_exercise) VALUES (?,?,?,?,?)", snaps)
        for row in c.execute("SELECT id FROM snaps").fetchall():
            c.execute("INSERT OR IGNORE INTO snap_likes (user_id,snap_id) VALUES (?,?)",(u1,row[0]))
            c.execute("UPDATE snaps SET like_count=like_count+1 WHERE id=?",(row[0],))

    db.commit()
    db.close()
