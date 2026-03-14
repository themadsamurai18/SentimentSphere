from app import app, init_db

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run()
