#!/usr/bin/env python3
"""
mine_note_tags.py — 강사 전송 노트(history/) → 태그화 후보 워딩 발굴

운영 방식 (수동 LLM, 비용 0)
  1) build  : history 취합 + 현행 태그 분류를 묶어 '분석 프롬프트'를 파일로 생성.
              → 사용자가 그 프롬프트를 Claude 채팅에 붙여넣어 JSON 결과를 받음.
  2) ingest : 받은 JSON을 넣으면 누적 리포트(REPORT.md)·상태(state.json) 갱신,
              같은 후보가 PROMOTE_STREAK주 연속 반복되면 태그 승격 권고.

  주기(주 1회)로 build 만 자동/수동 실행 → 사람이 LLM 한 번 돌려 ingest.
  history 읽기는 현재 secret 불요(보안룰 미전환). claude API 키 불필요.

사용
  python scripts/mine_note_tags.py build               # state 이후(없으면 7일)
  python scripts/mine_note_tags.py build --days 7
  python scripts/mine_note_tags.py build --since 2026-06-08
  python scripts/mine_note_tags.py build --all
  python scripts/mine_note_tags.py ingest result.json  # 채팅서 받은 JSON 반영
  python scripts/mine_note_tags.py ingest -            # stdin 으로 JSON 붙여넣기
"""
import sys, os, json, argparse, datetime, urllib.request, urllib.parse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # cp949 콘솔 방어

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_CODE = os.path.join(_ROOT, 'code')
sys.path.insert(0, _CODE)

OUT_DIR    = os.path.join(_ROOT, 'documents', 'tag-mining')
REPORT_MD  = os.path.join(OUT_DIR, 'REPORT.md')
STATE_JSON = os.path.join(OUT_DIR, 'state.json')
PROMPT_MD  = os.path.join(OUT_DIR, 'PROMPT.md')      # 사용자가 붙여넣을 프롬프트
PENDING    = os.path.join(OUT_DIR, '.pending.json')  # build→ingest 윈도우 메타
PROMOTE_STREAK = 3   # 연속 N주 반복 시 정식 태그 승격 권고

# ── 자격 해석 (firebase url/path 만 필요) ────────────────────────────
def load_fb():
    url  = os.environ.get('DRW_FB_URL')
    path = os.environ.get('DRW_FB_PATH')
    for src in (os.path.join(_HERE, '.mine-creds.json'),
                os.path.join(_CODE, 'dist', 'config.json')):
        if (not url or not path) and os.path.exists(src):
            c = json.load(open(src, encoding='utf-8'))
            url  = url  or c.get('firebase_url')
            path = path or c.get('firebase_path')
    return url, path

# ── history 취합 ─────────────────────────────────────────────────────
def fetch_notes(url, path, since):
    full = (f"{url.rstrip('/')}/{urllib.parse.quote(path.strip('/'), safe='/')}"
            f"/history.json")
    with urllib.request.urlopen(full, timeout=30) as r:
        data = json.loads(r.read()) or {}
    notes = []
    for nk, days in data.items():
        if not isinstance(days, dict):
            continue
        for d, rec in days.items():
            if not isinstance(rec, dict):
                continue
            note = (rec.get('note') or '').strip()
            if note and (since is None or d >= since):
                notes.append({'date': d, 'instructor': rec.get('instructor', ''),
                              'note': note})
    notes.sort(key=lambda x: x['date'])
    return notes

# ── 현행 태그 분류 자동 추출 (프롬프트 동봉용) ───────────────────────
def current_taxonomy():
    from constants import TAGS
    import ai_engine as ae
    phrase = {
        'condition': ae._CONDITION_TEXT, 'understand': ae._UNDERSTAND_TEXT,
        'understand_sub': ae._UNDERSTAND_SUB_TEXT, 'engage': ae._ENGAGE_TEXT,
        'caution': ae._CAUTION_TEXT, 'extra': ae._EXTRA_TEXT,
        'highlight': ae._HIGHLIGHT_TEXT,
    }
    lines = []
    for cat, items in TAGS.items():
        for it in items:
            k = it['key']
            lines.append(f"  [{cat}] {it['label']} (key={k}) → "
                         f"{phrase.get(cat, {}).get(k, '(문구 없음)')}")
    return "\n".join(lines)

