# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB del modulo amministrazione.
# Gestisce query operatori, override permessi e profili reparto.
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from typing import Any, ClassVar, cast

from django.db import DatabaseError, connection, transaction

from apps.core.db._helpers import (
    colonna_ordinamento,
    sql_order_direction_lista,
    predicato_giorno_operativo,
    limiti_pagina,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    jsonb_out,
    RicercaFull,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
    sql_order_direction,
    sql_tiebreak_direction,
)

from apps.core.services.auth_constants import (
    CATEGORIA_ACCESSO_OPERATORE,
    RUOLO_APPLICATIVO_OPERATORE,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import MISSING, MissingType
from apps.amm_software.constants import DEFAULT_LIMIT
from apps.amm_software.types import CredenzialePerEmailRow, OperatoreDetailRow, OperatoreRow

# ⛔ IL TAB DELL'AREA ACCESSI IN CUI STA UNA CREDENZIALE LO DICE IL DATABASE:
#    `script.fn_categoria_accesso` → OPERATORE / SISTEMA / ALTRO, un valore
#    solo per credenziale (brief-db-be-fe-area-accessi, R-DB-A1). Le liste di
#    questo modulo sono di OPERATORI: le credenziali delle macchine (utenti
#    tecnici dei processi automatici, API_CLIENT) stanno nel tab «Di sistema»,
#    le persone senza veste operatore — e le credenziali senza alcuna veste —
#    in «Altri accessi». ⭐ Una funzione che dà UN valore rende la partizione
#    vera per costruzione: nessuna credenziale in due tab, nessuna in nessuno.
#    Fino al 2026-10-02 la regola stava qui in due copie
#    (`SOLO_VESTE_OPERATORE` + `ESCLUDI_UTENTI_TECNICI`) e le altre due liste
#    non c'erano. Le vesti spente contano: un operatore disattivato resta qui.
#    `{au}` = l'espressione della credenziale nella query.
_CATEGORIA_OPERATORE = "script.fn_categoria_accesso({au}) = '" + CATEGORIA_ACCESSO_OPERATORE + "'"

# ⛔ LA VESTE OPERATORE di una credenziale, quella che si guarda e si comanda:
#    `script.fn_veste_di_riferimento(credenziale, 'OPERATORE')` — l'accesa,
#    altrimenti la spenta piu' recente. ⭐ Dal 2026-10-02 (R-DB-1) una veste
#    spenta TIENE il suo tipo, quindi un JOIN nudo su `ruolo_applicativo`
#    prenderebbe la spenta accanto all'accesa (due righe in lista, due vesti
#    accese da una riattivazione). E' la stessa regola che il DB usa in
#    `fn_get_operatore_detail`: una sede sola, la sua.
#    Dal riuso della credenziale (D-6, «una persona una credenziale», 2026-09)
#    una credenziale puo' avere ALTRE vesti — cliente del portale, dello shop —
#    e i comandi dell'operatore non le toccano.
#    `{au}` = l'espressione (o il segnaposto) della credenziale.
_VESTE_OPERATORE = "script.fn_veste_di_riferimento({au}, '" + RUOLO_APPLICATIVO_OPERATORE + "')"

# Le ALTRE vesti ATTIVE della credenziale (D-6: una persona, una credenziale):
# in lista sono un'informazione — «e' anche cliente dello shop» — non qualcosa
# da gestire da qui. Ordinate, per una resa stabile.
_COLONNA_ALTRE_VESTI = """ARRAY(SELECT av.ruolo_applicativo::text
                           FROM anagrafiche.identita_digitali av
                          WHERE av.auth_user_id = au.id
                            AND av.id <> id.id
                            AND av.attivo
                          ORDER BY 1) AS altre_vesti"""

# Whitelist ORDER BY lista operatori: chiave = `campo_sorgente` inviato dal
# frontend, valore = espressione SQL. Le chiavi che sono alias di output della
# SELECT restano nude (ORDER BY le risolve solo cosi'). Niente piu'
# "ruolo_sistema": il campo legacy non e' esposto. Per ordinare per stato
# amministrativo si usa `is_super_admin` o `ruolo_applicativo`.
#
# `valido_al` NULL = incarico senza scadenza, cioe' validita' INFINITA: va in
# testa in DESC, non in fondo. Senza il COALESCE finirebbe dal lato sbagliato
# (la SELECT casta a `::text`, quindi l'alias nudo ordinerebbe pure come
# stringa: qui si ordina la colonna vera).
ALLOWED_ORDER_COLUMNS: dict[str, str] = {
    "last_name": "last_name",
    "soggetto_cognome": "soggetto_cognome",
    "username": "username",
    "is_super_admin": "is_super_admin",
    "ruolo_applicativo": "ruolo_applicativo",
    "is_active": "is_active",
    "unita_organizzativa_nome": "unita_organizzativa_nome",
    "override_count": "override_count",
    "valido_dal": "ru.valido_dal",
    "valido_al": "COALESCE(ru.valido_al, 'infinity'::date)",
}


# Cosa si PUO' cercare nella lista operatori; cosa si cerca lo dice il catalogo
# (`add_ricerca_full_condition`). Mappa `campo_sorgente → espressione`: i nomi
# del catalogo sono nomi di USCITA della SELECT di `list_operatori`, e ogni
# valore e' la stessa espressione che la SELECT proietta con quel nome (si
# cerca su cio' che si mostra).
# ⭐ `soggetto_cognome`/`soggetto_nome` cercano il `COALESCE` col nome
#    dell'utente, come li mostra la lista: fino al 2026-09-24 la ricerca scritta
#    a mano cercava `s.cognome`/`s.nome` nudi, e un operatore senza soggetto non
#    si trovava per il nome che la lista gli mostrava.
# ⭐ `email`, `soggetto_nome` e `soggetto_ragione_sociale` sono colonne del
#    catalogo dal 2026-09-24 (brief DB §3.2-bis); la terza e' proiettata apposta.
_RICERCA_OPERATORI = RicercaFull(
    "anagrafiche.operatori",
    {
        "soggetto_cognome": "COALESCE(s.cognome, au.last_name)",
        "soggetto_nome": "COALESCE(s.nome, au.first_name)",
        "username": "au.username",
        "email": "au.email",
        "soggetto_ragione_sociale": "s.ragione_sociale_completa",
    },
)


# Whitelist ORDER BY della lista reparti (`amm.reparti`): chiave = `campo_sorgente`
# del catalogo, valore = colonna della CTE `reparti` di `list_reparti` (alias
# `rp`). I due conteggi sono alias della CTE, non colonne di tabella: e' per
# loro che la SELECT e' avvolta.
# `profilo_aree_count` a video e' «configurato / mancante», ma ordina il numero:
# i reparti senza profilo vengono insieme, in testa in ASC.
REPARTI_ORDER_COLUMNS: dict[str, str] = {
    "descrizione": "rp.descrizione",
    "codice": "rp.codice",
    "profilo_aree_count": "rp.profilo_aree_count",
    "operatori_count": "rp.operatori_count",
}

# Cosa si PUO' cercare nella lista reparti; cosa si cerca lo dice il catalogo
# (soglia 1: codici corti, `ricerca_min_caratteri` della lista). Espressioni su
# `uo`: la ricerca sta dentro la CTE, sulle colonne vere.
_RICERCA_REPARTI = RicercaFull("amm.reparti", {
    "descrizione": "uo.descrizione",
    "codice": "uo.codice",
})


# Whitelist ORDER BY del log di audit (`storico.audit_log`): chiave =
# `campo_sorgente` che il frontend invia come sortField (il nome del campo COME
# APPARE nel risultato), valore = colonna reale della CTE `events`. I due nomi
# divergono su tre colonne su quattro, ed e' l'unico posto del sistema dove
# succede.
#
# Era un `frozenset` confrontato DOPO una mappatura interna, e conteneva sia i
# nomi logici sia quelli SQL. `tabella` -> `code` non tornava (`code` non era
# nell'insieme): l'ordinamento per *Tabella* ripiegava in silenzio sul default,
# pur essendo `sortable` a video. Una mappa sola, letta una volta.
#
# Vive a livello MODULO come `ALLOWED_ORDER_COLUMNS` qui sopra (era attributo di
# classe): due whitelist con lo stesso ruolo e due forme diverse nello stesso
# file sono il modo in cui un presidio finisce per leggere il simbolo sbagliato
# — e su questa mappa era gia' successo.
# `dettaglio` non c'e' di proposito: nel seed e' `ordinabile=f` (colonna
# calcolata lato FE, senza `campo_sorgente`).
AUDIT_ORDER_COLUMNS: dict[str, str] = {
    "timestamp": "valid_from",
    "tabella": "code",
    "tipo_operazione": "tipo_operazione",
    "user_modifica": "user_insert",
}


class AmmSoftwareRepository:
    """Accesso DB per amministrazione operatori e reparti."""

    # Scopo: Restituisce la lista paginata degli operatori con filtri opzionali.
    # JOIN: auth_user + identita_digitali (OPERATORE) + soggetti_ruoli +
    # risorse_umane + unita_organizzative. Il modello identitario e' multi-face:
    # `is_super_admin` da `script.fn_is_super_admin`, `ruolo_applicativo` da
    # `identita_digitali`, `is_active` da `auth_user`. Niente piu' enum
    # legacy `config.ruolo_sistema` esposto in output (Fase 7).
    # Risultato: (lista righe, conteggio totale).
    def list_operatori(
        self,
        *,
        search: str | None = None,
        is_super_admin: bool | None = None,
        unita_organizzativa_id: int | None = None,
        is_active: bool | None = None,
        includi_di_prova: bool = False,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[OperatoreRow], int]:
        # ⛔ Un `order_by` fuori whitelist e' un 400 (`colonna_ordinamento`, qui
        #    sotto), non il default: fino al 2026-10-20 la colonna estranea
        #    ripiegava qui sull'ordine di default, in silenzio
        #    (brief-be-verifica-documentazione-api §A1).

        conditions: list[str] = [_CATEGORIA_OPERATORE.format(au="au.id")]
        params: list[Any] = []

        # ⚠️ Sotto la soglia della lista (catalogo) il termine non filtra: fino al
        #    2026-09-24 la ricerca scritta a mano filtrava da un carattere, senza
        #    `strip` ne' `escape_ilike`.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_OPERATORI)

        if is_super_admin is not None:
            # Multi-face auth: filtro binario sul binding SUPER_ADMIN.
            # Ortogonale a is_active. Delega a script.fn_is_super_admin.
            conditions.append("script.fn_is_super_admin(au.id) = %s")
            params.append(is_super_admin)

        if unita_organizzativa_id is not None:
            conditions.append("ru.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)

        if is_active is not None:
            conditions.append("au.is_active = %s")
            params.append(is_active)

        # Gli utenti di prova (etichetta del provisioning di sviluppo) restano
        # fuori, salvo chiederli: la lista degli operatori veri resta pulita
        # (Tid, 2026-10-16, brief-db-processi-accensione-per-ambiente R-4).
        # Il filtro sta qui, prima della paginazione e del conteggio.
        if not includi_di_prova:
            conditions.append("cp.auth_user_id IS NULL")

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Ordinamento sicuro (whitelist): la mappa traduce il campo inviato dal
        # client nell'espressione SQL, in un passaggio solo.
        order_column = colonna_ordinamento(order_by, ALLOWED_ORDER_COLUMNS)
        # ⛔ Direzione risolta PRIMA del ramo (2026-09-26): senza colonna il
        #    ramo di default la ignora, e un `order_dir` estraneo passava muto.
        #    Il BB la rifiuta anche quando poi non la si usa.
        direction = sql_order_direction_lista(order_by, order_dir, colonne=ALLOWED_ORDER_COLUMNS)
        if order_column:
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = f"ORDER BY {order_column} {direction}, au.id {tiebreak_dir}"
        else:
            order_clause = "ORDER BY soggetto_cognome ASC, au.username ASC, au.id"

        sql = f"""
            SELECT au.id AS auth_user_id,
                   au.username,
                   au.email,
                   au.first_name,
                   au.last_name,
                   COALESCE(s.cognome, au.last_name) AS soggetto_cognome,
                   COALESCE(s.nome, au.first_name) AS soggetto_nome,
                   s.ragione_sociale_completa AS soggetto_ragione_sociale,
                   script.fn_is_super_admin(au.id) AS is_super_admin,
                   id.ruolo_applicativo::text AS ruolo_applicativo,
                   -- Lo stato della VESTE operatore: dal 2026-10-02 (R-DB-1)
                   -- una veste spenta tiene il tipo, e «disabilitato» si legge
                   -- da qui, non dal ruolo. `is_active` e' della credenziale
                   -- (derivato da TUTTE le vesti): un operatore spento che e'
                   -- anche cliente dello shop resta `is_active`.
                   id.attivo AS veste_attiva,
                   au.is_active,
                   ru.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_nome,
                   ru.id AS risorsa_umana_id,
                   ru.attivo,
                   ru.valido_dal::text,
                   ru.valido_al::text,
                   {_COLONNA_ALTRE_VESTI},
                   (SELECT string_agg(s_ef.ragione_sociale_completa, ', '
                                      ORDER BY s_ef.ragione_sociale_completa)
                      FROM config.user_emittenti_fiscali uef
                      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
                      LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
                      LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
                     WHERE uef.auth_user_id = au.id
                   ) AS emittenti_descrizione,
                   -- Override dei permessi SCRITTI (D-2 del brief
                   -- riepilogo-permessi, validita' ignorata): dalla sede unica
                   -- `script.vw_override_operatore_area`, la stessa che legge
                   -- il riepilogo per area. Mai ricontati qui.
                   (SELECT count(*)::int
                      FROM script.vw_override_operatore_area vo
                     WHERE vo.auth_user_id = au.id) AS override_count,
                   (cp.auth_user_id IS NOT NULL) AS di_prova,
                   COUNT(*) OVER() AS total_count
              FROM auth_user au
              LEFT JOIN dbops.credenziali_di_prova cp
                ON cp.auth_user_id = au.id
              LEFT JOIN anagrafiche.identita_digitali id
                ON id.id = {_VESTE_OPERATORE.format(au="au.id")}
              LEFT JOIN anagrafiche.soggetti_ruoli sr
                ON sr.id = id.soggetto_ruolo_id
              LEFT JOIN anagrafiche.risorse_umane ru
                ON ru.soggetto_ruolo_id = sr.id
              LEFT JOIN anagrafiche.soggetti s
                ON s.id = sr.soggetto_id
              LEFT JOIN config.unita_organizzative uo
                ON uo.id = ru.unita_organizzativa_id
             WHERE {where_clause}
             {order_clause}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE da frammenti letterali + colonne _RICERCA_OPERATORI, ORDER BY da whitelist ALLOWED_ORDER_COLUMNS, valori come parametri
        # ⚠️ Il clamp sta nel repository, non nella view: un `?limit=-5`
        #    arrivava a DB come `LIMIT -5` e rispondeva 500.
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        params.extend([safe_limit, safe_offset])
        rows, total_count = fetch_paged_with_total(sql, params, offset=safe_offset)
        return cast(list[OperatoreRow], rows), total_count

    # Scopo: Restituisce il dettaglio completo di un operatore con conteggi
    # override e i 9 campi capability (can_invite/disable/demote + reason
    # + reason_key, §16).
    #
    # Delega interamente a `script.fn_get_operatore_detail(p_auth_user_id)`
    # (Fase 1 multi-face): la fn DB e' single source of truth per la
    # composizione del dettaglio. Lo SQL inline precedente e' eliminato per
    # evitare drift tra Python e regole DB.
    #
    # Semantica lookup-by-id: la fn ritorna 0 righe per id NULL/<=0/inesistenti
    # (idioma standard per i lookup; diverge dalla regola AGENTS "guard
    # NULL/<=0" volutamente — i chiamanti gestiscono `None` come "non
    # trovato"). I service consumer (`get_operatore`, `update_operatore`,
    # `disabilita_operatore`) trasformano None in
    # E_AMM_OPERATORE_NOT_FOUND quando rilevante.
    #
    # GUC awareness: la fn DB usa `script.fn_is_super_admin` che e' gated
    # su `app.ruolo_applicativo` (post 2026-04-21) e ritorna false per
    # contesti non-OPERATORE (portale/shop). Questo repo e' richiamato solo
    # da `AdminAPIView` (drawer admin-only), quindi il contesto e' sempre
    # OPERATORE. Se in futuro la fn fosse esposta altrove, la GUC va
    # garantita prima della chiamata.
    def get_operatore_detail(self, auth_user_id: int) -> OperatoreDetailRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM script.fn_get_operatore_detail(%s)",
                [auth_user_id],
            )
            if not cursor.description:
                return None
            return row_to_dict(cursor)  # type: ignore[return-value]

    # Scopo: La categoria di una credenziale — il tab dell'area Accessi —
    #        da `script.fn_categoria_accesso`: OPERATORE, SISTEMA o ALTRO.
    #        `None` se la credenziale non esiste (la funzione SQL risponde
    #        ALTRO anche per un id inesistente: l'esistenza la chiede la query).
    def get_categoria_accesso(self, auth_user_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_categoria_accesso(au.id) FROM auth_user au WHERE au.id = %s",
                [auth_user_id],
            )
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: L'id della VESTE OPERATORE della credenziale (`_VESTE_OPERATORE`:
    # l'accesa, altrimenti la spenta piu' recente), None se non ce n'e'.
    # Serve a chiudere le sessioni di QUELLA veste (D-5): il chiamante la
    # legge PRIMA di spegnerla, cosi' l'id e' quello della veste che spegne.
    def get_veste_operatore_id(self, auth_user_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_VESTE_OPERATORE.format(au='%s')}",
                [auth_user_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Aggiunge o rimuove il binding SUPER_ADMIN sull'identita
    # digitale dell'utente (la veste OPERATORE di `_VESTE_OPERATORE`; no-op se
    # l'utente non ne ha una). Il guard DB
    # `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` blocca
    # la rimozione dell'ultimo binding attivo (lockout prevention).
    # ⭐ Dal 2026-10-18 (2b-2, lotto 8) il legame lo scrive la madre del DB
    #    `config.fn_lega_profilo_identita`: idempotente sullo stesso profilo,
    #    e un ALTRO profilo gia' legato all'identita' lo rifiuta
    #    `uq_profili_accesso_bindings_identita`. Fino ad allora la INSERT era
    #    `ON CONFLICT DO NOTHING`: il SUPER_ADMIN chiesto non arrivava e
    #    nessuno lo diceva. Il rifiuto lo traduce il service.
    # ⭐ Dal 2026-10-19 (brief-db-processi-accensione-per-ambiente §6.15,
    #    §6.16) anche il profilo e lo slegare stanno nel DB: il profilo lo
    #    risolve il lettore `config.fn_profilo_super_admin_id` (per `tipo`,
    #    fra gli ATTIVI, esattamente uno, altrimenti `E_CONFIG_MANCANTE`
    #    «trovati N»: la stessa sede di `fn_crea_risorsa_umana_v2`), lo
    #    slegare la madre `config.fn_slega_profilo_identita`. Fino ad allora
    #    la regola del profilo era ricopiata qui e il DELETE toglieva i
    #    legami verso OGNI profilo di quel tipo, spenti compresi.
    def _set_super_admin_binding(
        self, auth_user_id: int, *, enabled: bool
    ) -> None:
        madre = (
            "config.fn_lega_profilo_identita" if enabled
            else "config.fn_slega_profilo_identita"
        )
        with connection.cursor() as cursor:
            # Il profilo prima della veste: una configurazione rotta si dice
            # anche a chi non ha una veste OPERATORE (nessuna veste = no-op).
            cursor.execute("SELECT config.fn_profilo_super_admin_id()")
            profilo_id = cursor.fetchone()[0]
            # La veste nella stessa istruzione del legame (niente
            # SELECT + WRITE).
            cursor.execute(
                "SELECT " + madre + """(%s::integer, v.id)
                     FROM (SELECT """ + _VESTE_OPERATORE.format(au="%s") + """ AS id) v
                    WHERE v.id IS NOT NULL""",  # noqa: S608 — nome della madre e predicato letterali del modulo, valori come parametri
                [profilo_id, auth_user_id],
            )

    # Scopo: Aggiorna i campi modificabili di un operatore (auth_user +
    # bindings SUPER_ADMIN + risorse_umane).
    # Dopo la modifica, il chiamante deve invalidare la cache permessi.
    # Transazione atomica: i 4-5 step devono succedere insieme o
    # nessuno (nessuno stato parziale inconsistente).
    #
    # Contract Fase 7 multi-face — solo campi nuovi:
    #   - `is_super_admin=True`  -> binding SUPER_ADMIN UPSERT (identita
    #                               OPERATORE attiva)
    #   - `is_super_admin=False` -> binding SUPER_ADMIN DELETE (identita
    #                               OPERATORE attiva)
    # ⛔ Niente `attivo` (2026-10-04): spegnere e' `disabilita_operatore`,
    #    che il service chiama anche dall'interruttore (Tid: «l'interruttore
    #    fa come Disabilita»); accendere e' dell'attivazione dell'invito (D-3).
    #    Fino a quel giorno l'interruttore spento scriveva qui una sua
    #    versione dello spegnimento, senza `valido_al = oggi`.
    def update_operatore(
        self,
        auth_user_id: int,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        is_super_admin: bool | None = None,
        unita_organizzativa_id: int | None = None,
        valido_al: date | str | MissingType | None = MISSING,
    ) -> None:
        with transaction.atomic():
            # 1) Aggiorna auth_user (name/email)
            auth_fields: list[str] = []
            auth_params: list[Any] = []
            if email is not None:
                auth_fields.append("email = %s")
                auth_params.append(email)
            if first_name is not None:
                auth_fields.append("first_name = %s")
                auth_params.append(first_name)
            if last_name is not None:
                auth_fields.append("last_name = %s")
                auth_params.append(last_name)

            if auth_fields:
                auth_params.append(auth_user_id)
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE auth_user SET {', '.join(auth_fields)} WHERE id = %s",  # noqa: S608 — SET da frammenti letterali di questo metodo, valori come parametri
                        auth_params,
                    )

            # 2) Binding SUPER_ADMIN.
            if is_super_admin is True:
                self._set_super_admin_binding(auth_user_id, enabled=True)
            elif is_super_admin is False:
                self._set_super_admin_binding(auth_user_id, enabled=False)

            # 3) Aggiorna la risorsa umana della VESTE OPERATORE (catena
            #    veste -> soggetto_ruolo): le altre vesti della credenziale
            #    hanno soggetti_ruoli loro, e non sono affari di questo comando.
            ru_fields: list[str] = []
            ru_params: list[Any] = []
            if unita_organizzativa_id is not None:
                ru_fields.append("unita_organizzativa_id = %s")
                ru_params.append(unita_organizzativa_id)
            # ⭐ `valido_al` ha TRE stati (brief-db-veste-utilizzabile §10):
            #    assente (MISSING) non tocca, una data la mette, `None` la
            #    TOGLIE (rapporto senza scadenza). Fino al 2026-10-07 `None`
            #    voleva dire «non toccare», e una data di fine messa non si
            #    poteva piu' togliere. Togliere passa sempre anche sull'ultimo
            #    SUPER_ADMIN: il guard ferma solo le scritture che riducono la
            #    garanzia.
            if valido_al is not MISSING:
                ru_fields.append("valido_al = %s::date")
                ru_params.append(valido_al)

            if ru_fields:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""UPDATE anagrafiche.risorse_umane ru
                               SET {', '.join(ru_fields)}
                              FROM anagrafiche.identita_digitali id
                             WHERE id.id = {_VESTE_OPERATORE.format(au="%s")}
                               AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id""",  # noqa: S608 — SET da frammenti letterali di questo metodo, predicato letterale del modulo, valori come parametri
                        ru_params + [auth_user_id],
                    )

            # 4) Sync auth_user.is_active se il binding e' cambiato
            if is_super_admin is not None:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                        [auth_user_id],
                    )

    # Scopo: Disabilita un operatore: la sede UNICA dello spegnimento, sia
    # da «Disabilita» sia dall'interruttore «Accesso attivo» (2026-10-04).
    # Post-cutover (§13.3.2) il framework
    # ATTIVO su risorse_umane valuta RUA.attivo come vista derivata da
    # identita_digitali.attivo, quindi l'ordine figlio→padre funziona
    # scrivendo su identita prima di RU. Transazione atomica per evitare
    # stato inconsistente se uno dei 3 step fallisce.
    def disabilita_operatore(self, auth_user_id: int) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            # 1. Spegne la veste operatore (figlio), non le altre: una
            #    credenziale puo' avere anche vesti di portale o shop (D-6).
            #    ⛔ Solo `attivo = false`, il tipo resta (R-DB-1, 2026-10-02):
            #    la tabella rifiuta `DISABILITATO` con
            #    `E_RUOLO_APPLICATIVO_RITIRATO`.
            cursor.execute(
                "UPDATE anagrafiche.identita_digitali SET attivo = false "  # noqa: S608 — predicato letterale del modulo (_VESTE_OPERATORE), valori come parametri
                f"WHERE id = {_VESTE_OPERATORE.format(au='%s')}",
                [auth_user_id],
            )
            # 2. Disattiva la risorsa umana di quella veste (padre) +
            #    valido_al = oggi
            cursor.execute(
                f"""UPDATE anagrafiche.risorse_umane ru
                      SET attivo = false,
                          valido_al = (SELECT script.fn_data_operativa())
                     FROM anagrafiche.identita_digitali id
                    WHERE id.id = {_VESTE_OPERATORE.format(au="%s")}
                      AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id""",  # noqa: S608 — predicato letterale del modulo (_VESTE_OPERATORE), valori come parametri
                [auth_user_id],
            )
            # 3. Sync auth_user.is_active
            cursor.execute(
                "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                [auth_user_id],
            )

    # Scopo: Crea un operatore invocando la madre DB
    # `anagrafiche.fn_crea_operatore_v2` (rev P-2, 20260925-42). Due flussi sul
    # soggetto: soggetto_id NULL (crea il soggetto PF) o valorizzato (usa
    # l'esistente). Due flussi sulla CREDENZIALE, decisi dal DB per email
    # senza maiuscole (D-6: una persona, una credenziale):
    #   - nuova: nasce con `password_hash` e `username`;
    #   - RIUSATA: password, username e nome restano i suoi, e quelli passati
    #     sono ignorati — il ritorno dice quale username vale davvero.
    # ⛔ La veste OPERATORE nasce SEMPRE spenta: la accende l'attivazione
    # dell'invito. Credenziale gia' operatore (veste attiva o spenta) →
    # `E_CREDENZIALE_GIA_OPERATORE` dal DB.
    # ⭐ Il riuso non e' silenzioso (`20260925-51`): `riusa_auth_user_id` e'
    # la DICHIARAZIONE della credenziale che l'admin ha visto e confermato.
    # Senza, o con un'altra, la madre ferma con `E_CREDENZIALE_DA_CONFERMARE`;
    # su un'altra persona fisica con `E_CREDENZIALE_ALTRA_PERSONA`.
    # Ritorna {auth_user_id, username, credenziale_riusata}.
    def crea_operatore(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        qualifica_id: int,
        soggetto_id: str | None = None,
        cognome: str | None = None,
        nome: str | None = None,
        codice_fiscale: str | None = None,
        unita_organizzativa_id: int | None = None,
        data_nascita: str | None = None,
        # None solo col soggetto esistente: per il nuovo lo pretende il service.
        sesso: str | None = None,
        is_super_admin: bool = False,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        comune_nascita_id: int | None = None,
        indirizzo_resid_dettaglio_id: int | None = None,
        indirizzo_domfisc_dettaglio_id: int | None = None,
        riusa_auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            SELECT auth_user_id, username, credenziale_riusata
              FROM anagrafiche.fn_crea_operatore_v2(
                p_soggetto_id                    := %s::uuid,
                p_cognome                        := %s,
                p_nome                           := %s,
                p_codice_fiscale                 := %s,
                p_username                       := %s,
                p_email                          := %s,
                p_password_hash                  := %s,
                p_qualifica_id                   := %s,
                p_unita_organizzativa_id         := %s,
                p_data_nascita                   := %s::date,
                p_sesso                          := %s,
                p_is_super_admin                 := %s,
                p_valido_dal                     := COALESCE(%s::date, (SELECT script.fn_data_operativa())),
                p_valido_al                      := %s::date,
                p_comune_nascita_id              := %s,
                p_indirizzo_resid_dettaglio_id   := %s,
                p_indirizzo_domfisc_dettaglio_id := %s,
                p_riusa_auth_user_id             := %s
            )
        """
        params = [
            soggetto_id,
            cognome, nome, codice_fiscale,
            username, email, password_hash,
            qualifica_id, unita_organizzativa_id,
            data_nascita, sesso, is_super_admin,
            valido_dal, valido_al,
            comune_nascita_id,
            indirizzo_resid_dettaglio_id,
            indirizzo_domfisc_dettaglio_id,
            riusa_auth_user_id,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return {
                "auth_user_id": int(row[0]),
                "username": row[1],
                "credenziale_riusata": bool(row[2]),
            }

    # Scopo: La credenziale che porta un'email, con username e vesti, per il
    #        dialog di conferma del riuso (B-20). Sede unica della lettura:
    #        `script.fn_get_credenziale_per_email`, la stessa che la madre usa
    #        per il rifiuto E_CREDENZIALE_DA_CONFERMARE. Email assente, vuota o
    #        di nessuno -> None (zero righe: lo decide il DB, non qui); due
    #        credenziali con la stessa email -> E_CREDENZIALE_EMAIL_AMBIGUA
    #        dal DB. `vesti` e' jsonb: fuori dall'ORM arriva `str`, lo decodifica
    #        `jsonb_out` (BB, esplode su un JSON malformato).
    def get_credenziale_per_email(self, email: str | None) -> CredenzialePerEmailRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT auth_user_id, username, vesti"
                "  FROM script.fn_get_credenziale_per_email(%s)",
                [email],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {"auth_user_id": int(row[0]), "username": row[1], "vesti": jsonb_out(row[2])}

    # Scopo: Lista unita' organizzative per dropdown filtro.
    def list_unita_organizzative(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, descrizione, parent_id
                     FROM config.unita_organizzative
                    ORDER BY descrizione"""
            )
            return rows_to_list(cursor)

    # ================================================================== #
    # Override aree per operatore                                           #
    # ================================================================== #

    # Scopo: Restituisce gli override aree per un operatore con nome area.
    def get_override_aree(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoa.id, uoa.area_id, af.codice AS area_codice,
                   af.descrizione AS area_descrizione,
                   uoa.livello::text, uoa.motivo,
                   uoa.valido_dal::text, uoa.valido_al::text
              FROM config.user_override_aree uoa
              JOIN config.aree_funzionali af ON af.id = uoa.area_id
             WHERE uoa.auth_user_id = %s
             ORDER BY af.ordinamento, af.codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override aree di un operatore (replace semantics).
    # Cancella tutti gli override esistenti e inserisce i nuovi.
    def put_override_aree(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_override_aree WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for item in items:
                cursor.execute(
                    """INSERT INTO config.user_override_aree
                       (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
                       VALUES (%s, %s, %s::config.livello_accesso, %s, %s::date, %s::date)""",
                    [
                        auth_user_id,
                        item["area_id"],
                        item["livello"],
                        item.get("motivo"),
                        item.get("valido_dal"),
                        item.get("valido_al"),
                    ],
                )

    # ================================================================== #
    # Override azioni per operatore                                         #
    # ================================================================== #

    # Scopo: Restituisce gli override azioni per un operatore con descrizione azione.
    def get_override_azioni(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoz.id, uoz.azione_id, ap.permission_codename,
                   ap.descrizione AS azione_descrizione,
                   af.codice AS area_codice,
                   uoz.abilitata, uoz.motivo,
                   uoz.valido_dal::text, uoz.valido_al::text
              FROM config.user_override_azioni uoz
              JOIN config.azioni_processo ap ON ap.id = uoz.azione_id
              JOIN config.aree_funzionali af ON af.id = ap.area_id
             WHERE uoz.auth_user_id = %s
             ORDER BY af.ordinamento, ap.permission_codename
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override azioni di un operatore (replace semantics).
    def put_override_azioni(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_override_azioni WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for item in items:
                cursor.execute(
                    """INSERT INTO config.user_override_azioni
                       (auth_user_id, azione_id, abilitata, motivo, valido_dal, valido_al)
                       VALUES (%s, %s, %s, %s, %s::date, %s::date)""",
                    [
                        auth_user_id,
                        item["azione_id"],
                        item["abilitata"],
                        item.get("motivo"),
                        item.get("valido_dal"),
                        item.get("valido_al"),
                    ],
                )

    # ================================================================== #
    # Override oggetti per operatore (v2 permessi)                         #
    # ================================================================== #

    # Scopo: Restituisce gli override oggetto di un operatore con info model e area.
    def get_override_oggetti(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoo.id, uoo.app_label, uoo.model_name,
                   uoo.livello::text,
                   uoo.motivo,
                   uoo.valido_dal::text, uoo.valido_al::text,
                   amo.area_id,
                   af.descrizione AS area_descrizione
              FROM config.user_override_oggetti uoo
              LEFT JOIN config.area_model_overrides amo
                ON amo.app_label = uoo.app_label AND amo.model_name = uoo.model_name
              LEFT JOIN config.aree_funzionali af ON af.id = amo.area_id
             WHERE uoo.auth_user_id = %s
             ORDER BY af.descrizione, uoo.app_label, uoo.model_name
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override oggetto di un operatore (replace semantics)
    #        con la madre del DB `config.fn_imposta_override_oggetti`
    #        (2026-10-18, 2b-2, lotto 9).
    # ⚠️ Le sei chiavi viaggiano SEMPRE, anche a null: per la madre una chiave
    #    assente prende il DEFAULT (`valido_dal` = la data operativa), una a null
    #    scrive NULL. Il significato di prima e' «null = senza inizio».
    def put_override_oggetti(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        oggetti = [
            {
                "app_label": item["app_label"],
                "model_name": item["model_name"],
                "livello": item["livello"],
                "motivo": item.get("motivo"),
                "valido_dal": item.get("valido_dal"),
                "valido_al": item.get("valido_al"),
            }
            for item in items
        ]
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT config.fn_imposta_override_oggetti(%s::integer, %s::jsonb)",
                [auth_user_id, json.dumps(oggetti, default=str)],
            )

    # Scopo: Lista model registrati in area_model_overrides (lookup per dropdown admin).
    #        Ogni riga e' arricchita con capability `can_override` (bool) +
    #        `reason` (chiave i18n|None) — Fase 8: i model che afferiscono al
    #        kernel del sistema permessi (identita, profili, bindings, override
    #        stessi) NON possono essere target di override per evitare lockout
    #        ricorsivi. Pattern simmetrico a `can_change_scope`/`change_scope_reason`
    #        di Fase 2.
    # ⭐ Il riservato e' la colonna `area_model_overrides.riservato` (D-4 di
    #    brief-db-be-fe-catalogo-oggetti-permessi, `20260928-01`): il catalogo
    #    DICHIARA i dieci oggetti del kernel, e la FK composita
    #    `fk_user_override_oggetti_catalogo` rifiuta un override su un oggetto
    #    fuori catalogo o riservato.
    # ⛔ Fino al 2026-09-28 l'elenco era la costante Python
    #    `_MODEL_OVERRIDE_RISERVATI`, preventiva e senza riscontro a DB: due
    #    elenchi dei riservati, ritirata la copia (regola del 2).
    def list_model_overrides(self) -> list[dict[str, Any]]:
        sql = """
            SELECT amo.id, amo.app_label, amo.model_name, amo.riservato,
                   af.id AS area_id,
                   af.schema_db AS area_schema, af.descrizione AS area_descrizione
              FROM config.area_model_overrides amo
              JOIN config.aree_funzionali af ON af.id = amo.area_id
             ORDER BY af.descrizione, amo.app_label, amo.model_name
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = rows_to_list(cursor)

        for row in rows:
            riservato = bool(row.pop("riservato"))
            row["can_override"] = not riservato
            row["reason"] = "amm.model_override_reason_riservato" if riservato else None
        return rows

    # ================================================================== #
    # Emittenti scope per operatore (Fase 2 multi-face)                     #
    # ================================================================== #

    # Scopo: Restituisce lo scope emittenti dichiarativo dell'operatore via
    # `script.fn_get_user_emittenti_scope`. La fn DB e' single source of truth
    # per:
    #   - scope_mode ('GLOBAL'|'SINGLE') derivato dal numero di righe in
    #     config.user_emittenti_fiscali (post Q2: max 1 riga per UNIQUE)
    #   - emittente_id + emittente_descrizione (NULL se GLOBAL)
    #   - allowed_scope_modes (sempre ['GLOBAL','SINGLE'] post Q2; MULTI
    #     architetturalmente chiuso)
    #   - can_change_scope: false sse l'operatore e' SA e l'unico attivo
    #     (delega a fn_check_ultimo_super_admin_attivo di Fase 1)
    #   - change_scope_reason: testo it-IT free-form, NULL se can=true
    #
    # Idioma lookup-by-id: 0 righe per p_auth_user_id non valido (None lato
    # Python), coerente con fn_get_operatore_detail. Il chiamante service
    # gestisce None come E_AMM_OPERATORE_NOT_FOUND quando rilevante.
    def get_user_emittenti_scope(self, auth_user_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM script.fn_get_user_emittenti_scope(%s)",
                [auth_user_id],
            )
            if not cursor.description:
                return None
            return row_to_dict(cursor)

    # Scopo: Cambio scope emittenti atomico via
    # `script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)`.
    # La fn DB esegue in transazione:
    #   1. Validazione array_length IN (NULL|0|1) — altrimenti RAISE con
    #      marker E_AMM_VALIDAZIONE / E_AMM_SCOPE_NON_AMMESSO (no MULTI).
    #   2. Guard `fn_check_ultimo_super_admin_attivo` se SA -> RAISE
    #      E_PROFILO_ULTIMO_SUPER_ADMIN (riuso Fase 1).
    #   3. DELETE + INSERT condizionale.
    # Ritorna jsonb con lo stato post-change. Per il consumer Python ci
    # interessa solo l'esito (errori sollevati come DatabaseError gestiti
    # dal service); il return jsonb non viene proiettato perche' il service
    # rilegge tramite get_user_emittenti_scope per consistenza con il GET.
    def change_user_emittenti_scope(
        self, auth_user_id: int, emittente_ids: list[int]
    ) -> None:
        with connection.cursor() as cursor:
            # GLOBAL = array vuoto []; SINGLE = [id]. La fn DB Q2 valida
            # array_length <= 1 e solleva E_AMM_SCOPE_NON_AMMESSO altrimenti.
            cursor.execute(
                "SELECT script.fn_change_user_emittenti_scope(%s, %s::bigint[])",
                [auth_user_id, list(emittente_ids)],
            )

    # ================================================================== #
    # Reparti e profili                                                    #
    # ================================================================== #

    # Scopo: Lista reparti (`amm.reparti`, lista 87) con flag profilo
    #        configurato e conteggio operatori: paginata, ordinata sulla
    #        whitelist `REPARTI_ORDER_COLUMNS`, con la ricerca libera del
    #        catalogo. Ritorna (righe della pagina, totale).
    #        Conteggi su modello generalizzato profili_accesso_* via binding
    #        REPARTO (post-cutover PR-B): JOIN profili_accesso_bindings ->
    #        profili_accesso_aree/_azioni filtrato per unita_organizzativa_id.
    # ⭐ La SELECT sta in una CTE perche' due colonne ordinabili sono CONTEGGI
    #    (sottoquery col loro alias): fuori dalla CTE si ordinano per nome come
    #    le altre, e il `COUNT(*) OVER ()` si conta sulle righe gia' filtrate.
    #    La ricerca invece resta DENTRO, sulle colonne vere di `uo`.
    # ⚠️ Solo i reparti ATTIVI (`uo.attivo = true`), come prima della
    #    paginazione: se servano anche i disattivati e' una domanda aperta
    #    (brief-db-liste-datatable-grezze §8 punto 5), non una scelta di qui.
    def list_reparti(
        self, *, search: str | None = None,
        order_by: str | None = "descrizione", order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=REPARTI_ORDER_COLUMNS, default="rp.descrizione", tiebreak="rp.id",
        )
        conditions: list[str] = ["uo.attivo = true"]
        params: list[Any] = []
        add_ricerca_full_condition(conditions, params, search, _RICERCA_REPARTI)
        where_clause = "WHERE " + " AND ".join(conditions)
        return fetch_paged_with_total(
            f"""
            WITH reparti AS (
                SELECT uo.id, uo.codice, uo.descrizione, uo.attivo,
                       (SELECT COUNT(*)
                          FROM config.profili_accesso_bindings pab
                          JOIN config.profili_accesso_aree paa
                            ON paa.profilo_accesso_id = pab.profilo_accesso_id
                         WHERE pab.unita_organizzativa_id = uo.id) AS profilo_aree_count,
                       (SELECT COUNT(*)
                          FROM config.profili_accesso_bindings pab
                          JOIN config.profili_accesso_azioni paz
                            ON paz.profilo_accesso_id = pab.profilo_accesso_id
                         WHERE pab.unita_organizzativa_id = uo.id) AS profilo_azioni_count,
                       (SELECT COUNT(*) FROM anagrafiche.risorse_umane ru
                         WHERE ru.unita_organizzativa_id = uo.id
                           AND ru.attivo = true) AS operatori_count
                  FROM config.unita_organizzative uo
                 {where_clause}
            )
            SELECT rp.*, COUNT(*) OVER () AS total_count
              FROM reparti rp
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
            """,  # noqa: S608 — WHERE da condizioni letterali + add_ricerca_full_condition (_RICERCA_REPARTI), ORDER BY da sql_order_clause su REPARTI_ORDER_COLUMNS, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) FROM config.unita_organizzative uo {where_clause}",  # noqa: S608 — stesso FROM/WHERE della CTE, condizioni letterali e valori come parametri
            fallback_params=params,
            offset=safe_offset,
        )

    # Scopo: Restituisce il profilo completo di un reparto (aree + azioni).
    #        Legge dal modello generalizzato profili_accesso_* via binding
    #        REPARTO. Contratto API invariato: {"aree": [...], "azioni": [...]}
    def get_profilo_reparto(self, uo_id: int) -> dict[str, Any]:
        # Aree
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT paa.id, paa.area_id, af.codice AS area_codice,
                          af.descrizione AS area_descrizione,
                          paa.livello::text
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso_aree paa
                       ON paa.profilo_accesso_id = pab.profilo_accesso_id
                     JOIN config.aree_funzionali af ON af.id = paa.area_id
                    WHERE pab.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, af.codice""",
                [uo_id],
            )
            aree = rows_to_list(cursor)

        # Azioni
        # ⭐ `limitata_da_area` (2026-10-31, decisione Tid «sola regola DB»):
        #    l'azione e' abilitata nel profilo ma la SUA area, nello stesso
        #    profilo, non arriva al `livello_minimo_area` dell'azione. La regola
        #    e' quella del DB, `script.fn_area_consente_azione` (sede unica, la
        #    leggono i resolver): qui la si chiama, non la si riscrive. L'editor
        #    del profilo la mostra sui valori SALVATI; la copia di `tettoArea.js`
        #    resta per la sola anteprima di cio' che l'admin sta cambiando.
        #    ⚠️ LEFT JOIN: un'area senza riga nel profilo arriva NULL, e la
        #    funzione su NULL dice «no» (fail-closed) — un'azione abilitata in
        #    un'area non configurata e' limitata, come per i resolver.
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT paz.id, paz.azione_id, ap.permission_codename,
                          ap.descrizione AS azione_descrizione,
                          af.codice AS area_codice,
                          paz.abilitata,
                          (paz.abilitata AND NOT script.fn_area_consente_azione(
                               paa.livello, ap.livello_minimo_area)) AS limitata_da_area
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso_azioni paz
                       ON paz.profilo_accesso_id = pab.profilo_accesso_id
                     JOIN config.azioni_processo ap ON ap.id = paz.azione_id
                     JOIN config.aree_funzionali af ON af.id = ap.area_id
                     LEFT JOIN config.profili_accesso_aree paa
                       ON paa.profilo_accesso_id = pab.profilo_accesso_id
                      AND paa.area_id = ap.area_id
                    WHERE pab.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, ap.permission_codename""",
                [uo_id],
            )
            azioni = rows_to_list(cursor)

        # Il segno del secondo fattore sul profilo (D-T1 del brief DB TOTP):
        # chi riceve il profilo deve usare il secondo fattore. Nessun profilo
        # ancora per il reparto = false, come il default della colonna.
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT pa.richiede_secondo_fattore
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
                    WHERE pab.unita_organizzativa_id = %s""",
                [uo_id],
            )
            riga = cursor.fetchone()

        return {
            "aree": aree,
            "azioni": azioni,
            "richiede_secondo_fattore": bool(riga[0]) if riga else False,
        }

    # Scopo: I livelli che un operatore EREDITA dal profilo, per area e per
    #        azione — cioe' cosa avrebbe senza nessun override individuale.
    #        Alimenta la colonna «ereditato» del pannello permessi: senza,
    #        l'admin riscrive override che ripetono il profilo, e un override
    #        che ripete il profilo CONGELA la riga (da quel momento non segue
    #        piu' il reparto se il reparto cambia).
    #
    # ⭐ L'ereditato e' calcolato a DB, da `script.fn_get_permessi_ereditati_aree`
    #    e `..._azioni`: sono la SEDE UNICA del passo 4 dei resolver
    #    (`fn_resolve_livello_area`, `fn_check_azione_processo` e le due mappe
    #    le CHIAMANO), quindi la colonna coincide col valore applicato per
    #    costruzione. Qui non si riscrive ne' la raccolta dei profili ne' lo
    #    spareggio: lo presidia il pgTAP `test-fn-get-permessi-ereditati-v1`
    #    (brief-db-pgtap-permessi-ereditati §7).
    # ⛔ NON e' `get_profilo_reparto`, che legge il solo binding REPARTO per
    #    `unita_organizzativa_id`: i profili sono TRE (AD_HOC, REPARTO,
    #    PORTALE di veste) e per un utente con un binding AD_HOC quella lettura
    #    darebbe un valore PLAUSIBILE E SBAGLIATO, su una schermata di sicurezza.
    #
    # Qui si aggiunge solo presentazione: le etichette del catalogo (JOIN su
    # `aree_funzionali` / `azioni_processo`). `profilo_nome` e' il nome di
    # contratto dell'endpoint per `profilo_descrizione`.
    #
    # ℹ️ Nessuna chiave `oggetti`: `config.profili_accesso_oggetti` non esiste.
    #    Per un model l'ereditato e' il livello della sua AREA, che il chiamante
    #    ha gia' da `aree` — restituirlo qui sarebbe una seconda risposta alla
    #    stessa domanda, con due posti in cui sbagliarla.
    # ℹ️ Voce ASSENTE = nessun profilo copre quell'area/azione ⇒ vale il default
    #    (`BLOCCATO` / azione negata). La lista vuota e' un dato, non un buco.
    def get_permessi_ereditati(self, auth_user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT e.area_id,
                          af.codice               AS area_codice,
                          af.descrizione          AS area_descrizione,
                          e.livello::text         AS livello,
                          e.profilo_descrizione   AS profilo_nome,
                          e.profilo_tipo::text    AS profilo_tipo
                     FROM script.fn_get_permessi_ereditati_aree(%s) e
                     JOIN config.aree_funzionali af
                       ON af.id = e.area_id
                    ORDER BY e.area_id""",
                [auth_user_id],
            )
            aree = rows_to_list(cursor)

        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT e.azione_id,
                          ap.permission_codename,
                          ap.descrizione          AS azione_descrizione,
                          af.codice               AS area_codice,
                          e.abilitata,
                          e.profilo_descrizione   AS profilo_nome,
                          e.profilo_tipo::text    AS profilo_tipo
                     FROM script.fn_get_permessi_ereditati_azioni(%s) e
                     JOIN config.azioni_processo ap
                       ON ap.id = e.azione_id
                     JOIN config.aree_funzionali af
                       ON af.id = ap.area_id
                    ORDER BY e.azione_id""",
                [auth_user_id],
            )
            azioni = rows_to_list(cursor)

        return {"aree": aree, "azioni": azioni}

    # Scopo: I permessi EFFETTIVI di un operatore su azioni e oggetti, col
    #        tetto d'area (brief-db-permessi-tetto-area): per ogni voce il
    #        valore senza tetto, quello applicato e se l'area lo ferma.
    #        Alimenta l'etichetta «limitata dall'area» del pannello permessi:
    #        senza, il pannello mostrerebbe un override «abilitata» che non
    #        vale niente.
    #
    # ⭐ La catena sta a DB, in `script.fn_get_permessi_effettivi_azioni` e
    #    `..._oggetti`: sono la SEDE UNICA che leggono anche i resolver
    #    (`fn_check_azione_processo`, `fn_resolve_livello_oggetto`) e le mappe
    #    di `/me/`. Qui non si confrontano livelli e non si applica il tetto:
    #    si aggiungono solo le etichette del catalogo.
    # ⚠️ L'enum `livello_accesso` e' ordinato TUTTO < LETTURA < BLOCCATO: chi
    #    volesse confrontare livelli in Python sbaglierebbe il verso. Non serve:
    #    `limitata_da_area` / `limitato_da_area` arrivano gia' calcolati.
    # ℹ️ Niente chiave `aree`: il livello effettivo di un'area e' l'override o
    #    l'ereditato, che il pannello ha gia' (override + `permessi-ereditati`).
    #    Le azioni si limitano alle ATTIVE, come il catalogo del pannello; gli
    #    oggetti sono tutto `config.area_model_overrides`, riservati compresi.
    def get_permessi_effettivi(self, auth_user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT e.azione_id,
                          e.permission_codename,
                          e.area_id,
                          e.abilitata_specifica,
                          e.livello_area::text        AS livello_area,
                          e.livello_minimo_area::text AS livello_minimo_area,
                          e.abilitata,
                          e.limitata_da_area
                     FROM script.fn_get_permessi_effettivi_azioni(%s) e
                    WHERE e.attivo
                    ORDER BY e.azione_id""",
                [auth_user_id],
            )
            azioni = rows_to_list(cursor)

        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT e.app_label,
                          e.model_name,
                          e.area_schema_db,
                          e.livello_override::text  AS livello_override,
                          e.livello_area::text      AS livello_area,
                          e.livello_specifico::text AS livello_specifico,
                          e.livello::text           AS livello,
                          e.limitato_da_area
                     FROM script.fn_get_permessi_effettivi_oggetti(%s) e
                    ORDER BY e.app_label, e.model_name""",
                [auth_user_id],
            )
            oggetti = rows_to_list(cursor)

        return {"azioni": azioni, "oggetti": oggetti}

    # Scopo: Sostituisce il profilo completo di un reparto (aree + azioni).
    #        Operazione atomica:
    #          1. il reparto (codice del profilo = 'REPARTO_' || codice_interno);
    #          2. il profilo REPARTO con aree e azioni sostituite, dalla madre
    #             `config.fn_scrivi_profilo_accesso`;
    #          3. il legame REPARTO -> profilo per uo_id, dalla madre
    #             `config.fn_lega_profilo_reparto`.
    #        Il fail-fast su uo_id inesistente solleva E_AMM_VALIDAZIONE prima
    #        di toccare qualunque tabella. Tutti gli operatori bindati al
    #        reparto ereditano le modifiche; la cache permessi e' invalidata
    #        dal service caller (`invalidate_department`).
    #        `richiede_secondo_fattore` None = lascia il valore che c'e' (un
    #        profilo nuovo nasce con false, il default della colonna).
    def put_profilo_reparto(
        self, uo_id: int, aree: list[dict[str, Any]], azioni: list[dict[str, Any]],
        *, richiede_secondo_fattore: bool | None = None,
    ) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            # 1. Recupera codice/descrizione UO per derivare codice profilo.
            cursor.execute(
                "SELECT codice_interno, descrizione, attivo "
                "FROM config.unita_organizzative WHERE id = %s",
                [uo_id],
            )
            row = cursor.fetchone()
            if not row:
                ErrorManager.raise_error(
                    code="E_AMM_VALIDAZIONE",
                    message="Reparto inesistente.",
                    detail=f"unita_organizzativa_id={uo_id}",
                )
            codice_interno, descrizione_uo, attivo_uo = row
            codice_profilo = f"REPARTO_{codice_interno}"

            # 2. Il profilo (tipo REPARTO), creato o aggiornato per codice, con
            #    aree e azioni sostituite: la madre del DB
            #    `config.fn_scrivi_profilo_accesso` (2026-10-18, 2b-2, lotto 8).
            #    `attivo` segue il reparto; `richiede_secondo_fattore` assente =
            #    invariato (nuovo: false).
            campi: dict[str, Any] = {"attivo": attivo_uo}
            if richiede_secondo_fattore is not None:
                campi["richiede_secondo_fattore"] = richiede_secondo_fattore
            cursor.execute(
                """SELECT config.fn_scrivi_profilo_accesso(
                          'REPARTO'::config.tipo_profilo_accesso, %s, %s,
                          %s::jsonb, %s::jsonb, %s::jsonb)""",
                [
                    codice_profilo, f"Profilo reparto {descrizione_uo}",
                    json.dumps([{"area_id": a["area_id"], "livello": a["livello"]} for a in aree]),
                    json.dumps([{"azione_id": a["azione_id"], "abilitata": a["abilitata"]} for a in azioni]),
                    json.dumps(campi),
                ],
            )
            profilo_id = cursor.fetchone()[0]

            # 3. Il legame REPARTO -> profilo, dalla madre del DB
            #    `config.fn_lega_profilo_reparto` (2026-10-19, R-DB-16a):
            #    idempotente sullo stesso profilo. Un ALTRO profilo gia' legato
            #    al reparto lo rifiuta `uq_profili_accesso_bindings_uo` invece
            #    di sostituirlo, come faceva l'UPSERT di prima: da qui non
            #    capita, il codice del profilo deriva dal `codice_interno` del
            #    reparto (passo 1), che non cambia
            #    (`trg_unita_organizzative_a10_lock_columns_upd`).
            cursor.execute(
                "SELECT config.fn_lega_profilo_reparto(%s, %s)",
                [profilo_id, uo_id],
            )

    # ================================================================== #
    # Audit log globale permessi                                           #
    # ================================================================== #

    _OP_LABELS: dict[int, str] = {1: "INIZIALE", 2: "MODIFICA", 3: "ELIMINAZIONE"}

    # Scopo: Restituisce le sorgenti audit ammesse (Fase 5).
    #        Single source of truth lato DB: `script.vw_audit_sources` gia'
    #        filtrata `attivo=true` e ordinata per `code`. Sostituisce l'ex
    #        `_AUDIT_TABLES` hardcoded. La vista include 8 sorgenti (incluse
    #        `user_override_oggetti` permessi v2 e `identita_digitali`
    #        multi-face). Cardinalita' bassa, no paginazione.
    #
    #        Cache modulo-level via `lru_cache`: la vista cambia solo con
    #        migration (no mutazioni runtime), 8 righe immutabili durante
    #        il processo. Evita 2 round-trip DB per ogni `get_audit_summary`
    #        (validazione code + fn call). Test/hot-reload: `cache_clear()`.
    # ⭐ `storico_table` SI LEGGE DAL 2026-09-02 (changeSet `20260902-11`), ed e'
    #    la meta' che mancava: e' il NOME FISICO della storico, l'unica sede
    #    autorevole. Prima la vista non lo esponeva affatto e il nome si
    #    ricostruiva da `code` — vedi la nota su `list_audit_log`.
    # ⚠️ Quarta colonna e IN CODA, non in mezzo: la vista e' un
    #    `CREATE OR REPLACE` (per non perdere i GRANT), e quella forma puo' solo
    #    aggiungere colonne alla fine. Qui si seleziona per NOME, quindi la
    #    posizione non ci riguarda — ma sapere perche' e' li' evita di
    #    «riordinarla» un giorno.
    @staticmethod
    @lru_cache(maxsize=1)
    def _list_audit_sources_cached() -> tuple[tuple[str, str, str, str], ...]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT code, label_key, area_funzionale, storico_table
                  FROM script.vw_audit_sources
                """
            )
            return tuple((r[0], r[1], r[2], r[3]) for r in cursor.fetchall())

    # ⛔ `storico_table` NON entra in questo payload, ed e' voluto: questo e' il
    #    contratto API della tendina del drawer (`/amm-software/audit-sources/`)
    #    e l'insieme dei codici ammessi per `get_audit_summary`. Il nome fisico
    #    di una tabella non e' un dato che il frontend debba conoscere — e il
    #    changeSet `20260429-06` lo dichiarava «tecnico» proprio in questo senso.
    #    Chi dentro il repository ne ha bisogno legge il cache direttamente.
    def list_audit_sources(self) -> list[dict[str, Any]]:
        return [
            {"code": code, "label_key": label_key, "area_funzionale": area}
            for code, label_key, area, _storico_table in self._list_audit_sources_cached()
        ]

    # Scopo: Calcola summary + diff per uno snapshot audit (Fase 5).
    #        Wrapper su `script.fn_audit_summary(p_audit_source_code, p_storico_id)`.
    #        Ritorna dict {"summary": "<N> modifiche", "diff": [{field, old, new}]}.
    #        Convenzione "snapshot mancante -> None": il fn DB solleva
    #        `E_AUDIT_SNAPSHOT_NON_TROVATO` come marker stabile; il repo lo
    #        traduce in None per coerenza con il pattern lookup-by-id (idiom
    #        `feedback_db_doc_first`). Il service mappa None ->
    #        ServiceError(E_AUDIT_SNAPSHOT_NON_TROVATO) preservando il code.
    #        Altri DatabaseError sono ri-sollevati (gestiti dal middleware).
    def get_audit_summary(self, code: str, storico_id: int) -> dict[str, Any] | None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_audit_summary(%s, %s) AS audit",
                    [code, storico_id],
                )
                row = cursor.fetchone()
        except DatabaseError as exc:
            if "E_AUDIT_SNAPSHOT_NON_TROVATO" in str(exc):
                return None
            raise
        if not row or row[0] is None:
            return None
        # Il driver Postgres ritorna jsonb come dict Python.
        return row[0]

    # Defensive: i `code` e `area_funzionale` arrivano da `script.vw_audit_sources`
    # (whitelist DB) ma vengono interpolati in f-string nella query
    # (`storico.{code}`, `fn_audit_summary('{code}', ...)`,
    # `'{area}' AS area_funzionale`). Se in futuro la vista esponesse valori
    # con caratteri inattesi (improbabile, ma mitigation lowcost), l'iniezione
    # SQL diventerebbe possibile. Le regex riflettono la convenzione naming:
    #   - code: nomi tabella PG snake_case lowercase
    #   - area: enum chiuso UPPERCASE (PERMESSI/AUTH/ANAGRAFICHE/...)
    _AUDIT_CODE_RE: ClassVar = re.compile(r"^[a-z_][a-z0-9_]*$")
    _AUDIT_AREA_RE: ClassVar = re.compile(r"^[A-Z][A-Z_]*$")
    # ⚠️ `storico_table` e' QUALIFICATA (`schema.tabella`), quindi vuole una sua
    #    regex: `_AUDIT_CODE_RE` non ammette il punto e scarterebbe OGNI riga —
    #    cioe' un audit log vuoto invece di un errore. ⭐ E il primo segmento
    #    ammette `_` iniziale apposta: un identificatore PostgreSQL puo'
    #    cominciare con `_`, e la tabella che ha fatto emergere tutto questo
    #    (una shadow «legacy» rinominata col prefisso, droppata il 2026-09-12)
    #    lo faceva. La regex resta giusta anche senza quella tabella.
    _AUDIT_STORICO_TABLE_RE: ClassVar = re.compile(
        r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$"
    )

    # Scopo: Restituisce la timeline globale degli eventi audit permessi (Fase 5).
    # Paginata, filtri opzionali: data_da, data_a, tabella.
    #
    # Build dinamico delle UNION ALL dalla vista `script.vw_audit_sources`:
    # niente piu' lista hardcoded `_AUDIT_TABLES`. Quando il team DB aggiunge
    # una sorgente alla vista, l'audit log la vede automaticamente.
    #
    # Ogni branch UNION espone:
    #   - `code` (= label_key sorgente, era `tabella`),
    #   - `storico_id` = `s.id` (PK riga in storico.<tabella>, NECESSARIO per
    #     `fn_audit_summary` — l'id della riga sorgente non basta),
    #   - `area_funzionale` (5 valori: PERMESSI/AUTH/ANAGRAFICHE/EMITTENTI/FATTURAZIONE),
    #   - `summary` + `diff` calcolati inline via LATERAL `fn_audit_summary`
    #     (1 query, no N+1 sulle pagine).
    #
    # ⛔ IL `FROM` SI COSTRUISCE DA `storico_table`, MAI DA `code` (2026-09-02).
    #    Sono due cose diverse e per un anno hanno coinciso:
    #      · `code` e' l'IDENTITA' LOGICA — ci si ordina
    #        (`AUDIT_ORDER_COLUMNS["tabella"]`), ci si filtra l'API (`?tabella=`)
    #        e lo prende `fn_audit_summary` come chiave di dispatch;
    #      · `storico_table` e' il NOME FISICO, l'unica sede autorevole, quella
    #        che `fn_audit_summary` usa per il suo `EXECUTE format(%I)`.
    #    Finche' coincidono, dedurre il secondo dal primo SEMBRA funzionare.
    # 🔴 Difetto reale, e non teorico: `anagrafiche.risorse_umane_auth_user` e'
    #    diventata una vista (la tabella e' `_legacy_...`), su un database
    #    RICOSTRUITO `storico.risorse_umane_auth_user` non nasce piu' e la CI e'
    #    andata rossa con 9 errori. Il database di sviluppo no — si portava
    #    dietro la vecchia dalla propria storia — quindi il difetto era
    #    invisibile esattamente dove si lavora.
    # ⚠️ Il rosso l'ha spento il team DB (`attivo = f` sulla riga 5); QUESTA
    #    riga toglie la TRAPPOLA, cioe' fa in modo che la prossima rinomina non
    #    ripeta la storia. Sono due cose separate, e nessuna delle due sostituisce
    #    l'altra.
    #
    # Whitelist `vw_audit_sources` controllata dal DB + regex paranoia
    # (`_AUDIT_CODE_RE`, `_AUDIT_STORICO_TABLE_RE`) per defense-in-depth.
    def list_audit_log(
        self,
        *,
        data_da: date | None = None,
        data_a: date | None = None,
        tabella: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        # ⛔ Il cache GREZZO e non `list_audit_sources()`: quello e' il payload
        #    pubblico e `storico_table` apposta non ce l'ha.
        sources = self._list_audit_sources_cached()
        if not sources:
            return [], 0

        unions: list[str] = []
        for code, _label_key, area, storico_table in sources:
            if tabella and tabella != code:
                continue
            # Defensive: i tre valori arrivano da vw_audit_sources (whitelist
            # DB) ma sono interpolati in f-string. Regex check come safety net
            # se la vista esponesse mai un nome anomalo. Salta la sorgente: la
            # dropperebbe silenziosamente, ma la vista e' under DB control.
            if not self._AUDIT_CODE_RE.match(code):
                continue
            if not self._AUDIT_AREA_RE.match(area):
                continue
            if not self._AUDIT_STORICO_TABLE_RE.match(storico_table or ""):
                continue
            unions.append(
                f"SELECT '{code}' AS code, "  # noqa: S608 — code/area/storico_table dal catalogo vw_audit_sources filtrati dalle regex _AUDIT_*_RE, nessun input
                f"'{area}' AS area_funzionale, "
                f"s.id AS storico_id, "
                f"s.valid_from, s.tipo_operazione, s.user_insert, "
                f"s.snapshot, "
                # ⭐ `fn_audit_summary` prende il `code`, non la tabella: la sua
                #    chiave di dispatch e' l'identita' logica, ed e' lei che va
                #    a rileggere `storico_table` dal catalogo. Le due
                #    interpolazioni qui sotto SONO diverse apposta.
                f"script.fn_audit_summary('{code}', s.id) AS audit "
                f"FROM {storico_table} s"
            )

        if not unions:
            return [], 0

        params: list[Any] = []
        sql = f"WITH events AS ({' UNION ALL '.join(unions)}) "
        sql += (
            "SELECT code, area_funzionale, storico_id, valid_from, "
            "tipo_operazione, user_insert, snapshot, audit, "
            "COUNT(*) OVER() AS total_count "
            "FROM events WHERE true "
        )

        # Giorni dell'AZIENDA, `data_a` incluso (BB): fino al 2026-10-09 il
        # confine basso era `%s::timestamptz` e l'alto `%s::date`, due forme
        # diverse per lo stesso filtro, entrambe nel fuso della sessione.
        giorno_sql, giorno_params = predicato_giorno_operativo("valid_from", data_da, data_a)
        sql += f"AND {giorno_sql} "
        params.extend(giorno_params)

        # Ordinamento sicuro: la whitelist traduce il nome di risultato nel nome
        # colonna in un passaggio solo (vedi `AUDIT_ORDER_COLUMNS`).
        order_column = colonna_ordinamento(order_by, AUDIT_ORDER_COLUMNS)
        # ⛔ Direzione risolta PRIMA del ramo (2026-09-26): il ramo di default
        #    la ignora, e un `order_dir` estraneo passava muto.
        direction = sql_order_direction(order_dir, default_desc=True)
        if order_column:
            # `valid_from DESC` NON e' uno spareggio tecnico ma l'ordine
            # STORICO delle versioni di una stessa riga (la piu' recente
            # prima): resta fisso anche ordinando al contrario, altrimenti la
            # storia di un record si leggerebbe a rovescio.
            sql += f"ORDER BY {order_column} {direction}, valid_from DESC "
        else:
            sql += "ORDER BY valid_from DESC "
        sql += "LIMIT %s OFFSET %s"
        # ⚠️ Il clamp sta nel repository, non nella view: un `?limit=-5`
        #    arrivava a DB come `LIMIT -5` e rispondeva 500.
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        params.extend([safe_limit, safe_offset])
        rows, total_count = fetch_paged_with_total(sql, params, offset=safe_offset)
        events = [
            {
                "code": r["code"],
                # Manteniamo `tabella` come alias di `code` per retrocompat
                # con consumer FE legacy. Nuovi consumer usano `code`.
                "tabella": r["code"],
                "area_funzionale": r["area_funzionale"],
                "storico_id": r["storico_id"],
                "timestamp": r["valid_from"].isoformat() if r["valid_from"] else None,
                "tipo_operazione": self._OP_LABELS.get(r["tipo_operazione"], str(r["tipo_operazione"])),
                "user_modifica": r["user_insert"],
                "snapshot": r["snapshot"],
                "audit": r["audit"],  # {"summary": "...", "diff": [...]}
            }
            for r in rows
        ]
        return events, total_count

    # ================================================================== #
    # Riepilogo permessi per area (chip della lista operatori)            #
    # ================================================================== #

    # Scopo: Il riepilogo dei permessi PER AREA di un insieme di operatori —
    #        livello effettivo, override scritti, voci fermate dal tetto — per
    #        le chip della lista operatori (brief riepilogo-permessi, 2026-10-06).
    # ⭐ Tutto da `script.fn_get_permessi_riepilogo_aree`: la funzione legge le
    #    sedi uniche (resolver d'area, funzioni del tetto, e
    #    `vw_override_operatore_area` per il conteggio). Qui si aggiungono solo
    #    le etichette dell'area. Fino al 2026-10-06 questo metodo costruiva con
    #    un f-string una subquery per area, su TUTTI gli operatori.
    # ⚠️ Riceve gli id della PAGINA della lista. Un id che non e' un operatore si
    #    scarta prima della funzione (che altrimenti gli darebbe righe
    #    `BLOCCATO`): il riepilogo resta perimetrato come la lista.
    def get_permessi_riepilogo(self, auth_user_ids: list[int]) -> list[dict[str, Any]]:
        if not auth_user_ids:
            return []
        sql = f"""
            SELECT r.auth_user_id,
                   r.area_id,
                   af.codice      AS area_codice,
                   af.descrizione AS area_descrizione,
                   r.livello::text AS livello,
                   r.override_count,
                   r.voci_limitate
              FROM script.fn_get_permessi_riepilogo_aree(
                     ARRAY(SELECT x.id
                             FROM unnest(%s::int[]) AS x(id)
                            WHERE {_CATEGORIA_OPERATORE.format(au="x.id")})
                   ) r
              JOIN config.aree_funzionali af ON af.id = r.area_id
             ORDER BY r.auth_user_id, af.ordinamento, af.codice
        """  # noqa: S608 — frammento letterale _CATEGORIA_OPERATORE, id come parametro
        with connection.cursor() as cursor:
            cursor.execute(sql, [list(auth_user_ids)])
            return rows_to_list(cursor)

    # ================================================================== #
    # Lookup: aree funzionali e azioni processo                            #
    # ================================================================== #

    # Scopo: Lista aree funzionali attive per dropdown/selezione.
    def list_aree_funzionali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, codice, codice_interno, schema_db, descrizione,
                          ordinamento
                     FROM config.aree_funzionali
                    WHERE attivo = true
                    ORDER BY ordinamento, codice"""
            )
            return rows_to_list(cursor)

    # Scopo: Lista azioni processo attive per dropdown/selezione.
    # ⭐ `livello_minimo_area` (2026-10-31): il tetto d'area dell'azione, letto
    #    dall'editor del profilo REPARTO per l'anteprima «limitata dall'area»
    #    (`tettoArea.js`), come gia' fa il pannello dell'operatore dai permessi
    #    effettivi. Senza, si abilitava su un reparto un'azione che il livello
    #    della sua area rende senza effetto, e nessuno lo diceva.
    def list_azioni_processo(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT ap.id, ap.permission_codename, ap.descrizione,
                          ap.pericolosa, ap.area_id,
                          af.codice AS area_codice,
                          ap.livello_minimo_area::text AS livello_minimo_area
                     FROM config.azioni_processo ap
                     JOIN config.aree_funzionali af ON af.id = ap.area_id
                    WHERE ap.attivo = true
                    ORDER BY af.ordinamento, ap.permission_codename"""
            )
            return rows_to_list(cursor)

    # Scopo: Lista emittenti fiscali per dropdown scope operatore.
    #        Espone ragione_sociale del soggetto associato via soggetto_ruolo_id.
    # `emittenti_fiscali.descrizione` non viene piu' proiettata ne' usata come
    # tiebreaker d'ordine (etichetta interna divergente, in via di eliminazione —
    # brief `brief-emittente-ragione-sociale-dal-soggetto.md`): il consumer FE
    # (`formatEmittenteOptionLabel`) legge `ragione_sociale`, gia' presente.
    def list_emittenti_fiscali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT ef.id, ef.codice,
                          ef.soggetto_ruolo_id,
                          -- Il SOGGETTO dell'emittente (uuid): chi sceglie fra
                          -- gli indirizzi dell'azienda lo legge da qui
                          -- (`useEmittenteFiscaleField.soggettoIdSessione`,
                          -- il super admin dentro un emittente).
                          sr.soggetto_id,
                          s.ragione_sociale_completa AS ragione_sociale
                     FROM anagrafiche.emittenti_fiscali ef
                     LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
                     LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
                    WHERE ef.attivo = true
                    ORDER BY s.ragione_sociale_completa, ef.codice"""
            )
            return rows_to_list(cursor)

    # Scopo: Wrapper script.fn_get_setup_status. Refactor operatore-emittenti
    # (decisione D1): conta emittenti attivi, operatori totali/assegnati/
    # admin globali/non assegnati per il banner UI "operatori non assegnati".
    def get_setup_status(self) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_get_setup_status()")
            row = cursor.fetchone()
        return row[0] if row else {}
