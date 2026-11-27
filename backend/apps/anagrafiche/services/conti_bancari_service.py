# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione conti bancari.
#        Orchestrazione registro IBAN (get_or_create), legami
#        soggetto ↔ conto, legami ruolo ↔ conto, lookup filiali.
#        Ref: docs/it/guide/gestione-conti-bancari.md
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.non_editable_fields_helper import compute_non_editable_fields
from apps.anagrafiche.db.conti_bancari_repository import (
    LEGAME_RUOLO_UPDATE_COLS,
    LEGAME_SOGGETTO_UPDATE_COLS,
    ContiBancariRepository,
)
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_CONTO_NOT_FOUND,
    E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
    E_ANAG_DUPLICATO,
    E_ANAG_FK,
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.anagrafiche.services._validators import (
    optional_str,
    require_str,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)


# Contratti delle PATCH dei legami, validati QUI con 400 `E_ANAG_VALIDAZIONE`
# (2026-09-26): dal passaggio al BB `sql_set_clause` il repository rifiuta con
# `RuntimeError` (500) ogni colonna fuori whitelist — fino a quel giorno la
# scartava in silenzio. Partono dalle colonne scrivibili del repository.
# ⛔ Conto, `uso` e possessore (`istanza_utility_id` compresa) non ci sono:
#    hanno il lucchetto del DB (giro T8a) e una PATCH che li porta e' un 400
#    che li nomina, non un `E_CONTO_LEGAME_IMMUTABILE` dopo il viaggio.
_UPDATE_LEGAME_SOGGETTO_KEYS: frozenset[str] = LEGAME_SOGGETTO_UPDATE_COLS
_UPDATE_LEGAME_RUOLO_KEYS: frozenset[str] = LEGAME_RUOLO_UPDATE_COLS
_MESSAGE_LEGAME = "Payload conto bancario non valido."

# Validator stateless del dominio (solo il codice errore): condivisibile.
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

# Vincoli DB dei due legami -> codici errore (E-7 di
# analisi-be-difetti-emersi-verifica-doc-api-core, 2026-10-07). Prima ogni
# `IntegrityError` usciva `E_ANAG_DUPLICATO` «gia' associato», anche per un
# `uso` fuori elenco, date invertite o una FK violata. I nomi vengono dalla doc
# auto-gen `dbzero/anagrafiche/tabelle/{conti_bancari,soggetti{,_ruoli}_conti_bancari}.md`;
# le unicita' del legame RUOLO sono indici parziali (con e senza istanza), non
# vincoli, e il nome che PostgreSQL riporta e' quello dell'indice.
# Terzo elemento = il campo del payload, solo dove la violazione ne ha UNO.
# ⭐ Predefinito per periodo e predefinito non bloccato (giro T8a, D-T8a-7 a e
#    D-T8a-2): li dice il guard `a12` del DB col suo codice; EXCLUDE e CHECK
#    restano come rete (le scritture concorrenti, 23P01) e qui rispondono con
#    LO STESSO codice del guard, perche' per chi scrive e' la stessa regola.
_E_PREDEFINITO_SOVRAPPOSTO = "E_CONTO_PREDEFINITO_SOVRAPPOSTO"
_E_PREDEFINITO_BLOCCATO = "E_CONTO_PREDEFINITO_BLOCCATO"
_MSG_PREDEFINITO = (
    "C'e' gia' un conto predefinito per questo uso in un periodo che si sovrappone."
)
_MSG_PREDEFINITO_BLOCCATO = "Un conto predefinito non si puo' bloccare."
_MSG_INCASSO = (
    "Il conto e' gia' il conto di incasso di un altro soggetto: "
    "un conto di incasso appartiene a un soggetto solo."
)
# ⭐ Gli usi ammessi del legame, UN elenco: lo leggono il guard del payload
#    (create e PATCH) e il messaggio del CHECK `chk_*_uso`, che lo rispecchia.
#    Prima erano tre copie nello stesso file.
_USI_LEGAME: tuple[str, ...] = ("INCASSO", "PAGAMENTO", "RIMBORSO", "GENERICO")
_MSG_USO = f"Uso non ammesso (consentiti: {', '.join(_USI_LEGAME)})."
_MSG_VALIDITA = "La fine validita' non puo' precedere l'inizio."
_MSG_CONTO_FK = "Conto bancario non trovato nel registro."
_MSG_LEGAME_NOT_FOUND = "Associazione conto bancario non trovata."

