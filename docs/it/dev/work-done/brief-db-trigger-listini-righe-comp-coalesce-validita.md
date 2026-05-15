# Brief DB — Fix asimmetria COALESCE in `trgfn_listini_righe_comp_guard_coerenza_bom`

> **Data**: 2026-05-15
> **Branch target**: `dev/db-tid`
> **Urgenza**: BLOCCA la duplica versione listino con BoM quando `valido_al` non valorizzato.
> Riproducibile end-to-end con il pattern "1ª clone OK con valido_al concreto → elimina →
> 2ª clone con valido_al lasciato vuoto → fallisce con `E_LISTINO_COMPONENTE_COERENZA_BOM`".

## 1. Sintesi

Il trigger `script.trgfn_listini_righe_comp_guard_coerenza_bom` (guard 7,
coerenza periodo riga ⊆ versione) costruisce **manualmente** la validità
della riga senza applicare COALESCE NULL→'infinity', mentre confronta con
la validità della versione che è **GENERATED STORED** *con* COALESCE.

Risultato: `valido_al = NULL` sulla riga produce `daterange [d,)` (open
upper), mentre `valido_al = NULL` sulla versione produce STORED
`[d, infinity]` (letterale). PostgreSQL considera le due rappresentazioni
*non contenute*, e il guard solleva
`E_LISTINO_COMPONENTE_COERENZA_BOM` anche se logicamente i due range
coincidono.

Messaggio errore osservato lato UI:

```
Riga listino componenti incoerente:
  validita=[2026-05-16,) non contenuta in versione=[2026-05-16,infinity].
```

## 2. Root cause precisa

Funzione [`script.trgfn_listini_righe_comp_guard_coerenza_bom`](../../dbzero/script/funzioni/trgfn_listini_righe_comp_guard_coerenza_bom.md), riga 34:

```sql
-- Attuale (asimmetrico)
v_new_validita := daterange(NEW.valido_dal, NEW.valido_al, '[]');
```

Confrontato a riga 128 con:

```sql
IF v_lv_validita IS NULL OR NOT (v_lv_validita @> v_new_validita) THEN
    -- raise E_LISTINO_COMPONENTE_COERENZA_BOM
END IF;
```

Dove `v_lv_validita := vendite.listini_versioni.validita` è la STORED
column generata come `daterange(COALESCE(d,'-infinity'::date),
COALESCE(a,'infinity'::date), '[]')`.

**Asimmetria**:

| Sorgente | NULL su `valido_al` → range | Rendering |
| --- | --- | --- |
| `v_lv_validita` (STORED su versione, con COALESCE) | `[d, infinity]` letterale | `[d,infinity]` |
| `v_new_validita` (calcolato in trigger, senza COALESCE) | `[d, NULL)` open | `[d,)` |

`v_lv_validita @> v_new_validita` ritorna `false` per il mismatch di forma
canonica anche quando i due intervalli sono logicamente lo stesso
(da `d` fino a sempre).

## 3. Reproducer minimale

```sql
-- Setup: una versione con valido_al NULL (STORED→infinity), un articolo
-- composito con BoM valido_al NULL, IVA coerente.
-- Tentativo di INSERT su listini_righe_componenti con valido_al NULL:

INSERT INTO vendite.listini_righe_componenti (
    listino_versione_id, articolo_componente_id,
    articolo_padre_id, articolo_figlio_id,
    prezzo, iva_id, valido_dal, valido_al, attivo
) VALUES (
    <ver_id>, <ac_id>,
    <padre>, <figlio>,
    10.00, <iva>, '2026-05-16', NULL, TRUE
);
-- ERROR:  E_LISTINO_COMPONENTE_COERENZA_BOM
-- HINT:   validita=[2026-05-16,) non contenuta in versione=[2026-05-16,infinity]
```

Workaround temporaneo lato applicazione: passare `'infinity'::date`
letterale invece di `NULL`. Ma è una pezza: qualunque caller che
seguirà la convenzione "NULL = open-ended" inciamperà nel guard.

## 4. Fix proposto

Allineare il calcolo di `v_new_validita` al canonico STORED:

```sql
-- Proposta (simmetrico, COALESCE come la STORED su listini_versioni)
v_new_validita := daterange(
    COALESCE(NEW.valido_dal, '-infinity'::date),
    COALESCE(NEW.valido_al,  'infinity'::date),
    '[]'
);
```

Nessun cambio comportamentale per gli insert con date concrete:
COALESCE è no-op quando il valore è non-NULL. Il fix tocca solo gli
insert con `valido_dal=NULL` o `valido_al=NULL`, che oggi falliscono
spuriamente.

