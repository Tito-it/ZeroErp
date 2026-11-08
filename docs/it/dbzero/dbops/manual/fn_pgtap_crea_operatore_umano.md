## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_operatore_umano`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — la veste OPERATORE, che la fixture accende
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — la risorsa umana dietro l'operatore
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2) — la madre di produzione che costruisce l'operatore
> * [anagrafiche.fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste) — il building block che accende la veste, come l'invito accettato
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — per legare l'operatore a un'azienda, dopo
> * [dbops.fn_pgtap_cf_libero](/dbzero/dbops/funzioni/fn_pgtap_cf_libero) — il codice fiscale libero
> * [dbops.fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio) — l'indirizzo di residenza
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'alternativa: un utente tecnico legato alla sua azienda
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — «un super admin non ha un'azienda»

---

### 🎯 Scopo Principale

Costruisce per un test un **operatore umano** — persona fisica, risorsa umana, credenziale,
veste OPERATORE attiva — dal percorso di produzione, volendo super admin. Restituisce
credenziale, identità, risorsa umana, soggetto ruolo e soggetto.

---

### ⭐ Dal percorso di produzione

L'operatore lo costruisce la madre di produzione
[fn_crea_operatore_v2](/dbzero/anagrafiche/funzioni/fn_crea_operatore_v2), con la
qualifica di dipendente. La fixture aggiunge solo ciò che un test non sceglie bene da sé:

* un codice fiscale libero adesso, chiesto una volta sola subito prima di scriverlo, e da lui
  lo username e l'email, quindi la credenziale è sempre nuova;
* il sesso, che per un privato è obbligatorio e la madre non sceglie più;
* un indirizzo di residenza, dall'etichetta del test;
* una password che non serve a entrare: una fixture non fa login.

---

### ⭐ L'invito accettato

La madre crea la veste OPERATORE **spenta**: in esercizio la accende il backend quando
l'operatore consuma l'invito. La fixture promette un operatore pronto a lavorare, quindi fa
lei quel passo, con il building block
[fn_accendi_veste](/dbzero/anagrafiche/funzioni/fn_accendi_veste). Poi verifica il
risultato: se non trova un'identità OPERATORE attiva con la sua risorsa umana solleva,
invece di tornare una riga con un vuoto dentro.

---

### ⚠️ Nasce senza azienda

Come in produzione, l'operatore non è legato a nessuna azienda. Per un super admin è il caso
normale: lavora su più aziende, e toglierla dopo non si potrebbe. Per legarlo a un'azienda si
usa [fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope).

È la differenza con [fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore),
che costruisce un utente tecnico già legato alla sua azienda: quando il soggetto del test è
l'operatore umano (la natura tecnica, i profili di accesso, il super admin) si usa questa.

---

### ⚠️ La finestra differita, il contesto e la fotografia

* La madre scrive il soggetto persona fisica e solo all'ultimo passo i suoi indirizzi; il
  guard degli indirizzi è differito, e col preambolo dei pgTAP scatterebbe sul soggetto
  ancora nudo. La fixture apre la finestra intorno alla madre e la richiude subito dopo: esce
  con i vincoli immediati.
* Non apre il contesto dell'operatore: lo fa il test.
* ⛔ Ciò che scrive si legge in un'**istruzione separata**: un join, o una funzione stabile
  come [fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin), nella stessa
  istruzione della chiamata vede la fotografia di prima.

---

### Codici errore

Valgono quelli della madre e del building block della veste. La qualifica di dipendente
assente dal catalogo, o nessuna identità attiva alla fine, sono eccezioni senza codice
sollevate dalla fixture.

---

### Test

Nessun pgTAP dedicato: la esercitano i test che hanno l'operatore umano come soggetto, per
esempio quelli delle credenziali, del secondo fattore e dei profili di accesso in
`db/pgtap/config/`, e quelli dei permessi in `db/pgtap/script/`.

---

### Note di migrazione

* 2026-09-23 — nasce (`brief-db-fixture-che-costruiscono-giro-2`).
* 2026-09-25 — la madre crea la veste spenta, e la fixture fa il passo dell'invito accettato (`brief-db-blocco-login-per-credenziale`).
* 2026-10-09 — passa il sesso esplicito alla madre (`brief-db-sesso-senza-default`).
* 2026-10-18 — la veste la accende il building block invece di un aggiornamento scritto qui (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
