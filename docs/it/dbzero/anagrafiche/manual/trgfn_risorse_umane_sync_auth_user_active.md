## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_risorse_umane_sync_auth_user_active`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto su cui il trigger scatta
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste da cui si risale alla credenziale
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) — la funzione a cui delega
> * [script.fn_get_auth_user_id_for_risorsa_umana](/dbzero/script/funzioni/fn_get_auth_user_id_for_risorsa_umana) — dalla risorsa umana alla credenziale
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola, che per l'operatore umano guarda anche il rapporto
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — il gemello sulle vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_risorse_umane_sync_auth_user_active` riallinea `django.auth_user.is_active` dell'operatore quando
il suo rapporto, la risorsa umana, si accende, si spegne o cambia le date.

---

### Il rapporto conta per l'operatore umano

La veste di un operatore umano è utilizzabile solo se lo è anche il suo rapporto: la risorsa umana dello stesso
ruolo del soggetto, accesa e nelle sue date. Chiudere il rapporto, o spostarne l'inizio a domani, cambia quindi la
risposta della regola anche se la veste non si tocca, e questo trigger lo fa sapere alla credenziale.

---

### Scatta solo se cambia davvero

Il trigger scatta dopo una modifica della risorsa umana in cui `attivo`, `valido_dal` o `valido_al` hanno un valore
diverso da prima. Una modifica che riscrive gli stessi valori, o che tocca altre colonne, non lo fa scattare.

---

### Dalla risorsa umana alla credenziale

Il trigger cerca la credenziale con `script.fn_get_auth_user_id_for_risorsa_umana`: la veste `OPERATORE` dello stesso
ruolo del soggetto, l'accesa prima e, fra le altre, la più recente. Se la risorsa umana non ha nessuna veste
operatore non c'è niente da allineare, e il trigger esce senza fare nulla. Il calcolo lo fa
`fn_sync_auth_user_is_active`, sull'insieme delle vesti della credenziale: un operatore che ha anche una veste del
portale resta acceso, se quella è utilizzabile.

Basta una credenziale: il ruolo di un soggetto ha al più una veste operatore accesa, e una veste spenta non diventa
utilizzabile per un cambio del rapporto.

---

### ⚠️ Che cosa oggi non copre

* **Il rapporto che cambia ruolo del soggetto.** `soggetto_ruolo_id` non è fra le colonne del trigger: la risorsa
  umana che passa a un altro ruolo lascia com'erano le credenziali di tutti e due.
* **Il rapporto che nasce.** Il trigger non scatta sull'inserimento: una risorsa umana creata dopo la veste
  dell'operatore la rende utilizzabile senza che la credenziale lo sappia.

In tutti e due i casi la credenziale ha delle vesti, e la riallinea il passaggio periodico entro l'ora.

---

{% include-markdown "it/dbzero/anagrafiche/_sincronizzazione-accesso.md" %}

---

### Codici errore

Il trigger non ne solleva di suoi: la funzione a cui delega riceve sempre una credenziale.

---

### Test

* `db/pgtap/anagrafiche/test-risorse-umane-guard-identita-attiva-v1.sql` (caso 7) — spegnere il rapporto spegne la
  credenziale dell'operatore.

Nessun test prova il cambio delle date del rapporto attraverso il trigger, né l'operatore che resta acceso per
un'altra veste.

---

### Note di migrazione

* 2026-04-18 — il trigger risolve la credenziale prima di chiamare la sincronizzazione, che da quel giorno riceve
  una credenziale e non più una risorsa umana.
* 2026-09-12 — la credenziale si risolve dalle vesti, con `script.fn_get_auth_user_id_for_risorsa_umana`: la vista
  `risorse_umane_auth_user` è ritirata.

---

{% include-markdown "signature-core.md" %}
