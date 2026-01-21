# Meta Metrics: Deep Dive & Strategic Implementation
**Companion to META_METRICS.md**

This document provides the "Director's Commentary" on the derived metrics, explaining the *why*, the *how*, and the *strategy* behind each indicator.

---

## 1. Player Profitability: The "Grinder" Suite

### 1.1 Effective Hourly Rate (EHR)

**The Philosophy:**
A bonus of $1000 looks great, but if it requires 100,000 spins, you are working for pennies. EHR normalizes all bonuses to a "wage."

**The Math:**
$$ \text{EHR} = \frac{\text{PV Score}}{\text{Estimated Hours}} $$

Where:
- `Total Wager` = Bonus Amount $\times$ Rollover
- `Est. Hours` = `Total Wager` / (`Avg Bet` $\times$ `Speed`)

**Standard Assumptions:**
- **Slots:** $5/spin @ 600 spins/hr = $3000 wager/hr
- **Blackjack:** $25/hand @ 50 hands/hr = $1250 wager/hr

**Strategic Application:**
- **Scenario A:** Bonus $500, PV $100. Wager $15,000. (5 hours slots). **EHR = $20/hr.**
- **Scenario B:** Bonus $100, PV $80. Wager $1,000. (0.3 hours slots). **EHR = $266/hr.**
- **Verdict:** **Scenario B is vastly superior** despite the lower face value. It frees up your time to hunt other bonuses.

**Implementation:**
Add a "Game Speed" toggle in the Dashboard Settings to personalize this calc.

---

### 1.2 Risk-Adjusted Value (RAV)

**The Philosophy:**
"Expected Value" (EV/PV) assumes infinite bankroll. In reality, you can go bust. High rollover requirements increase the "Variance" (swings). RAV discounts the value of "risky" bonuses.

**The Math (Heuristic):**
$$ \text{RAV} = \text{PV} \times (1 - \text{Bust Probability}) $$

*Simplified approximation for coding:*
$$ \text{RAV} = \text{PV} \times \left( \frac{100 - \text{Rollover}}{100} \right)^2 $$

**Strategic Application:**
- **Bonus A:** $1000, 10x Rollover. PV=$900. RAV $\approx$ $900 \times 0.9^2 = 729$.
- **Bonus B:** $1000, 60x Rollover. PV=$800. RAV $\approx$ $800 \times 0.4^2 = 128$.
- **Insight:** The high rollover crushes the *real* value because you are likely to lose the bonus before clearing it.

---

### 1.3 Opportunity Cost Index (OCI)

**The Philosophy:**
Liquidity is king. A bonus that locks your deposit for 30 days costs you the ability to use that money elsewhere.

**The Math:**
$$ \text{Cost} = \text{Deposit} \times \left( \frac{\text{Daily Market Return}}{100} \times \text{Lock Days} \right) $$

**Strategic Application:**
- You have $5,000 total bankroll.
- **Bonus:** Deposit $5,000 for $500 bonus. Lock 30 days.
- **Alternative:** You could cycle that $5,000 through 10 different "instant clear" bonuses earning $50 each ($500 total) in just 2 days.
- **Decision:** The "slow" bonus has a massive Opportunity Cost because it halts your operation.

---

## 2. Network Intelligence: The "Scout" Suite

### 2.1 Clone Saturation Rate (CSR) - *The "Orphan Hunter"*

**The Philosophy:**
Casino networks update their sites centrally. However, sometimes a mirror site (e.g., `mirror-74.com`) gets "disconnected" from the central update server. It stays online but stops receiving new (worse) terms.

**The Analysis:**
1. Take a specific Bonus Fingerprint (e.g., "Welcome 2024").
2. Count how many active sites show this bonus.
3. If `Total Active Sites` = 100, and `Bonus Count` = 99... **Who is the missing 1?**

**Strategic Application:**
- **The Anomaly:** Check the 1 site *not* showing the standard bonus.
- **The Prize:** It might still be showing the *old* "Welcome 2023" bonus which had 20x rollover instead of the current 40x.
- **Action:** This is an "Orphan Bonus." **High Priority Target.**

---

### 2.2 Generosity Trend (GT)

**The Philosophy:**
Casinos operate in cycles.
- **Acquisition Phase:** High bonuses, low rollover (Loose).
- **Profit Phase:** Low bonuses, high rollover (Tight).

**The Math:**
Track the **Moving Average of Daily PV** for the entire network.

**Strategic Application:**
- **Trend Line:** If the 7-day moving average crosses *below* the 30-day average, the casino is entering a "Tight" phase.
- **Action:** Stop depositing new money. Clear existing bonuses and wait.
- **Signal:** If the trend spikes up, they are desperate for players. **Aggressive scraping.**

---

## 3. Operational: The "Engineer" Suite

### 3.1 Ghost Rate (Soft Ban Detection)

**The Philosophy:**
Casinos rarely ban IPs outright (403 Forbidden) because they use Cloudflare. Instead, they serve "Soft 404s" – the page loads 200 OK, but the bonus list is empty or shows generic "No bonuses available" text.

**The Detection:**
- Worker reports `Status: Success` (HTTP 200).
- `Bonuses Found` = 0.
- `Historical Avg Bonuses` for this site = 12.

**Strategic Application:**
- **Diagnosis:** If `Bonuses Found` drops to 0 instantly across all proxies, the layout changed.
- **Diagnosis:** If only *specific* proxies return 0, those IPs are "Ghosted."
- **Action:** Automatically retire those proxies without human intervention.

---

## 4. Summary of Metrics

| Metric | Type | Question Answered | Actionable Value |
| :--- | :--- | :--- | :--- |
| **EHR** | Profit | "Is this worth my time?" | Prioritizes fast/easy bonuses. |
| **RAV** | Risk | "Will I go bust?" | Filters high-variance traps. |
| **OCI** | Finance | "Is my money stuck?" | Manages cash flow liquidity. |
| **CSR** | Network | "Are there glitches?" | Finds rare "Orphan" bonuses. |
| **GT** | Trend | "Is the casino tightening?" | Times the market entry/exit. |
| **Ghost**| Ops | "Am I soft-banned?" | Automates proxy health. |
