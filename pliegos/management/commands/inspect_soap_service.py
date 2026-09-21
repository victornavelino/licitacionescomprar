from django.core.management.base import BaseCommand, CommandError

from pliegos.services import PliegoServiceError, list_operations


class Command(BaseCommand):
    help = (
        "Imprime las operaciones disponibles en el WSDL configurado "
        "(PLIEGOS_WSDL_URL) junto con la firma de cada una. Requiere acceso "
        "de red al WSDL real; útil para confirmar el nombre exacto de los "
        "parámetros de FindPliegosConAperturaProxima."
    )

    def handle(self, *args, **options):
        try:
            operations = list_operations()
        except PliegoServiceError as exc:
            raise CommandError(str(exc)) from exc

        if not operations:
            self.stdout.write(self.style.WARNING("El WSDL no expone operaciones."))
            return

        for name, signature in sorted(operations.items()):
            self.stdout.write(f"{name}({signature})")
