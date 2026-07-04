## 📘 Documentazione Funzione – `pratiche.fn_check_definizione_struttura_bloccata`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_check_definizione_congelata](fn_check_definizione_congelata.md)
> [pratiche.trgfn_template_flussi_guard_immutabile](trgfn_template_flussi_guard_immutabile.md)
> [pratiche.trgfn_template_flussi_figli_guard_immutabile](trgfn_template_flussi_figli_guard_immutabile.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Predicato **puro** (boolean, no raise) che risponde a: **la struttura di questa
edizione è bloccata alla modifica?**

> `TRUE` **se e solo se** la definizione è un'edizione **forkata**
> (`emittente_fiscale_id` valorizzato) **già emessa**, cioè fuori da BOZZA
> (`stato <> 'BOZZA'` → **PUBBLICATA o RITIRATA**).

È il predicato che governa il blocco **INSERT/UPDATE** di template e figli
(strategia **C** dell'immutabilità «Leggera»): le pratiche pinnate a un'edizione
emessa non devono vedere cambiare la struttura sotto di loro (V6) — e questo vale
**anche per una RITIRATA**, che ha ancora pratiche pinnate alla sua versione.

---

### Relazione con `fn_check_definizione_congelata`

Due predicati, due assi:

| Predicato | Vero su | Governa |
|---|---|---|
| **`fn_check_definizione_struttura_bloccata`** | fork **PUBBLICATA o RITIRATA** | blocco **INSERT/UPDATE** (modifica struttura) |
| [`fn_check_definizione_congelata`](fn_check_definizione_congelata.md) | fork **PUBBLICATA** soltanto | blocco **DELETE** (edizione in uso) |

Conseguenza (strategia **C**): una **RITIRATA-emittente** è *struttura-bloccata*
(non editabile) ma **non congelata** → **cancellabile** (housekeeping /
smantellamento delle edizioni storiche; il pattern "ritira-poi-cancella" resta
valido). Il **preset** (emittente NULL) e le **BOZZA** restano liberamente editabili.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_check_definizione_struttura_bloccata(
    p_definizione_id pratiche.workflow_definizioni.id%TYPE
)
RETURNS boolean
LANGUAGE plpgsql STABLE
```

`p_definizione_id` NULL o non trovata → `false`.

---

### Note operative

- Funzione `fn_check_*`: pura, `STABLE`, no raise. Unico punto della regola
  "struttura bloccata"; la invocano i due guard di immutabilità per il ramo
  INSERT/UPDATE.
- Introdotta con `20260704-02` (strategia C, brief-db-accesso-write-editing-bozza
  §Problema 3).
- Test: `db/pgtap/pratiche/test-definizione-ritirata-edit-freeze.sql`.

---
{% include-markdown "signature-core.md" %}
