## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la tabella che custodisce
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — `is_final` e `righe_lavorabili` della distinta
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — `is_postabile`, la domanda «è pronta?»
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) — la porta d'uscita, gemella di questa
> * [pagamenti.trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto) — la sede di `DELETE` e disattivazione
> * [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile) — il motivo `DISTINTA_ANNULLATA` sul cestino
> * [pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva) — l'unica porta della quarta mossa
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — perché una distinta non manuale non va in `ANNULLATA`
> * [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili) — il saldo che esclude le distinte finali
> * [script.fn_get_contabile_stato_origine](/dbzero/script/funzioni/fn_get_contabile_stato_origine) — lo stato della distinta, letto fuori dalla row security

---

### 🎯 Scopo Principale

Impedisce che una riga contabile finisca, o **torni utile**, sotto una distinta in
stato **finale** (`CHIUSA` o `ANNULLATA`), e **congela** le righe che stanno già sotto una distinta
annullata: lì si leggono soltanto.

---

### 🔴 Il difetto, in tre negazioni

Una riga utile appesa sotto una distinta finale:

* **non entra** nel saldo contabile: la funzione che lo calcola esclude le righe la cui distinta
  è finale;
* **non entra** nel saldo movimenti: non è registrata;
* **non verrà mai registrata**: la registrazione parte dalla distinta.

È **denaro dichiarato che non compare da nessuna parte**. E la differenza fra il residuo e la
copertura la legge come «manca copertura»: il **fondo fattura si rigenera**.

⚠️ **E il filtro che sembrava proteggere non protegge**: le righe di una distinta chiusa sono
già registrate, quindi escluse comunque. L'unica cosa che quel filtro riesce a escludere
è **proprio la riga anomala**. *Un filtro che nasconde ciò che non sa gestire sembra un presidio
finché non si guarda che cosa esclude davvero.*

---

### Quattro mosse d'ingresso, e chiuderne una sola non serve

Sotto una distinta finale una riga può diventare un problema in quattro modi:

1. **nascendoci** (inserimento di una riga attiva);
2. essendo **riattivata** (`attivo` da falso a vero);
3. essendo **spostata** lì da un'altra distinta;
4. ⭐ **diventandoci pronta da registrare**, restando dov'è.

⭐ **La quarta esiste perché la chiusura è la conseguenza del registrare.** La madre del posting
chiude la distinta appena ha registrato, e sotto possono restare righe «da abbinare», che il
guard di chiusura non considera un ostacolo, deliberatamente, *«o la distinta non si chiuderebbe
mai»*. Abbinarne una il giorno dopo produrrebbe **denaro dichiarato e pronto sotto una distinta
che non si registra più**: il posting parte dalla distinta, e una chiusa la rifiuta.

ℹ️ La domanda *«questo stato è pronto da registrare?»* si fa al **catalogo** (`is_postabile`),
non a un elenco di stati scritto dentro il guard: è la stessa scelta del guard gemello sui dati
(`richiede_abbinamento`).

---

### ⭐ La quinta mossa: sotto un'annullata le righe si leggono soltanto

`CHIUSA` e `ANNULLATA` sono entrambe finali, ma per le righe sono **opposte**:

| Sotto una… | Le righe… | Perché |
| --- | --- | --- |
| `CHIUSA` | si lavorano ancora: si sospendono, si scartano, si riprendono, si registrano in ritardo | il denaro è arrivato, e resta da dire che cosa ne è stato |
| `ANNULLATA` | si **leggono soltanto** | la distinta non è mai successa: quel denaro, per il registro, non è mai arrivato |

La differenza sta nel catalogo, nella bandiera `righe_lavorabili` di
[vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) (oggi falsa solo su
`ANNULLATA`): `is_final` non basta a rispondere.

La quinta mossa si valuta **per prima**, su **ogni** aggiornamento: se la distinta dove la
riga **sta** (quella di partenza) non ha le righe lavorabili, il rifiuto è
`E_RIGA_CONTABILE_DISTINTA_ANNULLATA`. Vale per un cambio di stato (anche verso sospesa o
scartata), per la correzione di un dato, per la riattivazione e per lo spostamento **fuori**. Le
quattro mosse guardano la distinta d'arrivo, e tirare una riga fuori da un'annullata non lo
vedrebbero.

* ℹ️ Il `DELETE` e la disattivazione hanno la loro sede nel
  [guard del contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto),
  che chiama la check dell'eliminazione (motivo `DISTINTA_ANNULLATA`, stesso codice). Il
  cestino si spegne col perché e il rifiuto dice la stessa cosa.
* ⚠️ La porta della registrazione tardiva qui non vale: la tardiva lavora solo sotto una
  distinta registrata.
* ⭐ Perché nessun giro di sistema ci sbatta contro, una distinta **non manuale** non va in
  `ANNULLATA` ([guard di validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione),
  regola 3). Il sync dei fondi e la cancellazione di un atto lavorano solo sotto distinte
  generate.

