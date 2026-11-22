## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — le righe che la funzione scrive
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — i tipi obbligatori della natura, coi loro ripieghi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la singolare, che scrive ogni riga
> * [anagrafiche.fn_indirizzi_con_obbligatori](/dbzero/anagrafiche/funzioni/fn_indirizzi_con_obbligatori) — la copia del primo negli obbligatori
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato dei guard, oggi
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — la gemella del ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — gli obbligatori del soggetto

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_indirizzi_soggetto` scrive gli indirizzi di un soggetto in un'istruzione sola, e copia il primo
negli indirizzi obbligatori che mancano. Restituisce quanti indirizzi ha scritto.

È la gemella della plurale del ruolo: stesse regole, cambia la matrice da cui si leggono gli obbligatori, che qui è
quella della natura del soggetto. La usano l'applicazione e i builder dei soggetti dei test.

---

### ⭐ La copia del primo negli obbligatori

Se l'operatore compila un indirizzo solo, gli obbligatori della natura che mancano nell'elenco ricevono una **copia del
primo**: lo stesso indirizzo, col tipo cambiato, una per tipo. La fa `anagrafiche.fn_indirizzi_con_obbligatori`, la
stessa della plurale del ruolo.

Sono obbligatori le righe obbligatorie della natura che il predicato dei guard,
`anagrafiche.fn_tipo_indirizzo_ammesso_per_natura`, ammette il giorno operativo: attive e nella loro finestra di
validità. Una riga scaduta non fa nascere una copia, che il guard poi rifiuterebbe.

La copia si può spegnere (`p_copia_obbligatori`, accesa se non si dice altro): nasce allora solo ciò che l'elenco
indica, e gli obbligatori li pretende comunque il guard del soggetto al COMMIT.

---

### Le righe

* **Ogni indirizzo passa dalla grammatica** di `anagrafiche.fn_indirizzo_elemento` e lo scrive la singolare,
  `anagrafiche.fn_crea_indirizzo_soggetto`, coi suoi controlli sul tipo.
* **Un tipo che il soggetto ha già si salta**: niente doppioni, nemmeno da una seconda chiamata.
* **Un elenco vuoto** non scrive niente, nemmeno le copie.

---

### ⚠️ Che cosa oggi non copre

* **Il ripiego già nell'elenco.** Il guard degli obbligatori del soggetto è soddisfatto dal tipo obbligatorio o dal suo
  ripiego, ma la copia guarda solo il tipo: se l'elenco porta il ripiego e non il tipo, nasce lo stesso la copia del
  tipo, cioè un indirizzo in più di quanti il soggetto ne debba avere.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — gli indirizzi non sono un elenco, o un elemento non è un oggetto.
* `E_SOGGETTO_NOT_FOUND` — il soggetto non esiste.
* `E_CAMPO_NON_AMMESSO`, `E_TIPO_INDIRIZZO_NON_TROVATO` — dalla grammatica dell'elemento.
* Dalla singolare e dai guard: i rifiuti sul tipo e sulla forma.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` — il tipo che il soggetto ha già, la copia
  dell'obbligatorio col suo indirizzo, la copia spenta, il soggetto che non c'è.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — l'obbligatorio scaduto, che non fa nascere la copia.
* `db/pgtap/anagrafiche/test-fn-pgtap-crea-soggetto-pf-v1.sql`, `test-fn-pgtap-crea-soggetto-pg-v1.sql` — i builder dei
  soggetti, che scrivono gli indirizzi da qui.

---

### Note di migrazione

* 2026-10-19 — nasce, e prende il posto della procedura dell'applicazione che copiava gli obbligatori e scriveva gli
  indirizzi uno per uno.

---

{% include-markdown "signature-core.md" %}
