# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.contratti + contratti_righe +
#        contratti_utilities (CRUD v5 — F2-BE-05).
#
#        Modello contratto post refactor 2026-05-15: un unico tipo di
#        contratto con due forme derivate (non scelte dall'operatore):
#          - "con_listino"  : `listino_id` valorizzato. Le righe del listino
#                             sono lette via resolver (versione fissata
#                             all'attivazione). Le eccezioni vivono in
#                             `contratti_righe` come OVERRIDE / ESCLUSIONE /
#                             AGGIUNTA. Variazione globale opzionale.
#          - "senza_listino": `listino_id` NULL. Tutte le righe sono AGGIUNTA
#                             con prezzo manuale, governate dal contratto
#                             stesso.
#
#        Validazioni in ordine crescente di costo:
#          1) struttura payload (chiavi ammesse, tipi)
#          2) coerenza coppia variazione globale (tipo+valore entrambi
#             NULL o entrambi NOT NULL)
#          3) affidamento ai trigger DB per gli invarianti piu' complessi
#             (overlap cross-contratto, tipo/classe utenza dinamica, lock
#             della testata fuori bozza, validita' versione listino fissata).
#
#        Il numero contratto e' generato nel service via
#        `script.fn_generate_codice('contratto')` — NON va mai
#        accettato in payload (immutabile via trigger lock_columns).
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import DatabaseError, IntegrityError, transaction

from apps.config.sorgenti import SORGENTE_CONTRATTO
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.services.documento_modello import (
    e_stato_di_annullo,
    rifiuta_stato_di_emissione,
    stato_di_emissione,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.vendite.services._righe_bozza_guard import Verbo, richiedi_righe_in_bozza
from apps.vendite.services._cliente_coppia_documento import (
    coppia_cambiata,
    rifiuta_colonne_ferme,
    risolvi_cliente_coppia,
)
from apps.vendite.services._annullo_con_legami import (
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    delete_indirizzo_documento,
    list_indirizzi_documento,
    upsert_indirizzo_documento,
)
from apps.core.services.payload_helpers import (
    MISSING,
    PayloadValidator,
    map_integrity_error,
)
from apps.core.services.partitioned_note_service import contatori_documento
from apps.vendite.db.note_repositories import NOTE_REPO_CONTRATTO
from apps.vendite.db.contratti_repository import (
    STATO_CESSATO,
    TESTATA_CONTRATTI,
    _ORDER_COLS_CONTRATTI,
    ContrattiRepository,
    ContrattoRigheListaRepository,
)
from apps.vendite.db._documento_eccezioni_repo import (
    list_erogazioni_riga,
    listino_versione_operativa,
)
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_overrides,
    resolve_emittente_sr_id_for_testata,
)
from apps.vendite.services._approvazioni_prezzo_constants import (
    META_SORGENTE_CONTRATTO,
    STATO_APPROVAZIONE_PENDING,
)
from apps.vendite.services._pricing_gate_helpers import (
    check_limite_variazione_globale,
    guard_uom_id_positive,
    resolve_or_check_override_prezzo,
    validate_componenti_overrides_authorization,
)

logger = logging.getLogger(__name__)


# Codici errore (registrati in error_policies.py).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
# ⭐ La sovrapposizione con un contratto vincolante ha UN codice, quello del
#    guard del DB (`script.fn_check_contratto_sovrapposto`, 2026-10-19). L'EXCLUDE
#    `ex_contratti_no_overlap` (`partecipa_overlap_snapshot`, cioe' vincolante) e'
#    la stessa regola, sulla corsa: risponde con lo stesso codice e lo stesso
#    testo del ripiego (senza il numero del contratto, che il vincolo non da').
#    Fino ad allora rispondeva con `E_VENDITE_CONTRATTO_OVERLAP` e un testo suo.
E_CONTRATTO_OVERLAP_ESISTENTE = "E_CONTRATTO_OVERLAP_ESISTENTE"
_MESSAGGIO_OVERLAP = USER_MESSAGE_FALLBACK[E_CONTRATTO_OVERLAP_ESISTENTE]


# Whitelist order_by: DERIVATA dalle chiavi del mapping SQL del repository
# (`_ORDER_COLS_CONTRATTI`), unica fonte di verita'. Evita il drift fra le due
# strutture: una chiave accettata dal service ma non mappata nel repo
# darebbe un fallback silenzioso a 'data' (ordinamento sbagliato senza
# errore). Sono i `campo_sorgente` della vista `vendite.vw_contratti_lista`
# che il FE invia come sortField (niente alias `ba_*` su cliente/id_fiscale).
_ORDER_BY_CONTRATTI: frozenset[str] = frozenset(_ORDER_COLS_CONTRATTI)


_AMBITI_VALIDI: frozenset[str] = frozenset({"COMMODITY", "COMMERCIO"})

# Lunghezze massime dei tre riferimenti dell'atto (I8/D9), allineate alle colonne
# di `vendite.contratti`: VARCHAR(15) per CIG e CUP, VARCHAR(100) per la commessa.
# ⚠️ Sono anche l'ORDINE in cui il mapper li scorre: e' l'ordine del blocco XML
#    FatturaPA, non l'alfabetico.
_CODICI_ATTO_MAX_LEN: dict[str, int] = {
    "codice_cig": 15,
    "codice_cup": 15,
    "codice_commessa": 100,
}
# ⭐ FONTE UNICA dei tre nomi dentro questo modulo: whitelist di update,
#   whitelist per stato ATTIVO e mapper li derivano tutti da qui. Scriverli tre
#   volte a mano significherebbe tre punti da tenere allineati per una lista che
#   non cambia mai insieme.
# 📌 L'unico altro posto che li nomina e' `TESTATA_UPDATE_COLUMNS` nel repository, ed
#   e' voluto che resti esplicito: e' il TERZO anello, e `ContrattiCatenaUpdateTests`
#   esiste proprio per confrontare i tre anelli fra loro — derivarlo dallo stesso
#   oggetto renderebbe il confronto vero per costruzione, cioe' spegnerebbe il
#   guardrail invece di superarlo.
_CODICI_ATTO: frozenset[str] = frozenset(_CODICI_ATTO_MAX_LEN)
# Tipi variazione ammessi sulla variazione GLOBALE della testata contratto.
# Decisione 2026-05-18 (§3-bis-E refactor): solo PERCENTUALE. VALORE_FISSO
# resta ammesso unicamente per OVERRIDE su singola riga (semantica "prezzo
# fisso sostitutivo per quell'articolo") — non per la testata, dove non
# avrebbe significato applicativo coerente coi gate L2 % e con la formula
# di applicazione cross-articolo del listino.
_TIPI_VARIAZIONE_GLOBALE_AMMESSI: frozenset[str] = frozenset({"PERCENTUALE"})


# Chiavi ammesse nel payload create testata. `numero` escluso: generato dal
# service. `stato_doc_contratto_id` escluso: stato iniziale DRAFT impostato
# dal service (cambi stato successivi via endpoint dedicato).
CREATE_KEYS_TESTATA: frozenset[str] = frozenset({
    # Post brief simmetria 2026-05-26: `emittente_fiscale_id` ora e' colonna
    # nativa di `vendite.contratti` (NOT NULL). Pattern duale al trigger
    # `script.trgfn_default_emittente_fiscale` (BB unico dal 2026-09-15, la
    # copia `trgfn_contratti_default_emittente` e' droppata): se il payload lo
    # specifica il
    # trigger salta; se NULL il trigger lo deriva da
    # `script.fn_resolve_emittente_for_user(GUC app.current_user_id)`.
    # Il FE invia sempre il valore pre-popolato da `defaultEmittenteId`
    # (operatore non-admin) o scelto dall'admin globale.
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "ambito",
    "valido_dal",
    "valido_al",
    "parent_contratto_id",
    "data",
    "listino_id",
    "tipo_variazione_globale",
    "valore_variazione_globale",
    # Snapshot categoria cliente: opzionale. Se fornito, congela il valore
    # scelto dall'operatore; se omesso, il trigger DB lo popola dal BA.
    "categoria_cliente_id_snapshot",
    # Corsia di instradamento della fatturazione: «questo contratto va fatturato
    # subito». Si decide PRIMA del push in commessa — dopo, il flag e' inerte
    # (fa parte della chiave di dedup della commessa) e il guard DB
    # `trgfn_guard_fatturazione_immediata_immutabile` respinge l'UPDATE.
    # ⚠️ Non basta la whitelist: il mapper `_build_create_data_testata` copia
    # campo per campo, quindi la chiave va letta anche li' (lezione del difetto
    # 2026-07-27: stesso gesto su tre domini, due successi e un no-op).
    # ⚠️ Contratto con la fn madre (§C4 del brief DB): omettere la chiave oppure
    # mandare un booleano, MAI `null` — la colonna e' NOT NULL e il filtro della
    # whitelist DB e' sulla PRESENZA della chiave, non sul valore.
    "fatturazione_immediata",

    # Snapshot valuta fissato al CREATE, opzionale: se non passato, il
    # trigger DB `_a*_set_valuta_default_ins` risolve via
    # `vendite.fn_get_valuta_id` (catena BA → emittente → gestore, brief
    # work-done 2026-05-29). Non in UPDATE_KEYS_TESTATA: snapshot
    # immutabile post-CREATE (simmetrico a preventivi/offerte).
    "valuta_id",
    # Riferimenti dell'atto (I8/D9), ammessi in CREATE dalla slice S3-b
    # (2026-08-31), ad apply avvenuto del changeSet `20260831-24` che li ha
    # aggiunti alla whitelist interna di `vendite.fn_create_contratto`.
    # ⛔ Prima erano fuori DI PROPOSITO: quella whitelist non RESPINGE una
    #    chiave che non conosce, la SCARTA — il contratto sarebbe nato, il
    #    backend avrebbe risposto 200 e il CIG non sarebbe andato da nessuna
    #    parte. Stesso difetto gia' pagato su `fatturazione_immediata` il
    #    2026-07-27.
    # ⭐ Il caso d'uso e' proprio la creazione: un CIG nasce con la gara, cioe'
    #    PRIMA del contratto.
    *_CODICI_ATTO,
    "meta",
    # Sub-entita' opzionale: se presente crea la riga utility 1:1 nella
    # stessa transazione. Il service NON permette payload utility senza
    # chiavi pulite (stessa whitelist _UTILITY_KEYS).
    "utility",
})

UPDATE_KEYS_TESTATA: frozenset[str] = frozenset({
    # Il cliente si cambia in bozza, per coppia (B-1 di Tid, 2026-10-12,
    # brief-db-indirizzi-documento-seguono-il-cliente §8.3): BA e istanza
    # viaggiano insieme, risolti dal BB `risolvi_cliente_coppia` sulla utility
    # della testata. Fuori bozza li ferma il lock di testata del DB. Al cambio
    # di coppia il DB rifa' la scheda di fornitura e gli indirizzi presi
    # dall'anagrafica.
    "billing_account_id",
    "istanza_utility_id",
    "ambito",
    "valido_dal",
    "valido_al",
    "parent_contratto_id",
    "data",
    "listino_id",
    "tipo_variazione_globale",
    "valore_variazione_globale",
    "categoria_cliente_id_snapshot",
    "fatturazione_immediata",
    # Riferimenti dell'atto da cui nasce il contratto (I8/D9, 2026-08-29).
    # In fattura elettronica viaggiano nello STESSO blocco
    # (DatiContratto/DatiOrdineAcquisto): nascono insieme e nominano lo stesso
    # atto. Prima stavano su `anagrafiche.clienti`, cioe' su una riga PER
    # FORNITURA — un CIG identifica una GARA, quindi una PA con tre contratti ha
    # tre CIG: su quella riga ne entrava uno solo, ripetuto su tutte le forniture
    # dello stesso contratto e incapace di tenerne due sulla stessa.
    *_CODICI_ATTO,
    "meta",
})

# Il corpo della PATCH: le colonne della testata piu' la scheda di fornitura
# inline (`utility`), come in creazione e come sull'offerta, nella stessa
# transazione. ⛔ Fino al 2026-10-14 il drawer mostrava tipo e classe utenza
# modificabili in bozza ma la PATCH non le portava: «contratto salvato» e
# niente scritto. `utility` non e' una colonna: resta fuori da
# `UPDATE_KEYS_TESTATA`, la catena che i guardrail confrontano col repository.
UPDATE_KEYS_CONTRATTO: frozenset[str] = UPDATE_KEYS_TESTATA | {"utility"}

# Quali colonne della testata si cambiano in quale stato lo dice il DB,
# colonna per colonna: il lock `vendite.trgfn_doc_testata_lock_fuori_bozza`
# (DRAFT tutto; ATTIVO `valido_al`, i riferimenti dell'atto e `meta`; CESSATO e
# ANNULLATO niente). Fino al 2026-10-10 qui c'era la tabella per stato
# `_CONTRATTO_PATCH_ALLOWED_BY_STATE`, la seconda copia di quella regola
# (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del lock passa com'e'.

# Il listino sotto le righe: se si cambia (messo o sostituito) con righe
# attive, o si toglie con eccezioni OVERRIDE/ESCLUSIONE, lo dice il DB, per
# contratto e offerta (`script.trgfn_doc_guard_listino_con_righe`, codici
# `E_DOC_LISTINO_CAMBIO_CON_RIGHE` e `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI`,
# 422 sul campo `listino_id`). Fino al 2026-10-11 le due regole vivevano solo
# qui (brief-db-testata-dopo-emissione §11, R-DB-4 e R-BE-5).
#
# `tipo_variazione_globale` / `valore_variazione_globale` NON sono bloccati:
# la variazione si applica solo alle righe DA_LISTINO della preview (le
# persistite OVERRIDE/AGGIUNTA mantengono prezzo proprio, ESCLUSIONE ha
# prezzo NULL). Cambiarli con righe presenti cambia la visualizzazione preview
# ma non rompe coerenza dati. Se serve un blocco UX preventivo si aggiunge
# come gating FE / warning, non come hard guard BE.

