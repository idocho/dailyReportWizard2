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
