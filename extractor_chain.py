from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from models import ProgramacaoEmail

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você extrai dados logísticos de e-mails em português do Brasil. "
            "Datas DD/MM/AAAA são dia/mês/ano (não use MM/DD). "
            "Quando houver lista de materiais (marcadores '-', números, ou linhas separadas), "
            "cada linha vira um item em 'itens' com seu material e volume numérico. "
            "Ex.: 'Parafuso: 10 volumes' → material Parafuso, volume 10. "
            "A data de chegada comum a todos os itens vai em data_horario_previsto (uma vez). "
            "Para data_horario_previsto use ISO 8601 com ano de quatro dígitos "
            "(ex.: 2026-04-17T12:00:00), sem sufixo Z; horário America/Sao_Paulo; "
            "se só houver data sem hora, use 12:00. "
            "Não invente dados. Não inclua explicações fora dos campos do objeto.",
        ),
        ("human", "Conteúdo do e-mail:\n{email}"),
    ]
)


@lru_cache(maxsize=1)
def _chain():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured = llm.with_structured_output(ProgramacaoEmail)
    return prompt | structured


def extrair_dados(email_texto: str) -> ProgramacaoEmail:
    return _chain().invoke({"email": email_texto})
