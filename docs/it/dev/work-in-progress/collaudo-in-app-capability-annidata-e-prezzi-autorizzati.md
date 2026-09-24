# Collaudo in-app · La capability annidata e i prezzi non autorizzati

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano — il *perché* sta nei due brief
> chiusi, [brief-be-fe-capability-annidata.md](../work-done/brief-be-fe-capability-annidata.md)
> e [brief-db-preventivi-congelamento-pricing.md](../work-done/brief-db-preventivi-congelamento-pricing.md);
> qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** I due cantieri sono chiusi a codice su tutti i lati: DB
> applicato (`20260924-20 → -37`, pgTAP verdi), BE e FE mergiati, presidi verdi
> (`guard:capability`, `useEntityCapabilities.spec.js`, `useDrawerActions.spec.js`).
> Ma **nessun test monta un drawer**: che un drawer legga il blob da
> `detail.capabilities` e che il tooltip porti il motivo col numero l'ha
> visto solo chi l'ha scritto. Un drawer che legge la forma sbagliata non dà
> errori: mostra una barra **vuota** o un pulsante PDF **senza modo**.
>
> **Stato**: ✏️ scritto il 2026-09-24, da eseguire.
> **Ambiente**: sviluppo (`dbdev`). **Utente**: un operatore con l'area
> vendite in scrittura e il permesso di cambio stato dei documenti.

---

## ⛔ Prima di cominciare

| | Cosa | Perché conta |
| --- | --- | --- |
| **Dato** | Un prezzo **in attesa** e uno **rifiutato** vanno **costruiti**: su una riga metti un prezzo fuori listino oltre la soglia → «Richiedi approvazione» (la riga va `PENDING`); per il rifiutato, il responsabile rifiuta da **Approvazioni prezzo** | Al 2026-09-24 sul DB di sviluppo nessun documento in bozza o emesso ne ha uno: cercarlo non serve |
| **Due utenti** | Un operatore e un **responsabile** che può esitare le approvazioni | Il rifiutato lo produce solo lui |
| **Leggere il tooltip** | Il perché di un pulsante spento sta **solo** nel tooltip (col mouse sopra il pulsante spento): il banner dei prezzi del preventivo è stato **ritirato**, per scelta | Non cercare un banner: se ne compare uno sui prezzi, è codice vecchio |

---

## 1. Ogni drawer legge il blob annidato

Per ciascun drawer apri **un documento in bozza e uno in uno stato avanzato**.
Le quattro cose da guardare sono sempre le stesse:

* **(a) barra azioni** — i pulsanti di stato ci sono (non una barra vuota);
* **(b) nota di stato** — il messaggio informativo sotto la testata, dove il documento ne ha uno;
* **(c) PDF** — il pulsante c'è e apre l'anteprima **nel modo giusto** (bozza/definitivo);
* **(d) campi bloccati** — fuori bozza la form è in sola lettura, in bozza no.

| | Drawer | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | **Preventivo** | (a)-(d). In più «Crea revisione» da EMESSO e «Push commessa» dove previsto | Barra vuota = il drawer legge `detail.available_actions` piatto |
| **1.2** | **Contratto** | (a)-(d). ⚠️ Un contratto ATTIVO ha la form bloccata ma deve mostrare **«Cessa»** | Se «Cessa» sparisce, il readonly passato al mapper è quello sbagliato |
| **1.3** | **Offerta** | (a)-(d). «Push a contratto» e «Genera ordine» spenti col **motivo nel tooltip** quando non ammessi | Offerta: il ripiego è `capabilities: {}` — un blob rotto dà una barra vuota **e un warning nel log BE**, non un errore |
| **1.4** | **Ordine** | (a)-(d). «Push commessa» spento col motivo | — |
| **1.5** | **DDT** | (a)-(d). «Push commessa» spento col motivo | — |
| **1.6** | **Reso** | (a)-(d) | — |
| **1.7** | **Promo articolo** | (a), (d) e il **banner promo** (stato temporale, date minime di validità) | Il banner legge `stato_temporale` / `min_valido_*` dal blob |
| **1.8** | **Lotto** | Barra azioni e kebab di lista: le azioni vengono da `available_actions` del blob | — |
| **1.9** | **Documento interno** (magazzino) | «Registra» spento col motivo quando non ammesso; la nota di stato compare **una volta sola** | Due note uguali = la copia sulla testata è tornata |

