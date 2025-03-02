import sqlite3
import argparse
import dspy
from dspy.teleprompt import BootstrapFewShot
import os
import re
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
    
    def search_exercises(self, query):
        """Search exercises by name, muscle group, or equipment."""
        # Use LIKE for partial matching
        search_term = f'%{query}%'
        self.cursor.execute("""
            SELECT * FROM exercises 
            WHERE name LIKE ? 
            OR muscle_group LIKE ? 
            OR equipment LIKE ?
        """, (search_term, search_term, search_term))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def find_exercises_for_workout(self, description):
        """Find exercises that match the workout description."""
        # Extract potential muscle groups and equipment from description
        muscle_groups = self.extract_muscle_groups(description)
        equipment = self.extract_equipment(description)
        
        # Build query based on extracted terms
        params = []
        conditions = []
        
        if muscle_groups:
            placeholders = ', '.join(['?'] * len(muscle_groups))
            conditions.append(f"muscle_group IN ({placeholders})")
            params.extend(muscle_groups)
        
        if equipment:
            placeholders = ', '.join(['?'] * len(equipment))
            conditions.append(f"equipment IN ({placeholders})")
            params.extend(equipment)
        
        # If no specific conditions, return a diverse set
        if not conditions:
            # Get a variety of exercises across different muscle groups
            return self.get_diverse_exercise_set()
        
        # Execute the query
        query = f"SELECT * FROM exercises WHERE {' OR '.join(conditions)}"
        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_diverse_exercise_set(self, limit_per_group=3):
        """Get a diverse set of exercises covering different muscle groups."""
        # Get distinct muscle groups
        self.cursor.execute("SELECT DISTINCT muscle_group FROM exercises")
        muscle_groups = [row[0] for row in self.cursor.fetchall()]
        
        # Get exercises for each muscle group
        results = []
        for group in muscle_groups:
            self.cursor.execute(
                "SELECT * FROM exercises WHERE muscle_group = ? LIMIT ?", 
                (group, limit_per_group)
            )
            results.extend([dict(row) for row in self.cursor.fetchall()])
        
        return results
    
    def extract_muscle_groups(self, description):
        """Extract potential muscle groups from a description."""
        common_muscle_groups = [
            "Chest", "Back", "Legs", "Shoulders", "Arms", 
            "Biceps", "Triceps", "Abs", "Core", "Glutes", 
            "Quads", "Hamstrings", "Calves"
        ]
        
        # Find mentioned muscle groups
        found_groups = []
        description_lower = description.lower()
        
        for group in common_muscle_groups:
            if group.lower() in description_lower:
                found_groups.append(group)
        
        return found_groups
    
    def extract_equipment(self, description):
        """Extract potential equipment from a description."""
        common_equipment = [
            "Barbell", "Dumbbells", "Machine", "Cable", "Bodyweight",
            "Kettlebell", "Resistance Band", "Smith Machine", "TRX"
        ]
        
        # Find mentioned equipment
        found_equipment = []
        description_lower = description.lower()
        
        for equip in common_equipment:
            if equip.lower() in description_lower:
                found_equipment.append(equip)
        
        return found_equipment
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

class Exercise(dspy.Signature):
    """Information about an exercise."""
    id: int = dspy.OutputField()
    name: str = dspy.OutputField()
    muscle_group: str = dspy.OutputField()
    equipment: str = dspy.OutputField()

class WorkoutRequest(dspy.Signature):
    """A request for a workout."""
    description: str = dspy.InputField()
    available_exercises: List[Dict[str, Any]] = dspy.InputField()

class WorkoutPlan(dspy.Signature):
    """A workout plan with exercises."""
    title: str = dspy.OutputField()
    description: str = dspy.OutputField()
    exercises: List[Dict[str, Any]] = dspy.OutputField()
    sets_and_reps: List[str] = dspy.OutputField()
    notes: str = dspy.OutputField()

class WorkoutGenerator(dspy.Module):
    """Module to generate a workout plan based on user input."""
    
    def __init__(self):
        super().__init__()
        self.generate_workout = dspy.ChainOfThought(
            WorkoutRequest, WorkoutPlan
        )
        self.exercise_db = ExerciseDB()
    
    def forward(self, description: str) -> WorkoutPlan:
        """Generate a workout plan based on user description."""
        # Find relevant exercises using direct database query
        relevant_exercises = self.exercise_db.find_exercises_for_workout(description)
        
        # Generate the workout plan
        workout_request = WorkoutRequest(
            description=description,
            available_exercises=relevant_exercises
        )
        workout_plan = self.generate_workout(workout_request)
        
        return workout_plan

def configure_lm(provider='openai'):
    """Configure the language model based on provider."""
    if provider.lower() == 'claude':
        # Set up Anthropic Claude
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        return dspy.LM('anthropic/claude-3-opus-20240229', api_key=api_key)
    else:
        # Default to OpenAI
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # In dspy v2.0.0+, use ChatOpenAI instead of OpenAI
        try:
            return dspy.LM('openai/gpt-4o-mini', api_key=api_key)
        except AttributeError:
            # Fallback for compatibility with different dspy versions
            import openai
            openai.api_key = api_key
            return dspy.LM('openai/gpt-4o-mini', api_key=api_key)

def bootstrap_examples():
    """Create examples for bootstrapping."""
    examples = [
        dspy.Example(
            x=WorkoutRequest(
                description="I want a quick full body workout with dumbbells",
                available_exercises=[
                    {"id": 1, "name": "Dumbbell Squat", "muscle_group": "Legs", "equipment": "Dumbbells"},
                    {"id": 2, "name": "Dumbbell Bench Press", "muscle_group": "Chest", "equipment": "Dumbbells"},
                    {"id": 3, "name": "Dumbbell Row", "muscle_group": "Back", "equipment": "Dumbbells"},
                    {"id": 4, "name": "Lateral Raise", "muscle_group": "Shoulders", "equipment": "Dumbbells"},
                    {"id": 5, "name": "Bicep Curl", "muscle_group": "Arms", "equipment": "Dumbbells"},
                    {"id": 6, "name": "Overhead Tricep Extension", "muscle_group": "Arms", "equipment": "Dumbbells"},
                ]
            ),
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
            x=WorkoutRequest(
                description="Help me design a chest and triceps workout for hypertrophy",
                available_exercises=[
                    {"id": 1, "name": "Bench Press", "muscle_group": "Chest", "equipment": "Barbell"},
                    {"id": 2, "name": "Incline Bench Press", "muscle_group": "Chest", "equipment": "Barbell"},
                    {"id": 3, "name": "Dumbbell Fly", "muscle_group": "Chest", "equipment": "Dumbbells"},
                    {"id": 4, "name": "Cable Crossover", "muscle_group": "Chest", "equipment": "Cable Machine"},
                    {"id": 5, "name": "Skull Crusher", "muscle_group": "Arms", "equipment": "EZ Bar"},
                    {"id": 6, "name": "Tricep Extension", "muscle_group": "Arms", "equipment": "Cable Machine"},
                    {"id": 7, "name": "Close-Grip Bench Press", "muscle_group": "Arms", "equipment": "Barbell"},
                ]
            ),
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
    parser = argparse.ArgumentParser(description="Generate workouts using LLMs and direct database queries")
    parser.add_argument('--provider', type=str, default='openai', choices=['openai', 'claude'],
                        help='LLM provider to use (openai or claude)')
    args = parser.parse_args()
    
    # Configure the language model
    dspy.settings.configure(lm=configure_lm(args.provider))
    
    # Create the workout generator
    workout_generator = WorkoutGenerator()
    
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

if __name__ == "__main__":
    main()