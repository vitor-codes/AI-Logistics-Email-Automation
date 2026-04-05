from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ItemProgramacao(BaseModel):
    material: str = Field(
        description="Nome do item ou material (ex.: Parafuso, Porca).",
    )
    volume: float = Field(
        description=(
            "Quantidade numérica associada ao item (unidades, volumes, toneladas, etc.); "
            "0 se não houver número explícito para esse item."
        ),
    )


class ProgramacaoEmail(BaseModel):
    """
    Um e-mail pode listar vários itens com volumes distintos e uma data comum de entrega.
    """

    itens: list[ItemProgramacao] = Field(
        description=(
            "Um elemento por item/material mencionado (listas com '-', números, tabelas). "
            "Se o e-mail falar de um único material, use uma lista com um único elemento. "
            "Não agrupe vários nomes em um só material."
        ),
    )
    data_horario_previsto: Optional[datetime] = Field(
        default=None,
        description=(
            "Data/hora da entrega prevista para a remessa (comum a todos os itens quando "
            "houver uma só data no texto). ISO 8601 com ano de 4 dígitos, ex. 2026-04-17T12:00:00, "
            "sem Z; horário America/Sao_Paulo; se só data, use 12:00. "
            "Leia DD/MM/AAAA como dia/mês/ano. null se não houver menção."
        ),
    )


# Alias legado para documentação / compatibilidade conceitual
ProgramacaoEntrega = ItemProgramacao
