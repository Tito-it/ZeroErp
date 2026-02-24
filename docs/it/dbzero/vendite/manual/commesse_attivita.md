## 📘 Documentazione Concettuale – Tabella `vendite.commesse_attivita`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.commesse_attivita` e` la sorgente di verita` operativa delle righe
da emettere verso `attivita_fatturabili`.

Contiene snapshot pricing (`prezzo_snapshot`, `prezzo_bloccato`), competenza,
segmentazione idempotente (`segment_key`) e stato approvazione/emissione.

---

### ✅ Regole principali

* `segment_key` univoca nel perimetro commessa (`commessa_id + segment_key`);
* `istanza_utility_id` sempre valorizzata (anche tramite istanza fittizia);
* `competenza_mese` al primo giorno del mese;
* `prezzo_snapshot >= 0`, `factor_to_base > 0`;
* `pricing_mode`:
  * `FIXED`
  * `FORMULA`
  * `SCAGLIONI`
* `stato_approvazione`:
  * `BOZZA`
  * `APPROVATA`
  * `RIFIUTATA`
* `stato_emissione`:
  * `NON_EMESSA`
  * `EMESSA`
  * `ANNULLATA`

---

### 🧩 Utilizzo previsto

* input del pull `fn_emit_attivita_fatturabili_da_commessa`;
* supporto idempotenza e replay controllato;
* separazione netta owner business (commessa) vs layer esecutivo (AF).

---

{% include-markdown "signature-core.md" %}
