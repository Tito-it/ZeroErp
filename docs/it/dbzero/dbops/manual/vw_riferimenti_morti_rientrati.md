## 📘 Documentazione Concettuale – Vista `dbops.vw_riferimenti_morti_rientrati`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — il registro che la vista rilegge
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — la riga di catalogo del presidio
>
> Approfondimento viste:
>
> * [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) — la gemella, dal verso dei difetti
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — la misura
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — perché un registro ha due versi

---

### 🎯 Scopo Principale

Le voci del registro del debito sui riferimenti morti che non corrispondono più a nessun difetto:
righe da togliere. È ciò che impedisce al registro di diventare un elenco di eccezioni permanenti.

---

### ⚠️ Perché senza questa vista il presidio si degrada da solo

Un registro di esenzioni tende a riempirsi e a non svuotarsi: ogni difetto giudicato accettabile
aggiunge una riga, e quando il difetto si sana nessuno torna a togliere l'esenzione, perché niente
lo segnala. Dopo un po' il guardrail è verde e non presidia quasi nulla. Questa vista rende visibile
l'esenzione diventata inutile: è la ragione per cui il registro si può chiamare «debito».

---

### Come funziona

Per ogni voce del registro la vista pone due domande alla misura:

1. trova ancora un difetto `REALE` o `ORFANA` con lo stesso schema, la stessa funzione e un esito
   che corrisponde al pattern?
2. la funzione della voce è uscita `NON_MISURATO`, cioè `plpgsql_check` non l'ha potuta controllare?

La voce è rientrata solo se la risposta è **no a entrambe**. Espone anche il motivo e la data di
registrazione, così chi la toglie vede perché era stata messa e da quanto.

La misura si legge **una volta sola** per interrogazione: compila centinaia di funzioni, e le due
domande la chiederebbero due volte.

---

### ⛔ Una funzione non misurata non è «rientrata»

Se lo strumento non ha potuto misurare la funzione esentata (`NON_MISURATO`), di quella funzione non
si sa niente: né che il difetto c'è ancora, né che è sparito. Dare la voce per rientrata vorrebbe
dire svuotare il registro proprio quando lo strumento si rompe. Per questo la vista la tiene fuori,
e resta in silenzio.

⇒ Il rosso della misura mancata non sta qui: lo danno
[vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare), che elenca le
funzioni `NON_MISURATO`, e il guardrail della CI, che si ferma per primo su quella classe. Le due
viste vanno lette insieme.

⚠️ Una funzione che **non esiste più** non compare nella misura, né come difetto né come
`NON_MISURATO`: la sua voce esce rientrata, ed è giusto, perché non copre più niente.

---

### ⚠️ Una riga qui non è sempre «difetto sanato»

La funzione può essere stata **rinominata o eliminata**, o il messaggio di `plpgsql_check` può
essere cambiato (un aggiornamento dell'estensione, un ritocco che sposta il testo): il pattern non
aggancia più. Prima di togliere una voce si controlla che il difetto sia davvero sparito.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`, e la misura sotto vede solo ciò che il chiamante può compilare: da un
ruolo che non possiede gli oggetti ispezionati la risposta cambia. Nel catalogo il suo perimetro è
`DEFINER`: il digest la conta come proprietario e riporta il numero, non le righe. Costa quanto la
gemella: fa girare `plpgsql_check` su tutto il database.

---

### Test

* `db/pgtap/dbops/test-riferimenti-morti-v1.sql`:
  * nessuna voce rientrata nel registro, dallo stesso ruolo da cui si misura;
  * test 9-11 — la vista viva su una misura **costruita**: il testo della vista, con la chiamata
    alla misura sostituita da una funzione temporanea con le stesse colonne (il 9 prova che la
    sostituzione avviene). Il 10 prova che una voce su una funzione `NON_MISURATO` non è rientrata;
    l'11 che una voce ancora coperta da un difetto non è rientrata, e una su una funzione che la
    misura non vede più sì. La misura è costruita perché il caso vero non si riproduce in un test:
    `plpgsql_check` riferisce qualunque funzione costruibile, e solleva solo per l'ambiente
    (estensione irraggiungibile, lock).

---

### Note di migrazione

* 2026-08-04 — nasce con `brief-db-bonifica-riferimenti-morti` §5, insieme alla gemella.
* 2026-09-10 — la riga di catalogo passa a perimetro `DEFINER`: letta da un ruolo che non possiede
  gli oggetti ispezionati, la vista rispondeva in modo diverso dal proprietario.
* 2026-09-14 — il primo digest settimanale dà rientrata la voce legata a pgAgent: era il ruolo che
  misurava, non la funzione. Da lì una classe nuova nella misura e una voce che segue la macchina.
* 2026-11-04 — D7 di `brief-db-revisione-dbops`: una voce la cui funzione esce `NON_MISURATO` non è
  più rientrata (prima il registro si svuotava proprio quando lo strumento si rompeva); la misura si
  legge una volta sola.

---

{% include-markdown "signature-core.md" %}