# In create: numero e stato_doc_contratto_id sono impostati dal service,
# mai in payload. In update anche utility ed emittente, rifiutate sul campo da
# `rifiuta_colonne_ferme` (BB comune a preventivo e offerta).
_FORBIDDEN_TESTATA_CREATE: frozenset[str] = frozenset({
    "numero",
    "stato_doc_contratto_id",
})
# ⭐ Dal 2026-10-19 (R-BE-10) utility ed emittente non stanno piu' qui: le
#    rifiuta `rifiuta_colonne_ferme`, sul campo e con la frase del lock del DB
#    (prima: messaggio suo, senza campo). Si cambia il cliente, cioe' BA e
#    istanza in coppia, dentro la stessa utility (B-4 di Tid, 2026-10-12); un BA
#    di un altro emittente lo dice il guard `script.trgfn_doc_guard_emittente_ba`.
_FORBIDDEN_TESTATA_UPDATE: frozenset[str] = frozenset({
    "numero",
    "stato_doc_contratto_id",
})


# Righe contratto: chiavi ammesse create/update. tipo_eccezione e' la
# classificazione introdotta dal refactor 2026-05-15: distingue OVERRIDE,
# ESCLUSIONE, AGGIUNTA. Obbligatoria in create (NOT NULL nello schema),
# immutabile in update (per cambiare tipo serve DELETE + INSERT — meno
# zone grigie di un cambio di semantica in-place).
CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id",
    "tipo_eccezione",
    "tipo_erogazione",
    "fonte_quantita_attesa",
    "periodicita",
    "generazione_canone",
    "competenza_canone",
    "prezzo_unitario",
    # ⛔ Niente `quantita`: e' calcolata dal DB da `qta_operativa` (FISSA) e
    #    vuota con una fonte a valle (`script.trgfn_qta_from_operativa`). Un
    #    client che la manda riceve un 400 sulla chiave. Fino al 2026-10-21
    #    restava per la DERIVATA_COMPONENTI, ritirata (I-D1 di
    #    brief-db-offerta-emissione-ed-erogazione).
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "ordine",
    "attivo",
    "meta",
    # Modello unificato BoM 2026-05-13: override prezzi componenti per
    # auto-init post-create_riga su articoli compositi. Forma:
    # {componente_id_uuid: prezzo_numeric}. Validato/normalizzato da
    # `_normalize_componenti_overrides` prima dell'init.
    "componenti_overrides",
    # Workflow L3 (refactor 2026-05-19 BE porting gate riga contratti): flag
    # opt-in con cui il client conferma di voler aprire una pratica di
    # approvazione quando il prezzo viola L2. Estratto e consumato da
    # create_riga prima di `_build_data_riga` (non finisce nella tabella).
    "richiesta_approvazione",
})

UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
    "tipo_erogazione",
    "fonte_quantita_attesa",
    "periodicita",
    "generazione_canone",
    "competenza_canone",
    "prezzo_unitario",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "ordine",
    "attivo",
    "meta",
    # Workflow L3: vedi commento CREATE_KEYS_RIGA. update_riga lo gestisce
    # alla stessa stregua per `prezzo_unitario` modificato che viola L2.
    "richiesta_approvazione",
})

# In create: contratto_id arriva dall'URL, non da payload. articolo_id e
# tipo_eccezione sono obbligatori e accettati. In update: articolo_id e
# tipo_eccezione diventano immutabili (cambio tipo = DELETE + INSERT).
_FORBIDDEN_RIGA_CREATE: frozenset[str] = frozenset({"contratto_id"})
_FORBIDDEN_RIGA_UPDATE: frozenset[str] = frozenset({
    "articolo_id", "contratto_id", "tipo_eccezione",
})

# Tipi eccezione ammessi su contratti_righe (refactor 2026-05-15).
_TIPI_ECCEZIONE: frozenset[str] = frozenset({"OVERRIDE", "ESCLUSIONE", "AGGIUNTA"})
# Sottoinsieme che richiede il passaggio per il gate L1+L2+L3 (refactor
# 2026-05-19 BE porting gate riga contratti). ESCLUSIONE ha prezzo NULL per
# design e salta i gate; OVERRIDE/AGGIUNTA passano al BB
# `resolve_or_check_override_prezzo_riga_contratto` con la matrice
# Alternativa B (L1 sempre, L2/L3 condizionali al resolver).
_TIPI_ECCEZIONE_CON_GATE: frozenset[str] = frozenset({"OVERRIDE", "AGGIUNTA"})

# Utility 1:1: chiavi ammesse in create/update. istanza_utility_id e
# utility_id sono derivati dal contratto in create; immutabili in update.
# Utility 1:1: istanza_utility_id e utility_id derivano dalla testata,
# NON dal payload (evita incoerenze silenziose).
UTILITY_CREATE_KEYS: frozenset[str] = frozenset({
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})

UTILITY_UPDATE_KEYS: frozenset[str] = frozenset({
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})

_UTILITY_IMMUTABLE_KEYS: frozenset[str] = frozenset({
    "contratto_id",
    "istanza_utility_id",
    "utility_id",
})


_MESSAGE = "Payload contratto non valido."
_MESSAGE_RIGA = "Payload riga contratto non valido."
_MESSAGE_UTILITY = "Payload utility contratto non valido."

# Nota: lo stato iniziale DRAFT (config.stati_doc_contratti) e' ora risolto
# DENTRO la funzione madre vendite.fn_create_contratto (fix #2), non piu' dal BE.


# Mapping UNIQUE/EXCLUDE/FK -> codici errore applicativi.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_contratti_numero": (
        E_VENDITE_DUPLICATO,
        "Numero contratto gia' esistente.",
    ),
    # uq_* nome storico (UNIQUE WITHOUT OVERLAPS pre-2026-05-21);
    # ex_* nome post-fix overlap parziale 2026-05-21 (migration 20260521-01..03,
    # EXCLUDE gist partial WHERE NOT is_abortito_snapshot). Entrambi mappati
    # per resilienza a futuri rename DB.
    "uq_contratti_no_overlap": (E_CONTRATTO_OVERLAP_ESISTENTE, _MESSAGGIO_OVERLAP),
    "ex_contratti_no_overlap": (E_CONTRATTO_OVERLAP_ESISTENTE, _MESSAGGIO_OVERLAP),
    "uq_contratti_utilities_contratto_id": (
        E_VENDITE_DUPLICATO,
        "Questo contratto ha gia' una riga utility associata.",
    ),
}
# Lo dicono il BB `risolvi_cliente_coppia` (prima) e la FK composta (dopo):
# una frase sola.
_MSG_BA_FUORI_COPPIA = (
    "Il billing account non e' quello dell'istanza e della utility del contratto."
)
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_contratti_billing_account": (E_VENDITE_FK, "Billing account inesistente."),
    # FK composta (billing_account_id, istanza_utility_id, utility_id) verso il
    # BA della coppia, dal 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): la
    # semplice qui sopra resta accanto, e dice solo «non esiste».
    "fk_contratti_ba_coppia": (
        E_VENDITE_FK,
        _MSG_BA_FUORI_COPPIA,
        "billing_account_id",
    ),
    "fk_contratti_istanza": (E_VENDITE_FK, "Istanza utility inesistente."),
    "fk_contratti_utility": (E_VENDITE_FK, "Utility inesistente."),
    "fk_contratti_listino": (E_VENDITE_FK, "Listino inesistente."),
    "fk_contratti_parent": (E_VENDITE_FK, "Contratto padre inesistente."),
    "fk_v_contratti_stato_ddt": (E_VENDITE_FK, "Stato documento inesistente."),
    "fk_contrighe_articoli": (E_VENDITE_FK, "Articolo inesistente."),
    "fk_contrighe_contratti": (E_VENDITE_FK, "Contratto inesistente."),
    "fk_contratti_righe_uom_operativa_id": (E_VENDITE_FK, "UoM operativa inesistente."),
    "fk_contratti_utilities_classi_utenze": (E_VENDITE_FK, "Classe utenza inesistente."),
    "fk_contratti_utilities_tipo_utenza": (E_VENDITE_FK, "Tipo utenza inesistente."),
    "fk_contratti_utilities_istanze_utilities": (E_VENDITE_FK, "Istanza utility inesistente."),
    "fk_contratti_utilities_istanze_dati_precontrattuali": (
        E_VENDITE_FK,
        "Istanza dati precontrattuali inesistente.",
    ),
    "fk_contratti_utilities_contratti": (E_VENDITE_FK, "Contratto inesistente."),
    # FK creata con REFERENCES inline: PG auto-genera il nome. Mappiamo sia
    # la convenzione progetto (fk_*) sia il formato PG ({table}_{col}_fkey).
    "fk_contratti_categoria_cliente_snapshot": (
        E_VENDITE_FK,
        "Categoria cliente (snapshot) inesistente.",
    ),
    "contratti_categoria_cliente_id_snapshot_fkey": (
        E_VENDITE_FK,
        "Categoria cliente (snapshot) inesistente.",
    ),
}


# Marker di identificazione codici P0001 dai trigger. Match multi-substring
# stretto (tutti i marker della tupla devono comparire nel MESSAGE).
# Coerente con pricing_service._KNOWN_DB_ERROR_MARKERS.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Refactor modalita 2026-05-15: i vecchi marker E_CONTRATTO_MODALITA_C_*
    # sono stati droppati dal team DB con i trigger correlati. I nuovi
    # marker coprono il modello unificato a 3 eccezioni + lock attivazione.
    (
        "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE",
        ("contratto senza listino", "almeno un'AGGIUNTA"),
    ),
    (
        "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO",
        ("AGGIUNTA", "gia' presente nel listino"),
    ),
    (
        "E_ARTICOLO_ESCLUSO_DA_CONTRATTO",
        ("articolo escluso dal contratto",),
    ),
    (
        "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI",
        ("tipo_utenza_id e classe_utenza_id sono obbligatori",),
    ),
    (
        "E_CONTRATTO_CLASSE_TIPO_INCOERENTE",
        ("appartiene al tipo", "ma il contratto dichiara tipo"),
    ),
    (
        "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI",
        ("senza dimensione tipo/classe", "devono essere NULL"),
    ),
    # Refactor 2026-05-20: defense-in-depth. La transizione ATTIVO → ANNULLATO
    # NON e' ammessa lato UI (bottone "Annulla" visibile solo per DRAFT) ma
    # il trigger DB esiste come safety net e blocca chiunque tenti la
    # transizione via SQL diretto / tool esterno con E_CONTRATTO_ANNULLATO_CON_FATTURE
    # se ci sono attivita_fatturabili gia' fatturate. Marker ipotizzati;
    # se al primo trigger reale il match non scatta, aggiornare le
    # sottostringhe in base al log.
    (
        "E_CONTRATTO_ANNULLATO_CON_FATTURE",
        ("ANNULLATO", "fatture"),
    ),
)


# Gli ingressi del gate L2 sulla variazione globale (`_check_limite_variazione_globale`).
_INGRESSI_GATE_L2 = frozenset({
    "valore_variazione_globale", "tipo_variazione_globale", "billing_account_id",
})


