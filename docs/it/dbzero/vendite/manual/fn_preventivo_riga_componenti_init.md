# fn_preventivo_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga preventivo composita: chiama `fn_resolve_prezzo_composito`, inserisce una riga in `preventivi_righe_componenti` per ogni componente con `esposto_in_fattura = TRUE`, con prezzo suggerito dal resolver e contesto di audit nel JSONB. Idempotente e con fallback resolver robusto.

> **Vedi anche**
>
> - [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — tabella popolata
> - [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito) — resolver chiamato internamente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_preventivo_riga_componenti_init(
    p_riga_id          vendite.preventivi_righe.id%TYPE,
    p_emittente_sr_id  anagrafiche.soggetti_ruoli.id%TYPE,
    p_data_riferimento date,
    p_force_manuale    boolean DEFAULT FALSE
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga preventivo padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver come `p_emittente_soggetto_ruolo_id`. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per il resolver e per la validazione BoM (`validita @> data`). Di norma uguale a `preventivi.data`. |
| `p_force_manuale` | `boolean` | No (default `FALSE`) | Se `TRUE`, in caso di errore `P0001` dal resolver inserisce i componenti con `prezzo_unitario = NULL` e `origine_prezzo = 'MANUALE'` invece di sollevare `E_DOC_COMPONENTE_LISTINO_MANCANTE`. Richiede azione `prezzo_override_manuale` sull'operatore. |

## Output

`integer`: numero di componenti inseriti in `preventivi_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo (resolver OK o fallback). |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, preventivo_id` da `preventivi_righe`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0 silenziosamente (non è un errore: il BE può chiamare la funzione su qualsiasi riga senza pre-filtro).
4. **Idempotenza** — se esistono già righe in `preventivi_righe_componenti` con `riga_preventivo_id = p_riga_id`, ritorna 0 senza modifiche.
5. **Lettura parametri preventivo** — `billing_account_id`, `utility_id` per il resolver.
6. **Chiamata resolver** — `fn_resolve_prezzo_composito(articolo_id, uom, data, ba, utility, emittente_sr, NULL)` filtrata su `esposto_in_fattura = TRUE`. `classe_utenza_id = NULL` (non disponibile direttamente dal preventivo).
7. **INSERT per ogni componente** — per ogni riga restituita dal resolver: cerca `articolo_componente_id` dalla BoM, inserisce con `prezzo_unitario`, `origine_prezzo` e contesto resolver nel JSONB `prezzo_resolver_context`.
8. **Gestione P0001** — se il resolver lancia `SQLSTATE 'P0001'` (listino non trovato su un componente), il comportamento dipende da `p_force_manuale`:
   - `FALSE` (default): gli INSERT parziali vengono annullati via savepoint e viene sollevato `E_DOC_COMPONENTE_LISTINO_MANCANTE` (HTTP 422). L'operatore deve configurare il listino prima di procedere.
   - `TRUE`: gli INSERT parziali vengono annullati via savepoint e tutti i componenti vengono reinseriti con `prezzo_unitario = NULL` e `origine_prezzo = 'MANUALE'`. Il JSONB `prezzo_resolver_context` riporta `error = 'resolver_failed'`, `reason`, `force_manuale: true`. L'operatore valorizza i prezzi manualmente in UI prima della finalizzazione del documento.

## Idempotenza e gestione fallback

La funzione è progettata per essere chiamata **esattamente una volta** per riga padre, subito dopo l'INSERT di `preventivi_righe`. Tuttavia:

- Se chiamata di nuovo su una riga già inizializzata → ritorna 0 senza modifiche (safe per retry).
- Se il resolver fallisce su un componente con `p_force_manuale = FALSE` → raise `E_DOC_COMPONENTE_LISTINO_MANCANTE`; nessun componente viene inserito.
- Se il resolver fallisce su un componente con `p_force_manuale = TRUE` → l'intera batch usa il fallback NULL/MANUALE (tutti i componenti, non solo quelli senza listino). Questo evita stati parziali dove alcuni componenti hanno prezzo e altri no.

## `prezzo_resolver_context` JSONB

Struttura in caso di successo resolver:
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-11",
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
    "data_riferimento": "2026-05-11",
    "ba_id": 100,
    "utility_id": 3
}
```

> Con `p_force_manuale = FALSE` (default), il resolver P0001 viene rilanciato come `E_DOC_COMPONENTE_LISTINO_MANCANTE` e nessun componente viene inserito — non si produce alcun JSONB di fallback.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.preventivi_righe` | tabella | sorgente articolo_id, uom, quantita, preventivo_id |
| `vendite.preventivi` | tabella | sorgente billing_account_id, utility_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | lookup `articolo_componente_id` per ogni componente |
| `vendite.fn_resolve_prezzo_composito` | funzione | resolver prezzi componenti CASO A |
| `vendite.preventivi_righe_componenti` | tabella | destinazione INSERT |

## Note operative

- **`classe_utenza_id = NULL`**: il preventivo non espone direttamente la classe utenza. Il resolver la gestisce con DEFAULT NULL (fallback a categoria base).
- **`uom_operativa_id` nullable**: se NULL sulla riga padre, usa `catalogo.articoli.uom_id` come fallback via `COALESCE` nel resolver call.
- **Trigger attivati**: l'INSERT in `preventivi_righe_componenti` attiva i trigger `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`. Quest'ultimo aggiorna automaticamente `preventivi_righe.prezzo_unitario` al termine. Se almeno un componente è inserito con `prezzo_unitario = NULL`, anche il padre risulterà NULL (vedasi `fn_ricalcola_prezzo_padre_da_componenti`).
- **`p_force_manuale = TRUE`**: attivabile solo se l'operatore ha l'azione `prezzo_override_manuale`. Il service BE deve verificare il permesso prima di passare `TRUE`. Il documento con componenti NULL non potrà transitare ad ACCETTATO finché non sono tutti valorizzati (check in `trgfn_preventivi_guard_transizione_approvazione`).
- **Backward-compatibilità**: i caller esistenti senza 4° argomento ottengono `p_force_manuale = FALSE` per default — comportamento invariato.
- **Non STABLE**: esegue INSERT, quindi VOLATILE per default — corretto.
