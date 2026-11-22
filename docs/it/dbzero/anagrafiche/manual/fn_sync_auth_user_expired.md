## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_expired`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti di cui si giudica la validità
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto che l'operatore umano pretende
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) — la funzione che decide e scrive, una credenziale per volta
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola con cui si scelgono i candidati
> * [maintenance.proc_sync_auth_user_expired_job](/dbzero/maintenance/funzioni/proc_sync_auth_user_expired_job) — la procedura del job che la chiama
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login

---

### 🎯 Scopo Principale

`anagrafiche.fn_sync_auth_user_expired` riallinea, nei due versi, `django.auth_user.is_active` di ogni credenziale
che ha delle vesti e il cui flag non dice più se una di esse è utilizzabile oggi. Restituisce quante credenziali ha
riallineato, spente o accese.

---

### Copre ciò che nessuna scrittura annuncia

I trigger di sincronizzazione reagiscono alle scritture. Il tempo non scrive: una veste che scade, un rapporto che
finisce, una veste che comincia oggi cambiano la risposta della regola senza che nessuno tocchi una riga. Ci sono
poi le scritture che nessun trigger guarda (una veste che cambia credenziale, un rapporto che nasce dopo la veste).
Questa funzione ripara tutte e due le cose, perché non guarda che cosa è cambiato: confronta il flag con la regola.

---

### Una domanda sola, nei due versi

I candidati sono le credenziali che hanno **almeno una veste** e il cui `is_active` è diverso dalla risposta
«esiste una veste utilizzabile oggi?», chiesta a `script.fn_veste_utilizzabile`, la stessa regola che poi decide.
Così il passaggio spegne la credenziale accesa che non ha più vesti utilizzabili e accende quella spenta che ne ha
una diventata valida.

Per ogni candidato chiama `fn_sync_auth_user_is_active`, che ricalcola e scrive; il ritorno conta solo le
credenziali che questa ha davvero cambiato. Una seconda chiamata subito dopo restituisce zero.

---

### ⛔ Una credenziale senza vesti resta fuori

Una credenziale senza nessuna veste non è un candidato, accesa o spenta che sia: la funzione non la tocca. Chi la
vede è il presidio `dbops.vw_credenziali_da_sanare`, col motivo `NESSUNA_VESTE`.

---

### Chi la chiama

* Il job pgAgent `sync_auth_user_expired_daily`, attraverso `maintenance.proc_sync_auth_user_expired_job`, che lascia
  la corsa nel giornale dei job. La sveglia è **oraria, al minuto 10**, e il job parte solo se la sua sveglia è
  accesa. Il nome dice «daily» e resta.
* Il comando di gestione del backend `sync_auth_user_active`, a mano, che dopo il riallineamento invalida la cache
  dei permessi delle credenziali toccate.

Dove lo schema Django non c'è (un database di sola integrazione continua) la funzione esce subito e restituisce
zero.

---

{% include-markdown "it/dbzero/anagrafiche/_sincronizzazione-accesso.md" %}

---

### ⚠️ Che cosa oggi non copre

* **La credenziale rimasta senza vesti.** Una veste passata a un'altra credenziale, o cancellata, lascia la
  credenziale di prima com'era; se era la sua ultima veste, questa funzione non la riallinea, per la regola qui
  sopra.

---

### Codici errore

La funzione non ne solleva di suoi.

---

### Test

* `db/pgtap/anagrafiche/test-super-admin-senza-scadenza-v1.sql` (casi 14-16) — accende la credenziale la cui veste
  diventa valida oggi senza che nessuno scriva, spegne quella con la veste scaduta, e il ritorno conta tutte e due.
* `db/pgtap/script/test-fn-veste-utilizzabile-v1.sql` (caso 24) — spegne la credenziale accesa il cui operatore ha il
  rapporto scaduto.

Nessun test prova che una credenziale senza vesti resti fuori, né che una seconda chiamata restituisca zero.

---

### Note di migrazione

* 2026-09-12 — cade il ramo che leggeva il rapporto attraverso la vista `risorse_umane_auth_user`, ritirata.
* 2026-10-07 — i candidati si scelgono con `script.fn_veste_utilizzabile`, che guarda anche il rapporto
  dell'operatore umano; e il passaggio, che fino ad allora solo spegneva, anche accende. Una credenziale con l'unica
  veste a inizio futuro restava spenta anche il giorno in cui la veste diventava valida. Il nome resta perché lo
  chiamano il job, il comando e il backend.
* 2026-10-09 — la sveglia del job passa da una volta al giorno a una volta all'ora.

---

{% include-markdown "signature-core.md" %}
