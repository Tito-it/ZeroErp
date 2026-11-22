## 📘 Documentazione Concettuale – Tabella `anagrafiche.bank_branches`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `BANK_B` della banca, a cui la filiale appartiene
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — i conti, che nominano tutti una filiale
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali di incasso, che nominano la filiale
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_bank_guard_ruolo_bank_branches](/dbzero/anagrafiche/funzioni/trgfn_bank_guard_ruolo_bank_branches) — il ruolo della filiale è una banca
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — una filiale usata non si spegne
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — una filiale non si cancella
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — il registro degli IBAN e i suoi legami

---

### 🎯 Scopo Principale

`anagrafiche.bank_branches` è il catalogo delle filiali delle banche: ogni riga è uno sportello, col suo codice
banca, il suo codice filiale e il suo BIC, sotto il ruolo «istituto di credito» del soggetto che è la banca.

---

### La banca è un ruolo, la filiale è una sua riga

Una banca è un soggetto come gli altri, con il ruolo `BANK_B` («istituti di credito»). Le sue filiali stanno qui,
e ognuna nomina quel ruolo con `soggetto_ruolo_id`: il guard di ruolo rifiuta un ruolo di altro tipo. È l'unica
specializzazione di ruolo in cui più righe stanno sotto lo stesso ruolo: una banca ha tutte le sue filiali.

La filiale è identificata dal ruolo della banca più la coppia codice banca e codice filiale
(`uq_bank_branches_soggetto_ruolo_bank_branch_code`). In Italia i due codici sono l'ABI e il CAB; il modello non
li lega a un formato, e vale per qualunque paese. Il BIC è facoltativo, e quando c'è ha 8 o 11 caratteri
maiuscoli (`check_bank_branches_bic_swift_fmt`). `name` è la descrizione completa, banca e filiale, per le
schermate e le stampe.

---

### Chi la usa

* **I conti bancari.** Ogni conto nomina la sua filiale, obbligatoriamente: un IBAN non entra nel registro senza
  la banca che lo tiene.
* **I canali di incasso** (`pagamenti.enti_incasso`), che nominano la filiale su cui arrivano i soldi.

---

### ⛔ Una filiale usata non si spegne, e nessuna si cancella

* **Lo spegnimento.** `attivo` toglie la filiale dall'uso senza perderla. Non si spegne finché un conto **attivo**
  o un canale di incasso **attivo** la nomina (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`): prima si spengono loro. Dal verso
  opposto, un conto attivo non si scrive su una filiale spenta: lo controlla il conto, al COMMIT.
* **La cancellazione.** È rifiutata sempre, salvo che la sessione abbia acceso l'interruttore di manutenzione dei
  ruoli: la filiale è un dato che altri nominano, e il suo ritiro è lo spegnimento.

---

### ⚠️ Che cosa oggi non copre

* **Il BIC non si normalizza.** Un BIC scritto in minuscolo, o con uno spazio, è rifiutato dal vincolo di formato:
  la tabella non ha la normalizzazione che i conti hanno.
* **La filiale e il conto non si confrontano.** Nessun controllo lega il codice banca e il codice filiale ai
  caratteri dell'IBAN che li portano, né il BIC della filiale a quello del conto.
* **Lo stesso codice banca su due banche.** L'unicità è per ruolo: la stessa coppia di codici sotto due soggetti
  diversi è ammessa.

---

### Test

* `db/pgtap/anagrafiche/create-soggetto-bank-branches.sql` — un soggetto banca col ruolo `BANK_B` e una sua
  filiale, attiva, coi codici attesi.
* `dbops.fn_pgtap_crea_filiale_bancaria` è l'aiuto con cui le altre prove costruiscono la filiale su cui agganciare
  i loro conti.

---

### Note di migrazione

* 2026-11-14 — l'indice dedicato a `soggetto_ruolo_id` è tolto: lo serve il vincolo unico, che comincia con quella
  colonna.

---

{% include-markdown "signature-core.md" %}
