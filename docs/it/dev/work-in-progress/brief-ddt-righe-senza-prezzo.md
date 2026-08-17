# Brief — il DDT deve ammettere righe a prezzo zero, e oggi non le ammette

> **Tipo**: brief (decisione presa, perimetro da chiudere) · **Data**: 2026-08-17 ·
> **Owner**: Tid · **Stato**: 🟡 **APERTO** — decisione di dominio presa, il
> lavoro tecnico è da definire con BE e DB.
>
> **Origine**: rilievo in-app di Tid (2026-08-17) mentre validava **DL-28**:
> *«se inserisco un articolo senza prezzo compare "impossibile risolvere il
> prezzo listino", e questo per qualsiasi causale scelga»*.
>
> **Decisione di Tid (2026-08-17)**: **deve essere permesso inserire articoli a
> prezzo 0 nel DDT.**
>
>
> ## 🔢 ORDINE DEI LAVORI COLLEGATI
>
> **1.** partita generalizzata → **2.** pannello situazione merce (ordine e DDT)
> → **3.** nota di credito.  ·  *In parallelo e indipendente*: righe DDT a
> prezzo zero.
>
> Catena completa e ragioni in
> [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md).
>
> **Rif.**: [brief-design-fatturazione-due-lenti.md](../work-done/brief-design-fatturazione-due-lenti.md)
> §10 **DL-28** · [brief-db-fatturazione-ddt-resi.md](../work-done/brief-db-fatturazione-ddt-resi.md) §4a ·
> checklist V2 in [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md) §13.2.

---

## 1. Il fatto: una premessa del design non è vera nel prodotto

DL-28 poggia su questa frase, testuale:

> *«Il DDT ammette righe senza prezzo **per design** ("solo trasporto"), ma il
> lister non le esclude → standalone senza prezzi a SPEDITO = "da fatturare" con
> prezzo vuoto.»*

Su quella premessa è stato costruito il **gate all'emissione**: causale
fatturabile → ogni riga deve avere un prezzo **risolvibile**, altrimenti blocco
parlante; *«il prezzo dimenticato diventa errore, non silenzio»*.

⚠️ **Ma la riga senza prezzo non è inseribile.** Provando a caricarla, il
pricing la respinge con *«impossibile risolvere il prezzo listino»* — **e lo fa
per qualunque causale**, comprese quelle non fatturabili (conto visione,
campionatura, trasferimento, conto lavoro, omaggio).

Ne discendono due conseguenze, entrambe da sanare:

1. **il DDT di solo trasporto non è realizzabile**, pur essendo il caso che DL-28
   dichiara esistere «per design»;
2. **la metà «blocco parlante» di DL-28 è irraggiungibile**: un gate che si
   attiva su una condizione che il sistema non consente di produrre non scatta
   mai. Non è un gate sbagliato — è un gate che presidia una porta murata.

## 2. La decisione

**Le righe a prezzo zero sono ammesse nel DDT.** Il documento di trasporto
descrive merce che si muove, e la merce si muove anche quando non si vende:
conto visione, campionatura, riparazione, trasferimento fra depositi, conto
lavorazione, omaggio. Pretendere un prezzo di listino su quei documenti è
chiedere un dato che per essi non ha significato.

⭐ **E il vocabolario per distinguerli esiste già**: `config.causali_trasporto`
porta la colonna `fatturabile`, seedata il 2026-07-17 — `VENDITA` è l'unica
`true`, le altre sette `false`. Era già la sede dell'intento, secondo la regola
di DL-28: *«l'intento non si inferisce dall'assenza di prezzo (ambiguo:
dimenticanza o scelta): si dichiara col campo che l'operatore già compila»*.

## 3. Le due domande da chiudere prima di scrivere codice

**3.1 Il prezzo zero è ammesso sempre, o solo su causale non fatturabile?**

Le due letture non sono equivalenti:

