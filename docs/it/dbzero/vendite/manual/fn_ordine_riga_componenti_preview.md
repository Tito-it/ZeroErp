# fn_ordine_riga_componenti_preview

### Scopo

Preview read-only dei componenti BoM CASO A per il drawer riga ordine (pattern form atomic). Stesso comportamento di `fn_preventivo_riga_componenti_preview` ma tipizzato per la testata `ordini`. Consumata dal BE prima del save della riga composita.

> **Vedi anche**
>
> - [vendite.fn_preventivo_riga_componenti_preview](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview) — funzione analoga per preventivi (riferimento per logica completa)
> - [vendite.fn_ordine_riga_componenti_init](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_init) — inizializzazione effettiva (con INSERT)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente

## Schema

`vendite`

## Firma

```sql
vendite.fn_ordine_riga_componenti_preview(
    p_articolo_id         catalogo.articoli.id%TYPE,
    p_uom_id              catalogo.unita_misura.id%TYPE,
    p_quantita_padre      vendite.ordini_righe.quantita%TYPE,
    p_data_riferimento    date,
    p_ba_id               anagrafiche.billing_account.id%TYPE,
    p_utility_id          vendite.ordini.utility_id%TYPE,
    p_emittente_sr_id     anagrafiche.soggetti_ruoli.id%TYPE,
    p_classe_utenza_id    config.classi_utenze.id%TYPE DEFAULT NULL
) RETURNS TABLE (
    articolo_componente_id catalogo.articoli_componenti.id%TYPE,
    componente_id          catalogo.articoli.id%TYPE,
    componente_codice      catalogo.articoli.codice%TYPE,
    componente_descrizione catalogo.articoli.descrizione%TYPE,
    coeff_qta_snapshot     catalogo.articoli_componenti.coeff_qta%TYPE,
    quantita_componente    catalogo.articoli_componenti.coeff_qta%TYPE,
    uom_id                 catalogo.articoli.uom_id%TYPE,
    uom_codice             catalogo.unita_misura.codice%TYPE,
    iva_id                 catalogo.articoli.iva_id%TYPE,
    prezzo_suggerito       vendite.listini_righe.prezzo%TYPE,
    origine_prezzo         vendite.ordini_righe_componenti.origine_prezzo%TYPE,
    resolver_error_reason  text
)
```

## Differenze rispetto a `fn_preventivo_riga_componenti_preview`

| Aspetto | Preventivi | Ordini |
|---|---|---|
| `p_quantita_padre` tipo | `preventivi_righe.quantita%TYPE` | `ordini_righe.quantita%TYPE` |
| `p_utility_id` tipo | `preventivi.utility_id%TYPE` | `ordini.utility_id%TYPE` (nullable) |
| `origine_prezzo` tipo | da `preventivi_righe_componenti` | da `ordini_righe_componenti` |

## Logica, output e pattern form atomic

Identici a `fn_preventivo_riga_componenti_preview` — vedi quella doc per la descrizione completa.

`prezzo_suggerito = NULL` + `resolver_error_reason` se il resolver fallisce per un componente. STABLE, nessun side-effect.
