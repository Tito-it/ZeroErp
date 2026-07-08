## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_backlog_riepilogo`

> 👀 **Vedi anche**
>
[vw_dash_backlog_documenti](vw_dash_backlog_documenti.md)
> [config.motivi_fermo](/dbzero/config/tabelle/motivi_fermo)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Contatori di testata della pagina **Backlog** (Lente 2): `🟠 n · 🔵 n · 🔴 n`
per classe × area (il 🟢 FISIOLOGICO è già escluso a monte da
`vw_dash_backlog_documenti`). Grana: una riga per `classe × area` con
`n_documenti`, `valore_fermo_tot` (0 per le aree a conteggi),
`unita_ferme_tot`, `anzianita_max_giorni`.

---

### Esempio d'uso

```sql
-- I contatori in cima alla pagina backlog.
SELECT classe, sum(n_documenti) AS n
FROM vendite.vw_dash_backlog_riepilogo
GROUP BY classe;
```

---

### Note operative

* Deriva interamente da `vw_dash_backlog_documenti`: stesse regole di
  classificazione, scope e fail-visible.
* Test: `db/pgtap/vendite/test-vw-dash-backlog-v1.sql` (coerenza
  riepilogo/dettaglio).

---

{% include-markdown "signature-core.md" %}
