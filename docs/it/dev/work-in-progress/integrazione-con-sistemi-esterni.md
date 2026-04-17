# Integrazioni con sistemi esterni

**Stato:** WIP — bozza di lavoro
**Autore:** Michele Carlo
**Progetto:** ZeroERP

---

## Di cosa parliamo

In un ERP reale i dati non arrivano solo dagli operatori che digitano nelle maschere. Arrivano anche da fuori: ordini dal portale clienti, flussi EDI dai fornitori, fatture elettroniche dall'SdI, CSV scaricati da marketplace, email con allegati, bot, chatbot, form web. Ognuno di questi canali ha caratteristiche diverse — qualcuno è affidabile e strutturato, qualcuno è caotico e ambiguo.

La domanda che ci poniamo in questo documento è semplice: **quando conviene far scrivere questi dati direttamente nelle tabelle operative dell'ERP, e quando invece conviene farli passare per un'area di staging con un workflow di revisione?**

Non è una domanda tecnica astratta. Sbagliare da una parte significa appesantire inutilmente il sistema con passaggi burocratici che non servono a nessuno. Sbagliare dall'altra significa trovarsi ordini fantasma, clienti duplicati, preventivi collegati al cliente sbagliato, e operatori che inseguono errori invece di lavorare.

---

## Il concetto di "staging" detto in modo semplice

Uno *staging* è una zona di parcheggio. Quando arriva un dato da fuori, invece di scriverlo subito in `vendite.ordine` o `anagrafiche.cliente`, lo metti in una tabella a parte — tipo `portale.richieste_in_entrata` o `integrazioni.documenti_ricevuti` — dove rimane in uno stato tipo `DA_LAVORARE`. Lì dentro il dato esiste, è salvato, non si perde, ma non è ancora "ufficiale". Non genera movimenti contabili, non attiva pratiche, non blocca giacenze di magazzino.

Poi succede una di queste due cose:

- Un processo automatico riesce a validare e collegare tutto quello che serve (il cliente è riconosciuto, gli articoli esistono, i prezzi tornano) e promuove il dato in area operativa, spostandolo in `vendite.ordine` con stato `BOZZA` o `CONFERMATO`.
- Un operatore apre l'area staging, vede cosa è arrivato, sistema quello che non è chiaro (tipo "questo cliente nuovo è davvero nuovo o è un doppione di uno esistente?"), e fa la promozione a mano.

Finché il dato sta in staging, può essere modificato, scartato, unito ad altri, arricchito. Quando diventa un ordine vero, invece, è un documento con tutte le conseguenze del caso.

È lo stesso principio della "posta in arrivo" vs "pratiche aperte" in un ufficio reale. La posta in arrivo è dove arriva tutto, anche la roba sbagliata e i duplicati. Le pratiche aperte sono quelle già smistate e in lavorazione.

---

## Quando lo staging è utile

Lo staging serve quando c'è **almeno una** di queste condizioni:

**1. Il mittente non è identificato in modo certo.**
Un form pubblico sul sito dove chiunque può chiedere un preventivo senza registrarsi. Un marketplace che ti manda ordini con il nome "Mario Rossi" ma senza partita IVA, e tu hai già tre Mario Rossi in anagrafica. Un'email con un PDF allegato dove il cliente si identifica come vuole.

In questi casi, scrivere direttamente in `anagrafiche.cliente` vuol dire riempire il database di doppioni che poi qualcuno dovrà ripulire. Meglio tenere il dato in staging, far decidere a un operatore se è un cliente nuovo o uno già esistente, e poi promuovere.

**2. Il contenuto non è strutturato o è ambiguo.**
Un modulo di richiesta preventivo dove il cliente scrive in un campo libero "vorrei tre chiavi inglesi tipo quelle grandi che avete in vetrina". Tu non hai modo di mapparlo automaticamente a un codice articolo. Serve un umano che legga, chieda chiarimenti se necessario, e traduca la richiesta in righe d'ordine con codici veri.

**3. Il formato cambia o è imprevedibile.**
Listini prezzi dai fornitori che arrivano come Excel con colonne ogni volta diverse. Ordini EDI da un cliente grosso che hanno il loro standard aziendale. Flussi SII/ARERA che cambiano versione due volte l'anno. Qui lo staging serve anche come zona cuscinetto contro i cambi di formato: importi quello che riesci, il resto lo parcheggi e lo fai sistemare a mano.

