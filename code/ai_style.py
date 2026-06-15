"""
ai_style.py — 강사 문체(말투) 프로파일링 & 프리셋

두 가지 경로로 AI 특이사항 생성에 '문체'를 주입한다.
  1) auto   : 로그인 강사 본인의 과거 전송 노트(history/)를 통계 분석해
              '문체 지침'을 자동 생성하고, 본인 노트 2~3개를 few-shot 예시로 제공.
  2) preset : 실데이터에서 도출한 4개 대표 유형(따뜻·상세 / 정돈·균형 /
              정보·코칭 / 간결·요점) 중 설정에서 고른 고정 지침 + 예시.

설정 키 `ai_style_mode` = 'auto' | preset id. 기본값 'auto'.
분석 소스: history/{nameKey}/{date} = {note, instructor} (강사 grain 누적).
"""
import re

# 이모지(픽토그램·기호) 탐지 — 따뜻형 식별/지침 생성에 사용
_EMOJI_RE = re.compile(r'[\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿]')
_YO_RE    = re.compile(r'(어요|아요|네요|에요|예요)')
_NIDA_RE  = re.compile(r'(습니다|입니다|니다)')

STYLE_AUTO = 'auto'

# ── 4개 대표 프리셋 (실데이터 분석 도출) ─────────────────────────────
# examples 는 실제 전송 노트에서 학생 실명이 없는 것을 골라 익명화한 샘플.
STYLE_PRESETS = {
    'warm_detail': {
        'label': '📖 따뜻·상세형',
        'guidance': (
            "4문장 이상 충분히 상세하게 작성합니다. 학생의 노력 과정과 태도 변화를 "
            "따뜻하게 공감하며 구체적으로 서술하고, 긍정적인 순간에는 문장 끝에 😊 같은 "
            "부드러운 이모지를 자연스럽게 한두 번 사용합니다. 격식체(~습니다)를 유지하되 "
            "다정하고 응원하는 어조로, 수업 내용과 당부를 문단으로 나누어 전달합니다."
        ),
        'examples': [
            "오늘은 피곤해하는 모습이 있었지만, 교재 오답도 성실하게 수정하고 설명도 집중해서 잘 들으며 수업에 참여했습니다. 연립방정식 활용 문제를 풀이하는 과정에서도 어려운 부분은 스스로 질문하며 내용을 잘 이해하는 모습을 보여주었습니다.\n\n내신 대비 기간이 쉽지만은 않겠지만, 지금처럼 차근차근 잘 따라와주면 좋겠습니다.😊",
            "수업 시간에는 연립방정식 활용 문제를 함께 풀이했는데, 질문에 대한 답변도 잘 해주었고 문제도 매우 잘 해결하는 모습을 보여주었습니다. 어려운 유형도 빠르게 이해하며 성실하게 수업에 참여하는 모습이 좋았습니다.😊",
        ],
    },
    'balanced': {
        'label': '📋 정돈·균형형',
        'guidance': (
            "3~4문장 적정 분량으로 작성합니다. 격식체(~습니다)로 명료하고 정돈되게 "
            "쓰되 담백하면서도 따뜻한 어조를 유지합니다. 수업 내용과 공지·당부는 문단을 "
            "나누어 분리하고, 이모지나 과한 느낌표는 사용하지 않습니다."
        ),
        'examples': [
            "설명을 빠르게 이해하며 막힘 없이 수업을 진행하고, 궁금한 점은 스스로 질문하는 능동적인 모습이 돋보였습니다. 과제도 완벽히 완료하여 오늘도 알찬 수업이었습니다.",
            "오늘도 평소처럼 성실하게 수업에 임하며 내용을 빠르게 이해하고 막힘 없이 진행하였습니다. 어려운 문제도 스스로 돌파하고 오답까지 꼼꼼히 점검하는 모습이 인상적이었습니다.",
        ],
    },
    'info_coach': {
        'label': '🎯 정보·코칭형',
        'guidance': (
            "수업에서 진행한 활동·시험·일정을 구체적으로 명시합니다. 학생에게 필요한 "
            "학습 방향과 코칭을 직설적이고 분명하게 전달하고, 보강·재검사·준비물·등원시간 "
            "같은 운영 안내는 날짜·시간까지 빠짐없이 적습니다. 격식체로 군더더기 없이 "
            "사실과 지도 내용 중심으로 작성합니다."
        ),
        'examples': [
            "기출모의고사 3회 시행했습니다. 논술형 작성이 다소 미비합니다. 오답노트를 꼼꼼히 잘 작성해왔으며, 몰랐던 문제에 대한 복습이 철저하고 신중하게 고려하며 푸는 성향이 있습니다.",
            "실전모의고사 1회 진행했습니다. 논술형 12번 세 가지 다른 풀이를 작성해오지 않아 화요일 재검사 예정입니다. 6/16(화) 4:50 시험대비 보강 있습니다.",
        ],
    },
    'concise': {
        'label': '⚡ 간결·요점형',
        'guidance': (
            "2~3문장 이내로 핵심만 간결하게 작성합니다. 점수·진도·핵심 사실 위주로 "
            "군더더기 없이 쓰고, 항목이 여럿이면 짧은 줄바꿈으로 구분합니다. 불필요한 "
            "수식이나 감상은 넣지 않습니다."
        ),
        'examples': [
            "25년 동수원기출 시험 100점. 금일 학습도 집중력 있게 진행하며 완료했습니다.",
            "25년 남수원기출 시험: 100점\n실전모의고사 1회: 100점\n결석 공백을 최대한 마무리하려 노력 중입니다.",
        ],
    },
}

