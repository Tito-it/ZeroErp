## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_update_cliente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i campi modificabili del cliente
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — dove sta la categoria del cliente
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) — le categorie
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — il verbo gemello, per la nascita

---

### 🎯 Scopo Principale

`anagrafiche.fn_update_cliente` modifica un cliente in un'istruzione sola: la categoria, che sta sul suo
billing account, e i campi modificabili della riga del cliente. O cambiano tutti e due o nessuno.

Restituisce il cliente e due indicazioni: se ha scritto la categoria e se ha scritto i campi del cliente. Se
non ha scritto niente, decide chi chiama se è un errore.

---

### ⭐ Due tabelle, una scrittura

La categoria vive sul billing account, i dati di pagamento sul cliente. Scritte in due momenti, il fallimento
della seconda lascerebbe la prima già salvata: un cliente e il suo conto che dicono cose diverse. Qui sono una
sola istruzione.

---

### Che cosa si modifica

* **La categoria**, se indicata. Non si porta mai a vuoto: la colonna del billing account è obbligatoria, e un
  valore assente vuol dire «non toccarla».
* **I campi del cliente**, come delta: modalità e termine di pagamento, servizio da fatturare, tipo e importo
  della garanzia. Cambia solo una chiave presente; una chiave presente con valore nullo svuota la colonna.
  Se nessuna di queste chiavi c'è, la riga del cliente non si scrive affatto, e lo storico non registra una
  modifica vuota.

Stato, date e fornitura non si cambiano da qui: la chiusura e il subentro hanno i loro verbi
(`script.fn_disdetta_cliente`, `script.fn_subentro_cliente`), e la fornitura è bloccata.

La funzione legge e scrive con i diritti di chi chiama: un cliente fuori dal suo perimetro risponde come un
cliente che non esiste.

---

### ⚠️ Che cosa oggi non copre

* **Una chiave fuori elenco è ignorata in silenzio**: la modifica riesce e quel valore non va da nessuna
  parte. `anagrafiche.fn_crea_cliente`, sugli stessi campi, la rifiuta con `E_CAMPO_NON_AMMESSO`.
* **Un delta che non è un oggetto** non ha un codice di catalogo: risponde l'errore tecnico di PostgreSQL.
* **La categoria si dice «aggiornata» anche quando non cambia**: basta averla indicata.

---

### Codici errore

* `E_CLIENTE_NON_TROVATO` — il cliente non esiste, o chi chiama non lo vede.

---

### Test

* `db/pgtap/anagrafiche/test-fn-update-cliente-v1.sql` — categoria e campi insieme, il delta che cambia solo
  le chiavi presenti, l'atomicità (un campo sbagliato annulla anche la categoria), il cliente che non esiste,
  la chiamata senza niente da cambiare.

---

### Note di migrazione

* 2026-07-31 — escono dall'elenco `tipo_gg_scadenza_ft` e `nr_giorni_scadenza`: le condizioni di pagamento sono
  tutte nel termine di catalogo.
* 2026-08-29 — escono `iva_id`, `cliente_pa`, `split_payment`, `codice_cig`, `codice_cup` e `codice_commessa`,
  colonne che il cliente non ha più.

---

{% include-markdown "signature-core.md" %}
