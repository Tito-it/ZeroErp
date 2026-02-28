# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Modelli ORM managed=False per le tabelle permessi dello schema config.
# ------------------------------------------------------------

from django.db import models


# ── Strutture base ─────────────────────────────────────────


class AreaFunzionale(models.Model):
    """Area funzionale del sistema permessi (1 area = 1 schema DB)."""

    id = models.IntegerField(primary_key=True)
    codice = models.CharField(max_length=50, unique=True)
    codice_interno = models.CharField(max_length=50, unique=True)
    descrizione = models.CharField(max_length=200)
    schema_db = models.CharField(max_length=50, unique=True)
    attivo = models.BooleanField(default=True)
    ordinamento = models.SmallIntegerField(default=0)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."aree_funzionali'
        ordering = ["ordinamento"]

    def __str__(self) -> str:
        return self.codice


class AzioneProcesso(models.Model):
    """Azione di processo gestibile nell'interfaccia permessi."""

    id = models.IntegerField(primary_key=True)
    area = models.ForeignKey(
        AreaFunzionale,
        on_delete=models.DO_NOTHING,
        db_column="area_id",
        related_name="azioni",
    )
    permission_codename = models.CharField(max_length=100, unique=True)
    descrizione = models.CharField(max_length=200)
    pericolosa = models.BooleanField(default=False)
    attivo = models.BooleanField(default=True)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."azioni_processo'

    def __str__(self) -> str:
        return self.permission_codename


class AreaModelOverride(models.Model):
    """Override: riassegna un model Django a un'area diversa dal suo schema."""

    id = models.IntegerField(primary_key=True)
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    area = models.ForeignKey(
        AreaFunzionale,
        on_delete=models.DO_NOTHING,
        db_column="area_id",
        related_name="model_overrides",
    )
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."area_model_overrides'
        constraints = [
            models.UniqueConstraint(
                fields=["app_label", "model_name"],
                name="uq_area_model_overrides_app_model",
            )
        ]

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model_name} -> {self.area_id}"


# ── Profili reparto (ereditarieta') ────────────────────────


class ProfiloRepartoArea(models.Model):
    """Profilo accesso ereditato: livello per area per ogni reparto."""

    LIVELLO_CHOICES = [
        ("TUTTO", "Tutto"),
        ("LETTURA", "Lettura"),
        ("BLOCCATO", "Bloccato"),
    ]

    id = models.IntegerField(primary_key=True)
    unita_organizzativa_id = models.IntegerField()
    area = models.ForeignKey(
        AreaFunzionale,
        on_delete=models.DO_NOTHING,
        db_column="area_id",
        related_name="profili_reparto",
    )
    livello = models.CharField(
        max_length=10, choices=LIVELLO_CHOICES, default="BLOCCATO"
    )
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."profili_reparto_aree'
        constraints = [
            models.UniqueConstraint(
                fields=["unita_organizzativa_id", "area"],
                name="uq_profili_reparto_aree_uo_area",
            )
        ]


class ProfiloRepartoAzione(models.Model):
    """Azioni di processo abilitate per reparto."""

    id = models.IntegerField(primary_key=True)
    unita_organizzativa_id = models.IntegerField()
    azione = models.ForeignKey(
        AzioneProcesso,
        on_delete=models.DO_NOTHING,
        db_column="azione_id",
        related_name="profili_reparto",
    )
    abilitata = models.BooleanField(default=False)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."profili_reparto_azioni'
        constraints = [
            models.UniqueConstraint(
                fields=["unita_organizzativa_id", "azione"],
                name="uq_profili_reparto_azioni_uo_azione",
            )
        ]


# ── Override utente ────────────────────────────────────────


class UserOverrideArea(models.Model):
    """Override individuale su area funzionale."""

    id = models.BigAutoField(primary_key=True)
    auth_user_id = models.IntegerField()
    area = models.ForeignKey(
        AreaFunzionale,
        on_delete=models.DO_NOTHING,
        db_column="area_id",
        related_name="user_overrides",
    )
    livello = models.CharField(max_length=10)
    motivo = models.TextField(null=True, blank=True)
    valido_dal = models.DateField(null=True, blank=True)
    valido_al = models.DateField(null=True, blank=True)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."user_override_aree'
        constraints = [
            models.UniqueConstraint(
                fields=["auth_user_id", "area"],
                name="uq_user_override_aree_user_area",
            )
        ]


class UserOverrideOggetto(models.Model):
    """Override individuale su singolo model."""

    id = models.BigAutoField(primary_key=True)
    auth_user_id = models.IntegerField()
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    livello = models.CharField(max_length=10)
    motivo = models.TextField(null=True, blank=True)
    valido_dal = models.DateField(null=True, blank=True)
    valido_al = models.DateField(null=True, blank=True)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."user_override_oggetti'
        constraints = [
            models.UniqueConstraint(
                fields=["auth_user_id", "app_label", "model_name"],
                name="uq_user_override_oggetti_user_app_model",
            )
        ]


class UserOverrideAzione(models.Model):
    """Override individuale su azione di processo."""

    id = models.BigAutoField(primary_key=True)
    auth_user_id = models.IntegerField()
    azione = models.ForeignKey(
        AzioneProcesso,
        on_delete=models.DO_NOTHING,
        db_column="azione_id",
        related_name="user_overrides",
    )
    abilitata = models.BooleanField()
    motivo = models.TextField(null=True, blank=True)
    valido_dal = models.DateField(null=True, blank=True)
    valido_al = models.DateField(null=True, blank=True)
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."user_override_azioni'
        constraints = [
            models.UniqueConstraint(
                fields=["auth_user_id", "azione"],
                name="uq_user_override_azioni_user_azione",
            )
        ]


# ── Scope emittente fiscale ────────────────────────────────


class UserEmittenteFiscale(models.Model):
    """Scope operativo: whitelist opzionale emittenti fiscali per utente."""

    id = models.BigAutoField(primary_key=True)
    auth_user_id = models.IntegerField()
    emittente_fiscale_id = models.BigIntegerField()
    meta = models.JSONField(default=dict)
    data_insert = models.DateTimeField(auto_now_add=True)
    user_insert = models.TextField(default="")
    data_update = models.DateTimeField(auto_now=True)
    user_update = models.TextField(default="")

    class Meta:
        managed = False
        db_table = 'config"."user_emittenti_fiscali'
        constraints = [
            models.UniqueConstraint(
                fields=["auth_user_id", "emittente_fiscale_id"],
                name="uq_user_emittenti_fiscali_user_emittente",
            )
        ]
