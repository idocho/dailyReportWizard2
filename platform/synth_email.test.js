/*
 * synth_email.test.js — synthEmail 단위 테스트 (순수 Node, 의존성 0)
 * 실행: node platform/synth_email.test.js
 */
const { synthEmail, hexUtf8, campusSlug } = require('./synth_email');

let pass = 0, fail = 0;
function ok(cond, msg) { if (cond) { pass++; } else { fail++; console.error('  ✗ ' + msg); } }
function eq(a, b, msg) { ok(a === b, `${msg} — got ${JSON.stringify(a)} expect ${JSON.stringify(b)}`); }

// 1) 결정성: 같은 입력 → 같은 출력
eq(synthEmail('홍길동', 'gangnam'), synthEmail('홍길동', 'gangnam'), '결정성');

// 2) 형식: n{hex}@{campus}.drw.local
const e = synthEmail('홍길동', 'gangnam');
ok(/^n[0-9a-f]+@gangnam\.drw\.local$/.test(e), '형식 일치: ' + e);

// 3) 한글 → 정확한 UTF-8 hex (홍길동 = ed998d eab8b8 eb8f99)
eq(hexUtf8('홍길동'), 'ed998deab8b8eb8f99', '홍길동 hex');
eq(synthEmail('홍길동', 'gangnam'), 'ned998deab8b8eb8f99@gangnam.drw.local', '전체 합성');

// 4) 캠퍼스 스코프: 같은 이름, 다른 캠퍼스 → 다른 이메일(도메인)
ok(synthEmail('홍길동', 'gangnam') !== synthEmail('홍길동', 'bundang'), '캠퍼스 분리');
eq(synthEmail('홍길동', 'bundang').split('@')[1], 'bundang.drw.local', '캠퍼스 도메인');

// 5) 다른 이름 → 다른 로컬파트
ok(synthEmail('김철수', 'gangnam') !== synthEmail('홍길동', 'gangnam'), '이름 구분');

// 6) 공백 trim
eq(synthEmail('  홍길동  ', 'gangnam'), synthEmail('홍길동', 'gangnam'), '이름 trim');
eq(synthEmail('홍길동', '  GANGNAM  '), synthEmail('홍길동', 'gangnam'), '캠퍼스 trim+소문자');

// 7) 이메일 로컬파트 유효성(ASCII 영숫자만)
ok(/^[a-z0-9]+$/.test(e.split('@')[0]), '로컬파트 ASCII 영숫자');

// 8) 비-ASCII 캠퍼스 id 도 안전화(hex)
ok(/^[a-z0-9]+\.drw\.local$/.test(synthEmail('홍길동', '강남').split('@')[1]), '비ASCII 캠퍼스 안전화');

// 9) 빈 입력 오류
let threw = false; try { synthEmail('', 'gangnam'); } catch (_) { threw = true; } ok(threw, '빈 이름 오류');
threw = false; try { synthEmail('홍길동', ''); } catch (_) { threw = true; } ok(threw, '빈 캠퍼스 오류');

// 10) 동명이인 같은 캠퍼스는 충돌(접미로 구분해야 함을 확인 — 설계상 운영자 책임)
eq(synthEmail('홍길동', 'gangnam'), synthEmail('홍길동', 'gangnam'), '동명이인 충돌(접미 필요 확인)');
ok(synthEmail('홍길동2', 'gangnam') !== synthEmail('홍길동', 'gangnam'), '접미로 구분 가능');

console.log(`\nsynth_email: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
