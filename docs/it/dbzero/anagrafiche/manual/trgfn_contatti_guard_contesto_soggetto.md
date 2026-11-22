## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_contatti_guard_contesto_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — la tabella su cui è montata
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_ruolo_di_altro_soggetto) — la domanda sul ruolo
> * [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_istanza_di_altro_soggetto) — la domanda sull'istanza
> * [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/funzioni/trgfn_guard_istanza_del_ruolo) — la stessa regola su indirizzi e conti del ruolo
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il contesto di un contatto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_contatti_guard_contesto_soggetto` rifiuta un contatto il cui ruolo o la cui istanza sono di un
altro soggetto: il contesto di un contatto è sempre del soggetto del contatto.

Un contatto è sempre di un soggetto e, se serve, di un suo ruolo (cliente, fornitore, …) e di una sua istanza
(una fornitura). Senza questo controllo un contatto potrebbe stare sul ruolo o sull'istanza di un altro soggetto.

---

### Quando scatta

Prima di ogni nascita e di ogni modifica di `anagrafiche.contatti`; in modifica, solo se cambiano il soggetto, il
ruolo o l'istanza. Un contatto del solo soggetto non ha niente da controllare.

---

### Che cosa rifiuta

Si controlla prima il ruolo, poi l'istanza. Spostare un contatto su un altro soggetto lasciandogli il ruolo di
prima è rifiutato per il ruolo. Le due domande le fanno due funzioni comuni a tutte le tabelle con la stessa
regola, e il rifiuto porta il campo da evidenziare.

---

### Codici errore

* `E_RUOLO_ALTRO_SOGGETTO` — il ruolo è di un altro soggetto; campo `soggetto_ruolo_id`.
* `E_ISTANZA_ALTRO_SOGGETTO` — l'istanza è di un altro soggetto; campo `istanza_utility_id`. Il messaggio porta il
  codice dell'istanza.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (test 13-16) — il ruolo e l'istanza di un altro
  soggetto rifiutati, quelli del soggetto e il contatto del solo soggetto ammessi, lo spostamento del contatto su
  un altro soggetto rifiutato per il ruolo.

---

### Note di migrazione

* 2026-10-19 — nasce, su richiesta del backend, insieme alla stessa regola su indirizzi e conti del ruolo.

---

{% include-markdown "signature-core.md" %}
