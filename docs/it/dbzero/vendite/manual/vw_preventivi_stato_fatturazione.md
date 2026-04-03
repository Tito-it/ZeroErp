## 📘 Documentazione Concettuale – Viste `vendite.vw_preventivi_stato_fatturazione_righe` e `vw_preventivi_stato_fatturazione`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
Due viste complementari per il **monitoraggio della pipeline fatturazione** dei preventivi:

1. **`vw_preventivi_stato_fatturazione_righe`**: dettaglio per riga — ogni riga preventivo
   con il suo stato nella pipeline (commessa, AF, fatturata).
2. **`vw_preventivi_stato_fatturazione`**: aggregato per preventivo — conteggi per badge UI.

---

### Vista dettaglio: `vw_preventivi_stato_fatturazione_righe`

**JOIN principali:**
* `vendite.commesse_attivita` via `segment_key = 'PREV:{uid}:R:{riga_id}'`
* `vendite.attivita_fatturabili` via `sorgente_uid = preventivo.uid` + `sorgente_riga = riga.id`

**Flag esposti:**

| Campo | Tipo | Significato |
|-------|------|-------------|
| `in_commessa` | boolean | Record presente in commesse_attivita |
| `stato_approvazione` | varchar | Stato approvazione dell'attivita' in commessa |
| `stato_emissione` | varchar | Stato emissione (EMESSA/NON_EMESSA) |
| `emessa_af` | boolean | Record presente in attivita_fatturabili |
| `fatturata` | boolean | fattura_riga_id IS NOT NULL |

---

### Vista aggregata: `vw_preventivi_stato_fatturazione`

| Campo | Descrizione |
|-------|-------------|
| `righe_totali` | Numero righe attive del preventivo |
| `righe_in_commessa` | Righe gia' inviate in commessa |
| `righe_emesse_af` | Righe emesse come attivita' fatturabili |
| `righe_fatturate` | Righe con fattura generata |

Utile per badge UI: "3/5 fatturate", "tutte in commessa", ecc.

---

### Esempio d'uso

```sql
-- Badge aggregato per lista preventivi
SELECT preventivo_numero, righe_totali, righe_in_commessa, righe_fatturate
FROM vendite.vw_preventivi_stato_fatturazione
WHERE preventivo_id = 42;

-- Dettaglio per riga (drawer/modale)
SELECT riga_id, articolo_id, in_commessa, emessa_af, fatturata
FROM vendite.vw_preventivi_stato_fatturazione_righe
WHERE preventivo_id = 42;
```

---

{% include-markdown "signature-core.md" %}
