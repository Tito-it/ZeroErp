# fn_available_actions_contratto

### Scopo

Restituisce in un **unico JSONB** tutte le capability del contratto
necessarie al detail endpoint BE. Permette ai drawer Vue di eliminare qualsiasi
ricalcolo di stato/transizioni lato client.

Pattern **data-driven capability layer**: allineato a
[fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo)
e [fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta).
Dalla rev 2026-05-28 legge `available_actions[]` da
`config.transizioni_stati_contratti` (3 transizioni) invece del campo
`stati_doc_contratti.meta.outgoing_action` (singola azione, pattern precedente).

Differenza residua rispetto agli altri due domini: le azioni con
`requires_date=true` (es. `cessa`) vengono arricchite a runtime con
`default_date` e `min_date` contestuali al contratto specifico.

> **Vedi anche**
>
> - [trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato) — guard transizioni (regola di business reale)
> - [transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti) — matrice metadati UI
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
| `p_contratto_id` | `bigint` | Sì | ID del contratto. Ritorna `NULL` se non esiste (gestito dal BE come 404). |

## Output

`jsonb` con le seguenti chiavi (contratto API stabile):

```jsonc
{
    // Lista azioni manuali disponibili dallo stato corrente.
    // Vuota ([]) per stati terminali (CESSATO, ANNULLATO).
    // Costruita da config.transizioni_stati_contratti.meta.
    "available_actions": [
        {
            "key": "attiva",
            "target_state": "ATTIVO",
            "label_key": "contratti.azione_attiva",
            "severity": "info",
            "requires_confirm": false,
            "requires_date": false,      // true solo per cessa → arricchita con default_date e min_date
            "outlined": false            // true per annulla (peso visivo ridotto)
        }
    ],
    "can_change_state":   true,    // true se available_actions non è vuota
    "can_edit_testata":   true,    // true in DRAFT e ATTIVO; false in terminali (CESSATO, ANNULLATO)
    "can_edit_righe":     true,    // true solo in DRAFT
    "non_editable_fields": [...],  // vedi dettaglio sotto
    "stato_codice":       "DRAFT"
}
```

### Dettaglio `available_actions` per stato

| `stato_codice` | Azioni in `available_actions` | Note |
|---|---|---|
| `DRAFT` | `attiva`, `annulla` | Due azioni dal 28-05-2026; prima ne aveva una sola |
| `ATTIVO` | `cessa` | Arricchita con `default_date` e `min_date` contestuali |
| `CESSATO` | `[]` | Terminale |
| `ANNULLATO` | `[]` | Terminale (`is_abortito=true`) |

### Arricchimento `cessa` — campi contestuali

L'azione `cessa` (ATTIVO → CESSATO) ha `requires_date=true` nel seed. La funzione
la arricchisce a runtime con:

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| `default_date` | `CURRENT_DATE::text` | Data suggerita dalla UI (cessazione questa sera via job) |
| `min_date` | `contratto.valido_dal::text` | Data minima accettabile (invariante di business) |

L'arricchimento usa `jsonb_array_elements` sul risultato aggregato: trova dinamicamente
qualsiasi azione con `requires_date=true` senza accoppiarsi al nome `cessa`.

### Dettaglio `non_editable_fields`

| Stato | `can_edit_testata` | `can_edit_righe` | `non_editable_fields` |
|---|:---:|:---:|---|
| `DRAFT` | `true` | `true` | `[]` — tutto editabile |
| `ATTIVO` | `true` | `false` | Tutti i campi tranne `valido_al` e `meta` |
| `CESSATO` | `false` | `false` | Tutti i campi testata inclusi `valido_al` e `meta` |
| `ANNULLATO` | `false` | `false` | Tutti i campi testata inclusi `valido_al` e `meta` |

Campi bloccati in **ATTIVO** (allineati a `_CONTRATTO_PATCH_ALLOWED_BY_STATE`):
```json
["billing_account_id", "istanza_utility_id", "utility_id", "ambito",
 "valido_dal", "parent_contratto_id", "data", "listino_id",
 "tipo_variazione_globale", "valore_variazione_globale",
 "categoria_cliente_id_snapshot"]
```

> **`can_edit_testata` in ATTIVO** — rimane `true`: il contratto ATTIVO è
> parzialmente editabile (`valido_al` e `meta` modificabili per cessazione programmata
> e note). Il drawer Vue usa `non_editable_fields` per disabilitare i singoli campi.

## Algoritmo

1. **Lookup contratto** — JOIN `vendite.contratti` × `config.stati_doc_contratti`
   per ottenere `stato_id`, `codice_interno`, `valido_dal`.
   `NOT FOUND` → `RETURN NULL`.
