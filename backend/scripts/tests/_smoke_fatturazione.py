# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block degli smoke Python di fatturazione: la BASE di una
#        fixture (cliente, istanza, utility, articolo, UoM, valuta, tipo
#        documento, sorgente, competenza, emittente, commessa) COSTRUITA dalle
#        radici del provisioning di sviluppo, dentro la transazione dello smoke.
# Note: ⭐ Regola del 2 (ok Tid, 2026-10-21; brief-be-utenti-di-sviluppo T-7b):
#       la stessa base stava in cinque smoke, letta da «l'ultima attivita'
#       fatturabile esistente» (`ORDER BY a.id DESC LIMIT 1`). Era una
#       fotografia della macchina: su un database nuovo non c'e' niente da
#       leggere, e su dbdev la riga presa era di un emittente qualunque, vista
#       solo perche' `dev.smoke` e' super admin senza emittente scelto.
#       ⭐ Le scelte sono quelle dei builder del DB (`dbops.fn_pgtap_crea_fattura`,
#       `fn_pgtap_crea_commessa_attivita`): il catalogo si SCEGLIE con un
#       ORDER BY, l'articolo si COSTRUISCE (`dbops.fn_pgtap_crea_articolo`),
#       la sorgente di una riga di commessa e' un consumo della commessa
#       (`consumo_della_commessa`), e la sua chiave lo nomina
#       (`chiave_di_commessa`, dal giro C.3). Se cambiano la',
#       si allinea qui.
#       ⚠️ Lo smoke resta sull'emittente di prova (`seleziona_emittente_di_prova`):
#       da qui in poi vede e scrive solo il suo perimetro. Tutto cio' che si
#       costruisce sparisce col rollback dello smoke.
#       ⭐ Seconda estrazione (regola del 2, ok Tid, 2026-10-21): la CATENA
#       lotto -> attivita' lockata -> righe -> fattura, che stava copiata con
#       varianti in sei smoke (`crea_lotto_di_prova`, `crea_attivita_lockata`,
#       `crea_attivita_di_commessa`).
#       ⛔ «Una fattura», un contratto, un ordine si chiedono ai builder del DB
#       (`dbops.fn_pgtap_crea_fattura`, `fn_pgtap_crea_contratto`, …), che dal
#       2026-10-21 accettano `dev.smoke` sull'emittente di prova (R-2): qui non
#       se ne scrive una seconda versione.
#       ⭐ Terza estrazione (regola del 2, ok Tid, 2026-11-03): la DATA ISOLATA
#       dei documenti di prova (`data_documento_isolata`), copiata in
#       `smoke-push-termine-documento-commessa` e `smoke-push-onere-ordine`.
#       Uso: `from scripts.tests._smoke_fatturazione import costruisci_base_fatturazione`,
#       dopo `apri_contesto_smoke(cur)`. Il trattino basso lo tiene fuori dalla
#       scoperta di `smoke-baseline.sh`.
# ------------------------------------------------------------

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from apps.core.services.fuso_aziendale import oggi_aziendale
from scripts.tests._smoke_commessa import (
    SORGENTE_CONSUMO,
    consumo_di_commessa,
    crea_riga_commessa,
)
from scripts.tests._smoke_contesto import seleziona_emittente_di_prova


# Scopo: la data dei documenti di prova, ISOLATA: ~14 mesi nel futuro
#        (`oggi_aziendale()` + 425 giorni), a meta' mese. La competenza che ne
#        nasce (`.replace(day=1)`) non incrocia attivita' vive dell'ambiente:
#        la selezione di un lotto, gia' filtrata per BA + emittente + tipo
#        documento, non le rastrella e non ne e' inquinata.
#        Il 15 lascia spazio a chi ha bisogno del mese prima o dopo.
_GIORNI_ISOLAMENTO = 425


def data_documento_isolata() -> date:
    return (oggi_aziendale() + timedelta(days=_GIORNI_ISOLAMENTO)).replace(day=15)


