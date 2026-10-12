# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli schemi OpenAPI UNICI di «Aggiorna date di consegna»
#        (`POST …/<documento>/<id>/righe/date-consegna/`), per ordine e
#        preventivo (brief-db-date-consegna-righe-in-blocco §8). Le chiavi le
#        decide il contratto del BB `_date_consegna_righe`, non si ricopiano.
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.vendite.services._date_consegna_righe import MODALITA_DATE_CONSEGNA

DATE_CONSEGNA_REQUEST = inline_serializer(
    name="VenditeRigheDateConsegnaReq",
    fields={
        "colonna": serializers.CharField(
            help_text="La data da scrivere: `data_consegna_richiesta_cliente` o, "
                      "sull'ordine, `data_consegna_confermata`.",
        ),
        "data": serializers.DateField(help_text="AAAA-MM-GG."),
        "modalita": serializers.ChoiceField(
            choices=sorted(MODALITA_DATE_CONSEGNA),
            help_text="TUTTE sovrascrive; SOLO_VUOTE scrive dove la data manca.",
        ),
        "anteprima": serializers.BooleanField(
            required=False,
            help_text="true: esegue lo stesso UPDATE e lo annulla (i numeri della "
                      "scrittura; un rifiuto del DB arriva gia' qui).",
        ),
    },
)

DATE_CONSEGNA_RESPONSE = inline_serializer(
    name="VenditeRigheDateConsegnaResp",
    fields={
        "data": inline_serializer(
            name="VenditeRigheDateConsegnaData",
            fields={
                "documento_id": serializers.IntegerField(),
                "colonna": serializers.CharField(),
                "data": serializers.DateField(),
                "modalita": serializers.CharField(),
                "anteprima": serializers.BooleanField(),
                "aggiornate": serializers.IntegerField(),
                "saltate_spedite": serializers.IntegerField(
                    help_text="Righe d'ordine gia' partite con un DDT: la loro "
                              "data confermata non si cambia, e si saltano.",
                ),
            },
        ),
    },
)
