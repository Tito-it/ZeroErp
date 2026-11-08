# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block degli smoke Python: la riga di commessa di prova, dalla
#        funzione di upsert (non da un INSERT diretto, cosi' i guard di dominio
#        — coerenza BA, articolo attivo, unicita' del segment_key — restano
#        esercitati).
# Note: ⭐ Regola del 2: la stessa chiamata a `vendite.fn_upsert_commessa_attivita`
#       stava in sei smoke, e il 2026-10-12 tutti e sei hanno dovuto imparare
#       la stessa cosa nuova (la sorgente, sotto). Una riga di commessa di
#       smoke nasce da qui.
#       ⛔ Dal 2026-10-12 una riga NORMALE senza sorgente non entra
#       (`chk_commesse_attivita_senza_sorgente_onere_rettifica`,
#       brief-db-annullo-a-valle-riapre-a-monte §8.5): senza sorgente esistono
#       solo ONERE e RETTIFICA.
#       ⛔ Dal 2026-11-07 la sorgente NON puo' piu' essere la commessa stessa:
#       `vendite.commesse` non ha `uid`, e il guard della chiave (sotto) vuole
#       l'uid del documento. La sorgente di default e' un CONSUMO vero del
#       billing account della commessa (`consumo_di_commessa`), il documento
#       piu' leggero del modello — la forma del builder pgTAP
#       `dbops.fn_pgtap_crea_commessa_attivita`.
#       ⛔ Dal 2026-11-07 (giro C.3 di brief-db-sorgente-documento-e-riga,
#       BE-C.3-c) la chiave del push NOMINA il documento della provenienza:
#       `<CODICE>:<uid del documento>...`, come la compone `script.fn_segment_key`
#       (guard `trgfn_commesse_attivita_guard_sorgente_segment`,
#       `E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`). Le chiavi
#       `SMOKE:<marker>:...` scritte a mano non entrano piu': la chiave la
#       compone il dominio (`consumo_di_commessa`, `chiave_di_documento`), e
#       l'etichetta dello smoke ne e' solo il suffisso.
#       Uso: gli smoke girano con `./manage-env.sh shell < …` da `backend/`,
#       quindi `from scripts.tests._smoke_commessa import crea_riga_commessa`.
#       Il trattino basso lo tiene fuori dalla scoperta di `smoke-baseline.sh`
#       (`smoke-*.py`).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from scripts.tests._smoke_contesto import ripristina_vincoli_differiti


# Scopo: La CHIAVE del push di una riga di commessa che viene dal documento
#        indicato: `script.fn_segment_key(<codice>, <uid del documento>)`, e
#        dopo `:` l'etichetta dello smoke (le righe di una stessa commessa
#        devono avere chiavi diverse). Il documento si nomina come lo nomina
#        il modello, con `sorgente_id` o `sorgente_uid` (uno dei due).
# ⭐ L'uid lo risolve `script.fn_sorgente_documento`, la stessa funzione con
#    cui il guard lo confronta: una seconda risoluzione qui potrebbe dare un
#    uid che il guard non riconosce.
# ⛔ Documento inesistente o non visibile = `SystemExit` parlante, non una
#    chiave con «None» dentro che il guard rifiuterebbe con un codice tecnico.
def chiave_di_documento(
    cur: Any,
    *,
    sorgente_codice: str,
    sorgente_id: int | None = None,
    sorgente_uid: str | None = None,
    etichetta: str | None = None,
) -> str:
    cur.execute(
        """
        SELECT script.fn_segment_key(s.codice_interno, d.documento_uid::text)
          FROM config.sorgenti s
          CROSS JOIN LATERAL script.fn_sorgente_documento(
                   s.id, %s::bigint, %s::uuid) d
         WHERE s.codice_interno = %s
        """,
        [sorgente_id, sorgente_uid, sorgente_codice],
    )
    riga = cur.fetchone()
    if riga is None or riga[0] is None:
        raise SystemExit(
            f"chiave_di_documento: {sorgente_codice} id={sorgente_id} "
            f"uid={sorgente_uid} non risolve un documento visibile."
        )
    return str(riga[0]) if etichetta is None else f"{riga[0]}:{etichetta}"


# Codice del tipo del documento di default di una riga di smoke (il consumo).
SORGENTE_CONSUMO = "ATTIVITA_CONSUMI"


