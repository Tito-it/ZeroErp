## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_aperto_riepilogo`

> 👀 **Vedi anche**
>
[vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)
> [vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)

---
### 🎯 Scopo Principale
(latest review 08-07-2026 — v2 serbatoio pre-commessa, DL-14..18)
Le **card della Situazione aperta v2**: aggregata `area × fase` sullo stock
degli **aperti-non-conclusi** (`vw_dash_aperto_documenti` v2). Alimenta le card
senza aggregazione BE-side (DB-first). Le fasi presenti sono solo
APERTO/IN_ATTESA/IN_CORSO (CHIUSO escluso a monte dalla dettaglio) → il FE le
rappresenta con un **donut a spicchi per fase** (maturità verso la commessa).

---

### Semantica

| Colonna | Regola |
|---------|--------|
| `n_documenti` | Documenti della cella (nel perimetro v2 sono **tutti** aperti) |
| `valore_totale` | Somma **senza COALESCE**: resta `NULL` per le aree a conteggi OFFERTE/CONTRATTI (DL-11 — `NULL` = misura non disponibile, `0` mentirebbe) |

Colonne **rimosse** rispetto alla v1 (DL-14): `n_aperti` (ridondante — nel
perimetro v2 coincide con `n_documenti`) e `valore_transitato` (concetto
transito eliminato). Scope emittente ereditato (invoker su tutta la catena).

---

### Esempio d'uso

```sql
-- Le card: stock aperti-non-conclusi per area e fase.
SELECT area, fase, n_documenti, valore_totale
FROM vendite.vw_dash_aperto_riepilogo
ORDER BY area, fase;
```

---

### Note operative

* Nessun asse temporale: la domanda "il mese M è completo?" è della **Lente 1**
  (`vw_dash_competenza_mensile`); "cosa è fermo e da quanto?" è della
  **Lente 2** (`vw_dash_backlog_*`). Qui: "com'è messa la pipeline, adesso?".
* Ricreata con **DROP + CREATE** (`20260708-04`) dopo la dettaglio (`20260708-03`
  la droppa prima per sciogliere la dipendenza): `CREATE OR REPLACE` non può
  rimuovere colonne.
* Test: `db/pgtap/vendite/test-vw-dash-aperto-v1.sql`.

---

{% include-markdown "signature-core.md" %}
