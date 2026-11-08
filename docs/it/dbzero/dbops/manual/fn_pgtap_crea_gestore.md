## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_gestore`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori) — la riga del gestore, dato di macchina
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_gestori_guard](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard) — il guard che tiene il gestore unico
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il soggetto della società
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il ruolo GE coi suoi indirizzi
> * [dbops.fn_pgtap_crea_filiale_bancaria](/dbzero/dbops/funzioni/fn_pgtap_crea_filiale_bancaria) — la filiale su cui il test aggancia i conti del gestore
> * [dbops.fn_pgtap_valuta](/dbzero/dbops/funzioni/fn_pgtap_valuta) — la valuta delle radici della catena, per le fixture
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i dati di macchina si costruiscono, non si pescano

---

### 🎯 Scopo Principale

Il gestore dell'installazione per un test: il soggetto della società che usa l'ERP, il suo
ruolo GE con gli indirizzi che quel ruolo pretende, e la riga in `anagrafiche.gestori`. Lo
prende se c'è, lo costruisce se non c'è.

---

### ⭐ Prendi-o-costruisci, perché il gestore è uno solo

`anagrafiche.gestori` è **dato di macchina**: su un database ricostruito è vuota, e un test
che legge «il primo gestore» non trova niente. Ma il gestore è unico, e un secondo lo
rifiuta [trgfn_gestori_guard](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard)
(`E_GESTORE_SINGLETON_VIOLATO`). Quindi la fixture risponde il gestore che c'è, il primo per
id, e costruisce solo dove manca: sulla macchina di sviluppo non scrive niente, su un
database ricostruito lo crea. Una fixture che costruisse sempre sarebbe rossa proprio dove
il gestore esiste già.

L'unicità non la tiene un vincolo: la tiene il guard. Sulla tabella l'unico vincolo di
unicità oltre la chiave è sul soggetto ruolo.

---

### Che cosa sceglie quando costruisce

Descrizione con l'etichetta del test, codice prodotto `ZEROERP`, la prima valuta a catalogo
per id, presa da [dbops.fn_pgtap_valuta](/dbzero/dbops/funzioni/fn_pgtap_valuta): la valuta
del gestore è l'ultimo anello della catena con cui si risolve la valuta di un documento.

---

### 🚫 Cosa non scrive

I **conti bancari** del gestore: uso, IBAN e conto predefinito sono il caso del test.

---

### ⚠️ La finestra dei vincoli differiti

Quando costruisce, la fixture apre da sé la finestra differita: il ruolo GE ha indirizzi
obbligatori con un controllo che scatta a fine transazione, e il preambolo dei pgTAP rende i
vincoli immediati. La richiude a catena finita, ed esce con i vincoli immediati come ogni
fixture.

---

### Codici errore

Nessuno suo: quando costruisce valgono i guard del gestore e del ruolo GE.

---

### Test

Nessun pgTAP dedicato: la usano come fixture i test che hanno bisogno del gestore, cioè
quelli dei conti bancari e degli indirizzi del gestore in `db/pgtap/anagrafiche/` e quelli
della valuta di default dei documenti in `db/pgtap/vendite/`.

---

### Note di migrazione

* 2026-09-23 — nasce (`brief-db-fixture-che-costruiscono-giro-2`, §11): i test di
  `anagrafiche/` che leggevano il primo gestore non trovavano niente su un database
  ricostruito.
* 2026-10-10 — ritirato `uq_gestori_singleton`, che nonostante il nome ripeteva la chiave
  primaria: il singleton è rimasto al guard.
* 2026-11-08 — la valuta la dà `dbops.fn_pgtap_valuta`, la sede comune delle fixture, invece di
  una copia della scelta.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
