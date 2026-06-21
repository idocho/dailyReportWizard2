// firebase-config.example.js — 복사해서 같은 폴더에 firebase-config.js 로 저장하고 콘솔 값으로 채우세요.
// 값 위치: Firebase 콘솔 → ⚙ 프로젝트 설정 → 일반 → 내 앱(웹) → SDK 설정 및 구성 → 구성(Config).
// apiKey 는 공개값(클라이언트에 내려가는 값)입니다 — 비밀 아님. 보안은 Auth+룰이 담당.
// firebase-config.js 는 git 제외(.gitignore) — 환경별로 따로 둡니다.
export const firebaseConfig = {
  apiKey: "PASTE_WEB_API_KEY",
  authDomain: "dailyreportwizard.firebaseapp.com",
  databaseURL: "https://dailyreportwizard-default-rtdb.firebaseio.com",
  projectId: "dailyreportwizard",
  appId: "PASTE_APP_ID"
};
