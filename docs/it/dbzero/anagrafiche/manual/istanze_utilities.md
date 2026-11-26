## 📘 Documentazione Concettuale – Tabella `anagrafiche.istanze_utilities`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il titolare della fornitura
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — uno per utility dell'istanza, nasce con lei
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — un cliente per billing account
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto fisico a cui l'istanza si lega
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il luogo della fornitura
> * [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali) — i dati tecnici per coppia (istanza, utility)
> * [anagrafiche.catasto_unita_immobiliari](/dbzero/anagrafiche/tabelle/catasto_unita_immobiliari) — l'unità catastale dell'istanza
>
> Approfondimento viste:
>
> * [anagrafiche.vw_istanze_utilities_dettaglio](/dbzero/anagrafiche/views/vw_istanze_utilities_dettaglio) — l'istanza con soggetto, PDP e indirizzo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — l'istanza nasce col suo billing account
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — un'istanza, un'azienda emittente
> * [anagrafiche.trgfn_clienti_set_parent_istanza](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) — chi scrive la catena `parent_istanza_id`
> * [anagrafiche.trgfn_clienti_sync_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_pdp) — il cliente copia il PDP dell'istanza
> * [anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_guard_clienti_chiave) — l'istanza che entra o esce dalle fittizie
> * [anagrafiche.trgfn_iu_sync_catasto_unita_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_iu_sync_catasto_unita_indirizzo) — il catasto segue l'indirizzo
> * [anagrafiche.trgfn_iu_clone_catasto_from_parent](/dbzero/anagrafiche/funzioni/trgfn_iu_clone_catasto_from_parent) — il catasto clonato dall'istanza precedente
> * [anagrafiche.trgfn_istanze_utilities_gen_codice](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_gen_codice) — il codice generato
>
> Guide:
>
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — il racconto del modello
> * [Generazione di un cliente](/guide/generazione-cliente) — come l'istanza diventa cliente

---

### 🎯 Scopo Principale

`anagrafiche.istanze_utilities` registra una fornitura: un soggetto, in un luogo, con una o più utility. È il
punto di giunzione a cui si agganciano billing account, clienti, dati precontrattuali, indirizzi, contatti,
conti, pratiche e documenti di vendita.

---

### Un'istanza ha un billing account per utility, e un cliente per billing account

Le utility di un'istanza non stanno sulla riga: le dichiarano i suoi billing account, uno per utility. Un
cliente è di un billing account (`uq_clienti_billing_account`), e un'istanza ha quindi tanti clienti quante
sono le sue utility attivate, nel tempo anche di più.

* **L'istanza nasce col suo billing account.** Al COMMIT un'istanza appena nata deve averne almeno uno
  (`E_ISTANZA_SENZA_BA`). Dopo non lo perde: un billing account non si cancella (`E_BA_NON_SI_CANCELLA`, il
  suo cliente si annulla) e non passa a un'altra istanza (`E_BA_ISTANZA_IMMUTABILE`).
* **Un'istanza, un'azienda.** I billing account di un'istanza sono tutti della stessa azienda emittente.
* **Sullo stesso PDP non si sovrappongono due clienti.** Lo dice l'esclusione per periodo
  `ex_clienti_no_overlap_stesso_pdp` su `clienti`, non un vincolo dell'istanza: due istanze possono puntare
  allo stesso PDP, con clienti in periodi diversi.

---

### ⛔ La fornitura non cambia titolare

Il soggetto dell'istanza è bloccato (`E_ISTANZA_SOGGETTO_IMMUTABILE`), come il codice
(`E_CODICE_NON_MODIFICABILE`). Un nuovo intestatario è una nuova istanza, il subentro; una fornitura creata
sul soggetto sbagliato si annulla e si ricrea. Su questo blocco si appoggiano i guard che chiedono «questa
istanza è dello stesso soggetto della riga?» su indirizzi, conti del ruolo, contatti e billing account: dato
che il soggetto dell'istanza non cambia, basta giudicare la riga che si scrive.

Il soggetto deve essere attivo, e così l'indirizzo, alla nascita e a ogni cambio della colonna: i due
controlli sono differiti al COMMIT.

---

### Istanza vera e istanza fittizia

* Un'istanza **vera** (`fittizia = false`) ha sempre un indirizzo (`chk_istanza_fittizia_indirizzo`).
* Un'istanza **fittizia** nasce per la creazione manuale del cliente, senza un luogo da dichiarare:
  l'indirizzo può mancare, e non può avere un PDP (`chk_iu_pdp_not_fittizia`).
* Il passaggio fra le due rigiudica al COMMIT la chiave unica dei clienti dell'istanza, perché fra le
  fittizie vale la regola «un cliente manuale per soggetto, utility e azienda».

`proprietario_inquilino` dice se il titolare occupa il luogo da proprietario (`P`) o da inquilino (`I`, il
default).

---

### Il PDP è dello stesso indirizzo

`pdp_id` è facoltativo e, quando c'è, richiede l'indirizzo (`chk_iu_pdp_requires_address`). La chiave
esterna composta `fk_iu_pdp_id_addr` lo lega alla coppia (PDP, indirizzo): il PDP collegato è per forza
quello del luogo dell'istanza. Con un PDP per utility e indirizzo (`uq_pdp_addr_utility`), un luogo ha al più
un PDP per ogni utility.

Il collegamento non giudica la utility né lo stato del PDP: che il PDP sia della utility del cliente lo
controlla la scrittura del cliente, che copia il PDP dell'istanza sulla sua riga. Lo stato del PDP lo
ricalcola la scrittura del cliente, dall'occupazione per periodo.

