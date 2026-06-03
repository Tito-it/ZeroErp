# trgfn_articoli_componenti_guard_iva

> **Vedi anche**
>
> - [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — tabella su cui il trigger opera
> - [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — lookup `iva_id` di padre e figlio
> - [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — gestione errori strutturata
> - [catalogo.trgfn_articoli_guard_iva_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva) — guard simmetrico su UPDATE iva_id dell'articolo

## Scopo

Garantisce che padre composito e figlio BoM condividano la stessa aliquota IVA al momento dell'INSERT **e a ogni (ri)attivazione del legame** in `catalogo.articoli_componenti`. L'invariante IVA uniforme è un requisito del modello unificato BoM (2026-05-13): se padre e figlio avessero IVA diversa, il calcolo del prezzo padre come somma dei figli produrrebbe righe fiscalmente incoerenti. Il confronto usa `IS DISTINCT FROM` per gestire correttamente il caso NULL = NULL (articoli senza IVA assegnata).

Insieme al guard simmetrico [`trgfn_articoli_guard_iva_bom_attiva`](/dbzero/catalogo/manual/trgfn_articoli_guard_iva_bom_attiva) (UPDATE di `iva_id` sull'articolo) e al freeze struttura (`componente_id` immutabile), questa funzione è il **punto unico di enforcement** dell'invariante IVA dei compositi: a valle, il listino non ri-controlla più l'IVA (Guard 5 di `script.trgfn_listini_righe_comp_guard_coerenza_bom` rimosso il 2026-06-03).

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
| Nome trigger | `trg_articoli_componenti_a10_guard_iva_bom_ins_upd` |
| Tabella | `catalogo.articoli_componenti` |
| Evento | `BEFORE INSERT OR UPDATE OF attivo` |
| Fase | `_a10_` (guard) |
| Scope | `FOR EACH ROW` |
| Perché `UPDATE OF attivo` | `prodotto_id`/`componente_id` restano immutabili (freeze struttura), ma `attivo` è modificabile: la riaccensione di un legame (`attivo` FALSE→TRUE) è l'unico percorso che poteva introdurre incoerenza IVA aggirando il guard B → la guardia ricontrolla l'IVA quando il legame (ri)diventa attivo (20260603-02) |

---

## Logica

Il trigger si applica solo a un legame **attivo**: se `NEW.attivo = FALSE` esce subito senza controlli (un legame spento non fa parte della BoM attiva). Altrimenti legge `iva_id` e `codice` di padre (`NEW.prodotto_id`) e figlio (`NEW.componente_id`) in un'unica `JOIN` su `catalogo.articoli`. Se i due `iva_id` risultano distinti (operatore `IS DISTINCT FROM`, che tratta NULL = NULL come uguali), viene sollevato l'errore `E_BOM_IVA_DISCORDANTE`.

```
0. IF NOT COALESCE(NEW.attivo, FALSE)   → RETURN NEW (skip: legame spento)

1. SELECT a_padre.iva_id, a_padre.codice,
          a_figlio.iva_id, a_figlio.codice
   FROM catalogo.articoli a_padre
   JOIN catalogo.articoli a_figlio ON a_figlio.id = NEW.componente_id
   WHERE a_padre.id = NEW.prodotto_id

2. IF v_iva_padre IS DISTINCT FROM v_iva_figlio
      → raise E_BOM_IVA_DISCORDANTE (445)
```

Su INSERT `attivo` ha default TRUE, quindi il controllo scatta sempre. Su `UPDATE OF attivo` lo skip al passo 0 ignora la deattivazione (FALSE) e intercetta la riaccensione (TRUE).

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

- Il trigger copre `BEFORE INSERT OR UPDATE OF attivo`. `prodotto_id`/`componente_id` restano immutabili (freeze struttura): la coppia padre-figlio cambia solo all'inserimento. Il fronte `UPDATE OF attivo` serve a coprire la **riattivazione** del legame.
- **Percorso chiuso (2026-06-03)**: prima il trigger era solo-INSERT e il guard B filtra `ac.attivo = TRUE`, lasciando aperta la sequenza *spegni legame → cambia `iva_id` padre (guard B ignora i legami spenti) → riaccendi legame*, che produceva una BoM attiva con padre e figlio a IVA diversa. Spostando il controllo anche sulla riaccensione, la sorgente è ora completa e il listino non deve più fare da rete a valle.
- Il guard simmetrico `trgfn_articoli_guard_iva_bom_attiva` protegge il caso inverso: quando si modifica `iva_id` su un articolo che partecipa già a BoM attive (`ac.attivo = TRUE`).
- Migration di riferimento: `20260513-02` (creazione), `20260513-33` (messaggio aliquota %), `20260603-01` (corpo: skip su legame spento), `20260603-02` (binding `INSERT OR UPDATE OF attivo`).
