#!/usr/bin/env python3
"""
Скрипт проверки позиции — запускается GitHub Actions каждые 30 минут.
Сохраняет результат в data/history.json
"""

import json, os
from datetime import datetime

NAME_PART    = "ФИХТЕР"
HISTORY_FILE = "data/history.json"
MAX_ENTRIES  = 500

SPECIALTIES = [
    {
        "name":   "09.02.11 Разработка и управление ПО",
        "label":  "Разработка ПО",
        "budget": 20,
        "color":  "#4F8EF7",
        "url": (
            "https://abitur.klgtu.ru/applicants-lists"
            "?campaign=ce0ebbfe-0296-11f1-af41-4c526250df5c"
            "&studyForm=1&basis=1"
            "&specialty=ff73a6f2-01c1-11ed-aeee-4c526250df5c"
            "&baseEducation=e52ebb96-11dd-11f1-af41-4c526250df5c"
        ),
    },
    {
        "name":   "09.02.06 Сетевое и системное администрирование",
        "label":  "Сетевое",
        "budget": 20,
        "color":  "#34C98A",
        "url": (
            "https://abitur.klgtu.ru/applicants-lists"
            "?campaign=ce0ebbfe-0296-11f1-af41-4c526250df5c"
            "&studyForm=1&basis=1"
            "&baseEducation=e52ebb96-11dd-11f1-af41-4c526250df5c"
            "&specialty=386d40d0-0aa3-11f1-af41-4c526250df5c"
        ),
    },
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(h):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

def fetch_page(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_selector("table,tbody,[class*='row']", timeout=15000)
        except: pass
        page.wait_for_timeout(3000)

        rows = []
        for row in page.query_selector_all("tbody tr"):
            cells = row.query_selector_all("td")
            if cells:
                rows.append([c.inner_text().strip() for c in cells])

        if not rows:
            for row in page.query_selector_all("[class*='row']:not([class*='header'])"):
                txt = row.inner_text().strip()
                if txt and any(c.isdigit() for c in txt):
                    rows.append(txt.split("\n"))

        full_text = page.inner_text("body")
        browser.close()
        return rows, full_text

def find_position(rows, full_text, name):
    name_up = name.upper()
    for i, row in enumerate(rows):
        if name_up in " ".join(str(c) for c in row).upper():
            pos = i + 1
            try: pos = int(row[0])
            except: pass
            score = None
            for cell in row:
                try:
                    v = float(str(cell).replace(",", "."))
                    if 3.0 <= v <= 5.0:
                        score = v; break
                except: pass
            return pos, len(rows), score
    if full_text and name_up in full_text.upper():
        lines = full_text.split("\n")
        for line in lines:
            if name_up in line.upper():
                for p in line.split():
                    try:
                        v = int(p)
                        if 1 <= v <= 500:
                            return v, len(rows) if rows else 0, None
                    except: pass
        return "?", len(rows) if rows else 0, None
    return None, len(rows) if rows else 0, None

def main():
    history = load_history()
    now = datetime.utcnow()

    print(f"\n[{now.strftime('%d.%m.%Y %H:%M')} UTC] Проверяю...")

    for idx, spec in enumerate(SPECIALTIES):
        print(f"  → {spec['label']}...", end=" ", flush=True)
        try:
            rows, full_text = fetch_page(spec["url"])
            pos, total, score = find_position(rows, full_text, NAME_PART)
            entry = {
                "time":     now.isoformat(),
                "spec_idx": idx,
                "position": pos,
                "total":    total,
                "score":    score,
                "error":    None,
            }
            try:
                icon = "✅" if int(str(pos).replace("~","")) <= spec["budget"] else "⏳"
            except:
                icon = "❓"
            print(f"{icon} Позиция: {pos} из {total}")
        except Exception as e:
            entry = {
                "time":     now.isoformat(),
                "spec_idx": idx,
                "position": None,
                "total":    None,
                "score":    None,
                "error":    str(e)[:100],
            }
            print(f"⚠️  {e}")

        history.append(entry)

    if len(history) > MAX_ENTRIES:
        history = history[-MAX_ENTRIES:]

    save_history(history)
    print(f"  Сохранено в {HISTORY_FILE} ({len(history)} записей)\n")

if __name__ == "__main__":
    main()
