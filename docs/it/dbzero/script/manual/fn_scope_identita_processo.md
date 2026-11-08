## 📘 Documentazione Concettuale – Funzione `script.fn_scope_identita_processo()`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Collegamenti utili**
>
Approfondimenti tabelle:
>
[`dbops.processi_identita`](/dbzero/dbops/manual/processi_identita)
>
Approfondimenti funzioni:
>
[`script.fn_is_super_admin`](/dbzero/script/manual/fn_is_super_admin) ·
[`script.fn_scope_ef_whitelist`](/dbzero/script/manual/fn_scope_ef_whitelist) ·
[`script.fn_get_auth_user_stato`](/dbzero/script/manual/fn_get_auth_user_stato)
>
Vista collegata:
> [`dbops.vw_processi_roster`](/dbzero/dbops/manual/vw_processi_roster)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Risponde a una domanda sola:

> **«Questa sessione è l'identità tecnica *viva* di quel processo?»**

Serve a chi deve decidere se una **macchina** può leggere qualcosa.

---

### ⛔ Perché nasce: due copie della stessa regola

La prima stesura della policy sulle email portava lo stesso controllo di dieci
righe **due volte** — una per la lettura, una per la scrittura.

⚠️ Altrove il progetto duplica anche, ma lì è **una chiamata**: due chiamate
identiche non possono divergere. Dieci righe sì.

⇒ Il giorno in cui qualcuno aggiunge una condizione a una sola delle due, chi
legge e chi scrive rispondono in modo diverso alla stessa domanda — e nessun
errore lo dice: ci si accorge da un permesso che c'era e non c'è più.

---

### ⭐ E la regola è più stretta di quella che sostituisce

Il controllo copiato guardava **un livello solo**: che il legame fra processo e
utente fosse acceso. Non basta.

| Livello | |
| --- | --- |
| il legame processo–utente | non è stato spento |
| il processo | è vivo: il ritiro non è raggiunto ([fn_e_obsoleto](/dbzero/script/funzioni/fn_e_obsoleto)) |
| l'identità applicativa | è **utilizzabile oggi** ([fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile): accesa, nelle sue date, soggetto attivo; dal 07-10-2026, prima bastava accesa). L'identità tecnica non ha rapporto e non lo pretende |
| il ruolo | è quello che le regole di sicurezza riconoscono |
| l'utente di accesso | non è stato revocato |

⛔ **Un'identità revocata avrebbe continuato a leggere i reset password** finché
qualcuno non toccava *anche* il legame. È la stessa lezione del roster: spegnerne
uno basta a fermare, quindi guardarne uno solo basta a sbagliare.

---

### ⚠️ Non c'è l'azienda, e non è una dimenticanza

Qui si chiede **«chi sei»**, non **«su quale azienda lavori»**.

⇒ Il perimetro aziendale lo dice
[`vw_processi_roster`](/dbzero/dbops/manual/vw_processi_roster), che è un'altra
domanda. Legarli qui toglierebbe la lettura delle email di **sistema**, che di
azienda non ne hanno.

---

### Dettagli che hanno una ragione

* **Con un parametro vuoto risponde «no».** Non per caso: il controllo
  semplicemente non trova niente. ⛔ Nessuna scorciatoia che restituirebbe
  «indeterminato» — che si comporterebbe come un no, ma per un'altra ragione.
* **L'utente di accesso si legge da una funzione**, mai da una vista: è la regola
  presa dopo che un collegamento diretto dentro una vista ha fermato la
  ricostruzione del database da zero.
* **È scritta per essere veloce**: una regola di sicurezza si valuta **riga per
  riga**, e in questa forma il database la può incorporare invece di chiamarla
  ogni volta.

---

### Dove si usa

Nella regola di sicurezza di `config.email_log`: le email di **sistema** le
leggono il super amministratore **e** l'identità tecnica di chi le spedisce.

> ⭐ Nel database **portare è leggere**: non esiste un modo di spedire una riga
> senza vederla. Senza questa autorizzazione la posta di sistema non partirebbe —
> e non lo direbbe a nessuno, perché una coda vuota è identica a «niente da fare».

⛔ Sulle **bozze** (`config.email_outbox`) lo stesso ramo è stato **ritirato**:
lì quel processo non entra mai, e un permesso che nessun codice esercita non si
può collaudare.

---

### Verifica

`db/pgtap/script/test-fn-scope-identita-processo.sql` — spegne i livelli uno alla
volta. ⭐ Il test sull'identità **revocata** è il caso che il controllo copiato
non prendeva: è la ragione per cui questa funzione esiste.

---

{% include-markdown "signature-core.md" %}