# 설정 드롭다운 표시 순서/라벨 (auto 우선)
STYLE_ORDER = [STYLE_AUTO, 'warm_detail', 'balanced', 'info_coach', 'concise']
STYLE_LABELS = {STYLE_AUTO: '✍️ 내 말투 자동 (전송 노트 학습)'}
STYLE_LABELS.update({k: v['label'] for k, v in STYLE_PRESETS.items()})


# ── auto: 본인 노트 통계 분석 ────────────────────────────────────────
def analyze_notes(notes):
    """전송 노트 리스트 → 문체 통계 dict. 노트 없으면 None."""
    notes = [n.strip() for n in (notes or []) if n and n.strip()]
    if not notes:
        return None
    n = len(notes)
    lens = [len(x) for x in notes]
    return {
        'count':      n,
        'avg_len':    sum(lens) / n,
        'emoji_rate': sum(1 for x in notes if _EMOJI_RE.search(x)) / n,
        'excl_rate':  sum(1 for x in notes if '!' in x) / n,
        'yo_rate':    sum(1 for x in notes if _YO_RE.search(x)) / n,
        # 개조식: 줄바꿈 2회+ & 격식 어미 1회 이하 (점수·항목 나열형)
        'bullet_rate': sum(1 for x in notes
                           if x.count('\n') >= 2 and len(_NIDA_RE.findall(x)) <= 1) / n,
    }


def build_guidance(profile):
    """통계 프로파일 → AI 프롬프트용 문체 지침 문장."""
    if not profile:
        return ""
    parts = []
    avg = profile['avg_len']
    if avg < 110:
        parts.append("2~3문장 이내로 핵심만 간결하게 작성합니다")
    elif avg < 200:
        parts.append("3~4문장 적정 분량으로 정돈되게 작성합니다")
    else:
        parts.append("4문장 이상 충분히 상세하게, 학생의 노력 과정을 구체적으로 서술합니다")

    if profile['bullet_rate'] >= 0.4:
        parts.append("항목이 여럿이면 짧은 줄바꿈으로 구분하고 사실 위주로 요약합니다")

    if profile['emoji_rate'] >= 0.4:
        parts.append("긍정적인 순간에는 문장 끝에 😊 같은 부드러운 이모지를 자연스럽게 한두 번 사용합니다")
    else:
        parts.append("이모지는 사용하지 않습니다")

    if profile['yo_rate'] >= 0.35:
        parts.append("기본은 격식체(~습니다)이되 부드러운 어조를 유지합니다")
    else:
        parts.append("격식체(~습니다)로 통일합니다")

    if profile['excl_rate'] >= 0.3:
        parts.append("칭찬 등 긍정적 대목에서는 느낌표로 생동감을 살립니다")

    return " ".join(p + "." for p in parts)


