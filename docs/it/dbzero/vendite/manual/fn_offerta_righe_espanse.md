# fn_offerta_righe_espanse

### Scopo

Espande un'offerta commerciale nelle **righe effettive ordine-ready** = listino base + variazione globale + eccezioni applicate, pronte per la **conversione offerta → ordine**. È l'analogo per le offerte di [vendite.fn_contratto_righe_preview](/dbzero/vendite/manual/fn_contratto_righe_preview), ma con output orientato alla creazione di `ordini_righe` (non al drawer).

Riusa il core [vendite.fn_espandi_listino_versione](/dbzero/vendite/manual/fn_espandi_listino_versione) per la parte listino+BoM e applica l'overlay eccezioni su [offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni).

> **Vedi anche**
>
> - [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — testata (`listino_id` NOT NULL, variazione globale)
> - [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) — eccezioni (mirror di `contratti_righe`)
> - [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) — target della copia
> - [vendite.fn_espandi_listino_versione](/dbzero/vendite/manual/fn_espandi_listino_versione) — core condiviso

## Firma

```sql
vendite.fn_offerta_righe_espanse(
    p_offerta_id  vendite.offerte_commerciali.id%TYPE
)
RETURNS TABLE (
    articolo_id       catalogo.articoli.id%TYPE,
    articolo_codice   catalogo.articoli.codice%TYPE,
    descrizione       catalogo.articoli.descrizione%TYPE,
    is_composito      catalogo.articoli.is_composito%TYPE,
    quantita          vendite.ordini_righe.quantita%TYPE,
    uom_operativa_id  vendite.ordini_righe.uom_operativa_id%TYPE,
    qta_operativa     vendite.ordini_righe.qta_operativa%TYPE,
    factor_to_base    vendite.ordini_righe.factor_to_base%TYPE,
    prezzo_unitario   vendite.ordini_righe.prezzo_unitario%TYPE,
    sconto_perc       vendite.ordini_righe.sconto_perc%TYPE,
    iva_id            vendite.ordini_righe.iva_id%TYPE,
    iva_perc          vendite.ordini_righe.iva_perc%TYPE,
    tipo_eccezione    vendite.tipo_eccezione_contratto,
    origine           varchar,
    componenti        jsonb
)
LANGUAGE plpgsql STABLE
```

## Logica

1. Legge dalla testata offerta: `listino_id` (NOT NULL), `listino_versione_id`, variazione globale. Se lo snapshot versione è NULL (offerta BOZZA), risolve la versione operativa (`stato IN ('ATTIVA','CHIUSA') AND validita @> CURRENT_DATE`). **Nessun ramo "senza listino"**: le offerte hanno sempre il listino.
2. **Parte 1**: righe dal core `fn_espandi_listino_versione` + LEFT JOIN `offerte_commerciali_eccezioni` (OVERRIDE/ESCLUSIONE). OVERRIDE → `prezzo_unitario = ecc.prezzo_unitario`; **ESCLUSIONE → riga rimossa** (non copiabile in ordine); DA_LISTINO → `prezzo_da_listino`.
3. **Parte 2a/2b**: AGGIUNTA standalone e bundle da `offerte_commerciali_eccezioni` (+ `_componenti` per i bundle).

## Differenze rispetto a fn_contratto_righe_preview

| Aspetto | preview contratti (drawer) | offerta espansa (ordine) |
|---|---|---|
| ESCLUSIONE | riga mostrata, `prezzo_finale` NULL | **riga rimossa** |
| IVA | non risolta | `iva_id` (da articolo) + `iva_perc` (da `config.iva.aliquota_iva`) |
| Sconto | n/d | `sconto_perc` = NULL (lo sconto è già nel prezzo override) |
| UoM | `uom_id` listino | `uom_operativa_id`/`qta_operativa`/`factor_to_base` mappati su `ordini_righe` |
| Quantità da-listino | NULL | **default 1** |

## Note operative

- **Ordine-ready**: l'output popola `ordini_righe` senza arricchimenti BE (IVA, uom, sconto risolti in DB — principio DB-first).
- **Stato-agnostica**: la funzione espande qualunque offerta; il guard stato `ACCETTATA` è nella conversione (BE).
- IVA risolta dall'**articolo** (`catalogo.articoli.iva_id`): il listino non porta l'aliquota.
- `componenti` jsonb (bundle AGGIUNTA / da-listino) include `articolo_componente_id` per la copia in `ordini_righe_componenti`.
- `STABLE`; offerta inesistente → zero righe (no raise).
