# fn_offerta_eccezione_componenti_init

### Scopo

Inizializza i componenti BoM CASO A (`esposto_in_fattura = TRUE`) per un'eccezione offerta commerciale composita. Per ogni componente esposto nella distinta base dell'articolo: se presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto = v_articolo_id` per attivare il pricing bundle — se il resolver fallisce (P0001), inserisce il componente a prezzo=0/MANUALE (fallback individuale). Idempotente. No-op se `quantita IS NULL` (eccezione a consumo senza quantità fissa).

> **Vedi anche**
>
> - [vendite.offerte_commerciali_eccezioni_componenti](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni_componenti) — tabella popolata
> - [vendite.fn_offerta_eccezione_componenti_preview](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_preview) — preview read-only per il drawer (form atomic)
> - [vendite.fn_contratto_riga_componenti_init](/dbzero/vendite/funzioni/fn_contratto_riga_componenti_init) — funzione analoga per contratti (riferimento per logica comune)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_offerta_eccezione_componenti_init(
    p_eccezione_id          vendite.offerte_commerciali_eccezioni.id%TYPE,
    p_emittente_sr_id       anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE,
    p_data_riferimento      date,
    p_componenti_overrides  jsonb DEFAULT NULL
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_eccezione_id` | `bigint` | Sì, `> 0` | ID dell'eccezione offerta padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale. Passato al resolver. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma `COALESCE(offerta.validita_dal, CURRENT_DATE)`. |
| `p_componenti_overrides` | `jsonb` | No | Mappa `{"<articolo_componente_id>": <prezzo_numeric>}`. Chiave = `bom_entry_id::text` (PK di `catalogo.articoli_componenti`). |

## Output

`integer`: numero di componenti inseriti in `offerte_commerciali_eccezioni_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito, componenti già presenti, oppure `quantita IS NULL`. |
| `> 0` | Componenti inseriti. Può includere componenti con prezzo=0/MANUALE (fallback resolver). |

## Logica

1. **Guard input** — valida `p_eccezione_id` e `p_emittente_sr_id`.
2. **Lettura eccezione padre** — legge `articolo_id`, `uom_operativa_id`, `quantita`, `offerta_id` da `offerte_commerciali_eccezioni`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **No-op quantita NULL** — se `offerte_commerciali_eccezioni.quantita IS NULL` (eccezione a consumo), ritorna 0. Non è possibile calcolare `coeff_qta × NULL`.
5. **Idempotenza** — se esistono già righe in `offerte_commerciali_eccezioni_componenti`, ritorna 0.
6. **Lettura parametri offerta** — `billing_account_id`, `utility_id`, `istanza_utility_id` da `offerte_commerciali`.
7. **Loop per-componente** — itera su `catalogo.articoli_componenti` con filtro `esposto_in_fattura = TRUE`, `attivo = TRUE`, `validita @> p_data_riferimento`:
   - **Path override**: se `p_componenti_overrides ? bom_entry_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto := v_articolo_id`. Se esiste una riga in `listini_righe_componenti` per (listino_versione, padre, figlio, data), ritorna `origine = 'LISTINO_BUNDLE'`.
   - **Fallback individuale P0001**: se il resolver fallisce per un componente, inserisce prezzo=0, `origine_prezzo='MANUALE'`, `prezzo_resolver_context.error = 'resolver_not_found'`. Gli altri componenti non sono influenzati.
8. **INSERT componente** — nessun campo `attivo` (la tabella non lo ha). `prezzo_unitario` NOT NULL sempre.

## Differenze rispetto a `fn_contratto_riga_componenti_init`

| Aspetto | `fn_contratto_riga_componenti_init` | `fn_offerta_eccezione_componenti_init` |
|---|---|---|
| Input padre | `p_riga_id → contratti_righe` | `p_eccezione_id → offerte_commerciali_eccezioni` |
| Filtro BoM | tutti i componenti attivi (modello unificato) | solo `esposto_in_fattura = TRUE` |
| Override key | `componente_id::text` | **`articolo_componente_id::text`** (= `bom_entry_id`) |
| Fallback resolver | raise `E_DOC_COMPONENTE_LISTINO_MANCANTE` | **fallback individuale** prezzo=0/MANUALE |
| Campo `attivo` in INSERT | `v_comp.obbligatorio` | **assente** (la tabella non ha `attivo`) |
| Check BoM vuota | raise `E_DOC_COMPOSITO_BOM_VUOTA` | non presente (offerta può avere BoM vuota) |

## `prezzo_resolver_context` JSONB

Struttura via resolver (successo):
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-26",
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

Struttura via override:
```jsonc
{
    "override": true,
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-26",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7
}
```

Struttura fallback resolver (P0001):
```jsonc
{
    "error": "resolver_not_found",
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-26",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7
}
```

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.offerte_commerciali_eccezioni` | tabella | sorgente articolo_id, uom, quantita, offerta_id |
| `vendite.offerte_commerciali` | tabella | sorgente billing_account_id, utility_id, istanza_utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | BoM per-componente (filtro `esposto_in_fattura = TRUE`) |
| `vendite.fn_resolve_prezzo_listino_v2` | funzione | resolver per-componente |
| `vendite.offerte_commerciali_eccezioni_componenti` | tabella | destinazione INSERT |

## Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_eccezione_id`/`p_emittente_sr_id` NULL/≤0; eccezione non trovata |

## Note operative

- **`p_data_riferimento`**: il BE deve passare `COALESCE(offerta.validita_dal, CURRENT_DATE)`, allineato alla preview.
- **Eccezioni a consumo**: se `quantita IS NULL` la funzione ritorna 0 silenziosamente. Il BE deve gestire il caso in UI prima di chiamare la init.
- **`p_componenti_overrides` key**: usa `bom_entry_id::text` (PK di `articoli_componenti`), non `componente_id::text` come in `fn_contratto_riga_componenti_init`. La preview espone `articolo_componente_id` per costruire la mappa.
- **Fallback individuale vs globale**: a differenza del pattern contratti (che solleva errore bloccante), l'offerta usa un fallback per-componente a 0/MANUALE. Il venditore può correggere manualmente i prezzi nel drawer.
- **Trigger attivati**: INSERT in `offerte_commerciali_eccezioni_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`.
- **Non STABLE**: VOLATILE per default.
