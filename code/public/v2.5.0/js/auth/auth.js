/*
 * auth.js — 실제 로그인 모듈 (Firebase Web SDK v10 모듈러). AUTH_DESIGN §3·§6.
 * DRW web·CampusManager 공용. 이름+캠퍼스 로그인 → acl 조회 → 세션.
 *
 * 선행(콘솔): ① Authentication 이메일/비밀번호 활성화 ② firebase-config.js 작성(apiKey 등).
 * synth_email.js 를 먼저 로드해 window.SynthEmail 이 있어야 함.
 *
 * 데이터 접근은 기존 REST 레이어 재사용 가능 — getIdToken() 으로 ?auth=idToken 전달.
 */
// SDK 버전 변경 시 아래 3개 URL을 함께 갱신. (import 지정자는 문자열 리터럴이어야 함)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, updatePassword, signOut, onAuthStateChanged,
         setPersistence, browserLocalPersistence, browserSessionPersistence }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
import { getDatabase, ref, get } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";
import { firebaseConfig } from "./firebase-config.js";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getDatabase(app);

// Firebase 오류코드 → 한국어
function humanize(code) {
  switch (code) {
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
    case "auth/invalid-email":     return "이름 또는 비밀번호가 올바르지 않습니다.";
    case "auth/user-disabled":     return "비활성화된 계정입니다. 관리자에게 문의하세요.";
    case "auth/too-many-requests": return "시도가 많아 잠시 후 다시 시도하세요.";
    case "auth/network-request-failed": return "네트워크 연결을 확인하세요.";
    default: return "로그인 중 문제가 발생했습니다. (" + code + ")";
  }
}

/**
 * 이름+캠퍼스+비번 로그인. 성공 시 세션 객체 반환:
 *   { uid, campus, role, instructorId, active, mustChangePw }
 * acl 미존재/비활성이면 로그아웃 후 오류 throw. allowRoles 지정 시 역할 게이트.
 */
export async function loginByName(campus, name, password, allowRoles, remember) {
  const email = window.SynthEmail.synthEmail(name, campus);
  let uid;
  try {
    // 로그인 유지 체크 시 local(무기한), 미체크 시 session(브라우저 닫으면 만료→재로그인)
    await setPersistence(auth, remember ? browserLocalPersistence : browserSessionPersistence);
    const cred = await signInWithEmailAndPassword(auth, email, password);
    uid = cred.user.uid;
  } catch (e) {
    throw new Error(humanize(e && e.code));
  }
  // acl 조회 (룰: 본인 엔트리 본인 읽기 허용)
  const snap = await get(ref(db, "acl/" + uid));
  const acl = snap.exists() ? snap.val() : null;
  if (!acl || acl.active !== true) {
    await signOut(auth);
    throw new Error(acl ? "비활성화된 계정입니다. 관리자에게 문의하세요." : "접근 권한이 없는 계정입니다.");
  }
  if (allowRoles && allowRoles.indexOf(acl.role) === -1) {
    await signOut(auth);
    throw new Error("이 앱에 대한 권한이 없습니다.");
  }
  return { uid, campus: acl.campus, role: acl.role, instructorId: acl.instructorId,
           active: true, mustChangePw: acl.mustChangePw === true };
}

/** 첫 로그인 비밀번호 변경. 변경 후 acl.mustChangePw 해제는 호출측(또는 관리툴)에서. */
export async function changePassword(newPassword) {
  if (!auth.currentUser) throw new Error("로그인 상태가 아닙니다.");
  if ((newPassword || "").length < 8) throw new Error("비밀번호는 8자 이상이어야 합니다.");
  try { await updatePassword(auth.currentUser, newPassword); }
  catch (e) { throw new Error(humanize(e && e.code)); }
}

export async function logout() { await signOut(auth); }

/** 데이터 REST 호출용 idToken (기존 fbE 의 ?auth= 에 사용 가능). */
export async function getIdToken() { return auth.currentUser ? auth.currentUser.getIdToken() : null; }

export function onAuth(cb) { return onAuthStateChanged(auth, cb); }
