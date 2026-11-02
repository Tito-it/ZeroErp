# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service dei TITOLI IVA del soggetto (I7 / D10 di
#        brief-db-be-iva-risolutore-e-regime-cliente). Orchestrazione e
#        validazioni di MERITO; i vincoli strutturali stanno a DB e restano la
#        difesa dura.
#
# ⭐ IL PRINCIPIO CHE QUESTA VOCE REALIZZA (D7): l'influenza del soggetto
#    sull'IVA passa SEMPRE da un titolo registrato, datato e con una prova
#    documentale — mai da una colonna di default appesa all'anagrafica. E' la
#    ragione per cui `anagrafiche.clienti.iva_id` e' stata tolta e NON sostituita
#    da un `soggetti.iva_id`.
#
# ⚠️ PERCHE' I GUARD QUI NON SONO RIDONDANTI rispetto ai trigger: un trigger
#    solleva con il codice giusto ma DOPO, e per alcune regole (il tipo di
#    movimento scrivibile da API, il DELETE con movimenti) non esiste nessun
#    trigger — sono decisioni del contratto d'uso, non del modello. Dove il
#    trigger c'e', il guard qui davanti serve a nominare il CAMPO che l'operatore
#    ha compilato invece di uno SQLSTATE.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.titoli_iva_repository import TitoliIvaRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE
from apps.anagrafiche.services._validators import require_found
from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator

_MESSAGE = "Payload titolo IVA non valido."
# Validator del dominio per i campi del payload (`imponibile` della forzatura).
_V = PayloadValidator(validation_code=E_ANAG_VALIDAZIONE)

# Tetto dichiarato della lista di presidio dei titoli sfondati (Q4).
# ⛔ Il cap a 500 e' stato RIMOSSO il 2026-09-02: la lista e' paginata, e un
# tetto silenzioso sopra una paginazione sarebbe la stessa bugia di prima con un
# numero diverso. Il tetto per pagina lo impone `parse_list_params` (MAX_LIMIT).

# Ambito dichiarato, mai dedotto da un NULL (D12 + `feedback_null_nelle_chiavi_due_forme`).
_AMBITI: frozenset[str] = frozenset({"TUTTO", "RISTRETTO"})

# I tre livelli dell'ambito e la colonna che ciascuno pretende. ⭐ E' anche la
# mappa che il normalizzatore usa per AZZERARE le altre due: il CHECK di DB
# pretende che siano NULL, e mandarle valorizzate sarebbe un 23514 muto.
_LIVELLI_AMBITO: dict[str, str] = {
    "ARTICOLO": "articolo_id",
    "GRUPPO_VOCE": "gruppo_voce_id",
    "TIPO_VOCE": "tipo_voce_id",
}

# Chiavi accettate dal payload del titolo.
# ⛔ `emittente_fiscale_id` sta solo in CREATE (Q5: immutabile dopo).
# ⛔ `imponibile_utilizzato` non c'e' in nessuno dei due: lo scrive il trigger
#    dell'accumulatore, ed e' cio' che rende vera la promessa di D5.
_CREATE_KEYS: frozenset[str] = frozenset({
    "emittente_fiscale_id", "tipo_titolo_iva_id", "iva_id", "ambito",
    "valido_dal", "valido_al", "protocollo", "data_ricezione", "riferimento",
    "plafond", "note",
})
# ⛔ I quattro NOT NULL della tabella che il chiamante deve fornire. Gli altri
#    (`ambito`, `attivo`, `imponibile_utilizzato`) hanno un default a DB.
#    ⚠️ In UPDATE non si ripete: una PATCH parziale che non tocca `valido_dal`
#    non deve pretenderlo, e toglierlo esplicitamente lo rifiuta gia' il DB.
_CREATE_OBBLIGATORI: tuple[str, ...] = (
    "emittente_fiscale_id", "tipo_titolo_iva_id", "iva_id", "valido_dal",
)

# ⛔ Colonne NOT NULL che una PATCH puo' toccare ma NON svuotare. E' l'altro
#    verso dello stesso guard (`feedback_normalize_guard_simmetrico`): la create
#    pretende che ci siano, l'update che restino. Senza, un `valido_dal: ""`
#    diventerebbe NULL e uscirebbe come 23502 — un errore che nomina una colonna
#    a chi ha svuotato un campo.
# ⚠️ `valido_al` e `data_ricezione` NON sono qui, ed e' voluto: sono nullable, e
#    svuotare la fine validita' («senza scadenza») e' un'operazione legittima.
_NON_ANNULLABILI: frozenset[str] = frozenset({
    "tipo_titolo_iva_id", "iva_id", "valido_dal",
})

