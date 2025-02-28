import sqlite3
import argparse
import dspy
from dspy.retrieve import VectorDBRetriever
from dspy.teleprompt import BootstrapFewShot
import os
from typing import List, Dict, Any

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

class Exercise(dspy.Signature):
    """Information about an exercise."""
    id: int
    name: str
    muscle_group: str
    equipment: str

class WorkoutRequest(dspy.Signature):
    """A request for a workout."""
    description: str

class WorkoutPlan(dspy.Signature):
    """A workout plan with exercises."""
    title: str
    description: str
    exercises: List[Dict[str, Any]]
    sets_and_reps: List[str]
    notes: str

class WorkoutGenerator(dspy.Module):
    """Module to generate a workout plan based on user input."""
    
    def __init__(self, retriever):
        super().__init__()
        self.retriever = retriever
        self.generate_workout = dspy.ChainOfThought(
            WorkoutRequest, WorkoutPlan
        )
    
    def forward(self, description: str) -> WorkoutPlan:
        """Generate a workout plan based on user description."""
        # Retrieve relevant exercises
        exercises = self.retriever(description).passages
        
        # Generate the workout plan
        workout_request = WorkoutRequest(description=description)
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
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        return dspy.Anthropic(model="claude-3-sonnet-20240229", api_key=api_key)
    else:
        # Default to OpenAI
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        return dspy.OpenAI(model="gpt-4-turbo", api_key=api_key)

def bootstrap_examples():
    """Create examples for bootstrapping."""
    examples = [
        dspy.Example(
            x=WorkoutRequest(description="I want a quick full body workout with dumbbells"),
            y=WorkoutPlan(
                title="Quick Full Body Dumbbell Workout",
                description="A time-efficient full body workout using only dumbbells, perfect for building strength and endurance.",
                exercises=[
                    {"name": "Dumbbell Squat", "muscle_group": "Legs", "equipment": "Dumbbells"},
                    {"name": "Dumbbell Bench Press", "muscle_group": "Chest", "equipment": "Dumbbells"},
                    {"name": "Dumbbell Row", "muscle_group": "Back", "equipment": "Dumbbells"},
                    {"name": "Lateral Raise", "muscle_group": "Shoulders", "equipment": "Dumbbells"},
                    {"name": "Bicep Curl", "muscle_group": "Arms", "equipment": "Dumbbells"},
                    {"name": "Overhead Tricep Extension", "muscle_group": "Arms", "equipment": "Dumbbells"},
                ],
                sets_and_reps=["3 sets of 12 reps for each exercise", "Rest 60 seconds between sets", "Complete as a circuit for additional cardio benefit"],
                notes="Start with a 5-minute warm-up. Use a weight that challenges you by the last rep. Focus on proper form rather than heavy weight."
            )
        ),
        dspy.Example(
            x=WorkoutRequest(description="Help me design a chest and triceps workout for hypertrophy"),
            y=WorkoutPlan(
                title="Chest and Triceps Hypertrophy Workout",
                description="A targeted workout for chest and triceps with emphasis on muscular growth (hypertrophy).",
                exercises=[
                    {"name": "Bench Press", "muscle_group": "Chest", "equipment": "Barbell"},
                    {"name": "Incline Bench Press", "muscle_group": "Chest", "equipment": "Barbell"},
                    {"name": "Dumbbell Fly", "muscle_group": "Chest", "equipment": "Dumbbells"},
                    {"name": "Cable Crossover", "muscle_group": "Chest", "equipment": "Cable Machine"},
                    {"name": "Skull Crusher", "muscle_group": "Arms", "equipment": "EZ Bar"},
                    {"name": "Tricep Extension", "muscle_group": "Arms", "equipment": "Cable Machine"},
                    {"name": "Close-Grip Bench Press", "muscle_group": "Arms", "equipment": "Barbell"},
                ],
                sets_and_reps=["4 sets of 8-12 reps for each exercise", "Rest 90-120 seconds between sets", "Increase weight once you can complete 12 reps with good form"],
                notes="For hypertrophy, aim for moderate weight with higher volume. Focus on the mind-muscle connection and consider techniques like drop sets or supersets for advanced stimulus."
            )
        )
    ]
    return examples

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate workouts using LLMs and RAG")
    parser.add_argument('--provider', type=str, default='openai', choices=['openai', 'claude'],
                        help='LLM provider to use (openai or claude)')
    args = parser.parse_args()
    
    # Load exercises from the database
    exercise_db = ExerciseDB()
    exercises = exercise_db.get_all_exercises()
    
    # Configure the language model
    dspy.settings.configure(lm=configure_lm(args.provider))
    
    # Set up the retriever
    retriever = setup_vector_db(exercises)
    
    # Create and optimize the workout generator
    workout_generator = WorkoutGenerator(retriever)
    
    # Bootstrap with examples for better performance
    examples = bootstrap_examples()
    teleprompter = BootstrapFewShot(metric=dspy.evaluate.answer_exact_match)
    workout_generator = teleprompter.compile(
        workout_generator,
        trainset=examples,
        num_bootstrapped_examples=2
    )
    
    # Get user input
    print("\n=== Workout Generator ===")
    print("Tell me what kind of workout you want, and I'll create a plan for you!")
    user_input = input("What workout are you looking for today? ")
    
    # Generate the workout plan
    try:
        workout_plan = workout_generator(user_input)
        
        # Display the workout plan
        print("\n" + "="*50)
        print(f"🏋️ {workout_plan.title} 🏋️")
        print("="*50)
        print(f"\n📝 Description: {workout_plan.description}\n")
        
        print("📋 Exercises:")
        for i, exercise in enumerate(workout_plan.exercises, 1):
            print(f"  {i}. {exercise['name']} ({exercise['muscle_group']} - {exercise['equipment']})")
        
        print("\n⚙️ Sets & Reps:")
        for instruction in workout_plan.sets_and_reps:
            print(f"  • {instruction}")
        
        print(f"\n📌 Notes: {workout_plan.notes}")
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"Error generating workout plan: {e}")
    
    # Close database connection
    exercise_db.close()

if __name__ == "__main__":
    main()