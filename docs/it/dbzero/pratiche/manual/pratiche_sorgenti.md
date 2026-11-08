## 📘 Documentazione Concettuale – Tabella `pratiche.pratiche_sorgenti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica collegata
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — i tipi di documento, la loro chiave e le loro righe
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — la tabella gemella, per le commesse
>
> Approfondimento viste:
>
> * [script.vw_pratica_doc_sorgente](/dbzero/script/views/vw_pratica_doc_sorgente) — il documento più vivo fra i collegamenti di una pratica
>
> Approfondimento funzioni:
>
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
> * [pratiche.fn_pratica_del_documento](/dbzero/pratiche/funzioni/fn_pratica_del_documento) — la pratica di un documento, letta da qui
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

La tabella ponte che collega una pratica ai documenti da cui nasce o che segue (preventivi, ordini,
contratti, commesse…): una riga per collegamento, con il tipo del documento, la sua chiave e il ruolo
del collegamento.

Una pratica può avere più documenti, anche di tipi diversi, e un documento può stare in più
pratiche. La navigazione va nei due sensi: dal documento si vedono le pratiche collegate, dalla
pratica si risale ai documenti.

---

### Il documento collegato, nelle colonne del modello

Il collegamento dice il documento con le colonne del modello della provenienza:

* `sorgente_tipo_id` — il tipo del documento (`config.sorgenti`), sempre presente;
* `sorgente_id` **oppure** `sorgente_uid` — la chiave del documento, una sola: quella che
  `config.sorgenti.key_selector` dichiara per il tipo (l'uid per preventivo e offerta, l'id per gli
  altri). Il `CHECK` di forma vuole esattamente una delle due;
* `sorgente_riga` — la riga del documento, quando il collegamento è a grana di riga; vuota quando il
  collegamento è al documento intero, come lo scrivono oggi i verbi.

Il guard unico `script.trgfn_guard_sorgente`, montato con livello minimo `DOCUMENTO` e azione
`BLOCCA`, verifica che il tipo sia attivo, che la chiave sia quella del tipo, che il documento
esista e sia visibile a chi scrive, e che la riga, se c'è, sia di quel documento. I verbi che
scrivono il collegamento ottengono la chiave dal BB che scrive, e non la compongono da sé.

⛔ **Un documento collegato non si cancella.** Con `BLOCCA`, il lato «in uscita» ferma la
cancellazione di un documento finché un collegamento lo cita (`E_SORG_ORIGINE_REFERENZIATA`), anche
in bozza: prima si toglie il collegamento.

---

### Il ruolo e il milestone del collegamento

* `ruolo_link` distingue il documento principale (`ROOT`) da quelli che si aggiungono dopo
  (`COLLEGATO`): una pratica nata da un preventivo lo ha come `ROOT`, l'ordine che ne deriva vi entra
  come `COLLEGATO`.
* `flusso_id`, facoltativo, aggancia il collegamento a un milestone della stessa pratica (lo
  verifica `pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso`); un milestone ha al più un
  collegamento `ROOT`. Il reconcile sull'esito proiettato lo usa come tie-break fra più istanze.

---

### L'unicità

Un collegamento è unico per pratica, documento (tipo e chiave) e ruolo: lo stesso documento non entra
due volte con lo stesso ruolo nella stessa pratica.

| Aspetto | `vendite.commesse_sorgenti` | `pratiche.pratiche_sorgenti` |
| --- | --- | --- |
| Documento principale | uno solo per commessa | più `ROOT`, di tipi diversi, per pratica |
| Unicità | un documento sta una volta in una commessa | un documento sta una volta per ruolo in una pratica |
| Caso d'uso | la commessa ha un documento d'origine | la pratica può servire più documenti commerciali |

---

### Test

* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — la forma, il guard unico, la riga di
  un altro documento rifiutata, la cancellazione bloccata, gli scrittori e i lettori sulle colonne
  del modello.
* `db/pgtap/pratiche/test-pratiche-sorgenti-flusso.sql` — l'aggancio al milestone.

---

### Note di migrazione

* 2026-11-06 — si aggiunge `sorgente_id`, per i tipi a chiave id.
* 2026-11-08 — `sorgente_uid` diventa uuid e porta solo l'uid dei tipi a chiave uid; la chiave in
  testo è ritirata, con l'unicità e gli indici riscritti sulle due colonne. Il guard unico prende il
  posto del guard sulla chiave in testo, e verifica ora anche la riga del documento
  (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
