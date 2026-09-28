## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_preventivi`

> 👀 **Vedi anche**
>
Approfondimento tabelle e viste:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [vw_preventivi_smistamento_righe](vw_preventivi_smistamento_righe.md) (vista canonica riusata)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
Resolver dell'area **PREVENTIVI** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per preventivo con
valore **imponibile** totale vs **transitato** (decisione D-4: senza IVA) e il
motivo del fermo. Read-time, nessun mirror.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Transito riga | Letto dalla vista canonica `vw_preventivi_smistamento_righe`: transitata = `stato_smistamento != 'RESIDUA'` (`A_ORDINE` / `IN_COMMESSA` / `EMESSA_AF` / `FATTURATA`; il ramo commessa richiede attività `EMESSA`) |
| Valore riga | `quantita × prezzo_unitario × (1 − sconto%/100)` — solo righe attive |
| Competenza | `COALESCE(competenza_mese, mese di validita_dal, mese di data)` — la `competenza_mese` scritta all'accettazione è autorevole quando esiste; i fallback sono gli stessi campi della policy di `fn_list_preventivi_da_pushare` |
| `is_abortito` | `esito = 'NEGATIVO'` da `config.stati_doc_preventivi` (D1 proiezione stato dominio) |
| `motivo_fermo` | `DOC_BOZZA` (DRAFT) · `IN_ATTESA_ACCETTAZIONE` (EMESSO) · `RIGA_RESIDUA` (accettato con residuo bi-ramo) |
| `cliente_display` | Ragione sociale intestatario istanza (`istanze_utilities → soggetti`, path `vw_preventivi_lista`), nullable |

---

### Esempio d'uso

```sql
-- Preventivi fermi di un mese di competenza.
SELECT codice, valore_totale, valore_transitato, unita_totali, unita_transitate, motivo_fermo
FROM vendite.vw_dash_fatturazione_preventivi
WHERE competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito AND NOT is_transitato;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_aperto_*` (layering).
* Un preventivo `ACCETTATO` può avere transito **parziale** e restare fermo con
  `RIGA_RESIDUA`: lo stato di testata da solo non basta (residuo bi-ramo, gate EVASO).
* RLS emittente applicata automaticamente (vista invoker su `vendite.preventivi`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

L'imponibile di riga (`valore_riga`) non è più scritto qui: viene da [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga), la sede unica della formula (`20260928-22`). Stesso valore — provato su una griglia di 252 casi e sui dati di dev — ma una regola sola: prezzo o quantità assenti danno **nessun valore**, mai zero; sconto assente è nessuno sconto; l'arrotondamento resta a chi consuma.

---

{% include-markdown "signature-core.md" %}
