## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_aperto_documenti`

> 👀 **Vedi anche**
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_riepilogo](vw_dash_aperto_riepilogo.md)
> [vw_dash_competenza_attivita](vw_dash_competenza_attivita.md) (Lente 1)
> [vw_dash_backlog_documenti](vw_dash_backlog_documenti.md) (Lente 2)

---
### 🎯 Scopo Principale
(latest review 07-07-2026)
Vista dettaglio della **Situazione aperta** (Fase 3 due lenti, trasformazione
della dashboard 5-card): lo **stock dei documenti vivi** delle 4 aree documento
(PREVENTIVI, ORDINI, OFFERTE, CONTRATTI), **senza asse temporale** — è la vista
di consistenza della pipeline, 🟢 fisiologici **inclusi** (a differenza del
Backlog che tiene solo il non-verde).

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| **Perimetro** | union `WHERE area <> 'COMMESSE' AND NOT is_abortito`. Le COMMESSE sono coperte dalla Lente 1 Competenza. Gli abortiti (esito NEGATIVO) si escludono **qui**: i resolver preventivi/ordini/offerte non li escludono alla fonte, li marcano soltanto (`is_abortito`) |
| **Tutte le fasi (DL-13)** | Anche `CHIUSO` è nello stock (cresce nel tempo): la vista è consultazione neutra, **il FE decide quali card mostrare** |
| `is_aperto` | `is_transitato IS DISTINCT FROM true` — include il **giudizio sospeso** dei contratti (`is_transitato NULL`, DL-12) |
| Valori | Da resolver: € per PREVENTIVI/ORDINI, `NULL` per OFFERTE/CONTRATTI (aree a conteggi) |
| Scope | `security_invoker = on` → RLS emittente delle 4 aree sul chiamante |

---

### Esempio d'uso

```sql
-- Drill-down di una card: i preventivi aperti in fase IN_ATTESA.
SELECT codice, cliente_display, stato_codice, motivo_fermo, data_riferimento
FROM vendite.vw_dash_aperto_documenti
WHERE area = 'PREVENTIVI' AND fase = 'IN_ATTESA' AND is_aperto;
```

---

### Note operative

* È il **perimetro unico** di card (`vw_dash_aperto_riepilogo`) e drill-down:
  il BE non deve replicare filtri.
* Sostituisce (con la gemella riepilogo) l'impianto mensile della 5-card:
  `vw_dash_fatturazione_mensile` è stata **dismessa** (`20260707-06`).
* `fase` è sempre valorizzata sulle 4 aree (join `config.stati_doc_*`).
* Test: `db/pgtap/vendite/test-vw-dash-aperto-v1.sql`.

---

{% include-markdown "signature-core.md" %}
