## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_erogazione_obbligatoria()`

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
>
> **Chi legge l'erogazione:** [vendite.fn_list_contratti_da_pushare](/dbzero/vendite/funzioni/fn_list_contratti_da_pushare)
>
> **Verifica:** `db/pgtap/vendite/test-righe-erogazione-obbligatoria-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-31`; trigger `20261004-32`)

**Una riga del contratto o dell'offerta che si fattura dice come si eroga.**
Un prezzo forzato (`OVERRIDE`) e un articolo aggiunto (`AGGIUNTA`) finiscono in
fattura, e la fattura deve sapere se contarli come canone, una tantum, a ore o
a consumo. Senza il tipo di erogazione il sistema dovrebbe indovinarlo.
L'esclusione non si fattura: lì l'erogazione è vuota, come gli altri dati di
vendita (dal 2026-10-04, [`trgfn_righe_guard_esclusione_senza_dati`](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_senza_dati)).

Decisione di Tid, 2026-10-04.

---

### Cosa rifiuta

Un `INSERT`, o un `UPDATE` di `tipo_erogazione` o `tipo_eccezione`, che lascia
vuota l'erogazione su una riga che non è `ESCLUSIONE` →
`E_RIGA_EROGAZIONE_OBBLIGATORIA` (dato errato, campo `tipo_erogazione`).

- La regola è scritta come «tutto tranne l'esclusione», non come «prezzo
  forzato o articolo aggiunto»: un tipo di riga aggiunto domani nasce vincolato.
- Dietro il guard ci sono i vincoli `chk_contrighe_erogazione_per_tipo_eccezione`
  e `chk_offerte_eccezioni_erogazione_per_tipo_eccezione`, con la stessa regola:
  il guard parla prima e dice quale campo correggere, il vincolo copre le
  strade che il trigger non percorre.

---

### Forma

- Una funzione sola per le due tabelle gemelle, come
  [`trgfn_righe_default_fonte_qta`](/dbzero/script/funzioni/trgfn_righe_default_fonte_qta):
  l'offerta passa la sua erogazione al contratto
  (`vendite.fn_push_offerta_a_contratto`), e la regola deve essere la stessa ai
  due capi.
- Argomento del trigger: la colonna del documento padre (`contratto_id`,
  `offerta_id`), usata solo nel contesto dell'errore.
- Trigger `trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd` e
  `trg_offerte_eccezioni_a10_guard_erogazione_obbligatoria_ins_upd`, fascia
  `_a10_`, `BEFORE INSERT OR UPDATE OF tipo_erogazione, tipo_eccezione`, per riga.
- Nessuna `fn_check_*`: la regola non spegne un pulsante, segnala un campo
  mancante in un form.
- Contesto dell'errore: `campo`, `riga_id`, la colonna padre, `articolo_id`,
  `tipo_eccezione`.

---

{% include-markdown "signature-core.md" %}
