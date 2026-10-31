# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestrazione per grouping e generazione righe fattura.
# ------------------------------------------------------------


import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.commesse_repository import TIPO_MOVIMENTO_RETTIFICA
from apps.vendite.db.pipeline_repository import (
    AttivitaDaFatturare,
    GroupAttivitaInput,
    VenditePipelineRepository,
)
from apps.vendite.services import _kit_meta as kit_meta
from apps.vendite.types import GroupAttivitaKey

# Il nome con cui la generazione delle righe firma i suoi errori.
_FN_GENERA = "vendite.fatture_righe_service.generate_fatture_righe"

# Servizio applicativo che porta in Python il grouping e la generazione righe
# fattura. È l'implementazione IN ESERCIZIO: il task `generate_fatture_righe`
# della pipeline passa di qui (`pipeline_step_executor`), non dalla funzione SQL
# omonima. Vedi docs/it/backend/vendite/manual/fn_generate_fatture_righe.md.


# Snapshot di esposizione kit congelato sulla riga di fattura alla generazione.
# Tutto già risolto dal push nel `meta` dell'attività: nessuna risoluzione di
# distinta base a valle (lo stesso componente può appartenere a più kit, solo il
# documento sorgente sa quale è stato venduto).
@dataclass(frozen=True)
class _KitSnapshot:
    key: str | None = None
    articolo_padre_id: str | None = None
    # Codice di `config.esposizioni_componente`; None sulle righe sciolte.
    esposizione: str | None = None
    # La UoM della riga PADRE del documento (`fatture_righe.kit_uom_id`): e'
    # del kit, non dell'attivita', quindi entra nel bucket come il padre.
    uom_padre_id: int | None = None


# Accumulatore di un gruppo di attività destinate a UNA riga di fattura.
@dataclass
class _GruppoRiga:
    fattura_id: int
    group_key: GroupAttivitaKey
    kit: _KitSnapshot
    articolo_id: str
    descrizione: str | None
    # Il codice a video dell'articolo: NON entra nella chiave di gruppo (due
    # attivita' dello stesso `articolo_id` hanno lo stesso codice per
    # costruzione) — serve solo all'ORDINAMENTO, che deve essere leggibile.
    articolo_codice: str | None = None
    qta_totale: Decimal = Decimal(0)
    # Somma della quantita' PADRE sulle attivita' del gruppo, come `qta_totale`
    # somma quella del componente; None sulle righe fuori dal kit.
    kit_qta_totale: Decimal | None = None
    # Il periodo della riga (`competenza_dal/_al`, NOT NULL): quello della
    # chiave se l'attivita' ne ha uno, altrimenti la data piu' recente fra le
    # attivita' aggregate (D-3.1). Lo risolve `_aggrega`.
    competenza_dal: date | None = None
    competenza_al: date | None = None
    # Vero se il periodo e' quello di una riga PUNTUALE (la data piu'
    # recente): e' il solo che `_allinea_periodo_kit` puo' spostare.
    periodo_puntuale: bool = False
    attivita_ids: list[int] = field(default_factory=list)


