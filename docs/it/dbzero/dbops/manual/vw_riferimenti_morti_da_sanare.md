## 📘 Documentazione Concettuale – Vista `dbops.vw_riferimenti_morti_da_sanare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni) — il registro del debito che si sottrae
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — la riga di catalogo del presidio
>
> Approfondimento viste:
>
> * [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) — la gemella, dal verso del registro
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — la misura
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — misura e registro

---

### 🎯 Scopo Principale

La lista di lavoro dei riferimenti morti: i difetti `REALE` e `ORFANA`, e le funzioni che non si
sono potute controllare (`NON_MISURATO`), non coperti dal registro del debito. Deve essere vuota.

È la differenza fra due insiemi: i difetti che la misura trova, meno le esenzioni registrate.

---

### Che cosa filtra, e perché così

**Sulle classi.** Entrano `REALE`, `ORFANA` e `NON_MISURATO`. Le classi `FP_*` sono falsi positivi
già giudicati e restano fuori — ma restano visibili interrogando la funzione, che le restituisce
tutte.

⛔ **`NON_MISURATO` entra di proposito.** Una funzione che `plpgsql_check` non ha potuto
controllare non è un riferimento morto e non si registra come debito: si ripara lo strumento. Ma
toglierla dalla lista farebbe tornare la vista **vuota** proprio quando nessuno ha potuto
guardare, cioè direbbe «nessun riferimento morto» nel momento peggiore. Resta lavoro, e resta
visibile.

**Sulle esenzioni.** Si confrontano schema, funzione e l'esito con il pattern della voce di
registro: per pattern e non per uguaglianza, perché il messaggio contiene numeri di riga che
cambiano a ogni ritocco della funzione.

---

### ⚠️ Una lista vuota ha due cause

Vuota può voler dire «nessun difetto» oppure «tutti i difetti sono stati esentati», e questa vista
da sola non le separa. Per questo il presidio ha due viste: la gemella
[vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) guarda il
registro dal verso opposto. Devono essere vuote **insieme**.

---

### ⚠️ Costa quanto la misura

Ogni lettura fa girare `plpgsql_check` su tutte le funzioni del database. Per questo la sua riga di
catalogo ha cadenza settimanale e non giornaliera: il costo di lettura è un attributo del presidio,
non del digest. Comporla con la gemella in una query sola è corretto, ma esegue il controllo due
volte.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`, e la misura sotto vede solo ciò che il chiamante può compilare: un
ruolo che non possiede gli oggetti ispezionati legge meno di quel che c'è. Per questo nel catalogo
il suo perimetro è `DEFINER`: il digest la conta da
[dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio), come proprietario, e riporta il
numero, non le righe.

---

### Test

* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — nessun difetto fuori dal registro, nessuna
  funzione non misurata, e il conteggio che legge il digest concorda con la misura diretta.

---

### Note di migrazione

* 2026-08-04 — nasce con `brief-db-bonifica-riferimenti-morti` §5, sulle sole classi `REALE` e
  `ORFANA`.
* 2026-09-10 — entra `NON_MISURATO`: quelle righe prima uscivano come falsi `REALE`, e toglierle
  senza rimetterle da un'altra porta avrebbe fatto tornare la vista vuota mentre lo strumento era
  rotto. Lo stesso giorno la riga di catalogo passa a perimetro `DEFINER`.

---

{% include-markdown "signature-core.md" %}
