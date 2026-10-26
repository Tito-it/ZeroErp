# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.offerte_commerciali + eccezioni +
#        utility 1:1 (CRUD iniziale, step DB 1-4 atterrati 2026-05-24).
#
#        L'offerta commerciale e' il documento pre-contrattuale: vive nel
#        ciclo BOZZA -> EMESSA -> (ACCETTATA | RIFIUTATA | SUPERATA) +
#        terminale di ritiro BOZZA | ACCETTATA -> ANNULLATA.
#        ⭐ Dal 2026-10-26 l'offerta e' sul modello del documento
#        (brief-modello-documento-vendita §13, giro 9): lo stato lo scrivono
#        solo i verbi DB `vendite.fn_cambia_stato_offerta` (con la
#        motivazione, obbligatoria dove la riga della matrice la chiede) e
#        `vendite.fn_annulla_offerta` (con la conferma dei legami: la
#        revisione precedente che torna emessa). Stati di partenza, permesso
#        del passaggio, motivazione e condizioni li giudica il DB; qui niente
#        copie Python della matrice.
#
#        Stato 2026-05-25: tutti gli step DB 1-9 atterrati. Il service
#        espone l'intero ciclo dell'offerta commerciale: create -> emetti ->
#        registra_esito -> push_a_contratto + revisione e annullamento.
#        Niente metodo "fuori scope" residuo.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.config.sorgenti import SORGENTE_OFFERTA_COMMERCIALE
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.documento_modello import stato_di_emissione
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.core.services.capability_blob import capabilities_o_vuoto
from apps.core.services.testata_guard import (
    pagina_dopo_testata,
    riga_del_padre_o_not_found,
    testata_o_not_found,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    translate_db_errors,
)
from apps.core.services.partitioned_note_service import contatori_documento
from apps.vendite.db.note_repositories import NOTE_REPO_OFFERTA
from apps.vendite.db._documento_eccezioni_repo import (
    list_erogazioni_riga,
    listino_versione_operativa,
)
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.offerte_repository import (
    _ORDER_COLS_OFFERTE,
    TESTATA_OFFERTE,
    OffertaRigheListaRepository,
    OfferteRepository,
)
from apps.vendite.services._cliente_coppia_documento import (
    coppia_cambiata,
    rifiuta_colonne_ferme,
    risolvi_cliente_coppia,
)
from apps.vendite.services._annullo_con_legami import (
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    delete_indirizzo_documento,
    list_indirizzi_documento,
    upsert_indirizzo_documento,
)
from apps.vendite.services._approvazioni_prezzo_constants import (
    META_SORGENTE_OFFERTA,
    STATO_APPROVAZIONE_PENDING,
)
from apps.vendite.services._componenti_service_helpers import (
    dati_patch_componente,
    normalize_componenti_overrides,
    resolve_emittente_sr_id_for_testata,
)
from apps.vendite.services._pricing_gate_helpers import (
    guard_uom_id_positive,
    resolve_or_check_override_prezzo,
    validate_componenti_overrides_authorization,
)
from apps.vendite.types import OffertaPushResult

logger = logging.getLogger(__name__)


# Codici errore applicativi (registrati in apps.core.services.error_policies).
# Riusiamo E_VENDITE_* per coerenza con preventivi/contratti; i codici DB
# specifici (E_OFFERTA_TRANSIZIONE_NON_AMMESSA, ecc.) emergono dal trigger
# guard e vengono mappati dal middleware API (P0001 -> 422 con codice
# applicativo passato dal RAISE EXCEPTION del DB).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
# Il rifiuto del verbo di stato quando la riga del passaggio chiede la
# motivazione e manca (O-3): il service lo riconosce per dire al client il
# campo della SUA richiesta (vedi `_db_errors`).
E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA = "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA"

# Il campo della richiesta che porta la motivazione (rifiuto e annullo).
_CAMPO_MOTIVAZIONE = "motivazione"


# Pattern per estrarre il codice errore applicativo dal MESSAGE dei trigger
# DB. Convenzione progetto: `RAISE EXCEPTION USING MESSAGE='E_OFFERTA_XXX'`.
# Il primo token con underscore in maiuscolo che inizia per E_ e' il codice.


# Codici stato documento (chiavi naturali `codice_interno` in
# config.stati_doc_offerte) che il service nomina: la bozza dell'eliminazione e
# i due esiti del cliente. ⛔ Non l'emissione ne' l'annullo, che li dice il
# vocabolario (`stato_di_emissione`; lo stato d'annullo lo sceglie
# `vendite.fn_annulla_offerta`), e non gli stati di partenza dei passaggi.
class StatoOfferta:
    BOZZA = "BOZZA"
    ACCETTATA = "ACCETTATA"
    RIFIUTATA = "RIFIUTATA"


# Gli stati da cui si ELIMINA l'offerta (hard delete). ⚠️ Resta, dichiarato
# (brief-modello-documento-vendita §13.6 punto 4): non ripete la matrice, che
# l'eliminazione non la attraversa, e la tabella non ha un guard sul DELETE.
# ⛔ Non governa piu' testata, utility ne' eccezioni: quali colonne e quali righe
# si cambiano in quale stato lo dicono i lock del DB
# (`trgfn_doc_testata_lock_fuori_bozza`, `trgfn_doc_righe_lock_fuori_bozza`).
_STATI_EDITABILI: frozenset[str] = frozenset({StatoOfferta.BOZZA})


# Gli esiti che la rotta dell'esito accetta in ingresso: e' la validazione del
# campo `esito` (un 400 col campo), non lo stato di partenza. Da quale stato si
# registra un esito lo dice la matrice, al verbo. ⛔ Fino al 2026-10-26 si
# chiamava `_ESITI_AMMESSI_DA_EMESSA` e insieme a `_STATI_DA_EMESSA`,
# `_STATI_PUSHABILI` e `_STATI_TERMINALI` ripeteva la matrice e i guard delle
# madri (revisione, push): ritirati (§13.6 punto 4).
_ESITI: frozenset[str] = frozenset(
    {StatoOfferta.ACCETTATA, StatoOfferta.RIFIUTATA}
)


# Whitelist order_by ammessi dal service (gate prima del repository), DERIVATA
# dalla whitelist del repository (`_ORDER_COLS_OFFERTE`), unica fonte di verita'
# — stesso schema di `_ORDER_BY_CONTRATTI`.
#
# Era una copia scritta a mano, e il 2026-07-31 aveva gia' divergito: teneva
# `stato_codice_interno` e `data_update` dopo che il repository li aveva persi.
# Un gate piu' largo del repository non protegge, sposta il difetto di un piano:
# la chiave passa la validazione e poi il repository ripiega in silenzio.
# `revisione_numero` ASSENTE: non ordinabile (decisione §7.3).
_ORDER_BY_OFFERTE: frozenset[str] = frozenset(_ORDER_COLS_OFFERTE)


# UNIQUE constraints catalogati per mappare violazioni IntegrityError.
# Formato richiesto da `map_integrity_error`: tuple[error_code, message].
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_offerte_commerciali_codice": (
        E_VENDITE_DUPLICATO,
        "Codice offerta gia' esistente.",
        "codice",
    ),
    "uq_offerte_commerciali_uid": (
        E_VENDITE_DUPLICATO,
        "UID offerta gia' esistente.",
    ),
    "uq_offerte_commerciali_utilities_offerta_id": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un record utility per questa offerta (1:1).",
    ),
    "uq_offerte_eccezioni_one_eccezione_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione OVERRIDE/ESCLUSIONE per questo articolo "
        "nell'offerta.",
    ),
    "uq_offerte_eccezioni_one_aggiunta_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione AGGIUNTA per questo articolo nell'offerta.",
    ),
}


# Lo dicono il BB `risolvi_cliente_coppia` (prima) e la FK composta (dopo):
# una frase sola.
_MSG_BA_FUORI_COPPIA = (
    "Il billing account non e' quello dell'istanza e della utility dell'offerta."
)


# FK constraints catalogati (best-effort: i nomi corrispondono a quelli
# emessi da Postgres su violazione FK).
_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_offerte_commerciali_billing_account": (
        E_VENDITE_FK, "Billing account non trovato.",
    ),
    # FK composta (billing_account_id, istanza_utility_id, utility_id) verso il
    # BA della coppia, dal 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): la
    # semplice qui sopra resta accanto, e dice solo «non esiste».
    "fk_offerte_commerciali_ba_coppia": (
        E_VENDITE_FK,
        _MSG_BA_FUORI_COPPIA,
        "billing_account_id",
    ),
    "fk_offerte_commerciali_emittente_fiscale": (
        E_VENDITE_FK, "Emittente fiscale non trovato.",
    ),
    "fk_offerte_commerciali_listino": (
        E_VENDITE_FK, "Listino non trovato.",
    ),
    "fk_offerte_commerciali_listino_versione": (
        E_VENDITE_FK, "Versione listino non trovata.",
    ),
    "fk_offerte_commerciali_istanza_utility": (
        E_VENDITE_FK, "Istanza utility non trovata.",
    ),
    "fk_offerte_commerciali_utility": (
        E_VENDITE_FK, "Utility non trovata.",
    ),
    "fk_offerte_eccezioni_articolo": (
        E_VENDITE_FK, "Articolo non trovato.",
    ),
    "fk_offerte_eccezioni_offerta": (
        E_VENDITE_FK, "Offerta non trovata.",
    ),
}


# Whitelist payload create offerta (testata).
# Step 5 brief DB atterrato 2026-05-25: il codice OFC-* e' generato dal trigger
# `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT). Il campo `codice` NON
# va piu' nel payload: se inviato si rifiuta come unknown_key (defense-in-depth
# applicativo; il trigger DB e' la garanzia ultima).
CREATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "listino_id",
    "listino_versione_id",
    # Snapshot valuta fissato al CREATE, opzionale: se non passato, il
    # trigger DB `_a*_set_valuta_default_ins` risolve via
    # `vendite.fn_get_valuta_id` (catena BA → emittente → gestore, brief
    # work-done 2026-05-29). Il FE form-defaults può pre-popolarlo via BB
    # `resolve_valuta_default` per UX.
    "valuta_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
    # Sub-oggetto opzionale per la creazione contestuale del record
    # utility 1:1 (mirror ContrattoDrawer pattern, piano §C2). Se presente,
    # il service crea l'offerta + utility nella stessa transazione,
    # evitando il flusso "create offerta poi PATCH utility" che lascerebbe
    # un'offerta orfana di utility su fallimento intermedio.
    "utility",
})


