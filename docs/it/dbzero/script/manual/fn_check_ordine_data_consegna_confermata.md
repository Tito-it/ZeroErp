## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_data_consegna_confermata()`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [script.fn_doc_colonna_modificabile](/dbzero/script/funzioni/fn_doc_colonna_modificabile) — da dove legge la regola
> • [vendite.trgfn_doc_righe_lock_fuori_bozza](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza) — il lock che rifiuterebbe
> • [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — chi accende e spegne il verbo

---

### 🎯 Scopo Principale

(nata il 2026-10-10, brief `brief-db-testata-dopo-emissione`, fase 1)

**La promessa di consegna delle righe di quest'ordine si cambia ora, da sola?**

Dopo la conferma il contenuto dell'ordine non si tocca più, con un'eccezione decisa da Tid:
la data di consegna confermata di una riga si può ancora spostare finché c'è merce da
evadere. L'eccezione è scritta negli argomenti del lock delle righe d'ordine (oggi
`CONFERMATO` e `PARZIALMENTE_EVASO`). Questa check la legge da lì, attraverso
`script.fn_doc_colonna_modificabile`, e non ne tiene una copia: se domani l'eccezione vale
in uno stato in più, check e lock cambiano insieme.

| Risposta | Quando |
| --- | --- |
| nessuna (`NULL`) | l'ordine non c'è, o chi chiede non lo vede |
| `[]` | il lock lascia cambiare la sola data. Anche in bozza, dove si modifica la riga intera |
| un motivo | lo stato non lo ammette più |

Il motivo ha la forma delle altre check:

| Campo | Valore |
| --- | --- |
| `codice` | `E_RIGA_DOC_NON_BOZZA`, quello che il lock solleva |
| `reason` | `STATO_NON_AMMETTE` |
| `reason_key` | `vendite.ordini.data_consegna_confermata_reason.stato_non_ammette` |
| `dettaglio` | lo stato |
| `valori` | i valori della frase del lock: il documento, lo stato, il verbo |

⚠️ In bozza la check dice `[]`, ed è vero: in bozza il lock lascia cambiare tutto. Che in
bozza il gesto giusto sia modificare la riga, e non il verbo dedicato, lo dice la
capability dell'ordine, col motivo `ORDINE_IN_BOZZA`.
