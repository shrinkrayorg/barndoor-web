import time
import random
import enum
from datetime import datetime, timedelta

# Import Playwright types for type hinting if useful, avoiding runtime crash if not available context context
# (But usually we just rely on duck typing or standard imports)

class NavReason(enum.Enum):
    INITIAL_LOAD = "INITIAL_LOAD"
    OPEN_DETAIL = "OPEN_DETAIL"
    RETURN_TO_RESULTS = "RETURN_TO_RESULTS"
    PAGINATE = "PAGINATE"
    FILTER_CHANGE = "FILTER_CHANGE"
    END_SESSION = "END_SESSION"

class Navigator:
    def __init__(self):
        self.history = []  # Stores (url, timestamp)
        self.nav_budget = 50  # Start with budget
        self.last_nav_time = datetime.min # Allow immediate first action
        
    def navigate_to(self, page, url, reason) -> bool:
        """
        Gated navigation method enforcing all stealth rules.
        Args:
            page: Playwright Page object.
            url: Target URL.
            reason: NavReason enum.
        """
        if self.nav_budget <= 0:
            print("⚠️ Navigation budget exhausted. Ending session.")
            return False

        # Rule A3: No chained navigations (Time separation)
        time_since_last = (datetime.now() - self.last_nav_time).total_seconds()
        if time_since_last < 2.0: # Minimum hard floor
            print("⏳ Chained navigation detected. Enforcing pause.")
            self._dwell(reason) # Force dwell

        # Rule A4: Anti Ping-Pong (A -> B -> A)
        if len(self.history) >= 2:
            prev_url = self.history[-1][0]
            prev_prev_url = self.history[-2][0]
            if url == prev_prev_url and time_since_last < 10:
                print("⚠️ Ping-pong detected. Hesitating extra.")
                time.sleep(random.uniform(2.0, 5.0))

        # Rule A5: Backtracking cost
        if any(h[0] == url for h in self.history):
            print("🔙 Backtracking detected. Slowing down.")
            time.sleep(random.uniform(1.5, 4.0))

        # Rule A9: Budget consumption
        self.nav_budget -= 1
        
        # Rule A8: Progressive Slowdown
        fatigue = min(len(self.history) * 0.1, 3.0) 
        if fatigue > 0:
            time.sleep(fatigue)

        # Rule A6: Stop Decision
        if self._should_stop_early():
            print("🛑 probabilistic stop triggered.")
            return False

        # Execute
        print(f"🧭 Navigating: {reason.value} -> {url}")
        try:
            # Playwright Navigation
            page.goto(url, wait_until='domcontentloaded')
            
            self.history.append((url, datetime.now()))
            self.last_nav_time = datetime.now()
            
            # Rule A2: Mandatory Dwell AFTER load
            self._dwell(reason)
            
            return True
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False

    def _dwell(self, reason):
        """
        Rule A2: Fat-tailed dwell sampler.
        """
        # Base dwell
        base = random.uniform(2.0, 5.0)
        
        # Fat tail (occasional long read)
        if random.random() < 0.1: # 10% chance
            base += random.uniform(5.0, 15.0)
            print("☕ Taking a short break...")
            
        # Contextual modifiers
        if reason == NavReason.OPEN_DETAIL:
            base += random.uniform(3.0, 8.0) # Reading detail
        elif reason == NavReason.RETURN_TO_RESULTS:
            base += random.uniform(1.0, 3.0) # Re-orienting
            
        print(f"  ...dwelling for {base:.1f}s...")
        time.sleep(base)

    def _should_stop_early(self):
        """Rule A6: Probabilistic stop."""
        # Chance increases as budget decreases or history grows
        chance = 0.005 + (len(self.history) * 0.002)
        return random.random() < chance
