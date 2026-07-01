## 📘 Documentazione Funzione – `pratiche.fn_pratica_flussi_aperti`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.flussi](flussi.md)
> [pratiche.fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md)
> [pratiche.trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)
> [config.transizioni_stati_flussi_pratiche](/dbzero/config/tabelle/transizioni_stati_flussi_pratiche)

---
### 🎯 Scopo Principale

`fn_check_*` puro (no raise): elenca i **flussi ISTANZIATI** della pratica che sono
in stato **non terminale**, cioe' il **lavoro ancora pendente** (D1 —
brief-db-chiusura-pratica-nessun-lavoro-pendente).

Uno stato e' **terminale** in modo **data-driven**: non ha alcuna transizione di
stato in **uscita attiva** in `config.transizioni_stati_flussi_pratiche` — stessa
definizione auto-mantenuta del guard pratica-terminale. Sul grafo attuale i terminali
sono `COMPLETATO` e `ANNULLATO`; `ERRORE` **non** e' terminale (ha uscite) quindi un
flusso in errore risulta pendente e blocca la chiusura. Nessun `codice_interno`
cablato: se cambia il grafo stati, la nozione di terminale si adegua.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_pratica_flussi_aperti(
    p_pratica_id        pratiche.flussi.pratica_id%TYPE,
    p_escludi_flusso_id pratiche.flussi.id%TYPE DEFAULT NULL
)
RETURNS TABLE(
    flusso_id            pratiche.flussi.id%TYPE,
    template_flusso_id   pratiche.flussi.template_flusso_id%TYPE,
    codice               pratiche.template_flussi.codice%TYPE,
    stato_codice_interno config.stati_flussi_pratiche.codice_interno%TYPE
)
LANGUAGE sql STABLE
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_pratica_id` | SI | Pratica da valutare |
| `p_escludi_flusso_id` | NO | Istanza di flusso da ignorare |

`p_escludi_flusso_id` serve al guard pre-completamento: in `BEFORE UPDATE` il flusso
che sta completando e' ancora `IN_CORSO` (non terminale) e conterebbe **se stesso**;
escludendolo il check non blocca il proprio completamento.

---

### Note operative

* Fonte **unica** del predicato "flusso aperto", condivisa da
  [fn_check_pratica_chiudibile](fn_check_pratica_chiudibile.md) (auto-chiusura + guard
  pre-completamento) e da [trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)
  (chiusura manuale): manuale e auto usano cosi' la **stessa** definizione di "lavoro pendente".
* Complementare a `fn_check_chiusura_pratica` (che ragiona sui **template obbligatori**):
  questa ragiona sulle **istanze aperte** (anche opzionali).
* Funzione `STABLE`, pura: nessun effetto collaterale, nessun `RAISE`.
* Test: `db/pgtap/pratiche/test-chiusura-nessun-lavoro-pendente.sql`.

---
{% include-markdown "signature-core.md" %}