_VINCOLI_LEGAME_SOGGETTO: dict[str, dict[str, tuple]] = {
    "unique_constraints": {
        "uq_soggetti_conti_bancari_soggetto_id_conto_id_uso": (
            E_ANAG_DUPLICATO,
            "Conto bancario gia' associato a questo soggetto per lo stesso uso.",
        ),
        "ex_scb_predefinito_per_periodo": (
            _E_PREDEFINITO_SOVRAPPOSTO, _MSG_PREDEFINITO, "predefinito",
        ),
        "ex_scb_conto_incasso_un_solo_soggetto": (E_ANAG_DUPLICATO, _MSG_INCASSO),
    },
    "check_constraints": {
        "chk_soggetti_conti_bancari_uso": (E_ANAG_VALIDAZIONE, _MSG_USO, "uso"),
        "chk_soggetti_conti_bancari_predefinito_non_bloccato": (
            _E_PREDEFINITO_BLOCCATO, _MSG_PREDEFINITO_BLOCCATO, "bloccato",
        ),
        "chk_soggetti_conti_bancari_validita": (
            E_ANAG_VALIDAZIONE, _MSG_VALIDITA, "valido_al",
        ),
    },
    "fk_constraints": {
        "fk_soggetti_conti_bancari_conti_bancari": (E_ANAG_FK, _MSG_CONTO_FK),
        "fk_soggetti_conti_bancari_soggetti": (E_ANAG_FK, "Soggetto non trovato."),
    },
}

_VINCOLI_LEGAME_RUOLO: dict[str, dict[str, tuple]] = {
    "unique_constraints": {
        "uq_src_bancari_ruolo_conto_uso_no_istanza": (
            E_ANAG_DUPLICATO,
            "Conto bancario gia' associato a questo ruolo per lo stesso uso.",
        ),
        "uq_src_bancari_ruolo_istanza_conto_uso": (
            E_ANAG_DUPLICATO,
            "Conto bancario gia' associato a questa istanza per lo stesso uso.",
        ),
        "ex_src_bancari_predefinito_no_istanza_periodo": (
            _E_PREDEFINITO_SOVRAPPOSTO, _MSG_PREDEFINITO, "predefinito",
        ),
        "ex_src_bancari_predefinito_istanza_periodo": (
            _E_PREDEFINITO_SOVRAPPOSTO, _MSG_PREDEFINITO, "predefinito",
        ),
        "ex_src_bancari_conto_incasso_un_solo_soggetto": (E_ANAG_DUPLICATO, _MSG_INCASSO),
    },
    "check_constraints": {
        "chk_soggetti_ruoli_conti_bancari_uso": (E_ANAG_VALIDAZIONE, _MSG_USO, "uso"),
        "chk_soggetti_ruoli_conti_bancari_predefinito_non_bloccato": (
            _E_PREDEFINITO_BLOCCATO, _MSG_PREDEFINITO_BLOCCATO, "bloccato",
        ),
        "chk_soggetti_ruoli_conti_bancari_validita": (
            E_ANAG_VALIDAZIONE, _MSG_VALIDITA, "valido_al",
        ),
    },
    "fk_constraints": {
        "fk_soggetti_ruoli_conti_bancari_conti_bancari": (E_ANAG_FK, _MSG_CONTO_FK),
        "fk_soggetti_ruoli_conti_bancari_soggetti_ruoli": (
            E_ANAG_FK, "Ruolo del soggetto non trovato.",
        ),
        "fk_src_bancari_istanze_utilities": (
            E_ANAG_FK, "Istanza utility non trovata.", "istanza_utility_id",
        ),
    },
}

