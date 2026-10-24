# Brief DB — La bolla consegnata e il reso confermato nei pgTAP: una strada, non trenta copie

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: nessuno — brief chiuso e archiviato il 2026-10-25.** Il giro 1 (la bolla consegnata) è fatto,
applicato e verde come app; il giro 2 (il reso confermato, con la bolla di ri-consegna) prosegue in
[brief-db-pgtap-reso-costruito](../work-in-progress/brief-db-pgtap-reso-costruito.md).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il problema, la ricognizione dei file, la proposta | §1-§4 | — |
| 2 | ✅ Tid | Via allo sviluppo, coi default del §4 (2026-10-25) | §4 | 1 |
| 3 | ✅ team DB | Giro 1: builder della bolla, presidio, porting di 36 file, regressione prima/dopo senza differenze | §6 | 2 |
| 4 | ✅ Tid | Decisioni D-1…D-3: come da proposte (2026-10-25) | §6.5 | 3 |
| 5 | ✅ team DB | D-1 (`-03`, `-04`) e i due debiti del §6.4, con la loro prova | §6.7 | 4 |
| 6 | ✅ Tid | Apply di `-01`…`-04`, corsa pgTAP come app: verde, nessuna regressione (2026-10-25) | §7 | 5 |
| 7 | ✅ team DB | Archiviazione; il giro 2 passa a un brief suo | §7 | 6 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: i quattro changeSet `20261025-01`…`-04`, i due
presidi, i 38 pgTAP toccati, le pagine manuali dei due builder, la guida pgTAP, questo documento archiviato e il
brief nuovo del giro 2.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid; poi il team DB.
> **Origine:** [brief-modello-documento-vendita](../work-in-progress/brief-modello-documento-vendita.md) §4-octies (proposta),
> decisa da Tid il 2026-10-25: «facciamolo, apri un brief specifico».
> **Perimetro:** solo DB — i pgTAP (`db/pgtap/`) e i builder di fixture (`dbops`). Nessuna ricaduta su
> backend o frontend, nessun cambio al modello del dominio.
> **Brief vicini verificati:** nessuno aperto sul tema. Chiusi, di cui questo è il seguito:
> [brief-db-fixture-che-costruiscono-giro-2](../work-done/brief-db-fixture-che-costruiscono-giro-2.md),
> [brief-db-fixture-che-costruiscono-d7-d6-d4](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md),
> [brief-db-fixture-rls-documenti-costruiti](../work-done/brief-db-fixture-rls-documenti-costruiti.md)
> (la famiglia dei builder `dbops.fn_pgtap_crea_*`). Il builder esistente
> `dbops.fn_pgtap_crea_ddt` (una bolla **in bozza**, per il magazzino) resta suo: quello nuovo ci si
> appoggia, non lo sostituisce.

---

## 1. Il problema, in parole semplici

### 1.1 La bolla consegnata

Molti test hanno bisogno di una **bolla già consegnata, nata da un ordine**: è il punto di partenza di
tutto ciò che viene dopo la consegna (il reso, l'accredito, la situazione della merce, la fatturazione
delle bolle). Per averla ogni test ripete a mano la stessa strada:

1. crea l'ordine e gli scrive una riga;
2. lo porta a **confermato**;
3. genera la bolla dall'ordine (`vendite.fn_genera_ddt_da_ordine`, la funzione del dominio);
4. le scrive ciò che la consegna pretende (indirizzo di consegna, causale di trasporto);
5. la porta a **consegnata**.

Sono cinque passi in un ordine obbligato, e ognuno ha i suoi controlli: salta un passo, o fanne uno nel
punto sbagliato, e il database ferma il test. **Ogni file li riscrive per conto suo.** Quando una regola
cambia — la bolla pretende un dato in più, la conferma dell'ordine un controllo nuovo — si correggono
tutti i file uno per uno. È ciò che è successo il 2026-10-24 con la nascita in bozza: decine di pgTAP da
portare, perché ognuno scriveva da sé la strada che la regola aveva cambiato.

### 1.2 Il reso confermato

