# fn_contratto_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga contratto composita: chiama `fn_resolve_prezzo_composito`, inserisce una riga in `contratti_righe_componenti` per ogni componente con `esposto_in_fattura = TRUE`. Idempotente, con no-op se `quantita IS NULL` (righe a consumo) e fallback resolver robusto.

> **Vedi anche**
>
> - [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — tabella popolata
> - [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito) — resolver chiamato internamente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_contratto_riga_componenti_init(
    p_riga_id          vendite.contratti_righe.id%TYPE,
    p_emittente_sr_id  anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento date,
    p_force_manuale    boolean DEFAULT FALSE
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga contratto padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma `COALESCE(contratti.valido_dal, contratti.data)`. |
| `p_force_manuale` | `boolean` | No (default `FALSE`) | Se `TRUE`, in caso di errore `P0001` dal resolver inserisce i componenti con `prezzo_unitario = NULL` e `origine_prezzo = 'MANUALE'` invece di sollevare `E_DOC_COMPONENTE_LISTINO_MANCANTE`. |

## Output

`integer`: numero di componenti inseriti in `contratti_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito, componenti già presenti, oppure `quantita IS NULL`. |
| `> 0` | Componenti inseriti con successo (resolver OK o fallback). |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id`.
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, contratto_id` da `contratti_righe`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0.
4. **No-op quantita NULL** — se `contratti_righe.quantita IS NULL` (riga a consumo senza quantita fissa), ritorna 0. Non è possibile calcolare `coeff_qta * NULL`.
5. **Idempotenza** — se esistono già righe in `contratti_righe_componenti`, ritorna 0.
6. **Lettura parametri contratto** — `billing_account_id`, `utility_id`, `istanza_utility_id` da `contratti`.
7. **Chiamata resolver** — `fn_resolve_prezzo_composito(..., utility_id::bigint, ...)` filtrata su `esposto_in_fattura = TRUE`.
8. **INSERT per ogni componente** — con `prezzo_unitario`, `origine_prezzo` e contesto JSONB (include `istanza_utility_id`).
9. **Gestione P0001** — se il resolver lancia `SQLSTATE 'P0001'`:
   - `p_force_manuale = FALSE` (default): annulla gli INSERT parziali via savepoint e rilancia `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
   - `p_force_manuale = TRUE`: annulla gli INSERT parziali via savepoint e reinserisce tutti i componenti con `prezzo_unitario = NULL`, `origine_prezzo = 'MANUALE'`. Il JSONB `prezzo_resolver_context` riporta `error = 'resolver_failed'`, `reason`, `force_manuale: true`.

## Differenze rispetto alle altre fn_init

| Aspetto | Preventivi | Ordini | DDT | Contratti |
|---|---|---|---|---|
| `utility_id` | da preventivi | da ordini (nullable) | da ddt (integer) | da contratti NOT NULL |
| `istanza_utility_id` | — | — | — | ✅ incluso nel context JSONB |
| No-op `quantita IS NULL` | — | — | — | ✅ (righe a consumo) |

## `prezzo_resolver_context` JSONB

Struttura in caso di successo resolver:
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7
}
```

Struttura in caso di fallback con `p_force_manuale = TRUE` (componenti inseriti con `prezzo_unitario = NULL`):
```jsonc
{
    "error": "resolver_failed",
    "reason": "<messaggio dell'eccezione P0001>",
    "force_manuale": true,
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3,
    "istanza_utility_id": 7
}
```

Con `p_force_manuale = FALSE` (default), il resolver P0001 viene rilanciato come `E_DOC_COMPONENTE_LISTINO_MANCANTE` e nessun componente viene inserito.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.contratti_righe` | tabella | sorgente articolo_id, uom, quantita, contratto_id |
| `vendite.contratti` | tabella | sorgente billing_account_id, utility_id, istanza_utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | lookup BoM |
| `vendite.fn_resolve_prezzo_composito` | funzione | resolver prezzi CASO A |
| `vendite.contratti_righe_componenti` | tabella | destinazione INSERT |

## Note operative

- **`p_data_riferimento`**: il BE deve passare `COALESCE(contratti.valido_dal, contratti.data)` come convenzione, allineata a `fn_list_contratti_da_pushare`.
- **Righe a consumo**: se `contratti_righe.quantita IS NULL` la funzione ritorna 0 silenziosamente. Il BE deve aggiornare la quantita prima di chiamare la init, oppure gestire il caso separatamente in UI.
- **`utility_id` come `integer`**: castato a `bigint` nella chiamata al resolver.
- **Non STABLE**: esegue INSERT — VOLATILE per default.
