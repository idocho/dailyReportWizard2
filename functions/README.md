# functions/ — CampusManager 관리자 백엔드 (Admin SDK)

클라이언트(apiKey)로 불가능한 작업만 담당: **비번 리셋 · 사용자 삭제 · mustChangePw 해제**.
(계정 생성·비활성은 클라에서 직접 — `platform/auth/provision.js`.)

## 함수 (onCall, 서울 리전)
| 함수 | 권한 | 동작 |
|---|---|---|
| `resetInstructorPassword({uid,newPassword})` | 같은 캠퍼스 admin/super | 새 임시비번 설정 + mustChangePw=true |
| `deleteInstructor({uid})` | 같은 캠퍼스 admin/super | Auth 사용자 + acl 삭제(영구) |
| `clearMustChangePw()` | 본인 | 첫 로그인 비번변경 후 플래그 해제 |

## ⚠️ 배포 전제 (운영자/콘솔)
1. **Blaze(종량제) 플랜** 필요 — Cloud Functions 는 무료(Spark) 플랜 미지원. 콘솔에서 업그레이드.
   (소규모 호출이라 실비용 거의 0이지만 결제수단 등록 필요.)
2. `firebase.json` 에 functions 연결 추가:
   ```json
   "functions": { "source": "functions" }
   ```
3. 배포: `cd functions && npm install` → `firebase deploy --only functions`

## 클라이언트 호출(배포 후)
```js
import { getFunctions, httpsCallable } from ".../firebase-functions.js";
const fns = getFunctions(app, "asia-northeast3");
await httpsCallable(fns, "resetInstructorPassword")({ uid, newPassword });
```
→ 배포 완료되면 `admin.html` 의 [비번 리셋]·[삭제] 버튼을 이 호출로 활성화.

## 미배포 현황
코드만 작성됨(미배포·미테스트). Blaze 플랜 결정 후 배포·테스트.
