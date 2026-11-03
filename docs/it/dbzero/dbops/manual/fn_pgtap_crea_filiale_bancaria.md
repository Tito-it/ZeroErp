## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_filiale_bancaria`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.bank_branches](/dbzero/anagrafiche/tabelle/bank_branches) — la filiale, dato di macchina
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il soggetto della banca
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il ruolo BANK_B coi suoi indirizzi
> * [anagrafiche.trgfn_bank_guard_ruolo_bank_branches](/dbzero/anagrafiche/funzioni/trgfn_bank_guard_ruolo_bank_branches) — il guard sul ruolo della filiale
> * [dbops.fn_pgtap_crea_gestore](/dbzero/dbops/funzioni/fn_pgtap_crea_gestore) — il gestore, l'altro titolare tipico dei conti nei test
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — `bank_branches` è dato di macchina

---

### 🎯 Scopo Principale

Una filiale bancaria costruita per un test: il soggetto della banca, il suo ruolo BANK_B con
gli indirizzi che quel ruolo pretende, e la filiale. Serve a chi deve agganciare un conto
bancario. Torna la filiale, il soggetto ruolo e il soggetto della banca.

---

### ⭐ La filiale è dato di macchina: si costruisce, non si pesca

`anagrafiche.bank_branches` non è un catalogo distribuito: su un database ricostruito è
vuota. Un test che ne pesca una non trova niente, e muore sull'obbligo di filiale del conto,
un errore che parla della colonna e non della filiale che manca.

I codici di banca e di sportello possono essere fissi: l'unicità della filiale comprende il
soggetto ruolo, che è nuovo a ogni chiamata.

---

### ⚠️ La finestra dei vincoli differiti

La catena è una saga, e i controlli del ruolo bancario sugli indirizzi obbligatori scattano a
fine transazione. Il preambolo dei pgTAP rende i vincoli immediati, e la catena morirebbe a
metà con un errore sugli indirizzi a chi voleva una banca. La fixture apre la finestra
differita, costruisce, e la **richiude** a catena finita: i controlli scattano lì, su un mondo
completo, e non si perdono nel `ROLLBACK` del test. Esce con i vincoli immediati, come ogni
fixture.

---

### 🚫 Cosa non scrive

Il **conto bancario** e il suo legame col titolare: IBAN e intestatario sono il caso del
test.

---

### Codici errore

Nessuno suo: valgono i guard del soggetto, del ruolo BANK_B e della filiale.

---

### Test

Nessun pgTAP dedicato: la usano come fixture i test dei conti bancari in
`db/pgtap/anagrafiche/` e quelli degli enti d'incasso e delle sistemazioni in
`db/pgtap/pagamenti/`.

---

### Note di migrazione

* 2026-09-23 — nasce (`brief-db-fixture-che-costruiscono-giro-2`, §10): i test di
  `pagamenti/` che pescavano una filiale morivano tutti su un database ricostruito.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
