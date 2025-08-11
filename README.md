# Task Manager AI

A simple AI-powered task manager web application built with Flask and MongoDB.

## Features

- User authentication (signup, login, logout)
- Task management (create, view, update, delete tasks)
- Routines, reminders, habits, and events
- Responsive UI with Tailwind CSS
- Email notifications (optional)
- AI-powered suggestions (optional, requires OpenAI API key)

## Requirements

- Python 3.8+
- MongoDB
- (Optional) OpenAI API key for AI features

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/YOUR-USERNAME/task-manager-ai.git
   cd task-manager-ai/backend
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy `config.py.example` to `config.py` and set your secrets and API keys.

5. **Start MongoDB** (if not already running):
   ```sh
   mongod
   ```

6. **Run the Flask app:**
   ```sh
   flask run
   ```

7. **Open your browser:**
   - Visit [http://localhost:5000](http://localhost:5000)

## Project Structure

```
backend/
│
├── app.py
├── config.py
├── requirements.txt
├── templates/
│   ├── login.html
│   ├── signup.html
│   └── ...
└── ...
```

## License

MIT