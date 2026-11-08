## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_ddt_consegnato`

> **Ultimo aggiornamento**: 8 novembre 2026
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
> * [vendite.fn_ddt_causale_magazzino](/dbzero/vendite/funzioni/fn_ddt_causale_magazzino) — riconosce la bolla di trasferimento

---

### 🎯 Scopo Principale

**«Non si rende ciò che non è stato consegnato»**: `BEFORE INSERT` su `vendite.resi`, ammette il reso solo se la bolla d'origine è in stato **`CONSEGNATO`** (`E_RESO_DDT_NON_CONSEGNATO`).

---

### Le regole

* **Si applica solo a una bolla di vendita**: se il reso dichiara un tipo diverso da
  `DDT_VENDITA` (un reso da fattura, domani), il guard tace.
* **La bolla si trova dalla provenienza del reso**: il tipo `DDT_VENDITA` è a chiave `id`, e il
  reso porta l'id della bolla in `sorgente_id`. Il guard legge la bolla con la regola d'incontro
  (id o uid), senza leggere il `key_selector`.
* **Una bolla di trasferimento fra depositi non genera un reso**
  (`E_RESO_DA_DDT_TRASFERIMENTO`): la merce è rimasta nostra, entrata nel magazzino di arrivo alla
  consegna; un reso la farebbe rientrare una seconda volta, con un accredito verso un cliente che
  non l'ha mai comprata. Si riconosce dalla causale di magazzino della sua causale di trasporto,
  non da un codice scritto a mano, e parla **prima** del controllo di stato: è la risposta vera.
* È la difesa nel database della regola che il backend presidia anche nell'interfaccia.

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

---

{% include-markdown "signature-core.md" %}
