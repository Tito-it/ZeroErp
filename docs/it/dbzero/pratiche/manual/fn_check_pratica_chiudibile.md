## 📘 Documentazione Funzione – `pratiche.fn_check_pratica_chiudibile`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_check_chiusura_pratica](fn_check_chiusura_pratica.md)
> [pratiche.fn_pratica_flussi_aperti](fn_pratica_flussi_aperti.md)
> [pratiche.trgfn_flussi_autochiusura_pratica](trgfn_flussi_autochiusura_pratica.md)
> [pratiche.trgfn_flussi_guard_chiusura_prematura](trgfn_flussi_guard_chiusura_prematura.md)

---
### 🎯 Scopo Principale

`fn_check_*` puro (no raise): risponde "la pratica e' **chiudibile**?", cioe' **non ha
piu' lavoro da fare** (brief-db-chiusura-pratica-nessun-lavoro-pendente §2). Due leve
data-driven, entrambe devono valere:

- **(a)** nessun template **obbligatorio bloccante** (obbligatorio, non completato,
  ancora percorribile) secondo [fn_check_chiusura_pratica](fn_check_chiusura_pratica.md).
  Il ramo morto di un bivio non blocca;
- **(b)** nessun **flusso istanziato in stato non terminale** (lavoro avviato pendente)
  secondo [fn_pratica_flussi_aperti](fn_pratica_flussi_aperti.md) — clausola **D1**.

Lo stesso predicato e' usato dalla chiusura **automatica** e dalla chiusura **manuale**
(via il guard di chiusura), cosi' non divergono.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_pratica_chiudibile(
    p_pratica_id          pratiche.flussi.pratica_id%TYPE,
    p_escludi_template_id pratiche.template_flussi.id%TYPE DEFAULT NULL,
    p_escludi_flusso_id   pratiche.flussi.id%TYPE          DEFAULT NULL
)
RETURNS boolean
LANGUAGE sql STABLE
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_pratica_id` | SI | Pratica da valutare |
| `p_escludi_template_id` | NO | Template da ignorare dalla clausola (a) bloccanti |
| `p_escludi_flusso_id` | NO | Istanza da ignorare dalla clausola (b) flussi aperti |

I due `p_escludi_*` servono al guard pre-completamento del **flusso di chiusura** (non
ancora COMPLETATO al momento del check): si escludono il suo **template** dai bloccanti
e la sua **istanza** dai flussi aperti, cosi' il flusso di chiusura non blocca sé stesso.

---

### Note operative

* Consumata da [trgfn_flussi_autochiusura_pratica](trgfn_flussi_autochiusura_pratica.md)
  (decide se auto-chiudere) e da [trgfn_flussi_guard_chiusura_prematura](trgfn_flussi_guard_chiusura_prematura.md)
  (decide se ammettere il completamento del flusso di chiusura).
* La chiusura **manuale** applica lo stesso principio via
  [trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)
  (clausola a → err 485, clausola b → err 501).
* Funzione `STABLE`, pura: nessun effetto collaterale, nessun `RAISE`.
* La firma a 2 argomenti resta valida (i chiamanti pre-D1 continuano a funzionare: il
  3° parametro ha default).
* Test: `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql` (bivio + D1) e
  `test-autochiusura-pratica.sql` (modelli A/B).

---
{% include-markdown "signature-core.md" %}
