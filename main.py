from datetime import datetime
from pathlib import Path

import pandas as pd
from googleapiclient.errors import HttpError

from date_utils import SP, resolver_data_entrega
from extractor_chain import extrair_dados
from gmail_service import buscar_emails_remetente, criar_evento
from report_excel import exportar_relatorio_profissional

_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = _ROOT / "outputs"

REMETENTE_LOGISTICO = ["seufornecedor@gmail.com"]


def _material_relevante(material) -> bool:
    t = (material or "").strip()
    if not t:
        return False
    return t.casefold() != "não identificado".casefold()


def main():
    registros = []

    for remetente in REMETENTE_LOGISTICO:
        emails = buscar_emails_remetente(remetente)

        for email in emails:
            texto = (email or "").strip()
            if not texto:
                continue
            try:
                dados = extrair_dados(texto)

                data_dt, aviso_data = resolver_data_entrega(
                    texto, dados.data_horario_previsto
                )
                if aviso_data:
                    print(aviso_data)

                if data_dt:
                    data_formatada = data_dt.astimezone(SP).strftime("%d/%m/%Y %H:%M")
                else:
                    data_formatada = ""

                registros.append(
                    {
                        "material": dados.material,
                        "volume": dados.volume,
                        "data_prevista": data_formatada,
                        "data_datetime": data_dt,
                    }
                )

            except Exception as e:
                print("Não foi possível extrair:", e)

    antes = len(registros)
    registros = [r for r in registros if _material_relevante(r["material"])]
    omitidos = antes - len(registros)
    if omitidos:
        print(
            f"Ignorados {omitidos} registro(s) sem material útil "
            "(vazio ou 'Não identificado')."
        )

    if not registros:
        print(
            "Nenhum registro extraído. Verifique REMETENTE_LOGISTICO, se há e-mails "
            "desse remetente e se o corpo tem texto (plain ou HTML)."
        )
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    df = pd.DataFrame(registros)
    nome_arquivo = (
        OUTPUT_DIR
        / f"Relatorio_programacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    df_out = df.drop(columns=["data_datetime"]).copy()
    exportar_relatorio_profissional(df_out, nome_arquivo)

    print("Arquivo salvo com sucesso:", nome_arquivo)

    for registro in registros:
        if not registro["data_datetime"]:
            continue
        try:
            criar_evento(
                registro["data_datetime"],
                registro["material"],
                registro["volume"],
            )
        except HttpError as e:
            print(
                "Não foi possível criar evento no Google Calendar:",
                getattr(e, "reason", None) or str(e),
            )


if __name__ == "__main__":
    main()
