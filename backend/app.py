from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from functools import wraps
from config import Config
import openai
from datetime import timedelta, datetime
import os
import json
from io import BytesIO
import smtplib

# ----------------- App Setup -----------------

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "your_secret_key"
app.permanent_session_lifetime = timedelta(hours=1)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/task_manager"
mongo = PyMongo(app)

# Collections
tasks_collection = mongo.db.tasks
routines_collection = mongo.db.routines
reminders_collection = mongo.db.reminders
habits_collection = mongo.db.habits
events_collection = mongo.db.events

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
openai.api_key = app.config['OPENAI_API_KEY']

# MongoDB collections
users = mongo.db.users
tasks = mongo.db.tasks
reminders = mongo.db.reminders

@app.context_processor
def inject_settings():
    # Example settings (you can fetch these from the database or session)
    settings = {
        "theme": session.get("theme", "light"),  # Default to "light" theme
    }
    return {"settings": settings}

# ----------------- Translations -----------------

translations = {
    "english": {
        "welcome": "Welcome to Task Manager AI",
        "organize_tasks": "Organize your tasks efficiently and boost productivity.",
        "login": "Login",
        "signup": "Sign Up",
        "dashboard": {
            "welcome": "Welcome to your Dashboard",
            "total_tasks": "Total Tasks",
            "completed_tasks": "Completed Tasks",
            "completion_rate": "Completion Rate",
            "avg_duration": "Avg. Duration",
            "task_trend": "Task Completion Trend",
            "new_task": "Add Task",
            "current_time": "Current Time"
        },
        "settings": {
            "title": "Settings",
            "theme": "Theme",
            "language": "Language",
            "notifications": "Notifications",
            "enable_notifications": "Enable Notifications",
            "export_data": "Export Data",
            "import_data": "Import Data",
            "save_settings": "Save Settings"
        }
    },
    "tamil": {
        "welcome": "டாஸ்க் மேனேஜர் ஏ.ஐ-க்கு வரவேற்கிறோம்",
        "organize_tasks": "உங்கள் பணிகளை திறமையாக ஒழுங்குபடுத்தி உற்பத்தித்திறனை மேம்படுத்துங்கள்.",
        "login": "உள்நுழைய",
        "signup": "பதிவு செய்யவும்",
        "dashboard": {
            "welcome": "உங்கள் டாஷ்போர்டுக்கு வரவேற்கிறோம்",
            "total_tasks": "மொத்த பணிகள்",
            "completed_tasks": "நிறைவு செய்யப்பட்ட பணிகள்",
            "completion_rate": "நிறைவு விகிதம்",
            "avg_duration": "சராசரி காலம்",
            "task_trend": "பணிகள் நிறைவு போக்கு",
            "new_task": "பணி சேர்க்கவும்",
            "current_time": "தற்போதைய நேரம்"
        },
        "settings": {
            "title": "அமைப்புகள்",
            "theme": "தீம்",
            "language": "மொழி",
            "notifications": "அறிவிப்புகள்",
            "enable_notifications": "அறிவிப்புகளை இயக்கவும்",
            "export_data": "தரவை ஏற்றுமதி செய்யவும்",
            "import_data": "தரவை இறக்குமதி செய்யவும்",
            "save_settings": "அமைப்புகளை சேமிக்கவும்"
        }
    },
    "hindi": {
        "welcome": "टास्क मैनेजर एआई में आपका स्वागत है",
        "organize_tasks": "अपने कार्यों को कुशलतापूर्वक व्यवस्थित करें और उत्पादकता बढ़ाएं।",
        "login": "लॉगिन करें",
        "signup": "साइन अप करें",
        "dashboard": {
            "welcome": "आपके डैशबोर्ड में आपका स्वागत है",
            "total_tasks": "कुल कार्य",
            "completed_tasks": "पूर्ण कार्य",
            "completion_rate": "पूर्णता दर",
            "avg_duration": "औसत अवधि",
            "task_trend": "कार्य पूर्णता प्रवृत्ति",
            "new_task": "कार्य जोड़ें",
            "current_time": "वर्तमान समय"
        },
        "settings": {
            "title": "सेटिंग्स",
            "theme": "थीम",
            "language": "भाषा",
            "notifications": "सूचनाएं",
            "enable_notifications": "सूचनाएं सक्षम करें",
            "export_data": "डेटा निर्यात करें",
            "import_data": "डेटा आयात करें",
            "save_settings": "सेटिंग्स सहेजें"
        }
    }
}