2. **Transizioni manuali** — `jsonb_agg` su `config.transizioni_stati_contratti`
   filtrata per `stato_da_id = v_stato_id AND attivo IS TRUE AND manuale IS NOT FALSE`.
   I metadati UI (`label_key`, `severity`, `requires_confirm`, `requires_date`,
   `outlined`) vengono letti da `t.meta`; l'icona la sceglie il frontend dal `key`. Ordine: `sa.ordine`.
   Guard defense-in-depth: `AND t.meta ? 'action_key' AND t.meta ? 'label_key'`.
3. **Arricchimento `requires_date`** — via `jsonb_array_elements`: ogni azione
   con `requires_date=true` riceve `default_date = CURRENT_DATE` e
   `min_date = valido_dal`. Non accoppiato al nome dell'azione.
4. **Capability editabilità** — calcolate da `v_stato_cod`:
   - `can_edit_testata = (stato IN ('DRAFT', 'ATTIVO'))`
   - `can_edit_righe = (stato = 'DRAFT')`
   - `non_editable_fields`: `CASE` su stato con costanti PL/pgSQL.
5. **Build JSONB** — `jsonb_build_object` con tutte le chiavi.

### Cessazione programmata vs immediata

Il trigger `trgfn_contratti_guard_transizione_stato` permette `ATTIVO → CESSATO`
**solo se** `valido_al IS NOT NULL`. Per cessazione manuale, vieta date retroattive
(raise `E_CONTRATTO_VALIDO_AL_RETROATTIVO`). Il job pgAgent
`chiusura_scadenze_daily` porta automaticamente in CESSATO i contratti con
`valido_al < CURRENT_DATE`. La funzione non distingue i due casi: mostra sempre
`cessa` con `requires_date=true`; la scelta programmata/immediata è responsabilità
del BE all'esecuzione.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.contratti` | tabella | sorgente stato e `valido_dal` |
| `config.stati_doc_contratti` | tabella | risoluzione `codice_interno` e `ordine` |
| `config.transizioni_stati_contratti` | tabella | matrice metadati UI (da rev 28-05-2026) |
| `20260528-04-create-transizioni-stati-contratti-mctit` | migration 00_schema | crea la tabella |
| `20260528-06-seed-transizioni-stati-contratti-mctit` | migration 80_data | popola le 3 transizioni |

## Note operative

- **STABLE**: solo lettura; il pianificatore può riusare il risultato nella stessa transazione.
- **Fallback NULL**: il BE interpreta `NULL` come contratto non trovato e risponde 404.
- **Meta mancante**: se una transizione non ha `manuale` → trattata come manuale
  (`COALESCE(..., true)`). Se non ha `requires_confirm`, `requires_date` o `outlined`
  → default `false`.
- **Fix bug ANNULLATO (rev 28-05-2026)**: `can_edit_testata` era `true` per ANNULLATO
  (il check era `<> 'CESSATO'`; ANNULLATO fu introdotto in 20260520 senza aggiornare la
  funzione). Ora: `can_edit_testata = stato IN ('DRAFT', 'ATTIVO')`.
- **`stati_doc_contratti.meta.outgoing_action`**: campo storico presente su DRAFT e ATTIVO
  in DB, non più letto dalla funzione. Da rimuovere nella prossima PR che tocca
  `stati_doc_contratti` (vedi `transizioni_stati_contratti` §Regole operative).

## Rev 2026-09-24 — «Attiva» spento finché un prezzo non è autorizzato

Regola decisa da Tid: *un prezzo che nessuno ha autorizzato non esce dalla bozza*. Un
contratto con una riga o un componente BoM **attivi** in attesa di approvazione
(`PENDING`) o **rifiutati** (`REJECTED`) non si attiva.

* La funzione passa alla forma dell'**array dei motivi**, come preventivo e ordine:
  `enabled`, `reason` e `reason_key` di ogni azione discendono da una chiave **nuova**,
  `reasons`. Nessuna chiave tolta.
* Verso `ATTIVO` l'array contiene prima i motivi di [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati), poi il generico «documento
  vuoto» di prima (`DOCUMENTO_SENZA_RIGHE`, invariato). Il primo è quello che il
  frontend mostra da solo.
* È lo stesso building block che
  [`vendite.trgfn_contratti_guard_transizione_stato`](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)
  usa per sollevare: pulsante e database non possono dissentire.

Motivi nuovi: `PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`, con `reason_key`
`common.azione_reason.prezzo_pendente` / `common.azione_reason.prezzo_rifiutato`.
(changeSet `20260924-26`, brief `brief-db-preventivi-congelamento-pricing`.)