---

### ⚠️ Che cosa non si rifiuta

Dove le righe si lavorano ancora (sotto una `CHIUSA`), le altre scritture su una riga già lì
passano: sospenderla, scartarla, riprenderla, correggerne il motivo. È **dire che cosa ne è
stato** di quel denaro, che è l'unica cosa che resta da fare.

⚠️ **Non blocca il posting**, per due ragioni indipendenti: lo stato «registrata» **non è** uno
stato pronto, e la distinta è ancora `VALIDATA` quando la madre muove le righe.

---

### ⭐ La quarta mossa ha una porta sola: la registrazione tardiva

Una `SOSPESA` sotto una distinta **registrata** ha un futuro:
[pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva) la abbina e
la registra nello stesso gesto. Per farlo la porta ad `ABBINATA` (così girano tutti i guard
dell'abbinamento) e a **questo** guard si presenta con la GUC transazionale
`app.registrazione_tardiva_riga_id`, valorizzata con l'id della riga: la quarta mossa lascia
passare **solo** quella riga, **solo** in quella transazione, **solo** nel ramo del cambio di
stato. Le altre tre mosse non leggono la GUC: la tardiva non fa nascere, non riattiva, non
sposta.

⛔ Un aggiornamento a mano di una sospesa verso uno stato pronto resta rifiutato; la GUC
valorizzata con un **altro** id non apre; dopo la madre la porta è richiusa. La regola resta
vera: sotto una chiusa nessuna riga *«pronta e mai registrata»*, perché non esiste più il
momento in cui sta pronta ad aspettare. Il precedente della forma è `app.cessazione_automatica`.

---

### Le porte sono due

Questa è la porta d'**ingresso**. La porta d'**uscita**, cioè *chiudere* una distinta che ha
ancora righe registrabili, è la strada che capita davvero, e la chiude
[pagamenti.trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura).

---

### 🔴 Lo stato della distinta si legge fuori dalla row security

Una riga contabile si vede per due strade: dall'emittente della distinta oppure da quello della
fattura. La riga «mista» (sulla distinta di un'azienda, abbinata alla fattura di un'altra) la
vede e la scrive anche chi lavora per l'azienda della fattura, che la distinta **non la vede**.

Per questo il guard chiede lo stato della distinta a
[script.fn_get_contabile_stato_origine](/dbzero/script/funzioni/fn_get_contabile_stato_origine),
che legge fuori dalla row security. Letta sotto RLS, per quell'operatore la distinta non c'era e
il guard **lasciava passare**: la riga diventava pronta sotto una distinta chiusa e si
ritoccava sotto un'annullata.

⚠️ Il **numero** della distinta, che serve solo al messaggio, resta letto sotto la row security:
chi non vede la distinta ne legge l'id, non il codice.

---

### Codici errore

* `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` — la quinta mossa: qualsiasi aggiornamento di una riga
  che sta sotto una distinta annullata.
* `E_RIGA_CONTABILE_DISTINTA_FINALE` — le quattro mosse d'ingresso sotto una distinta chiusa o
  annullata.

---

### Test

* `db/pgtap/pagamenti/test-righe-contabili-guard-dati.sql` — una riga non si aggiunge e non si
  sposta sotto una distinta chiusa.
* `db/pgtap/pagamenti/test-righe-distinta-annullata-congelate-v1.sql` — la quinta mossa:
  sospendere, scartare, correggere il motivo, spostare fuori, tutto rifiutato sotto
  un'annullata; la riga resta com'era.
* `db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — la porta della tardiva: fuori dalla
  madre la quarta mossa rifiuta (test 16), la GUC su un altro id non apre (17), dopo la madre la
  porta è richiusa (18).
* `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` — l'ordine col guard del
  contenuto sotto una distinta finale.
* `db/pgtap/pagamenti/test-righe-guard-distinta-vista-dalla-fattura-v1.sql` — la riga mista
  vista dalla fattura: chi non vede la distinta riceve lo stesso rifiuto di chi la vede, sotto
  la chiusa e sotto l'annullata, e il messaggio non mostra il numero della distinta.

---

### Note di migrazione

* 2026-08-21 — nasce come porta d'ingresso delle righe sotto una distinta finale, con le prime tre mosse.
* 2026-08-22 — la quarta mossa, nata con la madre del posting: fino ad allora una
  distinta si chiudeva a mano, e chi la chiudeva sapeva che cosa ci lasciava dentro.
* 2026-09-18 — la quarta mossa prende la porta della registrazione tardiva.
* 2026-09-30 — la quinta mossa e il codice `E_RIGA_CONTABILE_DISTINTA_ANNULLATA`.
* 2026-11-03 — lo stato della distinta si legge fuori dalla row security. Prima il guard lo
  leggeva con i diritti di chi scrive, e la riga vista dalla fattura passava senza controllo.

---

{% include-markdown "signature-core.md" %}