class FattureRigheService:
    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Gestisce `group_attivita_fatturabili` nel flusso applicativo del modulo.
    def group_attivita_fatturabili(self, attivita_id: int) -> GroupAttivitaKey:
        ErrorManager.require(
            attivita_id is not None,
            code="E_GROUP_ATTIVITA_VALIDATION",
            message="Parametro attivita non valido.",
            detail="attivita_id obbligatorio",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
            log_to_db=True,
        )
        assert attivita_id is not None
        row = self.repository.get_group_attivita_input(attivita_id)
        ErrorManager.require(
            row is not None,
            code="E_GROUP_ATTIVITA_NOT_FOUND",
            message="Attivita fatturabile non trovata.",
            detail=f"Attivita non trovata: {attivita_id}",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
            log_to_db=True,
        )
        assert row is not None
        _richiedi_dati_attivita(
            row.dest_billing_account_id is not None,
            detail=f"dest_billing_account_id mancante per attivita: {attivita_id}",
            context={"attivita_id": attivita_id},
            function_name="vendite.fatture_righe_service.group_attivita_fatturabili",
        )
        fn = "vendite.fatture_righe_service.group_attivita_fatturabili"
        self._guard_coerenza_rettifica(row, function_name=fn)
        # ⚠️ La facade risolve l'IVA come il giro vero, ma su un contesto
        #    RIDOTTO: qui l'attività può non avere ancora una testata, quindi il
        #    cliente è il suo billing account e la data è quella dell'attività.
        #    ⛔ L'AUTORITÀ resta `generate_fatture_righe`, che legge cliente,
        #    emittente e data dalla TESTATA. Questo entrypoint esiste per
        #    ispezionare la chiave di una singola attività, e va letto per
        #    quello: su un'attività la cui fattura porta una data diversa, le
        #    due risposte possono legittimamente non coincidere.
        iva_id = self._risolvi_iva_diagnostica(row, function_name=fn)
        return self._build_group_key(row, iva_id=iva_id)

    # Scopo: l'IVA per la sola facade di ispezione. Vedi l'avvertenza sopra.
    def _risolvi_iva_diagnostica(
        self, row: GroupAttivitaInput, *, function_name: str
    ) -> int | None:
        if row.fattura_riga_rettificata_id is not None:
            return row.rett_iva_id
        from apps.anagrafiche.db.billing_account_repository import (
            BillingAccountRepository,
        )
        from apps.vendite.services.iva_resolver_service import IvaResolverService

        ba_id = row.dest_billing_account_id
        emittente_id = BillingAccountRepository().get_emittente_fiscale_id(int(ba_id))
        _richiedi_dati_attivita(
            emittente_id is not None,
            detail=(
                f"emittente fiscale non risolvibile per il billing account {ba_id}: "
                "il trattamento IVA non e' determinabile"
            ),
            context={"attivita_id": row.attivita_id},
            function_name=function_name,
        )
        assert emittente_id is not None
        resolver = IvaResolverService()
        parte = resolver.risolvi_anteprima(
            articolo_id=str(row.articolo_id),
            billing_account_id=int(ba_id),
            emittente_fiscale_id=int(emittente_id),
            data_riferimento=row.data_attivita,
        )
        return parte.get("iva_id")

    # Scopo: Il cartellino `tipo_movimento` e il puntatore
    #        `fattura_riga_rettificata_id` sono una COPPIA, e il guard e'
    #        simmetrico su entrambi i versi (disciplina normalize+guard delle
    #        coppie flag/valore):
    #          RETTIFICA senza puntatore → la riga di nota di credito nascerebbe
    #            gemella di nessuna, con prezzo e sconto presi da un'attivita'
    #            che non li ha (brief nota di credito §12.6);
    #          puntatore senza RETTIFICA → il prezzo verrebbe copiato dal
    #            documento su una riga che si dichiara normale, e nessuno
    #            saprebbe perche' quel prezzo non e' quello dell'attivita'.
    # Perimetro: la regola vive QUI e non nei due chiamanti — il giro della
    #        pipeline e la facade `group_attivita_fatturabili` — perche' scritta
    #        due volte divergerebbe, ed e' un invariante su documenti fiscali.
    #        La madre `fn_accredita_riga_reso` scrive sempre i due insieme: se
    #        arrivano scompagnati la catena si e' rotta a monte, e fermarsi e'
    #        l'unica cosa onesta.
    @staticmethod
    def _guard_coerenza_rettifica(row: GroupAttivitaInput, *, function_name: str) -> None:
        e_rettifica_label = row.tipo_movimento == TIPO_MOVIMENTO_RETTIFICA
        e_rettifica_ptr = row.fattura_riga_rettificata_id is not None
        _richiedi_dati_attivita(
            e_rettifica_label == e_rettifica_ptr,
            detail=(
                f"attivita {row.attivita_id}: tipo_movimento="
                f"{row.tipo_movimento} e fattura_riga_rettificata_id="
                f"{row.fattura_riga_rettificata_id} sono incoerenti "
                "(la rettifica porta sempre entrambi)"
            ),
            context={"attivita_id": row.attivita_id},
            function_name=function_name,
        )

    # Scopo: Costruisce GroupAttivitaKey da un GroupAttivitaInput con logica competenza.
    # Perimetro: per una RETTIFICA (nota di credito) prezzo, sconto e IVA NON
    #        vengono dall'attività ma dalla RIGA DI FATTURA che rettifica —
    #        `af.fattura_riga_rettificata_id → fatture_righe` — e non si
    #        ricalcolano mai (N-1: «la nota di credito non può differire da
    #        quanto fatturato»).
    # ⚠️ Oggi i due valori COINCIDONO per costruzione, ed è precisamente il
    #        motivo per cui prendere quello dell'attività non darebbe nessun
    #        sintomo: si vedrebbe solo il giorno in cui divergono, su documenti
    #        già emessi. E lo sconto sull'attività non c'è affatto — la catena
    #        `commesse_attivita`/`attivita_fatturabili` non ha la colonna: senza
    #        questa lettura, «copia esatta compresi gli sconti» non sarebbe
    #        realizzabile senza toccare la catena di TUTTE le fatture.
    # ⛔ `iva_id` E' UN PARAMETRO, e non e' pignoleria di firma: dal 2026-08-31
    #    l'IVA della riga NON sta piu' su `GroupAttivitaInput` — la proiezione ha
    #    smesso di leggere `art.iva_id`, che era la risposta autonoma alla stessa
    #    domanda a cui risponde il risolutore. Passarla esplicitamente rende
    #    IMPOSSIBILE costruire una chiave senza aver risolto: se il campo fosse
    #    rimasto sulla dataclass con un default, un chiamante distratto avrebbe
    #    prodotto righe a IVA `None` senza nessun errore.
    @staticmethod
    def _build_group_key(row: GroupAttivitaInput, *, iva_id: int | None) -> GroupAttivitaKey:
        use_competenza = (
            row.competenza_dal is not None
            and row.competenza_al is not None
            and (
                row.competenza_dal != row.competenza_al
                or row.competenza_dal != row.data_attivita
            )
        )
        assert row.dest_billing_account_id is not None
        e_rettifica = row.fattura_riga_rettificata_id is not None
        return {
            "articolo_id": row.articolo_id,
            "dest_billing_account_id": int(row.dest_billing_account_id),
            "uom_id": row.uom_id,
            # Stringa canonica e non float: il prezzo sta nella chiave di gruppo,
            # ed è ciò che rende l'aggregazione un'identità esatta
            # (Σ(qᵢ×p) = p×Σqᵢ). Su float il raggruppamento sarebbe approssimato.
            "prezzo_unitario": _to_decimal_str(
                row.rett_prezzo_unitario if e_rettifica else row.prezzo_unitario
            ),
            # ⚠️ Sulla RETTIFICA vince la riga rettificata, non il risolutore:
            #    N-1, «la nota di credito non puo' differire da quanto
            #    fatturato». Ri-risolvere qui produrrebbe una gemella con
            #    un'aliquota diversa da quella del documento che corregge.
            "iva_id": row.rett_iva_id if e_rettifica else iva_id,
            "competenza_dal": _to_iso(row.competenza_dal) if use_competenza else None,
            "competenza_al": _to_iso(row.competenza_al) if use_competenza else None,
            "calcolo_qta_padre": row.calcolo_qta_padre,
            "arrotondamento_importi_dec": row.arrotondamento_importi_dec,
            "arrotondamento_quantita_dec": row.arrotondamento_quantita_dec,
            "metodo_arrotondamento_importi": row.metodo_arrotondamento_importi,
            "metodo_arrotondamento_quantita": row.metodo_arrotondamento_quantita,
            "fattura_riga_rettificata_id": row.fattura_riga_rettificata_id,
            # `None` fuori dalla rettifica, non `0`: la riga normale non ha uno
            # sconto da dichiarare, e la INSERT lo fa collassare sul DEFAULT del
            # DB. Scrivere 0 qui cambierebbe la chiave di TUTTE le righe di
            # fattura esistenti senza cambiare niente nel documento.
            "sconto_percentuale": (
                _to_decimal_str(row.rett_sconto_percentuale) if e_rettifica else None
            ),
            # ⛔ Fuori dalla rettifica il contratto SPEZZA: due attività di atti
            # diversi non possono finire nella stessa riga. Sulla rettifica è
            # `None`, e il perché sta accanto al campo in `GroupAttivitaKey` —
            # la gemella è identificata dalla riga che rettifica, che è più
            # specifica del contratto.
            "contratto_id": None if e_rettifica else row.contratto_id,
        }

    # Scopo: l'IVA di ogni attività, risolta dalla SEDE UNICA.
    #        Ritorna `attivita_id -> (iva_id, meta_iva)`.
    # ⭐ CACHE PER (fattura, articolo), e non è un'ottimizzazione opzionale: la
    #    risposta del risolutore dipende da articolo, cliente, emittente e data
    #    — e dentro una fattura gli ultimi tre sono fissi. Senza cache un lotto
    #    massivo farebbe una chiamata per ATTIVITÀ (il limite è 50.000): con la
    #    cache ne fa una per articolo distinto per fattura.
    # ⚠️ Le RETTIFICHE non passano di qui: la loro IVA viene dalla riga di
    #    fattura rettificata (N-1), e chiamare il risolutore darebbe una gemella
    #    con un'aliquota diversa da quella del documento che corregge.
    def _risolvi_iva_attivita(
        self,
        *,
        group_inputs: dict[int, GroupAttivitaInput],
        header_map: dict[int, int],
        attivita_ids: list[int],
        function_name: str,
    ) -> dict[int, tuple[int | None, dict[str, Any]]]:
        from apps.vendite.services.iva_resolver_service import IvaResolverService

        ctx_map = self.repository.batch_get_fattura_iva_context(
            sorted({header_map[a] for a in attivita_ids if a in header_map})
        )
        resolver = IvaResolverService()
        cache: dict[tuple[int, str], tuple[int | None, dict[str, Any]]] = {}
        esito: dict[int, tuple[int | None, dict[str, Any]]] = {}

        for aid in attivita_ids:
            gi = group_inputs.get(aid)
            fattura_id = header_map.get(aid)
            if gi is None or fattura_id is None:
                # Non si solleva QUI: a dirlo con un messaggio leggibile e'
                # il `require` del ciclo di validazione, che nomina l'attivita'.
                continue
            if gi.fattura_riga_rettificata_id is not None:
                esito[aid] = (gi.rett_iva_id, {})
                continue

            chiave = (fattura_id, str(gi.articolo_id))
            if chiave not in cache:
                ctx = ctx_map.get(fattura_id) or {}
                # ⛔ `P3`: senza emittente il calcolo si FERMA. La funzione DB è
                #    `SECURITY INVOKER` e legge una tabella con RLS: senza
                #    contesto emittente legge zero titoli e risponde con
                #    l'aliquota ordinaria SENZA sollevare. Non è una lista più
                #    corta — è un'imposta applicata dove non andava, su un
                #    documento che nessuno segnalerà.
                _richiedi_dati_attivita(
                    ctx.get("emittente_fiscale_id") is not None,
                    detail=(
                        "emittente fiscale non risolvibile per la fattura "
                        f"{fattura_id}: il trattamento IVA non e' determinabile"
                    ),
                    context={"attivita_id": aid, "fattura_id": fattura_id},
                    function_name=function_name,
                )
                _richiedi_dati_attivita(
                    ctx.get("data_riferimento") is not None,
                    detail=f"fattura {fattura_id} senza data: IVA non determinabile",
                    context={"attivita_id": aid, "fattura_id": fattura_id},
                    function_name=function_name,
                )
                # ⚠️ ANTEPRIMA, cioè SENZA imponibile, ed è deliberato in questa
                #    slice: passando l'importo il risolutore può tornare DUE
                #    parti (plafond che finisce a metà riga), e la riga andrebbe
                #    spezzata. La spezzatura vive nel giro del lotto, dove il
                #    plafond si CONSUMA (`P5`) — qui una proiezione a due parti
                #    sarebbe un numero che invecchia fino alla DEFINITIVA.
                parte = resolver.risolvi_anteprima(
                    articolo_id=str(gi.articolo_id),
                    billing_account_id=ctx["billing_account_id"],
                    emittente_fiscale_id=ctx["emittente_fiscale_id"],
                    data_riferimento=ctx["data_riferimento"],
                )
                cache[chiave] = (parte.get("iva_id"), resolver.meta_riga(parte))
            esito[aid] = cache[chiave]

        return esito

    # Scopo: Estrae dallo `meta` dell'attività lo snapshot di esposizione kit.
    # Perimetro: nessuna risoluzione di distinta base — il push ha già scritto
    # `componente_di` ed `esposizione`. Risultato: snapshot vuoto per le
    # righe normali, valorizzato per i componenti di kit.
    @staticmethod
    def _build_kit_snapshot(attivita: AttivitaDaFatturare) -> _KitSnapshot:
        meta = attivita.meta or {}
        segment = meta.get(kit_meta.META_KEY_SEGMENT_KEY)
        kit_key = kit_meta.kit_key_da_segment(segment)
        if kit_key is None:
            return _KitSnapshot()

        padre_raw = meta.get(kit_meta.META_KEY_COMPONENTE_DI)
        padre = str(padre_raw).strip() if padre_raw is not None else ""
        # R11 — fail-loud. Trattarla come riga normale la farebbe fatturare DUE
        # volte: una dentro il totale del padre e una per conto suo.
        ErrorManager.require(
            bool(padre),
            code="E_ATTIVITA_KIT_SENZA_PADRE",
            message="Attivita componente di kit senza articolo padre.",
            detail=f"componente_di assente nel meta dell'attivita: {attivita.id}",
            context={"attivita_id": attivita.id, "segment_key": segment},
            function_name=_FN_GENERA,
            log_to_db=True,
        )
        # ⛔ Nessun ripiego sulla UoM del componente: su un kit misto
        #    darebbe unita' discordanti nello stesso kit (D-4). Il meta delle
        #    attivita' di prima la riceve dalla correzione una tantum
        #    (R-BE-B5): se manca, la catena e' rotta a monte.
        uom_padre = kit_meta.uom_padre_da_meta(meta)
        _richiedi_dati_attivita(
            uom_padre is not None,
            detail=(
                f"attivita {attivita.id}: componente di kit senza una UoM del padre "
                f"valida ({kit_meta.META_KEY_UOM_PADRE}) nel meta"
            ),
            context={"attivita_id": attivita.id, "segment_key": segment},
            function_name=_FN_GENERA,
        )
        return _KitSnapshot(
            key=kit_key,
            articolo_padre_id=padre,
            esposizione=kit_meta.esposizione_o_default(
                meta.get(kit_meta.META_KEY_ESPOSIZIONE)
            ),
            uom_padre_id=uom_padre,
        )

    # Scopo: La quantita' PADRE che un'attivita' componente di kit rappresenta,
    #        letta dal meta (la scrive il push).
    # ⛔ Fail-loud in due casi, e nessuno dei due ha un ripiego onesto:
    #    - la chiave manca: la riga del kit uscirebbe senza quantita' (la
    #      tabella la rifiuta) o con una inventata;
    #    - il SEGNO non e' quello della quantita' del componente: le due
    #      quantita' descrivono la stessa attivita' (D-NC-2, il segno sta nel
    #      numero). E' il caso di una rettifica il cui meta eredita la quantita'
    #      padre della riga rettificata invece di quella accreditata: scritta
    #      cosi', la nota di credito direbbe «+2 kit» su componenti negativi.
    @staticmethod
    def _kit_qta_attivita(attivita: AttivitaDaFatturare) -> Decimal:
        fn = _FN_GENERA
        meta = attivita.meta or {}
        qta_padre = kit_meta.qta_padre_da_meta(meta)
        _richiedi_dati_attivita(
            qta_padre is not None,
            detail=(
                f"attivita {attivita.id}: componente di kit senza una quantita' del "
                f"padre valida ({kit_meta.META_KEY_QTA_PADRE}) nel meta"
            ),
            context={"attivita_id": attivita.id},
            function_name=fn,
        )
        assert qta_padre is not None
        qta = attivita.quantita or Decimal(0)
        _richiedi_dati_attivita(
            # Un componente a quantita' zero (coeff 0) ha qualunque padre; uno
            # a quantita' non nulla vuole un padre non nullo dello stesso segno
            # (quantita' componente = quantita' padre × coeff, coeff >= 0).
            qta == 0 or (qta_padre != 0 and (qta > 0) == (qta_padre > 0)),
            detail=(
                f"attivita {attivita.id}: quantita' del componente {qta} e quantita' "
                f"del padre {qta_padre} incoerenti (segno opposto o padre a zero)"
            ),
            context={"attivita_id": attivita.id},
            function_name=fn,
        )
        return qta_padre

    # Scopo: Genera le righe fattura del lotto AGGREGANDO le attività fatturabili
    #        per chiave di raggruppamento, e congelando lo snapshot di esposizione
    #        del kit.
    # Perimetro e risultato atteso: una riga di `vendite.fatture_righe` rappresenta
    #        1..n attività che condividono la stessa chiave; `qta` è la somma
    #        ESATTA delle quantità, `prezzo_unitario` è unico per costruzione
    #        perché sta nella chiave. Le attività del gruppo vengono collegate
    #        alla riga via `fattura_riga_id` e marcate fatturate/COMPLETED.
    #        L'importo di riga NON si calcola qui: lo scrive il trigger
    #        `a20_importo` sul DB (requisito D1).
    #        Riferimento: brief-fix-importi-riga-fattura-zero §4.6 (D4) e
    #        §4.7-bis (D5).
    # Round-trip DB: 4 (lista attività, marcatura RUNNING + group inputs, testate,
    #        max riga_nr) + 1 finale (INSERT righe + UPDATE attività in una CTE).
    def generate_fatture_righe(self, lotto_id: int, *, dry_run: bool = False) -> int:
        ErrorManager.require(
            lotto_id is not None,
            code="E_GENERATE_FATTURE_RIGHE_VALIDATION",
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio",
            context={"lotto_id": lotto_id},
            function_name=_FN_GENERA,
            log_to_db=True,
        )
        assert lotto_id is not None

        attivita_list = self.repository.list_attivita_da_fatturare(lotto_id)

        # In dry_run si conta solo: nessuna creazione testata, riga o
        # aggiornamento stato. Il conteggio è sulle ATTIVITÀ elaborate, non sulle
        # righe che verrebbero prodotte: è la grandezza che il chiamante usa per
        # sapere se c'è lavoro da fare.
        if dry_run:
            return len(attivita_list)

        if not attivita_list:
            return 0

        attivita_ids = [a.id for a in attivita_list]
        fn = _FN_GENERA

        with transaction.atomic():
            # 1. Le attività entrano in lavorazione.
            self.repository.mark_attivita_running(lotto_id)

            # 1-bis. La natura del documento dal SEGNO (D-1, §7.9 di brief-db-
            #    contratto-righe-periodiche-in-commessa): un documento che somma
            #    negativo nasce nota di credito, col suo registro e la sua serie.
            #    ⛔ L'ordine e' un requisito: la natura entra nella chiave della
            #    testata, quindi il verbo gira PRIMA delle testate (3), e prima
            #    dei group input, perche' nessuno legga la natura di prima.
            #    La regola e' tutta del DB: qui la chiamata sola.
            self.repository.applica_natura_dal_segno(lotto_id)

            # 2. Batch fetch group inputs (1 round-trip).
            group_inputs = self.repository.batch_get_group_attivita_inputs(attivita_ids)

            # 3. Le TESTATE, e stanno PRIMA delle chiavi dal 2026-08-31 (`I4`).
            #    ⛔ L'ordine è un requisito, non una comodità: l'IVA della riga
            #    ora la risolve il risolutore, che vuole cliente, emittente e
            #    data — cioè tre cose che stanno sulla TESTATA. Costruire le
            #    chiavi prima vorrebbe dire costruirle senza sapere l'IVA.
            #    ⭐ Lo scambio non costa niente: questa chiamata dipende solo da
            #    lotto e attività, mai dalle chiavi.
            header_map = self.repository.batch_get_or_create_fattura_headers(
                lotto_id, attivita_ids
            )
            # ⚠️ Si passano TUTTE le attivita': la condizione «ha un group
            #    input» era scritta due volte — qui come filtro e sotto come
            #    `require` — e due scritture della stessa condizione sono due
            #    cose da tenere d'accordo. A parlare resta il `require`, che e'
            #    quello che produce un errore leggibile invece di un `KeyError`.
            iva_risolta = self._risolvi_iva_attivita(
                group_inputs=group_inputs,
                header_map=header_map,
                attivita_ids=attivita_ids,
                function_name=fn,
            )

            # 4. Validazione per-attività + chiavi di gruppo.
            group_keys: dict[int, GroupAttivitaKey] = {}
            iva_meta_per_attivita: dict[int, dict[str, Any]] = {}
            for aid in attivita_ids:
                gi = group_inputs.get(aid)
                ErrorManager.require(
                    gi is not None,
                    code="E_GROUP_ATTIVITA_NOT_FOUND",
                    message="Attivita fatturabile non trovata.",
                    detail=f"Attivita non trovata: {aid}",
                    context={"attivita_id": aid},
                    function_name=fn,
                    log_to_db=True,
                )
                assert gi is not None
                _richiedi_dati_attivita(
                    gi.dest_billing_account_id is not None,
                    detail=f"dest_billing_account_id mancante per attivita: {aid}",
                    context={"attivita_id": aid},
                    function_name=fn,
                )
                self._guard_coerenza_rettifica(gi, function_name=fn)
                # `chiave` e non `gk`: piu' avanti nella stessa funzione `gk` e'
                # la chiave del GRUPPO in lavorazione, un'altra cosa. Due nomi
                # uguali per due cose diverse nello stesso scope si leggono male
                # e si sbagliano al primo refactor.
                iva_id_risolto, meta_iva = iva_risolta[aid]
                iva_meta_per_attivita[aid] = meta_iva
                chiave = self._build_group_key(gi, iva_id=iva_id_risolto)
                # `attivita_fatturabili.prezzo_unitario` è nullable, ma
                # `fatture_righe.prezzo_unitario` è NOT NULL: senza questo guard
                # l'attività senza prezzo arriverebbe fino all'INSERT e
                # produrrebbe un IntegrityError che non dice quale attività sia.
                # ⚠️ Si guarda il prezzo EFFETTIVO — quello della chiave — e non
                # `gi.prezzo_unitario`: su una rettifica il prezzo è quello
                # della riga di fattura, e guardare il campo sbagliato lascerebbe
                # passare proprio il caso che questo guard esiste per fermare.
                _richiedi_dati_attivita(
                    chiave["prezzo_unitario"] is not None,
                    detail=f"prezzo_unitario mancante per attivita: {aid}",
                    context={"attivita_id": aid},
                    function_name=fn,
                )
                group_keys[aid] = chiave

            # 5. Aggregazione: una riga per gruppo.
            gruppi = self._aggrega(
                attivita_list, group_keys, header_map, group_inputs, function_name=fn
            )

            # 6. riga_nr progressivo per fattura, su ordinamento deterministico
            #    dei gruppi: altrimenti l'ordine delle righe cambierebbe a ogni
            #    rigenerazione dello stesso lotto.
            distinct_fattura_ids = list({g.fattura_id for g in gruppi})
            max_riga_nrs = self.repository.get_max_riga_nrs(distinct_fattura_ids)
            riga_nr_counters: dict[int, int] = {
                fid: max_riga_nrs.get(fid, 0) + 1 for fid in distinct_fattura_ids
            }

            righe_fattura_ids: list[int] = []
            righe_nrs: list[int] = []
            righe_articolo_ids: list[str] = []
            righe_descrizioni: list[str | None] = []
            righe_uom_ids: list[int | None] = []
            righe_qtas: list[Decimal | None] = []
            righe_prezzi: list[Decimal | None] = []
            righe_iva_ids: list[int | None] = []
            righe_dest_ba_ids: list[int] = []
            righe_kit_keys: list[str | None] = []
            righe_kit_esposizioni: list[str | None] = []
            righe_kit_padri: list[str | None] = []
            righe_kit_qtas: list[Decimal | None] = []
            righe_kit_uom_ids: list[int | None] = []
            righe_competenze_dal: list[date] = []
            righe_competenze_al: list[date] = []
            righe_metas: list[str | None] = []
            # Le due colonne della rettifica. Restano piene di `None` su un
            # lotto senza note di credito, che e' il caso normale.
            righe_sconti: list[Decimal | None] = []
            righe_rettificate: list[int | None] = []

            att_ids: list[int] = []
            att_fattura_ids: list[int] = []
            att_riga_nrs: list[int] = []

            for gruppo in gruppi:
                riga_nr = riga_nr_counters[gruppo.fattura_id]
                riga_nr_counters[gruppo.fattura_id] = riga_nr + 1
                gk = gruppo.group_key

                righe_fattura_ids.append(gruppo.fattura_id)
                righe_nrs.append(riga_nr)
                righe_articolo_ids.append(gruppo.articolo_id)
                righe_descrizioni.append(gruppo.descrizione)
                righe_uom_ids.append(gk["uom_id"])
                # Somma ESATTA: `arrotondamento_quantita_dec` è una regola della
                # singola attività, a monte. Applicarla all'aggregato perderebbe
                # precisione dove nessuno la cerca (decisione D4-quantità).
                righe_qtas.append(gruppo.qta_totale)
                righe_prezzi.append(_to_decimal(gk["prezzo_unitario"]))
                righe_iva_ids.append(gk["iva_id"])
                righe_dest_ba_ids.append(gk["dest_billing_account_id"])
                righe_kit_keys.append(gruppo.kit.key)
                righe_kit_esposizioni.append(gruppo.kit.esposizione)
                righe_kit_padri.append(gruppo.kit.articolo_padre_id)
                righe_kit_qtas.append(gruppo.kit_qta_totale)
                righe_kit_uom_ids.append(gruppo.kit.uom_padre_id)
                assert gruppo.competenza_dal is not None
                assert gruppo.competenza_al is not None
                righe_competenze_dal.append(gruppo.competenza_dal)
                righe_competenze_al.append(gruppo.competenza_al)
                righe_sconti.append(_to_decimal(gk["sconto_percentuale"]))
                righe_rettificate.append(gk["fattura_riga_rettificata_id"])
                # ⭐ `iva_origine` e `iva_titolo_id` nel `meta`, come sui
                #    documenti (`P2`): sono i due fatti che nessuno può
                #    ricostruire dopo. Aliquota, natura e riferimento normativo
                #    si DERIVANO da `iva_id` con il JOIN su `config.iva` — e
                #    copiarli produrrebbe una frase che invecchia, che è il
                #    motivo per cui `fatture_righe.iva_perc` è stata tolta.
                # ⚠️ Preso dalla PRIMA attività del gruppo, e non è una scelta
                #    arbitraria: le attività di un gruppo condividono la chiave,
                #    quindi lo stesso `iva_id`, lo stesso articolo e la stessa
                #    fattura — cioè esattamente ciò da cui la risoluzione
                #    dipende.
                meta_riga: dict[str, Any] = {
                    "group_key": gk,
                    "n_attivita": len(gruppo.attivita_ids),
                    "attivita_ids": gruppo.attivita_ids,
                }
                if gruppo.attivita_ids:
                    meta_riga.update(
                        iva_meta_per_attivita.get(gruppo.attivita_ids[0]) or {}
                    )
                righe_metas.append(json.dumps(meta_riga))

                for aid in gruppo.attivita_ids:
                    att_ids.append(aid)
                    att_fattura_ids.append(gruppo.fattura_id)
                    att_riga_nrs.append(riga_nr)

            # 7. INSERT righe + UPDATE attività (1 round-trip CTE, correlazione n→1).
            self.repository.batch_insert_righe_and_mark(
                righe_fattura_ids=righe_fattura_ids,
                righe_nrs=righe_nrs,
                righe_articolo_ids=righe_articolo_ids,
                righe_descrizioni=righe_descrizioni,
                righe_uom_ids=righe_uom_ids,
                righe_qtas=righe_qtas,
                righe_prezzi_unitari=righe_prezzi,
                righe_iva_ids=righe_iva_ids,
                righe_dest_billing_account_ids=righe_dest_ba_ids,
                righe_kit_keys=righe_kit_keys,
                righe_kit_esposizioni=righe_kit_esposizioni,
                righe_kit_articolo_padre_ids=righe_kit_padri,
                righe_kit_qtas=righe_kit_qtas,
                righe_kit_uom_ids=righe_kit_uom_ids,
                righe_competenze_dal=righe_competenze_dal,
                righe_competenze_al=righe_competenze_al,
                righe_sconti=righe_sconti,
                righe_rettificate=righe_rettificate,
                righe_metas=righe_metas,
                att_ids=att_ids,
                att_fattura_ids=att_fattura_ids,
                att_riga_nrs=att_riga_nrs,
            )

        return len(attivita_list)

    # Scopo: Raggruppa le attività in righe di fattura e ne ordina l'esito.
    # L'ordinamento è esplicito (fattura, articolo, competenza, prezzo, uom, kit)
    # e non segue l'ordine di arrivo delle attività: è ciò che rende stabile il
    # `riga_nr` fra due rigenerazioni dello stesso lotto.
    # Risolve anche, per gruppo, il periodo della riga e la quantità padre del
    # kit (somma, come la quantità).
    @staticmethod
    def _aggrega(
        attivita_list: list[AttivitaDaFatturare],
        group_keys: dict[int, GroupAttivitaKey],
        header_map: dict[int, int],
        group_inputs: dict[int, GroupAttivitaInput],
        *,
        function_name: str,
    ) -> list[_GruppoRiga]:
        gruppi: dict[str, _GruppoRiga] = {}
        for attivita in attivita_list:
            gk = group_keys[attivita.id]
            kit = FattureRigheService._build_kit_snapshot(attivita)
            fattura_id = header_map[attivita.id]

            # `kit_key` entra nella chiave: due istanze di kit diverse possono
            # contenere lo stesso componente allo stesso prezzo, e fonderle
            # darebbe una riga che appartiene a due kit e non è esponibile in
            # nessuno dei due (R7).
            bucket = json.dumps(
                {
                    "fattura_id": fattura_id,
                    "group_key": gk,
                    "kit_key": kit.key,
                    "kit_padre": kit.articolo_padre_id,
                    "kit_esposizione": kit.esposizione,
                    "kit_uom_padre": kit.uom_padre_id,
                },
                sort_keys=True,
            )

            gruppo = gruppi.get(bucket)
            if gruppo is None:
                gruppo = _GruppoRiga(
                    fattura_id=fattura_id,
                    group_key=gk,
                    kit=kit,
                    articolo_id=attivita.articolo_id,
                    descrizione=attivita.articolo_descrizione,
                    articolo_codice=attivita.articolo_codice,
                )
                gruppi[bucket] = gruppo

            gruppo.qta_totale += attivita.quantita or Decimal(0)
            if kit.key is not None:
                gruppo.kit_qta_totale = (
                    gruppo.kit_qta_totale or Decimal(0)
                ) + FattureRigheService._kit_qta_attivita(attivita)
            FattureRigheService._accumula_periodo(
                gruppo, group_inputs[attivita.id], function_name=function_name
            )
            gruppo.attivita_ids.append(attivita.id)

        for gruppo in gruppi.values():
            gruppo.attivita_ids.sort()
        FattureRigheService._allinea_periodo_kit(list(gruppi.values()))

        return sorted(gruppi.values(), key=FattureRigheService._chiave_ordinamento)

    # Scopo: Chiave di ordinamento dei gruppi, da cui discende il `riga_nr`.
    # I valori sono confrontati nel LORO tipo — il prezzo come `Decimal`, la uom
    # come intero — perché su stringa `'100' < '5'` e l'ordine delle righe
    # risulterebbe incomprensibile pur restando deterministico. Le competenze
    # sono in formato ISO, dove l'ordine lessicografico coincide con quello
    # cronologico. Il flag `is None` che precede ogni valore opzionale evita il
    # confronto fra `None` e un valore, che solleverebbe `TypeError`.
    @staticmethod
    def _chiave_ordinamento(g: "_GruppoRiga") -> tuple:
        prezzo = _to_decimal(g.group_key["prezzo_unitario"])
        uom_id = g.group_key["uom_id"]
        return (
            g.fattura_id,
            # ⛔ IL CODICE, NON L'UUID. Fino al 2026-08-31 qui c'era
            # `group_key["articolo_id"]`, cioe' l'`id` di `catalogo.articoli`:
            # un UUID. L'ordine era perfettamente deterministico e perfettamente
            # ILLEGGIBILE — due articoli della stessa famiglia agli antipodi del
            # documento, e nemmeno un ordine sbagliato da criticare: proprio
            # nessun ordine leggibile. Decisione di Tid, 2026-08-31.
            # ⚠️ La stabilita' fra due rigenerazioni resta, ed e' l'altra meta'
            # dello scopo di questa chiave: il codice di un articolo non cambia
            # da solo. Se qualcuno lo rinomina fra due rigenerazioni di un lotto
            # in bozza l'ordine cambia — ⭐ ed E' CORRETTO che cambi, perche' il
            # documento riflette i codici di adesso. Va detto qui, o il prossimo
            # lettore torna all'UUID credendo di riparare qualcosa.
            # ℹ️ Le righe senza articolo (rettifiche, oneri) restano in testa
            # come prima: chiave vuota.
            str(g.articolo_codice or ""),
            g.group_key["competenza_dal"] or "",
            g.group_key["competenza_al"] or "",
            prezzo is None,
            prezzo if prezzo is not None else Decimal(0),
            uom_id is None,
            uom_id if uom_id is not None else 0,
            g.kit.key or "",
            # Discriminante della rettifica: due rettifiche di righe di fattura
            # diverse possono avere articolo, prezzo e uom identici. Senza
            # questo, l'ordine — e quindi il `riga_nr` — cambierebbe fra due
            # rigenerazioni dello stesso lotto, che è ciò che tutta questa
            # chiave esiste per impedire.
            g.group_key["fattura_riga_rettificata_id"] or 0,
            # ⚠️ E lo stesso vale per il contratto, per la stessa ragione: da
            # quando spezza, due gruppi possono differire SOLO per l'atto — e
            # due gruppi che l'ordinamento non distingue prendono il `riga_nr`
            # nell'ordine in cui le attività sono arrivate. Aggiungere una voce
            # alla chiave di raggruppamento senza aggiungerla a questa rende
            # instabile la numerazione delle righe, e il sintomo si vede solo
            # rigenerando lo stesso lotto due volte.
            g.group_key["contratto_id"] or 0,
        )

    # Scopo: Il periodo della riga di fattura (`competenza_dal/_al`, NOT NULL
    #        dal 2026-10-02 — brief-db-bom-flag-quantita-e-kit-in-fattura D-3,
    #        D-3.1, R-BE-B1), una attività alla volta:
    #          - RETTIFICA → il periodo della riga rettificata, come prezzo e
    #            IVA (N-1): vince su quello dell'attività, che è la data
    #            dell'accredito e non quella del fatto che corregge;
    #          - la chiave porta un periodo vero → quello, uguale per tutte le
    #            attività del gruppo perché sta nella chiave;
    #          - riga puntuale → `dal = al` = la data PIÙ RECENTE fra le
    #            attività aggregate. ⛔ Mai `min`–`max`: con `dal ≠ al` la riga
    #            si stamperebbe come un periodo che non esiste (la vista stampa
    #            il periodo quando `dal ≠ al`).
    # ⚠️ Il periodo vero si riconosce dalla chiave e non si ricalcola: la regola
    #    «è un periodo» sta in `_build_group_key`, e una seconda copia qui
    #    divergerebbe.
    @staticmethod
    def _accumula_periodo(
        gruppo: _GruppoRiga, gi: GroupAttivitaInput, *, function_name: str
    ) -> None:
        if gi.fattura_riga_rettificata_id is not None:
            _richiedi_dati_attivita(
                gi.rett_competenza_dal is not None and gi.rett_competenza_al is not None,
                detail=(
                    f"attivita {gi.attivita_id}: la riga rettificata "
                    f"{gi.fattura_riga_rettificata_id} non ha un periodo"
                ),
                context={"attivita_id": gi.attivita_id},
                function_name=function_name,
            )
            gruppo.competenza_dal = gi.rett_competenza_dal
            gruppo.competenza_al = gi.rett_competenza_al
            return
        gk = gruppo.group_key
        if gk["competenza_dal"] is not None and gk["competenza_al"] is not None:
            gruppo.competenza_dal = date.fromisoformat(gk["competenza_dal"])
            gruppo.competenza_al = date.fromisoformat(gk["competenza_al"])
            return
        # Puntuale: `competenza_al` è NOT NULL su `attivita_fatturabili` e su
        # una riga puntuale vale la data dell'attività.
        _richiedi_dati_attivita(
            gi.competenza_al is not None,
            detail=f"attivita {gi.attivita_id}: competenza_al mancante",
            context={"attivita_id": gi.attivita_id},
            function_name=function_name,
        )
        assert gi.competenza_al is not None
        gruppo.periodo_puntuale = True
        if gruppo.competenza_al is None or gi.competenza_al > gruppo.competenza_al:
            gruppo.competenza_dal = gi.competenza_al
            gruppo.competenza_al = gi.competenza_al

    # Scopo: Le righe PUNTUALI dello stesso kit portano la STESSA data: la piu'
    #        recente fra tutte, non quella di ciascuna riga.
    # 🔴 Perche': la vista separa il kit per periodo. Le attivita' dei
    #    componenti di un'istanza di kit nascono insieme (stesse date), ma un
    #    componente puo' finire in piu' righe (prezzi diversi nel tempo) e un
    #    altro in una sola: con la data piu' recente PER RIGA, il kit si
    #    spezzerebbe in due padri e la sua quantita' uscirebbe discordante
    #    (NULL) — senza nessun errore. La regola D-3.1 vale per l'istanza di kit.
    # ⚠️ Solo il periodo puntuale si sposta: un periodo vero sta nella chiave,
    #    quello di una rettifica e' della riga rettificata.
    @staticmethod
    def _allinea_periodo_kit(gruppi: list[_GruppoRiga]) -> None:
        piu_recente: dict[tuple[int, str], date] = {}
        for g in gruppi:
            if g.kit.key is None or not g.periodo_puntuale:
                continue
            assert g.competenza_al is not None
            chiave = (g.fattura_id, g.kit.key)
            if chiave not in piu_recente or g.competenza_al > piu_recente[chiave]:
                piu_recente[chiave] = g.competenza_al
        for g in gruppi:
            if g.kit.key is None or not g.periodo_puntuale:
                continue
            data = piu_recente[(g.fattura_id, g.kit.key)]
            g.competenza_dal = data
            g.competenza_al = data


# Scopo: Il rifiuto di un'attivita' con dati incompleti o incoerenti per il
#        raggruppamento: un codice e una frase, il dettaglio nomina l'attivita'.
#        Sede unica (regola del 2): era lo stesso `require` scritto dodici
#        volte, e una copia con la frase o il codice diversi non l'avrebbe
#        segnalata nessuno.
def _richiedi_dati_attivita(
    condizione: bool,
    *,
    detail: str,
    context: dict[str, Any],
    function_name: str,
) -> None:
    ErrorManager.require(
        condizione,
        code="E_GROUP_ATTIVITA_INVALID_DATA",
        message="Dati attivita non validi per grouping.",
        detail=detail,
        context=context,
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Rappresentazione decimale canonica, esatta e stabile fra scale diverse.
# `normalize()` rende uguali 5.0 e 5.00000000; `format(..., "f")` evita la
# notazione esponenziale che normalize() introduce sugli interi (100 → 1E+2).
def _to_decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), "f")


# Scopo: Ritorno alla forma Decimal dalla stringa canonica della chiave.
def _to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


# Scopo: Gestisce `_to_iso` nel flusso applicativo del modulo.
def _to_iso(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
