## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_bank_guard_ruolo_bank_branches`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.bank_branches](/dbzero/anagrafiche/tabelle/bank_branches) — le filiali, che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo della banca a cui la filiale punta
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il ruolo `BANK_B`, «istituti di credito»
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui il guard delega
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — le filiali e i conti che tengono

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_bank_guard_ruolo_bank_branches` impedisce che una filiale di `anagrafiche.bank_branches` punti a
un ruolo che non è una banca (`BANK_B`).

---

### Una banca, molte filiali

Il guard non crea il ruolo `BANK_B`: chi scrive la filiale passa il ruolo della banca, già esistente. Nessun verbo del
database crea una banca: il soggetto, il suo ruolo e le sue filiali li scrive l'applicazione.

A differenza delle altre specializzazioni, le filiali non hanno un vincolo unico sul solo ruolo: lo stesso ruolo
`BANK_B` ha tutte le filiali della banca, e il guard le giudica una per una.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo manca, non esiste o non è `BANK_B`.
* `E_COD_INT_RUOLO` — il codice `BANK_B` non è in `config.tipi_ruoli`.

Li solleva `script.fn_guard_soggetto_ruolo`, passando dal registro degli errori.

---

### Test

* `db/pgtap/anagrafiche/create-soggetto-bank-branches.sql` — la filiale nasce sul ruolo `BANK_B` della banca. Nessun
  test prova il rifiuto di un ruolo di altro tipo.

---

{% include-markdown "signature-core.md" %}
