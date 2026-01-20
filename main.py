#!/usr/bin/env python3
"""
Casino Bonus Intelligence Engine - Main Entry Point

This is the command-line interface for running the intelligence engine.
"""
import argparse
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.models.database import init_db
from src.engine.manager import EngineManager

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description='Casino Bonus Intelligence Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single scrape cycle
  python main.py run

  # Run continuously (daemon mode)
  python main.py run --continuous

  # Add a new mirror site
  python main.py add-site https://example-casino.com

  # Start web dashboard
  python main.py dashboard

  # Show statistics
  python main.py stats
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run scrape cycle')
    run_parser.add_argument('--continuous', action='store_true', help='Run continuously')
    run_parser.add_argument('--interval', type=int, default=3600, help='Interval between runs (seconds)')

    # Add site command
    add_parser = subparsers.add_parser('add-site', help='Add mirror site')
    add_parser.add_argument('url', help='Site URL')
    add_parser.add_argument('--name', help='Site name')
    add_parser.add_argument('--merchant-id', help='Merchant ID')

    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    dashboard_parser.add_argument('--port', type=int, default=8000, help='Port number')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')

    args = parser.parse_args()

    # Initialize database
    init_db()

    if args.command == 'run':
        run_scraper(args.continuous, args.interval)

    elif args.command == 'add-site':
        add_site(args.url, args.name, args.merchant_id)

    elif args.command == 'dashboard':
        start_dashboard(args.port)

    elif args.command == 'stats':
        show_stats()

    else:
        parser.print_help()


def run_scraper(continuous: bool = False, interval: int = 3600):
    """Run the scraper"""
    print("🎰 Casino Bonus Intelligence Engine")
    print("=" * 60)

    manager = EngineManager()

    if continuous:
        print(f"Running in CONTINUOUS mode (interval: {interval}s)")
        print("Press Ctrl+C to stop")
        import time

        try:
            while True:
                result = manager.run_cycle()
                print(f"\nNext run in {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
    else:
        result = manager.run_cycle()
        print("\n✅ Scrape cycle completed!")


def add_site(url: str, name: str = None, merchant_id: str = None):
    """Add a new mirror site"""
    manager = EngineManager()
    site = manager.add_mirror_site(url, merchant_id, name)
    print(f"✅ Added site: {url}")
    print(f"   ID: {site.id}")
    print(f"   Health: {site.health_status.value}")


def start_dashboard(port: int = 8000):
    """Start web dashboard"""
    print(f"🌐 Starting web dashboard on http://localhost:{port}")
    print("Press Ctrl+C to stop")

    import uvicorn
    from src.api.main import app

    uvicorn.run(app, host="0.0.0.0", port=port)


def show_stats():
    """Show statistics"""
    from src.models.database import SessionLocal
    from src.models import MirrorSite, Bonus, ScrapeRun
    from src.engine.deduplicator import BonusDeduplicator

    db = SessionLocal()

    print("📊 Casino Bonus Intelligence Engine - Statistics")
    print("=" * 60)

    # Site health
    manager = EngineManager()
    health = manager.get_site_health_summary()

    print(f"\n🌐 Mirror Sites:")
    print(f"   Active:     {health['active']}")
    print(f"   Purgatory:  {health['purgatory']}")
    print(f"   Pruned:     {health['pruned']}")
    print(f"   Total:      {health['total']}")

    # Bonuses
    total_bonuses = db.query(Bonus).filter(Bonus.is_active == True).count()
    beatable = db.query(Bonus).filter(Bonus.is_active == True, Bonus.is_beatable == True).count()

    print(f"\n🎁 Bonuses:")
    print(f"   Total:      {total_bonuses}")
    print(f"   Beatable:   {beatable}")
    print(f"   Non-Beat:   {total_bonuses - beatable}")

    # Top bonuses
    top_bonuses = db.query(Bonus).filter(
        Bonus.is_active == True,
        Bonus.is_beatable == True
    ).order_by(Bonus.pv_score.desc()).limit(5).all()

    print(f"\n🏆 Top 5 Beatable Bonuses:")
    for i, bonus in enumerate(top_bonuses, 1):
        print(f"   {i}. {bonus.title[:50]}")
        print(f"      PV: {bonus.pv_score} | Amount: ${bonus.bonus_amount or 'N/A'} | Rollover: {bonus.rollover or 'N/A'}x")

    # Deduplication
    dedup = BonusDeduplicator(db)
    dedup_stats = dedup.get_duplicate_stats()

    print(f"\n🔍 Deduplication:")
    print(f"   Unique:     {dedup_stats['unique_bonuses']}")
    print(f"   Duplicates: {dedup_stats['duplicate_bonuses']}")
    print(f"   Dedup Rate: {dedup_stats['deduplication_rate']}%")

    # Last run
    last_run = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).first()

    if last_run:
        print(f"\n⏱️  Last Scrape Run:")
        print(f"   Run #{last_run.run_number} ({last_run.run_type})")
        print(f"   Sites: {last_run.sites_successful}/{last_run.sites_checked}")
        print(f"   Bonuses: {last_run.bonuses_found} found, {last_run.bonuses_new} new")
        print(f"   Duration: {last_run.duration_seconds:.2f}s")
        print(f"   Time: {last_run.started_at}")

    db.close()
    print()


if __name__ == '__main__':
    main()
