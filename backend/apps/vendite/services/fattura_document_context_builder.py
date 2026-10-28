# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione concreta `DocumentContextBuilder` per la
#        sorgente FATTURA (stampa/ristampa della fattura). Compone il
#        dizionario di contesto consumato dal template HTML del motore
#        documentale (render_service.render_pdf).
#
#        Sesto dominio cablato sul motore `documenti` dopo
#        preventivo/offerta/contratto/ordine/DDT (clone strutturale di
#        `ordine_document_context_builder`, regola del 2 — memoria
#        feedback_regola_del_2_estrai_bb). Differenze FATTURA:
#         - `CODE = "FATTURA"` (= config.sorgenti.codice_interno + tipo
#           documento + colonna `template_documenti.context_builder_code`,
#           tutti allineati, sorgente id 10);
#         - la fattura NON si "emette" da UI: è già prodotta dalla pipeline
#           di fatturazione. Il builder alimenta solo stampa/ristampa (nessuna
#           transizione di stato → la view factory è istanziata SENZA emetti);
#         - testata, riepilogo IVA e scadenze da `VenditeRepository`; le
#           righe da `FattureRepository.list_righe`, la lettura completa della
#           STESSA vista della lista a video (`vw_fattura_righe_lista`);
#         - `riepilogo_iva` letto dalla tabella REALE
#           `vendite.fatture_riepiloghi_iva` (non da una vista derivata come
#           per gli ordini): la fattura fissa il riepilogo fiscale al momento
#           dell'emissione, il builder lo legge tale e quale.
#
#        Confine v1 (allineato agli altri domini):
#         - il builder NON applica scope/permessi: responsabilità del caller
#           (view di dominio con permessi `vendite_*` nel path web; canale
#           l'identita' dell'utente tecnico nel path worker C-2b);
#         - il builder NON conosce il template HTML: fornisce solo dati
#           strutturati formattabili lato Jinja; nessun calcolo fiscale in
#           Python (imponibile/imposta/totali sono già mantenuti dalla
#           pipeline sulle tabelle fattura).
#
#        ⭐ FORMA 2 dal 2026-09-30 (brief-db-documenti-versione-contesto-
#        template §11): `righe` e' il SOLO primo livello del documento
#        (NORMALE, PARTE_PLAFOND, KIT_PADRE) e un kit porta i suoi componenti
#        esposti DENTRO la riga (`riga.componenti`, lista, vuota fuori dai
#        kit). Nella forma 1 le righe erano in fila da `vw_fattura_righe_
#        esposte` e il componente si riconosceva da `tipo_riga`: una versione
#        di template scritta per la forma 1 su questi dati stamperebbe la
#        fattura SENZA i componenti, e il patto versione/forma lo impedisce.
#        Chiavi di riga: quelle della vista (`riga_key`, `fatture_righe_id`,
#        `riga_rettificata_documento` parlante…); via `id`, `livello` e
#        `riga_rettificata_fattura_numero` della forma 1.
#
#        ⭐ FORMA 3 dal 2026-10-02 (brief-db-esposizione-componenti-kit-in-
#        fattura, R-BE-7): un componente porta il suo modo (`esposizione`:
#        DESCRITTIVO | VALORIZZATO) e, se VALORIZZATO, `prezzo_unitario`,
#        `sconto_percentuale` e `importo_riga` suoi, FUORI dal totale del
#        padre; un padre senza resto (tutti valorizzati) ha `importo_riga`
#        NULL. Una versione scritta per la forma 2 su questi dati stamperebbe
#        il kit senza l'importo dei valorizzati e la fattura non tornerebbe
#        coi totali: per questo e' una forma nuova, non chiavi in piu'.
#
#        ⭐ FORMA 4 dal 2026-10-02 (brief-db-esigibilita-iva-per-cassa-
#        emittente §11, R-3): `annotazioni`, la lista `{codice, testo}` delle
#        annotazioni di legge del documento (oggi l'IVA per cassa, art. 32-bis
#        DL 83/2012), nell'ordine dato da `vendite.fn_annotazioni_fattura`;
#        lista vuota quando non ce ne sono. Le decide il database: una
#        versione scritta per la forma 3 stamperebbe una fattura RF17 senza
#        l'annotazione obbligatoria, ed e' per questo una forma nuova.
#
#        ⭐ FORMA 5 dal 2026-10-02 (brief-db-bom-flag-quantita-e-kit-in-
#        fattura, R-BE-B6): una riga di primo livello porta il suo periodo —
#        `competenza_dal`, `competenza_al` (date in italiano, con le gemelle
#        `_iso`) e `ha_periodo`, vero quando `dal != al` (D-3.1: la regola e'
#        della vista, qui si trasporta). Lo stesso kit su due periodi sono
#        due righe, e la quantita' del kit e' quella della riga padre del
#        documento: NULL quando i componenti non dicono lo stesso numero di
#        kit (nota di credito parziale), insieme al prezzo. Una versione
#        scritta per la forma 4 stamperebbe due righe identiche per due mesi
#        diversi, e un kit senza quantita' come se l'avesse: forma nuova.
#
#        ⭐ FORMA 6 dal 2026-10-28 (brief-modello-documento-vendita §15.16,
#        D-S1): `fattura.origini`, la catena dei documenti di origine nell'
#        ordine di `vendite.fn_fattura_origini` (la stessa del dettaglio a
#        video), lista di `{livello, tipo, etichetta, codice}`, vuota se la
#        fattura non cita niente. Via `fattura.origine` ({codice, tipo}, mai
#        popolata): una versione scritta per la forma 5 la leggerebbe e il
#        render StrictUndefined si fermerebbe, per questo e' una forma nuova.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.config.sorgenti import SORGENTE_FATTURA
from apps.core.services.testata_guard import testata_o_not_found
from apps.core.services.payload_helpers import PayloadValidator
from apps.documenti.services.context_builders._number_formatting import (
    format_importo,
    format_misura,
    formatta_campi,
)
from apps.documenti.services.context_builders._date_formatting import (
    format_date_it,
    format_date_iso,
)
from apps.documenti.services.context_builders.base import (
    DocumentContextBuilder,
)
from apps.documenti.services.context_builders.registry import register_builder
from apps.vendite.db.fatture_repository import FattureRepository
from apps.vendite.db.vendite_repository import VenditeRepository

