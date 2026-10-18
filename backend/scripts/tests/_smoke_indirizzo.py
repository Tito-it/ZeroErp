# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block degli smoke Python: l'indirizzo LIBERO di un ruolo di
#        prova, nella forma che decide il suo stato.
# Note: ⭐ Regola del 2 (ok Tid, 2026-10-18): la stessa INSERT stava tre volte
#       in due smoke (`smoke-indirizzi-documento-catena` ×2,
#       `smoke-fattura-indirizzi-snapshot`), e tutte e tre hanno dovuto
#       imparare insieme la forma nuova. Un indirizzo libero di smoke nasce da
#       qui.
#       ⭐ Dal 2026-10-18 la forma la decide lo stato (guard
#       `anagrafiche.trgfn_indirizzi_guard_forma_libera`, D-2 di Tid): comune e
#       CAP del catalogo per uno stato col catalogo dei comuni completo,
#       altrimenti la localita'. I campi li da' l'helper delle fixture
#       `dbops.fn_pgtap_indirizzo_libero_forma`; lo stato e' quello proposto
#       (`script.fn_stato_proposto_id`), non un `codice_iso2 = 'IT'`, che non e'
#       univoco.
#       Uso: gli smoke girano con `./manage-env.sh shell < …` da `backend/`,
#       quindi `from scripts.tests._smoke_indirizzo import crea_indirizzo_libero_ruolo`.
#       Il trattino basso lo tiene fuori dalla scoperta di `smoke-baseline.sh`
#       (`smoke-*.py`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any


# Scopo: scrive un indirizzo libero di `anagrafiche.indirizzi` per il ruolo e
#        il tipo dati, generico (`istanza_utility_id` None) o per istanza, con
#        `testo` come via. Ritorna l'id della riga.
def crea_indirizzo_libero_ruolo(
    cur: Any,
    *,
    soggetto_ruolo_id: int,
    tipo_indirizzo_id: int,
    testo: str,
    istanza_utility_id: int | None = None,
) -> int:
    cur.execute(
        """
        INSERT INTO anagrafiche.indirizzi
               (soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                indirizzo_libero, stato_id, comune_id, codice_postale_id,
                locality, postal_code)
        SELECT %s, %s, %s, %s,
               s.id, f.comune_id, f.codice_postale_id, f.locality, f.postal_code
          FROM (SELECT script.fn_stato_proposto_id('smoke') AS id) s
         CROSS JOIN dbops.fn_pgtap_indirizzo_libero_forma(s.id) f
        RETURNING id
        """,
        [soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id, testo],
    )
    return int(cur.fetchone()[0])
