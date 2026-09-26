# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facciata delle tre ANAGRAFICHE di `magazzino` — magazzini, ubicazioni
#        (figlie del magazzino), lotti (figli dell'articolo). Orchestrazione
#        sottile: validazione del payload, 404 no-leak, traduzione degli errori
#        del database, composizione della risposta paginata.
# Note: 🔴 Le regole vivono nel database e qui NON si riscrivono: il codice
#       del magazzino e' lockato (`E_CODICE_NON_MODIFICABILE`), `usa_ubicazioni`
#       si cambia solo a registro vuoto (`E_MAG_MAGAZZINO_CON_GIACENZA`), la
#       disattivazione con figli attivi e' rifiutata
#       (`E_ATTIVO_BLOCK_CHILDREN_EXIST`), il padre dell'ubicazione e' dello
#       stesso magazzino e senza cicli (`E_MAG_UBICAZIONE_PADRE_*`), il
#       magazzino dell'ubicazione e' immutabile (lock,
#       `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`), la scadenza del lotto e' >=
#       dell'arrivo (`chk_mag_lotti_scadenza_dopo_arrivo`), l'articolo del
#       lotto e' attivo (`E_ATTIVO_REQUIRE`). Il service esegue e traduce.
#
#       ⭐ `emittente_fiscale_id` del magazzino NON viaggia nel payload: lo
#       mette `trgfn_default_emittente_fiscale('SOLLEVA')` dalla GUC. L'admin
#       globale su «tutti gli emittenti» prende `E_EMITTENTE_NON_RISOLTO` (400
#       col campo) — la regola e' del DB (piano §4.1).
#
#       Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6;
#       codici: brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici R-2.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    MISSING,
    PayloadValidator,
    make_db_errors_translator,
)
from apps.magazzino.db.anagrafiche_magazzino_repository import (
    LOTTI_COLONNE,
    LOTTI_SORT_COLUMNS,
    MAGAZZINI_COLONNE,
    MAGAZZINI_SORT_COLUMNS,
    UBICAZIONI_COLONNE,
    UBICAZIONI_SORT_COLUMNS,
    AnagraficheMagazzinoRepository,
)
from apps.magazzino.services._helpers import (
    E_VALIDAZIONE,
    articolo_uuid,
    ordinamento_validato,
    risposta_paginata as _risposta,
)
from apps.magazzino.types import LottoRow, MagazzinoRow, UbicazioneRow

_FN = "magazzino.anagrafiche_magazzino_service"

# I tre 404 di dominio (R-2, a catalogo dal 2026-09-21, classe NON_TROVATO):
# la riga non c'e' — inesistente o fuori dal perimetro RLS, e i due restano
# indistinguibili di proposito.
E_MAGAZZINO_NON_TROVATO = "E_MAG_MAGAZZINO_NON_TROVATO"
E_UBICAZIONE_NON_TROVATA = "E_MAG_UBICAZIONE_NON_TROVATA"
E_LOTTO_NON_TROVATO = "E_MAG_LOTTO_NON_TROVATO"

# Il duplicato di anagrafica, come per le altre anagrafiche del progetto.
E_DUPLICATO = "E_ANAG_DUPLICATO"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

# Lunghezze massime dei testi (le colonne sono `varchar` senza limite
# dichiarato: il tetto e' un cancello di buon senso, non una regola del DB).
_MAX_CODICE = 50
_MAX_DESCRIZIONE = 500
_MAX_POSIZIONE = 50

