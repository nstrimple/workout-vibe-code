import sqlite3
import os

# Create database directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Connect to SQLite database (will be created if it doesn't exist)
conn = sqlite3.connect('data/exercises.db')
cursor = conn.cursor()

# Create exercises table
cursor.execute('''
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    muscle_group TEXT NOT NULL,
    equipment TEXT
)
''')

# Sample exercises data by muscle group
exercises = [
    # Chest
    ('Bench Press', 'Chest', 'Barbell'),
    ('Incline Bench Press', 'Chest', 'Barbell'),
    ('Decline Bench Press', 'Chest', 'Barbell'),
    ('Dumbbell Fly', 'Chest', 'Dumbbells'),
    ('Push-Up', 'Chest', 'Bodyweight'),
    ('Cable Crossover', 'Chest', 'Cable Machine'),
    ('Chest Dip', 'Chest', 'Parallel Bars'),
    ('Landmine Press', 'Chest', 'Barbell'),
    ('Machine Chest Press', 'Chest', 'Machine'),
    ('Svend Press', 'Chest', 'Weight Plate'),
    
    # Back
    ('Deadlift', 'Back', 'Barbell'),
    ('Pull-Up', 'Back', 'Bodyweight'),
    ('Bent Over Row', 'Back', 'Barbell'),
    ('Lat Pulldown', 'Back', 'Cable Machine'),
    ('T-Bar Row', 'Back', 'T-Bar'),
    ('Single-Arm Dumbbell Row', 'Back', 'Dumbbell'),
    ('Seated Cable Row', 'Back', 'Cable Machine'),
    ('Face Pull', 'Back', 'Cable Machine'),
    ('Hyperextension', 'Back', 'Hyperextension Bench'),
    ('Rack Pull', 'Back', 'Barbell'),
    
    # Legs
    ('Squat', 'Legs', 'Barbell'),
    ('Leg Press', 'Legs', 'Machine'),
    ('Lunge', 'Legs', 'Dumbbells'),
    ('Romanian Deadlift', 'Legs', 'Barbell'),
    ('Leg Extension', 'Legs', 'Machine'),
    ('Leg Curl', 'Legs', 'Machine'),
    ('Calf Raise', 'Legs', 'Machine'),
    ('Hack Squat', 'Legs', 'Machine'),
    ('Bulgarian Split Squat', 'Legs', 'Dumbbells'),
    ('Glute Bridge', 'Legs', 'Barbell'),
    
    # Shoulders
    ('Overhead Press', 'Shoulders', 'Barbell'),
    ('Lateral Raise', 'Shoulders', 'Dumbbells'),
    ('Front Raise', 'Shoulders', 'Dumbbells'),
    ('Reverse Fly', 'Shoulders', 'Dumbbells'),
    ('Arnold Press', 'Shoulders', 'Dumbbells'),
    ('Upright Row', 'Shoulders', 'Barbell'),
    ('Face Pull', 'Shoulders', 'Cable Machine'),
    ('Shoulder Press', 'Shoulders', 'Machine'),
    ('Push Press', 'Shoulders', 'Barbell'),
    ('Shrug', 'Shoulders', 'Dumbbells'),
    
    # Arms
    ('Bicep Curl', 'Arms', 'Barbell'),
    ('Hammer Curl', 'Arms', 'Dumbbells'),
    ('Tricep Extension', 'Arms', 'Cable Machine'),
    ('Skull Crusher', 'Arms', 'EZ Bar'),
    ('Concentration Curl', 'Arms', 'Dumbbell'),
    ('Close-Grip Bench Press', 'Arms', 'Barbell'),
    ('Tricep Dip', 'Arms', 'Parallel Bars'),
    ('Preacher Curl', 'Arms', 'EZ Bar'),
    ('Cable Curl', 'Arms', 'Cable Machine'),
    ('Overhead Tricep Extension', 'Arms', 'Dumbbell'),
    
    # Core
    ('Crunch', 'Core', 'Bodyweight'),
    ('Plank', 'Core', 'Bodyweight'),
    ('Russian Twist', 'Core', 'Weight Plate'),
    ('Leg Raise', 'Core', 'Bodyweight'),
    ('Ab Rollout', 'Core', 'Ab Wheel'),
    ('Mountain Climber', 'Core', 'Bodyweight'),
    ('Bicycle Crunch', 'Core', 'Bodyweight'),
    ('Side Plank', 'Core', 'Bodyweight'),
    ('Cable Woodchopper', 'Core', 'Cable Machine'),
    ('Hanging Leg Raise', 'Core', 'Pull-Up Bar')
]

# Insert sample data
cursor.executemany('INSERT INTO exercises (name, muscle_group, equipment) VALUES (?, ?, ?)', exercises)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database created successfully with sample exercises!")
print(f"Total exercises added: {len(exercises)}")