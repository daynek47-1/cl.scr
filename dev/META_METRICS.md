# Theorycraft: Derived Meta Metrics
**Goal:** Transform raw bonus data into strategic "Meta" intelligence.

These metrics go beyond simple "PV" (Perceived Value) to analyze trends, network behavior, and player efficiency. They are "derived" because they require aggregating data over time or across multiple entities.

## 1. Player Profitability Metrics (The "Grinder" Stats)
*Focus: Is this worth my time?*

### 1.1 Effective Hourly Rate (EHR)
*How much money am I making per hour of play?*
- **Formula:** `PV_Score / Estimated_Clearance_Time`
- **Derivation:**
  - `Total_Wager = Bonus_Amount * Rollover`
  - `Est_Time = Total_Wager / (Avg_Bet_Size * Hands_Per_Hour)`
  - *Standard Assumptions:* $5 bet, 300 spins/hour (slots) or 50 hands/hour (blackjack).
- **Utility:** Filters out high-PV bonuses that take 100+ hours to clear (grind traps).

### 1.2 Risk-Adjusted Value (RAV)
*Is the variance worth the reward?*
- **Formula:** `PV_Score * (1 - (Rollover / 100))`
- **Concept:** Penalizes high variance. A 60x rollover has huge variance (high risk of busting before clearing) compared to a 10x rollover, even if the raw math says the PV is similar.
- **Utility:** Identifies "safe" money vs. "lottery tickets".

### 1.3 Opportunity Cost Index (OCI)
*What am I missing by locking my funds here?*
- **Formula:** `(Deposit_Amount * Market_Interest_Rate) + (Daily_Bankroll_Utility)`
- **Concept:** If a bonus requires a $5000 deposit and locks it for 30 days, that capital cannot be used for other, faster bonuses.
- **Utility:** Critical for managing a limited bankroll.

## 2. Network Intelligence (The "Scout" Stats)
*Focus: What is the casino network doing?*

### 2.1 Mirror Volatility Index (MVI)
*How unstable is this casino's infrastructure?*
- **Formula:** `(Sites_Pruned_Last_7_Days + Sites_Purgatory_Last_7_Days) / Total_Active_Sites`
- **Utility:** High MVI indicates a casino is under heavy attack (DDoS or legal takedowns) or is aggressively rotating domains. Expect dead links.

### 2.2 Generosity Trend (GT)
*Are they tightening or loosening the screws?*
- **Formula:** `Avg(PV_Score_New_Bonuses_Today) - Avg(PV_Score_New_Bonuses_Last_30_Days)`
- **Utility:**
  - **Positive:** Casino is aggressive, running promos (Good time to hunt).
  - **Negative:** Casino is cutting costs (Avoid).

### 2.3 Clone Saturation Rate (CSR)
*Is this a unique offer or copy-paste spam?*
- **Formula:** `Count(Bonuses_With_Same_Fingerprint) / Total_Mirrors_Scraped`
- **Utility:**
  - **High CSR (>90%):** The network is perfectly synced.
  - **Low CSR (<50%):** Fragmentation! Some mirrors have "hidden" or "forgotten" older (potentially better) bonuses that were removed from the main site. **High Value Targets.**

## 3. Operational Metrics (The "Engineer" Stats)
*Focus: Is the scraper efficient?*

### 3.1 Yield Per Proxy (YPP)
*Cost efficiency of infrastructure.*
- **Formula:** `Beatable_Bonuses_Found / Proxy_Cost_Per_Month`
- **Utility:** Determines if premium residential proxies pay for themselves vs. cheap datacenter proxies.

### 3.2 Ghost Rate
*How often are we being served "soft 404s" or empty pages?*
- **Formula:** `Scrapes_With_0_Bonuses / Total_Successful_Scrapes`
- **Utility:** If a site returns HTTP 200 but 0 bonuses, the parser might be broken OR the casino is serving dummy pages to bots. High Ghost Rate = Needs human review.

## 4. Implementation Priorities

### Phase 1: Easy Wins (SQL Only)
1.  **CSR (Clone Saturation):** Simple `GROUP BY` on bonus fingerprints.
2.  **MVI (Volatility):** Count state changes in `MirrorSite` history.

### Phase 2: Code Required
1.  **EHR (Hourly Rate):** Needs a new `Bonus` property/method to calculate based on assumptions.
2.  **GT (Trends):** Requires a new table or view `daily_stats` to track historical averages efficiently.

### Phase 3: Advanced
1.  **RAV (Risk-Adjusted):** Needs integration with a simulation engine (Monte Carlo) to be truly accurate, or use the heuristic formula above.
