# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service generico per la gestione delle note partizionate delle
#        tabelle-madre `<schema>.note` (`vendite.note`, `catalogo.note`).
#        Composto sopra PartitionedNoteRepository: aggiunge validazione
#        payload, fallback id_stile da parameter NOTE_DEFAULT_STILE_ID,
#        coerenza target_riga_id <-> target_id, traduzione IntegrityError
#        in ServiceError parlanti. Stateless rispetto al dominio: ogni
#        dominio sorgente istanzia con il proprio repository.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Callable, NamedTuple

from django.db import IntegrityError, connection, transaction

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.db.partitioned_note_repository import (
    NOTE_ORDER_COLUMNS,
    ANCHOR_TIPI_AMMESSI,
    POSIZIONI_AMMESSE,
    PartitionedNoteRepository,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import (
    INTEGER_MAX,
    PayloadValidator,
    map_integrity_error,
)
from apps.core.services.service_errors import ServiceError

# Whitelist colonne payload accettate dal service (somma di create + update).
# La separazione create/update e' applicata dal service stesso (update rifiuta
# target_riga_id), il repository ha le sue whitelist piu' restrittive.
_PAYLOAD_KEYS: frozenset[str] = frozenset({
    "anchor_tipo",
    "posizione",
    "seq",
    "testo",
    "testo_md",
    "visibile",
    "solo_stampa",
    "id_stile",
    "id_lingua",
    "meta",
    "target_riga_id",
})

# Codice parametro di sistema per lo stile note di default.
# Convenzione confermata dal team DB (correzione brief 2026-05-19): il parametro
# contiene la **chiave naturale** `codice_interno` (es. "DEFAULT"), non l'id
# numerico. Vantaggi:
#   - stabile rispetto a re-seed (l'id auto-incrementale puo' variare,
#     `codice_interno` e' lockato dal trigger `trgfn_lock_columns`);
#   - autodescrittivo nei log/audit del parametro;
#   - niente accoppiamento con FK-surrogate registry.
# Risoluzione runtime: get_parameter -> codice_interno -> lookup id su
# `config.note_stili.codice_interno` (vedi `_lookup_stile_id_by_codice`).
PARAM_DEFAULT_STILE = "NOTE_DEFAULT_STILE"

# Parametro chiave naturale codice_iso per id_lingua di default.
# Stesso meccanismo FK-surrogate dello stile: il parameter contiene il
# `codice_iso` (es. "it") di `config.lingue`, validato dichiarativamente
# via `config.parameter_fk_surrogate` (riga id=4 EXACT config.lingue.codice_iso,
# migration 20260520-02/03). Risoluzione runtime: get_parameter -> codice_iso
# -> lookup id su config.lingue.codice_iso (vedi `_lookup_lingua_id_by_codice_iso`).
PARAM_DEFAULT_LINGUA = "NOTE_DEFAULT_LINGUA"

# Vincoli LOCALI di ogni partizione di `vendite.note`: stesso significato su
# ogni partizione (coerenza anchor/riga, testo non vuoto, FK testata e riga),
# nomi diversi. ⚠️ I nomi NON seguono un prefisso solo (`offnote`, ma
# `ordini_note` per l'anchor e `ordnote` per il testo): si copiano dalla doc
# auto-gen `dbzero/vendite/tabelle/note_*.md`, mai per analogia. `testo` None =
# la partizione non ha un CHECK locale sul testo (vale `chk_note_testo_non_vuoto`
# della madre). Presidio: `core/tests/db/test_note_vincoli_mappati_db.py` legge
# i vincoli veri da `pg_constraint` e fallisce su uno non mappato (F-7 di
# analisi-be-difetti-emersi-verifica-doc-api-core: fino al 2026-10-07 offerta,
# ordine, DDT e fattura cadevano su `E_NOTA_VALIDATION`).


# Scopo: i nomi dei vincoli locali di UNA partizione e le frasi delle sue FK.
#        Tipizzata e non un `dict`: una chiave sbagliata o un None dove serve
#        un nome falliscono all'import, invece di diventare la voce `"None"`.
class _VincoliPartizione(NamedTuple):
    anchor: str
    testo: str | None
    fk_testata: str
    fk_riga: str
    msg_testata: str
    msg_riga: str


_VINCOLI_PARTIZIONE: tuple[_VincoliPartizione, ...] = (
    _VincoliPartizione(
        "chk_prevnote_anchor", "chk_prevnote_testo_non_vuoto",
        "fk_prevnote_testata", "fk_prevnote_riga",
        "Preventivo di riferimento non trovato.", "Riga preventivo non trovata.",
    ),
    _VincoliPartizione(
        "chk_contnote_anchor", "chk_contnote_testo_non_vuoto",
        "fk_contnote_testata", "fk_contnote_riga",
        "Contratto di riferimento non trovato.", "Riga contratto non trovata.",
    ),
    _VincoliPartizione(
        "chk_offnote_anchor", None,
        "fk_offnote_testata", "fk_offnote_riga",
        "Offerta di riferimento non trovata.", "Riga offerta non trovata.",
    ),
    _VincoliPartizione(
        "chk_ordini_note_anchor", "chk_ordnote_testo_non_vuoto",
        "fk_ordini_note_testata", "fk_ordini_note_riga",
        "Ordine di riferimento non trovato.", "Riga ordine non trovata.",
    ),
    _VincoliPartizione(
        "chk_ddt_note_anchor", "chk_ddtnote_testo_non_vuoto",
        "fk_ddt_note_testata", "fk_ddt_note_riga",
        "DDT di riferimento non trovato.", "Riga DDT non trovata.",
    ),
    _VincoliPartizione(
        "chk_fatture_note_anchor", "chk_fatnote_testo_non_vuoto",
        "fk_fatture_note_testata", "fk_fatture_note_riga",
        "Fattura di riferimento non trovata.", "Riga fattura non trovata.",
    ),
    _VincoliPartizione(
        "chk_ven_note_att_anchor", None,
        "fk_ven_note_att_testata", "fk_ven_note_att_riga",
        "Attivita' fatturabile di riferimento non trovata.",
        "Riga attivita' fatturabile non trovata.",
    ),
)

# Mappa vincoli DB -> codici errore applicativi per IntegrityError.
# Cross-partizione: i nomi `chk_note_*` sono ereditati dalla parent table, i
# locali di ogni partizione si derivano da `_VINCOLI_PARTIZIONE` (sotto).
# ⭐ Il terzo elemento e' il CAMPO del form (chiave del payload): arriva al
#    client in `error.fields`. Le voci di coerenza e il tipo target restano a
#    due — non hanno UN campo (presidio C2, brief-be-presidio-ui-action-e-canale-campi §3-ter).
_CHECK_CONSTRAINTS: dict[str, tuple] = {
    "chk_note_anchor_tipo": (
        "E_NOTA_CHECK_VIOLATION",
        "anchor_tipo non ammesso (consentiti: DOCUMENTO, RIGA).",
        "anchor_tipo",
    ),
    "chk_note_posizione": (
        "E_NOTA_CHECK_VIOLATION",
        "posizione non ammessa (consentiti: HEADER, SEZIONE, FOOTER, BEFORE, AFTER).",
        "posizione",
    ),
    "chk_note_seq_pos": (
        "E_NOTA_CHECK_VIOLATION",
        "Il valore seq non puo' essere negativo.",
        "seq",
    ),
    "chk_note_testo_non_vuoto": (
        "E_NOTA_CHECK_VIOLATION",
        "Il testo della nota non puo' essere vuoto.",
        "testo",
    ),
}

# FK comuni: il tipo target, lo stile e la lingua. Le FK locali a ogni
# partizione si derivano da `_VINCOLI_PARTIZIONE` (sotto).
# ⭐ Il tipo target e' dal 2026-10-25 una FK verso `config.tipi_entita` (prima
#    il CHECK `chk_note_target_tipo`, lotto 3 di brief-db-grammatica-unica-
#    documenti). Un codice senza partizione non ci arriva: lo rifiuta prima il
#    routing (23514 senza nome di vincolo, `E_NOTA_VALIDATION`). La voce resta
#    perche' il vincolo c'e' su ogni partizione, e una voce mancante e' un
#    vincolo che parla col messaggio generico.
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_vendite_note_target_tipo": (
        "E_NOTA_FK",
        "Tipo target nota non ammesso.",
    ),
    "fk_vendite_note_id_stile": (
        "E_NOTA_FK",
        "Stile nota non valido.",
        "id_stile",
    ),
    "fk_vendite_note_id_lingua": (
        "E_NOTA_FK",
        "Lingua nota non valida.",
        "id_lingua",
    ),
}

