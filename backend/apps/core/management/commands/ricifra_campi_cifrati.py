# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Ri-cifra con la PRIMA chiave di `DJANGO_FIELD_ENCRYPTION_KEYS` ogni
#        colonna iscritta in `crypto_service.CAMPI_CIFRATI`. E' il passo di
#        mezzo della rotazione: chiave nuova in testa → questo comando →
#        chiave vecchia tolta.
# Note: ⭐ `--anche-chiave-da-secret-key` e' la MIGRAZIONE una-tantum dei dati
#       cifrati prima del 2026-09-28, quando la chiave Fernet era derivata
#       dalla SECRET_KEY (SHA-256, base64): la aggiunge in coda, solo per
#       decifrare. Va lanciata PRIMA di ruotare la SECRET_KEY, con quella
#       ancora in uso (brief-be-fe-sicurezza-header-token-mfa §3.5).
#       ⛔ Tutto o niente: se un token non si apre con nessuna chiave il comando
#       fallisce e non scrive nulla. Quel segreto va reinserito (es. la password
#       SMTP dal drawer dell'account), poi si rilancia.
#       Comando manuale, non una sveglia: non si registra in `job_run_log`.
# ------------------------------------------------------------

from __future__ import annotations

import base64
import hashlib

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.core.services import crypto_service
from apps.core.services.crypto_service import CampoCifrato


# Scopo: La chiave Fernet come la derivava `crypto_service` fino al 2026-09-28.
#        Vive solo qui: serve a leggere i dati di allora, mai a scriverne.
def _chiave_derivata_da_secret_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


# Scopo: Le righe con un token da ri-cifrare. Tabella e colonna vengono da
#        `CAMPI_CIFRATI`, letterali del codice. `FOR UPDATE`: nessuno riscrive
#        il segreto fra la lettura e la scrittura.
def _righe_cifrate(campo: CampoCifrato) -> list[tuple[int, str]]:
    sql = (
        f"SELECT id, {campo.colonna} FROM {campo.tabella} "  # noqa: S608 — tabella/colonna letterali di CAMPI_CIFRATI
        f"WHERE {campo.colonna} IS NOT NULL AND {campo.colonna} <> '' "
        "ORDER BY id FOR UPDATE"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


class Command(BaseCommand):
    help = (
        "Ri-cifra con la prima chiave di DJANGO_FIELD_ENCRYPTION_KEYS tutti i "
        "segreti salvati nel DB. Tutto o niente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Verifica che ogni token si apra e conta, senza scrivere.",
        )
        parser.add_argument(
            "--anche-chiave-da-secret-key", action="store_true",
            help=(
                "Decifra anche con la chiave derivata dalla SECRET_KEY attuale "
                "(migrazione dei dati cifrati prima del 2026-09-28)."
            ),
        )

    # Scopo: Per ogni campo iscritto legge i token, li ri-cifra e li riscrive,
    #        in UNA transazione. Un token illeggibile annulla tutto.
    def handle(self, *args, **options):
        chiavi_extra = (
            [_chiave_derivata_da_secret_key()] if options["anche_chiave_da_secret_key"] else []
        )
        illeggibili: list[str] = []
        with transaction.atomic():
            for campo in crypto_service.CAMPI_CIFRATI:
                righe = _righe_cifrate(campo)
                nuovi: list[tuple[int, str]] = []
                for row_id, token in righe:
                    try:
                        nuovi.append((row_id, crypto_service.ricifra(token, chiavi_extra=chiavi_extra)))
                    except ValueError:
                        illeggibili.append(f"{campo.tabella}.{campo.colonna} id={row_id}")
                if not options["dry_run"]:
                    for row_id, nuovo in nuovi:
                        # ⛔ Una riga letta e non riscritta (RLS, trigger) e'
                        #    un token rimasto sulla chiave vecchia: si fallisce,
                        #    non si conta come ri-cifrata.
                        if not execute_dynamic_update(
                            campo.tabella, row_id, {campo.colonna: nuovo},
                            allowed={campo.colonna}, letterali={campo.colonna},
                        ):
                            raise CommandError(
                                f"{campo.tabella}.{campo.colonna} id={row_id}: "
                                "UPDATE senza righe, niente e' stato scritto"
                            )
                self.stdout.write(f"{campo.tabella}.{campo.colonna}: {len(nuovi)} su {len(righe)}")
            if illeggibili:
                raise CommandError(
                    "Nessuna chiave apre questi token, niente e' stato scritto: "
                    + ", ".join(illeggibili)
                )
        esito = "verificati (dry-run, nulla scritto)" if options["dry_run"] else "ri-cifrati"
        self.stdout.write(self.style.SUCCESS(f"Segreti {esito}."))
