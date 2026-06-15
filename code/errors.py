"""
errors.py — 기술적 예외를 일반 사용자용 한국어 메시지로 변환

네트워크/HTTP/파싱 예외를 비개발자가 알아들을 수 있는 안내문으로 바꾼다.
끝에 작은 참고 코드(예: "(참고: HTTP 413)")만 남겨 사용자가 문의 시 식별 가능.
"""
import json
import socket
import urllib.error

# HTTP 상태코드 → 친절 메시지
_HTTP_MSG = {
    400: "보낸 요청 형식에 문제가 있습니다. 입력 내용을 확인한 뒤 다시 시도해 주세요.",
    401: "API Key가 올바르지 않습니다. 설정에서 키를 다시 확인해 주세요.",
    403: "API 사용 권한이 없습니다. 키 권한·결제 상태를 확인해 주세요.",
    404: "요청 주소를 찾을 수 없습니다. 설정의 Firebase 주소/경로를 확인해 주세요.",
    413: "한 번에 보낸 내용이 너무 많습니다. 학생 수를 줄여 나눠서 생성해 주세요.",
    429: "요청이 너무 잦습니다. 잠시 후(약 30초 뒤) 다시 시도해 주세요.",
    500: "AI 서버에 일시적인 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
    502: "AI 서버 응답이 불안정합니다. 잠시 후 다시 시도해 주세요.",
    503: "AI 서버가 혼잡합니다. 잠시 후 다시 시도해 주세요.",
    504: "응답 시간이 초과됐습니다. 잠시 후 다시 시도해 주세요.",
}


def humanize_error(exc, context=""):
    """예외 → 사용자용 메시지. context는 상황별 보조 문구(선택)."""
    # 본문에 'too large/payload' 가 있으면 코드와 무관하게 용량 초과로 안내
    body = ""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = (exc.read() or b"").decode("utf-8", "replace").lower()
        except Exception:
            body = ""
        code = exc.code
        # 본문이 용량 초과를 가리키면 상태코드와 무관하게 413 안내
        # (일부 API는 400으로 'payload size exceeds' 를 반환)
        if ("too large" in body or "payload size" in body
                or "request entity" in body or "exceeds the limit" in body):
            code = 413
        msg = _HTTP_MSG.get(code, "AI 서버와 통신 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        return f"{msg} (참고: HTTP {exc.code})"

    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "응답이 너무 오래 걸려 중단됐습니다. 인터넷 상태를 확인하고 다시 시도해 주세요. (참고: timeout)"

    if isinstance(exc, urllib.error.URLError):
        return ("인터넷에 연결할 수 없습니다. 네트워크 연결을 확인한 뒤 다시 시도해 주세요. "
                "(참고: network)")

    if isinstance(exc, json.JSONDecodeError):
        return "AI 응답을 해석하지 못했습니다. 한 번 더 생성해 주세요. (참고: parse)"

    # 본문 길이 초과 등 명시 메시지(RuntimeError 등)
    text = str(exc)
    if "빈 응답" in text or "safety" in text.lower():
        return "AI가 답변을 만들지 못했습니다(내용 필터 등). 입력을 조금 바꿔 다시 시도해 주세요."

    # 그 외: 친절 기본문 + 짧은 원문 일부(식별용)
    snippet = text.strip().replace("\n", " ")
    if len(snippet) > 80:
        snippet = snippet[:80] + "…"
    base = context or "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
    return f"{base}" + (f" (참고: {snippet})" if snippet else "")