Sopra la bolla consegnata molti test costruiscono un **reso confermato**: la merce che torna indietro. Lo
scrivono a mano:

1. la testata del reso, legata alla bolla;
2. la riga del reso, legata alla riga della bolla;
3. la conferma (`vendite.fn_conferma_reso`, il verbo del dominio).

Il reso ha regole sue — la riga deve corrispondere a merce davvero consegnata, la quantità non può
superarla, la conferma pretende i suoi dati — e ogni file le soddisfa a mano. Stesso problema della
bolla: la regola è una, le copie sono tante, e restano indietro in silenzio quando la regola cambia.

⚠️ Del reso il database ha il **verbo di conferma** ma non una madre di creazione: la testata e le righe in
produzione le scrive il backend (`resi_service`). Il builder quindi le scrive coi suoi INSERT, come fanno
oggi i test, e passa dal verbo vero per la conferma.

### 1.3 Perché un builder, e non «un'altra comodità»

Il criterio dei builder di questo progetto (brief-db-fixture-che-costruiscono-giro-2 §7): **entra ciò che
ha una trappola d'ordine, non ciò che serve spesso.** Qui la trappola c'è, ed è doppia: l'ordine dei passi
e le condizioni che ogni passo pretende. Spostarli in un builder li scrive **una volta**, per le strade
vere del dominio; i test chiedono «una bolla consegnata» e si occupano del loro caso.

---

## 2. La ricognizione (fatto datato, 2026-10-25, sul repo)

> I numeri descrivono le copie da ritirare, **non** decidono che il lavoro va fatto (Regola zero): il
> motivo è il §1.3, e varrebbe anche per due file.

**La bolla.** 39 pgTAP chiamano `vendite.fn_genera_ddt_da_ordine`. In **27** la bolla viene portata a
consegnata: è la strada del §1.1, ripetuta. Negli altri 12 la generazione è usata o provata in sé
(per esempio `vendite/test-fn-genera-ddt-da-ordine-v1`, che prova proprio la generazione, o i test delle
azioni disponibili su un ordine): quelli restano come sono, il loro caso è la strada stessa.

**Il reso.** 30 pgTAP scrivono una testata di reso con un INSERT. In circa **20** il reso nasce su una
bolla generata da un ordine, prende le sue righe e viene confermato: la strada del §1.2. Gli altri provano
il reso in sé (le sue regole, la numerazione, il carico a magazzino, i reso senza ordine) e vanno guardati
uno per uno.

Il censimento fine — quale blocco di ogni file è una copia e quale è il caso — è il primo passo di ogni
giro (§5), file per file, come nei giri del brief del modello del documento.

---

## 3. Che cosa NON cambia

* Il modello del dominio: nessun guard, nessun verbo, nessuna tabella. Il lavoro è nei test e in `dbops`.
* I test in cui la strada è il caso provato (la generazione della bolla, la conferma del reso, i loro
  errori): restano scritti a mano.
* Le asserzioni: si cambia la fixture, non ciò che il test prova. Un'attesa che dipendeva da un valore
  scritto a mano si riscrive sul valore costruito, dichiarata nel file.

---

## 4. La proposta (con i default; Tid può cambiarli)

### 4.1 Il builder della bolla consegnata

`dbops.fn_pgtap_crea_ddt_da_ordine(etichetta, stato, billing_account_id, …)`:

* l'**ordine** dal builder esistente `dbops.fn_pgtap_crea_ordine`, con una riga di un articolo costruito
  (merce), portato a confermato per la matrice;
* la **bolla** dalla madre `vendite.fn_genera_ddt_da_ordine`, con indirizzo e causale che la consegna
  pretende;
* lo **stato** chiesto (default: consegnata) per i passaggi veri della bolla (`vendite.fn_cambia_stato_ddt`
  o `dbops.fn_pgtap_porta_a_stato`, quello che la matrice della bolla ammette);
* ritorna le chiavi: ordine, sua riga, bolla, sua riga, articolo, quantità.

Default proposti (da confermare o cambiare): **una** riga (chi ne vuole di più le aggiunge in bozza, o il
builder prende una quantità); il cliente del test col terzo parametro, come gli altri builder (niente
cliente in più: `dbops.fn_pgtap_cliente_del_builder`).

