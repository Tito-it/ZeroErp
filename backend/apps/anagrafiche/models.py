# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

    Rimpiazza il vecchio `RisorseUmaneAuthUser` per supportare, oltre
    all'operatore interno (ruolo_applicativo=OPERATORE), le identita
    portale cliente/fornitore, shop customer e API client.

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
    deve_cambiare_password = models.BooleanField(default=False)
    invito_inviato_at = models.DateTimeField(null=True, blank=True)
    tentativi_falliti = models.SmallIntegerField(default=0)
    bloccato_fino_a = models.DateTimeField(null=True, blank=True)
    totp_obbligatorio = models.BooleanField(default=False)
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


class RisorseUmaneAuthUser(models.Model):
    """Ponte 1:1 tra risorsa umana e auth_user. Include ruolo_sistema per permessi.

    DEPRECATO: post-cutover §4.6.H.2 questa "tabella" e' in realta' una
    vista su `identita_digitali` (leggibile, non scrivibile). I nuovi
    writer usano `IdentitaDigitale` direttamente. Mantenuto come
    `managed=False` per i reader legacy in transizione.
    """

    RUOLO_SISTEMA_CHOICES = [
        ("ADMIN", "Admin"),
        ("OPERATIVO", "Operativo"),
        ("DISABILITATO", "Disabilitato"),
    ]

    id = models.BigAutoField(primary_key=True)
    risorsa_umana = models.OneToOneField(
        RisorseUmane,
        on_delete=models.DO_NOTHING,
        db_column="risorsa_umana_id",
        related_name="auth_bridge",
    )
    auth_user_id = models.IntegerField(unique=True)
    attivo = models.BooleanField(default=True)
    ruolo_sistema = models.CharField(
        max_length=15,
        choices=RUOLO_SISTEMA_CHOICES,
        default="OPERATIVO",
    )
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'anagrafiche"."risorse_umane_auth_user'

    def __str__(self) -> str:
        return f"RisorseUmaneAuthUser(auth_user_id={self.auth_user_id})"
