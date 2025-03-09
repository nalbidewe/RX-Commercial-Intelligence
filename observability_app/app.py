from flask import Flask, render_template, jsonify
from models import db, User, Thread, Step, Element, Feedback
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
# Read DATABASE_URL from environment

db_url = os.getenv('DATABASE_URL')

# Replace 'postgres://' with 'postgresql://'
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables if needed (only for local development)
with app.app_context():
    db.create_all()

# Dashboard: shows overall counts and a chart for run durations.
@app.route('/')
def dashboard():
    thread_count = Thread.query.count()
    user_count = User.query.count()
    run_count = Step.query.filter_by(type='run').count()
    return render_template('dashboard.html',
                           thread_count=thread_count,
                           user_count=user_count,
                           run_count=run_count)

# List all threads.
@app.route('/threads')
def threads():
    threads = Thread.query.order_by(Thread.createdAt.desc()).all()
    return render_template('threads.html', threads=threads)

# Detail view for a single thread (includes its steps).
@app.route('/thread/<thread_id>')
def thread_detail(thread_id):
    thread = Thread.query.get_or_404(thread_id)
    # Order steps by startTime or endTime so the display is consistent
    steps = Step.query.filter_by(threadId=thread_id).order_by(Step.startTime).all()
    
    return render_template('thread_detail.html', thread=thread, steps=steps)


# List all users.
@app.route('/users')
def users():
    users = User.query.order_by(User.createdAt.desc()).all()
    return render_template('users.html', users=users)

# Detail view for a single user.
@app.route('/user/<user_id>')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_detail.html', user=user)

# API endpoint to get runs (steps with type 'run') for charting.
@app.route('/api/runs')
def api_runs():
    runs = Step.query.filter_by(type='run').order_by(Step.startTime.desc()).all()
    run_list = [{
        'id': run.id,
        'name': run.name if run.name else run.id,
        'startTime': run.startTime.isoformat(),
        'endTime': run.endTime.isoformat(),
        'threadId': run.threadId
    } for run in runs]
    return jsonify(run_list)

if __name__ == '__main__':
    app.run(debug=True)
