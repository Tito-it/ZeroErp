# fn_available_actions_ordine

### Scopo

Restituisce in un **unico JSONB** tutte le capability dell'ordine di vendita
necessarie al detail endpoint BE. Permette al drawer Vue di eliminare qualsiasi
ricalcolo di stato/transizioni lato client e di consumare le azioni con i building
block già usati dagli altri documenti vendite (`useEntityCapabilities`,
`mapAvailableActionsToDrawerActions`).

Pattern **data-driven capability layer**: allineato a
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo),
[fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) e
[fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto).
Dalla rev 2026-06-05 legge `available_actions[]` da `config.transizioni_stati_ordini`
invece del calcolo hardcoded in `ordini_service.py` (eliminato in fase BE).

> **Vedi anche**
>
> - [trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — guard transizioni (enforcement del grafo, stessa matrice)
> - [transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) — matrice metadati UI + grafo
> - [ordini](/dbzero/vendite/tabelle/ordini) — entità sorgente
> - [fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) — eleggibilità push (riusata)

## Schema

`script` (cross-dominio: legge `vendite.*` e `config.*`).

## Firma

```sql
script.fn_available_actions_ordine(
    p_ordine_id vendite.ordini.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_ordine_id` | `bigint` | Sì | ID dell'ordine. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Azioni di stato manuali (da config.transizioni_stati_ordini) +
    // push_commessa (azione applicativa appesa a mano, NON transizione).
    "available_actions": [
        {
            "key": "conferma",
            "target_state": "CONFERMATO",
            "label_key": "vendite.ordini.azione_conferma",
            "severity": "info",
            "icon": "pi pi-check",
            "requires_confirm": true,
            "outlined": false
        }
    ],
    "can_change_state":   true,   // SOLO transizioni di stato (escluso push_commessa)
    "can_edit_testata":   true,   // true solo in DRAFT
    "can_edit_righe":     true,   // true solo in DRAFT
    "can_push_commessa":  false,  // true solo da CONFERMATO con righe pushabili
    "can_push_commessa_reason":     "ORDINE_NON_CONFERMATO",                  // null se push disponibile
    "can_push_commessa_reason_key": "ordini.push_commessa_reason.non_confermato", // chiave i18n tooltip
    "non_editable_fields": [...],
    "stato_codice":       "DRAFT"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `DRAFT` | `conferma`, `annulla` | Ordinate per `stati_doc_ordini.ordine` (CONFERMATO=20, ANNULLATO=60) |
| `CONFERMATO` | `push_commessa` *(se eleggibile)* | Nessuna transizione manuale: `CONFERMATO → ANNULLATO` è `attivo=false`. `push_commessa` appesa solo se l'ordine è pushabile |
| `ANNULLATO` | `[]` | Terminale |

> **`can_change_state` vs `push_commessa`** — `can_change_state` riflette le **sole**
> transizioni di stato, calcolato **prima** di appendere `push_commessa`. Per un ordine
> CONFERMATO pushabile: `can_change_state=false` ma `available_actions` contiene comunque
> `push_commessa` (che non cambia lo stato).

### Azione `push_commessa` — applicativa, non di stato

Appesa a mano (non da matrice) quando `stato=CONFERMATO` **e** l'ordine ha almeno una
riga pushabile:

```jsonc
{
    "key": "push_commessa",
    "target_state": null,            // non cambia stato
    "label_key": "vendite.ordini.azione_push_commessa",
    "severity": "success",
    "icon": "pi pi-arrow-right",
    "requires_confirm": true,
    "outlined": false
}
```

L'eleggibilità riusa la funzione canonica
[`vendite.fn_list_ordini_da_pushare`](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
(no logica pushable duplicata). Quando `push_commessa` non è disponibile, la funzione
valorizza la coppia motivo/chiave i18n per il tooltip:

| Stato | `can_push_commessa` | `can_push_commessa_reason` | `can_push_commessa_reason_key` |
|---|:---:|---|---|
| ≠ CONFERMATO | `false` | `ORDINE_NON_CONFERMATO` | `ordini.push_commessa_reason.non_confermato` |
| CONFERMATO, 0 righe pushabili | `false` | `ORDINE_NESSUNA_RIGA_PUSHABILE` | `ordini.push_commessa_reason.nessuna_riga_pushabile` |
| CONFERMATO, ≥1 riga pushabile | `true` | `null` | `null` |

### Dettaglio `non_editable_fields`

| Stato | `can_edit_testata` | `can_edit_righe` | `non_editable_fields` |
|---|:---:|:---:|---|
| `DRAFT` | `true` | `true` | `["billing_account_id","soggetto_ruolo_id"]` — solo cliente |
| `CONFERMATO` / terminali | `false` | `false` | Tutta la testata aggiornabile + cliente |

Il **cliente** (`billing_account_id`, `soggetto_ruolo_id`) è immutabile **anche in DRAFT**
(lock columns via `script.trgfn_lock_columns`, errore `E_ORD_CLIENTE_IMMUTABILE`). Fuori
da DRAFT è bloccata tutta la testata, allineata a `_UPDATE_KEYS_ORDINE` di
`ordini_service.py`:

```json
["billing_account_id","soggetto_ruolo_id","utility_id","valuta_id",
 "modalita_pagamento_id","termine_pagamento_id","fatturazione_trigger",
 "agente_soggetto_ruolo_id","data","meta"]
```

## Algoritmo

1. **Lookup ordine** — JOIN `vendite.ordini` × `config.stati_doc_ordini` per ottenere
   `stato_id`, `codice_interno`. `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.transizioni_stati_ordini` filtrata per
   `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`. Metadati UI
   (`label_key`, `severity`, `icon`, `requires_confirm`, `outlined`) da `t.meta`. Ordine:
   `sa.ordine`. Guard defense-in-depth: `AND t.meta ? 'action_key' AND t.meta ? 'label_key'`.
3. **`can_change_state`** — `jsonb_array_length(v_actions) > 0` calcolato **qui**, prima di
   appendere `push_commessa`.
4. **push_commessa** — se `stato=CONFERMATO`: `EXISTS` su `fn_list_ordini_da_pushare(p_ordine_id)`.
   Se eleggibile, appende l'azione; altrimenti valorizza `reason`/`reason_key`.
5. **Capability editabilità** — da `v_stato_cod`: `can_edit_testata/righe = (stato='DRAFT')`;
   `non_editable_fields` via `CASE` con costanti PL/pgSQL.
6. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.ordini` | tabella | sorgente stato |
| `config.stati_doc_ordini` | tabella | risoluzione `codice_interno` e `ordine` |
| `config.transizioni_stati_ordini` | tabella | matrice metadati UI (rev 2026-06-05) |
| `vendite.fn_list_ordini_da_pushare` | funzione | eleggibilità push (riuso, no duplicazione) |
| `20260605-08-create-transizioni-stati-ordini-mctit` | migration 00_schema | crea la matrice |
| `20260605-11-seed-transizioni-stati-ordini-mctit` | migration 80_data | popola le 3 transizioni |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato nella stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come ordine non trovato e risponde 404.
- **Meta mancante**: se una transizione non ha `manuale` → trattata come manuale
  (`COALESCE(..., true)`). Se non ha `requires_confirm` o `outlined` → default `false`.
- **`can_conferma` deprecato**: il vecchio flag booleano del payload BE è eliminato; la
  conferma è ora una entry di `available_actions` (`key="conferma"`).
- **Enforcement separato**: questa funzione è il **lato lettura**. La validità della
  transizione all'esecuzione è garantita dal guard
  [`trgfn_ordini_guard_transizione`](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione),
  che legge la **stessa** matrice.
