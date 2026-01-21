# Exhaustive Reference List of Console Output Values

This list defines every metric, icon, and placeholder value found in the generated layouts, along with its purpose and typical format.

## Core Identifiers \& Health

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`\[ProxyH]` / `🟥`-`💚`|**Proxy Health:** Indicates the reliability/risk level of the proxy. Uses the 12-step gradient.|Real (calc)|Emoji|
|`\[Count]` / `000`|**Scrape Attempt Count:** The sequential index of the current scrape attempt. Zero-padded to 3 digits.|Real|`001` - `999`|
|`\[HistH]` / `🟢`/`🟡`/`🔴`|**Historical Health:** Represents the long-term success rate of the target or proxy.|Simulated|Emoji|
|`\[Bonus]` / `000`|**Bonuses Found:** Number of bonuses found in the current run.|Real|`005`|
|`\[Total]` / `050`|**Total Scrapes/Targets:** The total number of URLs to process in this batch.|Real|`050`|
|`\[RunH]` / `💚`/`🟡`/`🔴`|**Run Health:** Indicator of the current session's success rate. Uses hearts (💚) for high success.|Real (calc)|Emoji|
|`\[Run%]` / `095%`|**Success Percentage:** The percentage of successful scrapes in the current session.|Real (calc)|`000%` - `100%`|

## Status \& Timing

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`\[StatusIcon]` / `✅`/`⛔`|**Status Icon:** Visual indicator of the result. Checkmark for success, Entry Sign for failure.|Real|Emoji|
|`\[StatusText]` / `DONE`/`E404`|**Status Text:** Text description of the result. "DONE" for success, error code (E404, E503) for failure.|Real|`DONE` / `E###`|
|`⏱️`|**Time Icon:** Anchor for timing metrics.|Static|Emoji|
|`\[Elapsed]` / `05:48`|**Elapsed Time:** Time passed since the start of the batch (MM:SS).|Real|`MM:SS`|
|`\[TotalDuration]` / `21m`|**Total Duration:** Estimated or total time for the batch (Minutes).|Real (calc)|`##m`|

## System \& Worker

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`💾`|**Memory Icon:** Anchor for memory usage.|Static|Emoji|
|`\[Sys]` / `\[Mem]` / `202MB`|**Memory Usage:** RAM consumed by the scraper process.|Simulated|`###MB`|
|`🖥️`|**CPU Icon:** Anchor for CPU usage.|Static|Emoji|
|`\[CPU]` / `17%`|**CPU Usage:** Processor load percentage.|Simulated|`##%`|
|`👷`|**Worker Icon:** Anchor for worker ID.|Static|Emoji|
|`\[Worker]` / `\[Wid]` / `05`|**Worker ID:** Identifier for the thread/process performing the scrape.|Real|`01` - `09`|

## Network \& Performance

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`⚡`|**Latency Icon:** Anchor for network speed.|Static|Emoji|
|`\[Latency]` / `\[Lat]` / `01.3`|**Current Latency:** Response time for the current request (Seconds).|Real|`##.#`|
|`\[Avg]` / `02.5`|**Average Latency:** Rolling average response time (Seconds).|Real|`##.#`|
|`🚀`|**Throughput Icon:** Anchor for throughput metrics.|Static|Emoji|
|`\[Throughput]` / `\[Thru]` / `04.4/s`|**Throughput:** Scrapes processed per second.|Simulated|`##.#/s`|

## Statistics \& Errors

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`📊`|**Stats Icon:** Anchor for success/fail counts.|Static|Emoji|
|`\[Success]` / `19`|**Success Count:** Total successful scrapes in this session.|Real|`##`|
|`\[Fail]` / `83`|**Fail Count:** Total failed scrapes in this session.|Real|`##`|
|`❌`|**Error Icon:** Anchor for error count.|Static|Emoji|
|`\[Err]` / `8`|**Error Count:** Count of specific error types (distinct from general fails).|Simulated|`#`|

## Miscellaneous

|Value Representation|Description|Source|Typical Format|
|-|-|-|-|
|`🌐`|**URL Icon:** Anchor for the target URL.|Static|Emoji|
|`\[URL]`|**Target URL:** The domain being scraped.|Real|`example.com`|

---

## Visual Indicators \& Symbolic Logic

This section details the logic behind metrics that rely on visual symbols (emojis) to convey state, quality, or categorization at a glance.

