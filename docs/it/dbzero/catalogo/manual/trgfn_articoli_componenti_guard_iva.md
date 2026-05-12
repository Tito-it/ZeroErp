# trgfn_articoli_componenti_guard_iva

> **Vedi anche**
>
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — tabella su cui il trigger opera
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — lookup `iva_id` di padre e figlio
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata
> - [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva) — guard simmetrico su UPDATE iva_id dell'articolo

## Scopo

Garantisce che padre composito e figlio BoM condividano la stessa aliquota IVA al momento dell'INSERT in `catalogo.articoli_componenti`. L'invariante IVA uniforme è un requisito del modello unificato BoM (2026-05-13): se padre e figlio avessero IVA diversa, il calcolo del prezzo padre come somma dei figli produrrebbe righe fiscalmente incoerenti. Il confronto usa `IS DISTINCT FROM` per gestire correttamente il caso NULL = NULL (articoli senza IVA assegnata).

---

## Schema DB

`catalogo`

## Firma

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_guard_iva()
RETURNS trigger
LANGUAGE plpgsql
```

## Trigger associato

| Attributo | Valore |
|---|---|
| Nome trigger | `trg_articoli_componenti_a10_guard_iva_bom_ins` |
| Tabella | `catalogo.articoli_componenti` |
| Evento | `BEFORE INSERT` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| UPDATE escluso | `prodotto_id` e `componente_id` sono immutabili per struttura (bloccati da `trg_articoli_componenti_a10_block_modifica_struttura`); `iva_id` non è una colonna di `articoli_componenti` |

---

## Logica

Il trigger legge `iva_id` e `codice` di padre (`NEW.prodotto_id`) e figlio (`NEW.componente_id`) in un'unica `JOIN` su `catalogo.articoli`. Se i due `iva_id` risultano distinti (operatore `IS DISTINCT FROM`, che tratta NULL = NULL come uguali), viene sollevato l'errore `E_BOM_IVA_DISCORDANTE`.

```
1. SELECT a_padre.iva_id, a_padre.codice,
          a_figlio.iva_id, a_figlio.codice
   FROM catalogo.articoli a_padre
   JOIN catalogo.articoli a_figlio ON a_figlio.id = NEW.componente_id
   WHERE a_padre.id = NEW.prodotto_id

2. IF v_iva_padre IS DISTINCT FROM v_iva_figlio
      → raise E_BOM_IVA_DISCORDANTE (445)
```

---

## Comportamento su NULL

Se uno dei due articoli ha `iva_id = NULL`, il confronto `NULL IS DISTINCT FROM NULL` restituisce `FALSE`: il trigger non solleva errore. Questo è il comportamento intenzionale: un articolo senza IVA ancora assegnata può partecipare a una BoM in attesa di completamento dell'anagrafica.

---

## Codici errore

| Codice | ID | Quando |
|---|---|---|
| `E_BOM_IVA_DISCORDANTE` | 445 | `iva_id` del figlio diverso da `iva_id` del padre composito |

Contesto JSON incluso nella segnalazione: `prodotto_id`, `componente_id`, `iva_padre`, `iva_figlio`.

---

## Dipendenze

| Oggetto | Tipo | Motivo |
|---|---|---|
| `catalogo.articoli` | Tabella | Lookup `iva_id` e `codice` di padre e figlio |
| `script.fn_log_and_raise_error` | Funzione | Registrazione e raise strutturato dell'errore |

---

## Note operative

- Il trigger copre solo `BEFORE INSERT`: `prodotto_id` e `componente_id` sono immutabili dopo l'insert (bloccati da guard separato), quindi l'unico momento in cui la coppia cambia è all'inserimento.
- Il guard simmetrico `trgfn_articoli_guard_iva_bom_attiva` protegge il caso inverso: quando si modifica `iva_id` su un articolo che partecipa già a BoM attive.
- Migration di riferimento: `20260513-02`.
