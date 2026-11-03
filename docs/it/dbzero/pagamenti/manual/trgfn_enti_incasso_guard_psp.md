## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_enti_incasso_guard_psp`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — la tabella su cui il guard è montato
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il soggetto-ruolo nominato dal canale
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — dove si riconosce il ruolo `PSP`
> * [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp) — il censimento del PSP

---

### 🎯 Scopo Principale

Garantisce la coerenza di un canale di incasso di tipo `PSP`: il canale deve nominare un
soggetto-ruolo che sia davvero un PSP e che sia censito come tale.

---

### Tre gradini, tre rimedi

Quando `tipo = 'PSP'` il guard controlla, in quest'ordine:

1. `soggetto_ruolo_id` è valorizzato;
2. il soggetto-ruolo ha il ruolo `PSP`;
3. esiste una riga **attiva** in `anagrafiche.psp` per quello stesso soggetto-ruolo.

Ogni gradino ha il suo codice, perché ognuno ha un rimedio diverso: compilare il campo, scegliere
un altro soggetto, censire il PSP. Sugli altri tipi il guard non dice niente.

⭐ Il ruolo si riconosce dal `codice_interno` di `config.tipi_ruoli`, che non cambia, e non
dall'etichetta, che si può modificare.

⚠️ Il terzo gradino è un `CONFLITTO_STATO` e non un `NON_TROVATO`: il canale e il soggetto-ruolo
esistono, manca un censimento a monte.

---

### Codici errore

* `E_ENTE_INCASSO_PSP_SOGGETTO_RUOLO_OBBLIGATORIO` (`DATO_ERRATO`) — canale `PSP` senza
  `soggetto_ruolo_id`.
* `E_ENTE_INCASSO_PSP_RUOLO_NON_PSP` (`DATO_ERRATO`) — il soggetto-ruolo indicato non ha il
  ruolo `PSP`.
* `E_ENTE_INCASSO_PSP_NON_CENSITO` (`CONFLITTO_STATO`) — il soggetto-ruolo è un PSP ma non ha
  una riga attiva in `anagrafiche.psp`.

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — un canale `PSP` valido si crea; sono
  rifiutati il canale senza soggetto-ruolo, quello con un soggetto-ruolo non PSP e quello con un
  PSP non censito. Gira come l'applicazione, con il ruolo operatore e la row security attiva.

---

### Note di migrazione

* 2026-08-21 — i tre rifiuti, fino ad allora un unico `E_GENERICO`, passano a tre codici
  distinti, e il terzo smette di registrare il nome del trigger al posto di quello della
  funzione. Nessun predicato è cambiato.

---

{% include-markdown "signature-core.md" %}
