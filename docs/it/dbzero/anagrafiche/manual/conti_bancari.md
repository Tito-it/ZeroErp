## 📘 Documentazione Concettuale – Tabella `anagrafiche.conti_bancari`

> **Ultimo aggiornamento**: 27 novembre 2026
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
> * [anagrafiche.trgfn_conti_bancari_normalize](/dbzero/anagrafiche/funzioni/trgfn_conti_bancari_normalize) — IBAN e BIC normalizzati, il paese sempre dall'IBAN
> * [anagrafiche.trgfn_conti_bancari_guard_iban_filiale](/dbzero/anagrafiche/funzioni/trgfn_conti_bancari_guard_iban_filiale) — l'IBAN porta banca e filiale della sua filiale
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

### L'IBAN è unico, normalizzato, e non cambia

Prima di ogni altro controllo (fase `a01`) `anagrafiche.trgfn_conti_bancari_normalize` porta IBAN e BIC nella forma
di confronto di `script.fn_normalizza_codice_bancario`: senza spazi, trattini o altri separatori, in maiuscolo, il
vuoto `NULL`. Il paese è sempre le prime due lettere dell'IBAN: un paese diverso mandato da chi scrive si
sovrascrive. Poi i vincoli giudicano il valore normalizzato:

* l'IBAN è unico nel registro (`uq_conti_bancari_iban`), da 15 a 34 caratteri alfanumerici
  (`chk_conti_bancari_iban_fmt`);
* il BIC, se c'è, ha 8 o 11 caratteri (`chk_conti_bancari_bic_fmt`);
* il paese ha due lettere (`chk_conti_bancari_paese_fmt`).

L'IBAN non si modifica (`E_CONTO_BANCARIO_IBAN_IMMUTABILE`, lucchetto di colonna): un IBAN sbagliato è un altro
conto. Il lucchetto confronta il valore già normalizzato, quindi riscrivere lo stesso IBAN con gli spazi passa.

Dove l'IBAN porta il codice della banca e quello della filiale, sono quelli della filiale del conto
(`E_CONTO_IBAN_FILIALE_INCOERENTE`, `anagrafiche.trgfn_conti_bancari_guard_iban_filiale`), alla nascita e quando
cambia la filiale. Dove stanno lo dichiara lo stato dell'IBAN (`config.stati.iban_pos_*`, oggi Italia e San Marino);
uno stato che non lo dichiara non si confronta.

Non si controlla la cifra di controllo dell'IBAN, né che il paese esista.

---

### Lo stato del conto e quello che lo circonda

`attivo` toglie il conto dall'uso senza cancellarlo. La regola corre in tre direzioni:

* **Un conto legato non si spegne.** Basta che un legame col soggetto o col ruolo esista, di qualunque validità:
  i legami non hanno un loro `attivo`, e lo spegnimento è rifiutato (`E_ATTIVO_BLOCK_CHILDREN_EXIST`) finché non
  sono tolti.
* **Un legame vuole un conto attivo**, controllato al COMMIT (`E_ATTIVO_PADRE_NON_ATTIVO`, l'automazione ATTIVO
  sui due legami).
* **Un conto attivo sta su una filiale attiva**: il controllo è al COMMIT, quando il conto nasce attivo, si
  riaccende o cambia filiale (`E_ATTIVO_PADRE_NON_ATTIVO`). Dal lato della filiale, una filiale con conti attivi
  non si spegne.

La vista dei conti candidati e la funzione di scelta tengono solo i conti attivi.

La cancellazione di un conto legato è rifiutata dalle chiavi esterne dei legami. Ogni modifica e cancellazione
lascia la versione precedente nello storico, quando `storicizza` è acceso.

---

### ⚠️ Che cosa oggi non copre

* **Un conto con legami chiusi non si spegne**: lo spegnimento conta i legami di qualunque validità.
* **L'IBAN di uno stato che non dichiara banca e filiale** non si confronta con la filiale.

---

### Codici errore

* `E_ATTIVO_BLOCK_CHILDREN_EXIST` — lo spegnimento di un conto che ha legami.
* `E_ATTIVO_PADRE_NON_ATTIVO` — al COMMIT, un conto attivo su una filiale spenta, o un legame su un conto spento.
* `E_CONTO_BANCARIO_IBAN_IMMUTABILE` — l'IBAN di un conto non si cambia.
* `E_CONTO_IBAN_FILIALE_INCOERENTE` — l'IBAN non porta banca e filiale della filiale del conto.

---

### Test

* `db/pgtap/anagrafiche/create-gestore-conto-bancario.sql` — un conto sulla sua filiale, legato al ruolo di un
  gestore: attivo, non verificato, con l'IBAN atteso.
* `db/pgtap/anagrafiche/create-gestore-conto-soggetto.sql` — lo stesso, legato al soggetto.
* `db/pgtap/anagrafiche/test-conti-bancari-forma-e-legami-v1.sql` — la normalizzazione e il paese, il lucchetto
  dell'IBAN (e lo stesso IBAN riscritto con gli spazi), l'IBAN contro la filiale nei due versi, un IBAN estero non
  confrontato, il legame su un conto spento.
* Nessun test prova il rifiuto dello spegnimento.

---

{% include-markdown "signature-core.md" %}
