## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_soggetto_ruolo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice degli indirizzi del ruolo
>
> Approfondimento funzioni:
>
> * [script.fn_get_or_create_soggetto_ruolo](/dbzero/script/funzioni/fn_get_or_create_soggetto_ruolo) — il ruolo, preso se c'è e creato se manca
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — il verbo che scrive gli indirizzi del ruolo
> * [dbops.fn_pgtap_indirizzo_libero_forma](/dbzero/dbops/funzioni/fn_pgtap_indirizzo_libero_forma) — i campi dell'indirizzo nella forma dello stato
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — il passo precedente: il soggetto
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — la finestra differita e le istruzioni separate

---

### 🎯 Scopo Principale

Assegna a un soggetto un **ruolo** (per esempio `CL`, `FO`, `GE`) già completo dei suoi
indirizzi obbligatori, e restituisce l'id del soggetto ruolo.

---

### ⚠️ Gli indirizzi del ruolo sono un livello a parte

Gli indirizzi di un ruolo hanno una matrice propria e un guard proprio, separati da quelli
del soggetto. Un indirizzo del soggetto, per quanto presente, non soddisfa il guard del
ruolo: il ripiego del guard porta a un altro *tipo* di indirizzo, non all'altro *livello*.
Per questo la fixture scrive gli indirizzi del ruolo anche quando il soggetto li ha già.

Gli indirizzi li scrive il verbo di dominio, come nell'applicazione. La fixture gli passa il
primo tipo obbligatorio, nella forma che lo stato pretende; gli altri tipi obbligatori li
copia il verbo. Se il ruolo non ha tipi obbligatori, non scrive niente.

---

### ⭐ Idempotente sul ruolo e sugli indirizzi

Il ruolo può esistere già: in quel caso la fixture lo riprende invece di crearne un altro, e
il verbo salta i tipi di indirizzo che il ruolo ha già. Come la fixture del soggetto, apre la
finestra dei vincoli differiti e la richiude prima di uscire.

---

### ⛔ In un'istruzione separata dalla creazione del soggetto

Le scritture nella stessa istruzione condividono la stessa fotografia del database: una
policy che risolve il perimetro dal soggetto padre non lo troverebbe, e negherebbe. Il
soggetto si crea con [fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg),
il ruolo con questa fixture, in un'istruzione successiva. È anche la ragione per cui sono due
funzioni e non una con un parametro in più: la separazione è obbligatoria, e due funzioni la
rendono evidente.

---

### Codici errore

La fixture non ne solleva di suoi: valgono quelli del ruolo (una natura che non ammette il
ruolo) e del verbo degli indirizzi.

---

### Test

Nessun pgTAP dedicato: la esercitano i test che costruiscono clienti, fornitori, banche e
aziende, a partire da quelli sulla natura ammessa dei ruoli in `db/pgtap/anagrafiche/`.

---

### Note di migrazione

* 2026-08-18 — nasce con la bonifica della baseline pgTAP di vendite (`brief-db-bonifica-baseline-pgtap-vendite`).
* 2026-10-17 — gli indirizzi passano dal verbo di dominio (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-19 — l'indirizzo nella forma che lo stato pretende; prima aveva la forma estera anche per l'Italia.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
