import os
os.environ['FLASK_APP'] = ''  # Disable Flask auto-run

from app import create_app, db

app = create_app()

with app.app_context():
    try:
        # Test database connection
        db.engine.execute(db.text('SELECT 1'))
        print("✅ PostgreSQL connection successful!")

        # Check if tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables in database: {tables}")

        if tables:
            print("✅ Database tables are created!")
        else:
            print("⚠️  No tables found. You may need to run migrations.")

    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("💡 Make sure PostgreSQL is running and the database exists.")