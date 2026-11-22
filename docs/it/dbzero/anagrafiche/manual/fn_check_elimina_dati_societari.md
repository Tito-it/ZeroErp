## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_elimina_dati_societari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.dati_societari](/dbzero/anagrafiche/tabelle/dati_societari) — la riga di cui si chiede l'eliminazione
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, che può pretendere la riga
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_elimina_dati_societari](/dbzero/anagrafiche/funzioni/fn_elimina_dati_societari) — il verbo, che solleva il primo motivo

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_elimina_dati_societari` dice perché i dati societari di un soggetto non si possono
eliminare: restituisce l'elenco dei motivi, vuoto se si può. Non scrive niente.

La legge il verbo `anagrafiche.fn_elimina_dati_societari`, che solleva il primo motivo, e la può leggere
l'applicazione per spegnere l'azione prima che l'utente la chieda.

---

### Un motivo solo: la natura li pretende

Se la natura del soggetto pretende i dati societari (la società di capitali) e la riga c'è, il motivo è
`E_DATI_SOCIETARI_NON_ELIMINABILI`, col campo della natura (`tipo_soggetto_dettaglio_id`) e il nome della
natura fra i valori: il rimedio, se c'è, è cambiare natura.

Non ci sono motivi, e l'elenco è vuoto, quando la riga non c'è (non c'è niente da eliminare), quando la
natura non la pretende, quando il soggetto non ha natura o non esiste. Il soggetto inesistente lo rifiuta il
verbo, non la check.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il soggetto non è passato: è un chiamante rotto, non un motivo.

---

### Test

* `db/pgtap/anagrafiche/test-fn-elimina-dati-societari-v1.sql` — il motivo per una società di capitali, col
  campo della natura; nessun motivo per una ditta individuale.

---

### Note di migrazione

* 2026-11-14 — nasce col verbo dell'eliminazione.

---

{% include-markdown "signature-core.md" %}