# ----------------- Helper: Login Required -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- Helper: Calculate Productivity -----------------

def calculate_productivity(user_id):
    total_tasks = tasks.count_documents({'user_id': user_id})
    completed_tasks = tasks.count_documents({'user_id': user_id, 'status': 'completed'})
    if total_tasks == 0:
        return 0
    return round((completed_tasks / total_tasks) * 100, 2)

def authenticate(email, password):
    user = users.find_one({'email': email})
    if user and 'password' in user and check_password_hash(user['password'], password):
        return user
    return None

# ----------------- Routes: Authentication -----------------

@app.route('/')
def index():
    settings = {
        'language': 'english',
        'theme': 'light'
    }
    translation = translations.get(settings['language'], translations['english'])

    return render_template('index.html', translation=translation, settings=settings)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    settings = {
        'language': 'english',
        'theme': 'light',
        'notifications': True
    }
    translation = translations.get(settings['language'], translations['english'])

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if all fields are provided
        if not name or not email or not password or not confirm_password:
            flash('All fields are required.', 'error')
            return render_template('signup.html', translation=translation, settings=settings)

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html', translation=translation, settings=settings)

        # Check if the email is already registered
        if users.find_one({'email': email}):
            flash('Email is already registered.', 'error')
            return render_template('signup.html', translation=translation, settings=settings)

        # Hash the password and save the user
        hashed_password = generate_password_hash(password)
        user_id = users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "settings": {
                "language": "english",
                "theme": "light",
                "email_notifications": True
            }
        }).inserted_id

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html', translation=translation, settings=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = {
        'language': 'english',
        'theme': 'light',
        'notifications': True
    }
    translation = translations.get(settings['language'], translations['english'])

    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        password = request.form['password']
        user = authenticate(email, password)
        if user:
            session['user'] = str(user['_id'])
            print("LOGIN SUCCESSFUL, redirecting to dashboard")  # Add this line
            return redirect('/dashboard')
        else:
            print("LOGIN FAILED")  # Add this line
            flash('Invalid credentials', 'error')
            return render_template('login.html', translation=translation, settings=settings)

    return render_template('login.html', translation=translation, settings=settings)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ----------------- Dashboard -----------------

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id})

    # Get user's preferred language
    language = user.get('settings', {}).get('language', 'english')
    translation = translations.get(language, translations['english'])

    # Fetch user's name
    name = user.get('name', 'User')  # Default to 'User' if name is not found

    # Fetch all tasks for the user
    all_tasks = tasks.find({'user_id': user_id})

    # Get today's date and tomorrow's date
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # Filter tasks for today and upcoming tasks
    today_tasks = [
        task for task in all_tasks
        if datetime.strptime(task['deadline'], '%Y-%m-%dT%H:%M').date() == today
    ]
    upcoming_tasks = [
        task for task in all_tasks
        if datetime.strptime(task['deadline'], '%Y-%m-%dT%H:%M').date() >= tomorrow
    ]

    # Calculate stats
    total_tasks = len(list(all_tasks))
    completed_tasks = tasks.count_documents({'user_id': user_id, 'status': 'completed'})
    in_progress = tasks.count_documents({'user_id': user_id, 'status': 'in-progress'})
    productivity = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    stats = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'in_progress': in_progress,
        'productivity': round(productivity, 2)
    }

    return render_template(
        'dashboard.html',
        translation=translation,
        name=name,
        stats=stats,
        today_tasks=today_tasks,
        upcoming_tasks=upcoming_tasks,
        current_date=today.strftime('%A, %B %d, %Y')
    )

