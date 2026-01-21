"""2-Line Console Output System for Real-Time Scraper Monitoring"""
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import os


class TwoLineConsole:
    """
    Manages 2-line console output with rich metrics and emoji indicators

    Line 1: Primary Summary (ProxyH, Count, RunH, Run%, HistH, Bonuses, Stats, Status, URL)
    Line 2: Performance & Diagnostics (CPU, Mem, Latency, Throughput, Worker, Timing)
    """

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        self.run_stats = {
            'success_count': 0,
            'fail_count': 0,
            'total_count': 0,
            'bonuses_found': 0,
            'error_count': 0
        }
        self.latencies = []
        self.throughput_samples = []
        self.last_sample_time = time.time()

    def get_health_gradient(self, percentage: float) -> str:
        """
        12-step health gradient from red to green
        0-9%: 🟥, 10-19%: 🔴, 20-24%: ❤️
        25-34%: 🟧, 35-44%: 🟠, 45-49%: 🧡
        50-59%: 🟨, 60-69%: 🟡, 70-74%: 💛
        75-84%: 🟩, 85-94%: 🟢, 95-100%: 💚
        """
        if percentage < 10:
            return '🟥'
        elif percentage < 20:
            return '🔴'
        elif percentage < 25:
            return '❤️'
        elif percentage < 35:
            return '🟧'
        elif percentage < 45:
            return '🟠'
        elif percentage < 50:
            return '🧡'
        elif percentage < 60:
            return '🟨'
        elif percentage < 70:
            return '🟡'
        elif percentage < 75:
            return '💛'
        elif percentage < 85:
            return '🟩'
        elif percentage < 95:
            return '🟢'
        else:
            return '💚'

    def get_status_icon(self, success: bool) -> str:
        """Get status icon: ✅ for success, ⛔ for failure"""
        return '✅' if success else '⛔'

    def get_status_text(self, success: bool, error_code: Optional[str] = None) -> str:
        """Get status text: DONE or error code"""
        if success:
            return 'DONE'
        elif error_code:
            return f'E{error_code}'
        else:
            return 'FAIL'

    def update_stats(self, success: bool, bonuses: int = 0, error: bool = False):
        """Update run statistics"""
        self.run_stats['total_count'] += 1
        if success:
            self.run_stats['success_count'] += 1
            self.run_stats['bonuses_found'] += bonuses
        else:
            self.run_stats['fail_count'] += 1
        if error:
            self.run_stats['error_count'] += 1

    def add_latency(self, latency: float):
        """Add latency sample"""
        self.latencies.append(latency)
        # Keep only last 50 samples
        if len(self.latencies) > 50:
            self.latencies.pop(0)

    def get_avg_latency(self) -> float:
        """Get average latency"""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    def calculate_throughput(self) -> float:
        """Calculate current throughput (items/second)"""
        current_time = time.time()
        elapsed = current_time - self.last_sample_time
        if elapsed > 0:
            throughput = 1.0 / elapsed
            self.throughput_samples.append(throughput)
            # Keep only last 20 samples
            if len(self.throughput_samples) > 20:
                self.throughput_samples.pop(0)
            self.last_sample_time = current_time
            return throughput
        return 0.0

    def get_avg_throughput(self) -> float:
        """Get average throughput"""
        return sum(self.throughput_samples) / len(self.throughput_samples) if self.throughput_samples else 0.0

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return self.process.cpu_percent(interval=0.1)
        except:
            return 0.0

    def get_memory_usage(self) -> str:
        """Get current memory usage in MB"""
        try:
            mem = self.process.memory_info().rss / (1024 * 1024)  # Convert to MB
            return f"{int(mem)}m"
        except:
            return "0m"

    def format_elapsed(self) -> str:
        """Format elapsed time as MM:SS or HHhMMm"""
        elapsed = time.time() - self.start_time
        if elapsed < 3600:  # Less than 1 hour
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes:02d}m{seconds:02d}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h{minutes:02d}m"

    def estimate_eta(self, total_sites: int) -> str:
        """Estimate completion time"""
        if self.run_stats['total_count'] == 0:
            return "--:--"

        elapsed = time.time() - self.start_time
        avg_time_per_site = elapsed / self.run_stats['total_count']
        remaining_sites = total_sites - self.run_stats['total_count']
        eta_seconds = remaining_sites * avg_time_per_site

        eta_time = datetime.now() + timedelta(seconds=eta_seconds)
        return eta_time.strftime("%H:%M")

    def print_two_line(
        self,
        count: int,
        total_sites: int,
        url: str,
        worker_id: int,
        success: bool,
        bonuses_this_site: int,
        latency: float,
        proxy_health: float = 100.0,
        hist_health: float = 100.0,
        error_code: Optional[str] = None
    ):
        """
        Print the 2-line console output

        Line 1: [ProxyH][Count][RunH][Run%][HistH][Bonuses/Total]📊[Success/Fail]❌[Err]✅[Status]🌐[URL]
        Line 2: 🖥️[CPU]💾[Mem]📶[Lat]/[Avg]🚀[Thru]/[Avg]👷[Wid]⏱️[Elapsed]/[Total] @[ETA]
        """
        # Update statistics
        self.update_stats(success, bonuses_this_site, error_code is not None)
        self.add_latency(latency)
        throughput = self.calculate_throughput()

        # Calculate percentages and health indicators
        run_percentage = (self.run_stats['success_count'] / self.run_stats['total_count'] * 100) if self.run_stats['total_count'] > 0 else 0

        proxy_health_icon = self.get_health_gradient(proxy_health)
        run_health_icon = self.get_health_gradient(run_percentage)
        hist_health_icon = self.get_health_gradient(hist_health)

        status_icon = self.get_status_icon(success)
        status_text = self.get_status_text(success, error_code)

        # Get performance metrics
        cpu = int(self.get_cpu_usage())
        mem = self.get_memory_usage()
        avg_lat = self.get_avg_latency()
        avg_thru = self.get_avg_throughput()
        elapsed = self.format_elapsed()
        eta = self.estimate_eta(total_sites)

        # Truncate URL if too long
        display_url = url.replace('https://', '').replace('http://', '')
        if len(display_url) > 30:
            display_url = display_url[:27] + '...'

        # Line 1: Primary Summary
        line1 = (
            f"{proxy_health_icon}"
            f"{count:03d}"
            f"{run_health_icon}"
            f"{int(run_percentage):03d}%"
            f"{hist_health_icon}"
            f"{bonuses_this_site:03d}/{self.run_stats['bonuses_found']:03d}"
            f"📊{self.run_stats['success_count']:03d}/{self.run_stats['fail_count']:03d}"
            f"❌{self.run_stats['error_count']}"
            f"{status_icon}{status_text}"
            f"🌐{display_url}"
        )

        # Line 2: Performance & Diagnostics
        line2 = (
            f"🖥️{cpu:02d}%"
            f"💾{mem}"
            f"📶{latency:.1f}/{avg_lat:.1f}"
            f"🚀{throughput:.1f}/{avg_thru:.1f}"
            f"👷{worker_id}"
            f"⏱️{elapsed} @{eta}"
        )

        # Print both lines
        print(f"\r{line1}")
        print(f"{line2}")
        print()  # Blank line for separation

    def print_header(self):
        """Print header explaining the format"""
        print("=" * 80)
        print("🎰 Casino Bonus Intelligence Engine - Live Monitoring")
        print("=" * 80)
        print()

    def print_summary(self):
        """Print final summary"""
        print()
        print("=" * 80)
        print("📊 SCRAPE RUN SUMMARY")
        print("=" * 80)
        print(f"Total Sites Checked: {self.run_stats['total_count']}")
        print(f"Successful: {self.run_stats['success_count']}")
        print(f"Failed: {self.run_stats['fail_count']}")
        print(f"Success Rate: {(self.run_stats['success_count'] / self.run_stats['total_count'] * 100) if self.run_stats['total_count'] > 0 else 0:.1f}%")
        print(f"Bonuses Found: {self.run_stats['bonuses_found']}")
        print(f"Errors Encountered: {self.run_stats['error_count']}")
        print(f"Total Time: {self.format_elapsed()}")
        if self.latencies:
            print(f"Average Latency: {self.get_avg_latency():.2f}s")
        if self.throughput_samples:
            print(f"Average Throughput: {self.get_avg_throughput():.2f} sites/s")
        print("=" * 80)
