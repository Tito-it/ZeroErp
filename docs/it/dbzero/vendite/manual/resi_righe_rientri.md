## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe_rientri`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) (la riga commerciale)
> [vendite.ddt_righe_prelievi](/dbzero/vendite/tabelle/ddt_righe_prelievi) (che cosa era uscito)
> [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) (il registro)
>
> Funzioni:
> [vendite.fn_reso_merce_da_rientrare](/dbzero/vendite/funzioni/fn_reso_merce_da_rientrare)
> [script.fn_check_reso_merce](/dbzero/script/funzioni/fn_check_reso_merce)
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)
>
> Brief: `brief-db-magazzino-lotto-3-bis-carico-da-reso` (D-3b-b, D-3b-g)

---

### 🎯 Scopo Principale

(rev 2026-09-29 — Lotto 3-bis del magazzino)

**Che cosa torna, fisicamente, con una riga di reso.** Un rientro dice: *di questa riga di reso,
questa quantità, di quel prelievo della bolla d'origine, in questa ubicazione*.

La riga di reso è l'unità **commerciale** (tipo di reso, quantità, credito); il rientro è l'unità
**fisica**. Una riga che rende 4 pezzi usciti in due lotti ha due rientri.

---

### Il rientro non sceglie: ritrova

Il rientro non indica lotto, seriale né articolo: nomina il **prelievo** con cui la merce era
uscita (`ddt_riga_prelievo_id`) e da lì li legge. La merce che torna è quella che era partita:
se è uscito il lotto A, rientra il lotto A — anche per un richiamo di lotto la traccia regge.
Il prelievo deve appartenere alla riga di bolla da cui viene la riga di reso
(`E_RESO_RIENTRO_INCOERENTE`).

Ne discendono due cose, senza una regola in più:

* **il kit**: se con la bolla erano usciti i componenti (kit non gestito, componenti gestiti), i
  prelievi sono dei componenti, e rientrano i componenti. Ciascuno in proporzione a quanto ne era
  uscito, ma **non oltre**: un kit può tornare senza un pezzo, e il magazzino deve dirlo;
* **un reso da una bolla che non aveva mosso merce** non ha prelievi da nominare, e non fa
  rientrare niente.

Dove c'è una sola cosa possibile — un solo prelievo d'origine, un magazzino senza ubicazioni —
il rientro lo crea da sé la conferma. Chi scrive un rientro su una riga si prende la riga intera:
è così che si dice «di questo kit è tornato solo questo».

---

### Le regole

* **quantità** in unità base, sempre positiva: il verso lo mette il carico;
* **ubicazione** di rientro, obbligatoria o vietata secondo il magazzino del reso (come per ogni
  movimento);
* **non più di quanto era uscito**: sommando i resi non annullati della stessa bolla, da un
  prelievo non rientra più della sua quantità (`E_RESO_RIENTRO_OLTRE_USCITO`, alla conferma);
* **solo in bozza**: dopo la conferma il carico è scritto e i rientri non cambiano più
  (`E_RIGA_DOC_NON_BOZZA`, come le righe). Dal 2026-10-05 lo dice lo stesso
  [building block delle righe](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
  montato a livello RIGA (`trg_resi_righe_rientri_a05_doc_bozza_ins_upd_dlt`); la copia della
  regola che stava nel guard del rientro è stata ritirata, e il guard
  (`trg_resi_righe_rientri_a10_guard_ins_upd`) tiene solo la coerenza col prelievo;
* ogni rientro è la **sorgente** del suo carico di magazzino (`RESO_VENDITA_RIENTRO`): un rientro,
  un movimento `CARICO_RESO_VEN`, al costo dell'uscita d'origine. All'annullo del reso il carico si
  storna.

La tabella è un satellite del reso: la vede e la scrive chi vede il reso (perimetro
dell'emittente). Meccanismo comune: [Linee guida SQL — sezione 10](/linee-guida-sql#10-row-level-security-rls).
