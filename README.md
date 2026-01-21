# 🎰 Casino Bonus Intelligence Engine

A sophisticated, autonomous system for discovering, analyzing, and ranking casino bonuses across mirror site networks using **Perceived Value (PV)** analysis to identify mathematically "beatable" offers.

## 🎯 Core Concept

This isn't just a bonus scraper - it's a **quantitative intelligence engine** that:

- **Autonomously patrols** vast networks of casino mirror sites
- **Calculates Perceived Value (PV)** to determine if bonuses are mathematically beatable
- **Self-heals** with site health management (Active → Purgatory → Pruned)
- **Deduplicates** intelligently using fingerprinting + fuzzy matching
- **Operates continuously** without human intervention

## 🏗️ Architecture

### Four Core Components

#### 1. **The Manager** (Lifecycle & Scheduling)
Orchestrates heartbeat cycles with adaptive site checking:
- **Standard Run**: Check all Active sites
- **Retest Cycle** (every 5th run): Re-check Purgatory sites
- **Resurrection** (every 125th run): Deep scan of Pruned sites

#### 2. **The Workforce** (Parallel Workers)
- Multi-threaded parallel scraping
- Automatic proxy rotation on 403/failure
- Human mimicry with random delays
- Individual worker logging

#### 3. **The Brain** (Analysis & Deduplication)
- **PV Calculator**: Determines bonus beatability
  ```
  PV = (bonus_amount × weight) - (rollover × penalty) + (max_withdrawal × reward)
  ```
- **Smart Deduplication**:
  - SHA256 fingerprinting for exact matches
  - Fuzzy matching (Levenshtein distance) for variants
  - Parent-child linking across mirror sites
- **Expiration Tracking**: Automatic date parsing and marking

#### 4. **The Interface** (Dashboard & TUI)
- **Web Dashboard**: Real-time bonus rankings, PV scores, filtering
- **Command Center**: Matrix-style worker status updates

## 📡 API Access Protocol

### The Exact Endpoint

```
Endpoint: {Base_URL}/api/v1/index.php
Method: POST
```

### Required Payload

```json
{
  "module": "/users/syncData",
  "merchantId": "<extracted_from_html>",
  "accessToken": "<from_login>",
  "accessId": "<from_login>",
  "domainId": "0",
  "walletIsAdmin": ""
}
```

### Authentication Flow

1. **Login**: Authenticate on homepage → get `accessToken` + `accessId`
2. **Cache**: Store credentials for 6 hours
3. **Extract**: Send POST to API endpoint
4. **Retry**: On failure, force fresh login and retry

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repo-url>
cd cl.scr

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configuration

Edit `.env`:

```bash
# Casino Credentials (REQUIRED)
CASINO_USERNAME=your_username
CASINO_PASSWORD=your_password

# Worker Configuration
WORKER_COUNT=5
WORKER_DELAY_MIN=2
WORKER_DELAY_MAX=5

# Proxy Configuration (Optional)
USE_PROXIES=true
PROXY_LIST=http://proxy1:port,http://proxy2:port

# PV Calculation Weights
PV_BONUS_WEIGHT=1.0
PV_ROLLOVER_WEIGHT=0.5
PV_MAX_WITHDRAWAL_WEIGHT=0.3
```

### 3. Add Mirror Sites

```bash
# Add your first mirror site
python main.py add-site https://casino-mirror1.com --name "Casino Mirror 1"

# Add multiple sites
python main.py add-site https://casino-mirror2.com
python main.py add-site https://casino-mirror3.com
```

### 4. Run First Scrape

```bash
# Single run
python main.py run

# Continuous mode (runs every hour)
python main.py run --continuous --interval 3600
```

### 5. View Dashboard

```bash
# Start web dashboard
python main.py dashboard

# Open in browser
http://localhost:8000
```

## 📊 Usage Examples

### Check Statistics

```bash
python main.py stats
```

Output:
```
📊 Casino Bonus Intelligence Engine - Statistics
============================================================

🌐 Mirror Sites:
   Active:     15
   Purgatory:  3
   Pruned:     2
   Total:      20

🎁 Bonuses:
   Total:      487
   Beatable:   142
   Non-Beat:   345

🏆 Top 5 Beatable Bonuses:
   1. Welcome Bonus 200% Match + $500
      PV: 285.5 | Amount: $500 | Rollover: 25x
   2. No Deposit Bonus $100 Free
      PV: 195.0 | Amount: $100 | Rollover: 15x
```

