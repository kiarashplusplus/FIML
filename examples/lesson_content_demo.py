"""
Lesson Content Integration Example
Demonstrates how to use the educational lessons with the LessonContentEngine
"""

import asyncio
from pathlib import Path
from fiml.bot.education.lesson_engine import LessonContentEngine
from fiml.bot.education.quiz_system import QuizSystem
from fiml.bot.education.gamification import GamificationEngine

async def main():
    """Demo lesson loading and rendering"""
    
    # Initialize engines
    lessons_dir = Path("fiml/bot/content/lessons")
    lesson_engine = LessonContentEngine(lessons_dir)
    quiz_system = QuizSystem()
    gamification = GamificationEngine()
    
    print("=" * 70)
    print("FIML Educational Bot - Lesson Content Demo")
    print("=" * 70)
    
    # List available lessons
    print("\n📚 Available Lessons:")
    lessons = list(lessons_dir.glob("*.yaml"))
    for i, lesson_file in enumerate(sorted(lessons), 1):
        print(f"  {i}. {lesson_file.stem.replace('_', ' ').title()}")
    
    print(f"\n✅ Total: {len(lessons)} lessons loaded")
    
    # Load and display first lesson
    print("\n" + "=" * 70)
    print("Sample Lesson: Understanding Stock Prices")
    print("=" * 70)
    
    try:
        lesson = await lesson_engine.load_lesson("stock_basics_001")
        
        print(f"\n📖 Title: {lesson.title}")
        print(f"🎯 Category: {lesson.category}")
        print(f"⏱️  Duration: {lesson.duration_minutes} minutes")
        print(f"📊 Difficulty: {lesson.difficulty}")
        print(f"⭐ XP Reward: {lesson.xp_reward}")
        
        print(f"\n🎓 Learning Objectives:")
        for obj in lesson.learning_objectives:
            print(f"  • {obj}")
        
        print(f"\n📝 Sections: {len(lesson.sections)}")
        for i, section in enumerate(lesson.sections, 1):
            print(f"  {i}. {section.type.replace('_', ' ').title()}")
        
        print(f"\n❓ Quiz Questions: {len(lesson.quiz_questions)}")
        total_quiz_xp = sum(q.xp_reward for q in lesson.quiz_questions)
        print(f"   Total Quiz XP: {total_quiz_xp}")
        
        # Show first quiz question
        if lesson.quiz_questions:
            q = lesson.quiz_questions[0]
            print(f"\n   Example Question:")
            print(f"   Q: {q.text}")
            print(f"   Type: {q.type}")
            print(f"   Options: {len(q.options)} choices")
            print(f"   XP: {q.xp_reward}")
        
        # Simulate user progression
        print("\n" + "=" * 70)
        print("User Progression Simulation")
        print("=" * 70)
        
        user_id = "demo_user_001"
        
        # Complete lesson
        await lesson_engine.mark_lesson_complete(user_id, lesson.id)
        print(f"\n✅ Lesson '{lesson.title}' completed!")
        
        # Award XP
        current_xp = gamification.add_xp(user_id, lesson.xp_reward, "lesson_complete")
        level_info = gamification.get_level_info(user_id)
        
        print(f"🎉 Earned {lesson.xp_reward} XP!")
        print(f"📊 Total XP: {level_info['total_xp']}")
        print(f"🏆 Level: {level_info['level']} - {level_info['level_name']}")
        print(f"📈 Progress to next level: {level_info['progress_to_next']:.1f}%")
        
        # Check for badges
        badges = gamification.check_and_award_badges(user_id)
        if badges:
            print(f"\n🏅 Badges Earned:")
            for badge in badges:
                print(f"   • {badge['name']}: {badge['description']}")
        
        # Show learning path
        print("\n" + "=" * 70)
        print("Recommended Learning Path")
        print("=" * 70)
        
        beginner_path = [
            "01_understanding_stock_prices",
            "02_market_orders_vs_limit_orders",
            "03_volume_and_liquidity",
            "04_understanding_market_cap",
            "09_diversification",
            "13_bull_vs_bear",
            "15_index_funds_vs_individual_stocks",
        ]
        
        print("\n🎓 Beginner Path (Start Here):")
        for i, lesson_file in enumerate(beginner_path, 1):
            status = "✅" if i == 1 else "🔒"
            title = lesson_file.replace('_', ' ').title().split(' ', 1)[1]
            print(f"  {status} {i}. {title}")
        
        # Content statistics
        print("\n" + "=" * 70)
        print("Content Statistics")
        print("=" * 70)
        
        total_xp = len(lessons) * 50  # Approximate
        total_questions = len(lessons) * 4  # Approximate
        
        print(f"\n📊 Metrics:")
        print(f"   Total Lessons: {len(lessons)}")
        print(f"   Total Quiz Questions: ~{total_questions}")
        print(f"   Total XP Available: ~{total_xp}")
        print(f"   Categories: 9")
        print(f"   Difficulty Levels: 2 (Beginner, Intermediate)")
        print(f"   Average Duration: 6 minutes/lesson")
        
        print("\n" + "=" * 70)
        print("✅ Demo Complete!")
        print("=" * 70)
        
    except FileNotFoundError:
        print(f"\n❌ Error: Lesson file not found")
        print(f"   Make sure lesson files are in: {lessons_dir}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
