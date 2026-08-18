# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il predicato «questa riga di coda appartiene a QUESTO documento» per le
#        due code resi (`vw_resi_da_accreditare`, `vw_resi_da_riconsegnare`),
#        in un posto solo.
# ------------------------------------------------------------

# PERCHE' ESISTE (regola del 2, ok Tid 2026-08-18). Lo stesso predicato serve a
# due chiamanti che rispondono alla STESSA domanda da due schermate diverse:
#
#   VenditeRepository._list_coda_su_partite  → le sezioni «da accreditare» e «da
#       ri-consegnare» del pannello situazione merce (ordine e DDT);
#   ResiRepository._list_coda                → le due code di lavoro, quando si
#       arriva dal pannello con il filtro sul documento gia' messo (FE-2).
#
# ⚠️ Scritto due volte, il giorno in cui uno dei due cambia il pannello dice
# «8 da accreditare» e la coda filtrata ne mostra 7 — e nessun test lo
# intercetta, perche' ognuna delle due copie e' coerente con se' stessa. E' il
# tipo di divergenza che si nota solo guardando due schermate insieme.
#
# Brief: brief-design-note-credito-resi.md §22 (slice B3), richiesta FE-2.

from typing import Any


# Scopo: Predicato SQL + parametri per restringere una coda resi a un solo
#        documento. Esattamente uno dei due id va valorizzato.
# Perimetro e risultato atteso: ritorna `(condizione, params)` da comporre in un
#        `WHERE`, oppure `(None, [])` quando nessun documento e' indicato — cioe'
#        «nessuna restrizione», che e' il caso della coda aperta a mano.
#        ⚠️ La condizione assume l'alias di tabella `v` sulla vista-coda: e' la
#        convenzione di entrambi i chiamanti, e cambiarla da un lato solo
#        romperebbe l'altro.
def filtro_coda_per_documento(
    *,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
) -> tuple[str | None, list[Any]]:
    if ddt_id is not None:
        # Lato DDT basta la colonna che la coda espone gia': e' il DDT della
        # riga resa, che per costruzione e' lo stesso della partita.
        return "v.ddt_id = %s", [int(ddt_id)]

    if ordine_id is not None:
        # Lato ordine il legame NON e' una colonna: e' il FULFILLMENT della riga
        # di DDT resa, che e' la stessa fonte da cui la partita deriva la sua
        # origine (CTE `orig` di `vw_partite_merce`). Un criterio solo, non un
        # terzo criterio inventato qui.
        #
        # ⚠️ E non si passa da `v.ordine_riga_id`, che pure c'e': con la partita
        # generalizzata quella colonna e' NULLABLE — vuota sulla merce senza
        # origine ordine (riga di DDT aggiunta a mano, DDT standalone). Usarla
        # come chiave farebbe sparire dal filtro proprio le righe che il
        # cantiere 1 ha appena portato dentro il conto.
        return (
            """EXISTS (
                    SELECT 1
                      FROM vendite.ordini_righe_fulfillment f
                      JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
                     WHERE f.ddt_riga_id = v.ddt_riga_id
                       AND orr.ordine_id = %s
             )""",
            [int(ordine_id)],
        )

    return None, []