class ContrattiService:
    """Service CRUD contratti v5 (F2-BE-05)."""

    def __init__(self) -> None:
        self._repo = ContrattiRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="contratti_service",
        )

    # =================================================================
    # Guard DB errors uniforme (map IntegrityError + P0001 trigger)
    # =================================================================

    # Scopo: Context manager che normalizza errori DB sollevati dentro il
    #        blocco in `ServiceError` applicativi. Concentra in un unico
    #        posto la catena try/except duplicata per tutti i mutatori.
    #        ATTENZIONE (igiene analisi-fix-transazioni): questo NON e' un
    #        confine transazionale — non apre alcun `transaction.atomic()`, e'
    #        solo un mapper di eccezioni. Per l'atomicita' di 2+ scritture serve
    #        un `with transaction.atomic()` esplicito ATTORNO (vedi create/update
    #        riga). Rinominato da `_db_errors` per non trarre in inganno il lettore.
    @contextmanager
    def _map_db_errors(
        self,
        context: dict[str, Any],
        *,
        fallback_message: str = "Violazione vincolo DB su contratto.",
    ) -> Iterator[None]:
        try:
            yield
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_VENDITE_VALIDATION,
                fallback_message=fallback_message,
                context=context,
            )
        except DatabaseError as exc:
            ErrorManager.raise_from_database_error(
                exc,
                known_markers=_KNOWN_DB_ERROR_MARKERS,
                fallback_code=E_VENDITE_VALIDATION,
                message="Violazione vincolo contrattuale.",
                fallback_message=_MESSAGE,
                context=context,
                function_name="contratti_service.db_error",
            )

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata contratti con filtri standard espliciti.
    #        Il backend non applica default temporali impliciti: eventuali
    #        default visibili all'operatore sono responsabilita' della UI.
    def list_contratti(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_doc_contratto_id: int | None = None,
        utility_id: int | None = None,
        ambito: str | None = None,
        listino_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        scadenza_mese: str | None = None,
        auth_user_id: int | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_CONTRATTI, order_dir=order_dir)
        if ambito is not None:
            ErrorManager.require(
                ambito in _AMBITI_VALIDI,
                code=E_VENDITE_VALIDATION,
                message="Filtro ambito non valido.",
                detail=f"Ammessi: {', '.join(sorted(_AMBITI_VALIDI))}.",
                context={"ambito": ambito},
            )
        # Validazione scadenza_mese: formato YYYY-MM, mese >= mese corrente.
        if scadenza_mese is not None:
            import re
            ErrorManager.require(
                bool(re.match(r"^\d{4}-\d{2}$", scadenza_mese)),
                code=E_VENDITE_VALIDATION,
                message="Formato scadenza_mese non valido.",
                detail="Atteso YYYY-MM (es. 2026-07).",
                context={"scadenza_mese": scadenza_mese},
            )
        return self._repo.list_contratti(
            search=search,
            billing_account_id=billing_account_id,
            stato_doc_contratto_id=stato_doc_contratto_id,
            utility_id=utility_id,
            ambito=ambito,
            listino_id=listino_id,
            data_da=data_da,
            data_a=data_a,
            scadenza_mese=scadenza_mese,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
            max_limit=max_limit,
        )

    # Scopo: Etichette leggibili dei filtri attivi, incluse come metadato nel
    #        file di export (DEF-1 §6: un file filtrato deve dichiararsi
    #        sottoinsieme). I filtri FK sono dichiarati con l'id (sufficiente a
    #        comunicare "lista filtrata"); i filtri testuali/data sono resi
    #        come stringa.
    def resolve_filtri_export_label(
        self,
        *,
        ambito: str | None = None,
        stato_doc_contratto_id: int | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        scadenza_mese: str | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if ambito:
            out["Ambito"] = ambito
        if stato_doc_contratto_id is not None:
            out["Stato (id)"] = stato_doc_contratto_id
        if utility_id is not None:
            out["Utility (id)"] = utility_id
        if listino_id is not None:
            out["Listino (id)"] = listino_id
        if billing_account_id is not None:
            out["Cliente BA (id)"] = billing_account_id
        if data_da is not None:
            out["Dal"] = str(data_da)
        if data_a is not None:
            out["Al"] = str(data_a)
        if scadenza_mese:
            out["Scadenza mese"] = scadenza_mese
        return out

    # Scopo: Dettaglio completo contratto (testata + utility 1:1 + righe +
    #        capabilities). Le capability (available_actions con default_date/
    #        min_date per "cessa", can_change_state, can_edit_*, non_editable_fields)
    #        sono calcolate da script.fn_available_actions_contratto: il backend
    #        non duplica la logica e trasporta il blob intatto SOTTO
    #        `capabilities` (api.md §«Il blob sta SOTTO `capabilities`»).
    #        ⚠️ Il blob porta `stato_codice` e `stato_codice_interno`, che la
    #        testata ha gia': fuso, il blob li sovrascriveva in silenzio.
    def get_contratto(self, contratto_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        testata = self._get_contratto_or_raise(contratto_id, op="get_contratto")
        testata["utility"] = self._repo.get_utility(contratto_id)
        righe = self._repo.list_righe(contratto_id)
        testata["righe"] = righe
        # Il badge FE "Gestisci righe" deve riflettere la lista effettiva
        # mostrata dal sub-drawer: in A/B e' preview listino+override, in C
        # sono le righe negoziate persistite in contratti_righe.
        if testata.get("listino_id"):
            testata["righe_count"] = len(self._repo.list_righe_preview(contratto_id))
        else:
            testata["righe_count"] = len(righe)
        testata["capabilities"] = self._repo.get_capabilities(contratto_id)
        testata["contatori"] = contatori_documento(NOTE_REPO_CONTRATTO, contratto_id)
        return testata

    # =================================================================
    # Creazione testata
    # =================================================================

    # Scopo: Crea un nuovo contratto. Genera numero via fn_generate_codice,
    #        risolve stato iniziale DRAFT, valida coerenza coppia variazione
    #        globale pre-DB, opzionalmente crea la riga utility 1:1 nella
    #        stessa transazione (trigger DB gestira' fail-fast su coerenze
    #        dinamiche).
    # ⛔ `auth_user_id`: il gate L2 sulla variazione globale vale anche alla
    #    NASCITA. Fino al 2026-10-21 lo applicava la sola PATCH, e un contratto
    #    creato con una variazione oltre la soglia dell'operatore passava
    #    (brief-be-verifica-documentazione-api §B9).
    def create_contratto(
        self, payload: dict[str, Any], *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_TESTATA_CREATE,
            reason="Campi gestiti dal sistema non modificabili in payload create.",
            # Le chiavi presenti le aggiunge `reject_keys`: l'elenco non si
            # ripete qui (e' l'insieme `forbidden`, e si e' gia' disallineato).
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=CREATE_KEYS_TESTATA, message=_MESSAGE)

        data = self._build_create_data_testata(payload)
        self._check_limite_variazione_globale(
            existing={}, data=data, auth_user_id=auth_user_id,
        )
        utility_payload = payload.get("utility")
        utility_data: dict[str, Any] | None = None
        if utility_payload is not None:
            self._validate_utility_payload_shape(utility_payload, for_create=True)
            utility_data = self._build_utility_data(
                utility_payload,
                istanza_utility_id=data["istanza_utility_id"],
                utility_id=data["utility_id"],
                for_create=True,
            )

        # Fix analisi-fix-transazioni #2 (Classe A): numero (`fn_generate_codice`)
        # + INSERT testata (stato DRAFT risolto dalla fn) + INSERT utility opzionale
        # in UNA sola statement atomica (fn madre), non piu' generate_numero + 2
        # INSERT separati in autocommit. O tutto o rollback (numero incluso):
        # niente contratto orfano ne' numero consumato a vuoto.
        with self._map_db_errors({"billing_account_id": data.get("billing_account_id")}):
            new_id = self._repo.create_contratto_atomico(
                testata=data, utility=utility_data,
            )

        # Lo slot di default lo riempie `vendite.fn_create_contratto` in coda,
        # nella stessa statement (brief-db-indirizzi-documento-seguono-il-cliente).
        return self.get_contratto(new_id)

    # =================================================================
    # Aggiornamento testata
    # =================================================================

    # Scopo: Aggiorna una testata contratto sui soli campi mutabili.
    #        Validazione coerenza coppia variazione globale pre-DB.
    #        `auth_user_id`: usato dal gate L2 sulla variazione globale
    #        (refactor 2026-05-15 §3-bis-E) per risolvere la soglia con la
    #        cascata user→categoria→group→emittente. None = gate L2 skip.
    def update_contratto(
        self,
        contratto_id: int,
        payload: dict[str, Any],
        *,
        auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        rifiuta_colonne_ferme(
            payload, code=E_VENDITE_VALIDATION, function_name=f"{__name__}.update_contratto",
        )
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_TESTATA_UPDATE,
            reason="Identificativi contratto non modificabili.",
            # Le chiavi presenti le aggiunge `reject_keys`: l'elenco non si
            # ripete qui (e' l'insieme `forbidden`, e si e' gia' disallineato).
            detail_prefix="Campi rifiutati",
            context_extra={"contratto_id": contratto_id},
        )
        self._v.validate_allowed_keys(payload, allowed=UPDATE_KEYS_CONTRATTO, message=_MESSAGE)
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            ErrorManager.require(
                isinstance(utility_payload, dict),
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE_UTILITY,
                detail="Campo 'utility' deve essere oggetto.",
                context={"field": "utility"},
            )
            # La coppia della scheda e' quella della testata, mai del payload.
            self._v.reject_keys(
                utility_payload,
                forbidden=_UTILITY_IMMUTABLE_KEYS,
                reason="Identificativi utility immutabili.",
                detail_prefix="Campi rifiutati",
            )
            self._validate_utility_payload_shape(utility_payload, for_create=False)
        testata_payload = {k: v for k, v in payload.items() if k != "utility"}

        # Leggiamo la testata esistente PRIMA di validare la coppia variazione
        # globale: serve al validator per sapere il listino_id corrente quando
        # il payload patch non lo include (es. patch solo su variazione globale).
        existing = self._get_contratto_or_raise(contratto_id, op="update_contratto")

        data = self._build_update_data_testata(testata_payload, existing=existing)

        # Almeno un campo, della testata o della scheda: `{"utility": {}}` da
        # solo non e' una modifica.
        self._v.require_campi_da_aggiornare(
            data, sotto_oggetti={"utility": utility_payload},
            context={"allowed_keys": sorted(UPDATE_KEYS_CONTRATTO)},
            log_to_db=False,
        )

        # Refactor modalita 2026-05-15 §3-bis-E: se il PATCH tocca la
        # variazione globale e il tipo e' PERCENTUALE, applichiamo il gate L2
        # sulla soglia configurata per (utente, categoria cliente, ...).
        # Per VALORE_FISSO il gate non e' applicabile (non e' una percentuale)
        # e viene saltato — decisione operativa §3-bis-E "decisione brief DB".
        self._check_limite_variazione_globale(
            existing=existing,
            data=data,
            auth_user_id=auth_user_id,
        )

        # ⛔ Con un CAMBIO DI CLIENTE la scheda del payload NON si applica: il
        #    trigger `trg_contratti_m50_fornitura_segue_cliente_upd` l'ha appena
        #    rifatta dal contatore nuovo, e quella del form e' del contatore di
        #    prima (R-BE-6/R-BE-7 di brief-db-indirizzi-documento-seguono-il-
        #    cliente, D-5 di Tid). Il dettaglio restituito porta la scheda del DB.
        cambia_cliente = coppia_cambiata(data, existing)
        with self._map_db_errors({"contratto_id": contratto_id}), transaction.atomic():
            if data:
                updated = self._repo.update_contratto(contratto_id, data)
                ErrorManager.require(
                    updated,
                    code=E_VENDITE_NOT_FOUND,
                    message="Contratto non trovato.",
                    context={"contratto_id": contratto_id},
                )
            if utility_payload is not None and not cambia_cliente:
                self._scrivi_utility_inline(contratto_id, existing, utility_payload)
        return self.get_contratto(contratto_id)

    # Scopo: la scheda di fornitura inline della PATCH di testata (payload gia'
    #        validato da `update_contratto`): la crea se il contratto non ce
    #        l'ha, altrimenti ne aggiorna i campi del form. La coppia (istanza,
    #        utility) della scheda e' quella della testata. Lo stato lo giudica
    #        il DB (lock «solo in bozza» dei satelliti, 409).
    def _scrivi_utility_inline(
        self, contratto_id: int, testata: dict[str, Any], corpo: dict[str, Any],
    ) -> None:
        existing = self._repo.get_utility(contratto_id)
        if existing is None:
            self._repo.create_utility(contratto_id, self._build_utility_data(
                corpo,
                istanza_utility_id=int(testata["istanza_utility_id"]),
                utility_id=int(testata["utility_id"]),
                for_create=True,
            ))
            return
        data = self._build_utility_data(
            corpo,
            istanza_utility_id=int(existing["istanza_utility_id"]),
            utility_id=int(existing["utility_id"]),
            for_create=False,
        )
        if data:
            self._repo.update_utility(int(existing["id"]), data)

    # =================================================================
    # Cambio stato
    # =================================================================

    # Scopo: Cambia lo stato del contratto al codice_interno richiesto, dal
    #        verbo che lo scrive (brief-modello-documento-vendita §11.6):
    #          - lo stato d'annullo (dal vocabolario) passa SEMPRE da
    #            `vendite.fn_annulla_contratto` (brief-db-annullo-documento-con-
    #            legami): con legami il DB rifiuta (E_DOC_ANNULLO_CON_LEGAMI,
    #            `confirm_and_retry`) finche' la richiesta non dichiara
    #            `legami_confermati`, letto da `get_legami`;
    #          - la cessazione (`STATO_CESSATO`) passa da
    #            `vendite.fn_cessa_contratto` con la sua data, e decide lui:
    #            senza data, data passata, oggi (data e stato) o futura (solo la
    #            data, `programmata`: lo stato lo chiude il job sugli scaduti);
    #          - ogni altro stato dal verbo di stato
    #            `vendite.fn_cambia_stato_contratto`, che giudica matrice,
    #            condizioni, lo stato che non c'e' e quello che il contratto ha
    #            gia'.
    #        ⛔ Fino al 2026-10-26 qui c'erano due copie Python della
    #        cessazione — la data obbligatoria e la scelta programmata/immediata
    #        — e la scrittura di `valido_al` prima dello stato (Y-3).
    # Ritorna: il dettaglio del contratto; per la cessazione anche
    #          `programmata` (lo stato non e' cambiato, lo chiudera' il job).
    def cambia_stato(
        self,
        contratto_id: int,
        *,
        codice_interno: str,
        valido_al: date | None = None,
        user: AbstractBaseUser | AnonymousUser | None = None,
        legami_confermati: Any = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        ErrorManager.require(
            isinstance(codice_interno, str) and codice_interno.strip() != "",
            code=E_VENDITE_VALIDATION,
            message="codice_interno dello stato obbligatorio.",
            context={"field": "codice_interno"},
        )
        codice_norm = codice_interno.strip()
        # ⛔ Lo stato di emissione (ATTIVO) NO (M-2): DRAFT -> ATTIVO passa da
        #    ApiContrattoEmetti (`/emetti/`, multipart), che orchestra in
        #    transaction.atomic() stato + genera_documento + allegati; da qui
        #    la transizione lascerebbe il contratto ATTIVO senza PDF. Quale
        #    stato sia l'emissione lo dice il vocabolario (BB
        #    `rifiuta_stato_di_emissione`, brief-modello-documento-vendita §8.7
        #    punto 4).
        rifiuta_stato_di_emissione(
            TESTATA_CONTRATTI, codice_norm, campo="codice_interno",
            validation_code=E_VENDITE_VALIDATION, function_name="contratti_service.cambia_stato",
        )
        # La data accompagna solo la cessazione: con un altro stato non ha un
        # verbo che la scriva, e scartarla in silenzio direbbe al client che e'
        # stata presa.
        ErrorManager.require(
            valido_al is None or codice_norm == STATO_CESSATO,
            code=E_VENDITE_VALIDATION,
            message="La data di cessazione si indica solo per cessare il contratto.",
            context={"field": "valido_al", "codice_interno": codice_norm},
        )
        # Esistenza col lettore leggero: qui serve solo che il contratto ci sia.
        self._get_contratto_or_raise(contratto_id, op="cambia_stato", getter=self._repo.get_stato_codice)

        contesto = {"contratto_id": contratto_id, "codice_interno": codice_norm}
        # L'annullo (lo stato d'annullo del vocabolario) dal suo verbo.
        if e_stato_di_annullo(TESTATA_CONTRATTI, codice_norm):
            confermati = dichiarazione_legami(
                legami_confermati, validation_code=E_VENDITE_VALIDATION,
                function_name="contratti_service.cambia_stato",
            )
            with self._map_db_errors(contesto, fallback_message="Violazione vincolo DB su annullo contratto."):
                self._repo.annulla(contratto_id, confermati)
            return self.get_contratto(contratto_id)

        if codice_norm == STATO_CESSATO:
            with self._map_db_errors(contesto, fallback_message="Violazione vincolo DB su cessazione contratto."):
                esito = self._repo.cessa(contratto_id, valido_al)
            return {**self.get_contratto(contratto_id), "programmata": bool(esito["programmata"])}

        with self._map_db_errors(contesto, fallback_message="Violazione vincolo DB su cambio stato."):
            self._repo.cambia_stato(contratto_id, codice_norm)
        return self.get_contratto(contratto_id)

    # Scopo: I legami del contratto per la finestra di conferma dell'annullo
    #        (BB `legami_del_documento`): offerta d'origine, righe di commessa
    #        da emettere. Prima la testata: il lettore del DB non applica il
    #        perimetro.
    def get_legami(self, contratto_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._get_contratto_or_raise(
            contratto_id, op="get_legami", getter=self._repo.get_stato_codice,
        )
        return legami_del_documento(SORGENTE_CONTRATTO, contratto_id)

    # Scopo: DRAFT -> ATTIVO. Solo la transizione di stato: la view multipart
    #        ApiContrattoEmetti incapsula questa chiamata insieme a
    #        DocumentGenerationService.genera_documento(allegati=...) in
    #        un'unica transaction.atomic() esterna, garantendo che ATTIVO
    #        implichi sempre l'esistenza del documento generato (invariante di
    #        dominio). Mirror del pattern offerta/preventivo emetti (refactor
    #        2026-05-28). Bypassa il guard di cambia_stato su ATTIVO via
    #        accesso diretto al repository.
    def emetti(self, contratto_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        # ⭐ La sovrapposizione con un contratto vincolante la dice il DB, in un
        #    posto solo (2026-10-19, `script.fn_check_contratto_sovrapposto`):
        #    la capability spegne «Attiva» col motivo che nomina il contratto in
        #    conflitto, e il guard della transizione rifiuta con
        #    `E_CONTRATTO_OVERLAP_ESISTENTE`, che passa com'e' (il codice del
        #    catalogo vince in `_map_db_errors`). Fino ad allora qui c'era una
        #    copia Python della regola, con un testo suo, che scattava solo alla
        #    conferma della stampa: «Attiva» restava acceso (collaudo di Tid).
        #    L'EXCLUDE `ex_contratti_no_overlap` resta la difesa dura.
        # Lo stato di emissione dal vocabolario (V-2, brief-modello-documento-
        # vendita §8.11 B-4), scritto dal verbo di stato (§11.6): permesso
        # dalla riga del passaggio, il contratto che non c'e', un secondo
        # «Emetti» (E_DOC_GIA_NELLO_STATO) li giudica il DB.
        stato = stato_di_emissione(TESTATA_CONTRATTI, function_name="contratti_service.emetti")
        with self._map_db_errors(
            {"contratto_id": contratto_id, "codice_interno": stato.codice},
            fallback_message="Violazione vincolo DB su attivazione contratto.",
        ):
            self._repo.cambia_stato(contratto_id, stato.codice)
        return self.get_contratto(contratto_id)

    # =================================================================
    # Contesto pricing (banner FE)
    # =================================================================

    # Scopo: Restituisce il contesto pricing applicato al contratto (forma,
    #        listino + versione fissata/corrente, variazione globale,
    #        categoria cliente). Mutuato dal pattern preventivi
    #        `get_contesto_pricing` per la simmetria UI: l'header del drawer
    #        contratto mostra un badge con questi dati per audit visivo del
    #        path resolver applicato. Lettura puramente informativa.
    def get_contesto_pricing(
        self, contratto_id: int,
    ) -> dict[str, Any] | None:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        # ⛔ Prima la testata: un contratto inesistente o fuori perimetro e' il
        #    404 del dominio, non `200 {}` (2026-10-20, l'ordine di lettura dei
        #    satelliti di api.md §«Scope emittente»).
        self._get_contratto_or_raise(
            contratto_id, op="get_contesto_pricing", getter=self._repo.get_stato_codice,
        )
        return self._repo.resolve_contesto_pricing_contratto(contratto_id)

    # =================================================================
    # Righe contratto - la lista operativa
    # =================================================================

    # Scopo: una PAGINA delle righe operative del contratto, per la lista
    #        configurabile `vendite.contratto_righe` (lotto D del
    #        brief-db-liste-righe-documento): ricerca dal catalogo, ordinamento
    #        dalla whitelist, codice articolo quando nessuno chiede altro.
    #        Ritorna `(righe, totale)`.
    # ⭐ «Leggi prima la testata»: un contratto fuori perimetro e' un 404, non
    #    una lista vuota (la funzione su un id che non vede risponde zero righe).
    # ⭐ Una sorgente per le due forme: senza listino la funzione risponde le
    #    sole aggiunte, quindi qui non si decide niente per forma.
    def list_righe_pagina(
        self, contratto_id: int, **opzioni: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        return pagina_dopo_testata(
            lambda: self._get_contratto_or_raise(
                contratto_id, op="list_righe_pagina", getter=self._repo.get_stato_codice,
            ),
            ContrattoRigheListaRepository().list_righe_pagina, contratto_id, **opzioni,
        )

    # =================================================================
    # Lettura della testata (guard di esistenza)
    # =================================================================

    # Scopo: Carica la testata contratto o solleva E_VENDITE_NOT_FOUND (BB core
    #        `testata_o_not_found`: qui solo codice e messaggio del dominio).
    #        `getter` ammette il lettore leggero `get_stato_codice`, dove al
    #        chiamante basta lo stato.
    def _get_contratto_or_raise(
        self, contratto_id: int, *, op: str,
        getter: Callable[[int], Any] | None = None,
    ) -> Any:
        return testata_o_not_found(
            getter or self._repo.get_contratto, contratto_id,
            code=E_VENDITE_NOT_FOUND, message="Contratto non trovato.",
            id_name="contratto_id", function_name=f"contratti_service.{op}",
        )

    # Scopo: «Le righe si toccano solo in bozza» sul contratto, col codice e la
    #        frase del BB a DB `trgfn_doc_righe_lock_fuori_bozza` (montato su
    #        `contratti_righe`): `E_RIGA_DOC_NON_BOZZA`, etichetta
    #        «Contratto <numero>». Pre-check prima di scrivere, come in
    #        ddt/ordini/preventivi (BB `richiedi_righe_in_bozza`).
    def _richiedi_righe_in_bozza(
        self, contratto_id: int, *, verbo: Verbo, function_name: str,
    ) -> None:
        contratto = self._get_contratto_or_raise(contratto_id, op=function_name)
        richiedi_righe_in_bozza(
            contratto, documento=SORGENTE_CONTRATTO, documento_id=contratto_id, verbo=verbo,
            function_name=f"contratti_service.{function_name}",
        )

    # Scopo: Guard delle righe in bozza sul contratto dell'URL, poi la riga:
    #        esiste ED e' di quel contratto (altrimenti E_VENDITE_NOT_FOUND).
    #        Stesso ordine dei gemelli (ordini, DDT, resi, preventivi):
    #        testata -> bozza -> riga. Restituisce la riga, che `update_riga`
    #        riusa.
    # ⛔ L'UPDATE e il DELETE vanno per il solo `riga_id`: prima la bozza si
    #    verificava sul contratto DELLA RIGA, e una riga di un altro contratto
    #    in bozza passava con l'URL di questo.
    def _riga_del_contratto_in_bozza(
        self, contratto_id: int, riga_id: int, *, verbo: Verbo, function_name: str,
    ) -> dict[str, Any]:
        self._richiedi_righe_in_bozza(contratto_id, verbo=verbo, function_name=function_name)
        return riga_del_padre_o_not_found(
            self._repo.get_riga, riga_id, padre_id=contratto_id, chiave_padre="contratto_id",
            code=E_VENDITE_NOT_FOUND, message="Riga contratto non trovata.",
            function_name=f"contratti_service.{function_name}",
        )

    # =================================================================
    # Righe contratto
    # =================================================================

    # Scopo: Aggiunge una riga al contratto. I trigger DB del refactor
    #        2026-05-15 governano la coerenza dell'eccezione
    #        (tipo_eccezione vs prezzo_unitario, AGGIUNTA non duplicabile su
    #        articoli del listino, lock post-attivazione): traduzione P0001
    #        via `_KNOWN_DB_ERROR_MARKERS`.
    def create_riga(
        self, contratto_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._richiedi_righe_in_bozza(contratto_id, verbo="aggiungere", function_name="create_riga")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_CREATE,
            reason="contratto_id arriva dall'URL, non dal payload.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=CREATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        # `componenti_overrides` non e' campo di `contratti_righe`: estraiamo
        # PRIMA di `_build_data_riga` cosi' non finisce nell'INSERT.
        componenti_overrides_raw = payload.pop("componenti_overrides", None)
        componenti_overrides = normalize_componenti_overrides(
            componenti_overrides_raw,
            function_name="contratti_service.create_riga",
            error_code=E_VENDITE_VALIDATION,
        )
        # Gate L1 sugli override prezzo componenti (allineamento a preventivi,
        # 2026-06-01): contratti non lo applicava → un operatore senza azione
        # `prezzo_override_manuale` poteva scrivere prezzi manuali sui figli
        # BoM. BB condiviso, enforcement solo BE (azione di processo Django,
        # nessun safety-net DB possibile).
        validate_componenti_overrides_authorization(
            {"componenti_overrides": componenti_overrides_raw},
            auth_user_id,
            function_name="contratti_service.create_riga",
        )
        # Flag opt-in workflow L3 (richiesta approvazione). Estratto qui per
        # non finire nel data_riga.
        richiesta_approvazione = self._v.optional_bool(payload, "richiesta_approvazione") is True
        payload.pop("richiesta_approvazione", None)

        data = self._build_data_riga(payload, for_create=True)

        articolo_id = payload.get("articolo_id")
        tipo_eccezione = data.get("tipo_eccezione")

        # Gate L1+L2+L3: solo OVERRIDE/AGGIUNTA. Helper riusato da update_riga.
        # `testata_gate` riusato sotto per il ramo composito (1 round-trip
        # DB risparmiato).
        pratica_id_l3: int | None = None
        testata_gate: dict[str, Any] | None = None
        # Transazione atomica: gate L3 (crea la pratica di approvazione) +
        # create_riga + (se composito) auto-init componenti.
        # Fix analisi-fix-transazioni #7 (Classe B): il gate era invocato PRIMA
        # dell'atomic → la pratica di approvazione creata dal gate restava orfana
        # se la create_riga rollava. Ora il gate vive DENTRO l'atomic (il suo
        # atomic interno diventa un savepoint), come gia' in preventivi_service
        # (modello corretto). Nota gate-vs-fn-DB: il gate fa permission-check
        # L1/L2 in Python (azioni di processo), quindi resta orchestrazione BE,
        # non promuovibile a funzione madre DB. Senza atomic, inoltre, una riga
        # padre composito potrebbe restare senza componenti se la fn DB
        # `fn_contratto_riga_componenti_init` solleva (es. BoM scaduta).
        # Ordine dei CM: mapper ESTERNO, atomic INTERNO (allineato a offerte).
        # Su errore trigger (DatabaseError) l'atomic rolla PRIMA, poi il mapper
        # traduce + logga su connessione pulita — altrimenti il log-to-db girerebbe
        # sulla transazione avvelenata e verrebbe perso (review 2026-07-08).
        with self._map_db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su riga contratto.",
        ), transaction.atomic():
            if tipo_eccezione in _TIPI_ECCEZIONE_CON_GATE:
                pratica_id_l3, testata_gate = self._apply_pricing_gate_riga(
                    contratto_id=contratto_id,
                    articolo_id=articolo_id,
                    uom_id=data.get("uom_operativa_id"),
                    data=data,
                    auth_user_id=auth_user_id,
                    richiesta_approvazione=richiesta_approvazione,
                    riga_id_for_link=None,  # riga_id non noto qui
                    function_name="contratti_service.create_riga",
                )
            new_id = self._repo.create_riga(contratto_id, data)

            # Link riga<->pratica L3: post-create_riga, riga_id ora noto.
            # link_riga_a_pratica aggiunge `riga_contratto_id` al meta della
            # pratica per permettere all'approver di risalire dalla coda
            # (UI ApprovazioniPrezzoListView routing su /righe-contratto/...).
            if pratica_id_l3 is not None:
                from apps.vendite.services.approvazioni_prezzo_service import (
                    link_riga_a_pratica,
                )
                link_riga_a_pratica(
                    pratica_id=pratica_id_l3,
                    riga_id=new_id,
                    sorgente=META_SORGENTE_CONTRATTO,
                )

            # ESCLUSIONE escluso dall'auto-init: un articolo escluso non ha
            # prezzo (CHECK chk_contrighe_prezzo_per_tipo_eccezione impone
            # prezzo_unitario NULL) ne' senso di negoziare i suoi componenti.
            # Inizializzarli farebbe scattare trgfn_componenti_ricalcola_padre
            # che scriverebbe SUM(figli) sul padre ESCLUSIONE -> violazione.
            if (
                articolo_id
                and tipo_eccezione != "ESCLUSIONE"
                and self._repo.is_articolo_composito(str(articolo_id))
            ):
                # Riusa la testata letta dal gate (sopra) se disponibile;
                # altrimenti (gate skip per ESCLUSIONE) la carica adesso.
                testata = testata_gate or self._repo.get_contratto(contratto_id)
                assert testata is not None
                emittente_sr_id = self._resolve_emittente_sr_id_for_contratto(
                    testata, auth_user_id,
                )
                valido_dal_raw = testata.get("valido_dal")
                # Refactor 2026-05-19: stop allo skip silente. Se mancano
                # emittente o valido_dal, sollevare errore parlante invece
                # di lasciare un padre composito orfano in DB (la
                # transaction.atomic sopra ne fa il rollback). L'utente vede
                # il vero motivo e sa come rimediare. Pattern simmetrico
                # alla logica preventivi composito (gestisci_riga).
                ErrorManager.require(
                    emittente_sr_id is not None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        "Inserimento articolo composito non possibile: "
                        "emittente fiscale non risolvibile per il contratto."
                    ),
                    context={
                        "contratto_id": contratto_id,
                        "articolo_id": articolo_id,
                        "motivo": "emittente_non_risolvibile",
                    },
                )
                ErrorManager.require(
                    valido_dal_raw is not None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        "Inserimento articolo composito non possibile: "
                        "valorizza prima `valido_dal` sulla testata del contratto."
                    ),
                    context={
                        "contratto_id": contratto_id,
                        "articolo_id": articolo_id,
                        "motivo": "valido_dal_null",
                    },
                )
                data_riferimento = (
                    valido_dal_raw if isinstance(valido_dal_raw, date)
                    else date.fromisoformat(str(valido_dal_raw))
                )
                assert emittente_sr_id is not None  # garantito dal require sopra
                self._repo.init_componenti_riga(
                    riga_id=new_id,
                    emittente_soggetto_ruolo_id=emittente_sr_id,
                    data_riferimento=data_riferimento,
                    componenti_overrides=componenti_overrides,
                )

        result = self._repo.get_riga(new_id)
        assert result is not None
        return result

    # Scopo: Risolve emittente_soggetto_ruolo_id per le operazioni componenti
    # del contratto. Thin wrapper su `resolve_emittente_sr_id_for_testata`
    # (helper Fase H) per non duplicare la logica di lookup + fallback.
    def _resolve_emittente_sr_id_for_contratto(
        self,
        testata: dict[str, Any],
        auth_user_id: int | None,
    ) -> int | None:
        return resolve_emittente_sr_id_for_testata(
            testata, auth_user_id,
            repo_get_sr_id_by_fiscale_id=self._repo.get_emittente_sr_id_by_fiscale_id,
        )

    # Scopo: Helper unificato per il gate L1+L2+L3 su righe contratto.
    #        Riusato da create_riga e update_riga (refactor 2026-05-19,
    #        rimuove ~30 righe duplicate). Pipeline:
    #          1) get_contratto + invoca BB `resolve_or_check_override_prezzo_riga_contratto`
    #          2) normalizza `data["prezzo_unitario"]` col valore ritornato
    #          3) merge `data["meta"]` con `prezzo_meta` (con fallback opzionale
    #             al meta della riga esistente — case update_riga)
    #          4) se workflow L3 (`richiesta_approvazione_pending`): orchestra
    #             pratica + popola `data["stato_approvazione_prezzo"]` +
    #             `data["pratica_approvazione_prezzo_id"]`. Per create il
    #             `riga_id_for_link=None` (link post-INSERT); per update il
    #             riga_id e' gia' noto.
    #        Ritorna `(pratica_id_l3 | None, testata_gate)`: la testata viene
    #        restituita perche' il caller create_riga la riusa nel ramo
    #        composito evitando un double-fetch.
    def _apply_pricing_gate_riga(
        self,
        *,
        contratto_id: int,
        articolo_id: Any,
        uom_id: Any,
        data: dict[str, Any],
        auth_user_id: int | None,
        richiesta_approvazione: bool,
        riga_id_for_link: int | None,
        function_name: str,
        fallback_meta: dict[str, Any] | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        testata_gate = self._repo.get_contratto(contratto_id)
        assert testata_gate is not None
        prezzo_finale, prezzo_meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata_gate,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=data.get("prezzo_unitario"),
            auth_user_id=auth_user_id,
            function_name=function_name,
            richiesta_approvazione=richiesta_approvazione,
        )
        # Override prezzo col valore normalizzato dal BB (auto-fill se
        # payload era None + resolver ha prezzo, oppure prezzo manuale
        # confermato dall'L1).
        if prezzo_finale is not None:
            data["prezzo_unitario"] = prezzo_finale
        # Merge meta riga: il BB ritorna `prezzo_meta` con audit pricing.
        # Va mergiato sul `meta` corrente del data_riga (priorita': payload
        # > fallback existing meta) senza sovrascrivere chiavi gia' presenti.
        # Coerce JSONB→dict defensivo (fix 2026-05-20): per certi articoli
        # psycopg ritorna `meta` JSONB della riga esistente come stringa JSON
        # invece di dict — `dict(str)` solleverebbe TypeError "dictionary
        # update sequence". Stesso pattern coerce gia' applicato in altri
        # repo (_decode_jsonb in commesse_repository, coerceJsonbToObject FE).
        if prezzo_meta:
            base_meta = data.get("meta") or fallback_meta or {}
            if isinstance(base_meta, str):
                try:
                    parsed = json.loads(base_meta)
                    base_meta = parsed if isinstance(parsed, dict) else {}
                except (json.JSONDecodeError, ValueError):
                    base_meta = {}
            merged_meta = dict(base_meta)
            merged_meta.update(prezzo_meta)
            data["meta"] = merged_meta
        # Workflow L3: il BB ha segnalato violazione + richiesta. Crea pratica
        # PRIMA dell'INSERT/UPDATE riga per ottenere la FK; il link riga<->pratica
        # avviene nel caller (post-INSERT per create, inline per update).
        pratica_id_l3: int | None = None
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request_contratto(
                contratto_id=contratto_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id_for_link,
            )
            data["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            data["pratica_approvazione_prezzo_id"] = pratica_id_l3
        return pratica_id_l3, testata_gate

    # Scopo: Aggiorna una riga contratto. articolo_id e tipo_eccezione
    #        immutabili (refactor 2026-05-15: per cambiare tipo serve
    #        DELETE + INSERT, meno zone grigie di un cambio di semantica
    #        in-place). Gate L1+L2+L3 attivo quando il PATCH tocca
    #        `prezzo_unitario` su una riga OVERRIDE/AGGIUNTA (refactor
    #        2026-05-19 BE porting gate riga contratti).
    def update_riga(
        self, contratto_id: int, riga_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        existing_riga = self._riga_del_contratto_in_bozza(
            contratto_id, riga_id, verbo="modificare", function_name="update_riga",
        )
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_UPDATE,
            reason="articolo_id, contratto_id e tipo_eccezione immutabili: per rimpiazzarli eliminare la riga e crearne una nuova.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=UPDATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        # Flag opt-in L3 estratto pre-build_data (non e' una colonna riga).
        richiesta_approvazione = self._v.optional_bool(payload, "richiesta_approvazione") is True
        payload.pop("richiesta_approvazione", None)
        data = self._build_data_riga(payload, for_create=False)

        self._v.require_campi_da_aggiornare(
            data,
            message="Nessun campo aggiornabile presente nel payload riga.",
            context={"allowed_keys": sorted(UPDATE_KEYS_RIGA)},
            log_to_db=False,
        )

        # Coerenza prezzo_unitario / tipo_eccezione (refactor 2026-05-15):
        # se il PATCH tocca prezzo_unitario, valida contro il tipo_eccezione
        # della riga esistente (immutabile). Pre-validation parlante invece
        # del fallback E_DATABASE sul CHECK DB chk_contrighe_prezzo_per_tipo_eccezione.
        # Un'ESCLUSIONE non entra qui: non si modifica affatto, e lo dice il
        # guard DB `_a05_` (E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE), che parla
        # prima del CHECK sul prezzo — brief-db-contratto-esclusione-non-modificabile.
        # `existing_riga` (letta dal guard di appartenenza in testa) serve
        # anche al gate L1+L2+L3 sotto.
        tipo_existing: str | None = None
        if "prezzo_unitario" in data:
            tipo_existing = existing_riga.get("tipo_eccezione")
            nuovo_prezzo = data["prezzo_unitario"]
            if tipo_existing in ("OVERRIDE", "AGGIUNTA"):
                ErrorManager.require(
                    nuovo_prezzo is not None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        f"{tipo_existing}: prezzo_unitario obbligatorio. "
                        f"Per escludere l'articolo, eliminare la riga e "
                        f"crearne una nuova come ESCLUSIONE."
                    ),
                    context={"riga_id": riga_id, "tipo_eccezione": tipo_existing},
                )

        # Gate L1+L2+L3 (refactor 2026-05-19): scatta solo se il PATCH tocca
        # `prezzo_unitario` su una riga OVERRIDE o AGGIUNTA. Un'ESCLUSIONE
        # la rifiuta il guard DB nell'UPDATE qui sotto: nessun gate.
        # Riusiamo `existing_riga` per evitare double-fetch.
        # riga_id noto subito: link inline alla pratica (no post-INSERT).
        # Fix analisi-fix-transazioni #6 (Classe B): gate L3 (crea + linka inline
        # la pratica di approvazione) e UPDATE riga in UN solo transaction.atomic().
        # Prima il gate era fuori da qualsiasi atomic — l'UPDATE stava solo in
        # `_map_db_errors`, che NON e' un atomic — quindi la pratica creata dal gate
        # restava orfana se l'UPDATE riga falliva. Il gate fa permission-check
        # L1/L2 in Python (azioni di processo): resta orchestrazione BE, non
        # promuovibile a funzione madre DB.
        # Ordine dei CM: mapper ESTERNO, atomic INTERNO (vedi create_riga): il
        # rollback su errore trigger avviene prima del log-to-db del mapper.
        with self._map_db_errors(
            {"riga_id": riga_id},
            fallback_message="Violazione vincolo DB su riga contratto.",
        ), transaction.atomic():
            if (
                "prezzo_unitario" in data
                and tipo_existing in _TIPI_ECCEZIONE_CON_GATE
            ):
                self._apply_pricing_gate_riga(
                    contratto_id=int(existing_riga["contratto_id"]),
                    articolo_id=existing_riga.get("articolo_id"),
                    uom_id=(
                        data.get("uom_operativa_id")
                        if "uom_operativa_id" in data
                        else existing_riga.get("uom_operativa_id")
                    ),
                    data=data,
                    auth_user_id=auth_user_id,
                    richiesta_approvazione=richiesta_approvazione,
                    riga_id_for_link=riga_id,
                    function_name="contratti_service.update_riga",
                    fallback_meta=existing_riga.get("meta"),
                )
            updated = self._repo.update_riga(riga_id, data)

        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            context={"riga_id": riga_id},
        )
        result = self._repo.get_riga(riga_id)
        assert result is not None
        return result

    # Scopo: Elimina una riga contratto (hard delete). Eventuali note
    #        collegate bloccano la cancellazione via trigger DB.
    def delete_riga(self, contratto_id: int, riga_id: int) -> None:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._riga_del_contratto_in_bozza(
            contratto_id, riga_id, verbo="togliere", function_name="delete_riga",
        )
        with self._map_db_errors(
            {"riga_id": riga_id},
            fallback_message="Impossibile eliminare la riga (dipendenze).",
        ):
            deleted = self._repo.delete_riga(riga_id)
        ErrorManager.require(
            deleted,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            context={"riga_id": riga_id},
        )

    # =================================================================
    # Componenti BoM riga contratto (modello unificato 2026-05-13)
    # =================================================================
    # Specchio simmetrico del pattern preventivi. I componenti vivono in
    # `vendite.contratti_righe_componenti`; l'init e' invocato automaticamente
    # da `create_riga` quando l'articolo e' composito. Helper di
    # normalizzazione overrides + resolve emittente in
    # `_componenti_service_helpers.py` (Fase H BB).

    # Scopo: Helper privato condiviso da update/delete componente. Esegue
    # guard + scope check (riga_id URL + contratto_id) + stato contratto
    # modificabile in UN'unica query JOIN componente→riga→contratto (Fix #2
    # refactor-componenti.md). Solleva `E_VENDITE_NOT_FOUND` su componente
    # inesistente o fuori scope, `E_RIGA_DOC_NON_BOZZA` (BB
    # `richiedi_righe_in_bozza`, col `verbo` del chiamante) se il contratto
    # non e' in bozza.
    def _load_componente_for_modification(
        self,
        *,
        contratto_id: int,
        riga_id: int,
        componente_id: int,
        verbo: Verbo,
        function_name: str,
    ) -> None:
        scope = self._repo.load_componente_with_scope(componente_id)
        ErrorManager.require(
            scope is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=f"componente_id={componente_id}",
            function_name=function_name,
        )
        assert scope is not None

        # Anti-tampering URL: riga_id dalla rotta deve matchare riga reale.
        riga_reale = int(scope["riga_contratto_id"])
        ErrorManager.require(
            riga_reale == riga_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=(
                f"componente_id={componente_id} non appartiene a "
                f"riga_id={riga_id} (riga reale={riga_reale})"
            ),
            function_name=function_name,
        )

        # Scope contratto: defense-in-depth contro URL forgiati.
        ErrorManager.require(
            int(scope["contratto_id"]) == contratto_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=(
                f"componente_id={componente_id} fuori scope "
                f"contratto_id={contratto_id}"
            ),
            function_name=function_name,
        )

        # Guard stato modificabile: contratti_righe_componenti seguono la
        # stessa policy delle righe padre (solo in bozza). Lo stato e il
        # numero sono gia' nella tupla del JOIN — nessun round-trip extra.
        richiedi_righe_in_bozza(
            scope, documento=SORGENTE_CONTRATTO, documento_id=contratto_id, verbo=verbo,
            function_name=function_name,
        )

    # Scopo: Le combinazioni (tipo_erogazione, fonte_quantita_attesa) che una
    #        riga con questo articolo puo' avere sul contratto, col default che
    #        erediterebbe in testa: il form delle righe le propone e
    #        preseleziona il default (brief-db-offerta-emissione-ed-erogazione
    #        B-R4). Le dice il DB (`vendite.fn_documento_riga_erogazioni`), la
    #        stessa sede che leggono l'eredita' e il guard del perimetro.
    #        Prima la testata: un contratto che non si vede e' un 404, non una
    #        lista vuota. Lista vuota = l'articolo ha una tipologia che la
    #        utility del contratto non prevede. Gemello di
    #        `OfferteService.list_erogazioni_riga`.
    def list_erogazioni_riga(
        self, contratto_id: int, articolo_id: Any,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        articolo = self._v.require_uuid({"articolo_id": articolo_id}, "articolo_id")
        self._get_contratto_or_raise(
            contratto_id, op="list_erogazioni_riga", getter=self._repo.get_stato_codice,
        )
        return list_erogazioni_riga(SORGENTE_CONTRATTO, contratto_id, articolo)

    # Scopo: Preview componenti BoM per drawer riga contratto (ComponentiDialog
    # FE). Read-only: il FE invoca PRIMA del save di una riga composita per
    # ottenere prezzi suggeriti dei componenti. Per ogni componente:
    # `prezzo_suggerito` + `origine_prezzo`, oppure NULL +
    # `resolver_error_reason` se il listino manca per quel componente.
    # `auth_user_id`: utente loggato. L'emittente_soggetto_ruolo_id viene
    # risolto internamente (precedenza emittente esplicito sulla testata >
    # operatore loggato). Pattern simmetrico preventivi: la view non deve
    # accedere a membri privati del service per risolvere l'emittente.
    # Solleva `E_VENDITE_NOT_FOUND` se contratto inesistente, `E_VENDITE_VALIDATION`
    # se data/utility/emittente non risolvibili.
    def preview_componenti_riga(
        self,
        contratto_id: int,
        *,
        articolo_id: str,
        uom_operativa_id: int | None,
        quantita: Any,
        auth_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        ctx = _load_contratto_context_for_pricing(
            contratto_id, auth_user_id,
            function_name="contratti_service.preview_componenti_riga",
            repo=self._repo,
        )

        return self._repo.preview_componenti_riga(
            articolo_id=str(articolo_id),
            uom_id=uom_operativa_id,
            quantita_padre=quantita,
            data_riferimento=ctx["data_riferimento"],
            ba_id=ctx["ba_id"],
            utility_id=ctx["utility_id"],
            emittente_soggetto_ruolo_id=ctx["emittente_sr_id"],
        )

    # Scopo: Lista componenti BoM di una riga padre composita contratto.
    # Guard di esistenza: la riga deve appartenere al contratto richiesto.
    # `solo_attivi=True` (default backcompat): solo componenti attivi.
    # `solo_attivi=False` (EDIT panel): include opzionali disattivati.
    def list_componenti_riga(
        self,
        contratto_id: int, riga_id: int,
        *, solo_attivi: bool = True,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        riga_del_padre_o_not_found(
            self._repo.get_riga, riga_id, padre_id=contratto_id, chiave_padre="contratto_id",
            code=E_VENDITE_NOT_FOUND, message="Riga contratto non trovata.",
            function_name="contratti_service.list_componenti_riga",
        )
        return self._repo.list_componenti_riga(riga_id, solo_attivi=solo_attivi)

    # Scopo: Modifica componente riga contratto esistente. Guard stato
    # contratto modificabile + esistenza componente + match URL
    # anti-tampering. Whitelist campi via repo.
    def update_componente_riga(
        self,
        contratto_id: int, riga_id: int, componente_id: int,
        payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._load_componente_for_modification(
            contratto_id=contratto_id, riga_id=riga_id,
            componente_id=componente_id, verbo="modificare",
            function_name="contratti_service.update_componente_riga",
        )
        # ⛔ Contratto dell'OPERATORE (BB unico per i cinque documenti), non
        #    la whitelist del repository: fino al 2026-09-26 qui si validava
        #    contro `COMPONENTE_UPDATE_ALLOWED`, che contiene
        #    `stato_approvazione_prezzo` — un operatore poteva approvarsi da
        #    solo un prezzo L3 PENDING. `origine_prezzo` la deriva il server.
        payload = dati_patch_componente(
            payload, auth_user_id=auth_user_id,
            function_name="contratti_service.update_componente_riga",
        )
        with self._map_db_errors(
            {"componente_id": componente_id, "riga_id": riga_id},
            fallback_message="Violazione vincolo DB su componente riga contratto.",
        ):
            self._repo.update_componente(componente_id, **payload)
        return {"status": "ok", "componente_id": componente_id}

    # Scopo: Soft delete componente riga contratto (`attivo=FALSE`). Guard
    # stato + esistenza + match URL anti-tampering. Il trigger DB di
    # ricalcolo padre esclude i componenti inattivi dalla SUM.
    def delete_componente_riga(
        self,
        contratto_id: int, riga_id: int, componente_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._load_componente_for_modification(
            contratto_id=contratto_id, riga_id=riga_id,
            componente_id=componente_id, verbo="togliere",
            function_name="contratti_service.delete_componente_riga",
        )
        with self._map_db_errors(
            {"componente_id": componente_id, "riga_id": riga_id},
            fallback_message="Impossibile eliminare il componente (dipendenze).",
        ):
            deleted = self._repo.delete_componente(componente_id)
        return {
            "status": "ok",
            "componente_id": componente_id,
            "deleted": deleted,
        }

    # =================================================================
    # Utility 1:1
    # =================================================================

    # Scopo: Crea la riga utility associata al contratto. Richiede che
    #        istanza_utility_id / utility_id coincidano con quelli della
    #        testata (controllo anticipato lato service).
    #        ⭐ In quale stato la fornitura si cambia lo dice il DB: il lock
    #        «solo in bozza» dei satelliti (`E_DOC_DATI_COLLEGATI_NON_BOZZA`,
    #        409) e la capability `can_edit_utility`. Fino al 2026-10-11 qui
    #        c'era `_assert_contratto_draft`, la seconda copia di quella regola
    #        (brief-db-testata-dopo-emissione §11, R-BE-6).
    def create_utility(self, contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        testata = self._get_contratto_or_raise(contratto_id, op="create_utility")

        self._validate_utility_payload_shape(payload, for_create=True)
        data = self._build_utility_data(
            payload,
            istanza_utility_id=int(testata["istanza_utility_id"]),
            utility_id=int(testata["utility_id"]),
            for_create=True,
        )

        with self._map_db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su utility contratto.",
        ):
            self._repo.create_utility(contratto_id, data)

        result = self._repo.get_utility(contratto_id)
        assert result is not None
        return result

    # Scopo: Aggiorna la riga utility (1:1 con il contratto). I campi
    #        identificativi contratto/istanza/utility sono immutabili. Lo
    #        stato lo giudica il DB (vedi `create_utility`).
    def update_utility(self, contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._get_contratto_or_raise(contratto_id, op="update_utility", getter=self._repo.get_stato_codice)
        existing = self._repo.get_utility(contratto_id)
        ErrorManager.require(
            existing is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Riga utility non trovata per il contratto.",
            context={"contratto_id": contratto_id},
        )
        assert existing is not None

        self._v.reject_keys(
            payload,
            forbidden=_UTILITY_IMMUTABLE_KEYS,
            reason="Identificativi utility immutabili.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=UTILITY_UPDATE_KEYS, message=_MESSAGE_UTILITY)
        self._validate_utility_payload_shape(payload, for_create=False)
        data = self._build_utility_data(
            payload,
            istanza_utility_id=int(existing["istanza_utility_id"]),
            utility_id=int(existing["utility_id"]),
            for_create=False,
        )
        self._v.require_campi_da_aggiornare(
            data,
            message="Nessun campo aggiornabile presente nel payload utility.",
            context={"allowed_keys": sorted(UTILITY_UPDATE_KEYS)},
            log_to_db=False,
        )

        with self._map_db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su utility contratto.",
        ):
            updated = self._repo.update_utility(int(existing["id"]), data)

        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Riga utility non trovata.",
            context={"contratto_id": contratto_id},
        )
        result = self._repo.get_utility(contratto_id)
        assert result is not None
        return result

    # =================================================================
    # Helpers privati — payload testata
    # =================================================================

    # Scopo: Compone il dict di create testata validando campi e coerenza
    #        della coppia variazione globale (tipo+valore entrambi NULL o
    #        entrambi NOT NULL).
    def _build_create_data_testata(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {
            "billing_account_id": self._v.require_positive_int(
                payload, "billing_account_id", message=_MESSAGE,
            ),
            "istanza_utility_id": self._v.require_positive_int(
                payload, "istanza_utility_id", message=_MESSAGE,
            ),
            "utility_id": self._v.require_positive_int(
                payload, "utility_id", message=_MESSAGE,
            ),
            "valido_dal": self._v.require_date(payload, "valido_dal", message=_MESSAGE),
        }
        # emittente_fiscale_id opzionale: se presente passa al DB e il trigger
        # `script.trgfn_default_emittente_fiscale` lo lascia (skip su IS NOT NULL);
        # se assente il trigger lo deriva via `fn_resolve_emittente_for_user`
        # dalla GUC `app.current_user_id`. Il guard `guard_emittente_ba`
        # rifiuta in ogni caso divergenze BA<->EF.
        self._apply_optional_positive_int(
            payload, data, "emittente_fiscale_id", message=_MESSAGE,
        )
        # valido_al e ambito opzionali in create (ambito ha default DB
        # 'COMMODITY', valido_al puo' essere aperto).
        if "valido_al" in payload and payload["valido_al"] is not None:
            valido_al = self._v.require_date(payload, "valido_al", message=_MESSAGE)
            data["valido_al"] = valido_al
        if "ambito" in payload:
            data["ambito"] = self._extract_ambito(payload)
        self._apply_optional_positive_int(
            payload, data, "parent_contratto_id", message=_MESSAGE,
        )
        if "data" in payload:
            data["data"] = self._v.require_date(payload, "data", message=_MESSAGE)
        self._apply_optional_positive_int(
            payload, data, "listino_id", message=_MESSAGE,
        )
        self._apply_variazione_globale(payload, data)
        self._validate_variazione_globale_coppia_coerente(data, existing=None)
        # Snapshot categoria cliente: opzionale, nullable. Se fornito
        # congela il valore scelto dall'operatore; se omesso il trigger
        # DB lo popola dal BA.
        self._apply_optional_positive_int(
            payload, data, "categoria_cliente_id_snapshot", message=_MESSAGE,
        )
        # Snapshot valuta: opzionale. Se fornito congela il valore scelto
        # dall'operatore (es. via form-defaults che pre-popola dal BB
        # `resolve_valuta_default`); se omesso il trigger DB
        # `_a*_set_valuta_default_ins` risolve via `vendite.fn_get_valuta_id`
        # (catena BA → emittente → gestore). Brief work-done 2026-05-29.
        self._apply_optional_positive_int(
            payload, data, "valuta_id", message=_MESSAGE,
        )
        self._apply_fatturazione_immediata(payload, data)
        # ⭐ SLICE S3-b (2026-08-31): i tre riferimenti dell'atto entrano anche
        #    in CREATE, ora che `20260831-24` li ha messi nella whitelist
        #    interna di `vendite.fn_create_contratto`.
        # ⚠️ La chiamata qui NON e' ridondante con la whitelist: i due mapper
        #    del contratto copiano campo per campo, quindi una chiave ammessa e
        #    non mappata si perde in silenzio — e' il difetto del 2026-07-27
        #    (whitelist estesa, mapper no → 200 «contratto salvato» e niente
        #    persistito). Stesso helper dell'update: validazione di lunghezza e
        #    normalizzazione del vuoto vivono in un posto solo.
        self._apply_codici_atto(payload, data)
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # Scopo: Estrae i tre riferimenti dell'atto (CIG/CUP/commessa) nel data dict.
    #        Chiave assente -> non si tocca; stringa vuota o null -> NULL
    #        (`feedback_null_vs_empty`); stringa -> trim + guard di lunghezza.
    # ⚠️ Il mapper esiste perche' la whitelist DA SOLA NON BASTA: qui si copia
    #    campo per campo, ed e' il difetto costato un giro su
    #    `fatturazione_immediata` il 2026-07-27 — chiave whitelisted e mapper non
    #    aggiornato = valore scartato in silenzio.
    # ⚠️ Il guard di lunghezza non e' burocrazia: senza, un CIG di 20 caratteri
    #    arriverebbe come DataError del driver, cioe' come 500 con un messaggio
    #    che nomina una colonna invece del campo che l'operatore ha compilato.
    def _apply_codici_atto(
        self, payload: dict[str, Any], data: dict[str, Any],
    ) -> None:
        for key, max_len in _CODICI_ATTO_MAX_LEN.items():
            value = self._v.extract_optional_string(
                payload, key, nullable=True, message=_MESSAGE,
            )
            if value is MISSING:
                continue
            if value is not None:
                assert isinstance(value, str)
                ErrorManager.require(
                    len(value) <= max_len,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE,
                    detail=f"{key} supera la lunghezza massima di {max_len} caratteri.",
                    context={"field": key, "len": len(value), "max_len": max_len},
                )
            data[key] = value

    # Scopo: Porta `fatturazione_immediata` dal payload al dict che raggiunge il
    #        DB. Esiste come metodo suo, condiviso da create e update, perche' i
    #        due mapper del contratto copiano campo per campo: aggiungere la
    #        chiave alla sola whitelist non basta, ed e' esattamente il difetto
    #        del 2026-07-27 (whitelist estesa, mapper no → PATCH che rispondeva
    #        200 con «contratto salvato» e non persisteva nulla).
    #        Validazione con `optional_bool` e non `bool(...)`: quest'ultimo
    #        accetterebbe la stringa `"false"` come True.
    #        Chiave assente o `null` → si OMETTE dal dict: la colonna e' NOT
    #        NULL e la fn madre filtra sulla PRESENZA della chiave, quindi un
    #        `None` propagato diventerebbe un 23502 invece del DEFAULT false
    #        (contratto §C4 del brief DB).
    def _apply_fatturazione_immediata(
        self, payload: dict[str, Any], data: dict[str, Any],
    ) -> None:
        valore = self._v.optional_bool(payload, "fatturazione_immediata")
        if valore is not None:
            data["fatturazione_immediata"] = valore

    # Scopo: Compone il dict di update testata. Rivalida coerenza coppia
    #        variazione globale con la foto attuale (listino_id in DRAFT si
    #        cambia finche' non ci sono righe attive o eccezioni: lo ferma
    #        `script.trgfn_doc_guard_listino_con_righe`; il trigger attivazione fissa
    #        `listino_versione_id` su transizione DRAFT -> ATTIVO).
    #        `existing` e' la riga corrente dal DB: serve per applicare il
    #        validator alla coppia effettiva quando il patch tocca solo una
    #        dimensione (es. variazione globale senza listino_id nel payload).
    def _build_update_data_testata(
        self, payload: dict[str, Any], *, existing: dict[str, Any]
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        # Il cliente si cambia per coppia: BA e istanza viaggiano insieme, letti
        # dal lato che il payload porta, sulla utility della testata (che non
        # cambia). Cambiare il solo BA lascerebbe l'istanza vecchia, che la FK
        # composta `fk_contratti_ba_coppia` rifiuta.
        if "billing_account_id" in payload or "istanza_utility_id" in payload:
            data["billing_account_id"], data["istanza_utility_id"] = risolvi_cliente_coppia(
                billing_account_id=self._v.optional_positive_int(
                    payload, "billing_account_id", message=_MESSAGE,
                ),
                istanza_utility_id=self._v.optional_positive_int(
                    payload, "istanza_utility_id", message=_MESSAGE,
                ),
                utility_id=int(existing["utility_id"]),
                code=E_VENDITE_VALIDATION,
                msg_ba_fuori_coppia=_MSG_BA_FUORI_COPPIA,
                function_name=f"{__name__}.update_contratto",
            )
        if "ambito" in payload:
            data["ambito"] = self._extract_ambito(payload)
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.require_date(payload, "valido_dal", message=_MESSAGE)
        if "valido_al" in payload:
            if payload["valido_al"] is None:
                data["valido_al"] = None
            else:
                data["valido_al"] = self._v.require_date(payload, "valido_al", message=_MESSAGE)
        self._apply_optional_positive_int(
            payload, data, "parent_contratto_id", message=_MESSAGE,
        )
        if "data" in payload:
            data["data"] = self._v.require_date(payload, "data", message=_MESSAGE)
        self._apply_optional_positive_int(
            payload, data, "listino_id", message=_MESSAGE,
        )
        self._apply_variazione_globale(payload, data)
        # Valida coerenza coppia variazione globale sulla foto post-update merge
        # (delta data + existing). Se il patch tocca listino_id o una delle 2
        # componenti della variazione, rivalida combinando i campi presenti
        # con lo stato corrente.
        if (
            "listino_id" in data
            or "tipo_variazione_globale" in data
            or "valore_variazione_globale" in data
        ):
            self._validate_variazione_globale_coppia_coerente(data, existing=existing)
        # Categoria snapshot: fuori bozza la ferma il lock di testata del DB
        # (`E_DOC_CONDIZIONI_FUORI_BOZZA`).
        self._apply_optional_positive_int(
            payload, data, "categoria_cliente_id_snapshot", message=_MESSAGE,
        )
        self._apply_fatturazione_immediata(payload, data)
        self._apply_codici_atto(payload, data)
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # Scopo: Normalizza ambito a uppercase e valida contro whitelist (la
    #        lettura e' del BB `PayloadValidator`, il vocabolario resta qui).
    def _extract_ambito(self, payload: dict[str, Any]) -> str:
        return self._v.require_enum(payload, "ambito", allowed=_AMBITI_VALIDI, message=_MESSAGE)

    # Scopo: Estrae e applica la coppia (tipo/valore) variazione globale nel
    #        data dict. Coerenza coppia validata da
    #        `_validate_variazione_globale_coppia_coerente`.
    def _apply_variazione_globale(
        self, payload: dict[str, Any], data: dict[str, Any]
    ) -> None:
        tipo_present = "tipo_variazione_globale" in payload
        valore_present = "valore_variazione_globale" in payload
        tipo = None
        if tipo_present:
            # Tre stati (PATCH): la chiave c'e' — `None` azzera la variazione,
            # un codice va letto contro il vocabolario (BB `PayloadValidator`).
            tipo = self._v.extract_optional_enum(
                payload, "tipo_variazione_globale",
                allowed=_TIPI_VARIAZIONE_GLOBALE_AMMESSI, nullable=True, message=_MESSAGE,
                nota=(
                    "VALORE_FISSO non e' ammesso sulla testata contratto: per "
                    "prezzi fissi su singolo articolo usa una riga OVERRIDE."
                ),
            )
            assert tipo is not MISSING
            data["tipo_variazione_globale"] = tipo
        if valore_present:
            data["valore_variazione_globale"] = self._v.optional_decimal(
                payload, "valore_variazione_globale", message=_MESSAGE,
            )

    # Scopo: Gate L2 sulla variazione globale del contratto al PATCH testata
    #        (refactor 2026-05-15 §3-bis-E). Wrapper sottile sul BB condiviso
    #        `_pricing_gate_helpers.check_limite_variazione_globale` che
    #        contiene la logica (cascata user→categoria→group→emittente,
    #        superuser bypass, PERCENTUALE-only, raise retryable).
    #        Qui ci limitiamo a estrarre i campi dal merge (data + existing)
    #        prima di delegare.
    def _check_limite_variazione_globale(
        self,
        *,
        existing: dict[str, Any],
        data: dict[str, Any],
        auth_user_id: int | None,
    ) -> None:
        # ⛔ La soglia dipende da TRE ingressi — valore, tipo e cliente — e il
        #    gate scatta quando il payload ne tocca uno qualunque: fino al
        #    2026-10-21 guardava il solo valore, e spostare il contratto su un
        #    cliente con soglia piu' bassa (o passare da VALORE_FISSO a
        #    PERCENTUALE) lasciava il contratto oltre soglia senza controllo.
        #    In creazione `existing` e' vuoto.
        if not _INGRESSI_GATE_L2 & data.keys():
            return

        def dopo(chiave: str) -> Any:
            return data[chiave] if chiave in data else existing.get(chiave)

        check_limite_variazione_globale(
            auth_user_id=auth_user_id,
            tipo_variazione=dopo("tipo_variazione_globale"),
            valore_variazione=dopo("valore_variazione_globale"),
            function_name="contratti_service._check_limite_variazione_globale",
            # Il cliente su cui si misura la soglia e' quello che il contratto
            # AVRA': quello del payload (nascita, o cambio cliente in bozza),
            # altrimenti quello che ha.
            ba_id=dopo("billing_account_id"),
        )

    # Scopo: Verifica coerenza della coppia variazione globale (tipo + valore).
    #        Post refactor modalita' (2026-05-15): non c'e' piu' il vincolo
    #        "listino_id NULL -> tipo/valore NULL" — il modello unificato
    #        ammette qualunque combinazione di listino + variazione + eccezioni.
    #        Resta solo il vincolo strutturale: tipo e valore devono essere
    #        coppia (entrambi NULL o entrambi NOT NULL) per dare semantica a
    #        `valore_variazione_globale`.
    def _validate_variazione_globale_coppia_coerente(
        self, data: dict[str, Any], *, existing: dict[str, Any] | None
    ) -> None:
        tipo = data.get("tipo_variazione_globale") if "tipo_variazione_globale" in data else (
            existing.get("tipo_variazione_globale") if existing else None
        )
        valore = data.get("valore_variazione_globale") if "valore_variazione_globale" in data else (
            existing.get("valore_variazione_globale") if existing else None
        )
        pair_complete = (tipo is None) == (valore is None)
        ErrorManager.require(
            pair_complete,
            code=E_VENDITE_VALIDATION,
            message=_MESSAGE,
            detail="tipo_variazione_globale e valore_variazione_globale devono essere entrambi presenti o entrambi NULL.",
            context={
                "tipo_variazione_globale": tipo,
                "valore_variazione_globale": str(valore) if valore is not None else None,
            },
        )

    # =================================================================
    # Helpers privati — righe
    # =================================================================

    # Scopo: Compone il dict CRUD per contratti_righe. articolo_id e
    #        tipo_eccezione sono obbligatori in create; mutazione dei campi
    #        commerciali solo sui campi presenti. Il check di coerenza
    #        (ESCLUSIONE -> prezzo NULL, OVERRIDE/AGGIUNTA -> prezzo NOT NULL)
    #        e' enforced dal CHECK DB chk_contrighe_prezzo_per_tipo_eccezione;
    #        qui si pre-valida, per messaggio parlante, il solo ramo
    #        OVERRIDE/AGGIUNTA (l'ESCLUSIONE la rifiuta il guard DB col campo).
    def _build_data_riga(self, payload: dict[str, Any], *, for_create: bool) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if for_create:
            data["articolo_id"] = self._v.require_uuid(
                payload, "articolo_id", message=_MESSAGE_RIGA,
            )
            # tipo_eccezione obbligatorio in create (NOT NULL nello schema):
            # la lettura e' del BB `PayloadValidator`, il vocabolario resta qui.
            tipo_eccezione = self._v.require_enum(
                payload, "tipo_eccezione", allowed=_TIPI_ECCEZIONE, message=_MESSAGE_RIGA,
            )
            data["tipo_eccezione"] = tipo_eccezione

            # Coerenza prezzo_unitario / tipo_eccezione (pre-DB):
            # - OVERRIDE / AGGIUNTA -> prezzo NOT NULL (e' il prezzo finale)
            # ⛔ L'ESCLUSIONE non si pre-valida qui: il prezzo e' uno dei dieci
            #    dati di fatturazione che il guard DB rifiuta col campo
            #    (E_RIGA_ESCLUSIONE_CON_DATI, brief-db-righe-esclusione-solo-
            #    non-si-vende R-BE-3). Un 400 nostro sul solo prezzo direbbe la
            #    stessa regola con un altro codice.
            # Eccezione: articolo composito (modello unificato BoM 2026-05-13).
            # Il FE puo' omettere `prezzo_unitario` per padri compositi perche'
            # il prezzo padre = SUM(figli × coeff_qta) calcolato dal trigger
            # DB `_z90_ricalcola_padre` post-init componenti BoM nello stesso
            # `@transaction.atomic`. Setto un placeholder Decimal(0) per
            # superare il CHECK `chk_contrighe_prezzo_per_tipo_eccezione`
            # (`prezzo_unitario IS NOT NULL` per OVERRIDE/AGGIUNTA) — il
            # trigger lo sovrascrive sincrono dopo INSERT padre + INSERT figli.
            # Pattern simmetrico al preventivo (cfr. preventivi_service.py
            # `gestisci_riga` ~ linea 670, "Padre composito").
            prezzo_raw = payload.get("prezzo_unitario")
            if prezzo_raw is None and tipo_eccezione != "ESCLUSIONE":
                # OVERRIDE / AGGIUNTA: prezzo None ammesso solo se composito.
                articolo_id_val = data.get("articolo_id")
                is_composito = bool(
                    articolo_id_val
                    and self._repo.is_articolo_composito(str(articolo_id_val))
                )
                ErrorManager.require(
                    is_composito,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        f"{tipo_eccezione}: prezzo_unitario obbligatorio "
                        "per articoli non compositi."
                    ),
                    context={"tipo_eccezione": tipo_eccezione},
                )
                # Placeholder: il trigger DB lo sovrascrive a SUM componenti.
                payload = {**payload, "prezzo_unitario": Decimal("0")}
        # Numeric opzionali: `null` esplicito azzera, chiave assente non tocca.
        for field in ("prezzo_unitario", "qta_operativa", "factor_to_base"):
            if field in payload:
                data[field] = self._v.optional_decimal(
                    payload, field, message=_MESSAGE_RIGA,
                )
        self._apply_optional_positive_int(
            payload, data, "uom_operativa_id", message=_MESSAGE_RIGA,
        )
        if "ordine" in payload:
            value = self._v.optional_smallint(payload, "ordine", min_val=0)
            if value is not None:
                data["ordine"] = value
        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            if value is not None:
                data["attivo"] = value
        # Stringhe opzionali (varchar libere lato DB: CHECK constraint sul DB
        # per enum — traduciamo un eventuale IntegrityError.
        for field in (
            "tipo_erogazione",
            "fonte_quantita_attesa",
            "periodicita",
            "generazione_canone",
            "competenza_canone",
        ):
            if field in payload:
                raw = payload[field]
                if raw is None:
                    data[field] = None
                else:
                    ErrorManager.require(
                        isinstance(raw, str),
                        code=E_VENDITE_VALIDATION,
                        message=_MESSAGE_RIGA,
                        detail=f"{field} deve essere stringa o NULL.",
                        context={"field": field},
                    )
                    assert isinstance(raw, str)
                    data[field] = raw.strip().upper()

        # ⛔ La quantita' per fonte non si normalizza qui: con una fonte a valle
        # (MANUALE, LETTURE, TIMESHEET) il DB svuota `quantita` da solo
        # (`script.trgfn_qta_from_operativa`) e rifiuta una `qta_operativa`
        # valorizzata col campo (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`); la FISSA
        # senza quantita' la rifiuta il DB (`E_QTA_MISSING`). Quali coppie
        # (tipo_erogazione, fonte) sono ammesse, e cosa eredita una riga che non
        # le indica, lo dice il DB dall'articolo (`vendite.fn_articolo_erogazioni`).
        # La copia Python (`_apply_fonte_quantita_logic`) azzerava in silenzio, e
        # solo sul contratto: ritirata (brief-db-offerta-emissione-ed-erogazione F-1).

        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — utility 1:1
    # =================================================================

    # Scopo: Verifica struttura payload utility. Il controllo di coerenza
    #        tipo/classe dinamico e' delegato al trigger DB.
    def _validate_utility_payload_shape(
        self, payload: dict[str, Any], *, for_create: bool
    ) -> None:
        allowed = UTILITY_CREATE_KEYS if for_create else UTILITY_UPDATE_KEYS
        self._v.validate_allowed_keys(
            payload, allowed=allowed, message=_MESSAGE_UTILITY,
        )

    # Scopo: Compone il dict CRUD per contratti_utilities. istanza_utility_id
    #        e utility_id sono derivati dal contratto, non dal payload.
    def _build_utility_data(
        self,
        payload: dict[str, Any],
        *,
        istanza_utility_id: int,
        utility_id: int,
        for_create: bool,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if for_create:
            data["istanza_utility_id"] = istanza_utility_id
            data["utility_id"] = utility_id
        for fk_field in ("istanza_dati_precontrattuali_id", "tipo_utenza_id", "classe_utenza_id"):
            self._apply_optional_positive_int(
                payload, data, fk_field, message=_MESSAGE_UTILITY,
            )
        if "param_1_num" in payload:
            data["param_1_num"] = self._v.optional_decimal(
                payload, "param_1_num", message=_MESSAGE_UTILITY,
            )
        if "param_2_txt" in payload:
            raw = payload["param_2_txt"]
            if raw is None:
                data["param_2_txt"] = None
            else:
                ErrorManager.require(
                    isinstance(raw, str),
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_UTILITY,
                    detail="param_2_txt deve essere stringa o NULL.",
                    context={"field": "param_2_txt"},
                )
                assert isinstance(raw, str)
                data["param_2_txt"] = raw.strip()
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — numeri e DB errors
    # =================================================================

    # Scopo: Helper per campi int opzionali nullable. Estrae dal payload,
    #        accetta None esplicito, valida positivita' altrimenti. Applica
    #        al data dict solo se la chiave e' presente nel payload.
    def _apply_optional_positive_int(
        self,
        payload: dict[str, Any],
        data: dict[str, Any],
        field: str,
        *,
        message: str,
    ) -> None:
        if field not in payload:
            return
        raw = payload[field]
        if raw is None:
            data[field] = None
            return
        data[field] = self._v.require_positive_int(payload, field, message=message)


# ────────────────────────────────────────────────────────────────────────
# Pricing per riga contratto — entry point + gate 3-livelli (BE 2.0)
# ────────────────────────────────────────────────────────────────────────
#
# Simmetrico al pattern preventivi (`suggerisci_prezzo_riga` +
# `_resolve_or_check_override_prezzo`). Le funzioni qui sotto NON sono
# ancora cablate nei flussi `create_riga`/`update_riga` di
# `ContrattiService`: il wiring avviene in BE 2.2 (introduzione delle
# operazioni eccezione OVERRIDE/AGGIUNTA dove il prezzo manuale ha senso).
# Esposte ora come BB testabile in isolamento.


# Scopo: Suggerisce il prezzo unitario per una riga contratto, dato
#        l'articolo, l'UoM e il contesto del contratto (BA, utility, data,
#        emittente). Simmetrica a `preventivi_service.suggerisci_prezzo_riga`.
#
#        Differenze rispetto ai preventivi:
#          - Data di riferimento: `valido_dal` del contratto (non `data`
#            documento). Coerente con `preview_componenti_riga` e con la
#            semantica "il contratto e' una promessa valida per il range
#            valido_dal/valido_al".
#          - Emittente: delegato a `resolve_emittente_sr_id_for_testata`
#            (helper Fase H) che gestisce precedenza emittente esplicito
#            sulla testata vs derivato da auth_user_id.
#
#        Solleva `E_VENDITE_VALIDATION` su input mancanti o non risolubili,
#        `E_VENDITE_NOT_FOUND` su contratto inesistente, e propaga errori
#        ServiceError dal `PricingService.resolve_prezzo` (es.
#        `E_CATEGORIA_LISTINO_NON_MAPPATA`).
# Scopo: Helper module-level. Risolve il contesto di pricing per un
#        contratto: lookup testata + emittente + validazione BA/utility/data,
#        parsing `valido_dal` a `date`. Riusato da
#        `contratti_suggerisci_prezzo_riga` (pricing singola riga) e da
#        `ContrattiService.preview_componenti_riga` (pricing BoM components).
#        Centralizza il pattern condiviso ed evita drift fra i due caller.
#
#        Ritorna dict con: `testata`, `ba_id`, `utility_id`,
#        `emittente_sr_id`, `data_riferimento`.
#
#        Errori:
#          - `E_VENDITE_NOT_FOUND` se contratto inesistente
#          - `E_VENDITE_VALIDATION` se manca BA/utility/valido_dal o
#            emittente non risolvibile
def _load_contratto_context_for_pricing(
    contratto_id: int,
    auth_user_id: int | None,
    *,
    function_name: str,
    repo: ContrattiRepository | None = None,
) -> dict[str, Any]:
    if repo is None:
        repo = ContrattiRepository()
    testata = testata_o_not_found(
        repo.get_contratto, contratto_id,
        code=E_VENDITE_NOT_FOUND, message="Contratto non trovato.",
        id_name="contratto_id", function_name=function_name,
    )

    ba_id_raw = testata.get("billing_account_id")
    ErrorManager.require(
        ba_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    # Data di riferimento: `valido_dal` del contratto. Il resolver bundle-aware
    # cerca prezzi/promo/categoria validi a quella data; coerente col fatto che
    # il contratto e' una promessa contrattuale valida per il range.
    valido_dal_raw = testata.get("valido_dal")
    ErrorManager.require(
        valido_dal_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza valido_dal: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert valido_dal_raw is not None
    data_riferimento = (
        valido_dal_raw if isinstance(valido_dal_raw, date)
        else date.fromisoformat(str(valido_dal_raw))
    )

    # Emittente: precedenza emittente esplicito sulla testata > derivato
    # dall'operatore (modello operatore-emittenti 1-a-1). Helper Fase H.
    emittente_sr_id = resolve_emittente_sr_id_for_testata(
        testata, auth_user_id,
        repo_get_sr_id_by_fiscale_id=repo.get_emittente_sr_id_by_fiscale_id,
    )
    ErrorManager.require(
        emittente_sr_id is not None,
        code=E_VENDITE_VALIDATION,
        message="Impossibile risolvere l'emittente fiscale per il pricing.",
        function_name=function_name,
    )
    assert emittente_sr_id is not None

    # Refactor 2026-05-20: listino_versione_id passato al resolver pricing
    # v2 come `p_listino_versione_id_preferito` per attivare il fast path
    # CONTRATTO_LISTINO. Evita il drift verso stadio CATEGORIA quando il BA
    # ha una mappa categorie_clienti_listini su un listino diverso.
    # ⭐ La versione la dice il DB (`vendite.fn_documento_listino_operativo`):
    # la fissata all'attivazione, altrimenti quella in vigore oggi — la stessa
    # che governa le righe a video, quindi preview e pricing coincidono per
    # costruzione. Senza listino: None (resolver senza fast path).
    # ⛔ Fino al 2026-10-07 qui c'era una copia Python che la cercava alla data
    # `valido_dal`, mentre le righe usavano gia' quella di oggi
    # (brief-db-offerta-emissione-ed-erogazione §C.1.3).
    # Doc DB: cfr. nota team `dev/db-tid` sul 9° arg di fn_resolve_prezzo_listino_v2.
    listino_versione_id_preferito = listino_versione_operativa(SORGENTE_CONTRATTO, contratto_id)

    assert ba_id_raw is not None and utility_id_raw is not None
    return {
        "testata": testata,
        "ba_id": int(ba_id_raw),
        "utility_id": int(utility_id_raw),
        "emittente_sr_id": emittente_sr_id,
        "data_riferimento": data_riferimento,
        "listino_versione_id_preferito": listino_versione_id_preferito,
    }


def contratti_suggerisci_prezzo_riga(
    contratto_id: int,
    *,
    articolo_id: str,
    uom_id: int,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = "contratti_service.contratti_suggerisci_prezzo_riga"

    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code=E_VENDITE_VALIDATION,
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    guard_uom_id_positive(
        uom_id, error_code=E_VENDITE_VALIDATION, function_name=function_name,
    )

    ctx = _load_contratto_context_for_pricing(
        contratto_id, auth_user_id, function_name=function_name,
    )

    result = PricingService().resolve_prezzo(
        articolo_id=str(articolo_id),
        uom_id=int(uom_id),
        data_riferimento=ctx["data_riferimento"],
        ba_id=ctx["ba_id"],
        utility_id=ctx["utility_id"],
        emittente_soggetto_ruolo_id=ctx["emittente_sr_id"],
        listino_versione_id_preferito=ctx["listino_versione_id_preferito"],
    )

    # Normalizzazione Decimal/date → string per stabilita' JSON (coerente
    # con preventivi_service.suggerisci_prezzo_riga).
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Orchestratore 3 gate prezzo (L1+L2+L3) per riga contratto.
#        Thin wrapper sul BB `_pricing_gate_helpers.resolve_or_check_override_prezzo`,
#        simmetrico al wrapper omonimo di `preventivi_service`. Cabla
#        direttamente `contratti_suggerisci_prezzo_riga` come resolver_fn
#        (la signature e' gia' quella attesa dal BB) + il codice errore di
#        validazione del dominio (`E_VENDITE_VALIDATION`).
#
#        Normalizzazione testata: il BB usa `testata["data"]` nel guard
#        skip-context (riga ~401 di _pricing_gate_helpers). La testata
#        contratto espone invece `valido_dal`. Aliasiamo qui per
#        incapsulare la differenza nel wrapper di dominio invece di
#        contaminare il BB con conoscenza per-sorgente.
def resolve_or_check_override_prezzo_riga_contratto(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    # Refactor 2026-05-20: skip TUTTI i gate (L1+L2+L3) per contratti senza
    # listino. Semantica del modello "senza_listino": tutte le righe sono
    # AGGIUNTA negoziate, il prezzo e' governato dal contratto stesso —
    # nessun benchmark esterno comparabile. La cascata pricing v5 cadrebbe
    # comunque su stadio CATEGORIA o PROMO (gli unici disponibili senza
    # listino del contratto), generando confronti L2 contro riferimenti
    # semanticamente non pertinenti (stesso pattern del bug fixato per
    # contratti CON listino via fast path `listino_versione_id_preferito`).
    # NB: il payload_prezzo viene ritornato as-is senza meta audit; il
    # CHECK chk_contrighe_prezzo_per_tipo_eccezione del DB resta come
    # safety net (prezzo NOT NULL per OVERRIDE/AGGIUNTA non-compositi).
    if testata.get("listino_id") is None:
        return payload_prezzo, None

    testata_normalized = (
        testata if testata.get("data") is not None
        else {**testata, "data": testata.get("valido_dal")}
    )
    return resolve_or_check_override_prezzo(
        testata=testata_normalized,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=contratti_suggerisci_prezzo_riga,
        error_code_validazione=E_VENDITE_VALIDATION,
        richiesta_approvazione=richiesta_approvazione,
    )


# Scopo: orchestratore L3 simmetrico a `preventivi_service._orchestrate_l3_request`
#        per le righe contratto (refactor 2026-05-19 BE porting gate riga
#        contratti). Crea la pratica APPROVAZIONE_PREZZO via
#        `approvazioni_prezzo_service.crea_richiesta_approvazione_contratto`,
#        opzionalmente collega riga_id (per update_riga il riga_id e' gia'
#        noto; per create_riga il link avviene post-INSERT). Ritorna pratica_id.
def _orchestrate_l3_request_contratto(
    *,
    contratto_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    # Import lazy: il service approvazioni importa contratti_service per
    # `ContrattiRepository.update_riga` nel dispatch sorgente-agnostico.
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione_contratto,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione_contratto(
        contratto_id=contratto_id,
        riga_id=riga_id_for_link,
        articolo_id=str(articolo_id) if articolo_id is not None else "",
        prezzo_resolver=Decimal(prezzo_meta["prezzo_base_resolver"])
        if prezzo_meta.get("prezzo_base_resolver") else None,
        prezzo_manuale=Decimal(str(prezzo_finale)),
        violazione=prezzo_meta["violazione_l2"],
        auth_user_id=auth_user_id,
    )
    if riga_id_for_link is not None:
        link_riga_a_pratica(
            pratica_id=pratica_id,
            riga_id=riga_id_for_link,
            sorgente=META_SORGENTE_CONTRATTO,
        )
    return pratica_id


# ══════════════════════════════════════════════════════════
#  Indirizzi documento (BB condiviso _indirizzi_documento_helpers)
# ══════════════════════════════════════════════════════════

_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono il repository.
    repo_factory=lambda: ContrattiRepository(),
    not_found_code=E_VENDITE_NOT_FOUND,
    error_code=E_VENDITE_VALIDATION,
    fn_prefix="vendite.contratti_service",
)


# Scopo: Pannello indirizzi del contratto (ambito CONTRATTI). Guard di
#        esistenza e traduzione errori DB nel BB condiviso.
def list_indirizzi(contratto_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, contratto_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo DRAFT: post-attivazione
#        lo snapshot e' congelato col documento).
def upsert_indirizzo(contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, contratto_id, payload)


# Scopo: Rimozione slot indirizzo (solo DRAFT).
def delete_indirizzo(contratto_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, contratto_id, indirizzo_id)
