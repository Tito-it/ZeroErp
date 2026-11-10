# fn_preventivo_riga_componenti_init

### Scopo

Inizializza i componenti BoM (modello unificato) per una riga preventivo composita. Per ogni componente attivo della BoM al `p_data_riferimento`: se è presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto = v_articolo_id` per attivare il pricing bundle — se il resolver fallisce, solleva immediatamente `E_DOC_COMPONENTE_LISTINO_MANCANTE` senza inserire nulla. Idempotente.

> **Vedi anche**
>
> - [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — tabella popolata
> - [vendite.fn_preventivo_riga_componenti_preview](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview) — preview read-only per il drawer (form atomic)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_preventivo_riga_componenti_init(
    p_riga_id                vendite.preventivi_righe.id%TYPE,
    p_emittente_sr_id        anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento       date,
    p_componenti_overrides   jsonb DEFAULT NULL
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga preventivo padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM (`validita @> data`). Di norma uguale a `preventivi.data`. |
| `p_componenti_overrides` | `jsonb` | No | Mappa `{"<componente_id>": <prezzo_numeric>}`. Se presente per un componente, quel prezzo viene usato direttamente (origine `MANUALE`) senza chiamare il resolver. Override con prezzo `= 0` → raise `E_PARAMETRO_INVALIDO`. |

## Output

`integer`: numero di componenti inseriti in `preventivi_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo. |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — un'unica query JOIN tra `preventivi_righe` e `catalogo.articoli` recupera in un solo round-trip: `articolo_id`, `codice`, `uom_operativa_id`, `quantita`, `preventivo_id` e `is_composito`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0 silenziosamente.
4. **Idempotenza** — se esistono già righe in `preventivi_righe_componenti` con `riga_preventivo_id = p_riga_id`, ritorna 0 senza modifiche.
5. **Lettura parametri preventivo** — `billing_account_id`, `utility_id` da `preventivi`.
6. **Loop per-componente** — per ogni legame della distinta a `p_data_riferimento`, letto da `catalogo.fn_distinta_alla_data` (attivo e in vigore quel giorno), senza filtro sull'esposizione in fattura (`esposizione_in_fattura`, fino al 2026-10-01 il booleano `esposto_in_fattura`):
   - **Path override**: se `p_componenti_overrides ? componente_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`. Prezzo = 0 → raise `E_PARAMETRO_INVALIDO` **solo** se `v_comp.obbligatorio = TRUE`; per i componenti opzionali, prezzo = 0 è ammesso.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2(componente_id, uom, data, ba_id, utility_id, emittente_sr_id, NULL, p_articolo_padre_contesto := v_articolo_id)`. Se esiste una riga in `vendite.listini_righe_componenti` per (listino_versione, padre, figlio, data), il resolver ritorna `origine = 'LISTINO_BUNDLE'`. Se il resolver fallisce (`SQLSTATE 'P0001'`) → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
   - **INSERT**: `attivo` = `v_comp.obbligatorio` — TRUE per i componenti obbligatori, FALSE per i componenti opzionali (attivabili dall'operatore nel drawer).
7. **INSERT componente** — inserisce in `preventivi_righe_componenti` con `prezzo_unitario` NOT NULL, `origine_prezzo`, `prezzo_resolver_context` JSONB.
8. **Check BoM vuota** — se `v_inserted = 0` dopo il loop (articolo composito senza componenti validi alla data) → raise `E_DOC_COMPOSITO_BOM_VUOTA` (442). Non scatta in caso di idempotenza (componenti già presenti — intercettata al passo 4).

## Pattern form atomic

Con il pattern form atomic, il BE:
1. Chiama `fn_preventivo_riga_componenti_preview` per mostrare all'operatore i prezzi suggeriti nel drawer.
2. Se alcuni componenti hanno `prezzo_suggerito = NULL` (listino mancante), l'operatore inserisce i prezzi manualmente.
3. Al save, il BE passa `p_componenti_overrides` con i prezzi forniti dall'operatore. La init non vede mai listini mancanti: o il resolver trova il prezzo, o c'è un override.

## `prezzo_resolver_context` JSONB

Struttura via resolver (successo):
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3,
    "listino_id": 7,
    "listino_versione_id": 12,
    "listino_riga_id": 45,
    "contratto_id": null,
    "origine": "LISTINO"
}
```

Struttura via override:
```jsonc
{
    "override": true,
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3
}
```

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.preventivi_righe` | tabella | sorgente articolo_id, uom, quantita, preventivo_id |
| `vendite.preventivi` | tabella | sorgente billing_account_id, utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | BoM per-componente |
| `vendite.fn_resolve_prezzo_listino_v2` | funzione | resolver per-componente (path senza override) |
| `vendite.preventivi_righe_componenti` | tabella | destinazione INSERT |

## Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_riga_id`/`p_emittente_sr_id` NULL/≤0; riga non trovata; override con prezzo = 0 su componente obbligatorio |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` (id 440) | Resolver fallisce per un componente e non c'è override corrispondente |
| `E_DOC_COMPOSITO_BOM_VUOTA` (442) | Articolo composito senza componenti attivi e validi alla data di riferimento |

## Note operative

- **`prezzo_unitario` sempre NOT NULL**: con il pattern form atomic, ogni INSERT ha prezzo valorizzato (resolver o override). Il check prezzo ≠ 0 è ora condizionale tramite trigger: obbligatori non possono avere prezzo = 0 (`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`), opzionali ammettono qualsiasi valore incluso 0.
- **Componenti opzionali** (`obbligatorio = FALSE`): vengono inseriti con `attivo = FALSE` — l'operatore può attivarli nel drawer.
- **`classe_utenza_id = NULL`**: passato al resolver come DEFAULT (fallback categoria base).
- **Trigger attivati**: INSERT in `preventivi_righe_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`. Quest'ultimo aggiorna `preventivi_righe.prezzo_unitario` come `COALESCE(SUM(figli.prezzo × coeff), 0)`.
- **Non STABLE**: esegue INSERT — VOLATILE per default.
