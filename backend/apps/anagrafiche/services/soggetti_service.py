# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per gestione soggetti (PF/PG/ENTE).
#        Orchestrazione creazione soggetto + contatto + indirizzo + dati societari
#        in una transazione. I trigger DEFERRED verificano al COMMIT.
#        Ref: docs/it/dev/api.md (sezione Layering)
# ------------------------------------------------------------

from __future__ import annotations

import uuid
from typing import Any

from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db.conti_bancari_repository import ContiBancariRepository
from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository
from apps.anagrafiche.db.soggetti_repository import (
    CONTATTO_UPDATE_COLS,
    INDIRIZZO_RUOLO_UPDATE_COLS,
    SOGGETTO_UPDATE_ALIAS,
    SOGGETTO_UPDATE_COLS,
    SoggettiRepository,
)
from apps.anagrafiche.db.titoli_iva_repository import TitoliIvaRepository
from apps.anagrafiche.error_codes import (
    E_ANAG_NOT_FOUND,
    E_ANAG_VALIDAZIONE,
)
from apps.anagrafiche.services._validators import (
    create_with_constraint_mapping,
    create_with_dedup,
    optional_str,
    require_found,
    require_str,
    update_with_dedup,
)
from apps.anagrafiche.services.cf_validator_it import genera_cf_it, valida_cf_congruenza_it
from apps.anagrafiche.services.geo_service import richiedi_via
from apps.anagrafiche.services.contatti_service import (
    crea_contatto_validato,
    richiedi_contatto_valido,
)
from apps.core.services.payload_helpers import PayloadValidator


# Ruoli che hanno un flusso di creazione proprio, per CODICE INTERNO (la chiave
# stabile, bloccata dal DB): `assign_ruolo` li rifiuta. Cio' che l'utente legge
# (codice e descrizione) viene da `config.tipi_ruoli`, non da qui. Vedi la nota
# su `assign_ruolo`.
_RUOLI_CON_FLUSSO_DEDICATO: frozenset[str] = frozenset({"CL", "FO", "EF", "RIS_UMANA"})

# Limiti lookup contesto pratica (mirror billing_account_service).
_LOOKUP_MIN_QUERY_LENGTH = 2
_LOOKUP_DEFAULT_LIMIT = 20
_LOOKUP_MAX_LIMIT = 50

# Flag di regime fiscale della controparte (I0/D8, 2026-08-29): saliti da
# `anagrafiche.clienti`, che e' una riga PER FORNITURA e ammetteva che lo stesso
# soggetto dichiarasse valori opposti per la stessa partita IVA.
# ⚠️ NON sono un codice IVA e non entrano nel risolutore (D4): non cambiano
#    l'aliquota, cambiano CHI VERSA l'imposta — in fattura elettronica sono
#    l'`EsigibilitaIVA`.
_FLAG_FISCALI_SOGGETTO: tuple[str, ...] = ("split_payment", "cliente_pa")
# Dominio ammesso, speculare al CHECK ('S','N') delle due colonne.
_FLAG_FISCALI_VALORI: frozenset[str] = frozenset({"S", "N"})

# Contratti delle PATCH (chiavi ammesse nel payload), validati QUI con 400
# `E_ANAG_VALIDAZIONE` (2026-09-26): dal passaggio ai BB di scrittura il
# repository rifiuta con `RuntimeError` (500) ogni colonna fuori whitelist, e
# fino a quel giorno la SCARTAVA in silenzio — un salvataggio che «riusciva»
# senza aver scritto il campo. Partono dalle colonne scrivibili del repository:
# oggi coincidono, e un contratto piu' stretto si scrive restringendo qui.
# `dati_societari` (2026-10-10, brief-db-dati-fiscali-e-societari-del-soggetto,
# parte B): una SOTTO-CHIAVE della PATCH, non una colonna di `soggetti`. Va al
# verbo DB `fn_scrivi_dati_societari`, che riceve lo STATO INTERO della sezione.
_CHIAVE_DATI_SOCIETARI = "dati_societari"
_UPDATE_SOGGETTO_KEYS: frozenset[str] = (
    SOGGETTO_UPDATE_COLS | frozenset(SOGGETTO_UPDATE_ALIAS) | {_CHIAVE_DATI_SOCIETARI}
)
# Le chiavi della sezione dati societari: i parametri del verbo, senza il
# soggetto. ⚠️ Stato intero: una chiave ASSENTE vale NULL come una chiave a
# null — il verbo non distingue «non toccare» da «svuota» (B-2, team DB).
_DATI_SOCIETARI_KEYS: frozenset[str] = frozenset({
    "forma_giuridica_id", "id_prov_iscri_rea", "iscrizione_rea", "capitale_sociale",
    "socio_unico", "liquidazione",
    "destinatario_fe", "pec_fatturazione", "codice_sdi",
    "data_costituzione",
})
_MSG_REA_DUPLICATA = "Iscrizione REA gia' presente per un altro soggetto."
_MSG_PG_CF_PIVA_DUPLICATA = "Soggetto PG con CF/PIVA duplicata."
_UPDATE_CONTATTO_KEYS: frozenset[str] = CONTATTO_UPDATE_COLS
_UPDATE_INDIRIZZO_RUOLO_KEYS: frozenset[str] = INDIRIZZO_RUOLO_UPDATE_COLS

# Validator stateless del dominio (solo il codice errore): condivisibile.
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)


# Scopo: UN indirizzo nella forma che le madri del DB ricevono
#        (`fn_crea_indirizzo_soggetto`, `fn_crea_indirizzi_ruolo`, e attraverso
#        lei `fn_crea_fornitore` e `fn_crea_cliente`: la stessa grammatica,
#        `fn_indirizzo_elemento`), coi pre-check per l'operatore: un elemento
#        che non e' un oggetto, i campi di una via nuova (`richiedi_via`). Le
#        stringhe vuote e i null valgono assenti (null_vs_empty). La forma
#        dell'indirizzo LIBERO non si ripete qui: la giudica il guard della
#        tabella (`trgfn_indirizzi_guard_forma_libera`), col campo.
def indirizzo_per_madre(ind: Any) -> dict[str, Any]:
    ErrorManager.require(
        isinstance(ind, dict),
        code=E_ANAG_VALIDAZIONE,
        message="Indirizzo non valido: atteso un oggetto.",
    )
    pulito = {
        k: v for k, v in ind.items()
        if v is not None and not (isinstance(v, str) and not v.strip())
    }
    if not pulito.get("indirizzo_libero") and not pulito.get("indirizzo_dettaglio_id"):
        richiedi_via(pulito)
    return pulito