# Scopo: i vincoli locali di ogni partizione nelle due mappe, con UNA frase
#        per significato; le frasi delle FK nominano il documento, e stanno
#        intere in `_VINCOLI_PARTIZIONE` (il genere cambia col documento).
for _p in _VINCOLI_PARTIZIONE:
    _CHECK_CONSTRAINTS[_p.anchor] = (
        "E_NOTA_CHECK_VIOLATION",
        "Coerenza anchor_tipo/target_riga_id non rispettata.",
    )
    if _p.testo is not None:
        _CHECK_CONSTRAINTS[_p.testo] = (
            "E_NOTA_CHECK_VIOLATION",
            "Il testo della nota non puo' essere vuoto.",
            "testo",
        )
    _FK_CONSTRAINTS[_p.fk_testata] = ("E_NOTA_PARENT_NOT_FOUND", _p.msg_testata)
    _FK_CONSTRAINTS[_p.fk_riga] = ("E_NOTA_FK", _p.msg_riga)
del _p

# ⭐ I vincoli di `catalogo.note` (dal 2026-11-11, giro 4 di
#    brief-db-revisione-catalogo: le note di catalogo hanno la forma di quelle
#    degli altri schemi, e passano da questo service). I `chk_note_*` comuni
#    hanno lo stesso nome e lo stesso significato delle note di vendita, e
#    sono gia' sopra; qui il CHECK proprio della sede e le FK, coi nomi della
#    doc auto-gen `dbzero/catalogo/tabelle/note*.md`.
_CHECK_CONSTRAINTS["chk_note_catalogo_ancora_documento"] = (
    "E_NOTA_CHECK_VIOLATION",
    "Una nota di catalogo annota l'articolo o il legame interi, non una riga.",
    "anchor_tipo",
)
_FK_CONSTRAINTS.update({
    "fk_cat_note_target_tipo": ("E_NOTA_FK", "Tipo target nota non ammesso."),
    "fk_cat_note_id_stile": ("E_NOTA_FK", "Stile nota non valido.", "id_stile"),
    "fk_cat_note_id_lingua": ("E_NOTA_FK", "Lingua nota non valida.", "id_lingua"),
    "fk_cat_note_articoli_target": ("E_NOTA_PARENT_NOT_FOUND", "Articolo di riferimento non trovato."),
    "fk_cat_note_articoli_componenti_target": (
        "E_NOTA_PARENT_NOT_FOUND", "Legame di distinta di riferimento non trovato.",
    ),
})