# Traduzione degli errori del database: i VINCOLI con nome parlano qui
# (UNIQUE col campo, FK col campo, CHECK col campo); i guard e i lock del DB
# sollevano codici registrati e passano INTATTI da `translate_db_errors`.
_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    "uq_magazzini_codice": (E_DUPLICATO, "Esiste gia' un magazzino con questo codice.", "codice"),
    "uq_mag_ubicazioni_mag_codice": (
        E_DUPLICATO, "Esiste gia' un'ubicazione con questo codice nel magazzino.", "codice",
    ),
    "uq_mag_lotti_articolo_codice": (
        E_DUPLICATO, "Esiste gia' un lotto con questo codice per l'articolo.", "codice",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_magazzini_indirizzo_dettaglio": (E_VALIDAZIONE, "Indirizzo non valido.", "indirizzo_dettaglio_id"),
    "fk_mag_tipi_ubicazione_magazzino": (E_VALIDAZIONE, "Tipo di ubicazione non valido.", "tipo_id"),
    "fk_mag_ubicazioni_parent": (E_VALIDAZIONE, "Ubicazione padre non valida.", "parent_id"),
    "fk_mag_lotti_articolo": (E_VALIDAZIONE, "Articolo non valido.", "articolo_id"),
}
_CHECK_CONSTRAINTS: dict[str, tuple] = {
    "chk_magazzini_codice_nonvuoto": (E_VALIDAZIONE, "Il codice del magazzino non puo' essere vuoto.", "codice"),
    "chk_mag_lotti_codice_non_vuoto": (E_VALIDAZIONE, "Il codice del lotto non puo' essere vuoto.", "codice"),
    "chk_mag_lotti_scadenza_dopo_arrivo": (
        E_VALIDAZIONE, "La data di scadenza non puo' precedere la data di arrivo.", "data_scadenza",
    ),
}

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo sull'anagrafica di magazzino.",
    unique_constraints=_UNIQUE_CONSTRAINTS,
    fk_constraints=_FK_CONSTRAINTS,
    check_constraints=_CHECK_CONSTRAINTS,
)


# ══════════════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════════════

# Scopo: Un boolean OBBLIGATORIO quando la chiave c'e' (le colonne sono NOT
#        NULL): `null` non e' un valore ammesso in un PATCH.
def _bool_presente(payload: dict[str, Any], key: str) -> bool:
    valore = _PAYLOAD.optional_bool(payload, key)
    ErrorManager.require(
        valore is not None,
        code=E_VALIDAZIONE,
        message=f"Campo '{key}' deve essere vero o falso.",
        context={"field": key},
        function_name=_FN,
    )
    assert valore is not None
    return valore


# Scopo: Un intero positivo NULLABLE quando la chiave c'e' (`parent_id`):
#        `null` AZZERA, un valore va validato.
def _int_nullable_presente(payload: dict[str, Any], key: str) -> int | None:
    if payload.get(key) is None:
        return None
    return _PAYLOAD.require_positive_int(payload, key)


# Scopo: I campi testuali di un PATCH, presenti nel payload: `None`/vuoto
#        azzera i nullable, e' un 400 sugli obbligatori.
def _testi_presenti(
    payload: dict[str, Any], campi: dict[str, Any], *, obbligatori: dict[str, int], nullable: dict[str, int],
) -> None:
    for key, max_len in obbligatori.items():
        if key in payload:
            campi[key] = _PAYLOAD.require_string(payload, key, max_len=max_len)
    for key, max_len in nullable.items():
        valore = _PAYLOAD.extract_optional_string(payload, key, nullable=True, max_len=max_len)
        if valore is not MISSING:
            campi[key] = valore


# Scopo: Legge il magazzino o solleva il 404 di dominio — PRIMA di ogni
#        figlia (api.md: «leggi prima la testata»).
def _magazzino_o_404(repository: AnagraficheMagazzinoRepository, magazzino_id: int) -> MagazzinoRow:
    magazzino = repository.get_magazzino(magazzino_id)
    ErrorManager.require(
        magazzino is not None,
        code=E_MAGAZZINO_NON_TROVATO,
        message="Magazzino non trovato.",
        detail=f"magazzino_id={magazzino_id}",
        function_name=_FN,
    )
    assert magazzino is not None
    return magazzino


# Scopo: Legge l'ubicazione DEL magazzino o solleva il 404: la coppia e' la
#        risorsa dell'URL, e un'ubicazione di un altro magazzino «non c'e'».
def _ubicazione_o_404(
    repository: AnagraficheMagazzinoRepository, magazzino_id: int, ubicazione_id: int,
) -> UbicazioneRow:
    ubicazione = repository.get_ubicazione(magazzino_id, ubicazione_id)
    ErrorManager.require(
        ubicazione is not None,
        code=E_UBICAZIONE_NON_TROVATA,
        message="Ubicazione non trovata.",
        detail=f"magazzino_id={magazzino_id} ubicazione_id={ubicazione_id}",
        function_name=_FN,
    )
    assert ubicazione is not None
    return ubicazione


# Scopo: Legge il lotto o solleva il 404.
def _lotto_o_404(repository: AnagraficheMagazzinoRepository, lotto_id: int) -> LottoRow:
    lotto = repository.get_lotto(lotto_id)
    ErrorManager.require(
        lotto is not None,
        code=E_LOTTO_NON_TROVATO,
        message="Lotto non trovato.",
        detail=f"lotto_id={lotto_id}",
        function_name=_FN,
    )
    assert lotto is not None
    return lotto


