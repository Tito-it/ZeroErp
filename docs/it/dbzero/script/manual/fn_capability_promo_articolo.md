# fn_capability_promo_articolo

### Scopo

Restituisce in un **unico JSONB** le capability di editing della promo
articolo per il detail endpoint BE (Fase 1 refactor frontend vendite,
2026-04-30).

A differenza di
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo)
e
[fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto),
le promo **non hanno stato persistito né transizioni manuali**: lo
stato è date-driven, calcolato live da `CURRENT_DATE` vs `valido_dal` /
`valido_al`. Il JSONB non include `available_actions` (non esistono
azioni di cambio-stato) — da qui il nome `fn_capability_*` invece di
`fn_available_actions_*`.

La logica del dispatch è uno specchio esatto del trigger
[trgfn_promo_articoli_guard_data_driven](/dbzero/vendite/funzioni/trgfn_promo_articoli_guard_data_driven),
garantendo consistenza totale tra capability esposta all'API e guard DB.

> **Vedi anche**
>
> - [trgfn_promo_articoli_guard_data_driven](/dbzero/vendite/funzioni/trgfn_promo_articoli_guard_data_driven) — guard reale (usa `OLD.*` su UPDATE)
> - [promo_articoli](/dbzero/vendite/tabelle/promo_articoli) — entità sorgente

## Schema

`script` (cross-dominio: legge `vendite.*`).

## Firma

```sql
script.fn_capability_promo_articolo(
    p_promo_id vendite.promo_articoli.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_promo_id` | `bigint` | Sì, `> 0` | ID della promo. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    "stato_temporale":     "FUTURA",      // FUTURA | INIZIATA | SCADUTA
    "can_update":          true,          // false solo in SCADUTA
    "can_update_reason":   null,          // reason code se false
    "non_editable_fields": [],            // varia per stato (vedi sotto)
    "min_valido_dal":      "2026-05-01",  // null se non applicabile
    "min_valido_al":       "2026-04-30"   // null se non applicabile
}
```

### Stati temporali

| Stato | Condizione | `can_update` |
|---|---|:---:|
| `FUTURA` | `CURRENT_DATE < valido_dal` | `true` |
| `INIZIATA` | `valido_dal ≤ CURRENT_DATE ≤ valido_al` | `true` |
| `SCADUTA` | `CURRENT_DATE > valido_al` | `false` |

### `non_editable_fields` per stato

Allineati alla whitelist del trigger guard (usa `OLD.*`):

| Stato | `non_editable_fields` | Campi ancora editabili |
|---|---|---|
| `FUTURA` | `[]` | tutti (con vincoli su date) |
| `INIZIATA` | `codice`, `articolo_id`, `uom_id`, `tipo_variazione`, `valore_variazione`, `valido_dal`, `attivo` | `descrizione`, `valido_al`, `meta` |
| `SCADUTA` | tutti i campi dominio | nessuno |

### `min_valido_dal` / `min_valido_al` per stato

| Stato | `min_valido_dal` | `min_valido_al` |
|---|---|---|
| `FUTURA` | `CURRENT_DATE + 1` — trigger blocca `valido_dal ≤ oggi` | `CURRENT_DATE` — trigger blocca `valido_al < oggi` |
| `INIZIATA` | `null` — `valido_dal` immutabile | `CURRENT_DATE` — trigger blocca `valido_al < oggi` |
| `SCADUTA` | `null` | `null` |

## Algoritmo

1. **Lookup promo** — `SELECT valido_dal, valido_al FROM vendite.promo_articoli WHERE id = p_promo_id`. `NOT FOUND` → `RETURN NULL`.
2. **Dispatch stato** — confronti mutuamente esclusivi con `v_today = CURRENT_DATE`:
   - `v_today < valido_dal` → `FUTURA`
   - `v_today <= valido_al` → `INIZIATA` (necessariamente `valido_dal ≤ oggi`)
   - `ELSE` → `SCADUTA`
3. **Assegnazione variabili** — `can_update`, `non_editable_fields`, `min_valido_dal`, `min_valido_al` assegnate nel ramo corretto.
4. **Build JSONB** — `jsonb_build_object`.

### Consistenza con il trigger guard

Il trigger usa `OLD.valido_dal` / `OLD.valido_al` (valori prima dell'UPDATE).
La funzione usa i valori correnti della riga, che saranno `OLD.*` al momento
del successivo UPDATE: la capability calcolata è sempre coerente con il guard
che verrà eseguito sull'operazione.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.promo_articoli` | tabella | sorgente `valido_dal` / `valido_al` |
| `trgfn_promo_articoli_guard_data_driven` | trigger | guard reale — logica speculare |

## Note operative

- **STABLE**: solo lettura. `CURRENT_DATE` è stabile per transazione
  (PostgreSQL snapshot consistency) → `STABLE` è corretto.
- **Nessun file 80_data**: il calcolo non dipende da dati di configurazione.
- **Fallback NULL**: il BE interpreta `NULL` come promo non trovata (404).
- **`tipo_variazione_options`**: il documento di analisi menziona questo
  campo nel detail. È un lookup statico gestito in Fase 2 (endpoint dedicato)
  e **non è incluso** in questa funzione.
