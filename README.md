# 디스코드 + Groq 팀 봇

팀 디스코드 서버에서 AI에게 질문하고, 대화를 요약하고, 일정 D-day를 확인하는 봇입니다.

## 명령어

| 명령어 | 설명 |
|---|---|
| `/ask 질문` | AI가 답한다 |
| `/summary [개수]` | 이 채널의 최근 대화를 요약한다 (기본 30개, 5~100) |
| `/dday` | 프로젝트 일정까지 남은 날짜 (AI 미사용) |
| `@봇 질문` | 멘션해서 질문해도 된다 |

일정은 `bot.py` 위쪽의 `SCHEDULE`에서 고칩니다.

## 설치 순서

### 1. 디스코드 봇 만들기
1. https://discord.com/developers/applications 에서 **New Application**을 만든다.
2. 왼쪽 **Bot** 메뉴에서 **Reset Token**을 눌러 토큰을 복사한다. (한 번만 보인다)
3. 같은 화면 아래 **Privileged Gateway Intents**에서 **Message Content Intent**를 켠다. (`/summary`와 멘션 답변에 필요)
4. 왼쪽 **OAuth2 → URL Generator**에서 다음을 선택한다.
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `View Channels`, `Send Messages`, `Read Message History`
5. 아래에 생성된 URL을 브라우저에 열어 우리 서버에 봇을 초대한다.

### 2. Groq API 키 받기
https://console.groq.com 에서 가입한 뒤 **API Keys**에서 키를 만든다.

### 3. 서버 ID 복사 (선택, 권장)
디스코드 설정 → 고급 → **개발자 모드**를 켠다. 서버 아이콘을 우클릭 → **서버 ID 복사**. 넣으면 명령어가 바로 뜬다.

### 4. 실행 (Windows PowerShell 기준)
**Python 3.9 이상**이 필요합니다. (`zoneinfo` 사용) `python --version`으로 먼저 확인하세요.

```powershell
git clone https://github.com/Jbs1214/discode-groq-api.git
cd discode-groq-api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy env.example .env
# .env 를 열어 토큰과 키를 채운다
python bot.py
```
`로그인: 봇이름#1234` 라고 뜨면 성공입니다. 디스코드에서 `/` 를 입력해 명령어가 보이는지 확인하세요.

## 자주 나는 오류
| 오류 | 원인 / 해결 |
|---|---|
| `ModuleNotFoundError: No module named 'zoneinfo'` | Python 3.8 이하. 3.9 이상으로 venv를 다시 만든다. |
| `KeyError: 'DISCORD_TOKEN'` | `.env`가 없거나 비어 있음. `env.example`을 복사해 값을 채운다. |
| `403 Forbidden (error code: 50001): Missing Access` | 봇이 `GUILD_ID` 서버에 없거나, 초대할 때 `applications.commands` scope가 빠졌거나, `GUILD_ID`가 틀림. 1단계 4번대로 다시 초대한다. |

## 주의
- `.env`는 절대 git에 올리지 마세요. 토큰이 유출되면 봇이 탈취됩니다. (이미 `.gitignore`에 들어 있습니다.) 실수로 올렸다면 토큰을 즉시 재발급하세요.
- **교차로 영상, 얼굴 등 개인정보가 담긴 내용은 질문에 붙여 넣지 마세요.** 내용이 외부 API로 전송됩니다.
- 봇은 **내 컴퓨터에서 `python bot.py`를 실행하고 있는 동안만** 동작합니다. 항상 켜 두려면 별도 서버가 필요하지만, 프로젝트 용도로는 필요할 때만 켜도 충분합니다.
- 무료 한도에 걸리면 "요청이 너무 많아…"라고 답합니다. 잠시 뒤 다시 시도하세요.
- 모델 이름이 바뀌어 오류가 나면 Groq 콘솔의 모델 목록을 보고 `.env`의 `GROQ_MODEL`을 수정하세요.
