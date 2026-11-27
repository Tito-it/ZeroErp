## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_conti_bancari`

> **Ultimo aggiornamento**: 27 novembre 2026
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
> * [anagrafiche.trgfn_conti_legami_guard_predefinito](/dbzero/anagrafiche/funzioni/trgfn_conti_legami_guard_predefinito) — il predefinito: uno per periodo, mai bloccato
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

* **L'identità non si sposta.** Soggetto, conto e uso non si modificano (`E_CONTO_LEGAME_IMMUTABILE`, lucchetto di
  colonna): un legame sbagliato si chiude con la sua data di fine e se ne apre uno nuovo.
* **Il predefinito.** Per ogni soggetto e uso c'è al più un legame predefinito **in ogni giorno**: due predefiniti
  non hanno periodi che si sovrappongono, date comprese (`ex_scb_predefinito_per_periodo`; il rifiuto parlante è
  `E_CONTO_PREDEFINITO_SOVRAPPOSTO`, da `anagrafiche.trgfn_conti_legami_guard_predefinito`). Un cambio di conto
  programmato marca il nuovo legame dal suo primo giorno.
* **La validità.** `valido_dal` e `valido_al` sono facoltativi, e la fine non precede l'inizio.
* **Il blocco.** `bloccato` toglie il legame dalla scelta del conto senza cancellarlo (un blocco per compliance). Un
  predefinito non si blocca (`E_CONTO_PREDEFINITO_BLOCCATO`; `chk_soggetti_conti_bancari_predefinito_non_bloccato`
  come rete).
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

* Il conto del legame è attivo, al COMMIT, quando il legame nasce (`E_ATTIVO_PADRE_NON_ATTIVO`).
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

* **Un soggetto con un conto storico non si spegne**: lo spegnimento conta i legami di qualunque validità.

---

### Codici errore

* `E_CONTO_LEGAME_IMMUTABILE` — soggetto, conto o uso del legame non si cambiano.
* `E_CONTO_PREDEFINITO_BLOCCATO` — un predefinito bloccato.
* `E_CONTO_PREDEFINITO_SOVRAPPOSTO` — due predefiniti dello stesso soggetto e uso in periodi che si sovrappongono.
* `E_DATA_AL_MINORE_DAL` — la fine della validità precede l'inizio.
* `E_ATTIVO_PADRE_NON_ATTIVO` — al COMMIT, il soggetto o il conto è spento.

---

### Test

* `db/pgtap/anagrafiche/test-conto-incasso-un-solo-soggetto.sql` — lo stesso conto d'incasso su un secondo soggetto
  rifiutato, su un uso diverso ammesso, sullo stesso soggetto ammesso.
* `db/pgtap/anagrafiche/create-gestore-conto-soggetto.sql` — un legame d'incasso sul soggetto di un gestore.
* `db/pgtap/anagrafiche/test_vw_conti_bancari_per_ruolo_gestore.sql` — il legame del soggetto che esce, nella vista,
  come candidata del ruolo.
* `db/pgtap/anagrafiche/test-conti-bancari-forma-e-legami-v1.sql` — l'uso che non si cambia, i due predefiniti
  sovrapposti.

---

### Note di migrazione

* 2026-08-25 — nasce l'esclusione `ex_scb_conto_incasso_un_solo_soggetto`, gemella di quella sul ruolo (nata il
  2026-08-22): fino ad allora lo stesso conto poteva essere d'incasso per due aziende, dichiarato sul soggetto.
* 2026-09-23 — il controllo delle date esce dal guard del legame e passa a `script.trgfn_guard_date_validita`, la
  sede comune per le tabelle con validità.
* 2026-11-14 — l'indice dedicato a `soggetto_id` è tolto: lo serve il vincolo unico, che comincia con quella
  colonna.
* 2026-11-27 — il predefinito diventa uno per periodo (EXCLUDE al posto dell'indice unico), mai bloccato; soggetto,
  conto e uso prendono il lucchetto; il guard immediato «conto attivo» si ritira, e resta il controllo al COMMIT.

---

{% include-markdown "signature-core.md" %}