# ----------------- Forgot / Reset Password -----------------

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    settings = {
        'language': 'english',
        'theme': 'light',
        'notifications': True
    }
    translation = translations.get(settings['language'], translations['english'])

    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        user = users.find_one({'email': email})
        if user:
            try:
                token = serializer.dumps(email, salt='email-reset')
                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message('Password Reset Request', recipients=[email])
                msg.body = f'Click the link to reset your password:\n\n{reset_link}\n\nThis link expires in 30 minutes.'
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'info')
            except smtplib.SMTPAuthenticationError:
                flash('Failed to send email. Please check your email credentials.', 'danger')
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'danger')
        else:
            flash('No user found with this email address.', 'danger')

    return render_template('forgot_password.html', translation=translation, settings=settings)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='email-reset', max_age=1800)
    except SignatureExpired:
        flash('The reset link has expired.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html')
        hashed_password = generate_password_hash(password)
        users.update_one({'email': email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# ----------------- Task Management -----------------

from flask import jsonify, request
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# Fetch all tasks for the logged-in user
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    user_id = ObjectId(session['user'])
    tasks_list = list(tasks.find({'user_id': user_id}))
    for task in tasks_list:
        task['_id'] = str(task['_id'])  # Convert ObjectId to string
    return jsonify(tasks_list)

# Add a new task
@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    user_id = ObjectId(session['user'])
    data = request.json
    task = {
        'user_id': user_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'deadline': datetime.strptime(data['deadline'], '%Y-%m-%dT%H:%M'),
        'priority': data['priority'],
        'category': data['category'],
        'status': 'pending',
        'createdAt': datetime.now()
    }
    tasks.insert_one(task)
    return jsonify({'success': True, 'message': 'Task added successfully'})

# Delete a task
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    user_id = ObjectId(session['user'])
    result = tasks.delete_one({'_id': ObjectId(task_id), 'user_id': user_id})
    if result.deleted_count == 1:
        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Task not found'}), 404

@app.route('/tasks', methods=['GET'])
@login_required
def tasks_page():
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id})

    # Get user's preferred language and theme
    settings = user.get('settings', {
        'language': 'english',
        'theme': 'light',
        'notifications': True
    })
    language = settings.get('language', 'english')
    translation = translations.get(language, translations['english'])

    return render_template('tasks.html', translation=translation, settings=settings)