# Scopo: UN indirizzo per le madri singolari (`fn_crea_indirizzo_soggetto`,
#        `fn_crea_indirizzo_ruolo`): il codice del tipo e' obbligatorio (il form
#        manda sempre quello) e poi `indirizzo_per_madre`. Sede unica del
#        pre-check delle due singolari (regola del 2, 2026-10-19).
def indirizzo_singolo_per_madre(payload: Any) -> dict[str, Any]:
    # Il tipo prima della via: e' il campo che dice che cosa si sta scrivendo.
    if isinstance(payload, dict):
        require_str(payload, "tipo_indirizzo_codice", "Codice tipo indirizzo obbligatorio.")
    return indirizzo_per_madre(payload)


# Scopo: Gli indirizzi di un ruolo per la madre: `indirizzo_per_madre` per
#        elemento. `None` o un elenco vuoto: nessun indirizzo; un elenco che
#        non e' una lista e' un 400 (era un TypeError, cioe' un 500).
def indirizzi_per_madre(indirizzi_data: list[Any] | None) -> list[dict[str, Any]]:
    ErrorManager.require(
        indirizzi_data is None or isinstance(indirizzi_data, list),
        code=E_ANAG_VALIDAZIONE,
        message="Indirizzi non validi: attesa una lista.",
        context={"field": "indirizzi"},
    )
    return [indirizzo_per_madre(ind) for ind in indirizzi_data or []]


