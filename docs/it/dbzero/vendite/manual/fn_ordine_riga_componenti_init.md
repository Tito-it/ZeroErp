# fn_ordine_riga_componenti_init

### Scopo

Inizializza i componenti BoM CASO A per una riga ordine composita: chiama `fn_resolve_prezzo_composito`, inserisce una riga in `ordini_righe_componenti` per ogni componente con `esposto_in_fattura = TRUE`, con prezzo suggerito dal resolver e contesto di audit nel JSONB. Idempotente e con fallback resolver robusto.

> **Vedi anche**
>
> - [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti) — tabella popolata
> - [vendite.fn_resolve_prezzo_composito](/dbzero/vendite/funzioni/fn_resolve_prezzo_composito) — resolver chiamato internamente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente
> - [Gestione Listini v5 §5.2](/guide/gestione-listini) — definizione CASO A

## Schema

`vendite`

## Firma

```sql
vendite.fn_ordine_riga_componenti_init(
    p_riga_id          vendite.ordini_righe.id%TYPE,
    p_emittente_sr_id  anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE,
    p_data_riferimento vendite.ordini.data%TYPE
) RETURNS integer
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_riga_id` | `bigint` | Sì, `> 0` | ID della riga ordine padre. Guard raise `E_PARAMETRO_INVALIDO` se NULL o ≤ 0. |
| `p_emittente_sr_id` | `bigint` | Sì, `> 0` | `soggetto_ruolo_id` dell'emittente fiscale — passato al resolver come `p_emittente_soggetto_ruolo_id`. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per il resolver e per la validazione BoM (`validita @> data`). Di norma uguale a `ordini.data`. |

## Output

`integer`: numero di componenti inseriti in `ordini_righe_componenti`.

| Valore | Significato |
|---|---|
| `0` | No-op: articolo non composito (CASO B), oppure componenti già presenti (idempotenza). |
| `> 0` | Componenti inseriti con successo (resolver OK o fallback). |

## Logica

1. **Guard input** — valida `p_riga_id` e `p_emittente_sr_id` (non NULL, > 0).
2. **Lettura riga padre** — `SELECT articolo_id, uom_operativa_id, quantita, ordine_id` da `ordini_righe`. NOT FOUND → raise `E_PARAMETRO_INVALIDO`.
3. **No-op CASO B** — se `articoli.is_composito = FALSE`, ritorna 0 silenziosamente.
4. **Idempotenza** — se esistono già righe in `ordini_righe_componenti` con `riga_ordine_id = p_riga_id`, ritorna 0 senza modifiche.
5. **Lettura parametri ordine** — `billing_account_id` da `ordini`. `utility_id` non è presente su `ordini`: viene passato `NULL` al resolver.
6. **Chiamata resolver** — `fn_resolve_prezzo_composito(articolo_id, uom, data, ba, NULL, emittente_sr, NULL)` filtrata su `esposto_in_fattura = TRUE`.
7. **INSERT per ogni componente** — per ogni riga restituita dal resolver: cerca `articolo_componente_id` dalla BoM, inserisce con `prezzo_unitario`, `origine_prezzo` e contesto resolver nel JSONB `prezzo_resolver_context`.
8. **Fallback P0001** — se il resolver lancia `SQLSTATE 'P0001'`, gli INSERT parziali vengono annullati via savepoint e tutti i componenti vengono reinseriti con `prezzo_unitario = 0` e `origine_prezzo = 'MANUALE'`.

## Differenze rispetto a `fn_preventivo_riga_componenti_init`

| Aspetto | Preventivi | Ordini |
|---|---|---|
| Tabella sorgente | `vendite.preventivi_righe` | `vendite.ordini_righe` |
| Tabella testata | `vendite.preventivi` | `vendite.ordini` |
| `utility_id` | `integer NOT NULL` da `preventivi.utility_id` | `integer` nullable da `ordini.utility_id` (aggiunto in 20260511-29) |
| Tabella destinazione | `preventivi_righe_componenti` | `ordini_righe_componenti` |

## `prezzo_resolver_context` JSONB

Struttura in caso di successo resolver:
```jsonc
{
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100
}
```

Struttura in caso di fallback:
```jsonc
{
    "error": "resolver_failed",
    "emittente_sr_id": 42,
    "data_riferimento": "2026-05-12",
    "ba_id": 100
}
```

Note: `utility_id` è assente dal JSONB perché non disponibile sulla testata ordine.

## Dipendenze

| Oggetto | Tipo | Ruolo |
|---|---|---|
| `vendite.ordini_righe` | tabella | sorgente articolo_id, uom, quantita, ordine_id |
| `vendite.ordini` | tabella | sorgente billing_account_id |
| `catalogo.articoli` | tabella | check `is_composito` |
| `catalogo.articoli_componenti` | tabella | lookup `articolo_componente_id` per ogni componente |
| `vendite.fn_resolve_prezzo_composito` | funzione | resolver prezzi componenti CASO A |
| `vendite.ordini_righe_componenti` | tabella | destinazione INSERT |

## Note operative

- **`utility_id = NULL`**: il resolver riceve NULL per `p_classe_utenza_id` e per `p_utility_id`. Questo può limitare la copertura delle regole di pricing basate su utility. Se nel tempo la testata ordine acquisisce `utility_id`, la funzione andrà aggiornata.
- **`uom_operativa_id` nullable**: se NULL sulla riga padre, usa `catalogo.articoli.uom_id` come fallback via `COALESCE` nel resolver call.
- **Trigger attivati**: l'INSERT in `ordini_righe_componenti` attiva i trigger `_a10_guard_bom_coerenza`, `_m50_calcola_quantita`, audit, tx_id e `_z90_ricalcola_padre`. Quest'ultimo aggiorna automaticamente `ordini_righe.prezzo_unitario` al termine.
- **Non STABLE**: esegue INSERT, quindi VOLATILE per default — corretto.
