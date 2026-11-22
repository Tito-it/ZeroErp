## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_categorie_clienti_listini_guard_listino`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini) — la matrice categoria → listino che il guard presidia
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la traduzione dal ruolo dell'azienda al suo emittente fiscale
> * [vendite.listini](/dbzero/vendite/tabelle/listini) — il listino controllato
>
> Approfondimento funzioni:
>
> * [script.fn_check_listino_documento](/dbzero/script/funzioni/fn_check_listino_documento) — il controllo, lo stesso di contratti e offerte

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_categorie_clienti_listini_guard_listino` rifiuta una riga della matrice categoria → listino
il cui listino è di un'altra utility o di un'altra azienda rispetto a quelle della riga.

---

### ⭐ Lo sbaglio si ferma dove nasce

Una riga dice «i clienti di questa categoria, per questa utility, di questa azienda, usano questo listino».
Senza il guard una riga «clienti di A → listino di B» entrava: il calcolo del prezzo la sceglieva, e lo
sbaglio usciva solo al passaggio in commessa, come errore tecnico, lontano da chi aveva configurato la
matrice. Fermato qui, arriva a chi lo può correggere nel momento in cui lo fa.

---

### La domanda è quella dei documenti, i codici sono della matrice

Il controllo è `script.fn_check_listino_documento`, lo stesso di contratti e offerte. Vuole l'emittente
fiscale, mentre la riga porta il ruolo dell'azienda: il guard lo traduce, e la traduzione è univoca (un ruolo,
un emittente fiscale). Un listino che chi scrive non può leggere è fuori dal suo perimetro, e conta come di
un'altra azienda.

I codici sono propri della matrice, perché quelli dei documenti parlano «del documento»: il guard li sceglie
dal motivo che la check dà per primo. Un motivo nuovo della check, senza un codice qui, ferma la scrittura con
un errore che lo nomina: non passa in silenzio e non prende la frase di un altro.

---

### Quando scatta

Sempre alla nascita della riga; in modifica solo se cambiano listino, utility o azienda. Una riga già scritta
resta com'è finché non si tocca la sua chiave: cambiare la sola variazione o le date non rilegge il listino.

---

### Codici errore

* `E_CATEGORIA_LISTINO_UTILITY_DIVERSA` — il listino è di un'altra utility.
* `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO` — il listino è di un'altra azienda, o chi scrive non lo vede.

Entrambi sul campo `listino_id`, con frasi chiuse che non dicono niente del listino.

---

### Test

* `db/pgtap/anagrafiche/test-categorie-clienti-listini-guard-listino-v1.sql` — il listino giusto che entra,
  quello di un'altra utility e quello di un'altra azienda rifiutati, la modifica verso il listino di un'altra
  azienda rifiutata, la modifica della sola variazione che passa.

---

### Note di migrazione

* 2026-10-16 — nasce: prima l'errore arrivava solo al passaggio in commessa, come
  `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`.

---

{% include-markdown "signature-core.md" %}
