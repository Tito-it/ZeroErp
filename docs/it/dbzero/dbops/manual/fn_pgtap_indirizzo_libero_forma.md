## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_indirizzo_libero_forma`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati](/dbzero/config/tabelle/stati) — il flag del catalogo dei comuni, che decide la forma
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — il guard di cui questa fixture rispetta la forma
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — la usa per gli indirizzi del soggetto
> * [dbops.fn_pgtap_crea_soggetto_ruolo](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_ruolo) — la usa per gli indirizzi del ruolo
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — le fixture non si inventano i campi

---

### 🎯 Scopo Principale

Per uno stato, i campi della forma dell'indirizzo libero come li pretende il guard: comune e
CAP del catalogo, oppure località e codice postale. Torna una riga sola, da unire ai campi
dell'indirizzo che la fixture scrive.

Non scrive niente.

---

### ⭐ La forma la decide il flag dello stato, come nel guard

[trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera)
sceglie la forma dal flag del catalogo completo dei comuni dello stato, e la fixture legge lo
stesso flag:

* **stato col catalogo completo** (l'Italia): il primo comune dello stato che ha un CAP, e
  quel CAP, nell'ordine degli id, quindi sempre lo stesso. Località e codice postale restano
  vuoti, perché il guard rifiuta i campi della forma estera insieme a quelli del catalogo;
* **altrimenti**: la località `Localita pgTAP` e il codice postale `00000`, con comune e CAP
  vuoti.

Il catalogo dei comuni c'è anche su un database ricostruito: la scelta non dipende dalla
macchina.

⚠️ Una fixture che si inventa i campi tiene una copia della regola, e la copia invecchia:
indirizzi italiani scritti nella forma estera (città, CAP e provincia a testo) erano ammessi
prima del guard, e oggi sono rifiutati.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — lo stato non esiste, oppure ha il catalogo dei comuni
  acceso e nessun comune con un CAP.

---

### Test

Nessun pgTAP dedicato: la provano le fixture del soggetto e del ruolo, e i test che la usano
per scrivere indirizzi propri, soprattutto in `db/pgtap/anagrafiche/` (indirizzi del
soggetto e del ruolo, obbligatori, singolari e plurali) e in `db/pgtap/vendite/` (indirizzi
dei documenti e loro fotografie).

---

### Note di migrazione

* 2026-10-18 — nasce insieme al guard della forma dell'indirizzo libero (D-2 di Tid,
  richiesta BE in `brief-db-processi-accensione-per-ambiente`, §6.11): fino ad allora le
  fixture scrivevano indirizzi italiani nella forma estera.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
