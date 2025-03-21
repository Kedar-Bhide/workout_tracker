from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///workouts.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'workout-tracker-secret-key')
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    workouts = db.relationship('Workout', backref='user', lazy=True)

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    workout_type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    today = datetime.now().date()
    
    # Get workouts for the last 30 days
    thirty_days_ago = today - timedelta(days=30)
    recent_workouts = Workout.query.filter(
        Workout.user_id == user.id,
        Workout.date >= thirty_days_ago
    ).order_by(Workout.date.desc()).all()
    
    # Check if worked out today
    worked_out_today = any(workout.date == today for workout in recent_workouts)
    
    # Calculate streaks
    dates = [workout.date for workout in recent_workouts]
    dates.sort(reverse=True)
    
    current_streak = 0
    for i in range(int((today - thirty_days_ago).days) + 1):
        check_date = today - timedelta(days=i)
        if check_date in dates:
            current_streak += 1
        else:
            break
    
    return render_template('index.html', 
                          workouts=recent_workouts, 
                          worked_out_today=worked_out_today,
                          current_streak=current_streak,
                          today=today)

@app.route('/add', methods=['GET', 'POST'])
def add_workout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        workout = Workout(
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            workout_type=request.form['workout_type'],
            duration=int(request.form['duration']),
            notes=request.form['notes'],
            user_id=session['user_id']
        )
        db.session.add(workout)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('add_workout.html', today=datetime.now().date())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:  # In production, use proper password hashing
            session['user_id'] = user.id
            return redirect(url_for('index'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Username already exists')
        
        user = User(username=username, password=password)  # In production, hash the password
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)