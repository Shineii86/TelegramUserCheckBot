"""
Core Checker — main orchestrator with thread-safe counters and stop conditions.
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
WHT = "\033[1;37m"
RST = "\033[0m"


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


class Checker:
    """Main orchestrator — runs the username checking loop."""

    def __init__(self, config: Config):
        self.config = config
        self.stats = Stats()
        self._stop = threading.Event()

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
        status, _ = self.client.check(username, delay=self.config.delay)
        return status

    def _print_result(self, status: str, username: str):
        """Print a color-coded result to console."""
        if status == AVAILABLE:
            print(f"{WHT} [+] {GRN}AVAILABLE: {PNK}@{username}{RST}")
        elif status == TAKEN:
            print(f"{WHT} [+] {RED}Taken: {YEL}@{username}{RST}")
        elif status == INVALID:
            print(f"{WHT} [+] {BLU}Invalid: {YEL}@{username}{RST}")
        elif status == RATE_LIMITED:
            print(f"{WHT} [+] {RED}Rate limited: {YEL}@{username}{RST}")
        else:
            print(f"{WHT} [+] {RED}Error: {YEL}@{username}{RST}")

    def _username_source(self) -> Iterator[str]:
        """Get the username source iterator."""
        if self.config.use_wordlist:
            if self.config.wordlist_url:
                usernames = UsernameGenerator.load_from_url(self.config.wordlist_url)
            elif self.config.wordlist_path:
                usernames = UsernameGenerator.load_from_file(self.config.wordlist_path)
            else:
                print(f"{RED}[!] Wordlist enabled but no path or URL provided.{RST}")
                usernames = []

            if not usernames:
                print(f"{RED}[!] No usernames loaded. Falling back to random generation.{RST}")
                yield from self.generator.random_stream()
            else:
                print(f"{WHT}[+] Loaded {len(usernames)} usernames from wordlist.{RST}")
                yield from iter(usernames)
        else:
            yield from self.generator.random_stream()

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
        print(f"{WHT}\n🔍 TelegramUserCheckBot Starting...{RST}")
        print("=" * 50)
        print(f"{WHT}Mode: {self.config.mode} | Workers: {self.config.max_workers} | Delay: {self.config.delay}s{RST}")

        self.notifier.send_start()

        # Open output file
        out_file = None
        if self.config.save_hits:
            out_file = open(self.config.output_file, "a")

        username_iter = self._username_source()
        max_workers = self.config.max_workers

        # Timeout for as_completed must exceed per-request delay + network time
        _wait_timeout = max(self.config.delay * 2, 5.0)

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
                        # Process whatever finished and continue
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

        except KeyboardInterrupt:
            print(f"\n{WHT}[!] Interrupted by user.{RST}")
            self.stop()

        finally:
            if out_file:
                out_file.close()

        # Summary
        print("\n" + "=" * 50)
        print(f"{GRN}✨ Complete!{RST}")
        print(f"{WHT}  Checked:    {self.stats.checked}{RST}")
        print(f"{GRN}  Available:  {self.stats.hits}{RST}")
        print(f"{RED}  Taken:      {self.stats.taken}{RST}")
        print(f"{BLU}  Invalid:    {self.stats.invalid}{RST}")
        print(f"{YEL}  Rate Limit: {self.stats.rate_limited}{RST}")
        print(f"{RED}  Errors:     {self.stats.errors}{RST}")

        if self.config.save_hits and self.stats.available:
            print(f"{WHT}  Saved to:   {self.config.output_file}{RST}")

        self.notifier.send_finish(self.stats.checked, self.stats.hits)
        return self.stats
