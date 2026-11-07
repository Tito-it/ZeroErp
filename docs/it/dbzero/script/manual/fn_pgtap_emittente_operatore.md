## 📘 Documentazione Concettuale – Funzione `script.fn_pgtap_emittente_operatore()`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) — la sede a cui delega
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — la regola di produzione
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto da aprire prima
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---

### 🎯 Scopo Principale

Restituisce l'**emittente fiscale su cui l'operatore del contesto può scrivere**.

⭐ Serve a una regola precisa del template pgTAP: **l'emittente non si pesca, si deriva**. Un
documento appartiene all'emittente di chi agisce, e le policy `ef_whitelist` lo pretendono.

---

### ⭐ Una sede sola: l'azienda di chi agisce

La risposta è quella di
[dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce),
che la risolve con la regola di produzione
[script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user):
l'azienda scelta in alto (`app.current_emittente_id`) se l'utente la può usare, altrimenti
quella assegnata. È la stessa risposta del trigger che lega il cliente all'azienda di chi
agisce. La funzione non ricopia la regola: la chiede.

---

### ⛔ Non sceglie un'azienda al posto di chi agisce

Senza un contesto aperto, con un utente che non ha un'azienda su cui scrivere, o senza
un'identità operatore attiva, **solleva**, nominando questa funzione. Un emittente scelto al
posto di chi agisce sarebbe un'azienda su cui chi agisce non può né leggere né scrivere: il
test fallirebbe più avanti, per un motivo che non è il suo.

⚠️ Scriverlo con `SELECT id FROM emittenti_fiscali ORDER BY id LIMIT 1` funziona **finché c'è
un solo emittente con documenti**, e smette di funzionare senza preavviso quando ne nasce un
secondo.

---

### Test

* `db/pgtap/script/test-fn-pgtap-emittente-operatore-v1.sql` — senza contesto solleva; col
  contesto risponde come `dbops.fn_pgtap_azienda_di_chi_agisce`; un utente di contesto senza
  azienda solleva.
* La usano come fixture molti test che scrivono documenti dell'azienda di chi agisce.

---

### Note di migrazione

* 2026-08-21 — nasce, al posto dell'emittente pescato con `LIMIT 1`.
* 2026-10-21 — con un contesto aperto risponde la regola di produzione.
* 2026-11-08 — delega all'azienda di chi agisce: i ripieghi sull'emittente di un operatore
  qualunque e sul primo emittente attivo sono ritirati, e senza un'azienda solleva.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
