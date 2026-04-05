from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from models import ProgramacaoEntrega

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você extrai dados logísticos de e-mails em português do Brasil. "
            "Datas no formato DD/MM/AAAA são dia/mês/ano (não use interpretação estilo MM/DD). "
            "material: carga ou produto. volume: número (0 se não houver). "
            "data_horario_previsto: só se houver data ou data+hora no texto; caso contrário null. "
            "Para data_horario_previsto use sempre ISO 8601 com ano de quatro dígitos "
            "(ex.: 2026-04-06T12:00:00), sem sufixo Z. Horário em America/Sao_Paulo. "
            "Se só houver a data sem hora, use 12:00. "
            "Não invente datas nem volumes. Não inclua explicações fora dos campos do objeto.",
        ),
        ("human", "Conteúdo do e-mail:\n{email}"),
    ]
)


@lru_cache(maxsize=1)
def _chain():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured = llm.with_structured_output(ProgramacaoEntrega)
    return prompt | structured


def extrair_dados(email_texto: str) -> ProgramacaoEntrega:
    return _chain().invoke({"email": email_texto})
