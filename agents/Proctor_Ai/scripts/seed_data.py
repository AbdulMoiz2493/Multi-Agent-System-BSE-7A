"""
Seed script to populate the database with test data
Run this after creating the database and running migrations
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.study_session import StudySession
from app.models.course import Course
from app.models.reminder import Reminder, ReminderStatus


def seed_database():
    """Seed the database with test data"""
    db = SessionLocal()
    
    try:
        # Create test users
        users = []
        test_users_data = [
            {"email": "student1@test.com", "full_name": "John Doe", "password": "password123"},
            {"email": "student2@test.com", "full_name": "Jane Smith", "password": "password123"},
            {"email": "student3@test.com", "full_name": "Bob Johnson", "password": "password123"},
        ]
        
        for user_data in test_users_data:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                print(f"User {user_data['email']} already exists, skipping...")
                users.append(existing_user)
                continue
            
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"]
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        
        # Refresh users to get IDs
        for user in users:
            db.refresh(user)
        
        print(f"Created {len(users)} users")
        
        # Create courses for users
        courses_data = [
            "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
            "English", "History", "Geography"
        ]
        
        for user in users:
            user_courses = random.sample(courses_data, k=random.randint(3, 5))
            for course_name in user_courses:
                course = Course(
                    user_id=user.id,
                    name=course_name,
                    importance_level=random.randint(1, 5)
                )
                db.add(course)
        
        db.commit()
        print("Created courses")
        
        # Create study sessions (last 60 days)
        session_count = 0
        for user in users:
            # Generate sessions for the last 60 days
            for day_offset in range(60):
                session_date = datetime.utcnow() - timedelta(days=day_offset)
                
                # Randomly create sessions (about 40% chance per day)
                if random.random() < 0.4:
                    # Get user's courses
                    user_courses = db.query(Course).filter(Course.user_id == user.id).all()
                    if user_courses:
                        course = random.choice(user_courses)
                        
                        session = StudySession(
                            user_id=user.id,
                            course_name=course.name,
                            duration_minutes=random.randint(30, 180),
                            session_date=session_date,
                            notes=f"Study session for {course.name}" if random.random() < 0.3 else None
                        )
                        db.add(session)
                        session_count += 1
        
        db.commit()
        print(f"Created {session_count} study sessions")
        
        # Create some reminders
        reminder_count = 0
        for user in users:
            for _ in range(random.randint(2, 5)):
                scheduled_time = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                reminder = Reminder(
                    user_id=user.id,
                    scheduled_time=scheduled_time,
                    message=f"Don't forget to study {random.choice(courses_data)} today!",
                    status=random.choice(list(ReminderStatus))
                )
                db.add(reminder)
                reminder_count += 1
        
        db.commit()
        print(f"Created {reminder_count} reminders")
        
        print("\n✅ Database seeded successfully!")
        print("\nTest users:")
        for user in users:
            print(f"  - {user.email} / password123")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

