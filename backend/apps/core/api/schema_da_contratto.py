# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block — lo schema OpenAPI del corpo di una scrittura si LEGGE
#        dal contratto del service o della view (l'insieme delle chiavi che
#        accetta), non si ricopia. Il TIPO di ogni chiave lo dichiara il
#        dominio, una volta, in un dizionario suo (`tipi`).
# Note: ⭐ Nato in vendite il 2026-09-26 e traslocato qui lo stesso giorno
#       (regola del 2, ok Tid), quando email (core) e amm_software hanno avuto
#       lo stesso bisogno: un contratto di chiavi accanto a uno schema scritto a
#       mano diverge al primo cambio, e nessuna delle due parti da' un errore —
#       una chiave fuori contratto il service la scarta o la rifiuta, e un
#       client che segue la documentazione non sa perche'.
#       ⛔ Una chiave del contratto senza tipo nel dizionario del dominio e' un
#       errore ALL'IMPORT: le due sedi non possono divergere in silenzio.
#       ⭐ I dizionari: `vendite/api/_schema_da_contratto.py` (documenti di
#       vendita), `core/api/schema_email.py` (bozze, template, account email).
#       Cio' che il service valida oltre al tipo (domini, obbligatorieta'
#       incrociate) resta al service: lo schema non lo ripete.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from collections.abc import Callable, Iterable, Mapping

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

# Il tipo di una chiave: la fabbrica del campo e se la colonna ammette NULL.
Fabbrica = Callable[..., serializers.Field]
Tipi = Mapping[str, tuple[Fabbrica, bool]]


# Scopo: fabbriche dei campi, parametriche su `required` / `allow_null`: un
#        campo DRF e' legato al serializer che lo contiene, quindi se ne crea
#        uno per uso.
def intero(**kw: Any) -> serializers.Field:
    return serializers.IntegerField(**kw)


def decimale(**kw: Any) -> serializers.Field:
    return serializers.DecimalField(max_digits=22, decimal_places=10, **kw)


def data(**kw: Any) -> serializers.Field:
    return serializers.DateField(**kw)


def testo(**kw: Any) -> serializers.Field:
    return serializers.CharField(**kw)


def json(**kw: Any) -> serializers.Field:
    return serializers.JSONField(**kw)


def booleano(**kw: Any) -> serializers.Field:
    return serializers.BooleanField(**kw)


def uuid(**kw: Any) -> serializers.Field:
    return serializers.UUIDField(**kw)


def lista_di_testi(**kw: Any) -> serializers.Field:
    return serializers.ListField(child=serializers.CharField(), **kw)


# Scopo: lo schema del corpo di una scrittura, dalle chiavi del contratto.
#        `tipi`: il dizionario del dominio. `obbligatorie`: le chiavi senza cui
#        il service rifiuta (le altre sono facoltative, come le tratta il
#        service). `speciali`: le chiavi il cui valore non e' una colonna (un
#        oggetto o una lista annidati), col campo gia' costruito — anche fuori
#        dal contratto, quando il service le legge a parte.
def schema_da_contratto(
    nome: str,
    chiavi: Iterable[str],
    *,
    tipi: Tipi,
    obbligatorie: Iterable[str] = (),
    speciali: Mapping[str, serializers.Field] | None = None,
) -> serializers.Serializer:
    chiavi = frozenset(chiavi)
    obbligatorie = frozenset(obbligatorie)
    speciali = dict(speciali or {})
    fuori = sorted(obbligatorie - chiavi)
    senza_tipo = sorted(chiavi - tipi.keys() - speciali.keys())
    if fuori or senza_tipo:
        raise RuntimeError(
            f"schema_da_contratto({nome}): obbligatorie fuori contratto {fuori}, "
            f"chiavi del contratto senza tipo {senza_tipo}"
        )

    campi: dict[str, serializers.Field] = {}
    # ⚠️ Anche le `speciali` fuori dal contratto: scorrere le sole chiavi del
    #    contratto le perdeva dallo schema (difetto del 2026-09-26, test 0).
    for chiave in sorted(chiavi | speciali.keys()):
        if chiave in speciali:
            campi[chiave] = speciali[chiave]
            continue
        fabbrica, nullable = tipi[chiave]
        if chiave in obbligatorie:
            campi[chiave] = fabbrica()
        else:
            campi[chiave] = fabbrica(required=False, allow_null=nullable)
    return inline_serializer(name=nome, fields=campi)
