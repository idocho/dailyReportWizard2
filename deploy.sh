#!/usr/bin/env bash
# deploy.sh — 빌드 토큰 갱신 후 git push + Firebase 배포
set -e

BUILD=$(date -u +%Y%m%d%H%M)
INDEX="code/public/index.html"

# 이전 버전 토큰을 새 타임스탬프로 교체
sed -i "s/v=[0-9]\{12\}/v=$BUILD/g" "$INDEX"
echo "Build token: $BUILD"

git add "$INDEX"
git diff --staged --stat

MSG=${1:-"deploy: $BUILD"}
git commit -m "$MSG

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin main
firebase deploy --only hosting
