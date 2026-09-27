import os, csv, json, time, uuid, threading, queue, base64, ctypes, math
from pathlib import Path
from datetime import datetime, timezone, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

try:
    import ttkbootstrap as tb
    HAVE_BOOT = True
except Exception:
    HAVE_BOOT = False

BOOT_THEMES = ["darkly", "cyborg", "superhero", "solar", "vapor", "flatly", "litera", "morph", "journal", "minty"]
LEGACY_THEMES = ["System", "Light", "Dark", "Midnight Blue"]

APP = "Coinbase Multi-Crypto Maker Bot v2.2"
SUPPORTED_PRODUCTS = ["BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD"]
PRODUCT = "BTC-USD"

DEFAULT_SETTINGS = {
    "ORDER_USD": 15.00, "DESIRED_NET_PROFIT_PCT": 0.0050, "STOP_LOSS_PCT": 0.0030,
    "MAX_HOLD_MINUTES": 45, "MAX_TRADES_DAY": 10, "MAX_LOSSES": 3, "MAX_DAILY_LOSS": 25.0,
    "ENTRY_TIMEOUT_MINUTES": 10, "POLL": 5, "FAST_EMA": 5, "SLOW_EMA": 12,
    "MIN_RET": 0.0010, "MAX_RET": 0.0150, "MIN_TREND": 0.0005, "SAFETY_MARGIN": 0.0005, "REPRICE_SECONDS": 20,
    # v2.0 strategy-quality additions
    "TREND_EMA": 26, "ATR_PERIOD": 14, "ATR_MIN_MULT": 0.3, "ATR_MAX_MULT": 3.0,
    "VOLUME_LOOKBACK": 20, "VOLUME_MIN_RATIO": 0.5,
    "LOSS_COOLDOWN_MINUTES": 15, "SPREAD_GUARD_RATIO": 0.5,
    "VOL_SCALE_ENABLED": 1, "VOL_SCALE_MIN_MULT": 0.4, "VOL_SCALE_ATR_REF": 0.0060,
    "ERROR_CIRCUIT_BREAKER": 5,
    # v2.1: hourly trend gate (dual-timeframe confirmation)
    "HTF_ENABLED": 1, "HTF_TREND_EMA": 20, "HTF_REFRESH_MINUTES": 15,
    # v2.2 order management + market intelligence
    "PRODUCT": "BTC-USD", "FUNDING_RESERVE_USD": 0.25, "FUNDING_RETRY_LIMIT": 1,
    "FUNDING_FAILURE_PAUSE": 3, "CANCEL_CONFIRM_SECONDS": 12, "LEARNING_ENABLED": 1,
}

DATA = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "CoinbaseBTCMakerBot"
DATA.mkdir(parents=True, exist_ok=True)
CREDS = DATA / "credentials.dat"
SETTINGS = DATA / "settings.json"

def product_paths(product):
    tag = product.lower().replace("-", "_")
    return DATA / f"{tag}_trades.csv", DATA / f"{tag}_signals.csv", DATA / f"{tag}_orders.csv", DATA / f"{tag}_intelligence.csv"

TRADES, SIGNALS, ORDERS, INTELLIGENCE = product_paths(PRODUCT)

TRADES_HEADER = ["time", "mode", "product", "action", "order_type", "ticker", "fill_price", "base_size", "value", "fee", "net_pnl", "reason", "order_id", "entry_regime", "entry_confidence"]
ORDERS_HEADER = ["time", "mode", "event", "side", "order_id", "price", "requested_btc", "filled_btc", "avg_fill_price", "fee", "status", "note"]
SIGNALS_HEADER = ["time", "product", "candle", "close", "return", "fast", "slow", "trend", "trend_ema", "atr_pct", "trend_ok", "vol_ok", "atr_ok", "htf_ok", "regime", "confidence", "signal"]
INTEL_HEADER = ["time", "product", "regime", "confidence", "spread_pct", "trend", "return", "atr_pct", "recommendation"]


def load_settings():
    x = DEFAULT_SETTINGS.copy()
    try:
        x.update(json.loads(SETTINGS.read_text()))
    except Exception:
        pass
    return x


CFG = load_settings()


def apply_settings():
    global ORDER_USD, DESIRED_NET_PROFIT_PCT, STOP_LOSS_PCT, MAX_HOLD_MINUTES, MAX_TRADES_DAY, MAX_LOSSES, MAX_DAILY_LOSS
    global ENTRY_TIMEOUT_MINUTES, POLL, FAST_EMA, SLOW_EMA, MIN_RET, MAX_RET, MIN_TREND
    global TREND_EMA, ATR_PERIOD, ATR_MIN_MULT, ATR_MAX_MULT, VOLUME_LOOKBACK, VOLUME_MIN_RATIO
    global LOSS_COOLDOWN_MINUTES, SPREAD_GUARD_RATIO, VOL_SCALE_ENABLED, VOL_SCALE_MIN_MULT, VOL_SCALE_ATR_REF, ERROR_CIRCUIT_BREAKER
    global HTF_ENABLED, HTF_TREND_EMA, HTF_REFRESH_MINUTES, PRODUCT, TRADES, SIGNALS, ORDERS, INTELLIGENCE
    global FUNDING_RESERVE_USD, FUNDING_RETRY_LIMIT, FUNDING_FAILURE_PAUSE, CANCEL_CONFIRM_SECONDS, LEARNING_ENABLED
    ORDER_USD = float(CFG["ORDER_USD"]); DESIRED_NET_PROFIT_PCT = float(CFG["DESIRED_NET_PROFIT_PCT"]); STOP_LOSS_PCT = float(CFG["STOP_LOSS_PCT"])
    MAX_HOLD_MINUTES = int(CFG["MAX_HOLD_MINUTES"]); MAX_TRADES_DAY = int(CFG["MAX_TRADES_DAY"]); MAX_LOSSES = int(CFG["MAX_LOSSES"]); MAX_DAILY_LOSS = float(CFG["MAX_DAILY_LOSS"])
    ENTRY_TIMEOUT_MINUTES = int(CFG["ENTRY_TIMEOUT_MINUTES"]); POLL = int(CFG["POLL"]); FAST_EMA = int(CFG["FAST_EMA"]); SLOW_EMA = int(CFG["SLOW_EMA"])
    MIN_RET = float(CFG["MIN_RET"]); MAX_RET = float(CFG["MAX_RET"]); MIN_TREND = float(CFG["MIN_TREND"])
    TREND_EMA = int(CFG.get("TREND_EMA", 26)); ATR_PERIOD = int(CFG.get("ATR_PERIOD", 14))
    ATR_MIN_MULT = float(CFG.get("ATR_MIN_MULT", 0.3)); ATR_MAX_MULT = float(CFG.get("ATR_MAX_MULT", 3.0))
    VOLUME_LOOKBACK = int(CFG.get("VOLUME_LOOKBACK", 20)); VOLUME_MIN_RATIO = float(CFG.get("VOLUME_MIN_RATIO", 0.5))
    LOSS_COOLDOWN_MINUTES = int(CFG.get("LOSS_COOLDOWN_MINUTES", 15)); SPREAD_GUARD_RATIO = float(CFG.get("SPREAD_GUARD_RATIO", 0.5))
    VOL_SCALE_ENABLED = bool(int(float(CFG.get("VOL_SCALE_ENABLED", 1)))); VOL_SCALE_MIN_MULT = float(CFG.get("VOL_SCALE_MIN_MULT", 0.4))
    VOL_SCALE_ATR_REF = float(CFG.get("VOL_SCALE_ATR_REF", 0.006)); ERROR_CIRCUIT_BREAKER = int(CFG.get("ERROR_CIRCUIT_BREAKER", 5))
    HTF_ENABLED = bool(int(float(CFG.get("HTF_ENABLED", 1)))); HTF_TREND_EMA = int(CFG.get("HTF_TREND_EMA", 20)); HTF_REFRESH_MINUTES = int(CFG.get("HTF_REFRESH_MINUTES", 15))
    PRODUCT = str(CFG.get("PRODUCT", "BTC-USD")).upper()
    if PRODUCT not in SUPPORTED_PRODUCTS: PRODUCT = "BTC-USD"
    FUNDING_RESERVE_USD = float(CFG.get("FUNDING_RESERVE_USD", 0.25)); FUNDING_RETRY_LIMIT = int(CFG.get("FUNDING_RETRY_LIMIT", 1))
    FUNDING_FAILURE_PAUSE = int(CFG.get("FUNDING_FAILURE_PAUSE", 3)); CANCEL_CONFIRM_SECONDS = int(CFG.get("CANCEL_CONFIRM_SECONDS", 12))
    LEARNING_ENABLED = bool(int(float(CFG.get("LEARNING_ENABLED", 1))))
    TRADES, SIGNALS, ORDERS, INTELLIGENCE = product_paths(PRODUCT)


