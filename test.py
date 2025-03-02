#!/usr/bin/env python
# coding: utf-8

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Basic testing script for database functionality

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

# Test functions
def test_exercise_db():
    print("Testing ExerciseDB...")
    try:
        db = ExerciseDB()
        all_exercises = db.get_all_exercises()
        print(f"Found {len(all_exercises)} exercises")
        
        if all_exercises:
            print("Sample exercise:", all_exercises[0])
            
            # Get unique muscle groups
            muscle_groups = set(ex['muscle_group'] for ex in all_exercises)
            print(f"Available muscle groups: {', '.join(muscle_groups)}")
            
            # Get unique equipment
            equipment_types = set(ex['equipment'] for ex in all_exercises)
            print(f"Available equipment: {', '.join(equipment_types)}")
            
            # Test filtering
            if muscle_groups:
                first_group = list(muscle_groups)[0]
                exercises_by_group = db.get_exercises_by_muscle_group(first_group)
                print(f"Found {len(exercises_by_group)} exercises for {first_group}")
            
            if equipment_types:
                first_equip = list(equipment_types)[0]
                exercises_by_equip = db.get_exercises_by_equipment(first_equip)
                print(f"Found {len(exercises_by_equip)} exercises for {first_equip}")
        else:
            print("No exercises found in the database.")
        
        db.close()
        print("ExerciseDB test complete")
    except Exception as e:
        print(f"Error testing ExerciseDB: {e}")

def test_gym_db():
    print("\nTesting GymDB...")
    try:
        db = GymDB()
        
        # Get all gyms
        gyms = db.get_all_gyms()
        print(f"Found {len(gyms)} gyms")
        
        if not gyms:
            # If no gyms, create a test gym
            print("Creating a test gym...")
            gym_id = db.add_gym("Test Gym", "Test Location", "A test gym for debugging")
            print(f"Created gym with ID {gym_id}")
            
            # Add some equipment
            equipment_list = [
                ("Barbell", "Free Weights", 5),
                ("Dumbbells", "Free Weights", 10),
                ("Squat Rack", "Racks", 2),
                ("Treadmill", "Cardio", 3),
                ("Bench Press", "Benches", 2)
            ]
            
            for name, category, quantity in equipment_list:
                equip_id = db.add_equipment(gym_id, name, category, quantity)
                print(f"Added {name} (ID: {equip_id})")
            
            # Get the gym again
            gyms = db.get_all_gyms()
        
        # Print gym info
        for gym in gyms:
            print(f"Gym: {gym['name']} (ID: {gym['id']})")
            equipment = db.get_gym_equipment(gym['id'])
            print(f"  Equipment count: {len(equipment)}")
            
            # Show some equipment
            for i, equip in enumerate(equipment[:5], 1):
                print(f"  {i}. {equip['name']} ({equip['category']}) - Qty: {equip['quantity']}")
            
            if len(equipment) > 5:
                print(f"  ... and {len(equipment) - 5} more items")
        
        db.close()
        print("GymDB test complete")
    except Exception as e:
        print(f"Error testing GymDB: {e}")

# Main test function
if __name__ == "__main__":
    print("Starting database tests...")
    
    # First check if the data directory exists
    if not os.path.exists("data"):
        print("Creating data directory...")
        os.makedirs("data", exist_ok=True)
    
    # Test the exercise database
    test_exercise_db()
    
    # Test the gym database
    test_gym_db()
    
    print("\nAll tests complete!")