def pick_examples(notes, k=2):
    """대표 예시 노트 k개 — 중앙값 길이 근처에서 학생 실명 흔적이 적은 것 우선."""
    notes = [n.strip() for n in (notes or []) if n and n.strip()]
    if not notes:
        return []
    name_pat = re.compile(r'[가-힣]{2,3}(이는|이가|이를|이의|이에게|이도|군은|양은)')
    anon = [n for n in notes if not name_pat.search(n)] or notes
    anon.sort(key=len)
    mid = len(anon) // 2
    # 중앙값부터 양옆으로 k개 수집
    order = sorted(range(len(anon)), key=lambda i: abs(i - mid))
    return [anon[i] for i in order[:k]]


def auto_style(notes):
    """본인 노트 → (guidance, examples). 노트 없으면 ('', [])."""
    prof = analyze_notes(notes)
    if not prof:
        return "", []
    return build_guidance(prof), pick_examples(notes, k=2)


def profile_summary(profile):
    """통계 프로파일 → 설정 UI 미리보기용 한 줄 요약."""
    if not profile:
        return "분석할 전송 노트가 없습니다. 기본 문체로 생성됩니다."
    avg  = round(profile['avg_len'])
    tone = "격식체" if profile['yo_rate'] < 0.35 else "격식체+부드러운 어조"
    emoji = "이모지 사용" if profile['emoji_rate'] >= 0.4 else "이모지 미사용"
    excl  = " · 칭찬 시 느낌표" if profile['excl_rate'] >= 0.3 else ""
    bullet = " · 개조식" if profile['bullet_rate'] >= 0.4 else ""
    return (f"내 노트 {profile['count']}건 분석 → 평균 {avg}자 · {tone} · "
            f"{emoji}{excl}{bullet}")


def resolve_style(mode, instructor_notes_provider):
    """설정 모드 → (guidance, examples).

    mode == 'auto' 면 instructor_notes_provider() 를 호출해 본인 노트를 받아
    분석한다(호출측에서 fetch/캐시 책임). preset 이면 고정값.
    """
    mode = (mode or STYLE_AUTO).strip()
    if mode != STYLE_AUTO:
        p = STYLE_PRESETS.get(mode)
        return (p['guidance'], list(p['examples'])) if p else ("", [])
    notes = instructor_notes_provider() if instructor_notes_provider else []
    return auto_style(notes)


def style_prompt_block(guidance, examples):
    """(guidance, examples) → 프롬프트에 끼워 넣을 문체 블록 텍스트.

    예시는 '문체만 참고, 내용은 새 데이터로' 임을 강조해 실명·사실 베끼기를 방지.
    """
    if not guidance and not examples:
        return ""
    out = []
    if guidance:
        out.append(f"[문체 지침 — 이 말투와 분량을 따라 작성]\n{guidance}")
    if examples:
        ex = "\n".join(f"예{i+1}) \"{e}\"" for i, e in enumerate(examples))
        out.append(
            "[문체 참고 예시 — 말투·길이·어조만 참고하고, 예시의 학생 이름·점수·"
            "사실은 절대 가져오지 말 것. 내용은 아래 학생 데이터로 새로 작성]\n" + ex
        )
    return "\n\n".join(out)