**4. Servono controlli o autorizzazioni prima che il dato diventi ufficiale.**
Un ordine da portale B2B sopra una certa soglia che deve essere approvato dal commerciale. Una richiesta di apertura credito. Un ordine con articoli a magazzino zero che richiede decisione umana (si ordina al fornitore? si propone un sostituto? si rifiuta?).

**5. Il canale in entrata è inaffidabile.**
Un marketplace che ogni tanto rimanda lo stesso ordine due volte. Un partner EDI che ogni tanto manda file corrotti. Lo staging ti permette di deduplicare, validare, e scartare la spazzatura prima che inquini le tabelle vere.

**6. Vuoi una tracciabilità pulita dell'originale ricevuto.**
Se un domani il cliente contesta "ma io vi avevo scritto X", devi poter recuperare il documento esattamente come è arrivato, non il risultato dell'elaborazione. Lo staging è il tuo archivio legale di cosa è entrato e quando.

---

## Quando lo staging è inutile (o peggio, dannoso)

Lo staging è un peso. Aggiunge tabelle, stati, workflow, maschere operatore, formazione. Se non serve, evitalo.

**1. Utente loggato e autenticato che compila un form con schema rigido.**
Un cliente B2B registrato sul portale che compila il form "nuovo ordine" scegliendo articoli dal catalogo pubblicato, con prezzi già concordati. Il cliente lo conosci (è loggato), gli articoli li conosci (li hai pubblicati tu), i prezzi li conosci (li hai calcolati tu dal listino). Non c'è nulla da sistemare. Scrive direttamente in `vendite.ordine` stato `BOZZA` o `CONFERMATO`, fine.

**2. Dati tecnici letti dal gestionale del partner via API.**
Se hai un'integrazione API-to-API con un fornitore fidato dove tu chiedi "dammi lo stato dell'ordine 12345" e lui ti risponde con JSON strutturato, qui lo staging non serve. Il dato arriva già coerente, mappato su un'interfaccia che avete concordato, e lo usi subito.

**3. Operazioni idempotenti e a bassa criticità.**
Un webhook che ti dice "il pacco è stato consegnato". Aggiorni lo stato della spedizione e buonanotte. Metterlo in staging sarebbe teatro.

**4. Quando l'operatore dovrebbe solo cliccare "conferma" senza guardare nulla.**
Se lo staging diventa un passaggio formale dove l'operatore tira sempre avanti senza leggere, hai creato solo rumore. O togli lo staging, o trovi il modo di farlo saltare quando i controlli automatici passano tutti.

---

## Esempi concreti (ferramenta con negozio online e B2B)

Facciamo finta di avere una ferramenta "Rossi Ferramenta SRL" con negozio fisico, e-commerce B2C per privati, portale B2B per aziende clienti (idraulici, muratori, imprese edili), e qualche fornitore grosso con cui si scambiano file EDI.

### Scenario 1 — Ordine B2C dal sito

Una signora di Ancona compra online un trapano da 89 euro. Si è registrata al volo, pagamento con carta, articolo a magazzino.

**Serve staging?** No. Il catalogo è quello che hai pubblicato, il cliente è loggato (anche se registrato 30 secondi fa, è identificato in modo univoco con email verificata), il prezzo è quello che hai pubblicato, il pagamento è già incassato da Stripe. L'ordine nasce direttamente in `vendite.ordine` stato `CONFERMATO` e parte tutto il flusso normale.

L'unica cosa che vale la pena fare è un controllo di deduplica soft sull'anagrafica cliente ("c'è già una Maria Bianchi con questa email? unisci") ma si fa in transazione, non in staging.

### Scenario 2 — Richiesta preventivo da modulo pubblico

Dal sito, sezione "hai un progetto? chiedi un preventivo", un geometra scrive: *"Buongiorno, sto ristrutturando un bagno, mi servono tipo 50 metri di tubo multistrato 20mm, raccorderia assortita, e due miscelatori termostatici di buona marca. Mi fate un preventivo? Francesco M."*

