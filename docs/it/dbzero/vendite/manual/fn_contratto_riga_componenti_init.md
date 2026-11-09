# fn_contratto_riga_componenti_init

### Scopo

Inizializza i componenti BoM (modello unificato) per una riga contratto composita. Per ogni componente attivo della BoM: se presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto = v_articolo_id` per attivare il pricing bundle — se il resolver fallisce, solleva `E_DOC_COMPONENTE_LISTINO_MANCANTE`. Idempotente. No-op se `quantita IS NULL` (riga a consumo senza quantità fissa) **o se `tipo_eccezione = 'ESCLUSIONE'`** (articolo escluso interamente: nessun prezzo, nessun componente).

> **Vedi anche**
>
> - [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — tabella popolata
> - [vendite.fn_contratto_riga_componenti_preview](/dbzero/vendite/funzioni/fn_contratto_riga_componenti_preview) — preview read-only per il drawer (form atomic)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_contratto_riga_componenti_init(
    p_riga_id                vendite.contratti_righe.id%TYPE,
    p_emittente_sr_id        anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento       date,
    p_componenti_overrides   jsonb DEFAULT NULL
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga contratto padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma `COALESCE(contratti.valido_dal, contratti.data)`. |
| `p_componenti_overrides` | `jsonb` | No | Mappa `{"<componente_id>": <prezzo_numeric>}`. Override con prezzo `= 0` → raise `E_PARAMETRO_INVALIDO`. |

## Output

`integer`: numero di componenti inseriti in `contratti_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito, `tipo_eccezione = 'ESCLUSIONE'`, componenti già presenti, oppure `quantita IS NULL`. |
| `> 0` | Componenti inseriti con successo. |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id`.
2. **Lettura riga padre** — un'unica query JOIN tra `contratti_righe` e `catalogo.articoli` recupera in un solo round-trip: `articolo_id`, `codice`, `uom_operativa_id`, `quantita`, `contratto_id`, `tipo_eccezione` e `is_composito`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **No-op ESCLUSIONE (guard difensivo)** — se `tipo_eccezione = 'ESCLUSIONE'`, ritorna 0. Una riga di esclusione rimuove l'articolo per intero: per il CHECK `chk_contrighe_prezzo_per_tipo_eccezione` il prezzo padre deve restare NULL, quindi non vanno creati componenti. Inizializzarli scatenerebbe il ricalcolo del prezzo padre (`_z90_ricalcola_padre → SUM(figli)`) in violazione del CHECK. Vedi [§nota sul modello](#modello-esclusione-nessun-componente).
5. **No-op quantita NULL** — se `contratti_righe.quantita IS NULL` (riga a consumo), ritorna 0. Non è possibile calcolare `coeff_qta × NULL`.
6. **Idempotenza** — se esistono già righe in `contratti_righe_componenti`, ritorna 0.
7. **Lettura parametri contratto** — `billing_account_id`, `utility_id`, `istanza_utility_id` da `contratti`.
8. **Loop per-componente** — per ogni legame della distinta a `p_data_riferimento`, letto da `catalogo.fn_distinta_alla_data` (attivo e in vigore quel giorno), senza filtro sull'esposizione in fattura (`esposizione_in_fattura`, fino al 2026-10-01 il booleano `esposto_in_fattura`):
   - **Path override**: se `p_componenti_overrides ? componente_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`. Prezzo = 0 → raise `E_PARAMETRO_INVALIDO` **solo** se `v_comp.obbligatorio = TRUE`; per i componenti opzionali, prezzo = 0 è ammesso.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto := v_articolo_id`. Se esiste una riga in `vendite.listini_righe_componenti` per (listino_versione, padre, figlio, data), il resolver ritorna `origine = 'LISTINO_BUNDLE'`. Se fallisce → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
   - **INSERT**: `attivo = TRUE` per tutti i componenti (BoM = contratto immutabile: l'operatore non sceglie quali includere).
9. **INSERT componente** — `prezzo_unitario` NOT NULL, `origine_prezzo`, `prezzo_resolver_context` JSONB (include `istanza_utility_id`, `listino_riga_id`, `contratto_id`).
10. **Check BoM vuota** — se `v_inserted = 0` dopo il loop → raise `E_DOC_COMPOSITO_BOM_VUOTA` (442). Non scatta in caso di idempotenza (intercettata al passo 6).

## Differenze rispetto alle altre fn_init

| Aspetto | Preventivi | Ordini | DDT | Contratti |
|---|---|---|---|---|
| `utility_id` | da preventivi NOT NULL | da ordini nullable | da ddt integer | da contratti NOT NULL |
| `istanza_utility_id` | — | — | — | incluso nel context JSONB |
| No-op `quantita IS NULL` | — | — | — | ✅ (righe a consumo) |
| Loop BoM | tutti i componenti attivi (modello unificato) | identico | identico | identico |
| `attivo` INSERT | `TRUE` (BoM immutabile) | identico | identico | identico |
| Guard ESCLUSIONE | — | — | — | ✅ no-op `RETURN 0` |
| Context JSONB extra | — | — | — | `listino_riga_id`, `contratto_id` sempre inclusi |

## `prezzo_resolver_context` JSONB

Struttura via resolver (successo):
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7,
    "listino_id": 7,
    "listino_versione_id": 12,
    "listino_riga_id": 45,
    "contratto_id": null,
    "origine": "LISTINO_BUNDLE"
}
```

Nota: `listino_riga_id` e `contratto_id` sono sempre inclusi nel context JSONB dei contratti (anche quando NULL), per supportare audit completo del percorso di pricing.

Struttura via override:
```jsonc
{
    "override": true,
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7
}
```

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.contratti_righe` | tabella | sorgente articolo_id, uom, quantita, contratto_id |
| `vendite.contratti` | tabella | sorgente billing_account_id, utility_id, istanza_utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | BoM per-componente |
| `vendite.fn_resolve_prezzo_listino_v2` | funzione | resolver per-componente |
| `vendite.contratti_righe_componenti` | tabella | destinazione INSERT |

## Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_riga_id`/`p_emittente_sr_id` NULL/≤0; riga non trovata; override con prezzo = 0 su componente obbligatorio |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` (id 440) | Resolver fallisce per un componente senza override |
| `E_DOC_COMPOSITO_BOM_VUOTA` (442) | Articolo composito senza componenti attivi e validi alla data di riferimento |

## Modello: ESCLUSIONE = nessun componente

Sulla riga contratto `tipo_eccezione` governa il prezzo (CHECK
`chk_contrighe_prezzo_per_tipo_eccezione`):

- **OVERRIDE / AGGIUNTA** → l'articolo **ha un prezzo** (`prezzo_unitario NOT NULL`);
- **ESCLUSIONE** → l'articolo è **escluso interamente**, **non ha prezzo**
  (`prezzo_unitario IS NULL`).

Per coerenza con questo invariante, **una riga ESCLUSIONE non ha componenti BoM**:
non ha senso negoziare il prezzo dei pezzi di qualcosa che stai togliendo. Il
guard al passo 4 è la rete di sicurezza a DB (single source of truth): rende la
funzione corretta per qualunque chiamante (BE, FE, script, fix dati), anche se
oggi BE e FE già saltano l'auto-init per le ESCLUSIONI. Specchio simmetrico in
[`fn_offerta_eccezione_componenti_init`](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_init).

## Note operative

- **`p_data_riferimento`**: il BE deve passare `COALESCE(contratti.valido_dal, contratti.data)` come convenzione, allineata a `fn_list_contratti_da_pushare`.
- **Righe ESCLUSIONE**: la funzione ritorna 0 senza creare componenti (passo 4). Il FE/BE evitano comunque di chiamarla per le ESCLUSIONI; il guard a DB protegge gli altri chiamanti.
- **Righe a consumo**: se `contratti_righe.quantita IS NULL` la funzione ritorna 0 silenziosamente. Il BE deve gestire il caso in UI prima di chiamare la init.
- **`prezzo_unitario` sempre NOT NULL**: con form atomic, ogni INSERT ha prezzo valorizzato. Il check prezzo ≠ 0 è condizionale: obbligatori non possono avere prezzo = 0 (`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`), opzionali ammettono qualsiasi valore incluso 0.
- **Campo `attivo`**: tutti i componenti sono inseriti con `attivo = TRUE` (BoM = contratto immutabile per documento). Il guard prezzo = 0 sui soli obbligatori resta l'unico vincolo differenziato per `obbligatorio`.
- **Trigger attivati**: INSERT in `contratti_righe_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`.
- **Non STABLE**: VOLATILE per default.
