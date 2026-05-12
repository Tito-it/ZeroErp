# fn_ddt_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga DDT composita: chiama `fn_resolve_prezzo_composito`, inserisce una riga in `ddt_righe_componenti` per ogni componente con `esposto_in_fattura = TRUE`, con prezzo suggerito dal resolver e contesto di audit nel JSONB. Idempotente e con fallback resolver robusto.

> **Vedi anche**
>
> - [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti) — tabella popolata
> - [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito) — resolver chiamato internamente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_ddt_riga_componenti_init(
    p_riga_id          vendite.ddt_righe.id%TYPE,
    p_emittente_sr_id  anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento date,
    p_force_manuale    boolean DEFAULT FALSE
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga DDT padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver come `p_emittente_soggetto_ruolo_id`. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per il resolver e per la validazione BoM (`validita @> data`). Di norma uguale a `ddt.data`. |
| `p_force_manuale` | `boolean` | No (default `FALSE`) | Se `TRUE`, in caso di errore `P0001` dal resolver inserisce i componenti con `prezzo_unitario = NULL` e `origine_prezzo = 'MANUALE'` invece di sollevare `E_DOC_COMPONENTE_LISTINO_MANCANTE`. |

## Output

`integer`: numero di componenti inseriti in `ddt_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo (resolver OK o fallback). |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, ddt_id` da `ddt_righe`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0 silenziosamente.
4. **Idempotenza** — se esistono già righe in `ddt_righe_componenti` con `riga_ddt_id = p_riga_id`, ritorna 0 senza modifiche.
5. **Lettura parametri DDT** — `billing_account_id` e `utility_id` da `ddt`. `utility_id` è di tipo `integer` sulla testata DDT e viene castato a `bigint` nella chiamata al resolver.
6. **Chiamata resolver** — `fn_resolve_prezzo_composito(articolo_id, uom, data, ba, utility_id::bigint, emittente_sr, NULL)` filtrata su `esposto_in_fattura = TRUE`.
7. **INSERT per ogni componente** — per ogni riga restituita dal resolver: cerca `articolo_componente_id` dalla BoM, inserisce con `prezzo_unitario`, `origine_prezzo` e contesto resolver nel JSONB `prezzo_resolver_context`.
8. **Gestione P0001** — se il resolver lancia `SQLSTATE 'P0001'`:
   - `p_force_manuale = FALSE` (default): annulla gli INSERT parziali via savepoint e rilancia `E_DOC_COMPONENTE_LISTINO_MANCANTE`.
   - `p_force_manuale = TRUE`: annulla gli INSERT parziali via savepoint e reinserisce tutti i componenti con `prezzo_unitario = NULL`, `origine_prezzo = 'MANUALE'`. Il JSONB `prezzo_resolver_context` riporta `error = 'resolver_failed'`, `reason`, `force_manuale: true`.

## Differenze rispetto a `fn_preventivo_riga_componenti_init`

| Aspetto | Preventivi | DDT |
|---|---|---|
| Tabella sorgente | `vendite.preventivi_righe` | `vendite.ddt_righe` |
| Tabella testata | `vendite.preventivi` | `vendite.ddt` |
| `utility_id` | `bigint` da `preventivi.utility_id` | `integer` da `ddt.utility_id`, castato a `bigint` |
| Tabella destinazione | `preventivi_righe_componenti` | `ddt_righe_componenti` |

## `prezzo_resolver_context` JSONB

Struttura in caso di successo resolver:
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100,
    "utility_id": 3
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
    "utility_id": 3
}
```

Con `p_force_manuale = FALSE` (default), il resolver P0001 viene rilanciato come `E_DOC_COMPONENTE_LISTINO_MANCANTE` e nessun componente viene inserito.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.ddt_righe` | tabella | sorgente articolo_id, uom, quantita, ddt_id |
| `vendite.ddt` | tabella | sorgente billing_account_id, utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | lookup `articolo_componente_id` per ogni componente |
| `vendite.fn_resolve_prezzo_composito` | funzione | resolver prezzi componenti CASO A |
| `vendite.ddt_righe_componenti` | tabella | destinazione INSERT |

## Note operative

- **`utility_id` come `integer`**: `ddt.utility_id` è di tipo `integer` (non `bigint`). Il CAST a `bigint` avviene in modo implicito nel call al resolver; nessuna perdita di dati.
- **`uom_operativa_id` nullable**: se NULL sulla riga padre, usa `catalogo.articoli.uom_id` come fallback via `COALESCE` nel resolver call.
- **Trigger attivati**: l'INSERT in `ddt_righe_componenti` attiva i trigger `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`. Quest'ultimo aggiorna automaticamente `ddt_righe.prezzo_unitario` al termine. Se almeno un componente è inserito con `prezzo_unitario = NULL`, anche il padre risulterà NULL.
- **`p_force_manuale = TRUE`**: richiede azione `prezzo_override_manuale` sull'operatore (verificata dal service BE). Il DDT con componenti NULL non potrà transitare a `EMESSO` (check in `trgfn_ddt_guard_transizione_approvazione`).
- **Backward-compatibilità**: i caller esistenti senza 4° argomento ottengono `p_force_manuale = FALSE` per default — comportamento invariato.
- **Non STABLE**: esegue INSERT, quindi VOLATILE per default — corretto.
