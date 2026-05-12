# fn_ordine_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga ordine composita. Per ogni componente esposto della BoM: se presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` — se il resolver fallisce, solleva `E_DOC_COMPONENTE_LISTINO_MANCANTE`. Idempotente.

> **Vedi anche**
>
> - [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti) — tabella popolata
> - [vendite.fn_ordine_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_preview) — preview read-only per il drawer (form atomic)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_ordine_riga_componenti_init(
    p_riga_id                vendite.ordini_righe.id%TYPE,
    p_emittente_sr_id        anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento       date,
    p_componenti_overrides   jsonb DEFAULT NULL
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga ordine padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma uguale a `ordini.data`. |
| `p_componenti_overrides` | `jsonb` | No | Mappa `{"<componente_id>": <prezzo_numeric>}`. Override con prezzo `= 0` → raise `E_PARAMETRO_INVALIDO`. |

## Output

`integer`: numero di componenti inseriti in `ordini_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo. |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, ordine_id` da `ordini_righe`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **Idempotenza** — se esistono già righe in `ordini_righe_componenti`, ritorna 0.
5. **Lettura parametri ordine** — `billing_account_id`, `utility_id` da `ordini`. `utility_id` è di tipo `integer` (nullable su `ordini`).
6. **Loop per-componente** — per ogni componente della BoM esposta:
   - **Path override**: se `p_componenti_overrides ? componente_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`. Prezzo = 0 → raise `E_PARAMETRO_INVALIDO`.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2`. Se fallisce → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
7. **INSERT componente** — `prezzo_unitario` NOT NULL, `origine_prezzo`, `prezzo_resolver_context` JSONB.

## Differenze rispetto a `fn_preventivo_riga_componenti_init`

| Aspetto | Preventivi | Ordini |
|---|---|---|
| Tabella sorgente | `vendite.preventivi_righe` | `vendite.ordini_righe` |
| Tabella testata | `vendite.preventivi` | `vendite.ordini` |
| `utility_id` | `integer NOT NULL` da `preventivi.utility_id` | `integer` nullable da `ordini.utility_id` |
| Tabella destinazione | `preventivi_righe_componenti` | `ordini_righe_componenti` |

## `prezzo_resolver_context` JSONB

Struttura via resolver (successo):
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
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
    "ba_id": 100
}
```

Note: `utility_id` è assente dal JSONB override quando NULL sulla testata ordine.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.ordini_righe` | tabella | sorgente articolo_id, uom, quantita, ordine_id |
| `vendite.ordini` | tabella | sorgente billing_account_id, utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | BoM per-componente |
| `vendite.fn_resolve_prezzo_listino_v2` | funzione | resolver per-componente |
| `vendite.ordini_righe_componenti` | tabella | destinazione INSERT |

## Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_riga_id`/`p_emittente_sr_id` NULL/≤0; riga non trovata; override con prezzo = 0 |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` (id 440) | Resolver fallisce per un componente senza override |

## Note operative

- **`utility_id` nullable**: se NULL (ordine senza utility), il resolver riceve NULL per `p_utility_id`. Può limitare copertura regole pricing basate su utility.
- **`prezzo_unitario` sempre NOT NULL**: con form atomic, ogni INSERT ha prezzo valorizzato.
- **Trigger attivati**: INSERT in `ordini_righe_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`.
- **Non STABLE**: VOLATILE per default.