@app.route('/tasks/toggle/<task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    user_id = ObjectId(session['user'])

    # Toggle the task's completion status
    task = tasks.find_one({'_id': ObjectId(task_id), 'user_id': user_id})
    if task:
        tasks.update_one(
            {'_id': ObjectId(task_id), 'user_id': user_id},
            {'$set': {'done': not task['done']}}
        )
        return jsonify({'success': True, 'message': 'Task status updated successfully.'})
    return jsonify({'success': False, 'message': 'Task not found.'}), 404


@app.route('/tasks/<category>', methods=['GET'])
@login_required
def get_tasks_by_category(category):
    user_id = ObjectId(session['user'])
    tasks_by_category = list(tasks.find({'user_id': user_id, 'tab': category}))
    for task in tasks_by_category:
        task['_id'] = str(task['_id'])  # Convert ObjectId to string for JSON serialization
    return jsonify(tasks_by_category)

# ----------------- Calendar -----------------

@app.route('/calendar')
def calendar():
    
    translation = {
        "goal_planner": "Goal Planner",
        "new_event": "New Event",
        "view_tasks": "View Tasks",
        "toggle_view": "Toggle View",
        "upcoming_events": "Upcoming Events",
        "quick_add": "Quick Add Event",
        "event_title": "Event Title",
        "today": "Today",
        "tomorrow": "Tomorrow",
        "add_event": "Add Event",
        "navigation": "Navigation",
        "previous": "Previous",
        "next": "Next",
        "start_date": "Start Date",
        "end_date": "End Date",
        "description": "Description",
        "event_color": "Event Color",
        "priority": "Priority",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "all_day_event": "All Day Event",
        "cancel": "Cancel",
        "save_event": "Save Event",
        "saving": "Saving",
        "event_details": "Event Details",
        "when": "When",
        "no_description": "No Description",
        "edit": "Edit",
        "delete": "Delete",
        "confirmation": "Confirmation",
        "confirm_delete": "Confirm Delete",
        "confirm_delete_event": "Are you sure you want to delete this event?",
        "event_deleted": "Event Deleted",
        "event_updated": "Event Updated",
        "event_created": "Event Created",
        "event_added": "Event Added",
        "event_title_required": "Event title is required.",
        "end_date_error": "End date must be after start date.",
        "save_error": "Failed to save event.",
        "update_error": "Failed to update event.",
        "no_upcoming_events": "No upcoming events.",
        "all_day": "All Day"
    }
    return render_template('calendar.html', translation=translation)

@app.route('/calendar/tasks/<date>')
@login_required
def tasks_by_date(date):
    user_id = ObjectId(session['user'])
    user_tasks = list(tasks.find({'user_id': user_id, 'due_date': date}))
    for task in user_tasks:
        task['_id'] = str(task['_id'])
    return jsonify(user_tasks)

@app.route('/calendar/tasks')
@login_required
def calendar_tasks():
    user_id = session.get('user_id')
    # Assuming MongoDB is used for tasks, replace SQL logic with MongoDB query
    user_tasks = list(tasks.find({'user_id': ObjectId(user_id)}))
    events = []

    for task in user_tasks:
        events.append({
            "title": task['task_name'],
            "start": task['due_date'],  # ensure it's in 'YYYY-MM-DD' format
            "description": task['task_description']
        })
    events = []

    for task in tasks:
        events.append({
            "title": task['title'],
            "start": task['due_date'],  # ensure it's in 'YYYY-MM-DD' format
            "description": task['description']
        })

    return jsonify(events)

@app.route('/calendar/events', methods=['GET'])
@login_required
def get_events():
    user_id = ObjectId(session['user'])
    user_events = list(events_collection.find({'user_id': user_id}))
    for event in user_events:
        event['_id'] = str(event['_id'])  # Convert ObjectId to string
    return jsonify(user_events)

@app.route('/calendar/events', methods=['POST'])
@login_required
def create_event():
    data = request.json
    user_id = ObjectId(session['user'])
    new_event = {
        "user_id": user_id,
        "title": data['title'],
        "start": data['start'],
        "end": data['end'],
        "description": data.get('description', ''),
        "color": data.get('color', 'yellow'),
        "priority": data.get('priority', 'medium'),
        "allDay": data.get('allDay', False),
        "createdAt": datetime.utcnow()
    }
    result = events_collection.insert_one(new_event)
    new_event['_id'] = str(result.inserted_id)  # Convert ObjectId to string
    return jsonify(new_event), 201

@app.route('/calendar/events/<event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    data = request.json
    updated_event = events_collection.find_one_and_update(
        {"_id": ObjectId(event_id)},
        {"$set": {
            "title": data['title'],
            "start": data['start'],
            "end": data['end'],
            "description": data.get('description', ''),
            "color": data.get('color', 'yellow'),
            "priority": data.get('priority', 'medium'),
            "allDay": data.get('allDay', False),
            "updatedAt": datetime.utcnow()
        }},
        return_document=True
    )
    if updated_event:
        updated_event['_id'] = str(updated_event['_id'])  # Convert ObjectId to string
        return jsonify(updated_event)
    return jsonify({"error": "Event not found"}), 404

@app.route('/calendar/events/<event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    result = events_collection.delete_one({"_id": ObjectId(event_id)})
    if result.deleted_count > 0:
        return jsonify({"message": "Event deleted"}), 200
    return jsonify({"error": "Event not found"}), 404

# ----------------- AI Chat -----------------

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'response': "Please provide a message."}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=100
        )
        ai_response = response['choices'][0]['message']['content']
    except Exception as e:
        print("OpenAI API Error:", e)
        ai_response = "Sorry, I couldn't process your request. Please try again later."

    return jsonify({'response': ai_response})

@app.route('/api/ai-suggestion', methods=['POST'])
@login_required
def ai_suggestion():
    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'response': "Please provide a message."}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=100
        )
        ai_response = response['choices'][0]['message']['content']
    except Exception as e:
        print("OpenAI API Error:", e)
        ai_response = "Sorry, I couldn't process your request. Please try again later."

    return jsonify({'response': ai_response})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message', '')
    # Replace this with your AI logic or OpenAI API call
    ai_reply = "This is a sample AI response to: " + user_message
    return jsonify({'reply': ai_reply})

