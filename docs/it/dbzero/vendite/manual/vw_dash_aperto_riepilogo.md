## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_aperto_riepilogo`

> 👀 **Vedi anche**
>
[vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)
> [vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)

---
### 🎯 Scopo Principale
(latest review 07-07-2026)
Le **card della Situazione aperta**: aggregata `area × fase` sullo stock
documenti (`vw_dash_aperto_documenti`: 4 aree, no abortiti, tutte le fasi —
DL-13). Alimenta le card senza aggregazione BE-side (DB-first).

---

### Semantica

| Colonna | Regola |
|---------|--------|
| `n_documenti` | Documenti vivi della cella |
| `n_aperti` | Con transito non-true (`is_aperto`); per i CONTRATTI (giudizio sospeso, DL-12) coincide col totale |
| `valore_totale` / `valore_transitato` | Somme **senza COALESCE**: restano `NULL` per le aree a conteggi OFFERTE/CONTRATTI (DL-11 — `NULL` = misura non disponibile, `0` mentirebbe) |

Scope emittente ereditato (invoker su tutta la catena).

---

### Esempio d'uso

```sql
-- Le card: stock per area e fase (il FE sceglie quali fasi mostrare).
SELECT area, fase, n_documenti, n_aperti, valore_totale
FROM vendite.vw_dash_aperto_riepilogo
ORDER BY area, fase;
```

---

### Note operative

* Nessun asse temporale: la domanda "il mese M è completo?" è della **Lente 1**
  (`vw_dash_competenza_mensile`); "cosa è fermo e da quanto?" è della
  **Lente 2** (`vw_dash_backlog_*`). Qui: "com'è messa la pipeline, adesso?".
* La fase `CHIUSO` è inclusa e cresce nel tempo (DL-13): il FE tipicamente
  non la mostra o la mostra a parte.
* Test: `db/pgtap/vendite/test-vw-dash-aperto-v1.sql`.

---

{% include-markdown "signature-core.md" %}
