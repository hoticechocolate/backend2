# polarice 백엔드

현재 범위는 MongoDB 데이터 주입, SIC 이미지 주소 조회, 실험 평가 조회다. 프런트엔드와 YOLO 코드는 변경하거나 추가하지 않았다.

## 구성

- `config/local.example.json`: MongoDB, 이미지 기본 주소, 일반 웹·관리자 수신 IP와 포트
- `app/config.py`: 설정 파일을 읽는 설정 클래스
- `app/database.py`: MongoDB 컬렉션 검증 규칙과 고유 인덱스
- `app/models.py`: 주입 데이터 검증 모델
- `app/importer.py`: CSV 전체 검증 후 연월·실험 ID 기준 갱신 또는 삽입
- `app/services.py`: 설정과 데이터베이스를 주입받는 조회 클래스
- `app/api.py`: 일반 API와 관리자 API를 별도 앱으로 구성
- `imports/`: 원본 CSV의 사본. 원본은 상위 폴더에 보존

## 로컬 실행

이 폴더에서 실행한다. Python 3.10 이상과 실행 중인 MongoDB가 필요하다.

이번 로컬 검증에 사용한 MongoDB 실행 파일은 `.runtime` 아래에 있다. 로컬 재실행 시 별도 PowerShell 창에서 `./start-local-mongo.ps1`을 실행하고, 아래 API 명령은 다른 창에서 실행한다. MongoDB 데이터도 `.runtime/db`에 유지된다. 테스트 종료 후 서버 프로세스는 중지한다.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item config/local.example.json config/local.json
```

`config/local.json`에 환경에 맞는 주소·포트를 입력한다. 아래는 로컬 파일을 명시한 실행 예다.

```powershell
python manage.py init-db --config config/local.json
python manage.py import-data --config config/local.json
python manage.py web --config config/local.json
```

일반 API: `http://127.0.0.1:8000/docs`. 설정에서 포트를 변경하면 접속 주소도 바뀐다.

관리자는 별도 터미널에서 비밀 토큰을 환경 변수로 지정한 뒤 실행한다. 최소 24자이며 공유하거나 저장소에 올리지 않는다.

```powershell
$env:POLARICE_ADMIN_TOKEN = '<직접 생성한 충분히 긴 비밀값>'
python manage.py admin --config config/local.json
```

관리자 조회는 `http://127.0.0.1:8001/status`이며 `Authorization: Bearer <비밀값>` 헤더가 필요하다. 관리자 앱에는 데이터 변경·업로드 기능을 아직 제공하지 않는다. 주입은 명령행에서 수행한다.

## 일반 API

| 요청 | 역할 |
| --- | --- |
| `GET /health` | MongoDB 연결 확인 |
| `GET /api/sic-maps/dates` | 등록된 연월 목록 |
| `GET /api/sic-maps?year=2025&month=9` | 관측·예측·오차 경로와 전체 URL |
| `GET /api/evaluations` | 실험 ID 목록 |
| `GET /api/evaluations/{experiment_id}` | 원본 JSON을 유지한 실험 평가 |

날짜 없음은 404, 잘못된 월은 422, DB 연결 장애는 503으로 응답한다. 개별 이미지 경로가 비어 있으면 해당 URL은 null이다. URL 반환은 파일 존재를 보장하지 않는다.

이미지 주소는 설정의 공개 기본 주소와 CSV 경로를 조합한다. Supabase 키를 사용하지 않는다. 연월별 이미지 중복은 MongoDB 고유 인덱스로 방지한다. 평가와 이미지의 실험 연결은 보류 상태라 임의 연결하지 않는다.

두 CSV를 먼저 검증한 다음 데이터를 쓴다. 재주입은 동일 키를 갱신하며, CSV에서 삭제된 레코드는 DB에서 자동 삭제하지 않는다. 실행 도중 연결 장애가 나면 일부만 반영될 수 있지만 같은 명령으로 재주입할 수 있다.

## 테스트

```powershell
python -m pytest -q
```

실제 MongoDB에 고유 이름의 테스트 DB를 만들고 종료 시 해당 테스트 DB만 삭제한다. 원본 JSON 파싱, 중복 방지, DB 검증, 재주입, URL 구성, 날짜 오류, 관리자 인증을 확인한다. `POLARICE_CONFIG` 환경 변수로 테스트 연결 설정을 변경할 수 있다.

`python verify_local.py`는 프로젝트 내 MongoDB 실행 파일을 사용하여 임시 포트에서 DB와 두 API 서버를 실행하고, CSV 주입·테스트·실제 HTTP 요청을 검증한 후 프로세스를 중지한다. 주입한 `polarice` DB는 보존하고 결과는 `test-report.json`에 기록한다. 다른 MongoDB가 동일한 `.runtime/db`를 사용 중이라면 먼저 정상 종료해야 한다.

## 학교 서버로 이전

1. Python 환경·MongoDB를 준비하고 `backend` 폴더와 CSV를 복사한다.
2. 학교 환경용 설정 파일을 별도로 작성하고 MongoDB 인증 정보를 설정한다. 실제 설정 파일은 버전 관리에서 제외한다.
3. DB 초기화·주입 명령을 학교 설정으로 실행한다.
4. 일반 API와 관리자 앱을 별도 프로세스로 실행한다. 관리자와 MongoDB는 내부 접근으로 제한하고, 외부 웹은 HTTPS 진입점에서 연결한다.
5. 프런트 정적 빌드를 같은 서버에 배포하고 `/api` 요청을 백엔드에 연결한다. 이번 작업에서는 기존 프런트 수정·빌드·배포를 하지 않았다.
6. 학교 서버 OS·도메인·권한을 확인한 뒤 서비스 자동 실행과 실제 공개 설정을 작성한다.

로컬 기본값은 모두 루프백 수신이다. `host`는 서버가 수신할 인터페이스이며 외부 접속 도메인과 다르다. 같은 출처로 서비스하면 CORS 설정이 필요 없고, 개발 중 출처가 다르면 `allowed_origins`에 실제 프런트 주소를 명시한다.

YOLO 포트·모델·영상 전송 방식은 이번 구성에 추가하지 않았다. 저장 영상의 추론 기능은 추후 별도 작업으로 연결한다.