class SoggettiService:
    """Service per gestione soggetti completa."""

    def __init__(self) -> None:
        self._repo = SoggettiRepository()
        self._ind = IndirizziRepository()
        self._conti = ContiBancariRepository()
        self._titoli_iva = TitoliIvaRepository()

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata soggetti.
    def list_soggetti(self, **params: Any) -> tuple[list, int]:
        return self._repo.list_soggetti(**params)

    # Scopo: Risolve i filtri attivi della lista soggetti in dict
    #        {label_italiano: descrizione_leggibile} per l'header
    #        dell'export DEF-1. Stesso pattern di
    #        `ClientiService.resolve_filtri_export_label`: sostituisce il
    #        dump JSON opaco ("tipo_soggetto_dettaglio_id: 3") con
    #        etichette comprensibili ("Tipo: Persona Fisica").
    #
    #        Fallback: se il lookup non trova match (id obsoleto), usa
    #        "id=N" per non perdere informazione.
    def resolve_filtri_export_label(
        self,
        *,
        tipo_soggetto_dettaglio_id: int | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if tipo_soggetto_dettaglio_id is not None:
            desc = self._repo.get_tipo_soggetto_dettaglio_descrizione(
                tipo_soggetto_dettaglio_id,
            )
            out["Tipo"] = desc or f"id={tipo_soggetto_dettaglio_id}"
        return out

    # Scopo: Dettaglio soggetto con contatti, indirizzi, ruoli e dati societari.
    #        Obiettivo: restituire tutto il necessario per popolare il drawer.
    #        emittente_ids filtra i ruoli CL per scope emittente (None = nessun filtro).
    #        non_editable_fields (Fase 6 B4): lista dei campi anagrafici
    #        che NON possono essere modificati per questo soggetto, calcolata
    #        dallo stato corrente. Il frontend usa questa lista invece di
    #        ricostruire la regola "CF/PIVA bloccati se valorizzati".
    def get_soggetto(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        soggetto = require_found(self._repo.get_soggetto(soggetto_id), "Soggetto non trovato.")
        soggetto["contatti"] = self._repo.get_soggetto_contatti(soggetto_id)
        soggetto["indirizzi"] = self._repo.get_soggetto_indirizzi(soggetto_id)
        soggetto["ruoli"] = self._repo.get_soggetto_ruoli(soggetto_id, emittente_ids)
        soggetto["dati_societari"] = self._repo.get_dati_societari(soggetto_id)
        soggetto["conti_bancari"] = self._conti.list_conti_soggetto(soggetto_id)
        # Titoli IVA (I7/D10): composti qui come le altre sotto-entita', e non
        # chiesti a parte dal drawer. ⭐ Il riepilogo nella sezione del soggetto
        # arriva cosi' senza un round-trip in piu', esattamente come i conti.
        # ⚠️ Si scarta il totale, e non e' distrazione: qui i titoli sono una
        #    SOTTO-LISTA del soggetto e arrivano SENZA `limit`, quindi il totale
        #    coincide con `len()` di questa lista. Portarselo dietro in questo
        #    punto vorrebbe dire dichiarare un conteggio che nessuno legge.
        soggetto["titoli_iva"], _totale = self._titoli_iva.list_titoli_soggetto(
            soggetto_id,
        )
        soggetto["non_editable_fields"] = self._compute_non_editable_fields(soggetto)
        return soggetto

    # Scopo: Computa la lista dei campi non modificabili per il soggetto
    # in edit. Regola di immutabilita': CF/PIVA bloccati se gia' valorizzati
    # (analogo Profilo A contratti/listini-versioni). La lista cresce se
    # in futuro arrivano altri campi immutabili (es. tipo_soggetto post stato
    # avanzato). Frontend deriva cfDisabled/pivaDisabled da questa lista.
    @staticmethod
    def _compute_non_editable_fields(soggetto: dict[str, Any]) -> list[str]:
        non_editable: list[str] = []
        if (soggetto.get("codice_fiscale") or "").strip():
            non_editable.append("codice_fiscale")
        if (soggetto.get("partita_iva") or "").strip():
            non_editable.append("partita_iva")
        return non_editable

    # =================================================================
    # Creazione soggetto (orchestratore)
    # =================================================================

    # Scopo: Crea soggetto completo (PF o PG) con contatto e indirizzi.
    #        Determina il path (PF/PG) dal tipo_soggetto_dettaglio_id.
    #        Gli indirizzi li scrive la madre plurale del DB
    #        `anagrafiche.fn_crea_indirizzi_soggetto`: con auto_clone (vero di
    #        default) i tipi obbligatori del tipo di soggetto che mancano
    #        ricevono una copia del primo; un tipo gia' presente si salta.
    #        Tutto in una transazione: i trigger DEFERRED verificano al COMMIT.
    #        Risultato: UUID del soggetto creato.
    def create_soggetto(self, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction

        tipo_id = optional_int(payload, "tipo_soggetto_dettaglio_id")
        ErrorManager.require(tipo_id is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto obbligatorio.")
        assert tipo_id is not None

        natura = self._repo.get_natura_by_tipo_id(tipo_id)
        ErrorManager.require(natura is not None, code=E_ANAG_VALIDAZIONE,
                             message="Tipo soggetto non valido.")
        assert natura is not None

        # I pre-check degli indirizzi PRIMA di scrivere, come in `assign_ruolo`.
        indirizzi = self._collect_indirizzi(payload)
        # ⚠️ Assente = vero; un valore non booleano e' un 400 (prima
        #    `bool(...)`: la stringa "false" accendeva la copia).
        copia_obbligatori = _V.optional_bool(payload, "auto_clone") is not False

        with transaction.atomic():
            if natura == "PF":
                soggetto_id = self._create_pf(payload, tipo_id)
            else:
                soggetto_id = self._create_pg(payload, tipo_id)

            if indirizzi:
                create_with_dedup(
                    lambda: self._repo.crea_indirizzi_soggetto(
                        soggetto_id, indirizzi, copia_obbligatori=copia_obbligatori,
                    ),
                    "Indirizzo duplicato per questo soggetto.",
                )

        return {"id": soggetto_id}

    # =================================================================
    # Aggiornamento soggetto
    # =================================================================

    # Scopo: Aggiorna campi soggetto e, se la PATCH porta `dati_societari`,
    #        crea o aggiorna i dati societari col verbo DB.
    # ⚠️ L'ORDINE e' parte del contratto (brief §8.3): prima l'UPDATE del
    #    soggetto, poi il verbo, nella STESSA transazione. Se cambia la natura,
    #    il guard della forma giuridica confronta la forma con la natura NUOVA,
    #    e il guard al COMMIT `trgfn_soggetti_guard_forma_giuridica_natura`
    #    vede le due scritture insieme. Invertite, una forma giusta per la
    #    natura nuova verrebbe rifiutata contro quella vecchia.
    def update_soggetto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction

        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_SOGGETTO_KEYS, message="Payload soggetto non valido.",
        )
        dati = self._normalizza_flag_fiscali(payload)
        dati_societari = (
            self._valida_dati_societari(dati.pop(_CHIAVE_DATI_SOCIETARI))
            if _CHIAVE_DATI_SOCIETARI in dati else None
        )
        # La stessa forma della creazione: «x» e' «X», non un rifiuto del CHECK.
        if "sesso" in dati:
            dati["sesso"] = _V.optional_upper(dati, "sesso")
        if "tipo_soggetto_dettaglio_id" in dati:
            # NOT NULL a DB per chi la scrive da qui: la natura si cambia, non si toglie.
            dati["tipo_soggetto_dettaglio_id"] = _V.require_positive_int(
                dati, "tipo_soggetto_dettaglio_id",
            )
        with transaction.atomic():
            # ⚠️ Con i soli dati societari non c'e' niente da scrivere sul
            #    soggetto: l'UPDATE vuoto risponderebbe «non trovato». Il
            #    soggetto inesistente lo dice allora il verbo
            #    (`E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`).
            if dati or dati_societari is None:
                update_with_dedup(
                    lambda: self._repo.update_soggetto(soggetto_id, dati),
                    "Codice fiscale o partita IVA duplicata.",
                    "Soggetto non trovato.",
                )
            if dati_societari is not None:
                # L'unicita' raggiungibile e' la coppia provincia/numero REA
                # (`uq_ds_prov_cea`; quella per soggetto la assorbe il verbo,
                # che aggiorna): col campo, l'operatore vede DOVE correggere.
                create_with_constraint_mapping(
                    lambda: self._repo.scrivi_dati_societari(soggetto_id, **dati_societari),
                    {"uq_ds_prov_cea": (_MSG_REA_DUPLICATA, "iscrizione_rea")},
                    default_message=_MSG_REA_DUPLICATA,
                )
        return {"updated": True}

    # Scopo: Valida la sezione `dati_societari` della PATCH (contratto: un
    #        oggetto con le sole chiavi del verbo) e ne restituisce i parametri.
    # ⚠️ Solo la FORMA dei valori. Cosa e' ammesso (la forma per la natura, REA e
    #    capitale per la forma, il recapito per il canale FE) lo giudicano i
    #    trigger di `anagrafiche.dati_societari`, che accendono il campo: una
    #    copia qui sarebbe una seconda sede delle stesse regole.
    # ⚠️ `socio_unico` e `liquidazione` restano testo: il valore lo valida il
    #    cast all'enum nel repository, come in creazione. Scriverne l'elenco
    #    qui sarebbe una copia dell'enum del DB.
    @staticmethod
    def _valida_dati_societari(raw: Any) -> dict[str, Any]:
        ErrorManager.require(
            isinstance(raw, dict),
            code=E_ANAG_VALIDAZIONE,
            message="Dati societari non validi: atteso un oggetto.",
            detail=f"dati_societari={type(raw).__name__}",
            context={"field": _CHIAVE_DATI_SOCIETARI},
        )
        assert isinstance(raw, dict)
        _V.validate_allowed_keys(
            raw, allowed=_DATI_SOCIETARI_KEYS, message="Dati societari non validi.",
        )
        return {
            "forma_giuridica_id": _V.optional_positive_int(raw, "forma_giuridica_id"),
            "id_prov_iscri_rea": _V.optional_positive_int(raw, "id_prov_iscri_rea"),
            "iscrizione_rea": _V.optional_string(raw, "iscrizione_rea"),
            "capitale_sociale": _V.optional_decimal(raw, "capitale_sociale"),
            "socio_unico": _V.optional_upper(raw, "socio_unico"),
            "liquidazione": _V.optional_upper(raw, "liquidazione"),
            "destinatario_fe": _V.optional_upper(raw, "destinatario_fe"),
            "pec_fatturazione": _V.optional_string(raw, "pec_fatturazione"),
            "codice_sdi": _V.optional_string(raw, "codice_sdi"),
            "data_costituzione": _V.optional_date(raw, "data_costituzione"),
        }

    # Scopo: Valida e normalizza i due flag di regime fiscale (I0/D8).
    #        Perimetro: `split_payment` e `cliente_pa`, `character(1)` NOT NULL
    #        con CHECK ('S','N') a DB.
    # Risultato: una COPIA del payload con i due flag normalizzati a 'S'/'N'.
    # ⚠️ Ritorna una copia e non muta l'originale, ed e' deliberato: il payload
    #    che arriva qui e' `request.data` della view — mutarlo significherebbe
    #    modificare l'input del chiamante da dentro una funzione che si chiama
    #    «valida», cioe' un effetto collaterale che il nome non annuncia
    #    (`feedback_estrarre_non_condividere_stato`). E su un `QueryDict`
    #    immutabile l'assegnamento solleverebbe.
    # ⚠️ Il guard NON e' ridondante rispetto al CHECK: dice QUALE campo e con
    #    quali valori ammessi. Senza, il CHECK uscirebbe come validazione
    #    generica (`rifiuto_integrita`, dal 2026-10-07; prima ancora
    #    `update_with_dedup` lo traduceva in «Codice fiscale o partita IVA
    #    duplicata», un messaggio che affermava il falso).
    #    Il CHECK a DB resta la difesa dura (defense-in-depth).
    # ⭐ E il valore sbagliato non e' innocuo: la colonna accetterebbe 'Y', 't',
    #    '1' o uno spazio, e ognuno si comporterebbe come «non applicare lo
    #    split» al primo `= 'S'` — un errore fiscale silenzioso, nella direzione
    #    peggiore.
    @staticmethod
    def _normalizza_flag_fiscali(payload: dict[str, Any]) -> dict[str, Any]:
        dati = dict(payload)
        for key in _FLAG_FISCALI_SOGGETTO:
            if key not in dati:
                continue
            val = dati[key]
            ErrorManager.require(
                isinstance(val, str) and val.strip().upper() in _FLAG_FISCALI_VALORI,
                code=E_ANAG_VALIDAZIONE,
                message=f"Valore non ammesso per {key}: attesi 'S' o 'N'.",
                detail=f"{key}={val!r}",
            )
            dati[key] = val.strip().upper()
        return dati

    # =================================================================
    # Contatti
    # =================================================================

    # Scopo: Lista contatti di un soggetto.
    def get_soggetto_contatti(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_contatti(soggetto_id)

    # Scopo: Crea contatto per un soggetto con validazione.
    # ⚠️ Fino al 2026-10-09 non pretendeva il tipo contatto e non traduceva
    #    l'unicita' per tipo: tutti e due arrivavano come `E_DATABASE` (BB
    #    `crea_contatto_validato`, regola del 2).
    def create_contatto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        return crea_contatto_validato(self._repo, soggetto_id, payload)

    # Scopo: Crea un contatto del RUOLO (eventualmente per un'istanza).
    #        Fino al 2026-10-09 la creazione stava nella view
    #        `RuoloContattiView.post`, senza la regola del contatto valido.
    def create_contatto_ruolo(self, soggetto_ruolo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import connection

        from apps.anagrafiche.db._helpers import resolve_soggetto_id

        with connection.cursor() as cursor:
            soggetto_id = resolve_soggetto_id(cursor, soggetto_ruolo_id)
        return crea_contatto_validato(
            self._repo, soggetto_id, payload,
            soggetto_ruolo_id=soggetto_ruolo_id,
            istanza_utility_id=optional_int(payload, "istanza_utility_id"),
        )

    # Scopo: Aggiorna contatto esistente con verifica ownership.
    def update_contatto(self, contatto_id: int, payload: dict[str, Any],
                        soggetto_id: str | None = None) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_CONTATTO_KEYS, message="Payload contatto non valido.",
        )
        updated = self._repo.update_contatto(contatto_id, payload, soggetto_id=soggetto_id)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato.")
        return {"updated": True}

    # Scopo: Aggiorna un contatto del RUOLO con ownership check sul ruolo.
    # ⚠️ Fino al 2026-09-26 la view chiamava il repository direttamente con
    #    `request.data`: nessuno validava le chiavi, e il repository scartava in
    #    silenzio quelle fuori lista. Ora il contratto sta qui (400).
    def update_contatto_ruolo(
        self, soggetto_ruolo_id: int, contatto_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_CONTATTO_KEYS, message="Payload contatto non valido.",
        )
        updated = self._repo.update_contatto(
            contatto_id, payload, soggetto_ruolo_id=soggetto_ruolo_id,
        )
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato o non appartiene al ruolo.")
        return {"updated": True}

    # Scopo: Aggiorna un indirizzo del RUOLO con ownership check sul ruolo.
    #        Stessa storia di `update_contatto_ruolo`: la view scriveva
    #        `request.data` direttamente nel repository (2026-09-26).
    def update_indirizzo_ruolo(
        self, soggetto_ruolo_id: int, indirizzo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        _V.validate_allowed_keys(
            payload, allowed=_UPDATE_INDIRIZZO_RUOLO_KEYS,
            message="Payload indirizzo non valido.",
        )
        updated = self._repo.update_indirizzo_ruolo(indirizzo_id, soggetto_ruolo_id, payload)
        ErrorManager.require(
            updated, code=E_ANAG_NOT_FOUND,
            message="Indirizzo non trovato o non appartiene al ruolo.",
        )
        return {"updated": True}

    # Scopo: Elimina contatto con ownership check.
    def delete_contatto(self, soggetto_id: str, contatto_id: int) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_contatto(contatto_id, soggetto_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato.")
        return {"deleted": True}

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_indirizzi(soggetto_id)

    # Scopo: Crea indirizzo soggetto con validazione tipo.
    def create_indirizzo_soggetto(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction
        self._require_soggetto_exists(soggetto_id)
        with transaction.atomic():
            sog_id = self._create_indirizzo(soggetto_id, payload)
        return {"id": sog_id}

    # Scopo: Sostituisce un indirizzo soggetto: elimina il vecchio, crea il nuovo.
    #        Per l'utente e' una "modifica", ma dietro e' delete + create
    #        perche' indirizzi_dettaglio e' condiviso.
    def replace_indirizzo_soggetto(
        self, soggetto_id: str, indirizzo_soggetto_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        from django.db import transaction
        self._require_soggetto_exists(soggetto_id)
        with transaction.atomic():
            deleted = self._repo.delete_indirizzo_soggetto(indirizzo_soggetto_id, soggetto_id)
            ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Indirizzo soggetto non trovato.")
            sog_id = self._create_indirizzo(soggetto_id, payload)
        return {"id": sog_id}

    # Scopo: Elimina un indirizzo soggetto.
    def delete_indirizzo_soggetto(self, soggetto_id: str, indirizzo_soggetto_id: int) -> dict[str, Any]:
        self._require_soggetto_exists(soggetto_id)
        deleted = self._repo.delete_indirizzo_soggetto(indirizzo_soggetto_id, soggetto_id)
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND, message="Indirizzo soggetto non trovato.")
        return {"deleted": True}

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli di un soggetto con filtro scope emittente su CL.
    def get_soggetto_ruoli(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        self._require_soggetto_exists(soggetto_id)
        return self._repo.get_soggetto_ruoli(soggetto_id, emittente_ids)

    # Scopo: Lookup ricco contesto pratica — una riga per soggetto_ruolo +
    #        riga "senza ruolo" per i soggetti privi di qualunque ruolo (senza
    #        istanze: il ruolo CLIENTE nasce con la prima, D-3 di
    #        brief-db-istanza-nasce-col-ba). Mirror del pattern
    #        BillingAccountService.search_lookup.
    def search_ruoli_lookup(
        self,
        *,
        q: str,
        tipo_ruolo: str | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = _LOOKUP_DEFAULT_LIMIT,
        con_ruolo: bool = False,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.soggetti_service.search_ruoli_lookup"
        cleaned_q = q.strip() if isinstance(q, str) else ""
        ErrorManager.require(
            len(cleaned_q) >= _LOOKUP_MIN_QUERY_LENGTH,
            code="E_ANAG_VALIDAZIONE",
            message="Parametro di ricerca troppo corto.",
            detail=f"q deve avere almeno {_LOOKUP_MIN_QUERY_LENGTH} caratteri.",
            context={"q_len": len(cleaned_q)},
            function_name=function_name,
            log_to_db=False,
        )
        cleaned_tipo = tipo_ruolo.strip().upper() if tipo_ruolo else None

        # Cap di sicurezza sul limit — default 20, max 50.
        if limit is None or limit <= 0:
            effective_limit = _LOOKUP_DEFAULT_LIMIT
        else:
            effective_limit = min(int(limit), _LOOKUP_MAX_LIMIT)

        results, total_count = self._repo.search_ruoli_lookup(
            q=cleaned_q,
            tipo_ruolo=cleaned_tipo,
            emittente_ids=emittente_ids,
            limit=effective_limit,
            con_ruolo=con_ruolo,
        )
        return {
            "results": results,
            "total_count": total_count,
            "limit": effective_limit,
        }

    # Scopo: Restore by-id del lookup contesto pratica
    #        (feedback_autocomplete_restore). Esattamente UNA delle due chiavi:
    #        soggetto_ruolo_id (riga ruolo) o soggetto_id (riga "senza ruolo").
    # Perimetro: lo scope emittente del chiamante, con la stessa regola della
    #        ricerca (sulla riga «senza ruolo» piu' larga, di proposito: vedi
    #        `SoggettiRepository.get_ruolo_lookup_by_id`); fuori scope e'
    #        E_ANAG_NOT_FOUND come un id inesistente.
    def get_ruoli_lookup_by_id(
        self,
        *,
        soggetto_ruolo_id: int | None = None,
        soggetto_id: str | None = None,
        emittente_ids: list[int] | None,
    ) -> dict[str, Any]:
        function_name = "anagrafiche.soggetti_service.get_ruoli_lookup_by_id"
        ErrorManager.require(
            (soggetto_ruolo_id is not None) != (soggetto_id is not None),
            code="E_ANAG_VALIDAZIONE",
            message="Chiave di restore non valida.",
            detail="Indicare esattamente uno tra soggetto_ruolo_id e soggetto_id.",
            context={
                "soggetto_ruolo_id": soggetto_ruolo_id,
                "soggetto_id": soggetto_id,
            },
            function_name=function_name,
            log_to_db=False,
        )
        if soggetto_ruolo_id is not None:
            valid_id = (
                isinstance(soggetto_ruolo_id, int)
                and not isinstance(soggetto_ruolo_id, bool)
                and soggetto_ruolo_id > 0
            )
            ErrorManager.require(
                valid_id,
                code="E_ANAG_VALIDAZIONE",
                message="soggetto_ruolo_id non valido.",
                detail="soggetto_ruolo_id deve essere un intero positivo.",
                context={"soggetto_ruolo_id": soggetto_ruolo_id},
                function_name=function_name,
                log_to_db=False,
            )
        else:
            # Formato UUID validato qui: un malformato esploderebbe sul cast
            # ::uuid del repository con un errore DB non parlante.
            try:
                uuid.UUID(str(soggetto_id))
            except (ValueError, TypeError):
                ErrorManager.raise_error(
                    code="E_ANAG_VALIDAZIONE",
                    message="soggetto_id non valido.",
                    detail="soggetto_id deve essere un UUID.",
                    context={"soggetto_id": soggetto_id},
                    function_name=function_name,
                    log_to_db=False,
                )
        result = self._repo.get_ruolo_lookup_by_id(
            soggetto_ruolo_id=soggetto_ruolo_id,
            soggetto_id=soggetto_id,
            emittente_ids=emittente_ids,
        )
        ErrorManager.require(
            result is not None,
            code="E_ANAG_NOT_FOUND",
            message="Contesto soggetto/ruolo non trovato.",
            detail=f"soggetto_ruolo_id={soggetto_ruolo_id}, soggetto_id={soggetto_id}",
            context={
                "soggetto_ruolo_id": soggetto_ruolo_id,
                "soggetto_id": soggetto_id,
            },
            function_name=function_name,
            log_to_db=False,
        )
        assert result is not None
        return result

    # Scopo: Assegna ruolo a soggetto (idempotente).
    # ⛔ I ruoli con un FLUSSO DEDICATO non nascono da qui (decisione di Tid,
    #    2026-10-09): il ruolo e' solo il primo anello della loro catena.
    #    Un CL nasce con la prima istanza e il suo billing account (flusso
    #    Clienti): creato «nudo» da qui non aveva clienti, e un operatore con
    #    emittente non lo vedeva nemmeno (scope CL). Stesso discorso per FO
    #    (condizioni d'acquisto), EF (emittente fiscale) e RIS_UMANA (rapporto
    #    di lavoro, operatore).
    # ⛔ Gli indirizzi obbligatori di un ruolo (matrice
    #    `config.tipi_ruolo_tipi_indirizzo`, es. SEDELEG e FATT per GE) sono
    #    indirizzi DEL RUOLO, non del soggetto: li pretende il guard differito
    #    `trgfn_soggetti_ruoli_guard_indirizzi_required` al COMMIT. Fino al
    #    2026-10-09 questo endpoint non li accettava, e un ruolo che ne ha di
    #    obbligatori non poteva nascere. Stessa catena dei flussi
    #    clienti/fornitori: ruolo, poi `create_indirizzi_ruolo` (auto-clone del
    #    primo per gli obbligatori mancanti), una transazione.
    def assign_ruolo(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from django.db import transaction

        self._require_soggetto_exists(soggetto_id)
        codice_ruolo = require_str(payload, "codice_ruolo", "Codice ruolo obbligatorio.")
        # `CLIENTE` o `CL`: la chiave e' il codice interno (None = sconosciuto,
        # lo rifiuta la funzione DB col suo codice).
        tipo = self._repo.resolve_tipo_ruolo(codice_ruolo)
        codice_interno = str(tipo["codice_interno"]) if tipo else None
        if tipo and codice_interno in _RUOLI_CON_FLUSSO_DEDICATO:
            ErrorManager.raise_error(
                code=E_ANAG_VALIDAZIONE,
                message=(
                    f"Il ruolo {tipo['descrizione']} non si assegna da qui: "
                    "ha un flusso di creazione dedicato."
                ),
                context={"field": "codice_ruolo", "codice_ruolo": tipo["codice"]},
            )
        indirizzi = self._collect_indirizzi(payload)
        with transaction.atomic():
            ruolo_id = create_with_dedup(
                lambda: self._repo.assign_ruolo(soggetto_id, codice_interno or codice_ruolo),
                "Ruolo gia' assegnato.",
            )
            if indirizzi:
                self.create_indirizzi_ruolo(ruolo_id, indirizzi)
        return {"id": ruolo_id}

    # =================================================================
    # Utility
    # =================================================================

    # Scopo: Validazione CF (congruenza + duplicato) e P.IVA (duplicato).
    #        Ritorna warnings e errors per feedback immediato nel frontend.
    def valida_cf_piva(self, payload: dict[str, Any]) -> dict[str, Any]:
        from datetime import date as _date

        warnings: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []

        cf = (payload.get("codice_fiscale") or "").strip().upper()
        piva = (payload.get("partita_iva") or "").strip().upper()
        sesso = _V.optional_upper(payload, "sesso")
        data_nascita_raw = payload.get("data_nascita")
        comune_nascita_id = optional_int(payload, "comune_nascita_id")

        # --- Validazione congruenza CF ---
        if cf and len(cf) == 16:
            data_nascita = None
            if data_nascita_raw:
                if isinstance(data_nascita_raw, str):
                    try:
                        data_nascita = _date.fromisoformat(data_nascita_raw)
                    except ValueError:
                        pass
                else:
                    data_nascita = data_nascita_raw

            codice_catastale = None
            if comune_nascita_id:
                codice_catastale = self._repo.get_codice_catastale(comune_nascita_id)

            cf_errors = valida_cf_congruenza_it(
                cf,
                data_nascita=data_nascita,
                sesso=sesso,
                codice_catastale_comune=codice_catastale,
            )
            for e in cf_errors:
                errors.append({"field": "codice_fiscale", "message": e})

            # Duplicato CF
            existing = self._repo.find_by_codice_fiscale(cf)
            if existing:
                warnings.append({
                    "field": "codice_fiscale",
                    "message": f"CF gia' presente: {existing['ragione_sociale_completa']} ({existing['codice']})",
                })

        # --- Duplicato P.IVA ---
        if piva and len(piva) >= 11:
            existing = self._repo.find_by_partita_iva(piva)
            if existing:
                warnings.append({
                    "field": "partita_iva",
                    "message": f"P.IVA gia' presente: {existing['ragione_sociale_completa']} ({existing['codice']})",
                })

        return {"errors": errors, "warnings": warnings}

    # Scopo: Genera codice fiscale italiano da dati anagrafici.
    def genera_cf(self, payload: dict[str, Any]) -> dict[str, Any]:
        from datetime import date as _date

        cognome = require_str(payload, "cognome", "Cognome obbligatorio.")
        nome = require_str(payload, "nome", "Nome obbligatorio.")
        sesso = require_str(payload, "sesso", "Sesso obbligatorio.").upper()
        # ⛔ Il codice fiscale codifica solo M e F (il giorno +40). Con `X`
        #    («non si puo' stabilire») un calcolo darebbe il CF di un uomo:
        #    un sesso inventato, rientrato dalla finestra.
        ErrorManager.require(
            sesso in ("M", "F"),
            code=E_ANAG_VALIDAZIONE,
            message="Il codice fiscale si calcola solo con sesso M o F.",
            context={"field": "sesso"},
        )
        comune_id = optional_int(payload, "comune_nascita_id")
        ErrorManager.require(
            comune_id is not None and comune_id > 0,
            code=E_ANAG_VALIDAZIONE,
            message="Comune di nascita obbligatorio.",
        )
        assert comune_id is not None

        data_nascita_raw = payload.get("data_nascita")
        ErrorManager.require(
            data_nascita_raw is not None,
            code=E_ANAG_VALIDAZIONE,
            message="Data di nascita obbligatoria.",
        )
        assert data_nascita_raw is not None
        if isinstance(data_nascita_raw, str):
            data_nascita = _date.fromisoformat(data_nascita_raw)
        else:
            data_nascita = data_nascita_raw

        codice_catastale = self._repo.get_codice_catastale(comune_id)
        ErrorManager.require(
            codice_catastale is not None,
            code=E_ANAG_VALIDAZIONE,
            message="Codice catastale non trovato per il comune selezionato.",
        )
        assert codice_catastale is not None

        cf = genera_cf_it(cognome, nome, data_nascita, sesso, codice_catastale)
        return {"codice_fiscale": cf}

    # =================================================================
    # Metodi interni
    # =================================================================

    # Scopo: Crea soggetto PF (privato PR o ditta individuale DI) via building
    #        block DB, con la natura di dettaglio SCELTA e la partita IVA.
    #        Include validazione congruenza CF con dati anagrafici (data, sesso, comune).
    # ⚠️ Fino al 2026-10-09 la funzione DB cablava `PR` e non riceveva la P.IVA:
    #    chi sceglieva «Ditta individuale» otteneva un privato, e la P.IVA si
    #    perdeva senza errore (brief-db-sesso-senza-default §2).
    def _create_pf(self, payload: dict[str, Any], tipo_id: int) -> str:
        cognome = require_str(payload, "cognome", "Cognome obbligatorio.")
        nome = require_str(payload, "nome", "Nome obbligatorio.")
        codice_fiscale = require_str(payload, "codice_fiscale", "Codice fiscale obbligatorio.")
        # ⛔ Nessun controllo e nessun default qui (decisione di Tid,
        #    2026-10-09): QUANDO il sesso serve lo dice la natura
        #    (`sesso_policy`), e lo giudica il guard
        #    `trgfn_soggetti_guard_sesso_policy`, che accende il campo dal canale
        #    `COLUMN`. Un controllo qui sarebbe una seconda sede della regola, e
        #    per la DI (sesso facoltativo) una sede sbagliata.
        sesso = _V.optional_upper(payload, "sesso")

        # Validazione congruenza CF con dati anagrafici
        self._valida_cf_congruenza(payload, codice_fiscale, sesso)

        contatto = payload.get("contatto") or {}
        # Regola unificata via classify_contatto_payload (Fase 5): per il
        # soggetto il contatto e' obbligatorio (sempre VALID richiesto),
        # quindi sia EMPTY che PARTIAL → errore esplicito.
        richiedi_contatto_valido(contatto)
        email_addr = optional_str(contatto, "email") or ""

        soggetto_id = create_with_dedup(
            lambda: self._repo.crea_soggetto_pf(
                cognome=cognome, nome=nome, codice_fiscale=codice_fiscale,
                email=email_addr,
                data_nascita=optional_str(payload, "data_nascita"),
                sesso=sesso,
                stato_iso2=optional_str(payload, "stato_iso2"),
                comune_nascita_id=optional_int(payload, "comune_nascita_id"),
                tipo_contatto_id=optional_int(contatto, "tipo_contatto_id"),
                tipo_soggetto_dettaglio_id=tipo_id,
                partita_iva=optional_str(payload, "partita_iva"),
            ),
            "Soggetto con questo codice fiscale gia' esistente.",
        )

        self._update_contatto_default(soggetto_id, contatto,
                                      contatto.get("nominativo", f"{cognome} {nome}"))
        return soggetto_id

    # Scopo: Crea soggetto PG/ENTE via building block DB.
    #        Obiettivo: INSERT soggetto + contatto default + dati societari
    #        (se policy lo richiede). I trigger DEFERRED verificano al COMMIT.
    def _create_pg(self, payload: dict[str, Any], tipo_id: int) -> str:
        ragione_sociale = require_str(payload, "ragione_sociale", "Ragione sociale obbligatoria.")

        contatto = payload.get("contatto") or {}
        # Regola unificata via classify_contatto_payload (Fase 5): per il
        # soggetto il contatto e' obbligatorio (sempre VALID richiesto).
        richiedi_contatto_valido(contatto)
        email_addr = optional_str(contatto, "email") or ""

        dati_soc = payload.get("dati_societari") or {}

        soggetto_id = create_with_constraint_mapping(
            lambda: self._repo.crea_soggetto_pg(
                ragione_sociale=ragione_sociale,
                tipo_soggetto_dettaglio_id=tipo_id,
                email=email_addr,
                codice_fiscale=optional_str(payload, "codice_fiscale"),
                partita_iva=optional_str(payload, "partita_iva"),
                stato_iso2=optional_str(payload, "stato_iso2"),
                forma_giuridica_id=optional_int(dati_soc, "forma_giuridica_id"),
                id_prov_iscri_rea=optional_int(dati_soc, "id_prov_iscri_rea"),
                iscrizione_rea=optional_str(dati_soc, "iscrizione_rea"),
                capitale_sociale=dati_soc.get("capitale_sociale"),
                socio_unico=optional_str(dati_soc, "socio_unico"),
                liquidazione=optional_str(dati_soc, "liquidazione"),
                destinatario_fe=optional_str(dati_soc, "destinatario_fe"),
                pec_fatturazione=optional_str(dati_soc, "pec_fatturazione"),
                codice_sdi=optional_str(dati_soc, "codice_sdi"),
                tipo_contatto_id=optional_int(contatto, "tipo_contatto_id"),
            ),
            # ⚠️ La creazione scrive DUE tabelle con unicita' proprie: il REA
            #    duplicato (`uq_ds_prov_cea`, dentro `fn_scrivi_dati_societari`)
            #    fino al 2026-10-11 usciva come «CF/PIVA duplicata». Il DB dice
            #    quale vincolo e' violato: lo si legge, come in modifica.
            {
                "uq_soggetto_idstato_id_fiscale_univoco": _MSG_PG_CF_PIVA_DUPLICATA,
                "uq_ds_prov_cea": (_MSG_REA_DUPLICATA, "iscrizione_rea"),
            },
            default_message=_MSG_PG_CF_PIVA_DUPLICATA,
        )

        self._update_contatto_default(soggetto_id, contatto,
                                      contatto.get("nominativo", ragione_sociale))
        return soggetto_id

    # Scopo: Aggiorna il contatto default creato dalla funzione DB con i campi aggiuntivi.
    def _update_contatto_default(self, soggetto_id: str, contatto: dict, default_nominativo: str) -> None:
        if not contatto:
            return
        contatti = self._repo.get_soggetto_contatti(soggetto_id)
        if contatti:
            self._repo.update_contatto(contatti[0]["id"], {
                "nominativo": contatto.get("nominativo", default_nominativo),
                "telefono": optional_str(contatto, "telefono"),
                "cellulare": optional_str(contatto, "cellulare"),
                "pec": optional_str(contatto, "pec"),
                "tipo_contatto_id": optional_int(contatto, "tipo_contatto_id"),
                "unita_organizzativa_id": optional_int(contatto, "unita_organizzativa_id"),
                "note": optional_str(contatto, "note"),
            })

    # Scopo: Raccoglie indirizzi dal payload ("indirizzi" array e/o "indirizzo"
    #        singolo) nella forma delle madri, coi pre-check di
    #        `indirizzi_per_madre`.
    # ⛔ Fino al 2026-10-19 un elenco che non era una lista e gli elementi che
    #    non erano oggetti si SCARTAVANO in silenzio: il soggetto nasceva senza
    #    gli indirizzi chiesti e la risposta era ok. Ora sono un 400.
    def _collect_indirizzi(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        indirizzi = indirizzi_per_madre(payload.get("indirizzi"))
        if payload.get("indirizzo") is not None:
            indirizzi.append(indirizzo_per_madre(payload["indirizzo"]))
        return indirizzi

    # Scopo: Crea UN indirizzo del soggetto con la madre del DB
    #        `anagrafiche.fn_crea_indirizzo_soggetto(soggetto, indirizzo jsonb)`:
    #        tipo per codice, indirizzo in una di tre forme (libero, dettaglio
    #        gia' risolto, via da risolvere). La forma dell'indirizzo libero —
    #        comune e CAP del catalogo, o la localita' per uno stato senza
    #        catalogo — la giudica il guard della tabella, col campo.
    # ⭐ Dal 2026-10-18 (D-4 di Tid, brief-db-processi-accensione-per-ambiente
    #    §6.11): la firma posizionale non aveva la forma estera, e il backend
    #    risolveva da se' la via. Ora un oggetto, la stessa grammatica della
    #    gemella del ruolo.
    def _create_indirizzo(self, soggetto_id: str, payload: dict[str, Any]) -> int:
        indirizzo = indirizzo_singolo_per_madre(payload)
        return create_with_dedup(
            lambda: self._repo.crea_indirizzo_soggetto(soggetto_id, indirizzo),
            "Indirizzo duplicato per questo soggetto.",
        )

    # Scopo: Crea gli indirizzi di un ruolo con la madre del DB
    #        `anagrafiche.fn_crea_indirizzi_ruolo`: tipo per codice o id, forma
    #        libera, dettaglio gia' risolto o via da risolvere. L'AUTO-CLONE dei
    #        tipi obbligatori del ruolo (dal primo indirizzo) e il salto dei tipi
    #        che il ruolo ha gia' sono regole del DB, che legge anche il tipo di
    #        ruolo. Ritorna quanti indirizzi sono stati scritti.
    #        Qui restano i pre-check per l'operatore (`indirizzi_per_madre`).
    #        Una chiave estranea la rifiuta il DB (`E_CAMPO_NON_AMMESSO`).
    # ⭐ Dal 2026-10-18 (2b-2, lotto 2): la saga Python (matrice, auto-clone,
    #    skip, risoluzione della via, INSERT riga per riga) era la copia della
    #    regola; con lei e' sparito anche un difetto — il primo dettaglio
    #    risolto si riusava per OGNI indirizzo successivo senza dettaglio, non
    #    solo per i cloni: due vie diverse finivano sullo stesso dettaglio.
    #    Chiamanti: crea_fornitore, crea_cliente, assign_ruolo.
    def create_indirizzi_ruolo(
        self, soggetto_ruolo_id: int, indirizzi_data: list[dict[str, Any]],
    ) -> int:
        indirizzi = indirizzi_per_madre(indirizzi_data)
        if not indirizzi:
            return 0
        # Una FK o un CHECK violati dentro la madre sono un 400, come per le
        # singolari: senza traduzione uscivano `E_DATABASE` (500).
        return create_with_dedup(
            lambda: self._repo.crea_indirizzi_ruolo(soggetto_ruolo_id, indirizzi),
            "Indirizzo con questo tipo gia' presente per il ruolo/istanza.",
        )

    # Scopo: Crea UN indirizzo di un ruolo, anche di un'istanza
    #        (`istanza_utility_id`), con la madre del DB
    #        `anagrafiche.fn_crea_indirizzo_ruolo`: la stessa grammatica e gli
    #        stessi pre-check dell'indirizzo di soggetto
    #        (`indirizzo_singolo_per_madre`).
    #        Un tipo gia' presente sul ruolo (o sull'istanza) lo rifiuta il
    #        vincolo. Ritorna la riga scritta.
    # ⭐ Dal 2026-10-19 (R-DB-16b): fino ad allora la view risolveva tipo e via
    #    e il repository scriveva la riga con una INSERT sua.
    def create_indirizzo_ruolo(
        self, soggetto_ruolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        indirizzo = indirizzo_singolo_per_madre(payload)
        return create_with_dedup(
            lambda: self._repo.crea_indirizzo_ruolo(soggetto_ruolo_id, indirizzo),
            "Indirizzo con questo tipo gia' presente per il ruolo/istanza.",
        )

    # Scopo: Validazione congruenza CF italiano con dati anagrafici (data, sesso, comune).
    #        Non blocca se i dati opzionali non sono forniti — valida solo quelli presenti.
    # ⚠️ `sesso` gia' normalizzato dal chiamante: riletto grezzo dal payload,
    #    « m » non era ne' M ne' F e la congruenza col CF si saltava in silenzio.
    def _valida_cf_congruenza(
        self, payload: dict[str, Any], codice_fiscale: str, sesso: str | None,
    ) -> None:
        from datetime import date as date_type

        data_nascita = None
        dn_str = optional_str(payload, "data_nascita")
        if dn_str:
            try:
                data_nascita = date_type.fromisoformat(dn_str)
            except ValueError:
                pass

        codice_catastale = None
        comune_id = optional_int(payload, "comune_nascita_id") or optional_int(payload, "comune_id")
        if comune_id:
            codice_catastale = self._repo.get_codice_catastale(comune_id)

        errors = valida_cf_congruenza_it(
            codice_fiscale,
            data_nascita=data_nascita,
            sesso=sesso,
            codice_catastale_comune=codice_catastale,
        )
        if errors:
            ErrorManager.raise_error(code=E_ANAG_VALIDAZIONE,
                                     message=" ".join(errors))

    # Scopo: Guard leggero — verifica che il soggetto esista (SELECT 1).
    def _require_soggetto_exists(self, soggetto_id: str) -> None:
        exists = self._repo.exists_soggetto(soggetto_id)
        ErrorManager.require(exists, code=E_ANAG_NOT_FOUND,
                             message="Soggetto non trovato.")
