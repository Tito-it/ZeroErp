## 📘 Documentazione Concettuale – Tabella `vendite.note_offerte_commerciali` (partizione)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.note](/dbzero/vendite/tabelle/note)
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)

---

### 🎯 Scopo Principale

(rev 2026-05-24)

`vendite.note_offerte_commerciali` e' la **partizione `'OFFERTA'`** della tabella
partizionata `vendite.note`. Gestisce le note testuali associate all'offerta commerciale
(testata) e alle singole eccezioni (righe).

Per la struttura completa delle colonne e dei trigger comuni a tutte le partizioni,
vedi la documentazione principale [vendite.note](/dbzero/vendite/tabelle/note).

---

### Partizione e `target_tipo`

Il valore di partizione e' `'OFFERTA'` (7 caratteri) — il tipo `target_tipo` e'
`varchar(16)` e non ammette il codice lungo `'OFFERTA_COMMERCIALE'` (19 caratteri).
Il codice breve e' registrato anche nella tabella `config.sorgenti` (scope `PIPELINE_MARKER`).

---

### Anchor note (CHECK `chk_offnote_anchor`)

Lo stesso pattern di `note_contratto` e `note_preventivo`:

| `target_tipo_nota` | `target_riga_id` | `posizione` ammessa             |
| ------------------ | ---------------- | ------------------------------- |
| `DOCUMENTO`        | NULL             | `HEADER`, `FOOTER`, `SEZIONE`   |
| `RIGA`             | NOT NULL         | `BEFORE`, `AFTER`               |

- **DOCUMENTO**: nota di testata sull'offerta (`target_id → offerte_commerciali.id`).
  `target_riga_id` deve essere NULL.
- **RIGA**: nota su una singola eccezione (`target_riga_id → offerte_commerciali_eccezioni.id`).
  `target_riga_id` NOT NULL.

---

### FK e ciclo di vita

- `target_id → offerte_commerciali(id)` — ON DELETE CASCADE: le note scompaiono con l'offerta.
- `target_riga_id → offerte_commerciali_eccezioni(id)` — ON DELETE CASCADE: le note di riga
  scompaiono con l'eccezione.

Il trigger `trg_note_offerte_commerciali_a10_eccezioni_require_attivo_ins_upd`
(→ `dbops.trgfn_child_requires_active_parent`) blocca l'inserimento di note su eccezioni
disattivate (`attivo = false`).

---

{% include-markdown "signature-core.md" %}

---