# Whitelist payload update offerta (testata). Sub-set di create (immutabili:
# codice/uid/stato_doc_offerta_id/revisione_numero/revisione_padre_id e
# tutti i campi audit/timestamp di transizione).
# ⛔ Dal 2026-10-19 (R-BE-9) niente `utility_id` ne' `emittente_fiscale_id`: si
#    scelgono alla creazione e non si cambiano, nemmeno in bozza (E-3 di Tid; il
#    lock del DB «ferma sempre»). Le rifiuta sul campo `rifiuta_colonne_ferme`.
UPDATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "billing_account_id",
    "istanza_utility_id",
    "listino_id",
    "listino_versione_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
    # Sub-oggetto opzionale per upsert del record utility 1:1 nella stessa
    # transazione (simmetria col create, mirror ContrattoDrawer pattern).
    # Se valorizzato, l'update testata + l'upsert utility sono atomici.
    "utility",
})


# Whitelist payload eccezione (create).
# `componenti_overrides` non e' campo di `offerte_commerciali_eccezioni`:
# viene estratto pre-INSERT e passato a `fn_offerta_eccezione_componenti_init`
# (auto-init post-create_eccezione su articolo composito).
# Tipi eccezione che ammettono un prezzo manuale e quindi passano dal gate
# L1/L2/L3 (mirror di `contratti_service._TIPI_ECCEZIONE_CON_GATE`).
# ESCLUSIONE ha prezzo NULL → nessun gate.
_TIPI_ECCEZIONE_CON_GATE: frozenset[str] = frozenset({"OVERRIDE", "AGGIUNTA"})


CREATE_KEYS_ECCEZIONE: frozenset[str] = frozenset({
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
    "componenti_overrides",
    # Flag opt-in workflow L3 (richiesta approvazione su violazione L2). Non e'
    # colonna DB: estratto pre-INSERT dal service (mirror contratti).
    "richiesta_approvazione",
})


# Whitelist payload eccezione (update): articolo_id e tipo_eccezione immutabili.
# `componenti_overrides` non re-spedito in update (la BoM e' contratto
# immutabile post-init); la modifica prezzi componente passa via endpoint
# CRUD dedicato `PATCH .../componenti/<cid>/`.
UPDATE_KEYS_ECCEZIONE: frozenset[str] = frozenset(
    CREATE_KEYS_ECCEZIONE - {
        "articolo_id", "tipo_eccezione", "componenti_overrides",
    }
)


# Whitelist payload utility (create).
CREATE_KEYS_UTILITY: frozenset[str] = frozenset({
    "istanza_utility_id",
    "utility_id",
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})


# Whitelist payload utility (update): istanza_utility_id/utility_id immutabili.
UPDATE_KEYS_UTILITY: frozenset[str] = frozenset(
    CREATE_KEYS_UTILITY - {"istanza_utility_id", "utility_id"}
)


