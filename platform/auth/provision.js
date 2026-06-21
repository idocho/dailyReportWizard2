/*
 * provision.js — 강사 계정 발급/상태관리 (CampusManager 관리자용). AUTH_DESIGN §3.1·§5.
 * 클라이언트 가능 범위만: 생성(signUp REST) + acl 쓰기/비활성.
 * ⚠️ 비번 리셋·Auth 사용자 삭제·완전 비활성은 Admin 권한 필요 → 소형 백엔드(Cloud Function) 별도(문서 참조).
 *
 * signUp 은 SDK 가 아닌 raw REST 로 호출 → 관리자의 현재 로그인 세션을 건드리지 않는다.
 * (SDK createUserWithEmailAndPassword 는 새 유저로 로그인 전환되는 부작용이 있어 회피.)
 */
import { firebaseConfig } from "./firebase-config.js";
const API = firebaseConfig.apiKey;
const DB  = firebaseConfig.databaseURL.replace(/\/$/, "");

async function rest(url, method, body) {
  const r = await fetch(url, {
    method, headers: { "Content-Type": "application/json" },
    body: body == null ? undefined : JSON.stringify(body),
  });
  const d = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data: d };
}

/**
 * 강사 계정 발급: Auth 사용자 생성 + acl 작성(mustChangePw:true → 첫 로그인 비번변경 강제).
 * 반환 { uid, email }. 동명이인(EMAIL_EXISTS) 시 오류.
 * authToken: (선택) 관리자 idToken — 룰 배포 후 acl 쓰기 권한용. 미지정 시 무인증(전환 전 오픈 DB).
 */
export async function createInstructor(campus, name, tempPw, authToken) {
  const email = window.SynthEmail.synthEmail(name, campus);
  const su = await rest(
    "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + API,
    "POST", { email, password: tempPw, returnSecureToken: false }
  );
  if (!su.ok) {
    const m = su.data && su.data.error && su.data.error.message;
    if (m === "EMAIL_EXISTS") throw new Error("같은 캠퍼스에 동일 이름 계정이 이미 있습니다(접미로 구분).");
    if (m === "OPERATION_NOT_ALLOWED") throw new Error("콘솔에서 이메일/비밀번호 로그인을 먼저 활성화하세요.");
    if (m === "WEAK_PASSWORD" || (m||"").indexOf("PASSWORD")>=0) throw new Error("임시 비밀번호는 6자 이상이어야 합니다.");
    throw new Error("계정 생성 실패: " + (m || su.status));
  }
  const uid = su.data.localId;
  const acl = { campus, role: "instructor", instructorId: name, active: true, mustChangePw: true };
  const q = authToken ? "?auth=" + encodeURIComponent(authToken) : "";
  const aw = await rest(DB + "/acl/" + uid + ".json" + q, "PUT", acl);
  if (!aw.ok) throw new Error("권한(acl) 작성 실패: " + aw.status);
  return { uid, email };
}

/** 강사 비활성/활성 (acl.active 토글). 즉시 차단(룰이 매 요청 확인). */
export async function setActive(uid, active, authToken) {
  const q = authToken ? "?auth=" + encodeURIComponent(authToken) : "";
  const r = await rest(DB + "/acl/" + uid + "/active.json" + q, "PUT", active === true);
  if (!r.ok) throw new Error("상태 변경 실패: " + r.status);
  return true;
}

/** acl 조회(단건). */
export async function getAcl(uid, authToken) {
  const q = authToken ? "?auth=" + encodeURIComponent(authToken) : "";
  const r = await rest(DB + "/acl/" + uid + ".json" + q, "GET");
  return r.data;
}
