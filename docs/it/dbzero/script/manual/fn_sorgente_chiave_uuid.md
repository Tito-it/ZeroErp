## 📘 Documentazione Concettuale – Funzione `script.fn_sorgente_chiave_uuid`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — `key_selector`, che dice con quale chiave si riconosce un tipo di documento
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — la colonna `sorgente_chiave_uuid`, su cui si cerca con la chiave convertita
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id) — la gemella, per le chiavi intere
> * [script.fn_sorgente_documento_da_chiave](/dbzero/script/funzioni/fn_sorgente_documento_da_chiave) — il ponte per le chiavi in testo, che la usa per riconoscerle
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che scrive, che la usa sulla chiave che riceve
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico
> * [dbops.fn_sorgenti_orfane](/dbzero/dbops/funzioni/fn_sorgenti_orfane) — il presidio degli orfani, per le tabelle testuali
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza, e le chiavi in testo

---

### 🎯 Scopo Principale

Il lettore della **forma canonica** di una chiave di documento scritta come testo, per i tipi
riconosciuti dall'**uid**: riporta il testo al suo tipo uuid, se è scritto esattamente come lo scrive
il database, e altrimenti risponde vuoto.

---

### Dove esistono chiavi in testo

Le tabelle che dicono «nasce da» scrivono la chiave nelle colonne tipizzate, `sorgente_id` e
`sorgente_uid`. Esistono però chiavi che sono **testo per costruzione**: i nodi della lineage, la
chiave di un gruppo fatturabile, la chiave che il backend passa ai verbi del push, la chiave che
riceve il BB che scrive. Questa funzione e la gemella `script.fn_sorgente_chiave_id` sono l'unico
posto in cui si decide se quel testo è una chiave, e di quale specie. Le leggono il ponte
`script.fn_sorgente_documento_da_chiave`, il BB che scrive, il guard unico, il presidio degli orfani
per le tabelle testuali, la lineage e il riferimento del gruppo fatturabile.

---

### La forma canonica, e nient'altro

| Testo in ingresso | Risultato |
| --- | --- |
| un uuid scritto come lo scrive il database (minuscolo, con i trattini) | l'uuid |
| un uuid in un'altra forma (maiuscolo, senza trattini, tra graffe) | vuoto |
| un numero, o qualunque altra cosa | vuoto |
| vuoto | vuoto |

Non solleva mai errori: «vuoto» vuol dire solo «questa chiave non è un uuid canonico». Decide il
chiamante: il ponte non risolve il documento, il BB che scrive risponde `E_SORG_FORMATO`.

⚠️ Le forme non canoniche danno vuoto **di proposito**. La conversione del database le
accetterebbe, ma un confronto sul testo non le troverebbe: le due strade per cercare la stessa
chiave devono dare lo stesso risultato.

---

### ⭐ Si converte il parametro, non la colonna

Sotto la sicurezza per riga un confronto fatto sulla forma testuale di un uuid non arriva
all'indice, perché la conversione in testo non è dichiarata sicura, e il database rilegge tutte le
righe. Convertita la chiave cercata nel suo tipo, il confronto avviene sulla colonna nativa e usa
l'indice.

⚠️ È scritta in PL/pgSQL e non in SQL di proposito: una funzione SQL si espande nella query, e con un
argomento costante la conversione verrebbe valutata prima del controllo di validità, sollevando un
errore invece di rispondere vuoto.

---

### Test

* `db/pgtap/script/test-sorgente-documento-e-chiave-v1.sql` — il ponte per chiave testuale (uid e
  id in testo si risolvono, una chiave non canonica no) e il BB che scrive (un uuid con le maiuscole
  riceve `E_SORG_FORMATO`).

---

### Note di migrazione

* 2026-10-05 — nasce con la gemella, per cercare la chiave testuale delle provenienze delle pratiche
  sulla colonna nativa della vista dello stato.
* 2026-11-08 — con il cantiere della provenienza documento e riga (`brief-db-sorgente-documento-e-riga`)
  le tabelle passano alle colonne tipizzate, e le due funzioni restano come lettore della forma
  canonica delle chiavi che sono testo per costruzione. Il guard «modello B», che le usava sulle
  chiavi in testo delle tabelle, è ritirato.

---

{% include-markdown "signature-core.md" %}
