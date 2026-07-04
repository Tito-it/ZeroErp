## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_mensile`

> 👀 **Vedi anche**
>
Fonte e brief:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md) (contratto colonne, vocabolario motivi, semantica)
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-dashboard-fatturazione.md`

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
`vendite.vw_dash_fatturazione_mensile` è l'aggregata **area × mese di competenza**
della Dashboard Fatturazione: la vista letta dall'endpoint
`GET /api/v1/vendite/dashboard-fatturazione/?anno=` (matrice 12 mesi × 5 aree).
Quando `valore_totale = valore_transitato` e `n_fermi = 0` il mese è a posto per
quell'area.

---

### 📑 Campi chiave esposti

| Campo | Significato |
|-------|-------------|
| `area`, `competenza_mese` | Chiave di aggregazione (1° del mese) |
| `valore_totale` / `valore_transitato` | Somme in euro imponibile dei soli documenti **vivi**; NULL per le aree a conteggi (OFFERTE, CONTRATTI in v1) |
| `n_documenti` / `n_transitati` / `n_fermi` | Conteggi sui soli documenti vivi |
| `n_abortiti` | Documenti con esito `NEGATIVO`, contati a parte (fuori dal confronto; per CONTRATTI sempre 0 in v1: gli annullati sono esclusi a monte dal resolver) |

---

### Esempio d'uso

```sql
-- Matrice dell'anno 2026 (i mesi vuoti li genera il BE con generate_series).
SELECT area, competenza_mese, valore_totale, valore_transitato,
       n_documenti, n_transitati, n_fermi, n_abortiti
FROM vendite.vw_dash_fatturazione_mensile
WHERE competenza_mese >= DATE '2026-01-01'
  AND competenza_mese <  DATE '2027-01-01'
ORDER BY competenza_mese, area;
```

---

### Note operative

* I mesi senza documenti **non** compaiono: è il backend a generare sempre i 12 mesi
  dell'anno richiesto con zeri (contratto API, decisione D-5).
* Le righe **COMMESSE** sono **scope-aware**: il resolver
  `vw_dash_fatturazione_commesse` filtra per emittente da GUC, quindi anche
  l'aggregata mensile rispetta lo scope dell'operatore (card e drill-down
  concordano). Le altre 4 aree sono filtrate dalla RLS. Senza GUC operatore la
  sezione commesse dell'aggregata è vuota (fail-closed, vedi scheda commesse).
* Il contratto colonne è pensato per reggere una futura **materializzazione**
  (snapshot notturno) senza cambiare l'interfaccia verso il backend.
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
