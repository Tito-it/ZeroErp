# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facciata del dominio `magazzino` — il DOCUMENTO INTERNO (inventario e
#        rettifica: una famiglia, due configurazioni), le sue righe, il piano,
#        la registrazione, e i tre lookup di riga. Orchestrazione sottile:
#        validazione del payload, traduzione degli errori del database,
#        composizione della risposta.
# Note: 🔴 Il backend qui e' sottile PER OBBLIGO. Le regole vivono nel
#       database: la matrice degli stati e la porta `POSTED` (guard di
#       transizione), il congelamento delle righe fuori da `DRAFT` (guard di
#       riga), la coerenza della riga con articolo/lotto/seriale/ubicazione
#       (`fn_check_riga_magazzino`, letta dal piano e dalla primitiva), il
#       posting (`fn_posta_*`, UNA `SELECT`, una transazione). Il service NON
#       decide se una transizione e' ammessa ne' se una riga e' coerente:
#       chiede, e traduce la risposta.
#
#       ⭐ 2026-11-23 (R-2 di brief-db-magazzino-tutte-le-scritture-dal-verbo):
#       ogni scrittura passa da un VERBO del DB (il repository), che controlla
#       il livello `TUTTO` sull'oggetto della famiglia e il perimetro. Le
#       chiavi AMMESSE le dice il DB (`fn_documento_interno_colonne_ammesse`,
#       lette a ogni scrittura); qui resta il TRASPORTO di ogni chiave. Una
#       divergenza fra DB e lettori e' un `RuntimeError` (500), mai uno
#       scarto silenzioso (`PayloadValidator.campi_del_gesto`). `meta` non e' fra le colonne
#       dei verbi: il contratto non lo porta piu'.
#       ⚠️ Q-2 (Tid, 2026-09-18) SUPERATA dal P-5b del brief: la testata si
#       modifica solo in `DRAFT`, e lo dice il verbo
#       (`E_MAG_DOCUMENTO_TESTATA_CONGELATA`, 409). Il BE non aggiunge un
#       guard suo: traduce.
#       ⛔ Q-3 (Tid, 2026-09-18): la riga incoerente PASSA — il DB l'ammette in
#       `DRAFT` (C8 b) e il piano la dichiara `NON_POSTABILE`; il form la
#       MOSTRA (`righe/motivi/`). Un rifiuto qui sarebbe una regola piu'
#       stretta del modello, scritta fuori dal DB.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_enum_param
from apps.core.services.payload_helpers import (
    Lettura,
    PayloadValidator,
    chiavi_lettura,
    make_db_errors_translator,
)
from apps.magazzino.db.famiglie import FAMIGLIE, INVENTARI, FamigliaDocumentoInterno
from apps.magazzino.db.magazzino_repository import (
    DOCUMENTI_SORT_COLUMNS,
    PIANO_SORT_COLUMNS,
    MagazzinoRepository,
    righe_sort_columns,
)
from apps.magazzino.services._helpers import (
    E_VALIDAZIONE,
    articolo_uuid,
    ordinamento_validato,
    risposta_paginata as _risposta,
)
from apps.magazzino.types import DocumentoInternoRow, RigaDocumentoInternoRow

logger = logging.getLogger(__name__)

_FN = "magazzino.magazzino_service"

# `E_VALIDAZIONE` vive in `_helpers.py` (condiviso con la consultazione) e
# resta leggibile da qui (`svc.E_VALIDAZIONE`): e' il nome che i test usano.

# La testata che non c'e' — o che il perimetro non lascia vedere, e i due
# restano volutamente indistinguibili (404 no-leak). A catalogo, NON_TROVATO.
E_DOCUMENTO_NON_TROVATO = "E_MAG_DOCUMENTO_NON_TROVATO"
# E la RIGA che non c'e': a catalogo dal 2026-09-23 (R-7 del brief 2-bis).
# ⭐ La risposta a chi guarda non cambia — 404 identico nei due casi — ma il
# codice dice QUALE delle due cose manca. Prima rispondeva quello della
# testata con una frase scritta qui: codice e frase dicevano due cose diverse.
E_RIGA_NON_TROVATA = "E_MAG_DOCUMENTO_RIGA_NON_TROVATA"

