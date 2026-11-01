## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_periodicita_canone()`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/manual/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/manual/offerte_commerciali_eccezioni)
>
> **Il default che viene prima:** [script.trgfn_righe_default_periodicita_da_listino](/dbzero/script/funzioni/trgfn_righe_default_periodicita_da_listino)
>
> **Chi legge la periodicità:** [vendite.fn_contratti_addebiti_maturati](/dbzero/vendite/manual/fn_contratti_addebiti_maturati)
>
> **Verifica:** `db/pgtap/vendite/test-righe-canone-periodicita-obbligatoria-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-11-01, `20261101-05`; trigger `20261101-06`; CHECK `20261101-04` —
brief `brief-db-contratto-righe-periodiche-in-commessa` §6.11, passo 4)

**Una riga a canone del contratto o dell'offerta dice ogni quanto si addebita.** Senza la
periodicità il canone non si può addebitare: prima di questa regola la riga si salvava, e il push
la scartava ogni giro (`SENZA_PERIODICITA`), visibile solo dalla dashboard.

Decisioni di Tid: la periodicità è una condizione della riga e del listino (G-0-bis, 2026-10-28);
sull'AGGIUNTA la scrive l'operatore, senza default (F-9, 2026-10-29: un «mensile» d'ufficio farebbe
passare un canone annuale fatturato dodici volte); l'obbligo entra quando il form la chiede (la
(b) del Lotto 4b, 2026-10-29).

---

### Cosa rifiuta

Un `INSERT`, o un `UPDATE` di `tipo_erogazione` o `periodicita`, che lascia senza periodicità una
riga `CANONE` → `E_RIGA_CANONE_SENZA_PERIODICITA` (dato errato, campo `periodicita`).

- ADESIONE e OVERRIDE la ereditano dal listino, se il listino la dice: il default scatta prima.
  Se il listino non la dice, la riga la deve scrivere.
- L'ESCLUSIONE non ha erogazione e non si giudica; una riga che non è a canone nemmeno.
- Dietro il guard ci sono i vincoli `chk_contrighe_canone_periodicita` e
  `chk_offerte_eccezioni_canone_periodicita`, con la stessa regola: il guard parla prima e dice
  quale campo correggere, il vincolo copre le strade che il trigger non percorre.

---

### Forma

- Una funzione sola per le due tabelle gemelle: il passaggio offerta → contratto e la revisione
  dell'offerta copiano la periodicità, e la regola deve essere la stessa ai due capi.
- `TG_ARGV[0]` = la colonna del documento padre (`contratto_id`, `offerta_id`), solo per il
  contesto dell'errore.
- **L'ordine è il nome** (fascia `_a10_`, `guard_periodicita_canone`): dopo i default
  dell'erogazione e della periodicità, dopo i guard dell'erogazione (obbligo e perimetro: a una
  riga che non può essere a canone parla prima il perimetro), prima della quantità per fonte.
- `SECURITY INVOKER`.

---

{% include-markdown "signature-core.md" %}
