# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facciata del dominio `pagamenti` — le distinte contabili e le loro
#        righe. Orchestrazione sottile: validazione del payload, traduzione
#        degli errori del database, composizione della risposta.
# Note: 🔴 Il backend qui e' sottile PER OBBLIGO, non per stile. Le regole di
#       questo dominio vivono in quindici guard e due matrici di transizione
#       dentro PostgreSQL: riscriverle qui significherebbe avere due sedi che
#       divergono al primo aggiornamento. Il service NON decide se una
#       transizione e' ammessa, se una distinta quadra, se una rata ha
#       capienza: chiede, e traduce la risposta.
#
#       ⛔ E in particolare NON compone piu' scritture: il posting e' UNA SOLA
#       `SELECT pagamenti.fn_posta_contabile(...)`, atomica per costruzione.
#       Un guardrail AST in CI vede il livello repository e boccerebbe la
#       build, ma la regola non e' la rete: e' che quelle due scritture non
#       devono esistere.
# ------------------------------------------------------------

import json
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.core.api.payload_validators import envelope_da_offset
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.fan_out import run_fan_out
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.services.list_helpers import (
    validate_enum_param,
    validate_order_params,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.pagamenti.services._helpers import (
    E_FATTURA_NON_TROVATA,
    E_RATA_NON_TROVATA,
    E_VALIDAZIONE,
)
from apps.pagamenti.db.pagamenti_repository import (
    DISTINTA_RIGHE_SORT_COLUMNS,
    DISTINTE_SORT_COLUMNS,
    RATE_FUORI_CAPIENZA_SORT_COLUMNS,
    RIGHE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.types import (
    DistintaDettaglioRow,
    RicevutaPosting,
    RicevutaTardiva,
    RigaContabileRow,
)

logger = logging.getLogger(__name__)

_FN = "pagamenti.pagamenti_service"



# Codici di dominio gia' a catalogo che il backend solleva da se': sono i due
# casi in cui l'oggetto non c'e' (o il perimetro non lo lascia vedere, e i due
# restano volutamente indistinguibili).
E_DISTINTA_NON_TROVATA = "E_CONTABILE_NON_TROVATA"
E_RIGA_NON_TROVATA = "E_RIGA_CONTABILE_NON_TROVATA"
# La fattura di destinazione che non c'e' (`E_FATTURA_NON_TROVATA`) e' lo
# stesso codice di `saldi_service` e `sistemazioni_service`: importato da
# `_helpers`, non riscritto.
# Lo stato chiesto non risolve a catalogo (assente o non attivo). ⭐ TECNICO e
# non «dato sbagliato»: chi ha fatto la richiesta non puo' rimediare — manca
# una riga di configurazione, e la mette chi amministra il database.
E_STATO_NON_CONFIGURATO = "E_CONTABILE_STATO_NON_CONFIGURATO"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

# Traduzione degli errori del database in errori parlanti. ⚠️ I guard di
# `pagamenti` sollevano gia' codici registrati con la loro frase: il traduttore
# li fa passare INTATTI e serve per le violazioni di vincolo (FK), dove il
# database parla il linguaggio dei nomi di vincolo e non quello di chi legge.
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_vendite_contabili_centro": (E_VALIDAZIONE, "Centro di riscossione non valido."),
    "fk_vendite_contabili_ente": (E_VALIDAZIONE, "Canale di incasso non valido."),
    "fk_vendite_contabili_righe_contabile": (
        E_VALIDAZIONE,
        "Distinta contabile non valida.",
    ),
    "fk_vendite_contabili_righe_fattura": (E_VALIDAZIONE, "Fattura non valida."),
    "fk_vendite_contabili_righe_billing_account": (
        E_VALIDAZIONE,
        "Cliente (billing account) non valido.",
    ),
    "fk_vendite_contabili_righe_scadenza": (E_VALIDAZIONE, "Rata non valida."),
}

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo sulla distinta contabile.",
    fk_constraints=_FK_CONSTRAINTS,
)

# ⭐ Vocabolario chiuso: gli stati che una PERSONA puo' chiedere sulla testata.
# ⛔ `CHIUSA` non c'e', e non e' una dimenticanza: la chiusura e' una
#    CONSEGUENZA del registrare, non un gesto a parte — la scrive la funzione
#    madre. Un pulsante «chiudi» rimetterebbe in mano a qualcuno una decisione
#    che il database prende da se'.
# ⛔ `IMPORTATA` nemmeno: la scrive l'import, che non esiste ancora.
STATI_DISTINTA_RICHIEDIBILI: tuple[str, ...] = ("VALIDATA", "BOZZA", "ANNULLATA")

# Gli stati che una persona puo' chiedere su una riga. `POSTATA` non c'e': la
# scrive il posting. `IMPORTATA` la scrive l'import.
STATI_RIGA_RICHIEDIBILI: tuple[str, ...] = (
    "DA_ABBINARE",
    "ABBINATA",
    "SOSPESA",
    "SCARTATA",
)

# Le origini che il backend puo' creare. ⭐ Solo `MANUALE`: `GENERATA` la scrive
# il giro dei fondi fattura, `AUTOMATICA` l'import.
ORIGINE_MANUALE = "MANUALE"
# Il vocabolario INTERO dell'origine, per il filtro della lista: specchio del
# CHECK `chk_vendite_contabili_origine`, che il guardrail
# `test_specchi_dei_check_db` confronta col database.
ORIGINI_VENDITA_CONTABILE: tuple[str, ...] = (ORIGINE_MANUALE, "AUTOMATICA", "GENERATA")

# Gli stati in cui i due oggetti NASCONO. Sono codici di catalogo, non id: gli
# id sono seminati e non si scrivono a mano da nessuna parte.
STATO_DISTINTA_INIZIALE = "BOZZA"
# ⭐ La riga MANUALE nasce con la destinazione (D16, 2026-09-14): chi digita un
#    incasso da una contabile sa chi ha pagato, quindi la riga nasce gia'
#    `ABBINATA` — fattura, cliente e (facoltativa) rata nello stesso INSERT.
# ⚠️ `DA_ABBINARE` e' lo stato di un importo arrivato SENZA NOME: sulla manuale
#    e' l'ECCEZIONE che l'operatore dichiara («non ho trovato il documento»),
#    non il default di un form. Fino al 14/09 era il default, col commento
#    «quando il denaro arriva non si sa ancora di chi sia» — vero per l'import,
#    falso per chi digita: il default aveva scelto il flusso sbagliato.
STATO_RIGA_SENZA_DESTINAZIONE = "DA_ABBINARE"
# Lo stato in cui l'abbinamento porta la riga — alla nascita come dopo: e' lo
# stesso gesto, non due.
STATO_RIGA_ABBINATA = "ABBINATA"
# ⭐ «Non e' nostra» (D20-c, 2026-09-18): la riga SCARTATA resta nella distinta
#    — e' lei la traccia, e conta nella quadratura («quel denaro e' arrivato»)
#    — ma ESCE DAL LAVORO: nascosta di default fra le righe del drawer, mai in
#    nessuna coda. Si nomina qui, per codice, come gli altri due: la lista la
#    filtra e la quadratura la conta «di cui non nostre».
STATO_RIGA_SCARTATA = "SCARTATA"
# ⭐ Lo stato in cui si ENTRA validando (D20-a/D20-d): e' quello che il catalogo
#    marca `is_registrabile`. Si nomina per il solo cancello della terna del
#    verbo «valida» (`_transizione_verso_validata`): il resto lo legge dal flag.
STATO_DISTINTA_VALIDATA = "VALIDATA"
# ⭐ L'origine e lo stato della distinta sotto cui il CONTENUTO delle righe si
#    lavora (D17/D18): righe nuove, fatti modificati, eliminazioni. ⚠️ E' una
#    COPIA DICHIARATA del motivo 3 di `script.fn_check_riga_contabile_eliminabile`
#    e della porta 2 di `trgfn_vendite_contabili_righe_guard_contenuto` — il
#    database stesso lo scrive due volte (brief §4 P-5) perche' sull'INSERT non
#    c'e' una riga da passare alla check. Il presidio e' il pgTAP del guard piu'
#    `test_gli_stati_iniziali_esistono_a_catalogo`: il rifiuto vero arriva
#    comunque dal DB (409), questo flag serve solo a NON PROPORRE.

# ⭐ Le due code del riconciliatore, e sono DUE MESTIERI (D12-f): `DA_ABBINARE`
#    e' lavoro non ancora fatto, `SOSPESA` e' lavoro fatto che ha trovato un
#    ostacolo. Due voci di menu, una lista sola con il filtro gia' impostato.
CODE_RIGHE: dict[str, tuple[str, ...]] = {
    "DA_ABBINARE": ("DA_ABBINARE",),
    "SOSPESE": ("SOSPESA",),
    # La terza voce non e' una coda: e' il modo di guardarle insieme quando
    # serve, e non compare in nessun menu.
    "TUTTE": ("DA_ABBINARE", "SOSPESA"),
}