---

## 2. Un prezzo non autorizzato non esce dalla bozza

Su ogni documento: il pulsante che fa avanzare è **spento**, il tooltip dice il
motivo **col numero** (*«Ci sono prezzi in attesa di approvazione (1).»*),
**«Annulla» resta acceso**, e testata e righe non bloccate restano
modificabili in bozza.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | **Preventivo** in bozza con una riga in attesa | «Emetti» spento col motivo; **«Annulla» acceso**; testata e **altre** righe modificabili, la riga in attesa no | Se si spegne tutto, è tornata la riscrittura Python del blob |
| **2.2** | **Preventivo EMESSO** con un prezzo non autorizzato | «Accetta» spento col motivo. ⚠️ **Dall'app il caso non nasce più**: la richiesta si apre in bozza, e in bozza blocca già l'emissione. Lo coprono i pgTAP (`test-fn-check-prezzi-autorizzati-v1`, 13-15; offerta 25-26), che lo costruiscono con un `UPDATE` diretto. A video solo se Tid lo costruisce a mano su dev | Se si riesce a produrlo **dall'app**, c'è una strada che il guard non vede: segnala |
| **2.3** | **Preventivo** con una riga rifiutata **e** una in attesa | Il tooltip porta **due righe**, prima l'attesa poi il rifiutato, ognuna col suo numero | Una riga sola = il mapper rende solo il primo motivo |
| **2.4** | Correggi il prezzo della riga rifiutata (torna nel listino) | Il rifiuto sparisce, il motivo si toglie dal tooltip | — |
| **2.5** | **Contratto** con una riga rifiutata | «Attiva» spento col motivo | — |
| **2.6** | **Offerta** con un'eccezione in attesa | «Emetti» e «Accetta» spenti col motivo | — |
| **2.7** | **Ordine** in bozza con un componente BoM rifiutato | «Conferma» spento col motivo | — |
| **2.8** | **DDT** di vendita con un componente in attesa; poi cambia la causale in una che **non vende** | Con la causale che vende «Emetti» è spento; con quella che non vende è **acceso** | — |
| **2.9** | **Revisione** — preventivo e offerta EMESSI con un prezzo in attesa | «Crea revisione» spento col motivo; con un prezzo **solo rifiutato** resta acceso. ⚠️ Stesso limite del 2.2: il caso si costruisce solo a DB, lo coprono i pgTAP 39-44 dello stesso file | — |
| **2.10** | **Lotto** — dal kebab di lista, un'azione spenta | L'avviso mostra **il suo motivo**, non «azione non più disponibile» | — |
| **2.11** | 🔴 Forza la mano: dal preventivo in bozza con una riga in attesa, prova a emettere per un'altra strada (chiamata API diretta al cambio stato) | Rifiuto **409** con «Non si può procedere: ci sono prezzi ancora in attesa di approvazione (1).» | Se passa, il guard a DB non morde: fermati e segnala |

---

## 3. 🔴 I punti già noti, da confermare a video

| | Cosa | Dove sta scritto |
| --- | --- | --- |
| **Banner** | Il banner dei prezzi del preventivo è **ritirato**, non copiato sugli altri documenti: il perché di un pulsante spento ha un canale solo, il tooltip. Il **tag di stato sulla riga** resta | brief congelamento, §6.2 |
| **Revisione** | Un prezzo **rifiutato** si ricopia sulla revisione e la blocca finché non si corregge: voluto (D-1) | brief congelamento, §10 |
| **CI** | La riga `test-preventivi-approvazione-prezzo.sql` in `db/pgtap/baseline-rossi-ci.tsv` si toglie (team DB, `scripts/pgtap-baseline-ci-rientrati.sh`) dopo la corsa CI su `Tito-dev`. Non tocca il collaudo | brief congelamento, testata |

---

## 4. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-24** | ✏️ Stesura, alla chiusura dei due brief (archiviati in `work-done/` lo stesso giorno). Tutto a codice, **niente visto a video** |
