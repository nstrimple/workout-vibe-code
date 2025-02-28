import sqlite3
import os
import dspy
import json
import argparse
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime
from typing import List, Dict, Any, Optional

app = Flask(__name__)
app.secret_key = 'workout_vibe_secret_key'  # For session management

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

class ExerciseDB:
    def __init__(self, db_path='data/exercises.db'):
        """Initialize the database connection."""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def get_all_exercises(self):
        """Get all exercises from the database."""
        self.cursor.execute("SELECT * FROM exercises")
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_exercises_by_muscle_group(self, muscle_group):
        """Get exercises for a specific muscle group."""
        self.cursor.execute("SELECT * FROM exercises WHERE muscle_group = ?", (muscle_group,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_exercises_by_equipment(self, equipment):
        """Get exercises for specific equipment."""
        self.cursor.execute("SELECT * FROM exercises WHERE equipment = ?", (equipment,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

class GymDB:
    def __init__(self, db_path='data/gyms.db'):
        """Initialize the gym database connection."""
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        # Create gyms table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS gyms (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            description TEXT
        )
        ''')
        
        # Create equipment table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY,
            gym_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            description TEXT,
            FOREIGN KEY (gym_id) REFERENCES gyms (id)
        )
        ''')
        
        self.conn.commit()
    
    def add_gym(self, name: str, location: str = None, description: str = None) -> int:
        """Add a new gym to the database."""
        self.cursor.execute(
            'INSERT INTO gyms (name, location, description) VALUES (?, ?, ?)',
            (name, location, description)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def add_equipment(self, gym_id: int, name: str, category: str, 
                     quantity: int = 1, description: str = None) -> int:
        """Add equipment to a gym."""
        self.cursor.execute(
            'INSERT INTO equipment (gym_id, name, category, quantity, description) VALUES (?, ?, ?, ?, ?)',
            (gym_id, name, category, quantity, description)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_gym(self, gym_id: int) -> Optional[Dict]:
        """Get gym details by ID."""
        self.cursor.execute('SELECT * FROM gyms WHERE id = ?', (gym_id,))
        gym = self.cursor.fetchone()
        if gym:
            return dict(gym)
        return None
    
    def get_all_gyms(self) -> List[Dict]:
        """Get all gyms."""
        self.cursor.execute('SELECT * FROM gyms ORDER BY name')
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_gym_equipment(self, gym_id: int) -> List[Dict]:
        """Get all equipment for a specific gym."""
        self.cursor.execute('SELECT * FROM equipment WHERE gym_id = ? ORDER BY category, name', (gym_id,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

# DSPy Classes for Workout Generation
class Exercise(dspy.Signature):
    """Information about an exercise."""
    id: int = dspy.OutputField()
    name: str = dspy.OutputField()
    muscle_group: str = dspy.OutputField()
    equipment: str = dspy.OutputField()

class WorkoutRequest(dspy.Signature):
    """A request for a workout."""
    description: str = dspy.InputField()
    gym_equipment: List[Dict] = dspy.InputField()

class WorkoutPlan(dspy.Signature):
    """A workout plan with exercises."""
    title: str = dspy.OutputField()
    description: str = dspy.OutputField()
    exercises: List[Dict[str, Any]] = dspy.OutputField()
    sets_and_reps: List[str] = dspy.OutputField()
    rest_times: List[str] = dspy.OutputField()
    notes: str = dspy.OutputField()

class WorkoutGenerator(dspy.Module):
    """Module to generate a workout plan based on user input and available equipment."""
    
    def __init__(self, retriever):
        super().__init__()
        self.retriever = retriever
        self.generate_workout = dspy.ChainOfThought(
            WorkoutRequest, WorkoutPlan
        )
    
    def forward(self, description: str, gym_equipment: List[Dict]) -> WorkoutPlan:
        """Generate a workout plan based on user description and gym equipment."""
        # Retrieve relevant exercises
        exercises = self.retriever(description).passages
        
        # Generate the workout plan
        workout_request = WorkoutRequest(
            description=description,
            gym_equipment=gym_equipment
        )
        workout_plan = self.generate_workout(workout_request)
        
        return workout_plan

def setup_vector_db(exercises):
    """Set up a vector database for exercises."""
    # For simplicity, we'll use a list-based retriever
    # In a real application, you might want to use a proper vector DB
    
    passages = []
    for exercise in exercises:
        passage_text = (f"Exercise ID: {exercise['id']}, Name: {exercise['name']}, "
                        f"Muscle Group: {exercise['muscle_group']}, Equipment: {exercise['equipment']}")
        passages.append(dspy.Passage(text=passage_text, id=exercise['id']))
    
    return dspy.SimpleRetriever(passages=passages)

def configure_lm(provider='openai'):
    """Configure the language model based on provider."""
    if provider.lower() == 'claude':
        # Set up Anthropic Claude
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not found")
        
        return dspy.Anthropic(model="claude-3-sonnet-20240229", api_key=api_key)
    else:
        # Default to OpenAI
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not found")
        
        # In dspy v2.0.0+, use ChatOpenAI instead of OpenAI
        try:
            return dspy.ChatOpenAI(model="gpt-4-turbo", api_key=api_key)
        except AttributeError:
            # Fallback for compatibility with different dspy versions
            import openai
            openai.api_key = api_key
            return dspy.OpenAIChat(model="gpt-4-turbo")

def bootstrap_examples():
    """Create examples for bootstrapping."""
    examples = [
        dspy.Example(
            x=WorkoutRequest(
                description="I want a quick full body workout with dumbbells",
                gym_equipment=[
                    {"name": "Dumbbells", "category": "Free Weights", "quantity": 10},
                    {"name": "Bench", "category": "Free Weights", "quantity": 2}
                ]
            ),
            y=WorkoutPlan(
                title="Quick Full Body Dumbbell Workout",
                description="A time-efficient full body workout using only dumbbells, perfect for building strength and endurance.",
                exercises=[
                    {"name": "Dumbbell Squat", "muscle_group": "Legs", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                    {"name": "Dumbbell Bench Press", "muscle_group": "Chest", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                    {"name": "Dumbbell Row", "muscle_group": "Back", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                    {"name": "Lateral Raise", "muscle_group": "Shoulders", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                    {"name": "Bicep Curl", "muscle_group": "Arms", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                    {"name": "Overhead Tricep Extension", "muscle_group": "Arms", "equipment": "Dumbbells", "sets": 3, "reps": 12},
                ],
                sets_and_reps=["3 sets of 12 reps for each exercise"],
                rest_times=["60 seconds between sets", "90 seconds between exercises"],
                notes="Start with a 5-minute warm-up. Use a weight that challenges you by the last rep. Focus on proper form rather than heavy weight."
            )
        ),
        dspy.Example(
            x=WorkoutRequest(
                description="Help me design a chest and triceps workout for hypertrophy",
                gym_equipment=[
                    {"name": "Barbell", "category": "Free Weights", "quantity": 4},
                    {"name": "Bench", "category": "Free Weights", "quantity": 3},
                    {"name": "Dumbbells", "category": "Free Weights", "quantity": 10},
                    {"name": "Cable Machine", "category": "Machines", "quantity": 2},
                    {"name": "Chest Press Machine", "category": "Machines", "quantity": 1}
                ]
            ),
            y=WorkoutPlan(
                title="Chest and Triceps Hypertrophy Workout",
                description="A targeted workout for chest and triceps with emphasis on muscular growth (hypertrophy).",
                exercises=[
                    {"name": "Bench Press", "muscle_group": "Chest", "equipment": "Barbell", "sets": 4, "reps": "8-12"},
                    {"name": "Incline Bench Press", "muscle_group": "Chest", "equipment": "Barbell", "sets": 4, "reps": "8-12"},
                    {"name": "Dumbbell Fly", "muscle_group": "Chest", "equipment": "Dumbbells", "sets": 3, "reps": "10-15"},
                    {"name": "Cable Crossover", "muscle_group": "Chest", "equipment": "Cable Machine", "sets": 3, "reps": "12-15"},
                    {"name": "Skull Crusher", "muscle_group": "Arms", "equipment": "EZ Bar", "sets": 4, "reps": "8-12"},
                    {"name": "Tricep Extension", "muscle_group": "Arms", "equipment": "Cable Machine", "sets": 3, "reps": "12-15"},
                    {"name": "Close-Grip Bench Press", "muscle_group": "Arms", "equipment": "Barbell", "sets": 3, "reps": "8-12"},
                ],
                sets_and_reps=["4 sets of 8-12 reps for compound movements", "3 sets of 10-15 reps for isolation exercises"],
                rest_times=["90-120 seconds between sets for compound exercises", "60 seconds between sets for isolation exercises"],
                notes="For hypertrophy, aim for moderate weight with higher volume. Focus on the mind-muscle connection and consider techniques like drop sets or supersets for advanced stimulus."
            )
        )
    ]
    return examples

# Workout tracking and history
class WorkoutTracker:
    def __init__(self, db_path='data/workouts.db'):
        """Initialize the workout tracker database."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        # Create workouts table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            gym_id INTEGER,
            workout_data TEXT NOT NULL
        )
        ''')
        
        # Create workout_logs table for tracking sets, reps, weights
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY,
            workout_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER,
            weight REAL,
            rest_time INTEGER,
            notes TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workouts (id)
        )
        ''')
        
        self.conn.commit()
    
    def save_workout(self, title, description, gym_id, workout_data):
        """Save a workout plan to the database."""
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert workout data to JSON string
        if isinstance(workout_data, dict):
            workout_data = json.dumps(workout_data)
        
        self.cursor.execute(
            'INSERT INTO workouts (title, description, date, gym_id, workout_data) VALUES (?, ?, ?, ?, ?)',
            (title, description, date, gym_id, workout_data)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def log_exercise_set(self, workout_id, exercise_name, set_number, reps=None, weight=None, rest_time=None, notes=None):
        """Log a completed exercise set."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.cursor.execute(
            'INSERT INTO workout_logs (workout_id, exercise_name, set_number, reps, weight, rest_time, notes, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (workout_id, exercise_name, set_number, reps, weight, rest_time, notes, timestamp)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_workout(self, workout_id):
        """Get a workout by ID."""
        self.cursor.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,))
        workout = self.cursor.fetchone()
        if workout:
            result = dict(workout)
            result['workout_data'] = json.loads(result['workout_data'])
            return result
        return None
    
    def get_recent_workouts(self, limit=10):
        """Get recent workouts."""
        self.cursor.execute('SELECT * FROM workouts ORDER BY date DESC LIMIT ?', (limit,))
        workouts = self.cursor.fetchall()
        return [dict(w) for w in workouts]
    
    def get_workout_logs(self, workout_id):
        """Get all logs for a specific workout."""
        self.cursor.execute('SELECT * FROM workout_logs WHERE workout_id = ? ORDER BY exercise_name, set_number', (workout_id,))
        logs = self.cursor.fetchall()
        return [dict(log) for log in logs]
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

# Flask routes
@app.route('/')
def index():
    """Home page route."""
    # Check if exercise DB exists, if not prompt to create it
    if not os.path.exists('data/exercises.db'):
        return render_template('setup.html')
    
    # Get available gyms
    gym_db = GymDB()
    gyms = gym_db.get_all_gyms()
    gym_db.close()
    
    # Get recent workouts
    tracker = WorkoutTracker()
    recent_workouts = tracker.get_recent_workouts(5)
    tracker.close()
    
    return render_template('index.html', 
                          gyms=gyms, 
                          recent_workouts=recent_workouts,
                          api_key_status={
                              'openai': bool(os.environ.get('OPENAI_API_KEY')),
                              'claude': bool(os.environ.get('ANTHROPIC_API_KEY'))
                          })

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup route for initial database creation."""
    if request.method == 'POST':
        # Create the exercise database
        os.system('python create_exercise_db.py')
        return redirect(url_for('index'))
    
    return render_template('setup.html')

@app.route('/gym/new', methods=['GET', 'POST'])
def new_gym():
    """Create a new gym."""
    if request.method == 'POST':
        gym_name = request.form.get('gym_name')
        location = request.form.get('location', '')
        description = request.form.get('description', '')
        
        # Process equipment data from form
        equipment_data = []
        equipment_names = request.form.getlist('equipment_name[]')
        equipment_categories = request.form.getlist('equipment_category[]')
        equipment_quantities = request.form.getlist('equipment_quantity[]')
        equipment_descriptions = request.form.getlist('equipment_description[]')
        
        for i in range(len(equipment_names)):
            if equipment_names[i].strip():
                equipment_data.append({
                    'name': equipment_names[i],
                    'category': equipment_categories[i],
                    'quantity': int(equipment_quantities[i] or 1),
                    'description': equipment_descriptions[i] if equipment_descriptions[i].strip() else None
                })
        
        # Save to database
        gym_db = GymDB()
        gym_id = gym_db.add_gym(gym_name, location, description)
        
        for item in equipment_data:
            gym_db.add_equipment(
                gym_id=gym_id,
                name=item['name'],
                category=item['category'],
                quantity=item['quantity'],
                description=item['description']
            )
        
        gym_db.close()
        
        return redirect(url_for('index'))
    
    return render_template('new_gym.html')

@app.route('/gym/<int:gym_id>')
def view_gym(gym_id):
    """View a specific gym's details."""
    gym_db = GymDB()
    gym = gym_db.get_gym(gym_id)
    equipment = gym_db.get_gym_equipment(gym_id)
    gym_db.close()
    
    if not gym:
        return "Gym not found", 404
    
    # Group equipment by category
    equipment_by_category = {}
    for item in equipment:
        category = item['category']
        if category not in equipment_by_category:
            equipment_by_category[category] = []
        equipment_by_category[category].append(item)
    
    return render_template('view_gym.html', 
                          gym=gym, 
                          equipment=equipment, 
                          equipment_by_category=equipment_by_category)

@app.route('/workout/new', methods=['GET', 'POST'])
def new_workout():
    """Create a new workout."""
    if request.method == 'POST':
        # Save selected preferences to session
        session['model_provider'] = request.form.get('model_provider', 'openai')
        session['gym_id'] = request.form.get('gym_id')
        workout_description = request.form.get('workout_description', '')
        
        # Get gym equipment if a gym was selected
        gym_equipment = []
        if session['gym_id'] and session['gym_id'] != 'none':
            gym_db = GymDB()
            equipment = gym_db.get_gym_equipment(int(session['gym_id']))
            gym_db.close()
            
            # Format equipment for the model
            gym_equipment = [{
                'name': item['name'],
                'category': item['category'],
                'quantity': item['quantity']
            } for item in equipment]
        
        try:
            # Load exercises
            exercise_db = ExerciseDB()
            all_exercises = exercise_db.get_all_exercises()
            exercise_db.close()
            
            # Configure LLM
            dspy.settings.configure(lm=configure_lm(session['model_provider']))
            
            # Set up the retriever
            retriever = setup_vector_db(all_exercises)
            
            # Create and optimize the workout generator
            workout_generator = WorkoutGenerator(retriever)
            
            # Bootstrap with examples for better performance
            examples = bootstrap_examples()
            teleprompter = dspy.teleprompt.BootstrapFewShot(metric=dspy.evaluate.answer_exact_match)
            optimized_generator = teleprompter.compile(
                workout_generator,
                trainset=examples,
                num_bootstrapped_examples=2
            )
            
            # Generate the workout plan
            workout_plan = optimized_generator(workout_description, gym_equipment)
            
            # Save to session for the confirm step
            session['workout_plan'] = {
                'title': workout_plan.title,
                'description': workout_plan.description,
                'exercises': workout_plan.exercises,
                'sets_and_reps': workout_plan.sets_and_reps,
                'rest_times': workout_plan.rest_times,
                'notes': workout_plan.notes
            }
            
            return redirect(url_for('confirm_workout'))
        
        except Exception as e:
            return render_template('error.html', error=str(e))
    
    # Get available gyms for the form
    gym_db = GymDB()
    gyms = gym_db.get_all_gyms()
    gym_db.close()
    
    return render_template('new_workout.html', 
                          gyms=gyms,
                          api_key_status={
                              'openai': bool(os.environ.get('OPENAI_API_KEY')),
                              'claude': bool(os.environ.get('ANTHROPIC_API_KEY'))
                          })

@app.route('/workout/confirm', methods=['GET', 'POST'])
def confirm_workout():
    """Confirm and save the generated workout."""
    if 'workout_plan' not in session:
        return redirect(url_for('new_workout'))
    
    if request.method == 'POST':
        # Save the workout to the database
        tracker = WorkoutTracker()
        workout_id = tracker.save_workout(
            title=session['workout_plan']['title'],
            description=session['workout_plan']['description'],
            gym_id=session.get('gym_id') if session.get('gym_id') != 'none' else None,
            workout_data=session['workout_plan']
        )
        tracker.close()
        
        # Clear session data
        session.pop('workout_plan', None)
        
        return redirect(url_for('start_workout', workout_id=workout_id))
    
    return render_template('confirm_workout.html', workout=session['workout_plan'])

@app.route('/workout/<int:workout_id>/start')
def start_workout(workout_id):
    """Start a workout tracking session."""
    tracker = WorkoutTracker()
    workout = tracker.get_workout(workout_id)
    tracker.close()
    
    if not workout:
        return "Workout not found", 404
    
    # Format workout data for the template
    workout_data = workout['workout_data']
    
    return render_template('start_workout.html', 
                          workout=workout,
                          workout_data=workout_data)

@app.route('/api/log_set', methods=['POST'])
def log_set():
    """API endpoint to log a completed set."""
    data = request.json
    
    tracker = WorkoutTracker()
    log_id = tracker.log_exercise_set(
        workout_id=data['workout_id'],
        exercise_name=data['exercise_name'],
        set_number=data['set_number'],
        reps=data.get('reps'),
        weight=data.get('weight'),
        rest_time=data.get('rest_time'),
        notes=data.get('notes')
    )
    tracker.close()
    
    return jsonify({'success': True, 'log_id': log_id})

@app.route('/workout/<int:workout_id>/summary')
def workout_summary(workout_id):
    """Display a summary of a completed workout."""
    tracker = WorkoutTracker()
    workout = tracker.get_workout(workout_id)
    logs = tracker.get_workout_logs(workout_id)
    tracker.close()
    
    if not workout:
        return "Workout not found", 404
    
    # Get gym info if applicable
    gym = None
    if workout['gym_id']:
        gym_db = GymDB()
        gym = gym_db.get_gym(workout['gym_id'])
        gym_db.close()
    
    # Group logs by exercise
    logs_by_exercise = {}
    for log in logs:
        if log['exercise_name'] not in logs_by_exercise:
            logs_by_exercise[log['exercise_name']] = []
        logs_by_exercise[log['exercise_name']].append(log)
    
    return render_template('workout_summary.html', 
                          workout=workout,
                          logs_by_exercise=logs_by_exercise,
                          gym=gym)

@app.route('/workouts')
def workout_history():
    """View workout history."""
    tracker = WorkoutTracker()
    workouts = tracker.get_recent_workouts(50)  # Get up to 50 recent workouts
    tracker.close()
    
    return render_template('workout_history.html', workouts=workouts)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the Workout Vibe web application")
    parser.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Check if exercise database exists, create if not
    if not os.path.exists('data/exercises.db'):
        print("Exercise database not found. Creating it now...")
        os.system('python create_exercise_db.py')
    
    app.run(host='0.0.0.0', port=args.port, debug=args.debug)