# Scopo: costruisce un articolo di prova (non gestito a magazzino) col builder
#        del DB e ne restituisce `(articolo_id, uom_id)`. `uom_id` dato = la
#        UoM base dell'articolo (e' loccata: si sceglie alla nascita).
#        `natura_vendita_id` dato = la natura (es. una merce, per stare in un
#        ordine); senza, il default di tabella.
# ⚠️ L'IVA si assegna QUI: il builder non la scrive, e la fornitura del cliente
#    di prova non ha un tipo d'uso che la dia (stadio A2 di
#    `vendite.fn_resolve_iva_riga_it`). Senza, la riga di fattura nasce senza
#    `iva_id`, e dal 2026-10-22 la fattura si ferma entrando in EMESSA con
#    `E_FATTURA_RIGA_IVA_MANCANTE` (brief-be-utenti-di-sviluppo §9.9; prima si
#    rompeva nel riepilogo con un errore tecnico).
#    L'aliquota imponibile piu' alta del catalogo, scelta con un ORDER BY.
#    `iva_id` non e' fra le colonne congelate su un articolo usato, e questo
#    non e' ancora usato.
def crea_articolo_di_prova(
    cur: Any,
    *,
    prefisso: str,
    uom_id: int | None = None,
    natura_vendita_id: int | None = None,
) -> tuple[Any, int]:
    codice = f"{prefisso}-{uuid.uuid4().hex[:10]}".upper()
    cur.execute(
        "SELECT dbops.fn_pgtap_crea_articolo(%s, false, p_uom_id => %s, p_natura_vendita_id => %s)",
        [codice, uom_id, natura_vendita_id],
    )
    articolo_id = cur.fetchone()[0]
    cur.execute(
        """
        UPDATE catalogo.articoli
           SET iva_id = (SELECT i.id FROM config.iva i
                          WHERE i.attivo AND i.aliquota_iva > 0
                          ORDER BY i.aliquota_iva DESC, i.id LIMIT 1)
         WHERE id = %s
        """,
        [articolo_id],
    )
    cur.execute("SELECT uom_id, iva_id FROM catalogo.articoli WHERE id = %s", [articolo_id])
    uom_id, iva_id = cur.fetchone()
    # Un catalogo IVA senza aliquote imponibili lascerebbe `iva_id` NULL in
    # silenzio, e lo smoke si romperebbe lontano, nel riepilogo IVA.
    if iva_id is None:
        raise SystemExit("SENZA_CONTESTO: nessuna aliquota IVA imponibile attiva in config.iva.")
    return articolo_id, int(uom_id)


# Scopo: una commessa NUOVA del cliente della base (`p_force_new`), che porta le
#        condizioni di pagamento (D-R): e' il punto in cui la fixture entra
#        nella catena reale (`vendite.fn_resolve_termini_pagamento`: documento
#        -> commessa -> cliente) invece di scavalcarla.
# ⚠️ La modalita' la porta la commessa, perche' il cliente di prova non ne ha
#    una: senza, la catena la da' NULL (non ha default, D-J) e rate e testata
#    restano senza. Senza `modalita_id` si sceglie la prima del catalogo.
# Note: ⭐ Regola del 2: la stessa funzione stava in fattura-scadenze e in
#       fattura-aggregazione-termini, identica. `p_force_new` da' commesse
#       distinte anche a termine uguale: aggregazione-termini prova cosi' che a
#       separare le fatture e' il termine, non la commessa.
def crea_commessa_di_prova(
    cur: Any,
    t: dict[str, Any],
    *,
    marker: str,
    termine_id: int | None = None,
    modalita_id: int | None = None,
) -> int:
    if modalita_id is None:
        cur.execute("SELECT m.id FROM config.modalita_pagamento m ORDER BY m.id LIMIT 1")
        modalita_id = cur.fetchone()[0]
    cur.execute(
        """
        SELECT vendite.fn_get_or_create_commessa(
            p_billing_account_id => %s, p_utility_id => %s,
            p_competenza_dal => %s, p_competenza_al => %s,
            p_meta => %s::jsonb, p_force_new => true,
            p_termine_pagamento_id => %s, p_modalita_pagamento_id => %s
        )
        """,
        [t["billing_account_id"], t["utility_id"],
         t["competenza_mese"], t["competenza_mese"],
         json.dumps({"smoke": marker}), termine_id, modalita_id],
    )
    return int(cur.fetchone()[0])