### 4.2 Il builder del reso confermato

`dbops.fn_pgtap_crea_reso(etichetta, ddt_id, quantità, stato, …)`:

* sopra una bolla consegnata (quella del §4.1, o una che il test passa);
* testata e riga col collegamento alla riga della bolla, la quantità chiesta (default: una parte del
  consegnato, così il residuo resta misurabile);
* la conferma dal verbo `vendite.fn_conferma_reso` se lo stato chiesto lo vuole (default: confermato).

### 4.3 Il modo

Un builder per giro, **con tutte le sue copie ritirate nello stesso giro** (regola del 2). Prima la bolla,
perché il reso ci si appoggia. Ogni giro: censimento fine, il builder col suo presidio, il porting dei
file, la regressione prima/dopo sullo scratch, poi l'apply e la corsa come app di Tid.

---

## 5. I giri

| Giro | Che cosa | Fatto quando |
| --- | --- | --- |
| 1 | builder della bolla consegnata, presidio, porting dei ~27 file | i file ricopiano la strada solo dove è il caso; regressione senza differenze; corsa come app verde |
| 2 | builder del reso confermato, presidio, porting dei ~20 file | spostato in [brief-db-pgtap-reso-costruito](../work-in-progress/brief-db-pgtap-reso-costruito.md) (§7) |

Aperto il 2026-10-25; via di Tid lo stesso giorno («bisogna farlo»), coi default del §4.

---

## 6. Giro 1 — la bolla consegnata (fatto, 2026-10-25)

### 6.1 Il builder

* `20261025-01` — `dbops.fn_pgtap_crea_ddt_da_ordine(etichetta, stato DEFAULT 'CONSEGNATO', billing_account_id,
  p_quantita, p_prezzo, p_articolo_id, p_fatturazione_trigger, p_ordine_id, p_qta_da_evadere, p_righe, p_data,
  p_causale_codice DEFAULT 'VENDITA')`. L'ordine da `dbops.fn_pgtap_crea_ordine` con una riga (10 a 25, salvo
  parametri), trigger di fatturazione scritto in bozza, conferma per la matrice; la bolla dalla madre; causale e
  indirizzi obbligatori mancanti (come `dbops.fn_pgtap_crea_ddt`); lo stato per la matrice. Rispetto al §4.1 ha in
  più due strade che il censimento ha mostrato: **`p_ordine_id`** (la bolla da un ordine che il test ha costruito
  da sé: più righe, kit, date di consegna) e **`p_qta_da_evadere`/`p_righe`** (più spedizioni dalla stessa riga).
  La bolla da lavorare in bozza (riga a mano, legame in più, prezzo tolto) si chiede `DRAFT` e si porta avanti con
  `dbops.fn_pgtap_porta_a_stato`.
* `20261025-02` — uno stato **abortito** (`is_abortito`, cioè `ANNULLATO`) si rifiuta prima di costruire. Il
  `-01` lo accettava e moriva in fondo su `E_DOC_ANNULLO_CON_LEGAMI`: la bolla da ordine ha i legami, e l'annullo
  li dichiara il verbo `vendite.fn_annulla_ddt` (caso del test). L'ha trovato il porting (gruppo A).
* Presidio `db/pgtap/dbops/test-fn-pgtap-crea-ddt-da-ordine-v1.sql`, 13 casi; senza il `-02` il 13 è rosso.
* Doc: pagina manuale `dbzero/dbops/manual/fn_pgtap_crea_ddt_da_ordine.md`, riga nella tabella dei builder della
  guida pgTAP.

### 6.2 Il porting

36 file portati, 4 lasciati perché la strada è il loro caso; nessuna attesa e nessun `plan` cambiati.

| Lasciato com'è | Perché |
| --- | --- |
| `vendite/test-fn-genera-ddt-da-ordine-v1` | prova la generazione |
| `vendite/test-ddt-da-ordine-emittente-prima-dei-lettori-v1` | prova il giro generazione → emissione dal verbo |
| `vendite/test-righe-natura-vendita-congelata-v1` | il passaggio ordine → bolla è il caso del test 12 |
| `script/test-available-actions-requires-righe-v1` | nomina la generazione solo in un commento (ma vedi §6.4) |