# I due motivi per cui una rata esce dalla banda di capienza.
MOTIVI_FUORI_CAPIENZA: tuple[str, ...] = ("SOVRA_INCASSATA", "MOVIMENTO_CONTRARIO")

# Campi della testata che una persona compila. ⛔ Lo stato non e' qui: quello e'
# un'azione, e ha il suo endpoint.
_CAMPI_DISTINTA_PATCH: tuple[str, ...] = (
    "data_contabile",
    "ente_incasso_id",
    "importo_dichiarato",
    "meta",
)

# I FATTI di una riga (come sono arrivati i soldi) e le decisioni che non sono
# un'azione di dominio. ⛔ `fattura_id`, `billing_account_id` e `scadenza_id`
# NON sono qui: abbinare e' un verbo, e porta con se' la destinazione. ⭐ Alla
# NASCITA invece la destinazione viaggia coi fatti (D16): una riga che nasce
# non ha uno stato da proteggere — R-6 vale per la modifica.
_CAMPI_RIGA_PATCH: tuple[str, ...] = (
    "importo",
    "riferimento_ente",
    "data_pagamento",
    "data_valuta",
    "data_operazione",
    "motivo_sospeso",
    "meta",
)

# ⭐ IL SECONDO TEMPO: la conferma di una scrittura che il guard della rata
#    rifiuterebbe. Viaggia con OGNI verbo che quel guard incontra — nascita,
#    abbinamento e, dal 2026-09-15 (decisione di Tid, brief D16/D17 Q-H),
#    anche la MODIFICA dell'importo: il guard gira sull'`UPDATE` come
#    sull'`INSERT`, e un 409 «confermabile» su un verbo che non sa raccogliere
#    la conferma e' una domanda a cui nessuno puo' rispondere. ⛔ Non e' la
#    destinazione: R-6 protegge `fattura_id`/`billing_account_id`/`scadenza_id`
#    e resta intero.
_CAMPI_FORZATURA: tuple[str, ...] = ("forzata", "motivo_forzatura")

# La DESTINAZIONE di una riga: le chiavi che `abbina` e `crea` leggono allo
# stesso modo (una lettura sola, `_destinazione_da_payload`).
_CAMPI_DESTINAZIONE: tuple[str, ...] = (
    "fattura_id",
    "billing_account_id",
    "scadenza_id",
    *_CAMPI_FORZATURA,
)


# ══════════════════════════════════════════════════════════════════
#  Helper locali
# ══════════════════════════════════════════════════════════════════

# Scopo: Serializza `meta` per il passaggio a una colonna jsonb.
def _meta_json(payload: dict[str, Any]) -> str:
    meta = _PAYLOAD.optional_meta(payload, "meta")
    return json.dumps(meta or {})


# Scopo: Legge la distinta o solleva il 404 di dominio.
# ⚠️ «Non esiste» e «non la vedi» danno la stessa risposta, ed e' voluto: dire
#    «esiste ma non e' tua» racconterebbe a un operatore fuori perimetro che
#    quel documento c'e'.
def _distinta_o_404(repository: PagamentiRepository, contabile_id: int) -> DistintaDettaglioRow:
    distinta = repository.get_distinta(contabile_id)
    ErrorManager.require(
        distinta is not None,
        code=E_DISTINTA_NON_TROVATA,
        message="Distinta contabile non trovata.",
        detail=f"contabile_id={contabile_id}",
        function_name=_FN,
    )
    assert distinta is not None
    return distinta


# Scopo: Legge la riga o solleva il 404 di dominio.
def _riga_o_404(repository: PagamentiRepository, riga_id: int) -> RigaContabileRow:
    riga = repository.get_riga(riga_id)
    ErrorManager.require(
        riga is not None,
        code=E_RIGA_NON_TROVATA,
        message="Riga contabile non trovata.",
        detail=f"riga_id={riga_id}",
        function_name=_FN,
    )
    assert riga is not None
    return riga


# Scopo: «Il motivo si scrive solo insieme alla forzatura» — la regola vale
#        identica ovunque la forzatura entri: nascita, abbinamento, modifica.
# ⚠️ Un motivo senza forzatura e' una nota che nessuno leggera' mai: la
#    colonna esiste per spiegare una forzatura, e scriverla su una riga non
#    forzata lascerebbe a registro una spiegazione di un gesto mai fatto.
def _guard_motivo_con_forzatura(
    forzata: bool, motivo_forzatura: str | None, *, function_name: str
) -> None:
    ErrorManager.require(
        forzata or motivo_forzatura is None,
        code=E_VALIDAZIONE,
        message="Il motivo si scrive solo insieme alla forzatura.",
        detail="motivo_forzatura richiede forzata = true.",
        context={"field": "motivo_forzatura"},
        function_name=function_name,
    )


# Scopo: Legge la DESTINAZIONE di una riga dal payload — fattura, cliente,
#        rata facoltativa e la forzatura col suo motivo — con le regole che
#        valgono sia per `abbina` sia per la nascita della riga (D16).
# Note: ⭐ Una lettura sola per i due verbi: la regola «il motivo si scrive solo
#       insieme alla forzatura» e quella «rata e forzatura pretendono una
#       fattura» stavano per nascere due volte, e due copie divergono alla
#       prima correzione.
#       ⚠️ `obbligatoria=False` e' la nascita: senza `fattura_id` la riga nasce
#       senza destinazione (l'eccezione dichiarata), e allora rata, cliente e
#       forzatura non hanno niente a cui riferirsi — un valore li' e' un
#       errore del chiamante, non un dato da ignorare in silenzio.
#       ⚠️ `billing_account_id` puo' mancare: lo deriva chi chiama, dalla
#       fattura (`get_riferimenti_fattura`). Qui si legge, non si risolve.
def _destinazione_da_payload(
    payload: dict[str, Any], *, obbligatoria: bool, function_name: str
) -> dict[str, Any]:
    if obbligatoria:
        fattura_id: int | None = _PAYLOAD.require_positive_int(
            payload, "fattura_id", message="La fattura e' obbligatoria per abbinare."
        )
    else:
        fattura_id = _PAYLOAD.optional_positive_int(payload, "fattura_id")
    billing_account_id = _PAYLOAD.optional_positive_int(payload, "billing_account_id")
    scadenza_id = _PAYLOAD.optional_positive_int(payload, "scadenza_id")
    forzata = _PAYLOAD.optional_bool(payload, "forzata") or False
    motivo_forzatura = _PAYLOAD.optional_string(payload, "motivo_forzatura")
    _guard_motivo_con_forzatura(forzata, motivo_forzatura, function_name=function_name)
    # ⚠️ Senza fattura non c'e' destinazione: una rata, un cliente o una
    #    forzatura «orfani» non sono un'eccezione dichiarata — sono un payload
    #    rotto, e si dice quale campo.
    if fattura_id is None:
        for campo, valore in (
            ("scadenza_id", scadenza_id),
            ("billing_account_id", billing_account_id),
            ("forzata", forzata or None),
        ):
            ErrorManager.require(
                valore is None,
                code=E_VALIDAZIONE,
                message="Senza fattura la riga non ha una destinazione.",
                detail=f"{campo} richiede fattura_id.",
                context={"field": campo},
                function_name=function_name,
            )
    return {
        "fattura_id": fattura_id,
        "billing_account_id": billing_account_id,
        "scadenza_id": scadenza_id,
        "forzata": forzata,
        "motivo_forzatura": motivo_forzatura,
    }


# Scopo: Risolve il cliente della riga quando il chiamante non lo passa: e' il
#        billing account della fattura scelta, letto dal documento.
# ⚠️ Il 404 di una fattura inesistente (o fuori perimetro) esce di qui col
#    codice di dominio, prima dell'INSERT — e nomina il campo.
def _billing_account_della_fattura(
    repository: PagamentiRepository, fattura_id: int, *, function_name: str
) -> int:
    riferimenti = repository.get_riferimenti_fattura(fattura_id)
    ErrorManager.require(
        riferimenti is not None,
        code=E_FATTURA_NON_TROVATA,
        message="Fattura non trovata.",
        detail=f"fattura_id={fattura_id}",
        context={"field": "fattura_id"},
        function_name=function_name,
    )
    assert riferimenti is not None
    return int(riferimenti["billing_account_id"])


