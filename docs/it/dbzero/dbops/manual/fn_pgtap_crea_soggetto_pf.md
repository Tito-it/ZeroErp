## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_soggetto_pf`

> **Ultimo aggiornamento**: 17 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la testata, scritta dalla madre
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi del soggetto, scritti dalla madre degli indirizzi
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che decide sesso, partita IVA e dati societari
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice che dice quali indirizzi servono
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la madre di dominio: testata, contatto, dati societari
> * [anagrafiche.fn_crea_indirizzi_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_soggetto) — la madre degli indirizzi del soggetto
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il gemello per la persona giuridica
> * [dbops.fn_pgtap_cf_libero](/dbzero/dbops/funzioni/fn_pgtap_cf_libero) — il codice fiscale libero
> * [dbops.fn_pgtap_piva_libera](/dbzero/dbops/funzioni/fn_pgtap_piva_libera) — la partita IVA libera
> * [dbops.fn_pgtap_indirizzo_libero_forma](/dbzero/dbops/funzioni/fn_pgtap_indirizzo_libero_forma) — i campi dell'indirizzo nella forma dello stato
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il passo successivo: il ruolo
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — la persona fisica che è anche un operatore
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — la finestra differita e le fixture che costruiscono

---

### 🎯 Scopo Principale

Crea per un test un **soggetto persona fisica già valido** — testata, contatto, indirizzi
obbligatori — dalle madri del dominio, e ne restituisce l'id. Al test basta passare il
cognome: nome, natura, stato e partita IVA hanno un default, e senza natura il soggetto è un
privato.

È il gemello di [fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg):
stesse scelte, stessa finestra, la porta della persona fisica.

---

### ⭐ La finestra differita si apre e si richiude

I tre guard di completezza del soggetto (dati societari, indirizzi, contatti) sono differiti
apposta: un soggetto è una saga, e la completezza si verifica quando la saga è finita. La
fixture costruisce con i guard differiti e li **richiude** in fondo, quando il soggetto è
completo: i controlli scattano lì. Al ritorno i vincoli sono immediati: un chiamante che poi
costruisce a mano un'altra saga, o assegna un ruolo con la madre del ruolo, deve aprirsi la
sua finestra.

---

### Che cosa sceglie la natura, non la fixture

* **Natura**: quella del test; se non la dà, il privato dello stato.
* **Codice fiscale**: uno libero, mai usato.
* **Sesso**: si scrive se la natura lo prevede (per il privato è obbligatorio, per la ditta
  individuale facoltativo).
* **Partita IVA**: quella del test; se non la dà e la natura la pretende (la ditta
  individuale), una libera.
* **Dati societari**: solo se la natura li **pretende**. Per una persona fisica sono
  facoltativi o vietati, e la fixture costruisce il soggetto minimo che il modello ammette:
  una ditta individuale nasce senza. Un test che li vuole li scrive col verbo dei dati
  societari.
* **Indirizzi**: un indirizzo del primo tipo obbligatorio della matrice della natura, nella
  forma che lo stato pretende; la madre degli indirizzi lo copia sugli altri tipi
  obbligatori. Una natura senza tipi obbligatori nasce **senza** indirizzi.
* **Contatto**: il contatto predefinito della madre, col nominativo «cognome nome» e
  un'email di prova.

⚠️ Una natura di persona giuridica non passa: la rifiuta la madre
(`E_SOGGETTO_CREAZIONE_NATURA_ERRATA`).

---

### ⛔ Crea il soggetto, non i ruoli né l'operatore

Un soggetto senza ruolo non è ancora né cliente né fornitore: il ruolo lo assegna
[fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo), o la
madre del ruolo, in un'istruzione **separata**. La fixture non crea nemmeno la risorsa umana
né l'identità: per un operatore c'è
[fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano).

---

### Codici errore

La fixture solleva da sé solo per uno stato che non esiste o che non ha un privato. Valgono i
codici delle due madri e i guard del soggetto, degli indirizzi e del contatto, che scattano
alla richiusura della finestra.

---

### Test

* `db/pgtap/anagrafiche/test-fn-pgtap-crea-soggetto-pf-v1.sql` — il privato di default, il
  contatto della madre, gli indirizzi obbligatori, la ditta individuale con la partita IVA e
  senza dati societari, una natura che li pretende e una senza tipi obbligatori (costruite
  nella transazione), il rifiuto di una natura di persona giuridica.
* La esercitano i test degli indirizzi di residenza, del fornitore privato, delle risorse
  umane e dei titoli IVA in `db/pgtap/anagrafiche/`.

---

### Note di migrazione

* 2026-11-17 — nasce dalle cinque copie dei pgTAP che costruivano a mano un privato valido,
  ritirate nello stesso giro (`brief-db-fornitore-privato-indirizzi`, riga 7-bis).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