# Il registro degli IBAN (`anagrafiche.conti_bancari`), scritto dal
# get_or_create della nascita di un legame. ⭐ La FORMA la tiene il DB
# (giro T8a, D-T8a-8 e -14): il trigger `a01` normalizza IBAN e BIC, poi i
# CHECK giudicano il valore normalizzato, lunghezza compresa. Qui non c'e'
# piu' la regex del backend: la violazione del formato si traduce sul campo.
# `uq_conti_bancari_iban` e' la gara fra due nascite dello stesso IBAN (il
# get_or_create legge prima di scrivere).
_VINCOLI_CONTO: dict[str, dict[str, tuple]] = {
    "unique_constraints": {
        "uq_conti_bancari_iban": (
            E_ANAG_DUPLICATO,
            "Il conto con questo IBAN e' stato appena registrato: riprova.",
            "iban",
        ),
    },
    "check_constraints": {
        "chk_conti_bancari_iban_fmt": (
            E_ANAG_VALIDAZIONE,
            "IBAN non valido: da 15 a 34 lettere e cifre, separatori esclusi.",
            "iban",
        ),
        "chk_conti_bancari_bic_fmt": (
            E_ANAG_VALIDAZIONE,
            "BIC non valido: 8 o 11 lettere e cifre, separatori esclusi.",
            "bic_swift",
        ),
        "chk_conti_bancari_paese_fmt": (
            E_ANAG_VALIDAZIONE,
            "L'IBAN non comincia con il codice di un paese.",
            "iban",
        ),
    },
    "fk_constraints": {
        "fk_conti_bancari_bank_branches": (
            E_ANAG_FK, "Filiale bancaria non trovata.", "bank_branch_id",
        ),
    },
}


# Traduttori degli errori DB dei due legami (BB `make_db_errors_translator`):
# un vincolo non mappato esce `E_ANAG_VALIDAZIONE` generico (mai «duplicato»),
# un RAISE di trigger col suo codice; `context.op` nomina l'operazione.
_db_errors_legame_soggetto = make_db_errors_translator(
    fn_prefix="anagrafiche.conto_soggetto",
    fallback_code=E_ANAG_VALIDAZIONE,
    fallback_message="Associazione conto bancario non valida.",
    **_VINCOLI_LEGAME_SOGGETTO,
)
_db_errors_legame_ruolo = make_db_errors_translator(
    fn_prefix="anagrafiche.conto_ruolo",
    fallback_code=E_ANAG_VALIDAZIONE,
    fallback_message="Associazione conto bancario non valida.",
    **_VINCOLI_LEGAME_RUOLO,
)
_db_errors_conto = make_db_errors_translator(
    fn_prefix="anagrafiche.conto_bancario",
    fallback_code=E_ANAG_VALIDAZIONE,
    fallback_message="Conto bancario non valido.",
    **_VINCOLI_CONTO,
)


# Scopo: l'`uso` del payload normalizzato (maiuscolo, senza spazi) e validato
#        contro `_USI_LEGAME`; None se assente o vuoto. UNA regola per create e
#        PATCH: prima la PATCH lo passava grezzo e «incasso», accettato in
#        create, in update cadeva sul CHECK del DB.
def _normalizza_uso(payload: dict[str, Any]) -> str | None:
    uso = optional_str(payload, "uso")
    if not uso:
        return None
    uso_upper = uso.upper().strip()
    ErrorManager.require(
        uso_upper in _USI_LEGAME,
        code=E_ANAG_VALIDAZIONE,
        message=f"Tipo d'uso non valido: {uso}. {_MSG_USO}",
        context={"field": "uso"},
    )
    return uso_upper


# Scopo: il payload di una PATCH di legame con i flag presenti letti come
#        booleani JSON (copia: `payload` e' spesso `request.data`, non si muta
#        l'input).
# ⛔ I flag passavano crudi al repository: `"abc"` era un errore di cast del
#    DB. Un flag presente vuole un booleano.
_FLAG_LEGAME: tuple[str, ...] = ("predefinito", "verificato", "bloccato")


def _payload_patch(payload: dict[str, Any]) -> dict[str, Any]:
    normalizzato = {**payload}
    for flag in _FLAG_LEGAME:
        if flag in payload:
            normalizzato[flag] = _V.require_bool(payload, flag)
    return normalizzato


