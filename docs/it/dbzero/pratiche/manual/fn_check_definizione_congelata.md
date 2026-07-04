## 📘 Documentazione Funzione – `pratiche.fn_check_definizione_congelata`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.trgfn_template_flussi_guard_immutabile](trgfn_template_flussi_guard_immutabile.md)
> [pratiche.trgfn_template_flussi_figli_guard_immutabile](trgfn_template_flussi_figli_guard_immutabile.md)
> [pratiche.fn_nuova_versione_definizione](fn_nuova_versione_definizione.md)
> [pratiche.fn_pubblica_definizione](fn_pubblica_definizione.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Predicato **puro** (boolean, nessun raise) che risponde a una sola domanda:
**questa edizione di workflow è "congelata" (in uso, non cancellabile)?**

> `TRUE` **se e solo se** la definizione è un'edizione **forkata**
> (`emittente_fiscale_id` valorizzato) **e** in stato **`PUBBLICATA`**.

Con la **strategia C** dell'immutabilità «Leggera» questo predicato governa
**specificamente il blocco `DELETE`** (un'edizione in uso non si smantella). Il blocco
`INSERT`/`UPDATE` (modifica struttura) è invece governato dal predicato più ampio
[fn_check_definizione_struttura_bloccata](fn_check_definizione_struttura_bloccata.md)
(PUBBLICATA **o** RITIRATA).

Conseguenze dirette:

* il **preset** di fabbrica (`emittente_fiscale_id NULL`) **non è mai congelato**, in
  qualsiasi stato → resta editabile da seed CSV / migrazioni (zero attrito sul seeding);
* solo il **fork `PUBBLICATA`** è congelato → non cancellabile (né modificabile);
* una **`RITIRATA`-emittente** **non è congelata** → **cancellabile** (housekeeping), pur
  restando **non modificabile** (è struttura-bloccata: ha ancora pratiche pinnate);
* le **`BOZZA`** non sono congelate → editabili e cancellabili.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_check_definizione_congelata(
    p_definizione_id pratiche.workflow_definizioni.id%TYPE
)
RETURNS boolean
LANGUAGE plpgsql STABLE
```

**Ritorna**: `true` se l'edizione è un fork pubblicato; `false` altrimenti.
`p_definizione_id` NULL o non trovata → `false` (fail-open: la coerenza
referenziale è già garantita dalle FK a monte).

---

### Note operative

* Funzione **`fn_check_*`** per convenzione: pura, `STABLE`, non solleva mai — la
  decisione di bloccare (raise) è dei guard che la invocano.
* Riuso: la usano i due guard di immutabilità
  ([template](trgfn_template_flussi_guard_immutabile.md) e
  [figli](trgfn_template_flussi_figli_guard_immutabile.md)); è chiamabile anche da
  viste/BE per esporre "editabile sì/no" senza duplicare la regola.
* Per **scongelare** un fork (es. per smantellarlo) va portato a `RITIRATA`
  (`PUBBLICATA→RITIRATA`); per modificarne la struttura si crea una nuova versione
  BOZZA ([fn_nuova_versione_definizione](fn_nuova_versione_definizione.md)).
* Introdotta con `20260703-10` (Parte 2 / Fase 2b, D2-9).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2b.sql` (casi 3–4).

---
{% include-markdown "signature-core.md" %}
