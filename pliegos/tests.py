from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse

from .services import PliegoServiceError, find_pliegos_con_apertura_proxima

SAMPLE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<ArrayOfPliegoWSDTO xmlns="http://tempuri.org/">
  <PliegoWSDTO>
    <numeroExpediente>EX-2026-001</numeroExpediente>
    <unidadEjecutora>Direccion X</unidadEjecutora>
    <servicioAdministrativoFinanciero>Direccion X</servicioAdministrativoFinanciero>
    <fechaActoApertura>23/09/2026 10:00 Hrs.</fechaActoApertura>
    <montoContratacion>1000,00</montoContratacion>
    <modalidad>Compra Determinada</modalidad>
    <nombreTipoSeleccionPliego>Licitaci\xc3\xb3n P\xc3\xbablica</nombreTipoSeleccionPliego>
    <objetoContratacion>Compra de insumos</objetoContratacion>
    <lnkNumeroProceso>https://comprar.catamarca.gob.ar/PLIEGO/x</lnkNumeroProceso>
    <actosAdministrativo>
      <ActoAdministrativoWSDTO>
        <documento>Autorizacion_llamado</documento>
        <numeroGDE>RS-2026-1</numeroGDE>
        <numeroEspecial>RESOL-2026-1</numeroEspecial>
      </ActoAdministrativoWSDTO>
    </actosAdministrativo>
    <idPliego>1</idPliego>
  </PliegoWSDTO>
</ArrayOfPliegoWSDTO>
"""


class FindPliegosConAperturaProximaTests(TestCase):
    @patch("pliegos.services.requests.get")
    def test_parses_xml_response(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=SAMPLE_XML)
        mock_get.return_value.raise_for_status = Mock()

        results = find_pliegos_con_apertura_proxima()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["numeroExpediente"], "EX-2026-001")
        self.assertEqual(results[0]["idPliego"], "1")
        self.assertEqual(len(results[0]["actosAdministrativo"]), 1)
        self.assertEqual(
            results[0]["actosAdministrativo"][0]["documento"], "Autorizacion_llamado"
        )

    @patch("pliegos.services.requests.get")
    def test_wraps_network_errors(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("boom")

        with self.assertRaises(PliegoServiceError):
            find_pliegos_con_apertura_proxima()

    @patch("pliegos.services.requests.get")
    def test_wraps_invalid_xml(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=b"not xml")
        mock_get.return_value.raise_for_status = Mock()

        with self.assertRaises(PliegoServiceError):
            find_pliegos_con_apertura_proxima()


class PliegosViewTests(TestCase):
    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_html_view_renders_results(self, mock_find):
        mock_find.return_value = [
            {
                "numeroExpediente": "EX-2026-001",
                "unidadEjecutora": "Direccion X",
                "fechaActoApertura": "23/09/2026 10:00 Hrs.",
                "montoContratacion": "1000,00",
                "modalidad": "Compra Determinada",
                "nombreTipoSeleccionPliego": "Licitación Pública",
                "objetoContratacion": "Compra de insumos",
                "lnkNumeroProceso": "https://comprar.catamarca.gob.ar/PLIEGO/x",
                "actosAdministrativo": [],
                "idPliego": "1",
            }
        ]

        response = self.client.get(reverse("pliegos:proxima-apertura"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EX-2026-001")

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_html_view_shows_error_on_service_failure(self, mock_find):
        mock_find.side_effect = PliegoServiceError("WS inalcanzable")

        response = self.client.get(reverse("pliegos:proxima-apertura"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WS inalcanzable")

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_json_view_returns_results(self, mock_find):
        mock_find.return_value = [{"numeroExpediente": "EX-2026-001"}]

        response = self.client.get(reverse("pliegos:proxima-apertura-json"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_json_view_returns_502_on_service_failure(self, mock_find):
        mock_find.side_effect = PliegoServiceError("WS inalcanzable")

        response = self.client.get(reverse("pliegos:proxima-apertura-json"))

        self.assertEqual(response.status_code, 502)
