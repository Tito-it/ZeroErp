## 📘 Documentazione Concettuale – Funzione `script.trgfn_doc_righe_guard_data_consegna()`

> 👀 **Vedi anche**
>
> • [script.fn_data_consegna_ammessa](/dbzero/script/manual/fn_data_consegna_ammessa) — la regola, e perché esiste
> • [script.fn_doc_date_consegna_anteriori](/dbzero/script/manual/fn_doc_date_consegna_anteriori) — il lettore che decide quali date giudicare
> • [script.trgfn_doc_testata_guard_data_consegna_righe](/dbzero/script/manual/trgfn_doc_testata_guard_data_consegna_righe) — il lato opposto

---

### 🎯 Scopo Principale

(nato il 2026-10-13, dal collaudo)

**Il guard di riga: una data di consegna anteriore alla data del documento si
rifiuta.** Non contiene il predicato: chiede al lettore quali date della riga
sono fuori regola (in un UPDATE solo quelle cambiate) e solleva la prima.

| Montaggio | Argomenti |
| --- | --- |
| `trg_ordini_righe_a10_guard_data_consegna_vs_doc_ins_upd` | `('ORDINE', 'ordine_id')` |
| `trg_preventivi_righe_a10_guard_data_consegna_vs_doc_ins_upd` | `('PREVENTIVO', 'preventivo_id')` |

`BEFORE INSERT OR UPDATE FOR EACH ROW`, fascia `_a10_`. Parlano prima il lock
fuori bozza (`_a05_`: la riga non si tocca) e, sulle righe d'ordine, il guard
della riga già spedita: un rifiuto di immutabilità viene prima di uno sul valore.

### 🚨 Il rifiuto

`E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE` (`DATO_ERRATO`): l'operatore rimedia
scrivendo un'altra data. Il campo è la colonna fuori regola, e il frontend
accende quella. La frase dice il documento, la data di consegna e la data del
documento. Nessun numero di riga: in blocco la data è una per tutte.

⭐ La regola non spegne un pulsante: riguarda un valore che l'operatore scrive.
Il frontend la anticipa mettendo come minimo del calendario la data del
documento, che ha già in mano.
