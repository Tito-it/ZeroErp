# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione emittenti fiscali (ruolo EF).
#        Orchestrazione creazione (ruolo EF + insert) in transazione atomica.
#        CRUD, lista paginata, update. Riservato ad amministratori.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.api.constants import DEFAULT_LIMIT
from apps.anagrafiche.db.emittenti_fiscali_repository import (
    EMITTENTE_UPDATE_ALLOWED,
    UTILITIES_PARAMETRI,
    UTILITIES_UPDATE_ALLOWED,
    EmittentiFiscaliBillingAccountRepository,
    EmittentiFiscaliRepository,
    EmittentiFiscaliUtilitiesRepository,
)
from apps.anagrafiche.error_codes import E_ANAG_FK, E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import (
    CAMPO_REGIME_FISCALE,
    create_with_constraint_mapping,
    extract_optional_fields,
    require_found,
    regime_nel_catalogo,
    require_str,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.non_editable_fields_helper import (
    compute_non_editable_fields,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    translate_db_errors,
)


# Contratti delle PATCH, validati QUI con 400 `E_ANAG_VALIDAZIONE` (2026-09-26):
# dal passaggio ai BB di scrittura il repository rifiuta con `RuntimeError`
# (500) ogni colonna fuori whitelist — fino a quel giorno la scartava in
# silenzio. Partono dalle colonne scrivibili del repository.
# ⚠️ `codice` NON c'e': e' immutabile (trigger `lock_columns`). Fino al
#    2026-09-26 una PATCH che lo portava veniva accettata e il campo ignorato;
#    ora e' un 400 che lo nomina.
_UPDATE_EMITTENTE_KEYS: frozenset[str] = EMITTENTE_UPDATE_ALLOWED
# Le chiavi della CREAZIONE: quelle che `crea_emittente` legge (il drawer manda
# solo queste, verificato il 2026-10-21).
_CREA_EMITTENTE_KEYS: frozenset[str] = frozenset({
    "soggetto_id", "codice", "valuta_id", "attivo", "bollo_auto",
    "regime_fiscale_rf", "rounding_policy", "bollo_soglia",
})
_UPDATE_UTILITY_KEYS: frozenset[str] = UTILITIES_UPDATE_ALLOWED
# L'attivazione: l'utility e, facoltativi, i parametri. ⛔ `attivo` non c'e'
# piu' (D-U-11): una POST o una PATCH che lo porta e' un 400 che lo nomina.
_CREA_UTILITY_KEYS: frozenset[str] = UTILITIES_PARAMETRI | {"utility_id"}

# Validator stateless del dominio (solo il codice errore): condivisibile.
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

# Il regime fiscale dell'emittente (brief-db-esigibilita-iva-per-cassa-emittente,
# 2026-10-01): NOT NULL con default RF01 e FK al catalogo `config.regimi_fiscali`.
# Il codice fuori catalogo lo traduce il BB `regime_nel_catalogo` (_validators).
_CAMPO_REGIME = CAMPO_REGIME_FISCALE
_FK_REGIME = "fk_emittenti_fiscali_regimi_fiscali"


# Scopo: Dice se il payload DICHIARA il regime fiscale, e ne rifiuta il vuoto.
#        ⭐ Dichiarare il regime e' confermarlo: chi lo porta nel payload lo ha
#        scelto, e la conferma (data e autore) la deriva il database da ogni
#        UPDATE che nomina il regime (§10 del brief, applicato il 2026-10-02).
#        ⛔ Il vuoto e il `null` NON significano «lascia stare»: sono un 400
#        sul campo. Fino al 2026-10-01 diventavano NULL, e con la colonna NOT
#        NULL sarebbero stati un 23502 — in creazione, peggio, un vuoto veniva
#        omesso in silenzio e l'emittente nasceva RF01 come se nessuno avesse
#        scritto niente. Chi non vuole dichiarare il regime NON manda la chiave.
def _regime_dichiarato(payload: dict[str, Any]) -> bool:
    if _CAMPO_REGIME not in payload:
        return False
    valore = payload[_CAMPO_REGIME]
    ErrorManager.require(
        isinstance(valore, str) and bool(valore.strip()),
        code=E_ANAG_VALIDAZIONE,
        message="Regime fiscale obbligatorio: scegliere un codice dal catalogo.",
        context={"field": _CAMPO_REGIME},
    )
    return True


class EmittentiFiscaliService:
    """Service per gestione emittenti fiscali (Amm. Software)."""

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata emittenti fiscali.
    def list_emittenti_fiscali(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_emittenti_fiscali(**params)

    # Scopo: Dettaglio completo di un emittente fiscale.
    #        Arricchito con `non_editable_fields` (Fase 4 — A9):
    #        il FE costruisce il drawer di edit usando questi metadata,
    #        coerente con altre matrici amm-software.
    def get_emittente(self, emittente_id: int) -> dict[str, Any]:
        emittente = require_found(
            self._repo.get_emittente(emittente_id), "Emittente fiscale non trovato.")
        emittente["non_editable_fields"] = self.get_non_editable_fields()
        return emittente

    # Scopo: Lista `non_editable_fields` per anagrafica emittente (Fase 4 — A9).
    # ⭐ Tutta dal DB, senza gap: `codice` (E_CODICE_NON_MODIFICABILE) e
    #        `soggetto_ruolo_id` (E_EMITTENTE_SOGGETTO_IMMUTABILE, dal
    #        2026-11-21) li blocca il trigger di lock e la vista li elenca.
    #        Fino a quel giorno qui c'era il gap `soggetto_id`: nominava un
    #        campo del payload (l'emittente non ha quella colonna) per una
    #        regola che il DB non garantiva.
    def get_non_editable_fields(self) -> list[str]:
        return compute_non_editable_fields("anagrafiche", "emittenti_fiscali")

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea un emittente fiscale completo in una transazione atomica.
    #        Obiettivo: associa il soggetto al ruolo EF e crea il record emittente.
    #        Perimetro: validazione soggetto_id (con P.IVA obbligatoria) e codice,
    #        get_or_create ruolo, insert emittente con campi opzionali.
    #        Risultato: dict con id dell'emittente e soggetto_ruolo_id.
    #        Nota: il primo emittente creato attiva il trigger default_bootstrap che
    #        popola automaticamente il default mapping in emittenti_fiscali_billing_account.
    def crea_emittente(self, payload: dict[str, Any]) -> dict[str, Any]:
        # ⛔ Una chiave fuori contratto e' un 400, come nella PATCH: fino al
        #    2026-10-21 la creazione la scartava in silenzio
        #    (brief-be-verifica-documentazione-api §B2, regola di api.md).
        _V.validate_allowed_keys(
            payload, allowed=_CREA_EMITTENTE_KEYS, message="Payload emittente fiscale non valido.",
        )
        soggetto_id = _V.optional_uuid(payload, "soggetto_id")
        ErrorManager.require(
            soggetto_id is not None,
            code=E_ANAG_VALIDAZIONE,
            message="soggetto_id obbligatorio.",
        )
        assert soggetto_id is not None
        soggetto_id = str(soggetto_id)

        # Validazione P.IVA del soggetto: requisito legale per emissione fatture
        # tramite SDI. Un soggetto privato (solo CF) non puo' essere emittente fiscale.
        partita_iva = self._repo.get_soggetto_partita_iva(soggetto_id)
        ErrorManager.require(
            bool(partita_iva),
            code=E_ANAG_VALIDAZIONE,
            message="L'emittente fiscale richiede un soggetto con Partita IVA.",
        )

        # Campi obbligatori dell'emittente. `descrizione` non c'e' piu' dal
        # 2026-08-02 (DROP `20260802-22`): il nome dell'emittente e' la ragione
        # sociale del soggetto scelto sopra, non un testo digitato a parte
        # (brief `brief-emittente-ragione-sociale-dal-soggetto.md`).
        codice = require_str(payload, "codice", "Codice emittente obbligatorio.")

        # Il regime: dichiarato = scelto e confermato; assente = default DB RF01,
        # NON confermato (l'emittente entra nel presidio dei regimi da confermare).
        # Qui si rifiuta solo il vuoto: la conferma la fa la madre del DB.
        _regime_dichiarato(payload)

        # Campi opzionali (incluso attivo se passato dal payload, default DB true)
        emittente_data = self._extract_emittente_data(payload)

        # ⭐ Una madre sola (2026-10-18, 2b-2): ruolo EF, riga e conferma del
        #    regime dichiarato in un'istruzione, `fn_crea_emittente_fiscale`.
        #    Restano qui il pre-check della partita IVA (sopra) e la traduzione
        #    dei vincoli per nome.
        with regime_nel_catalogo(_FK_REGIME):
            emittente_id, soggetto_ruolo_id = create_with_constraint_mapping(
                lambda: self._repo.crea_emittente_fiscale(soggetto_id, codice, emittente_data),
                {
                    "uq_emittenti_fiscali_ruolo": "Esiste gia' un emittente fiscale per questo soggetto.",
                    "uq:codice": "Esiste gia' un emittente fiscale con questo codice.",
                },
            )

        return {
            "id": emittente_id,
            "soggetto_ruolo_id": soggetto_ruolo_id,
        }

    # Scopo: Estrae i campi opzionali dell'emittente dal payload.
    def _extract_emittente_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        # bool a None = "non fornito" → lasciar usare il default DB.
        return extract_optional_fields(
            payload,
            ints=("valuta_id",),
            bools=("attivo", "bollo_auto"),
            strings=("regime_fiscale_rf", "rounding_policy"),
            numeric=("bollo_soglia",),
        )

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Scopo: Aggiorna campi editabili dell'emittente fiscale.
    #        Il campo codice e' bloccato dal trigger DB: in PATCH e' rifiutato
    #        (400) dal contratto `_UPDATE_EMITTENTE_KEYS`, come ogni chiave ignota.
    #        ⭐ Una PATCH che porta `regime_fiscale_rf` lo CONFERMA, anche se il
    #        valore e' lo stesso di prima: e' cosi' che l'operatore conferma un
    #        regime che nessuno aveva dichiarato. Chi non tocca il regime
    #        non manda la chiave. Data e autore della conferma non sono chiavi
    #        del contratto: li deriva il database (§10 del brief).
    def update_emittente(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_EMITTENTE_KEYS,
            message="Payload emittente fiscale non valido.",
        )
        _regime_dichiarato(payload)
        # Verifica che l'emittente esista
        self.get_emittente(emittente_id)
        # Un PATCH vuoto e' un 400, non il 404 che dava il rowcount (2026-10-14).
        _V.require_campi_da_aggiornare(payload)
        # Copia difensiva: il repo normalizza stringhe vuote -> None e non deve mutare
        # request.data della view (che potrebbe essere riusato dal middleware di logging).
        with regime_nel_catalogo(_FK_REGIME):
            updated = self._repo.update_emittente(emittente_id, dict(payload))
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Emittente fiscale non trovato.",
        )
        return {"updated": True}

    # =================================================================
    # Helper interno: risolve emittente_id -> soggetto_ruolo_id (con guard)
    # =================================================================

    # Scopo: Risolve il soggetto_ruolo_id partendo dall'emittente_id.
    #        Usato dai metodi sub-resource (BA mapping, utilities) per validare
    #        l'esistenza dell'emittente padre prima di operare sui figli.
    def _resolve_soggetto_ruolo_id(self, emittente_id: int) -> int:
        soggetto_ruolo_id = self._repo.get_soggetto_ruolo_id(emittente_id)
        ErrorManager.require(
            soggetto_ruolo_id is not None,
            code=E_ANAG_NOT_FOUND,
            message="Emittente fiscale non trovato.",
        )
        assert soggetto_ruolo_id is not None
        return soggetto_ruolo_id


# Scopo: Helper condiviso per i sub-resource service. Risolve il soggetto_ruolo_id
#        del padre e verifica che il record figlio appartenga effettivamente al padre.
#        Solleva ServiceError E_ANAG_NOT_FOUND in entrambi i casi mancanti.
#        Estratto per evitare duplicazione in aggiorna_record/elimina_record.
def _verify_record_ownership(parent_service, repo, emittente_id, record_id, not_found_message):
    soggetto_ruolo_id = parent_service._resolve_soggetto_ruolo_id(emittente_id)
    ErrorManager.require(
        repo.belongs_to_emittente(record_id, soggetto_ruolo_id),
        code=E_ANAG_NOT_FOUND,
        message=not_found_message,
    )
    return soggetto_ruolo_id


# =================================================================
# Service Mapping BA -> emittente fiscale
# =================================================================


class EmittentiFiscaliBillingAccountService:
    """Service per mapping BA -> emittente fiscale.

    Endpoint sub-resource montati sotto un emittente padre. Usa
    EmittentiFiscaliService._resolve_soggetto_ruolo_id per validare
    l'esistenza dell'emittente padre prima di ogni operazione.
    """

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliBillingAccountRepository()
        self._parent = EmittentiFiscaliService()

    # Scopo: Lista paginata dei collegamenti BA di un emittente, con search,
    #        IN CONSULTAZIONE (D-T4-3; Tid, brief-db-revisione-anagrafiche §26.2,
    #        2026-11-27). ⛔ Niente piu' `can_remove` e motivo per riga: fino a
    #        quel giorno la riga portava l'esito di
    #        `script.fn_check_ba_cambio_emittente` per il cestino; dal giro 6
    #        nessun collegamento si toglie (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`),
    #        e il cestino non c'e' piu'.
    def list_mapping(
        self,
        emittente_id: int,
        *,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "billing_account_codice",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        rows, total = self._repo.list_by_emittente(
            soggetto_ruolo_id,
            search=search,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )
        return rows, total

    # Scopo: Rende l'emittente l'azienda PREDEFINITA, in cui nascono i clienti
    #        creati senza sessione (la riga `billing_account_id` NULL si sposta
    #        qui). Payload VUOTO: un `billing_account_id` e' un 400 che lo nomina,
    #        perche' ogni BA nasce col suo collegamento a un'azienda e non lo
    #        perde (D-T4-3, giro 6 di brief-db-revisione-anagrafiche; la scheda
    #        dei BA e' in sola consultazione, Tid §26.2, 2026-11-27).
    def imposta_predefinita(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=frozenset(),
            message="Da qui si sceglie solo l'azienda predefinita: un cliente nasce gia' collegato alla sua.",
        )
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        riga_id = self._repo.imposta_predefinita(soggetto_ruolo_id)
        # La predefinita manca solo se una via di servizio ha spento i rifiuti
        # del DB: si dice, non si ricrea (vedi il repository).
        ErrorManager.require(
            riga_id is not None,
            code="E_EMITTENTE_DEFAULT_MISSING",
            message="Emittente fiscale default non configurato.",
        )
        return {
            "id": riga_id,
            "emittente_id": emittente_id,
            "billing_account_id": None,
            "is_default": True,
        }

    # Scopo: Riepilogo mapping BA dell'emittente (has_default + count_specifici).
    #        Esposto al FE come bypass della dipendenza dalla pagina corrente:
    #        senza summary, il check "esiste gia' un default" puo' fallire se
    #        il record default non e' nella pagina visualizzata.
    def summary_mapping(self, emittente_id: int) -> dict[str, Any]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        return self._repo.summary_by_emittente(soggetto_ruolo_id)


# =================================================================
# Service Utilities per emittente fiscale
# =================================================================


# Vincoli di `anagrafiche.emittenti_fiscali_utilities`, tradotti in errori
# parlanti (R-2 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3).
#
# ⚠️ Prima di questa mappa OGNI IntegrityError della tabella passava da
# `create_with_dedup` e usciva come «esiste gia' un record per questa coppia»:
# non un messaggio povero, un messaggio FALSO — chi sbagliava le soglie leggeva
# di un duplicato che non c'era. E sul percorso di UPDATE non c'era nessuna
# traduzione, quindi la stessa violazione diventava un 500.
#
# ⚠️ Nessuna delle due voci sulle soglie dichiara un CAMPO, ed e' voluto: i due
# vincoli guardano la COPPIA (min, max), che l'operatore compila per intero.
# Accendere uno solo dei due input manderebbe a correggere meta' delle volte il
# campo giusto — peggio che non accenderne nessuno (regola di `map_integrity_error`).
_UTILITY_UNIQUE_CONSTRAINTS: dict[str, tuple] = {
    "uq_emittenti_fiscali_utilities_emittente_utility": (
        "E_ANAG_DUPLICATO",
        "Esiste gia' un record utility per questa coppia (emittente, utility).",
    ),
}

_UTILITY_CHECK_CONSTRAINTS: dict[str, tuple] = {
    # D-0: le due soglie si dichiarano INSIEME. Entrambe vuote = meccanismo del
    # fondo fattura spento; entrambe piene = attivo sulla banda; una sola =
    # errore di configurazione, perche' non spegne il meccanismo ma lo spalanca.
    "chk_emittenti_fiscali_utilities_soglie_coppia": (
        "E_FONDO_SOGLIE_INCOMPLETE",
        "Le due soglie del minimo si dichiarano insieme: valorizzare sia la "
        "soglia minima sia la massima, oppure lasciarle entrambe vuote "
        "(fondo fattura non attivo su questa utility).",
    ),
    # Vincolo storico e distinto: presidia l'ORDINE delle due soglie.
    "chk_emittenti_fiscali_utilities_soglie": (
        E_ANAG_VALIDAZIONE,
        "Soglie del minimo incoerenti: la soglia minima non puo' superare la massima.",
    ),
    # ⭐ I due CHECK dell'arrotondamento (2026-10-31): fino a quel giorno
    #    cadevano sul ripiego «Dati del record utility non validi.», che non
    #    dice cosa correggere — e il FE ammetteva decimali fino a 6 contro i 2
    #    del vincolo. Un campo solo per vincolo, quindi il campo si dichiara.
    # ⛔ L'intervallo NON e' scritto nel messaggio: sta nel CHECK, e un numero
    #    ricopiato qui diverge in silenzio al primo cambio del vincolo.
    "chk_emittenti_fiscali_utilities_arrotondamento_dec": (
        E_ANAG_VALIDAZIONE,
        "Decimali di arrotondamento degli importi fuori dall'intervallo ammesso.",
        "arrotondamento_importi_dec",
    ),
    "chk_emittenti_fiscali_utilities_metodo_arrotondamento": (
        E_ANAG_VALIDAZIONE,
        "Metodo di arrotondamento degli importi non ammesso.",
        "metodo_arrotondamento_importi",
    ),
    # D-U-11 (2026-11-27): la riga non ha uno stato suo, e' sempre accesa. Il
    # BE non scrive piu' `attivo`: la voce copre un chiamante che lo scrivesse.
    "chk_emittenti_fiscali_utilities_attivo": (
        E_ANAG_VALIDAZIONE,
        "Un'utility dell'azienda non si spegne: si toglie all'azienda, "
        "se nessun billing account e nessun documento la usa.",
    ),
}

# ⭐ La riga tolta mentre qualcuno la usa (D-U-9, D-U-12). Le FK composte
# verso (emittente_soggetto_ruolo_id, utility_id) stanno sui FIGLI: il nome
# che il DB riporta alla cancellazione e' quello della FK del figlio. Sono
# DIFFERITE, e il rifiuto arriva alla fine dell'istruzione perche' il backend
# gira in autocommit (`ATOMIC_REQUESTS` spento, api.md §Atomicita'): dentro un
# `transaction.atomic()` arriverebbe al COMMIT, fuori da questa traduzione.
# Presidio sul DB vero: test_emittente_utility_gestita_db.
_MSG_UTILITY_IN_USO = (
    "L'utility e' usata da billing account o documenti di questa azienda: "
    "non si puo' togliere."
)
_UTILITY_FK_CONSTRAINTS: dict[str, tuple] = dict.fromkeys(
    (
        "fk_emittenti_fiscali_ba_utility_gestita",
        "fk_categorie_clienti_listini_utility_gestita",
        "fk_listini_utility_gestita",
        "fk_commesse_utility_gestita",
        "fk_fatture_utility_gestita",
        "fk_registri_fatturazione_utility_gestita",
        "fk_fatturazione_lotti_utility_gestita",
    ),
    (E_ANAG_FK, _MSG_UTILITY_IN_USO),
)


# Scopo: I parametri d'importo PRESENTI nel payload, col tipo verificato, per
#        l'attivazione (POST) e per la modifica (PATCH, delta): un campo
#        assente non si scrive; null o la stringa vuota = NULL («vale la
#        policy dell'azienda o il sistema»). L'intervallo dei decimali, il
#        metodo ammesso e la coppia delle soglie li giudicano i CHECK del DB,
#        tradotti col campo da `_UTILITY_CHECK_CONSTRAINTS`.
# ⭐ 2026-11-28 (/verifica): fino a quel giorno i valori passavano grezzi al
#    DB, e un `"abc"` nei decimali usciva col testo di PostgreSQL
#    («invalid input syntax…») senza il campo; la POST li validava prima che i
#    parametri diventassero facoltativi, la PATCH mai.
def _parametri_utility(payload: dict[str, Any]) -> dict[str, Any]:
    letti: dict[str, Any] = {}
    for campo in UTILITIES_PARAMETRI & payload.keys():
        valore = payload[campo]
        if isinstance(valore, str) and not valore.strip():
            valore = None
        uno = {campo: valore}
        if campo == "arrotondamento_importi_dec":
            letti[campo] = _V.optional_smallint(uno, campo)
        elif campo == "metodo_arrotondamento_importi":
            letti[campo] = _V.optional_string(uno, campo)
        else:
            letti[campo] = _V.optional_decimal(uno, campo)
    return letti


class EmittentiFiscaliUtilitiesService:
    """Le utility che un'azienda (emittente fiscale) gestisce, coi parametri.

    Sub-resource montato sotto un emittente padre, solo SUPER_ADMIN
    (`AdminAPIView`, D-U-5). Attivare = inserire la riga; i parametri si
    modificano sulla riga, e «togliere i parametri» li riporta a NULL;
    disattivare = cancellare la riga, ammesso solo senza billing account ne'
    documenti (brief-db-utility-gestite-dall-emittente §10 R-3).
    """

    def __init__(self) -> None:
        self._repo = EmittentiFiscaliUtilitiesRepository()
        self._parent = EmittentiFiscaliService()

    # Scopo: Le utility dell'azienda (tutte quelle attivabili), con le
    #        capability della riga:
    #          - `can_attivare`: l'azienda non la gestisce e l'emittente e'
    #            acceso (sotto un emittente spento non nasce niente)
    #          - `can_update`: la riga c'e' (si scrivono i parametri)
    #          - `can_reset`: la riga ha parametri suoi (si riportano a NULL)
    #          - `can_remove`: la riga c'e'. Se un billing account o un
    #            documento la usa, il DB rifiuta: la capability non lo
    #            anticipa, una copia della regola divergerebbe (regola del 2)
    #        L'autorita' resta il DB.
    def list_records(self, emittente_id: int) -> list[dict[str, Any]]:
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        emittente = self._parent._repo.get_emittente(emittente_id)
        emittente_attivo = bool(emittente and emittente.get("attivo"))

        rows = self._repo.list_by_emittente(soggetto_ruolo_id)
        for row in rows:
            ha_riga = row.get("record_id") is not None
            row["can_attivare"] = (not ha_riga) and emittente_attivo
            row["can_update"] = ha_riga
            row["can_reset"] = ha_riga and bool(row.get("personalizzata"))
            row["can_remove"] = ha_riga
        return rows

    # Scopo: Attiva l'utility per l'azienda: `utility_id` obbligatorio, i
    #        parametri facoltativi (D-U-1: la riga presente e' l'elenco, i
    #        parametri restano opzionali).
    def crea_record(self, emittente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_CREA_UTILITY_KEYS,
            message="Payload record utility non valido.",
        )
        soggetto_ruolo_id = self._parent._resolve_soggetto_ruolo_id(emittente_id)
        utility_id = _V.optional_int(payload, "utility_id")
        ErrorManager.require(
            utility_id is not None,
            code=E_ANAG_VALIDAZIONE,
            message="utility_id obbligatorio.",
        )
        assert utility_id is not None
        parametri = _parametri_utility(payload)

        # Non `create_with_dedup`: la tabella ha piu' CHECK oltre alla UNIQUE,
        # e ricondurli tutti a «duplicato» diceva una cosa falsa (vedi la mappa).
        with self._vincoli_tradotti(utility_id=utility_id):
            record_id = self._repo.create_record(
                emittente_soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
                parametri=parametri,
            )
        return {"id": record_id}

    # Scopo: Traduce le violazioni DB della tabella in errori di dominio
    #        parlanti, delegando al BB `translate_db_errors` (che oltre agli
    #        IntegrityError copre anche i RAISE P0001 di trigger/fn — un ramo
    #        che una copia locale perderebbe).
    #        ⚠️ Vale su ENTRAMBI i percorsi (create e update): l'update e' un
    #        delta, quindi la coppia di soglie effettiva nasce dall'unione del
    #        payload con la riga gia' a database — solo il CHECK la conosce,
    #        nessuna guard Python sul solo payload potrebbe deciderlo.
    def _vincoli_tradotti(self, **context: Any):
        return translate_db_errors(
            context=context,
            fallback_code=E_ANAG_VALIDAZIONE,
            fallback_message="Dati del record utility non validi.",
            unique_constraints=_UTILITY_UNIQUE_CONSTRAINTS,
            fk_constraints=_UTILITY_FK_CONSTRAINTS,
            check_constraints=_UTILITY_CHECK_CONSTRAINTS,
        )

    # Scopo: Aggiorna un record utility (delta update).
    def aggiorna_record(self, emittente_id: int, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_UTILITY_KEYS,
            message="Payload record utility non valido.",
        )
        _verify_record_ownership(
            self._parent, self._repo, emittente_id, record_id,
            "Record utility non trovato per l'emittente indicato.",
        )
        # Un PATCH vuoto e' un 400, non il 404 che dava il rowcount (2026-10-14).
        _V.require_campi_da_aggiornare(payload)
        with self._vincoli_tradotti(record_id=record_id):
            updated = self._repo.update_record(record_id, _parametri_utility(payload))
        ErrorManager.require(
            updated,
            code=E_ANAG_NOT_FOUND,
            message="Record utility non trovato.",
        )
        return {"updated": True}

    # Scopo: Toglie l'utility all'azienda (D-U-9): rifiutato, col messaggio
    #        della mappa FK, se un billing account o un documento la usa.
    def elimina_record(self, emittente_id: int, record_id: int) -> dict[str, Any]:
        _verify_record_ownership(
            self._parent, self._repo, emittente_id, record_id,
            "Record utility non trovato per l'emittente indicato.",
        )
        with self._vincoli_tradotti(record_id=record_id):
            deleted = self._repo.delete_record(record_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Record utility non trovato.")
        return {"deleted": True}
