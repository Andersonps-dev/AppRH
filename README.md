# Flask Login App

This project is a simple Flask application that provides user authentication using a login form. It utilizes SQLite as the database to store user credentials, including username, password, and company.

## Project Structure

```
flask-login-app
├── app.py               # Main application file
├── templates            # Directory for HTML templates
│   └── login.html      # Login page template
├── static              # Directory for static files
│   └── style.css       # CSS styles for the login page
├── database.db         # SQLite database file
├── requirements.txt     # Project dependencies
└── README.md           # Project documentation
```

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd flask-login-app
   ```

2. **Create a virtual environment**:
   ```
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - On Windows:
     ```
     .venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source .venv/bin/activate
     ```

4. **Install the required dependencies**:
   ```
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```
   python app.py
   ```

6. **Access the application**:
   Open your web browser and go to `http://127.0.0.1:5000` to view the login page.

## Usage

- Enter your username, password, and company in the login form.
- Upon successful authentication, you will be granted access to the application.

## Note

This project does not include user registration functionality. It is assumed that user credentials are already stored in the `database.db` file.