## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — le righe che la funzione scrive
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — i tipi obbligatori del ruolo, coi loro ripieghi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la singolare, che scrive ogni riga
> * [anagrafiche.fn_indirizzi_con_obbligatori](/dbzero/anagrafiche/funzioni/fn_indirizzi_con_obbligatori) — la copia del primo negli obbligatori
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — quali tipi sono obbligatori oggi
> * [anagrafiche.fn_crea_indirizzi_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_soggetto) — la gemella del soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — gli obbligatori e i ripieghi

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_indirizzi_ruolo` scrive gli indirizzi di un ruolo (cliente, fornitore, …) in un'istruzione sola,
e copia il primo negli indirizzi obbligatori che mancano. Restituisce quanti indirizzi ha scritto.

La usano la creazione del cliente e del fornitore (`anagrafiche.fn_crea_cliente`, `anagrafiche.fn_crea_fornitore`) e
il builder dei ruoli dei test.

---

### ⭐ La copia del primo negli obbligatori

Ogni ruolo ha i suoi indirizzi **obbligatori**: per il cliente e per il fornitore, la fatturazione. Se chi crea il ruolo
ne indica uno solo, gli obbligatori che mancano nell'elenco ricevono una **copia del primo**: lo stesso indirizzo, col
tipo cambiato, una per tipo.

Sono obbligatori i tipi per cui `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo` risponde vero, sul tipo di
ruolo e sulla natura del soggetto, il giorno operativo. È lo stesso giudizio dei guard degli obbligatori e dei picker:

* una riga obbligatoria attiva e valida conta col suo tipo, se la natura lo ammette;
* se la natura non lo ammette, conta il suo **ripiego**, quando il ruolo e la natura ammettono quello;
* una riga scaduta, o una di cui la natura vieta tipo e ripiego, non fa nascere una copia, che i guard poi
  rifiuterebbero.

La copia la fa `anagrafiche.fn_indirizzi_con_obbligatori`, la stessa della plurale del soggetto: cambia solo la matrice
da cui si leggono gli obbligatori.

---

### Le righe

* **Ogni indirizzo passa dalla grammatica** di `anagrafiche.fn_indirizzo_elemento` (le tre forme, il tipo per id o per
  codice interno) e lo scrive la singolare, `anagrafiche.fn_crea_indirizzo_ruolo`, coi suoi controlli sul tipo.
* **Un tipo che il ruolo ha già si salta**: niente doppioni, nemmeno da una seconda chiamata. Conta solo l'indirizzo del
  ruolo, senza istanza: lo stesso tipo su un servizio del ruolo non fa saltare quello del ruolo.
* **L'istanza non si accetta**: la plurale scrive gli indirizzi del ruolo, e un elemento con `istanza_utility_id` si
  rifiuta come chiave estranea. L'indirizzo di un'istanza si scrive con la singolare.
* **Due indirizzi diversi restano diversi**: ognuno risolve la sua via e il suo civico.
* **Un elenco vuoto** non scrive niente, nemmeno le copie.

---

### Che cosa lascia agli altri

* **I campi di una via nuova** (tipo strada, nome, comune, CAP) non li controlla: arrivano ai vincoli dello stradario.
* **La forma dell'indirizzo libero** la dice il guard della tabella, con codice e campo.
* **Il permesso** lo decide l'applicazione.

---

### ⚠️ Che cosa oggi non copre

* **Il ripiego già nell'elenco.** Il guard degli obbligatori è soddisfatto dal tipo obbligatorio o dal suo ripiego, ma la
  copia guarda solo il tipo: se l'elenco porta il ripiego e non il tipo, nasce lo stesso la copia del tipo, cioè un
  indirizzo in più di quanti il ruolo ne debba avere.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — gli indirizzi non sono un elenco, o un elemento non è un oggetto.
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha, compresa l'istanza.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — il codice del tipo manca o non esiste.
* Dalla singolare e dai guard: i rifiuti sul tipo e sulla forma.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql` — la copia negli obbligatori letti dalla matrice, la
  seconda chiamata senza doppioni, l'elenco vuoto, le tre forme, due civici sulla stessa via, i rifiuti, il builder dei
  test che passa da qui.
* `db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` — il tipo che il ruolo ha solo su un'istanza, e
  l'istanza rifiutata nella plurale.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — l'obbligatorio scaduto, che non fa nascere la copia.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — l'obbligatorio che la natura vieta non si copia sul
  privato, e si copia sulla società.

---

### Note di migrazione

* 2026-10-17 — nasce, e prende il posto della creazione degli indirizzi fatta dall'applicazione, che riusava il
  dettaglio del primo indirizzo per tutti quelli dopo.
* 2026-10-18 — la grammatica dell'elemento passa nei building block comuni alla madre del soggetto.
* 2026-10-19 — le righe le scrive la singolare; il salto dei tipi presenti guarda solo gli indirizzi senza istanza
  (prima un indirizzo di un'istanza faceva saltare quello del ruolo, che poi non nasceva).

---

{% include-markdown "signature-core.md" %}
