# fn_ddt_riga_componenti_preview

> ## ⚠️ Rev 2026-08-19 — stesso risultato, senza sporcare il diario
>
> La preview chiama ora il **nucleo**
> [fn_resolve_prezzo_listino_v2_esito](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito)
> e ha perso il `BEGIN … EXCEPTION` che catturava l'errore del resolver.
>
> **Per il drawer non cambia niente**: prezzo suggerito `NULL` e motivazione in
> `resolver_error_reason`, esattamente come prima.
>
> ⛔ **Cambia il costo nascosto.** `script.fn_log_error_only` scrive su
> `dbops.error_log` via una connessione dblink **separata, fuori transazione**:
> il database la riga la scriveva **prima** di sollevare. Catturare l'eccezione
> nascondeva l'errore al chiamante e lasciava il log intatto — una riga per ogni
> componente non risolto, **a ogni apertura del drawer**. Ora zero.
>
> ⚠️ Il messaggio mostrato viene composto con `format()` sui valori dell'esito,
> con il ripiego che ha `fn_log_and_raise_error`: se la sostituzione dei
> segnaposto fallisce resta il modello — brutto da leggere, ma una preview non
> deve rompersi per colpa di un messaggio.

### Scopo

Preview read-only dei componenti BoM per il drawer riga DDT (pattern form atomic). Stesso comportamento di `fn_preventivo_riga_componenti_preview` ma tipizzato per la testata `ddt`. Proietta tutti i componenti attivi della BoM (modello unificato), inclusi `obbligatorio` ed `esposizione_in_fattura` (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`; fino al 2026-10-01 era il booleano `esposto_in_fattura`, rev `20261001-50`). Consumata dal BE prima del save della riga composita.

> **Vedi anche**
>
> - [vendite.fn_preventivo_riga_componenti_preview](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_preview) — funzione analoga per preventivi (riferimento per logica completa)
> - [vendite.fn_ddt_riga_componenti_init](/dbzero/vendite/funzioni/fn_ddt_riga_componenti_init) — inizializzazione effettiva (con INSERT)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver per-componente

## Schema

`vendite`

## Firma

```sql
vendite.fn_ddt_riga_componenti_preview(
    p_articolo_id         catalogo.articoli.id%TYPE,
    p_uom_id              catalogo.unita_misura.id%TYPE,
    p_quantita_padre      vendite.ddt_righe.quantita%TYPE,
    p_data_riferimento    date,
    p_ba_id               anagrafiche.billing_account.id%TYPE,
    p_utility_id          vendite.ddt.utility_id%TYPE,
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
    origine_prezzo         vendite.ddt_righe_componenti.origine_prezzo%TYPE,
    resolver_error_reason  text,
    obbligatorio           boolean,
    esposizione_in_fattura catalogo.articoli_componenti.esposizione_in_fattura%TYPE
)
```

## Differenze rispetto a `fn_preventivo_riga_componenti_preview`

| Aspetto | Preventivi | DDT |
|---|---|---|
| `p_quantita_padre` tipo | `preventivi_righe.quantita%TYPE` | `ddt_righe.quantita%TYPE` |
| `p_utility_id` tipo | `preventivi.utility_id%TYPE` | `ddt.utility_id%TYPE` (integer) |
| `origine_prezzo` tipo | da `preventivi_righe_componenti` | da `ddt_righe_componenti` |
| `obbligatorio` | proiettato (modello unificato) | identico |
| `esposizione_in_fattura` | proiettata (solo informativa) | identico |

## Logica, output e pattern form atomic

Identici a `fn_preventivo_riga_componenti_preview` — vedi quella doc per la descrizione completa.

`prezzo_suggerito = NULL` + `resolver_error_reason` se il resolver fallisce per un componente. STABLE, nessun side-effect. Il resolver riceve `p_articolo_padre_contesto = p_articolo_id` per attivare lo STADIO BUNDLE. Se `p_articolo_id` non ha componenti attivi → zero righe restituite.