# Scopo: la base di una fixture di fatturazione sull'emittente di prova, nella
#        forma `t` che gli smoke usavano gia' (stesse chiavi). Il cliente e' il
#        primo billing account di un cliente di prova legato a quell'emittente
#        (riconosciuto dall'etichetta `dbops.soggetti_di_prova`, non da un nome);
#        la commessa e' nuova (`p_force_new`). `competenza_mese` dato = una
#        competenza scelta dallo smoke (es. isolata nel futuro, perche' la
#        selezione del lotto non rastrelli altro); senza, il mese di oggi.
#        Si ferma (SystemExit, col perche') se il provisioning non ha dato
#        quel cliente.
def costruisci_base_fatturazione(
    cur: Any, *, marker: str, competenza_mese: date | None = None
) -> dict[str, Any]:
    ef_id, ef_sr_id = seleziona_emittente_di_prova(cur)
    cur.execute(
        """
        SELECT ba.id, ba.istanza_utility_id, ba.utility_id, ba.soggetto_ruolo_id,
               COALESCE(ba.valuta_id, (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1))
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
          JOIN dbops.soggetti_di_prova sp ON sp.soggetto_id = sr.soggetto_id
          JOIN anagrafiche.emittenti_fiscali_billing_account efba
            ON efba.billing_account_id = ba.id
         WHERE efba.emittente_soggetto_ruolo_id = %s
         ORDER BY ba.codice
         LIMIT 1
        """,
        [ef_sr_id],
    )
    riga = cur.fetchone()
    if riga is None:
        raise SystemExit(
            "SENZA_CONTESTO: nessun cliente di prova sull'emittente di prova. "
            "Lancia `./manage-env.sh provision_utenti_sviluppo` (run-book §11)."
        )
    ba_id, istanza_id, utility_id, cliente_sr_id, valuta_id = riga

    cur.execute(
        "SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1"
    )
    tipo_doc_fiscale_id = cur.fetchone()[0]
    if competenza_mese is None:
        cur.execute("SELECT date_trunc('month', script.fn_data_operativa())::date")
        competenza_mese = cur.fetchone()[0]

    articolo_id, uom_id = crea_articolo_di_prova(cur, prefisso="SMOKE-FATT")

    t = {
        "articolo_id": articolo_id,
        "istanza_utility_id": istanza_id, "billing_account_id": ba_id,
        "uom_id": uom_id, "valuta_id": valuta_id,
        "tipo_doc_fiscale_id": tipo_doc_fiscale_id,
        "competenza_mese": competenza_mese, "data": competenza_mese,
        "emittente_sr_id": ef_sr_id, "emittente_fiscale_id": ef_id,
        "cliente_sr_id": cliente_sr_id, "utility_id": utility_id,
    }
    t["commessa_id"] = crea_commessa_di_prova(cur, t, marker=marker)
    return t


# Scopo: un lotto MASSIVO della base, gia' IN_ESECUZIONE e APERTO sul suo
#        `lock_batch_id`, stato fiscale DRAFT: la forma in cui il task
#        `select_attivita` lo consegna al generatore righe. Competenza, utility,
#        tipo documento ed emittente sono quelli di `t`.
# Note: ⭐ Regola del 2: lo stesso INSERT stava in sei smoke, diverso solo per
#       il codice.
def crea_lotto_di_prova(cur: Any, t: dict[str, Any], *, codice: str, lock_batch_id: str) -> int:
    cur.execute(
        """
        INSERT INTO vendite.fatturazione_lotti (
            codice, competenza_mese, utility_id, tipo_doc_fiscale_id,
            stato_doc_fiscale_id, emittente_soggetto_ruolo_id, tipo_lotto,
            stato_lotto, stato_operativo, lock_batch_id, meta
        )
        SELECT %s, %s, %s, %s,
               (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'),
               %s, 'MASSIVO', 'IN_ESECUZIONE', 'APERTO', %s,
               '{"smoke": true}'::jsonb
        RETURNING id
        """,
        [codice, t["competenza_mese"], t["utility_id"], t["tipo_doc_fiscale_id"],
         t["emittente_sr_id"], lock_batch_id],
    )
    return int(cur.fetchone()[0])


# Scopo: l'attivita' fatturabile agganciata a una riga di commessa, gia'
#        lockata sul lotto (`lock_batch_id`), approvata, PENDING, prezzo
#        bloccato. `emit_batch_id` dato = la marca del giro che la emette:
#        `fn_select_attivita_fatturabili` prende solo le righe marcate col
#        proprio giro (20260904-50), e chi passa dallo STEP della pipeline la
#        deve avere. `articolo_id` di default quello della base.
# Note: ⭐ Regola del 2: lo stesso INSERT stava in sei smoke, con varianti di
#       quantita', meta e marca del giro.
#       ⛔ Nessuna colonna di provenienza (dal 2026-11-07, giro C.1 di
#       brief-db-sorgente-documento-e-riga, BE-C.1-b): `sorgente_*` di
#       `vendite.attivita_fatturabili` non esistono piu'. La provenienza di
#       un'attivita' e' la sua riga di commessa (`commessa_attivita_id`).
def crea_attivita_lockata(
    cur: Any,
    t: dict[str, Any],
    *,
    commessa_id: int,
    ca_id: int,
    lock_batch_id: str,
    prezzo: Decimal,
    quantita: Decimal | int = 1,
    meta: str = "{}",
    emit_batch_id: str | None = None,
    articolo_id: Any = None,
) -> int:
    cur.execute(
        """
        INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            quantita, uom_id, qta_operativa, uom_operativa_id, factor_to_base,
            prezzo_unitario, valuta_id, tipo_doc_fiscale_id,
            competenza_mese, competenza_dal, competenza_al,
            commessa_id, commessa_attivita_id,
            lock_batch_id, emit_batch_id, lock_in_fatturazione, approvato,
            stato_esecuzione, prezzo_bloccato, meta
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, TRUE, TRUE, 'PENDING', TRUE, %s::jsonb
        ) RETURNING id
        """,
        [articolo_id or t["articolo_id"], t["istanza_utility_id"], t["billing_account_id"],
         t["data"], quantita, t["uom_id"], quantita, t["uom_id"], prezzo,
         t["valuta_id"], t["tipo_doc_fiscale_id"], t["competenza_mese"],
         t["data"], t["data"], commessa_id, ca_id,
         lock_batch_id, emit_batch_id, meta],
    )
    return int(cur.fetchone()[0])


