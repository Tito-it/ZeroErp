# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il CONTESTO che il risolutore IVA vuole, ricavato dalla testata di un
#        documento di vendita — e ricavato in UN posto solo.
#
#        ⛔ ESISTE PER UNA RAGIONE PRECISA, e non e' la de-duplicazione.
#        L'anteprima (il form) e il salvataggio (il service) devono guardare
#        la STESSA fonte, o mostrano un numero e ne scrivono un altro. Il
#        frontend non ha, in modo uniforme, i campi che al risolutore servono:
#        `PreventiviRigaForm` conosce il billing account, `OrdiniRigaForm` e
#        `DdtRigaForm` hanno il solo id del documento. Farglieli passare come
#        prop attraverso due livelli avrebbe messo nel client la conoscenza di
#        QUALI campi servono al risolutore — che e' precisamente la
#        conoscenza destinata a invecchiare (decisione di Tid, opzione «c»).
#
#        Due funzioni, e la separazione e' voluta:
#        * `carica_testata` fa I/O — la usa chi ha in mano solo un id (la view);
#        * `contesto_da_testata` e' PURA — la usano i service, che la testata
#          l'hanno gia' caricata e non devono spendere un secondo round-trip.
#
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (F2-d)
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from collections.abc import Mapping
from typing import Any, Callable

