## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_enti_incasso_guard_psp`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — la tabella su cui il guard è montato
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il soggetto-ruolo nominato dal canale
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — dove si riconosce il ruolo `PSP`
> * [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp) — il censimento del PSP
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_psp_guard_enti_incasso_attivi](/dbzero/anagrafiche/funzioni/trgfn_psp_guard_enti_incasso_attivi) — il verso opposto: il PSP con canali accesi non si spegne

---

### 🎯 Scopo Principale

Garantisce la coerenza di un canale di incasso di tipo `PSP`: il canale deve nominare un
soggetto-ruolo che sia davvero un PSP e che sia censito come tale.

---

### Quattro gradini, quattro rimedi

Quando `tipo = 'PSP'` il guard controlla, in quest'ordine:

1. `soggetto_ruolo_id` è valorizzato;
2. il soggetto-ruolo ha il ruolo `PSP`;
3. esiste una riga in `anagrafiche.psp` per quello stesso soggetto-ruolo, accesa o spenta;
4. solo per un canale **acceso**: quella riga è accesa.

Ogni gradino ha il suo codice, perché ognuno ha un rimedio diverso: compilare il campo, scegliere
un altro soggetto, censire il PSP, riaccenderlo. Sugli altri tipi il guard non dice niente.

⭐ **Un canale spento si modifica anche col PSP spento.** I primi tre gradini sono la forma del
canale e valgono sempre; l'acceso del PSP conta solo per un canale che lavora. Il verso opposto, il
PSP che non si spegne finché ha canali accesi, lo tiene
`anagrafiche.trgfn_psp_guard_enti_incasso_attivi`.

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
  una riga in `anagrafiche.psp`.
* `E_ENTE_INCASSO_PSP_SPENTO` (`CONFLITTO_STATO`) — il canale è acceso e il suo PSP è spento.

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — un canale `PSP` valido si crea; sono
  rifiutati il canale senza soggetto-ruolo, quello con un soggetto-ruolo non PSP e quello con un
  PSP non censito. Gira come l'applicazione, con il ruolo operatore e la row security attiva.
* `db/pgtap/anagrafiche/test-ruoli-impresa-psp-vettore-gestore-v1.sql` — il canale spento che si
  modifica col PSP spento, e il canale che non si riaccende finché il PSP è spento.

---

### Note di migrazione

* 2026-08-21 — i tre rifiuti, fino ad allora un unico `E_GENERICO`, passano a tre codici
  distinti, e il terzo smette di registrare il nome del trigger al posto di quello della
  funzione. Nessun predicato è cambiato.
* 2026-11-27 — il PSP acceso lo vuole solo il canale acceso, con un codice suo
  (`E_ENTE_INCASSO_PSP_SPENTO`); prima un PSP spento rispondeva «non censito» anche su un canale
  spento.

---

{% include-markdown "signature-core.md" %}