### View Best Bonuses

```bash
# Via API
curl http://localhost:8000/api/bonuses/best

# Via Web Dashboard
http://localhost:8000
```

### Trigger Manual Scrape

```bash
# Via CLI
python main.py run

# Via API
curl -X POST http://localhost:8000/api/scrape/run
```

## 🔍 How It Works

### 1. Site Health Management

Sites progress through health states based on failures:

```
Active (0 failures)
  ↓ (5 consecutive failures)
Purgatory (checked less frequently)
  ↓ (10 consecutive failures)
Pruned (rarely checked, "dead")
  ↓ (resurrection cycles can revive)
Active (if successful again)
```

### 2. Perceived Value (PV) Calculation - V14 Algorithm

The **V14 Algorithm** is the secret sauce - a sophisticated non-linear formula that determines if a bonus is mathematically beatable:

#### The V14 Formula

```python
PV = (10 * log2(max_withdrawal + 1) * sqrt(bonus_amount)) /
     (pow(rollover, 1.25) * log10(bonus_amount + 10))
```

**Why V14 is Superior:**
- **Logarithmic Scaling**: Large max withdrawals have diminishing marginal value (realistic)
- **Exponential Rollover Penalty**: High rollovers (40x, 50x) are penalized much more heavily
- **Size Efficiency**: Bigger bonuses aren't always better - square root prevents huge bonuses from dominating
- **Non-Linear**: Models real-world playability better than simple linear formulas

**Example 1: Excellent Bonus (High PV)**
```
Bonus: $500
Rollover: 25x
Max Withdrawal: $2000

Calculation:
- Numerator: 10 * log2(2001) * sqrt(500) = 10 * 10.97 * 22.36 = 2,453
- Denominator: pow(25, 1.25) * log10(510) = 78.43 * 2.71 = 212.5
- PV = 2,453 / 212.5 = 115.4 ✅ EXCELLENT (Rating: Good)
```

**Example 2: Poor Bonus (Low PV)**
```
Bonus: $100
Rollover: 60x
Max Withdrawal: $200

Calculation:
- Numerator: 10 * log2(201) * sqrt(100) = 10 * 7.65 * 10 = 765
- Denominator: pow(60, 1.25) * log10(110) = 191.4 * 2.04 = 390.5
- PV = 765 / 390.5 = 19.6 ❌ POOR (Below beatable threshold of 20)
```

**Beatability Thresholds (V14):**
- **Excellent**: PV > 200 and rollover < 30x
- **Good**: PV > 100 or (PV > 50 and rollover < 40x)
- **Fair**: PV > 20
- **Poor**: PV ≤ 20 (not beatable)

### 3. Smart Deduplication with Safety Checks

The same bonus appears on 50 mirror sites? No problem. But different bonuses with similar names? Protected.

#### Deduplication Strategy

1. **Exact Fingerprinting**: SHA256 hash of title+description
2. **Fuzzy Matching**: difflib.SequenceMatcher with 80% similarity threshold
3. **Safety Checks**: Critical protections to prevent incorrect merges
4. **Parent-Child Linking**: Duplicates link to parent, track `seen_on_sites`

#### Safety Features

**Number Protection**: Prevents merging bonuses with different numbers
```
✅ "Welcome Bonus 2024" matches "Welcome Bonus 2024"
❌ "Bonus 100 Free" does NOT match "Bonus 200 Free"
❌ "$50 Bonus" does NOT match "$100 Bonus"
```

**Roman Numeral Protection**: Prevents merging different tiers/levels
```
✅ "VIP Tier I" matches "VIP Tier I Bonus"
❌ "VIP Tier I" does NOT match "VIP Tier II"
❌ "Level III Bonus" does NOT match "Level IV Bonus"
```

#### How It Works

```python
Title 1: "Welcome Bonus 2024 - 100% Match"
Title 2: "Welcome Bonus 2024 - 100% Match Up To $500"
→ Similarity: 87% → MATCHED (no conflicting numbers)

Title 1: "Tier I Welcome Bonus $100"
Title 2: "Tier II Welcome Bonus $100"
→ Similarity: 93% → BLOCKED (different Roman numerals)

Title 1: "Get $50 Free Bonus"
Title 2: "Get $100 Free Bonus"
→ Similarity: 88% → BLOCKED (different dollar amounts)
```

This prevents the database from incorrectly merging distinct bonuses that happen to have similar names.

