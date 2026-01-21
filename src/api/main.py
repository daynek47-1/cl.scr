"Casino Bonus Intelligence Engine - Web Dashboard API"
from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import threading
import asyncio
import logging
import json

from ..models import get_db, MirrorSite, Bonus, SiteHealth, ScrapeRun, WorkerLog
from ..models.database import init_db
from ..engine.manager import EngineManager
from ..engine.broadcaster import broadcaster

# Initialize database
init_db()

app = FastAPI(
    title="Casino Bonus Intelligence Engine",
    description="Smart casino bonus discovery with PV-based beatability analysis",
    version="1.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Scraper Control ---
class ScraperController:
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.is_running = False

    def start(self):
        if self.is_running:
            return False
        
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._run_wrapper)
        self.thread.start()
        return True

    def stop(self):
        if not self.is_running:
            return False
        self.stop_event.set()
        return True

    def _run_wrapper(self):
        try:
            # Force quiet_mode=False to ensure logging works (redirected to console)
            manager = EngineManager(quiet_mode=False) 
            manager.run_cycle(stop_event=self.stop_event)
        except Exception as e:
            logging.error(f"Scraper thread failed: {e}")
            broadcaster.broadcast_sync(f"CRITICAL ERROR: {e}")
        finally:
            self.is_running = False
            broadcaster.broadcast_sync("--- Scraper Cycle Ended ---")

scraper_controller = ScraperController()

@app.on_event("startup")
async def startup_event():
    broadcaster.set_loop(asyncio.get_running_loop())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = broadcaster.subscribe()
    try:
        while True:
            data = await queue.get()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        broadcaster.unsubscribe(queue)

