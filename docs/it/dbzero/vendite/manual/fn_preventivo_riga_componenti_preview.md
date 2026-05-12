# fn_preventivo_riga_componenti_preview

### Scopo

Preview read-only dei componenti BoM CASO A per il drawer riga preventivo (pattern form atomic). Per ogni componente esposto della BoM tenta `fn_resolve_prezzo_listino_v2`; se il resolver fallisce, restituisce `prezzo_suggerito = NULL` e la motivazione in `resolver_error_reason`. Nessun side-effect (STABLE).

Consumata dal backend per l'endpoint `POST /vendite/preventivi/{id}/righe/preview-componenti/` prima del save della riga composita.

> **Vedi anche**
>
> - [vendite.fn_preventivo_riga_componenti_init](/dbzero/vendite/funzioni/fn_preventivo_riga_componenti_init) — inizializzazione effettiva (con INSERT)
> - [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver chiamato per ogni componente
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM sorgente

## Schema

`vendite`

## Firma

```sql
vendite.fn_preventivo_riga_componenti_preview(
    p_articolo_id         catalogo.articoli.id%TYPE,
    p_uom_id              catalogo.unita_misura.id%TYPE,
    p_quantita_padre      vendite.preventivi_righe.quantita%TYPE,
    p_data_riferimento    date,
    p_ba_id               anagrafiche.billing_account.id%TYPE,
    p_utility_id          vendite.preventivi.utility_id%TYPE,
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
    origine_prezzo         vendite.preventivi_righe_componenti.origine_prezzo%TYPE,
    resolver_error_reason  text
)
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_articolo_id` | `bigint` | Sì | ID articolo composito della riga preventivo (non ancora inserita). |
| `p_uom_id` | `bigint` | Sì | UoM operativa della riga padre. |
| `p_quantita_padre` | `numeric` | Sì | Quantità della riga padre — per calcolare `quantita_componente = coeff_qta × quantita_padre`. |
| `p_data_riferimento` | `date` | Sì | Data di riferimento per resolver e validazione BoM. Di norma uguale a `preventivi.data`. |
| `p_ba_id` | `bigint` | Sì | `billing_account_id` del preventivo. |
| `p_utility_id` | `integer` | Sì | `utility_id` del preventivo. |
| `p_emittente_sr_id` | `bigint` | Sì | `soggetto_ruolo_id` dell'emittente fiscale. |
| `p_classe_utenza_id` | `bigint` | No | Classe utenza per il resolver (DEFAULT NULL → fallback categoria base). |

## Output — colonne RETURNS TABLE

| Colonna | Descrizione |
|---|---|
| `articolo_componente_id` | PK della voce BoM in `catalogo.articoli_componenti`. |
| `componente_id` | ID articolo componente. |
| `componente_codice` | Codice articolo componente. |
| `componente_descrizione` | Descrizione articolo componente. |
| `coeff_qta_snapshot` | Coefficiente quantità della BoM. |
| `quantita_componente` | `coeff_qta × p_quantita_padre`. |
| `uom_id` | UoM del componente (`catalogo.articoli.uom_id`). |
| `uom_codice` | Codice leggibile UoM componente. |
| `iva_id` | Aliquota IVA del componente. |
| `prezzo_suggerito` | Prezzo da listino se trovato, `NULL` se il resolver fallisce. |
| `origine_prezzo` | Origine del prezzo (es. `LISTINO`, `CONTRATTO`) — `NULL` se resolver fail. |
| `resolver_error_reason` | Messaggio di errore del resolver se `prezzo_suggerito = NULL`, altrimenti `NULL`. |

## Logica

1. Interroga la BoM esposta (`esposto_in_fattura = TRUE`, `attivo = TRUE`, `validita @> p_data_riferimento`) per `p_articolo_id`.
2. Per ogni componente, tenta `fn_resolve_prezzo_listino_v2(componente_id, uom, data, ba, utility_id, emittente_sr, classe_utenza_id)`.
3. Se il resolver riesce → `prezzo_suggerito = prezzo_finale`, `origine_prezzo` da resolver, `resolver_error_reason = NULL`.
4. Se il resolver fallisce (`SQLSTATE 'P0001'`) → `prezzo_suggerito = NULL`, `origine_prezzo = NULL`, `resolver_error_reason = MESSAGE_TEXT`.
5. `RETURN NEXT` per ogni componente.

## Pattern form atomic

```
BE riceve POST /righe (riga composita)
  ↓
Chiama fn_preventivo_riga_componenti_preview(articolo_id, ...)
  ↓
FE mostra drawer con tabella componenti:
  - prezzo_suggerito valorizzato → campo pre-popolato (editabile)
  - prezzo_suggerito NULL       → campo vuoto + resolver_error_reason come hint
  ↓
Operatore conferma/modifica prezzi → save
  ↓
BE chiama fn_preventivo_riga_componenti_init(riga_id, ..., p_componenti_overrides={...})
```

## Note operative

- **STABLE**: nessun side-effect. Può essere chiamata più volte senza problemi (es. refresh drawer).
- Se `p_articolo_id` non ha componenti esposti → zero righe restituite (il BE può gestire come articolo non composito).
- Il risultato della preview non è persistito: serve solo per pre-popolare il drawer. La fonte di verità è il risultato di `fn_preventivo_riga_componenti_init`.
