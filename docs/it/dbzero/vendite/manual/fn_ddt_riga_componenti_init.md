# fn_ddt_riga_componenti_init

### Scopo

Inizializza i componenti BoM (modello unificato) per una riga DDT composita. Per ogni componente attivo della BoM: se presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto = v_articolo_id` per attivare il pricing bundle — se il resolver fallisce, solleva `E_DOC_COMPONENTE_LISTINO_MANCANTE`. Idempotente.

> **Vedi anche**
>
> - [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti) — tabella popolata
> - [vendite.fn_ddt_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_preview) — preview read-only per il drawer (form atomic)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_ddt_riga_componenti_init(
    p_riga_id                vendite.ddt_righe.id%TYPE,
    p_emittente_sr_id        anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento       date,
    p_componenti_overrides   jsonb DEFAULT NULL
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga DDT padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma uguale a `ddt.data`. |
| `p_componenti_overrides` | `jsonb` | No | Mappa `{"<componente_id>": <prezzo_numeric>}`. Override con prezzo `= 0` → raise `E_PARAMETRO_INVALIDO`. |

## Output

`integer`: numero di componenti inseriti in `ddt_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo. |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — un'unica query JOIN tra `ddt_righe` e `catalogo.articoli` recupera in un solo round-trip: `articolo_id`, `codice`, `uom_operativa_id`, `quantita`, `ddt_id` e `is_composito`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **Idempotenza** — se esistono già righe in `ddt_righe_componenti`, ritorna 0.
5. **Lettura parametri DDT** — `billing_account_id`, `utility_id` da `ddt`. `utility_id` è di tipo `integer`.
6. **Loop per-componente** — per ogni componente attivo della BoM (`attivo = TRUE`, `validita @> p_data_riferimento`), senza filtro su `esposto_in_fattura`:
   - **Path override**: se `p_componenti_overrides ? componente_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`. Prezzo = 0 → raise `E_PARAMETRO_INVALIDO` **solo** se `v_comp.obbligatorio = TRUE`; per i componenti opzionali, prezzo = 0 è ammesso.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto := v_articolo_id`. Se esiste una riga in `vendite.listini_righe_componenti` per (listino_versione, padre, figlio, data), il resolver ritorna `origine = 'LISTINO_BUNDLE'`. Se fallisce → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
   - **INSERT**: `attivo` = `v_comp.obbligatorio` — TRUE per i componenti obbligatori, FALSE per i componenti opzionali.
7. **INSERT componente** — `prezzo_unitario` NOT NULL, `origine_prezzo`, `prezzo_resolver_context` JSONB.
8. **Check BoM vuota** — se `v_inserted = 0` dopo il loop → raise `E_DOC_COMPOSITO_BOM_VUOTA` (442). Non scatta in caso di idempotenza (intercettata al passo 4).

## Differenze rispetto a `fn_preventivo_riga_componenti_init`

| Aspetto | Preventivi | DDT |
|---|---|---|
| Tabella sorgente | `vendite.preventivi_righe` | `vendite.ddt_righe` |
| Tabella testata | `vendite.preventivi` | `vendite.ddt` |
| `utility_id` | `integer NOT NULL` da `preventivi.utility_id` | `integer` da `ddt.utility_id`, castato a `int` nel resolver |
| Tabella destinazione | `preventivi_righe_componenti` | `ddt_righe_componenti` |
| Loop BoM | tutti i componenti attivi (modello unificato) | identico |
| `attivo` INSERT | `v_comp.obbligatorio` | identico |

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
| `vendite.ddt_righe` | tabella | sorgente articolo_id, uom, quantita, ddt_id |
| `vendite.ddt` | tabella | sorgente billing_account_id, utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | BoM per-componente |
| `vendite.fn_resolve_prezzo_listino_v2` | funzione | resolver per-componente |
| `vendite.ddt_righe_componenti` | tabella | destinazione INSERT |

## Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `p_riga_id`/`p_emittente_sr_id` NULL/≤0; riga non trovata; override con prezzo = 0 su componente obbligatorio |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` (id 440) | Resolver fallisce per un componente senza override |
| `E_DOC_COMPOSITO_BOM_VUOTA` (442) | Articolo composito senza componenti attivi e validi alla data di riferimento |

## Note operative

- **`utility_id` come `integer`**: `ddt.utility_id` è di tipo `integer`. Il CAST è implicito nella chiamata al resolver; nessuna perdita di dati.
- **`prezzo_unitario` sempre NOT NULL**: con form atomic, ogni INSERT ha prezzo valorizzato. Il check prezzo ≠ 0 è condizionale: obbligatori non possono avere prezzo = 0 (`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO`), opzionali ammettono qualsiasi valore incluso 0.
- **Componenti opzionali** (`obbligatorio = FALSE`): vengono inseriti con `attivo = FALSE` — l'operatore può attivarli nel drawer.
- **Trigger attivati**: INSERT in `ddt_righe_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`.
- **Non STABLE**: VOLATILE per default.
