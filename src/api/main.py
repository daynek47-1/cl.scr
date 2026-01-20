"""Casino Bonus Intelligence Engine - Web Dashboard API"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import os

from ..models import get_db, MirrorSite, Bonus, SiteHealth, ScrapeRun, WorkerLog
from ..models.database import init_db
from ..engine.manager import EngineManager

# Initialize database
init_db()

app = FastAPI(
    title="Casino Bonus Intelligence Engine",
    description="Smart casino bonus discovery with PV-based beatability analysis",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Casino Bonus Intelligence Engine</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #1a1a1a; color: #fff; }
            h1 { color: #4CAF50; }
            .stats { display: flex; gap: 20px; margin: 20px 0; }
            .stat-card { background: #2a2a2a; padding: 20px; border-radius: 8px; flex: 1; }
            .bonus-list { background: #2a2a2a; padding: 20px; border-radius: 8px; }
            .bonus-item { background: #3a3a3a; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
            .beatable { border-left-color: #4CAF50; }
            .not-beatable { border-left-color: #f44336; }
            .pv-score { font-size: 24px; font-weight: bold; color: #4CAF50; }
            a { color: #64B5F6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🎰 Casino Bonus Intelligence Engine</h1>
        <div class="stats">
            <div class="stat-card">
                <h3>Active Sites</h3>
                <div class="pv-score" id="activeSites">-</div>
            </div>
            <div class="stat-card">
                <h3>Total Bonuses</h3>
                <div class="pv-score" id="totalBonuses">-</div>
            </div>
            <div class="stat-card">
                <h3>Beatable Bonuses</h3>
                <div class="pv-score" id="beatableBonuses">-</div>
            </div>
        </div>

        <h2>Top Beatable Bonuses (by PV Score)</h2>
        <div id="bonusList" class="bonus-list">Loading...</div>

        <p style="margin-top: 40px;">
            <a href="/docs">📘 API Documentation</a> |
            <a href="/api/stats">📊 Statistics</a> |
            <a href="/api/bonuses/best">🏆 Best Bonuses</a>
        </p>

        <script>
            async function loadDashboard() {
                try {
                    // Load stats
                    const stats = await fetch('/api/stats').then(r => r.json());
                    document.getElementById('activeSites').textContent = stats.active_sites;
                    document.getElementById('totalBonuses').textContent = stats.total_bonuses;
                    document.getElementById('beatableBonuses').textContent = stats.beatable_bonuses;

                    // Load top bonuses
                    const bonuses = await fetch('/api/bonuses/best?limit=10').then(r => r.json());
                    const bonusList = document.getElementById('bonusList');
                    bonusList.innerHTML = bonuses.map(b => `
                        <div class="bonus-item ${b.is_beatable ? 'beatable' : 'not-beatable'}">
                            <strong>${b.title}</strong><br>
                            <span style="color: #4CAF50; font-size: 18px;">PV Score: ${b.pv_score}</span> |
                            Amount: $${b.bonus_amount || 'N/A'} |
                            Rollover: ${b.rollover || 'N/A'}x |
                            Max Withdrawal: $${b.max_withdrawal || 'N/A'}<br>
                            <small>${b.description || ''}</small>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error('Error loading dashboard:', e);
                }
            }
            loadDashboard();
            setInterval(loadDashboard, 30000); // Refresh every 30s
        </script>
    </body>
    </html>
    """
    return html


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    active_sites = db.query(MirrorSite).filter(MirrorSite.health_status == SiteHealth.ACTIVE).count()
    total_bonuses = db.query(Bonus).filter(Bonus.is_active == True).count()
    beatable_bonuses = db.query(Bonus).filter(Bonus.is_active == True, Bonus.is_beatable == True).count()

    last_run = db.query(ScrapeRun).order_by(desc(ScrapeRun.started_at)).first()

    return {
        'active_sites': active_sites,
        'total_bonuses': total_bonuses,
        'beatable_bonuses': beatable_bonuses,
        'last_run': last_run.started_at if last_run else None,
        'last_run_duration': last_run.duration_seconds if last_run else None
    }


@app.get("/api/bonuses/best")
async def get_best_bonuses(
    limit: int = 20,
    beatable_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get best bonuses ranked by PV score"""
    query = db.query(Bonus).filter(Bonus.is_active == True)

    if beatable_only:
        query = query.filter(Bonus.is_beatable == True)

    bonuses = query.order_by(desc(Bonus.pv_score)).limit(limit).all()

    return [
        {
            'id': b.id,
            'title': b.title,
            'description': b.description,
            'bonus_amount': b.bonus_amount,
            'rollover': b.rollover,
            'max_withdrawal': b.max_withdrawal,
            'pv_score': b.pv_score,
            'is_beatable': b.is_beatable,
            'bonus_code': b.bonus_code,
            'url': b.url,
            'first_seen': b.first_seen,
            'seen_on_sites': b.seen_on_sites
        }
        for b in bonuses
    ]


@app.get("/api/bonuses")
async def get_bonuses(
    skip: int = 0,
    limit: int = 50,
    min_pv: Optional[float] = None,
    beatable_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get bonuses with filtering"""
    query = db.query(Bonus).filter(Bonus.is_active == True)

    if beatable_only:
        query = query.filter(Bonus.is_beatable == True)

    if min_pv is not None:
        query = query.filter(Bonus.pv_score >= min_pv)

    total = query.count()
    bonuses = query.order_by(desc(Bonus.pv_score)).offset(skip).limit(limit).all()

    return {
        'total': total,
        'bonuses': [
            {
                'id': b.id,
                'title': b.title,
                'bonus_amount': b.bonus_amount,
                'rollover': b.rollover,
                'pv_score': b.pv_score,
                'is_beatable': b.is_beatable,
            }
            for b in bonuses
        ]
    }


@app.get("/api/sites")
async def get_sites(db: Session = Depends(get_db)):
    """Get all mirror sites"""
    sites = db.query(MirrorSite).all()

    return [
        {
            'id': s.id,
            'url': s.url,
            'name': s.name,
            'health_status': s.health_status.value,
            'consecutive_failures': s.consecutive_failures,
            'last_success': s.last_success,
            'last_scraped': s.last_scraped
        }
        for s in sites
    ]


@app.post("/api/scrape/run")
async def trigger_scrape():
    """Trigger a scrape cycle"""
    try:
        manager = EngineManager()
        result = manager.run_cycle()
        return {'status': 'success', 'result': result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runs")
async def get_runs(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent scrape runs"""
    runs = db.query(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(limit).all()

    return [
        {
            'run_number': r.run_number,
            'run_type': r.run_type,
            'sites_checked': r.sites_checked,
            'bonuses_found': r.bonuses_found,
            'bonuses_new': r.bonuses_new,
            'duration_seconds': r.duration_seconds,
            'started_at': r.started_at
        }
        for r in runs
    ]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('API_PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