# ══════════════════════════════════════════════════════════════════
#  Magazzini
# ══════════════════════════════════════════════════════════════════

# Le chiavi ammesse nel payload SONO le colonne scrivibili del repository: un
# solo elenco (rilettura del 2026-09-21 — erano due copie identiche, e una
# chiave aggiunta a una sola delle due sarebbe stata validata e poi scartata in
# silenzio dal filtro dell'altra).
_CHIAVI_MAGAZZINO = MAGAZZINI_COLONNE
# I contratti di scrittura, con un nome: li legge anche lo schema OpenAPI
# (`magazzino/api/views_anagrafiche.py`). `attivo` nasce vero: non si manda.
CREATE_KEYS_MAGAZZINO: frozenset[str] = _CHIAVI_MAGAZZINO - {"attivo"}
UPDATE_KEYS_MAGAZZINO: frozenset[str] = _CHIAVI_MAGAZZINO


# Scopo: L'elenco paginato dei magazzini del perimetro.
def list_magazzini(
    *,
    auth_user_id: int | None,
    search: str | None = None,
    attivo: bool | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=MAGAZZINI_SORT_COLUMNS, function_name=f"{_FN}.list_magazzini",
    )
    results, total = AnagraficheMagazzinoRepository().list_magazzini(
        auth_user_id=auth_user_id, search=search, attivo=attivo,
        order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return _risposta(results, total)


# Scopo: Il dettaglio del magazzino; 404 no-leak.
def get_magazzino(magazzino_id: int) -> MagazzinoRow:
    return _magazzino_o_404(AnagraficheMagazzinoRepository(), magazzino_id)


# Scopo: Crea il magazzino: `codice`, `descrizione`, `indirizzo_dettaglio_id`
#        obbligatori; i flag opzionali (default del DB). ⛔ `attivo` non si
#        sceglie alla nascita: un magazzino nasce attivo.
def crea_magazzino(payload: dict[str, Any]) -> MagazzinoRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=CREATE_KEYS_MAGAZZINO)
    valori: dict[str, Any] = {
        "codice": _PAYLOAD.require_string(payload, "codice", max_len=_MAX_CODICE),
        "descrizione": _PAYLOAD.require_string(payload, "descrizione", max_len=_MAX_DESCRIZIONE),
        "indirizzo_dettaglio_id": _PAYLOAD.require_positive_int(payload, "indirizzo_dettaglio_id"),
    }
    for flag in ("usa_ubicazioni", "predefinito"):
        valore = _PAYLOAD.optional_bool(payload, flag)
        if valore is not None:
            valori[flag] = valore
    meta = _PAYLOAD.optional_meta(payload, "meta")
    if meta is not None:
        valori["meta"] = meta
    repository = AnagraficheMagazzinoRepository()
    with _db_errors("crea_magazzino"):
        magazzino_id = repository.create_magazzino(valori)
    return _magazzino_o_404(repository, magazzino_id)


# Scopo: Aggiorna il magazzino per DELTA: solo le chiavi presenti viaggiano,
#        cosi' il lock su `codice` scatta solo se il codice cambia davvero e
#        il guard su `usa_ubicazioni` solo se lo si tocca.
def aggiorna_magazzino(magazzino_id: int, payload: dict[str, Any]) -> MagazzinoRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=UPDATE_KEYS_MAGAZZINO)
    repository = AnagraficheMagazzinoRepository()
    _magazzino_o_404(repository, magazzino_id)
    campi: dict[str, Any] = {}
    _testi_presenti(
        payload, campi,
        obbligatori={"codice": _MAX_CODICE, "descrizione": _MAX_DESCRIZIONE}, nullable={},
    )
    if "indirizzo_dettaglio_id" in payload:
        campi["indirizzo_dettaglio_id"] = _PAYLOAD.require_positive_int(payload, "indirizzo_dettaglio_id")
    for flag in ("usa_ubicazioni", "predefinito", "attivo"):
        if flag in payload:
            campi[flag] = _bool_presente(payload, flag)
    if "meta" in payload:
        campi["meta"] = _PAYLOAD.optional_meta(payload, "meta")
    if campi:
        with _db_errors("aggiorna_magazzino"):
            repository.update_magazzino(magazzino_id, campi)
    return _magazzino_o_404(repository, magazzino_id)


# ══════════════════════════════════════════════════════════════════
#  Ubicazioni
# ══════════════════════════════════════════════════════════════════

