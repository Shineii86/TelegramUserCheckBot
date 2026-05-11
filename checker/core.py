"""
Core Checker — main orchestrator with thread-safe counters, live progress, and clean output.
"""

import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Iterator

from .config import Config
from .telegram_client import TelegramUsernameClient, AVAILABLE, TAKEN, INVALID, RATE_LIMITED, ERROR
from .telegram_notifier import TelegramNotifier
from .generator import UsernameGenerator
from .proxy import ProxyManager


# ── ANSI Colors ──
RED = "\033[1;31m"
YEL = "\033[1;33m"
GRN = "\033[2;32m"
PNK = "\033[2;35m"
BLU = "\033[2;34m"
CYN = "\033[2;36m"
WHT = "\033[1;37m"
DIM = "\033[2m"
RST = "\033[0m"
BOLD = "\033[1m"

# ── Spinner frames ──
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class Stats:
    """Thread-safe counters."""

    def __init__(self):
        self._lock = threading.Lock()
        self.checked = 0
        self.hits = 0
        self.taken = 0
        self.invalid = 0
        self.errors = 0
        self.rate_limited = 0
        self.available: List[str] = []
        self.start_time = 0.0

    def record(self, status: str, username: str) -> bool:
        """Record a check result. Returns True if it was a hit."""
        with self._lock:
            self.checked += 1
            if status == AVAILABLE:
                self.hits += 1
                self.available.append(username)
                return True
            elif status == TAKEN:
                self.taken += 1
            elif status == INVALID:
                self.invalid += 1
            elif status == RATE_LIMITED:
                self.rate_limited += 1
            elif status == ERROR:
                self.errors += 1
            return False

    @property
    def elapsed(self) -> float:
        """Elapsed time since start."""
        if self.start_time:
            return time.time() - self.start_time
        return 0.0

    @property
    def speed(self) -> float:
        """Checks per second."""
        e = self.elapsed
        return self.checked / e if e > 0 else 0.0

    @property
    def hit_rate(self) -> float:
        """Hit rate percentage."""
        return (self.hits / self.checked * 100) if self.checked > 0 else 0.0


