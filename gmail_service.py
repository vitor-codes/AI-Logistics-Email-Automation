import base64
import html
import os
import re
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")
TOKEN_PATH = _ROOT / "token.json"


def _client_secrets_path() -> Path:
    """Um único JSON OAuth tipo Desktop cobre Gmail e Calendar; use credentials.json ou GOOGLE_OAUTH_CLIENT_SECRETS."""
    explicit = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS", "").strip()
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else (_ROOT / p)
    return _ROOT / "credentials.json"


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]


def _html_to_plain(html_str: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", "", html_str)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _gather_plain_and_html_parts(payload, plains, htmls):
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    data_b64 = body.get("data")
    if data_b64:
        raw = base64.urlsafe_b64decode(data_b64).decode(errors="replace")
        if mime == "text/plain":
            plains.append(raw)
        elif mime == "text/html":
            htmls.append(raw)
    for part in payload.get("parts", []):
        _gather_plain_and_html_parts(part, plains, htmls)


def _message_body_as_text(payload) -> str:
    """
    Um único texto por mensagem. Em multipart/alternative o mesmo conteúdo vem em
    text/plain e text/html; usar os dois gerava duplicatas no Excel/Calendar.
    """
    plains, htmls = [], []
    _gather_plain_and_html_parts(payload, plains, htmls)
    if plains:
        return "\n\n".join(p.strip() for p in plains if p.strip()).strip()
    converted = [_html_to_plain(h) for h in htmls]
    converted = [c for c in converted if c]
    return "\n\n".join(converted).strip()


def autenticar():
    secrets = _client_secrets_path()
    if not secrets.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {secrets}. "
            "Use um único OAuth Client tipo Desktop no mesmo projeto onde Gmail API e Calendar API estão ativas; "
            "salve como credentials.json na raiz ou defina GOOGLE_OAUTH_CLIENT_SECRETS no .env com o caminho do JSON."
        )

    creds = None
    if TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def buscar_emails_remetente(remetente):
    creds = autenticar()
    service = build("gmail", "v1", credentials=creds)

    query = f"from:{remetente}"

    resultado = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=10)
        .execute()
    )

    mensagens = resultado.get("messages", [])

    corpos = []

    for msg in mensagens:
        txt = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="full")
            .execute()
        )

        payload = txt["payload"]
        corpo = _message_body_as_text(payload)
        if corpo:
            corpos.append(corpo)

    return corpos


def criar_evento(data_hora, material, volume):
    creds = autenticar()
    service = build("calendar", "v3", credentials=creds)

    fim = data_hora + timedelta(hours=1)

    evento = {
        "summary": f"Recebimento - {material}",
        "description": f"Material: {material}\nVolume: {volume} toneladas",
        "start": {
            "dateTime": data_hora.isoformat(),
            "timeZone": "America/Sao_Paulo",
        },
        "end": {
            "dateTime": fim.isoformat(),
            "timeZone": "America/Sao_Paulo",
        },
    }

    event = service.events().insert(calendarId="primary", body=evento).execute()

    print("Evento criado:", event.get("htmlLink"))
