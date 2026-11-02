# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Questa lettura appartiene a QUESTO documento», in un posto solo, nelle
#        DUE forme che il modello ha oggi: il predicato nel `WHERE` per le viste
#        (`filtro_coda_per_documento`) e la sorgente nel `FROM` per le funzioni
#        con la chiusura dentro (`sorgente_per_documento`, dal 2026-09-21:
#        `fn_partite_merce`, `fn_situazione_merce_ordine`,
#        `fn_resi_da_accreditare`) — e, per le CODE resi, la scelta fra le due
#        (`lettura_coda_per_documento` sulla mappa `FUNZIONE_PER_CODA`, dal
#        2026-09-22): quale coda ha la chiusura dentro lo dice una riga qui,
#        non i wrapper dei due repository.
# ------------------------------------------------------------

# PERCHE' ESISTE (regola del 2, ok Tid 2026-08-18). Lo stesso predicato serve a
# due chiamanti che rispondono alla STESSA domanda da due schermate diverse:
#
#   VenditeRepository._list_coda_su_partite  → la sezione «da ri-consegnare»
#       del pannello situazione merce (ordine e DDT);
#   ResiRepository._list_coda                → la coda di lavoro ri-consegne,
#       quando si arriva dal pannello col filtro sul documento gia' messo (FE-2).
#
# ⚠️ Scritto due volte, il giorno in cui uno dei due cambia il pannello dice
# «8 da ri-consegnare» e la coda filtrata ne mostra 7 — e nessun test lo
# intercetta, perche' ognuna delle due copie e' coerente con se' stessa. E' il
# tipo di divergenza che si nota solo guardando due schermate insieme.
#
# ⭐ Fino al 2026-09-21 il predicato serviva ANCHE alla coda accrediti, sulle
# stesse due schermate: da quel giorno quella coda ha la chiusura dentro
# `fn_resi_da_accreditare` (stesso `EXISTS` sul fulfillment, per costruzione)
# e si legge con `sorgente_per_documento`, sotto. Il predicato resta per la
# coda che una funzione non ce l'ha.
#
# Brief: brief-design-note-credito-resi.md §22 (slice B3), richiesta FE-2.

from typing import Any, NamedTuple


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


# PERCHE' ESISTE ANCHE QUESTO (regola del 2, ok Tid 2026-09-21). Dal giro 1-2 di
# `brief-db-partita-merce-per-documento` la chiusura di un documento sta DENTRO
# tre funzioni `(p_ddt_ids, p_ordine_ids)`: il repository non filtra piu' nel
# `WHERE`, sceglie quale array riempire nel `FROM`. Quella scelta e' la stessa
# in quattro punti (partite, situazione ordine, coda accrediti del pannello,
# coda accrediti di lavoro), e scritta quattro volte avrebbe lo stesso modo di
# sbagliare del predicato qui sopra: due schermate che rispondono cose diverse
# sullo stesso documento, ciascuna coerente con se' stessa.
#
# ⚠️ Le tre funzioni hanno la STESSA firma e la stessa semantica dei semi:
# entrambi `NULL` = tutte (la vista), array vuoto = zero righe, entrambi
# valorizzati = unione. Qui si riempie SEMPRE uno solo dei due: «tutte» non e'
# una domanda che questi lettori fanno, e un chiamante che non passa nessun id
# e' rotto — non chiede l'intero database.


# Scopo: L'espressione da mettere nel `FROM` per leggere `funzione` ristretta a
#        un documento, coi suoi parametri. Esattamente uno dei due id.
# Perimetro e risultato atteso: `("vendite.fn_x(ARRAY[%s]::bigint[], NULL)",
#        [ddt_id])` per DDT, `("vendite.fn_x(NULL, ARRAY[%s]::bigint[])",
#        [ordine_id])` per ordine. Il chiamante mette l'alias dopo.
#        ⚠️ `ValueError` — non un ripiego su «tutte» — se non e' esattamente
#        uno: e' la stessa guardia dei quattro chiamanti, portata qui.
def sorgente_per_documento(
    funzione: str,
    *,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
) -> tuple[str, list[Any]]:
    if (ddt_id is None) == (ordine_id is None):
        raise ValueError(
            f"sorgente_per_documento({funzione}): passare ESATTAMENTE uno fra "
            "ddt_id e ordine_id"
        )
    # `::bigint[]` esplicito, come chiede il brief (§8.4): l'argomento arriva
    # gia' del tipo della firma, senza coercizione da `integer[]`.
    if ddt_id is not None:
        return f"{funzione}(ARRAY[%s]::bigint[], NULL)", [int(ddt_id)]
    assert ordine_id is not None
    return f"{funzione}(NULL, ARRAY[%s]::bigint[])", [int(ordine_id)]