# --- Helpers ---
def get_config_dict():
    """Read .env file into a dict"""
    config = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def update_config_file(new_config: Dict[str, str]):
    """Update .env file preserving comments if possible"""
    lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            lines = f.readlines()
    
    # Simple strategy: replace existing keys, append new ones
    updated_keys = set()
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in new_config:
                new_lines.append(f"{key}={new_config[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    # Append new keys that weren't in the file
    for key, value in new_config.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")
            
    with open('.env', 'w') as f:
        f.writelines(new_lines)

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard with Tabs"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Casino Bonus Intelligence Engine</title>
        <meta charset="utf-8">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root { --primary: #4CAF50; --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --accent: #2196F3; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: var(--bg); color: var(--text); }
            
            /* Layout */
            .sidebar { width: 250px; height: 100vh; background: #000; position: fixed; top: 0; left: 0; padding: 20px; box-sizing: border-box; }
            .content { margin-left: 250px; padding: 20px; }
            
            /* Sidebar Nav */
            .logo { font-size: 1.2em; font-weight: bold; color: var(--primary); margin-bottom: 30px; display: block; text-decoration: none; }
            .nav-item { display: block; padding: 12px 15px; color: #888; text-decoration: none; border-radius: 5px; margin-bottom: 5px; transition: 0.2s; cursor: pointer; }
            .nav-item:hover, .nav-item.active { background: #333; color: white; }
            .nav-item i { margin-right: 10px; width: 20px; text-align: center; }
            
            /* Components */
            .card { background: var(--card); padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; }
            .stats-grid { display: flex; gap: 20px; }
            .stat-card { flex: 1; text-align: center; background: #2a2a2a; padding: 15px; border-radius: 5px; }
            .stat-value { font-size: 24px; font-weight: bold; color: var(--primary); }
            
            /* Tables */
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
            th { color: #888; font-weight: normal; }
            tr:hover { background: #2a2a2a; }
            
            /* Buttons */
            .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
            .btn-primary { background: var(--accent); color: white; }
            .btn-success { background: var(--primary); color: white; }
            .btn-danger { background: #f44336; color: white; }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; }
            
            /* Console */
            .console { background: #000; color: #0f0; font-family: monospace; padding: 15px; height: 400px; overflow-y: auto; white-space: pre-wrap; font-size: 12px; border: 1px solid #333; }
            
            /* Utils */
            .hidden { display: none; }
            .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
            .running { background: var(--primary); box-shadow: 0 0 5px var(--primary); }
            .stopped { background: #f44336; }
            
            /* Form */
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; color: #888; }
            .form-group input { width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: white; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <a href="#" class="logo">🎰 Intelligence Engine</a>
            <div class="nav-item active" onclick="showTab('dashboard')"><i class="fas fa-chart-line"></i> Dashboard</div>
            <div class="nav-item" onclick="showTab('console')"><i class="fas fa-terminal"></i> Console</div>
            <div class="nav-item" onclick="showTab('database')"><i class="fas fa-database"></i> Database</div>
            <div class="nav-item" onclick="showTab('logs')"><i class="fas fa-list-alt"></i> Logs</div>
            <div class="nav-item" onclick="showTab('settings')"><i class="fas fa-cog"></i> Settings</div>
            
            <div style="margin-top: 50px; font-size: 12px; color: #666;">
                Status: <span id="globalStatus">Checking...</span>
            </div>
        </div>

        <div class="content">
            <!-- DASHBOARD TAB -->
            <div id="tab-dashboard">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Overview</h2>
                    <div>
                        <button id="btnStart" class="btn btn-success" onclick="startScrape()">Start Scraper</button>
                        <button id="btnStop" class="btn btn-danger" onclick="stopScrape()" disabled>Stop</button>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="activeSites">-</div>
                        <div>Active Sites</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="totalBonuses">-</div>
                        <div>Total Bonuses</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="beatableBonuses">-</div>
                        <div>High Value</div>
                    </div>
                </div>
                
                <div class="grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                    <div class="card">
                        <h3>🏆 Top Opportunities</h3>
                        <div id="topBonusesList">Loading...</div>
                    </div>
                    <div class="card">
                        <h3>📊 Recent Runs</h3>
                        <div id="recentRunsList">Loading...</div>
                    </div>
                </div>
            </div>

            <!-- CONSOLE TAB -->
            <div id="tab-console" class="hidden">
                <h2>Live Console</h2>
                <div class="card">
                    <div id="consoleOutput" class="console">Waiting for output...</div>
                </div>
            </div>

            <!-- DATABASE TAB -->
            <div id="tab-database" class="hidden">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2>Bonus Database</h2>
                    <div>
                        <input type="text" id="dbSearch" placeholder="Search..." style="padding: 5px; background: #333; border: 1px solid #444; color: white;">
                        <button class="btn btn-primary" onclick="loadDatabase()">Refresh</button>
                    </div>
                </div>
                <div class="card">
                    <table id="bonusesTable">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>Amount</th>
                                <th>Rollover</th>
                                <th>PV Score</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>

            <!-- LOGS TAB -->
            <div id="tab-logs" class="hidden">
                <h2>System Logs</h2>
                <div class="card">
                    <table id="logsTable">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Worker</th>
                                <th>Action</th>
                                <th>Status</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>

            <!-- SETTINGS TAB -->
            <div id="tab-settings" class="hidden">
                <h2>Configuration</h2>
                <div class="card">
                    <div id="configForm"></div>
                    <div style="margin-top: 20px;">
                        <button class="btn btn-success" onclick="saveConfig()">Save Configuration</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // State
            let ws;
            let currentTab = 'dashboard';

            // Navigation
            function showTab(tabName) {
                document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.add('hidden'));
                document.getElementById(`tab-${tabName}`).classList.remove('hidden');
                
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                event.currentTarget.classList.add('active');
                
                currentTab = tabName;
                if (tabName === 'database') loadDatabase();
                if (tabName === 'logs') loadLogs();
                if (tabName === 'settings') loadSettings();
            }

            // WebSocket
            function connectWS() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                const consoleDiv = document.getElementById('consoleOutput');
                
                ws.onmessage = (event) => {
                    const line = document.createElement('div');
                    line.textContent = event.data;
                    consoleDiv.appendChild(line);
                    consoleDiv.scrollTop = consoleDiv.scrollHeight;
                    
                    if (event.data.includes('Starting Run')) updateStatus(true);
                    if (event.data.includes('Scraper Cycle Ended')) updateStatus(false);
                };
                
                ws.onclose = () => setTimeout(connectWS, 2000);
            }

            // API Calls
            async function updateStatus(isRunning) {
                const statusSpan = document.getElementById('globalStatus');
                const btnStart = document.getElementById('btnStart');
                const btnStop = document.getElementById('btnStop');
                
                if (isRunning) {
                    statusSpan.innerHTML = '<span class="status-dot running"></span> Running';
                    btnStart.disabled = true;
                    btnStop.disabled = false;
                } else {
                    statusSpan.innerHTML = '<span class="status-dot stopped"></span> Stopped';
                    btnStart.disabled = false;
                    btnStop.disabled = true;
                }
            }

            async function checkStatus() {
                const res = await fetch('/api/control/status');
                const data = await res.json();
                updateStatus(data.is_running);
            }

            async function startScrape() {
                await fetch('/api/control/start', { method: 'POST' });
                showTab('console'); // Auto switch to console
            }

            async function stopScrape() {
                if (confirm('Stop scraper?')) {
                    await fetch('/api/control/stop', { method: 'POST' });
                }
            }
            
            async function claimBonus(id) {
                if (confirm('Mark this bonus as claimed?')) {
                    await fetch(`/api/bonuses/${id}/claim`, { method: 'POST' });
                    loadDatabase(); // Refresh
                }
            }

            // Data Loading
            async function loadDashboard() {
                const stats = await fetch('/api/stats').then(r => r.json());
                document.getElementById('activeSites').textContent = stats.active_sites;
                document.getElementById('totalBonuses').textContent = stats.total_bonuses;
                document.getElementById('beatableBonuses').textContent = stats.beatable_bonuses;
                
                const bonuses = await fetch('/api/bonuses/best?limit=5').then(r => r.json());
                document.getElementById('topBonusesList').innerHTML = bonuses.map(b => `
                    <div style="padding: 10px; border-bottom: 1px solid #333;">
                        <div style="font-weight: bold; color: #4CAF50;">${b.pv_score} PV - ${b.title}</div>
                        <div style="font-size: 0.9em; color: #888;">$${b.bonus_amount} | ${b.rollover}x</div>
                    </div>
                `).join('');
                
                const runs = await fetch('/api/runs?limit=5').then(r => r.json());
                document.getElementById('recentRunsList').innerHTML = runs.map(r => `
                    <div style="padding: 10px; border-bottom: 1px solid #333;">
                        <div>Run #${r.run_number} (${r.run_type})</div>
                        <div style="font-size: 0.9em; color: #888;">Found: ${r.bonuses_found} | New: ${r.bonuses_new}</div>
                    </div>
                `).join('');
            }

            async function loadDatabase() {
                const res = await fetch('/api/bonuses?limit=100');
                const data = await res.json();
                const tbody = document.querySelector('#bonusesTable tbody');
                tbody.innerHTML = data.bonuses.map(b => `
                    <tr>
                        <td>${b.title}</td>
                        <td>$${b.bonus_amount || 0}</td>
                        <td>${b.rollover || 0}x</td>
                        <td style="color: ${b.pv_score > 50 ? '#4CAF50' : '#e0e0e0'}">${b.pv_score}</td>
                        <td>${b.is_claimed ? '<span style="color:#aaa">Claimed</span>' : (b.is_beatable ? '<span style="color:#4CAF50">High Value</span>' : 'Standard')}</td>
                        <td>
                            ${!b.is_claimed ? `<button class="btn btn-primary" style="padding: 2px 8px; font-size: 12px;" onclick="claimBonus(${b.id})">Claim</button>` : ''}
                        </td>
                    </tr>
                `).join('');
            }

            async function loadLogs() {
                const res = await fetch('/api/logs?limit=50');
                const logs = await res.json();
                const tbody = document.querySelector('#logsTable tbody');
                tbody.innerHTML = logs.map(l => `
                    <tr>
                        <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
                        <td>Worker ${l.worker_id}</td>
                        <td>${l.action}</td>
                        <td style="color: ${l.status === 'success' ? '#4CAF50' : '#f44336'}">${l.status}</td>
                        <td style="font-family: monospace;">${l.error_message || l.proxy_used || '-'}</td>
                    </tr>
                `).join('');
            }

            async function loadSettings() {
                const res = await fetch('/api/config');
                const config = await res.json();
                const form = document.getElementById('configForm');
                form.innerHTML = Object.entries(config).map(([k, v]) => `
                    <div class="form-group">
                        <label>${k}</label>
                        <input type="text" name="${k}" value="${v}">
                    </div>
                `).join('');
            }
            
            async function saveConfig() {
                const inputs = document.querySelectorAll('#configForm input');
                const config = {};
                inputs.forEach(input => config[input.name] = input.value);
                
                if(confirm("Save config? This may require a restart.")) {
                    await fetch('/api/config', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    });
                    alert("Saved!");
                }
            }

            // Init
            connectWS();
            checkStatus();
            loadDashboard();
            setInterval(checkStatus, 5000);
            setInterval(() => { if(currentTab === 'dashboard') loadDashboard(); }, 10000);
        </script>
    </body>
    </html>
    "
    return html


# --- Data API ---

@app.get("/api/config")
async def get_config():
    return get_config_dict()

@app.post("/api/config")
async def save_config(config: Dict[str, str]):
    update_config_file(config)
    return {"status": "success"}

@app.get("/api/logs")
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(WorkerLog).order_by(desc(WorkerLog.timestamp)).limit(limit).all()
    return [
        {
            "timestamp": l.timestamp,
            "worker_id": l.worker_id,
            "action": l.action,
            "status": l.status,
            "error_message": l.error_message,
            "proxy_used": l.proxy_used
        } for l in logs
    ]

@app.post("/api/bonuses/{bonus_id}/claim")
async def claim_bonus(bonus_id: int, db: Session = Depends(get_db)):
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    if not bonus:
        raise HTTPException(404, "Bonus not found")
    bonus.is_claimed = True
    bonus.claimed_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}

# ... (Original stats/bonuses/sites/runs endpoints preserved)

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
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
    query = db.query(Bonus).filter(Bonus.is_active == True)
    if beatable_only:
        query = query.filter(Bonus.is_beatable == True)
    bonuses = query.order_by(desc(Bonus.pv_score)).limit(limit).all()
    return [
        {
            'id': b.id,
            'title': b.title,
            'bonus_amount': b.bonus_amount,
            'rollover': b.rollover,
            'max_withdrawal': b.max_withdrawal,
            'pv_score': b.pv_score,
            'is_beatable': b.is_beatable,
            'is_claimed': b.is_claimed, # Added field
            'url': b.url
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
    query = db.query(Bonus).filter(Bonus.is_active == True)

    if beatable_only:
        query = query.filter(Bonus.is_beatable == True)

    if min_pv is not None:
        query = query.query.filter(Bonus.pv_score >= min_pv)

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
                'is_claimed': b.is_claimed # Added field
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

# --- Control Endpoints ---

@app.post("/api/control/start")
async def start_scraper():
    """Start the scraper in a background thread"""
    if scraper_controller.start():
        return {'status': 'success'}
    return {'status': 'error', 'message': 'Running'}

@app.post("/api/control/stop")
async def stop_scraper():
    """Signal the scraper to stop"""
    if scraper_controller.stop():
        return {'status': 'success'}
    return {'status': 'error', 'message': 'Not running'}


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

@app.get("/api/control/status")
async def get_scraper_status():
    return {'is_running': scraper_controller.is_running}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('API_PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)