## 5. Cosa fare

**Nuovo changelog** con numerazione successiva (es.
`20260515-XX-update-trgfn-listini-righe-comp-guard-coerenza-bom-coalesce-mctit.yaml`)
con `runOnChange: true` e `validCheckSums: [ANY]`, che fa
`CREATE OR REPLACE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()`
identica all'originale (rev 2026-05-14) **eccetto la riga 34** del corpo,
sostituita come sopra.

Aggiornare anche:

* Il commento head della funzione (riga 21 nel corpo `--` rendering):
  da
  > `v_new_validita: daterange(NEW.valido_dal, NEW.valido_al, '[]') perche' validita e' STORED generated, non disponibile nei BEFORE trigger (D-OPEN-1).`

  a
  > `v_new_validita: daterange(coalesce(NEW.valido_dal,'-infinity'), coalesce(NEW.valido_al,'infinity'), '[]') — match STORED expression su listini_versioni.validita per evitare mismatch canonico NULL vs 'infinity' (rev 2026-05-15).`

* `COMMENT ON FUNCTION` finale: bump rev a `2026-05-15` e nota
  "fix COALESCE simmetrico vs STORED versioni listino".

## 6. Verifica post-deploy

**Smoke test pgTAP (o psql diretto)**:

```sql
-- 1) Versione con valido_al NULL
INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al, stato)
VALUES (<l>, 'TEST-INF', '2026-05-16', NULL, 'BOZZA') RETURNING id;
-- v_id = X

-- 2) BoM componente con valido_al NULL
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, valido_dal, valido_al, attivo)
VALUES (<padre_composito>, <figlio>, '2026-05-16', NULL, TRUE) RETURNING id;
-- ac_id = Y

-- 3) Riga listino componenti con valido_al NULL → DEVE passare il guard
INSERT INTO vendite.listini_righe_componenti (
    listino_versione_id, articolo_componente_id,
    articolo_padre_id, articolo_figlio_id,
    prezzo, iva_id, valido_dal, valido_al, attivo
) VALUES (X, Y, <padre>, <figlio>, 10.00, <iva>, '2026-05-16', NULL, TRUE);
-- ATTESO: OK (pre-fix: E_LISTINO_COMPONENTE_COERENZA_BOM)
```

**Regression**: invariata l'azione del guard sui range realmente
incompatibili (riga oltre versione):

```sql
INSERT INTO vendite.listini_righe_componenti (
    ..., valido_dal, valido_al, ...
) VALUES (..., '2026-05-16', '2099-12-31', ...);
-- Se la versione ha valido_al='2026-12-31':
-- ATTESO ancora: E_LISTINO_COMPONENTE_COERENZA_BOM (riga oltre versione)
```

## 7. Impatto applicativo post-fix

Una volta atterrato il fix DB, il backend potrà rimuovere il workaround
nel CASE WHEN di `clone_versione` step 3 + `upsert_bundle_componenti`
([`backend/apps/vendite/db/listini_repository.py`](../../../backend/apps/vendite/db/listini_repository.py) righe 546-550 e
1347-1351) e tornare a una formula più semplice:

```sql
-- Post-fix DB: il caller può passare NULL → niente più mismatch canonico
GREATEST(ac.valido_dal, target_v.valido_dal),
LEAST(
    COALESCE(ac.valido_al, 'infinity'::date),
    COALESCE(target_v.valido_al, 'infinity'::date)
) -- → ammette NULL su entrambi: ritorna 'infinity'::date, trigger ora coerente
```

(Da valutare se preferire `infinity::date` letterale sull'INSERT — più
esplicito — o `NULL` puro — più idiomatico nelle convenzioni temporal
della codebase. Decidere col team DB.)

## 8. Riferimenti

* Funzione attuale: `docs/it/dbzero/script/funzioni/trgfn_listini_righe_comp_guard_coerenza_bom.md`
  (rev 2026-05-14, post-rimozione guard 6 in `20260514-12`).
* Tabella vincolata: `vendite.listini_righe_componenti`
  (FK temporale `fk_listrighe_comp_articoli_comp_temporal`).
* Tabella di riferimento per `v_lv_validita`: `vendite.listini_versioni.validita`
  (STORED generated, COALESCE NULL→'-infinity'/'infinity').
* App-side workaround attuale: commit `b8068878f` (CASE WHEN) +
  fix simmetrico `upsert_bundle` working tree 2026-05-15.

---

**Stima effort DB**: 1 changelog `runOnChange`, ~10 righe modificate
nel corpo + comment. pgTAP test ~30 righe. Stimato < 1h.
