# trgfn_componenti_check_prezzo_obbligatorio

> **Vedi anche**
>
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — lookup flag `obbligatorio`
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — lookup `codice` del componente
> - [script.trgfn_componenti_guard_coerenza_bom](/dbzero/script/manual/trgfn_componenti_guard_coerenza_bom) — guard precedente nella stessa fase `_a10_`
> - [script.trgfn_componenti_guard_obbligatorio](/dbzero/script/manual/trgfn_componenti_guard_obbligatorio) — guard complementare su disattivazione
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata

## Scopo

Blocca `prezzo_unitario = 0` esclusivamente per i componenti BoM marcati `obbligatorio = TRUE`. I componenti opzionali ammettono qualsiasi valore, incluso zero (servizi inclusi a costo zero) e valori negativi (sconti, abbuoni). Questo trigger sostituisce il vecchio `CHECK (prezzo_unitario <> 0)` rimosso con la migration `20260513-06`, che era troppo restrittivo per il modello unificato BoM.

---

## Schema DB

`script` (funzione generica riusata da più tabelle)

## Firma

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_check_prezzo_obbligatorio()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger registrati

La stessa funzione è registrata su 4 tabelle:

| Trigger | Tabella | Evento |
|---|---|---|
| `trg_prevrighe_comp_a10_prezzo_obbligatorio_ins_upd` | `vendite.preventivi_righe_componenti` | `BEFORE INSERT OR UPDATE OF prezzo_unitario, articolo_componente_id` |
| `trg_ordrighe_comp_a10_prezzo_obbligatorio_ins_upd` | `vendite.ordini_righe_componenti` | `BEFORE INSERT OR UPDATE OF prezzo_unitario, articolo_componente_id` |
| `trg_ddtrighe_comp_a10_prezzo_obbligatorio_ins_upd` | `vendite.ddt_righe_componenti` | `BEFORE INSERT OR UPDATE OF prezzo_unitario, articolo_componente_id` |
| `trg_contrighe_comp_a10_prezzo_obbligatorio_ins_upd` | `vendite.contratti_righe_componenti` | `BEFORE INSERT OR UPDATE OF prezzo_unitario, articolo_componente_id` |

Tutti con fase `_a10_` (guard), scope `FOR EACH ROW`.

---

## Logica

```
1. SELECT ac.obbligatorio, a.codice
   FROM catalogo.articoli_componenti ac
   JOIN catalogo.articoli a ON a.id = ac.componente_id
   WHERE ac.id = NEW.articolo_componente_id

2. IF COALESCE(v_obbligatorio, TRUE) AND NEW.prezzo_unitario = 0
      → raise E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO (444)
```

Il `COALESCE(v_obbligatorio, TRUE)` è conservativo: se per qualunque motivo il record BoM non viene trovato, il check viene applicato come se il componente fosse obbligatorio. Valori negativi del prezzo sono esplicitamente ammessi (il check è `= 0`, non `<= 0`).

---

## Ordine con altri trigger

All'interno della fase `_a10_`, l'ordine di esecuzione è determinato dal nome del trigger in ordine alfabetico:

| Ordine | Trigger | Verifica |
|---|---|---|
| 1 | `trg_*_a10_guard_coerenza_bom_*` | Esistenza e coerenza di `articolo_componente_id` nella BoM |
| 2 | `trg_*_a10_prezzo_obbligatorio_*` | Prezzo zero su obbligatorio (questo trigger) |

Il trigger di coerenza BoM scatta prima: se `articolo_componente_id` non è valido, il blocco avviene già al guard precedente e questo trigger non viene mai raggiunto.

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 444 | Componente con `obbligatorio = TRUE` ha `prezzo_unitario = 0` |

Contesto JSON: `articolo_componente_id`, `componente_id`, `prezzo_unitario`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli_componenti` | Tabella | Lookup flag `obbligatorio` |
| `catalogo.articoli` | Tabella | Lookup `codice` del componente per il messaggio di errore |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- La motivazione della sostituzione del CHECK con questo trigger è la distinzione obbligatorio/opzionale: il CHECK universale impediva abbuoni (prezzo negativo) e componenti opzionali a zero su qualunque riga componente, rendendo il modello troppo rigido.
- Valori negativi rimangono ammessi anche per i componenti obbligatori (es. sconti sul composito espressi come componente negativo).
- Migration di riferimento: `20260513-07` (rimozione CHECK: `20260513-06`).