# Scopo: Un CONSUMO nuovo del billing account della commessa, nel mese dato:
#        il documento d'origine piu' leggero che il modello ammette (non ha
#        righe). Ritorna `(consumo_id, chiave)`, dove `chiave` e' quella che
#        il push dei consumi comporrebbe (`script.fn_segment_key`).
# ⭐ Dal builder del DB (`dbops.fn_pgtap_crea_consumo`), non da un INSERT
#    proprio: se cambia la forma di un consumo, si allinea la'.
# ⚠️ Un documento sta in UNA sola commessa aperta: il consumo e' di questa
#    commessa, e le sue righe ne condividono la chiave (estesa con
#    l'etichetta). I componenti di un kit, in particolare, devono stare sotto
#    la stessa radice di chiave del padre.
def consumo_di_commessa(
    cur: Any, commessa_id: int, competenza_mese: date,
) -> tuple[int, str]:
    cur.execute(
        """
        SELECT c.consumo_id, c.segment_key
          FROM vendite.commesse k
          CROSS JOIN LATERAL dbops.fn_pgtap_crea_consumo(
                   k.billing_account_id, %s::date,
                   '{"smoke": true}'::jsonb) c
         WHERE k.id = %s
        """,
        [competenza_mese, int(commessa_id)],
    )
    riga = cur.fetchone()
    if riga is None:
        raise SystemExit(f"consumo_di_commessa: nessuna commessa {commessa_id} visibile.")
    # ⛔ Il builder esce con i vincoli IMMEDIATE: senza rimetterli, la
    #    pipeline che lo smoke esegue dopo vedrebbe i guard differiti
    #    scattare a meta' verbo (`ripristina_vincoli_differiti`).
    ripristina_vincoli_differiti(cur)
    return int(riga[0]), str(riga[1])


# Scopo: crea (o ritrova, e' un upsert sul segment_key) una riga NORMALE di
#        commessa con prezzo bloccato. Gli stati di default sono quelli della
#        funzione (BOZZA, NON_EMESSA). La sorgente e' OBBLIGATORIA: il
#        documento da cui la riga viene (`sorgente_codice` + la sua chiave in
#        `sorgente_uid`, l'id o l'uid in testo come la vuole la madre) — un
#        consumo (`consumo_di_commessa`), o per esempio `DDT_VENDITA` e l'uid
#        della bolla, la riga che il push della bolla scriverebbe.
#        ⚠️ `segment_key` deve nominare quel documento: si compone con
#        `chiave_di_documento` o da `consumo_di_commessa`. `sorgente_riga` = la
#        riga del documento (None = il documento intero).
# Ritorna: l'id della riga di commessa.
def crea_riga_commessa(
    cur: Any,
    *,
    commessa_id: int,
    segment_key: str,
    articolo_id: Any,
    istanza_utility_id: int,
    uom_id: int,
    data_attivita: date,
    competenza_mese: date,
    competenza_dal: date,
    competenza_al: date,
    prezzo: Decimal | int,
    tipo_doc_fiscale_id: int,
    valuta_id: int,
    quantita: Decimal | int = 1,
    stato_approvazione: str = "BOZZA",
    stato_emissione: str = "NON_EMESSA",
    meta: str = "{}",
    sorgente_codice: str,
    sorgente_uid: str,
    sorgente_riga: int | None = None,
) -> int:
    cur.execute(
        """
        SELECT attivita_id FROM vendite.fn_upsert_commessa_attivita(
            p_commessa_id => %s, p_segment_key => %s, p_articolo_id => %s,
            p_istanza_utility_id => %s, p_data_attivita => %s, p_uom_id => %s,
            p_quantita => %s, p_competenza_mese => %s, p_competenza_dal => %s,
            p_competenza_al => %s, p_prezzo_snapshot => %s,
            p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
            p_tipo_variazione_applicata => NULL,
            p_valore_variazione_applicata => NULL, p_promo_id => NULL,
            p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL,
            p_classe_utenza_id_snapshot => NULL,
            p_tipo_doc_fiscale_id => %s, p_valuta_id => %s,
            p_prezzo_bloccato => true,
            p_stato_approvazione => %s, p_stato_emissione => %s,
            p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                                    WHERE s.codice_interno = %s AND s.attivo),
            p_sorgente_chiave => %s::text,
            p_sorgente_riga => %s::bigint,
            p_meta => %s::jsonb
        )
        """,
        [commessa_id, segment_key, articolo_id, istanza_utility_id,
         data_attivita, uom_id, quantita, competenza_mese, competenza_dal,
         competenza_al, prezzo, tipo_doc_fiscale_id, valuta_id,
         stato_approvazione, stato_emissione, sorgente_codice,
         str(sorgente_uid), sorgente_riga, meta],
    )
    return int(cur.fetchone()[0])
