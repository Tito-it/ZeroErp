## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipo_indirizzo_ammesso_per_natura`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice che legge
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_ruolo) — il gemello sulla matrice del tipo di ruolo
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo) — il guard del soggetto
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — il guard del ruolo, per la natura del soggetto
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — il cambio di natura, sugli indirizzi già scritti
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — gli obbligatori, che conta solo se ammessi
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipo_indirizzo_ammesso_per_natura` dice se una natura di dettaglio ammette un tipo
d'indirizzo, un dato giorno, secondo la sua matrice. È la sede unica della regola della natura, su tutti e due
gli strati degli indirizzi.

---

### Un predicato puro

Riceve la natura, il tipo e il giorno, e non legge né il soggetto né i suoi indirizzi: per questo lo leggono
tanto chi scrive un indirizzo quanto chi giudica un cambio di natura o una natura scelta in un form, prima che il
soggetto esista. Il giorno lo passa il chiamante; tutti i lettori passano il giorno operativo.

La natura vuota è ammessa, come la natura senza righe di matrice. Un tipo che non esiste non ha riga, e risulta
non ammesso da una natura che ha la matrice: lo rifiuta comunque la chiave esterna.

---

### Chi lo legge

* i due guard degli indirizzi, del soggetto e del ruolo;
* le check su contesto del soggetto e del ruolo, e per loro tramite le madri e i picker;
* la regola del cambio di natura, sugli indirizzi del soggetto e dei suoi ruoli;
* la regola degli indirizzi obbligatori, del soggetto e del ruolo, che conta come obbligatorio solo un tipo
  ammesso, e la creazione degli obbligatori del soggetto;
* i picker del soggetto e della natura, per la colonna `obbligatorio`.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la riga scaduta e la natura vuota, attraverso la
  check del soggetto.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — il guard del ruolo legge il predicato, non la
  matrice; il privato e la sede legale.
* `db/pgtap/anagrafiche/test-cambio-natura-soggetto-v1.sql` — il motivo degli indirizzi del soggetto, provato sul
  predicato.

---

### Note di migrazione

* 2026-11-14 — estratto dal guard degli indirizzi del soggetto, perché la stessa regola la legga il cambio di
  natura.

---

{% include-markdown "signature-core.md" %}
