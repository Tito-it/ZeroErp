## 📘 Documentazione Concettuale – Funzione `dbops.fn_sorgenti_orfane`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di sorgente, con il bersaglio e la chiave di ciascuno
>
> Approfondimento viste:
>
> * [dbops.vw_sorgenti_orfane](/dbzero/dbops/views/vw_sorgenti_orfane) — la vista che la espone, iscritta fra i presidi
>
> Approfondimento funzioni:
>
> * [dbops.fn_sorgenti_orfane_perimetro](/dbzero/dbops/funzioni/fn_sorgenti_orfane_perimetro) — le tabelle che esamina
> * [script.trgfn_guard_sorgente_polimorfa_tipizzata](/dbzero/script/funzioni/trgfn_guard_sorgente_polimorfa_tipizzata) — il guard che impedisce di inserire un orfano
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello del collegamento tipo + chiave

---

### 🎯 Scopo Principale

Trova le righe la cui **sorgente** punta a un record che non esiste più: per ogni tabella del
perimetro e per ogni tipo di sorgente presente, cerca nel bersaglio dichiarato a catalogo la chiave
che la riga porta, e restituisce le righe che non la trovano. È il calcolo dietro
`dbops.vw_sorgenti_orfane`.

---

### ⭐ Perché serve, se c'è il guard

Il collegamento fra una riga e la sua sorgente è un tipo a catalogo più una chiave, e il bersaglio
cambia con il tipo: non è una chiave esterna e non può esserlo. Il guard tipizzato impedisce di
**inserire** una riga che punta a un bersaglio inesistente; nessuno però impedisce di **cancellare**
il bersaglio dopo. Questa funzione trova gli orfani nati così.

---

### Come confronta

* Il bersaglio e la chiave li dice il catalogo: `config.sorgenti.target_table` e `key_selector`.
  Con chiave `uid` si confronta l'identificativo universale della riga, altrimenti l'identificativo
  numerico. La scelta si fa per tipo, perché un bersaglio può non avere l'identificativo universale.
* Il confronto è su testo: nel perimetro convivono chiavi universali tipizzate e chiavi universali
  scritte come testo.
* I tipi di sorgente senza bersaglio dichiarato non si esaminano.
* I nomi di tabelle e colonne vengono dal catalogo di PostgreSQL e dal perimetro, mai da un input.

---

### ⚠️ Gira coi privilegi del proprietario

È `SECURITY DEFINER` del proprietario degli schemi, con il `search_path` fissato, e legge soltanto.
Il motivo è la row level security: un orfano in una tabella protetta va visto comunque, anche da chi
non ne vedrebbe la riga.

---

### ⚠️ La forma del ciclo interno

Il ciclo che legge «quali tipi di sorgente ci sono in questa tabella» è una query dinamica, e il suo
bersaglio sono tre variabili tipizzate sulle colonne di `config.sorgenti`, non un record. Un record
riempito da una query dinamica ha una forma che il controllo statico delle funzioni non conosce, e il
presidio dei riferimenti morti lo segnalava come difetto reale. La regola vale per ogni ciclo su una
query dinamica del progetto: chi tocca questa funzione tiene la forma.

---

### Test

* `db/pgtap/dbops/test-sorgenti-orfane-v1.sql` — zero orfani sul mondo costruito, poi un bersaglio
  cancellato produce esattamente una riga.
* `db/pgtap/magazzino/test-porta-ledger-v1.sql`, test 10 — la funzione è `SECURITY DEFINER` con il
  `search_path` fissato.

---

### Note di migrazione

* 2026-09-18 — nasce con il secondo lotto del magazzino (`brief-db-magazzino-lotto-2-motore`). Lo
  stesso giorno il ciclo interno passa dal record ai tre scalari tipizzati, dopo il rosso del presidio
  dei riferimenti morti; firma e comportamento invariati.

---

{% include-markdown "signature-core.md" %}
