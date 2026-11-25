## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_annulla_sistemazione`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — l'atto che la funzione scarta
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — il fondo che un riporto confermato aveva creato
>
> Approfondimento viste:
>
> * [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare) — l'elenco in cui l'eccedenza resta dopo l'annullamento
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_sistemazioni_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_transizione) — la sede unica della regola sugli stati, e del varco sul riporto
> * [vendite.fn_applica_cancellazione_fondo_fattura](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura) — la primitiva che fa cadere il fondo del riporto
> * [script.fn_guard_livello_area](/dbzero/script/funzioni/fn_guard_livello_area) — il permesso: il livello `TUTTO` sull'area `pagamenti`
> * [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — la rigenerazione automatica, che la cancellazione del fondo riapre
> * [pagamenti.fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione) — il verbo gemello, che aveva creato l'esito
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — le sistemazioni e i fondi fattura

---

### 🎯 Scopo Principale

Scarta un atto di sistemazione lasciandolo a registro, con la ragione per cui è stato scartato; se l'atto era un riporto già confermato, fa cadere insieme il fondo che aveva creato.

⚠️ **Annullare non è cancellare**, ed è il senso stesso di avere un registro: l'eccedenza
continua a comparire nell'elenco (è vera, non se n'è andata), e chi guarderà troverà scritto
perché la volta scorsa si è deciso di lasciarla lì.

---

### Chi la chiama, con quale permesso e su quale atto

È il verbo dell'endpoint di annullo della sistemazione. Gira come proprietario
(`SECURITY DEFINER`), fuori dalla row security, quindi permesso e perimetro li controlla lei,
all'ingresso:

* **il permesso**, in prima riga: il livello `TUTTO` sull'area `pagamenti`
  ([`script.fn_guard_livello_area`](/dbzero/script/funzioni/fn_guard_livello_area)), senza un
  oggetto. È ciò che l'endpoint controlla già: chi arriva dall'interfaccia non riceve un rifiuto
  nuovo. Sotto il livello: `E_PERMESSO_NEGATO`;
* **il perimetro**, sull'atto: la sistemazione dev'essere di un'azienda di chi agisce. Fuori dal
  perimetro l'atto «non c'è» (`E_SISTEMAZIONE_NON_TROVATA`, la stessa risposta di un atto
  inesistente).

**Le porte spente all'ingresso.** Il verbo spegne la GUC delle righe contabili e quella del reset
del lotto prima di cominciare.

⭐ **Chi annulla non deve avere anche `governa_fondo_fattura`.** Il fondo del riporto cade dalla
primitiva [`vendite.fn_applica_cancellazione_fondo_fattura`](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura),
che non chiede permessi suoi, e non dal verbo pubblico del gesto «cancella il fondo», che quel
permesso lo chiede.

---

### ⭐ È piccola, e deve restarlo

Esiste per tre ragioni:

1. dare un messaggio giusto a «quell'atto non c'è», che vuol dire anche «non è tuo», e le due
   cose devono restare indistinguibili;
2. far arrivare il **motivo** nello stesso gesto in cui si annulla, invece di chiedere a chi
   chiama di scriverlo prima con un aggiornamento a parte;
3. disfare l'**esito** di un riporto confermato, perché l'atto e il suo effetto cadono insieme.

⛔ **Non ricontrolla lo stato**: se l'atto è già terminale, o è un rimborso o una compensazione
confermati, a parlare è
[trgfn_sistemazioni_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_transizione),
che dice anche in che stato si trova l'atto o quale strada prendere. Ripetere qui quel
controllo vorrebbe dire due sedi per la stessa regola, e il giorno in cui una cambia l'altra
mente. La riga si legge per sapere se c'è un esito da disfare, non per rideliberare.

---

### ⭐ Il motivo si fonde, non si sovrascrive

Se la chiamata arriva con un motivo vuoto e l'atto ne aveva già uno, **si tiene quello che
c'era**; un motivo nuovo lo sostituisce.

⚠️ Se restano entrambi vuoti l'annullamento non passa: il guard dei dati pretende il motivo su
un annullamento, perché una decisione scartata senza una ragione non si ricostruisce. Fra sei
mesi nessuno saprebbe se è stata una scelta o una dimenticanza.

---

### ⭐ Su un riporto confermato, il fondo cade con l'atto

