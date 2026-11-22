## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi del ruolo e delle sue istanze, su cui scatta
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo, da cui legge il tipo di ruolo e il soggetto
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice del tipo di ruolo
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_ruolo) — il predicato del tipo di ruolo
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato della natura
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo) — la check con cui la madre lo anticipa
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo) — il guard gemello sugli indirizzi del soggetto
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — chi giudica gli indirizzi del ruolo quando cambia la natura
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` rifiuta un indirizzo del ruolo, o di una sua
istanza, di un tipo che il tipo di ruolo oppure la natura del soggetto del ruolo non ammettono. È il presidio
della regola sullo strato del ruolo, qualunque strada scriva la tabella.

---

### Due regole, nell'ordine dei motivi

Scatta prima della scrittura, alla nascita dell'indirizzo e quando ne cambia il tipo. Dal ruolo legge il tipo di
ruolo e la natura del soggetto, poi chiede ai due predicati, sul giorno operativo, nello stesso ordine della
check della madre:

1. il **tipo di ruolo** ammette il tipo (`anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo`), altrimenti
   `E_TIPO_INDIRIZZO_NON_PERMESSO`, coi valori tipo di ruolo e tipo d'indirizzo;
2. la **natura del soggetto** ammette il tipo (`anagrafiche.fn_tipo_indirizzo_ammesso_per_natura`), altrimenti
   `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`, il codice del guard del soggetto, coi valori natura e tipo.

Ciascuna regola è libera quando la sua matrice non dice niente, o quando il tipo di ruolo o la natura sono
vuoti. Il campo da evidenziare è `tipo_indirizzo_id`; il contesto porta gli id e il ruolo. L'istanza non
entra nel giudizio: un indirizzo dell'istanza ha le regole del suo ruolo.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il cambio del tipo di ruolo non rigiudica gli indirizzi del ruolo.** `soggetti_ruoli.tipo_ruolo_id` si può
  modificare: lo guardano la natura ammessa del ruolo e, al COMMIT, gli indirizzi obbligatori, ma nessun
  oggetto chiede se gli indirizzi che il ruolo ha già siano ammessi dal tipo di ruolo nuovo. Restano anche
  quelli che la matrice del tipo nuovo non prevede. Per la natura il caso è coperto dal cambio di natura.

---

### Codici errore

* `E_TIPO_INDIRIZZO_NON_PERMESSO` — il tipo di ruolo non ammette il tipo d'indirizzo.
* `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` — la natura del soggetto del ruolo non lo ammette.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql` — il rifiuto del tipo di ruolo, sui tipi del gestore.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — il guard legge il predicato, non la matrice.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — la sede legale sul ruolo di un privato,
  rifiutata dalla strada che salta la madre con la frase della natura; il guard legge il predicato della natura.

---

### Note di migrazione

* 2026-11-15 — il guard smette di leggere la matrice e chiede al predicato del tipo di ruolo, estratto.
* 2026-11-16 — si aggiunge la seconda regola, la natura del soggetto del ruolo, col fornitore privato: prima
  la natura giudicava solo gli indirizzi del soggetto.

---

{% include-markdown "signature-core.md" %}
