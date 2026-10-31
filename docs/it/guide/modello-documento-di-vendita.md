# Guida — Il modello del documento di vendita

> **Ultimo aggiornamento**: 31 ottobre 2026
>
> **Destinatari**: chi lavora su un documento di vendita o d'acquisto — sviluppatori database,
> backend, frontend e analisti funzionali. Prima di cambiare come un documento nasce, cambia stato,
> si emette o si annulla, si legge qui.
>
> **Vedi anche** — schemi DB:
>
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — il catalogo delle azioni di processo, quelle che si concedono a un profilo
> * [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) — una matrice dei passaggi presa ad esempio: le altre hanno la stessa forma
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.trgfn_doc_stato_iniziale](/dbzero/script/funzioni/trgfn_doc_stato_iniziale) — un documento nasce nel suo stato iniziale
> * [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) — la mappa: dove sta lo stato di una testata e quale matrice ne dice i passaggi
> * [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) — la riga del passaggio: è di processo? che azione chiede?
> * [script.fn_guard_passaggio](/dbzero/script/funzioni/fn_guard_passaggio) e [script.fn_doc_scrivi_stato](/dbzero/script/funzioni/fn_doc_scrivi_stato) — le due metà del verbo di stato
> * [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) — la porta: lo stato si cambia solo dal verbo
> * [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) — l'unico lettore dello stato iniziale di un vocabolario
> * [script.fn_doc_stato_iniziale_id](/dbzero/script/funzioni/fn_doc_stato_iniziale_id) — lo stesso, a partire dal documento
> * [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) — l'unico lettore dello stato di emissione di un documento
> * [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) — l'unico lettore dello stato d'annullo di un documento
> * [script.fn_stato_cessazione_id](/dbzero/script/funzioni/fn_stato_cessazione_id) — l'unico lettore dello stato di cessazione (il contratto)
> * [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) — l'unico lettore dello stato di accettazione (preventivo e offerta)
> * [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) — dal codice di uno stato al suo id, per ogni documento
> * [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) — il gemello inverso: dall'id di uno stato al suo codice
> * [script.fn_doc_azione_passaggio](/dbzero/script/funzioni/fn_doc_azione_passaggio) — la domanda del backend: che cosa chiede questo passaggio?
> * [script.fn_doc_azioni_permesse](/dbzero/script/funzioni/fn_doc_azioni_permesse) — i passaggi manuali che l'operatore può fare da uno stato: lo leggono le capability e le liste
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il permesso dentro il verbo
> * [script.fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo) — la regola del permesso, la stessa per DB e backend
> * [vendite.trgfn_doc_guard_annullo_con_legami](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami) — l'annullo di un documento con legami si conferma
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §7.4, «una scrittura = un verbo»: il modello generale di cui questo è il caso dei documenti
> * [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici) — come nasce il numero all'emissione
> * [Documenti e Stampe](/guide/documenti-e-stampe) — come nasce il PDF all'emissione
> * Le guide dei singoli documenti: [preventivi](/guide/gestione-preventivi) · [offerte](/guide/gestione-offerte-commerciali) · [contratti](/guide/gestione-contratti) · [ordini](/guide/gestione-ordini) · [DDT e resi](/guide/gestione-ddt) · [commesse](/guide/gestione-commesse) · [fatturazione](/guide/fatturazione) · [listini](/guide/gestione-listini)

---

## 1. A cosa serve questa guida

Preventivo, offerta, contratto, ordine, DDT, reso, commessa, fattura e versione di listino sono
documenti diversi, ma fanno le stesse cose: **nascono**, **cambiano stato**, a un certo punto si
**emettono** e qualche volta si **annullano**. Ognuna di queste cose ha **una regola sola**, che vale
per tutti, e questa guida è il posto in cui è scritta.

Le guide dei singoli documenti descrivono ciò che è **loro**: quali stati hanno, quali passaggi, che
cosa controlla l'emissione di quel documento. Per le regole comuni **rimandano qui**, e non ne
scrivono una versione locale: nove spiegazioni della stessa regola diventano, col tempo, nove regole.

