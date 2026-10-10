## 📘 Documentazione Concettuale – Funzione `script.trgfn_righe_guard_esclusione_senza_dati()`

> 👀 **Vedi anche**
>
> **Tabelle:** [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) ·
> [vendite.offerte_commerciali_eccezioni](/dbzero/vendite/tabelle/offerte_commerciali_eccezioni)
>
> **Funzioni sorelle:** [script.trgfn_righe_guard_esclusione_immutabile](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_immutabile) ·
> [script.trgfn_righe_guard_erogazione_obbligatoria](/dbzero/script/funzioni/trgfn_righe_guard_erogazione_obbligatoria)
>
> **Verifica:** `db/pgtap/vendite/test-righe-esclusione-solo-non-si-vende-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-47`; trigger `20261004-48` e `-49`)

**Un'esclusione dice solo «questo articolo non si vende».** Non si fattura,
quindi non ha dati di vendita: prezzo, quantità, quantità operativa, unità di
misura, fattore di conversione, tipo di erogazione, fonte della quantità,
periodicità, generazione e competenza del canone **restano vuoti**. Vale sul
contratto e sull'offerta, che passa le sue righe al contratto.

Decisione di Tid, 2026-10-04.

---

### Cosa rifiuta

Un `INSERT` di una riga `ESCLUSIONE` con uno di quei dieci dati →
`E_RIGA_ESCLUSIONE_CON_DATI` (dato errato).

- Nel contesto dell'errore `campo` è il **primo** dato valorizzato (nell'ordine
  dell'elenco): è quello che il form evidenzia. `colonne` li elenca tutti.
- Dietro il guard ci sono i vincoli `chk_contrighe_esclusione_senza_dati` e
  `chk_offerte_eccezioni_esclusione_senza_dati`, con lo stesso elenco: il guard
  parla prima e dice quale campo svuotare, il vincolo copre le strade che il
  trigger non percorre.
- Solo `INSERT`, di proposito: un'esclusione si scrive solo nascendo. Il suo
  `UPDATE` lo rifiuta il guard «non si modifica», il cambio di tipo verso
  `ESCLUSIONE` il lock di colonna su `tipo_eccezione`: ciascuno col suo
  rimedio. Montato anche in `UPDATE`, questo guard parlerebbe prima del lock
  e direbbe «svuota il campo» invece di «elimina e ricrea».

---

### Perché l'esclusione restava piena

Fino al 2026-10-04 il drawer creava l'esclusione con una quantità 1, una fonte
`FISSA` e un'erogazione, e i trigger della riga riempivano il resto (fonte di
default, unità di misura e fattore dall'articolo). Dati che nessuno aveva
scelto, su una riga che non si vende. Da quel giorno i due trigger che
riempiono la riga la saltano (`WHEN` sul trigger), e `fonte_quantita_attesa`
non è più `NOT NULL`: è obbligatoria solo sulle righe che non sono esclusioni.

---

### Forma

- Una funzione sola per le due tabelle gemelle, come gli altri guard delle
  righe in `script`.
- Argomento del trigger: la colonna del documento padre, solo per il contesto.
- Trigger `trg_contratti_righe_a10_guard_esclusione_senza_dati_ins` e
  `trg_offerte_eccezioni_a10_guard_esclusione_senza_dati_ins`, fascia
  `_a10_`, `BEFORE INSERT`, per riga,
  `WHEN (NEW.tipo_eccezione = 'ESCLUSIONE')`. Fra gli `_a10_` parla dopo il
  guard del componente di bundle: «questo articolo non si esclude» viene prima
  di «hai mandato dati».
- Nessuna `fn_check_*`: non spegne un pulsante, dice quale campo di un form è
  di troppo.

---

{% include-markdown "signature-core.md" %}
