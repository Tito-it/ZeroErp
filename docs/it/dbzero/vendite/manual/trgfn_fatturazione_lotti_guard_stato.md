## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatturazione_lotti_guard_stato`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)  
>
### 🎯 Scopo Principale
(latest review 24-01-2026; rev 2026-10-24: il lotto fermo)
La funzione **`vendite.trgfn_fatturazione_lotti_guard_stato()`** controlla le
transizioni tra stati documento sui lotti di fatturazione.

---

### Regola applicata

* Trigger `BEFORE UPDATE OF stato_doc_fiscale_id` su `vendite.fatturazione_lotti`.
* Verifica la transizione in `config.stati_doc_fiscale_transizioni`.
* Se `config.stati_doc_fiscale_transizioni.meta.tipo_lotto` e` valorizzato,
  la transizione e` ammessa solo per lotti con lo stesso `tipo_lotto`.
* Se lo stato non e` applicabile o la transizione non e` ammessa → errore.

> Nota: il blocco puo` essere **bypassato** solo in contesti di manutenzione
> tramite GUC `zeroerp.maintenance_reset_lotto_draft = on` (reset tecnico lotto DRAFT).

---

### Un lotto fermo non diventa definitivo

(rev 2026-10-24, `brief-modello-documento-vendita` R-1)

La regola di Tid: *se un documento del lotto è in errore, gli altri non possono passare a
uno stato definitivo; prima i documenti non conformi si tolgono dal lotto (o si correggono e
si rilancia lo step).*

* Quando il lotto sta per entrare in uno stato **congelato e non abortito** (dal vocabolario:
  `congela_fiscale = true`, `is_abortito = false`; oggi Definitiva, Inviata, Registrata), il
  controllo legge se il lotto è **fermo** dalla sede unica
  [vendite.vw_lotti_segnalazioni_summary](/dbzero/vendite/views/vw_lotti_segnalazioni_summary):
  segnalazioni critiche, fatture in errore, documenti in errore.
* Se è fermo, rifiuta con `E_PIPELINE_LOTTO_CRITICAL`: lo **stesso codice** del runner della
  pipeline. La regola è una, i punti in cui si applica due: il runner si ferma prima, il
  database decide anche per chi scrive senza passare dal runner.
* Un passaggio **non** congelato (per esempio a Emessa) resta ammesso, e così l'**annullo**.

L'altra metà della regola sta nell'invariante lotto ↔ fatture
([vendite.fn_guard_lotto_fatture_stato_coerente](/dbzero/vendite/manual/fn_guard_lotto_fatture_stato_coerente)).
Presidio: `db/pgtap/vendite/test-lotto-fermo-non-diventa-definitivo-v1.sql`.

---

{% include-markdown "signature-core.md" %}