⭐ **Una proposta che non sta in questa guida, o la contraddice, si dichiara come cambio del modello**
(e, se ne toglie una regola, come revoca): non si applica a un documento solo.

Il modello vale **anche per gli acquisti** (ordine e DDT d'acquisto): §9.

---

## 2. Le regole, in una tabella

| # | La regola | In una riga |
| --- | --- | --- |
| 1 | **Si nasce nello stato iniziale** | Un documento nuovo è in bozza; ogni altro stato si raggiunge coi passaggi (§3) |
| 2 | **Stati e passaggi stanno in tabella** | Il vocabolario degli stati e la matrice dei passaggi ammessi sono dati, non codice (§4) |
| 3 | **Ogni cambio di stato passa da un verbo** | Una funzione del database per cambiare lo stato, che controlla anche il permesso (§5) |
| 4 | **Il permesso sta sul passaggio** | La riga della matrice dice quale azione chiede quel passaggio; un'azione per documento, sui passaggi pesanti (§6) |
| 5 | **Si emette solo da «Emetti»** | Numero e PDF nascono insieme, nella stessa operazione (§7) |
| 6 | **Un annullo che riapre altro si conferma** | Chi annulla vede che cosa si riapre e conferma (§8) |

Non tutti i documenti seguono già tutte le regole: dove è arrivato ciascuno lo dice il §10.

---

## 3. Nascere: lo stato iniziale

Un documento nuovo nasce **nel suo stato iniziale** (la bozza) e in nessun altro. Gli altri stati si
raggiungono con i passaggi del documento — emetti, conferma, accetta… — che sono il posto dove stanno
le condizioni: righe presenti, indirizzi, causale, e così via. Un documento che nascesse già avanti
le salterebbe tutte: una bolla nata emessa è numerata e vuota, e dopo le righe non si aggiungono più.

* **Quale sia lo stato iniziale lo dice il vocabolario**, con la colonna `iniziale`: uno stato solo
  per vocabolario, ed è attivo. Nessuno scrive `'DRAFT'` o `'BOZZA'` nel codice per dire «lo stato
  in cui si nasce»: lo legge [`script.fn_stato_iniziale_id`](/dbzero/script/funzioni/fn_stato_iniziale_id),
  e chi ha in mano il documento e non il vocabolario lo chiede a
  [`script.fn_doc_stato_iniziale_id`](/dbzero/script/funzioni/fn_doc_stato_iniziale_id).
* **Se chi crea non dice lo stato, il database mette l'iniziale**; se dice l'iniziale, passa; se dice
  un altro stato, l'errore è `E_DOC_STATO_INIZIALE_NON_VALIDO`. È un errore tecnico: nessuna maschera
  crea un documento già avanti, lo commette solo chi scrive il codice.
* **Chi ha bisogno di un documento già avanti** (un passaggio da un altro documento, un import, una
  fixture di test) lo crea in bozza e lo porta avanti coi passaggi, nella stessa transazione.
* Le API di creazione non accettano lo stato dal client, e i service non lo scrivono.

Il trigger è uno solo,
[`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale), montato su
ogni testata che ha un vocabolario degli stati: la sua scheda dice dove e perché è il primo a
scattare.

---

## 4. Stati e passaggi: il vocabolario e la matrice

Ogni documento ha due tabelle di configurazione:

* il **vocabolario degli stati** (`config.stati_doc_*`): quali stati esistono, e per ognuno se è
  quello iniziale, se è quello di emissione, se è terminale, se è un annullo e, dove il documento li
  ha, se è quello di cessazione (il contratto) o di accettazione (preventivo e offerta);
* la **matrice dei passaggi** (`config.transizioni_stati_*`): **una riga = un passaggio ammesso**,
  da uno stato a un altro.

La matrice è **l'unica fonte** dei passaggi, e la leggono tutti:

| Chi la legge | Per fare che cosa |
| --- | --- |
| il **guard di transizione** del documento (un trigger) | rifiuta ogni cambio di stato che non è nella matrice, da qualunque strada arrivi |
| la **funzione di capability** del documento | dice quali azioni sono disponibili e perché le altre sono spente |
| il **frontend**, attraverso le capability | disegna i bottoni: il `meta` della riga porta la chiave dell'azione, l'etichetta, se chiede conferma, se il passaggio è manuale o di un processo |

⛔ Un passaggio scritto nel codice (un `IF` nel trigger, un elenco di stati in Python) è una seconda
matrice: prima o poi le due rispondono in modo diverso. I passaggi si aggiungono, si tolgono e si
spengono **nella tabella**.

Lo stesso vale per **gli stati che hanno un significato**: l'inizio, l'emissione, l'annullo, la
cessazione, l'accettazione. Il codice non scrive `'CESSATO'` o `'ACCETTATO'` per dire «lo stato di
cessazione» o «lo stato di accettazione»: lo dice una colonna del vocabolario (al più uno stato per
documento, ed è attivo), e lo legge il suo lettore —
[`script.fn_stato_cessazione_id`](/dbzero/script/funzioni/fn_stato_cessazione_id),
[`script.fn_stato_accettazione_id`](/dbzero/script/funzioni/fn_stato_accettazione_id) e gli altri
elencati in testa. Un documento che quello stato non lo ha (il preventivo non cessa) riceve un valore
vuoto. Chi ha già in mano la riga del vocabolario legge la colonna direttamente.

---

## 5. Chi cambia lo stato: il verbo

**Ogni cambio di stato di un documento passa da un verbo**: una funzione del database che cambia lo
stato e, nella sua prima riga, controlla il permesso. È il modello generale
«una scrittura = un verbo» della
[guida dei permessi](/guide/architettura-permessi-e-autorizzazioni) (§7.4), applicato allo stato dei
documenti.

* Il verbo **non decide** quali passaggi sono ammessi: lo dice la matrice, e lo fa rispettare il
  guard di transizione.
* Il verbo **non decide** quale permesso serve: lo legge dalla riga del passaggio (§6).
* I verbi specifici (annulla, conferma…) **non scrivono lo stato da sé**: fanno il loro lavoro
  (ritirare i legami, scrivere il magazzino…) e poi chiamano il verbo di stato del documento.
* Il backend chiama il verbo; non cambia lo stato con un `UPDATE`.

**Il verbo comune ha due metà**, perché i verbi dei documenti lavorano in mezzo:

1. la **prima riga**, [`script.fn_guard_passaggio`](/dbzero/script/funzioni/fn_guard_passaggio): il
   permesso del passaggio, prima di scrivere qualunque cosa;
2. la **scrittura**, [`script.fn_doc_scrivi_stato`](/dbzero/script/funzioni/fn_doc_scrivi_stato): lo
   stato, con tutti i controlli di sempre.

La bolla, per esempio, scrive i prelievi di magazzino fra le due, e i movimenti dopo.

**La porta.** Lo stato si scrive **solo** dalla seconda metà: un guard sulla colonna di stato
([`script.trgfn_doc_stato_solo_dal_verbo`](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo))
rifiuta ogni modifica diretta con `E_DOC_STATO_SOLO_DAL_VERBO`, anche quella del backend. Non si
toglie all'applicazione la scrittura sulla testata, che le serve per i campi ordinari: si chiude la
sola colonna di stato.

**I passaggi di processo.** Alcune righe della matrice non sono una scelta dell'operatore: le fa il
sistema come conseguenza di un'altra operazione (la bolla passa a «Reso» quando si conferma il reso
di tutta la sua merce). Sono le righe con `manuale = false`: le capability non le propongono, il
verbo le rifiuta se chieste a mano (`E_DOC_PASSAGGIO_DI_PROCESSO`), e le scrive solo il verbo che ne
è la causa, con la sola seconda metà.
Ogni riga della matrice **dichiara** se è manuale o di processo: una riga senza la dichiarazione non
si scrive, perché chi la leggeva da sé l'avrebbe interpretata in due modi diversi. Per la stessa
ragione una condizione sul tipo di lotto sta solo sui passaggi di processo: un passaggio manuale vale
per ogni lotto, così la lista e il dettaglio propongono gli stessi bottoni.

**Lo stato che il documento ha già.** Chiedere al verbo lo stato in cui il documento si trova (un
secondo «Emetti», la stessa conferma inviata due volte) non è un passaggio: la matrice non ha la riga
X → X, e il verbo lo rifiuta nella prima riga, prima di ogni suo lavoro, con lo stesso codice per
tutti i documenti (`E_DOC_GIA_NELLO_STATO`). Il guard di transizione invece guarda solo i cambi di
stato, e lascia passare un `UPDATE` che riscrive lo stesso stato: la regola è del verbo, non di ogni
scrittura della testata.

---

## 6. Chi può: il permesso sul passaggio

Le operazioni ordinarie su un documento (crearlo, modificarlo) chiedono il **livello** sull'area del
documento. Le operazioni di **processo** chiedono un'**azione di processo**, cioè un permesso con un
nome, che si concede a un profilo ([`config.azioni_processo`](/dbzero/config/tabelle/azioni_processo)).

**L'azione si dichiara sulla riga del passaggio, nella matrice.** Una riga senza azione chiede solo il
permesso sul documento. La stessa riga la leggono tre punti, e nessuno dei tre decide da sé:

| Chi | Che cosa fa con l'azione della riga |
| --- | --- |
| il **verbo** | la controlla ([`script.fn_guard_azione`](/dbzero/script/funzioni/fn_guard_azione)) e rifiuta con `E_PERMESSO_NEGATO` |
| il **backend** | risponde 403 subito, prima di aprire la transazione, con le stesse funzioni del database: chiede, non decide una seconda volta |
| le **capability** e le **liste** | nascondono il bottone a chi non ha l'azione: chiedono i passaggi permessi a [`script.fn_doc_azioni_permesse`](/dbzero/script/funzioni/fn_doc_azioni_permesse), una regola sola per il dettaglio e per la riga di una lista |

Un punto unico è ciò che rende i permessi **configurabili**: un'azione scritta nel corpo di un verbo,
o nel codice di una view, non la cambia nessuno senza un rilascio.

**Il permesso di un'operazione dentro il passaggio** non sta sulla riga. Se un passaggio, in certi
casi, fa anche un'operazione che ha un permesso suo, quel permesso lo chiede il verbo quando la fa.
È il caso della consegna di una bolla di trasferimento che muove merce: scrive gli arrivi in
magazzino e chiede `registra_magazzino`. Una riga della matrice non sa dire «solo se è un
trasferimento che muove merce», e il permesso protegge l'operazione di magazzino, non il passaggio.

**Quante azioni per documento: una, sui passaggi pesanti.** Ogni documento ha **un'azione** per i
passaggi che pesano — l'emissione e l'annullo di un documento emesso: chi può farlo può anche
disfarlo. Gli altri passaggi (spedito, accettato, rifiutato…) chiedono solo il permesso sul
documento. Nessun documento fa eccezione. Separare un giorno l'annullo dall'emissione è un cambio di
riga nella matrice, non un lavoro sul codice.

**Le azioni per riga** (togliere un documento dal giro di un lotto, e domani quelle degli altri
documenti) seguono la stessa regola in un'altra forma: un controllo del database dice perché il pulsante è
spento, la funzione che esegue l'azione rifiuta con lo stesso motivo, e una vista porta il motivo su ogni
riga. Il registro [`config.azioni_riga`](/dbzero/config/tabelle/azioni_riga) lega i tre pezzi, e il
frontend legge da lì quali colonne mostrare. La regola completa è nelle
[linee guida SQL](/linee-guida-sql) §12.5.

---

## 7. L'emissione

**Un documento che si stampa si emette solo da «Emetti»** (la rotta `/emetti/` del backend): numero e
PDF nascono **insieme**, nella stessa transazione. Nessun'altra strada — un cambio di stato generico,
una conferma, un passaggio da un altro documento — porta un documento che si stampa nello stato
emesso.

* Il **numero** lo assegna il database, al passaggio allo stato emesso: il meccanismo è quello della
  [guida della numerazione](/guide/numerazione-documenti-e-codici).
* Il **PDF** lo genera il modulo documenti, col modello di stampa del documento: [guida](/guide/documenti-e-stampe).
* Le **condizioni** per uscire dalla bozza (righe, indirizzi, causale…) stanno sul passaggio, nel
  guard del documento: sono sue, e le descrive la sua guida.
* **Quale stato è l'emissione** lo dice il vocabolario (colonna `emissione`), e lo legge
  [`script.fn_stato_emissione_id`](/dbzero/script/funzioni/fn_stato_emissione_id): il backend rifiuta
  quello stato sul cambio di stato generico, per ogni documento, senza un nome di stato scritto nel
  codice. «Emetti» ne legge il codice con
  [`script.fn_doc_stato_codice`](/dbzero/script/funzioni/fn_doc_stato_codice) a ogni richiesta, e lo
  passa al verbo; lo stesso codice gli dà l'azione da chiedere.

I documenti che non si stampano hanno il loro passaggio al posto dell'emissione: la commessa nasce
dalla push dei documenti a monte, la fattura segue gli step della pipeline di fatturazione.

La fattura ha una forma sua: **i pulsanti stanno sul lotto di fatturazione**, non sulla fattura. Il
lotto si numera, si riporta in bozza, si annulla mentre è in bozza; da lì parte anche la stampa, e sulla
fattura resta solo la ristampa. Lotto e fattura condividono vocabolario e matrice
([`config.stati_doc_fiscale_transizioni`](/dbzero/config/tabelle/stati_doc_fiscale_transizioni), coi
passaggi solo del lotto e solo della fattura). I passaggi manuali del lotto li scrive il suo verbo,
[`vendite.fn_cambia_stato_lotto`](/dbzero/vendite/funzioni/fn_cambia_stato_lotto), chiamato da
«riporta in bozza» e dall'annullo dopo la loro pulizia; l'avanzamento negli step lo scrive il giro della
pipeline, [`vendite.fn_lotto_proietta_stato_step`](/dbzero/vendite/funzioni/fn_lotto_proietta_stato_step);
la fattura cambia stato dal suo verbo,
[`vendite.fn_fattura_proietta_stato`](/dbzero/vendite/funzioni/fn_fattura_proietta_stato), che oggi chiama
solo la pipeline (tutti i passaggi della fattura sono di processo). Il permesso di «numera» si chiede quando
l'operatore preme il pulsante; il lavoro accodato scrive come passaggio di processo.

**Le origini della fattura.** Sulla fattura si citano i documenti a monte che il cliente riconosce — la
bolla, l'ordine, il contratto, l'offerta, il preventivo; per una nota di credito la fattura che corregge e
il reso —, non la commessa, che è un contenitore interno. Sono tutte sorgenti, di tipo diverso, e la
regola è una sola. Li dà [`vendite.fn_fattura_origini`](/dbzero/vendite/funzioni/fn_fattura_origini), a
stampa e dettaglio: parte dai genitori diretti del documento (al posto della commessa, i documenti delle
righe fatturate) e ne risale la catena, senza mai ripassare dalla commessa né dalla revisione di un'offerta
(una fattura non cita le revisioni superate). Quali tipi si citano lo dice
il registro delle sorgenti, colonna `citato_in_fattura` ([`config.sorgenti`](/dbzero/config/tabelle/sorgenti)).

---

## 8. L'annullo

Ogni documento ha un **verbo d'annullo**, tranne la fattura: una fattura numerata si storna con la nota
di credito, e prima della numerazione la si toglie dal lotto (il lotto in bozza, invece, si annulla).
Annullare un documento che ha consumato qualcosa di un
altro — la bolla che ha evaso un ordine, l'ordine nato da un preventivo — restituisce ciò che aveva
consumato: per questo non avviene in silenzio.

* Entrare in uno stato di annullo con dei legami è rifiutato con `E_DOC_ANNULLO_CON_LEGAMI`, che dice
  quanti sono, su qualunque strada cambi lo stato
  ([guard comune](/dbzero/vendite/funzioni/trgfn_doc_guard_annullo_con_legami)).
* Il backend mostra i legami ([`vendite.fn_documento_legami`](/dbzero/vendite/funzioni/fn_documento_legami))
  e, alla conferma, chiama il verbo d'annullo passando **quanti legami ha mostrato**: chi conferma
  dichiara ciò che ha visto, e se nel frattempo i legami sono cambiati la finestra si ripresenta.
* Il verbo d'annullo ritira i legami e poi cambia lo stato attraverso il verbo di stato (§5).

Quale stato è un annullo lo dice il vocabolario (`is_abortito`, uno solo per documento, ed è attivo), e lo
legge [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id); non il nome `'ANNULLATO'` scritto nel
codice. Lo legge anche il backend, per mandare l'annullo chiesto dal cambio di stato al verbo d'annullo.

---

## 9. Gli acquisti nascono sul modello

L'ordine e il DDT d'acquisto usano gli stessi vocabolari degli ordini e dei DDT di vendita, e seguono
**lo stesso modello**: stesso verbo, stessa matrice, stesse azioni, stessi building block. Quando un
documento di vendita viene portato al modello, il suo gemello d'acquisto ci arriva **nello stesso
lavoro**, non in una fase successiva: gli acquisti non hanno una copia loro delle regole, quindi non
possono sbagliarla in un altro modo.

---

## 10. A che punto è ogni documento

Stato al 27 ottobre 2026. ✅ = segue la regola; ❌ = non ancora, con che cosa fa oggi. La riga di un
documento cambia quando quel documento viene portato al modello (§11). Bolla e reso sono stati portati
il 25 ottobre 2026, database e backend (403 dalla riga del passaggio, emissione solo da «Emetti»). Il
preventivo è stato portato lo stesso giorno lato database; il backend lo segue (il 403 dalla riga del
passaggio e l'emissione letta dal vocabolario). L'ordine è stato portato lo stesso giorno lato database;
il backend lo segue (la conferma e il cambio di stato dal verbo, il 403 dalla riga del passaggio, il
ritiro della conferma senza «Emetti»). Il contratto è stato portato il 26 ottobre 2026 lato database;
il backend lo segue (l'attivazione e la cessazione dai verbi, il 403 dalla riga del passaggio, la
cessazione programmata decisa dal database). L'offerta è stata portata il 26 ottobre 2026 lato database;
il backend la segue (l'emissione, l'esito e l'annullo dai verbi, il 403 dalla riga del passaggio, la
motivazione chiesta dal database, la conferma dei legami all'annullo di una revisione). La commessa è stata
portata il 26 ottobre 2026 lato database; il backend la segue (il 403 dalla riga del passaggio, la firma
nuova del verbo). La fattura, col suo lotto, è stata portata il 27 ottobre 2026 lato database; il backend
la segue (il 403 dalla riga del passaggio su «numera» e «riporta in bozza», il giro della pipeline dai
verbi invece che con gli `UPDATE`, lo stato del job senza la sua copia delle regole). La versione di
listino è stata portata il 28 ottobre 2026 lato database; il backend non la segue ancora: finché non
chiama il verbo dell'attivazione, l'attivazione dall'applicazione è rifiutata dalla porta.

| Documento | Nasce in bozza (§3) | Matrice in tabella (§4) | Verbo di stato (§5) | Azione sul passaggio (§6) | Emissione (§7) | Annullo (§8) |
| --- | --- | --- | --- | --- | --- | --- |
| Preventivo | ✅ | ✅ | ✅ `fn_cambia_stato_preventivo` sul verbo comune, con la porta; ACCETTATO ↔ EVASO dalla proiezione dello smistamento; EMESSO → SCADUTO dal job delle scadenze (`fn_chiudi_preventivi_scaduti`, dal 2026-10-31) | ✅ `emetti_preventivo` su emissione e annullo dell'emesso e dell'accettato (backend allineato il 2026-10-25: il 403 dalla riga del passaggio) | ✅ solo da «Emetti»; le righe sul passaggio, nel guard | ✅ `fn_annulla_preventivo` → verbo di stato |
| Offerta | ✅ | ✅ (tabella `config.stati_doc_offerte_transizioni`: il nome fuori serie è una divergenza dichiarata, nessuna regola dipende dal nome) | ✅ `fn_cambia_stato_offerta` sul verbo comune, con la porta, e con la motivazione obbligatoria dove la riga del passaggio la chiede (rifiuto, annulli), e ammessa solo lì; il superamento e il ritorno della revisione precedente dalla proiezione delle revisioni vive | ✅ `emetti_offerta` sull'emissione e sull'annullo dell'accettata | ✅ solo da «Emetti». ⚠️ Il numero si assegna alla nascita, non all'emissione: divergenza dichiarata, tema a parte | ✅ `fn_annulla_offerta` → verbo di stato; prima ciò che vieta (un contratto o un ordine vivo, `fn_check_offerta_annullabile`), poi la conferma: la revisione precedente che torna emessa è un legame |
| Contratto | ✅ | ✅ | ✅ `fn_cambia_stato_contratto` sul verbo comune, con la porta; la cessazione con la sua data da `fn_cessa_contratto` (oggi: cessa; futura: programmata), quella per scadenza da `fn_cessa_contratti_scaduti` | ✅ `emetti_contratto` sull'attivazione e sulla cessazione | ✅ solo da «Emetti». ⚠️ Il numero si assegna alla nascita, non all'emissione: divergenza dichiarata, tema a parte | ✅ `fn_annulla_contratto` → verbo di stato |
| Ordine | ✅ | ✅ | ✅ `fn_cambia_stato_ordine` sul verbo comune, con la porta; l'evasione (confermato ↔ parzialmente evaso ↔ evaso) dalla proiezione delle bolle | ✅ `emetti_ordine` sulla conferma e sull'annullo del confermato | ✅ solo da «Emetti» (la conferma senza PDF è ritirata dal 2026-10-25). ⚠️ Il numero si assegna alla nascita, non all'emissione: divergenza dichiarata, tema a parte | ✅ `fn_annulla_ordine` → verbo di stato |
| DDT | ✅ | ✅ | ✅ `fn_cambia_stato_ddt` sul verbo comune, con la porta | ✅ `emetti_ddt` sulla riga di emissione e annullo dell'emesso; `registra_magazzino` nel verbo, per l'operazione di magazzino | ✅ solo da «Emetti»: il cambio stato generico rifiuta emesso | ✅ `fn_annulla_ddt` → verbo di stato |
| Reso | ✅ | ✅ | ✅ `fn_conferma_reso`, `fn_annulla_reso` sul verbo comune, con la porta | ✅ `conferma_reso` sulla riga di conferma e annullo del confermato | — la conferma fa da emissione | ✅ verbo |
| Commessa | ✅ | ✅ (tabella in `vendite`, non in `config`) | ✅ `fn_cambia_stato_commessa` sul verbo comune, con la porta; il passaggio a pronta della push dalla proiezione `fn_commessa_proietta_stato_emittibile` | ✅ `cambia_stato_commessa` su «rendi pronta», «riapri», «chiudi» e sull'annullo di una commessa non in bozza | — nasce dalla push | ✅ `fn_annulla_commessa` → verbo di stato |
| Fattura (col lotto) | ✅ | ✅ (`config.stati_doc_fiscale_transizioni`, con passaggi solo del lotto e solo della fattura singola) | ✅ il lotto `fn_cambia_stato_lotto` (passaggi manuali) e `fn_lotto_proietta_stato_step` (il giro), la fattura `fn_fattura_proietta_stato`, con la porta su entrambi | ✅ `numera_fatture_lotti` su «numera» e «riporta in bozza»; l'annullo della bozza senza azione | — la pipeline (numera) | — la nota di credito; prima della numerazione, «togli dal lotto»; il lotto in bozza si annulla |
| Versione di listino | ✅ | ✅ (`config.transizioni_stati_listino_versioni`) | ✅ `fn_attiva_versione_listino` sul verbo comune, con la porta: chiude anche le versioni precedenti che si sovrappongono; la chiusura a scadenza da `fn_chiudi_versioni_listino_scadute` (il job) | ✅ `attiva_listino` su «Attiva» | — l'attivazione mette i prezzi in uso; la versione non si stampa | — non si annulla: in bozza si elimina, attiva si chiude con la fine validità |
| Ordine e DDT d'acquisto | ✅ | ❌ nessun guard di transizione | ❌ | ❌ | ❌ | ❌ |

Le azioni a catalogo che nessuno usava — `genera_fattura`, `approva_fattura`, `emetti_fattura` — sono
ritirate col giro della fattura, insieme a `reset_lotto_draft` («riporta in bozza» chiede
`numera_fatture_lotti`).

**La revisione di offerta e preventivo** si dice in due modi, ed è una scelta: l'offerta mette la
revisione precedente nello stato *superata* (e la riporta a *emessa* se l'ultima revisione viva si
annulla, con la conferma dei legami del §8, che mostra il numero della revisione che torna emessa), il preventivo la **calcola** (la revisione valida è
l'ultima emessa, e la precedente resta *emesso*). Non è una divergenza da correggere: l'offerta è un
documento per revisione, il preventivo versiona lo stesso numero. Il perché sta nella
[guida dei preventivi, §4.5](/guide/gestione-preventivi#45-differenza-col-modello-offerte).

Lo stato del **job** del lotto (in esecuzione, completato, errore: com'è andato il lavoro della pipeline)
non è lo stato del documento, ma segue la stessa idea: i valori nel vocabolario
[`config.stati_lotto_job`](/dbzero/config/tabelle/stati_lotto_job), i passaggi nella matrice
[`config.transizioni_stati_lotto_job`](/dbzero/config/tabelle/transizioni_stati_lotto_job), una regola sola
applicata dal guard a ogni scrittura.

---

## 11. Come si porta un documento al modello

* **Un documento per volta, tutto intero**: verbo, matrice, azioni, emissione, annullo, insieme al
  suo gemello d'acquisto se ne ha uno. Non un tema alla volta su nove documenti: è così che una regola
  comune finisce ricopiata in nove posti, e le nove copie divergono.
* **Prima, chi emette o conferma senza passare da «Emetti»** (import, passaggi da altri documenti):
  si censisce, e per ognuno si decide.
* **Le copie si ritirano nello stesso lavoro**: i passaggi scritti nel codice, gli stati ripetuti in
  Python, le azioni controllate solo dal backend.
* Prima di ricopiare una regola nelle capability o nei guard di ogni documento, si valuta se può
  vivere in un **building block comune che legge la matrice**.
* Si va **per la strada più corta**, senza fasi in cui vecchio e nuovo convivono: il database consegna
  il suo lavoro e scrive al backend che cosa si è rotto e come si ripara.

---

## 12. Da dove vengono le regole

Le decisioni, con la data e le alternative scartate, stanno nel brief del cantiere:
[brief-modello-documento-vendita](../dev/work-done/brief-modello-documento-vendita.md) — M-1 …
M-6 (verbo, emissione, permesso, azioni, matrici, nascita), N-1 … N-3 e P-1 … P-3 (lo stato
iniziale). Il permesso nel verbo viene da
[brief-db-permesso-nel-verbo-di-scrittura](../dev/work-done/brief-db-permesso-nel-verbo-di-scrittura.md);
l'annullo con legami da
[brief-db-annullo-documento-con-legami](../dev/work-done/brief-db-annullo-documento-con-legami.md).

{% include-markdown "signature-core.md" %}
