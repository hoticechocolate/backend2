# Docker 실행과 학교 서버 이전

외부 접속 포트는 기본 **8080 하나**다. 게이트웨이가 프런트 화면·일반 API·관리자 경로를 나누고, MongoDB·백엔드 내부 포트는 호스트에 공개하지 않는다. 기존 프런트 소스는 수정하지 않고 별도 Docker 빌드에서 정적 화면으로 포함한다.

프런트가 기존에 사용하는 두 데이터 조회 요청은 `/compat/rest/v1/` 호환 경로로 MongoDB에 연결한다. Supabase 자동 API로 연결하는 것이 아니다. 이미지 요청은 공개 Supabase Storage 주소로 리다이렉트한다. 빌드의 `local-public-data`는 기존 로더를 활성화하는 공개 표시값이며 인증 키가 아니다.

## 실행

`backend` 폴더에서 Docker Compose v2를 사용한다.

```text
python deploy/prepare_env.py
docker compose up -d --build
docker compose ps
```

`.env`가 이미 있으면 생성 명령은 기존 비밀값 보호를 위해 실패한다. 재실행 시 두 번째 명령부터 실행한다. 포트는 `.env`의 `POLARICE_HTTP_PORT`로 바꾼다.

첫 실행은 MongoDB 준비 → 컬렉션·인덱스 생성 및 CSV 주입 → 일반·관리자 API → 게이트웨이 순서로 진행한다. 이미지는 Supabase에서 직접 제공한다.

- API 문서: `http://서버IP:8080/docs`
- 프런트 화면: `http://서버IP:8080/`
- 샘플 조회: `http://서버IP:8080/api/sic-maps?year=2025&month=9`
- 관리자 상태: `http://서버IP:8080/admin/status`
- 관리자 요청 헤더: `Authorization: Bearer <.env의 POLARICE_ADMIN_TOKEN>`

관리자 토큰은 URL에 넣지 않는다. 학교 외부망 공개 시에는 학교의 HTTPS 진입점 뒤에 연결한다. 서버 방화벽·라우터의 공개 허용은 해당 서버 환경에서 설정해야 하며, 컨테이너 실행만으로 인터넷 주소가 생성되지는 않는다.

## 검증과 재주입

```text
docker compose --profile test run --rm test
python deploy/verify_container.py
docker compose run --rm import-data
docker compose logs --tail 50 import-data web admin gateway
```

이미지 데이터 132건과 평가 데이터 1건을 주입한다. 같은 키의 재주입은 갱신한다. DB는 이름 있는 Docker 볼륨에 보존된다. 기존 Windows MongoDB 파일을 공유하지 않고 원본 CSV에서 주입한다.

## 중지와 이전

`docker compose down`은 컨테이너·네트워크를 중지·제거하지만 DB 볼륨은 보존한다. `down -v`는 데이터까지 삭제하므로 데이터 초기화 목적이 아니면 사용하지 않는다.

학교 서버에는 `backend` 폴더를 복사하고 새 `.env`를 생성하여 같은 명령으로 빌드·실행한다. `.runtime`, `.venv`, 기존 `.env`는 복사할 필요가 없다. 서버 OS에 맞는 Docker Engine·Compose가 필요하다. MongoDB 데이터가 생성된 후에는 `.env`의 DB 비밀번호만 바꿔도 기존 계정 비밀번호가 자동 변경되지는 않는다.

학교 서버 접속 정보는 아직 제공되지 않았으므로 원격 배포는 수행하지 않는다. YOLO 실행 포트나 영상 API는 추가하지 않았다.

## 이전 시작 오류 (해결됨)

Compose 설정 검사와 Python 구문 검사는 통과했다. 실제 이미지 빌드·컨테이너 실행은 Docker Desktop 엔진 시작 오류로 완료하지 못했다. Docker 로그에는 `run/dockerInference` 통신 파일을 제거할 수 없어 Inference manager 초기화에 실패했다고 기록되어 있다. 해당 파일 정리도 Windows 접근 오류로 실패했다. 엔진 복구 후 `docker compose up -d --build`, 테스트 및 단일 포트 검증 명령을 실행해야 한다. 기존 네이티브 MongoDB 테스트 통과 결과를 Docker 실행 검증 결과로 간주하지 않는다.

## Docker 실행 검증 완료 (2026-10-17)

사용자 요청에 따라 기존 컨테이너 5개를 제거하고 기존 볼륨은 보존했다. 현재 `polarice` 프로젝트의 MongoDB·일반 API·관리자 API·프런트 게이트웨이가 실행 중이다. CSV 주입 컨테이너는 `Exited (0)`으로 정상 완료했다.

- 프런트·백엔드 이미지 빌드 성공
- MongoDB·일반 API·관리자 API healthy
- Docker 내부 통합 테스트 4개 통과
- 외부 포트 8080 하나만 공개
- 실제 HTTP 검사: 화면 문서 제공 200, 이미지 조회·기존 프런트 호환 조회 성공
- MongoDB 이미지 132건, 평가 1건 확인
- 관리자 인증 없는 요청 401, 올바른 토큰 조회 성공
- 브라우저 자동 접근은 도구의 URL 정책에 막혀 시각적인 화면 조작·렌더링 검증은 수행하지 못함
- 프런트 소스 파일 변경 없음

접속: `http://localhost:8080/`