---

### La catena delle istanze

`parent_istanza_id` lega un'istanza a quella che l'ha preceduta. Non la sceglie chi scrive l'istanza: la
riscrive il trigger dei clienti a ogni nascita del cliente e a ogni cambio del suo PDP o della sua data di
attivazione.

* **Con un PDP**, la precedente è l'istanza del cliente più recente sullo stesso PDP, attivato non dopo.
* **Su un'istanza fittizia**, è l'ultima istanza con la stessa chiave soggetto, utility e azienda.
* **Su un'istanza vera senza PDP**, la catena non si tocca.
* Un cliente annullato o senza data di attivazione toglie la sua istanza dalla catena.

---

### Il catasto dell'istanza

Un'unità catastale è di un'istanza sola: lo scrive l'indice unico parziale
`uq_istanze_utilities_catasto_unita_immobiliare`, sulle sole righe con l'unità. Un'istanza senza unità è
ammessa, e l'indice copre anche la chiave esterna verso `catasto_unita_immobiliari`.

Quattro trigger, dopo la scrittura, fanno seguire il catasto all'istanza:

* `trg_istanze_utilities_z40_sync_catasto_unita_indirizzo_ins` e `_upd` — alla nascita con unità e civico, e al
  cambio di unità o di civico, la ponte fra unità e civici segue l'istanza: la coppia di prima esce, l'unità che
  nessuno nomina più si cancella, la coppia nuova entra.
* `trg_istanze_utilities_z50_clone_catasto_from_parent_ins` e `_upd` — quando nasce il legame con l'istanza
  precedente (alla nascita con la precedente già scritta, o al cambio della precedente), l'istanza senza unità e
  col civico riceve una copia dell'unità della precedente. Una riscrittura uguale della precedente non clona.

Il racconto del catasto sta nella guida [Il catasto delle istanze](/guide/catasto-delle-istanze).

---

### Il codice

Il codice si genera dalla configurazione `istanze_utilities` di `config.sistema_codici` quando chi scrive non
lo passa, si salva nella forma normalizzata (maiuscolo) ed è unico (`uq_istanze_utilities_codice`).

---

### ⚠️ Che cosa oggi non copre

* **Niente vieta che un'istanza sia la precedente di sé stessa.** La chiave esterna di `parent_istanza_id`
  non esclude la riga stessa, e una scrittura diretta della colonna passa; il trigger dei clienti la
  riscrive solo alla prossima scrittura di un cliente dell'istanza.
* **Il PDP dell'istanza non è bloccato, e il cliente non lo vede cambiare.** Un cambio di `pdp_id` dopo la
  nascita del cliente arriva sulla riga del cliente, e sullo stato dei PDP, solo alla sua prossima scrittura.
* **La cancellazione dell'istanza non tocca la sua unità catastale**, che resta senza nessuno che la nomini.
* **Nessuno storico.** La tabella non ha il trigger di storico: una modifica dell'istanza (indirizzo, PDP,
  catena) non lascia la versione di prima.
* **Un trigger che non fa niente.** `trgfn_istanze_utilities_normalize` scatta a ogni scrittura e restituisce
  la riga com'è.
* **Le chiavi esterne non dicono che cosa succede alla cancellazione.** Hanno solo `ON UPDATE CASCADE`: la
  cancellazione di un'istanza ancora nominata da un'altra tabella la ferma la chiave esterna della figlia,
  con un errore tecnico e non con un codice di catalogo.

---

### Codici errore

* `E_ISTANZA_SENZA_BA` — al COMMIT, un'istanza appena nata senza billing account.
* `E_ISTANZA_SOGGETTO_IMMUTABILE` — cambio del soggetto.
* `E_CODICE_NON_MODIFICABILE` — cambio del codice.

---

### Test

* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql` — l'istanza senza BA, il BA che non si cancella
  (né l'ultimo, né insieme all'istanza: `E_BA_NON_SI_CANCELLA`), un'istanza un'azienda, la coppia bloccata.
* `db/pgtap/anagrafiche/test-create-istanza-from-pdp.sql` — l'istanza legata al PDP del suo indirizzo.
* `db/pgtap/anagrafiche/test-istanza-cliente-chain.sql` — la catena delle istanze sullo stesso PDP.
* `db/pgtap/anagrafiche/test-simula-subentro.sql` — il subentro: nuova istanza sullo stesso PDP, la catena e
  il catasto clonato.
* `db/pgtap/anagrafiche/test-catasto-unita-della-sua-istanza-v1.sql` — un'unità per istanza, il clone quando
  nasce il legame con la precedente, la ponte e l'unità lasciata che seguono l'istanza.

---

### Note di migrazione

* 2026-10-08 — l'istanza nasce col suo billing account; prima bastava un satellite qualunque fra BA, dati
  precontrattuali e cliente.
* 2026-10-14 — la catena vale anche fra le istanze fittizie, per chiave soggetto, utility e azienda.
* 2026-11-25 — un'unità catastale per istanza, con un indice unico; i trigger del catasto scattano al cambio di
  valore, il clone anche alla nascita, e prendono i nomi `trg_istanze_utilities_z40_…` e `trg_istanze_utilities_z50_…`.
* Il modello «un'istanza, al massimo un cliente», con un vincolo unico sull'istanza in `clienti`, non c'è
  più: il vincolo unico del cliente è sul billing account.

---

{% include-markdown "signature-core.md" %}
