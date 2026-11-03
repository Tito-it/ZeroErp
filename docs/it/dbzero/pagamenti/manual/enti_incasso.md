## 📘 Documentazione Concettuale – Tabella `pagamenti.enti_incasso`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli_conti_bancari](/dbzero/anagrafiche/tabelle/soggetti_ruoli_conti_bancari) — il conto su cui atterra il denaro del canale
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — l'origine di incasso a cui il canale si appoggia
> * [anagrafiche.bank_branches](/dbzero/anagrafiche/tabelle/bank_branches) — la filiale, solo per i canali `BANCA`
> * [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp) — il censimento dei PSP, per i canali `PSP`
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — le distinte che arrivano da un canale
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_enti_incasso_guard_conto_incasso](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_conto_incasso) — il conto deve essere di incasso
> * [pagamenti.trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp) — la coerenza di un canale `PSP`

---

### 🎯 Scopo Principale

La tabella **`pagamenti.enti_incasso`** è il catalogo dei **canali** da cui arrivano i flussi di
incasso (banca, poste, PSP, altro): ogni canale è legato al conto dell'azienda su cui atterra il
denaro e ai riferimenti anagrafici e operativi che servono all'import e alla riconciliazione.

`tipo` vale `BANCA`, `POSTE`, `PSP` o `ALTRO`; `regole_match` può portare la configurazione per
l'abbinamento automatico dei movimenti.

---

### ⭐ Il conto su cui atterra il denaro è il perimetro dei soldi non attribuiti

`soggetto_ruolo_conto_bancario_id` (**obbligatorio**) dice **su quale conto dell'azienda finisce
il denaro di questo canale**.

È il perimetro dei soldi non ancora attribuiti. Quando mille euro arrivano in banca non hanno
ancora una fattura, e il perimetro dell'operatore in questo sistema si risolve *dalla fattura*:
senza questa colonna la coda «da abbinare» sarebbe invisibile **a tutti**, che è peggio di
visibile a chi non dovrebbe, perché una lista vuota sembra una lista di cose finite. Il denaro
ha un padrone dal primo istante: l'ha deciso il cliente scegliendo su quale conto pagare.

⚠️ **Obbligatorio su TUTTI i tipi**, non solo su `BANCA`. Un ente `POSTE`, `PSP` o `ALTRO`
senza conto sarebbe lo stesso difetto travestito, con la coda invisibile spostata su un altro
`tipo`. E il dato c'è: un conto corrente postale ha un IBAN, il saldo di un PSP arriva sul conto
di accredito dell'emittente.

⚠️ **Da non confondere con `bank_branch_id`**, che è la **filiale**: è obbligatoria per
`tipo = BANCA` e deve restare vuota negli altri casi. È un fatto diverso, e non è il perimetro.

---

### ⚠️ La chiave esterna sa che il conto esiste, non che cosa è

Che il conto sia di **incasso** lo impone
[trgfn_enti_incasso_guard_conto_incasso](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_conto_incasso):
senza di lui un ente potrebbe appoggiarsi al conto dei **pagamenti**, che sta fuori
dall'unicità «un conto di incasso → un solo soggetto», e il perimetro tornerebbe a essere
un'assunzione senza che nessun errore lo dica.

📮 **Conseguenza operativa, ed è voluta**: finché un emittente non ha un conto con
`uso = 'INCASSO'` censito, non può configurare nessun canale. Si fallisce alla configurazione,
dove se ne accorge chi può rimediare, e non in esercizio, dove non se ne accorge nessuno.

---

### Un canale `PSP` nomina un PSP censito

Per `tipo = PSP` il `soggetto_ruolo_id` è obbligatorio, deve avere il ruolo `PSP` e deve
esistere una riga attiva in `anagrafiche.psp` per lo stesso soggetto-ruolo. Lo verifica
[trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp).

---

### 🔒 Chi vede un canale: il perimetro passa dal conto

La tabella ha la row security, con una policy `FOR ALL` (`rls_enti_incasso_perimetro_incasso`)
il cui predicato sta sul **conto**: l'operatore vede e scrive i canali appoggiati a un conto di
un emittente del suo perimetro. Senza policy l'elenco dei canali, IBAN compreso, sarebbe comune a
tutti gli emittenti, e si vedrebbe come un dato, non come un errore: una lista più lunga del vero
non la mette in dubbio nessuno.

⭐ **Perché il conto e non l'id del canale.** Un predicato che rilegge `enti_incasso` per l'id
della riga non vede la riga che il comando sta inserendo: risolverebbe nulla e ogni `INSERT`
verrebbe rifiutato. Il conto è una colonna della riga e punta a una tabella senza row security,
quindi vale identico in lettura e in scrittura: `USING` e `WITH CHECK` dicono la stessa cosa.

⚠️ **La policy tace dove parla il vincolo.** Con il conto a nulla il predicato passa, e a
rifiutare è il `NOT NULL`, col suo messaggio: altrimenti «hai dimenticato il conto» diventerebbe
un errore di permesso (403 al posto di 400). Una policy non deve rispondere a una domanda che un
vincolo risponde meglio.

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-conto-incasso.sql` — un ente senza conto non si crea,
  qualunque sia il tipo; con un conto di incasso si crea, con un conto di pagamento è rifiutato
  e la frase dice quale uso ha trovato; un `UPDATE` che non tocca il conto passa.
* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — i tre rifiuti del canale `PSP`.
* `db/pgtap/rls/test-rls-pagamenti-perimetro.sql` — la policy è `FOR ALL`; un canale sul
  proprio conto si crea, su quello di un altro emittente è rifiutato, e l'altro emittente non
  lo vede.

---

### Note di migrazione

* 2026-08-22 — nasce `soggetto_ruolo_conto_bancario_id`, obbligatorio su tutti i tipi, con il
  guard sul conto di incasso.
* 2026-08-28 — si accende la row security, su una tabella ancora vuota; lo stesso giorno
  la policy viene corretta perché non copra più il «manca il conto».

---

{% include-markdown "signature-core.md" %}
