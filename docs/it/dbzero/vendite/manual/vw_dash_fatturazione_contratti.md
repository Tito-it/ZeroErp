## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_contratti`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/funzioni/fn_list_contratti_da_pushare) (predicato gemello)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_fatturazione_mensile](vw_dash_fatturazione_mensile.md)

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
Resolver dell'area **CONTRATTI** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per **contratto vivo ×
mese coperto dalla validità**, **a conteggi** (decisione D-3: il canone mensile
atteso non è un campo pronto — v2). Risponde alla domanda operativa: *"per il mese
M, quali contratti non hanno ancora generato il canone?"*

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Mesi generati | `generate_series` da `valido_dal` fino a `LEAST(valido_al, mese corrente)` — **cap al mese corrente**: la domanda ha senso solo per mesi non futuri, e i contratti aperti (`valido_al NULL`) non esplodono |
| Transito nel mese M | `EXISTS` attività con sorgente `CONTRATTO` (`config.sorgenti.codice_interno`, mai id letterale), `sorgente_uid = uid::text`, `competenza_mese = M`, `stato_emissione = 'EMESSA'` |
| Contratti abortiti | Esclusi a monte (`esito = 'NEGATIVO'`, es. ANNULLATO): per quest'area `n_abortiti = 0` in v1 |
| `motivo_fermo` | `DOC_BOZZA` (DRAFT) · `CANONE_NON_GENERATO` |

---

### Esempio d'uso

```sql
-- Contratti senza canone generato per il mese corrente.
SELECT codice, stato_codice
FROM vendite.vw_dash_fatturazione_contratti
WHERE competenza_mese = date_trunc('month', CURRENT_DATE)::date
  AND motivo_fermo = 'CANONE_NON_GENERATO';
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_fatturazione_mensile` (layering).
* ⚠️ **Push ricorrente non ancora esistente**: oggi `fn_list_contratti_da_pushare`
  ancora il canone al **mese di inizio validità** (`segment_key
  'CONTR:<uid>:R:<riga>:M:YYYY-MM'`, nessuna iterazione mensile). Nei mesi successivi
  i contratti attivi appariranno `CANONE_NON_GENERATO`: è la **realtà operativa**,
  la dashboard non la maschera. Il predicato su `sorgente_* + competenza_mese` è già
  pronto per il futuro push ricorrente.
* L'`EXISTS` è assistito da `ix_commesse_attivita_sorgente_competenza`
  (90_end `20260703-58`).
* RLS emittente applicata automaticamente (vista invoker su `vendite.contratti`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
