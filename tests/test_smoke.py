import base64
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import gmail_service
from date_utils import (
    SP,
    data_e_plausivel,
    extrair_data_br_do_texto,
    normalizar_data_entrega,
    resolver_data_entrega,
)
from models import ItemProgramacao, ProgramacaoEmail, ProgramacaoEntrega
from report_excel import exportar_relatorio_profissional


class TestMessageBodyAsText(unittest.TestCase):
    def test_root_text_plain(self):
        raw = base64.urlsafe_b64encode(b"hello mail").decode()
        text = gmail_service._message_body_as_text(
            {"mimeType": "text/plain", "body": {"data": raw}},
        )
        self.assertEqual(text, "hello mail")

    def test_nested_multipart(self):
        raw = base64.urlsafe_b64encode(b"nested body").decode()
        text = gmail_service._message_body_as_text(
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": raw}},
                ],
            },
        )
        self.assertEqual(text, "nested body")

    def test_text_html(self):
        html = "<p>Olá <b>mundo</b></p>"
        raw = base64.urlsafe_b64encode(html.encode()).decode()
        text = gmail_service._message_body_as_text(
            {"mimeType": "text/html", "body": {"data": raw}},
        )
        self.assertEqual(text, "Olá mundo")

    def test_multipart_prefers_plain_not_duplicate_html(self):
        """Mesmo conteúdo em plain + HTML não deve virar dois processamentos."""
        plain_raw = base64.urlsafe_b64encode(b"Entrega amanha").decode()
        html_raw = base64.urlsafe_b64encode(b"<p>Entrega amanha</p>").decode()
        text = gmail_service._message_body_as_text(
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": plain_raw}},
                    {"mimeType": "text/html", "body": {"data": html_raw}},
                ],
            },
        )
        self.assertEqual(text, "Entrega amanha")


class TestNormalizarData(unittest.TestCase):
    def test_naive_usa_brasilia(self):
        dt = datetime(2026, 4, 6, 9, 30)
        out = normalizar_data_entrega(dt)
        self.assertEqual(out.tzinfo, SP)
        self.assertEqual(out.hour, 9)

    def test_meia_noite_utc_vira_meio_dia_mesmo_dia_no_br(self):
        """Evita cair em 05/04 no Calendar quando o modelo manda 06/04 00:00 UTC."""
        dt = datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc)
        out = normalizar_data_entrega(dt)
        self.assertEqual(out.tzinfo, SP)
        self.assertEqual((out.year, out.month, out.day), (2026, 4, 6))
        self.assertEqual(out.hour, 12)


class TestExtrairDataBr(unittest.TestCase):
    def test_frase_com_dd_mm_aaaa(self):
        t = (
            "estará chegando no dia 06/04/2026. Uma remessa de 2 toneladas de borracha"
        )
        dt = extrair_data_br_do_texto(t)
        self.assertIsNotNone(dt)
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 4, 6))


class TestResolverData(unittest.TestCase):
    def test_ia_ano_absurdo_cai_para_regex_no_texto(self):
        lixo = datetime(604, 12, 11, 23, 53, tzinfo=SP)
        texto = "estará chegando no dia 06/04/2026. borracha"
        out, aviso = resolver_data_entrega(texto, lixo)
        self.assertIsNotNone(out)
        self.assertEqual((out.year, out.month, out.day), (2026, 4, 6))
        self.assertIsNotNone(aviso)

    def test_ano_604_nao_e_plausivel(self):
        self.assertFalse(data_e_plausivel(datetime(604, 1, 1, tzinfo=SP)))


class TestClientSecretsPath(unittest.TestCase):
    def test_default_is_credentials_json(self):
        with patch.dict(os.environ, {"GOOGLE_OAUTH_CLIENT_SECRETS": ""}):
            p = gmail_service._client_secrets_path()
        self.assertEqual(p, gmail_service._ROOT / "credentials.json")

    def test_env_relative_filename(self):
        with patch.dict(os.environ, {"GOOGLE_OAUTH_CLIENT_SECRETS": "other.json"}):
            p = gmail_service._client_secrets_path()
        self.assertEqual(p, gmail_service._ROOT / "other.json")


class TestProgramacaoModel(unittest.TestCase):
    def test_item_programacao(self):
        it = ItemProgramacao(material="Paletes", volume=12.5)
        self.assertEqual(it.material, "Paletes")
        self.assertEqual(it.volume, 12.5)

    def test_email_com_data(self):
        dt = datetime(2025, 6, 1, 14, 30)
        e = ProgramacaoEmail(
            itens=[ItemProgramacao(material="Paletes", volume=12.5)],
            data_horario_previsto=dt,
        )
        self.assertEqual(len(e.itens), 1)
        self.assertEqual(e.data_horario_previsto, dt)

    def test_data_opcional_no_email(self):
        e = ProgramacaoEmail(
            itens=[ItemProgramacao(material="X", volume=1.0)],
            data_horario_previsto=None,
        )
        self.assertIsNone(e.data_horario_previsto)

    def test_alias_programacao_entrega(self):
        it = ProgramacaoEntrega(material="Parafuso", volume=10)
        self.assertEqual(it.material, "Parafuso")

    def test_multiplos_itens_estilo_lista_email(self):
        dt = datetime(2026, 4, 17, 12, 0)
        e = ProgramacaoEmail(
            itens=[
                ItemProgramacao(material="Parafuso", volume=10),
                ItemProgramacao(material="Porca", volume=8),
                ItemProgramacao(material="Arruela", volume=15),
                ItemProgramacao(material="Rebite", volume=20),
            ],
            data_horario_previsto=dt,
        )
        self.assertEqual(len(e.itens), 4)
        self.assertEqual(e.itens[2].material, "Arruela")


class TestReportExcel(unittest.TestCase):
    def test_gera_xlsx(self):
        df = pd.DataFrame(
            [
                {
                    "material": "Borracha",
                    "volume": 2.0,
                    "data_prevista": "06/04/2026 12:00",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "relatorio.xlsx"
            exportar_relatorio_profissional(df, p)
            self.assertTrue(p.is_file())
            self.assertGreater(p.stat().st_size, 2000)


class TestMaterialRelevante(unittest.TestCase):
    def test_filtra_nao_identificado(self):
        import main

        self.assertFalse(main._material_relevante("Não identificado"))
        self.assertFalse(main._material_relevante("  não identificado  "))
        self.assertFalse(main._material_relevante(""))
        self.assertTrue(main._material_relevante("borracha"))


class TestImports(unittest.TestCase):
    def test_main_imports(self):
        import main  # noqa: F401

        self.assertEqual(main.OUTPUT_DIR.name, "outputs")


if __name__ == "__main__":
    unittest.main()
