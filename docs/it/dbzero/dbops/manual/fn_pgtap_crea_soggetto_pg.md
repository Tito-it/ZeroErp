## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_soggetto_pg`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la testata, scritta dalla fixture
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi del soggetto, scritti dalla fixture
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice che dice quali indirizzi servono
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_scrivi_dati_societari](/dbzero/anagrafiche/funzioni/fn_scrivi_dati_societari) — il verbo dei dati societari
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il building block del contatto
> * [anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) — la madre di dominio, che la fixture non usa
> * [dbops.fn_pgtap_piva_libera](/dbzero/dbops/funzioni/fn_pgtap_piva_libera) — la partita IVA libera
> * [dbops.fn_pgtap_indirizzo_libero_forma](/dbzero/dbops/funzioni/fn_pgtap_indirizzo_libero_forma) — i campi dell'indirizzo nella forma dello stato
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — il passo successivo: il ruolo
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — la finestra differita e le fixture che costruiscono

---

### 🎯 Scopo Principale

Crea per un test un **soggetto persona giuridica già valido** — testata, dati societari,
indirizzi obbligatori, contatto — e ne restituisce l'id. Al test basta passare la ragione
sociale: natura, stato e partita IVA hanno un default.

---

### ⭐ La finestra differita si apre e si richiude

I tre guard di completezza del soggetto (dati societari, indirizzi, contatti) sono differiti
apposta: un soggetto è una saga, e la completezza si verifica quando la saga è finita, non
dopo il primo inserimento. Il preambolo dei pgTAP li rende immediati, e senza la fixture
scatterebbero sul soggetto ancora nudo.

La fixture costruisce con i guard differiti e li **richiude** in fondo, quando il soggetto è
completo: i controlli scattano lì, che è esattamente la verifica che il modello vuole.
⚠️ La richiusura non è facoltativa: senza, il `ROLLBACK` del test si porterebbe via i
controlli non eseguiti, e il test sarebbe verde per sottrazione. Al ritorno i vincoli sono
immediati: un chiamante che poi costruisce a mano un'altra saga deve aprirsi la sua finestra.

---

### Che cosa sceglie la configurazione, non la fixture

* **Codice fiscale**: coincide con la partita IVA, come per una persona giuridica italiana.
  Il sesso non si scrive: per società ed enti non si indica.
* **Dati societari**: passano dal verbo, come nell'applicazione. La forma giuridica è la
  prima ammessa dalla natura per lo stato; numero REA e capitale ci sono solo se la forma li
  prevede (il numero REA si ricava dalla partita IVA, già unica). Nessun canale di
  fatturazione elettronica. Se la natura vieta i dati societari, non si scrivono.
* **Indirizzi**: tutti i tipi obbligatori della matrice della natura, nella forma che lo
  stato pretende (comune e CAP del catalogo, oppure località). Se la natura non ha tipi
  obbligatori, se ne scrive comunque uno, il primo ammesso: il guard degli indirizzi
  pretende almeno una riga.
* **Contatto**: un contatto predefinito, scritto dal building block.

⚠️ Una natura di persona fisica non passa: la rifiuta il guard del sesso, perché la fixture
non ne ha uno da dare. Per una persona fisica c'è
[fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano).

---

### ⚠️ Testata e indirizzi sono scritti dalla fixture

Dati societari e contatto passano dal dominio. La testata del soggetto e i suoi indirizzi
invece la fixture li scrive da sé, senza passare dalla madre
[anagrafiche.fn_crea_soggetto_pg](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pg) né dalla
madre degli indirizzi del soggetto.

---

### ⛔ Crea il soggetto, non i ruoli

Un soggetto senza ruolo non è ancora né cliente né fornitore. Il ruolo lo assegna
[fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo), in
un'istruzione **separata**.

---

### Codici errore

La fixture non ne solleva di suoi: valgono i guard del soggetto, dei dati societari, degli
indirizzi e del contatto, che scattano alla richiusura della finestra.

---

### Test

Nessun pgTAP dedicato: la esercitano i test che costruiscono clienti, fornitori, banche e
aziende, e quelli dei dati societari in `db/pgtap/anagrafiche/`.

---

### Note di migrazione

* 2026-08-18 — nasce con la bonifica della baseline pgTAP di vendite (`brief-db-bonifica-baseline-pgtap-vendite`).
* 2026-10-09 — il sesso è vuoto invece di un valore fuori vocabolario (`brief-db-sesso-senza-default`).
* 2026-10-10 — i dati societari nascono senza canale di fatturazione elettronica.
* 2026-10-11 — i dati societari passano dal verbo, e i valori li decide la configurazione (`brief-db-dati-fiscali-e-societari-del-soggetto`).
* 2026-10-17 — il contatto passa dal building block (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-19 — gli indirizzi nella forma che lo stato pretende; prima avevano la forma estera anche per l'Italia.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
