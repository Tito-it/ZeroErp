# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Modelli ORM managed=False per tabelle anagrafiche usate dal sistema permessi.
# ------------------------------------------------------------

from django.db import models


class RisorseUmane(models.Model):
    """Risorsa umana (dipendente/collaboratore). Solo campi necessari per il resolver permessi."""

    id = models.BigAutoField(primary_key=True)
    soggetto_ruolo_id = models.BigIntegerField()
    qualifica_id = models.IntegerField(null=True, blank=True)
    unita_organizzativa_id = models.IntegerField(null=True, blank=True)
    attivo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'anagrafiche"."risorse_umane'

    def __str__(self) -> str:
        return f"RisorseUmane(id={self.id})"


class IdentitaDigitale(models.Model):
    """Bridge generico soggetto_ruolo <-> auth_user.

    Rimpiazza il vecchio ponte 1:1 `risorse_umane_auth_user` per supportare,
    oltre all'operatore interno (ruolo_applicativo=OPERATORE), le identita
    portale cliente/fornitore, shop customer e API client.

    ⛔ E' l'UNICO model del ponte. Fino al 2026-09-12 qui sotto viveva anche
    un model `managed=False` sulla vista di compatibilita' col nome vecchio
    (`risorse_umane_auth_user`, «tenuto per i reader»): un secondo nome per
    la stessa cosa, che nascondeva nel corpo della vista il filtro OPERATORE
    e la proiezione RU. Ritirato con i suoi lettori
    (analisi-software-per-dati-morti §2.1, «strato 2»); il DB ritira la vista.
    ⚠️ Il nome del model ritirato non si scrive nemmeno qui: e' il canale con
    cui un oggetto morto rientra (analisi §0), e lo presidia
    `core/tests/db/test_risorsa_umana_dalla_madre`.
    Il legame con la risorsa umana si fa per `soggetto_ruolo_id` verso
    `RisorseUmane`, che e' come lo fa `script.fn_get_user_profile`.

    Vedi guida `architettura-multi-face-auth.md` sezione 3 e WIP
    `sviluppo-multi-face-auth.md` sezione 4.2 per il modello dati.
    """

    RUOLO_APPLICATIVO_CHOICES = [
        ("OPERATORE", "Operatore"),
        ("CLIENTE_PORTALE", "Cliente portale"),
        ("FORNITORE_PORTALE", "Fornitore portale"),
        ("SHOP_CUSTOMER", "Shop customer"),
        ("API_CLIENT", "API client"),
        ("DISABILITATO", "Disabilitato"),
    ]

    id = models.BigAutoField(primary_key=True)
    soggetto_ruolo_id = models.BigIntegerField()
    auth_user_id = models.IntegerField(unique=True)
    ruolo_applicativo = models.CharField(
        max_length=20,
        choices=RUOLO_APPLICATIVO_CHOICES,
    )
    attivo = models.BooleanField(default=True)
    valido_dal = models.DateField(null=True, blank=True)
    valido_al = models.DateField(null=True, blank=True)
    invito_inviato_at = models.DateTimeField(null=True, blank=True)
    # Tentativi falliti, blocco, cambio password obbligatorio e TOTP sono
    # della CREDENZIALE, non della veste: config.credenziali (2026-09-25).
    storicizza = models.BooleanField(default=True)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'anagrafiche"."identita_digitali'

    def __str__(self) -> str:
        return (
            f"IdentitaDigitale(auth_user_id={self.auth_user_id}, "
            f"ruolo_applicativo={self.ruolo_applicativo})"
        )
