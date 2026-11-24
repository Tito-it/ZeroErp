## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzi_ruolo`

> **Ultimo aggiornamento**: 24 novembre 2026
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
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — il requisito del ruolo, col tipo richiesto e il ripiego
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
ne indica uno solo, gli obbligatori che mancano davvero ricevono una **copia del primo**: lo stesso indirizzo, col
tipo cambiato, una per tipo.

I tipi obbligatori li dice il requisito del ruolo, `anagrafiche.fn_indirizzi_obbligatori_ruolo`, sul tipo di ruolo e
sulla natura del soggetto, il giorno operativo: per ogni riga il tipo richiesto e il ripiego che lo sostituisce. È lo
stesso giudizio dei guard degli obbligatori e dei picker:

* una riga obbligatoria attiva e valida conta col suo tipo, se la natura lo ammette;
* se la natura non lo ammette, conta il suo **ripiego**, quando il ruolo e la natura ammettono quello;
* una riga scaduta, o una di cui la natura vieta tipo e ripiego, non fa nascere una copia, che i guard poi
  rifiuterebbero;
* un tipo il cui ripiego è già nell'elenco, o sul ruolo senza istanza, non si copia: il ruolo ha già ciò che la riga
  chiede, e una copia sarebbe un indirizzo che nessuno ha chiesto. Lo stesso vale per un tipo che l'elenco o il ruolo
  senza istanza hanno già.

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

* **I campi di una via nuova** (tipo strada, nome, comune, CAP) li controlla `anagrafiche.fn_create_indirizzo`, a cui
  la via arriva dall'elemento: ogni campo che manca è `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA`, col campo.
* **La forma dell'indirizzo libero** la dice il guard della tabella, con codice e campo.
* **Il permesso** lo decide l'applicazione.

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — gli indirizzi non sono un elenco, o un elemento non è un oggetto.
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha, compresa l'istanza.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — il tipo manca, o l'id o il codice detti non esistono (un id non numerico compreso).
* `E_TIPO_INDIRIZZO_DISCORDE` — l'id e il codice del tipo dicono due tipi diversi.
* `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` — a una via nuova manca un campo.
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
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (12, 13, 14, 17, 18, 19) — l'elemento vuoto o col
  solo tipo, la via nuova senza toponomastica, il tipo che non esiste, non numerico o discorde dal codice.

---

### Note di migrazione

* 2026-10-17 — nasce, e prende il posto della creazione degli indirizzi fatta dall'applicazione, che riusava il
  dettaglio del primo indirizzo per tutti quelli dopo.
* 2026-10-18 — la grammatica dell'elemento passa nei building block comuni alla madre del soggetto.
* 2026-10-19 — le righe le scrive la singolare; il salto dei tipi presenti guarda solo gli indirizzi senza istanza
  (prima un indirizzo di un'istanza faceva saltare quello del ruolo, che poi non nasceva).
* 2026-11-24 — i tipi da copiare vengono dal requisito del ruolo, senza quelli il cui ripiego è nell'elenco o sul ruolo
  senza istanza: prima si copiava il tipo anche col ripiego già presente.

---

{% include-markdown "signature-core.md" %}
