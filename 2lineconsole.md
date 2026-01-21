# 2-Line Console Output Legend

This document outlines the structure and legend for the 2-line console output format.

---

### **Template**

```
[ProxyH][Count][RunH][Run%][HistH][Bonuses/TotalBonusesRun]📊[Success/Fail]❌[Err]✅[StatusText]🌐[URL]
[CPU]💾[Mem]📶[LatCurrent]/[LatAvg]🚀[ThruCurrent]/[ThruAvg]👷[Wid]⏱️[Elapsed]/[TotalDuration] @[ETA]
```

### **Example Output**

```
🟧045🟩080%🟡005/120📊036/009❌0✅DONE🌐newsite.org
🖥️65%💾812m📶0.5/0.8🚀8.1/7.5👷3⏱️61m03s/65m @16:45
```

---

### **Line 1 Legend: Primary Summary**

*   `[ProxyH]`: **Proxy Health** - Quality of the proxy used.
*   `[Count]`: **Attempt Count** - The sequential number of this scrape attempt.
*   `[RunH]`: **Run Health** - Overall success rate of the current run.
*   `[Run%]`: **Run Percentage** - The exact success percentage of the run.
*   `[HistH]`: **Historical Health** - The historical success rate for this specific target.
*   `[Bonuses/TotalBonusesRun]`: **Bonuses** - Bonuses found on this site / Total bonuses found this run.
*   `📊[Success/Fail]`: **Success/Fail Count** - Successful and failed scrapes this run.
*   `❌[Err]`: **Error Count** - Total number of specific errors (e.g., timeouts, bans).
*   `✅[StatusText]`: **Status** - The result of this specific scrape.
*   `🌐[URL]`: **Target URL** - The site that was scraped.

---

### **Line 2 Legend: Performance & Diagnostics**

*   `[CPU]`: **CPU Usage** - The current processor load (e.g., `🖥️65%`).
*   `💾[Mem]`: **Memory Usage** - RAM being consumed by the process (e.g., `💾812m`).
*   `📶[LatCurrent]/[LatAvg]`: **Latency** - Response time for this request vs. the average (e.g., `📶0.5/0.8`).
*   `🚀[ThruCurrent]/[ThruAvg]`: **Throughput** - Current scrapes per second vs. the average (e.g., `🚀8.1/7.5`).
*   `👷[Wid]`: **Worker ID** - The identifier for the specific thread that ran this scrape (e.g., `👷3`).
*   `⏱️[Elapsed]/[TotalDuration] @[ETA]`: **Full Timing** - Elapsed time / Estimated total duration @ Estimated Time of Arrival (e.g., `⏱️61m03s/65m @16:45`).