Resta scritto a mano, dentro i file portati, ciò che è il caso: gli ordini speciali (più righe, sconto, date di
consegna, data a -40 nel ritardo), le righe e i legami scritti sulla bolla in bozza, le emissioni che sono
l'asserzione, gli annulli dal verbo, la bolla di ri-consegna (`fn_genera_ddt_riconsegna`) e **tutti i resi**
(giro 2).

### 6.3 La prova (fatto datato, 2026-10-25, scratch `zeroerp_ruoli` come owner)

* I 40 file del censimento, prima e dopo, in sequenza, col changeSet in testa: **stesso piano, stessi `ok`, stessi
  `not ok` in tutti i 40**, testo delle righe TAP identico. I sei `not ok` di partenza sono i test di scope (rossi
  da owner, verdi come app) e restano gli stessi.
* Presidi trasversali col changeSet: `dbops/test-riferimenti-morti-v1` (plpgsql_check) verde, e i presidi che
  leggono le funzioni di `dbops` verdi o col rosso preesistente identico
  (`vendite/test-registri-fatturazione-scadenza-alla-nascita`, uguale senza il changeSet).
* Guardrail dei changeSet verdi. Non provato: la corsa come app (passo 4).

### 6.4 Debiti emersi (chiusi nel §6.7)

* `script/test-available-actions-requires-righe-v1`: i test 8-12 pescano dal database una bolla in bozza vuota e
  una piena (`LIMIT 1` senza ordine) e su un database ricostruito passano in `skip`: **verde per sottrazione**, 5 su
  15. La bolla piena si costruisce col builder in `DRAFT`, quella vuota con `dbops.fn_pgtap_crea_ddt`.
* `dbops/test-automazioni-guasto-ambiente-rilanciato-v1` viola il guardrail del preambolo (manca
  `SET CONSTRAINTS ALL IMMEDIATE` e il contesto): file non toccato da questo brief, già così nel commit.

### 6.5 Decisioni di Tid (2026-10-25: «d-1 d2 d3 ok come da proposte, risolvere i debiti»)

* **D-1 — la data dell'ordine.** Il builder fa l'ordine alla data operativa, mentre `p_data` può dare alla bolla
  una data precedente (oggi la madre lo accetta). Nessuna asserzione la misura, ma una bolla più vecchia del suo
  ordine è una fixture incoerente col modello. Proposta: `p_data_ordine` in coda (scritta in bozza, prima della
  conferma), e i file che fissavano la data la passano.
* **D-2 — altri parametri segnalati dal porting.** Lo sconto della riga d'ordine (un file), la causale omessa in
  bozza (un file), l'indirizzo con l'origine dal cliente (un file). Proposta: **no** — un file solo non fa una
  copia (regola del 2); restano scritti dove servono.
* **D-3 — la bolla di ri-consegna.** Dopo `vendite.fn_genera_ddt_riconsegna` quattro file scrivono a mano
  indirizzo CON e causale e portano a consegnata: la stessa trappola d'ordine della bolla. Proposta: nel giro 2,
  insieme al reso (il builder del reso con la ri-consegna a richiesta, o un builder suo).

### 6.6 Per il giro 2: la strada del reso come la scrivono i file (fatto datato)

* Testata `vendite.resi` (stato DRAFT, sorgente `DDT_VENDITA`, `sorgente_uid` = uid della bolla); emittente e
  cliente dal normalize.
* Righe `vendite.resi_righe` (riga della bolla, `ordine_riga_id` dal legame — in sei file con `LIMIT 1` senza
  ordine —, articolo/descrizione/uom/fattore copiati dalla riga della bolla, quantità, tipo reso
  `RESO_A_CREDITO` o `RESO_PER_RICONSEGNA`).