# ── 분석 프롬프트 조립 ───────────────────────────────────────────────
def build_prompt(notes, taxonomy):
    corpus = "\n".join(f"- ({n['date']}/{n['instructor']}) {n['note']}" for n in notes)
    return (
        "너는 수학학원 데일리리포트의 관찰 태그 체계를 개선하는 분석가다.\n"
        "[현행 태그]는 교사가 클릭해 학생 관찰을 기록하는 태그와 그 자연어 문구다.\n"
        "[노트 모음]은 강사들이 실제 학부모에게 보낸 최종 특이사항이다.\n\n"
        "할 일: 노트에서 '반복적으로 등장하는 의미 있는 관찰/워딩' 중 현행 태그가\n"
        "아직 담지 못하는 것을 찾아 태그화 후보로 제시하라. 이미 기존 태그로\n"
        "충분히 표현되는 것은 제외한다. 단발성·문체 표현이 아닌, 여러 학생·여러\n"
        "강사에 걸쳐 반복되는 '교육적으로 의미 있는' 패턴만 추린다.\n"
        "각 후보에 대해 판단: 신규 태그 필요(new_tag), 기존 태그 문구 보완(refine_wording),\n"
        "무시(ignore).\n\n"
        f"[현행 태그]\n{taxonomy}\n\n"
        f"[노트 모음] (총 {len(notes)}건)\n{corpus}\n\n"
        "오직 아래 JSON만 출력 (마크다운·설명 금지):\n"
        "{\n"
        '  "candidates": [\n'
        "    {\n"
        '      "theme": "후보를 한국어 한 구절로",\n'
        '      "category": "engage|caution|highlight|understand_sub|extra|understand|none",\n'
        '      "frequency": 노트에서_관찰된_대략_건수(정수),\n'
        '      "covered_by_existing": true|false,\n'
        '      "nearest_existing_key": "가장 가까운 기존 태그 key 또는 none",\n'
        '      "suggested_key": "영문_snake_case",\n'
        '      "suggested_label": "이모지 라벨",\n'
        '      "suggested_phrase": "AI 생성용 자연어 문구",\n'
        '      "examples": ["노트에서 발췌한 짧은 근거 1","2"],\n'
        '      "recommendation": "new_tag|refine_wording|ignore",\n'
        '      "rationale": "왜 의미 있는지/왜 기존으로 부족한지"\n'
        "    }\n"
        "  ],\n"
        '  "summary": "이번 기간 총평 1~2문장"\n'
        "}\n"
    )

# ── 상태/리포트 ──────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_JSON):
        return json.load(open(STATE_JSON, encoding='utf-8'))
    return {'last_run_date': None, 'runs': 0, 'candidates': {}}