### 4. Worker Behavior

Each worker operates independently:

```python
Worker 1: [ACTIVE] Scanning site-1.com... SUCCESS (12 bonuses found)
Worker 2: [ACTIVE] Scanning site-2.com... 403 ERROR → Rotating proxy
Worker 3: [SLEEPING] Delay 3.2s (human mimicry)
Worker 4: [PARSING] Processing bonus data...
Worker 5: [FAILED] site-5.com → Network timeout → Marking site as failed
```

## 🛠️ Advanced Configuration

### PV Algorithm Selection

The system supports two algorithms:

**V14 Algorithm (Recommended - Default)**
```bash
USE_V14_FORMULA=true  # Sophisticated non-linear algorithm
```

**Linear Algorithm (Simple - For Testing)**
```bash
USE_V14_FORMULA=false  # Legacy linear calculation

# Then configure weights:
PV_BONUS_WEIGHT=1.0
PV_ROLLOVER_WEIGHT=0.5
PV_MAX_WITHDRAWAL_WEIGHT=0.3
```

**When to use Linear:**
- Testing/debugging PV calculations
- Need predictable, easy-to-understand scores
- Comparing against external systems

**When to use V14 (default):**
- Production deployments
- Realistic bonus evaluation
- Better handling of extreme values (very high rollovers, huge bonuses)
- More accurate beatability assessment

### Heartbeat Cycle Tuning

```bash
# Check Purgatory sites more often
PURGATORY_CHECK_INTERVAL=3  # Every 3rd run instead of 5th

# Resurrect sites more frequently
RESURRECTION_CHECK_INTERVAL=50  # Every 50th run instead of 125th
```

### Proxy Rotation

```bash
USE_PROXIES=true
PROXY_LIST=http://proxy1:8080,http://proxy2:8080,socks5://proxy3:1080
```

Workers automatically rotate to next proxy on:
- HTTP 403 (Forbidden)
- Connection timeout
- Proxy-specific errors

## 📁 Project Structure

```
cl.scr/
├── src/
│   ├── engine/              # Core intelligence engine
│   │   ├── auth.py          # Authentication & session caching
│   │   ├── api_client.py    # API client with exact payload
│   │   ├── worker.py        # Parallel workers with proxy rotation
│   │   ├── manager.py       # Lifecycle manager & heartbeat
│   │   ├── pv_calculator.py # Perceived Value algorithm
│   │   └── deduplicator.py  # Smart deduplication
│   ├── models/              # Database models
│   │   ├── database.py      # SQLAlchemy setup
│   │   └── casino.py        # MirrorSite, Bonus, SessionCache, etc.
│   └── api/                 # Web dashboard
│       └── main.py          # FastAPI application
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

## 🔐 Security Notes

- **Credentials**: Never commit `.env` file (in .gitignore)
- **Session Tokens**: Cached for 6 hours, auto-expire
- **Proxies**: Use authenticated proxies to avoid IP bans
- **Rate Limiting**: Random delays (2-5s) between requests

## 🐛 Troubleshooting

### Sites Keep Failing

**Problem**: Sites moving to Purgatory/Pruned
**Solutions**:
1. Check if credentials are correct
2. Verify merchantId extraction is working
3. Enable proxy rotation
4. Check if site structure changed

### Low Bonus Count

**Problem**: Not finding many bonuses
**Solutions**:
1. Check API response structure (may need custom parser)
2. Verify login is successful
3. Check if sites require additional authentication steps

### High Deduplication Rate

**Problem**: Too many duplicates
**Solution**: This is normal! Same bonuses on mirror sites. Check `seen_on_sites` to see how widespread a bonus is.

## 📈 Performance

- **Speed**: 5 workers can scan 100 sites in ~10 minutes
- **Deduplication**: 70-80% typical rate (many mirrors = many duplicates)
- **Database**: SQLite handles 10,000+ bonuses efficiently
- **Memory**: ~200MB for typical operation

## 🤝 Contributing

This is a specialized intelligence engine. Contributions welcome for:
- Additional casino API parsers
- Enhanced PV algorithms
- Better expiration date parsing
- TUI improvements

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

Built for automated bonus intelligence and analysis. Use responsibly and in accordance with casino terms of service.

---

**Ready to find beatable bonuses?** Start scraping:

```bash
python main.py run --continuous
```

**Monitor in real-time:**

```bash
python main.py dashboard
```

Happy hunting! 🎰💰
