## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_fatturazione_commesse`

> 👀 **Vedi anche**
>
Approfondimento tabelle e funzioni:
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
>
Union e aggregata:
>
[vw_dash_fatturazione_documenti](vw_dash_fatturazione_documenti.md)
> [vw_dash_fatturazione_mensile](vw_dash_fatturazione_mensile.md)

---
### 🎯 Scopo Principale
(latest review 03-07-2026)
Resolver dell'area **COMMESSE** per la Dashboard Fatturazione
(brief-design-dashboard-fatturazione §5, Fase 1): una riga per **commessa ×
`competenza_mese`** delle attività (la competenza "vera" del funnel, la stessa che
perimetra i lotti): valore **imponibile** totale vs **transitato** (attività emesse
in `attivita_fatturabili`). È il tratto finale pre-fattura.

---

### Semantica

| Aspetto | Regola |
|---------|--------|
| Valore | `Σ prezzo_snapshot × quantita` per `competenza_mese`; transitato = filtro `stato_emissione = 'EMESSA'`. `'EMESSA'`/`'NON_EMESSA'` sono enum CHECK di colonna (literale ammesso §6d, stessi literali delle fn di dominio) |
| `is_abortito` | Commessa `ANNULLATA` (`stati_commessa.codice_interno`) — le commesse non hanno la proiezione fase/esito D1 → `fase` NULL |
| `motivo_fermo` | `ATTIVITA_NON_APPROVATA` (esistono ferme non ancora `APPROVATA`: collo di bottiglia = approvazione) · `ATTIVITA_NON_EMESSA` (tutte approvate, manca l'emissione) |
| Commesse senza attività | Non compaiono (nessun valore, nessun mese) |

---

### Esempio d'uso

```sql
-- Colli di bottiglia del mese: dove il valore e' fermo e perche'.
SELECT codice, valore_totale - valore_transitato AS valore_fermo, motivo_fermo
FROM vendite.vw_dash_fatturazione_commesse
WHERE competenza_mese = DATE '2026-05-01'
  AND NOT is_abortito AND NOT is_transitato
ORDER BY valore_fermo DESC;
```

---

### Note operative

* **Non interrogarla dal BE**: il backend passa da
  `vw_dash_fatturazione_documenti` / `vw_dash_fatturazione_mensile` (layering).
* Il drill-down mostra il secondo livello (fatturata =
  `attivita_fatturabili.fattura_riga_id IS NOT NULL`) solo come informazione: il
  transito dell'area è l'**emissione** in `attivita_fatturabili`.
* Le commesse **non sono in RLS**: la vista espone `emittente_soggetto_ruolo_id`
  per l'eventuale filtro applicativo lato BE (`emittente_fiscale_id` è NULL).
* Una riga sorgente parcheggiata in commessa `NON_EMESSA` risulta ferma **anche**
  nell'area sorgente (predicato canonico EMESSA): coerente, il valore non è avanzato.
* Test: `db/pgtap/vendite/test-vw-dash-fatturazione-v1.sql`.

---

{% include-markdown "signature-core.md" %}
