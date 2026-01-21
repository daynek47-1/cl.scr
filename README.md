# 🎰 Casino Bonus Intelligence Engine

A sophisticated, autonomous system for discovering, analyzing, and ranking casino bonuses across mirror site networks using **Perceived Value (PV)** analysis to convey **relative average value** and identify high-utility offers.

## 🎯 Core Concept

This isn't just a bonus scraper - it's a **quantitative intelligence engine** that:

- **Autonomously patrols** vast networks of casino mirror sites
- **Calculates Perceived Value (PV)** to convey the **relative average value** of bonuses
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
- **2-Line Console**: Real-time monitoring with emoji-based health indicators

### 2-Line Console Output

When `QUIET_MODE=true` (default), the engine displays a clean 2-line console format:

```
🟢[100%][12/50][🟢][96%][🟢][143/487]📊[✅12][❌0][ERR0]✅[Active]🌐[https://casino-mirror1.com]
🖥️[15%]💾[2.1GB]📶[1.2s]/[1.5s]🚀[8.3/s]/[7.9/s]👷[W3]⏱️[0:15:22]/[1:45:00] @[2:12:00]
```

**Line 1: Summary Metrics**
- `🟢[100%]` - Proxy health (12-step gradient from 🟥 to 💚)
- `[12/50]` - Current site / Total sites
- `🟢[96%]` - Run health (success rate for this cycle)
- `🟢` - Site history health (based on consecutive failures)
- `[143/487]` - Bonuses found this site / Total bonuses
- `[✅12]` - Successful sites this run
- `[❌0]` - Failed sites this run
- `[ERR0]` - Error count
- `✅[Active]` - Current status
- `🌐[URL]` - Site being processed

**Line 2: Performance Diagnostics**
- `🖥️[15%]` - CPU usage
- `💾[2.1GB]` - Memory usage
- `📶[1.2s]/[1.5s]` - Current latency / Average latency
- `🚀[8.3/s]/[7.9/s]` - Current throughput / Average throughput
- `👷[W3]` - Worker ID
- `⏱️[0:15:22]/[1:45:00]` - Elapsed time / Total estimated time
- `@[2:12:00]` - Estimated completion time

Set `QUIET_MODE=false` in `.env` for verbose logging with full details.

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

# Display Mode
QUIET_MODE=true  # Only show 2-line console output (recommended)

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

The **V14 Algorithm** is the secret sauce - a sophisticated non-linear formula that conveys the **relative average value** of a bonus:

#### The V14 Formula

```python
PV = (10 * log2(bonus_amount + 1) * sqrt(max_withdrawal)) /
     (pow(rollover, 1.25) * log10(bonus_amount + 10))
```

**Why V14 is Superior:**
- **Logarithmic Scaling**: Captures diminishing returns on bonus size
- **Exponential Rollover Penalty**: Models the rapid decay of value as wagering requirements increase
- **Relative Ranking**: Allows for precise comparison between disparate bonus structures
- **Non-Linear**: Better reflects value distribution than simple linear models

**Example 1: High Relative Value**
```
Bonus: $500
Rollover: 25x
Max Withdrawal: $2000

Calculation:
- PV = 115.4 ✅ HIGH VALUE
```

**Example 2: Low Relative Value**
```
Bonus: $100
Rollover: 60x
Max Withdrawal: $200

Calculation:
- PV = 19.6 ❌ POOR (Below value threshold of 20)
```

**Relative Value Thresholds (V14):**
- **Excellent**: PV > 200 and rollover < 30x
- **Good**: PV > 100 or (PV > 50 and rollover < 40x)
- **Fair**: PV > 20
- **Poor**: PV ≤ 20 (low utility)

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

## 🗄️ Database Schema

The system uses SQLAlchemy ORM with the following core models:

### MirrorSite
Tracks casino mirror URLs with health management:
- `health_status`: ACTIVE → PURGATORY → PRUNED
- `consecutive_failures`: Tracks failure count for state transitions
- `last_success`, `last_scraped`: Timestamp tracking
- `merchant_id`: Extracted from site HTML for API calls

### Bonus
Comprehensive bonus data with PV scoring:
- `fingerprint`: SHA256 hash for exact deduplication
- `parent_bonus_id`: Links fuzzy duplicates to parent
- `pv_score`: Calculated beatability score (V14)
- `is_beatable`: Boolean flag for quick filtering
- `expiration_date`: Parsed from bonus text
- `seen_on_sites`: Counter for multi-site tracking
- Financial fields: `bonus_amount`, `rollover`, `max_withdrawal`