### 1\. Quality \& Health Gradient (12-Step)

Used for both **Run Health** `\[RunH]` and **Proxy Health** `\[ProxyH]`. This metric uses a granular scale of shapes and colors to indicate precise quality tiers.

The logic follows a progression of **Color** (Red -> Orange -> Yellow -> Green) and **Shape** (Square -> Circle -> Heart) as quality increases.

* **For Run Health:** Based on success percentage (Higher = Better).
* **For Proxy Health:** Based on inverted IP Risk Score (Lower Risk = Higher Quality = Better).

|Range|Symbol|Description|Meaning|
|-|:-:|-|-|
|**0% - 9%**|🟥|Red Square|**Critical Failure:** high risk / zero success.|
|**10% - 19%**|🔴|Red Circle|**Very Poor:** significant issues.|
|**20% - 24%**|❤️|Red Heart|**Poor:** slightly better but still critical.|
|**25% - 34%**|🟧|Orange Square|**Low:** approaching functional levels.|
|**35% - 44%**|🟠|Orange Circle|**Below Average:** frequent friction.|
|**45% - 49%**|🧡|Orange Heart|**Marginal:** nearing acceptable threshold.|
|**50% - 59%**|🟨|Yellow Square|**Fair:** functional but degraded.|
|**60% - 69%**|🟡|Yellow Circle|**Good:** standard acceptable performance.|
|**70% - 74%**|💛|Yellow Heart|**Very Good:** above average reliability.|
|**75% - 84%**|🟩|Green Square|**Excellent:** high reliability / low risk.|
|**85% - 94%**|🟢|Green Circle|**Superior:** very clean / stable.|
|**95% - 100%**|💚|Green Heart|**Perfect/Near Perfect:** optimal state.|

### 2\. Operational Status (✅ / ⛔)

Used for the **Status Icon** `\[StatusIcon]`. This provides a binary (Pass/Fail) visual confirmation of the specific request result.

* **✅ Check Mark:** **Success**

  * *Condition:* HTTP 200 OK + Valid Data Parsed.
  * *Meaning:* The specific URL was scraped, and data was extracted successfully. Corresponds to status text "DONE".

* **⛔ No Entry:** **Failure**

  * *Condition:* HTTP 4xx/5xx Error, Timeout, or Ban.
  * *Meaning:* The request failed. Corresponds to error codes like "E404", "E503", or "E000" (Network Error).

### 4\. Metric Anchors (Icons)

These static icons serve as visual delimiters, allowing the user to quickly locate specific data points in the dense text grid without reading labels.

* **⏱️ (Stopwatch):** Marks the **Timing** block (Elapsed / Duration).
* **💾 (Floppy Disk):** Marks the **System Memory** usage.
* **🖥️ (Desktop Computer):** Marks the **CPU** usage.
* **⚡ (High Voltage):** Marks the **Latency/Network Speed**.
* **🚀 (Rocket):** Marks the **Throughput** (items per second).
* **👷 (Construction Worker):** Marks the **Thread/Worker ID**.
* **📊 (Bar Chart):** Marks the **Statistics** (Success/Fail counts).
* **❌ (Cross Mark):** Marks the **Error Count** (specific error instances).
* **🌐 (Globe):** Marks the **Target URL**.

---

## Extended \& Hypothetical Iconography (Experimental)

These symbols are used in advanced layouts to replace text labels entirely or provide secondary state information.

### 1\. Symbolic Status Codes \& Error Mapping

Replaces the standard `E###` text codes with representative imagery for faster cognitive processing.

|Icon|Symbol Name|Replaces|Meaning|Context/Nuance|
|:-:|-|-|-|-|
|🏁|Chequered Flag|`DONE`|**Success**|Request completed and data parsed perfectly.|
|🚧|Construction|`E503`|**Service Unavailable**|Server temporarily overloaded or down for maintenance.|
|👻|Ghost|`E404`|**Not Found**|The resource no longer exists at this endpoint.|
|🛡️|Shield|`E403`|**Forbidden**|Access blocked by WAF, permissions, or geo-restriction.|
|🐌|Snail|`E408`|**Timeout**|Connection established but server failed to respond in time.|
|💣|Bomb|`E500`|**Server Error**|Internal crash on the remote server side.|
|🛑|Stop Sign|`E429`|**Rate Limited**|Too many requests; temporary ban active.|
|🕸️|Spider Web|`E000`|**Network Error**|DNS failure, connection reset, or no internet.|
|🧟|Zombie|`PARTIAL`|**Partial Data**|Request succeeded but returned incomplete/malformed data.|

