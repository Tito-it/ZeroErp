## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_ordini`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) (predicato gemello)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_aperto_documenti](vw_dash_aperto_documenti.md)

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
Resolver dell'area **ORDINI** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per ordine con valore
**imponibile** totale vs **transitato a commessa** e il motivo del fermo.
Read-time, nessun mirror.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Transito riga | `EXISTS` attività con `segment_key = 'ORD:<uid>:R:<riga_id>'` e `stato_emissione = 'EMESSA'` — lo **stesso** `NOT EXISTS` che rende la riga non più eligible in `fn_list_ordini_da_pushare` (attività `NON_EMESSA` = riga ancora ferma, ri-pushabile) |
| Valore riga | `quantita × prezzo_unitario × (1 − sconto%/100)` — solo righe attive |
| Competenza | Mese di `ordini.data` (l'ordine non ha competenza nativa; quella puntuale nasce sulla commessa) |
| `is_abortito` | `esito = 'NEGATIVO'` da `config.stati_doc_ordini` |
| `motivo_fermo` | `DOC_BOZZA` (DRAFT) · `PUSH_NON_ESEGUITO` (confermato, 0 righe transitate) · `PUSH_PARZIALE` |
| `cliente_display` | Ragione sociale del `soggetto_ruolo_id` (path `vw_ordini_lista`), nullable |

---

### Esempio d'uso

```sql
-- Ordini con push a commessa assente o parziale nel mese.
SELECT codice, valore_totale, valore_transitato, motivo_fermo, stato_codice
FROM vendite.vw_dash_fatturazione_ordini
WHERE competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito AND NOT is_transitato;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_aperto_*` (layering).
* L'`EXISTS` su `segment_key` è assistito da `ix_commesse_attivita_segment_key`
  (90_end `20260703-58`): l'UNIQUE esistente ha `commessa_id` in testa e non serve
  il lookup puntuale.
* `EVASO` scatta solo a push completo: un ordine `CONFERMATO` con push parziale è
  il caso `PUSH_PARZIALE`.
* RLS emittente applicata automaticamente (vista invoker su `vendite.ordini`).
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
