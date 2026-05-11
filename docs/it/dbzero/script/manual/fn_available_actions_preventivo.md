# fn_available_actions_preventivo

### Scopo

Restituisce in un **unico JSONB** tutte le capability del preventivo
necessarie al detail endpoint BE (Fase 1 refactor frontend vendite,
2026-04-30). Permette ai drawer Vue di eliminare qualsiasi ricalcolo
di stato/transizioni lato client: il FE legge il payload e renderizza
di conseguenza.

> **Vedi anche**
>
> - [fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo) — esegue la transizione (guard reale)
> - [transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi) — matrice configurabile da cui si leggono le azioni
> - [preventivi](/dbzero/vendite/tabelle/preventivi) — entità sorgente

## Schema

`script` (cross-dominio: legge `vendite.*` e `config.*`).

## Firma

```sql
script.fn_available_actions_preventivo(
    p_preventivo_id vendite.preventivi.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_preventivo_id` | `bigint` | Sì, `> 0` | ID del preventivo. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Lista azioni manuali disponibili dallo stato corrente.
    // Vuota ([]) per stati terminali (ANNULLATO, RIFIUTATO, SCADUTO).
    // Costruita dalla matrice config.transizioni_stati_preventivi.meta.
    "available_actions": [
        {
            "key": "emetti",                       // chiave semantica
            "target_state": "EMESSO",              // codice_interno stato destinazione
            "label_key": "preventivi.azione_emetti", // chiave i18n per il label bottone
            "severity": "info",                    // severity PrimeVue
            "icon": "pi pi-send",                  // classe PrimeIcons
            "requires_confirm": false              // se true → dialog conferma
        }
    ],
    "can_edit_testata":             true,    // true solo in DRAFT
    "can_edit_righe":               true,    // true solo in DRAFT
    "can_push_commessa":            false,   // true solo in ACCETTATO
    "can_push_commessa_reason":     "PREVENTIVO_NON_ACCETTATO",         // reason code machine-readable; null se can_push=true
    "can_push_commessa_reason_key": "preventivi.push_commessa_reason.non_accettato", // chiave i18n associata; null se can_push=true
    "can_create_revisione":         false,   // true in EMESSO o ACCETTATO
    "non_editable_fields":          ["utility_id"],  // sempre presente; vedi dettaglio sotto
    "stato_codice":                 "DRAFT"  // codice_interno stato corrente
}
```

### Coppia `can_push_commessa_reason` / `can_push_commessa_reason_key`

- **`can_push_commessa_reason`** = reason code stabile machine-readable, usato in log e da BE per logica condizionale (es. `'PREVENTIVO_NON_ACCETTATO'`).
- **`can_push_commessa_reason_key`** = chiave i18n pronta per `$t()` lato FE (es. `'preventivi.push_commessa_reason.non_accettato'`).

Le due chiavi sono sempre coerenti (entrambe `null` quando `can_push_commessa=true`, entrambe valorizzate altrimenti). In Fase 3 saranno aggiunti nuovi reason cross-dominio (commesse già pushate, approvazioni pendenti); il BE usa il reason, il FE traduce via key.

### Dettaglio `non_editable_fields`

Due famiglie di immutabilità:

| Famiglia | Campi | Sempre? |
|---|---|---|
| Sempre immutabili (regola di dominio) | `utility_id` | sì, anche in DRAFT |
| Bloccati fuori DRAFT (whitelist Python) | `billing_account_id`, `istanza_utility_id`, `valuta_id`, `termine_pagamento_id`, `validita_dal`, `validita_al`, `competenza_mese`, `fatturazione_immediata`, `meta` | solo fuori DRAFT |

Risultato per stato:

| Stato | `non_editable_fields` |
|---|---|
| `DRAFT` | `["utility_id"]` |
| Fuori DRAFT | `["utility_id", "billing_account_id", "istanza_utility_id", "valuta_id", "termine_pagamento_id", "validita_dal", "validita_al", "competenza_mese", "fatturazione_immediata", "meta"]` |

> **Nota di consistenza** — `utility_id` è nella whitelist `aggiorna_preventivo` del service Python al momento. Il BE deve rimuoverlo dalla whitelist per allineare il contratto API alla regola di dominio (l'utility identifica il preventivo, non cambia post-create). Senza la rimozione lato Python, il FE renderizza il campo readonly ma il PATCH lo accetta — incoerenza temporanea ammessa in fase di sviluppo.

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni disponibili |
|---|---|
| `DRAFT` | `emetti`, `annulla` |
| `EMESSO` | `accetta`, `rifiuta`, `annulla` |
| `ACCETTATO` | `annulla` |
| `ANNULLATO` / `RIFIUTATO` / `SCADUTO` | `[]` |

La transizione `EMESSO → SCADUTO` è **automatica** (job notturno) e
marcata `manuale=false` in `transizioni_stati_preventivi.meta`: viene
esclusa dalla lista.

## Algoritmo

1. **Lookup preventivo** — JOIN `vendite.preventivi` × `config.stati_doc_preventivi`
   per ottenere `stato_id` e `codice_interno`. `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.transizioni_stati_preventivi`
   filtrata per `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`.
   I metadati UI (`label_key`, `severity`, `icon`, `requires_confirm`) vengono
   letti direttamente da `t.meta`. Ordine: `sa.ordine` (ordine stati config).
3. **Capability derivate** — calcolate da `v_stato_cod` con semplici confronti:
   - `can_edit_testata / can_edit_righe = (stato = 'DRAFT')`
   - `can_push_commessa = (stato = 'ACCETTATO')`
   - `can_create_revisione = (stato IN ('EMESSO','ACCETTATO'))`
   - `non_editable_fields`: `[]` in DRAFT, costante `c_non_edit` altrove.
4. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

> **Nota Fase 3** — `can_push_commessa` è derivato dallo stato soltanto.
> Il check cross-dominio (righe già in commessa con `stato_emissione=EMESSA`)
> è rinviato a Fase 3 e sarà aggiunto senza modificare il contratto API.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.preventivi` | tabella | sorgente stato e ID |
| `config.stati_doc_preventivi` | tabella | risoluzione `codice_interno` |
| `config.transizioni_stati_preventivi` | tabella | matrice transizioni + meta UI |
| `20260430-60-update-transizioni-stati-preventivi-meta-ui-mctit` | migration 80_data | popola `meta` con `label_key`/`severity`/`icon`/`manuale` |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato
  nella stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come preventivo non trovato
  e risponde 404 prima di serializzare il payload.
- **Meta mancante**: se una transizione non ha `manuale` in meta, viene
  trattata come manuale (`COALESCE(..., true)`). Se non ha `requires_confirm`,
  il valore default è `false`.
- **Guard meta keys (rev 11-05-2026)**: la WHERE dell'aggregazione include
  `AND t.meta ? 'action_key' AND t.meta ? 'label_key'`. Questo è un layer
  defense-in-depth rispetto al CHECK `ck_transizioni_stati_prev_meta_ui`
  sulla tabella: anche se un DBA inserisse una riga manuale con meta incompleto
  bypassando il vincolo, la funzione non la esporrebbe. Sicuro in questo
  punto perché siamo già nella branch `manuale IS TRUE` (COALESCE sopra),
  quindi le transizioni automatiche (es. EMESSO→SCADUTO con `manuale=false`)
  sono già escluse prima di questo check.