### 2\. Performance Trends \& Motion

Used alongside **Latency** `\[Lat]` or **Throughput** `\[Thru]` to indicate the velocity and direction of metrics.

|Icon|Meaning|Application|
|:-:|-|-|
|📈|**Rising Badly**|Latency spiking significantly (>20% vs avg).|
|📉|**Improving**|Latency dropping or Throughput increasing.|
|➡️|**Stable**|Metric holding steady within standard deviation.|
|🚀|**Surge**|Throughput unexpectedly high (positive anomaly).|
|🐢|**Lag**|System slowing down due to resource constraints.|

### 3\. Worker \& Thread Identity

Methods to distinguish the thread/process ID `\[Wid]` to trace logs or errors to a specific worker.

* **Circled Numbers:** ① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨ ⑩ ⑪ ⑫

  * *Usage:* Compact, distinct from stats. Good for low thread counts.

* **Faces/Avatars:** 👷(Worker), 🕵️(Spy), 🤖(Bot), 👽(Alien)

  * *Usage:* Assigning a distinct "persona" to each persistent worker.

* **Dice:** 🎲

  * *Usage:* Indicates a worker operating on randomized delays.

### 4\. Compact Count Labels

Alternatives to `📊` for extremely space-constrained layouts.

|Icon|Represents|Logic|
|:-:|-|-|
|✔️|**Success Count**|Number of 200 OK responses.|
|✖️|**Fail Count**|Number of any non-200 responses.|
|➕|**Added**|New items/bonuses discovered this run.|
|➖|**Skipped**|Items skipped due to deduplication.|

### 5\. System Load Indicators

Visual shorthand for `💾` Memory and `🖥️` CPU states.

|Icon|Metric|State|Meaning|
|:-:|-|-|-|
|🧊|System|**Cool**|Low resource usage (<30%).|
|🔥|System|**Hot**|High resource usage (>80%).|
|🧠|Memory|**Thinking**|Heavy processing/parsing operation active.|
|🧹|Memory|**GC**|Garbage collection / Memory cleanup in progress.|

### 6\. Data Quality \& Validation

Icons representing the state of the data *after* it has been fetched.

|Icon|State|Meaning|
|:-:|-|-|
|💎|**Pristine**|Data is complete, valid, and high-value.|
|🏚️|**Broken**|HTML structure was unexpected; parser failed.|
|🗑️|**Junk**|Content was fetched but contained no useful bonuses.|
|📝|**Schema**|Data matched a strict schema validation check.|
|⚖️|**Dupe**|Valid data, but identical to a previous record.|

### 7\. Proxy \& Network Types

Distinguishing the *method* of connection.

|Icon|Type|Meaning|
|:-:|-|-|
|🏢|**Datacenter**|Fast, stable, but easily detected DC proxy.|
|🏠|**Residential**|High-trust ISP/Home IP address.|
|📱|**Mobile**|4G/5G connection (highest trust).|
|🧅|**Tor**|Routed through the Tor network.|
|🔄|**Rotating**|IP changes on every request.|
|📌|**Sticky**|IP remains constant for session duration.|

### 8\. Timing Phases \& Precision

Granular icons for *what* is taking time.

|Icon|Phase|Meaning|
|:-:|-|-|
|⏳|**Queue**|Request is waiting for an available worker slot.|
|📡|**Connect**|DNS resolution and TCP handshake in progress.|
|📥|**Download**|Receiving the response body bytes.|
|⚙️|**Process**|Parsing HTML/JSON after download.|
|💾|**Saving**|Writing results to the database.|

### 9\. Scrape Depth \& Modes

Indicating the scraper's current operational mode.

|Icon|Mode|Meaning|
|:-:|-|-|
|🔍|**Discovery**|Hunting for new URLs or sitemaps.|
|⛏️|**Mining**|Extracting deep data from known pages.|
|📸|**Snapshot**|Archiving full page state/HTML.|
|🩺|**Audit**|Re-checking existing data for changes.|
|⚡|**Speed**|Skipping non-essential checks for velocity.|