# Scopo: Compone i campi da aggiornare leggendo SOLO le chiavi presenti nel
#        payload — un PATCH che non nomina un campo non lo tocca.
def _campi_presenti(
    payload: dict[str, Any],
    consentiti: tuple[str, ...],
    *,
    lettori: dict[str, Any],
) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset(consentiti))
    campi: dict[str, Any] = {}
    for chiave in consentiti:
        if chiave in payload:
            campi[chiave] = lettori[chiave](payload)
    return campi


# ══════════════════════════════════════════════════════════════════
#  Distinte — lettura
# ══════════════════════════════════════════════════════════════════

# Scopo: Elenco paginato delle distinte contabili.
# Perimetro: la RLS dello schema; il filtro data ha il floor standard delle
#        liste (lo applica il chiamante, non questo service).
def list_distinte(
    *,
    stato: str | None = None,
    origine: str | None = None,
    centro_riscossione_id: int | None = None,
    ente_incasso_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    order_by, order_dir = validate_order_params(
        order_by or "data_contabile",
        order_dir or "desc",
        allowed_columns=frozenset(DISTINTE_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_distinte",
    )
    # ⛔ I due filtri nel loro vocabolario, o un 400 sul campo — come la doc
    #    promette («un 400, mai una lista vuota»): fino al 2026-10-20 andavano
    #    nel WHERE senza controllo. Lo stato e' una tabella (codici dismessi
    #    ammessi), l'origine un CHECK (lo specchio qui sopra).
    richiedi_codice_a_vocabolario(
        "pagamenti.vendite_contabili_stati", "codice_interno", stato,
        codice_errore=E_VALIDAZIONE, parametro="stato",
    )
    validate_enum_param(
        origine, allowed=ORIGINI_VENDITA_CONTABILE, param_name="origine",
        error_code=E_VALIDAZIONE, function_name=f"{_FN}.list_distinte",
    )

    repository = PagamentiRepository()
    results, total = repository.list_distinte(
        stato_codice=stato,
        origine=origine,
        centro_riscossione_id=centro_riscossione_id,
        ente_incasso_id=ente_incasso_id,
        data_da=data_da,
        data_a=data_a,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return envelope_da_offset(results, total, limit=limit, offset=offset)


# Scopo: Le transizioni che una PERSONA puo' chiedere, stato per stato, lette
#        dalla MATRICE del database e ristrette al vocabolario dei richiedibili.
# ⭐ E' il pezzo che mancava (BE-5, collaudo del 14/09): il vocabolario dice
#    che cosa si puo' chiedere IN GENERALE, la matrice dice DA DOVE. Offrire il
#    vocabolario intero meno lo stato corrente proponeva `SCARTATA` su una riga
#    `ABBINATA`, che il database rifiuta — un pulsante che finisce in errore.
# ⚠️ `stato_a` ristretto ai richiedibili, `stato_da` no: `POSTATA` e `CHIUSA`
#    non si chiedono (li scrive la registrazione) ma da `IMPORTATA` — quando
#    l'import ci sara' — si chiede eccome. La forma e' `{stato_da: [stato_a…]}`
#    per entrambe le macchine, e uno stato senza uscite richiedibili ha la
#    lista vuota, non la chiave assente.
def _transizioni_richiedibili(
    grafo: list[tuple[str, str]], richiedibili: tuple[str, ...]
) -> dict[str, list[str]]:
    ammesse: dict[str, list[str]] = {}
    for stato_da, stato_a in grafo:
        ammesse.setdefault(stato_da, [])
        if stato_a in richiedibili and stato_a not in ammesse[stato_da]:
            ammesse[stato_da].append(stato_a)
    # L'ordine di offerta e' quello del vocabolario, non quello della matrice:
    # e' stabile fra una lettura e l'altra e non dipende dagli id seminati.
    for stato_da, uscite in ammesse.items():
        ammesse[stato_da] = sorted(uscite, key=richiedibili.index)
    return ammesse


# Scopo: Dettaglio di una distinta: testata, totali derivati, i due cataloghi
#        di stato e le transizioni ammesse — in un round-trip solo.
# ⭐ I cataloghi viaggiano col dettaglio e non si cablano nel frontend: quali
#    stati si possono chiedere e da dove, quali pretendono fattura e cliente,
#    quali occupano spazio su una rata lo dice il database.
# ⛔ Le RIGHE non viaggiano piu' qui (dal 2026-09-18): sono una lista
#    configurabile con la sua pagina (`list_righe`), e portarle anche nel
#    dettaglio sarebbe leggere due volte la parte piu' costosa (la LATERAL
#    sulla check di eliminabilita', per riga) a ogni apertura del drawer — per
#    un campo che nessuno legge piu'.
# ⭐ E porta il verbo «valida» COL MOTIVO (BE-1, D20-a): la terna
#    `validazione_blocco_*` + `can_validare`, letta dalla STESSA check che il
#    guard chiama per rifiutare. ⚠️ Viaggia SOLO se lo stato corrente ammette
#    VALIDATA fra le uscite (la matrice, gia' letta qui): su una CHIUSA o su
#    una ANNULLATA il verbo non si propone, e un motivo per un pulsante che
#    non c'e' sarebbe rumore — si azzera a `null`, non si inventa.
# ⭐ `righe_per_stato` e i due numeri «di cui non nostre» (`righe_scartate`,
#    `totale_scartate`): la quadratura li mostra accanto al totale, perche'
#    «dichiarato 1000 · righe 1000» con 200 di scartate dentro si legge come
#    «tutto nostro» — e non lo e'. Derivati QUI dall'array, con lo stesso
#    codice che la lista usa per nasconderle: una sede, non due letterali.
def get_distinta(contabile_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    distinta = _distinta_o_404(repository, contabile_id)
    grafo_distinta, grafo_riga = repository.list_transizioni()
    transizioni_distinta = _transizioni_richiedibili(
        grafo_distinta, STATI_DISTINTA_RICHIEDIBILI
    )
    if not _transizione_verso_validata(transizioni_distinta, distinta.get("stato_codice")):
        distinta = {
            **distinta,
            "validazione_blocco_reason": None,
            "validazione_blocco_reason_key": None,
            "validazione_blocco_dettaglio": None,
            "can_validare": None,
        }
    scartate = [
        r for r in (distinta.get("righe_per_stato") or [])
        if r.get("stato_codice_interno") == STATO_RIGA_SCARTATA
    ]
    return {
        "distinta": {
            **distinta,
            "righe_scartate": sum(int(r.get("righe") or 0) for r in scartate),
            # ⚠️ Parte da `Decimal("0")`, non dallo `0` di `sum`: un importo che
            #    esce come numero JSON senza scartate e come stringa (`"5.00"`,
            #    la forma di ogni Decimal) con una sola cambierebbe TIPO coi
            #    dati — `totale_righe` accanto e' sempre una stringa.
            "totale_scartate": sum(
                (Decimal(str(r.get("importo") or 0)) for r in scartate), Decimal("0")
            ),
            # ⭐ D17/D18: il CONTENUTO (righe nuove, fatti, eliminazioni) si
            #    lavora solo su una manuale in bozza. Il flag viaggia perche'
            #    il frontend non ricalcoli la regola: e' una copia dichiarata
            #    (vedi `STATO_RIGA_SENZA_DESTINAZIONE`), e il rifiuto vero
            #    resta quello del database. ⚠️ Le DECISIONI (abbinare,
            #    sospendere, cambiare stato) non passano di qui: sotto una
            #    validata si abbina, non si digita.
            "contenuto_modificabile": (
                distinta.get("stato_codice") == STATO_DISTINTA_INIZIALE
                and distinta.get("origine") == ORIGINE_MANUALE
            ),
        },
        "stati_distinta": repository.list_stati_distinta(),
        "stati_riga": repository.list_stati_riga(),
        # ⭐ Le transizioni sono DUE mappe, e servono entrambe: il drawer disegna
        # il percorso della testata e quello della riga nella stessa
        # schermata. ⛔ Fino al 14/09 viaggiava il solo vocabolario
        # (`stati_richiedibili`), e il frontend toglieva lo stato corrente:
        # cio' che offriva coincideva con la matrice sulla testata PER CASO e
        # non coincideva sulla riga. Adesso non puo' divergere: si legge.
        "transizioni": {
            "distinta": transizioni_distinta,
            "riga": _transizioni_richiedibili(grafo_riga, STATI_RIGA_RICHIEDIBILI),
        },
    }


# Scopo: «dallo stato corrente si puo' chiedere VALIDATA?» — letto dalla
#        matrice ristretta ai richiedibili, la stessa che il frontend riceve.
# ⚠️ Serve al solo cancello della terna del verbo «valida»: il frontend
#    riconosce il pulsante dal flag `is_registrabile` del catalogo, e qui non
#    si offre ne' si toglie nessuna transizione.
def _transizione_verso_validata(
    transizioni: dict[str, list[str]], stato_codice: str | None
) -> bool:
    if stato_codice is None:
        return False
    return STATO_DISTINTA_VALIDATA in transizioni.get(stato_codice, [])


# ══════════════════════════════════════════════════════════════════
#  Distinte — scrittura
# ══════════════════════════════════════════════════════════════════

# Scopo: Apre la distinta manuale di lavoro dell'operatore.
# ⭐ E' un *get or create*: se l'operatore riapre con gli stessi dati (stessa
#    giornata, stesso canale, stessa persona) il database NON ne crea una
#    seconda — gli ridà la sua. E' cio' che rende inutile qualunque lock.
# ⚠️ Da cui `gia_popolata` nella risposta: dice che la distinta restituita ha
#    gia' delle righe, e serve al frontend per annunciarlo. ⛔ NON significa
#    «riaperta»: una distinta esistente e vuota e' indistinguibile da una
#    appena creata, e il caso e' innocuo.
def crea_distinta(payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload,
        allowed=frozenset(
            {"centro_riscossione_id", "data_contabile", "ente_incasso_id",
             "emittente_fiscale_id", "importo_dichiarato", "meta"}
        ),
    )
    centro_riscossione_id = _PAYLOAD.require_positive_int(
        payload,
        "centro_riscossione_id",
        message="Il centro di riscossione e' obbligatorio per aprire una distinta.",
    )
    data_contabile = _PAYLOAD.require_date(
        payload,
        "data_contabile",
        message="La data contabile e' obbligatoria per aprire una distinta.",
    )
    ente_incasso_id = _PAYLOAD.optional_positive_int(payload, "ente_incasso_id")
    # ⭐ L'EMITTENTE E' FACOLTATIVO QUI, E OBBLIGATORIO A DATABASE (D4, brief
    #    distinta-numerata-sul-registro, 2026-09-17). Il backend lo TRASPORTA e
    #    non lo deduce: se manca, lo risolve `fn_get_emittente_distinta` dal
    #    canale o dall'operatore in sessione — la stessa `fn_resolve_emittente_
    #    for_user` che legge l'emittente attivo scelto in topbar. E se non lo
    #    trova rifiuta con `E_CONTABILE_EMITTENTE_OBBLIGATORIO` (400, campo
    #    `emittente_fiscale_id`): e' il super admin in «tutti gli emittenti» su
    #    CASSA, che deve scegliere. ⛔ Un default dal profilo scritto qui
    #    sarebbe un secondo risolutore, e attribuirebbe denaro a un emittente
    #    che nessuno ha scelto.
    emittente_fiscale_id = _PAYLOAD.optional_positive_int(payload, "emittente_fiscale_id")
    importo_dichiarato = _PAYLOAD.optional_decimal(payload, "importo_dichiarato")

    repository = PagamentiRepository()
    # 🔴 DUE scritture, e devono essere UNA unita'. Il totale dichiarato non e'
    # un parametro della funzione madre, quindi si scrive subito dopo — ma una
    # distinta che nascesse SENZA il suo dichiarato sarebbe una distinta la cui
    # quadratura non scatta mai: il controllo esisterebbe e non direbbe niente,
    # che e' il modo peggiore in cui puo' mancare.
    # ⚠️ `ATOMIC_REQUESTS` non e' attivo in questo progetto: senza questo blocco
    # le due scritture sarebbero due transazioni separate.
    with transaction.atomic(), _db_errors("crea_distinta"):
        contabile_id = repository.get_or_create_distinta(
            centro_riscossione_id=centro_riscossione_id,
            data_contabile=data_contabile,
            ente_incasso_id=ente_incasso_id,
            emittente_fiscale_id=emittente_fiscale_id,
            origine=ORIGINE_MANUALE,
            codice_stato_interno=STATO_DISTINTA_INIZIALE,
            meta=_meta_json(payload),
        )
        if importo_dichiarato is not None:
            repository.update_distinta(
                contabile_id, {"importo_dichiarato": importo_dichiarato}
            )

    dettaglio = get_distinta(contabile_id)
    dettaglio["gia_popolata"] = bool(dettaglio["distinta"]["righe_totali"])
    return dettaglio


# Scopo: Aggiorna i campi compilabili della testata.
def aggiorna_distinta(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)

    campi = _campi_presenti(
        payload,
        _CAMPI_DISTINTA_PATCH,
        lettori={
            "data_contabile": lambda p: _PAYLOAD.require_date(p, "data_contabile"),
            "ente_incasso_id": lambda p: _PAYLOAD.optional_positive_int(
                p, "ente_incasso_id"
            ),
            "importo_dichiarato": lambda p: _PAYLOAD.optional_decimal(
                p, "importo_dichiarato"
            ),
            "meta": lambda p: _meta_json(p),
        },
    )
    # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    _PAYLOAD.require_campi_da_aggiornare(campi)
    with _db_errors("aggiorna_distinta"):
        repository.update_distinta(contabile_id, campi)
    return get_distinta(contabile_id)


# Scopo: Chiede un cambio di stato sulla testata.
# ⚠️ Il backend verifica solo che lo stato chiesto sia uno di quelli che una
#    PERSONA puo' chiedere. Se il passaggio sia ammesso da dove la distinta si
#    trova adesso lo dice la matrice delle transizioni, e le altre tre
#    condizioni (quadratura col dichiarato, riapertura solo se manuale,
#    chiusura con righe ancora pronte) le dicono i loro guard: ⛔ riscriverle
#    qui vorrebbe dire tenerle allineate a mano per sempre.
def cambia_stato_distinta(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset({"nuovo_stato"}))
    nuovo_stato = _PAYLOAD.require_string(payload, "nuovo_stato").upper()
    ErrorManager.require(
        nuovo_stato in STATI_DISTINTA_RICHIEDIBILI,
        code=E_VALIDAZIONE,
        message="Stato non richiedibile su una distinta contabile.",
        detail=(
            f"Ammessi: {', '.join(STATI_DISTINTA_RICHIEDIBILI)}. "
            "CHIUSA non si chiede: la scrive la registrazione."
        ),
        context={"field": "nuovo_stato", "nuovo_stato": nuovo_stato},
        function_name=f"{_FN}.cambia_stato_distinta",
    )

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    with _db_errors("cambia_stato_distinta"):
        toccate = repository.set_stato_distinta(contabile_id, nuovo_stato)
    # 🔴 Zero righe toccate NON e' un successo silenzioso: la distinta esiste
    # (l'abbiamo appena letta), quindi a non risolvere e' il CODICE DI STATO.
    # Senza questo controllo la risposta sarebbe un 200 con lo stato invariato
    # — l'operatore vedrebbe «fatto» su un gesto che non e' avvenuto.
    ErrorManager.require(
        toccate > 0,
        code=E_STATO_NON_CONFIGURATO,
        message="Stato distinta contabile non configurato.",
        detail=f"codice_interno={nuovo_stato} assente o non attivo a catalogo.",
        function_name=f"{_FN}.cambia_stato_distinta",
    )
    return get_distinta(contabile_id)


# ══════════════════════════════════════════════════════════════════
#  Righe
# ══════════════════════════════════════════════════════════════════

# Scopo: Le righe di una distinta, PAGINATE — la lista `pagamenti.distinta_righe`.
# ⭐ Offset-based (`limit`/`offset`, la lingua di `useSearchTable`) e risposta
#    `{count, results}`, come le due sorelle nate su `<ListaConfigurabile>`
#    (`fatture/{id}/sistemazioni/`, `rate/`). ⛔ Fino al 2026-09-18 rispondeva
#    `{"count": len(righe), ...}`: un'eco, non un conteggio (api.md §«Il `count`
#    non si deriva MAI dalle righe»). Ora il totale viene da `COUNT(*) OVER ()`.
# ⭐ `nullable=True`: «non specificato» e' legittimo e l'ordine lo decide il
#    repository (`id DESC`); fuori whitelist e' un 400 col campo, non un 500.
# ⭐ `scartate` (BE-2, D20-c): le SCARTATA — «non e' nostra» — sono FUORI di
#    default, e la risposta dice quante ne sta nascondendo (`scartate_count`,
#    la forma di `archiviate_count`): spento e senza numero, «elenco pulito» e
#    «tre righe messe via» si leggerebbero uguali. A interruttore acceso non
#    c'e' niente di nascosto e il conteggio non si paga. L'export segue la
#    lista a video, interruttore compreso.
def list_righe(
    contabile_id: int,
    *,
    limit: int,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
    scartate: bool = False,
    search: str | None = None,
) -> dict[str, Any]:
    order_by, order_dir = validate_order_params(
        order_by, order_dir,
        allowed_columns=DISTINTA_RIGHE_SORT_COLUMNS,
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_righe",
        nullable=True,
    )
    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    results, total = repository.list_righe_distinta(
        contabile_id,
        escludi_stato_codice=None if scartate else STATO_RIGA_SCARTATA,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    scartate_count = 0 if scartate else repository.count_righe_in_stato(
        contabile_id, STATO_RIGA_SCARTATA
    )
    return {"count": total, "results": results, "scartate_count": scartate_count}


# Scopo: Aggiunge una riga alla distinta — un importo arrivato, e di chi e'.
# ⭐ D16 (2026-09-14): la riga MANUALE nasce con la destinazione. Con
#    `fattura_id` nasce `ABBINATA` — fattura, cliente, rata facoltativa e la
#    forzatura viaggiano nello STESSO `INSERT` dei fatti, atomico per
#    costruzione. Senza, nasce `DA_ABBINARE`: e' l'eccezione che l'operatore
#    dichiara («non ho trovato il documento»), e si recupera dalla coda.
# ⛔ Non due scritture (`create` + `abbina`): i guard di riga — dati richiesti
#    dallo stato, coerenza rata/fattura, capienza, perimetro emittente — sono
#    `BEFORE INSERT OR UPDATE`, e sull'INSERT fanno esattamente cio' che fanno
#    sull'UPDATE. Il doppio tempo della capienza (D14-d) vale anche qui, e il
#    backend NON lo interpreta: primo tentativo senza `forzata`, 409
#    confermabile, secondo con `forzata = true` che resta scritto sulla riga.
# ⚠️ `billing_account_id` assente ⇒ e' quello della fattura (letto, non
#    dedotto): il guard lo pretende comunque su `ABBINATA`.
def crea_riga(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    # I FATTI sono gli stessi del PATCH (una lista sola, non una ricopiata),
    # piu' la destinazione che alla nascita viaggia con loro.
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({*_CAMPI_RIGA_PATCH, *_CAMPI_DESTINAZIONE})
    )
    importo = _PAYLOAD.require_decimal(payload, "importo")
    destinazione = _destinazione_da_payload(
        payload, obbligatoria=False, function_name=f"{_FN}.crea_riga"
    )

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    fattura_id = destinazione["fattura_id"]
    if fattura_id is not None and destinazione["billing_account_id"] is None:
        destinazione["billing_account_id"] = _billing_account_della_fattura(
            repository, fattura_id, function_name=f"{_FN}.crea_riga"
        )
    # Lo stato lo decide la presenza della destinazione, non un parametro: una
    # riga che sa a chi appartiene nasce abbinata, una che non lo sa nasce da
    # abbinare. Non c'e' un terzo caso da chiedere all'operatore.
    stato_iniziale = (
        STATO_RIGA_ABBINATA if fattura_id is not None else STATO_RIGA_SENZA_DESTINAZIONE
    )
    with _db_errors("crea_riga"):
        riga_id = repository.create_riga(
            contabile_id=contabile_id,
            importo=importo,
            codice_stato_interno=stato_iniziale,
            riferimento_ente=_PAYLOAD.optional_string(payload, "riferimento_ente"),
            data_pagamento=_PAYLOAD.optional_date(payload, "data_pagamento"),
            data_valuta=_PAYLOAD.optional_date(payload, "data_valuta"),
            data_operazione=_PAYLOAD.optional_date(payload, "data_operazione"),
            motivo_sospeso=_PAYLOAD.optional_string(payload, "motivo_sospeso"),
            meta=_meta_json(payload),
            **destinazione,
        )
    return {"riga": _riga_o_404(repository, riga_id)}


# I FATTI COMUNI di «righe da rate»: valgono per tutte le righe del giro. Sono i
# fatti della riga MENO l'importo, che e' per rata, e meno `motivo_sospeso`, che
# non ha senso su una riga che nasce ABBINATA.
_CAMPI_DA_RATE_COMUNI: tuple[str, ...] = (
    "riferimento_ente",
    "data_pagamento",
    "data_valuta",
    "data_operazione",
    "meta",
)


# Scopo: Legge i fatti comuni UNA volta, PRIMA del giro, con gli stessi lettori
#        che `crea_riga` usa per riga — e li restituisce gia' letti, cosi' che
#        per riga non ci sia piu' niente da rifiutare su di loro.
# 🔴 Senza questa lettura una data malformata — un fatto della RICHIESTA, non
#    di una rata — veniva rifiutata dentro il savepoint di OGNI riga: la
#    risposta era un 200 con esito `ERRORE` e N fallite identiche, e il
#    frontend avrebbe mostrato la stessa frase su ogni rata dell'area senza
#    accendere il campo in testa. Un fatto comune sbagliato e' un 400 col
#    campo, come su `POST righe/`.
# ⚠️ Non e' una seconda regola: i lettori sono quelli di `_PAYLOAD`, e
#    `crea_riga` li riapplica a valori gia' letti (una `date` resta una
#    `date`, un `dict` resta un `dict`) — stesso esito, nessun secondo parere.
def _fatti_comuni_da_rate(payload: dict[str, Any], *, function_name: str) -> dict[str, Any]:
    comuni: dict[str, Any] = {}
    for chiave in _CAMPI_DA_RATE_COMUNI:
        if chiave not in payload:
            continue
        if chiave == "meta":
            comuni[chiave] = _PAYLOAD.optional_meta(payload, chiave, function_name=function_name)
        elif chiave.startswith("data_"):
            comuni[chiave] = _PAYLOAD.optional_date(payload, chiave, function_name=function_name)
        else:
            comuni[chiave] = _PAYLOAD.optional_string(payload, chiave, function_name=function_name)
    return comuni
# Per riga: la rata, il suo importo e il secondo tempo.
_CAMPI_DA_RATE_RIGA: tuple[str, ...] = ("scadenza_id", "importo", *_CAMPI_FORZATURA)
# Il tetto delle rate in un giro. ⭐ Lo stesso 200 dei verbi di massa delle code
#    (`archivia/`): un elenco piu' lungo e' un import, non un gesto.
MAX_RIGHE_DA_RATE = 200


# Scopo: Legge l'elenco delle rate scelte, con la regola che un elenco spedito
#        da un picker rispetta per costruzione — e che, se non rispetta, e' un
#        difetto del client da dire, non da aggiustare.
# ⛔ `scadenza_id` DUPLICATO = 400 col campo: deduplicare in silenzio butterebbe
#    via un importo, e non c'e' modo di sapere quale dei due voleva l'operatore.
# ⚠️ Elenco VUOTO = 400: «zero righe da rate» non e' un giro a esito
#    COMPLETATO, e' un payload che non chiede niente.
def _righe_da_rate_da_payload(payload: dict[str, Any], *, function_name: str) -> list[dict[str, Any]]:
    righe = payload.get("righe")
    ErrorManager.require(
        isinstance(righe, list) and len(righe) > 0,
        code=E_VALIDAZIONE,
        message="Indicare almeno una rata.",
        context={"field": "righe"},
        function_name=function_name,
    )
    assert isinstance(righe, list)
    ErrorManager.require(
        len(righe) <= MAX_RIGHE_DA_RATE,
        code=E_VALIDAZIONE,
        message=f"Al massimo {MAX_RIGHE_DA_RATE} rate per giro.",
        detail=f"ricevute {len(righe)}",
        context={"field": "righe"},
        function_name=function_name,
    )
    letti: list[dict[str, Any]] = []
    visti: set[int] = set()
    for indice, riga in enumerate(righe):
        ErrorManager.require(
            isinstance(riga, dict),
            code=E_VALIDAZIONE,
            message="Ogni riga deve indicare la rata e l'importo.",
            detail=f"righe[{indice}] non e' un oggetto",
            context={"field": "righe"},
            function_name=function_name,
        )
        assert isinstance(riga, dict)
        _PAYLOAD.validate_allowed_keys(riga, allowed=frozenset(_CAMPI_DA_RATE_RIGA))
        scadenza_id = _PAYLOAD.require_positive_int(
            riga, "scadenza_id", message="La rata e' obbligatoria su ogni riga."
        )
        assert scadenza_id is not None
        ErrorManager.require(
            scadenza_id not in visti,
            code=E_VALIDAZIONE,
            message="La stessa rata compare due volte nell'elenco.",
            detail=f"scadenza_id={scadenza_id} (righe[{indice}])",
            context={"field": "righe", "scadenza_id": scadenza_id},
            function_name=function_name,
        )
        visti.add(scadenza_id)
        importo = _PAYLOAD.require_decimal(riga, "importo")
        forzata = _PAYLOAD.optional_bool(riga, "forzata") or False
        motivo_forzatura = _PAYLOAD.optional_string(riga, "motivo_forzatura")
        _guard_motivo_con_forzatura(forzata, motivo_forzatura, function_name=function_name)
        letti.append({
            "scadenza_id": scadenza_id,
            "importo": importo,
            "forzata": forzata,
            "motivo_forzatura": motivo_forzatura,
        })
    return letti


# Scopo: N RATE → N RIGHE in un Salva (D19-d, 2026-09-17): le rate scelte nel
#        picker diventano righe della distinta, ognuna con la propria
#        destinazione — e' D1 reso a video (*«un incasso che copre tre rate
#        resta tre righe»*).
# ⭐ NESSUNA SECONDA STRADA DI INSERIMENTO: per ogni rata si risolve la
#    fattura (sotto RLS) e si chiama `crea_riga` cosi' com'e' — BA dalla
#    fattura, stato `ABBINATA`, i guard del database di coerenza rata/fattura e
#    di capienza sull'`INSERT`. Il backend non decide niente in piu' di quello
#    che decide per una riga sola.
# ⭐ ESITO PARZIALE PER RIGA (`run_fan_out`, un savepoint per riga): le riuscite
#    ENTRANO, le rifiutate tornano al chiamante col loro errore INTERO —
#    `ErrorTranslator.to_api_error`, la sede unica delle politiche
#    dell'envelope (hint tolto sui tecnici, bersaglio solo dove c'e' un gesto).
#    Cosi' la capienza di una rata che non regge risale con
#    `ui_action = confirm_and_retry` PER QUELLA RIGA, e il secondo tempo e'
#    per riga: venti righe buone non si perdono per una.
# ⚠️ Lo status HTTP e' 200 anche su `PARZIALE`/`ERRORE`: chi legge guarda
#    `esito` e `falliti[]`, come per l'archiviazione delle code.
# ⚠️ L'idempotenza copre il GIRO (la chiave e' della richiesta): il secondo
#    tempo e' un giro NUOVO con le sole righe rimaste, e ha una chiave nuova.
def crea_righe_da_rate(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    fn = f"{_FN}.crea_righe_da_rate"
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({*_CAMPI_DA_RATE_COMUNI, "righe"})
    )
    righe = _righe_da_rate_da_payload(payload, function_name=fn)
    # I fatti comuni si leggono UNA volta, qui — un 400 col campo se sono
    # sbagliati — e viaggiano gia' letti su ogni riga.
    comuni = _fatti_comuni_da_rate(payload, function_name=fn)

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)

    # Scopo: UNA riga: risolve la fattura dalla rata e chiama la nascita. Solleva
    #        su rifiuto — e' cosi' che il fan-out distingue riuscite e fallite,
    #        e l'eccezione la tiene il BB (`FanOutItemErrore.eccezione`).
    def _process(voce: tuple[int, dict[str, Any]]) -> dict[str, Any]:
        indice, riga = voce
        fattura_id = repository.get_fattura_id_di_rata(riga["scadenza_id"])
        ErrorManager.require(
            fattura_id is not None,
            code=E_RATA_NON_TROVATA,
            message="Rata non trovata.",
            detail=f"scadenza_id={riga['scadenza_id']}",
            context={"field": "scadenza_id"},
            function_name=fn,
        )
        esito_riga = crea_riga(
            contabile_id,
            {
                **comuni,
                "importo": str(riga["importo"]),
                "fattura_id": fattura_id,
                "scadenza_id": riga["scadenza_id"],
                "forzata": riga["forzata"],
                **(
                    {"motivo_forzatura": riga["motivo_forzatura"]}
                    if riga["motivo_forzatura"] is not None else {}
                ),
            },
        )
        return {"indice": indice, "scadenza_id": riga["scadenza_id"], "riga": esito_riga["riga"]}

    esito = run_fan_out(list(enumerate(righe)), _process)
    return {
        "esito": esito.esito,
        "richieste": esito.totale,
        "riuscite": esito.ok,
        "creati": esito.risultati,
        "falliti": [
            {
                "indice": e.indice,
                "scadenza_id": righe[e.indice]["scadenza_id"],
                # ⭐ L'errore INTERO, nella forma dell'envelope e con le sue
                #    politiche — non un `code` + `message` a mano: il frontend
                #    ramifica su `ui_action` e mostra `hint`, come su un rifiuto
                #    arrivato da solo. L'eccezione la porta il BB, anche quando
                #    nasce FUORI da `_process` (il savepoint stesso): li' e' un
                #    GUASTO e `to_api_error` lo rende come errore tecnico
                #    (messaggio della policy, niente `hint` grezzo).
                "errore": ErrorTranslator.to_api_error(e.eccezione).to_dict(),
            }
            for e in esito.errori
        ],
    }


# Scopo: Elimina una riga di una distinta MANUALE in BOZZA — `attivo = false`.
# ⭐ D17 (2026-09-14): una riga digitata male su una bozza non e' un fatto — non
#    e' denaro arrivato, e' un errore di battitura — e si toglie. «Scarta» dice
#    un'altra cosa (denaro arrivato, non nostro) e CONTA nella quadratura: con
#    un totale dichiarato, scartare la riga sbagliata non ha via d'uscita.
# ⛔ Nessuna copia del predicato in Python: i motivi li da' il database
#    (`script.fn_check_riga_contabile_eliminabile`, i cui motivi sono quelli
#    di `_su_distinta` che alimenta il cestino spento in lista) e il guard
#    rifiuta con `E_RIGA_CONTABILE_DISTINTA_*` (409), tradotto come ogni altro.
# ⚠️ Una riga eliminata non e' piu' raggiungibile da nessun verbo: `get_riga`
#    filtra `attivo`, quindi un secondo DELETE — come un PATCH o un abbina —
#    risponde «non trovata», che e' la stessa risposta di «non la vedi». Il
#    doppio invio lo copre l'`Idempotency-Key`, non un ramo «gia' eliminata».
def elimina_riga(riga_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    with _db_errors("elimina_riga"):
        toccate = repository.disattiva_riga(riga_id)
    # La riga c'era un istante fa (l'abbiamo letta ATTIVA): zero righe toccate
    # vuol dire che qualcun altro l'ha eliminata nel frattempo. Per chi chiede
    # e' la stessa cosa di «non c'e'», ed e' quello che si risponde.
    ErrorManager.require(
        toccate > 0,
        code=E_RIGA_NON_TROVATA,
        message="Riga contabile non trovata.",
        detail=f"riga_id={riga_id}",
        function_name=f"{_FN}.elimina_riga",
    )
    return {"riga_id": int(riga_id), "eliminata": True}


# Scopo: Aggiorna i FATTI di una riga — e, se serve, il SECONDO TEMPO.
# ⛔ Non l'abbinamento: quello e' un verbo, perche' porta con se' la rata, e
#    perche' un abbinamento e' una decisione — non la correzione di un dato che
#    era stato digitato male (R-6).
# ⭐ `forzata` + `motivo_forzatura` SI' (decisione di Tid, 2026-09-15 — Q-H):
#    correggere un importo puo' incontrare il guard della rata esattamente
#    come inserirlo, e il rifiuto arriva «confermabile». Senza questa porta il
#    verbo riceveva una domanda a cui non sapeva rispondere, e il rimedio era
#    eliminare la riga e ricrearla. Stessa regola della nascita: il motivo solo
#    con la forzatura, e il backend NON decide che cosa sia forzabile.
def aggiorna_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)

    campi = _campi_presenti(
        payload,
        (*_CAMPI_RIGA_PATCH, *_CAMPI_FORZATURA),
        lettori={
            "importo": lambda p: _PAYLOAD.require_decimal(p, "importo"),
            "riferimento_ente": lambda p: _PAYLOAD.optional_string(
                p, "riferimento_ente"
            ),
            "data_pagamento": lambda p: _PAYLOAD.optional_date(p, "data_pagamento"),
            "data_valuta": lambda p: _PAYLOAD.optional_date(p, "data_valuta"),
            "data_operazione": lambda p: _PAYLOAD.optional_date(p, "data_operazione"),
            "motivo_sospeso": lambda p: _PAYLOAD.optional_string(p, "motivo_sospeso"),
            "meta": lambda p: _meta_json(p),
            # `null` su una colonna NOT NULL vale «torna al default»: falso.
            "forzata": lambda p: _PAYLOAD.optional_bool(p, "forzata") or False,
            "motivo_forzatura": lambda p: _PAYLOAD.optional_string(
                p, "motivo_forzatura"
            ),
        },
    )
    # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    _PAYLOAD.require_campi_da_aggiornare(campi)
    _guard_motivo_con_forzatura(
        campi.get("forzata", False),
        campi.get("motivo_forzatura"),
        function_name=f"{_FN}.aggiorna_riga",
    )
    with _db_errors("aggiorna_riga"):
        repository.update_riga(riga_id, campi)
    return {"riga": _riga_o_404(repository, riga_id)}


# Scopo: Chiede un cambio di stato su una riga.
# ⚠️ Come sulla testata: il backend guarda solo il vocabolario, i guard fanno
#    il resto — compreso rifiutare `ABBINATA` su una riga che non dice a quale
#    fattura e a quale cliente appartiene.
def cambia_stato_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({"nuovo_stato", "motivo_sospeso"})
    )
    nuovo_stato = _PAYLOAD.require_string(payload, "nuovo_stato").upper()
    ErrorManager.require(
        nuovo_stato in STATI_RIGA_RICHIEDIBILI,
        code=E_VALIDAZIONE,
        message="Stato non richiedibile su una riga contabile.",
        detail=(
            f"Ammessi: {', '.join(STATI_RIGA_RICHIEDIBILI)}. "
            "POSTATA non si chiede: la scrive la registrazione."
        ),
        context={"field": "nuovo_stato", "nuovo_stato": nuovo_stato},
        function_name=f"{_FN}.cambia_stato_riga",
    )
    motivo_sospeso = _PAYLOAD.optional_string(payload, "motivo_sospeso")

    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    # ⛔ Un `atomic` suo (2026-10-24): motivo e stato sono due UPDATE, e senza
    #    il motivo restava scritto anche quando lo stato veniva rifiutato. Il
    #    brief-be-verifica-documentazione-api §I.7.2 contava sull'`atomic`
    #    esterno di `handle_post_json`, che pero' c'e' solo in modalita' forte.
    with transaction.atomic():
        with _db_errors("cambia_stato_riga"):
            # Il motivo accompagna la sospensione nello stesso giro: sospendere
            # senza dire perche' lascia la riga in una coda dove il prossimo che
            # la guarda non sa che cosa si era gia' capito.
            if motivo_sospeso is not None:
                repository.update_riga(riga_id, {"motivo_sospeso": motivo_sospeso})
            toccate = repository.set_stato_riga(riga_id, nuovo_stato)
        # Stessa ragione della testata: la riga esiste, quindi a non risolvere e'
        # il codice di stato — e un 200 sopra un gesto non avvenuto e' peggio di
        # un errore. Dentro l'`atomic`: il rifiuto si porta via anche il motivo.
        ErrorManager.require(
            toccate > 0,
            code=E_STATO_NON_CONFIGURATO,
            message="Stato riga contabile non configurato.",
            detail=f"codice_interno={nuovo_stato} assente o non attivo a catalogo.",
            function_name=f"{_FN}.cambia_stato_riga",
        )
    return {"riga": _riga_o_404(repository, riga_id)}


# ══════════════════════════════════════════════════════════════════
#  L'abbinamento — il verbo che porta il denaro alla rata
# ══════════════════════════════════════════════════════════════════

# Scopo: Imputa una riga a una fattura, e quando c'e' a una rata.
# ⭐ E' un VERBO e non un PATCH, per due ragioni: porta con se' la rata e la
#    forzatura, ed e' una DECISIONE — non la correzione di un dato che era
#    stato digitato male.
# ⚠️ La rata resta FACOLTATIVA anche su una riga abbinata: la riga del fondo
#    fattura ha fattura si' e rata no, ed e' un caso normale.
# 🔴 Il doppio tempo della capienza (D14-d) passa di qui e il backend NON lo
#    interpreta: il primo tentativo arriva senza `forzata`, il guard del
#    database rifiuta con la ragione e i numeri, e la conferma dell'operatore
#    torna con `forzata = true`. ⛔ Il backend non decide che cosa sia
#    forzabile — se lo facesse, sarebbe una seconda sede della regola.
def abbina_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset(_CAMPI_DESTINAZIONE))
    destinazione = _destinazione_da_payload(
        payload, obbligatoria=True, function_name=f"{_FN}.abbina_riga"
    )
    fattura_id = destinazione["fattura_id"]
    assert fattura_id is not None

    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    # Il cliente, se non lo dice chi chiama, e' quello della fattura — come
    # alla nascita della riga: stessa regola, stessa lettura.
    if destinazione["billing_account_id"] is None:
        destinazione["billing_account_id"] = _billing_account_della_fattura(
            repository, fattura_id, function_name=f"{_FN}.abbina_riga"
        )
    with _db_errors("abbina_riga"):
        toccate = repository.abbina_riga(
            riga_id=riga_id,
            codice_stato_interno=STATO_RIGA_ABBINATA,
            **destinazione,
        )
    ErrorManager.require(
        toccate > 0,
        code=E_STATO_NON_CONFIGURATO,
        message="Stato riga contabile non configurato.",
        detail=f"codice_interno={STATO_RIGA_ABBINATA} assente o non attivo.",
        function_name=f"{_FN}.abbina_riga",
    )
    return {"riga": _riga_o_404(repository, riga_id)}


# Scopo: La registrazione TARDIVA (D20-b): una riga `SOSPESA` sotto una
#        distinta gia' registrata si abbina E si registra nello stesso gesto.
# ⭐ Il payload e' quello di `abbina` (`_CAMPI_DESTINAZIONE`), letto dalla
#    stessa funzione e con le stesse regole — il cliente, se manca, e' quello
#    della fattura. E' un verbo suo e non un `abbina` + `stato`: sotto una
#    CHIUSA il secondo verrebbe rifiutato dalla quarta mossa, e il primo
#    resterebbe scritto. La madre passa da ABBINATA (girano tutti i guard
#    dell'abbinamento) e alla quarta mossa si presenta con la GUC.
# 🔴 Il doppio tempo della capienza passa INTATTO: primo tentativo senza
#    `forzata`, 409 `confirm_and_retry`, secondo con `forzata = true`. Il
#    backend non decide che cosa sia forzabile.
# ⛔ Nessuna verifica di stato qui («e' SOSPESA?», «la distinta e' registrata?»):
#    sono i guard della madre (`E_RIGA_CONTABILE_TARDIVA_*`), e riscriverli
#    sarebbe la seconda sede. Il 404 di dominio PRIMA della madre, come per
#    tutti i verbi: «non esiste» e «non la vedi» restano indistinguibili.
def registra_riga_tardiva(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset(_CAMPI_DESTINAZIONE))
    destinazione = _destinazione_da_payload(
        payload, obbligatoria=True, function_name=f"{_FN}.registra_riga_tardiva"
    )
    fattura_id = destinazione["fattura_id"]
    assert fattura_id is not None

    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    if destinazione["billing_account_id"] is None:
        destinazione["billing_account_id"] = _billing_account_della_fattura(
            repository, fattura_id, function_name=f"{_FN}.registra_riga_tardiva"
        )
    with _db_errors("registra_riga_tardiva"):
        ricevuta: RicevutaTardiva = repository.posta_riga_tardiva(
            riga_id=riga_id, **destinazione
        )
    # La riga com'e' adesso — POSTATA, col movimento scritto — accanto alla
    # ricevuta: chi ha premuto vede il fatto, non solo un id.
    return {**ricevuta, "riga": _riga_o_404(repository, riga_id)}


# ══════════════════════════════════════════════════════════════════
#  Le due code, e l'elenco che rende onesta la forzatura
# ══════════════════════════════════════════════════════════════════

# Scopo: La coda del riconciliatore: le righe di TUTTE le distinte in uno degli
#        stati chiesti.
# ⭐ `coda` sceglie il mestiere, non lo stato: chi entra da «Da abbinare» vede
#    solo quelle, chi entra da «Sospese» solo le sue — ma la definizione a
#    catalogo e' una sola.
def list_coda_righe(
    *,
    coda: str | None = None,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    chiave = (coda or "TUTTE").upper()
    ErrorManager.require(
        chiave in CODE_RIGHE,
        code=E_VALIDAZIONE,
        message="Coda non riconosciuta.",
        detail=f"Ammesse: {', '.join(CODE_RIGHE)}.",
        context={"parametro": "coda", "coda": chiave},
        function_name=f"{_FN}.list_coda_righe",
    )
    order_by, order_dir = validate_order_params(
        order_by or "data_pagamento",
        order_dir or "desc",
        allowed_columns=frozenset(RIGHE_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_coda_righe",
    )

    repository = PagamentiRepository()
    results, total = repository.list_righe_coda(
        stati=CODE_RIGHE[chiave],
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_a=data_a,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    # ⭐ Il catalogo degli stati di riga e le uscite richiedibili DA OGNI STATO
    #    viaggiano ACCANTO alle righe (FE-4, D20): dalla coda si lavora — abbina,
    #    sospendi, scarta, riporta — e le voci del kebab si costruiscono dalla
    #    MATRICE, come nel drawer. ⛔ Non un elenco cablato nel frontend, e non
    #    un endpoint suo: pulsanti e righe vengono dalla stessa lettura, quindi
    #    non possono raccontare due istanti diversi (la forma di `stati` sul
    #    registro lotti).
    _grafo_distinta, grafo_riga = repository.list_transizioni()
    return {
        **envelope_da_offset(results, total, limit=limit, offset=offset),
        "stati_riga": repository.list_stati_riga(),
        "transizioni_riga": _transizioni_richiedibili(grafo_riga, STATI_RIGA_RICHIEDIBILI),
    }


# Scopo: Le rate uscite dalla banda di capienza.
# 🔴 Senza questo elenco la forzatura sarebbe «un modo per nascondere, non per
#    registrare»: e' la ragione per cui la vista e il guard che permette di
#    forzare stanno nello stesso lotto.
def list_rate_fuori_capienza(
    *,
    motivo: str | None = None,
    billing_account_id: int | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    # Fail-fast sul vocabolario chiuso: un motivo inventato darebbe una lista
    # vuota, che su due soli valori possibili e' indistinguibile da «non c'e'
    # niente fuori capienza» — cioe' dalla risposta piu' rassicurante.
    ErrorManager.require(
        motivo is None or motivo in MOTIVI_FUORI_CAPIENZA,
        code=E_VALIDAZIONE,
        message="Motivo non riconosciuto.",
        detail=f"Ammessi: {', '.join(MOTIVI_FUORI_CAPIENZA)}.",
        context={"parametro": "motivo", "motivo": motivo},
        function_name=f"{_FN}.list_rate_fuori_capienza",
    )
    order_by, order_dir = validate_order_params(
        order_by or "data_scadenza",
        order_dir or "desc",
        allowed_columns=frozenset(RATE_FUORI_CAPIENZA_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_rate_fuori_capienza",
    )

    repository = PagamentiRepository()
    results, total = repository.list_rate_fuori_capienza(
        motivo=motivo,
        billing_account_id=billing_account_id,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return envelope_da_offset(results, total, limit=limit, offset=offset)


# ══════════════════════════════════════════════════════════════════
#  Registrazione (posting)
# ══════════════════════════════════════════════════════════════════

# Scopo: L'anteprima della registrazione — la fotografia di che cosa succede
#        se si preme adesso.
# ⭐ E' cio' che l'operatore vede PRIMA di premere, ed e' cio' che poi
#    DICHIARA: i due numeri di questa risposta sono quelli da rimandare
#    indietro nella registrazione.
def anteprima_registrazione(contabile_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    distinta = _distinta_o_404(repository, contabile_id)
    righe = repository.list_righe(contabile_id)
    # Le righe che restano indietro, con il loro stato: non un numero solo, ma
    # il motivo per cui non partono — «due righe non registrabili» senza dire
    # quali obbliga l'operatore a cercarle a mano.
    non_registrabili = [
        {
            "id": riga["id"],
            "importo": riga["importo"],
            "stato_codice": riga["stato_codice"],
            "stato_descrizione": riga["stato_descrizione"],
        }
        for riga in righe
        if not riga["stato_is_postabile"]
    ]
    return {
        "contabile_id": contabile_id,
        "stato_codice": distinta["stato_codice"],
        "righe_registrabili": distinta["righe_registrabili"],
        "totale_registrabile": distinta["totale_registrabile"],
        "righe_non_registrabili": non_registrabili,
        "importo_dichiarato": distinta["importo_dichiarato"],
        "scarto_dichiarato": distinta["scarto_dichiarato"],
    }


# Scopo: Registra la distinta — il gesto che trasforma il denaro dichiarato in
#        denaro registrato, e da cui i saldi smettono di mentire.
# ⭐ Una sola `SELECT` sulla funzione madre. ⛔ Nessun `transaction.atomic()`,
#    nessun ciclo, nessuna lettura-poi-scrittura.
# ⚠️ La dichiarazione (`righe_attese` + `totale_atteso`) e' facoltativa ma
#    LEGATA: o tutti e due o nessuno. Mezza dichiarazione non si puo'
#    verificare, e accettarla significherebbe registrare senza controllo
#    credendo di averlo fatto.
# ⛔ E l'esito risale INTATTO: `NULLA_DA_POSTARE` non e' un errore e non si
#    trasforma in uno. Se il backend lo facesse, il database scriverebbe nel
#    registro degli errori un errore che non e' un errore — ed e' la ragione
#    esatta per cui la funzione madre e' stata scritta cosi'.
def registra_distinta(contabile_id: int, payload: dict[str, Any]) -> RicevutaPosting:
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({"righe_attese", "totale_atteso"})
    )
    # ⚠️ NON `optional_positive_int`: **zero e' una dichiarazione legittima**.
    # L'anteprima puo' mostrare zero righe registrabili, e in quel caso la
    # coppia (0, 0) e' esattamente cio' che l'operatore ha davanti — il
    # database risponde `NULLA_DA_POSTARE`, che e' un esito e non un errore.
    # Rifiutarla qui avrebbe trasformato una risposta vera in un 400 con una
    # frase falsa («deve essere un intero positivo»).
    # ℹ️ Il tetto e' quello dello smallint: una distinta con piu' di 32.767
    #    righe non e' un caso reale, e se lo diventasse con l'import si allarga
    #    qui — un errore parlante, non un troncamento silenzioso.
    righe_attese = _PAYLOAD.optional_smallint(payload, "righe_attese", min_val=0)
    totale_atteso = _PAYLOAD.optional_decimal(payload, "totale_atteso")
    ErrorManager.require(
        (righe_attese is None) == (totale_atteso is None),
        code=E_VALIDAZIONE,
        message="La dichiarazione va passata intera: righe attese e totale atteso.",
        detail=(
            "Mezza dichiarazione non e' verificabile: o si passano entrambi i "
            "valori, o nessuno dei due."
        ),
        context={"field": "righe_attese"},
        function_name=f"{_FN}.registra_distinta",
    )

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    with _db_errors("registra_distinta"):
        return repository.posta_contabile(
            contabile_id=contabile_id,
            righe_attese=righe_attese,
            totale_atteso=totale_atteso,
        )


# Scopo: La CORREZIONE GUIDATA (Q-7) — da una distinta registrata nasce una
#        distinta nuova con le righe di segno opposto gia' compilate.
# ⭐ Il backend qui fa quasi niente, ed e' voluto: legge il payload e chiama la
#    madre. Le tre regole (si corregge solo il registrato, una correzione per
#    documento, le righe non postate si saltano e si contano) stanno tutte nella
#    funzione, che e' l'unica sede.
# ⛔ Non si chiama «storno»: `STORNATA` e' stata ritirata dal catalogo il 21/08.
# ⚠️ `NULLA_DA_CORREGGERE` NON e' un errore: si passa intatto, come
#    `NULLA_DA_POSTARE`. Chi legge decide la frase; qui non si interpreta.
def correggi_distinta(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({"data_contabile", "motivo"})
    )
    # ⚠️ Facoltativa: se non arriva, la madre usa l'oggi dell'azienda (`fn_data_operativa()`). Il default sta
    #    LA' e non qui — due default sulla stessa cosa divergono al primo cambio.
    data_contabile = _PAYLOAD.optional_date(payload, "data_contabile")
    motivo = _PAYLOAD.optional_string(payload, "motivo")

    repository = PagamentiRepository()
    # ⚠️ Il 404 di dominio PRIMA della madre: sotto RLS «non esiste» e «non la
    #    vedi» sono indistinguibili di proposito, e la madre risponderebbe con
    #    il proprio codice — ma il giro dei quattro gesti sulla distinta risponde
    #    gia' cosi', e due frasi diverse per lo stesso caso confondono.
    _distinta_o_404(repository, contabile_id)
    with _db_errors("correggi_distinta"):
        esito = repository.crea_distinta_correzione(
            contabile_id=contabile_id,
            data_contabile=data_contabile,
            motivo=motivo,
        )

    # ⭐ Sul nulla da correggere `contabile_id` e' NULL: non si legge nessun
    #    dettaglio, e la risposta dice l'esito e basta. Cercare una distinta che
    #    non e' stata creata sarebbe un 404 su un esito legittimo.
    # ⛔ `is None` e non un test di verita': e' la regola di tutto il cantiere —
    #    uno zero legittimo non deve leggersi come «assente». Qui un id a zero
    #    non esiste, ma la forma dev'essere la stessa ovunque: e' quando cambia
    #    da un punto all'altro che qualcuno la sbaglia dove conta.
    if esito.get("contabile_id") is None:
        return {"esito": esito, "distinta": None}
    return {
        "esito": esito,
        "distinta": _distinta_o_404(repository, int(esito["contabile_id"])),
    }
