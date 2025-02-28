import sqlite3
import os
import argparse
from typing import List, Dict, Optional
import json

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

def display_gym_summary(gym_db: GymDB, gym_id: int):
    """Display a summary of the gym and its equipment."""
    gym = gym_db.get_gym(gym_id)
    if not gym:
        print("Gym not found!")
        return
    
    equipment = gym_db.get_gym_equipment(gym_id)
    
    print(f"\n{'='*60}")
    print(f"GYM: {gym['name']}")
    if gym['location']:
        print(f"Location: {gym['location']}")
    if gym['description']:
        print(f"Description: {gym['description']}")
    print(f"{'='*60}")
    
    # Group equipment by category
    equipment_by_category = {}
    for item in equipment:
        category = item['category']
        if category not in equipment_by_category:
            equipment_by_category[category] = []
        equipment_by_category[category].append(item)
    
    # Display equipment by category
    if equipment:
        print("\nEQUIPMENT AVAILABLE:")
        for category, items in equipment_by_category.items():
            print(f"\n{category.upper()}:")
            for item in items:
                qty_str = f" (x{item['quantity']})" if item['quantity'] > 1 else ""
                print(f"  - {item['name']}{qty_str}")
                if item['description']:
                    print(f"    {item['description']}")
    else:
        print("\nNo equipment recorded for this gym yet.")
    
    print(f"\n{'='*60}")

def interactive_onboarding() -> Dict:
    """Interactive prompt for gym onboarding."""
    print("\n=== GYM ONBOARDING ===")
    
    # Collect gym information
    gym_info = {}
    gym_info['name'] = input("Gym Name: ")
    gym_info['location'] = input("Location (optional, press Enter to skip): ").strip() or None
    gym_info['description'] = input("Brief Description (optional, press Enter to skip): ").strip() or None
    
    # Collect equipment information
    gym_info['equipment'] = []
    
    print("\nNow let's add equipment to your gym.")
    print("You'll be asked to add equipment by category.")
    print("Common categories include: Cardio, Free Weights, Machines, Functional, etc.")
    
    adding_equipment = True
    while adding_equipment:
        print("\n--- Add Equipment Category ---")
        category = input("Equipment Category (e.g., Cardio, Free Weights, Machines): ")
        
        adding_to_category = True
        while adding_to_category:
            item = {}
            item['category'] = category
            item['name'] = input(f"Equipment Name in {category} category: ")
            
            qty_input = input("Quantity (default is 1, press Enter for default): ").strip()
            item['quantity'] = int(qty_input) if qty_input.isdigit() and int(qty_input) > 0 else 1
            
            item['description'] = input("Description (optional, press Enter to skip): ").strip() or None
            
            gym_info['equipment'].append(item)
            
            add_more = input(f"Add more equipment to {category}? (y/n): ").lower()
            adding_to_category = add_more == 'y'
        
        add_category = input("Add another equipment category? (y/n): ").lower()
        adding_equipment = add_category == 'y'
    
    return gym_info

def process_text_description(description: str) -> Dict:
    """
    This is a placeholder for NLP processing of a gym description.
    In a real application, this would use an LLM to extract equipment details.
    """
    print("\nProcessing text description... (this is a demo without actual NLP)")
    print("In a real application, this would use an LLM to extract equipment from your description.")
    
    # This is just a mock function that returns some demo data
    # In a real app, this would use NLP/LLM to extract equipment from the text
    
    gym_info = {
        'name': 'Extracted Gym Name',
        'location': None,
        'description': description[:50] + '...' if len(description) > 50 else description,
        'equipment': [
            {'category': 'Cardio', 'name': 'Treadmill', 'quantity': 3, 'description': None},
            {'category': 'Cardio', 'name': 'Exercise Bike', 'quantity': 2, 'description': None},
            {'category': 'Free Weights', 'name': 'Dumbbells', 'quantity': 10, 'description': 'Pairs from 5-50 lbs'},
            {'category': 'Machines', 'name': 'Leg Press', 'quantity': 1, 'description': None}
        ]
    }
    
    print("\nExtracted the following equipment (mock data):")
    for item in gym_info['equipment']:
        qty_str = f" (x{item['quantity']})" if item['quantity'] > 1 else ""
        print(f"  - {item['name']}{qty_str} ({item['category']})")
    
    # Ask user to confirm this is correct
    confirm = input("\nIs this information correct? In a real app, you would be able to edit it. (y/n): ").lower()
    if confirm == 'y':
        return gym_info
    else:
        print("Please try the interactive onboarding instead.")
        return interactive_onboarding()

def save_to_json(gym_info: Dict, filename: str):
    """Save gym information to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(gym_info, f, indent=2)
    print(f"\nGym information saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Onboard a new gym by describing available equipment")
    parser.add_argument('--interactive', action='store_true', help='Use interactive prompt mode')
    parser.add_argument('--description', type=str, help='Text description of gym equipment')
    parser.add_argument('--save-json', type=str, help='Save gym info to a JSON file')
    args = parser.parse_args()
    
    # Determine which mode to use
    if args.interactive:
        gym_info = interactive_onboarding()
    elif args.description:
        gym_info = process_text_description(args.description)
    else:
        print("Please specify either --interactive or --description")
        parser.print_help()
        return
    
    # Save to database
    gym_db = GymDB()
    
    # Add gym
    gym_id = gym_db.add_gym(
        name=gym_info['name'],
        location=gym_info['location'],
        description=gym_info['description']
    )
    
    # Add equipment
    for item in gym_info['equipment']:
        gym_db.add_equipment(
            gym_id=gym_id,
            name=item['name'],
            category=item['category'],
            quantity=item['quantity'],
            description=item.get('description')
        )
    
    # Display summary
    display_gym_summary(gym_db, gym_id)
    
    # Save to JSON if requested
    if args.save_json:
        save_to_json(gym_info, args.save_json)
    
    # Close database connection
    gym_db.close()
    
    print("\nOnboarding complete! Your gym has been added to the database.")

if __name__ == "__main__":
    main()