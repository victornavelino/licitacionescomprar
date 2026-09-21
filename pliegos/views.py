import logging

from django.http import JsonResponse
from django.shortcuts import render

from .services import PliegoServiceError, find_pliegos_con_apertura_proxima

logger = logging.getLogger(__name__)


def pliegos_proxima_apertura(request):
    """Muestra en una página HTML los pliegos con apertura próxima."""
    try:
        results = find_pliegos_con_apertura_proxima()
        error = None
    except PliegoServiceError as exc:
        logger.warning("Fallo al consumir ServicioPliegoWS: %s", exc)
        results = []
        error = str(exc)

    return render(
        request,
        "pliegos/lista.html",
        {"results": results, "error": error},
    )


def pliegos_proxima_apertura_json(request):
    """Devuelve en JSON crudo lo que responde FindPliegosConAperturaProxima."""
    try:
        results = find_pliegos_con_apertura_proxima()
    except PliegoServiceError as exc:
        logger.warning("Fallo al consumir ServicioPliegoWS: %s", exc)
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"count": len(results), "results": results})