**Serve staging?** Sì, assolutamente. Il cliente non è registrato, "raccorderia assortita" non è un codice articolo, "di buona marca" non è un prezzo. Qui lo staging non è un optional, è proprio *il punto*: il dato arriva in `portale.richieste_preventivo` stato `DA_LAVORARE`, l'operatore vede la richiesta, chiama o risponde via email per chiarire, costruisce un preventivo vero con righe e prezzi, e solo a quel punto promuove il tutto a `vendite.preventivo`.

### Scenario 3 — Ordine B2B da cliente storico

L'impresa edile "Bianchi Costruzioni", cliente da 12 anni con listino dedicato, entra nel portale B2B con le sue credenziali e inserisce un ordine di 40 righe scegliendo dal catalogo.

**Serve staging?** No, per le stesse ragioni dello Scenario 1. Cliente identificato, catalogo chiuso, listino applicato automaticamente da `vendite.fn_resolve_prezzo_listino`. Va dritto in `vendite.ordine`.

**Caveat:** se l'ordine supera una soglia (esempio: 10.000€) e c'è una policy interna di approvazione, lo stato iniziale può essere `DA_APPROVARE` invece che `CONFERMATO`. Ma è uno stato del documento operativo, non staging vero e proprio.

### Scenario 4 — Listino fornitore via email

Il rappresentante della Würth manda ogni trimestre un file Excel con 8.000 righe di aggiornamento prezzi. Le colonne ogni tanto cambiano, ogni tanto aggiungono articoli nuovi, ogni tanto tolgono codici vecchi, ogni tanto sbagliano una virgola decimale.

**Serve staging?** Sì, e forse è il caso più classico. Il file arriva in `integrazioni.listini_fornitore_staging`, si fa un'elaborazione che evidenzia: articoli nuovi (da codificare?), articoli scomparsi (da archiviare?), variazioni anomale (aumento del 300% = probabile errore del rappresentante?), mapping incerti. L'operatore degli acquisti guarda, decide, e poi lancia la promozione verso `acquisti.listino_fornitore`.

### Scenario 5 — Fattura elettronica passiva da SdI

Arriva una fattura XML dallo SdI da un fornitore.

**Serve staging?** Sì, ma lo staging qui è quasi un obbligo normativo: devi conservare il file originale firmato per 10 anni, devi poter gestire il caso "fattura ricevuta ma non riconosco il fornitore", "fattura con importo che non corrisponde all'ordine", "fattura doppia". Quindi `contabilita.fatture_passive_in_entrata` stato `DA_REGISTRARE`, e solo dopo riconciliazione diventa movimento contabile.

### Scenario 6 — Webhook di tracking spedizione

Il corriere manda un webhook "pacco AB12345 consegnato alle 14:32".

**Serve staging?** No. Trovi la spedizione per tracking number, aggiorni lo stato. Fine. Se il tracking number non esiste logghi un warning e tiri avanti.

### Scenario 7 — Ordini da marketplace (Amazon, eBay)

Ordini che arrivano da Amazon Seller API. Ogni marketplace ha il suo formato, il suo cliente "anonimo" (l'indirizzo c'è ma la mail è offuscata), le sue regole su prezzi e promozioni.

**Serve staging?** Sì. Entra in `integrazioni.ordini_marketplace_staging`, si fa matching con anagrafica (esiste già un cliente con questo indirizzo? di solito no, si crea "cliente marketplace Amazon" generico o nominativo), si verificano articoli e prezzi (il prezzo marketplace deve essere accettato come è, anche se diverso dal listino), e poi si promuove a `vendite.ordine`. Per ordini con matching automatico al 100% la promozione può essere automatica; per quelli con anomalie resta in staging per l'operatore.

### Scenario 8 — API verso il gestionale del cliente grosso

Un cliente industriale vuole integrarsi con te via API: il loro sistema ti chiama quando vogliono fare un ordine, passando i codici articolo del loro catalogo (che tu hai già mappato sui tuoi).

**Serve staging?** Dipende. Se avete concordato un'interfaccia stretta con validazione rigorosa e il mapping codici è stabile, va dritto in `vendite.ordine`. Se invece il mapping è soggetto a drift (loro aggiungono codici senza avvisarti), uno staging leggero con validazione + fallback manuale sugli articoli non riconosciuti ha senso.

---

## Come decidere in pratica — una regola spannometrica