_UPDATE_KEYS: frozenset[str] = frozenset({
    "tipo_titolo_iva_id", "iva_id", "ambito", "valido_dal", "valido_al",
    "protocollo", "data_ricezione", "riferimento", "plafond", "attivo", "note",
})


class TitoliIvaService:
    """Service per titoli IVA del soggetto, ambiti e registro movimenti."""

    def __init__(self) -> None:
        self._repo = TitoliIvaRepository()

    # =================================================================
    # Tipi ammessi (lookup del drawer)
    # =================================================================

    # Scopo: I tipi di titolo IVA ammessi dalla natura del soggetto, in
    #        envelope di lookup `{"results": [...]}` (api.md §Lookup).
    def list_tipi_ammessi(self, soggetto_id: str) -> dict[str, Any]:
        return {"results": self._repo.list_tipi_ammessi_soggetto(soggetto_id)}

    # =================================================================
    # Titoli
    # =================================================================

    # Scopo: Titoli IVA di un soggetto, in envelope `results` + `count`.
    # ⚠️ Ogni titolo porta `ambito_incompleto`: RISTRETTO con zero righe di
    #    ambito. E' la decisione Q2 — il DB ammette apposta quello stato, perche'
    #    il caso si costruisce in due istruzioni; l'API lo DICHIARA, cosi' il
    #    frontend puo' avvisare senza dover ri-derivare la regola in un template.
    # ⭐ PAGINATA dal 2026-09-02: prima consegnava TUTTI i titoli in un colpo e
    #    il conteggio veniva da una query separata (`count_titoli_soggetto`, ora
    #    sparita). Due valutazioni dello stesso predicato possono non concordare;
    #    una sola non puo'.
    def list_titoli_soggetto(
        self,
        soggetto_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> dict[str, Any]:
        titoli, totale = self._repo.list_titoli_soggetto(
            soggetto_id,
            limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        )
        for t in titoli:
            t["ambito_incompleto"] = self._ambito_incompleto(t)
        return {"results": titoli, "count": totale}

    # Scopo: Dettaglio di un titolo, con ambiti e registro movimenti.
    def get_titolo(self, soggetto_id: str, titolo_id: int) -> dict[str, Any]:
        titolo = self._require_titolo(soggetto_id, titolo_id)
        # ⚠️ Si scartano i totali, e non e' distrazione: qui ambiti e movimenti
        #    sono SOTTO-LISTE del titolo e arrivano senza `limit`, quindi il
        #    totale coincide con la lunghezza. Portarselo dietro vorrebbe dire
        #    dichiarare due conteggi che in questo punto nessuno legge.
        titolo["ambiti"], _tot_ambiti = self._repo.list_ambiti(titolo_id)
        titolo["movimenti"], _tot_movimenti = self._repo.list_movimenti(titolo_id)
        titolo["ambito_incompleto"] = self._ambito_incompleto(titolo)
        return titolo

    # Scopo: Registra un titolo IVA per il soggetto.
    # ⚠️ I campi obbligatori si guardano QUI, e non e' ridondante rispetto al
    #    serializer: in questo progetto i serializer di `extend_schema` servono
    #    lo SCHEMA OpenAPI e non validano niente — `handle_post_json` passa il
    #    payload grezzo al service. Senza questi guard un `valido_dal` mancante
    #    arriverebbe come violazione di NOT NULL, cioe' un errore che nomina una
    #    colonna a chi ha lasciato vuoto un campo.
    def create_titolo(self, soggetto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        _V.validate_allowed_keys(payload, allowed=_CREATE_KEYS, message=_MESSAGE)
        for campo in _CREATE_OBBLIGATORI:
            ErrorManager.require(
                payload.get(campo) not in (None, ""),
                code=E_ANAG_VALIDAZIONE,
                message=_MESSAGE,
                detail=f"{campo} obbligatorio.",
                context={"field": campo},
            )
        emittente_fiscale_id = optional_int(payload, "emittente_fiscale_id")
        ErrorManager.require(
            emittente_fiscale_id is not None,
            code=E_ANAG_VALIDAZIONE,
            message=_MESSAGE,
            detail="emittente_fiscale_id deve essere un intero.",
            context={"field": "emittente_fiscale_id"},
        )
        assert emittente_fiscale_id is not None
        dati = self._normalizza_titolo(payload)
        titolo_id = self._repo.create_titolo(
            soggetto_id=soggetto_id,
            emittente_fiscale_id=emittente_fiscale_id,
            data=dati,
        )
        return {"id": titolo_id}

    # Scopo: Aggiorna un titolo.
    def update_titolo(
        self, soggetto_id: str, titolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        _V.validate_allowed_keys(payload, allowed=_UPDATE_KEYS, message=_MESSAGE)
        self._require_titolo(soggetto_id, titolo_id)
        dati = self._normalizza_titolo(payload)
        # Prima della scrittura: il rowcount dopo l'UPDATE non distingue il
        # payload vuoto dal titolo sparito (l'esistenza e' gia' verificata).
        _V.require_campi_da_aggiornare(
            dati, context={"allowed_keys": sorted(_UPDATE_KEYS)},
        )
        self._repo.update_titolo(titolo_id, dati)
        return {"updated": True}

    # Scopo: Elimina un titolo, ma SOLO se non ha consumato niente (Q6).
    # ⛔ Con dei movimenti non si cancella: un registro e' la traccia di cio' che
    #    e' stato consumato, e un DELETE che se la porta via cancella la prova.
    # ⚠️ Il DB lo regge gia' — la FK dei movimenti NON ha ON DELETE CASCADE — ma
    #    lo direbbe con un 23503 che nomina un vincolo. Qui si dice la cosa vera,
    #    e si dice anche COSA FARE al posto.
    def delete_titolo(self, soggetto_id: str, titolo_id: int) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)
        movimenti = self._repo.count_movimenti(titolo_id)
        ErrorManager.require(
            movimenti == 0,
            code=E_ANAG_VALIDAZIONE,
            message="Il titolo ha gia' movimenti di plafond registrati: "
                    "non si elimina, si disattiva.",
            detail=f"movimenti={movimenti}",
            context={"titolo_iva_id": titolo_id, "movimenti": movimenti},
        )
        self._repo.delete_titolo(titolo_id)
        return {"deleted": True}

    # Scopo: Titoli con il plafond sfondato, su tutti i soggetti (Q4).
    # ⚠️ Il tetto sul numero di righe e' dichiarato e non implicito: una lista di
    #    presidio dovrebbe essere quasi vuota, ma «dovrebbe» non e' un limite —
    #    e una query senza LIMIT che un giorno torna diecimila righe fa cadere la
    #    schermata proprio quando c'e' piu' da guardare. Le righe sono ordinate
    #    per eccedenza decrescente: se il tetto morde, in cima ci sono comunque i
    #    casi peggiori.
    # ⭐ PAGINATA dal 2026-09-02 (decisione Tid: «così è standard e non ci
    #    pensiamo più»). Prima restituiva i primi `_SFONDATI_LIMIT` (500) e
    #    **non lo diceva a nessuno**: su una lista di presidio significava che
    #    dal 501-esimo caso in poi una forzatura non si vedeva, e nessuno poteva
    #    accorgersene. Ora la pagina e' una pagina e il totale e' il totale.
    def list_titoli_sfondati(
        self,
        *,
        limit: int,
        offset: int,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> dict[str, Any]:
        # ⭐ UNA chiamata: righe e totale arrivano dalla stessa valutazione
        #    (`COUNT(*) OVER()`), quindi non possono raccontare due popolazioni
        #    diverse. Prima erano due query separate — scritte a mano sopra un
        #    building block che gia' faceva questo.
        risultati, totale = self._repo.list_titoli_sfondati(
            limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        )
        return {"results": risultati, "count": totale}

    # =================================================================
    # Ambiti
    # =================================================================

    # Scopo: Righe di ambito di un titolo, in envelope `results` + `count`.
    # ⛔ Il `count` viene da una valutazione INDIPENDENTE dalle righe (la stessa
    #    query, via `COUNT(*) OVER()`), mai da `len(results)`: la lista si monta
    #    non paginata, e li' il totale e' l'asserzione che le righe siano tutte.
    def list_ambiti(
        self, soggetto_id: str, titolo_id: int,
        *, limit: int | None = None, offset: int = 0,
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)
        risultati, totale = self._repo.list_ambiti(
            titolo_id, limit=limit, offset=offset,
        )
        return {"results": risultati, "count": totale}

    # Scopo: Aggiunge una riga di ambito.
    def create_ambito(
        self, soggetto_id: str, titolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)
        dati = self._normalizza_ambito(payload)
        ambito_id = self._repo.create_ambito(titolo_id, dati)
        return {"id": ambito_id}

    # Scopo: Toglie una riga di ambito.
    def delete_ambito(
        self, soggetto_id: str, titolo_id: int, ambito_id: int,
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)
        tolto = self._repo.delete_ambito(titolo_id, ambito_id)
        ErrorManager.require(
            tolto, code=E_ANAG_NOT_FOUND,
            message="Riga di ambito non trovata su questo titolo.",
        )
        return {"deleted": True}

    # =================================================================
    # Registro movimenti (D5)
    # =================================================================

    # Scopo: Il registro di un titolo, in envelope `results` + `count`.
    # ⭐ Paginato (lista 65): un registro append-only cresce a ogni fattura.
    def list_movimenti(
        self, soggetto_id: str, titolo_id: int,
        *, limit: int | None = None, offset: int = 0,
        order_by: str | None = None, order_dir: str | None = None,
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)
        risultati, totale = self._repo.list_movimenti(
            titolo_id, limit=limit, offset=offset,
            order_by=order_by, order_dir=order_dir,
        )
        return {"results": risultati, "count": totale}

    # Scopo: Registra una forzatura manuale sul plafond.
    # ⛔ DALL'API SI SCRIVE SOLO `FORZATURA`, ed e' la decisione Q3 — la piu'
    #    delicata di questo piano. `FATTURA` e `NOTA_CREDITO` li produce la
    #    pipeline con I4, all'emissione del lotto, passando da
    #    `fn_consuma_plafond_titolo_iva_righe`, che e' anche l'unica a prendere
    #    il lock di D15-bis.
    # ⚠️ Un POST che accettasse `FATTURA` consumerebbe plafond SENZA una fattura:
    #    il CHECK di DB pretende `fattura_id NOT NULL` sui tipi non-forzatura,
    #    quindi il chiamante dovrebbe passare l'id di una fattura vera — e a quel
    #    punto `uq_stiva_movimenti_documento` non protegge piu' niente, perche' la
    #    riga E' formalmente valida. Il numero che ne esce e' precisamente quello
    #    che l'Agenzia delle Entrate verifica.
    def create_forzatura(
        self, soggetto_id: str, titolo_id: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)

        tipo = payload.get("tipo_movimento")
        ErrorManager.require(
            tipo in (None, "FORZATURA"),
            code=E_ANAG_VALIDAZIONE,
            message="Dal registro si possono inserire solo forzature manuali: "
                    "i movimenti di fattura e nota di credito li produce la "
                    "fatturazione.",
            detail=f"tipo_movimento={tipo!r}",
            context={"field": "tipo_movimento"},
        )

        # ⚠️ `Decimal` e non `float`: e' un importo fiscale, e il binario
        #    d'arrivo e' una colonna `numeric`. Un float introdurrebbe un errore
        #    di rappresentazione proprio sul numero che l'Agenzia delle Entrate
        #    verifica. La coercizione (da `str`, bool e NaN rifiutati) e' del BB.
        valore = _V.require_decimal(payload, "imponibile", message=_MESSAGE)
        # ⚠️ Il segno lo lascia decidere il chiamante (una forzatura corregge in
        #    entrambe le direzioni), ma lo ZERO no: `chk_stiva_movimenti_segno`
        #    lo rifiuta, e un movimento che non muove niente non e' una
        #    correzione — e' una riga di rumore nel registro.
        ErrorManager.require(
            valore != 0,
            code=E_ANAG_VALIDAZIONE, message=_MESSAGE,
            detail="imponibile non puo' essere zero.",
            context={"field": "imponibile"},
        )

        data_movimento = payload.get("data_movimento")
        ErrorManager.require(
            bool(data_movimento),
            code=E_ANAG_VALIDAZIONE, message=_MESSAGE,
            detail="data_movimento obbligatoria.",
            context={"field": "data_movimento"},
        )

        # ⚠️ Il motivo lo pretende gia' `chk_stiva_movimenti_motivo_forzatura`, e
        #    lo si chiede QUI per nominare il campo invece di uno SQLSTATE. Ed e'
        #    il campo che rende una forzatura leggibile a distanza di mesi: senza,
        #    resta un numero che qualcuno ha messo li'.
        motivo = payload.get("motivo")
        motivo = motivo.strip() if isinstance(motivo, str) else ""
        ErrorManager.require(
            bool(motivo),
            code=E_ANAG_VALIDAZIONE,
            message="La forzatura richiede un motivo: e' la traccia del perche'.",
            context={"field": "motivo"},
        )

        movimento_id = self._repo.create_forzatura(
            titolo_id,
            imponibile=valore,
            data_movimento=data_movimento,
            motivo=motivo,
        )
        return {"id": movimento_id}

    # Scopo: Annulla un movimento del registro — obiettivo, perimetro, esito.
    #
    #        Obiettivo: correggere una forzatura sbagliata senza cancellarla,
    #        scrivendo il contro-movimento che la annulla (`Q7`).
    #
    #        Perimetro: il titolo dev'essere di QUESTO soggetto (le rotte sono
    #        annidate, e senza il check l'id di un titolo altrui sarebbe
    #        annullabile passando dal soggetto sbagliato) e il movimento
    #        dev'essere di QUESTO titolo — stessa ragione, un livello sotto.
    #
    #        Esito: l'id del contro-movimento creato.
    #
    # ⛔ LE PRECONDIZIONI NON SI RICOPIANO QUI. Sono cinque — non trovato, non
    #    e' una forzatura, e' esso stesso un annullo, gia' annullato, porterebbe
    #    il plafond sotto zero — e vivono in
    #    `script.fn_check_annullo_movimento_titolo_iva`, che e' la stessa
    #    funzione da cui la vista prende il motivo per spegnere il pulsante.
    #    Riscriverle qui vorrebbe dire che il tooltip e il rifiuto possono
    #    divergere: e' esattamente il difetto che quella funzione esiste per
    #    togliere.
    # ⚠️ Il MOTIVO si chiede qui e non si lascia al `CHECK`: nominare il campo
    #    vale piu' di uno SQLSTATE, ed e' la traccia del perche' — la stessa
    #    ragione per cui lo chiede la forzatura che si sta annullando.
    def annulla_movimento(
        self, soggetto_id: str, titolo_id: int, movimento_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_titolo(soggetto_id, titolo_id)

        # ⛔ Senza `limit`: qui il registro serve per VERIFICARE che il
        #    movimento appartenga a questo titolo, e un controllo di
        #    appartenenza su una pagina guarda meta' delle righe.
        righe, _totale = self._repo.list_movimenti(titolo_id)
        movimenti = {int(m["id"]): m for m in righe}
        ErrorManager.require(
            movimento_id in movimenti,
            code=E_ANAG_NOT_FOUND,
            message="Movimento non trovato su questo titolo.",
            detail=f"movimento_id={movimento_id}",
        )

        motivo = payload.get("motivo")
        motivo = motivo.strip() if isinstance(motivo, str) else ""
        ErrorManager.require(
            bool(motivo),
            code=E_ANAG_VALIDAZIONE,
            message="L'annullo richiede un motivo: e' la traccia del perche'.",
            context={"field": "motivo"},
        )

        return {"id": self._repo.annulla_movimento(movimento_id, motivo=motivo)}

    # =================================================================
    # Helper privati
    # =================================================================

    # Scopo: Il titolo esiste ED e' di questo soggetto.
    # ⚠️ L'ownership check non e' burocrazia: le rotte sono annidate sotto il
    #    soggetto, e senza questo controllo l'id di un titolo di un ALTRO
    #    soggetto (dentro lo stesso perimetro emittente, quindi visibile alla
    #    RLS) sarebbe modificabile passando dal soggetto sbagliato.
    def _require_titolo(self, soggetto_id: str, titolo_id: int) -> dict[str, Any]:
        titolo = require_found(
            self._repo.get_titolo(titolo_id), "Titolo IVA non trovato.",
        )
        ErrorManager.require(
            str(titolo["soggetto_id"]) == str(soggetto_id),
            code=E_ANAG_NOT_FOUND,
            message="Titolo IVA non trovato.",
            detail="Il titolo non appartiene al soggetto indicato.",
        )
        return titolo

    # Scopo: RISTRETTO con zero righe di ambito (Q2). Non e' un errore: e' lo
    #        stato intermedio che il DB ammette apposta, e che il risolutore
    #        legge come «nessun articolo nell'ambito» lasciando l'aliquota
    #        ordinaria — la direzione sicura.
    # ⚠️ Il conteggio arriva dalla stessa query che ha portato il titolo
    #    (`ambiti_count`): chiederlo a giro sarebbe un N+1 sulla lista.
    @staticmethod
    def _ambito_incompleto(titolo: dict[str, Any]) -> bool:
        return (
            titolo.get("ambito") == "RISTRETTO"
            and int(titolo.get("ambiti_count") or 0) == 0
        )

    # Scopo: Normalizza il payload del titolo verso le colonne.
    def _normalizza_titolo(self, payload: dict[str, Any]) -> dict[str, Any]:
        dati: dict[str, Any] = {}
        # Guard simmetrico: le colonne NOT NULL, se il payload le tocca, devono
        # portare un valore. Vale in create e in update — in create il campo
        # potrebbe arrivare valorizzato ma vuoto, che i guard di obbligatorieta'
        # gia' prendono; qui si chiude il caso della PATCH che le svuota.
        for key in _NON_ANNULLABILI:
            if key in payload:
                ErrorManager.require(
                    payload[key] not in (None, ""),
                    code=E_ANAG_VALIDAZIONE,
                    message=_MESSAGE,
                    detail=f"{key} non puo' essere svuotato.",
                    context={"field": key},
                )
        for key in ("tipo_titolo_iva_id", "iva_id"):
            if key in payload:
                dati[key] = payload[key]
        if "ambito" in payload:
            ambito = payload["ambito"]
            ambito = ambito.strip().upper() if isinstance(ambito, str) else ambito
            ErrorManager.require(
                ambito in _AMBITI,
                code=E_ANAG_VALIDAZIONE, message=_MESSAGE,
                detail=f"ambito deve essere uno tra: {', '.join(sorted(_AMBITI))}.",
                context={"field": "ambito"},
            )
            dati["ambito"] = ambito
        for key in ("valido_dal", "valido_al", "data_ricezione"):
            if key in payload:
                dati[key] = payload[key] or None
        # ⚠️ Stringa vuota -> NULL (`feedback_null_vs_empty`): un protocollo ''
        #    sarebbe un estremo documentale che SEMBRA esserci.
        for key in ("protocollo", "riferimento", "note"):
            if key in payload:
                val = payload[key]
                dati[key] = val.strip() or None if isinstance(val, str) else val
        if "plafond" in payload:
            val = payload["plafond"]
            dati["plafond"] = None if val in (None, "") else val
        if "attivo" in payload:
            dati["attivo"] = _V.require_bool(payload, "attivo")
        return dati

    # Scopo: Normalizza una riga di ambito: valorizza la colonna del livello
    #        dichiarato e AZZERA le altre due.
    # ⚠️ L'azzeramento non e' cortesia: `chk_soggetti_titoli_iva_ambiti_livello`
    #    pretende che le altre due siano NULL, e un payload che le porta tutte e
    #    tre valorizzate diventerebbe un 23514 che nomina un vincolo invece del
    #    campo sbagliato.
    @staticmethod
    def _normalizza_ambito(payload: dict[str, Any]) -> dict[str, Any]:
        livello = payload.get("livello")
        livello = livello.strip().upper() if isinstance(livello, str) else livello
        ErrorManager.require(
            livello in _LIVELLI_AMBITO,
            code=E_ANAG_VALIDAZIONE,
            message="Livello di ambito non ammesso.",
            detail=f"Ammessi: {', '.join(sorted(_LIVELLI_AMBITO))}.",
            context={"field": "livello"},
        )
        assert isinstance(livello, str)
        colonna = _LIVELLI_AMBITO[livello]
        valore = payload.get(colonna)
        ErrorManager.require(
            valore not in (None, ""),
            code=E_ANAG_VALIDAZIONE,
            message="Ambito incompleto: manca l'oggetto del livello scelto.",
            detail=f"livello={livello} richiede {colonna}.",
            context={"field": colonna},
        )
        dati: dict[str, Any] = {"livello": livello, colonna: valore}
        note = payload.get("note")
        dati["note"] = note.strip() or None if isinstance(note, str) else note
        return dati
