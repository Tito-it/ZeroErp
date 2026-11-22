## 📘 Documentazione Concettuale – Tabella `anagrafiche.conti_bancari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.bank_branches](/dbzero/anagrafiche/tabelle/bank_branches) — la filiale che tiene il conto, obbligatoria
> * [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari) — il legame del conto col soggetto
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il legame del conto col ruolo
> * [pagamenti.sepa_mandati](/dbzero/pagamenti/tabelle/sepa_mandati) — i mandati, che si agganciano al legame del ruolo
>
> Approfondimento viste:
>
> * [anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/views/vw_conti_bancari_per_ruolo) — i conti candidati di ogni ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_conti_bancari_normalize](/dbzero/anagrafiche/funzioni/trgfn_conti_bancari_normalize) — IBAN e BIC normalizzati, il paese dall'IBAN
> * [script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito) — il conto da usare per un ruolo, un uso e un'istanza
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — un conto legato non si spegne
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — un conto attivo sta su una filiale attiva
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — il modello intero, dalla registrazione alla scelta del conto

---

### 🎯 Scopo Principale

`anagrafiche.conti_bancari` è il registro unico degli IBAN: ogni conto corrente esiste una volta sola, normalizzato,
qualunque sia il numero di soggetti e di ruoli che lo usano.

---

### Il registro sa che cos'è il conto, non di chi è

La riga porta i dati del conto: l'IBAN, il BIC, l'intestatario da mostrare, il paese, la filiale che lo tiene. Chi
lo usa e per che cosa lo dicono i due legami, col soggetto e col ruolo; il conto non nomina nessuno dei due. Così lo
stesso IBAN, se lo usano due soggetti per pagare, è una riga sola con due legami.

* **La filiale è obbligatoria.** `bank_branch_id` nomina la filiale che tiene il conto: un IBAN entra nel registro
  insieme alla sua banca.
* **`verificato`** è l'esito di una verifica del conto (un micro-bonifico, una conferma della banca), che il
  database non fa: lo scrive chi l'ha fatta.
* **`intestatario_predefinito`** è il nome da mostrare; un legame può dichiararne un altro.

---

### L'IBAN è unico e normalizzato

Prima di ogni scrittura `anagrafiche.trgfn_conti_bancari_normalize` toglie gli spazi e porta in maiuscolo IBAN e
BIC, e ricava il paese dalle prime due lettere dell'IBAN quando chi scrive non lo passa. Poi i vincoli giudicano il
valore normalizzato:

* l'IBAN è unico nel registro (`uq_conti_bancari_iban`), da 15 a 34 caratteri alfanumerici
  (`chk_conti_bancari_iban_fmt`);
* il BIC, se c'è, ha 8 o 11 caratteri (`chk_conti_bancari_bic_fmt`);
* il paese, se c'è, ha due lettere (`chk_conti_bancari_paese_fmt`).

Il formato è tutto quello che si controlla: né la cifra di controllo dell'IBAN né l'esistenza del paese.

---

### Lo stato del conto e quello che lo circonda

`attivo` toglie il conto dall'uso senza cancellarlo. La regola corre in tre direzioni:

* **Un conto legato non si spegne.** Basta che un legame col soggetto o col ruolo esista, di qualunque validità:
  i legami non hanno un loro `attivo`, e lo spegnimento è rifiutato (`E_ATTIVO_BLOCK_CHILDREN_EXIST`) finché non
  sono tolti.
* **Un legame non si scrive su un conto spento** (`E_CONTO_BANCARIO`): lo dicono i guard dei due legami.
* **Un conto attivo sta su una filiale attiva**: il controllo è al COMMIT, quando il conto nasce attivo, si
  riaccende o cambia filiale (`E_ATTIVO_PADRE_NON_ATTIVO`). Dal lato della filiale, una filiale con conti attivi
  non si spegne.

La vista dei conti candidati e la funzione di scelta tengono solo i conti attivi.

La cancellazione di un conto legato è rifiutata dalle chiavi esterne dei legami. Ogni modifica e cancellazione
lascia la versione precedente nello storico, quando `storicizza` è acceso.

---

### ⚠️ Che cosa oggi non copre

* **Il paese non segue l'IBAN.** Si ricava solo quando manca: cambiato l'IBAN, il paese resta quello di prima, e un
  paese passato da chi scrive non è confrontato con le prime due lettere dell'IBAN.
* **«Il conto è attivo» sta in due sedi.** Il legame su un conto spento lo rifiuta il suo guard, prima della
  scrittura; il controllo differito montato sugli stessi legami dice la stessa cosa al COMMIT, e così non parla
  mai per primo.
* **L'IBAN si modifica sotto i legami.** Nessun blocco protegge l'IBAN di un conto già legato: cambiarlo cambia il
  conto di tutti i soggetti e i ruoli che lo usano.
* **La filiale e l'IBAN non si confrontano.** Il codice banca e il codice filiale della filiale non sono
  confrontati con i caratteri dell'IBAN che li portano.

---

### Codici errore

* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — lo spegnimento di un conto che ha legami.
* `E_ATTIVO_PADRE_NON_ATTIVO` — al COMMIT, un conto attivo su una filiale spenta.

---

### Test

* `db/pgtap/anagrafiche/create-gestore-conto-bancario.sql` — un conto sulla sua filiale, legato al ruolo di un
  gestore: attivo, non verificato, con l'IBAN atteso.
* `db/pgtap/anagrafiche/create-gestore-conto-soggetto.sql` — lo stesso, legato al soggetto.
* Nessun test prova la normalizzazione, il rifiuto dello spegnimento o il controllo della filiale.

---

{% include-markdown "signature-core.md" %}
