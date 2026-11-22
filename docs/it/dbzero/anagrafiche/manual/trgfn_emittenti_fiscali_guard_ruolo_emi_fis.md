## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la specializzazione che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo a cui la riga punta
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui il guard delega
> * [anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale) — la creazione, che fa il ruolo `EF` prima della riga
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis` impedisce che un emittente fiscale punti a un ruolo che
non è di emittente fiscale (`EF`). Senza, nulla vieterebbe di agganciarlo al ruolo cliente o fornitore dello
stesso soggetto.

---

### Il tipo del ruolo, non la sua identità

Il guard dice che il ruolo è `EF`, non che resta lo stesso. Che `soggetto_ruolo_id` non cambi dopo la nascita lo
tiene il lock di colonna di `anagrafiche.emittenti_fiscali` (`E_EMITTENTE_SOGGETTO_IMMUTABILE`), che per fascia
scatta prima: un emittente spostato su un altro ruolo `EF` è fermato lì, e il guard non arriva a vederlo.

Il ruolo `EF` lo crea chi crea l'emittente: `anagrafiche.fn_crea_emittente_fiscale` lo prende o lo crea sul
soggetto prima di scrivere la riga.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo manca, non esiste o non è `EF`.
* `E_COD_INT_RUOLO` — il codice `EF` non è in `config.tipi_ruoli`.

Li solleva `script.fn_guard_soggetto_ruolo`, passando dal registro degli errori.

---

### Test

Nessun pgTAP prova il rifiuto di un ruolo di altro tipo sugli emittenti.

---

{% include-markdown "signature-core.md" %}
