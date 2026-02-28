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


class RisorseUmaneAuthUser(models.Model):
    """Ponte 1:1 tra risorsa umana e auth_user. Include ruolo_sistema per permessi."""

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
