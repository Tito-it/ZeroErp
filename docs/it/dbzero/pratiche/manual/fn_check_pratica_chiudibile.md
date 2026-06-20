## 📘 Documentazione Funzione – `pratiche.fn_check_pratica_chiudibile`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_check_chiusura_pratica](fn_check_chiusura_pratica.md)
> [pratiche.trgfn_flussi_autochiusura_pratica](trgfn_flussi_autochiusura_pratica.md)
> [pratiche.trgfn_flussi_guard_chiusura_prematura](trgfn_flussi_guard_chiusura_prematura.md)

---
### 🎯 Scopo Principale

`fn_check_*` puro (no raise): risponde "la pratica e' **chiudibile**?", cioe' non
resta alcun template **obbligatorio bloccante** (obbligatorio, non completato,
ancora percorribile) secondo `fn_check_chiusura_pratica`.
Il ramo morto di un bivio non blocca.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_pratica_chiudibile(
    p_pratica_id          pratiche.pratiche.id%TYPE,
    p_escludi_template_id pratiche.template_flussi.id%TYPE DEFAULT NULL
)
RETURNS boolean
LANGUAGE sql STABLE
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_pratica_id` | SI | Pratica da valutare |
| `p_escludi_template_id` | NO | Template da ignorare dal calcolo dei bloccanti |

`p_escludi_template_id` serve al guard pre-completamento per escludere il **flusso
di chiusura stesso** (non ancora COMPLETATO al momento del check): cosi' si valuta
solo il resto del percorso obbligatorio.

---

### Note operative

* Consumata da [trgfn_flussi_autochiusura_pratica](trgfn_flussi_autochiusura_pratica.md)
  (decide se chiudere) e da [trgfn_flussi_guard_chiusura_prematura](trgfn_flussi_guard_chiusura_prematura.md)
  (decide se ammettere il completamento del flusso di chiusura).
* Funzione `STABLE`, pura: nessun effetto collaterale, nessun `RAISE`.
* Test: `db/pgtap/pratiche/test-autochiusura-pratica.sql`.

---
{% include-markdown "signature-core.md" %}
