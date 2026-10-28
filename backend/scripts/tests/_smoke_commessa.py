# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#       solo ONERE e RETTIFICA. La sorgente e' la commessa stessa, la forma del
#       builder pgTAP `dbops.fn_pgtap_crea_commessa_attivita`.
#       Uso: gli smoke girano con `./manage-env.sh shell < …` da `backend/`,
#       quindi `from scripts.tests._smoke_commessa import crea_riga_commessa`.
#       Il trattino basso lo tiene fuori dalla scoperta di `smoke-baseline.sh`
#       (`smoke-*.py`).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


# Scopo: crea (o ritrova, e' un upsert sul segment_key) una riga NORMALE di
#        commessa con prezzo bloccato. Gli stati di default sono quelli della
#        funzione (BOZZA, NON_EMESSA). La sorgente di default e' la commessa
#        stessa; `sorgente_codice`/`sorgente_uid` dati = un'altra sorgente
#        (es. `DDT_VENDITA` e l'uid della bolla: la riga che il push della
#        bolla scriverebbe, su cui la partita di merce si aggancia).
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
    sorgente_codice: str = "COMMESSA",
    sorgente_uid: str | None = None,
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
            p_sorgente_uid => %s::text,
            p_meta => %s::jsonb
        )
        """,
        [commessa_id, segment_key, articolo_id, istanza_utility_id,
         data_attivita, uom_id, quantita, competenza_mese, competenza_dal,
         competenza_al, prezzo, tipo_doc_fiscale_id, valuta_id,
         stato_approvazione, stato_emissione, sorgente_codice,
         sorgente_uid if sorgente_uid is not None else commessa_id, meta],
    )
    return int(cur.fetchone()[0])
