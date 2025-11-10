from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["MONGO_URI"] = "mongodb://localhost:27017/pgsystem"
mongo = PyMongo(app)

# ---------------- Initialize 100 rooms if not exist ----------------
if mongo.db.rooms.count_documents({}) == 0:
    for i in range(1, 101):
        mongo.db.rooms.insert_one({
            "room_id": i,
            "name": f"Room {i}",
            "price": 3000 + (i * 10),
            "rating": (i % 5) + 1,
            "image": f"{(i % 8) + 1}.jpeg",
            "booked": False,
            "booked_by": None,
            "booked_at": None,
            "booking_date": None
        })

# ---------------- Register / Login / Logout ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("⚠️ Fill all fields!", "danger")
            return redirect(url_for("register"))
        if mongo.db.users.find_one({"username": username}):
            flash("⚠️ Username already exists!", "danger")
            return redirect(url_for("register"))
        mongo.db.users.insert_one({"username": username, "password": password})
        flash("✅ Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("⚠️ Fill all fields!", "danger")
            return redirect(url_for("login"))
        user = mongo.db.users.find_one({"username": username})
        if user and user["password"] == password:
            session["user"] = username
            flash("✅ Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("❌ Invalid username or password", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("👋 Logged out successfully.", "info")
    return redirect(url_for("login"))

# ---------------- Profile ----------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        flash("⚠️ Please login first.", "danger")
        return redirect(url_for("login"))

    user = mongo.db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        new_name = request.form.get("name")
        new_mobile = request.form.get("mobile")
        new_email = request.form.get("email")

        mongo.db.users.update_one(
            {"username": session["user"]},
            {"$set": {
                "name": new_name,
                "mobile": new_mobile,
                "email": new_email
            }}
        )
        flash("✅ Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

# ---------------- Dashboard ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("⚠️ Please login first.", "danger")
        return redirect(url_for("login"))

    total_rooms = mongo.db.rooms.count_documents({})
    booked_rooms = mongo.db.rooms.count_documents({"booked": True})
    available_rooms = total_rooms - booked_rooms
    total_profit = sum([room["price"] for room in mongo.db.rooms.find({"booked": True})])

    user_rooms = list(mongo.db.rooms.find({"booked_by": session["user"]}))

# ----------------Booking count per user----------------     
    users_booking = mongo.db.rooms.aggregate([
        {"$match": {"booked": True}},
        {"$group": {"_id": "$booked_by", "count": {"$sum": 1}}}
    ])

    return render_template(
        "dashboard.html",
        username=session["user"],
        total_rooms=total_rooms,
        booked_rooms=booked_rooms,
        available_rooms=available_rooms,
        total_profit=total_profit,
        user_rooms=user_rooms,
        users_booking=list(users_booking)
    )

# ---------------- Home / Rooms ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        flash("⚠️ Please login first.", "danger")
        return redirect(url_for("login"))

    page = int(request.args.get("page", 1))
    per_page = 20

    # Filter params
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")
    min_rating = request.args.get("min_rating")
    search_query = request.args.get("q", "")

    query = {}

    # Search by room name
    if search_query:
        query["name"] = {"$regex": search_query, "$options": "i"}

    # Filters
    if min_price:
        query.setdefault("price", {})
        query["price"]["$gte"] = int(min_price)
    if max_price:
        query.setdefault("price", {})
        query["price"]["$lte"] = int(max_price)
    if min_rating:
        query["rating"] = {"$gte": int(min_rating)}

    # Booking POST
    if request.method == "POST":
        room_id = int(request.form.get("room_id"))
        booking_date = request.form.get("booking_date")
        mongo.db.rooms.update_one(
            {"room_id": room_id},
            {"$set": {
                "booked": True,
                "booked_by": session.get("user"),
                "booked_at": datetime.now(),
                "booking_date": booking_date
            }}
        )
        flash(f"Room {room_id} booked for {booking_date}!", "success")
        return redirect(url_for("index", page=page, min_price=min_price, max_price=max_price, min_rating=min_rating, q=search_query))

    total_rooms = mongo.db.rooms.count_documents(query)
    rooms = list(mongo.db.rooms.find(query).skip((page - 1) * per_page).limit(per_page))
    available = mongo.db.rooms.count_documents({**query, "booked": False})
    total_pages = (total_rooms + per_page - 1) // per_page

    return render_template(
        "index.html",
        rooms=rooms,
        total=total_rooms,
        available=available,
        page=page,
        total_pages=total_pages,
        min_price=min_price or "",
        max_price=max_price or "",
        min_rating=min_rating or "",
        q=search_query
    )

# ---------------- Cancel Booking ----------------
@app.route("/cancel/<int:room_id>")
def cancel_booking(room_id):
    if "user" not in session:
        flash("⚠️ Please login first.", "danger")
        return redirect(url_for("login"))
    mongo.db.rooms.update_one(
        {"room_id": room_id},
        {"$set": {"booked": False, "booked_by": None, "booked_at": None, "booking_date": None}}
    )
    flash(f"Booking for Room {room_id} canceled!", "info")
    return redirect(request.referrer or url_for("index"))

# ---------------- Room Details / Booking ----------------
@app.route("/room/<int:room_id>", methods=["GET", "POST"])
def room_details(room_id):
    if "user" not in session:
        flash("⚠️ Please login first.", "danger")
        return redirect(url_for("login"))

    room = mongo.db.rooms.find_one({"room_id": room_id})
    if not room:
        flash("⚠️ Room not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")
        adults = int(request.form.get("adults", 1))
        children = int(request.form.get("children", 0))

        mongo.db.rooms.update_one(
            {"room_id": room_id},
            {"$set": {
                "booked": True,
                "booked_by": session["user"],
                "booked_at": datetime.now(),
                "booking_date": {
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": adults,
                    "children": children
                }
            }}
        )
        flash(f"Room {room_id} booked successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("room_details.html", room=room)

# ---------------- Chatbot ----------------
qa_data = [
    # Greetings
    {"keywords": ["hi", "hii", "hiii", "hello"], "reply": "Hi! How can I help you today?"},
    {"keywords": ["how are you"], "reply": "I am a bot, but I am doing great! 😊"},
    {"keywords": ["what is your name"], "reply": "I am your helper bot."},

    #Negative
    {"keywords": ["yes", "hmm"], "reply": "How can i help you?"},
    {"keywords": ["no", "never"], "reply": "If you need help ask me I am happy to help you 😊"},
    {"keywords": ["bye", "by", "goodbye", "see you"], "reply": "Goodbye! Have a great day 😊"},
    {"keywords": ["bad", "stupid", "idiot", "hate", "angry", "mad", "nonsense"],"reply": "I'm sorry if you're upset. 😔 I’ll try to do better. Can I help you with something else?"},

    # Booking & Cancel
    {"keywords": ["how to book room", "book room"], "reply": "To book a room, go to the home page, choose your room, and click 'Book'."},
    {"keywords": ["how to cancel room", "cancel booking", "cancel room"], "reply": "Go to your dashboard and click 'Cancel' next to the booked room."},
    {"keywords": ["how to modify booking", "change booking"], "reply": "Currently, you can cancel your booking and make a new one with updated details."},
    {"keywords": ["check availability", "available rooms"], "reply": "Go to the home page and use filters to check available rooms."},
    {"keywords": ["room price", "how much is room", "cost of room"], "reply": "Room prices vary depending on the type. Please check the home page for details."},
    {"keywords": ["offers", "discount", "deals"], "reply": "We provide seasonal discounts. Please check the offers section on the home page."},

    # Login & Register
    {"keywords": ["how to login", "login"], "reply": "Go to the login page and enter your username and password."},
    {"keywords": ["how to register", "register"], "reply": "Go to the register page and fill all fields to create an account."},
    {"keywords": ["forgot password", "reset password"], "reply": "Conactto admin in case of 'Forgot Password' or to reset your password."},

    # Dashboard & Profile
    {"keywords": ["how to check dashboard", "dashboard"], "reply": "Click on Dashboard in the navbar to see your bookings and stats."},
    {"keywords": ["edit profile", "update details"], "reply": "Go to your profile page where you can edit your name, email, and mobile number."},

    # Payments
    {"keywords": ["how to pay", "payment methods", "payment options", "make payment"], "reply": "We accept cash."},
    {"keywords": ["refund policy", "refund"], "reply": "No Refunds."},

    # Check-in / Check-out
    {"keywords": ["check in time", "checkin time"], "reply": "Our standard check-in time is 12:00 PM."},
    {"keywords": ["check out time", "checkout time"], "reply": "Our standard check-out time is 11:00 AM."},
    {"keywords": ["early check in", "late check out"], "reply": "Early check-in and late check-out are subject to availability. Please contact the admin."},

    # Contact / Help
    {"keywords": ["how to contact", "contact"], "reply": "You can contact the admin via email at cksrivastava49@gmail.com."},
    {"keywords": ["help", "support"], "reply": "Sure! Tell me what you need help with: booking, login, payment, or profile?"},

    # Facilities & Services
    {"keywords": ["location", "address", "where is hotel"], "reply": "Our hotel is located at City Center near MG Road, New Delhi."},
    {"keywords": ["services", "facilities"], "reply": "We offer free WiFi, breakfast, parking, laundry, spa, gym, and a swimming pool."},
    {"keywords": ["restaurant", "food"], "reply": "Yes, we have an in-house restaurant serving multi-cuisine dishes."},
    {"keywords": ["gym", "swimming pool"], "reply": "Yes, our hotel has a fitness gym and a rooftop swimming pool for guests."},
    {"keywords": ["wifi", "internet"], "reply": "Yes, free high-speed WiFi is available in all rooms and common areas."},
    {"keywords": ["parking"], "reply": "Yes, we provide free parking for guests."},
]

@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_msg = data.get("message", "").lower().strip()

    reply = "Sorry, I don't know about that yet."

    for item in qa_data:
        if any(keyword in user_msg for keyword in item["keywords"]):
            reply = item["reply"]
            break

    return jsonify({"reply": reply})

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
