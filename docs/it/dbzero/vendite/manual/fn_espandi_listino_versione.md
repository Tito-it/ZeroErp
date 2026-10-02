# fn_espandi_listino_versione

### Scopo

Core **condiviso** di espansione listino: data una versione di listino e la variazione globale, ritorna le righe piatte (standalone + bundle compositi) con prezzo da-listino e composizione BoM in JSONB. Contiene **solo** la logica listino + variazione + BoM, **nessuna eccezione di dominio** (overlay OVERRIDE/ESCLUSIONE/AGGIUNTA resta nelle funzioni di dominio).

È il building block che elimina la duplicazione (regola del 2) tra [vendite.fn_contratto_righe_preview](/dbzero/vendite/manual/fn_contratto_righe_preview) (drawer contratti) e [vendite.fn_offerta_righe_espanse](/dbzero/vendite/manual/fn_offerta_righe_espanse) (conversione offerta→ordine).

> **Vedi anche**
>
> - [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — righe standalone del listino
> - [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti) — composizione bundle
> - [vendite.fn_contratto_righe_preview](/dbzero/vendite/manual/fn_contratto_righe_preview) — consumer (drawer contratti)
> - [vendite.fn_offerta_righe_espanse](/dbzero/vendite/manual/fn_offerta_righe_espanse) — consumer (offerta→ordine)

## Firma

```sql
vendite.fn_espandi_listino_versione(
    p_listino_versione_id  vendite.listini_versioni.id%TYPE,
    p_tipo_var             varchar,   -- 'PERCENTUALE' | 'VALORE_FISSO' | NULL
    p_valore_var           numeric
)
RETURNS TABLE (
    articolo_id          catalogo.articoli.id%TYPE,
    articolo_codice      catalogo.articoli.codice%TYPE,
    articolo_descrizione catalogo.articoli.descrizione%TYPE,
    is_composito         catalogo.articoli.is_composito%TYPE,
    uom_id               vendite.listini_righe.uom_id%TYPE,
    uom_codice           catalogo.unita_misura.codice%TYPE,
    prezzo_listino       vendite.listini_righe.prezzo%TYPE,
    prezzo_da_listino    vendite.listini_righe.prezzo%TYPE,
    componenti           jsonb
)
LANGUAGE plpgsql STABLE
```

## Logica

- **Standalone** (`is_composito = FALSE`): da `listini_righe`; `prezzo_da_listino = prezzo ± variazione globale` (PERCENTUALE → `prezzo × (1 + valore/100)`; VALORE_FISSO → `prezzo + valore`; NULL → invariato). `prezzo_listino` = prezzo raw, `componenti` = NULL.
- **Bundle** (`is_composito = TRUE`): padri compositi distinti da `listini_righe_componenti`; `prezzo_da_listino = SUM(prezzo_componente × coeff_qta)`. `prezzo_listino` = NULL. `componenti` = `jsonb_agg` dei figli.

> ⚠️ **Fedeltà comportamentale**: la variazione globale si applica agli **standalone** ma **non ai bundle** (prezzo bundle = somma componenti), esattamente come nella `fn_contratto_righe_preview` storica. Questa asimmetria è intenzionale (no regressione del drawer contratti).

## Shape JSONB `componenti`

```json
{
  "articolo_componente_id": "uuid",
  "componente_id":          "uuid",
  "componente_codice":      "varchar",
  "componente_descrizione": "varchar",
  "uom_id":                 "bigint",
  "uom_codice":             "varchar",
  "coeff_qta":              "numeric",
  "prezzo":                 "numeric",
  "obbligatorio":           "boolean",
  "esposizione_in_fattura": "varchar"
}
```

`esposizione_in_fattura`: il codice interno del modo in cui il componente si vede in fattura sotto il suo kit (`NASCOSTO` | `DESCRITTIVO` | `VALORIZZATO`), letto da `catalogo.articoli_componenti`. Fino al 2026-10-01 la chiave era `esposto_in_fattura` (boolean: `false` → `NASCOSTO`, `true` → `DESCRITTIVO`), rev `20261001-54`.

`articolo_componente_id` (rispetto alla preview storica) serve ai consumer per copiare i componenti in `*_righe_componenti` (es. `ordini_righe_componenti`).

## Note operative

- `p_listino_versione_id IS NULL` → zero righe (no raise).
- `STABLE`, nessun side effect.
- Non risolve la *versione operativa* (snapshot vs lookup): è responsabilità del consumer passare la versione già risolta.
- Non risolve IVA né eccezioni: sono responsabilità del consumer di dominio.