# ----------------- Analytics -----------------

@app.route('/analytics')
@login_required
def analytics():
    user_id = ObjectId(session['user'])
    user_tasks = list(tasks.find({'user_id': user_id}))

    # Calculate priority counts
    priority_counts = {
        'Low': sum(1 for task in user_tasks if task.get('priority') == 'Low'),
        'Medium': sum(1 for task in user_tasks if task.get('priority') == 'Medium'),
        'High': sum(1 for task in user_tasks if task.get('priority') == 'High'),
    }

    # Calculate category counts
    category_counts = {
        'Yearly': sum(1 for task in user_tasks if task.get('category') == 'Yearly'),
        'Monthly': sum(1 for task in user_tasks if task.get('category') == 'Monthly'),
        'Weekly': sum(1 for task in user_tasks if task.get('category') == 'Weekly'),
        'Daily': sum(1 for task in user_tasks if task.get('category') == 'Daily'),
    }

    # Weekly productivity heatmap
    weekly_productivity = [[0] * 7 for _ in range(4)]  # 4 time slots (morning, midday, afternoon, evening)
    for task in user_tasks:
        if 'due_date' in task:
            due_date_str = task['due_date']
            try:
                # Try parsing with seconds
                due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Fallback to parsing without seconds
                due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")

            day_of_week = due_date.weekday()  # Monday = 0, Sunday = 6
            hour = due_date.hour
            if 6 <= hour < 9:
                weekly_productivity[0][day_of_week] += 1
            elif 9 <= hour < 12:
                weekly_productivity[1][day_of_week] += 1
            elif 12 <= hour < 15:
                weekly_productivity[2][day_of_week] += 1
            elif 15 <= hour < 18:
                weekly_productivity[3][day_of_week] += 1

    # Example data for other variables
    task_performance = {
        'Daily': {'total': 10, 'completed': 7},
        'Weekly': {'total': 5, 'completed': 3},
        'Monthly': {'total': 8, 'completed': 6},
        'Yearly': {'total': 2, 'completed': 1},
    }
    task_trend = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    task_completion_trend = [3, 8, 12, 18, 22, 28, 32, 38, 42, 48, 52, 58]
    habit_consistency = {'Exercise': 80, 'Reading': 60, 'Meditation': 70}
    recommendations = [
        {'title': 'Focus on High Priority Tasks', 'description': 'Complete tasks with high priority first.', 'color': 'red'},
        {'title': 'Improve Daily Productivity', 'description': 'Try to complete at least 5 tasks daily.', 'color': 'green'},
    ]

    return render_template(
        'analytics.html',
        priority_counts=priority_counts,
        category_counts=category_counts,
        weekly_productivity=weekly_productivity,
        task_performance=task_performance,
        task_trend=task_trend,
        task_completion_trend=task_completion_trend,
        habit_consistency=habit_consistency,
        recommendations=recommendations
    )

