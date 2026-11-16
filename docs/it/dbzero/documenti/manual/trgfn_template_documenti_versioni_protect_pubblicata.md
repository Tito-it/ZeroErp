## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_documenti_versioni_protect_pubblicata`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la tabella protetta
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — le stampe che rileggono la versione
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — anche un'obsoleta stampa, fino alla sua fine
>
> Approfondimento funzioni:
>
> * [documenti.fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione) — il verbo che porta una versione fuori bozza e chiude la precedente
> * [documenti.trgfn_template_documenti_versioni_block_delete](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_block_delete) — quali versioni si cancellano
> * [documenti.trgfn_template_documenti_versioni_guard_derivata_da](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_guard_derivata_da) — l'origine di una copia, che ha il suo guard
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — il riconoscimento del proprietario della tabella
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — versioni e stati

---

### 🎯 Scopo Principale

Lo **stato di una versione** di template ha un verbo solo, la pubblicazione. La funzione fa valere
tre regole:

1. una versione **nasce in bozza**;
2. **esce dalla bozza solo pubblicandosi**;
3. **fuori bozza non si modifica**, pubblicata o obsoleta: il contenuto, la pagina, le date, la forma
   dei dati, il modello, il numero e lo stato restano quelli della pubblicazione.

È montata `BEFORE INSERT OR UPDATE OF` quelle colonne su `documenti.template_documenti_versioni`,
in fase `a05`.

---

### Si nasce in bozza, se ne esce pubblicando

La pubblicazione,
[fn_pubblica_template_documento_versione](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione),
fa due cose che uno stato scritto a mano salterebbe: controlla che la versione legga i dati nella
forma che il sistema prepara, e chiude la versione che la nuova supera. Per questo una versione non
nasce pubblicata od obsoleta, e una bozza non diventa pubblicata con un UPDATE dello stato.

La pubblicazione scrive sotto la porta `zeroerp.allow_template_versione_pubblicazione_override`, e a
porta aperta il guard ammette una forma sola: da bozza a pubblicata, con le sole date cambiate. Un
UPDATE che a porta aperta cambia anche il corpo, o porta una bozza a obsoleta, è rifiutato.

Una bozza si modifica liberamente, date comprese.

---

### ⛔ Fuori bozza non cambia niente, nemmeno lo stato

Una versione fuori bozza è il contenuto con cui si è stampato. Se cambiasse, le stampe che la citano
avrebbero un'impronta del template non più verificabile, e la ristampa fedele produrrebbe un
documento diverso. Vale anche per una versione superata: un'obsoleta stampa fino all'ultimo giorno
della sua validità, e la ristampa la rilegge.

Lo stato fa parte dell'elenco: fuori bozza non torna indietro. Senza questa regola, riportare una
versione pubblicata in bozza la renderebbe di nuovo modificabile in tutto. La forma dei dati ne fa
parte perché la controlla la pubblicazione: cambiarla dopo aggirerebbe il controllo.

Fuori dall'elenco: `titolo`, `meta`, `attivo`, l'origine della copia (ha il suo guard) e le colonne
d'audit. Per cambiare il layout si crea una bozza nuova e la si pubblica.

Il trigger scatta anche quando la colonna è riscritta con lo stesso valore: un salvataggio che
riscrive tutta la riga di una versione fuori bozza è rifiutato. Nessun altro trigger `BEFORE` della
tabella scrive queste colonne, quindi la forma `UPDATE OF` è sicura.

**L'eccezione: la chiusura fatta dalla pubblicazione.** Quando pubblica una versione, il verbo chiude
quelle che la nuova supera. È l'unica scrittura ammessa su una versione fuori bozza, e passa solo se
valgono tutte insieme:

* la porta del verbo è aperta;
* lo stato va da `PUBBLICATA` a `OBSOLETA`;
* la data di fine diventa una data, uguale o precedente a quella di prima: la validità si accorcia;
* ogni altra colonna protetta resta com'era.

Una versione già obsoleta non si chiude di nuovo.

---

### Chi passa senza porta: il proprietario della tabella

Il seed e i changeSet, che girano come proprietario della tabella, scrivono lo stato senza porta: è
così che nasce e si chiude un modello standard. Il riconoscimento è
[script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella), lo stesso del
guard di sola lettura dello standard. Le prime due regole valgono per l'applicazione; la terza vale
anche per il proprietario.

⚠️ La porta protegge da un backend che sbaglia, non da uno manomesso: una sessione può aprirla a
mano. Anche aperta, però, ammette solo le due forme del verbo.

---

### L'ordine dei trigger

La fase è `a05`: è un'immutabilità, e parla prima della validità del valore nuovo. Fra gli `a10`
della tabella c'è il guard comune delle date: su una versione pubblicata con le date invertite, la
frase è quella dell'immutabilità, non «la data di fine è inferiore alla data di inizio», che
manderebbe a correggere una data che non si può cambiare. Il guard di sola lettura dello standard
(`a05_guard_standard`) viene prima: dall'applicazione, su uno standard, non si scrive niente.

---

### Codici errore

* `E_DOCUMENTI_VERSIONE_STATO_FUORI_VERBO` (`TECNICO`) — una versione che nasce fuori bozza, o che
  esce dalla bozza fuori dalla forma della pubblicazione. Il backend crea solo bozze e pubblica dal
  verbo: se arriva, è rotto il chiamante.
* `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` — ogni modifica di una colonna protetta su una
  versione fuori bozza, fuori dalla forma della chiusura. Il contesto porta modello, numero, lo stato
  di prima e quello chiesto.

---

### Test

* `db/pgtap/documenti/test-documenti-pubblicazione-e-copia-v1.sql` — il montaggio e la fase; una
  versione non nasce pubblicata né obsoleta; una bozza non diventa pubblicata né obsoleta con un
  UPDATE; a porta aperta passa solo la forma della pubblicazione; sulle date di una pubblicata parla
  l'immutabilità; una bozza si modifica come prima.
* `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` — un'obsoleta non si
  modifica e non torna in bozza; una pubblicata non torna in bozza; la porta è richiusa dopo la
  pubblicazione; senza porta una pubblicata non si chiude a mano; a porta aperta passa solo la
  chiusura; la pubblicazione chiude come deve.
* `db/pgtap/documenti/test-documenti-template-versioni.sql` — corpo, data di inizio e forma dei dati
  di una pubblicata non cambiano; `meta` sì.
* Il passaggio del proprietario lo percorrono i pgTAP che girano da owner e costruiscono standard
  pubblicati e obsoleti: `test-documenti-template-standard-v1.sql`, `-personalizza-v1.sql`,
  `-template-porta-unica-v1.sql`.

---

### Note di migrazione

* 2026-05-01 — nasce il guard, sulle sole versioni pubblicate.
* 2026-09-30 — la forma dei dati entra fra le colonne protette.
* 2026-11-14 — protegge anche le obsolete, e lo stato entra nell'elenco: fino ad allora un UPDATE
  del solo stato riportava una pubblicata in bozza. La chiusura della pubblicazione diventa una
  scrittura sola, a porta aperta.
* 2026-11-16 — guarda anche la bozza: una versione nasce in bozza e ne esce solo dalla pubblicazione.
  Fino ad allora un UPDATE dello stato, o una versione nata pubblicata, saltava il controllo della
  forma dei dati e la chiusura della precedente. Il trigger monta anche l'INSERT e passa da `a10` ad
  `a05`; la porta prende il nome del verbo (prima `…_chiusura_override`).

---

{% include-markdown "signature-core.md" %}
