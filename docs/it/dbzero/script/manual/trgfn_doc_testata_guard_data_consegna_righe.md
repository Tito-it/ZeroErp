## 📘 Documentazione Concettuale – Funzione `script.trgfn_doc_testata_guard_data_consegna_righe()`

> 👀 **Vedi anche**
>
> • [script.fn_data_consegna_ammessa](/dbzero/script/manual/fn_data_consegna_ammessa) — la regola, e perché esiste
> • [script.fn_doc_date_consegna_anteriori](/dbzero/script/manual/fn_doc_date_consegna_anteriori) — il lettore che conta le righe
> • [script.trgfn_doc_righe_guard_data_consegna](/dbzero/script/manual/trgfn_doc_righe_guard_data_consegna) — il lato della riga

---

### 🎯 Scopo Principale

(nato il 2026-10-13, dal collaudo)

**La data del documento non si sposta oltre le date di consegna già scritte
sulle sue righe attive.** È il lato opposto del guard di riga: senza, la regola
si aggirerebbe dalla testata (righe con la consegna il 20, poi la data
dell'ordine spostata al 25).

| Montaggio | Argomenti |
| --- | --- |
| `trg_ordini_a10_guard_data_vs_consegne_righe_upd` | `('ORDINE')` |
| `trg_preventivi_a10_guard_data_vs_consegne_righe_upd` | `('PREVENTIVO')` |

`BEFORE UPDATE FOR EACH ROW WHEN (OLD.data IS DISTINCT FROM NEW.data)`, fascia
`_a10_`. La data della testata la riscrive solo normalize, e solo in INSERT: il
`WHEN` vede il valore vero. Fuori bozza la data del documento non cambia già
(il lock della testata, `_a05_`, parla per primo): in pratica il guard lavora
sulle bozze.

### 🚨 Il rifiuto

`E_DOC_DATA_OLTRE_CONSEGNA_RIGHE` (`DATO_ERRATO`), campo `data`. La frase dice la
data chiesta e la **consegna più bassa** fra quelle che resterebbero prima, cioè
il limite oltre cui la data del documento non va. Le righe spente non contano.
Retrodatare il documento passa sempre.
