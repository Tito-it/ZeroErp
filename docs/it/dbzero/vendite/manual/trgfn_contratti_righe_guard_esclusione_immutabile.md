## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_righe_guard_esclusione_immutabile()`

> 👀 **Vedi anche**
>
> **Tabella:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
>
> **La stessa regola, a video:** [vendite.fn_contratto_righe_preview](/dbzero/vendite/funzioni/fn_contratto_righe_preview) — la riga esclusa ha il solo verbo «Ripristina articolo»
>
> **Verifica:** `db/pgtap/vendite/test-contratto-esclusione-non-modificabile-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-12`; trigger `20261004-13`)

**Un'esclusione del contratto non si modifica.** Un articolo escluso è un
articolo che il contratto non vende: prezzo, quantità, unità di misura,
erogazione e fonte non hanno senso. L'esclusione si crea («Escludi») e si
cancella («Ripristina articolo»), e basta. Per vendere l'articolo a un prezzo
diverso lo si ripristina e poi se ne forza il prezzo.

Decisione di Tid, 2026-10-04.

---

### Cosa rifiuta

Ogni `UPDATE` di una riga `ESCLUSIONE` che cambi qualcosa di diverso dalle
colonne **tecniche** (`data_update`, `user_update`, `tx_id`), che i trigger
della stessa riga riscrivono da soli → `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`.

- La regola elenca le colonne **ammesse**, non quelle vietate: una colonna
  aggiunta domani alla tabella nasce bloccata, non aperta.
- **`attivo` è vietata.** Un'esclusione spenta non toglie l'esclusione: tiene
  occupato il posto dell'articolo nell'indice unico
  `uq_contrighe_one_eccezione_per_articolo`, e sull'articolo non si potrebbe più
  creare né un'altra esclusione né un prezzo forzato.
- **Anche le FK sono vietate**: spostare un'esclusione su un altro articolo
  vuol dire crearne un'altra. Le tre FK della tabella sono `ON UPDATE CASCADE`,
  quindi rinumerare la chiave di un articolo, di un contratto o di un'unità di
  misura con un'esclusione verrebbe rifiutato: è la stessa scelta dei lock di
  colonna su FK, e nessuna operazione del gestionale rinumera quelle chiavi.
- Un `UPDATE` che non cambia niente passa.

---

### Forma

- Trigger `trg_contratti_righe_a05_guard_esclusione_immutabile_upd`,
  `BEFORE UPDATE`, per riga, `WHEN (OLD.tipo_eccezione = 'ESCLUSIONE')`.
- **Fascia `_a05_`**: parla prima dei guard `_a10_` e del vincolo sul prezzo.
  Un prezzo scritto su un'esclusione deve dire «l'esclusione non si modifica»,
  non «un'esclusione non ha prezzo», che inviterebbe a togliere il prezzo e
  riprovare. Viene dopo il rifiuto «fuori bozza» del documento, che vale per
  tutte le righe.
- Guarda il tipo **vecchio**: il passaggio di una riga verso `ESCLUSIONE` lo
  rifiuta il lock di colonna su `tipo_eccezione`
  (`E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`).
- Nessuna `fn_check_*`: non c'è un pulsante da spegnere con un motivo, perché
  l'origine `ESCLUSIONE` non ha proprio il verbo «Modifica».
- Contesto dell'errore: `riga_id`, `contratto_id`, `articolo_id`, `colonne`
  (quelle cambiate).

---

{% include-markdown "signature-core.md" %}
