# fn_ordine_riga_componenti_preview

### Scopo

Preview read-only dei componenti BoM per il drawer riga ordine (pattern form atomic). Stesso comportamento di `fn_preventivo_riga_componenti_preview` ma tipizzato per la testata `ordini`. Proietta tutti i componenti attivi della BoM (modello unificato), inclusi `obbligatorio` ed `esposizione_in_fattura` (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`; fino al 2026-10-01 era il booleano `esposto_in_fattura`, rev `20261001-49`). Consumata dal BE prima del save della riga composita.

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
    resolver_error_reason  text,
    obbligatorio           boolean,
    esposizione_in_fattura catalogo.articoli_componenti.esposizione_in_fattura%TYPE
)
```

## Differenze rispetto a `fn_preventivo_riga_componenti_preview`

| Aspetto | Preventivi | Ordini |
|---|---|---|
| `p_quantita_padre` tipo | `preventivi_righe.quantita%TYPE` | `ordini_righe.quantita%TYPE` |
| `p_utility_id` tipo | `preventivi.utility_id%TYPE` | `ordini.utility_id%TYPE` (nullable) |
| `origine_prezzo` tipo | da `preventivi_righe_componenti` | da `ordini_righe_componenti` |
| `obbligatorio` | proiettato (modello unificato) | identico |
| `esposizione_in_fattura` | proiettata (solo informativa) | identico |

## Logica, output e pattern form atomic

Identici a `fn_preventivo_riga_componenti_preview` — vedi quella doc per la descrizione completa.

`prezzo_suggerito = NULL` + `resolver_error_reason` se il resolver fallisce per un componente. STABLE, nessun side-effect. Il resolver riceve `p_articolo_padre_contesto = p_articolo_id` per attivare lo STADIO BUNDLE. Se `p_articolo_id` non ha componenti attivi → zero righe restituite.
