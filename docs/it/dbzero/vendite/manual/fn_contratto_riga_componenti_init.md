# fn_contratto_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga contratto composita. Per ogni componente esposto della BoM: se presente un override in `p_componenti_overrides`, usa quel prezzo; altrimenti chiama `fn_resolve_prezzo_listino_v2` — se il resolver fallisce, solleva `E_DOC_COMPONENTE_LISTINO_MANCANTE`. Idempotente. No-op se `quantita IS NULL` (riga a consumo senza quantità fissa).

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
| `0` | No-op: articolo non composito, componenti già presenti, oppure `quantita IS NULL`. |
| `> 0` | Componenti inseriti con successo. |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id`.
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, contratto_id` da `contratti_righe`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **No-op quantita NULL** — se `contratti_righe.quantita IS NULL` (riga a consumo), ritorna 0. Non è possibile calcolare `coeff_qta × NULL`.
5. **Idempotenza** — se esistono già righe in `contratti_righe_componenti`, ritorna 0.
6. **Lettura parametri contratto** — `billing_account_id`, `utility_id`, `istanza_utility_id` da `contratti`.
7. **Loop per-componente** — per ogni componente della BoM esposta:
   - **Path override**: se `p_componenti_overrides ? componente_id::text` → prezzo = valore della mappa, `origine_prezzo = 'MANUALE'`. Prezzo = 0 → raise `E_PARAMETRO_INVALIDO`.
   - **Path resolver**: chiama `fn_resolve_prezzo_listino_v2`. Se fallisce → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
8. **INSERT componente** — `prezzo_unitario` NOT NULL, `origine_prezzo`, `prezzo_resolver_context` JSONB (include `istanza_utility_id`).

## Differenze rispetto alle altre fn_init

| Aspetto | Preventivi | Ordini | DDT | Contratti |
|---|---|---|---|---|
| `utility_id` | da preventivi NOT NULL | da ordini nullable | da ddt integer | da contratti NOT NULL |
| `istanza_utility_id` | — | — | — | incluso nel context JSONB |
| No-op `quantita IS NULL` | — | — | — | ✅ (righe a consumo) |

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
| `E_PARAMETRO_INVALIDO` | `p_riga_id`/`p_emittente_sr_id` NULL/≤0; riga non trovata; override con prezzo = 0 |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` (id 440) | Resolver fallisce per un componente senza override |

## Note operative

- **`p_data_riferimento`**: il BE deve passare `COALESCE(contratti.valido_dal, contratti.data)` come convenzione, allineata a `fn_list_contratti_da_pushare`.
- **Righe a consumo**: se `contratti_righe.quantita IS NULL` la funzione ritorna 0 silenziosamente. Il BE deve gestire il caso in UI prima di chiamare la init.
- **`prezzo_unitario` sempre NOT NULL**: con form atomic, ogni INSERT ha prezzo valorizzato.
- **Trigger attivati**: INSERT in `contratti_righe_componenti` attiva `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`.
- **Non STABLE**: VOLATILE per default.