class PartitionedNoteService:
    """Facade CRUD sopra una `PartitionedNoteRepository`.

    Usage:

        repo = PartitionedNoteRepository(
            partition_table="vendite.note_preventivo",
            target_tipo="PREVENTIVO",
            parent_table="vendite.preventivi",
            parent_pk="id",
            child_table="vendite.preventivi_righe",
            child_parent_fk="preventivo_id",
        )
        svc = PartitionedNoteService(repo=repo)
        rows, total = svc.list_note(target_id=42)
        svc.crea_nota(target_id=42, payload={"testo_md": "..."})
    """

    # Scopo: Inizializza il service. `parameter_service`, `stile_lookup_fn` e
    #        `lingua_lookup_fn` iniettabili per i test (evita patching globale
    #        di connection.cursor).
    #        - `stile_lookup_fn(codice_interno) -> id | None`: lookup su
    #          config.note_stili; default fa query diretta.
    #        - `lingua_lookup_fn(codice_iso) -> id | None`: lookup su
    #          config.lingue per codice_iso (chiave naturale ISO).
    def __init__(
        self,
        *,
        repo: PartitionedNoteRepository,
        parameter_service: ParameterService | None = None,
        stile_lookup_fn: Callable[[str], int | None] | None = None,
        lingua_lookup_fn: Callable[[str], int | None] | None = None,
    ) -> None:
        self._repo = repo
        self._parameters = parameter_service or ParameterService()
        self._validator = PayloadValidator(validation_code="E_NOTA_VALIDATION")
        self._stile_lookup_fn = stile_lookup_fn or _default_stile_lookup
        self._lingua_lookup_fn = lingua_lookup_fn or _default_lingua_lookup

    # Scopo: La chiave del padre nella forma della sua sede: un intero
    #        positivo (documenti di vendita) o un UUID (anagrafiche di
    #        catalogo, `repo.target_id_uuid`), normalizzato a stringa.
    #        Altrimenti 400 `E_NOTA_VALIDATION`.
    def _target_id(self, target_id: Any) -> int | str:
        if self._repo.target_id_uuid:
            return self._validator.require_uuid({"target_id": target_id}, "target_id")
        self._validator.guard_positive_int(target_id, field="target_id")
        return int(target_id)

    # Scopo: Una sede senza righe (le anagrafiche di catalogo: la nota annota
    #        l'articolo o il legame interi) non ha note di riga: ne' l'ancora
    #        RIGA in scrittura, ne' il filtro `target_riga_id` in lettura.
    #        UNA frase per le due porte, col campo che l'ha chiesto.
    def _require_riga_ammessa(self, *, field: str) -> None:
        ErrorManager.require(
            self._repo.supports_riga,
            code="E_NOTA_VALIDATION",
            message="Note di riga non ammesse per questo target.",
            context={"field": field, "target_tipo": self._repo.target_tipo},
        )

    # Scopo: Verifica esistenza padre, solleva E_NOTA_PARENT_NOT_FOUND se mancante.
    def _ensure_parent_exists(self, target_id: int | str) -> None:
        ErrorManager.require(
            self._repo.exists_parent(target_id),
            code="E_NOTA_PARENT_NOT_FOUND",
            message="Documento di riferimento non trovato.",
            context={"target_tipo": self._repo.target_tipo, "target_id": target_id},
        )

    # Scopo: Lista note (testata + righe) per un target_id, con paginazione.
    #        Opzionalmente filtrabile per `target_riga_id` (drawer note-di-riga).
    def list_note(
        self,
        *,
        target_id: int | str,
        target_riga_id: int | None = None,
        include_invisible: bool = True,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        target_id = self._target_id(target_id)
        if target_riga_id is not None:
            # ⛔ Prima della forma: in una sede senza righe `target_riga_id` e'
            #    `uuid` (catalogo) e un intero arriverebbe al DB come
            #    `uuid = integer`, un 500.
            self._require_riga_ammessa(field="target_riga_id")
            self._validator.guard_positive_int(target_riga_id, field="target_riga_id")
        # La pagina della lista `<schema>.note` (dal 2026-10-31): l'ordinamento
        # dalla whitelist comune delle note (`ordine_note_valido`).
        order_by, order_dir = ordine_note_valido(
            order_by, order_dir, function_name="core.partitioned_note_service.list_note",
        )
        self._ensure_parent_exists(target_id)
        return self._repo.list(
            target_id,
            target_riga_id=target_riga_id,
            include_invisible=include_invisible,
            search=search,
            order_by=order_by,
            order_dir=order_dir,
            limit=min(MAX_LIMIT, max(1, limit)),
            offset=max(0, offset),
        )

    # Scopo: Restituisce una singola nota per id + target_id. Solleva
    #        E_NOTA_NOT_FOUND se mancante (anche su tampering url id<->target).
    def get_nota(self, *, note_id: int, target_id: int | str) -> dict[str, Any]:
        self._validator.guard_positive_int(note_id, field="note_id")
        target_id = self._target_id(target_id)
        nota = self._repo.get(note_id, target_id)
        ErrorManager.require(
            nota is not None,
            code="E_NOTA_NOT_FOUND",
            message="Nota non trovata.",
            context={"note_id": note_id, "target_id": target_id},
        )
        assert nota is not None
        return nota

    # Scopo: Crea una nuova nota. Valida payload + coerenza anchor/target_riga,
    #        applica fallback id_stile da parameter, traduce IntegrityError.
    #        Difese applicative simmetriche al trigger DB `trgfn_note_validate_generic`.
    def crea_nota(
        self,
        *,
        target_id: int | str,
        payload: dict[str, Any],
        auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        target_id = self._target_id(target_id)
        self._ensure_parent_exists(target_id)
        normalized = self._normalize_payload(payload, is_create=True, auth_user_id=auth_user_id)

        # Coerenza riga: target_riga_id valorizzato => deve appartenere al parent.
        # La sede senza righe e' gia' respinta da `_normalize_payload`
        # (`_require_riga_ammessa`): una riga valorizzata vuol dire ancora RIGA.
        riga_id = normalized.get("target_riga_id")
        if riga_id is not None:
            ErrorManager.require(
                self._repo.riga_belongs_to_parent(target_id, riga_id),
                code="E_NOTA_RIGA_INCOERENTE",
                message="La riga indicata non appartiene al documento.",
                context={"target_id": target_id, "target_riga_id": riga_id},
            )

        try:
            with transaction.atomic():
                new_id = self._repo.create(target_id, normalized)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code="E_NOTA_VALIDATION",
                fallback_message="Errore creazione nota.",
                context={"target_id": target_id},
            )

        return self.get_nota(note_id=new_id, target_id=target_id)

    # Scopo: Aggiorna una nota esistente. `target_riga_id` immutabile per design
    #        (spostare una nota fra righe = delete+create). Valida patch e
    #        traduce IntegrityError.
    def aggiorna_nota(
        self,
        *,
        note_id: int,
        target_id: int | str,
        patch: dict[str, Any],
        auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        # Verifica esistenza prima di accettare il patch (404 esplicito).
        target_id = self._target_id(target_id)
        self.get_nota(note_id=note_id, target_id=target_id)
        normalized = self._normalize_payload(patch, is_create=False, auth_user_id=auth_user_id)
        # ⛔ Un PATCH senza campi e' un 400, non un 200 che restituisce la nota
        #    com'e' (Tid, 2026-10-20, brief-be-verifica-documentazione-api §A2).
        self._validator.require_campi_da_aggiornare(normalized)
        try:
            with transaction.atomic():
                updated = self._repo.update(note_id, target_id, normalized)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code="E_NOTA_VALIDATION",
                fallback_message="Errore aggiornamento nota.",
                context={"note_id": note_id, "target_id": target_id},
            )

        ErrorManager.require(
            updated,
            code="E_NOTA_NOT_FOUND",
            message="Nota non trovata.",
            context={"note_id": note_id, "target_id": target_id},
        )
        return self.get_nota(note_id=note_id, target_id=target_id)

    # Scopo: Elimina (hard delete) una nota. 404 se inesistente; idempotenza
    #        delegata al chiamante (chi richiama 2 volte vede il 404 sulla seconda).
    def elimina_nota(self, *, note_id: int, target_id: int | str) -> None:
        self._validator.guard_positive_int(note_id, field="note_id")
        target_id = self._target_id(target_id)
        deleted = self._repo.delete(note_id, target_id)
        ErrorManager.require(
            deleted,
            code="E_NOTA_NOT_FOUND",
            message="Nota non trovata.",
            context={"note_id": note_id, "target_id": target_id},
        )

    # Scopo: Conta note totali sul documento (per badge UI).
    def count_per_target(self, *, target_id: int | str) -> int:
        target_id = self._target_id(target_id)
        return self._repo.count_for_parent(target_id)

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Normalizza e valida il payload note. Applica whitelist, default
    #        derivati (anchor_tipo da target_riga_id, posizione da anchor_tipo,
    #        seq=10, visibile=True, solo_stampa=False), fallback id_stile.
    #        `auth_user_id` riservato per estensioni future (gating campi).
    def _normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        is_create: bool,
        auth_user_id: int | None,
    ) -> dict[str, Any]:
        ErrorManager.require(
            isinstance(payload, dict),
            code="E_NOTA_VALIDATION",
            message="Payload nota non valido.",
        )

        # Whitelist generale; il vincolo specifico create-vs-update e' subito sotto.
        self._validator.validate_allowed_keys(
            payload, allowed=_PAYLOAD_KEYS,
            message="Campi nota non riconosciuti.",
        )

        if not is_create:
            # In UPDATE non e' ammesso modificare target_riga_id (spostare una
            # nota fra righe = delete+create). Errore esplicito invece di
            # ignorare silenziosamente.
            ErrorManager.require(
                "target_riga_id" not in payload,
                code="E_NOTA_VALIDATION",
                message="target_riga_id non modificabile su nota esistente.",
                hint="Per spostare la nota: elimina e ricrea sulla nuova riga.",
            )

        normalized: dict[str, Any] = {}

        # Stringhe obbligatorie/opzionali.
        # In CREATE almeno uno fra testo/testo_md non vuoto (DB lo verifica via
        # chk_note_testo_non_vuoto; qui errore parlante per UI).
        testo = self._validator.optional_string(payload, "testo", max_len=20000)
        testo_md = self._validator.optional_string(payload, "testo_md", max_len=20000)
        if is_create:
            ErrorManager.require(
                bool(testo) or bool(testo_md),
                code="E_NOTA_VALIDATION",
                message="Il testo della nota e' obbligatorio.",
            )
        if testo is not None or "testo" in payload:
            normalized["testo"] = testo
        if testo_md is not None or "testo_md" in payload:
            normalized["testo_md"] = testo_md

        # target_riga_id (solo CREATE; UPDATE gia' bloccato sopra).
        if is_create:
            riga_id = self._validator.optional_positive_int(payload, "target_riga_id")
            if riga_id is not None:
                normalized["target_riga_id"] = riga_id

        # anchor_tipo: default derivato. Se utente lo passa esplicito, valida.
        anchor_in = self._validator.optional_string(payload, "anchor_tipo", max_len=32)
        if anchor_in is not None:
            anchor_in = anchor_in.upper()
            ErrorManager.require(
                anchor_in in ANCHOR_TIPI_AMMESSI,
                code="E_NOTA_VALIDATION",
                message=f"anchor_tipo non valido. Ammessi: {sorted(ANCHOR_TIPI_AMMESSI)}",
                context={"anchor_tipo": anchor_in},
            )
            anchor_eff = anchor_in
        else:
            anchor_eff = "RIGA" if normalized.get("target_riga_id") is not None else "DOCUMENTO"
        # ⛔ Una sede senza righe (le anagrafiche di catalogo: la nota annota
        #    l'articolo o il legame interi) non ha l'ancora RIGA, ne' in
        #    creazione ne' in modifica. Lo dice anche il DB
        #    (`chk_note_catalogo_ancora_documento`); qui la frase col campo,
        #    prima della scrittura.
        if anchor_eff == "RIGA":
            self._require_riga_ammessa(field="anchor_tipo")
        if is_create or anchor_in is not None:
            normalized["anchor_tipo"] = anchor_eff

        # Coerenza anchor_tipo <-> presenza target_riga_id (defense-in-depth
        # rispetto a chk_prevnote_anchor / chk_contnote_anchor).
        if is_create:
            has_riga = normalized.get("target_riga_id") is not None
            ErrorManager.require(
                (anchor_eff == "RIGA") == has_riga,
                code="E_NOTA_VALIDATION",
                message=(
                    "anchor_tipo='RIGA' richiede target_riga_id valorizzato; "
                    "anchor_tipo='DOCUMENTO' richiede target_riga_id NULL."
                ),
                context={"anchor_tipo": anchor_eff, "target_riga_id": normalized.get("target_riga_id")},
            )

        # posizione: default derivato. HEADER per documento, AFTER per riga.
        posizione_in = self._validator.optional_string(payload, "posizione", max_len=32)
        if posizione_in is not None:
            posizione_in = posizione_in.upper()
            ErrorManager.require(
                posizione_in in POSIZIONI_AMMESSE,
                code="E_NOTA_VALIDATION",
                message=f"posizione non valida. Ammesse: {sorted(POSIZIONI_AMMESSE)}",
                context={"posizione": posizione_in},
            )
            normalized["posizione"] = posizione_in
        elif is_create:
            normalized["posizione"] = "AFTER" if anchor_eff == "RIGA" else "HEADER"

        # seq: il range e' quello del DB, `integer` con `CHECK (seq >= 0)` su
        # tutte le tabelle delle note (D-seq di Tid, 2026-11-11,
        # brief-db-revisione-catalogo §19). Lo 0 e' ammesso: mette una nota
        # prima di quelle nate col default 10. Il tetto e' quello dell'integer,
        # non dello smallint: `optional_smallint` qui e' il lettore d'intero a
        # range dichiarato. Default 10 in create.
        seq = self._validator.optional_smallint(
            payload, "seq", min_val=0, max_val=INTEGER_MAX,
        )
        if seq is not None:
            normalized["seq"] = seq
        elif is_create:
            normalized["seq"] = 10

        # visibile / solo_stampa: bool. Default true/false in create.
        visibile = self._validator.optional_bool(payload, "visibile")
        if visibile is not None:
            normalized["visibile"] = visibile
        elif is_create:
            normalized["visibile"] = True

        solo_stampa = self._validator.optional_bool(payload, "solo_stampa")
        if solo_stampa is not None:
            normalized["solo_stampa"] = solo_stampa
        elif is_create:
            normalized["solo_stampa"] = False

        # id_stile: fallback al parametro di sistema.
        id_stile = self._validator.optional_positive_int(payload, "id_stile")
        if id_stile is None and is_create:
            id_stile = self._resolve_default_stile_id(auth_user_id)
        if id_stile is not None:
            normalized["id_stile"] = id_stile

        # id_lingua: nullable in DB ma in CREATE applichiamo fallback al
        # parametro di sistema (simmetrico a id_stile). Se l'utente non
        # sceglie esplicitamente, viene applicato il default `NOTE_DEFAULT_LINGUA`
        # (codice_iso). Pattern coerente con `_resolve_default_stile_id`.
        id_lingua = self._validator.optional_positive_int(payload, "id_lingua")
        if id_lingua is None and is_create:
            id_lingua = self._resolve_default_lingua_id(auth_user_id)
        if id_lingua is not None:
            normalized["id_lingua"] = id_lingua

        # meta jsonb: opzionale; il PayloadValidator garantisce dict o None.
        meta = self._validator.optional_meta(payload, "meta")
        if meta is not None:
            normalized["meta"] = meta

        return normalized

    # Scopo: Risolve l'id stile di default in 2 step: legge il `codice_interno`
    #        dal parametro NOTE_DEFAULT_STILE, poi cerca l'id corrispondente
    #        in config.note_stili. Errore parlante se manca uno dei due
    #        (parametro non seedato OR codice non risolto OR stile disattivato).
    #        Cosi' evitiamo che un INSERT atterri su un NOT NULL violato.
    def _resolve_default_stile_id(self, auth_user_id: int | None) -> int:
        try:
            codice = self._parameters.get_parameter(
                PARAM_DEFAULT_STILE,
                django_user_id=auth_user_id,
            )
        except ServiceError as exc:
            # Ammessi: E_PARAMETER_NOT_FOUND (parametro non configurato).
            # Qualunque altro ServiceError esce: e' un bug reale a monte.
            if exc.code != "E_PARAMETER_NOT_FOUND":
                raise
            codice = None
        ErrorManager.require(
            codice is not None and codice.strip() != "",
            code="E_NOTA_VALIDATION",
            message="Stile nota obbligatorio.",
            hint=(
                "Indicare id_stile nel payload oppure configurare il parametro "
                f"{PARAM_DEFAULT_STILE} in config.parameters (chiave naturale "
                "del codice_interno su config.note_stili)."
            ),
        )
        assert codice is not None
        stile_id = self._stile_lookup_fn(codice.strip())
        ErrorManager.require(
            stile_id is not None,
            code="E_NOTA_VALIDATION",
            message="Stile nota di default non risolvibile.",
            hint=(
                f"Parametro {PARAM_DEFAULT_STILE}='{codice}' ma nessun "
                "record attivo in config.note_stili con questo codice_interno."
            ),
            context={"codice_interno": codice},
        )
        assert stile_id is not None
        return stile_id

    # Scopo: Risolve l'id lingua di default in 2 step (simmetrico allo stile):
    #        codice_iso dal parametro NOTE_DEFAULT_LINGUA -> id su config.lingue.
    #        Differenza con stile: la lingua e' nullable in DB, quindi se il
    #        parametro non e' configurato ritorniamo None senza sollevare (la
    #        nota verra' salvata con id_lingua NULL). L'errore parlante scatta
    #        solo se il parametro c'e' ma punta a un codice_iso inesistente.
    def _resolve_default_lingua_id(self, auth_user_id: int | None) -> int | None:
        try:
            codice = self._parameters.get_parameter(
                PARAM_DEFAULT_LINGUA,
                django_user_id=auth_user_id,
            )
        except ServiceError as exc:
            if exc.code != "E_PARAMETER_NOT_FOUND":
                raise
            codice = None
        if codice is None or codice.strip() == "":
            return None  # nessun default configurato -> id_lingua resta NULL
        lingua_id = self._lingua_lookup_fn(codice.strip())
        ErrorManager.require(
            lingua_id is not None,
            code="E_NOTA_VALIDATION",
            message="Lingua nota di default non risolvibile.",
            hint=(
                f"Parametro {PARAM_DEFAULT_LINGUA}='{codice}' ma nessun "
                "record attivo in config.lingue con questo codice_iso."
            ),
            context={"codice_iso": codice},
        )
        assert lingua_id is not None
        return lingua_id