Se l'atto era `CONFERMATA` e la destinazione è `RIPORTO`, l'annullamento chiama la primitiva
`vendite.fn_applica_cancellazione_fondo_fattura`, e il fondo creato dalla conferma **sparisce insieme alla
decisione**: l'atto e il suo effetto cadono insieme, o il registro racconta un fatto che non è
avvenuto.

Guida `pagamenti` e non `vendite` per tre ragioni: chi alza la bandiera la abbassa (il fondo
l'ha creato `fn_conferma_sistemazione`); nel backend le chiamate laterali fra moduli di pari
livello sono vietate, quindi la sola sede in cui i due schemi si toccano è il database; e
l'atto sta qui, mentre il fondo è la sua **conseguenza**.

⚠️ **Prima l'atto, poi il fondo.** `fk_sistemazioni_fondo_source` è `NO ACTION` e trattiene la
cancellazione del fondo finché l'atto lo punta: per staccare il puntatore serve proprio
l'aggiornamento dell'atto, che quindi viene prima. La garanzia regge per costruzione: è tutto
dentro una funzione, cioè una transazione, e se la cancellazione del fondo solleva
l'aggiornamento non sopravvive. Una sistemazione annullata con il suo fondo ancora vivo non è
raggiungibile.

⚠️ **Il composito dell'esito cade intero** (`data_esecuzione`, `user_esecuzione`,
`fondo_source_id`), perché il `CHECK` sull'esecuzione lo pretende fuori da `CONFERMATA`. ⭐ Ma
la memoria non si butta: ciò che il registro perderebbe, con la destinazione e il momento
dell'annullamento, finisce sotto la chiave `annullata_dopo_esecuzione` di `meta`, che nessun
`CHECK` vincola. Si scrive **solo** quando l'atto era davvero stato eseguito: su una `BOZZA`
una chiave piena di valori vuoti direbbe il falso.

⚠️ **Cancellare il fondo riapre la rigenerazione automatica**: l'«atto unico» dei fondi guarda
se un atto esiste in qualunque stato, quindi il giro successivo ne rifà uno leggendo il residuo
di adesso. Sul riporto è il comportamento giusto (l'eccedenza è tornata al suo posto, e se
merita un fondo lo si rifà), ma è un effetto reale.

---

### Codici errore

* `E_PERMESSO_NEGATO` — manca il livello `TUTTO` sull'area `pagamenti`, o manca l'utente.
* `E_SISTEMAZIONE_NON_TROVATA` — l'atto non esiste o è fuori perimetro.
* `E_SISTEMAZIONE_IMMUTABILE` — l'atto è già terminale (dal guard di transizione).
* `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO` — l'atto è un rimborso o una compensazione già
  confermati (dal guard di transizione).
* `E_SISTEMAZIONE_MOTIVO_OBBLIGATORIO` — né la chiamata né l'atto portano un motivo (dal guard
  dei dati).
* i codici di `vendite.fn_applica_cancellazione_fondo_fattura`, se il fondo del riporto non si
  può cancellare.

---

### Test

* `db/pgtap/pagamenti/test-sistemazione-annullo-riporto.sql` — l'annullamento del riporto
  confermato porta l'atto ad `ANNULLATA`, fa cadere il fondo, azzera il composito dell'esito e
  ne conserva la memoria in `meta`; su una compensazione il rifiuto nomina l'alternativa.
* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il test 12: l'annullamento lascia
  l'atto a registro, e su un atto inesistente rifiuta.
* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: il verbo è
  `SECURITY DEFINER`; con l'area `pagamenti` a `LETTURA` risponde `E_PERMESSO_NEGATO`; la
  sistemazione di un'altra azienda risponde `E_SISTEMAZIONE_NON_TROVATA` e resta com'era.

---

### Note di migrazione

* 2026-08-22 — nasce con il registro `sistemazioni`: scrive una riga sola, l'atto.
* 2026-08-31 — sul riporto confermato fa cadere anche il fondo. Il piano chiedeva l'ordine inverso,
  prima il fondo e poi l'atto: alla lettera non era eseguibile per la FK `NO ACTION`, e la
  stessa garanzia la dà la transazione unica.
* 2026-11-25 — `SECURITY DEFINER`: il livello d'area dell'endpoint in prima riga, il perimetro
  sull'atto all'ingresso (prima lo dava la row security), le porte spente all'ingresso; il fondo
  cade dalla primitiva e non più dal verbo pubblico (brief-db-porte-aperte-dalla-sola-guc, giro 8,
  D-U a).

---

{% include-markdown "signature-core.md" %}