### SessionCache
Authentication token management:
- `access_token`, `access_id`: API credentials
- `expires_at`: 6-hour validity period
- `cookies`: Serialized session cookies
- Automatic expiration checking

### ScrapeRun
Complete run cycle tracking:
- `run_type`: standard, retest, or resurrection
- `sites_checked`, `bonuses_found`: Statistics
- `duration_seconds`: Performance metrics
- Links to individual WorkerLog entries

## 📡 API Endpoints

The web dashboard provides a REST API:

### Statistics
```bash
GET /api/stats
# Returns: active sites, total bonuses, beatable count, last run time
```

### Best Bonuses
```bash
GET /api/bonuses/best?limit=20&beatable_only=true
# Returns: Top bonuses ranked by PV score
```

### All Bonuses (Paginated)
```bash
GET /api/bonuses?skip=0&limit=50&min_pv=50&beatable_only=false
# Returns: Filtered bonus list with pagination
```

### Mirror Sites
```bash
GET /api/sites
# Returns: All mirror sites with health status
```

### Trigger Scrape
```bash
POST /api/scrape/run
# Triggers immediate scrape cycle
# Returns: Run statistics
```

### Scrape History
```bash
GET /api/runs?limit=20
# Returns: Recent scrape run history
```

## 🧮 V14 Algorithm Deep Dive

### Component Breakdown

The V14 formula has two main parts:

**Numerator (Reward):**
```python
10 * log2(max_withdrawal + 1) * sqrt(bonus_amount)
```
- `10 *`: Base multiplier for score scaling
- `log2(mw + 1)`: Logarithmic withdrawal scaling (doubling withdrawal doesn't double value)
- `sqrt(ba)`: Square root bonus scaling (bigger bonuses have diminishing per-dollar value)

**Denominator (Penalty):**
```python
pow(rollover, 1.25) * log10(bonus_amount + 10)
```
- `pow(ro, 1.25)`: Exponential rollover penalty (60x is much worse than 30x)
- `log10(ba + 10)`: Size adjustment (prevents huge bonuses from dominating)

### Real-World Examples

**Case Study 1: Why $500 with 30x > $1000 with 50x**
```
Bonus A: $500, 30x rollover, $2000 max withdrawal
PV = (10 * log2(2001) * sqrt(500)) / (pow(30, 1.25) * log10(510))
PV = (10 * 10.97 * 22.36) / (95.39 * 2.71)
PV = 2,453 / 258.5 = 94.9 → Good

Bonus B: $1000, 50x rollover, $2000 max withdrawal
PV = (10 * log2(2001) * sqrt(1000)) / (pow(50, 1.25) * log10(1010))
PV = (10 * 10.97 * 31.62) / (167.88 * 3.00)
PV = 3,469 / 503.6 = 68.9 → Fair

Winner: Bonus A (easier to beat despite lower amount)
```

**Case Study 2: The No-Deposit Trap**
```
No-Deposit: $100, 60x rollover, $50 max withdrawal
PV = (10 * log2(51) * sqrt(100)) / (pow(60, 1.25) * log10(110))
PV = (10 * 5.67 * 10) / (191.4 * 2.04)
PV = 567 / 390.5 = 14.5 → Poor (not beatable)

Reason: High rollover (60x) and restrictive max withdrawal ($50)
```

### Sensitivity Analysis

**Impact of Rollover Changes:**
- 20x → 30x: PV drops ~30%
- 30x → 40x: PV drops ~40%
- 40x → 60x: PV drops ~55% (exponential!)

**Impact of Max Withdrawal:**
- $500 → $1000: PV increases ~15%
- $1000 → $2000: PV increases ~10%
- $2000 → $4000: PV increases ~7% (diminishing returns)

## 🔄 Migration & Upgrade Notes

### V14 Algorithm Migration

If upgrading from linear PV to V14:

1. **Scores will change**: V14 scores are typically 10-20x different
2. **Thresholds updated**: Beatability threshold is now 20 (vs. 0)
3. **Rankings shift**: Some bonuses will rank differently
4. **Database**: No schema changes needed - just recalculate

**Migration Steps:**
```python
# The system automatically uses V14 if USE_V14_FORMULA=true
# On next scrape, all bonuses will be recalculated with V14
# To force immediate recalculation:
python main.py run  # This will update all bonuses
```

### From Other Systems

If migrating from another bonus scraper:

1. **Import Sites**: Add mirror sites via `python main.py add-site <url>`
2. **First Run**: Initial scrape will populate database
3. **Credentials**: Update `.env` with single credential set
4. **Proxies**: Configure proxy list if using
5. **Monitor**: Check first run logs for any parsing issues

## ❓ FAQ

### General

**Q: How many mirror sites should I add?**
A: Start with 5-10, expand to 50-100 for comprehensive coverage. The system handles hundreds efficiently.

**Q: How often should I run scrapes?**
A: Every 6 hours is recommended. Bonuses don't change that frequently.

**Q: What if a site changes its structure?**
A: The API endpoint (/api/v1/index.php) is usually stable. If parsing fails, check the API response structure.

### Technical

**Q: Why V14 instead of linear PV?**
A: V14 models real-world playability better. A $1000 bonus with 60x rollover isn't "beatable" despite high score in linear calculation.

**Q: How does deduplication handle variants?**
A: SHA256 for exact matches, SequenceMatcher for fuzzy (80% threshold), plus safety checks for numbers/Roman numerals.

**Q: Can I run multiple instances?**
A: Yes, but use separate databases. SQLite has write locking - for true multi-process, use PostgreSQL.

**Q: How do I customize the PV formula?**
A: Modify `src/engine/pv_calculator.py` or switch to linear mode and adjust weights in `.env`.

### Troubleshooting

**Q: "ModuleNotFoundError" when running**
A: Run `pip install -r requirements.txt` to install all dependencies.

**Q: "401 Unauthorized" errors**
A: Check credentials in `.env`. Session may have expired, system will auto-retry with fresh login.

**Q: Database locked errors**
A: Only run one scraper instance per database. For concurrent access, use PostgreSQL.

**Q: High CPU usage**
A: Reduce WORKER_COUNT in `.env`. Default is 5, try 2-3 for lower-spec systems.

## 🔬 Development

### Running Tests

```bash
# Run unit tests (when implemented)
pytest tests/

# Test V14 calculation
python -c "from src.engine.pv_calculator import PVCalculator; calc = PVCalculator(); print(calc.calculate(500, 30, 2000))"
```

### Development Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Use linear PV for easier debugging
export USE_V14_FORMULA=false

# Single worker for sequential debugging
export WORKER_COUNT=1
```

### Adding New Parsers

To support additional casino API formats:

1. Extend `api_client.py` → `extract_bonuses_from_response()`
2. Add new response path patterns
3. Test with actual API responses
4. Update `parse_bonus()` for new field names

Example:
```python
# In api_client.py
possible_paths = [
    ['data', 'bonuses'],
    ['result', 'offers'],  # Add new path
]
```

## 🎓 Best Practices

### Production Deployment

1. **Use V14 Algorithm**: More accurate for real-world scenarios
2. **Enable Proxies**: Rotate IPs to avoid detection/blocking
3. **Monitor Logs**: Check `scrape_runs` table for patterns
4. **Database Backups**: Regular SQLite backups (or use PostgreSQL)
5. **Deduplication Rate**: Should stabilize at 70-80%
6. **Site Health**: Active sites should remain >90% of total

### Optimization Tips

- **Increase Workers**: Up to 10 for high-spec machines
- **Decrease Delays**: Minimum 1s if using good proxies
- **Purgatory Tuning**: Lower threshold (3 failures) for aggressive testing
- **Database Cleanup**: Periodically remove old expired bonuses

### Monitoring

Key metrics to track:
- **Sites Success Rate**: Should be >85%
- **New Bonuses per Run**: Should be consistent
- **PV Score Distribution**: Most beatable bonuses should be PV 50-150
- **Worker Efficiency**: All workers should complete ~same time

## 📚 Additional Resources

### Understanding Casino Bonuses

- **Rollover/Wagering**: Amount you must bet before withdrawal (e.g., 30x $100 = $3000 wagering)
- **Max Withdrawal**: Maximum you can cash out from bonus winnings
- **Game Restrictions**: Slots usually count 100%, table games 10-20%
- **Time Limits**: Typically 7-30 days to meet requirements

### Mathematical Background

The V14 algorithm is based on:
- **Information Theory**: log2 for doubling relationships
- **Diminishing Returns**: sqrt for sublinear scaling
- **Exponential Penalties**: pow for accelerating difficulty
- **Normalization**: log10 for size adjustment

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
