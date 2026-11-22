# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facciata delle tre ANAGRAFICHE di `magazzino` — magazzini, ubicazioni
#        (figlie del magazzino), lotti (dell'articolo e dell'azienda).
#        Orchestrazione sottile: validazione del trasporto, 404 no-leak,
#        traduzione degli errori del database, risposta paginata.
# Note: 🔴 Le regole vivono nel database e qui NON si riscrivono: il codice
#       del magazzino e' lockato (`E_CODICE_NON_MODIFICABILE`), `usa_ubicazioni`
#       si cambia solo a registro vuoto (`E_MAG_MAGAZZINO_CON_GIACENZA`), la
#       disattivazione con figli attivi e' rifiutata
#       (`E_ATTIVO_BLOCK_CHILDREN_EXIST`), il padre dell'ubicazione e' dello
#       stesso magazzino e senza cicli (`E_MAG_UBICAZIONE_PADRE_*`), il
#       magazzino dell'ubicazione e' immutabile (lock,
#       `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE`), la scadenza del lotto e' >=
#       dell'arrivo (`chk_mag_lotti_scadenza_dopo_arrivo`), l'articolo del
#       lotto e' attivo (`E_ATTIVO_PADRE_NON_ATTIVO`, 409 col campo). Il
#       service esegue e traduce.
#
#       ⭐ `emittente_fiscale_id` del magazzino NON viaggia nel payload: lo
#       mette `trgfn_default_emittente_fiscale('SOLLEVA')` dalla GUC. L'admin
#       globale su «tutti gli emittenti» prende `E_EMITTENTE_NON_RISOLTO` (400
#       col campo) — la regola e' del DB (piano §4.1).
#
#       ⭐ 2026-11-22 — le scritture dal VERBO (R-1 di
#       brief-db-magazzino-tutte-le-scritture-dal-verbo): il repository chiama
#       `magazzino.fn_aggiungi_*` / `fn_modifica_*`, che controllano il livello
#       `TUTTO` sull'oggetto e il perimetro. Le chiavi AMMESSE le dice il DB
#       (`fn_<tabella>_colonne_ammesse`, D-M4), lette a ogni scrittura; qui
#       resta il TRASPORTO (tipo, obbligo, lunghezza di ogni chiave). Se il DB
#       ammette una chiave che qui non si sa leggere, o viceversa,
#       `campi_per_presenza` alza un `RuntimeError` (500): mai uno scarto
#       silenzioso. Lo stesso controllo, sul DB vero, e' nei test `tests/db/`.
#
#       Piano: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config §4-6;
#       codici: brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici R-2.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from typing import Any, TypedDict

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.magazzino.db.anagrafiche_magazzino_repository import (
    LOTTI_SORT_COLUMNS,
    MAGAZZINI_SORT_COLUMNS,
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
    # Dal 2026-11-22 il codice del lotto e' unico nell'AZIENDA (D-L2 di
    # brief-db-magazzino-lotto-dell-azienda, `20261122-14`).
    "uq_mag_lotti_emittente_articolo_codice": (
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
#  Il contratto delle scritture: le chiavi dal DB, il trasporto da qui
# ══════════════════════════════════════════════════════════════════

_Lettore = Callable[[dict[str, Any], str], Any]


# I lettori del trasporto di un gesto, nei gruppi di `campi_per_presenza`.
class _Lettura(TypedDict, total=False):
    testi: Mapping[str, tuple[bool, int | None]]
    interi: Mapping[str, bool]
    flag: Collection[str]
    altri: Mapping[str, _Lettore]


# Scopo: Le chiavi che una lettura sa leggere: lo schema OpenAPI del corpo.
def _chiavi(lettura: _Lettura) -> frozenset[str]:
    return frozenset({
        *lettura.get("testi", {}), *lettura.get("interi", {}),
        *lettura.get("flag", ()), *lettura.get("altri", {}),
    })


# Scopo: Il payload di un gesto, letto sul contratto del DB: le chiavi ammesse
#        sono `fn_<tabella>_colonne_ammesse(gesto)` (piu' le `identita` che il
#        payload porta e il verbo riceve come argomento, l'articolo del
#        lotto). Gli `obbligatori` della nascita devono esserci; il resto lo
#        legge `campi_per_presenza`, che rifiuta (400) la chiave fuori
#        contratto e alza un `RuntimeError` se il DB e i lettori divergono.
def _campi_del_gesto(
    repository: AnagraficheMagazzinoRepository,
    payload: dict[str, Any],
    *,
    tabella: str,
    gesto: str,
    lettura: _Lettura,
    obbligatori: tuple[str, ...] = (),
    identita: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    for chiave in obbligatori:
        ErrorManager.require(
            chiave in payload,
            code=E_VALIDAZIONE,
            message=f"Campo '{chiave}' obbligatorio.",
            context={"field": chiave},
            function_name=_FN,
        )
    ammesse = repository.colonne_ammesse(tabella, gesto) | identita
    return _PAYLOAD.campi_per_presenza(payload, ammesse=ammesse, function_name=_FN, **lettura)


# ══════════════════════════════════════════════════════════════════
#  Magazzini
# ══════════════════════════════════════════════════════════════════

# Il trasporto delle chiavi, per gesto. ⛔ `attivo` non si sceglie alla
# nascita (un magazzino nasce attivo): non e' nella lista `'crea'` del DB.
_NASCITA_MAGAZZINO: _Lettura = {
    "testi": {"codice": (False, _MAX_CODICE), "descrizione": (False, _MAX_DESCRIZIONE)},
    "interi": {"indirizzo_dettaglio_id": False},
    "altri": {
        "usa_ubicazioni": _PAYLOAD.optional_bool,
        "predefinito": _PAYLOAD.optional_bool,
        "meta": _PAYLOAD.optional_meta,
    },
}
_MODIFICA_MAGAZZINO: _Lettura = {
    "testi": {"codice": (False, _MAX_CODICE), "descrizione": (False, _MAX_DESCRIZIONE)},
    "interi": {"indirizzo_dettaglio_id": False},
    "flag": frozenset({"usa_ubicazioni", "predefinito", "attivo"}),
    "altri": {"meta": _PAYLOAD.optional_meta},
}
# I contratti di scrittura, con un nome: li legge lo schema OpenAPI
# (`magazzino/api/views_anagrafiche.py`). Sono le chiavi che il backend sa
# LEGGERE; quelle AMMESSE le dice il DB, e un test sul DB vero le confronta.
CREATE_KEYS_MAGAZZINO: frozenset[str] = _chiavi(_NASCITA_MAGAZZINO)
UPDATE_KEYS_MAGAZZINO: frozenset[str] = _chiavi(_MODIFICA_MAGAZZINO)


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
#        obbligatori; i flag opzionali (default del DB).
def crea_magazzino(payload: dict[str, Any]) -> MagazzinoRow:
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="magazzini", gesto="crea", lettura=_NASCITA_MAGAZZINO,
        obbligatori=("codice", "descrizione", "indirizzo_dettaglio_id"),
    )
    with _db_errors("crea_magazzino"):
        magazzino_id = repository.create_magazzino(
            codice=campi.pop("codice"),
            descrizione=campi.pop("descrizione"),
            indirizzo_dettaglio_id=campi.pop("indirizzo_dettaglio_id"),
            campi=campi,
        )
    return _magazzino_o_404(repository, magazzino_id)


# Scopo: Aggiorna il magazzino per DELTA: solo le chiavi presenti viaggiano,
#        cosi' il lock su `codice` scatta solo se il codice cambia davvero e
#        il guard su `usa_ubicazioni` solo se lo si tocca. Chiave fuori
#        contratto e PATCH senza campi sono un 400 (Tid, 2026-10-20).
def aggiorna_magazzino(magazzino_id: int, payload: dict[str, Any]) -> MagazzinoRow:
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="magazzini", gesto="modifica", lettura=_MODIFICA_MAGAZZINO,
    )
    _magazzino_o_404(repository, magazzino_id)
    with _db_errors("aggiorna_magazzino"):
        repository.update_magazzino(magazzino_id, campi)
    return _magazzino_o_404(repository, magazzino_id)


# ══════════════════════════════════════════════════════════════════
#  Ubicazioni
# ══════════════════════════════════════════════════════════════════

_POSIZIONE = {"area": _MAX_POSIZIONE, "corsia": _MAX_POSIZIONE, "scaffale": _MAX_POSIZIONE,
              "piano": _MAX_POSIZIONE, "posizione": _MAX_POSIZIONE}
# ⛔ `magazzino_id` non e' fra le chiavi: un'ubicazione nasce dentro il
# magazzino del path (argomento del verbo) e non ne esce (lock a DB).
_TESTI_UBICAZIONE: dict[str, tuple[bool, int | None]] = {
    "codice": (False, _MAX_CODICE), "descrizione": (True, _MAX_DESCRIZIONE),
    **{key: (True, max_len) for key, max_len in _POSIZIONE.items()},
}
_NASCITA_UBICAZIONE: _Lettura = {
    "testi": _TESTI_UBICAZIONE,
    "interi": {"tipo_id": False, "parent_id": True},
    "altri": {"meta": _PAYLOAD.optional_meta},
}
_MODIFICA_UBICAZIONE: _Lettura = {
    "testi": _TESTI_UBICAZIONE,
    "interi": {"tipo_id": False, "parent_id": True},
    "flag": frozenset({"attivo"}),
    "altri": {"meta": _PAYLOAD.optional_meta},
}
CREATE_KEYS_UBICAZIONE: frozenset[str] = _chiavi(_NASCITA_UBICAZIONE)
UPDATE_KEYS_UBICAZIONE: frozenset[str] = _chiavi(_MODIFICA_UBICAZIONE)


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
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="ubicazioni", gesto="crea", lettura=_NASCITA_UBICAZIONE,
        obbligatori=("codice", "tipo_id"),
    )
    _magazzino_o_404(repository, magazzino_id)
    with _db_errors("crea_ubicazione"):
        ubicazione_id = repository.create_ubicazione(
            magazzino_id, codice=campi.pop("codice"), tipo_id=campi.pop("tipo_id"), campi=campi,
        )
    return _ubicazione_o_404(repository, magazzino_id, ubicazione_id)


