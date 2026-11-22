## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_fornitori_guard_ruolo_fornitore`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — la specializzazione che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo a cui la riga punta
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui il guard delega
> * [anagrafiche.fn_crea_fornitore](/dbzero/anagrafiche/funzioni/fn_crea_fornitore) — la porta che crea il ruolo `FO` e poi il fornitore
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, i ruoli e le loro specializzazioni

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_fornitori_guard_ruolo_fornitore` impedisce che una riga di `anagrafiche.fornitori` punti a un
ruolo che non è un fornitore (`FO`).

---

### Chi crea il ruolo

Il guard non crea il ruolo `FO`: lo crea, o lo riusa se il soggetto ce l'ha già, `anagrafiche.fn_crea_fornitore`,
prima di scrivere il fornitore. Chi scrive la riga per un'altra strada deve passare un ruolo `FO` già esistente.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

### Codici errore

* `E_SOGGETTI_RUOLI` — il ruolo manca, non esiste o non è `FO`.
* `E_COD_INT_RUOLO` — il codice `FO` non è in `config.tipi_ruoli`.

Li solleva `script.fn_guard_soggetto_ruolo`, passando dal registro degli errori.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql` — il fornitore nasce sul suo ruolo `FO`, nuovo o riusato.
  Nessun test prova il rifiuto di un ruolo di altro tipo.

---

{% include-markdown "signature-core.md" %}