E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"


class FatturaDocumentContextBuilder(DocumentContextBuilder):
    """Builder di contesto per documenti FATTURA (stampa/ristampa fattura)."""

    CODE = SORGENTE_FATTURA
    # La forma dei dati prodotti: sede unica (vedi DocumentContextBuilder).
    CONTEXT_VERSION = 6

    # Scopo: Iniezione opzionale dei repository per testabilità (mock). In
    #        runtime il default va benissimo: l'istanza è singleton di processo
    #        (registry).
    def __init__(
        self,
        repo: VenditeRepository | None = None,
        righe_repo: FattureRepository | None = None,
    ) -> None:
        self._repo = repo or VenditeRepository()
        self._righe_repo = righe_repo or FattureRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # Scopo: Costruisce il dict di contesto a partire dall'id della fattura.
    #        Pipeline:
    #         1. guard id positivo;
    #         2. testata via `get_fattura_testata` (None → NOT_FOUND);
    #         3. righe (primo livello, kit coi componenti dentro) + riepilogo
    #            IVA (tabella reale fatture_riepiloghi_iva) + annotazioni di
    #            legge (decise dal DB) + origini (catena dal DB);
    #         4. compone la shape della forma `CONTEXT_VERSION` (6).
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")

        testata = testata_o_not_found(
            self._repo.get_fattura_testata, sorgente_id,
            code=E_NOT_FOUND, message="Fattura non trovata per generazione documento.",
            id_name="fattura_id", function_name="FatturaDocumentContextBuilder.build",
        )

        # Numeri pronti per la stampa (2026-08-04): dal repository arrivano
        # con la scala della colonna (`7.000000`), qui prendono il formato
        # italiano. Misure e importi seguono due regole diverse — vedi
        # `_number_formatting`.
        righe = [
            self._shape_riga(r) for r in self._righe_repo.list_righe(sorgente_id)
        ]
        riepilogo_iva = [
            formatta_campi(
                r,
                importi=("iva_aliquota", "imponibile", "imposta", "arrotondamento",
                         "totale_riga"),
            )
            for r in self._repo.list_fattura_riepilogo_iva(sorgente_id)
        ]
        scadenze = self._repo.list_fattura_scadenze(sorgente_id)
        annotazioni = [
            {"codice": a["codice"], "testo": a["testo"]}
            for a in self._repo.list_fattura_annotazioni(sorgente_id)
        ]
        # Dopo il cancello della testata: il lettore e' INVOKER (vedi
        # `list_fattura_origini`).
        origini = [
            self._shape_origine(o) for o in self._repo.list_fattura_origini(sorgente_id)
        ]

        return {
            "fattura": self._shape_fattura(testata, origini),
            "cliente": self._shape_cliente(testata),
            "righe": righe,
            "riepilogo_iva": riepilogo_iva,
            "scadenze": [self._shape_scadenza(s) for s in scadenze],
            "annotazioni": annotazioni,
            # `_meta`: parametri di rendering stabili a parità di chiamata
            # (locale, utente). NON inserire qui timestamp/random: il
            # `context_hash` deve restare deterministico per il dedup logico
            # (orchestrator). Il tempo di generazione è tracciato lato DB da
            # `documenti_generati.generato_at`.
            "_meta": {
                "locale": locale,
                "auth_user_id": auth_user_id,
                "context_version": self.CONTEXT_VERSION,
                "context_code": self.CODE,
            },
        }

    # =================================================================
    # Helpers privati di shaping
    # =================================================================

    # Scopo: Estrae il sotto-dict "fattura" stabile dalla testata (numero
    #        fiscale, date IT/ISO, stato/tipo doc fiscale, emittente, totali).
    #        I totali sono raggruppati in una shape esplicita per il template
    #        (`fattura.totali.imponibile`).
    def _shape_fattura(
        self, testata: dict[str, Any], origini: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "id": testata.get("id"),
            "uid": testata.get("uid"),
            "numero": testata.get("numero"),
            "serie": testata.get("serie"),
            "anno": testata.get("anno"),
            "data": format_date_it(testata.get("data")),
            "data_iso": format_date_iso(testata.get("data")),
            "data_contabilizzazione": format_date_it(
                testata.get("data_contabilizzazione")
            ),
            "tipo_doc": {
                "id": testata.get("tipo_doc_fiscale_id"),
                "codice_interno": testata.get("tipo_doc_fiscale_codice"),
                "descrizione": testata.get("tipo_doc_fiscale_descrizione"),
            },
            "stato": {
                "id": testata.get("stato_doc_fiscale_id"),
                "codice_interno": testata.get("stato_codice_interno"),
                "descrizione": testata.get("stato_descrizione"),
            },
            # Intestazione emittente (chi emette la fattura): dallo SNAPSHOT
            # congelato `fatture.emittente_snapshot` (Fase 2 satelliti,
            # 2026-07-31 — ristampa conforme: l'anagrafica puo' cambiare, il
            # documento no). Le chiavi piatte sono derivate dal jsonb in
            # `get_fattura_testata`; `sede` e' il display dell'indirizzo
            # annidato, risolto a DB sui due layer RUOLO→SOGGETTO al momento
            # dello snapshot. `piva` = id fiscale univoco (P.IVA per le
            # imprese); `cf` = codice fiscale. Tutto None se lo snapshot manca
            # (fattura pre-Fase 1): nessun fallback per decisione (§9 piano).
            "emittente": {
                "id": testata.get("emittente_fiscale_id"),
                "codice": testata.get("emittente_fiscale_codice"),
                "denominazione": testata.get("emittente_denominazione"),
                "piva": testata.get("emittente_piva"),
                "cf": testata.get("emittente_cf"),
                "sede": testata.get("emittente_sede"),
            },
            "bollo_applicato": testata.get("bollo_applicato"),
            "totali": {
                "imponibile": format_importo(testata.get("imponibile_tot"), campo="imponibile_tot"),
                "imposta": format_importo(testata.get("imposta_tot"), campo="imposta_tot"),
                # alias `iva` (nome usato dal template) dell'imposta totale
                "iva": format_importo(testata.get("imposta_tot"), campo="imposta_tot"),
                "sconto": format_importo(testata.get("sconto_tot"), campo="sconto_tot"),
                "bollo": format_importo(testata.get("bollo_importo"), campo="bollo_importo"),
                "arrotondamento": format_importo(testata.get("arrotondamento_attuale"), campo="arrotondamento_attuale"),
                "documento": format_importo(testata.get("totale_doc"), campo="totale_doc"),
                "a_pagare": format_importo(testata.get("totale_a_pagare"), campo="totale_a_pagare"),
                "valuta_codice": testata.get("valuta_codice"),
                # Il tasso di cambio e' una MISURA, non denaro: `1.00000000`
                # si legge «1,00», ma un cambio 0,8732 conserva le sue cifre.
                "tasso_cambio": format_misura(testata.get("tasso_cambio"), campo="tasso_cambio"),
            },
            # Campi «ricchi» del template. Chiavi SEMPRE presenti (StrictUndefined
            # → chiave mancante = errore); il template le guarda con {% if %},
            # quindi None = riga omessa. `agente` NON e' mantenuto come dato
            # di testata di questa fattura (reseller a NULL) → resta None
            # finché il flusso a monte non lo popola (documentato nel brief).
            # `pagamento` è sorgentato (JOIN sotto).
            "agente_denominazione": testata.get("agente_denominazione"),
            # Forma 6: la lista, `[]` se la fattura non cita niente.
            "origini": origini,
            "pagamento": {
                "modalita_codice": testata.get("pagamento_modalita_codice"),
                "termine_codice": testata.get("pagamento_termine_codice"),
            },
            # Utility del servizio fatturato (dal billing account → config.utilities).
            "utility": {
                "codice": testata.get("utility_codice"),
                "descrizione": testata.get("utility_descrizione"),
            },
            "meta": testata.get("meta") or {},
        }

    # Scopo: Un documento di origine, con le chiavi della forma 6. `tipo` e'
    #        il codice interno del tipo (stabile), `etichetta` il nome da
    #        stampare; `codice` puo' essere None. Niente id ne' uid: il
    #        modello stampa, non naviga.
    @staticmethod
    def _shape_origine(origine: dict[str, Any]) -> dict[str, Any]:
        return {
            "livello": origine["livello"],
            "tipo": origine["tipo_codice_interno"],
            "etichetta": origine["etichetta"],
            "codice": origine["codice"],
        }

    # Scopo: Sotto-dict "cliente" dallo SNAPSHOT congelato
    #        `fatture.cliente_snapshot` (chiavi piatte derivate in
    #        `get_fattura_testata`) + indirizzo di fatturazione dalla riga
    #        `FATT` del satellite `fatture_indirizzi`. Ristampa conforme:
    #        nessuna lettura live dell'anagrafica.
    #        ⚠️ `billing_account_id`/`ba_codice` sono il BA *padre* (D-P), non
    #        il conto del consumatore nelle gerarchie.
    def _shape_cliente(self, testata: dict[str, Any]) -> dict[str, Any]:
        return {
            "soggetto_ruolo_id": testata.get("cliente_soggetto_ruolo_id"),
            "soggetto_id": testata.get("soggetto_id"),
            "denominazione": testata.get("ragione_sociale_completa"),
            "id_fiscale": testata.get("id_fiscale_univoco_cf_piva"),
            # Display dello snapshot FATT congelato. None se assente (fattura
            # pre-snapshot, nessun fallback — §9); chiave sempre presente
            # (StrictUndefined); il template la guarda con {% if %}.
            "indirizzo": testata.get("cliente_indirizzo"),
            "billing_account_id": testata.get("billing_account_id"),
            "ba_codice": testata.get("ba_codice"),
        }

    # Scopo: Una riga di primo livello, coi numeri pronti per la stampa, e i
    #        componenti esposti di un kit come LISTA (`[]` fuori dai kit: il
    #        template scorre `riga.componenti` senza chiedersi se c'e').
    #        `componenti` arriva gia' decodificato dal repository
    #        (il lettore comune decodifica i jsonb): NULL fuori dai kit. Forma 3: i numeri di un
    #        componente seguono le regole della riga (prezzo e sconto come
    #        misure, importo come importo); su un DESCRITTIVO sono NULL e
    #        restano NULL — e' cio' che dice al template «nel totale del kit».
    #        Forma 5: il periodo della riga, e `quantita`/`prezzo_unitario`
    #        NULL su un kit che non ha una quantita' (restano NULL: il
    #        formattatore li preserva).
    def _shape_riga(self, riga: dict[str, Any]) -> dict[str, Any]:
        r = formatta_campi(
            riga,
            misure=("quantita", "prezzo_unitario", "sconto_percentuale"),
            importi=("iva_aliquota", "importo_riga"),
        )
        # Le date escono come stringhe, come quelle di testata: il contesto
        # si serializza (hash, ristampa fedele) e il template non formatta.
        # ⛔ Lettura STRETTA (`riga[...]`, non `.get`): le tre colonne sono
        #    del contratto di `vw_fattura_righe_lista`, e una colonna sparita
        #    o rinominata deve fermare la stampa — con `.get` diventerebbe
        #    «nessun periodo» su ogni riga, senza nessun errore.
        for campo in ("competenza_dal", "competenza_al"):
            valore = riga[campo]
            r[campo] = format_date_it(valore)
            r[f"{campo}_iso"] = format_date_iso(valore)
        # ⛔ Non si ricalcola: «si stampa il periodo quando dal != al» e' la
        #    regola della vista (D-3.1), e una copia qui potrebbe divergere.
        r["ha_periodo"] = bool(riga["ha_periodo"])
        r["componenti"] = [
            formatta_campi(
                dict(c),
                misure=("quantita", "prezzo_unitario", "sconto_percentuale"),
                importi=("importo_riga",),
            )
            for c in (r.get("componenti") or [])
        ]
        return r

    # Scopo: Sotto-dict "scadenza" (rata del piano pagamenti). Chiavi stabili
    #        attese dal template (`nr`/`data`/`importo`/`modalita_codice`); tutte
    #        presenti (il motore usa StrictUndefined → una chiave mancante è
    #        errore di render). `modalita_codice` dal jsonb meta se presente.
    def _shape_scadenza(self, s: dict[str, Any]) -> dict[str, Any]:
        meta = s.get("meta") or {}
        return {
            "nr": s.get("numero_rata"),
            "data": format_date_it(s.get("data_scadenza")),
            "data_iso": format_date_iso(s.get("data_scadenza")),
            "importo": format_importo(s.get("importo"), campo="importo"),
            "modalita_codice": meta.get("modalita_codice"),
        }


# Registrazione esplicita: l'import del modulo (triggerato da
# `VenditeConfig.ready()`) popola il registry. Niente auto-discovery via signal.
register_builder(FatturaDocumentContextBuilder())
