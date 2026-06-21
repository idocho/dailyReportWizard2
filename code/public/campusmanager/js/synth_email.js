/*
 * synth_email.js — 한글 이름 + 캠퍼스 → Firebase Auth 합성 이메일
 * Crafted by IDO(idocho@kakao.com) · Powered by Claude AI
 *
 * 배경(AUTH_DESIGN §3): 로그인은 "캠퍼스 + 한글 이름 + 비번"이지만 Firebase Auth(이메일/비번)는
 * 아이디가 이메일 형식 필수 → 앱이 이름·캠퍼스를 결정적(deterministic) 합성 이메일로 변환해
 * signInWithPassword 에 사용한다. 사용자는 이 이메일을 보지도 입력하지도 않는다.
 *
 * 형식: n{hexUTF8(name)}@{campus}.drw.local
 *   · 이름을 UTF-8 hex 로 인코딩 → 항상 ASCII·이메일 안전·결정적(같은 입력=같은 메일).
 *   · 도메인에 campus 를 넣어 캠퍼스 내에서만 유일하면 됨(동명이인은 타 캠퍼스 무관).
 *   · 도메인 .drw.local 은 실제 메일 미발송(분실 시 관리자 리셋 — §3.1).
 *
 * 브라우저(DRW web·CampusManager)·Node 양쪽 사용. 순수 함수, 의존성 0.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api; // Node
  if (typeof window !== 'undefined') window.SynthEmail = api;                // 브라우저
})(this, function () {
  const SUFFIX = '.drw.local';

  function hexUtf8(s) {
    const bytes = new TextEncoder().encode(String(s == null ? '' : s).trim());
    let out = '';
    for (const b of bytes) out += b.toString(16).padStart(2, '0');
    return out;
  }

  // campus 가 이미 ASCII 슬러그면 그대로(가독성), 아니면 hex 로 안전화.
  function campusSlug(campus) {
    const c = String(campus == null ? '' : campus).trim().toLowerCase();
    return /^[a-z0-9-]+$/.test(c) ? c : hexUtf8(c);
  }

  /** 이름+캠퍼스 → 합성 이메일. 빈 이름/캠퍼스는 오류. */
  function synthEmail(name, campus) {
    const n = hexUtf8(name);
    const c = campusSlug(campus);
    if (!n) throw new Error('synthEmail: 이름이 비어 있음');
    if (!c) throw new Error('synthEmail: 캠퍼스가 비어 있음');
    return 'n' + n + '@' + c + SUFFIX;
  }

  return { synthEmail, hexUtf8, campusSlug, SUFFIX };
});
