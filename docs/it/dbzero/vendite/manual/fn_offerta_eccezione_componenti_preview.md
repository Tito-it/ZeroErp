# fn_offerta_eccezione_componenti_preview

### Scopo

Preview read-only dei componenti BoM CASO A per il drawer eccezione offerta (pattern form atomic). Mirror di `fn_contratto_riga_componenti_preview` tipizzato per il dominio offerte. Proietta tutti i componenti con `esposto_in_fattura = TRUE` della distinta base dell'articolo, incluso il prezzo suggerito dal resolver. Consumata dal BE prima del save dell'eccezione composita. STABLE: nessun effetto collaterale.

> **Vedi anche**
>
> - [vendite.fn_contratto_riga_componenti_preview](/dbzero/vendite/funzioni/fn_contratto_riga_componenti_preview) — funzione analoga per contratti (riferimento per logica completa)
> - [vendite.fn_offerta_eccezione_componenti_init](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_init) — inizializzazione effettiva (con INSERT)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente

## Schema

`vendite`

## Firma

```sql
vendite.fn_offerta_eccezione_componenti_preview(
    p_articolo_id         catalogo.articoli.id%TYPE,
    p_uom_id              catalogo.unita_misura.id%TYPE,
    p_quantita_padre      vendite.offerte_commerciali_eccezioni.quantita%TYPE,
    p_data_riferimento    date,
    p_ba_id               anagrafiche.billing_account.id%TYPE,
    p_utility_id          vendite.offerte_commerciali.utility_id%TYPE,
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
    origine_prezzo         vendite.contratti_righe_componenti.origine_prezzo%TYPE,
    resolver_error_reason  text
)
```

## Differenze rispetto a `fn_contratto_riga_componenti_preview`

| Aspetto | `fn_contratto_riga_componenti_preview` | `fn_offerta_eccezione_componenti_preview` |
|---|---|---|
| `p_quantita_padre` tipo | `contratti_righe.quantita%TYPE` | `offerte_commerciali_eccezioni.quantita%TYPE` |
| `p_utility_id` tipo | `contratti.utility_id%TYPE` | `offerte_commerciali.utility_id%TYPE` |
| `origine_prezzo` tipo | da `contratti_righe_componenti` | da `contratti_righe_componenti` (stesso CHECK) |
| `obbligatorio` / `esposto_in_fattura` | proiettati | **non proiettati** — la preview offerta espone solo i componenti CASO A (già filtrati `esposto_in_fattura = TRUE`) |

## Logica, output e pattern form atomic

Identici a `fn_contratto_riga_componenti_preview` — vedi quella doc per la descrizione completa.

`prezzo_suggerito = NULL` + `resolver_error_reason` se il resolver fallisce per un componente. STABLE, nessun side-effect. Il resolver riceve `p_articolo_padre_contesto = p_articolo_id` per attivare lo STADIO BUNDLE. Se `p_articolo_id` non ha componenti con `esposto_in_fattura = TRUE` attivi → zero righe restituite.

L'`articolo_componente_id` restituito è il valore da usare come chiave in `p_componenti_overrides` di `fn_offerta_eccezione_componenti_init` (shape `{articolo_componente_id::text: prezzo}`).
