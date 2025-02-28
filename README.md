# Workout Vibe Generator

A Flask web application that uses RAG (Retrieval Augmented Generation) with DSPy to create personalized workout plans based on a database of exercises. The app allows you to track workouts, record sets, reps and weights, and maintain a workout history.

![Workout Vibe](https://github.com/anthropics/workout-vibe-code/raw/main/screenshot.png)

## Features

- Web-based UI for workout planning and tracking
- SQLite databases for exercises, gyms, and workout history
- RAG-based workout plan generation
- Support for both OpenAI and Anthropic Claude models
- Gym equipment tracking for personalized workouts
- Rest timer with sound notifications
- Workout history and performance tracking
- Mobile-friendly responsive design

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/workout-vibe-code.git
cd workout-vibe-code
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API keys as environment variables:
```bash
# For OpenAI
export OPENAI_API_KEY=your_openai_api_key

# For Claude
export ANTHROPIC_API_KEY=your_anthropic_api_key
```

4. Start the Flask application:
```bash
python app.py
```

The application will automatically create the exercise database on first run if it doesn't exist.

5. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### Creating Workouts

1. On the home page, click "Create New Workout"
2. Select your preferred AI model (OpenAI or Claude)
3. Choose a gym (optional) to personalize equipment selection
4. Describe your desired workout (e.g., "Quick 30-minute full body workout for a beginner")
5. Review the generated workout plan and click "Start Workout"

### Tracking Workouts

During a workout:
- Use the rest timer to track rest periods between sets
- Record weights, reps, and optional notes for each set
- Navigate between exercises with the next/previous buttons
- Click "Complete Set" after finishing each set
- Use "Finish Workout" when done to view your workout summary

### Managing Gyms

1. Click "Add Gym" to create a new gym profile
2. Enter gym details and available equipment
3. View your gyms on the home page
4. Use gym profiles when creating workouts to ensure exercises match available equipment

### Viewing History

Access your workout history from the "History" link in the navigation menu to:
- See all completed workouts
- View detailed performance for each workout
- Repeat previous workouts

## Development

The application consists of several components:

- `app.py` - Main Flask application
- `create_exercise_db.py` - Script to initialize the exercise database
- `templates/` - HTML templates for the web interface
- `requirements.txt` - Python dependencies

### Database Structure

- `exercises.db` - Contains exercise definitions
- `gyms.db` - Stores gym profiles and equipment
- `workouts.db` - Records workout history and performance

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.