## 📘 Documentazione Concettuale – Funzione `pratiche.fn_reconcile_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — i collegamenti fra il documento e le pratiche
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — con quale verdetto un milestone avanza
> * [pratiche.reconcile_errori](/dbzero/pratiche/tabelle/reconcile_errori) — dove finiscono gli avanzamenti saltati
>
> Approfondimento funzioni:
>
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — il verdetto proiettato del documento
> * [pratiche.trgfn_documento_reconcile_proiezione](/dbzero/pratiche/funzioni/trgfn_documento_reconcile_proiezione) — il trigger che la chiama a ogni cambio di stato
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Il motore che fa avanzare i milestone sull'esito proiettato di un documento: quando il documento
proietta un **verdetto** (l'esito di `pratiche.fn_stato_sorgente` non è vuoto), completa i milestone
delle pratiche che lo **attendono**, su qualsiasi percorso di scrittura del documento (backend,
batch, SQL diretto, documento standalone). Ritorna il numero di milestone avanzati.

Fa da database ciò che il building block del backend `completa_step_pratica` fa da Python, e che un
trigger non può chiamare: porta il milestone a `COMPLETATO` con il verdetto proiettato, e da lì
scatta la generazione a valle (`pratiche.trgfn_flussi_generazione`) come per un completamento a
mano. Prende il posto dell'handler di dominio `vendita.accetta_preventivo`.

---

### Il documento si passa con le colonne del modello

Il documento si indica con il tipo (`config.sorgenti`), `sorgente_id` e `sorgente_uid`, come lo
scrive il modello della provenienza. I collegamenti in `pratiche.pratiche_sorgenti` si cercano con
la **regola d'incontro**: il collegamento vale se il suo `sorgente_id` è quello passato oppure il
suo `sorgente_uid` è quello passato. Chi ha il documento passa il suo id e il suo uid; chi ha la
chiave del modello passa quella, e vuoto nell'altra.

---

### Le regole dell'avanzamento

* **Nessun collegamento, niente da fare.** Se il documento non è collegato a nessuna pratica
  (nessun collegamento visibile a chi scrive), ritorna 0 **prima** di leggerne lo stato. Il
  risultato sarebbe 0 comunque; il controllo viene prima perché leggere lo stato costa molto più che
  cercare i collegamenti, e il trigger chiama la funzione a ogni cambio di stato, anche dei documenti
  che non stanno in nessuna pratica.
* **Nessun verdetto, niente da fare.** Se il documento non ha un esito (per esempio un preventivo
  `EMESSO`), ritorna 0.
* **Chi avanza.** I milestone della pratica il cui template attende quel tipo di documento
  (`template_flussi.attende_sorgente_tipo_id`), con un binding attivo in
  `template_flussi_avanzamento_proiezione` compatibile con il verdetto, e non ancora terminali.
* **Due salti dove serve.** La matrice delle transizioni non ha il passaggio diretto
  `DA_ESEGUIRE → COMPLETATO`: un milestone `DA_ESEGUIRE` passa prima da `IN_CORSO`.
* **Ripetere non fa danni.** Agisce solo sui flussi non terminali: un secondo reconcile non trova
  più niente.

---

### ⚠️ Più istanze dello stesso milestone: non indovina

Se il collegamento ha un `flusso_id` e quel flusso attende esso stesso il tipo del documento, la
funzione agisce **solo su quel flusso**: è il tie-break fra più istanze. Un collegamento ancorato al
flusso d'**origine** (per esempio la preventivazione, che non attende il documento) non conta come
tie-break: si riconciliano i milestone in attesa.

Se restano **più** candidati senza un tie-break usabile, la funzione non avanza niente e scrive una
riga `E_RECONCILE_AMBIGUO` in `pratiche.reconcile_errori`, con la chiave del collegamento. Il log è
a prova di fallimento: se non si riesce a scriverlo, diventa un avviso nel log del server.

---

### Chi agisce

La funzione è `SECURITY INVOKER`: gira nella transazione di chi ha cambiato lo stato del documento,
e il giornale del milestone (scritto da `pratiche.trgfn_flussi_giornale_stato`) dice il vero su chi
ha innescato l'avanzamento. Non scrive un evento di dominio suo.

⚠️ La funzione **può sollevare** (sui parametri, o da un guard di dominio sul completamento). A
proteggere il documento è il trigger `pratiche.trgfn_documento_reconcile_proiezione`, che la chiama
dentro un blocco di eccezione; chi la chiama direttamente gestisce l'errore da sé.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — il tipo è vuoto o non positivo, oppure manca la chiave del documento
  (né `sorgente_id` né `sorgente_uid`).
* `E_RECONCILE_AMBIGUO` — non si solleva: è il codice della riga di log scritta quando più
  candidati non hanno un tie-break.

---

### Test

* `db/pgtap/pratiche/test-guida-avanza-esito-proiettato.sql` — l'avanzamento sul verdetto, i due
  salti, l'idempotenza, il caso ambiguo.
* `db/pgtap/pratiche/test-reconcile-tie-break-flusso-origine.sql` — il collegamento al flusso
  d'origine non fa da tie-break.
* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — la firma sulle colonne del modello,
  senza collegamento 0 e nessun errore nel log.

---

### Note di migrazione

* 2026-07-06 — nasce con il meccanismo dell'avanzamento su esito proiettato
  (`brief-db-guida-avanza-esito-proiettato`).
* 2026-10-05 — il controllo dei collegamenti passa prima della lettura dello stato.
* 2026-11-08 — il documento si passa con tipo, `sorgente_id` e `sorgente_uid` al posto della chiave
  in testo, e la riga ambigua nel log porta la chiave nelle stesse colonne
  (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
