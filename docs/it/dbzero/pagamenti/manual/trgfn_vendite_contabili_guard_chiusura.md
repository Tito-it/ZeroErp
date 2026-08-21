## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_chiusura`

### 🎯 Scopo Principale
(rev 2026-08-21)

> **Una distinta contabile non si chiude finché ha righe pronte da registrare.**

È la porta d'**uscita** del difetto delle righe fuori da ogni conto — e, a
differenza della porta d'ingresso, è il **percorso naturale**: si registra la
distinta, restano due righe che non erano pronte, e qualcuno la chiude comunque.
Nessun gesto strano, nessuna cattiva intenzione — e quelle due righe spariscono da
entrambi i conti.

Chi vuole chiudere ha **due strade oneste**: registrarle, oppure portarle a
`SOSPESA` / `SCARTATA`, cioè **dire che cosa ne è stato**. Ciò che non si può fare
è chiudere lasciandole a metà.

### Regole applicate
* Il blocco lo danno le righe **pronte** (`is_postabile`), non le non-finali.
  ⛔ Con `NOT is_final` bloccherebbero anche `DA_ABBINARE` e `SOSPESA`, e la
  distinta **non si chiuderebbe mai**.
* Contano solo le righe **attive**.

### ⚠️ Annullare non è chiudere
Il guard vale sul passaggio a **`CHIUSA`**, non su `ANNULLATA`. Sono **opposti**:
`CHIUSA` vuol dire *«è fatta»* — e allora le righe pronte devono essere state
registrate; `ANNULLATA` vuol dire *«non è mai successa»* — e allora le sue righe
non devono contare in nessun conto, comprese quelle pronte.

ℹ️ Il calcolo del saldo contabile **non distingue i due casi**: li appiattisce
entrambi su `is_final`. Con questo guard e con quello sulla porta d'ingresso
l'anomalia non può più nascere, quindi la confusione resta **innocua** e non serve
un terzo attributo sul catalogo. È scritto qui perché chi ci tornerà sappia che è
una scelta, non una svista.

### ⭐ La chiusura diventa una conseguenza
Era una domanda aperta se la testata debba andare a `CHIUSA` **sempre** dopo la
registrazione o **solo se non restano righe lavorabili**. Con questo guard smette
di essere una scelta di chi registra: si può tentare sempre, e il database la
lascia passare solo quando è vera.

### Quando si attiva
* `BEFORE UPDATE OF stato_id` su `pagamenti.vendite_contabili`.

### ⚠️ Error handling
* `E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE` (`CONFLITTO_STATO`, 409): il messaggio
  dice **quante** righe restano.

{% include-markdown "signature-core.md" %}