# ⭐ Il VOCABOLARIO degli stati, specchio DICHIARATO del `CHECK`
# (`chk_mag_inventari_stato` / `chk_mag_rettifiche_stato`): lo pinna
# `tests/db/test_stati_documento_interno.py` con `valori_check`.
STATI_DOCUMENTO_INTERNO: tuple[str, ...] = ("DRAFT", "CONFIRM", "POSTED", "CANCEL")
# Gli stati che una PERSONA puo' chiedere. ⛔ `POSTED` non c'e': lo scrive
# SOLO l'operazione di registrazione (la porta `POSTED` del guard risponderebbe
# `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`, un TECNICO — cioe' un 500 per
# un pulsante). Il vocabolario lo tiene fuori PRIMA del database.
STATI_RICHIEDIBILI: tuple[str, ...] = ("CONFIRM", "CANCEL", "DRAFT")

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

# Lunghezze dei testi: quelle delle colonne (`inventari.descrizione`
# varchar(255), `rettifiche_righe.motivo` varchar(64)). Un testo piu' lungo e'
# un 400 col campo, non un `22001` del DB. Pubbliche: le legge anche lo schema
# OpenAPI (`api/views.py`), che le dichiara come `max_length`.
MAX_DESCRIZIONE_DOCUMENTO = 255
MAX_MOTIVO_RIGA = 64

# ⛔ La PROVENIENZA (`sorgente_*`) il DB la ammette alla nascita (D-M11), ma
#    non e' un dato che l'operatore compila: la scrive chi fa nascere il
#    documento da un altro documento, dal SUO service, chiamando il
#    repository. Il gesto dell'operatore la toglie per nome, cosi' ogni
#    ALTRA chiave che il DB ammettesse resta un `RuntimeError` se qui nessuno
#    la sa leggere.
_PROVENIENZA = frozenset({"sorgente_tipo_id", "sorgente_id", "sorgente_uid", "sorgente_riga"})

# Traduzione degli errori del database. ⚠️ I guard di `magazzino` sollevano
# codici registrati con la loro frase: passano INTATTI. Qui si traducono le
# violazioni di VINCOLO, dove il database parla il linguaggio dei nomi.
# ⭐ R-2, dal 2026-09-23: il `23505` di `uq_mag_inventari_righe_posizione`
#    (UNIQUE NULLS NOT DISTINCT su inventario, articolo, ubicazione, lotto,
#    asset) ha il suo codice a catalogo. Due letture della stessa posizione
#    non sono due fatti: sono la stessa riga scritta due volte, e il piano non
#    saprebbe quale delle due e' il conteggio.
# ⛔ Le RETTIFICHE non ce l'hanno, e non e' una dimenticanza: due delta dati
#    sulla stessa posizione sono due correzioni, non due letture (C14). Il
#    vincolo a DB non esiste, quindi qui non c'e' una riga da scrivere.
# ⚠️ Il NOME del vincolo ha una sede sola, la famiglia (`guard_riga_uniq`):
#    ricopiarlo qui farebbe di una rinomina a DB un 23505 che cade in silenzio
#    sul ripiego generico.
_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    vincolo: (
        "E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA",
        "L'articolo e' gia' contato in questa posizione dell'inventario.",
        # Il campo che si accende nel form: chi rimedia e' chi compila la riga,
        # e l'articolo e' il dato che identifica la lettura doppia.
        "articolo_id",
    )
    for vincolo in (INVENTARI.guard_riga_uniq,)
    if vincolo
}
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_mag_inventari_magazzino": (E_VALIDAZIONE, "Magazzino non valido.", "magazzino_id"),
    "fk_mag_rettifiche_magazzino": (E_VALIDAZIONE, "Magazzino non valido.", "magazzino_id"),
    "fk_mag_inventario_righe_articolo": (E_VALIDAZIONE, "Articolo non valido.", "articolo_id"),
    "fk_mag_rettifiche_righe_articolo": (E_VALIDAZIONE, "Articolo non valido.", "articolo_id"),
    "fk_mag_inventari_righe_ubicazione": (E_VALIDAZIONE, "Ubicazione non valida.", "ubicazione_id"),
    "fk_mag_rettifiche_righe_ubicazione": (E_VALIDAZIONE, "Ubicazione non valida.", "ubicazione_id"),
    "fk_mag_inventari_righe_lotto": (E_VALIDAZIONE, "Lotto non valido.", "lotto_id"),
    "fk_mag_rettifiche_righe_lotto": (E_VALIDAZIONE, "Lotto non valido.", "lotto_id"),
    "fk_mag_inventari_righe_asset": (E_VALIDAZIONE, "Seriale non valido.", "asset_id"),
    "fk_mag_rettifiche_righe_asset": (E_VALIDAZIONE, "Seriale non valido.", "asset_id"),
}
_CHECK_CONSTRAINTS: dict[str, tuple] = {
    "chk_mag_inventario_righe_qta_contata_non_neg": (
        E_VALIDAZIONE, "La quantita' contata non puo' essere negativa.", "qta_contata",
    ),
    "chk_mag_rettifiche_qta_non_zero": (
        E_VALIDAZIONE, "La quantita' della rettifica non puo' essere zero.", "qta_delta",
    ),
    "chk_mag_inventari_righe_costo_non_neg": (
        E_VALIDAZIONE, "Il costo unitario non puo' essere negativo.", "costo_unitario",
    ),
    "chk_mag_rettifiche_righe_costo_non_neg": (
        E_VALIDAZIONE, "Il costo unitario non puo' essere negativo.", "costo_unitario",
    ),
    "chk_mag_inventari_righe_asset_qta_unitaria": (
        E_VALIDAZIONE, "Con un seriale la quantita' e' uno.", "qta_contata",
    ),
    "chk_mag_rettifiche_righe_asset_qta_unitaria": (
        E_VALIDAZIONE, "Con un seriale la quantita' e' uno (in valore assoluto).", "qta_delta",
    ),
    # Il blocco manuale dice PER CHI e': il soggetto o una nota (un'attesa senza
    # sorgente, soggetto ne' nota e' una riga muta — manual movimenti_attesi).
    "chk_mag_movimenti_attesi_per_chi": (
        E_VALIDAZIONE, "Un blocco dice per chi e': indica il soggetto o scrivi una nota.", "nota",
    ),
}

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo sul documento di magazzino.",
    unique_constraints=_UNIQUE_CONSTRAINTS,
    fk_constraints=_FK_CONSTRAINTS,
    check_constraints=_CHECK_CONSTRAINTS,
)


