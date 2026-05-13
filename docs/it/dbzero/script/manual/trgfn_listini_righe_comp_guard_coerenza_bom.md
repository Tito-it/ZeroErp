# trgfn_listini_righe_comp_guard_coerenza_bom

> **Vedi anche**
>
> - [vendite.listini_righe_componenti](/dbzero/vendite/manual/listini_righe_componenti) — tabella su cui il trigger opera
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — sorgente verità BoM
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — padre e figlio per check IVA e is_composito
> - [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — verifica validità versione (guard 7)
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Esegue 7 guard di coerenza per garantire che ogni riga inserita o aggiornata in `vendite.listini_righe_componenti` sia perfettamente allineata con la BoM catalogo, le regole IVA e i vincoli di validità temporale. Il trigger è il punto di verità centralizzato per l'integrità della tabella bundle: senza questi guard, le colonne denorm (`articolo_padre_id`, `articolo_figlio_id`) potrebbero divergere dalla BoM, o potrebbero esistere prezzi bundle per periodi non coperti dalla BoM o dalla versione listino.

---

## Schema DB

`script` (funzione generica cross-dominio)

## Firma

```sql
CREATE OR REPLACE FUNCTION script.trgfn_listini_righe_comp_guard_coerenza_bom()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_listrighe_comp_a10_guard_coerenza_bom_ins_upd` |
| Tabella | `vendite.listini_righe_componenti` |
| Evento | `BEFORE INSERT OR UPDATE` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |

---

## I 7 guard

I guard 1-5 si basano su una singola `JOIN` unificata su `articoli_componenti + 2 articoli`. Il guard 7 richiede una seconda query separata su `listini_versioni`.

| # | Condizione verificata | Causa errore se fallisce |
|---|---|---|
| 1 | `articolo_componente_id` esiste in `catalogo.articoli_componenti` e `attivo = TRUE` | `articolo_componente_id non trovato o non attivo` |
| 2 | `NEW.articolo_padre_id = ac.prodotto_id` (denorm coerente) | `articolo_padre_id non coincide con BoM.prodotto_id` |
| 3 | `NEW.articolo_figlio_id = ac.componente_id` (denorm coerente) | `articolo_figlio_id non coincide con BoM.componente_id` |
| 4 | `padre.is_composito = TRUE` | `articolo padre non e'' composito` |
| 5 | `figlio.iva_id = padre.iva_id` (coerenza IVA) | `IVA padre != IVA figlio` |
| 6 | `NEW.validita ⊆ ac.validita` (validità riga ⊆ validità BoM) | `validita riga listino comp non contenuta in validita BoM` |
| 7 | `NEW.validita ⊆ lv.validita` (validità riga ⊆ validità versione listino) | `validita riga listino comp non contenuta in validita versione listino` |

Tutti i 7 guard sollevano il codice `E_LISTINO_COMPONENTE_COERENZA_BOM` (447) con una causa specifica nel contesto JSON.

---

## Logica di esecuzione

```sql
-- Lettura unificata guard 1-6
SELECT ac.prodotto_id, ac.componente_id, ac.attivo, ac.validita,
       a_padre.is_composito, a_padre.iva_id,
       a_figlio.iva_id
FROM catalogo.articoli_componenti ac
JOIN catalogo.articoli a_padre ON a_padre.id = ac.prodotto_id
JOIN catalogo.articoli a_figlio ON a_figlio.id = ac.componente_id
WHERE ac.id = NEW.articolo_componente_id;

-- Guard 7: query separata
SELECT lv.validita
FROM vendite.listini_versioni lv
WHERE lv.id = NEW.listino_versione_id;
```

Il guard 6 usa l'operatore `@>` (containment) sui `DATERANGE`: `ac.validita @> NEW.validita` verifica che il periodo della riga bundle sia interamente contenuto nel periodo della BoM.

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_LISTINO_COMPONENTE_COERENZA_BOM` | 447 | Qualsiasi dei 7 guard fallisce; la causa specifica è nel contesto JSON |

Il campo `causa` nel contesto JSON identifica quale guard ha prodotto l'errore. I valori possibili sono riportati nella tabella dei guard sopra.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli_componenti` | Tabella | Sorgente verità BoM per guard 1-6 |
| `catalogo.articoli` | Tabella | Check `is_composito` (guard 4) e `iva_id` padre/figlio (guard 5) |
| `vendite.listini_versioni` | Tabella | Verifica validità versione (guard 7) |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- Il guard 6 usa `v_ac_validita IS NULL OR NOT (v_ac_validita @> NEW.validita)`: se la BoM non ha validità (`NULL`), il controllo fallisce — le BoM senza periodo non possono avere prezzi bundle associati.
- Allo stesso modo, il guard 7 fallisce se la versione listino non ha validità (`NULL`).
- Il confronto IVA al guard 5 usa `IS DISTINCT FROM`: NULL = NULL è considerato uguale (coerenza con il guard IVA su `articoli_componenti`).
- Migration di riferimento: `20260513-19`.