* Conferma da `vendite.fn_conferma_reso`, con l'azione `conferma_reso` concessa prima.
* Forme che il builder deve coprire: tipo per codice, più righe (riga della bolla e quantità), stato finale DRAFT
  o CONFERMATO, più resi sulla stessa riga. Casi che restano del test: la riga spenta in bozza, il reso annullato,
  il legame `resi_righe_riconsegne`.

### 6.7 D-1 e i debiti (fatto, 2026-10-25)

* `20261025-03` — `dbops.fn_pgtap_crea_ordine` prende `p_data` in coda e la scrive **nell'INSERT** (fuori bozza
  la data è congelata; un UPDATE dopo il builder dipenderebbe dall'ordine della fixture). NULL = il default
  della colonna, con due rami come `fn_pgtap_crea_articolo`. DROP + CREATE: le chiamate a tre argomenti restano
  valide. Presidio `dbops/test-fn-pgtap-crea-ordine-v1`: firma a quattro e caso 11.
* `20261025-04` — `dbops.fn_pgtap_crea_ddt_da_ordine` prende `p_data_ordine` in coda e la passa al builder
  dell'ordine; con `p_ordine_id` solleva (la data è dell'ordine del test). DROP + CREATE. Presidio: firma, casi
  14 e 15.
* I tre file delle chiusure (`vendite/test-fn-partite-merce-chiusura-v1`, `test-fn-resi-da-accreditare-chiusura-v1`,
  `test-fn-situazione-merce-ordine-chiusura-v1`) passano `p_data_ordine => DATE '2026-08-05'`, la data che i loro
  ordini avevano prima del giro 1, a ogni chiamata che costruisce l'ordine (11 chiamate). Le bolle con
  `p_ordine_id` stanno su ordini del test, già datati. Gli altri file non danno date passate alle bolle.
* Debito `script/test-available-actions-requires-righe-v1`: il mondo si costruisce (prima il contesto si apriva
  su un operatore pescato), la bolla vuota da `dbops.fn_pgtap_crea_ddt`, quella con la riga dal builder in
  `DRAFT`; i rami `skip` sono tolti, i 15 test girano tutti. Il test 10 ora discrimina sul messaggio («senza righe
  attive»): la bolla vuota ha causale e indirizzi, quindi l'unico rifiuto atteso è quello delle righe.
* Debito `dbops/test-automazioni-guasto-ambiente-rilanciato-v1`: il preambolo dichiara il contesto escluso (il
  file legge solo il catalogo e una funzione pura) e richiude i vincoli differiti. Guardrail del preambolo
  verde su tutti i file.
* Prova (fatto datato, 2026-10-25, scratch come owner, in sequenza): i 40 file del censimento col `-03`/`-04` in
  testa danno **gli stessi esiti della partenza**; i due presidi sono verdi col changeSet e rossi senza (vedono
  la modifica); i 10 chiamanti di `fn_pgtap_crea_ordine`, `dbops/test-riferimenti-morti-v1` e il file del
  preambolo uguali con e senza. Non provato: la corsa come app.

---

## 7. Esito e archiviazione (2026-10-25)

* **Apply e corsa di Tid**: «migrazione applicata, test verdi, nessuna regressione» — `20261025-01`…`-04` su
  dbdev e scratch, corsa pgTAP come app.
* **Consegnato**: il builder `dbops.fn_pgtap_crea_ddt_da_ordine` (bolla da ordine, stato per la matrice, più
  spedizioni, data dell'ordine), `dbops.fn_pgtap_crea_ordine` con la data alla nascita, i due presidi, 36 pgTAP che
  non ricopiano più la strada della bolla, i due debiti del §6.4 chiusi; doc: due pagine manuali e la guida pgTAP.
* **Il giro 2 non è un residuo di questo lavoro ma il suo seguito**, deciso con lo stesso via: il builder del reso
  confermato e la bolla di ri-consegna (D-3). Tid ha chiesto di chiudere questo brief: il giro 2 vive in
  [brief-db-pgtap-reso-costruito](../work-in-progress/brief-db-pgtap-reso-costruito.md), che eredita il §1.2, il §4.2
  e il materiale del §6.6. Il titolo di questo documento resta quello di apertura: i pgTAP portati lo citano per
  nome.