apply_settings()


def now():
    return datetime.now(timezone.utc)


def sf(v, d=0):
    try:
        return float(v)
    except Exception:
        return d


def dd(x):
    if isinstance(x, dict):
        return x
    if hasattr(x, "to_dict"):
        return x.to_dict()
    try:
        return dict(x)
    except Exception:
        return {}


def ema(a, n):
    if len(a) < n:
        return None
    k = 2 / (n + 1); r = a[0]
    for x in a[1:]:
        r = k * x + (1 - k) * r
    return r


def round_down(x, n=8):
    p = 10 ** n
    return math.floor(x * p) / p


def ensure_csv(path, header):
    if not path.exists():
        with path.open("w", newline="") as f:
            csv.writer(f).writerow(header)
        return
    try:
        with path.open("r", newline="") as f:
            first = next(csv.reader(f), None)
        if first != header:
            backup = path.with_name(path.stem + "_pre_v2" + path.suffix)
            if not backup.exists():
                path.rename(backup)
            with path.open("w", newline="") as f:
                csv.writer(f).writerow(header)
    except Exception:
        pass


# ---------- Windows DPAPI credential storage (unchanged from v1.x) ----------
class BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def enc(s):
    b = s.encode()
    ib = BLOB(len(b), ctypes.cast(ctypes.create_string_buffer(b), ctypes.POINTER(ctypes.c_char)))
    ob = BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(ib), APP, None, None, None, 0, ctypes.byref(ob)):
        raise ctypes.WinError()
    try:
        return base64.b64encode(ctypes.string_at(ob.pbData, ob.cbData)).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(ob.pbData)