_CHIAVI_UBICAZIONE = UBICAZIONI_COLONNE
CREATE_KEYS_UBICAZIONE: frozenset[str] = _CHIAVI_UBICAZIONE - {"attivo"}
UPDATE_KEYS_UBICAZIONE: frozenset[str] = _CHIAVI_UBICAZIONE
_POSIZIONE = {"area": _MAX_POSIZIONE, "corsia": _MAX_POSIZIONE, "scaffale": _MAX_POSIZIONE,
              "piano": _MAX_POSIZIONE, "posizione": _MAX_POSIZIONE}


# Scopo: Le ubicazioni di UN magazzino, paginate. Il perimetro e' la testata:
#        magazzino fuori scope ⇒ 404 prima di leggere le figlie.
def list_ubicazioni(
    magazzino_id: int,
    *,
    search: str | None = None,
    attivo: bool | None = None,
    parent_id: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=UBICAZIONI_SORT_COLUMNS, function_name=f"{_FN}.list_ubicazioni",
    )
    repository = AnagraficheMagazzinoRepository()
    _magazzino_o_404(repository, magazzino_id)
    results, total = repository.list_ubicazioni(
        magazzino_id=magazzino_id, search=search, attivo=attivo, parent_id=parent_id,
        order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return _risposta(results, total)


# Scopo: Il dettaglio dell'ubicazione del magazzino; 404 no-leak sulla coppia.
def get_ubicazione(magazzino_id: int, ubicazione_id: int) -> UbicazioneRow:
    repository = AnagraficheMagazzinoRepository()
    _magazzino_o_404(repository, magazzino_id)
    return _ubicazione_o_404(repository, magazzino_id, ubicazione_id)


# Scopo: Crea l'ubicazione nel magazzino del path: `codice` e `tipo_id`
#        obbligatori, `parent_id` facoltativo (stesso magazzino, senza cicli:
#        lo decide `trgfn_ubicazioni_guard_parent`).
def crea_ubicazione(magazzino_id: int, payload: dict[str, Any]) -> UbicazioneRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=CREATE_KEYS_UBICAZIONE)
    repository = AnagraficheMagazzinoRepository()
    _magazzino_o_404(repository, magazzino_id)
    valori: dict[str, Any] = {
        "codice": _PAYLOAD.require_string(payload, "codice", max_len=_MAX_CODICE),
        "tipo_id": _PAYLOAD.require_positive_int(payload, "tipo_id"),
    }
    descrizione = _PAYLOAD.optional_string(payload, "descrizione", max_len=_MAX_DESCRIZIONE)
    if descrizione is not None:
        valori["descrizione"] = descrizione
    parent_id = _PAYLOAD.optional_positive_int(payload, "parent_id")
    if parent_id is not None:
        valori["parent_id"] = parent_id
    for key, max_len in _POSIZIONE.items():
        valore = _PAYLOAD.optional_string(payload, key, max_len=max_len)
        if valore is not None:
            valori[key] = valore
    meta = _PAYLOAD.optional_meta(payload, "meta")
    if meta is not None:
        valori["meta"] = meta
    with _db_errors("crea_ubicazione"):
        ubicazione_id = repository.create_ubicazione(magazzino_id, valori)
    return _ubicazione_o_404(repository, magazzino_id, ubicazione_id)


# Scopo: Aggiorna l'ubicazione per DELTA. ⛔ `magazzino_id` non e' fra le
#        chiavi: un'ubicazione nasce dentro il suo magazzino (lock a DB).
def aggiorna_ubicazione(magazzino_id: int, ubicazione_id: int, payload: dict[str, Any]) -> UbicazioneRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=UPDATE_KEYS_UBICAZIONE)
    repository = AnagraficheMagazzinoRepository()
    _magazzino_o_404(repository, magazzino_id)
    _ubicazione_o_404(repository, magazzino_id, ubicazione_id)
    campi: dict[str, Any] = {}
    _testi_presenti(
        payload, campi,
        obbligatori={"codice": _MAX_CODICE},
        nullable={"descrizione": _MAX_DESCRIZIONE, **_POSIZIONE},
    )
    if "tipo_id" in payload:
        campi["tipo_id"] = _PAYLOAD.require_positive_int(payload, "tipo_id")
    if "parent_id" in payload:
        campi["parent_id"] = _int_nullable_presente(payload, "parent_id")
    if "attivo" in payload:
        campi["attivo"] = _bool_presente(payload, "attivo")
    if "meta" in payload:
        campi["meta"] = _PAYLOAD.optional_meta(payload, "meta")
    if campi:
        with _db_errors("aggiorna_ubicazione"):
            repository.update_ubicazione(magazzino_id, ubicazione_id, campi)
    return _ubicazione_o_404(repository, magazzino_id, ubicazione_id)