@app.route('/api/analytics', methods=['GET'])
def api_analytics():
    try:
        tasks = list(tasks_collection.find())

        total_tasks = len(tasks)
        completed_tasks = sum(1 for task in tasks if task.get('status') == 'completed')
        completion_rate = total_tasks > 0 and round((completed_tasks / total_tasks) * 100, 1) or 0

        priority_counts = {
            'Low': sum(1 for task in tasks if task.get('priority') == 'Low'),
            'Medium': sum(1 for task in tasks if task.get('priority') == 'Medium'),
            'High': sum(1 for task in tasks if task.get('priority') == 'High'),
        }

        category_counts = {
            'daily': sum(1 for task in tasks if task.get('category') == 'daily'),
            'weekly': sum(1 for task in tasks if task.get('category') == 'weekly'),
            'monthly': sum(1 for task in tasks if task.get('category') == 'monthly'),
            'yearly': sum(1 for task in tasks if task.get('category') == 'yearly'),
        }

        completed_durations = [
            (datetime.strptime(task['completedAt'], "%Y-%m-%dT%H:%M:%S") - datetime.strptime(task['createdAt'], "%Y-%m-%dT%H:%M:%S")).days
            for task in tasks if task.get('status') == 'completed' and task.get('completedAt')
        ]

        avg_duration = len(completed_durations) > 0 and round(sum(completed_durations) / len(completed_durations), 1) or 0

        today = datetime.utcnow()
        trend = [0] * 7
        for task in tasks:
            if task.get('status') == 'completed' and task.get('completedAt'):
                completed_date = datetime.strptime(task['completedAt'], "%Y-%m-%dT%H:%M:%S")
                diff_days = (today - completed_date).days
                if 0 <= diff_days < 7:
                    trend[6 - diff_days] += 1

        return jsonify({
            'totalTasks': total_tasks,
            'completedTasks': completed_tasks,
            'completionRate': completion_rate,
            'priorityCounts': priority_counts,
            'categoryCounts': category_counts,
            'avgDuration': avg_duration,
            'trend': trend,
        })
    except Exception as e:
        return jsonify({'error': 'Server Error'}), 500

# ----------------- Settings -----------------

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    user_id = ObjectId(session['user'])

    # Get form data
    language = request.form.get('language', 'english')
    theme = request.form.get('theme', 'light')
    notifications = request.form.get('notifications') == 'on'

    # Update user settings in the database
    users.update_one(
        {'_id': user_id},
        {'$set': {
            'settings.language': language,
            'settings.theme': theme,
            'settings.notifications': notifications
        }}
    )

    flash('Settings updated successfully!', 'success')
    return redirect(url_for('settings_page'))


@app.route('/export_data', methods=['GET'])
@login_required
def export_data():
    user_id = ObjectId(session['user'])

    # Fetch all tasks for the user
    user_tasks = list(tasks.find({'user_id': user_id}, {'_id': 0}))  # Exclude MongoDB's ObjectId

    # Convert tasks to JSON and create a downloadable file
    tasks_json = json.dumps(user_tasks, indent=4)
    buffer = BytesIO()
    buffer.write(tasks_json.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='tasks.json',
        mimetype='application/json'
    )

@app.route('/import_data', methods=['POST'])
@login_required
def import_data():
    user_id = ObjectId(session['user'])

    # Check if a file is uploaded
    if 'import_file' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('settings_page'))

    file = request.files['import_file']

    # Check if the file is a JSON file
    if not file.filename.endswith('.json'):
        flash('Invalid file type. Please upload a JSON file.', 'danger')
        return redirect(url_for('settings_page'))

    try:
        # Load tasks from the uploaded file
        imported_tasks = json.load(file)

        # Add user_id to each task and insert into the database
        for task in imported_tasks:
            task['user_id'] = user_id
            tasks.insert_one(task)

        flash('Tasks imported successfully!', 'success')
    except Exception as e:
        print(f"Error importing tasks: {e}")
        flash('Failed to import tasks. Please check the file format.', 'danger')

    return redirect(url_for('settings_page'))


@app.route('/settings')
@login_required
def settings_page():
    user_id = ObjectId(session['user'])

    # Fetch user settings
    user = users.find_one({'_id': user_id})
    settings = user.get('settings', {
        'language': 'english',
        'theme': 'light',
        'notifications': True
    })

    # Get translations for the selected language
    language = settings.get('language', 'english')
    translation = translations.get(language, translations['english'])

    return render_template('settings.html', settings=settings, translation=translation)

@app.route("/set-theme/<theme>")
def set_theme(theme):
    if theme in ["light", "dark"]:
        session["theme"] = theme
    return redirect(request.referrer or url_for("index"))

# ----------------- Daily Routine -----------------

@app.route('/routine', methods=['GET'])
@login_required
def get_routine():
    user_id = ObjectId(session['user'])
    date = request.args.get('date')
    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    routine = routines.get(date, [])
    return jsonify(routine)

@app.route('/routine/<date>', methods=['GET'])
@login_required
def get_daily_routine(date):
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    routine = routines.get(date, [])
    return jsonify(routine)

