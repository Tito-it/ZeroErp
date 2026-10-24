# Brief DB — La bolla consegnata e il reso confermato nei pgTAP: una strada, non trenta copie

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: Tid**, con il via allo sviluppo del giro 1 (la bolla). Il brief è aperto e la ricognizione è
fatta; le scelte di forma sono proposte nel §4 (nessuna è una revoca).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il problema, la ricognizione dei file, la proposta | §1-§4 | — |
| 2 | **Tid** | Via allo sviluppo (e, se vuole, le scelte del §4) | §4 | 1 |
| 3 | team DB | Giro 1: il builder della bolla consegnata da un ordine, e i file che la ricopiano | §5 | 2 |
| 4 | **Tid** | Apply del giro 1 e corsa pgTAP come app | — | 3 |
| 5 | team DB | Giro 2: il builder del reso confermato su una bolla, e i file che lo ricopiano | §5 | 4 |
| 6 | **Tid** | Apply del giro 2, corsa pgTAP come app; archiviazione | — | 5 |

Decisioni aperte di Tid: il via (le scelte del §4 hanno un default proposto). Lavoro da committare: questo
documento.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid; poi il team DB.
> **Origine:** [brief-modello-documento-vendita](brief-modello-documento-vendita.md) §4-octies (proposta),
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
| 2 | builder del reso confermato, presidio, porting dei ~20 file | come sopra |

Aperto il 2026-10-25. Nessun lavoro scritto: si parte col via di Tid.
