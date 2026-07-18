## 📘 Documentazione Concettuale – Tabella `vendite.commesse_sorgenti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
>
### 🎯 Scopo Principale
La tabella `vendite.commesse_sorgenti` traccia la sorgente ROOT della commessa e
garantisce idempotenza sorgente a livello commessa.

---

### Regole principali

* una sola ROOT per commessa (unique parziale `uq_commesse_sorgenti_commessa_root`);
  dal 2026-06-09 la commessa è **multi-sorgente**: 1 ROOT + N COLLEGATO
  (`vendite.fn_link_commessa_sorgente` decide il ruolo);
* una sorgente (`sorgente_tipo_id + sorgente_uid`) appartiene a **una sola
  commessa** (`uq_commesse_sorgenti_src_uid`);
* **formato della chiave** (`sorgente_uid` TEXT): segue
  `config.sorgenti.key_selector` — uuid testuale per i tipi a chiave `uid`
  (preventivo, offerta), **`id::text`** per i tipi a chiave `id` (ordine,
  contratto, ddt, commessa). Dal 2026-07-18 la convenzione è blindata
  (brief-db-guard-sorgente-polimorfa): la fn di link **normalizza** (traduce
  l'uuid dei chiamanti storici in `id::text`) e il guard
  `trg_commesse_sorgenti_a10_guard_sorgente_ins_upd`
  (`trgfn_guard_sorgente_polimorfa_testuale`) valida formato ed esistenza;
* `sorgente_riga` non è una chiave documento: è la grana di riga del link,
  non validata dal guard.

---

### Utilizzo previsto

* tracciabilita` della root source commessa;
* protezione anti-doppio aggancio documento->commessa;
* base per recovery/audit lato orchestratore push.

---

{% include-markdown "signature-core.md" %}