def save_state(st):
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(st, open(STATE_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

def update_cumulative(st, result, run_date):
    seen_keys = set()
    for c in result.get('candidates', []):
        if c.get('recommendation') == 'ignore' or c.get('covered_by_existing'):
            continue
        k = c.get('suggested_key') or c.get('theme', '')[:20]
        seen_keys.add(k)
        e = st['candidates'].setdefault(k, {
            'theme': c.get('theme', ''), 'category': c.get('category', ''),
            'suggested_label': c.get('suggested_label', ''),
            'suggested_phrase': c.get('suggested_phrase', ''),
            'first_seen': run_date, 'history': [], 'streak': 0,
        })
        e['theme'] = c.get('theme', e['theme'])
        e['category'] = c.get('category', e['category'])
        e['suggested_label'] = c.get('suggested_label', e['suggested_label'])
        e['suggested_phrase'] = c.get('suggested_phrase', e['suggested_phrase'])
        e['last_seen'] = run_date
        e['history'].append({'date': run_date, 'freq': c.get('frequency', 0),
                             'rec': c.get('recommendation', '')})
        e['streak'] = e.get('streak', 0) + 1
    for k, e in st['candidates'].items():
        if k not in seen_keys:
            e['streak'] = 0
    return seen_keys

def render_report_section(result, st, run_date, meta, seen_keys):
    cand = result.get('candidates', [])
    actionable = [c for c in cand
                  if c.get('recommendation') != 'ignore' and not c.get('covered_by_existing')]
    promote = [k for k in seen_keys if st['candidates'][k]['streak'] >= PROMOTE_STREAK]
    L = [f"## {run_date} · 노트 태그 마이닝", ""]
    L.append(f"- 윈도우: `{meta.get('window')}` · 분석 노트 {meta.get('note_count')}건 "
             f"({meta.get('date_from')} ~ {meta.get('date_to')})")
    L.append(f"- 총평: {result.get('summary', '').strip()}")
    if promote:
        L.append(f"- 🚩 **승격 권고({PROMOTE_STREAK}주+ 연속)**: "
                 + ", ".join(f"`{st['candidates'][k]['suggested_label']}`" for k in promote))
    L += ["", "| 후보 | 분류 | 빈도 | 권고 | 연속주 | 근거 |",
          "|------|------|------|------|--------|------|"]
    for c in sorted(actionable, key=lambda x: -(x.get('frequency') or 0)):
        k = c.get('suggested_key') or c.get('theme', '')[:20]
        streak = st['candidates'].get(k, {}).get('streak', 1)
        L.append(f"| {c.get('theme','')} ({c.get('suggested_label','')}) | "
                 f"{c.get('category','')} | {c.get('frequency','')} | "
                 f"{c.get('recommendation','')} | {streak} | "
                 f"{c.get('rationale','').replace('|','/')[:80]} |")
    L.append("")
    return "\n".join(L)

def prepend_report(section):
    os.makedirs(OUT_DIR, exist_ok=True)
    header = ("# 노트 태그 마이닝 리포트\n\n"
              "강사 전송 노트(`history/`)에서 기존 obs 태그가 못 담는 반복 워딩을 주기적으로\n"
              "발굴한 누적 기록. 최신이 위. 빌드: `scripts/mine_note_tags.py`.\n\n---\n\n")
    old = ""
    if os.path.exists(REPORT_MD):
        txt = open(REPORT_MD, encoding='utf-8').read()
        old = txt.split('---\n\n', 1)[1] if '---\n\n' in txt else txt
    open(REPORT_MD, 'w', encoding='utf-8').write(header + section + "\n---\n\n" + old)

# ── 명령: build ──────────────────────────────────────────────────────
def cmd_build(a):
    url, path = load_fb()
    if not url or not path:
        sys.exit("자격 없음: DRW_FB_URL/DRW_FB_PATH(또는 creds/config.json) 필요")
    st = load_state()
    if a.all:
        since, window = None, 'all'
    elif a.since:
        since, window = a.since, f'since {a.since}'
    elif a.days:
        since = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
        window = f'last {a.days}d'
    elif st.get('last_run_date'):
        since, window = st['last_run_date'], f"since last run {st['last_run_date']}"
    else:
        since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        window = 'last 7d (first run)'

    notes = fetch_notes(url, path, since)
    print(f"[취합] 윈도우={window} · 노트 {len(notes)}건")
    if not notes:
        print("분석할 노트 없음 — 종료"); return
    prompt = build_prompt(notes, current_taxonomy())
    os.makedirs(OUT_DIR, exist_ok=True)
    open(PROMPT_MD, 'w', encoding='utf-8').write(prompt)
    meta = {'build_date': datetime.date.today().isoformat(), 'window': window,
            'note_count': len(notes),
            'date_from': notes[0]['date'], 'date_to': notes[-1]['date']}
    json.dump(meta, open(PENDING, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"[빌드] 프롬프트 → {PROMPT_MD}")
    print("  └ 이 파일 내용을 Claude 채팅에 붙여넣고, 받은 JSON을")
    print("    'python scripts/mine_note_tags.py ingest result.json' 로 반영하세요.")

# ── 명령: ingest ─────────────────────────────────────────────────────
def cmd_ingest(a):
    raw = sys.stdin.read() if a.file == '-' else open(a.file, encoding='utf-8').read()
    raw = raw.replace('```json', '').replace('```', '').strip()
    # 텍스트 앞뒤 잡소리 제거: 첫 { ~ 마지막 }
    s, e = raw.find('{'), raw.rfind('}')
    if s >= 0 and e > s:
        raw = raw[s:e + 1]
    result = json.loads(raw)
    meta = json.load(open(PENDING, encoding='utf-8')) if os.path.exists(PENDING) else {}
    run_date = datetime.date.today().isoformat()
    st = load_state()
    seen = update_cumulative(st, result, run_date)
    section = render_report_section(result, st, run_date, meta, seen)
    prepend_report(section)
    st['last_run_date'] = run_date
    st['runs'] = st.get('runs', 0) + 1
    save_state(st)
    if os.path.exists(PENDING):
        os.remove(PENDING)
    print(f"[반영] 후보 {len(result.get('candidates', []))}종 → {REPORT_MD}")
    print(section)

# ── main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--since'); b.add_argument('--days', type=int)
    b.add_argument('--all', action='store_true')
    b.set_defaults(func=cmd_build)
    g = sub.add_parser('ingest')
    g.add_argument('file', help="LLM JSON 결과 파일 경로 (또는 - 로 stdin)")
    g.set_defaults(func=cmd_ingest)
    a = ap.parse_args()
    a.func(a)

if __name__ == '__main__':
    main()