class Checker:
    """Main orchestrator — runs the username checking loop."""

    def __init__(self, config: Config):
        self.config = config
        self.stats = Stats()
        self._stop = threading.Event()
        self._spinner_idx = 0

        # Initialize components
        self.proxy_mgr = ProxyManager()
        self.notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)
        self.client = TelegramUsernameClient(config.user_agents, self.proxy_mgr)
        self.generator = UsernameGenerator(
            length=config.username_length,
            chars=config.character_set,
            avoid_start_underscore=config.avoid_start_underscore,
            avoid_end_underscore=config.avoid_end_underscore,
            avoid_double_underscore=config.avoid_double_underscore,
            avoid_start_number=config.avoid_start_number,
        )

    def stop(self):
        """Signal the checker to stop."""
        self._stop.set()

    @property
    def should_stop(self) -> bool:
        """Check if any stop condition is met."""
        if self._stop.is_set():
            return True
        if self.config.mode == "count" and self.stats.checked >= self.config.max_attempts:
            return True
        if self.config.mode == "hits" and self.stats.hits >= self.config.stop_after_hits:
            return True
        return False

    def _check_one(self, username: str) -> str:
        """Check a single username. Returns the status."""
        # Auto-adjust delay if rate limited
        delay = self.config.delay
        if self.config.auto_adjust_delay and self.client.is_rate_limited:
            delay = self.client.recommended_delay
        status, _ = self.client.check(username, delay=delay)
        return status

    def _spinner(self) -> str:
        """Get next spinner frame."""
        frame = SPINNER[self._spinner_idx % len(SPINNER)]
        self._spinner_idx += 1
        return frame

    def _progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Generate a colored progress bar."""
        if total == 0:
            return f"{DIM}{'░' * width}{RST}"
        filled = int(width * current / total)
        bar = f"{GRN}{'█' * filled}{DIM}{'░' * (width - filled)}{RST}"
        return bar

    def _print_banner(self):
        """Print a startup banner."""
        print(f"\n{CYN}{'═' * 50}{RST}")
        print(f"{BOLD}{CYN}  🔍 TelegramUserCheckBot v3.3{RST}")
        print(f"{CYN}{'═' * 50}{RST}")
        print(f"  {WHT}Mode:{RST}     {YEL}{self.config.mode}{RST}")
        print(f"  {WHT}Workers:{RST}  {YEL}{self.config.max_workers}{RST}")
        print(f"  {WHT}Delay:{RST}    {YEL}{self.config.delay}s{RST}")
        print(f"  {WHT}Length:{RST}   {YEL}{self.config.username_length}{RST}")

        if self.config.use_pattern:
            print(f"  {WHT}Pattern:{RST}  {PNK}{self.config.pattern}{RST}")
        elif self.config.generation_mode == "word_combo":
            print(f"  {WHT}Gen Mode:{RST} {PNK}word_combo{RST}")
        elif self.config.generation_mode == "mixed":
            print(f"  {WHT}Gen Mode:{RST} {PNK}mixed{RST}")

        if self.config.use_proxies:
            print(f"  {WHT}Proxies:{RST}  {GRN}enabled{RST}")
        print(f"{CYN}{'─' * 50}{RST}\n")

    def _print_result(self, status: str, username: str):
        """Print a color-coded result to console."""
        spin = self._spinner()
        count = self.stats.checked
        if status == AVAILABLE:
            print(f" {spin} {WHT}[{count}]{RST} {GRN}✅ AVAILABLE:{RST} {PNK}@{username}{RST}")
        elif status == TAKEN:
            print(f" {spin} {WHT}[{count}]{RST} {RED}❌ Taken:{RST} {DIM}@{username}{RST}")
        elif status == INVALID:
            print(f" {spin} {WHT}[{count}]{RST} {BLU}🚫 Invalid:{RST} {DIM}@{username}{RST}")
        elif status == RATE_LIMITED:
            print(f" {spin} {WHT}[{count}]{RST} {YEL}⚠️  Rate limited:{RST} {YEL}@{username}{RST}")
        else:
            print(f" {spin} {WHT}[{count}]{RST} {RED}💥 Error:{RST} {DIM}@{username}{RST}")

    def _print_live_stats(self):
        """Print a compact live stats line (overwrites current line)."""
        s = self.stats
        bar = self._progress_bar(s.checked, max(self.config.max_attempts, s.checked), 15)
        line = (
            f"\r {self._spinner()} "
            f"{bar} "
            f"{WHT}{s.checked}{RST} checked │ "
            f"{GRN}{s.hits} hits{RST} │ "
            f"{DIM}{s.speed:.1f}/s{RST}    "
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def _username_source(self) -> Iterator[str]:
        """Get the username source iterator."""
        if self.config.use_pattern:
            print(f"{WHT}[+] Using pattern:{RST} {PNK}{self.config.pattern}{RST}")
            yield from self.generator.pattern_stream(self.config.pattern)
        elif self.config.use_wordlist:
            if self.config.wordlist_url:
                usernames = UsernameGenerator.load_from_url(self.config.wordlist_url)
            elif self.config.wordlist_path:
                usernames = UsernameGenerator.load_from_file(self.config.wordlist_path)
            else:
                print(f"{RED}[!] Wordlist enabled but no path or URL provided.{RST}")
                usernames = []

            if not usernames:
                print(f"{RED}[!] No usernames loaded. Falling back to generation.{RST}")
                yield from self._get_generator_stream()
            else:
                print(f"{WHT}[+] Loaded {len(usernames)} usernames from wordlist.{RST}")
                yield from iter(usernames)
        else:
            yield from self._get_generator_stream()

    def _get_generator_stream(self) -> Iterator[str]:
        """Get the appropriate generator stream based on config."""
        mode = self.config.generation_mode
        if mode == "word_combo":
            print(f"{WHT}[+] Using word combo generation{RST}")
            return self.generator.word_combo_stream()
        elif mode == "mixed":
            print(f"{WHT}[+] Using mixed generation{RST}")
            return self.generator.mixed_stream()
        else:
            return self.generator.random_stream()

    def run(self) -> Stats:
        """Run the checker. Returns final stats."""
        # Load proxies
        if self.config.use_proxies:
            count = 0
            if self.config.proxy_url:
                count = self.proxy_mgr.load_from_url(self.config.proxy_url)
            elif self.config.proxy_file:
                count = self.proxy_mgr.load_from_file(self.config.proxy_file)
            print(f"{WHT}[+] Loaded {count} proxies.{RST}")

        # Validate
        errors = self.config.validate()
        if errors:
            for e in errors:
                print(f"{RED}[!] {e}{RST}")
            return self.stats

        # Banner
        self._print_banner()
        self.stats.start_time = time.time()

        self.notifier.send_start()

        # Open output file
        out_file = None
        if self.config.save_hits:
            out_file = open(self.config.output_file, "a")

        username_iter = self._username_source()
        max_workers = self.config.max_workers

        # Timeout for as_completed must exceed per-request delay + network time
        _wait_timeout = max(self.config.delay * 2, 5.0)
        _last_progress_notify = 0

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}

                while not self.should_stop:
                    # Submit new tasks to fill the pool
                    while len(futures) < max_workers and not self.should_stop:
                        try:
                            username = next(username_iter)
                        except StopIteration:
                            self.stop()
                            break
                        future = executor.submit(self._check_one, username)
                        futures[future] = username

                    # Wait for at least one to complete
                    if not futures:
                        break

                    try:
                        done = as_completed(futures, timeout=_wait_timeout)
                        completed = list(done)
                    except TimeoutError:
                        completed = [f for f in futures if f.done()]

                    for future in completed:
                        if future not in futures:
                            continue
                        username = futures.pop(future)
                        try:
                            status = future.result()
                        except Exception:
                            status = ERROR

                        is_hit = self.stats.record(status, username)
                        self._print_result(status, username)

                        if is_hit:
                            self.notifier.send_hit(self.stats.hits, username, self.stats.checked)
                            if out_file:
                                out_file.write(username + "\n")
                                out_file.flush()

                        # Periodic progress notifications
                        if (self.config.notify_progress_interval > 0
                                and self.stats.checked - _last_progress_notify >= self.config.notify_progress_interval):
                            _last_progress_notify = self.stats.checked
                            self.notifier.send_progress(
                                self.stats.checked,
                                self.stats.hits,
                                self.config.max_attempts if self.config.mode == "count" else None,
                            )

                    # Print live stats line
                    if self.config.mode == "count":
                        self._print_live_stats()

        except KeyboardInterrupt:
            print(f"\n\n{YEL}[!] Interrupted by user.{RST}")
            self.stop()

        finally:
            if out_file:
                out_file.close()

        # Final summary
        s = self.stats
        print(f"\n\n{CYN}{'═' * 50}{RST}")
        print(f"{BOLD}{CYN}  ✨ Check Complete!{RST}")
        print(f"{CYN}{'═' * 50}{RST}")
        print(f"  {WHT}📊 Checked:{RST}    {BOLD}{s.checked}{RST}")
        print(f"  {WHT}✅ Available:{RST}  {GRN}{BOLD}{s.hits}{RST}")
        print(f"  {WHT}❌ Taken:{RST}      {RED}{s.taken}{RST}")
        print(f"  {WHT}🚫 Invalid:{RST}   {BLU}{s.invalid}{RST}")
        print(f"  {WHT}⚠️  Rate Limit:{RST} {YEL}{s.rate_limited}{RST}")
        print(f"  {WHT}💥 Errors:{RST}    {RED}{s.errors}{RST}")
        print(f"  {WHT}⏱  Time:{RST}      {CYN}{s.elapsed:.1f}s{RST}")
        print(f"  {WHT}⚡ Speed:{RST}     {CYN}{s.speed:.1f}/s{RST}")
        print(f"  {WHT}🎯 Hit Rate:{RST}  {CYN}{s.hit_rate:.1f}%{RST}")

        if self.config.save_hits and s.available:
            print(f"  {WHT}📁 Saved to:{RST}  {PNK}{self.config.output_file}{RST}")

        if s.available:
            print(f"\n  {GRN}{'─' * 40}{RST}")
            print(f"  {GRN}Available Usernames:{RST}")
            for u in s.available:
                print(f"    {GRN}✅ @{u}{RST}")

        print(f"{CYN}{'═' * 50}{RST}\n")

        self.notifier.send_finish(s.checked, s.hits)
        return s
