## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_ruoli_conti_bancari`

> **Ultimo aggiornamento**: 27 novembre 2026
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
> * [anagrafiche.trgfn_conti_legami_guard_predefinito](/dbzero/anagrafiche/funzioni/trgfn_conti_legami_guard_predefinito) — il predefinito: uno per periodo, mai bloccato
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

L'istanza deve essere del soggetto del ruolo (`E_ISTANZA_ALTRO_SOGGETTO`), quando il legame nasce.

* **L'identità non si sposta.** Ruolo, istanza, conto e uso non si modificano (`E_CONTO_LEGAME_IMMUTABILE`,
  lucchetto di colonna): un legame sbagliato si chiude con la sua data di fine e se ne apre uno nuovo. Sull'istanza
  il lucchetto parla prima del guard dell'istanza (fase `a12`).
* **L'unicità** è sul ruolo, l'istanza, il conto e l'uso; due indici parziali la scrivono, uno per i legami con
  l'istanza e uno per quelli senza.
* **Il predefinito**: al più uno per ruolo, istanza e uso **in ogni giorno**, e al più uno per ruolo e uso fra i
  legami senza istanza: due predefiniti non hanno periodi che si sovrappongono, date comprese
  (`ex_src_bancari_predefinito_istanza_periodo`, `ex_src_bancari_predefinito_no_istanza_periodo`; il rifiuto parlante
  è `E_CONTO_PREDEFINITO_SOVRAPPOSTO`). Un cambio di conto programmato marca il nuovo legame dal suo primo giorno; il
  legame di un'istanza e quello di tutto il ruolo non si incontrano.
* **La validità** (`valido_dal`, `valido_al`) è facoltativa, e la fine non precede l'inizio.
* **Il blocco** (`bloccato`) toglie il legame dalla scelta del conto senza cancellarlo. Un predefinito non si blocca
  (`E_CONTO_PREDEFINITO_BLOCCATO`; `chk_soggetti_ruoli_conti_bancari_predefinito_non_bloccato` come rete).

---

### ⭐ Un conto d'incasso, un solo ruolo

Lo stesso conto con uso `INCASSO` non sta su due ruoli diversi (`ex_src_bancari_conto_incasso_un_solo_soggetto`). È il
pezzo su cui poggia il perimetro degli incassi: quando i soldi arrivano su un IBAN non hanno ancora una fattura, e di
chi sono lo dice il conto. Un canale di incasso (`pagamenti.enti_incasso`) nomina un legame di questa tabella, e il
suo guard pretende che l'uso sia `INCASSO`, e l'uso del legame non cambia dopo: è lì che l'unicità diventa il
perimetro.

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

Il conto del legame è attivo, al COMMIT, quando il legame nasce (`E_ATTIVO_PADRE_NON_ATTIVO`). Finché un legame
esiste, il conto non si spegne: il legame non ha un suo `attivo`, e conta che esista.

Un legame che un canale di incasso o un mandato SEPA nomina non si cancella: lo impediscono le loro chiavi esterne.

---

### Come lo legge la scelta del conto

La vista `vw_conti_bancari_per_ruolo` lo espone come candidata di fonte `RUOLO`, se valido nel giorno operativo (la
data di oggi nel fuso dell'azienda), non bloccato e su un conto attivo. La funzione di scelta guarda prima il legame
con l'istanza chiesta, poi quello senza istanza, poi il legame del soggetto, e ripete la cascata sull'uso `GENERICO`.

---

### ⚠️ Che cosa oggi non copre

* **Il soggetto del ruolo non deve essere attivo.** Il legame controlla il conto, non il soggetto: il gemello sul
  soggetto pretende il soggetto attivo, questo no. Che cosa vuol dire «un ruolo acceso» non è ancora scritto nel
  modello (il ruolo non ha `attivo`).
* **Un conto con legami chiusi non si spegne**: lo spegnimento conta i legami di qualunque validità.

---

### Codici errore

* `E_CONTO_LEGAME_IMMUTABILE` — ruolo, istanza, conto o uso del legame non si cambiano.
* `E_CONTO_PREDEFINITO_BLOCCATO` — un predefinito bloccato.
* `E_CONTO_PREDEFINITO_SOVRAPPOSTO` — due predefiniti dello stesso ruolo, istanza e uso in periodi che si
  sovrappongono.
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
* `db/pgtap/anagrafiche/test-conti-bancari-forma-e-legami-v1.sql` — l'istanza che non si cambia, il predefinito
  bloccato, i predefiniti sovrapposti, contigui e su due gradini, il legame su un conto spento.

---

### Note di migrazione

* 2026-03-25 — `istanza_utility_id` prende il posto del riferimento alla utility: il legame si restringe a una
  fornitura, non a un servizio.
* 2026-08-22 — nasce l'esclusione `ex_src_bancari_conto_incasso_un_solo_soggetto`, insieme al perimetro degli
  incassi che ci si appoggia.
* 2026-09-23 — il controllo delle date esce dal guard del legame e passa a `script.trgfn_guard_date_validita`.
* 2026-11-27 — il predefinito diventa uno per periodo (due EXCLUDE al posto dei due indici unici), mai bloccato;
  ruolo, istanza, conto e uso prendono il lucchetto; il guard immediato «conto attivo» si ritira, e resta il
  controllo al COMMIT.

---

{% include-markdown "signature-core.md" %}
