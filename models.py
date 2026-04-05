from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProgramacaoEntrega(BaseModel):
    material: str = Field(
        description="Descrição do material ou carga; use 'Não identificado' se não houver.",
    )
    volume: float = Field(
        description="Volume numérico (unidades, m³ ou toneladas conforme o e-mail); 0 se ausente.",
    )
    data_horario_previsto: Optional[datetime] = Field(
        default=None,
        description=(
            "ISO 8601 com ano de 4 dígitos, ex. 2026-04-06T12:00:00, "
            "horário America/Sao_Paulo, sem Z. Leia DD/MM/AAAA no e-mail como dia/mês/ano. "
            "null se não houver menção."
        ),
    )