# Scopo: Il CONSUMO d'origine delle righe di una commessa della fixture, e la
#        sua chiave: uno per commessa, creato alla prima richiesta e tenuto in
#        `t["consumi"]` (la fixture e' gia' lo stato dello smoke: niente
#        cache di modulo). Ritorna `(consumo_id, chiave)`.
# ⚠️ Uno per commessa, non uno per riga: un documento sta in una sola
#    commessa aperta, e le righe di una commessa — i componenti di un kit col
#    loro padre — devono condividere la radice della chiave.
def consumo_della_commessa(cur: Any, t: dict[str, Any], commessa_id: int) -> tuple[int, str]:
    consumi = t.setdefault("consumi", {})
    if commessa_id not in consumi:
        consumi[commessa_id] = consumo_di_commessa(cur, commessa_id, t["competenza_mese"])
    return consumi[commessa_id]


# Scopo: La CHIAVE del push di una riga di una commessa della fixture: quella
#        del suo consumo (`consumo_della_commessa`), e dopo `:` l'etichetta
#        dello smoke. È la chiave che `crea_attivita_di_commessa` vuole.
# ⛔ Dal giro C.3 (brief-db-sorgente-documento-e-riga, BE-C.3-c) la chiave
#    nomina il documento: un `SMOKE:<marker>:...` scritto a mano e' rifiutato
#    (`E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`).
def chiave_di_commessa(cur: Any, t: dict[str, Any], commessa_id: int, etichetta: str) -> str:
    _consumo_id, chiave = consumo_della_commessa(cur, t, commessa_id)
    return f"{chiave}:{etichetta}"


# Scopo: riga di commessa (dalla madre, `crea_riga_commessa`) + la sua
#        attivita' fatturabile lockata sul lotto. Ritorna `(ca_id, af_id)`.
#        Commessa e articolo di default quelli della base (un articolo dato
#        deve avere la UoM della base); stati della riga di default quelli della
#        madre (BOZZA, NON_EMESSA). `meta` va sulla riga di commessa e,
#        senza `meta_attivita`, anche sull'attivita' (il componente di un kit
#        ne porta uno suo, col `segment_key`).
# Note: ⭐ Regola del 2: la coppia stava in fattura-scadenze e in
#       fattura-aggregazione-termini (identica), in fattura-indirizzi-snapshot
#       (in linea) e in fatturazione-aggregazione-righe (col suo meta).
def crea_attivita_di_commessa(
    cur: Any,
    t: dict[str, Any],
    *,
    segment_key: str,
    lock_batch_id: str,
    prezzo: Decimal,
    quantita: Decimal | int = 1,
    commessa_id: int | None = None,
    stato_approvazione: str = "BOZZA",
    stato_emissione: str = "NON_EMESSA",
    emit_batch_id: str | None = None,
    articolo_id: Any = None,
    meta: str = "{}",
    meta_attivita: str | None = None,
) -> tuple[int, int]:
    commessa = commessa_id or t["commessa_id"]
    articolo = articolo_id or t["articolo_id"]
    # La provenienza e' il consumo della commessa: `segment_key` la deve
    # nominare (`chiave_di_commessa`), o il guard la rifiuta.
    consumo_id, _chiave = consumo_della_commessa(cur, t, commessa)
    ca_id = crea_riga_commessa(
        cur, commessa_id=commessa, segment_key=segment_key,
        articolo_id=articolo, istanza_utility_id=t["istanza_utility_id"],
        uom_id=t["uom_id"], data_attivita=t["data"],
        competenza_mese=t["competenza_mese"], competenza_dal=t["data"],
        competenza_al=t["data"], quantita=quantita, prezzo=prezzo,
        tipo_doc_fiscale_id=t["tipo_doc_fiscale_id"], valuta_id=t["valuta_id"],
        stato_approvazione=stato_approvazione, stato_emissione=stato_emissione,
        meta=meta, sorgente_codice=SORGENTE_CONSUMO, sorgente_uid=str(consumo_id),
    )
    af_id = crea_attivita_lockata(
        cur, t, commessa_id=commessa, ca_id=ca_id, lock_batch_id=lock_batch_id,
        prezzo=prezzo, quantita=quantita, emit_batch_id=emit_batch_id,
        articolo_id=articolo, meta=meta if meta_attivita is None else meta_attivita,
    )
    return ca_id, af_id
