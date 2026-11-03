## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_guard_chiusura`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — dove è montato
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe che conta
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — la bandiera `is_postabile` che decide quali righe bloccano
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — la registrazione, che chiude la distinta
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — la porta d'ingresso dello stesso difetto
> * [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili) — il saldo che si ferma al confine della distinta finale
> * [pagamenti.trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) — la matrice dei passaggi, che parla prima
>
> Guide:
>
> * [Linee guida trigger](/linee-guida-trigger) — l'ordine alfabetico dei `BEFORE ROW`

---

### 🎯 Scopo Principale

Una distinta contabile non si chiude finché ha righe pronte da registrare. Il guard
scatta sul passaggio della testata a `CHIUSA` e conta le righe attive in uno stato pronto.

È la porta d'**uscita** del difetto delle righe fuori da ogni conto — e, a differenza della
porta d'ingresso, è il **percorso naturale**: si registra la distinta, restano due righe che
non erano pronte, e qualcuno la chiude comunque. Nessun gesto strano, nessuna cattiva
intenzione, e quelle due righe spariscono da entrambi i conti.

Chi vuole chiudere ha **due strade oneste**: registrarle, oppure portarle a `SOSPESA` o
`SCARTATA`, cioè **dire che cosa ne è stato**. Ciò che non si può fare è chiudere lasciandole
a metà.

---

### ⛔ Bloccano le righe pronte, non le non finali

Il blocco lo danno le righe **pronte** (`is_postabile` sul catalogo degli stati della riga),
e solo quelle attive. Con «non finali» bloccherebbero anche `DA_ABBINARE` e `SOSPESA`, e la
distinta **non si chiuderebbe mai**.

---

### ⚠️ Annullare non è chiudere

Il guard vale sul passaggio a **`CHIUSA`**, non su `ANNULLATA`. Sono **opposti**: `CHIUSA`
vuol dire *«è fatta»*, e allora le righe pronte devono essere state registrate; `ANNULLATA`
vuol dire *«non è mai successa»*, e allora le sue righe non devono contare in nessun conto,
comprese quelle pronte.

ℹ️ Il saldo contabile della fattura **non distingue i due casi**: li appiattisce entrambi su
`is_final`. Con questo guard e con quello sulla porta d'ingresso l'anomalia non può nascere,
quindi la confusione resta **innocua** e non serve un attributo in più per il saldo. È
scritto qui perché chi ci tornerà sappia che è una scelta, non una svista.

---

### ⭐ La chiusura diventa una conseguenza

Con questo guard chiudere smette di essere una scelta di chi registra: si può tentare
sempre, e il database lo lascia passare solo quando è vero.
[fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) chiude la distinta
subito dopo averla registrata, perché a quel punto righe pronte non ne restano.

---

### ⭐ Parla dopo la matrice dei passaggi

Il trigger si chiama `trg_vendite_contabili_a10_guard_verifica_chiusura_upd`, e il nome non è
indifferente: i `BEFORE ROW` scattano in ordine alfabetico, e così questo guard viene **dopo**
la matrice (`…_guard_transizione_upd`) e dopo il guard di validazione. Un passaggio che la
matrice non ammette, come `BOZZA → CHIUSA`, riceve «passaggio non ammesso» anche se la distinta
ha righe pronte: prima si dice se il passaggio esiste, poi quali condizioni gli mancano.

---

### Codici errore

* `E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE` — si porta a `CHIUSA` una distinta con righe
  attive pronte; la frase dice **quante** restano.

---

### Test

* `db/pgtap/pagamenti/test-fn-posta-contabile.sql` — dopo la registrazione la distinta è
  `CHIUSA`, con le righe non pronte rimaste indietro.
* `db/pgtap/pagamenti/test-contabile-guard-chiusura-v1.sql` — la chiusura rifiutata con una riga
  pronta e ammessa quando la riga non lo è più, e l'ordine: `BOZZA → CHIUSA` riceve il codice
  della matrice, e i nomi dei trigger mettono la chiusura dopo transizione e validazione.

---

### Note di migrazione

* 2026-08-21 — nasce come porta d'uscita delle distinte già registrate; risolve in
  gran parte la domanda se chiudere sempre dopo la registrazione, o solo quando
  non restano righe lavorabili.
* 2026-11-03 — il trigger si rinomina da `trg_vendite_contabili_a10_guard_chiusura_upd` a
  `trg_vendite_contabili_a10_guard_verifica_chiusura_upd`: col nome vecchio scattava prima della
  matrice, e un passaggio non ammesso verso `CHIUSA` riceveva il rifiuto della chiusura.

---

{% include-markdown "signature-core.md" %}
