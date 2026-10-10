## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_aggiunta_fuori_listino()`

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) ·
> [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
>
> **La versione del listino:** [vendite.fn_documento_listino_operativo](/dbzero/vendite/funzioni/fn_documento_listino_operativo)
>
> **Verifica:** `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` (offerta) ·
> `db/pgtap/vendite/test-contratti-schema-step22-v1.sql` (contratto)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-45`; trigger `20261004-48` e `-49`)

**Un'aggiunta è un articolo fuori dal listino.** Per cambiare il prezzo di un
articolo che il listino ha già si usa il prezzo forzato (`OVERRIDE`), non
l'aggiunta. Vale sul contratto e sull'offerta.

Prende il posto di `vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino`
(nata nel maggio 2026, `20260515-12`), che valeva per il solo contratto.
Sull'offerta mancava: un'offerta con un'aggiunta di un articolo a listino
passava, e il contratto nato dal suo push veniva rifiutato. Ritirata nello
stesso giro.

---

### Cosa rifiuta

Una riga `AGGIUNTA` il cui articolo sta (riga attiva) nella versione del
listino che vale per il documento → `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`. Il
messaggio nomina l'articolo e il documento con la sua etichetta («Contratto
…», «Offerta …»); il codice porta «CONTRATTO» nel nome per storia.

**Quale versione** la dice
[`vendite.fn_documento_listino_operativo`](/dbzero/vendite/funzioni/fn_documento_listino_operativo):
quella fissata (contratto attivo, offerta emessa) o, in bozza, quella in vigore
oggi. Senza listino (solo un contratto può non averlo) l'aggiunta è sempre
ammessa. Un articolo a listino con la riga spenta non conta.

---

### Forma

- Argomenti del trigger: il documento (`CONTRATTO`, `OFFERTA`) e la colonna
  del padre (`contratto_id`, `offerta_id`).
- Trigger `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd` e
  `trg_offerte_eccezioni_a10_guard_aggiunta_fuori_listino_ins_upd`, fascia
  `_a10_`, `BEFORE INSERT OR UPDATE`, per riga,
  `WHEN (NEW.tipo_eccezione = 'AGGIUNTA')`: la funzione non viene neppure
  chiamata sulle altre righe.
- Contesto dell'errore: `campo` (`articolo_id`), il documento, la colonna
  padre, `articolo_id`, `listino_id`, `listino_versione_id`.

---

{% include-markdown "signature-core.md" %}
