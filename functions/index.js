/*
 * functions/index.js — CampusManager 관리자 백엔드 (Admin SDK).
 * 클라이언트(apiKey)로 불가한 작업만: 비번 리셋 / 사용자 삭제 / mustChangePw 해제.
 * 호출 가능(onCall) — 호출자 토큰(request.auth)으로 관리자·캠퍼스 검증.
 *
 * 배포 전제: Blaze(종량) 플랜 + firebase.json 에 functions 연결(README 참조) + `firebase deploy --only functions`.
 * AUTH_DESIGN §3.2 의 "소형 백엔드" 구현체.
 */
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { setGlobalOptions } = require("firebase-functions/v2");
const admin = require("firebase-admin");

admin.initializeApp();
setGlobalOptions({ region: "asia-northeast3" }); // 서울 리전(지연 최소)
const db = admin.database();

// synth_email.js 동일 규칙 — n{hexUTF8(name)}@{campusSlug}.drw.local
function synthEmail(name, campus) {
  const n = Buffer.from(String(name || "").trim(), "utf8").toString("hex");
  const c = String(campus || "").trim().toLowerCase();
  const slug = /^[a-z0-9-]+$/.test(c) ? c : Buffer.from(c, "utf8").toString("hex");
  if (!n || !slug) throw new HttpsError("invalid-argument", "이름·캠퍼스가 필요합니다.");
  return "n" + n + "@" + slug + ".drw.local";
}

// 호출자가 활성 관리자(admin/super)인지 + (admin이면) 대상과 같은 캠퍼스인지 검증.
async function requireAdmin(request, targetCampus) {
  if (!request.auth) throw new HttpsError("unauthenticated", "로그인이 필요합니다.");
  const acl = (await db.ref("acl/" + request.auth.uid).get()).val();
  if (!acl || acl.active !== true) throw new HttpsError("permission-denied", "권한이 없습니다.");
  if (acl.role !== "admin" && acl.role !== "super") throw new HttpsError("permission-denied", "관리자 전용입니다.");
  if (acl.role === "admin" && targetCampus && acl.campus !== targetCampus)
    throw new HttpsError("permission-denied", "다른 캠퍼스 계정은 관리할 수 없습니다.");
  return acl;
}

// 강사 비번 리셋 → 새 임시비번 설정 + 첫 로그인 변경 강제(mustChangePw=true)
exports.resetInstructorPassword = onCall(async (request) => {
  const { uid, newPassword } = request.data || {};
  if (!uid || !newPassword || String(newPassword).length < 6)
    throw new HttpsError("invalid-argument", "uid·임시비번(6자 이상)이 필요합니다.");
  const t = (await db.ref("acl/" + uid).get()).val();
  if (!t) throw new HttpsError("not-found", "대상 계정이 없습니다.");
  await requireAdmin(request, t.campus);
  await admin.auth().updateUser(uid, { password: String(newPassword) });
  await db.ref("acl/" + uid + "/mustChangePw").set(true);
  return { ok: true };
});

// 강사 계정 발급 — Admin SDK createUser(공개 signUp 차단 후에도 동작) + acl 작성.
// 권한: 운영자(admin/super)=전 캠퍼스·강사/관리자, 관리자(manager)=자기 캠퍼스·강사만(권한상승 차단).
exports.createInstructor = onCall(async (request) => {
  const { campus, name, password, role } = request.data || {};
  if (!campus || !name || !password || String(password).length < 6)
    throw new HttpsError("invalid-argument", "campus·name·비번(6자 이상)이 필요합니다.");
  if (!request.auth) throw new HttpsError("unauthenticated", "로그인이 필요합니다.");
  const me = (await db.ref("acl/" + request.auth.uid).get()).val();
  if (!me || me.active !== true) throw new HttpsError("permission-denied", "권한이 없습니다.");
  const isAdmin = me.role === "admin" || me.role === "super";
  const wantRole = role === "manager" ? "manager" : "instructor";
  if (!isAdmin) {
    if (me.role !== "manager") throw new HttpsError("permission-denied", "관리자 전용입니다.");
    if (me.campus !== campus) throw new HttpsError("permission-denied", "다른 캠퍼스 계정은 만들 수 없습니다.");
    if (wantRole !== "instructor") throw new HttpsError("permission-denied", "관리자는 강사만 생성할 수 있습니다.");
  }
  const email = synthEmail(name, campus);
  let user;
  try {
    user = await admin.auth().createUser({ email, password: String(password) });
  } catch (e) {
    if (e.code === "auth/email-already-exists")
      throw new HttpsError("already-exists", "같은 캠퍼스에 동일 이름 계정이 이미 있습니다(접미로 구분).");
    throw new HttpsError("internal", "계정 생성 실패: " + (e.message || e.code));
  }
  await db.ref("acl/" + user.uid).set(
    { campus, role: wantRole, instructorId: name, active: true, mustChangePw: true });
  return { uid: user.uid, email };
});

// 강사 계정 영구 삭제 (Auth 사용자 + acl). 오발급·파기요청용.
exports.deleteInstructor = onCall(async (request) => {
  const { uid } = request.data || {};
  if (!uid) throw new HttpsError("invalid-argument", "uid가 필요합니다.");
  const t = (await db.ref("acl/" + uid).get()).val();
  if (!t) throw new HttpsError("not-found", "대상 계정이 없습니다.");
  await requireAdmin(request, t.campus);
  await admin.auth().deleteUser(uid).catch(() => {}); // Auth 유저 없더라도 acl 정리 진행
  await db.ref("acl/" + uid).remove();
  return { ok: true };
});

// 본인 첫 로그인 비번 변경 후 플래그 해제(클라가 자기 acl 못 쓰는 룰 대비 — 토큰 본인만).
exports.clearMustChangePw = onCall(async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "로그인이 필요합니다.");
  await db.ref("acl/" + request.auth.uid + "/mustChangePw").set(false);
  return { ok: true };
});
