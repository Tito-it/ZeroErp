## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_esclusione_immutabile()`

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
>
> **La stessa regola, a video:** [vendite.fn_documento_righe_preview](/dbzero/vendite/funzioni/fn_documento_righe_preview) — la riga esclusa ha il solo verbo «Ripristina articolo»
>
> **Verifica:** `db/pgtap/vendite/test-contratto-esclusione-non-modificabile-v1.sql` (contratto) ·
> `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql` (offerta)

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-46`; trigger `20261004-48` e `-49`)

**Un'esclusione non si modifica, né sul contratto né sull'offerta.** Un articolo
escluso è un articolo che il documento non vende: non ha prezzo, quantità né
erogazione. L'esclusione si crea («Escludi») e si cancella («Ripristina
articolo»), e basta. Per vendere l'articolo a un prezzo diverso lo si ripristina
e poi se ne forza il prezzo.

Decisione di Tid, 2026-10-04.

Prende il posto di `vendite.trgfn_contratti_righe_guard_esclusione_immutabile`
(`20261004-12`), che valeva per il solo contratto: l'offerta passa le sue righe
al contratto, e la regola deve valere ai due capi. Ritirata nello stesso giro.

---

### Cosa rifiuta

Ogni `UPDATE` di una riga `ESCLUSIONE` che cambi qualcosa di diverso dalle
colonne **tecniche** (`data_update`, `user_update`, `tx_id`), che i trigger
della stessa riga riscrivono da soli → `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`.
Il codice porta «CONTRATTO» nel nome per storia; il messaggio non nomina il
documento.

- La regola elenca le colonne **ammesse**, non quelle vietate: una colonna
  aggiunta domani alla tabella nasce bloccata, non aperta.
- **`attivo` è vietata.** Un'esclusione spenta non toglie l'esclusione: tiene
  occupato il posto dell'articolo nell'indice unico (una sola eccezione per
  articolo), e sull'articolo non si potrebbe più creare né un'altra esclusione
  né un prezzo forzato.
- **Anche le FK sono vietate**: spostare un'esclusione su un altro articolo
  vuol dire crearne un'altra.
- Un `UPDATE` che non cambia niente passa.

---

### Forma

- Argomento del trigger: la colonna del documento padre (`contratto_id`,
  `offerta_id`), usata solo nel contesto dell'errore.
- Trigger `trg_contratti_righe_a05_guard_esclusione_immutabile_upd` e
  `trg_offerte_commerciali_eccezioni_a05_guard_escl_immut_upd`, `BEFORE UPDATE`,
  per riga, `WHEN (OLD.tipo_eccezione = 'ESCLUSIONE')`.
- **Fascia `_a05_`**: parla prima dei guard `_a10_` e dei vincoli. Un prezzo
  scritto su un'esclusione deve dire «l'esclusione non si modifica», non
  «un'esclusione non ha prezzo», che inviterebbe a togliere il prezzo e
  riprovare. Viene dopo il rifiuto «fuori bozza» del documento.
- Guarda il tipo **vecchio**: il passaggio di una riga verso `ESCLUSIONE` lo
  rifiuta il lock di colonna su `tipo_eccezione`.
- Nessuna `fn_check_*`: non c'è un pulsante da spegnere con un motivo, perché
  l'esclusione non ha proprio il verbo «Modifica».
- Contesto dell'errore: `riga_id`, la colonna padre, `articolo_id`, `colonne`
  (quelle cambiate).

---

{% include-markdown "signature-core.md" %}