@app.route('/routine/add', methods=['POST'])
@login_required
def add_routine_task():
    user_id = ObjectId(session['user'])
    data = request.json

    task = data.get('task', '').strip()
    time = data.get('time', '').strip()
    date = data.get('date', '').strip()

    if not task or not time or not date:
        return jsonify({'success': False, 'message': 'Task, time, and date are required.'}), 400

    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    if date not in routines:
        routines[date] = []

    routines[date].append({'task': task, 'time': time})
    users.update_one({'_id': user_id}, {'$set': {'daily_routines': routines}})
    return jsonify({'success': True, 'message': 'Routine task added successfully.'})

@app.route('/routine/edit/<int:index>', methods=['POST'])
@login_required
def edit_routine(index):
    user_id = ObjectId(session['user'])
    data = request.json
    new_task = data.get('task', '').strip()
    new_time = data.get('time', '').strip()
    date = data.get('date', '').strip()

    if not new_task or not new_time or not date:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    if date not in routines or index < 0 or index >= len(routines[date]):
        return jsonify({'success': False, 'message': 'Invalid task index.'}), 400

    routines[date][index] = {'task': new_task, 'time': new_time}
    users.update_one({'_id': user_id}, {'$set': {'daily_routines': routines}})
    return jsonify({'success': True, 'message': 'Task updated successfully.'})

@app.route('/routine/delete/<int:index>', methods=['POST'])
@login_required
def delete_routine_task(index):
    user_id = ObjectId(session['user'])
    date = request.args.get('date', '').strip()

    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    if date not in routines or index < 0 or index >= len(routines[date]):
        return jsonify({'success': False, 'message': 'Invalid task index.'}), 400

    routines[date].pop(index)
    users.update_one({'_id': user_id}, {'$set': {'daily_routines': routines}})
    return jsonify({'success': True, 'message': 'Task deleted successfully.'})

@app.route('/routine/save', methods=['POST'])
@login_required
def save_daily_routine():
    user_id = ObjectId(session['user'])
    data = request.json

    # Extract routine details
    date = data.get('date')
    routine_tasks = data.get('tasks', [])

    if not date or not routine_tasks:
        return jsonify({'success': False, 'message': 'Date and tasks are required.'}), 400

    # Fetch the user's existing routines
    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})

    # Save the routine for the specified date
    routines[date] = routine_tasks
    users.update_one({'_id': user_id}, {'$set': {'daily_routines': routines}})

    return jsonify({'success': True, 'message': 'Daily routine saved successfully.'})

@app.route('/routines', methods=['GET'])
def get_routines():
    routines = list(routines_collection.find())
    for routine in routines:
        routine['_id'] = str(routine['_id'])  # Convert ObjectId to string
    return jsonify(routines)

@app.route('/routines/add', methods=['POST'])
def add_routine():
    data = request.json
    routine = {
        "task": data.get("task"),
        "time": data.get("time"),
        "date": data.get("date"),
        "completed": False,
        "createdAt": datetime.utcnow()
    }
    result = routines_collection.insert_one(routine)
    return jsonify({"success": True, "routine_id": str(result.inserted_id)})

@app.route('/routines/update/<routine_id>', methods=['PUT'])
def update_routine(routine_id):
    data = request.json
    routines_collection.update_one(
        {"_id": ObjectId(routine_id)},
        {"$set": {
            "task": data.get("task"),
            "time": data.get("time"),
            "completed": data.get("completed"),
            "updatedAt": datetime.utcnow()
        }}
    )
    return jsonify({"success": True})

@app.route('/routines/delete/<routine_id>', methods=['DELETE'])
def delete_routine(routine_id):
    routines_collection.delete_one({"_id": ObjectId(routine_id)})
    return jsonify({"success": True})

@app.route('/api/routines/<date>', methods=['GET'])
@login_required
def get_routines_by_date(date):
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {}).get(date, [])
    return jsonify(routines)