class OfferteService:
    """Service CRUD offerte commerciali — ciclo completo (D6, BE 2026-05-25)."""

    def __init__(self) -> None:
        self._repo = OfferteRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="offerte_service",
        )

    # =================================================================
    # Guard DB errors uniforme
    # =================================================================

    # Scopo: Normalizza errori DB (IntegrityError + DatabaseError P0001 dei
    #        trigger guard, codici E_OFFERTA_* parlanti) in ServiceError.
    #        Delega al BB condiviso `translate_db_errors` (core
    #        payload_helpers, estratto 2026-07-13 — regola del 2 alla 5a
    #        copia); resta la firma context-based per i call site del service.
    # ⭐ Il campo di E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA: il verbo nomina la
    #    COLONNA (`motivazione_rifiuto`, canale `COLUMN`), la richiesta porta
    #    `motivazione`. `error.fields` promette un input della richiesta
    #    (api.md §Envelope): qui il nome si traduce, per questo codice soltanto.
    #    ⛔ Non con `context={"field": ...}`: vincerebbe su OGNI errore del
    #    blocco, e un E_DOC_GIA_NELLO_STATO accenderebbe la motivazione.
    @contextmanager
    def _db_errors(
        self,
        context: dict[str, Any],
        *,
        fallback_message: str = "Violazione vincolo DB su offerta.",
    ) -> Iterator[None]:
        try:
            with translate_db_errors(
                context=context,
                fallback_code=E_VENDITE_VALIDATION,
                fallback_message=fallback_message,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
            ):
                yield
        except ServiceError as exc:
            if exc.code == E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA:
                exc.fields = (_CAMPO_MOTIVAZIONE,)
            raise

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata offerte. Niente default temporali impliciti: la UI
    #        applica i propri (es. validita_dal_min = inizio anno-1).
    def list_offerte(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_codice_interno: str | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        solo_ultima_revisione: bool = True,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "data_insert",
        order_dir: str = "desc",
        auth_user_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_OFFERTE, order_dir=order_dir)
        # ⭐ La soglia del termine (vuoto o sotto 3 caratteri → non filtra) la
        #    applica il BB `add_ricerca_full_condition` nel repository, uguale
        #    per tutte le liste. Fino al 2026-09-23 qui era un 400: il frontend
        #    manda il termine a ogni tasto, e i primi due erano un errore.
        # ⛔ Il filtro di stato esiste nel vocabolario, o e' un 400 sul campo: un
        #    valore sbagliato finiva nel WHERE e la lista rispondeva vuota con un
        #    200 (2026-10-20). Codici dismessi ammessi: i documenti vecchi li portano.
        richiedi_codice_a_vocabolario(
            "config.stati_doc_offerte", "codice_interno", stato_codice_interno,
            codice_errore="E_VENDITE_VALIDATION", parametro="stato_codice_interno",
        )
        filters: dict[str, Any] = {
            "billing_account_id": billing_account_id,
            "stato_codice_interno": stato_codice_interno,
            "utility_id": utility_id,
            "listino_id": listino_id,
            "validita_dal_min": validita_dal_min,
            "validita_dal_max": validita_dal_max,
            "search": search,
            "solo_ultima_revisione": solo_ultima_revisione,
            # Scope emittente: `None` = nessuna restrizione (superuser a
            # livello API); entra nei filtri cosi' righe e conteggio hanno lo
            # stesso perimetro.
            "auth_user_id": auth_user_id,
        }
        rows = self._repo.list_offerte(
            **filters,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        total = self._repo.count_offerte(**filters)
        return rows, total

    # Scopo: Etichette leggibili dei filtri attivi, incluse come metadato nel
    #        file di export (DEF-1 §6: un file filtrato deve dichiararsi
    #        sottoinsieme). Gemello di ContrattiService.resolve_filtri_export_label.
    def resolve_filtri_export_label(
        self,
        *,
        stato_codice_interno: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        solo_ultima_revisione: bool = True,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if stato_codice_interno:
            out["Stato"] = stato_codice_interno
        if billing_account_id is not None:
            out["Cliente BA (id)"] = billing_account_id
        if utility_id is not None:
            out["Utility (id)"] = utility_id
        if listino_id is not None:
            out["Listino (id)"] = listino_id
        if validita_dal_min:
            out["Dal"] = str(validita_dal_min)
        if validita_dal_max:
            out["Al"] = str(validita_dal_max)
        # solo_ultima_revisione=False = storico revisioni incluso.
        if not solo_ultima_revisione:
            out["Storico revisioni"] = "incluso"
        return out

    # Scopo: Carica la testata offerta o solleva E_VENDITE_NOT_FOUND (BB core
    #        `testata_o_not_found`: qui solo codice e messaggio del dominio).
    #        `getter` ammette il lettore leggero `get_stato_codice`, dove al
    #        chiamante basta sapere che l'offerta esiste.
    def _get_offerta_or_raise(
        self, offerta_id: int, *, op: str,
        getter: Callable[[int], Any] | None = None,
    ) -> Any:
        return testata_o_not_found(
            getter or self._repo.get_offerta, offerta_id,
            code=E_VENDITE_NOT_FOUND, message="Offerta non trovata.",
            id_name="offerta_id", function_name=f"offerte_service.{op}",
        )

    # Scopo: Dettaglio offerta + eccezioni + utility 1:1 + blob capability
    #        (refactor data-driven 2026-05-26). Lo stato della macchina e
    #        le azioni ammesse arrivano da `script.fn_available_actions_offerta`,
    #        cosi' il drawer Vue NON ricalcola nulla lato client (pattern
    #        coerente con contratti/preventivi/promo). Il blob viaggia
    #        intatto SOTTO `capabilities`, non fuso nella testata (api.md
    #        §«Il blob sta SOTTO `capabilities`», 2026-09-23): il merge
    #        nasconde le collisioni invece di evitarle.
    #
    #        Graceful fallback (2026-05-26 post bug fn DB `??` JSONB):
    #        se la fn capability solleva DatabaseError, logghiamo warning e
    #        ritorniamo il dettaglio con `capabilities` VUOTO (la chiave c'e'
    #        sempre: la forma non dipende dall'esito). Il FE cade in readonly
    #        conservativo (canEditTestata=false), ma l'operatore vede
    #        comunque l'offerta — niente errore E_DATABASE criptico al
    #        client per un problema diagnostico del DB. Pattern coerente
    #        col principio "una rottura del capability layer non deve
    #        impedire la lettura dell'entita'".
    def get_offerta(self, offerta_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        row = self._get_offerta_or_raise(offerta_id, op="get_offerta")
        row["eccezioni"] = self._repo.list_eccezioni(offerta_id)
        row["utility"] = self._repo.get_utility(offerta_id)
        row["capabilities"] = capabilities_o_vuoto(
            lambda: self._repo.get_available_actions(offerta_id),
            funzione="fn_available_actions_offerta", entita_id=offerta_id, logger=logger,
        )
        row["contatori"] = contatori_documento(NOTE_REPO_OFFERTA, offerta_id)
        return row

    # =================================================================
    # Create / Update / Delete testata
    # =================================================================

    # Scopo: Crea offerta in stato BOZZA. Il codice `OFC-*` e' generato
    #        dal trigger DB `trgfn_offerte_commerciali_gen_codice` (Step 5,
    #        atterrato 2026-05-25): non va nel payload (rifiutato dalla
    #        whitelist). Lo stato BOZZA si risolve via lookup `codice_interno`.
    def crea_offerta(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(payload, allowed=CREATE_KEYS_OFFERTA)
        # Validazioni applicative minime (il DB rifinisce gli invarianti via
        # CHECK chk_offerte_*).
        for required in (
            "emittente_fiscale_id",
            "billing_account_id",
            "istanza_utility_id",
            "utility_id",
            "listino_id",
            "validita_dal",
        ):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio in creazione.",
                context={"field": required},
            )
        # Estrae il sub-oggetto utility (opzionale, mirror ContrattoDrawer)
        # PRIMA di passare il payload al repo: la testata non ha la colonna
        # `utility` (vive in offerte_commerciali_utilities) e l'INSERT
        # fallirebbe come colonna inesistente. Atomicita' garantita dalla
        # transaction.atomic() che incapsula entrambe le scritture.
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            ErrorManager.require(
                isinstance(utility_payload, dict),
                code=E_VENDITE_VALIDATION,
                message="Campo 'utility' deve essere oggetto.",
                context={"got": type(utility_payload).__name__},
            )
        # Lo stato non si passa: l'offerta nasce nello stato iniziale del suo
        # vocabolario, e lo mette il DB (BB `script.trgfn_doc_stato_iniziale`,
        # brief-modello-documento-vendita P-2).
        data: dict[str, Any] = self._con_meta_normalizzato(
            {k: v for k, v in payload.items() if k != "utility"},
        )
        # `codice` NON in payload (vedi nota CREATE_KEYS_OFFERTA): il trigger
        # BEFORE INSERT genera OFC-NNNNNNN via `script.fn_generate_codice`.
        # `revisione_numero` ha default DB = 1.
        with self._db_errors({"billing_account_id": payload.get("billing_account_id")}):
            with transaction.atomic():
                offerta_id = self._repo.create_offerta(data)
                # Utility 1:1 inline: derivata da BA + campi business opzionali.
                # Eredita istanza_utility_id/utility_id dal payload testata se
                # non specificati nel sub-oggetto (coerenza FK garantita dal
                # BA scelto). Saltata se utility_payload e' None.
                if utility_payload is not None:
                    self._add_utility_inline(
                        offerta_id, payload, utility_payload,
                    )
                # Slot di default dall'anagrafica del cliente, nella stessa
                # transazione: lo decide il DB (`vendite.fn_doc_indirizzo_default`).
                self._repo.riempi_indirizzo_default(int(offerta_id))
        return self.get_offerta(offerta_id)

    # Scopo: Crea il record utility 1:1 contestualmente alla testata. Riusa
    #        la stessa whitelist + guard della crea_utility "esposta", ma
    #        senza il check di stato (siamo dentro la create, l'offerta e'
    #        appena nata in BOZZA per costruzione).
    def _add_utility_inline(
        self,
        offerta_id: int,
        offerta_payload: dict[str, Any],
        utility_payload: dict[str, Any],
    ) -> None:
        # Eredita istanza_utility_id/utility_id dalla testata se non passati
        # esplicitamente nel sub-oggetto (BA -> utility coerente).
        merged = dict(utility_payload)
        merged.setdefault("istanza_utility_id", offerta_payload.get("istanza_utility_id"))
        merged.setdefault("utility_id", offerta_payload.get("utility_id"))
        self._v.validate_allowed_keys(merged, allowed=CREATE_KEYS_UTILITY)
        merged = self._con_meta_normalizzato(merged)
        for required in ("istanza_utility_id", "utility_id"):
            ErrorManager.require(
                merged.get(required) is not None,
                code=E_VENDITE_VALIDATION,
                message=f"Campo utility.'{required}' obbligatorio.",
                context={"field": required},
            )
        self._repo.create_utility(offerta_id, merged)

    # Scopo: Aggiorna la testata di un'offerta. Payload vuoto -> 400 (no-op
    #        silenzioso evitato).
    #
    #        Quali colonne della TESTATA si cambiano in quale stato lo dice il
    #        DB, colonna per colonna: il lock `vendite.trgfn_doc_testata_lock_fuori_bozza`
    #        (in bozza tutto; emessa e accettata le note; chiusa niente). Fino
    #        al 2026-10-10 qui c'era un «solo in BOZZA» che ne era la seconda
    #        copia (brief-db-testata-dopo-emissione, D-0 e R-BE-2): il 409 del
    #        lock passa com'e'.
    #
    #        Sub-oggetto opzionale `utility`: se presente, fa upsert del
    #        record utility 1:1 nella stessa transaction.atomic(). Simmetria
    #        col create (refactor atomico 2026-05-26). Eredita
    #        `istanza_utility_id`/`utility_id` dalla testata se non passati
    #        esplicitamente nel sub-oggetto (coerenza FK garantita dal BA).
    #        In quale stato la fornitura si cambia lo dice il DB: il lock «solo
    #        in bozza» dei satelliti (`E_DOC_DATI_COLLEGATI_NON_BOZZA`, 409) e la
    #        capability `can_edit_utility`. Fino al 2026-10-11 qui si leggeva la
    #        capability prima di scrivere (brief-db-testata-dopo-emissione §11,
    #        R-BE-6): ora il 409 del lock passa com'e'.
    #        ⛔ Con un CAMBIO DI COPPIA (cliente, istanza o utility diversi da
    #        quelli della testata) la scheda del payload NON si applica: il
    #        trigger `trg_*_m50_fornitura_segue_cliente_upd` l'ha appena rifatta
    #        dal contatore nuovo, e l'upsert ci riscriverebbe sopra i dati del
    #        contatore di prima (R-BE-6 di brief-db-indirizzi-documento-seguono-
    #        il-cliente: D-5 svanirebbe in silenzio). Il dettaglio restituito
    #        porta la scheda rifatta dal DB.
    def aggiorna_offerta(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        rifiuta_colonne_ferme(
            payload, code=E_VENDITE_VALIDATION, function_name=f"{__name__}.aggiorna_offerta",
        )
        self._v.validate_allowed_keys(payload, allowed=UPDATE_KEYS_OFFERTA)
        # Prima la testata: fuori perimetro o inesistente e' un 404.
        self._get_offerta_or_raise(
            offerta_id, op="aggiorna_offerta", getter=self._repo.get_stato_codice,
        )
        # Split testata vs utility prima del repo. La testata non ha la
        # colonna `utility` (vive in offerte_commerciali_utilities).
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            ErrorManager.require(
                isinstance(utility_payload, dict),
                code=E_VENDITE_VALIDATION,
                message="Campo 'utility' deve essere oggetto.",
                context={"got": type(utility_payload).__name__},
            )
        testata_payload = self._con_meta_normalizzato(
            {k: v for k, v in payload.items() if k != "utility"},
        )
        # Almeno un campo, della testata o della scheda: `{"utility": {}}` da
        # solo non e' una modifica (fino al 2026-10-14 passava, e la risposta
        # era «salvata» senza aver scritto niente).
        self._v.require_campi_da_aggiornare(
            testata_payload, sotto_oggetti={"utility": utility_payload},
            context={"op": "aggiorna_offerta"}, log_to_db=False,
        )

        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                cambia_coppia = False
                if testata_payload:
                    # Letta dal helper del 404, non con `or {}`: la utility della
                    # coppia serve (si indicizza), e un'offerta sparita nel
                    # frattempo e' «non trovata», non un KeyError (500).
                    coppia = self._get_offerta_or_raise(
                        offerta_id, op="aggiorna_offerta", getter=self._repo.get_coppia,
                    )
                    # Il cliente si cambia per coppia: BA e istanza viaggiano
                    # insieme, letti dal lato che il payload porta (BB
                    # `risolvi_cliente_coppia`, lo stesso di preventivo e
                    # contratto), dentro la utility della testata, che non cambia.
                    if "billing_account_id" in testata_payload or "istanza_utility_id" in testata_payload:
                        (
                            testata_payload["billing_account_id"],
                            testata_payload["istanza_utility_id"],
                        ) = risolvi_cliente_coppia(
                            billing_account_id=self._v.optional_positive_int(
                                testata_payload, "billing_account_id",
                            ),
                            istanza_utility_id=self._v.optional_positive_int(
                                testata_payload, "istanza_utility_id",
                            ),
                            utility_id=int(coppia["utility_id"]),
                            code=E_VENDITE_VALIDATION,
                            msg_ba_fuori_coppia=_MSG_BA_FUORI_COPPIA,
                            function_name=f"{__name__}.aggiorna_offerta",
                        )
                    cambia_coppia = coppia_cambiata(testata_payload, coppia)
                    self._repo.update_offerta(offerta_id, testata_payload)
                if utility_payload is not None and not cambia_coppia:
                    self._upsert_utility_inline(offerta_id, utility_payload)
        return self.get_offerta(offerta_id)

    # Scopo: Upsert del record utility 1:1 contestualmente al PATCH testata.
    #        Distingue create (nessuna utility ancora) da update (utility
    #        esistente) tramite lookup; entrambi i rami applicano la stessa
    #        whitelist (`CREATE_KEYS_UTILITY` per create, `UPDATE_KEYS_UTILITY`
    #        per update — istanza_utility_id/utility_id immutabili dopo
    #        la creazione del record).
    def _upsert_utility_inline(
        self, offerta_id: int, utility_payload: dict[str, Any]
    ) -> None:
        existing = self._repo.get_utility(offerta_id)
        if existing is None:
            # Create: applica la stessa logica di crea_offerta inline.
            offerta = self._repo.get_offerta(offerta_id)
            assert offerta is not None
            self._add_utility_inline(offerta_id, offerta, utility_payload)
            return
        # Update: gli id (`istanza_utility_id`/`utility_id`) sono immutabili e
        # il sotto-oggetto del form li riporta: si tolgono. ⛔ Ma una chiave
        # SCONOSCIUTA si rifiuta (400), come nel ramo create: fino al
        # 2026-09-26 l'intersezione con la whitelist la scartava in silenzio —
        # un salvataggio «riuscito» senza aver scritto il campo.
        self._v.validate_allowed_keys(utility_payload, allowed=CREATE_KEYS_UTILITY)
        update_payload = self._con_meta_normalizzato({
            k: v for k, v in utility_payload.items() if k in UPDATE_KEYS_UTILITY
        })
        if not update_payload:
            return
        self._repo.update_utility(int(existing["id"]), update_payload)

    # Scopo: Elimina un'offerta in stato BOZZA (hard delete). L'annullamento
    #        "di processo" passa invece da `annulla` (BOZZA -> ANNULLATA).
    #        Il `delete` qui resta come pulizia tecnica di bozze "vuote".
    def elimina_offerta(self, offerta_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                deleted = self._repo.delete_offerta(offerta_id)
                ErrorManager.require(
                    deleted,
                    code=E_VENDITE_NOT_FOUND,
                    message="Offerta non trovata.",
                    context={"offerta_id": offerta_id},
                )

    # =================================================================
    # Transizioni di stato manuali
    # =================================================================

    # Scopo: BOZZA -> EMESSA. ⭐ La versione di listino la CONGELA il DB, nella
    #        stessa scrittura del cambio stato: il guard
    #        `trgfn_offerte_commerciali_guard_transizione` fissa
    #        `listino_versione_id` sulla versione in vigore oggi se e' vuota,
    #        dopo averla verificata con `script.fn_check_listino_congelabile`
    #        (la stessa regola che spegne «Emetti» nella capability). Listino
    #        senza versione in vigore: E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO
    #        dal DB (brief-db-offerta-emissione-ed-erogazione A-R1, A-R2).
    #        ⛔ Fino al 2026-10-07 il congelamento era qui, in Python, PRIMA del
    #        cambio stato: la capability spegneva «Emetti» proprio perche' quel
    #        passo non c'era ancora stato, e un'offerta nuova non si emetteva.
    #        Lo stato di arrivo dal vocabolario (V-2, brief-modello-documento-
    #        vendita §8.11 B-4), non `StatoOfferta.EMESSA`, scritto dal verbo di
    #        stato (§13.6 punto 1): permesso dalla riga del passaggio
    #        (`emetti_offerta`), un secondo «Emetti» (E_DOC_GIA_NELLO_STATO) e
    #        lo stato di partenza li giudica il DB; l'offerta che non c'e' e' il
    #        404 del service (`_cambia_stato`).
    def emetti(self, offerta_id: int) -> dict[str, Any]:
        stato = stato_di_emissione(TESTATA_OFFERTE, function_name="offerte_service.emetti")
        return self._cambia_stato(offerta_id, stato_codice=stato.codice)

    # Scopo: EMESSA -> ACCETTATA (esito cliente positivo). Il trigger DB
    #        valorizza `data_accettazione`.
    def registra_accettazione(self, offerta_id: int) -> dict[str, Any]:
        return self._cambia_stato(offerta_id, stato_codice=StatoOfferta.ACCETTATA)

    # Scopo: EMESSA -> RIFIUTATA (esito cliente negativo). Il trigger DB
    #        valorizza `data_rifiuto`; la motivazione la scrive il verbo in
    #        `motivazione_rifiuto`.
    #        ⭐ Che la motivazione sia obbligatoria lo dice la riga del passaggio
    #        (`requires_motivazione`), al verbo:
    #        E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA, al client col campo
    #        `motivazione` (O-3, `_db_errors`). ⛔ Fino al 2026-10-26 era una copia Python
    #        (`guard_non_empty_string`).
    def registra_rifiuto(
        self, offerta_id: int, *, motivazione: Any
    ) -> dict[str, Any]:
        return self._cambia_stato(
            offerta_id, stato_codice=StatoOfferta.RIFIUTATA,
            motivazione=self._motivazione(motivazione),
        )

    # Scopo: Esito cliente unificato (ACCETTATA o RIFIUTATA, da EMESSA). La
    #        view si limita a passare il payload, il routing per esito vive
    #        qui — coerente con i due metodi specifici sopra (mantenuti per
    #        chi vuole l'API esplicita).
    #        ⛔ L'accettazione non porta una motivazione: la sola colonna che la
    #        terrebbe e' `motivazione_rifiuto`, e scartarla in silenzio direbbe
    #        al client che e' stata presa (stesso criterio di `valido_al` nel
    #        cambio stato del contratto). Una motivazione con ACCETTATA e' un
    #        400 col campo; assente, null o vuota passa. Fino al 2026-10-26 si
    #        perdeva qui senza dirlo.
    def registra_esito(
        self, offerta_id: int, *, esito: str, motivazione: Any = None
    ) -> dict[str, Any]:
        ErrorManager.require(
            esito in _ESITI,
            code=E_VENDITE_VALIDATION,
            message="Esito non valido.",
            detail=f"Atteso uno tra {sorted(_ESITI)}, ricevuto {esito!r}.",
            context={"offerta_id": offerta_id, "esito": esito, "field": "esito"},
        )
        if esito == StatoOfferta.ACCETTATA:
            ErrorManager.require(
                self._motivazione(motivazione) is None,
                code=E_VENDITE_VALIDATION,
                message="La motivazione si indica solo per rifiutare o annullare l'offerta.",
                context={"offerta_id": offerta_id, "esito": esito, "field": _CAMPO_MOTIVAZIONE},
            )
            return self.registra_accettazione(offerta_id)
        return self.registra_rifiuto(offerta_id, motivazione=motivazione)

    # Scopo: Crea rev.N+1 di un'offerta in stato EMESSA invocando la fn DB
    #        `vendite.fn_crea_revisione_offerta`. La fn copia testata +
    #        eccezioni attive + utility 1:1; il trigger DB
    #        `trg_offerte_commerciali_z90_revisione_ins` marca automaticamente
    #        la rev.N corrente come SUPERATA. Ritorna la nuova rev.N+1
    #        (BOZZA) come dettaglio completo.
    #
    #        Lo stato di partenza (EMESSA) lo dice il DB
    #        (`E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`); qui solo l'esistenza
    #        (404). ⛔ Fino al 2026-10-26 lo ripeteva `_assert_stato_corrente`
    #        (brief-modello-documento-vendita §13.6 punto 4).
    def crea_revisione(
        self, offerta_id: int, *, user: str | None = None
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="crea_revisione", getter=self._repo.get_stato_codice)
        with self._db_errors(
            {"offerta_id": offerta_id},
            fallback_message="Errore creazione revisione offerta.",
        ):
            with transaction.atomic():
                new_id = self._repo.crea_revisione(offerta_id, user)
        return self.get_offerta(new_id)

    # Scopo: Push offerta ACCETTATA → contratto DRAFT (Step 8 brief DB,
    #        atterrato 2026-05-25). Pattern A idempotenza: la fn DB
    #        `fn_push_offerta_a_contratto` ha guard UNIQUE su
    #        `contratti.offerta_id` — doppia invocazione fallisce con
    #        `E_OFFERTA_CONTRATTO_GIA_GENERATO`. Pratica opzionale.
    #
    #        Ritorna `OffertaPushResult` con id+numero del nuovo contratto
    #        DRAFT e il `sorgente_uid` (= `offerta.uid`) per tracciabilita'.
    #
    #        Successione su overlap (brief successione 2026-05-31): se per la
    #        quintupla esiste gia' un contratto attivo sovrapposto, la fn DB
    #        solleva `E_CONTRATTO_OVERLAP_ESISTENTE` quando `chiudi_esistente`
    #        e' False (il FE intercetta il codice, mostra il contratto in
    #        conflitto via `get_contratto_sovrapposto` e ri-chiama con
    #        `chiudi_esistente=True`, che chiude il vecchio per successione).
    #
    #        Lo stato di partenza (ACCETTATA) lo dice il verbo
    #        (`E_OFFERTA_PUSH_STATO_NON_AMMESSO`); qui solo l'esistenza (404).
    def push_a_contratto(
        self,
        offerta_id: int,
        *,
        pratica_id: int | None = None,
        chiudi_esistente: bool = False,
    ) -> OffertaPushResult:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        if pratica_id is not None:
            self._v.guard_positive_int(pratica_id, field="pratica_id")
        self._get_offerta_or_raise(offerta_id, op="push_a_contratto", getter=self._repo.get_stato_codice)
        with self._db_errors(
            {
                "offerta_id": offerta_id,
                "pratica_id": pratica_id,
                "chiudi_esistente": chiudi_esistente,
            },
            fallback_message="Errore push offerta a contratto.",
        ):
            with transaction.atomic():
                contratto_id = self._repo.push_a_contratto(
                    offerta_id, pratica_id, chiudi_esistente,
                )
                # La cascata DB copia gli indirizzi dell'offerta sul contratto;
                # il default riempie lo slot SOLO se e' rimasto vuoto (la
                # sorgente vince). Il verbo scrive la testata da se', non passa
                # da `vendite.fn_create_contratto`: il default va chiamato qui.
                ContrattiRepository().riempi_indirizzo_default(int(contratto_id))
        contratto = self._repo.get_contratto_minimal(contratto_id)
        ErrorManager.require(
            contratto is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto generato non leggibile post-push.",
            context={"contratto_id": contratto_id, "offerta_id": offerta_id},
        )
        assert contratto is not None
        return OffertaPushResult(
            contratto_id=int(contratto["id"]),
            contratto_codice=str(contratto["numero"]),
            sorgente_uid=str(contratto["uid"]),
        )

    # Scopo: Ritorna il contratto attivo la cui validita' si sovrappone a
    #        quella che il push genererebbe per questa offerta, o None.
    #        Lettura libera (read-only): alimenta il dialog FE di successione
    #        quando il push ha restituito `E_CONTRATTO_OVERLAP_ESISTENTE`.
    #        Delega a `fn_contratto_sovrapposto` (dominio contratti) via repo.
    def get_contratto_sovrapposto(
        self, offerta_id: int
    ) -> dict[str, Any] | None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="get_contratto_sovrapposto", getter=self._repo.get_stato_codice)
        return self._repo.get_contratto_sovrapposto(offerta_id)

    # Scopo: Ritorna una PAGINA della catena di revisioni che condivide la
    #        radice (rev.1) con l'offerta passata, col totale per
    #        `paginated_envelope`. Lettura libera in ogni stato.
    def list_revisioni(
        self, offerta_id: int, *,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str | None = None, order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        # 404 esplicito se l'offerta non esiste (o e' fuori perimetro): una
        # lista vuota direbbe «nessuna revisione» di un documento che non c'e'.
        self._get_offerta_or_raise(offerta_id, op="list_revisioni", getter=self._repo.get_stato_codice)
        return self._repo.list_revisioni(
            offerta_id,
            limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        )

    # Scopo: -> lo stato d'annullo, da BOZZA (ritiro prima dell'emissione) o
    #        da ACCETTATA (l'offerta che non si trasforma piu'), dal verbo
    #        `vendite.fn_annulla_offerta` (O-4, brief-modello-documento-vendita
    #        §13.6 punto 3): prima cio' che vieta (da ACCETTATA, un contratto o
    #        un ordine vivo nato dall'offerta), poi la conferma dei legami — la
    #        revisione precedente, superata, che torna emessa: senza
    #        `legami_confermati` il DB rifiuta (E_DOC_ANNULLO_CON_LEGAMI,
    #        `confirm_and_retry`), e il numero lo legge `get_legami` —, poi lo
    #        stato dal verbo di stato con la motivazione, obbligatoria
    #        (E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA). Il trigger DB valorizza
    #        `data_annullamento`. Il permesso dell'annullo dell'accettata
    #        (`emetti_offerta`) dalla riga del passaggio.
    #        ⛔ Nessuno stato di partenza ne' stato d'annullo scritto qui: li
    #        dicono la matrice e il vocabolario. Fino al 2026-10-26 lo stato
    #        passava da un UPDATE diretto e la motivazione da una copia Python.
    def annulla(
        self, offerta_id: int, *, motivazione: Any, legami_confermati: Any = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        motivo = self._motivazione(motivazione)
        confermati = dichiarazione_legami(
            legami_confermati, validation_code=E_VENDITE_VALIDATION,
            function_name="offerte_service.annulla",
        )
        # Esistenza col lettore leggero: il 404 del dominio prima del verbo.
        self._get_offerta_or_raise(offerta_id, op="annulla", getter=self._repo.get_stato_codice)
        with self._db_errors(
            {"offerta_id": offerta_id},
            fallback_message="Annullo offerta non consentito.",
        ):
            with transaction.atomic():
                self._repo.annulla(offerta_id, motivo, confermati)
        return self.get_offerta(offerta_id)

    # Scopo: I legami dell'offerta per la finestra di conferma dell'annullo
    #        (BB `legami_del_documento`): la revisione precedente, superata,
    #        che torna emessa se si annulla questa (O-4). Prima la testata: il
    #        lettore del DB non applica il perimetro.
    def get_legami(self, offerta_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="get_legami", getter=self._repo.get_stato_codice)
        return legami_del_documento(SORGENTE_OFFERTA_COMMERCIALE, offerta_id)

    # =================================================================
    # CRUD eccezioni (solo in BOZZA)
    # =================================================================

    # Scopo: Lista eccezioni di un'offerta (qualsiasi stato — la lettura
    #        non e' bloccata; il guard BOZZA si applica solo in scrittura).
    def list_eccezioni(self, offerta_id: int) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        # Verifica esistenza offerta per 404 esplicito.
        self._get_offerta_or_raise(offerta_id, op="list_eccezioni", getter=self._repo.get_stato_codice)
        return self._repo.list_eccezioni(offerta_id)

    # Scopo: una PAGINA delle righe operative dell'offerta, per la lista
    #        configurabile `vendite.offerta_righe` (brief-db-righe-esclusione-
    #        solo-non-si-vende §8.1): ricerca dal catalogo, ordinamento dalla
    #        whitelist, codice articolo quando nessuno chiede altro. Ritorna
    #        `(righe, totale)`. Gemella di `ContrattiService.list_righe_pagina`.
    # ⭐ «Leggi prima la testata»: un'offerta fuori perimetro e' un 404, non una
    #    lista vuota (la funzione su un id che non vede risponde zero righe).
    def list_righe_pagina(
        self, offerta_id: int, **opzioni: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        return pagina_dopo_testata(
            lambda: self._get_offerta_or_raise(
                offerta_id, op="list_righe_pagina", getter=self._repo.get_stato_codice,
            ),
            OffertaRigheListaRepository().list_righe_pagina, offerta_id, **opzioni,
        )

    # Scopo: Crea un'eccezione. Solo in stato BOZZA.
    def crea_eccezione(
        self,
        offerta_id: int,
        payload: dict[str, Any],
        *,
        auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=CREATE_KEYS_ECCEZIONE)
        payload = self._con_meta_normalizzato(payload)
        # «Solo in bozza» lo dice il DB (`trgfn_doc_righe_lock_fuori_bozza` su
        # eccezioni e componenti, `E_RIGA_DOC_NON_BOZZA`, 409): qui l'esistenza.
        self._get_offerta_or_raise(offerta_id, op="righe", getter=self._repo.get_stato_codice)
        # ⚠️ La fonte non si pretende qui (2026-10-04, brief-db-righe-esclusione-
        # solo-non-si-vende): l'ESCLUSIONE nasce vuota, e su OVERRIDE/AGGIUNTA la
        # riempie il trigger DB dall'erogazione, che il guard DB rende obbligatoria.
        # Stessa forma del contratto, che la fonte non l'ha mai pretesa.
        for required in ("articolo_id", "tipo_eccezione"):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )

        # Gate L1 override prezzo componenti (BB condiviso, 2026-06-01): se il
        # payload porta `componenti_overrides` l'operatore deve avere l'azione
        # `prezzo_override_manuale`. Prima del pop (il payload li contiene ancora).
        validate_componenti_overrides_authorization(
            payload, auth_user_id, function_name="offerte_service.crea_eccezione",
        )
        # Flag opt-in workflow L3. Estratto qui per non finire nel payload INSERT.
        richiesta_approvazione = self._v.optional_bool(payload, "richiesta_approvazione") is True
        payload.pop("richiesta_approvazione", None)

        # Estrae overrides BoM prima di passare il payload al repo (la colonna
        # non esiste su `offerte_commerciali_eccezioni`); normalizza valori.
        overrides_raw = payload.pop("componenti_overrides", None)
        componenti_overrides = normalize_componenti_overrides(
            overrides_raw,
            function_name="offerte_service.crea_eccezione",
            error_code=E_VENDITE_VALIDATION,
        )

        articolo_id = payload.get("articolo_id")
        # Pre-check articolo composito (cache locale per non chiamare 2 volte
        # il repo nel ramo INSERT + init componenti). Usato sia per il guard
        # `prezzo_unitario = None` sotto, sia per l'auto-init componenti.
        is_composito = bool(
            articolo_id
            and self._repo.is_articolo_composito(str(articolo_id)),
        )

        # Coerenza prezzo_unitario / tipo_eccezione (pre-DB, specchio CHECK
        # `chk_offerte_eccezioni_prezzo_per_tipo_eccezione`):
        # - OVERRIDE / AGGIUNTA -> prezzo NOT NULL (e' il prezzo finale)
        # ⛔ L'ESCLUSIONE non si pre-valida qui: il prezzo e' uno dei dieci dati
        #    di fatturazione che il guard DB rifiuta col campo
        #    (E_RIGA_ESCLUSIONE_CON_DATI, brief-db-righe-esclusione-solo-non-si-
        #    vende R-BE-3), come sul contratto.
        # Eccezione: articolo composito (modello unificato BoM). Il FE puo'
        # omettere `prezzo_unitario` per padri compositi perche' il prezzo
        # padre = SUM(figli × coeff_qta) calcolato dal trigger DB
        # `_z90_ricalcola_padre` post-init componenti BoM nello stesso
        # `transaction.atomic`. Settiamo `Decimal(0)` come placeholder per
        # superare il CHECK; il trigger lo sovrascrive sincrono dopo INSERT
        # padre + INSERT figli. Pattern simmetrico ai contratti (cfr.
        # `contratti_service` ~ linea 2114 "Padre composito").
        tipo_eccezione = payload.get("tipo_eccezione")
        prezzo_raw = payload.get("prezzo_unitario")
        if prezzo_raw is None and tipo_eccezione in ("OVERRIDE", "AGGIUNTA"):
            ErrorManager.require(
                is_composito,
                code=E_VENDITE_VALIDATION,
                message=(
                    f"{tipo_eccezione}: prezzo_unitario obbligatorio "
                    "per articoli non compositi."
                ),
                context={"tipo_eccezione": tipo_eccezione},
            )
            # Placeholder: il trigger DB lo sovrascrive a SUM(componenti).
            payload = {**payload, "prezzo_unitario": Decimal("0")}

        # Gate prezzo L1+L2+L3 su OVERRIDE/AGGIUNTA NON compositi: il prezzo
        # composito e' derivato (SUM figli) → nessun confronto col resolver.
        # `testata_gate` riusato dal ramo composito sotto (1 round-trip in meno).
        pratica_id_l3: int | None = None
        testata_gate: dict[str, Any] | None = None
        # Fix analisi-fix-transazioni #8 (Classe B): il gate L3 (crea la pratica
        # di approvazione) vive DENTRO transaction.atomic() insieme alla create
        # eccezione. Prima era invocato PRIMA dell'atomic → pratica orfana se la
        # create eccezione rollava. Il gate fa permission-check L1/L2 in Python
        # (azioni di processo): resta orchestrazione BE, non funzione madre DB.
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                if tipo_eccezione in _TIPI_ECCEZIONE_CON_GATE and not is_composito:
                    pratica_id_l3, testata_gate = self._apply_pricing_gate_eccezione(
                        offerta_id=offerta_id,
                        articolo_id=articolo_id,
                        uom_id=payload.get("uom_operativa_id"),
                        payload=payload,
                        auth_user_id=auth_user_id,
                        richiesta_approvazione=richiesta_approvazione,
                        riga_id_for_link=None,  # eccezione_id non noto qui
                    )
                eccezione_id = self._repo.create_eccezione(offerta_id, payload)
                # Link riga<->pratica L3: post-create, eccezione_id ora noto.
                if pratica_id_l3 is not None:
                    from apps.vendite.services.approvazioni_prezzo_service import (
                        link_riga_a_pratica,
                    )
                    link_riga_a_pratica(
                        pratica_id=pratica_id_l3,
                        riga_id=eccezione_id,
                        sorgente=META_SORGENTE_OFFERTA,
                    )
                # Auto-init componenti BoM su articolo composito (mirror del
                # flow contratti: la fn DB e' idempotente, no-op se gia'
                # presenti o articolo non composito).
                # ESCLUSIONE escluso: un articolo escluso non ha prezzo
                # (CHECK chk_offerte_eccezioni_prezzo_per_tipo_eccezione impone
                # prezzo_unitario NULL) ne' senso di negoziare i suoi componenti.
                # Inizializzarli farebbe scattare trgfn_componenti_ricalcola_padre
                # che scriverebbe SUM(figli) sul padre ESCLUSIONE -> violazione.
                if is_composito and tipo_eccezione != "ESCLUSIONE":
                    testata = testata_gate or self._repo.get_offerta(offerta_id) or {}
                    emittente_sr_id = self._resolve_emittente_sr_id_for_offerta(
                        offerta_id=offerta_id,
                        testata=testata,
                        auth_user_id=auth_user_id,
                        function_name="offerte_service.crea_eccezione",
                    )
                    self._repo.init_componenti_eccezione(
                        eccezione_id=eccezione_id,
                        emittente_soggetto_ruolo_id=emittente_sr_id,
                        data_riferimento=testata.get("validita_dal"),
                        componenti_overrides=componenti_overrides,
                    )
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Aggiorna un'eccezione. Solo se offerta in BOZZA. Payload vuoto
    #        -> 400 (no-op silenzioso evitato). Se il PATCH tocca
    #        `prezzo_unitario` su una eccezione OVERRIDE/AGGIUNTA non composita,
    #        applica il gate L1/L2/L3 (mirror di `contratti_service.update_riga`).
    def aggiorna_eccezione(
        self, offerta_id: int, eccezione_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.validate_allowed_keys(payload, allowed=UPDATE_KEYS_ECCEZIONE)
        payload = self._con_meta_normalizzato(payload)
        # Flag opt-in workflow L3 (estratto prima del guard non-vuoto: non e' un
        # campo di update di per se').
        richiesta_approvazione = self._v.optional_bool(payload, "richiesta_approvazione") is True
        payload.pop("richiesta_approvazione", None)
        self._v.require_campi_da_aggiornare(
            payload, context={"op": "aggiorna_eccezione"}, log_to_db=False,
        )
        # «Solo in bozza» lo dice il DB (`trgfn_doc_righe_lock_fuori_bozza` su
        # eccezioni e componenti, `E_RIGA_DOC_NON_BOZZA`, 409): qui l'esistenza.
        self._get_offerta_or_raise(offerta_id, op="righe", getter=self._repo.get_stato_codice)
        existing = riga_del_padre_o_not_found(
            self._repo.get_eccezione, eccezione_id,
            padre_id=offerta_id, chiave_padre="offerta_id",
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            function_name="vendite.offerte_service.aggiorna_eccezione",
        )
        # Gate prezzo L1+L2+L3 quando il PATCH tocca `prezzo_unitario` su
        # OVERRIDE/AGGIUNTA non composito. Il prezzo composito e' derivato →
        # nessun gate (i componenti hanno il proprio workflow). `articolo_id` e
        # `tipo_eccezione` sono immutabili → letti dalla riga esistente.
        tipo_existing = existing.get("tipo_eccezione")
        # Fix analisi-fix-transazioni #9 (Classe B): il gate L3 (crea + linka
        # inline la pratica di approvazione) vive DENTRO transaction.atomic()
        # insieme all'UPDATE eccezione. Prima era invocato PRIMA dell'atomic →
        # pratica orfana se l'UPDATE rollava. Il gate fa permission-check L1/L2
        # in Python (azioni di processo): resta orchestrazione BE, non fn madre DB.
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                if (
                    tipo_existing in _TIPI_ECCEZIONE_CON_GATE
                    and not bool(existing.get("is_composito"))
                    and "prezzo_unitario" in payload
                ):
                    self._apply_pricing_gate_eccezione(
                        offerta_id=offerta_id,
                        articolo_id=existing.get("articolo_id"),
                        uom_id=payload.get("uom_operativa_id") or existing.get("uom_operativa_id"),
                        payload=payload,
                        auth_user_id=auth_user_id,
                        richiesta_approvazione=richiesta_approvazione,
                        riga_id_for_link=eccezione_id,  # noto: link inline
                        # Preserva il meta persistito (audit/altre chiavi): senza,
                        # l'UPDATE prezzo lo sovrascriverebbe col solo audit nuovo.
                        fallback_meta=existing.get("meta"),
                    )
                self._repo.update_eccezione(eccezione_id, payload)
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Helper unificato gate L1+L2+L3 su eccezione offerta. Mirror di
    #        `contratti_service._apply_pricing_gate_riga`. Muta `payload`
    #        (prezzo_unitario normalizzato, merge meta audit, e — se workflow L3
    #        attivo — stato_approvazione_prezzo=PENDING + pratica id). Orchestra
    #        la pratica L3 quando il prezzo viola L2 e `richiesta_approvazione`
    #        e' true. Ritorna `(pratica_id_l3 | None, testata_gate)` (testata
    #        riusata dal caller per il ramo composito → no double-fetch).
    def _apply_pricing_gate_eccezione(
        self,
        *,
        offerta_id: int,
        articolo_id: Any,
        uom_id: Any,
        payload: dict[str, Any],
        auth_user_id: int | None,
        richiesta_approvazione: bool,
        riga_id_for_link: int | None,
        fallback_meta: dict[str, Any] | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        testata_gate = self._repo.get_offerta(offerta_id)
        assert testata_gate is not None
        prezzo_finale, prezzo_meta = resolve_or_check_override_prezzo_riga_offerta(
            testata=testata_gate,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=payload.get("prezzo_unitario"),
            auth_user_id=auth_user_id,
            function_name="offerte_service._apply_pricing_gate_eccezione",
            richiesta_approvazione=richiesta_approvazione,
        )
        if prezzo_finale is not None:
            payload["prezzo_unitario"] = prezzo_finale
        if prezzo_meta:
            # Merge audit pricing sul meta corrente. Priorita': payload.meta >
            # `fallback_meta` (meta della riga esistente, case update) > {}.
            # Senza fallback, un UPDATE che tocca il prezzo (payload senza meta)
            # sovrascriverebbe il meta persistito perdendo le chiavi precedenti.
            base_meta = payload.get("meta") or fallback_meta or {}
            # Coerce JSONB→dict difensivo (mirror contratti): il meta puo'
            # arrivare come stringa JSON da certi path repo.
            if isinstance(base_meta, str):
                try:
                    parsed = json.loads(base_meta)
                    base_meta = parsed if isinstance(parsed, dict) else {}
                except (json.JSONDecodeError, ValueError):
                    base_meta = {}
            merged_meta = dict(base_meta)
            merged_meta.update(prezzo_meta)
            payload["meta"] = merged_meta
        pratica_id_l3: int | None = None
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request_offerta(
                offerta_id=offerta_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id_for_link,
            )
            payload["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            payload["pratica_approvazione_prezzo_id"] = pratica_id_l3
        return pratica_id_l3, testata_gate

    # Scopo: Le combinazioni (tipo_erogazione, fonte_quantita_attesa) che una
    #        riga con questo articolo puo' avere sull'offerta, col default che
    #        erediterebbe in testa: il form delle righe le propone e
    #        preseleziona il default (brief-db-offerta-emissione-ed-erogazione
    #        B-R4). Le dice il DB (`vendite.fn_documento_riga_erogazioni`), la
    #        stessa sede che leggono l'eredita' e il guard del perimetro.
    #        Prima la testata: un'offerta che non si vede e' un 404, non una
    #        lista vuota. Lista vuota = l'articolo ha una tipologia che la
    #        utility dell'offerta non prevede. Gemello di
    #        `ContrattiService.list_erogazioni_riga`.
    def list_erogazioni_riga(
        self, offerta_id: int, articolo_id: Any,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        articolo = self._v.require_uuid({"articolo_id": articolo_id}, "articolo_id")
        self._get_offerta_or_raise(
            offerta_id, op="list_erogazioni_riga", getter=self._repo.get_stato_codice,
        )
        return list_erogazioni_riga(SORGENTE_OFFERTA_COMMERCIALE, offerta_id, articolo)

    # =================================================================
    # Componenti BoM su eccezione (mirror contratti, simmetria 2026-05-26)
    # =================================================================

    # Scopo: Preview componenti BoM PRIMA del save eccezione (ComponentiDialog
    # FE). Read-only, nessun side-effect. Risolve emittente da testata >
    # operatore. Mirror di `ContrattiService.preview_componenti_riga`.
    def preview_componenti_eccezione(
        self,
        offerta_id: int,
        *,
        articolo_id: str,
        uom_operativa_id: int | None,
        quantita: Any,
        auth_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        testata = self._get_offerta_or_raise(offerta_id, op="preview_componenti_eccezione")
        emittente_sr_id = self._resolve_emittente_sr_id_for_offerta(
            offerta_id=offerta_id,
            testata=testata,
            auth_user_id=auth_user_id,
            function_name="offerte_service.preview_componenti_eccezione",
        )
        # `utility_id` NOT NULL su DDL: guard parlante prima del cast per
        # evitare TypeError criptici in caso di dato malformato (test/dev).
        utility_id_raw = testata.get("utility_id")
        ErrorManager.require(
            utility_id_raw is not None,
            code=E_VENDITE_VALIDATION,
            message="Offerta senza utility_id: impossibile risolvere il pricing.",
            context={"offerta_id": offerta_id},
        )
        return self._repo.preview_componenti_eccezione(
            articolo_id=str(articolo_id),
            uom_id=uom_operativa_id,
            quantita_padre=quantita,
            data_riferimento=testata.get("validita_dal"),
            ba_id=testata.get("billing_account_id"),
            utility_id=int(utility_id_raw),
            emittente_soggetto_ruolo_id=emittente_sr_id,
        )

    # Scopo: Helper unificato risoluzione emittente_sr_id per le operazioni
    # componenti BoM dell'offerta. Precedenza: testata > operatore. Solleva
    # E_VENDITE_VALIDATION se nessuna fonte (admin globale + testata senza
    # emittente_fiscale_id). Centralizza il pattern riusato da
    # `crea_eccezione` e `preview_componenti_eccezione`.
    def _resolve_emittente_sr_id_for_offerta(
        self,
        *,
        offerta_id: int,
        testata: dict[str, Any],
        auth_user_id: int | None,
        function_name: str,
    ) -> int:
        emittente_sr_id = resolve_emittente_sr_id_for_testata(
            testata, auth_user_id,
            repo_get_sr_id_by_fiscale_id=self._repo.get_emittente_sr_id_by_fiscale_id,
        )
        ErrorManager.require(
            emittente_sr_id is not None,
            code=E_VENDITE_VALIDATION,
            message=(
                "Operazione componenti BoM richiede emittente fiscale "
                "risolvibile (testata o utente)."
            ),
            context={"offerta_id": offerta_id},
            function_name=function_name,
        )
        assert emittente_sr_id is not None
        return emittente_sr_id

    # Scopo: Lista componenti BoM persistiti su eccezione composita. Guard
    # esistenza eccezione + match URL anti-tampering (eccezione_id deve
    # appartenere all'offerta_id richiesto).
    def list_componenti_eccezione(
        self,
        offerta_id: int, eccezione_id: int,
        *, solo_attivi: bool = True,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        eccezione = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            eccezione is not None
            and int(eccezione.get("offerta_id") or 0) == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione offerta non trovata.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        return self._repo.list_componenti_riga(eccezione_id, solo_attivi=solo_attivi)

    # Scopo: Modifica componente BoM eccezione esistente. Whitelist colonne via
    # repo mixin. Guard stato offerta editabile + esistenza componente +
    # match URL.
    def update_componente_eccezione(
        self,
        offerta_id: int, eccezione_id: int, componente_id: int,
        payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        # «Solo in bozza» lo dice il DB (`trgfn_doc_righe_lock_fuori_bozza` su
        # eccezioni e componenti, `E_RIGA_DOC_NON_BOZZA`, 409): qui l'esistenza.
        self._get_offerta_or_raise(offerta_id, op="righe", getter=self._repo.get_stato_codice)
        self._load_componente_for_modification(
            offerta_id=offerta_id, eccezione_id=eccezione_id,
            componente_id=componente_id,
        )
        # ⛔ Contratto dell'OPERATORE (BB unico per i cinque documenti), non
        #    la whitelist del repository: fino al 2026-09-26 qui si validava
        #    contro `COMPONENTE_UPDATE_ALLOWED`, che contiene
        #    `stato_approvazione_prezzo` — un operatore poteva approvarsi da
        #    solo un prezzo L3 PENDING. `origine_prezzo` la deriva il server.
        payload = dati_patch_componente(
            payload, auth_user_id=auth_user_id,
            function_name="offerte_service.update_componente_eccezione",
        )
        with self._db_errors(
            {"componente_id": componente_id, "eccezione_id": eccezione_id},
            fallback_message=(
                "Violazione vincolo DB su componente eccezione offerta."
            ),
        ):
            self._repo.update_componente(componente_id, **payload)
        return {"status": "ok", "componente_id": componente_id}

    # Scopo: Soft delete componente BoM eccezione (`attivo=FALSE`). Il trigger
    # DB di ricalcolo padre esclude i componenti inattivi dalla SUM.
    def delete_componente_eccezione(
        self,
        offerta_id: int, eccezione_id: int, componente_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        # «Solo in bozza» lo dice il DB (`trgfn_doc_righe_lock_fuori_bozza` su
        # eccezioni e componenti, `E_RIGA_DOC_NON_BOZZA`, 409): qui l'esistenza.
        self._get_offerta_or_raise(offerta_id, op="righe", getter=self._repo.get_stato_codice)
        self._load_componente_for_modification(
            offerta_id=offerta_id, eccezione_id=eccezione_id,
            componente_id=componente_id,
        )
        with self._db_errors(
            {"componente_id": componente_id, "eccezione_id": eccezione_id},
            fallback_message="Impossibile eliminare il componente (dipendenze).",
        ):
            deleted = self._repo.delete_componente(componente_id)
        return {
            "status": "ok",
            "componente_id": componente_id,
            "deleted": deleted,
        }

    # Scopo: Lookup componente + verifica appartenenza eccezione/offerta.
    # Centralizza guard URL anti-tampering riusato da update/delete componente.
    def _load_componente_for_modification(
        self,
        *,
        offerta_id: int,
        eccezione_id: int,
        componente_id: int,
    ) -> dict[str, Any]:
        eccezione = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            eccezione is not None
            and int(eccezione.get("offerta_id") or 0) == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione offerta non trovata.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        componente = self._repo.get_componente(componente_id)
        ErrorManager.require(
            componente is not None
            and int(componente.get("eccezione_offerta_id") or 0) == eccezione_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente non trovato sull'eccezione.",
            context={
                "eccezione_id": eccezione_id,
                "componente_id": componente_id,
            },
        )
        assert componente is not None
        return componente

    # Scopo: Cancella un'eccezione. Solo se offerta in BOZZA.
    def elimina_eccezione(self, offerta_id: int, eccezione_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        # «Solo in bozza» lo dice il DB (`trgfn_doc_righe_lock_fuori_bozza` su
        # eccezioni e componenti, `E_RIGA_DOC_NON_BOZZA`, 409): qui l'esistenza.
        self._get_offerta_or_raise(offerta_id, op="righe", getter=self._repo.get_stato_codice)
        riga_del_padre_o_not_found(
            self._repo.get_eccezione, eccezione_id,
            padre_id=offerta_id, chiave_padre="offerta_id",
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            function_name="vendite.offerte_service.elimina_eccezione",
        )
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                self._repo.delete_eccezione(eccezione_id)

    # =================================================================
    # Utility 1:1 (solo in BOZZA per write)
    # =================================================================

    # Scopo: Legge il record utility 1:1 di un'offerta (read libero).
    def get_utility(self, offerta_id: int) -> dict[str, Any] | None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="get_utility", getter=self._repo.get_stato_codice)
        return self._repo.get_utility(offerta_id)

    # Scopo: Crea il record utility 1:1. UNIQUE su offerta_id: doppio create
    #        rilevato e mappato a E_VENDITE_DUPLICATO. Lo stato lo giudica il
    #        DB (vedi `aggiorna_offerta`).
    def crea_utility(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=CREATE_KEYS_UTILITY)
        payload = self._con_meta_normalizzato(payload)
        self._get_offerta_or_raise(offerta_id, op="crea_utility", getter=self._repo.get_stato_codice)
        for required in ("istanza_utility_id", "utility_id"):
            ErrorManager.require(
                required in payload and payload[required] is not None,
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.create_utility(offerta_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # Scopo: Aggiorna il record utility (campi business). Lo stato lo giudica
    #        il DB (vedi `aggiorna_offerta`). Payload vuoto -> 400 (no-op
    #        silenzioso evitato).
    def aggiorna_utility(
        self, offerta_id: int, utility_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(utility_id, field="utility_id")
        self._v.validate_allowed_keys(payload, allowed=UPDATE_KEYS_UTILITY)
        payload = self._con_meta_normalizzato(payload)
        self._v.require_campi_da_aggiornare(
            payload, context={"op": "aggiorna_utility"}, log_to_db=False,
        )
        self._get_offerta_or_raise(offerta_id, op="aggiorna_utility", getter=self._repo.get_stato_codice)
        existing = self._repo.get_utility(offerta_id)
        ErrorManager.require(
            existing is not None and existing.get("id") == utility_id,
            code=E_VENDITE_NOT_FOUND,
            message="Record utility non trovato per questa offerta.",
            context={"offerta_id": offerta_id, "utility_id": utility_id},
        )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.update_utility(utility_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # =================================================================
    # Helper interni
    # =================================================================

    # Scopo: Normalizza `meta` (se presente) con il BB `optional_meta`:
    #        oggetto JSON (dict, o stringa che ne contiene uno) -> dict,
    #        `null` -> `{}`, qualunque altra cosa -> 400 E_VENDITE_VALIDATION.
    #        Ritorna una COPIA del payload (il chiamante non vede la mutazione).
    # ⭐ 2026-09-26, migrazione delle scritture sul BB core. Fino a quel giorno
    #    il `meta` del client arrivava al repository COSI' COM'ERA e
    #    `to_write_param` lo passava a `json.dumps`: una stringa diventava uno
    #    SCALARE stringa jsonb, un numero un numero — su una colonna che il
    #    modello vuole oggetto (`NOT NULL DEFAULT '{}'` su tutte e tre le
    #    tabelle), e che il gate prezzo rilegge come dict. E `null` arrivava
    #    come NULL contro il NOT NULL (errore DB generico). Ora la regola e'
    #    quella di contratti/promo: un oggetto o un 400 parlante, `null` =
    #    reset a `{}`.
    def _con_meta_normalizzato(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "meta" not in payload:
            return payload
        return {**payload, "meta": self._v.optional_meta(payload)}

    # Scopo: Verifica che l'offerta esista e sia in uno degli stati attesi.
    #        Solleva 404 se offerta inesistente, 400 se stato fuori scope.
    #        ⚠️ Solo per l'eliminazione (`_STATI_EDITABILI`): i passaggi di
    #        stato li giudica il DB, e non si torna a ripeterli qui.
    def _assert_stato_corrente(
        self, offerta_id: int, *, expected: set[str] | frozenset[str]
    ) -> str:
        stato = self._get_offerta_or_raise(offerta_id, op="_assert_stato_corrente", getter=self._repo.get_stato_codice)
        ErrorManager.require(
            stato in expected,
            code=E_VENDITE_VALIDATION,
            message=(
                "Operazione non consentita: stato corrente "
                f"'{stato}', atteso uno tra {sorted(expected)}."
            ),
            context={
                "offerta_id": offerta_id,
                "stato_corrente": stato,
                "stati_attesi": sorted(expected),
            },
        )
        return stato

    # Scopo: La motivazione dal corpo della richiesta: una stringa o niente
    #        (assente, null o vuota = None). Solo la FORMA: un non-stringa e' un
    #        400 col campo, non un 500 dal cast del DB. Se serve lo dice il verbo.
    def _motivazione(self, valore: Any) -> str | None:
        return self._v.optional_string(
            {_CAMPO_MOTIVAZIONE: valore}, _CAMPO_MOTIVAZIONE,
            function_name="offerte_service._motivazione",
        )

    # Scopo: Un cambio di stato manuale dal verbo `vendite.fn_cambia_stato_offerta`
    #        (§13.6 punti 1-2), nella transazione del chiamante se c'e' (la
    #        factory di «Emetti» ci mette il PDF). Perimetro, stato di
    #        partenza, permesso del passaggio, motivazione e condizioni li
    #        giudica il DB.
    #        ⭐ L'esistenza col lettore leggero, come in `annulla`, revisione e
    #        push (e nel cambio stato del contratto): l'offerta che non c'e' e'
    #        UN codice, `E_VENDITE_NOT_FOUND`, da ogni rotta del service. Il
    #        verbo la ricontrolla nel perimetro (E_OFFERTA_NON_TROVATA), ma a
    #        quel punto e' solo la difesa del DB.
    #        ⛔ Fino al 2026-10-26 era `_cambia_stato_manuale`: uno stato di
    #        partenza scritto in Python (`expected_from`), l'id dello stato dal
    #        lettore e un UPDATE diretto (`update_stato`), che la porta ora
    #        rifiuta (E_DOC_STATO_SOLO_DAL_VERBO).
    def _cambia_stato(
        self, offerta_id: int, *, stato_codice: str, motivazione: str | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._get_offerta_or_raise(offerta_id, op="_cambia_stato", getter=self._repo.get_stato_codice)
        with self._db_errors(
            {"offerta_id": offerta_id, "stato_codice": stato_codice},
            fallback_message="Cambio stato offerta non consentito.",
        ):
            with transaction.atomic():
                self._repo.cambia_stato(offerta_id, stato_codice, motivazione)
        return self.get_offerta(offerta_id)


# ══════════════════════════════════════════════════════════
# Pricing riga offerta + gate L1/L2/L3 (module-level)
# ══════════════════════════════════════════════════════════
# Speculari a `contratti_service.contratti_suggerisci_prezzo_riga` +
# `resolve_or_check_override_prezzo_riga_contratto` (refactor 2026-06-01: gate
# prezzi sulle offerte, simmetria col contratto). Esposte module-level perche'
# `resolver_fn` del BB `_pricing_gate_helpers.resolve_or_check_override_prezzo`
# attende la signature `(documento_id, *, articolo_id, uom_id, auth_user_id)`.


# Scopo: Risolve il contesto di pricing per un'offerta: testata + emittente +
#        BA/utility/data + listino_versione preferita. Mirror di
#        `contratti_service._load_contratto_context_for_pricing` (offerta usa
#        `validita_dal` come data di riferimento e `codice` come numero doc).
def _load_offerta_context_for_pricing(
    offerta_id: int,
    auth_user_id: int | None,
    *,
    function_name: str,
    repo: OfferteRepository | None = None,
) -> dict[str, Any]:
    if repo is None:
        repo = OfferteRepository()
    testata = testata_o_not_found(
        repo.get_offerta, offerta_id,
        code=E_VENDITE_NOT_FOUND, message="Offerta non trovata.",
        id_name="offerta_id", function_name=function_name,
    )

    ba_id_raw = testata.get("billing_account_id")
    ErrorManager.require(
        ba_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    validita_dal_raw = testata.get("validita_dal")
    ErrorManager.require(
        validita_dal_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Offerta senza validita_dal: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert validita_dal_raw is not None
    data_riferimento = (
        validita_dal_raw if isinstance(validita_dal_raw, date)
        else date.fromisoformat(str(validita_dal_raw))
    )

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

    # Fast path CONTRATTO_LISTINO via `listino_versione_id_preferito` (come
    # contratti). La versione la dice il DB, con la regola che governa le righe
    # a video e che congela all'emissione: la fissata, altrimenti quella in
    # vigore oggi (`vendite.fn_documento_listino_operativo`).
    listino_versione_id_preferito = listino_versione_operativa(SORGENTE_OFFERTA_COMMERCIALE, offerta_id)

    assert ba_id_raw is not None and utility_id_raw is not None
    return {
        "testata": testata,
        "ba_id": int(ba_id_raw),
        "utility_id": int(utility_id_raw),
        "emittente_sr_id": emittente_sr_id,
        "data_riferimento": data_riferimento,
        "listino_versione_id_preferito": listino_versione_id_preferito,
    }


# Scopo: Suggerisce il prezzo unitario per una riga (eccezione) offerta.
#        `resolver_fn` per il BB gate. Mirror di
#        `contratti_suggerisci_prezzo_riga`.
def offerta_suggerisci_prezzo_riga(
    offerta_id: int,
    *,
    articolo_id: str,
    uom_id: int,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = "offerte_service.offerta_suggerisci_prezzo_riga"
    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code=E_VENDITE_VALIDATION,
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    guard_uom_id_positive(
        uom_id, error_code=E_VENDITE_VALIDATION, function_name=function_name,
    )

    ctx = _load_offerta_context_for_pricing(
        offerta_id, auth_user_id, function_name=function_name,
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
    # con contratti/preventivi).
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Thin wrapper sul BB `resolve_or_check_override_prezzo` per le eccezioni
#        offerta. Mirror di `resolve_or_check_override_prezzo_riga_contratto`.
#        Normalizza la testata aliasando `data`←`validita_dal` (il BB usa
#        `testata["data"]` nel guard skip-context). Skip gate se l'offerta
#        e' senza listino (per coerenza col contratto, anche se sull'offerta
#        `listino_id` e' obbligatorio).
def resolve_or_check_override_prezzo_riga_offerta(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    if testata.get("listino_id") is None:
        return payload_prezzo, None

    testata_normalized = (
        testata if testata.get("data") is not None
        else {**testata, "data": testata.get("validita_dal")}
    )
    return resolve_or_check_override_prezzo(
        testata=testata_normalized,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=offerta_suggerisci_prezzo_riga,
        error_code_validazione=E_VENDITE_VALIDATION,
        richiesta_approvazione=richiesta_approvazione,
    )


# Scopo: orchestratore L3 per le eccezioni offerta. Mirror di
#        `contratti_service._orchestrate_l3_request_contratto`. Crea la pratica
#        APPROVAZIONE_PREZZO via `crea_richiesta_approvazione_offerta`,
#        opzionalmente collega riga_id (update: noto subito; create: link
#        post-INSERT). Ritorna pratica_id.
def _orchestrate_l3_request_offerta(
    *,
    offerta_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione_offerta,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione_offerta(
        offerta_id=offerta_id,
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
            sorgente=META_SORGENTE_OFFERTA,
        )
    return pratica_id


# ══════════════════════════════════════════════════════════
#  Indirizzi documento (BB condiviso _indirizzi_documento_helpers)
# ══════════════════════════════════════════════════════════

_INDIRIZZI_CFG = IndirizziDocumentoConfig(
    # lambda (non la classe): risolve il nome a call-time, cosi' i @patch
    # dei test unit raggiungono il repository.
    repo_factory=lambda: OfferteRepository(),
    not_found_code=E_VENDITE_NOT_FOUND,
    error_code=E_VENDITE_VALIDATION,
    fn_prefix="vendite.offerte_service",
)


# Scopo: Pannello indirizzi dell'offerta (ambito OFFERTE). Guard di esistenza
#        e traduzione errori DB nel BB condiviso.
def list_indirizzi(offerta_id: int) -> dict[str, Any]:
    return list_indirizzi_documento(_INDIRIZZI_CFG, offerta_id)


# Scopo: Upsert slot indirizzo (uno-per-tipo, solo BOZZA).
def upsert_indirizzo(offerta_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return upsert_indirizzo_documento(_INDIRIZZI_CFG, offerta_id, payload)


# Scopo: Rimozione slot indirizzo (solo BOZZA).
def delete_indirizzo(offerta_id: int, indirizzo_id: int) -> dict[str, Any]:
    return delete_indirizzo_documento(_INDIRIZZI_CFG, offerta_id, indirizzo_id)
