## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe_rientri`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) — la riga commerciale
> * [vendite.ddt_righe_prelievi](/dbzero/vendite/tabelle/ddt_righe_prelievi) — che cosa era uscito
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro in cui il rientro diventa un carico
>
> Approfondimento funzioni:
>
> * [vendite.fn_reso_merce_da_rientrare](/dbzero/vendite/funzioni/fn_reso_merce_da_rientrare) — che cosa può rientrare
> * [script.fn_check_reso_merce](/dbzero/script/funzioni/fn_check_reso_merce) — i controlli della merce alla conferma
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — il verbo che scrive i carichi
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: il rientro è il dettaglio del reso

---

### 🎯 Scopo Principale

**Che cosa torna, fisicamente, con una riga di reso.** Un rientro dice: *di questa riga di reso, questa quantità, di quel prelievo della bolla d'origine, in questa ubicazione*.

La riga di reso è l'unità **commerciale** (tipo di reso, quantità, credito); il rientro è l'unità **fisica**. Una riga che rende 4 pezzi usciti in due lotti ha due rientri.

---

### Il rientro non sceglie: ritrova

Il rientro non indica lotto, seriale né articolo: nomina il **prelievo** con cui la merce era
uscita (`ddt_riga_prelievo_id`) e da lì li legge. La merce che torna è quella che era partita: se
è uscito il lotto A, rientra il lotto A — anche per un richiamo di lotto la traccia regge. Il
prelievo deve appartenere alla riga di bolla da cui viene la riga di reso
(`E_RESO_RIENTRO_INCOERENTE`).

Ne discendono due cose, senza una regola in più:

* **il kit**: se con la bolla erano usciti i componenti (kit non gestito, componenti gestiti), i
  prelievi sono dei componenti, e rientrano i componenti. Ciascuno in proporzione a quanto ne era
  uscito, ma **non oltre**: un kit può tornare senza un pezzo, e il magazzino deve dirlo;
* **un reso da una bolla che non aveva mosso merce** non ha prelievi da nominare, e non fa rientrare
  niente.

Dove c'è una sola cosa possibile — un solo prelievo d'origine, un magazzino senza ubicazioni — il
rientro lo crea da sé la conferma. Chi scrive un rientro su una riga si prende la riga intera: è
così che si dice «di questo kit è tornato solo questo».

---

### Le regole

* **quantità** in unità base, sempre positiva: il verso lo mette il carico;
* **ubicazione** di rientro, obbligatoria o vietata secondo il magazzino del reso (come per ogni
  movimento);
* **non più di quanto era uscito**: sommando i resi non annullati della stessa bolla, da un
  prelievo non rientra più della sua quantità (`E_RESO_RIENTRO_OLTRE_USCITO`, alla conferma);
* **solo in bozza**: dopo la conferma il carico è scritto e i rientri non cambiano più
  (`E_RIGA_DOC_NON_BOZZA`, come le righe). Lo dice il
  [building block delle righe](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza), montato a
  livello RIGA (`trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt`); il guard del rientro
  (`trg_resi_righe_rientri_a10_guard_ins_upd`) tiene solo la coerenza col prelievo.

---

### Il rientro è il dettaglio del reso, per il magazzino

Ogni rientro diventa **un** carico di magazzino (`CARICO_RESO_VEN`), al costo dell'uscita
d'origine. Il carico dichiara la sua provenienza con il modello comune, a tre livelli: il
documento è il **reso** (tipo `RESO_VENDITA`), la riga è la **riga di reso**, il dettaglio è il
**rientro**. Il catalogo dei tipi (`config.sorgenti`) dichiara per `RESO_VENDITA` le righe in
`vendite.resi_righe` e il dettaglio in questa tabella, ed è da lì che il guard unico del registro
verifica che il rientro appartenga a quella riga e quella riga a quel reso.

All'annullo del reso il carico si storna. Se un rientro si cancella, il lato «in uscita» della
provenienza guarda i movimenti che lo dichiarano come dettaglio e applica la loro regola: il
registro di magazzino blocca.

La tabella è un satellite del reso: la vede e la scrive chi vede il reso (perimetro
dell'emittente). Meccanismo comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).

---

### Note di migrazione

* 2026-09-29 — nasce col rientro in magazzino della merce resa (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-b, D-3b-g).
* 2026-10-05 — la regola «solo in bozza» passa al building block delle righe; la copia nel guard
  del rientro si ritira.
* 2026-11-08 — il carico dichiara il reso, la sua riga e il rientro come dettaglio, al posto del
  tipo dedicato ai rientri (`RESO_VENDITA_RIENTRO`), ritirato dal catalogo dei tipi
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