# Scopo: Aggiorna l'ubicazione per DELTA, dentro il SUO magazzino.
def aggiorna_ubicazione(magazzino_id: int, ubicazione_id: int, payload: dict[str, Any]) -> UbicazioneRow:
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="ubicazioni", gesto="modifica", lettura=_MODIFICA_UBICAZIONE,
    )
    _magazzino_o_404(repository, magazzino_id)
    _ubicazione_o_404(repository, magazzino_id, ubicazione_id)
    with _db_errors("aggiorna_ubicazione"):
        repository.update_ubicazione(magazzino_id, ubicazione_id, campi)
    return _ubicazione_o_404(repository, magazzino_id, ubicazione_id)


# ══════════════════════════════════════════════════════════════════
#  Lotti
# ══════════════════════════════════════════════════════════════════

# `articolo_id` viaggia nel payload della nascita (non nel path) ed e' un
# argomento del verbo, non una colonna ammessa: per questo e' un'IDENTITA'
# del gesto. In modifica l'articolo non cambia: un lotto e' di quell'articolo.
# ⛔ L'azienda del lotto non si sceglie: la mette il DB dalla sessione.
_IDENTITA_LOTTO: frozenset[str] = frozenset({"articolo_id"})
_NASCITA_LOTTO: _Lettura = {
    "testi": {"codice": (False, _MAX_CODICE)},
    "altri": {
        "articolo_id": _PAYLOAD.require_uuid,
        "data_arrivo": _PAYLOAD.require_date,
        "data_scadenza": _PAYLOAD.optional_date,
        "meta": _PAYLOAD.optional_meta,
    },
}
_MODIFICA_LOTTO: _Lettura = {
    "testi": {"codice": (False, _MAX_CODICE)},
    "flag": frozenset({"attivo"}),
    "altri": {
        "data_arrivo": _PAYLOAD.require_date,
        "data_scadenza": _PAYLOAD.optional_date,
        "meta": _PAYLOAD.optional_meta,
    },
}
CREATE_KEYS_LOTTO: frozenset[str] = _chiavi(_NASCITA_LOTTO)
UPDATE_KEYS_LOTTO: frozenset[str] = _chiavi(_MODIFICA_LOTTO)


