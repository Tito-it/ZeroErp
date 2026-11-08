## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_giornale_ins`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la sospensione che si registra
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — il giornale della pratica
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_giornale_riattivazione](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_riattivazione) — l'evento gemello alla chiusura della sospensione
> * [pratiche.trgfn_sospensioni_propaga](/dbzero/pratiche/funzioni/trgfn_sospensioni_propaga) — porta a `SOSPESO` i flussi attivi
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — valorizza la transazione della sospensione prima di questo trigger

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_giornale_ins` scrive nel giornale della pratica
l'evento `SOSPENSIONE_REGISTRATA` ogni volta che nasce una sospensione.

È audit di dominio, non tecnico: `pratiche.giornale` è la cronologia leggibile di che cosa è successo a
una pratica, ed è ciò che l'operatore consulta per capire perché i tempi si sono fermati. L'evento lo
scrive il database: una sospensione creata da un import, da uno script o da un inserimento diretto
finisce comunque nel giornale.

---

### Che cosa scrive

* Pratica e flusso sono quelli della sospensione; l'origine è `SISTEMA`.
* Il dettaglio porta l'id della sospensione, il motivo, la data di inizio, la data di riattivazione
  prevista e il **livello**: `PRATICA` se la sospensione riguarda l'intera pratica, `FLUSSO` se una sola
  fase. Il livello evita di dover reinterpretare il flusso vuoto in lettura.

---

### Il vocabolario delle azioni è un vincolo, non una tabella

`SOSPENSIONE_REGISTRATA` è ammesso perché compare nell'elenco chiuso degli eventi di motore del vincolo
`chk_giornale_azione`, che accetta anche qualunque codice nella forma `DOMINIO_<NOME>`.

⚠️ Il vocabolario si estende con una migrazione, non con una riga di dati: un evento di motore nuovo
fuori dalla forma `DOMINIO_*` richiede di riscrivere il vincolo.

---

### ⚠️ Il ripiego sulla transazione è una rete che non dovrebbe servire

Se la sospensione non porta `tx_id`, la funzione ne genera uno nuovo. Un id inventato qui non correla
niente: la riga di giornale risulterebbe di una transazione che non esiste altrove.

Non accade, perché `dbops.trgfn_tx_id_managed` valorizza `tx_id` sulla sospensione prima che questo
trigger parta. Ma se quel trigger venisse tolto, il difetto non si manifesterebbe come errore: si
manifesterebbe come righe di giornale non correlabili.

---

### Codici errore

Nessuno: la funzione non solleva. Un fallimento sarebbe una violazione di vincolo su
`pratiche.giornale` e, poiché il trigger gira nella stessa transazione, farebbe fallire anche
l'inserimento della sospensione.

---

{% include-markdown "signature-core.md" %}
