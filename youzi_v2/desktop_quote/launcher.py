"""Offline desktop host for the isolated Vue quotation widget."""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import threading
from contextlib import closing
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
PREFERENCES = ROOT.parent / 'data' / 'desktop_quote' / 'preferences.json'
WAREHOUSE_DATABASE = ROOT.parent / 'data' / 'youzi_v2.db'
FIELDS = ('channel', 'country', 'origin', 'customer', 'product', 'address', 'postcode', 'quantity',
          'weight', 'volume', 'chargeWeight', 'chargeVolume', 'volumeRatio', 'cost', 'profit',
          'extraFee', 'margin', 'unitPrice', 'unitPriceUsd', 'totalUnitPrice', 'total')
DEFAULT_FIELDS = ['channel', 'country', 'address', 'quantity', 'weight', 'volume', 'chargeWeight',
                  'chargeVolume', 'volumeRatio', 'cost', 'profit', 'unitPrice', 'totalUnitPrice', 'unitPriceUsd']


def sanitize_preferences(value) -> dict:
    value = value if isinstance(value, dict) else {}
    fields = value.get('visibleFields', DEFAULT_FIELDS)
    if not isinstance(fields, list):
        fields = DEFAULT_FIELDS
    fields = list(fields)
    if value.get('fieldLayoutVersion') != 1 and 'unitPrice' in fields and 'unitPriceUsd' not in fields:
        fields.append('unitPriceUsd')
    rate = value.get('exchangeRate', 6.7)
    if type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0:
        rate = 6.7
    return {'visibleFields': [key for key in FIELDS if key in fields], 'exchangeRate': rate, 'fieldLayoutVersion': 1,
            'showRecognition': value.get('showRecognition') if type(value.get('showRecognition')) is bool else True,
            'copyLanguage': value.get('copyLanguage') if value.get('copyLanguage') in ('zh', 'en') else 'en',
            'onTop': value.get('onTop') if type(value.get('onTop')) is bool else True}


def search_warehouses(conn: sqlite3.Connection, query: str) -> dict:
    query = query.strip()
    if not re.match(r'^[A-Za-z]', query) or len(query) > 120:
        return {'status': 'skipped', 'items': [], 'hasMore': False}
    columns = "DISTINCT TRIM(warehouse_code), TRIM(COALESCE(postcode, '')), TRIM(COALESCE(country_code, ''))"
    rows = conn.execute(
        f"SELECT {columns} FROM addresses_warehouse WHERE TRIM(warehouse_code) = ? COLLATE NOCASE LIMIT 21",
        (query,),
    ).fetchall()
    if not rows:
        prefix = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        rows = conn.execute(
            f"SELECT {columns} FROM addresses_warehouse WHERE TRIM(warehouse_code) LIKE ? ESCAPE '\\' "
            "ORDER BY 1 COLLATE NOCASE, 3, 2 LIMIT 21", (prefix,),
        ).fetchall()
    return {'status': 'ok', 'hasMore': len(rows) > 20,
            'items': [{'warehouseCode': row[0], 'postalCode': row[1], 'countryCode': row[2]} for row in rows[:20]]}


class DesktopApi:
    def __init__(self, path: Path = PREFERENCES):
        self._path = path
        self._window = None
        self._lock = threading.RLock()
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            saved = {}
        self._preferences = sanitize_preferences(saved)

    def get_preferences(self):
        with self._lock:
            return sanitize_preferences(self._preferences)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self._preferences, ensure_ascii=False), encoding='utf-8')
        temporary.replace(self._path)

    def save_preferences(self, value):
        with self._lock:
            # Only display preferences and exchange rate; never save quote or customer data.
            preferences = sanitize_preferences(value)
            self._preferences['visibleFields'] = preferences['visibleFields']
            self._preferences['exchangeRate'] = preferences['exchangeRate']
            self._preferences['showRecognition'] = preferences['showRecognition']
            self._preferences['copyLanguage'] = preferences['copyLanguage']
            self._save()
            return self.get_preferences()

    def find_warehouses(self, query):
        if not isinstance(query, str) or not re.match(r'^[A-Za-z]', query.strip()) or len(query.strip()) > 120:
            return {'status': 'skipped', 'items': [], 'hasMore': False}
        try:
            # Read-only URI prevents schema creation/migrations and accidental writes.
            with closing(sqlite3.connect(WAREHOUSE_DATABASE.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)) as conn:
                return search_warehouses(conn, query)
        except sqlite3.Error:
            return {'status': 'unavailable', 'items': [], 'hasMore': False}

    def set_on_top(self, value):
        if type(value) is not bool or self._window is None:
            raise ValueError('Invalid window state')
        # Bridge callbacks run on worker threads. WinForms properties must be changed
        # on its UI thread, without holding the preferences lock across that invocation.
        if sys.platform == 'win32':
            from System import Action
            self._window.native.Invoke(Action(lambda: setattr(self._window, 'on_top', value)))
        else:
            self._window.on_top = value
        with self._lock:
            self._preferences['onTop'] = value
            self._save()
            return value


class WidgetHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # No quote text or user input in access logs.

    def do_GET(self):
        requested = unquote(urlsplit(self.path).path).lstrip('/')
        target = (BUILD / requested).resolve()
        if not target.is_relative_to(BUILD.resolve()) or not target.is_file():
            self.send_error(404)
            return
        super().do_GET()

    def list_directory(self, _path):
        self.send_error(404)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verify dependencies and build, without opening a window')
    args = parser.parse_args()
    import webview

    if not (BUILD / 'quote-widget.html').is_file():
        raise RuntimeError('请先运行 desktop_quote 下的“安装并启动.cmd”，生成小窗界面。')
    if args.check:
        print('Desktop runtime and widget build are ready.')
        return
    api = DesktopApi()
    handler = partial(WidgetHandler, directory=str(BUILD))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        api._window = webview.create_window(
            '柚子 · 报价小窗', f'http://127.0.0.1:{server.server_port}/quote-widget.html',
            js_api=api, width=400, height=460, min_size=(300, 220),
            on_top=api.get_preferences()['onTop'], background_color='#f4f7fc', text_select=True,
        )
        webview.start(gui='edgechromium' if sys.platform == 'win32' else None, private_mode=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = f'报价小窗启动失败：{error}\n请运行“安装并启动.cmd”安装依赖，并确认已安装Edge WebView2 Runtime。'
        if sys.platform == 'win32' and not sys.stdout:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, '柚子报价小窗', 0x10)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)
