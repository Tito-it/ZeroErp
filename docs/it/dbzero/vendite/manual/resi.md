## 📘 Documentazione Concettuale – Tabella `vendite.resi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) — le righe del reso
> * [vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri) — la merce che rientra
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la bolla da cui il reso nasce
> * [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso) — gli stati del reso
>
> Approfondimento viste:
>
> * [dbops.vw_resi_confermati_senza_carico](/dbzero/dbops/views/vw_resi_confermati_senza_carico) — il presidio del carico mancante
>
> Approfondimento funzioni:
>
> * [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) · [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — i due verbi
> * [vendite.trgfn_resi_guard_ddt_consegnato](/dbzero/vendite/funzioni/trgfn_resi_guard_ddt_consegnato) — si rende solo ciò che è stato consegnato
> * [vendite.trgfn_resi_normalize](/dbzero/vendite/funzioni/trgfn_resi_normalize) — cliente ed emittente dalla bolla
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
> * [vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza) — si cancella solo la bozza vuota
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — stati, verbi e permessi

---

### 🎯 Scopo Principale

La testata del **reso di vendita**: il documento che registra il rientro di merce da una bolla consegnata. Il reso è un **ibrido** — le sue righe possono essere *a credito* (verso una nota di credito) o *per ri-consegna* (merce da rifare e rispedire, con una bolla di riconsegna che nasce dal reso).

---

### Il reso nasce sempre da una bolla

La provenienza è **obbligatoria**, ed è sempre la **bolla di vendita** da cui torna la merce: il
tipo `DDT_VENDITA` e l'id della bolla in `sorgente_id` (la bolla ha chiave `id`); `sorgente_uid`
resta vuota. La forma la tiene il CHECK `chk_resi_sorgente_forma`; il tipo lo fa valere il guard
del cliente (`vendite.trgfn_resi_guard_cliente_ddt`), che rifiuta un altro tipo con
`E_RESO_SORGENTE_NON_DDT`, perché il reso registra il rientro di una consegna, e la consegna è la
bolla.

* La forma la dice `chk_resi_sorgente_forma` (il tipo con **una** chiave); che la bolla esista e si
  veda lo verifica il guard unico (`trg_resi_a10_guard_sorgente_ins_upd`, livello `DOCUMENTO`,
  `BLOCCA`).
* **Solo da una bolla consegnata**:
  [`trgfn_resi_guard_ddt_consegnato`](/dbzero/vendite/funzioni/trgfn_resi_guard_ddt_consegnato)
  all'inserimento (`E_RESO_DDT_NON_CONSEGNATO`); una bolla di trasferimento fra depositi non genera
  un reso (`E_RESO_DA_DDT_TRASFERIMENTO`).
* La provenienza si sceglie in bozza: fuori bozza è ferma (`E_DOC_SORGENTE_FUORI_BOZZA`, dal lock
  di testata).

---

### Che cosa eredita dalla bolla

[`trgfn_resi_normalize`](/dbzero/vendite/funzioni/trgfn_resi_normalize) copia dalla bolla, se non
sono già valorizzati, cliente (`billing_account_id`), destinatario, utility, valuta ed emittente.
`emittente_fiscale_id` è obbligatorio ed è la chiave del perimetro: policy
`rls_resi_ef_whitelist` e guard di scrittura `script.trgfn_doc_guard_emittente_ba`, che parla dopo
il normalize e vede i valori finali.

---

### Stati, numero, cancellazione

* **Macchina a stati** dal vocabolario (`config.stati_doc_reso` con la sua matrice delle
  transizioni), presidiata da `trgfn_resi_guard_transizione`: `DRAFT → CONFERMATO → (ANNULLATO)`.
  Nessun reso cambia stato con una modifica diretta: lo impedisce la porta comune
  [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo).
* **Numero** assegnato alla **conferma** (vuoto in bozza), poi immutabile.
* **Cancellazione**: si cancella solo la **bozza vuota**, nello stato iniziale del vocabolario e
  senza righe attive
  ([vendite.trgfn_doc_guard_delete_solo_bozza](/dbzero/vendite/funzioni/trgfn_doc_guard_delete_solo_bozza)).
  Dopo, il lato «in uscita» della provenienza guarda chi dichiara il reso come origine (la bolla di
  riconsegna, i carichi di magazzino) e applica la regola che ognuno ha dichiarato.
* Storico, audit e `tx_id` dalle automazioni `dbops`.

---

### La merce rientra in magazzino

La merce **esce** dal magazzino quando si emette la bolla. Il reso chiude il giro: alla
**conferma** la merce resa **rientra** nel registro di magazzino, e se il reso si annulla riesce
con una riga opposta.

**In quale magazzino** — `magazzino_id`, sulla testata. Quando il reso nasce prende il magazzino da
cui era partita la bolla d'origine; in bozza lo si cambia. Chi riceve merce da controllare o rotta
può metterla in un magazzino a parte («resi da verificare»): **dove la metti dice in che stato è**.
Dev'essere un magazzino della stessa azienda del reso, e dopo la conferma non cambia più
(`E_RESO_MAGAZZINO_INCOERENTE`, `E_RESO_MAGAZZINO_IMMUTABILE`). È obbligatorio alla conferma solo
se il reso fa rientrare merce.

**Che cosa rientra** — i rientri, sotto le righe
([vendite.resi_righe_rientri](/dbzero/vendite/tabelle/resi_righe_rientri)). Il reso non sceglie di
nuovo lotto e seriale: li **ritrova** da ciò che era uscito con la bolla. Un reso da una bolla che
non aveva mosso merce (articoli non gestiti, causale che non muove merce) non fa rientrare niente.

**Quando** — alla conferma: la conferma è la presa in carico della merce, alla data del reso. Per
questo la conferma e l'annullo sono due **operazioni del database**. Il permesso lo dice la riga
del passaggio nella matrice: *Conferma reso* (`conferma_reso`) per la conferma e per l'annullo di un
reso confermato; l'annullo di una bozza chiede solo il permesso sul reso (guida
[Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6):

* [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) — controlla la merce (il
  pulsante «Conferma» è spento col motivo quando manca qualcosa), crea da sé i rientri dove non c'è
  niente da scegliere, porta il reso a `CONFERMATO` e scrive i carichi, tutto insieme. Ogni carico
  dichiara come provenienza il reso, la sua riga e il rientro, e ha il **costo dell'uscita
  d'origine**: la merce rientra al valore al quale era uscita;
* [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — su un reso confermato
  scrive gli storni dei carichi. Se la merce nel frattempo è già uscita di nuovo, l'annullo è
  rifiutato: il magazzino non va sotto zero per un annullo.

Se un reso confermato restasse senza carico, lo segnala il presidio
[dbops.vw_resi_confermati_senza_carico](/dbzero/dbops/views/vw_resi_confermati_senza_carico).

---

### Note di migrazione

* 2026-07-13 — nasce il reso di vendita (brief-db-resi-vendita).
* 2026-09-29 — la merce resa rientra in magazzino alla conferma (brief-db-magazzino-lotto-3-bis-carico-da-reso).
* 2026-11-06 — la provenienza passa al modello: la bolla d'origine, a chiave `id`, si dichiara in
  `sorgente_id` (prima stava come uid in `sorgente_uid`), col guard unico
  (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — si cancella solo la bozza vuota.
* 2026-11-08 — la provenienza è solo la bolla: il CHECK di forma vuole la chiave in `sorgente_id`, il
  guard del cliente rifiuta un altro tipo, e i lettori cercano la bolla per `sorgente_id`.
* 2026-11-08 — i carichi di magazzino dichiarano il reso con riga e rientro come dettaglio, al posto
  del tipo dedicato ai rientri.

---

{% include-markdown "signature-core.md" %}
