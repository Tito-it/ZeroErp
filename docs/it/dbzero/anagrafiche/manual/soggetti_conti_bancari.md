## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_conti_bancari`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.conti_bancari](/dbzero/anagrafiche/tabelle/conti_bancari) — il registro degli IBAN, da cui il legame prende il conto
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto del legame
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il legame gemello, sul ruolo, che ha la precedenza
>
> Approfondimento viste:
>
> * [anagrafiche.vw_conti_bancari_per_ruolo](/dbzero/anagrafiche/views/vw_conti_bancari_per_ruolo) — dove il legame del soggetto diventa una candidata di ogni suo ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_conti_bancari_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_conti_bancari_guard) — il conto del legame è attivo
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — la fine della validità non precede l'inizio
> * [script.fn_get_conto_bancario_predefinito](/dbzero/script/funzioni/fn_get_conto_bancario_predefinito) — la scelta del conto, che ricade qui quando il ruolo non ne ha
>
> Guide:
>
> * [Gestione dei conti bancari](/guide/gestione-conti-bancari) — i due legami e la scelta del conto

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_conti_bancari` lega un conto del registro a un soggetto, per un uso: incassare, pagare,
rimborsare, o in generale. È il livello di base: vale per tutti i ruoli del soggetto, quando il ruolo non ha un
legame suo.

---

### Un legame, un uso

La riga dice che il soggetto usa quel conto per quell'uso (`INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO`, che è il
default). Lo stesso conto può stare sullo stesso soggetto con usi diversi, una riga per uso: la terna soggetto,
conto e uso è unica (`uq_soggetti_conti_bancari_soggetto_id_conto_id_uso`).

* **Il predefinito.** Per ogni soggetto e uso c'è al più un legame predefinito
  (`ix_soggetti_conti_bancari_predef_per_uso`). Il database non lo sposta da solo: per cambiarlo si toglie il segno
  al vecchio e lo si mette al nuovo, in quest'ordine.
* **La validità.** `valido_dal` e `valido_al` sono facoltativi, e la fine non precede l'inizio. La validità non
  entra nell'unicità del predefinito: un predefinito già scaduto, o non ancora in vigore, occupa comunque il posto.
* **Il blocco.** `bloccato` toglie il legame dalla scelta del conto senza cancellarlo (un blocco per compliance).
* **`intestazione_dichiarata`** è l'intestazione che il soggetto dichiara, quando diversa da quella del conto;
  **`verificato`** è l'esito di una verifica del legame, che il database non fa.

---

### ⭐ Un conto d'incasso, un solo soggetto

Lo stesso conto con uso `INCASSO` non sta su due soggetti diversi (`ex_scb_conto_incasso_un_solo_soggetto`). Quando
i soldi arrivano su un IBAN non hanno ancora una fattura: di chi sono lo dice il conto, e il conto deve avere un
padrone solo.

* È un'**esclusione**, non un indice unico: lo stesso conto d'incasso sullo stesso soggetto resta ammesso (con
  validità o intestazioni diverse); è vietato il soggetto **diverso**.
* Vale solo per l'incasso: un conto di pagamento può stare su più soggetti.
* La validità non entra nel vincolo: un IBAN non passa di mano, e la risposta a «di chi sono questi soldi» non
  cambia con la data.

Il gemello sul legame del ruolo, `ex_src_bancari_conto_incasso_un_solo_soggetto`, presidia la sua tabella, ed è
quello su cui poggia il perimetro degli incassi. Ognuno dei due guarda la propria: un conto d'incasso sul
soggetto A e lo stesso conto d'incasso su un ruolo del soggetto B non si incontrano. È voluto: i canali di incasso
leggono solo il legame del ruolo, e una riga a livello soggetto non può confonderli.

---

### Il soggetto e il conto sono attivi

* Il conto del legame è attivo, prima della scrittura (`E_CONTO_BANCARIO`, dal guard) e di nuovo al COMMIT.
* Il soggetto è attivo, al COMMIT, quando il legame nasce o cambia soggetto (`E_ATTIVO_PADRE_NON_ATTIVO`).
* Dall'altro verso: finché un legame esiste, né il conto né il soggetto si spengono. Il legame non ha un suo
  `attivo`, quindi conta che esista, non che sia valido oggi.

---

### Come lo legge la scelta del conto

La vista `vw_conti_bancari_per_ruolo` proietta ogni legame del soggetto su **tutti** i suoi ruoli, come candidata di
fonte `SOGGETTO`, se valido nel giorno operativo (la data di oggi nel fuso dell'azienda), non bloccato e su un conto
attivo. La funzione di scelta la prende quando il ruolo non ha un legame suo per l'uso chiesto, prima di ricadere
sull'uso `GENERICO`.

---

### ⚠️ Che cosa oggi non copre

* **Un predefinito bloccato.** Niente nel database impedisce di bloccare il legame predefinito: la scelta del conto
  lo salta, e ricade sugli altri legami o sull'uso generico.
* **Il predefinito a scadenza.** Il predefinito è uno solo per uso, valido o no: un cambio di conto programmato a
  una data futura non può marcare il nuovo legame come predefinito finché il vecchio porta il segno.

---

### Codici errore

* `E_CONTO_BANCARIO` — il conto è spento o non esiste.
* `E_DATA_AL_MINORE_DAL` — la fine della validità precede l'inizio.
* `E_ATTIVO_PADRE_NON_ATTIVO` — al COMMIT, il soggetto o il conto è spento.

---

### Test

* `db/pgtap/anagrafiche/test-conto-incasso-un-solo-soggetto.sql` — lo stesso conto d'incasso su un secondo soggetto
  rifiutato, su un uso diverso ammesso, sullo stesso soggetto ammesso.
* `db/pgtap/anagrafiche/create-gestore-conto-soggetto.sql` — un legame d'incasso sul soggetto di un gestore.
* `db/pgtap/anagrafiche/test_vw_conti_bancari_per_ruolo_gestore.sql` — il legame del soggetto che esce, nella vista,
  come candidata del ruolo.

---

### Note di migrazione

* 2026-08-25 — nasce l'esclusione `ex_scb_conto_incasso_un_solo_soggetto`, gemella di quella sul ruolo (nata il
  2026-08-22): fino ad allora lo stesso conto poteva essere d'incasso per due aziende, dichiarato sul soggetto.
* 2026-09-23 — il controllo delle date esce dal guard del legame e passa a `script.trgfn_guard_date_validita`, la
  sede comune per le tabelle con validità.
* 2026-11-14 — l'indice dedicato a `soggetto_id` è tolto: lo serve il vincolo unico, che comincia con quella
  colonna.

---

{% include-markdown "signature-core.md" %}
