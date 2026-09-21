from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .services import PliegoServiceError, find_pliegos_con_apertura_proxima


class FindPliegosConAperturaProximaTests(TestCase):
    @patch("pliegos.services.get_soap_client")
    def test_parses_list_response(self, mock_get_client):
        mock_operation = mock_get_client.return_value.service.FindPliegosConAperturaProxima
        mock_operation.return_value = [
            {"IdPliego": 1, "Numero": "001/2026", "Objeto": "Compra de insumos"},
            {"IdPliego": 2, "Numero": "002/2026", "Objeto": "Servicio de limpieza"},
        ]

        results = find_pliegos_con_apertura_proxima()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["Numero"], "001/2026")

    @patch("pliegos.services.get_soap_client")
    def test_wraps_soap_errors(self, mock_get_client):
        from zeep.exceptions import Fault

        mock_operation = mock_get_client.return_value.service.FindPliegosConAperturaProxima
        mock_operation.side_effect = Fault("boom")

        with self.assertRaises(PliegoServiceError):
            find_pliegos_con_apertura_proxima()


class PliegosViewTests(TestCase):
    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_html_view_renders_results(self, mock_find):
        mock_find.return_value = [{"Numero": "001/2026", "Objeto": "Compra de insumos"}]

        response = self.client.get(reverse("pliegos:proxima-apertura"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "001/2026")

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_html_view_shows_error_on_service_failure(self, mock_find):
        mock_find.side_effect = PliegoServiceError("WSDL inalcanzable")

        response = self.client.get(reverse("pliegos:proxima-apertura"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WSDL inalcanzable")

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_json_view_returns_results(self, mock_find):
        mock_find.return_value = [{"Numero": "001/2026"}]

        response = self.client.get(reverse("pliegos:proxima-apertura-json"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    @patch("pliegos.views.find_pliegos_con_apertura_proxima")
    def test_json_view_returns_502_on_service_failure(self, mock_find):
        mock_find.side_effect = PliegoServiceError("WSDL inalcanzable")

        response = self.client.get(reverse("pliegos:proxima-apertura-json"))

        self.assertEqual(response.status_code, 502)
