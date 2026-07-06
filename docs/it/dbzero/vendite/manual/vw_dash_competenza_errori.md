## 📘 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_errori`

> 👀 **Vedi anche**
>
[vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)
> [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)
> [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)
> [vw_dash_competenza_attivita](vw_dash_competenza_attivita.md)

---
### 🎯 Scopo Principale
(latest review 06-07-2026)
Blocco **errori** della Lente 1 Competenza (blocco 4 del design, assorbe §12.3
del brief pre-fatturazione): gli eventi di errore **vivi** della pipeline di
fatturazione, per mese di competenza — dal cruscotto si vede subito se c'è un
lotto o una fattura inceppati, senza andare a caccia nei log.

---

### Semantica

| `tipo_evento` | Popolazione | Competenza |
|---------------|-------------|------------|
| `TASK_ERRORE` | Run di `fatturazione_lotti_task_runs` con `task_stato = 'ERRORE'` e `attivo`, **non superato** da un run `COMPLETATO` successivo sulla stessa chiave (lotto, step, task): un retry riuscito spegne l'errore | `fatturazione_lotti.competenza_mese` |
| `FATTURA_CRITICA` | `fatture.critical IS TRUE` (flag sincronizzato dai trigger su `fatture_log`); `messaggio` = ultimo log non disabilitato | Regola DB-7 in cascata: mese del **lotto** collegato → mesi **distinti** delle AF collegate (una riga per mese) → fallback mese della **data fattura** |

Scope emittente in-vista da GUC (fail-closed), `security_invoker = on`.

---

### Esempio d'uso

```sql
-- C'e' qualcosa di inceppato che tocca la competenza di maggio?
SELECT tipo_evento, lotto_codice, fattura_id, error_code, messaggio, data_evento
FROM vendite.vw_dash_competenza_errori
WHERE competenza_mese = DATE '2026-05-01'
ORDER BY data_evento DESC;
```

---

### Note operative

* Un errore si "spegne" da solo: retry `COMPLETATO` per i task,
  `critical = false` (risoluzione/disabilitazione log) per le fatture.
* Una fattura critica multi-mese (AF di competenze diverse, senza lotto)
  produce **una riga per mese**: ogni mese interessato vede il suo problema.
* ⚠️ Fail-closed: senza GUC operatore restituisce 0 righe.
* Test: `db/pgtap/vendite/test-vw-dash-competenza-v1.sql`.

---

{% include-markdown "signature-core.md" %}
