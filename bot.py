"""디스코드 + Groq 팀 봇.

명령어
  /ask      질문에 답한다
  /summary  이 채널의 최근 대화를 요약한다
  /dday     프로젝트 일정까지 남은 날짜를 보여준다 (AI 미사용)
  @봇 멘션   멘션하고 질문해도 답한다
"""
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
# 모델 이름은 Groq 콘솔의 모델 목록을 보고 .env에서 바꿀 수 있다.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
# 서버 ID를 넣으면 명령어가 바로 등록된다. 비우면 전체 등록에 최대 1시간 걸릴 수 있다.
GUILD_ID = os.getenv("GUILD_ID")

TZ = ZoneInfo("Asia/Seoul")

# D-day 일정. 기획서가 바뀌면 여기만 고치면 된다. (이름, 날짜)
SCHEDULE = [
    ("촬영 허가 확정", "2026-10-30"),
    ("1차 촬영 시작", "2026-10-31"),
    ("2차 촬영 시작", "2026-11-07"),
    ("분석 본 작업 시작", "2026-11-10"),
    ("MVP 완성", "2026-11-18"),
]

SYSTEM_PROMPT = (
    "너는 대학생 팀 프로젝트의 도우미 봇이다. "
    "프로젝트는 컴퓨터 비전 기반 영상 분석(차량 우회전 양보 감지, 졸음운전 감지)이다. "
    "항상 한국어로, 간결하고 정확하게 답한다. 모르면 모른다고 말한다. "
    "코드는 코드 블록으로 쓴다."
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

groq_client = AsyncGroq(api_key=GROQ_API_KEY)


class TeamBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # /summary와 멘션 답변에 필요 (개발자 포털에서도 켜야 함)
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = TeamBot()


async def ask_groq(user_text: str, system: str = SYSTEM_PROMPT, max_tokens: int = 900) -> str:
    resp = await groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        temperature=0.4,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def split_message(text: str, limit: int = 1900) -> list[str]:
    """디스코드 메시지 길이 제한(2000자)에 맞춰 나눈다."""
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks or ["(빈 응답)"]


def friendly_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "rate" in msg or "429" in msg:
        return "요청이 너무 많아 잠시 막혔어요. 1분 뒤에 다시 시도해 주세요."
    log.exception("Groq 호출 실패")
    return "AI 호출 중 오류가 났어요. 잠시 후 다시 시도해 주세요."


@bot.event
async def on_ready() -> None:
    log.info("로그인: %s (모델: %s)", bot.user, GROQ_MODEL)


@bot.tree.command(name="ask", description="AI에게 질문합니다")
@app_commands.describe(question="궁금한 내용")
@app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
async def ask(interaction: discord.Interaction, question: str) -> None:
    await interaction.response.defer(thinking=True)
    try:
        answer = await ask_groq(question)
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(friendly_error(exc))
        return
    chunks = split_message(answer)
    await interaction.followup.send(chunks[0])
    for extra in chunks[1:]:
        await interaction.followup.send(extra)


@bot.tree.command(name="summary", description="이 채널의 최근 대화를 요약합니다")
@app_commands.describe(count="요약할 최근 메시지 수 (5~100)")
@app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
async def summary(interaction: discord.Interaction, count: app_commands.Range[int, 5, 100] = 30) -> None:
    await interaction.response.defer(thinking=True)
    lines: list[str] = []
    async for m in interaction.channel.history(limit=count):
        if m.author.bot or not m.content.strip():
            continue
        lines.append(f"{m.author.display_name}: {m.content.strip()}")
    if not lines:
        await interaction.followup.send("요약할 대화가 없어요.")
        return
    lines.reverse()  # 오래된 것부터
    transcript = "\n".join(lines)[-12000:]  # 너무 길면 최근 부분만
    prompt = (
        "다음은 팀 채팅 대화다. 핵심 논의, 결정된 것, 해야 할 일(담당자 포함)로 나눠 "
        "짧게 요약해라.\n\n" + transcript
    )
    try:
        answer = await ask_groq(prompt, max_tokens=700)
    except Exception as exc:  # noqa: BLE001
        await interaction.followup.send(friendly_error(exc))
        return
    for chunk in split_message(answer):
        await interaction.followup.send(chunk)


@bot.tree.command(name="dday", description="프로젝트 일정까지 남은 날짜를 보여줍니다")
async def dday(interaction: discord.Interaction) -> None:
    today = datetime.now(TZ).date()
    rows = []
    for name, date_str in SCHEDULE:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        diff = (d - today).days
        if diff > 0:
            tag = f"D-{diff}"
        elif diff == 0:
            tag = "D-DAY"
        else:
            tag = f"D+{-diff} (지남)"
        rows.append(f"`{tag:>10}` {name} ({d.month}/{d.day})")
    await interaction.response.send_message("**프로젝트 일정**\n" + "\n".join(rows))


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CommandOnCooldown):
        text = f"{error.retry_after:.0f}초 뒤에 다시 써 주세요."
    else:
        log.exception("명령어 오류", exc_info=error)
        text = "명령어 처리 중 오류가 났어요."
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or bot.user is None or bot.user not in message.mentions:
        return
    question = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not question:
        await message.reply("질문을 같이 적어 주세요. 예: `@봇 git 충돌 어떻게 풀어?`")
        return
    async with message.channel.typing():
        try:
            answer = await ask_groq(question)
        except Exception as exc:  # noqa: BLE001
            await message.reply(friendly_error(exc))
            return
    chunks = split_message(answer)
    await message.reply(chunks[0])
    for extra in chunks[1:]:
        await message.channel.send(extra)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