# ══════════════════════════════════════════════════════════════════
#  Helper privati
# ══════════════════════════════════════════════════════════════════

# Scopo: La famiglia dal suo codice di URL; un codice ignoto e' un difetto di
#        routing, non un input utente: il router monta solo le due note.
def famiglia(codice: str) -> FamigliaDocumentoInterno:
    return FAMIGLIE[codice]


# Scopo: Legge la testata o solleva il 404 di dominio — PRIMA di ogni
#        satellite (api.md: «leggi prima la testata»).
def _documento_o_404(
    repository: MagazzinoRepository, f: FamigliaDocumentoInterno, doc_id: int
) -> DocumentoInternoRow:
    documento = repository.get_documento(f, doc_id)
    ErrorManager.require(
        documento is not None,
        code=E_DOCUMENTO_NON_TROVATO,
        message=f"{f.singolare.capitalize()} non trovato.",
        detail=f"{f.singolare}_id={doc_id}",
        function_name=_FN,
    )
    assert documento is not None
    return documento


# Scopo: Legge la riga DELLA testata o solleva il 404: la coppia (documento,
#        riga) e' la risorsa dell'URL, e una riga di un altro documento «non
#        c'e'» — stessa risposta, stesso no-leak. ⭐ Codice SUO dal 2026-09-23
#        (R-7): la frase la porta il catalogo, qui resta l'etichetta tecnica
#        che finisce nel log (stampo dei tre 404 di `anagrafiche_magazzino`).
def _riga_o_404(
    repository: MagazzinoRepository, f: FamigliaDocumentoInterno, doc_id: int, riga_id: int
) -> RigaDocumentoInternoRow:
    riga = repository.get_riga(f, doc_id, riga_id)
    ErrorManager.require(
        riga is not None,
        code=E_RIGA_NON_TROVATA,
        message="Riga non trovata.",
        detail=f"{f.singolare}_id={doc_id} riga_id={riga_id}",
        function_name=_FN,
    )
    assert riga is not None
    return riga