# ══════════════════════════════════════════════════════════════════
#  Lotti
# ══════════════════════════════════════════════════════════════════

# Piu' `articolo_id`: nel CREATE viaggia nel payload (non nel path), e il
# repository lo aggiunge lui alle colonne dell'INSERT.
_CHIAVI_LOTTO = LOTTI_COLONNE | {"articolo_id"}
# In modifica l'articolo non cambia: un lotto e' di quell'articolo.
CREATE_KEYS_LOTTO: frozenset[str] = _CHIAVI_LOTTO - {"attivo"}
UPDATE_KEYS_LOTTO: frozenset[str] = _CHIAVI_LOTTO - {"articolo_id"}


# Scopo: I lotti di UN articolo, paginati. `articolo_id` OBBLIGATORIO: un
#        elenco di tutti i lotti di tutti gli articoli non e' una domanda di
#        nessuno (piano §6).
def list_lotti(
    *,
    articolo_id: Any,
    search: str | None = None,
    attivo: bool | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    articolo = articolo_uuid(articolo_id, obbligatorio=True, function_name=f"{_FN}.list_lotti")
    assert articolo is not None
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=LOTTI_SORT_COLUMNS, function_name=f"{_FN}.list_lotti",
    )
    results, total = AnagraficheMagazzinoRepository().list_lotti(
        articolo_id=articolo, search=search, attivo=attivo,
        order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return _risposta(results, total)


# Scopo: Il dettaglio del lotto; 404.
def get_lotto(lotto_id: int) -> LottoRow:
    return _lotto_o_404(AnagraficheMagazzinoRepository(), lotto_id)


# Scopo: Crea il lotto dell'articolo: `articolo_id`, `codice`, `data_arrivo`
#        obbligatori; `data_scadenza` facoltativa (>= arrivo: lo dice il CHECK,
#        il BE traduce e non ricontrolla).
def crea_lotto(payload: dict[str, Any]) -> LottoRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=CREATE_KEYS_LOTTO)
    articolo = _PAYLOAD.require_uuid(payload, "articolo_id")
    valori: dict[str, Any] = {
        "codice": _PAYLOAD.require_string(payload, "codice", max_len=_MAX_CODICE),
        "data_arrivo": _PAYLOAD.require_date(payload, "data_arrivo"),
    }
    scadenza = _PAYLOAD.optional_date(payload, "data_scadenza")
    if scadenza is not None:
        valori["data_scadenza"] = scadenza
    meta = _PAYLOAD.optional_meta(payload, "meta")
    if meta is not None:
        valori["meta"] = meta
    repository = AnagraficheMagazzinoRepository()
    with _db_errors("crea_lotto"):
        lotto_id = repository.create_lotto(str(articolo), valori)
    return _lotto_o_404(repository, lotto_id)


# Scopo: Aggiorna il lotto per DELTA. ⛔ `articolo_id` non e' fra le chiavi:
#        un lotto nasce del suo articolo. `data_scadenza: null` la toglie.
def aggiorna_lotto(lotto_id: int, payload: dict[str, Any]) -> LottoRow:
    _PAYLOAD.validate_allowed_keys(payload, allowed=UPDATE_KEYS_LOTTO)
    repository = AnagraficheMagazzinoRepository()
    _lotto_o_404(repository, lotto_id)
    campi: dict[str, Any] = {}
    _testi_presenti(payload, campi, obbligatori={"codice": _MAX_CODICE}, nullable={})
    if "data_arrivo" in payload:
        campi["data_arrivo"] = _PAYLOAD.require_date(payload, "data_arrivo")
    if "data_scadenza" in payload:
        campi["data_scadenza"] = _PAYLOAD.optional_date(payload, "data_scadenza")
    if "attivo" in payload:
        campi["attivo"] = _bool_presente(payload, "attivo")
    if "meta" in payload:
        campi["meta"] = _PAYLOAD.optional_meta(payload, "meta")
    if campi:
        with _db_errors("aggiorna_lotto"):
            repository.update_lotto(lotto_id, campi)
    return _lotto_o_404(repository, lotto_id)
