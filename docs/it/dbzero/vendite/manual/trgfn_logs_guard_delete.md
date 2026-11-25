## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_logs_guard_delete`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
> Approfondimento funzioni:
>
> • [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset del lotto: la GUC e il proprietario  
> • [vendite.trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only) — il gemello su `event_log`  
> • [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — chi scrive la scadenza  
> • [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired) — chi la ritira  
> • [script.fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta) — la porta di manutenzione, solo per il migratore  
>
### 🎯 Scopo Principale
(rev 2026-09-18 — Passo D di `analisi-osservabilita-log.md`)  
La funzione trigger **`vendite.trgfn_logs_guard_delete()`** protegge i log funzionali
(`fatture_log`, `fatturazione_lotti_log`) dalla cancellazione **accidentale**,
distinguendo però fra **cancellare la storia** e **ritirare ciò che è scaduto**.

---

### Regole principali

* Trigger `BEFORE DELETE` su:
  * `vendite.fatture_log`
  * `vendite.fatturazione_lotti_log`
* `DELETE` **ammesso** in tre casi, in quest'ordine:
  1. la porta del **reset del lotto** è aperta
     ([fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta)): la
     GUC `zeroerp.maintenance_reset_lotto_draft` è accesa **e** chi cancella è il proprietario
     della tabella. La GUC la accende solo `vendite.fn_cleanup_fatture_by_ids`, riservata al
     proprietario, e la spegne prima di uscire. Per l'applicazione la GUC accesa non apre niente;
  2. **la riga è scaduta**: `cleanup_at IS NOT NULL AND cleanup_at <= now()` — è la
     retention che passa;
  3. la porta di **manutenzione** `zeroerp.maintenance_allow_delete_logs` è aperta, cioè
     accesa (`on`, `true` o `1`) da una sessione del migratore
     ([fn_porta_manutenzione_aperta](/dbzero/script/funzioni/fn_porta_manutenzione_aperta)).
     La riga cancellata resta nel diario delle porte. Per l'applicazione la GUC accesa non
     apre niente;
  — altrimenti la funzione solleva `E_DELETE_NOT_ALLOWED` (`NON_PERMESSO`) via
  `script.fn_log_and_raise_error`, con tabella, `id` e `cleanup_at` nel contesto.
* `cleanup_at` **NULL** = riga senza scadenza (nessuna regola `CLEANUP_AT` quando è nata):
  non si cancella. In dubbio si conserva.

---

### ⭐ Il criterio del ramo 2 non è *chi* cancella ma *cosa*

È la stessa scelta fatta su `event_log` (D-8, 2026-08-22): il purge settimanale
(`dbops.fn_purge_cleanup_expired`, lanciato da `fn_run_automations_cleanup`) cancella
**senza** propagare GUC né riconoscere ruoli, e il guard lo lascia passare perché la riga
ha passato la sua scadenza — non perché a cancellare sia il job.

Fino al 2026-09-18 il ramo della retention non c'era, e le due tabelle non avevano `cleanup_at`: era
la «mina latente» dichiarata in `test-cleanup-framework.sql` (13-16). Con la sola colonna
aggiunta, il job sarebbe stato respinto ogni domenica — dal 2026-08-23 l'orchestratore non
muore più, ma lascia una riga `ERROR` in `dbops.audit_log` (`BLOCKED_BY_TABLE`), per sempre.

---

### ⚠️ Qui `cleanup_at` non è immutabile, e va saputo

Su `event_log` il veto sull'`UPDATE` rende la scadenza immutabile. Queste due tabelle
l'`UPDATE` lo ammettono (`disabilitato`, `meta`, …): chi può scrivere può anche portare
`cleanup_at` nel passato e poi cancellare. Non è un buco nuovo — quelle righe erano già
modificabili, e il guard protegge dalla cancellazione **accidentale**, non dal dolo. Non si
è aggiunto un veto sull'`UPDATE` di `cleanup_at`: sarebbe un cancello nuovo su tabelle che
non sono append-only per progetto.

### ⚠️ Su `fatture_log` il purge ha una conseguenza

`trg_fatture_log_z90_sync_critical_ad` ricalcola `fatture.critical` (e `stato_esecuzione`
su `fatturazione_lotti_fatture`) dopo ogni `DELETE`. Il purge di una riga `status = 'C'`
non ancora `disabilitato` **spegne** il critico della fattura senza che nessuno l'abbia
ammesso. Con 750 giorni di termine è una fattura ferma da due chiusure annuali: la scelta è
che `critical` **deriva** dal registro e ne eredita la scadenza. Non si è aggiunta
un'eccezione «se è vivo non scade»: un rifiuto di riga dentro il batch del purge blocca
l'intera tabella per sempre, che è peggio.

---

### ⛔ Legge `OLD.cleanup_at`

Montare questo guard su una tabella **senza** la colonna fallisce a runtime — di proposito:
un guard con un ramo di retention sta su una tabella che ha una scadenza.

---

### Output

Nessun output funzionale (trigger guard: ritorna `OLD` in caso consentito).

---

### Verifica

* `db/pgtap/vendite/test-logs-guard-delete.sql` — la porta di manutenzione accesa
  dall'applicazione non apre, e la riga viva si rifiuta.
* `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — il ramo 2
  (riga scaduta) e la conseguenza su `critical`.
* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — la porta del reset accesa
  dall'applicazione non apre: una riga viva del log del lotto non si cancella.

---

### Note di migrazione

* 2026-09-18 — la riga scaduta passa (retention).
* 2026-11-17 — la porta di manutenzione passa da `script.fn_porta_manutenzione_aperta`: si
  apre solo alla sessione del migratore, e si chiede dopo la retention, così il diario
  registra solo le righe vive cancellate. La porta di verbo del reset del lotto resta com'è
  (`brief-db-seed-primo-impianto-non-si-riscrive`).
* 2026-11-25 — la porta del reset si legge da `vendite.fn_porta_reset_lotto_aperta` e chiede anche
  il proprietario; prima bastava la GUC, che l'applicazione poteva accendere da sé
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7).

---

{% include-markdown "signature-core.md" %}
