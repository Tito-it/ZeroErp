# fn_preventivo_riga_componenti_preview

### Scopo

Preview read-only dei componenti BoM per il drawer riga preventivo (pattern form atomic). Per ogni componente attivo della BoM tenta `fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto = p_articolo_id` per attivare il pricing bundle; se il resolver fallisce, restituisce `prezzo_suggerito = NULL` e la motivazione in `resolver_error_reason`. Proietta anche `obbligatorio` ed `esposizione_in_fattura` per ogni componente. Nessun side-effect (STABLE).

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
    resolver_error_reason  text,
    obbligatorio           boolean,
    esposizione_in_fattura catalogo.articoli_componenti.esposizione_in_fattura%TYPE
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
| `origine_prezzo` | Origine del prezzo (es. `LISTINO`, `LISTINO_BUNDLE`, `CONTRATTO`) — `NULL` se resolver fail. |
| `resolver_error_reason` | Messaggio di errore del resolver se `prezzo_suggerito = NULL`, altrimenti `NULL`. |
| `obbligatorio` | TRUE se il componente BoM è obbligatorio (non disattivabile dall'operatore). |
| `esposizione_in_fattura` | Come il componente si vede in fattura sotto il suo kit: `NASCOSTO` (non compare), `DESCRITTIVO` (riga senza prezzo né importo), `VALORIZZATO` (riga con prezzo e importo suoi, fuori dal totale del kit). Solo informativa: non è un gate di pricing. Fino al 2026-10-01 era il booleano `esposto_in_fattura` (`false` → `NASCOSTO`, `true` → `DESCRITTIVO`), rev `20261001-48`. |

## Logica

1. Legge la distinta di `p_articolo_id` a `p_data_riferimento` da `catalogo.fn_distinta_alla_data` (legami attivi e in vigore quel giorno) — tutti i componenti attivi, senza filtro sull'esposizione in fattura.
2. Per ogni componente, tenta `fn_resolve_prezzo_listino_v2(componente_id, uom, data, ba, utility_id, emittente_sr, classe_utenza_id, p_articolo_padre_contesto := p_articolo_id)`. Se esiste una riga in `vendite.listini_righe_componenti` per (listino_versione, padre, figlio, data), il resolver ritorna `origine_prezzo = 'LISTINO_BUNDLE'`.
3. Se il resolver riesce → `prezzo_suggerito = prezzo_finale`, `origine_prezzo` da resolver, `resolver_error_reason = NULL`.
4. Se il resolver fallisce (`SQLSTATE 'P0001'`) → `prezzo_suggerito = NULL`, `origine_prezzo = NULL`, `resolver_error_reason = MESSAGE_TEXT`.
5. `RETURN NEXT` per ogni componente, includendo `obbligatorio` ed `esposizione_in_fattura` dalla BoM sorgente.

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
- Se `p_articolo_id` non ha componenti attivi → zero righe restituite (il BE può gestire come articolo non composito).
- Il risultato della preview non è persistito: serve solo per pre-popolare il drawer. La fonte di verità è il risultato di `fn_preventivo_riga_componenti_init`.
- `obbligatorio = FALSE` indica un componente opzionale: il FE può mostrarlo come disattivato di default ma attivabile dall'operatore.
- `esposizione_in_fattura` è proiettata a solo scopo informativo (il FE la mostra per esteso) — nel modello unificato l'esposizione non è il gate per il processing: le regole le applica la vista di rappresentazione della fattura, `vendite.vw_fattura_righe_esposte`.