# Scopo: Il magazzino scelto in un form, o il 400 col campo: se non esiste,
#        non e' attivo o non e' nel perimetro, l'operatore ha scelto male.
# ⚠️ Non e' una regola del DB riscritta: e' la TRADUZIONE di un dato di form
#    prima che il DB risponda con la FK (400 senza contesto) o col require
#    del padre attivo (`E_ATTIVO_PADRE_NON_ATTIVO`, 409, con nella frase i
#    nomi delle tabelle, non una frase per chi ha scelto da una tendina).
def _magazzino_o_400(repository: MagazzinoRepository, magazzino_id: int) -> dict[str, Any]:
    magazzino = repository.get_magazzino(magazzino_id)
    ErrorManager.require(
        magazzino is not None,
        code=E_VALIDAZIONE,
        message="Magazzino inesistente, non attivo o fuori dal tuo perimetro.",
        context={"field": "magazzino_id", "magazzino_id": magazzino_id},
        function_name=_FN,
    )
    assert magazzino is not None
    return magazzino


# ══════════════════════════════════════════════════════════════════
#  Documento interno — lettura
# ══════════════════════════════════════════════════════════════════

# Scopo: L'elenco paginato delle testate di una famiglia.
# ⭐ `nullable=True`: «non specificato» e' legittimo e l'ordine lo decide il
#    repository (`data DESC`); fuori whitelist e' un 400 col campo.
def list_documenti(
    codice_famiglia: str,
    *,
    auth_user_id: int | None,
    magazzino_id: int | None = None,
    stato: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=DOCUMENTI_SORT_COLUMNS,
        function_name=f"{_FN}.list_documenti",
    )
    stato = validate_enum_param(
        stato, allowed=STATI_DOCUMENTO_INTERNO, param_name="stato",
        error_code=E_VALIDAZIONE, function_name=f"{_FN}.list_documenti",
    )
    results, total = MagazzinoRepository().list_documenti(
        f,
        auth_user_id=auth_user_id,
        magazzino_id=magazzino_id,
        stato=stato,
        data_da=data_da,
        data_a=data_a,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _risposta(results, total)


# Scopo: Il dettaglio: testata + magazzino + `righe_count` + le `capabilities`,
#        e per l'inventario il riepilogo del piano. 404 no-leak PRIMA di ogni
#        satellite (api.md: «leggi prima la testata»).
# ⭐ R-1, dal 2026-09-23: `capabilities` e `stato_info_key` vengono dal blob di
#    `script.fn_available_actions_<famiglia>`, e il BE lo TRASPORTA intatto. Le
#    azioni le decide la matrice che il guard fa rispettare
#    (`magazzino.fn_documento_interno_transizioni`), la terna di «registra» il
#    primo motivo della check che le due `fn_posta_*` chiamano
#    (`script.fn_check_documento_interno_registrabile`): una regola, una sede,
#    due lettori. ⛔ Nessun `dict` di stati qui: sarebbe la matrice riscritta.
# ⛔ `stato_info_key` sta SOLO nel blob: fino al 2026-09-23 era copiato anche
#    in cima al documento, cioe' una lettura piatta con due sedi (api.md §«Il
#    blob sta SOTTO `capabilities`»). Il FE lo legge da `capabilities`.
def get_documento(codice_famiglia: str, doc_id: int) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    documento: dict[str, Any] = dict(_documento_o_404(repository, f, doc_id))
    documento["famiglia"] = f.codice
    documento["capabilities"] = repository.get_capabilities(f, doc_id)
    if f.ha_piano:
        documento["piano_riepilogo"] = repository.piano_riepilogo(doc_id)
    return documento


# ══════════════════════════════════════════════════════════════════
#  Documento interno — scrittura
# ══════════════════════════════════════════════════════════════════

# Scopo: Il trasporto delle chiavi di testata di una famiglia: la data (NOT
#        NULL: `null` e' un 400; assente alla nascita = oggi, DEFAULT del DB)
#        e, solo dove la colonna c'e', la descrizione (nullable).
def _lettura_testata(f: FamigliaDocumentoInterno) -> Lettura:
    return {
        "testi": {"descrizione": (True, MAX_DESCRIZIONE_DOCUMENTO)} if f.ha_descrizione else {},
        "altri": {"data": _PAYLOAD.require_date},
    }


# Scopo: Le chiavi che il backend sa LEGGERE per (famiglia, parte, gesto),
#        senza le identita' che il verbo riceve come argomento (il magazzino
#        della testata). Sono le colonne del DB per il gesto dell'operatore:
#        un test sul DB vero le confronta con `fn_documento_interno_colonne_
#        ammesse` (la nascita della testata senza la provenienza).
def chiavi_lette(f: FamigliaDocumentoInterno, parte: str, gesto: str) -> frozenset[str]:
    lettura = _lettura_testata(f) if parte == "testata" else _lettura_riga(f)
    return chiavi_lettura(lettura)


# Scopo: Crea la BOZZA: il magazzino (obbligatorio, e decide tutto il resto:
#        e' l'argomento del verbo), la data, e — solo inventario — la
#        descrizione. Le chiavi le dice il DB (lista «crea» della testata).
def crea_documento(codice_famiglia: str, payload: dict[str, Any]) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    lettura = _lettura_testata(f)
    lettura["interi"] = {"magazzino_id": False}
    campi = _PAYLOAD.campi_del_gesto(
        payload,
        ammesse=(repository.colonne_ammesse(f, "testata", "crea") - _PROVENIENZA) | {"magazzino_id"},
        lettura=lettura,
        function_name=f"{_FN}.crea_documento",
        obbligatori=("magazzino_id",),
    )
    magazzino_id = campi.pop("magazzino_id")
    _magazzino_o_400(repository, magazzino_id)
    with _db_errors("crea_documento"):
        doc_id = repository.create_documento(f, magazzino_id=magazzino_id, campi=campi)
    return get_documento(codice_famiglia, doc_id)


# Scopo: Aggiorna la testata per DELTA (lista «modifica» del DB: la data, e la
#        descrizione dove c'e'). Fuori da `DRAFT` risponde il verbo
#        (`E_MAG_DOCUMENTO_TESTATA_CONGELATA`, 409).
# ⛔ `magazzino_id` non e' fra le chiavi: si sceglie alla nascita.
def aggiorna_documento(codice_famiglia: str, doc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    campi = _PAYLOAD.campi_del_gesto(
        payload,
        ammesse=repository.colonne_ammesse(f, "testata", "modifica"),
        lettura=_lettura_testata(f),
        function_name=f"{_FN}.aggiorna_documento",
    )
    _documento_o_404(repository, f, doc_id)
    with _db_errors("aggiorna_documento"):
        repository.update_documento(f, doc_id, campi)
    return get_documento(codice_famiglia, doc_id)


# Scopo: Elimina una BOZZA. Il verbo decide (`E_MAG_DOCUMENTO_NON_ELIMINABILE`,
#        409 fuori da `DRAFT`): qui si legge la testata (404) e si passa. Il
#        verbo risponde o solleva: tornato, il documento non c'e' piu'.
def elimina_documento(codice_famiglia: str, doc_id: int) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    with _db_errors("elimina_documento"):
        repository.delete_documento(f, doc_id)
    return {"id": doc_id, "eliminato": True}


# Scopo: Chiede un cambio di stato fra i RICHIEDIBILI al verbo; la matrice la
#        applicano i controlli della tabella
#        (`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, 409).
def cambia_stato_documento(codice_famiglia: str, doc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset({"stato"}))
    stato = _PAYLOAD.require_string(payload, "stato").upper()
    validate_enum_param(
        stato, allowed=STATI_RICHIEDIBILI, param_name="stato",
        error_code=E_VALIDAZIONE, function_name=f"{_FN}.cambia_stato_documento",
        nullable=False,
    )
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    with _db_errors("cambia_stato_documento"):
        repository.set_stato_documento(f, doc_id, stato)
    return get_documento(codice_famiglia, doc_id)


# Scopo: IL POSTING — legge la testata (404), poi UNA `SELECT` sulla madre.
#        Rifiuti (non `CONFIRM`, senza righe, righe non postabili) risalgono
#        tradotti dal database con il loro codice; la transazione e' la madre.
# ⛔ Nessun `transaction.atomic()`: sarebbe un involucro attorno a una
#    scrittura sola, e sposterebbe l'atomicita' da dove sta.
def registra_documento(codice_famiglia: str, doc_id: int) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    with _db_errors("registra_documento"):
        movimenti = repository.posta_documento(f, doc_id)
    return {
        "movimenti": movimenti,
        "n_movimenti": len(movimenti),
        "documento": get_documento(codice_famiglia, doc_id),
    }


# Scopo: Apre un BLOCCO manuale (Lotto 3 D-L3-j, R-5): pezzi di (articolo,
#        magazzino) riservati a qualcuno — una promessa che ferma gli scarichi
#        degli altri (M-3). Permesso (`blocca_merce`), perimetro, posizione
#        coerente con l'articolo e il magazzino: li giudica il verbo DB.
def apri_blocco(payload: dict[str, Any]) -> dict[str, Any]:
    fn = f"{_FN}.apri_blocco"
    repository = MagazzinoRepository()
    with _db_errors("apri_blocco"):
        blocco_id = repository.apri_blocco(
            magazzino_id=_PAYLOAD.require_positive_int(payload, "magazzino_id", function_name=fn),
            articolo_id=str(_PAYLOAD.require_uuid(payload, "articolo_id", function_name=fn)),
            qta=_PAYLOAD.require_decimal(payload, "qta", function_name=fn),
            soggetto_ruolo_id=_PAYLOAD.optional_positive_int(payload, "soggetto_ruolo_id", function_name=fn),
            nota=_PAYLOAD.optional_string(payload, "nota", function_name=fn),
            lotto_id=_PAYLOAD.optional_positive_int(payload, "lotto_id", function_name=fn),
            asset_id=_PAYLOAD.optional_positive_int(payload, "asset_id", function_name=fn),
            ubicazione_id=_PAYLOAD.optional_positive_int(payload, "ubicazione_id", function_name=fn),
        )
    return {"blocco_id": blocco_id}


# Scopo: Libera un blocco: il verbo scrive chi, quando e perche' (la nota).
#        Blocco inesistente o gia' liberato: il codice del DB.
def libera_blocco(blocco_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    nota = _PAYLOAD.optional_string(payload, "nota", function_name=f"{_FN}.libera_blocco")
    with _db_errors("libera_blocco"):
        MagazzinoRepository().libera_blocco(blocco_id, nota)
    return {"blocco_id": blocco_id, "liberato": True}


# Scopo: Il piano di un inventario, paginato: che cosa il posting scrivera'.
# ⚠️ Nessun vincolo di stato (la funzione non ne ha): in `DRAFT` e' un'anteprima.
def list_piano(
    codice_famiglia: str,
    doc_id: int,
    *,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    ErrorManager.require(
        f.ha_piano,
        code=E_VALIDAZIONE,
        message=f"Il piano esiste solo per l'inventario, non per la {f.singolare}.",
        function_name=f"{_FN}.list_piano",
    )
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=PIANO_SORT_COLUMNS,
        function_name=f"{_FN}.list_piano",
    )
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    results, total = repository.list_piano(
        doc_id, search=search, order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return _risposta(results, total)


# ══════════════════════════════════════════════════════════════════
#  Righe
# ══════════════════════════════════════════════════════════════════

# Scopo: Le righe di una testata, paginate (lista `magazzino.<famiglia>_righe`).
def list_righe(
    codice_famiglia: str,
    doc_id: int,
    *,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    order_by, order_dir = ordinamento_validato(
        order_by, order_dir, colonne=righe_sort_columns(f),
        function_name=f"{_FN}.list_righe",
    )
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    results, total = repository.list_righe(
        f, doc_id, search=search, order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return _risposta(results, total)


# Scopo: Il trasporto delle chiavi di riga di una famiglia — le stesse in
#        nascita e in modifica (le due liste del DB coincidono). L'articolo
#        come UUID canonico; quantita' e costo come Decimal ESATTI (bool e NaN
#        rifiutati: il rigore sta nel BB); `null` svuota un nullable
#        (togliere il lotto). Il motivo solo sulla famiglia che lo porta.
def _lettura_riga(f: FamigliaDocumentoInterno) -> Lettura:
    return {
        "testi": {"motivo": (True, MAX_MOTIVO_RIGA)} if f.con_motivo else {},
        "interi": {"ubicazione_id": True, "lotto_id": True, "asset_id": True},
        "altri": {
            "articolo_id": _PAYLOAD.require_uuid,
            f.col_qta: _PAYLOAD.require_decimal,
            "costo_unitario": _PAYLOAD.optional_decimal,
        },
    }


# Scopo: Aggiunge una riga alla testata: articolo e quantita' obbligatori
#        (argomenti del verbo), il resto dalla lista «crea» della riga.
# ⛔ Il BE NON ricalcola la coerenza della riga (Q-3): il DB la accetta in
#    `DRAFT`, il piano la dichiara, il form la mostra con `righe/motivi/`.
def crea_riga(codice_famiglia: str, doc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    campi = _PAYLOAD.campi_del_gesto(
        payload,
        ammesse=repository.colonne_ammesse(f, "riga", "crea"),
        lettura=_lettura_riga(f),
        function_name=f"{_FN}.crea_riga",
        obbligatori=("articolo_id", f.col_qta),
    )
    _documento_o_404(repository, f, doc_id)
    with _db_errors("crea_riga"):
        riga_id = repository.create_riga(
            f, doc_id,
            articolo_id=campi.pop("articolo_id"),
            qta=campi.pop(f.col_qta),
            campi=campi,
        )
    return dict(_riga_o_404(repository, f, doc_id, riga_id))


# Scopo: Aggiorna una riga per DELTA (lista «modifica» della riga). Fuori da
#        `DRAFT` risponde il guard di famiglia.
def aggiorna_riga(codice_famiglia: str, doc_id: int, riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    campi = _PAYLOAD.campi_del_gesto(
        payload,
        ammesse=repository.colonne_ammesse(f, "riga", "modifica"),
        lettura=_lettura_riga(f),
        function_name=f"{_FN}.aggiorna_riga",
    )
    _documento_o_404(repository, f, doc_id)
    _riga_o_404(repository, f, doc_id, riga_id)
    with _db_errors("aggiorna_riga"):
        repository.update_riga(f, doc_id, riga_id, campi)
    return dict(_riga_o_404(repository, f, doc_id, riga_id))


# Scopo: Toglie una riga col verbo. Il guard di famiglia risponde fuori da
#        `DRAFT`; tornato il verbo, la riga non c'e' piu'.
def elimina_riga(codice_famiglia: str, doc_id: int, riga_id: int) -> dict[str, Any]:
    f = famiglia(codice_famiglia)
    repository = MagazzinoRepository()
    _documento_o_404(repository, f, doc_id)
    _riga_o_404(repository, f, doc_id, riga_id)
    with _db_errors("elimina_riga"):
        repository.delete_riga(f, doc_id, riga_id)
    return {"riga_id": riga_id, "eliminata": True}


# Scopo: I MOTIVI per cui una riga non sarebbe postabile — `fn_check_riga_
#        magazzino` cosi' com'e', per l'anteprima del form (§12.5.2: la
#        stessa funzione che il piano e la primitiva usano). `[]` = nessuno.
def motivi_riga(
    *,
    magazzino_id: int,
    articolo_id: str,
    lotto_id: int | None,
    asset_id: int | None,
    ubicazione_id: int | None,
) -> dict[str, Any]:
    _PAYLOAD.guard_positive_int(magazzino_id, field="magazzino_id")
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=True, function_name=f"{_FN}.motivi_riga",
    )
    motivi = MagazzinoRepository().check_riga(
        magazzino_id=magazzino_id,
        articolo_id=articolo_id,
        lotto_id=lotto_id,
        asset_id=asset_id,
        ubicazione_id=ubicazione_id,
    )
    return {"motivi": motivi}


# ══════════════════════════════════════════════════════════════════
#  I lookup di riga
# ══════════════════════════════════════════════════════════════════

# Scopo: Le ubicazioni attive di un magazzino, per il form di riga.
def lookup_ubicazioni(magazzino_id: int) -> dict[str, Any]:
    _PAYLOAD.guard_positive_int(magazzino_id, field="magazzino_id")
    return {"results": MagazzinoRepository().lookup_ubicazioni(magazzino_id)}


# Scopo: I lotti attivi di un articolo, dell'emittente del magazzino, con
#        ricerca sul codice (il lotto e' dell'azienda, come il seriale).
def lookup_lotti(*, articolo_id: str, magazzino_id: int, search: str | None) -> dict[str, Any]:
    _PAYLOAD.guard_positive_int(magazzino_id, field="magazzino_id")
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=True, function_name=f"{_FN}.lookup_lotti",
    )
    return {"results": MagazzinoRepository().lookup_lotti(articolo_id, magazzino_id, search)}


# Scopo: I seriali attivi di un articolo, dell'emittente del magazzino.
def lookup_assets(*, articolo_id: str, magazzino_id: int) -> dict[str, Any]:
    _PAYLOAD.guard_positive_int(magazzino_id, field="magazzino_id")
    articolo_id = articolo_uuid(
        articolo_id, obbligatorio=True, function_name=f"{_FN}.lookup_assets",
    )
    return {"results": MagazzinoRepository().lookup_assets(articolo_id, magazzino_id)}