from apps.config.sorgenti import (
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService

__all__ = [
    "TIPI_DOCUMENTO_AMMESSI",
    "carica_testata",
    "contesto_da_testata",
    "make_risolvi_iva_riga",
    "normalizza_iva_id",
]

# Scopo: la testata del preventivo. I tre loader hanno import LOCALI per non
#        creare cicli fra i service di dominio e questo modulo (che loro
#        importano).
def _carica_preventivo(documento_id: int) -> Mapping[str, Any] | None:
    from apps.vendite.db.preventivi_repository import PreventiviRepository

    return PreventiviRepository().get_preventivo(documento_id)


# Scopo: la testata dell'ordine (stesso perimetro di `_carica_preventivo`).
def _carica_ordine(documento_id: int) -> Mapping[str, Any] | None:
    from apps.vendite.db.ordini_repository import OrdiniRepository

    return OrdiniRepository().get_ordine(documento_id)


# Scopo: la testata del DDT (stesso perimetro di `_carica_preventivo`).
def _carica_ddt(documento_id: int) -> Mapping[str, Any] | None:
    from apps.vendite.db.ddt_repository import DdtRepository

    return DdtRepository().get_ddt(documento_id)


# ⭐ Whitelist a dizionario e non una catena di `if`: aggiungere un dominio e'
#    una voce, ed e' lo stesso stampo di `_SORGENTE_CONFIG` in
#    `approvazioni_prezzo_service`. ⛔ E' anche il cancello: un `tipo` fuori
#    elenco non arriva mai a comporre un nome di tabella.
# ⭐ I tipi sono i codici di `config.sorgenti` (dal 2026-10-19,
#    brief-db-grammatica-unica-documenti lotto 2a: una grammatica sola per i
#    tipi di documento).
_LOADER: dict[str, Callable[[int], Mapping[str, Any] | None]] = {
    SORGENTE_PREVENTIVO: _carica_preventivo,
    SORGENTE_ORDINE_VENDITA: _carica_ordine,
    SORGENTE_DDT_VENDITA: _carica_ddt,
}


# ⛔ UNA SORGENTE SOLA: i tipi ammessi SONO le chiavi del registro. Erano due
#    elenchi scritti a mano, e aggiungerne uno solo di la' avrebbe fatto
#    passare il guard e poi sollevato un `KeyError` grezzo dentro la lettura —
#    un errore tecnico al posto di un rifiuto parlante. Sono le `choices` di
#    `views_iva.py`, quindi il contratto dell'API: `ORDINE_VENDITA` e
#    `DDT_VENDITA`, non piu' i corti.
TIPI_DOCUMENTO_AMMESSI: tuple[str, ...] = tuple(_LOADER)


# Scopo: Carica la testata del documento indicato, validando il tipo contro la
#        whitelist.
# Perimetro: sola lettura. Lo scope RLS resta quello del chiamante: un
#        documento fuori perimetro non si legge e diventa un «non trovato»,
#        che e' la stessa risposta che dara' il salvataggio.
def carica_testata(
    *,
    documento_tipo: str,
    documento_id: int,
    error_code: str,
    function_name: str,
) -> dict[str, Any]:
    ErrorManager.require(
        documento_tipo in _LOADER,
        code=error_code,
        message="Tipo documento non ammesso per la risoluzione IVA.",
        detail=f"ammessi: {', '.join(sorted(_LOADER))}",
        context={"field": "documento_tipo"},
        function_name=function_name,
    )
    ErrorManager.require(
        isinstance(documento_id, int) and documento_id > 0,
        code=error_code,
        message="documento_id obbligatorio.",
        context={"field": "documento_id"},
        function_name=function_name,
    )
    testata = _LOADER[documento_tipo](documento_id)
    ErrorManager.require(
        testata is not None,
        code=error_code,
        message="Documento non trovato.",
        context={"documento_tipo": documento_tipo, "documento_id": documento_id},
        function_name=function_name,
    )
    assert testata is not None
    return dict(testata)


# Scopo: Estrae dalla testata i quattro valori che il risolutore vuole —
#        emittente (PK), billing account, utility e data di riferimento.
# Perimetro: PURA, nessun I/O tranne il ripiego sull'operatore quando la
#        testata l'emittente non ce l'ha.
#
# ⛔ `emittente_fiscale_id` E' LA PK di `anagrafiche.emittenti_fiscali`, non il
#    `soggetto_ruolo_id` che il pricing usa. I due numeri si somigliano
#    abbastanza da passare inosservati, e con quello sbagliato il risolutore
#    non trova l'emittente, quindi non trova i suoi titoli, e risponde con
#    l'aliquota ordinaria SENZA sollevare.
#
# ⚠️ L'emittente in DUE PASSI — prima quello del documento, poi quello
#    dell'operatore — come gia' fa l'init dei componenti sui preventivi. Ma qui
#    l'assenza NON e' uno skip silenzioso: `P3` dice che ci si ferma.
def contesto_da_testata(
    testata: dict[str, Any],
    *,
    auth_user_id: int | None = None,
    error_code: str,
    function_name: str,
) -> dict[str, Any]:
    fiscale_id = testata.get("emittente_fiscale_id")
    if fiscale_id is None and auth_user_id is not None:
        fiscale_id = ParameterService().get_emittente_fiscale_id_for_user(auth_user_id)
    ErrorManager.require(
        fiscale_id is not None,
        code=error_code,
        message=(
            "Emittente fiscale non risolvibile: il trattamento IVA non e' "
            "determinabile."
        ),
        function_name=function_name,
    )
    assert fiscale_id is not None

    data_raw = testata.get("data")
    # ⚠️ Il risolutore prende una data e non legge mai l'«oggi» (D14):
    #    senza, non c'e' niente da passargli. Errore di dominio, non un
    #    `ValueError` grezzo da `fromisoformat`.
    ErrorManager.require(
        data_raw is not None,
        code=error_code,
        message="Documento senza data: il trattamento IVA non e' determinabile.",
        function_name=function_name,
    )

    return {
        "emittente_fiscale_id": int(fiscale_id),
        "billing_account_id": testata.get("billing_account_id"),
        "utility_id": testata.get("utility_id"),
        "data_riferimento": (
            data_raw
            if isinstance(data_raw, date)
            else date.fromisoformat(str(data_raw))
        ),
    }


# Scopo: normalizza l'`iva_id` che arriva dal payload di una riga.
# ⛔ `int(x) if x else None` E' LA FORMA SBAGLIATA, ed era scritta in tre
#    service: uno `0` esplicito e' *falsy*, quindi diventava `None` — cioe'
#    «nessuna scelta», e il risolutore rispondeva in modo AUTORITATIVO su un
#    payload che invece portava un valore (invalido). Un id non positivo non e'
#    un'assenza: e' un errore, e va detto.
# ⚠️ La stringa vuota resta un'assenza: e' cio' che il form manda quando il
#    campo non e' compilato, e i service la normalizzano gia' con
#    `empty_to_none` — tranne preventivi, che passa il payload grezzo.
def normalizza_iva_id(raw: Any, *, error_code: str, function_name: str) -> int | None:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None
    try:
        valore = int(raw)
    except (TypeError, ValueError):
        valore = 0
    ErrorManager.require(
        valore > 0,
        code=error_code,
        message="iva_id non valido.",
        context={"field": "iva_id"},
        function_name=function_name,
    )
    return valore


# Scopo: costruisce il `_risolvi_iva_riga` di un dominio — la funzione che dal
#        contesto di testata ottiene `(iva_id, meta_patch)` per la riga.
# ⭐ FACTORY e non tre copie: i tre service ne avevano una ciascuno, identiche a
#    meno del codice errore. E' lo stesso stampo di
#    `payload_helpers.make_db_errors_translator`, che fissa una volta i
#    parametri di dominio e restituisce il callable — cosi' i punti di chiamata
#    restano leggibili e la regola sta in un posto solo.
# ⚠️ `usa_auth_user` esiste perche' UN dominio si comporta diversamente e va
#    detto: sui preventivi l'emittente puo' non stare in testata (admin globale
#    che non l'ha scelto) e si ripiega su quello dell'operatore. Su DDT e ordini
#    la testata ce l'ha sempre — il trigger normalize lo garantisce NOT NULL.
# ⛔ `payload_iva_id` E' UN PARAMETRO CHE VALE SEMPRE `None`, dal 2026-08-31
#    (`I6`): la casella IVA e' chiusa sui tre domini, quindi nessuna riga porta
#    piu' un'aliquota scelta a mano. Il parametro RESTA, e resta guardato:
#    `applica_riga_documento` distingue due rami che NON hanno lo stesso peso —
#    senza valore la risoluzione e' AUTORITATIVA e i suoi errori passano, con un
#    valore diventa AUDIT best-effort dentro un savepoint, cioe' gli errori si
#    INGHIOTTONO e a vincere e' il payload.
# ⇒ Chi un giorno rimettesse una scelta manuale su un documento non otterrebbe
#    un errore: otterrebbe, in silenzio, una riga che si salva anche quando
#    l'IVA non e' determinabile. Il guard qui sotto trasforma quel silenzio in
#    un rifiuto, e costa una riga.
def make_risolvi_iva_riga(
    *,
    error_code: str,
    function_name: str,
    usa_auth_user: bool = False,
) -> Callable[..., tuple[int | None, dict[str, Any]]]:
    def _risolvi(
        testata: dict[str, Any],
        *,
        articolo_id: str,
        payload_iva_id: Any = None,
        auth_user_id: int | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        ErrorManager.require(
            payload_iva_id is None,
            code=error_code,
            message="L'aliquota IVA non si sceglie sulla riga del documento.",
            detail=(
                "`I6`: la casella e' chiusa e l'IVA la decide il risolutore. "
                f"Ricevuto payload_iva_id={payload_iva_id!r}"
            ),
            context={"field": "iva_id"},
            function_name=function_name,
        )
        # Import locale: il BB del risolutore importa questo modulo? No — ma
        # l'import qui tiene il grafo piatto e non costa nulla a runtime.
        from apps.vendite.services.iva_resolver_service import IvaResolverService

        ctx = contesto_da_testata(
            testata,
            auth_user_id=auth_user_id if usa_auth_user else None,
            error_code=error_code,
            function_name=function_name,
        )
        return IvaResolverService().applica_riga_documento(
            payload_iva_id=normalizza_iva_id(
                payload_iva_id, error_code=error_code, function_name=function_name,
            ),
            articolo_id=articolo_id,
            **ctx,
        )

    return _risolvi