# Scopo: Default lookup id_stile da codice_interno su config.note_stili.
#        Filtra `attivo=TRUE` per evitare di risolvere a stili disattivati.
#        Funzione modulo-level (no stato): facilmente sostituibile via DI
#        per test unit (passare `stile_lookup_fn` al PartitionedNoteService).
def _default_stile_lookup(codice_interno: str) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM config.note_stili "
            "WHERE codice_interno = %s AND attivo = TRUE LIMIT 1",
            [codice_interno],
        )
        row = cursor.fetchone()
    return int(row[0]) if row else None


# Scopo: Default lookup id_lingua da codice_iso su config.lingue.
#        Pattern simmetrico a `_default_stile_lookup`; chiave naturale
#        ISO standard (stabile per costruzione, no lock_columns necessario).
def _default_lingua_lookup(codice_iso: str) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM config.lingue "
            "WHERE codice_iso = %s AND attivo = TRUE LIMIT 1",
            [codice_iso],
        )
        row = cursor.fetchone()
    return int(row[0]) if row else None


# Scopo: I `contatori` dei badge di un documento, nel payload del suo
#        DETTAGLIO: oggi `{"note": <n>}`, il numero sul pulsante standard
#        «Gestisci note» (FE `useContatoreNote`). UN posto per la forma: la
#        chiave e' il contratto col frontend, e tutti i documenti con note
#        partizionate la danno uguale (regola del 2, 2026-10-25).
#        Dict e non scalare per reggere i prossimi contatori senza cambiare
#        shape (api_fattura_dettaglio §`contatori`).
# ⛔ Si chiama DOPO il cancello di testata: un documento fuori perimetro e'
#    un 404, non un conteggio.
def contatori_documento(repo: PartitionedNoteRepository, target_id: int | str) -> dict[str, int]:
    return {
        "note": PartitionedNoteService(repo=repo).count_per_target(target_id=target_id),
    }


# Scopo: L'ordinamento chiesto a una lista di note `<schema>.note`, validato
#        sulla whitelist COMUNE `NOTE_ORDER_COLUMNS` (quella con cui ordina
#        `pagina_note`): `vendite.note` (`list_note`, sotto) e `catalogo.note`
#        (`catalogo_service._lista_note`) dicevano la stessa regola in due copie
#        (regola del 2, 2026-10-31). Ritorna la coppia normalizzata.
# ⭐ Senza colonna non si valida qui: l'ordine lo decide il default di
#    `pagina_note`, e una direzione estranea la rifiuta comunque
#    `sql_order_clause` (400 `E_VALIDATION_INPUT`, lo stesso codice).
def ordine_note_valido(
    order_by: str | None, order_dir: str | None, *, function_name: str,
) -> tuple[str | None, str | None]:
    if not order_by:
        return order_by, order_dir
    return validate_order_params(
        order_by, order_dir,
        allowed_columns=frozenset(NOTE_ORDER_COLUMNS),
        error_code="E_VALIDATION_INPUT",
        nullable=True,
        function_name=function_name,
    )