# PERCHE' ESISTE ANCHE QUESTO (regola del 2, ok Tid 2026-09-22). Le due code
# resi si leggono per documento con DUE forme diverse — gli accrediti dalla
# funzione con la chiusura dentro, le ri-consegne dalla vista col predicato — e
# la scelta «quale coda legge quale forma» stava scritta in due repository
# (`VenditeRepository`, il pannello; `ResiRepository`, le code di lavoro), col
# nome della funzione ricopiato in entrambi. E' un fatto del MODELLO DB (una
# coda ha la funzione, l'altra no), non del repository: il giorno in cui anche
# le ri-consegne avranno la loro funzione, si cambia UNA riga qui e i quattro
# punti la seguono — invece di due wrapper che raccontano due modelli diversi.

# La sede unica: vista-coda -> funzione `(p_ddt_ids, p_ordine_ids)` con la
# chiusura dentro, o `None` per la coda che una funzione non ce l'ha ancora.
# ⚠️ Una coda che manca qui e' un chiamante rotto (`KeyError`), non «la vista»:
# la mappa deve conoscere OGNI coda, cosi' l'aggiunta di una terza e' una
# decisione scritta e non un ripiego silenzioso.
FUNZIONE_PER_CODA: dict[str, str | None] = {
    "vendite.vw_resi_da_accreditare": "vendite.fn_resi_da_accreditare",
    "vendite.vw_resi_da_riconsegnare": None,
}


class LetturaCoda(NamedTuple):
    """Come si legge una coda: cosa sta nel `FROM` e cosa (se serve) nel `WHERE`.

    `sorgente` e' l'espressione del `FROM` (la vista, o la funzione coi suoi
    parametri gia' riempiti) e `condizione` il predicato sul documento quando la
    chiusura NON sta nella sorgente — `None` altrimenti. I parametri sono
    separati perche' nel testo SQL stanno in due posti, e quelli della sorgente
    vengono PRIMA: e' il chiamante a comporli, nell'ordine dei suoi `%s`.
    """

    sorgente: str
    params_sorgente: list[Any]
    condizione: str | None
    params_condizione: list[Any]


# Scopo: La forma di lettura di `vista` per un documento, decisa dalla mappa
#        `FUNZIONE_PER_CODA` e non dal chiamante. Al piu' uno dei due id.
# Perimetro e risultato atteso:
#        - nessun documento -> la vista, senza condizione («tutte»: la coda
#          aperta a mano; e' `fn(NULL, NULL)` per costruzione);
#        - documento + coda con funzione -> `sorgente_per_documento`, senza
#          condizione (la chiusura e' dentro);
#        - documento + coda senza funzione -> la vista + il predicato di
#          `filtro_coda_per_documento`.
#        ⚠️ `ValueError` con ENTRAMBI gli id, per ogni coda: le due forme
#        altrimenti divergerebbero (la funzione farebbe l'unione, il predicato
#        sceglierebbe il DDT), e una lettura che risponde due cose diverse a
#        seconda della coda e' esattamente il difetto che questo BB chiude. Il
#        rifiuto parlante verso l'operatore sta nel service
#        (`_valida_filtro_documento`); qui e' una guardia di programmazione.
def lettura_coda_per_documento(
    vista: str,
    *,
    ddt_id: int | None = None,
    ordine_id: int | None = None,
) -> LetturaCoda:
    funzione = FUNZIONE_PER_CODA[vista]
    if ddt_id is not None and ordine_id is not None:
        raise ValueError(
            f"lettura_coda_per_documento({vista}): ddt_id e ordine_id sono "
            "alternativi, passarne al piu' uno"
        )
    if ddt_id is None and ordine_id is None:
        return LetturaCoda(vista, [], None, [])
    if funzione is not None:
        sorgente, params = sorgente_per_documento(
            funzione, ddt_id=ddt_id, ordine_id=ordine_id
        )
        return LetturaCoda(sorgente, params, None, [])
    condizione, params = filtro_coda_per_documento(ddt_id=ddt_id, ordine_id=ordine_id)
    assert condizione is not None  # un documento c'e': il predicato lo produce
    return LetturaCoda(vista, [], condizione, params)
