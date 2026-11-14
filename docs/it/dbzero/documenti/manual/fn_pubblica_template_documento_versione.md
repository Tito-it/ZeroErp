## 📘 Documentazione Concettuale – Funzione `documenti.fn_pubblica_template_documento_versione`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la versione che si pubblica e quelle che si chiudono
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — che cosa stampa dopo la pubblicazione
>
> Approfondimento funzioni:
>
> * [documenti.fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto) — il patto sulla forma dei dati
> * [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata) — la porta della chiusura
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle due date
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni, stati e date

---

### 🎯 Scopo Principale

**Pubblica una bozza** di un modello, e nella stessa transazione chiude e rende obsolete le versioni
pubblicate che la nuova supera. Restituisce la versione pubblicata, il suo modello e quante versioni
ha chiuso.

Chi chiama passa, oltre alla versione e alle date, la **forma dei dati** che il builder del backend
produce per quel tipo di documento: la versione si pubblica solo se legge proprio quella forma.

---

### Che cosa controlla, prima di scrivere

1. La versione e la data di inizio sono indicate; la versione esiste ed è in bozza.
2. La versione legge la forma dei dati che il builder produce
   ([fn_guard_versione_contesto](/dbzero/documenti/funzioni/fn_guard_versione_contesto)). Il controllo
   sta qui e non sulla bozza: una bozza può dichiarare una forma che il builder non produce ancora, ed
   è così che si prepara la versione successiva.

Tutti e due i controlli precedono ogni scrittura, quindi un rifiuto non lascia niente a metà.

L'ordine delle due date **non** si giudica qui: ha una sede sola, il guard comune delle date, che
scatta sulla scrittura della versione. Con le date invertite la transazione si annulla per intero,
chiusure comprese.

---

### Quali versioni chiude

Chiude le versioni **pubblicate e attive** dello stesso modello che cominciano prima della nuova e
sono ancora aperte al suo inizio. Ognuna diventa obsoleta e finisce il giorno prima dell'inizio della
nuova. La data di fine della nuova non entra nel giudizio: una versione che comincia prima si
sovrappone alla nuova se e solo se è ancora aperta al suo inizio.

Non chiude:

* una versione già finita prima dell'inizio della nuova, che resta pubblicata con la sua fine;
* una versione spenta, che è fuori dal vincolo di non sovrapposizione;
* una versione già obsoleta, che non si modifica più;
* una versione che comincia lo stesso giorno della nuova o dopo.

Negli ultimi due casi, se i periodi si toccano, la pubblicazione viola il vincolo di non
sovrapposizione e il backend la traduce in `E_DOCUMENTI_VERSIONE_OVERLAP`: una versione nuova comincia
dopo l'inizio della più recente già in vigore.

La chiusura è **una scrittura sola**, stato e data insieme, a porta
`zeroerp.allow_template_versione_chiusura_override` aperta: il guard d'immutabilità protegge le
versioni fuori bozza, e a porta aperta ammette solo questa forma. La funzione apre la porta dopo aver
scelto le versioni da chiudere e la richiude subito.

---

### ⭐ Che cosa stampa dopo: lo decide la validità

La precedente diventa obsoleta nel momento della pubblicazione, anche quando la nuova parte da una
data futura. Che cosa stampa lo decide la validità, non lo stato
([vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)): la
precedente stampa fino alla vigilia, la nuova dal giorno di partenza. Pubblicare in anticipo non
lascia mai il modello senza una versione che stampa.

---

### Concorrenza

La funzione blocca la versione da pubblicare all'inizio, poi tutte le versioni del modello in ordine
di id: due pubblicazioni dello stesso modello si mettono in fila, senza stallo. La pubblicazione
finale riscrive la versione solo se è ancora in bozza, e se non la trova più in bozza solleva il
rifiuto dello stato. Il vincolo di non sovrapposizione resta l'ultima difesa.

Audit, `tx_id`, storico e validità li gestiscono i trigger della tabella e la colonna generata.

---

### ⚠️ Che cosa oggi non copre

* **Pubblicare una versione spenta chiude quella accesa.** La funzione non guarda `attivo` della
  versione da pubblicare: una bozza spenta diventa pubblicata, che non stampa, e la versione attiva
  che la precedeva si chiude. Dal suo inizio il modello resta senza versione che stampa.
* Non è l'unica strada per pubblicare: una bozza portata a `PUBBLICATA` con un UPDATE diretto, o una
  versione che nasce pubblicata, salta i controlli di questa funzione (vedi la pagina della tabella).

---

### Codici errore

* `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` — versione non indicata o non positiva, data di inizio non
  indicata.
* `E_DOCUMENTI_VERSIONE_NOT_FOUND` — la versione non esiste.
* `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO` — la versione non è in bozza, anche se ha smesso di
  esserlo durante la pubblicazione.
* `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA` — la versione legge una forma dei dati diversa da quella
  passata.
* `E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE` — forma dei dati non passata; di classe tecnica.
* `E_DATA_AL_MINORE_DAL` — la fine precede l'inizio; lo solleva il guard comune delle date.
* `E_DOCUMENTI_TEMPLATE_STANDARD_SOLA_LETTURA` — dall'applicazione, su una versione di uno standard.

---

### Test

* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — date invertite rifiutate
  dal guard comune, con rifiuto atomico; chiusura di una versione aperta anche quando la nuova ha una
  fine; nessuna chiusura per una versione già finita; forma dei dati diversa o assente, con rifiuto
  atomico; una bozza preparata per la forma successiva si pubblica quando il builder la produce;
  vincolo e registro su pubblicate e obsolete; con la nuova che parte domani oggi stampa la
  precedente, con la nuova che parte oggi stampa la nuova; immutabilità delle obsolete e porta della
  chiusura.
* Non provati: i rifiuti `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO`, `E_DOCUMENTI_VERSIONE_NOT_FOUND` ed
  `E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO`.

---

### Note di migrazione

* 2026-05-06 — nasce la funzione.
* 2026-09-24 — l'ordine delle date passa al guard comune.
* 2026-09-30 — entra il patto sulla forma dei dati.
* 2026-11-14 — la chiusura diventa una scrittura sola a porta aperta, perché anche le obsolete sono
  protette: prima erano due UPDATE, lo stato e poi la data.

---

{% include-markdown "signature-core.md" %}
