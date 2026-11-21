# fn_offerta_righe_espanse

> **Ultimo aggiornamento**: 21 novembre 2026

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
    sconto_percentuale  vendite.ordini_righe.sconto_percentuale%TYPE,
    iva_id            vendite.ordini_righe.iva_id%TYPE,
    tipo_eccezione    vendite.tipo_eccezione_contratto,
    origine           varchar,
    componenti        jsonb,
    eccezione_id      vendite.offerte_commerciali_eccezioni.id%TYPE,
    -- la provenienza del prezzo, che la riga d'ordine copia
    origine_prezzo          vendite.ordini_righe.origine_prezzo%TYPE,
    listino_versione_id     vendite.ordini_righe.listino_versione_id%TYPE,
    listino_riga_id         vendite.ordini_righe.listino_riga_id%TYPE,
    prezzo_resolver_context vendite.ordini_righe.prezzo_resolver_context%TYPE
)
LANGUAGE plpgsql STABLE
```

## Logica

1. Legge dalla testata offerta: `listino_id` (NOT NULL), `listino_versione_id`, variazione globale. Se lo snapshot versione è NULL (offerta BOZZA), risolve la versione operativa (`stato IN ('ATTIVA','CHIUSA') AND validita @> CURRENT_DATE`). **Nessun ramo "senza listino"**: le offerte hanno sempre il listino.
2. **Parte 1**: righe dal core `fn_espandi_listino_versione` + LEFT JOIN `offerte_commerciali_eccezioni` (OVERRIDE/ESCLUSIONE). OVERRIDE → `prezzo_unitario = ecc.prezzo_unitario`; **ESCLUSIONE → riga rimossa** (non copiabile in ordine); DA_LISTINO → `prezzo_da_listino`.
3. **Parte 2a/2b**: AGGIUNTA standalone e bundle da `offerte_commerciali_eccezioni` (+ `_componenti` per i bundle).

## La provenienza del prezzo

Ogni riga dice **da dove viene il suo prezzo**, nella forma delle righe di documento, e
[vendite.fn_genera_ordine_da_offerta](/dbzero/vendite/funzioni/fn_genera_ordine_da_offerta) la
copia sulla riga d'ordine così com'è:

| Riga | `origine_prezzo` | Versione e riga di listino | Contesto |
| --- | --- | --- | --- |
| dal listino dell'offerta (`DA_LISTINO`, anche con l'ADESIONE) | `CONTRATTO_LISTINO`: il listino fissato dal documento, la stessa origine che il resolver dà alle righe dell'offerta | la versione operativa; la riga di listino se l'unità della riga è la sua | `prezzo_base_snapshot` (il prezzo della riga di listino), `tipo_variazione_applicata` e `valore_variazione_applicata` (la variazione globale; `NESSUNA` e 0 senza) |
| `OVERRIDE`, `AGGIUNTA` semplice | quella dell'eccezione | quelle dell'eccezione | quello dell'eccezione |
| kit | nessuna: il prezzo del padre è la somma dei componenti, e lo scrive `COMPONENTI` | — | — |

Sul kit, `componenti` porta per ogni componente il prezzo **e la sua provenienza**
(`origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`):
l'elemento è già un override che [vendite.fn_componente_override](/dbzero/vendite/funzioni/fn_componente_override)
legge.

* **AGGIUNTA composita, e OVERRIDE su un kit che ha componenti suoi**: i componenti
  dell'eccezione ([vendite.fn_offerta_eccezione_componenti_espansi](/dbzero/vendite/funzioni/fn_offerta_eccezione_componenti_espansi)),
  coi prezzi negoziati. Il prezzo forzato del kit è la loro somma, e l'ordine lo ritrova.
* **Kit dal listino**: i componenti del listino, `LISTINO_BUNDLE` con la versione, senza riga
  di listino (il prezzo sta in `listini_righe_componenti`) e senza variazione.
* Un OVERRIDE su un kit **senza** componenti suoi prenderebbe i componenti del listino.
  Non succede: un'offerta con un kit col prezzo negoziato senza componenti attivi non si
  emette ([script.fn_check_offerta_kit_con_componenti](/dbzero/script/funzioni/fn_check_offerta_kit_con_componenti)),
  e fuori dalla bozza i componenti non si toccano.

## Differenze rispetto a fn_contratto_righe_preview

| Aspetto | preview contratti (drawer) | offerta espansa (ordine) |
| --- | --- | --- |
| ESCLUSIONE | riga mostrata, `prezzo_finale` NULL | **riga rimossa** |
| IVA | non risolta | `iva_id` (da articolo); l'aliquota si deriva da `iva_id` (no `iva_perc`) |
| Sconto | n/d | `sconto_percentuale` = NULL (lo sconto è già nel prezzo override) |
| UoM | `uom_id` listino | `uom_operativa_id`/`qta_operativa`/`factor_to_base` mappati su `ordini_righe` |
| Quantità da-listino | NULL | **default 1** |

## Note operative

- **Ordine-ready**: l'output popola `ordini_righe` senza arricchimenti BE (IVA, uom, sconto risolti in DB — principio DB-first).
- **Stato-agnostica**: la funzione espande qualunque offerta; il guard stato `ACCETTATA` è nella conversione (BE).
- IVA risolta dall'**articolo** (`catalogo.articoli.iva_id`): il listino non porta l'aliquota.
- `componenti` jsonb (bundle AGGIUNTA / da-listino) include `articolo_componente_id` per la copia in `ordini_righe_componenti`.
- `STABLE`; offerta inesistente → zero righe (no raise).

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

La versione del listino in vigore per l'offerta senza versione fissata non è più scelta qui: la dice [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) (`20260928-40`). Per ogni data la versione in vigore è **al più una**, per costruzione (nessuna sovrapposizione fra versioni ATTIVE e CHIUSE, date di una CHIUSA bloccate), quindi «la prima» e «tutte le valide» sono la stessa cosa. Stesso esito, provato sui dati di dev.

<!-- rev-2026-10-04-listino-operativo -->
### 🔄 rev 2026-10-04 — brief-db-righe-esclusione-solo-non-si-vende

La versione e la variazione globale vengono da [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo) (`20261004-74`), la sede unica che serve anche la lista delle righe e i guard di contratto e offerta. Stessa regola di prima. Questa funzione resta la lista **pronta per l'ordine** (esclusioni tolte, quantità di default 1); la lista del drawer è [vendite.fn_offerta_righe_preview](/dbzero/vendite/funzioni/fn_offerta_righe_preview).