# Scopo: I lotti di UN articolo nel perimetro, paginati. `articolo_id`
#        OBBLIGATORIO: un elenco di tutti i lotti di tutti gli articoli non e'
#        una domanda di nessuno (piano §6).
def list_lotti(
    *,
    auth_user_id: int | None,
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
        auth_user_id=auth_user_id, articolo_id=articolo, search=search, attivo=attivo,
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
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="lotti", gesto="crea", lettura=_NASCITA_LOTTO,
        obbligatori=("articolo_id", "codice", "data_arrivo"), identita=_IDENTITA_LOTTO,
    )
    with _db_errors("crea_lotto"):
        lotto_id = repository.create_lotto(
            str(campi.pop("articolo_id")),
            codice=campi.pop("codice"), data_arrivo=campi.pop("data_arrivo"), campi=campi,
        )
    return _lotto_o_404(repository, lotto_id)


# Scopo: Aggiorna il lotto per DELTA. ⛔ `articolo_id` non e' fra le chiavi:
#        un lotto nasce del suo articolo. `data_scadenza: null` la toglie.
def aggiorna_lotto(lotto_id: int, payload: dict[str, Any]) -> LottoRow:
    repository = AnagraficheMagazzinoRepository()
    campi = _campi_del_gesto(
        repository, payload, tabella="lotti", gesto="modifica", lettura=_MODIFICA_LOTTO,
    )
    _lotto_o_404(repository, lotto_id)
    with _db_errors("aggiorna_lotto"):
        repository.update_lotto(lotto_id, campi)
    return _lotto_o_404(repository, lotto_id)
