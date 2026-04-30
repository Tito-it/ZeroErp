# fn_available_actions_contratto

### Scopo

Restituisce in un **unico JSONB** tutte le capability del contratto
necessarie al detail endpoint BE (Fase 1 refactor frontend vendite,
2026-04-30). Permette ai drawer Vue di eliminare qualsiasi ricalcolo
di stato/transizioni lato client.

Differenza chiave rispetto a
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo):
i contratti non hanno `config.transizioni_stati_contratti`; il grafo
è hardcodato nel trigger
[trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato).
I metadati UI sono memorizzati in `config.stati_doc_contratti.meta`
(campo `outgoing_action`) e arricchiti a runtime con le date contestuali
(per la cessazione).

> **Vedi anche**
>
> - [trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato) — guard transizioni (regola reale)
> - [stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) — store metadati UI via campo `meta`
> - [contratti](/dbzero/vendite/tabelle/contratti) — entità sorgente

## Schema

`script` (cross-dominio: legge `vendite.*` e `config.*`).

## Firma

```sql
script.fn_available_actions_contratto(
    p_contratto_id vendite.contratti.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_contratto_id` | `bigint` | Sì, `> 0` | ID del contratto. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // 0 o 1 azione disponibile dallo stato corrente.
    // Vuota ([]) in CESSATO (terminale).
    "available_actions": [
        {
            "key": "cessa",
            "target_state": "CESSATO",
            "label_key": "contratti.azione_cessa",
            "severity": "danger",
            "icon": "pi pi-stop",
            "requires_confirm": true,
            "requires_date": true,         // presente solo per la cessazione
            "default_date": "2026-04-30",  // CURRENT_DATE — suggerisce cessazione stasera
            "min_date": "2026-01-15"       // contratto.valido_dal — non si cessa prima dell'inizio
        }
    ],
    "can_change_state":   true,   // true se esiste almeno un'azione disponibile
    "can_edit_testata":   true,   // false solo in CESSATO
    "can_edit_righe":     false,  // true solo in DRAFT
    "non_editable_fields": [...], // vedi dettaglio sotto
    "stato_codice":       "ATTIVO"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azione | Note |
|---|---|---|
| `DRAFT` | `attiva` | target `ATTIVO`, `requires_date=false` |
| `ATTIVO` | `cessa` | target `CESSATO`, `requires_date=true` + `default_date` + `min_date` |
| `CESSATO` | `[]` | terminale |

### Dettaglio `non_editable_fields`

Allineati a `_CONTRATTO_PATCH_ALLOWED_BY_STATE` in `contratti_service.py`:

| Stato | `non_editable_fields` |
|---|---|
| `DRAFT` | `[]` — tutto editabile |
| `ATTIVO` | Tutti i campi tranne `valido_al` e `meta` |
| `CESSATO` | Tutti i campi testata inclusi `valido_al` e `meta` |

Campi bloccati in **ATTIVO**:
```json
["billing_account_id", "istanza_utility_id", "utility_id", "ambito",
 "valido_dal", "parent_contratto_id", "data", "listino_id",
 "tipo_variazione_globale", "valore_variazione_globale",
 "categoria_cliente_id_snapshot"]
```

### `can_edit_testata` in ATTIVO

`true` — il contratto in ATTIVO è **parzialmente editabile**
(`valido_al` e `meta` rimangono modificabili). Il drawer Vue deve usare
`non_editable_fields` per disabilitare i singoli campi, non trattare
ATTIVO come completamente readonly.

## Algoritmo

1. **Lookup contratto** — JOIN `vendite.contratti` × `config.stati_doc_contratti`
   per ottenere `stato_id`, `codice_interno`, `meta`, `valido_dal`.
   `NOT FOUND` → `RETURN NULL`.
2. **Azione disponibile** — legge `v_stato_meta -> 'outgoing_action'` dal meta
   dello stato corrente. Se `NULL` (CESSATO) → `available_actions = []`.
3. **Arricchimento date** — se `requires_date IS TRUE` (azione "cessa"):
   aggiunge `default_date = CURRENT_DATE::text` e `min_date = valido_dal::text`
   con `jsonb ||`. Le date dipendono dal contratto specifico, non dallo stato.
4. **Capability editabilità** — calcolate da `v_stato_cod`:
   - `can_edit_testata = (stato <> 'CESSATO')`
   - `can_edit_righe = (stato = 'DRAFT')`
   - `non_editable_fields`: `CASE` su stato con costanti PL/pgSQL (`c_non_edit_attivo`, `c_non_edit_tutti`).
5. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

### Cessazione programmata vs immediata

Il trigger `trgfn_contratti_guard_transizione_stato` permette
`ATTIVO → CESSATO` **solo se** `valido_al < CURRENT_DATE`. Per date
future, il BE esegue solo `PATCH valido_al` (nessun cambio stato); il
job pgAgent `chiusura_scadenze_daily` porta il contratto in CESSATO
quando la data scade. La funzione non gestisce questa distinzione: mostra
sempre l'azione "cessa" con `requires_date=true`; la scelta
programmata/immediata è responsabilità del BE al momento dell'esecuzione.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.contratti` | tabella | sorgente stato e `valido_dal` |
| `config.stati_doc_contratti` | tabella | store metadati UI (`meta.outgoing_action`) |
| `20260430-61-update-stati-doc-contratti-meta-ui-mctit` | migration 80_data | popola `meta.outgoing_action` su DRAFT e ATTIVO |

## Note operative

- **STABLE**: solo lettura; risultato stabile per transazione.
- **Fallback NULL**: il BE interpreta `NULL` come contratto non trovato
  e risponde 404 prima di serializzare il payload.
- **Meta mancante**: se `stati_doc_contratti.meta` non ha `outgoing_action`
  (es. CESSATO), `available_actions = []` e `can_change_state = false`.
