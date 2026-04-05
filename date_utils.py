"""Normalização e validação de datas para America/Sao_Paulo (e-mails em português / calendário)."""

import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc

# Entregas logísticas: rejeita anos absurdos (ex.: 604) que a IA ou o parser podem gerar
DATA_MIN_YEAR = 2020
DATA_MAX_YEAR = 2100

_BR_DATA = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])/(0?[1-9]|1[0-2])/(\d{4})\b"
)


def data_e_plausivel(dt: datetime | None) -> bool:
    if dt is None:
        return False
    y = dt.astimezone(SP).year
    return DATA_MIN_YEAR <= y <= DATA_MAX_YEAR


def normalizar_data_entrega(dt: datetime | None) -> datetime | None:
    """
    Evita evento no dia errado no Calendar quando o modelo devolve meia-noite em UTC (Z):
    2026-04-06T00:00:00+00:00 vira 05/04 à noite no Brasil — o usuário quer o dia 06 no calendário.

    - Datetime sem fuso: assume horário de Brasília.
    - Meia-noite exata em UTC: trata como *data civil* e usa 12:00 em Brasília (evita troca de dia).
    - Demais valores com fuso: converte para America/Sao_Paulo.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SP)
    utc = dt.astimezone(UTC)
    if (
        utc.hour == 0
        and utc.minute == 0
        and utc.second == 0
        and utc.microsecond == 0
    ):
        d = utc.date()
        return datetime.combine(d, time(12, 0), tzinfo=SP)
    return dt.astimezone(SP)


def extrair_data_br_do_texto(texto: str) -> datetime | None:
    """
    Primeira data DD/MM/AAAA plausível no texto (meio-dia, sem fuso — normalizar depois).
    Usado quando a IA devolve ano inválido ou lixo.
    """
    if not texto:
        return None
    for m in _BR_DATA.finditer(texto):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (DATA_MIN_YEAR <= ano <= DATA_MAX_YEAR):
            continue
        try:
            return datetime(ano, mes, dia, 12, 0, 0)
        except ValueError:
            continue
    return None


def resolver_data_entrega(
    texto_email: str,
    data_ia: datetime | None,
) -> tuple[datetime | None, str | None]:
    """
    Retorna (datetime em SP ou None, aviso opcional).
    Prioriza a IA normalizada; se implausível, tenta DD/MM/AAAA no corpo do e-mail.
    """
    data_dt = normalizar_data_entrega(data_ia)
    if data_e_plausivel(data_dt):
        return data_dt, None

    if data_dt is not None:
        aviso = (
            f"Data da IA fora do intervalo ou inválida ({data_dt.astimezone(SP)}); "
            "tentando DD/MM/AAAA no texto do e-mail."
        )
    else:
        aviso = None

    fb = extrair_data_br_do_texto(texto_email)
    if fb is None:
        return None, aviso

    data_dt = normalizar_data_entrega(fb)
    if data_e_plausivel(data_dt):
        return data_dt, aviso
    return None, aviso