# Scopo: le righe di una lista di legami, ognuna con i suoi campi fermi.
# ⭐ Trasporta, non deduce (BB `compute_non_editable_fields`): sono i
#    lucchetti di colonna vivi del DB sulla tabella del legame (conto, `uso`,
#    possessore: giro T8a). Il form li spegne in modifica col BB FE
#    `campoFermo` e li toglie dal PATCH con `senzaCampiFermi`, senza scrivere
#    nomi di campo. Statici per tabella: si leggono una volta per lista.
def _con_campi_fermi(righe: list[dict[str, Any]], tabella: str) -> list[dict[str, Any]]:
    fermi = compute_non_editable_fields("anagrafiche", tabella)
    return [{**r, "non_editable_fields": fermi} for r in righe]


class ContiBancariService:
    """Service per gestione conti bancari: registro, legami soggetto/ruolo, filiali."""

    def __init__(self) -> None:
        self._repo = ContiBancariRepository()
        self._soggetti = SoggettiRepository()

    # =================================================================
    # Lookup registro IBAN e filiali
    # =================================================================

    # Scopo: Ricerca IBAN nel registro per autocomplete.
    def search_conti_bancari(self, search: str, limit: int = 10) -> list[dict[str, Any]]:
        search = (search or "").strip()
        if len(search) < 2:
            return []
        return self._repo.search_conti_bancari(search, limit)

    # Scopo: Ricerca filiali bancarie per autocomplete.
    def search_bank_branches(self, search: str, limit: int = 10) -> list[dict[str, Any]]:
        search = (search or "").strip()
        if len(search) < 2:
            return []
        return self._repo.search_bank_branches(search, limit)

    # =================================================================
    # Conti bancari soggetto
    # =================================================================

    # Scopo: Lista conti bancari associati a un soggetto.
    def list_conti_soggetto(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return _con_campi_fermi(
            self._repo.list_conti_soggetto(soggetto_id), "soggetti_conti_bancari",
        )

    # Scopo: Crea legame soggetto ↔ conto bancario.
    #        Obiettivo: riceve IBAN + dati dal frontend, risolve (get_or_create)
    #        il registro, poi crea il legame. Transazione atomica.
    #        Risultato: dict con id del legame creato.
    def create_conto_soggetto(
        self, soggetto_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        from django.db import transaction

        self._require_soggetto_exists(soggetto_id)
        legame_payload = self._extract_legame_payload(payload)

        # Fix analisi-fix-transazioni #14 (Classe D): il get_or_create del registro
        # IBAN (_resolve_conto_bancario, una scrittura) e la create del legame in UN
        # solo transaction.atomic(). Prima il resolve era FUORI dall'atomic → una
        # riga IBAN di registro restava orfana se la create del legame falliva
        # (dedup riutilizzabile, non corruzione, ma comunque scrittura sospesa).
        # ⭐ Il traduttore del legame sta FUORI dall'atomic (giro T8a, D-T8a-1 a):
        #    «il conto del legame e' attivo» lo controlla il REQUIRE differito
        #    del DB alla chiusura della transazione, e il suo
        #    `E_ATTIVO_PADRE_NON_ATTIVO` deve passare di qui col contesto.
        with _db_errors_legame_soggetto("crea"), transaction.atomic():
            conto_bancario_id = self._resolve_conto_bancario(payload)
            result: dict[str, Any] = self._repo.create_conto_soggetto(
                soggetto_id,
                conto_bancario_id=conto_bancario_id,
                **legame_payload,
            )
        return result

    # Scopo: Aggiorna legame soggetto ↔ conto con ownership check.
    def update_conto_soggetto(
        self, soggetto_id: str, conto_soggetto_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_LEGAME_SOGGETTO_KEYS, message=_MESSAGE_LEGAME,
        )
        _V.require_campi_da_aggiornare(payload)
        payload = _payload_patch(payload)
        self._require_soggetto_exists(soggetto_id)
        with _db_errors_legame_soggetto("aggiorna"):
            updated = self._repo.update_conto_soggetto(
                conto_soggetto_id, soggetto_id, payload,
            )
        ErrorManager.require(
            updated, code=E_ANAG_NOT_FOUND, message=_MSG_LEGAME_NOT_FOUND,
        )
        return {"updated": True}

    # Scopo: Elimina legame soggetto ↔ conto con ownership check.
    def delete_conto_soggetto(
        self, soggetto_id: str, conto_soggetto_id: int,
    ) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_conto_soggetto(conto_soggetto_id, soggetto_id)
        ErrorManager.require(
            deleted, code=E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
            message=_MSG_LEGAME_NOT_FOUND,
        )
        return {"deleted": True}

    # =================================================================
    # Conti bancari ruolo
    # =================================================================

    # Scopo: Lista conti bancari associati a un ruolo, con cascata 3 livelli per uso.
    #        Cascata: istanza specifica → ruolo generico (NULL) → soggetto.
    #        Se istanza_utility_id e' None (ruoli senza istanza), la cascata parte
    #        dal livello 2 (ruolo generico) e fallback su soggetto.
    def list_conti_ruolo(
        self, soggetto_ruolo_id: int, istanza_utility_id: int | None = None,
    ) -> dict[str, Any]:
        conti_ruolo = _con_campi_fermi(
            self._repo.list_conti_ruolo(soggetto_ruolo_id), "soggetti_ruoli_conti_bancari",
        )
        conti_ereditati = self._repo.list_conti_ereditati_ruolo(soggetto_ruolo_id)

        editabili: list[dict[str, Any]] = []
        usi_coperti: set[str] = set()

        if istanza_utility_id is not None:
            # L1: ruolo + istanza specifica
            for c in conti_ruolo:
                uso = c.get("uso")
                if c.get("istanza_utility_id") == istanza_utility_id:
                    editabili.append({**c, "fonte": "istanza"})
                    if uso is not None:
                        usi_coperti.add(uso)

        # L2: ruolo generico (istanza NULL) — usi non ancora coperti
        for c in conti_ruolo:
            uso = c.get("uso")
            if c.get("istanza_utility_id") is None and uso not in usi_coperti:
                editabili.append({**c, "fonte": "ruolo"})
                if uso is not None:
                    usi_coperti.add(uso)

        # L3: soggetto (fallback readonly) — usi non ancora coperti
        readonly = [
            {**c, "fonte": "soggetto"}
            for c in conti_ereditati if c.get("uso") not in usi_coperti
        ]

        return {
            "conti_ruolo": editabili,
            "conti_ereditati": readonly,
        }

    # Scopo: Crea legame ruolo ↔ conto bancario con istanza_utility_id opzionale.
    #        Stessa logica di create_conto_soggetto ma per ruolo.
    def create_conto_ruolo(
        self, soggetto_ruolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        from django.db import transaction

        legame_payload = self._extract_legame_payload(payload)
        # istanza_utility_id opzionale (NULL = generico ruolo)
        istanza_utility_id = _V.optional_int(payload, "istanza_utility_id")
        if istanza_utility_id is not None:
            legame_payload["istanza_utility_id"] = istanza_utility_id

        # Fix analisi-fix-transazioni #15 (Classe D): get_or_create IBAN + create
        # legame in UN solo transaction.atomic() (vedi #14). Prima il resolve era
        # fuori → riga IBAN registro orfana se la create legame falliva.
        # ⭐ Traduttore fuori dall'atomic: il rifiuto differito al COMMIT (vedi
        #    create_conto_soggetto).
        with _db_errors_legame_ruolo("crea"), transaction.atomic():
            conto_bancario_id = self._resolve_conto_bancario(payload)
            result: dict[str, Any] = self._repo.create_conto_ruolo(
                soggetto_ruolo_id,
                conto_bancario_id=conto_bancario_id,
                **legame_payload,
            )
        return result

    # Scopo: Aggiorna legame ruolo ↔ conto con ownership check.
    def update_conto_ruolo(
        self, soggetto_ruolo_id: int, conto_ruolo_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_LEGAME_RUOLO_KEYS, message=_MESSAGE_LEGAME,
        )
        _V.require_campi_da_aggiornare(payload)
        payload = _payload_patch(payload)
        with _db_errors_legame_ruolo("aggiorna"):
            updated = self._repo.update_conto_ruolo(
                conto_ruolo_id, soggetto_ruolo_id, payload,
            )
        ErrorManager.require(
            updated, code=E_ANAG_NOT_FOUND, message=_MSG_LEGAME_NOT_FOUND,
        )
        return {"updated": True}

    # Scopo: Elimina legame ruolo ↔ conto con ownership check.
    def delete_conto_ruolo(
        self, soggetto_ruolo_id: int, conto_ruolo_id: int,
    ) -> dict[str, Any]:
        deleted = self._repo.delete_conto_ruolo(conto_ruolo_id, soggetto_ruolo_id)
        ErrorManager.require(
            deleted, code=E_ANAG_CONTO_SOGGETTO_NOT_FOUND,
            message=_MSG_LEGAME_NOT_FOUND,
        )
        return {"deleted": True}

    # =================================================================
    # Metodi interni
    # =================================================================

    # Scopo: Risolve conto_bancario_id dal payload.
    #        Se il payload ha gia' conto_bancario_id, lo usa direttamente.
    #        Altrimenti usa IBAN per get_or_create nel registro.
    #        Risultato: conto_bancario_id valido.
    def _resolve_conto_bancario(self, payload: dict[str, Any]) -> int:
        conto_id = _V.optional_int(payload, "conto_bancario_id")
        if conto_id is not None:
            # Verifica che il conto esista
            conto = self._repo.get_conto_bancario(conto_id)
            ErrorManager.require(
                conto is not None, code=E_ANAG_CONTO_NOT_FOUND, message=_MSG_CONTO_FK,
            )
            return conto_id

        # Risolve da IBAN, scritto come lo si legge: forma e formato li
        # giudica il DB (vedi `_VINCOLI_CONTO`), anche la coerenza con la
        # filiale (`E_CONTO_IBAN_FILIALE_INCOERENTE`, D-T8a-9).
        iban = require_str(payload, "iban", "IBAN obbligatorio.")
        bank_branch_id = _V.optional_int(payload, "bank_branch_id")
        ErrorManager.require(
            bank_branch_id is not None and bank_branch_id > 0,
            code=E_ANAG_VALIDAZIONE,
            message="Filiale bancaria obbligatoria.",
        )
        assert bank_branch_id is not None

        with _db_errors_conto("registra"):
            conto_id, _created = self._repo.get_or_create_conto_bancario(
                iban=iban,
                bic_swift=optional_str(payload, "bic_swift"),
                bank_branch_id=bank_branch_id,
                intestatario_predefinito=optional_str(payload, "intestatario_predefinito"),
            )
        return conto_id

    # Scopo: Estrae i campi del legame (soggetto o ruolo) dal payload.
    #        Separa i dati registro (iban, bic, banca) dai dati legame (uso, predefinito, ecc.).
    #        Per i booleani controlla la presenza della chiave nel payload:
    #        optional_bool ritorna sempre bool (mai None), quindi non si puo'
    #        distinguere "non inviato" da "inviato come False" dal valore di ritorno.
    def _extract_legame_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}

        uso = _normalizza_uso(payload)
        if uso is not None:
            result["uso"] = uso

        # Booleani: includi solo se la chiave e' presente nel payload
        for bool_key in _FLAG_LEGAME:
            if bool_key in payload:
                # Un `null` esplicito vale False, come prima della lettura del dominio.
                result[bool_key] = bool(_V.optional_bool(payload, bool_key))

        # Stringhe/date opzionali
        for str_key in ("valido_dal", "valido_al", "intestazione_dichiarata"):
            val = optional_str(payload, str_key)
            if val is not None:
                result[str_key] = val

        return result

    # Scopo: Guard leggero — verifica che il soggetto esista.
    def _require_soggetto_exists(self, soggetto_id: str) -> None:
        exists = self._soggetti.exists_soggetto(soggetto_id)
        ErrorManager.require(exists, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
