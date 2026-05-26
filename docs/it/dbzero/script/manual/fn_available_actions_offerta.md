# fn_available_actions_offerta

### Scopo

Restituisce in un **unico JSONB** tutte le capability dell'offerta commerciale
necessarie al detail endpoint BE. Permette ai drawer Vue di eliminare qualsiasi
ricalcolo di stato/transizioni lato client.

Pattern **data-driven capability layer**: specchio strutturale di
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo),
adattato al dominio offerte commerciali.

Differenze rispetto al preventivo:

- Le transizioni manuali vengono lette da `config.stati_doc_offerte_transizioni`
  (stesso schema di `config.transizioni_stati_preventivi`).
- Il check `can_push_contratto` è **cross-dominio in v1** (controlla
  `EXISTS` su `vendite.contratti.offerta_id`), a differenza di
  `can_push_commessa` del preventivo che usa solo lo stato e rinvia il check
  cross-dominio a Fase 3.
- Le azioni speciali hardcoded sono `crea_revisione` (EMESSA) e
  `push_contratto` (ACCETTATA senza contratto). Entrambe hanno
  `target_state: null` e appaiono in `available_actions` (non solo come flag).

> **Vedi anche**
>
> - [trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione) — guard transizioni (regola reale)
> - [stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) — matrice transizioni + meta UI
> - [fn_push_offerta_a_contratto](/dbzero/vendite/funzioni/fn_push_offerta_a_contratto) — esegue il push (guard idempotenza reale)
> - [fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — esegue la revisione

## Schema

`script` (cross-dominio: legge `vendite.*`, `config.*`).

## Firma

```sql
script.fn_available_actions_offerta(
    p_offerta_id vendite.offerte_commerciali.id%TYPE  -- bigint
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_offerta_id` | `bigint` | Sì | ID dell'offerta. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Lista azioni manuali + speciali disponibili dallo stato corrente.
    // Vuota ([]) per stati terminali (ACCETTATA con contratto, RIFIUTATA, ANNULLATA, SUPERATA).
    // Costruita da config.stati_doc_offerte_transizioni.meta + azioni hardcoded.
    "available_actions": [
        {
            "key": "emetti",
            "target_state": "EMESSA",          // null per azioni speciali (crea_revisione, push_contratto)
            "label_key": "offerte.azione_emetti",
            "severity": "success",
            "icon": "pi pi-send",
            "requires_confirm": true,
            "requires_motivazione": false       // true per annulla e rifiuta
        }
        // ...
    ],
    "can_change_state":             true,    // true se esiste almeno un'azione
    "can_edit_testata":             true,    // true solo in BOZZA
    "can_edit_eccezioni":           true,    // true solo in BOZZA
    "can_edit_utility":             true,    // true solo in BOZZA (utility 1:1 inline)
    "can_create_revisione":         false,   // true solo in EMESSA
    "can_push_contratto":           false,   // true solo in ACCETTATA senza contratto generato
    "can_push_contratto_reason":    "OFFERTA_NON_ACCETTATA",  // null se can_push=true
    "can_push_contratto_reason_key": "offerte.push_reason.non_accettata", // null se can_push=true
    "non_editable_fields":          [...],   // vedi dettaglio sotto
    "stato_codice":                 "BOZZA"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `BOZZA` | `emetti`, `annulla` | Da matrice transizioni |
| `EMESSA` | `accetta`, `rifiuta`, `crea_revisione` | `crea_revisione` hardcoded |
| `ACCETTATA` (senza contratto) | `push_contratto` | Hardcoded, condizionato a check cross-dominio |
| `ACCETTATA` (con contratto) | `[]` | Terminale de-facto |
| `RIFIUTATA` | `[]` | Terminale |
| `ANNULLATA` | `[]` | Terminale |
| `SUPERATA` | `[]` | Terminale tecnico (sostituita da revisione successiva) |

### Coppia `can_push_contratto_reason` / `can_push_contratto_reason_key`

| Caso | `can_push_contratto` | `reason` | `reason_key` |
|------|----------------------|----------|--------------|
| ACCETTATA senza contratto | `true` | `null` | `null` |
| ACCETTATA con contratto già generato | `false` | `OFFERTA_CONTRATTO_GIA_GENERATO` | `offerte.push_reason.gia_generato` |
| Qualsiasi altro stato | `false` | `OFFERTA_NON_ACCETTATA` | `offerte.push_reason.non_accettata` |

### Dettaglio `non_editable_fields`

Due famiglie di immutabilità:

| Famiglia | Campi |
|---|---|
| **Sempre immutabili** (gestiti da trigger transizione stato) | `codice`, `uid`, `revisione_numero`, `revisione_padre_id`, `stato_doc_offerta_id`, `data_emissione`, `data_accettazione`, `data_rifiuto`, `data_annullamento`, `motivazione_rifiuto` |
| **Bloccati fuori BOZZA** | `emittente_fiscale_id`, `billing_account_id`, `istanza_utility_id`, `utility_id`, `listino_id`, `listino_versione_id`, `valore_variazione_globale`, `tipo_variazione_globale`, `validita_dal`, `validita_al`, `meta` |

Risultato per stato:

| Stato | `non_editable_fields` |
|---|---|
| `BOZZA` | Solo famiglia "sempre immutabili" (10 campi) |
| Tutti gli altri | Unione delle due famiglie (21 campi) |

## Algoritmo

1. **Lookup offerta** — JOIN `vendite.offerte_commerciali` ×
   `config.stati_doc_offerte` per ottenere `stato_id` e `codice_interno`.
   `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.stati_doc_offerte_transizioni`
   filtrata per `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`.
   I metadati UI (`label_key`, `severity`, `icon`, `requires_confirm`,
   `requires_motivazione`) vengono letti da `t.meta`. Ordine: `sa.ordine`.
   Filtro defense-in-depth: `AND t.meta ?? 'action_key' AND t.meta ?? 'label_key'`.
3. **Azioni speciali** — aggiunte hardcoded in coda a `v_actions`:
   - `crea_revisione` se `v_stato_cod = 'EMESSA'`.
   - `push_contratto` se `v_stato_cod = 'ACCETTATA'` e `NOT EXISTS`
     contratto con `offerta_id = p_offerta_id`.
4. **Capability derivate** — calcolate da `v_stato_cod`:
   - `can_edit_*` = `(stato = 'BOZZA')`.
   - `can_create_revisione` = `(stato = 'EMESSA')`.
   - `can_push_contratto` + reason come da tabella §2.4 del brief.
5. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.offerte_commerciali` | tabella | sorgente stato e ID |
| `config.stati_doc_offerte` | tabella | risoluzione `codice_interno` e `ordine` |
| `config.stati_doc_offerte_transizioni` | tabella | matrice transizioni + meta UI |
| `vendite.contratti` | tabella | check idempotenza `can_push_contratto` |
| `20260524-22-upsert-stati-doc-offerte-transizioni-mctit` | migration 80_data | seed iniziale meta transizioni |
| `20260526-01-update-stati-doc-offerte-transizioni-meta-mctit` | migration 80_data | completa meta (requires_motivazione, severity, requires_confirm) |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato nella
  stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come offerta non trovata e
  risponde 404 prima di serializzare il payload.
- **Meta mancante**: se una transizione non ha `manuale` in meta, viene
  trattata come manuale (`COALESCE(..., true)`). Se non ha `requires_confirm`
  o `requires_motivazione`, il valore default è `false`.
- **Guard meta keys**: il WHERE esclude transizioni manuali senza
  `action_key` o `label_key` (defense-in-depth equivalente a
  `ck_transizioni_stati_prev_meta_ui` dei preventivi).
- **Idempotenza push**: la guard reale risiede in
  `vendite.fn_push_offerta_a_contratto` (errore `E_OFFERTA_CONTRATTO_GIA_GENERATO`
  + `UNIQUE uq_contratti_offerta_id`). Qui si calcola solo l'abilitabilità UI.
- **Azioni speciali `target_state: null`**: il FE distingue queste azioni
  dal `key` (`crea_revisione` e `push_contratto` usano routing speciale nel
  drawer; le transizioni standard usano l'endpoint generico cambio-stato).
