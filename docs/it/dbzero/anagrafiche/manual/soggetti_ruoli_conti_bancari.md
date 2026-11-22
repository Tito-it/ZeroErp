## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_ruoli_conti_bancari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — il registro degli IBAN, da cui il legame prende il conto
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo del legame
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza di servizio, facoltativa, a cui il legame si restringe
> * [anagrafiche.soggetti_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_conti_bancari) — il legame gemello, sul soggetto, su cui si ricade
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — i canali di incasso, che nominano un legame d'incasso
> * [pagamenti.sepa_mandati](/dbzero/pagamenti/tabelle/sepa_mandati) — i mandati SEPA, che nominano il legame del conto addebitato
>
> Approfondimento viste:
>
> * [anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/views/vw_conti_bancari_per_ruolo) — le candidate di ogni ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_conti_bancari_guard) — il conto del legame è attivo
> * [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/funzioni/trgfn_guard_istanza_del_ruolo) — l'istanza è del soggetto del ruolo
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — la fine della validità non precede l'inizio
> * [script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito) — la scelta del conto, che parte da qui
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i due legami e la scelta del conto

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_ruoli_conti_bancari` lega un conto del registro a un ruolo del soggetto, per un uso, e se serve
a una sua istanza di servizio. Quando c'è, ha la precedenza sul legame del soggetto.

---

### Il ruolo, e se serve l'istanza

Il legame nomina il ruolo (il cliente, il fornitore, il gestore…) e l'uso del conto (`INCASSO`, `PAGAMENTO`,
`RIMBORSO`, `GENERICO`, che è il default). `istanza_utility_id`, facoltativa, lo restringe a un'istanza di servizio:
due forniture dello stesso cliente possono incassare su conti diversi. Senza istanza il legame vale per il ruolo in
generale.

L'istanza deve essere del soggetto del ruolo (`E_ISTANZA_ALTRO_SOGGETTO`), quando il legame nasce o cambia ruolo o
istanza.

* **L'unicità** è sul ruolo, l'istanza, il conto e l'uso; due indici parziali la scrivono, uno per i legami con
  l'istanza e uno per quelli senza.
* **Il predefinito**: al più uno per ruolo, istanza e uso, e al più uno per ruolo e uso fra i legami senza istanza.
  Il database non lo sposta da solo.
* **La validità** (`valido_dal`, `valido_al`) è facoltativa, e la fine non precede l'inizio. Non entra
  nell'unicità del predefinito.
* **Il blocco** (`bloccato`) toglie il legame dalla scelta del conto senza cancellarlo.

---

### ⭐ Un conto d'incasso, un solo ruolo

Lo stesso conto con uso `INCASSO` non sta su due ruoli diversi (`ex_src_bancari_conto_incasso_un_solo_soggetto`). È il
pezzo su cui poggia il perimetro degli incassi: quando i soldi arrivano su un IBAN non hanno ancora una fattura, e di
chi sono lo dice il conto. Un canale di incasso (`pagamenti.enti_incasso`) nomina un legame di questa tabella, e il
suo guard pretende che l'uso sia `INCASSO`: è lì che l'unicità diventa il perimetro.

* È un'**esclusione**, non un indice unico: lo stesso conto d'incasso sullo stesso ruolo, una volta in generale e
  una per un'istanza, resta ammesso, come gli indici di unicità dichiarano.
* Il vincolo nomina il **ruolo**, non il soggetto, ed è più stretto del suo nome: lo stesso IBAN come conto d'incasso
  su due ruoli dello stesso soggetto è rifiutato, pur essendo la stessa azienda. Allentarlo è una decisione di
  dominio.
* La validità non entra nel vincolo: un IBAN non passa di mano.

Il gemello sul legame del soggetto presidia la sua tabella; i due non si incrociano. È voluto: il perimetro legge
solo questa tabella.

---

### Il conto è attivo

Il conto del legame è attivo, prima della scrittura (`E_CONTO_BANCARIO`, dal guard) e di nuovo al COMMIT. Finché un
legame esiste, il conto non si spegne: il legame non ha un suo `attivo`, e conta che esista.

Un legame che un canale di incasso o un mandato SEPA nomina non si cancella: lo impediscono le loro chiavi esterne.

---

### Come lo legge la scelta del conto

La vista `vw_conti_bancari_per_ruolo` lo espone come candidata di fonte `RUOLO`, se valido nel giorno operativo (la
data di oggi nel fuso dell'azienda), non bloccato e su un conto attivo. La funzione di scelta guarda prima il legame
con l'istanza chiesta, poi quello senza istanza, poi il legame del soggetto, e ripete la cascata sull'uso `GENERICO`.

---

### ⚠️ Che cosa oggi non copre

* **L'uso cambia sotto il canale di incasso.** Il guard del canale guarda l'uso quando il canale nasce o cambia
  legame; l'uso del legame si può poi modificare, e il canale resta appeso a un legame che non è più d'incasso,
  fuori dall'esclusione.
* **Il soggetto del ruolo non deve essere attivo.** Il legame controlla il conto, non il soggetto: il gemello sul
  soggetto pretende il soggetto attivo, questo no.
* **Un predefinito bloccato.** Niente nel database impedisce di bloccare il legame predefinito: la scelta del conto
  lo salta e ricade sugli altri.
* **Il predefinito a scadenza.** Il predefinito è uno solo, valido o no: un cambio di conto programmato non può
  marcare il nuovo legame finché il vecchio porta il segno.

---

### Codici errore

* `E_CONTO_BANCARIO` — il conto è spento o non esiste.
* `E_ISTANZA_ALTRO_SOGGETTO` — l'istanza è di un altro soggetto.
* `E_DATA_AL_MINORE_DAL` — la fine della validità precede l'inizio.
* `E_ATTIVO_PADRE_NON_ATTIVO` — al COMMIT, il conto è spento.

---

### Test

* `db/pgtap/anagrafiche/test-conto-incasso-un-solo-soggetto.sql` — lo stesso conto d'incasso sul ruolo di un secondo
  soggetto rifiutato, sullo stesso ruolo per un'istanza ammesso, su un uso diverso ammesso.
* `db/pgtap/anagrafiche/test-conti-bancari-istanza-cascata.sql` — i predefiniti con e senza istanza, la cascata della
  scelta.
* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — l'istanza di un altro soggetto rifiutata.
* `db/pgtap/anagrafiche/create-gestore-conto-bancario.sql` — un legame d'incasso predefinito sul ruolo di un gestore.

---

### Note di migrazione

* 2026-03-25 — `istanza_utility_id` prende il posto del riferimento alla utility: il legame si restringe a una
  fornitura, non a un servizio.
* 2026-08-22 — nasce l'esclusione `ex_src_bancari_conto_incasso_un_solo_soggetto`, insieme al perimetro degli
  incassi che ci si appoggia.
* 2026-09-23 — il controllo delle date esce dal guard del legame e passa a `script.trgfn_guard_date_validita`.

---

{% include-markdown "signature-core.md" %}