# Add a routine task
@app.route('/api/routines', methods=['POST'])
@login_required
def add_routine_api():
    user_id = ObjectId(session['user'])
    data = request.json
    date = data['date']
    task = {
        'task': data['task'],
        'time': data['time']
    }
    user = users.find_one({'_id': user_id})
    routines = user.get('daily_routines', {})
    if date not in routines:
        routines[date] = []
    routines[date].append(task)
    users.update_one({'_id': user_id}, {'$set': {'daily_routines': routines}})
    return jsonify({'success': True, 'message': 'Routine task added successfully'})

# ----------------- Reminders -----------------

@app.route('/reminders', methods=['GET'])
def get_reminders():
    reminders = list(reminders_collection.find())
    for reminder in reminders:
        reminder['_id'] = str(reminder['_id'])  # Convert ObjectId to string
    return jsonify(reminders)

@app.route('/reminders/add', methods=['POST'])
def add_reminder():
    data = request.json
    reminder = {
        "title": data.get("title"),
        "description": data.get("description"),
        "dueDate": data.get("dueDate"),
        "createdAt": datetime.utcnow()
    }
    result = reminders_collection.insert_one(reminder)
    return jsonify({"success": True, "reminder_id": str(result.inserted_id)})

@app.route('/reminders/delete/<reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    reminders_collection.delete_one({"_id": ObjectId(reminder_id)})
    return jsonify({"success": True})

# ----------------- Profile -----------------

@app.route('/profile', methods=['GET'])
@login_required
def profile_page():
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id})

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))

    # Get user's settings
    settings = user.get('settings', {
        'language': 'english',
        'theme': 'light',
        'email_notifications': True
    })

    return render_template('profile.html', user=user, settings=settings)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user_id = ObjectId(session['user'])
    data = request.form

    # Update user fields
    update_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "username": data.get("username"),
        "phone": data.get("phone"),
        "bio": data.get("bio")
    }

    users.update_one({'_id': user_id}, {'$set': update_data})
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile_page'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = ObjectId(session['user'])
    data = request.form

    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    user = users.find_one({'_id': user_id})

    # Verify current password
    if not check_password_hash(user['password'], current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('profile_page'))

    # Check if new passwords match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile_page'))

    # Update password
    hashed_password = generate_password_hash(new_password)
    users.update_one({'_id': user_id}, {'$set': {'password': hashed_password}})
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile_page'))

@app.route('/profile/delete', methods=['POST'])
@login_required
def delete_account():
    user_id = ObjectId(session['user'])
    data = request.form

    password = data.get('password')
    user = users.find_one({'_id': user_id})

    # Verify password
    if not check_password_hash(user['password'], password):
        flash('Password is incorrect.', 'error')
        return redirect(url_for('profile_page'))

    # Delete user account
    users.delete_one({'_id': user_id})
    session.clear()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))

@app.route('/profile/export', methods=['GET'])
@login_required
def export_user_data():
    user_id = ObjectId(session['user'])
    user = users.find_one({'_id': user_id}, {'_id': 0})  # Exclude MongoDB's ObjectId

    # Convert user data to JSON
    user_data = json.dumps(user, indent=4)
    buffer = BytesIO()
    buffer.write(user_data.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='user_data.json',
        mimetype='application/json'
    )

# ----------------- Habits -----------------

@app.route('/api/habits', methods=['GET'])
@login_required
def api_habits():
    user_id = ObjectId(session['user'])
    habits = list(habits_collection.find({'user_id': user_id}))
    for habit in habits:
        habit['_id'] = str(habit['_id'])  # Convert ObjectId to string
    return jsonify(habits)

# ----------------- Run App -----------------

if __name__ == '__main__':
    app.run(debug=True)

# Example task data
example_task = {
    "_id": ObjectId("abcdef1234567890abcdef12"),
    "user_id": ObjectId("1234567890abcdef12345678"),
    "task_name": "Complete project report",
    "task_description": "Finish the report for the client project",
    "due_date": "2025-04-20",
    "status": "in-progress",
    "priority": "high"
}

# Example habit data
example_habit = {
    "_id": ObjectId("abcdef1234567890abcdef34"),
    "user_id": ObjectId("1234567890abcdef12345678"),
    "name": "Exercise",
    "completed_days": [True, True, False, True, False, False, False]
}

from werkzeug.security import generate_password_hash
print(generate_password_hash("yourpassword"))
