# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Validator password custom per complessita'.
#        Richiede almeno una maiuscola, una minuscola, un numero
#        e un carattere speciale. Configurabile via settings.
# ------------------------------------------------------------

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """Verifica che la password contenga almeno una lettera maiuscola,
    una minuscola, un numero e un carattere speciale."""

    # Scopo: Valida complessita' password.
    def validate(self, password: str, user=None) -> None:
        errors = []
        if not re.search(r"[A-Z]", password):
            errors.append(_("La password deve contenere almeno una lettera maiuscola."))
        if not re.search(r"[a-z]", password):
            errors.append(_("La password deve contenere almeno una lettera minuscola."))
        if not re.search(r"\d", password):
            errors.append(_("La password deve contenere almeno un numero."))
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>?/~`]", password):
            errors.append(_("La password deve contenere almeno un carattere speciale."))
        if errors:
            raise ValidationError(errors)

    # Scopo: Messaggio di aiuto per l'interfaccia.
    def get_help_text(self) -> str:
        return _(
            "La password deve contenere almeno una lettera maiuscola, "
            "una minuscola, un numero e un carattere speciale."
        )