* **sempre** — la riga si carica comunque, e chi presidia è il **solo** gate
  all'emissione di DL-28: con causale fatturabile il DDT non esce finché i
  prezzi non ci sono. Il difetto («ho dimenticato il prezzo») viene intercettato
  al momento giusto, cioè quando il documento sta per avere effetti;
* **solo se non fatturabile** — il blocco resta in inserimento per le vendite.
  Più stretto, ma sposta l'errore su un momento in cui la causale potrebbe non
  essere ancora stata scelta, e obbliga a ri-validare le righe se la causale
  cambia dopo.

⚠️ **La seconda lettura ha un effetto collaterale da non sottovalutare**: la
causale è di **testata** e le righe si caricano dopo. Un vincolo di riga che
dipende dalla testata si rompe ogni volta che la testata cambia — e DL-28 aveva
già scelto di mettere il presidio **all'emissione** proprio per non incastrarsi
in quell'ordine.

**Raccomandazione**: ammettere il prezzo zero **sempre**, lasciando a DL-28 il
presidio. È anche l'unica delle due che rende raggiungibile il gate già scritto.

**3.2 Prezzo `0` o prezzo assente?**

Non sono la stessa cosa e il modello deve dirlo:

* `0` = «vale zero», un'affermazione — è il caso dell'omaggio;
* `NULL` = «non si applica», un'astensione — è il caso del trasferimento fra
  depositi.

Oggi la riga di DDT non consente né l'uno né l'altro. Va deciso se ne bastano
uno solo o se servono entrambi, perché la scelta si riflette sul gate di DL-28
(«prezzo risolvibile» deve considerare lo zero un valore valido?) e sulla stampa
del documento.

## 4. Da verificare prima di stimare

* **dove sta il blocco**: se in `PricingService`/`fn_resolve_prezzo_listino_v2`
  (che solleva quando non risolve) o in una validazione BE a monte. Cambia il
  perimetro: nel primo caso il chiamante DDT deve poter chiedere una risoluzione
  **non obbligatoria**, nel secondo basta allentare il guard;
* **chi altro dipende da quel comportamento**: il pricing è condiviso, e
  ammettere il non-risolto per i DDT non deve ammetterlo per ordini e
  preventivi, dove un prezzo mancante è davvero un difetto;
* **l'effetto sul contatore**: una riga a prezzo zero che entra in commessa
  produce un'attività a valore zero. Va confermato che i cruscotti a valore la
  reggano senza contarla come «merce da fatturare» per zero euro — o che le
  causali non fatturabili la tengano fuori, come DL-28 già prevede.

## 5. Conseguenza documentale, da non dimenticare

Qualunque sia la scelta del §3, **la premessa di DL-28 va corretta nel
design-of-record**. Oggi il §10 descrive come esistente un caso che il prodotto
non consente, e chi lo rileggerà fra sei mesi non avrà modo di accorgersene:
troverà un gate coerente con una premessa falsa.

⚠️ Finché la premessa non è vera, la voce **DL-28 della checklist V2 non è
spuntabile per intero**: la metà «causale non fatturabile fuori dalle card» si
prova (basta un DDT con prezzo e causale CONTO_VISIONE), la metà «blocco
parlante sul prezzo mancante» **no**, perché il caso non si può costruire.

## 6. Definizione di «fatto» (bozza)

* [ ] si carica una riga di DDT senza prezzo (o a zero) senza che il pricing la
      respinga;
* [ ] con causale **fatturabile**, l'emissione **blocca** con messaggio
      parlante che indica la riga — DL-28 finalmente esercitato;
* [ ] con causale **non fatturabile**, il DDT si emette e resta **fuori** da
      card e lister;
* [ ] ordini e preventivi **continuano** a rifiutare il prezzo non risolvibile:
      l'allentamento è del solo DDT;
* [ ] la premessa di DL-28 nel design-of-record è allineata al comportamento
      reale (§5).
