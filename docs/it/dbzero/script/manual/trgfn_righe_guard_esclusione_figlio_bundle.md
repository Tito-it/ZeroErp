## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_esclusione_figlio_bundle()`

> 👀 **Vedi anche**
>
> **Il predicato:** [script.fn_check_esclusione_articolo_documento](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento)
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni) ·
> [vendite.listini_righe_componenti](/dbzero/vendite/tabelle/listini_righe_componenti)
>
> **Verifica:** `db/pgtap/vendite/test-contratto-righe-lista-v1.sql` (contratto) ·
> `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` (offerta)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-44`; trigger `20261004-48` e `-49`)

**Un bundle si vende come unità: non se ne può escludere un pezzo.** Una riga
`ESCLUSIONE` su un articolo che è componente di un bundle del listino del
documento è rifiutata. Si esclude il bundle intero, o non si esclude niente: il
prezzo del bundle è il prezzo dell'insieme. Vale sul contratto e sull'offerta.

Prende il posto di `vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle`
(maggio 2026), che valeva per il solo contratto: un'offerta che escludeva un
componente passava, e il contratto nato dal suo push veniva rifiutato.
Ritirata nello stesso giro.

---

### Come decide

Non decide lei: chiede i motivi a
[`script.fn_check_esclusione_articolo_documento`](/dbzero/script/funzioni/fn_check_esclusione_articolo_documento)
e solleva il **primo** (`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`, campo
`articolo_id`). La stessa check spegne «Escludi» nella lista delle righe: il
pulsante e l'errore non possono dire cose diverse.

---

### Forma

- Argomenti del trigger: il documento (`CONTRATTO`, `OFFERTA`) e la colonna
  del padre.
- Trigger `trg_contratti_righe_a10_guard_esclusione_figlio_bundle_ins_upd` e
  `trg_offerte_eccezioni_a10_guard_escl_figlio_bundle_ins_upd` (nome accorciato
  per stare nei 63 caratteri), fascia `_a10_`, `BEFORE INSERT OR UPDATE`, per
  riga, `WHEN (NEW.tipo_eccezione = 'ESCLUSIONE')`.

---

{% include-markdown "signature-core.md" %}