def dec(s):
    b = base64.b64decode(s)
    ib = BLOB(len(b), ctypes.cast(ctypes.create_string_buffer(b), ctypes.POINTER(ctypes.c_char)))
    ob = BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(ib), None, None, None, None, 0, ctypes.byref(ob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(ob.pbData, ob.cbData).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(ob.pbData)


def save_creds(k, s):
    CREDS.write_text(enc(json.dumps({"k": k, "s": s})))


def load_creds():
    try:
        x = json.loads(dec(CREDS.read_text()))
        return x["k"], x["s"]
    except Exception:
        return "", ""


# ---------- Persistent bot state ----------
class S:
    def __init__(self):
        self.position = False; self.entry_price = 0.; self.btc = 0.; self.entry_value = 0.; self.entry_fee = 0.; self.entry_time = None
        self.entry_order = None; self.tp_order = None; self.tp_price = 0.
        self.day = now().date().isoformat(); self.pnl = 0.; self.trades = 0; self.losses = 0; self.last_candle = None
        self.paper_usd = 1000.; self.paper_btc = 0.
        self.cooldown_until = None
        self.entry_regime = "UNKNOWN"; self.entry_confidence = 0.0

    def reset(self):
        d = now().date().isoformat()
        if d != self.day:
            self.day = d; self.pnl = 0.; self.trades = 0; self.losses = 0

    def save(self):
        state = DATA / f"{PRODUCT.lower().replace('-', '_')}_state.json"
        t = state.with_suffix(".tmp")
        t.write_text(json.dumps(self.__dict__, indent=2))
        t.replace(state)

    @classmethod
    def load(cls):
        s = cls()
        try:
            state = DATA / f"{PRODUCT.lower().replace('-', '_')}_state.json"
            x = json.loads(state.read_text())
            for k, v in x.items():
                if hasattr(s, k):
                    setattr(s, k, v)
        except Exception:
            pass
        return s


# ---------- Trading engine ----------
class Bot:
    def __init__(self, k, sec, live, log):
        from coinbase.rest import RESTClient
        self.c = RESTClient(api_key=k, api_secret=sec, timeout=10)
        self.live = live; self.log = log; self.s = S.load(); self.stop = threading.Event()
        self.manual_flatten = threading.Event()
        self.last_price = 0.0
        self.consecutive_errors = 0
        self.funding_failures = 0; self.funding_paused = False
        self.current_regime = "UNKNOWN"; self.regime_confidence = 0.0; self.last_recommendation = "Collecting data"; self.last_signal = {}
        self.base_increment = 0.00000001; self.quote_increment = 0.01
        self.htf_ok = True; self.htf_checked_at = None; self.htf_close = None; self.htf_ema_val = None
        ensure_csv(TRADES, TRADES_HEADER)
        ensure_csv(SIGNALS, SIGNALS_HEADER)
        ensure_csv(ORDERS, ORDERS_HEADER)
        ensure_csv(INTELLIGENCE, INTEL_HEADER)

    def orderlog(self, event, side="", oid="", price="", req="", filled="", avg="", fee="", status="", note=""):
        with ORDERS.open("a", newline="") as f:
            csv.writer(f).writerow([now().isoformat(), "LIVE" if self.live else "PAPER", event, side, oid, price, req, filled, avg, fee, status, note])
        self.log(f"ORDER {event}: {side} {oid or ''} {note}".strip())

    def price(self):
        return sf(dd(self.c.get_public_product(PRODUCT)).get("price"))

    def book(self):
        x = dd(self.c.get_public_product_book(product_id=PRODUCT, limit=1)); pb = dd(x.get("pricebook", x))
        bids = pb.get("bids", []); asks = pb.get("asks", [])

        def px(z):
            z = dd(z)
            return sf(z.get("price"))

        return (px(bids[0]) if bids else self.price()), (px(asks[0]) if asks else self.price())

    def _need(self):
        return max(FAST_EMA, SLOW_EMA, TREND_EMA, ATR_PERIOD + 1, VOLUME_LOOKBACK + 1, 35)

    def candles(self):
        need = self._need()
        e = now(); st = e - timedelta(minutes=15 * (need + 5))
        limit = min(need + 10, 300)
        x = dd(self.c.get_public_candles(product_id=PRODUCT, start=str(int(st.timestamp())), end=str(int(e.timestamp())), granularity="FIFTEEN_MINUTE", limit=limit))
        a = []
        for q in x.get("candles", []):
            q = dd(q)
            a.append({"start": int(q["start"]), "open": sf(q.get("open")), "close": sf(q.get("close")), "high": sf(q.get("high")), "low": sf(q.get("low")), "volume": sf(q.get("volume"))})
        a.sort(key=lambda z: z["start"]); cut = int(time.time()) // 900 * 900
        return [z for z in a if z["start"] < cut]

    def signal(self):
        a = self.candles()
        if len(a) < self._need():
            return None
        q = a[-1]; cl = [z["close"] for z in a]
        r = q["close"] / q["open"] - 1
        f = ema(cl[-FAST_EMA:], FAST_EMA); sl = ema(cl[-SLOW_EMA:], SLOW_EMA); tr = f / sl - 1
        trend_ema = ema(cl[-TREND_EMA:], TREND_EMA)

        trs = []
        for i in range(1, len(a)):
            h = a[i]["high"]; lo = a[i]["low"]; pc = a[i - 1]["close"]
            if h and lo:
                trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
        atr = ema(trs[-ATR_PERIOD:], ATR_PERIOD) if len(trs) >= ATR_PERIOD else None
        atr_pct = (atr / q["close"]) if (atr and q["close"]) else None

        vols = [z["volume"] for z in a]
        avg_vol = (sum(vols[-VOLUME_LOOKBACK - 1:-1]) / VOLUME_LOOKBACK) if len(vols) >= VOLUME_LOOKBACK + 1 else None
        cur_vol = vols[-1] if vols else 0

        trend_ok = trend_ema is not None and q["close"] >= trend_ema
        atr_ok = True if not atr_pct else (ATR_MIN_MULT * atr_pct <= r <= ATR_MAX_MULT * atr_pct)
        vol_ok = True if not avg_vol else (cur_vol >= VOLUME_MIN_RATIO * avg_vol)

        buy = (MIN_RET <= r <= MAX_RET) and (tr >= MIN_TREND) and trend_ok and atr_ok and vol_ok
        return {"start": q["start"], "close": q["close"], "r": r, "f": f, "sl": sl, "tr": tr,
                "trend_ema": trend_ema, "atr_pct": atr_pct, "trend_ok": trend_ok, "vol_ok": vol_ok, "atr_ok": atr_ok,
                "buy": buy}

    def refresh_htf(self):
        """Higher-timeframe (hourly) trend gate: only lets 15m entries through when
        price is above a longer hourly EMA. Cached and refreshed at most every
        HTF_REFRESH_MINUTES, since an hourly trend doesn't need checking every poll."""
        if not HTF_ENABLED:
            self.htf_ok = True
            return
        if self.htf_checked_at and (now() - self.htf_checked_at).total_seconds() < HTF_REFRESH_MINUTES * 60:
            return
        try:
            need = HTF_TREND_EMA + 5
            e = now(); st = e - timedelta(hours=need + 2)
            x = dd(self.c.get_public_candles(product_id=PRODUCT, start=str(int(st.timestamp())), end=str(int(e.timestamp())),
                                              granularity="ONE_HOUR", limit=min(need + 10, 300)))
            a = []
            for q in x.get("candles", []):
                q = dd(q); a.append({"start": int(q["start"]), "close": sf(q.get("close"))})
            a.sort(key=lambda z: z["start"]); cut = int(time.time()) // 3600 * 3600
            a = [z for z in a if z["start"] < cut]
            if len(a) >= HTF_TREND_EMA:
                cl = [z["close"] for z in a]
                htf_ema = ema(cl[-HTF_TREND_EMA:], HTF_TREND_EMA)
                self.htf_ok = a[-1]["close"] >= htf_ema
                self.htf_close = a[-1]["close"]; self.htf_ema_val = htf_ema
            self.htf_checked_at = now()
        except Exception as e:
            self.log("Hourly trend check error (keeping previous HTF state): " + str(e))

    def get_order(self, oid):
        return dd(dd(self.c.get_order(oid)).get("order", dd(self.c.get_order(oid))))

    def cancel(self, oid):
        if oid:
            try:
                self.c.cancel_orders(order_ids=[oid])
            except Exception as e:
                self.log("Cancel note: " + str(e))

    def wait_terminal(self, oid, seconds):
        end = time.time() + seconds
        while time.time() < end:
            o = self.get_order(oid); st = str(o.get("status", "")).upper(); size = sf(o.get("filled_size")); avg = sf(o.get("average_filled_price"))
            if st in ("FILLED", "CANCELLED", "EXPIRED", "FAILED") or (size > 0 and avg > 0 and o.get("settled") is True):
                return o
            self.stop.wait(1)
        return self.get_order(oid)

    def fill(self, o):
        size = sf(o.get("filled_size")); avg = sf(o.get("average_filled_price")); fee = sf(o.get("total_fees")); val = sf(o.get("filled_value")) or size * avg
        return size, avg, fee, val

    def refresh_product_rules(self):
        try:
            d = dd(self.c.get_public_product(PRODUCT))
            self.base_increment = sf(d.get("base_increment"), 0.00000001) or 0.00000001
            self.quote_increment = sf(d.get("quote_increment"), 0.01) or 0.01
        except Exception as e:
            self.log("Product-rule refresh note: " + str(e))

    def floor_increment(self, value, increment):
        if increment <= 0: return value
        return math.floor((value + 1e-15) / increment) * increment

    def available_balance(self, currency):
        x = dd(self.c.get_accounts(limit=250)).get("accounts", [])
        total = 0.0
        for a in x:
            a = dd(a)
            if str(a.get("currency", "")).upper() == currency.upper():
                total += sf(dd(a.get("available_balance", {})).get("value"))
        return total

    def safe_buy_size(self, requested_usd, bid):
        available = self.available_balance("USD") if self.live else self.s.paper_usd
        spend = min(requested_usd, max(0.0, available - FUNDING_RESERVE_USD))
        base = self.floor_increment(spend / max(bid, 1e-12), self.base_increment)
        return base, spend, available

    def confirmed_cancel(self, oid):
        if not oid: return True
        self.cancel(oid)
        end = time.time() + CANCEL_CONFIRM_SECONDS
        while time.time() < end and not self.stop.is_set():
            try:
                o = self.get_order(oid); st = str(o.get("status", "")).upper()
                if st in ("CANCELLED", "EXPIRED", "FAILED", "FILLED"):
                    return True
            except Exception: pass
            self.stop.wait(0.5)
        return False

    def rejection_reason(self, response):
        er = dd(response.get("error_response", {}))
        return str(er.get("error") or er.get("preview_failure_reason") or "UNKNOWN").upper()

    def classify_regime(self, sg):
        tr = sf(sg.get("tr")); r = sf(sg.get("r")); atr = sf(sg.get("atr_pct"))
        strength = abs(tr) / max(atr, 0.0001)
        if tr >= max(MIN_TREND, atr * 0.35) and sg.get("trend_ok"):
            regime = "BULL"
        elif tr <= -max(MIN_TREND, atr * 0.35) and not sg.get("trend_ok"):
            regime = "BEAR"
        else:
            regime = "RANGE"
        conf = min(0.99, max(0.35, 0.45 + min(strength, 1.5) * 0.25 + (0.10 if sg.get("vol_ok") else -0.05)))
        return regime, conf

    def learning_recommendation(self, sg, spread_pct=0.0):
        regime, conf = self.classify_regime(sg)
        self.current_regime, self.regime_confidence = regime, conf
        if regime == "BEAR": rec = "TEST MODE: avoid new long maker entries; collect outcomes for comparison."
        elif regime == "RANGE": rec = "TEST MODE: require stronger momentum/edge before long entry; watch adverse-selection fills."
        else: rec = "TEST MODE: long conditions aligned; keep current live parameters unchanged until sample is larger."
        # Learn from this product's completed trades. Recommendations remain advisory only.
        samples = wins = 0; pnl_sum = 0.0
        try:
            if TRADES.exists():
                with TRADES.open("r", newline="") as tf:
                    for row in csv.DictReader(tf):
                        if row.get("action") == "SELL" and row.get("entry_regime") == regime and row.get("net_pnl") not in ("", None):
                            x = float(row["net_pnl"]); samples += 1; pnl_sum += x; wins += int(x > 0)
        except Exception:
            pass
        if samples >= 5:
            wr = wins / samples; avg = pnl_sum / samples
            rec += f" Learned {regime}: {samples} exits, {wr:.0%} profitable, avg net ${avg:+.4f}."
            if avg < 0: rec += " Recommendation: test stricter entry threshold / wider quality filter before changing LIVE settings."
            else: rec += " Recommendation: retain current parameters in test mode and collect more samples."
        else:
            rec += f" Need {max(0, 5-samples)} more {regime} exits before performance-based recommendations."
        self.last_recommendation = rec
        if LEARNING_ENABLED:
            with INTELLIGENCE.open("a", newline="") as f:
                csv.writer(f).writerow([now().isoformat(), PRODUCT, regime, conf, spread_pct, sg.get("tr"), sg.get("r"), sg.get("atr_pct"), rec])
        return regime, conf, rec

    def create_post_only(self, side, base, price, note=""):
        base = self.floor_increment(base, self.base_increment)
        price = self.floor_increment(price, self.quote_increment)
        data = {"client_order_id": f"maker-{side.lower()}-{uuid.uuid4().hex}", "product_id": PRODUCT, "side": side,
                "order_configuration": {"limit_limit_gtc": {"base_size": f"{base:.12f}".rstrip("0").rstrip("."), "limit_price": f"{price:.12f}".rstrip("0").rstrip("."), "post_only": True}}}
        r = dd(self.c.create_order(**data))
        if not r.get("success"):
            self.orderlog("REJECTED", side, "", price, base, status="REJECTED", note=json.dumps(r)[:400])
            err = RuntimeError(f"{side} maker order rejected: " + json.dumps(r)); err.order_response = r; raise err
        oid = dd(r.get("success_response", {})).get("order_id")
        self.orderlog("POSTED", side, oid, price, base, status="OPEN", note=note)
        return oid

    def fee_rate_from_fill(self, fee, val):
        return fee / val if val > 0 else 0.0

    def target_price(self, entry, val, fee):
        fr = self.fee_rate_from_fill(fee, val); cushion = float(CFG["SAFETY_MARGIN"])
        gross = (1 + DESIRED_NET_PROFIT_PCT + fee / max(val, 1e-9) + cushion) / (1 - fr if fr < .5 else 1)
        return entry * gross

    def allowed(self):
        self.s.reset()
        if self.s.position:
            return False, "position open"
        if self.funding_paused:
            return False, "funding circuit breaker active"
        if self.s.cooldown_until:
            try:
                if now() < datetime.fromisoformat(self.s.cooldown_until):
                    return False, "loss cooldown active"
            except Exception:
                pass
        if self.s.trades >= MAX_TRADES_DAY:
            return False, "daily trade limit"
        if self.s.losses >= MAX_LOSSES:
            return False, "loss cutoff"
        if self.s.pnl <= -MAX_DAILY_LOSS:
            return False, "daily loss cutoff"
        return True, "OK"

    def entry(self, ticker, atr_pct=None):
        ok, why = self.allowed()
        if not ok:
            self.log("Entry blocked: " + why)
            return
        bid, ask = self.book()
        if bid <= 0:
            self.log("Entry skipped: invalid order book data.")
            return

        # Spread guard: skip entries where the current spread already eats too much of the profit target.
        spread_pct = (ask - bid) / bid
        guard = DESIRED_NET_PROFIT_PCT * SPREAD_GUARD_RATIO
        if SPREAD_GUARD_RATIO > 0 and spread_pct > guard:
            self.log(f"Entry skipped: spread {spread_pct:.3%} exceeds guard {guard:.3%} (target {DESIRED_NET_PROFIT_PCT:.2%}).")
            self.orderlog("SKIPPED", "BUY", "", bid, note=f"spread {spread_pct:.3%} > guard {guard:.3%}")
            return

        # Volatility-scaled sizing: trim size (never increase it) when recent volatility is elevated.
        order_usd = ORDER_USD
        if VOL_SCALE_ENABLED and atr_pct and atr_pct > VOL_SCALE_ATR_REF:
            factor = max(VOL_SCALE_MIN_MULT, VOL_SCALE_ATR_REF / atr_pct)
            order_usd = ORDER_USD * factor
            self.log(f"Volatility-scaled order size: ${order_usd:.2f} (ATR {atr_pct:.3%} vs ref {VOL_SCALE_ATR_REF:.3%}).")

        base = round_down(order_usd / max(bid, 1), 8)
        if not self.live:
            fp = bid; val = base * fp; fee = 0.; oid = "PAPER"; self.s.paper_usd -= val; self.s.paper_btc += base
        else:
            self.refresh_product_rules()
            deadline = time.time() + ENTRY_TIMEOUT_MINUTES * 60; oid = None; o = {}; size = fp = fee = val = 0.
            funding_retries = 0; entry_attempt_started = time.time()
            while time.time() < deadline and not self.stop.is_set():
                bid, ask = self.book()
                # A BUY must remain strictly passive. Floor to product tick and never cross the ask.
                passive_cap = max(0.0, ask - self.quote_increment)
                price = self.floor_increment(min(bid, passive_cap), self.quote_increment)
                base, spend, available = self.safe_buy_size(order_usd, price)
                if base <= 0 or spend <= 0:
                    self.orderlog("ENTRY_ABORT_FUNDING", "BUY", "", price, base, status="ABORTED", note=f"available USD ${available:.4f}; reserve ${FUNDING_RESERVE_USD:.2f}")
                    self.log(f"Entry aborted: only ${available:.4f} USD available after reserve."); return
                if spend < order_usd - 0.005:
                    self.orderlog("ORDER_RESIZED", "BUY", "", price, base, status="RESIZED", note=f"requested ${order_usd:.2f}; safe allocation ${spend:.4f}; available ${available:.4f}")
                    self.log(f"Balance-aware sizing: ${order_usd:.2f} requested -> ${spend:.4f} safe allocation.")
                try:
                    oid = self.create_post_only("BUY", base, price, note="maker entry / managed reprice cycle")
                    self.funding_failures = 0
                except Exception as e:
                    resp = getattr(e, "order_response", {})
                    reason = self.rejection_reason(resp)
                    if "INSUFFICIENT" in reason:
                        self.funding_failures += 1
                        if funding_retries < FUNDING_RETRY_LIMIT:
                            funding_retries += 1
                            self.log("Funding rejection: refreshing balance and resizing once before retry.")
                            self.stop.wait(1); continue
                        self.orderlog("ENTRY_ABORT_FUNDING", "BUY", "", price, base, status="ABORTED", note=f"funding retry limit reached; available ${available:.4f}")
                        if self.funding_failures >= FUNDING_FAILURE_PAUSE:
                            self.funding_paused = True
                            self.log("FUNDING CIRCUIT BREAKER: new entries paused for this run after repeated insufficient-fund failures.")
                        return
                    if "POST_ONLY" in reason:
                        self.log("Post-only price moved: refreshing book and retrying once on next cycle.")
                        self.stop.wait(1); continue
                    self.log("Maker BUY rejected; entry aborted: " + str(e)); return
                wait_for = min(int(CFG.get("REPRICE_SECONDS", 20)), max(1, int(deadline - time.time())))
                o = self.wait_terminal(oid, wait_for); size, fp, fee, val = self.fill(o); status = str(o.get("status", "")).upper()
                if size > 0:
                    if size < base * .999:
                        self.confirmed_cancel(oid); self.orderlog("PARTIAL", "BUY", oid, price, base, size, fp, fee, status, "partial fill accepted; remainder cancel confirmed")
                    else:
                        self.orderlog("FILLED", "BUY", oid, price, base, size, fp, fee, status, "maker entry filled")
                    base = size
                    fill_seconds = time.time() - entry_attempt_started
                    sg = self.last_signal or {}
                    try:
                        bnow, anow = self.book(); sp = (anow-bnow)/bnow if bnow else 0
                        with INTELLIGENCE.open("a", newline="") as f:
                            csv.writer(f).writerow([now().isoformat(), PRODUCT, self.current_regime, self.regime_confidence, sp, sg.get("tr"), sg.get("r"), sg.get("atr_pct"), f"FILL_QUALITY: maker fill in {fill_seconds:.1f}s; bid {bnow}; ask {anow}; entry {fp}; fee {fee}"])
                    except Exception: pass
                    break
                if not self.confirmed_cancel(oid):
                    self.orderlog("CANCEL_UNCONFIRMED", "BUY", oid, price, base, 0, "", 0, status, "reprice aborted; cancellation not confirmed")
                    self.log("Reprice aborted: previous order cancellation was not confirmed."); return
                self.orderlog("CANCELLED_REPRICE", "BUY", oid, price, base, 0, "", 0, "CANCELLED", "cancel confirmed; funds may be reused")
                oid = None
            if size <= 0:
                self.orderlog("ENTRY_TIMEOUT", "BUY", oid or "", bid, base, 0, "", 0, "TIMEOUT", "no maker fill before entry timeout")
                self.log("Maker BUY entry window expired with no fill; skipped.")
                return
        self.s.position = True; self.s.entry_regime = self.current_regime; self.s.entry_confidence = self.regime_confidence; self.s.entry_price = fp; self.s.btc = base; self.s.entry_value = val; self.s.entry_fee = fee
        self.s.entry_time = now().isoformat(); self.s.entry_order = oid; self.s.trades += 1
        tp = self.target_price(fp, val, fee); self.s.tp_price = tp
        if self.live:
            try:
                self.s.tp_order = self.create_post_only("SELL", round_down(base, 8), tp, note="resting maker take-profit")
                self.log(f"Maker TP posted @ ${tp:,.2f} (targets about +{DESIRED_NET_PROFIT_PCT:.2%} net after estimated maker fees)")
            except Exception as e:
                self.s.tp_order = None; self.log("TP posting error: " + str(e))
        self.s.save(); self.trade("BUY", "POST_ONLY", ticker, fp, base, val, fee, "", "ENTRY", oid)

    def close_market(self, ticker, reason):
        s = self.s
        if not s.position:
            return
        self.cancel(s.tp_order); s.tp_order = None
        if self.live:
            cid = f"risk-sell-{uuid.uuid4().hex}"
            r = dd(self.c.market_order_sell(client_order_id=cid, product_id=PRODUCT, base_size=f"{self.floor_increment(s.btc, self.base_increment):.12f}".rstrip("0").rstrip(".")))
            if not r.get("success"):
                raise RuntimeError("Emergency sell rejected: " + json.dumps(r))
            oid = dd(r.get("success_response", {})).get("order_id"); o = self.wait_terminal(oid, 30); size, fp, fee, val = self.fill(o)
        else:
            oid = "PAPER"; size = s.btc; fp = ticker; fee = 0.; val = size * fp; s.paper_btc -= size; s.paper_usd += val
        self.finish(size, fp, fee, val, reason, oid, "MARKET")

    def finish(self, size, fp, fee, val, reason, oid, otype):
        s = self.s; pnl = val - s.entry_value - s.entry_fee - fee; s.pnl += pnl; s.losses = s.losses + 1 if pnl < 0 else 0
        if reason == "STOP_LOSS" and pnl < 0 and LOSS_COOLDOWN_MINUTES > 0:
            s.cooldown_until = (now() + timedelta(minutes=LOSS_COOLDOWN_MINUTES)).isoformat()
            self.log(f"Loss cooldown engaged for {LOSS_COOLDOWN_MINUTES} minute(s) — new entries paused.")
        self.trade("SELL", otype, fp, fp, size, val, fee, pnl, reason, oid)
        self.log(f"EXIT {reason}: NET ${pnl:+.4f}; exit fee ${fee:.4f}")
        s.position = False; s.entry_price = s.btc = s.entry_value = s.entry_fee = s.tp_price = 0.
        s.entry_time = None; s.entry_order = None; s.tp_order = None; s.entry_regime = "UNKNOWN"; s.entry_confidence = 0.0; s.save()

    def monitor(self, p):
        s = self.s
        if not s.position:
            return
        if self.live and s.tp_order:
            o = self.get_order(s.tp_order); size, fp, fee, val = self.fill(o)
            if size >= s.btc * .999 and fp > 0:
                self.orderlog("FILLED", "SELL", s.tp_order, s.tp_price, s.btc, size, fp, fee, str(o.get("status", "")), "maker take-profit filled")
                self.finish(size, fp, fee, val, "MAKER_TAKE_PROFIT", s.tp_order, "POST_ONLY"); return
        move = p / s.entry_price - 1; held = (now() - datetime.fromisoformat(s.entry_time)).total_seconds() / 60
        if move <= -STOP_LOSS_PCT:
            self.close_market(p, "STOP_LOSS")
        elif held >= MAX_HOLD_MINUTES:
            self.close_market(p, "TIME_EXIT")

    def trade(self, a, ot, ticker, fp, b, v, fee, pnl, why, oid):
        with TRADES.open("a", newline="") as f:
            csv.writer(f).writerow([now().isoformat(), "LIVE" if self.live else "PAPER", PRODUCT, a, ot, ticker, fp, b, v, fee, pnl, why, oid, self.s.entry_regime, self.s.entry_confidence])

    def reconcile(self):
        if not self.live or not self.s.position:
            return
        asset = PRODUCT.split("-")[0]; x = dd(self.c.get_accounts(limit=250)).get("accounts", []); held = 0.
        for a in x:
            a = dd(a)
            if a.get("currency") == asset:
                held += sf(dd(a.get("available_balance", {})).get("value"))
        if held + 1e-8 < self.s.btc and not self.s.tp_order:
            raise RuntimeError(f"Startup reconciliation failed: tracked {asset} not available.")
        self.log("Startup position reconciliation passed.")

    def run(self):
        p = dd(self.c.get_api_key_permissions())
        self.log(f"Coinbase connected. can_view={p.get('can_view')} can_trade={p.get('can_trade')}")
        if self.live and not p.get("can_trade"):
            raise RuntimeError("API key lacks trade permission.")
        self.refresh_product_rules(); self.reconcile(); self.log(f"STARTED: {PRODUCT} " + ("LIVE MAKER MODE" if self.live else "PAPER MAKER MODE"))
        self.consecutive_errors = 0
        while not self.stop.is_set():
            try:
                pr = self.price(); self.last_price = pr
                if self.manual_flatten.is_set():
                    if self.s.position:
                        try:
                            self.close_market(pr, "MANUAL_FLATTEN")
                        except Exception as e:
                            self.log("Manual flatten error: " + str(e))
                    self.manual_flatten.clear()
                self.monitor(pr)
                self.refresh_htf()
                sg = self.signal()
                if sg and str(sg["start"]) != self.s.last_candle:
                    self.s.last_candle = str(sg["start"]); self.s.save()
                    with SIGNALS.open("a", newline="") as f:
                        try:
                            lbid, lask = self.book(); lspread = (lask-lbid)/lbid if lbid else 0.0
                        except Exception: lspread = 0.0
                        regime, confidence, rec = self.learning_recommendation(sg, lspread)
                        self.last_signal = dict(sg)
                        csv.writer(f).writerow([now().isoformat(), PRODUCT, sg["start"], sg["close"], sg["r"], sg["f"], sg["sl"], sg["tr"],
                                                 sg.get("trend_ema"), sg.get("atr_pct"), sg.get("trend_ok"), sg.get("vol_ok"), sg.get("atr_ok"),
                                                 (self.htf_ok if HTF_ENABLED else ""), regime, confidence, "BUY" if sg["buy"] else "NO_TRADE"])
                    htf_txt = f" | HTF {'OK' if self.htf_ok else 'NO'}" if HTF_ENABLED else ""
                    self.log(f"15m: return {sg['r']:+.3%} | trend {sg['tr']:+.3%} | trendEMA {'OK' if sg.get('trend_ok') else 'NO'} | "
                             f"vol {'OK' if sg.get('vol_ok') else 'LOW'} | atr {'OK' if sg.get('atr_ok') else 'OUT'}{htf_txt} | {'BUY' if sg['buy'] else 'NO TRADE'}")
                    if sg["buy"] and not self.s.position:
                        if HTF_ENABLED and not self.htf_ok:
                            self.log("Entry blocked: hourly trend filter (HTF) not confirmed.")
                            self.orderlog("SKIPPED", "BUY", "", pr, note="HTF hourly trend filter blocked entry")
                        else:
                            self.entry(pr, sg.get("atr_pct"))
                self.log(f"{PRODUCT} ${pr:,.4f} | {'OPEN' if self.s.position else 'NONE'} | P/L ${self.s.pnl:+.4f} | {self.s.trades}/{MAX_TRADES_DAY}")
                self.consecutive_errors = 0
            except Exception as e:
                self.consecutive_errors += 1
                self.log("ERROR: " + str(e))
                if self.consecutive_errors >= ERROR_CIRCUIT_BREAKER:
                    cooloff = POLL * 5
                    self.log(f"Circuit breaker: {self.consecutive_errors} consecutive errors — pausing {cooloff}s.")
                    self.stop.wait(cooloff)
                    self.consecutive_errors = 0
            self.stop.wait(POLL)


# ---------- UI ----------
class App:
    def __init__(self, r):
        self.r = r
        r.title(APP); r.geometry("1080x860"); r.minsize(900, 700)

        # OS-level title bar / taskbar icon. Both calls are attempted independently
        # (not one-or-the-other) since .ico and PhotoImage take different code paths
        # on different platforms, and a failure in one shouldn't skip the other.
        self._win_icon = None
        try:
            icon_path = Path(__file__).with_name("jeep_icon.ico")
            r.iconbitmap(default=str(icon_path))
        except Exception:
            pass
        try:
            self._win_icon = tk.PhotoImage(file=str(Path(__file__).with_name("jeep_icon.png")))
            r.iconphoto(True, self._win_icon)
        except Exception:
            self._win_icon = None

        # In-app header icon: guaranteed visible regardless of how the OS renders
        # the title bar icon above. Kept as an instance attribute so Tk doesn't
        # garbage-collect the image out from under the label.
        self._header_icon = None
        try:
            self._header_icon = tk.PhotoImage(file=str(Path(__file__).with_name("jeep_icon.png")))
        except Exception:
            self._header_icon = None

        self.bot = None; self.th = None; self.q = queue.Queue()
        k, s = load_creds()

        self.price_var = tk.StringVar(value="\u2014")
        self.pos_var = tk.StringVar(value="Bot not running")
        self.stats_var = tk.StringVar(value="\u2014")
        self.mode_badge = tk.StringVar(value="PAPER")

        outer = ttk.Frame(r, padding=10); outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer); header.pack(fill="x")
        if self._header_icon is not None:
            ttk.Label(header, image=self._header_icon).pack(side="left", padx=(0, 10))
        ttk.Label(header, text=APP, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, textvariable=self.mode_badge, font=("Segoe UI", 10, "bold")).pack(side="right")

        self.nb = ttk.Notebook(outer); self.nb.pack(fill="both", expand=True, pady=(8, 0))
        self.tab_dash = ttk.Frame(self.nb, padding=10)
        self.tab_setup = ttk.Frame(self.nb, padding=10)
        self.tab_history = ttk.Frame(self.nb, padding=10)
        self.tab_logs = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_dash, text="Dashboard")
        self.nb.add(self.tab_setup, text="Setup & Strategy")
        self.nb.add(self.tab_history, text="Trade History")
        self.nb.add(self.tab_logs, text="Log")

        self.build_setup(self.tab_setup, k, s)
        self.build_dashboard(self.tab_dash)
        self.build_history(self.tab_history)
        self.build_logs(self.tab_logs)

        self.update_summary(); self.apply_theme()
        r.after(200, self.pump)
        r.after(1000, self.refresh_dashboard)
        r.after(4000, self.refresh_history)
        r.protocol("WM_DELETE_WINDOW", self.close)

    # ---- Dashboard tab ----
    def build_dashboard(self, parent):
        price_frame = ttk.LabelFrame(parent, text="Selected market", padding=12); price_frame.pack(fill="x")
        self.market_var = tk.StringVar(value=PRODUCT)
        ttk.Label(price_frame, textvariable=self.market_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(price_frame, textvariable=self.price_var, font=("Segoe UI", 28, "bold")).pack(anchor="w")

        pos_frame = ttk.LabelFrame(parent, text="Position", padding=10); pos_frame.pack(fill="x", pady=8)
        ttk.Label(pos_frame, textvariable=self.pos_var, font=("Segoe UI", 11)).pack(anchor="w")

        stats_frame = ttk.LabelFrame(parent, text="Today", padding=10); stats_frame.pack(fill="x")
        ttk.Label(stats_frame, textvariable=self.stats_var, font=("Segoe UI", 11)).pack(anchor="w")

        intel_frame = ttk.LabelFrame(parent, text="Market Intelligence / Learning (recommend/test mode)", padding=10); intel_frame.pack(fill="x", pady=8)
        self.intel_var = tk.StringVar(value="Collecting data — no automatic strategy changes")
        ttk.Label(intel_frame, textvariable=self.intel_var, font=("Segoe UI", 10)).pack(anchor="w")

        eq_frame = ttk.LabelFrame(parent, text="Equity (closed trades, cumulative net P/L)", padding=6); eq_frame.pack(fill="x", pady=8)
        self.equity_canvas = tk.Canvas(eq_frame, height=90, highlightthickness=0); self.equity_canvas.pack(fill="x")

        ctrl = ttk.LabelFrame(parent, text="Controls", padding=10); ctrl.pack(fill="x", pady=(0, 8))
        self.mode = tk.StringVar(value="PAPER")
        mrow = ttk.Frame(ctrl); mrow.pack(fill="x")
        ttk.Radiobutton(mrow, text="PAPER", variable=self.mode, value="PAPER").pack(side="left")
        ttk.Radiobutton(mrow, text="LIVE \u2014 REAL MONEY", variable=self.mode, value="LIVE").pack(side="left", padx=12)
        brow = ttk.Frame(ctrl); brow.pack(fill="x", pady=(8, 0))
        self.start = ttk.Button(brow, text="Save Credentials & Start", command=self.go); self.start.pack(side="left")
        self.stopb = ttk.Button(brow, text="Stop", command=self.halt, state="disabled"); self.stopb.pack(side="left", padx=8)
        self.flattenb = ttk.Button(brow, text="Flatten Position Now", command=self.flatten); self.flattenb.pack(side="left")

        ttk.Label(parent, text="Post-only maker entry + maker take-profit. Stop/time exits and manual flatten use market orders.",
                  foreground="#888888").pack(anchor="w", pady=(4, 0))
        ttk.Label(parent, text="This tool does not guarantee profit. Trading crypto involves real risk of loss.",
                  foreground="#888888").pack(anchor="w")

    # ---- Setup & Strategy tab ----
    def build_setup(self, parent, k, s):
        creds = ttk.LabelFrame(parent, text="Coinbase credentials", padding=8); creds.pack(fill="x")
        ttk.Label(creds, text="API key").grid(row=0, column=0, sticky="w")
        self.k = tk.StringVar(value=k); self.ke = ttk.Entry(creds, textvariable=self.k, show="\u2022", width=95); self.ke.grid(row=1, column=0, sticky="ew")
        ttk.Label(creds, text="Private key / secret").grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.s = tk.StringVar(value=s); self.se = ttk.Entry(creds, textvariable=self.s, show="\u2022", width=95); self.se.grid(row=3, column=0, sticky="ew")
        self.show_creds = tk.BooleanVar(value=False)
        ttk.Checkbutton(creds, text="Show credentials", variable=self.show_creds, command=self.toggle_creds).grid(row=4, column=0, sticky="w", pady=(5, 0))
        creds.columnconfigure(0, weight=1)

        market = ttk.LabelFrame(parent, text="Trading market", padding=8); market.pack(fill="x", pady=(8,0))
        ttk.Label(market, text="Crypto pair:").pack(side="left")
        self.product_choice = tk.StringVar(value=PRODUCT)
        ttk.Combobox(market, textvariable=self.product_choice, values=SUPPORTED_PRODUCTS, state="readonly", width=12).pack(side="left", padx=8)
        ttk.Label(market, text="BTC / Ethereum / XRP / Solana — one selected market runs at a time.").pack(side="left")

        sf_ = ttk.LabelFrame(parent, text="Strategy & risk settings", padding=8); sf_.pack(fill="x", pady=8)
        specs = [
            ("Order size ($)", "ORDER_USD", 1), ("Desired NET profit (%)", "DESIRED_NET_PROFIT_PCT", 100),
            ("Stop loss (%)", "STOP_LOSS_PCT", 100), ("Max hold (minutes)", "MAX_HOLD_MINUTES", 1),
            ("Max trades/day", "MAX_TRADES_DAY", 1), ("Consecutive-loss cutoff", "MAX_LOSSES", 1),
            ("Daily loss limit ($)", "MAX_DAILY_LOSS", 1), ("Maker entry timeout (min)", "ENTRY_TIMEOUT_MINUTES", 1),
            ("Maker reprice interval (sec)", "REPRICE_SECONDS", 1), ("Poll interval (sec)", "POLL", 1),
            ("Fast EMA", "FAST_EMA", 1), ("Slow EMA", "SLOW_EMA", 1),
            ("Min 15m return (%)", "MIN_RET", 100), ("Max 15m return (%)", "MAX_RET", 100),
            ("Min trend strength (%)", "MIN_TREND", 100), ("Safety margin (%)", "SAFETY_MARGIN", 100),
            ("Trend filter EMA (long)", "TREND_EMA", 1), ("ATR period", "ATR_PERIOD", 1),
            ("ATR min multiple", "ATR_MIN_MULT", 1), ("ATR max multiple", "ATR_MAX_MULT", 1),
            ("Volume lookback (candles)", "VOLUME_LOOKBACK", 1), ("Volume min ratio", "VOLUME_MIN_RATIO", 1),
            ("Loss cooldown (min)", "LOSS_COOLDOWN_MINUTES", 1), ("Spread guard ratio", "SPREAD_GUARD_RATIO", 1),
            ("Vol-scale sizing (1/0)", "VOL_SCALE_ENABLED", 1), ("Vol-scale min mult", "VOL_SCALE_MIN_MULT", 1),
            ("Vol-scale ATR ref (%)", "VOL_SCALE_ATR_REF", 100), ("Error circuit breaker", "ERROR_CIRCUIT_BREAKER", 1),
            ("Hourly trend gate (1/0)", "HTF_ENABLED", 1), ("Hourly trend EMA (hrs)", "HTF_TREND_EMA", 1),
            ("Hourly trend refresh (min)", "HTF_REFRESH_MINUTES", 1),
            ("Funding reserve ($)", "FUNDING_RESERVE_USD", 1), ("Funding retry limit", "FUNDING_RETRY_LIMIT", 1),
            ("Funding failures pause", "FUNDING_FAILURE_PAUSE", 1), ("Cancel confirm (sec)", "CANCEL_CONFIRM_SECONDS", 1),
            ("Learning panel (1/0)", "LEARNING_ENABLED", 1),
        ]
        self.vars = {}; self.scales = {}
        for i, (label, key, scale) in enumerate(specs):
            row = i // 3; col = (i % 3) * 2
            ttk.Label(sf_, text=label).grid(row=row, column=col, sticky="w", padx=(0, 5), pady=3)
            val = CFG[key] * scale if scale != 1 else CFG[key]
            if key in ("ORDER_USD", "MAX_DAILY_LOSS") or scale == 100:
                shown = f"{float(val):.2f}"
            else:
                shown = f"{val:.4f}".rstrip("0").rstrip(".") if isinstance(val, float) else str(val)
            v = tk.StringVar(value=shown)
            ttk.Entry(sf_, textvariable=v, width=12).grid(row=row, column=col + 1, sticky="w", padx=(0, 18))
            self.vars[key] = v; self.scales[key] = scale
        for c in range(6):
            sf_.columnconfigure(c, weight=1 if c % 2 == 0 else 0)

        tools = ttk.Frame(parent); tools.pack(fill="x")
        ttk.Label(tools, text="Theme:").pack(side="left")
        theme_values = BOOT_THEMES if HAVE_BOOT else LEGACY_THEMES
        default_theme = CFG.get("THEME") if CFG.get("THEME") in theme_values else ("darkly" if HAVE_BOOT else "System")
        self.theme = tk.StringVar(value=default_theme)
        ttk.Combobox(tools, textvariable=self.theme, values=theme_values, state="readonly", width=15).pack(side="left", padx=(4, 10))
        ttk.Button(tools, text="Apply Theme", command=self.apply_theme).pack(side="left", padx=(0, 10))
        ttk.Button(tools, text="Save Settings", command=self.save_settings).pack(side="left")
        ttk.Button(tools, text="Restore Defaults", command=self.defaults).pack(side="left", padx=6)
        ttk.Button(tools, text="Open Logs / State", command=lambda: os.startfile(DATA)).pack(side="left")
        self.summary = tk.StringVar()
        ttk.Label(parent, textvariable=self.summary, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(7, 2))

    # ---- Trade History tab ----
    def build_history(self, parent):
        cols = TRADES_HEADER
        widths = {"time": 155, "mode": 55, "action": 55, "order_type": 90, "ticker": 75, "fill_price": 85,
                  "base_size": 90, "value": 80, "fee": 60, "net_pnl": 75, "reason": 115, "order_id": 150, "entry_regime": 80, "entry_confidence": 90}
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", height=20)
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=widths.get(c, 90), anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview); self.tree.configure(yscroll=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")

    # ---- Log tab ----
    def build_logs(self, parent):
        self.out = scrolledtext.ScrolledText(parent, font=("Consolas", 10)); self.out.pack(fill="both", expand=True)

    def toggle_creds(self):
        ch = "" if self.show_creds.get() else "\u2022"
        self.ke.config(show=ch); self.se.config(show=ch)

    def parsed(self):
        n = {}
        integer = {"MAX_HOLD_MINUTES", "MAX_TRADES_DAY", "MAX_LOSSES", "ENTRY_TIMEOUT_MINUTES", "REPRICE_SECONDS", "POLL", "FAST_EMA", "SLOW_EMA",
                   "TREND_EMA", "ATR_PERIOD", "VOLUME_LOOKBACK", "LOSS_COOLDOWN_MINUTES", "ERROR_CIRCUIT_BREAKER",
                   "HTF_TREND_EMA", "HTF_REFRESH_MINUTES", "FUNDING_RETRY_LIMIT", "FUNDING_FAILURE_PAUSE", "CANCEL_CONFIRM_SECONDS"}
        for k, v in self.vars.items():
            x = float(v.get())
            if self.scales[k] != 1:
                x /= self.scales[k]
            n[k] = int(x) if k in integer else x
        if not (1 <= n["ORDER_USD"] <= 100000):
            raise ValueError("Order size must be positive.")
        if not (0 < n["DESIRED_NET_PROFIT_PCT"] < .50):
            raise ValueError("Net profit target must be between 0 and 50%.")
        if not (0 < n["STOP_LOSS_PCT"] < .50):
            raise ValueError("Stop loss must be between 0 and 50%.")
        if n["FAST_EMA"] >= n["SLOW_EMA"]:
            raise ValueError("Fast EMA must be smaller than Slow EMA.")
        if n["MIN_RET"] > n["MAX_RET"]:
            raise ValueError("Minimum 15m return cannot exceed maximum.")
        if min(n["MAX_HOLD_MINUTES"], n["MAX_TRADES_DAY"], n["MAX_LOSSES"], n["ENTRY_TIMEOUT_MINUTES"], n["REPRICE_SECONDS"], n["POLL"]) < 1:
            raise ValueError("Time/count settings must be at least 1.")
        if n["TREND_EMA"] <= n["SLOW_EMA"]:
            raise ValueError("Trend filter EMA should be greater than Slow EMA.")
        if n["ATR_PERIOD"] < 2:
            raise ValueError("ATR period must be at least 2.")
        if n["ATR_MIN_MULT"] >= n["ATR_MAX_MULT"]:
            raise ValueError("ATR min multiple must be less than ATR max multiple.")
        if n["VOLUME_LOOKBACK"] < 1:
            raise ValueError("Volume lookback must be at least 1.")
        if n["VOLUME_MIN_RATIO"] < 0:
            raise ValueError("Volume min ratio cannot be negative.")
        if n["SPREAD_GUARD_RATIO"] < 0:
            raise ValueError("Spread guard ratio cannot be negative.")
        if not (0 < n["VOL_SCALE_MIN_MULT"] <= 1):
            raise ValueError("Vol-scale min multiple must be between 0 and 1.")
        if n["ERROR_CIRCUIT_BREAKER"] < 1:
            raise ValueError("Error circuit breaker must be at least 1.")
        if n["HTF_TREND_EMA"] < 2:
            raise ValueError("Hourly trend EMA must be at least 2.")
        if n["HTF_REFRESH_MINUTES"] < 1:
            raise ValueError("Hourly trend refresh must be at least 1 minute.")
        n["PRODUCT"] = self.product_choice.get().upper()
        return n

    def apply_theme(self):
        name = self.theme.get()
        if HAVE_BOOT:
            try:
                if hasattr(self.r, "style"):
                    self.r.style.theme_use(name)
                else:
                    tb.Style().theme_use(name)
            except Exception:
                pass
            dark_themes = {"darkly", "cyborg", "superhero", "solar", "vapor"}
            try:
                if name in dark_themes:
                    self.out.configure(bg="#1a1a1a", fg="#e8e8e8", insertbackground="#e8e8e8")
                else:
                    self.out.configure(bg="#ffffff", fg="#111111", insertbackground="#111111")
            except Exception:
                pass
        else:
            style = ttk.Style()
            try:
                style.theme_use("clam")
            except Exception:
                pass
            palettes = {
                "Dark": {"bg": "#202124", "panel": "#202124", "fg": "#f1f3f4", "entry_bg": "#ffffff", "entry_fg": "#111111", "button_bg": "#e8eaed", "button_fg": "#111111", "select_bg": "#4c8bf5", "select_fg": "#ffffff", "log_bg": "#ffffff", "log_fg": "#111111"},
                "Midnight Blue": {"bg": "#07183f", "panel": "#07183f", "fg": "#ffffff", "entry_bg": "#ffffff", "entry_fg": "#07183f", "button_bg": "#e7edf9", "button_fg": "#07183f", "select_bg": "#2f6fed", "select_fg": "#ffffff", "log_bg": "#ffffff", "log_fg": "#07183f"},
                "Light": {"bg": "#f5f5f5", "panel": "#f5f5f5", "fg": "#111111", "entry_bg": "#ffffff", "entry_fg": "#111111", "button_bg": "#eeeeee", "button_fg": "#111111", "select_bg": "#3478f6", "select_fg": "#ffffff", "log_bg": "#ffffff", "log_fg": "#111111"},
                "System": {"bg": "#f0f0f0", "panel": "#f0f0f0", "fg": "#111111", "entry_bg": "#ffffff", "entry_fg": "#111111", "button_bg": "#e9e9e9", "button_fg": "#111111", "select_bg": "#3478f6", "select_fg": "#ffffff", "log_bg": "#ffffff", "log_fg": "#111111"},
            }
            p = palettes.get(name, palettes["System"])
            self.r.configure(bg=p["bg"])
            style.configure(".", background=p["panel"], foreground=p["fg"])
            style.configure("TFrame", background=p["panel"])
            style.configure("TLabelframe", background=p["panel"], foreground=p["fg"])
            style.configure("TLabelframe.Label", background=p["panel"], foreground=p["fg"])
            style.configure("TLabel", background=p["panel"], foreground=p["fg"])
            style.configure("TRadiobutton", background=p["panel"], foreground=p["fg"])
            style.configure("TCheckbutton", background=p["panel"], foreground=p["fg"])
            style.configure("TEntry", fieldbackground=p["entry_bg"], foreground=p["entry_fg"], insertcolor=p["entry_fg"])
            style.map("TEntry", fieldbackground=[("disabled", p["entry_bg"]), ("readonly", p["entry_bg"])],
                      foreground=[("disabled", p["entry_fg"]), ("readonly", p["entry_fg"])],
                      selectbackground=[("!disabled", p["select_bg"])], selectforeground=[("!disabled", p["select_fg"])])
            style.configure("TCombobox", fieldbackground=p["entry_bg"], foreground=p["entry_fg"], background=p["button_bg"])
            style.map("TCombobox", fieldbackground=[("readonly", p["entry_bg"])], foreground=[("readonly", p["entry_fg"])],
                      selectbackground=[("readonly", p["entry_bg"])], selectforeground=[("readonly", p["entry_fg"])])
            style.configure("TButton", background=p["button_bg"], foreground=p["button_fg"])
            style.map("TButton", foreground=[("disabled", "#666666"), ("!disabled", p["button_fg"])],
                      background=[("disabled", "#cfcfcf"), ("!disabled", p["button_bg"])])
            try:
                self.out.configure(bg=p["log_bg"], fg=p["log_fg"], insertbackground=p["log_fg"], selectbackground=p["select_bg"], selectforeground=p["select_fg"])
            except Exception:
                pass
        CFG["THEME"] = name

    def save_settings(self, quiet=False):
        global CFG
        try:
            n = self.parsed(); n["THEME"] = self.theme.get(); SETTINGS.write_text(json.dumps(n, indent=2)); CFG = n; apply_settings(); self.update_summary(); self.apply_theme()
            if not quiet:
                messagebox.showinfo(APP, "Settings saved. They will persist on this PC.")
            return True
        except Exception as e:
            messagebox.showerror(APP, "Settings error:\n" + str(e)); return False

    def defaults(self):
        self.product_choice.set(DEFAULT_SETTINGS.get("PRODUCT", "BTC-USD"))
        for k, v in DEFAULT_SETTINGS.items():
            if k in ("THEME", "PRODUCT"):
                continue
            val = v * self.scales[k] if self.scales.get(k, 1) != 1 else v
            if k in ("ORDER_USD", "MAX_DAILY_LOSS") or self.scales.get(k, 1) == 100:
                shown = f"{float(val):.2f}"
            else:
                shown = f"{val:.4f}".rstrip("0").rstrip(".") if isinstance(val, float) else str(val)
            self.vars[k].set(shown)
        self.save_settings(quiet=True)

    def update_summary(self):
        self.summary.set(f"${ORDER_USD:.2f} order | target +{DESIRED_NET_PROFIT_PCT:.2%} NET | SL -{STOP_LOSS_PCT:.2%} | "
                          f"max hold {MAX_HOLD_MINUTES}m | {MAX_TRADES_DAY}/day | {MAX_LOSSES}-loss cutoff | "
                          f"cooldown {LOSS_COOLDOWN_MINUTES}m | vol-scale {'ON' if VOL_SCALE_ENABLED else 'OFF'} | "
                          f"hourly trend gate {'ON' if HTF_ENABLED else 'OFF'}")

    def log(self, x):
        self.q.put(datetime.now().strftime("%H:%M:%S") + "  " + x)

    def pump(self):
        try:
            while 1:
                self.out.insert("end", self.q.get_nowait() + "\n"); self.out.see("end")
        except queue.Empty:
            pass
        self.r.after(200, self.pump)

    def refresh_dashboard(self):
        b = self.bot
        if b:
            price = getattr(b, "last_price", 0.0) or 0.0
            self.price_var.set(f"${price:,.4f}" if price else "\u2014")
            self.market_var.set(PRODUCT)
            self.intel_var.set(f"Regime: {getattr(b, 'current_regime', 'UNKNOWN')}  |  confidence {getattr(b, 'regime_confidence', 0):.0%}  |  {getattr(b, 'last_recommendation', 'Collecting data')}")
            s = b.s
            if s.position:
                held = (now() - datetime.fromisoformat(s.entry_time)).total_seconds() / 60 if s.entry_time else 0
                unreal = (price / s.entry_price - 1) if s.entry_price else 0
                self.pos_var.set(f"OPEN  |  entry ${s.entry_price:,.2f}  |  TP ${s.tp_price:,.2f}  |  unrealized {unreal:+.2%}  |  held {held:.1f}m")
            else:
                self.pos_var.set("No open position")
            htf_txt = f"   Hourly trend: {'OK' if getattr(b, 'htf_ok', True) else 'BLOCKED'}" if HTF_ENABLED else ""
            self.stats_var.set(f"Trades {s.trades}/{MAX_TRADES_DAY}   Losses {s.losses}/{MAX_LOSSES}   Daily P/L ${s.pnl:+.4f} (limit -${MAX_DAILY_LOSS:.2f}){htf_txt}")
            mode_txt = "LIVE \u2014 REAL MONEY" if b.live else "PAPER"
        else:
            self.price_var.set("\u2014"); self.pos_var.set("Bot not running"); self.stats_var.set("\u2014"); self.market_var.set(PRODUCT); self.intel_var.set("Collecting data — no automatic strategy changes")
            mode_txt = self.mode.get()
        self.mode_badge.set(mode_txt)
        self.r.after(1000, self.refresh_dashboard)

    def refresh_history(self):
        try:
            rows = []
            if TRADES.exists():
                with TRADES.open("r", newline="") as f:
                    rd = csv.reader(f); next(rd, None); rows = list(rd)
            for i in self.tree.get_children():
                self.tree.delete(i)
            for row in rows[-200:][::-1]:
                self.tree.insert("", "end", values=row)
            self.draw_equity(rows)
        except Exception:
            pass
        self.r.after(4000, self.refresh_history)

    def draw_equity(self, rows):
        c = self.equity_canvas; c.delete("all")
        pnls = []
        for row in rows:
            try:
                v = row[TRADES_HEADER.index("net_pnl")]
                if v not in ("", None):
                    pnls.append(float(v))
            except Exception:
                continue
        if not pnls:
            c.create_text(10, 45, text="No closed trades yet", anchor="w", fill="#888888"); return
        cum = []; t = 0.0
        for x in pnls:
            t += x; cum.append(t)
        w = max(int(c.winfo_width() or 400), 100); h = max(int(c.winfo_height() or 90), 40)
        lo = min(cum + [0]); hi = max(cum + [0]); span = (hi - lo) or 1.0
        n = len(cum)
        pts = []
        for i, v in enumerate(cum):
            x = 10 + (w - 20) * (i / max(1, n - 1))
            y = h - 10 - (h - 20) * ((v - lo) / span)
            pts.append((x, y))
        zero_y = h - 10 - (h - 20) * ((0 - lo) / span)
        c.create_line(10, zero_y, w - 10, zero_y, fill="#888888", dash=(2, 2))
        if len(pts) >= 2:
            flat = [coord for pt in pts for coord in pt]
            c.create_line(*flat, fill="#2ecc71" if cum[-1] >= 0 else "#e74c3c", width=2, smooth=True)
        c.create_text(w - 10, 10, text=f"Net ${cum[-1]:+.2f}", anchor="ne", fill="#888888")

    def go(self):
        if self.th and self.th.is_alive():
            return
        if not self.save_settings(quiet=True):
            return
        if not self.k.get().strip() or not self.s.get().strip():
            messagebox.showerror(APP, "Enter both API credentials."); return
        live = self.mode.get() == "LIVE"
        if live and not messagebox.askyesno("LIVE mode", f"This will place REAL {PRODUCT} orders.\n\nOrder size: ${ORDER_USD:.2f}\n"
                                             f"Desired net target: {DESIRED_NET_PROFIT_PCT:.2%}\nStop loss: {STOP_LOSS_PCT:.2%}\n\n"
                                             "Stop/time exits use market orders and may incur taker fees.\n\nContinue?"):
            return
        try:
            save_creds(self.k.get().strip(), self.s.get().strip())
            self.bot = Bot(self.k.get().strip(), self.s.get().strip(), live, self.log)
        except Exception as e:
            messagebox.showerror(APP, str(e)); return
        self.start.config(state="disabled"); self.stopb.config(state="normal")

        def w():
            try:
                self.bot.run()
            except Exception as e:
                self.log("FATAL: " + str(e))
            finally:
                self.r.after(0, lambda: (self.start.config(state="normal"), self.stopb.config(state="disabled")))

        self.th = threading.Thread(target=w, daemon=True); self.th.start()

    def halt(self):
        if self.bot:
            self.bot.stop.set(); self.log("Stop requested.")

    def flatten(self):
        if not self.bot or not (self.th and self.th.is_alive()):
            messagebox.showinfo(APP, "Bot is not running."); return
        if not self.bot.s.position:
            messagebox.showinfo(APP, "No open position to flatten."); return
        if self.bot.live and not messagebox.askyesno("Confirm flatten", "This will market-sell the open crypto position immediately. Continue?"):
            return
        self.bot.manual_flatten.set()
        self.log("Flatten requested from dashboard.")

    def close(self):
        if self.bot:
            self.bot.stop.set()
        self.r.destroy()


if __name__ == "__main__":
    if HAVE_BOOT:
        initial_theme = CFG.get("THEME") if CFG.get("THEME") in BOOT_THEMES else "darkly"
        try:
            r = tb.Window(themename=initial_theme)
        except Exception:
            r = tk.Tk()
    else:
        r = tk.Tk()
    App(r)
    r.mainloop()