Quando stai progettando un nuovo canale di ingresso, fatti queste quattro domande:

1. **Il mittente è identificato in modo certo?** (sì/no)
2. **Il contenuto è strutturato con schema rigido?** (sì/no)
3. **Le referenze nel contenuto (clienti, articoli, prezzi) sono tutte a codici che già conosci?** (sì/no)
4. **Serve una validazione umana per policy aziendali?** (sì/no)

Se le prime tre sono tutte sì e la quarta è no, **salta lo staging**, scrivi direttamente nell'area operativa.

Se anche una sola delle prime tre è no, o la quarta è sì, **metti uno staging**.

---

## Anti-pattern da evitare

**Staging teatro.** Creare un'area di staging dove tutto arriva "valido" e l'operatore clicca sempre conferma senza guardare. Serve solo a far perdere tempo. Se il canale è affidabile, taglialo.

**Staging buco nero.** Mettere uno staging e poi non dargli una maschera operatore decente, così i dati ci entrano e non escono più. Lo staging senza interfaccia di lavorazione è peggio che non averlo.

**Staging come cestino.** Usare lo staging per parcheggiare dati problematici che nessuno ha voglia di sistemare. Dopo sei mesi hai 40.000 record da `DA_LAVORARE` che sono diventati archeologia. Ci vuole una policy di aging: dopo tot giorni uno staging non lavorato va in `SCARTATO` con motivazione, e se ce ne sono tanti vuol dire che c'è un problema a monte da risolvere.

**Staging che duplica il modello operativo.** Se la tabella di staging ha esattamente le stesse colonne e gli stessi vincoli di `vendite.ordine`, hai solo fatto un clone inutile. Lo staging deve avere vincoli più deboli (campi opzionali dove l'operativa ha NOT NULL, foreign key facoltative, campi "testo libero" in attesa di essere risolti in codice), altrimenti non risolve nessuno dei problemi che dovrebbe risolvere.

**API "intelligente" che decide da sola in casi ambigui.** L'API che riceve un ordine, non trova il cliente, e *inventa* un cliente nuovo senza avvisare nessuno. Nel giro di un anno ti trovi 200 "Mario Rossi" in anagrafica. Meglio rifiutare l'ordine (se sei rigido) o metterlo in staging (se vuoi recuperarlo), ma mai far decidere silenziosamente all'automatismo cose che avrebbero bisogno di un umano.

---

## Collegamenti con il modulo `pratiche`

Una riflessione per quando passeremo dall'architettura alla realizzazione: lo staging e il modulo `pratiche` possono lavorare insieme molto bene.

Una richiesta che arriva in staging — poniamo il preventivo del geometra dello Scenario 2 — può generare automaticamente una `pratica` di tipo "gestione richiesta preventivo portale" che prende in carico il lavoro di trasformare la richiesta in preventivo vero. Così lo staging diventa il *contenuto* e la pratica diventa il *processo* con cui ci lavori sopra (assegnazione a un operatore, scadenze, stati, logbook).

Questo è proprio il pattern che usavi nel tuo vecchio sistema gas: flusso in entrata → pratica generata → lavorazione operatore → chiusura con creazione dei documenti operativi. Vale la pena tenerlo a mente quando definiremo i `tipo_prestazione` del modulo pratiche — alcuni avranno come "input" un record di staging invece che una creazione manuale dell'operatore.

---

## Cose da decidere più avanti

- Struttura comune delle tabelle di staging: un modello unificato (`integrazioni.documento_ricevuto` polimorfico con payload JSONB) o tabelle dedicate per canale? Pro e contro da valutare sul campo.
- Policy di retention: quanto tempo teniamo un record in staging prima di archiviarlo/scartarlo? Probabilmente varia per tipo di documento.
- Chi può promuovere cosa: permessi granulari sui workflow di promozione (un commerciale può confermare ordini sotto soglia X, solo il responsabile vendite sopra).
- Eventi / hook: la promozione da staging a operativo è un buon punto per esporre eventi verso altri moduli (magazzino, contabilità).
- Gestione degli allegati originali: il file XML della fattura passiva, il PDF del preventivo richiesto, l'Excel del listino — dove li conserviamo e per quanto.

---

*Documento in lavorazione. Da rivedere man mano che i moduli di integrazione prendono forma.*