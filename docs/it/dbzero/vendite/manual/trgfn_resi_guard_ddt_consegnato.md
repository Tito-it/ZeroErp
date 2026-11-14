## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_ddt_consegnato`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — la testata che controlla
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la bolla d'origine
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — gli stati della bolla
>
> Approfondimento funzioni:
>
> * [script.fn_check_ddt_rendibile](/dbzero/script/funzioni/fn_check_ddt_rendibile) — la regola, coi suoi motivi
> * [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) — `can_genera_reso`, dalla stessa check
> * [vendite.fn_ddt_causale_magazzino](/dbzero/vendite/funzioni/fn_ddt_causale_magazzino) — riconosce la bolla di trasferimento

---

### 🎯 Scopo Principale

**«Non si rende ciò che non è stato consegnato»**: `BEFORE INSERT` su `vendite.resi`, ammette il
reso solo se dalla bolla d'origine nasce un reso. La regola non è scritta qui: sta in
[`script.fn_check_ddt_rendibile`](/dbzero/script/funzioni/fn_check_ddt_rendibile), e il trigger
solleva il primo motivo. La stessa check dà `can_genera_reso` nella capability della bolla: il
pulsante «Genera reso» e il rifiuto dicono la stessa cosa.

---

### Le regole

* **Si applica solo a una bolla di vendita**: se il reso dichiara un tipo diverso da
  `DDT_VENDITA`, il guard tace; quel reso lo rifiuta
  [vendite.trgfn_resi_guard_cliente_ddt](/dbzero/vendite/funzioni/trgfn_resi_guard_cliente_ddt)
  (`E_RESO_SORGENTE_NON_DDT`), perché un reso nasce solo da una bolla.
* **La bolla si trova dalla provenienza del reso**: il tipo `DDT_VENDITA` è a chiave `id`, e il
  reso porta l'id della bolla in `sorgente_id`. Il guard cerca la bolla lì; `sorgente_uid` resta
  vuota. Il contesto dei due errori porta `sorgente_id`, e il dettaglio del motivo (`ddt_id`,
  `stato_ddt`). Con `sorgente_id` vuoto il guard lascia passare: risponde il vincolo della forma
  della sorgente (`chk_resi_sorgente_forma`).
* I due motivi, nell'ordine della check (si esce al primo):
  * **una bolla di trasferimento fra depositi non genera un reso** (`E_RESO_DA_DDT_TRASFERIMENTO`):
    la merce è rimasta nostra, entrata nel magazzino di arrivo alla consegna; un reso la farebbe
    rientrare una seconda volta, con un accredito verso un cliente che non l'ha mai comprata. Si
    riconosce dalla causale di magazzino della sua causale di trasporto, non da un codice scritto a
    mano, e parla **prima** del controllo di stato: è la risposta vera;
  * la bolla non è in `CONSEGNATO`, o non c'è (`E_RESO_DDT_NON_CONSEGNATO`). `CONSEGNATO` è la
    destinazione del processo di consegna, e si nomina col codice.

---

### Codici errore

* `E_RESO_DA_DDT_TRASFERIMENTO` — la bolla è un trasferimento fra depositi.
* `E_RESO_DDT_NON_CONSEGNATO` — la bolla non è `CONSEGNATO`.

---

### Note di migrazione

* 2026-07-13 — nasce col reso di vendita (brief-db-resi-vendita).
* 2026-09-28 — rifiuta il reso da una bolla di trasferimento (brief-db-magazzino-lotto-3-scarico-da-ddt).
* 2026-11-06 — la bolla si legge dalla chiave del modello, `sorgente_id`; prima dal suo uid in
  `sorgente_uid` (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la bolla si cerca per `sorgente_id` soltanto, e `sorgente_uid` esce dal dettaglio
  degli errori (brief-db-sorgente-documento-e-riga, G-3).
* 2026-11-14 — la regola esce in `script.fn_check_ddt_rendibile`, letta anche dalla capability della
  bolla (`can_genera_reso`); stessi codici (brief-db-stati-documento-dal-vocabolario, giro 6e).

---

{% include-markdown "signature-core.md" %}
