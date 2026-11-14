## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ordini_guard_transizione()`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini)
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
> [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
>
Approfondimento funzioni:
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine)
> [`script.fn_check_ordine_annullabile`](/dbzero/script/funzioni/fn_check_ordine_annullabile) — Regola 3
> [`script.fn_check_ordine_confermabile`](/dbzero/script/funzioni/fn_check_ordine_confermabile) — Regola 4
> [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — Regola 5
>
Pattern correlato (domini gemelli):
> [vendite.trgfn_preventivi_guard_transizione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione)
> [vendite.trgfn_offerte_commerciali_guard_transizione](/dbzero/vendite/funzioni/trgfn_offerte_commerciali_guard_transizione)

### 🎯 Scopo Principale

La trigger function **`vendite.trgfn_ordini_guard_transizione()`** giudica ogni cambio di
stato dell'ordine di vendita. La monta il trigger `trg_ordini_a10_guard_transizione_upd`
(`BEFORE UPDATE OF stato_doc_ordine_id`), dopo la porta
(`trg_ordini_a05_stato_solo_dal_verbo_upd`): lo stato lo scrivono solo i verbi
dell'ordine, e qui si decide se il passaggio si può fare.

Il grafo lo legge dalla matrice `config.transizioni_stati_ordini`, e il **significato**
degli stati dal vocabolario `config.stati_doc_ordini`: lo stato iniziale (`iniziale`), lo
stato di emissione (`emissione`) e lo stato di annullo (`is_abortito`). Nessun codice di
stato è scritto nel corpo: i codici vanno solo nel contesto degli errori. Le regole sono
le stesse con cui [`script.fn_available_actions_ordine`](/dbzero/script/funzioni/fn_available_actions_ordine)
spegne i pulsanti, quindi il pulsante e il guard non possono dire cose diverse.

---

### Regole applicate

| # | Quando | Regola | Errore |
|---|--------|--------|--------|
| 1 | sempre | la coppia (partenza, destinazione) esiste attiva in `config.transizioni_stati_ordini` | `E_ORDINE_TRANSIZIONE_NON_AMMESSA` |
| 2 | dallo stato iniziale allo stato di emissione | l'ordine ha almeno una riga **attiva**; nessun vincolo su quantità e prezzo | `E_ORDINE_CONFERMA_SENZA_RIGHE` |
| 3 | verso lo stato di annullo | il primo motivo di `script.fn_check_ordine_annullabile` | primo motivo (oggi `E_ORD_ANNULLA_CON_DDT`) |
| 4 | verso lo stato di emissione, **da qualunque partenza** | il primo motivo di `script.fn_check_ordine_confermabile`: una riga attiva che porta un prezzo porta anche l'aliquota | primo motivo (`E_ORDINE_RIGA_IVA_MANCANTE`, `E_ORDINE_CONFERMA_SOLO_ONERI`) |
| 5 | dallo stato iniziale allo stato di emissione | il primo motivo di `script.fn_check_prezzi_autorizzati`: nessun componente BoM attivo col prezzo in attesa o rifiutato | `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` |

Col vocabolario di oggi lo stato iniziale è `DRAFT`, quello di emissione `CONFERMATO`,
quello di annullo `ANNULLATO`.

### Perché le regole 4 e 5 hanno perimetri diversi

La matrice fa **rientrare** l'ordine nello stato di emissione da `EVASO` e
`PARZIALMENTE_EVASO`, in automatico, quando l'evasione torna indietro (una bolla
annullata). Quel rientro non conferma niente di nuovo:

* la **Regola 5** (i prezzi) vale solo dallo stato iniziale. Un prezzo rimasto non
  autorizzato bloccherebbe il rientro, e con lui l'annullamento a valle;
* la **Regola 4** (l'aliquota) vale per ogni ingresso nello stato di emissione: protegge il
  riepilogo IVA, che non sa da dove si arriva.

---

### La matrice (seed)

| Da | A | Manuale |
|----|---|:-------:|
| DRAFT | CONFERMATO | sì (conferma) |
| DRAFT | ANNULLATO | sì (annulla) |
| CONFERMATO | ANNULLATO | sì (annulla) |
| CONFERMATO | PARZIALMENTE_EVASO, EVASO | no (evasione) |
| PARZIALMENTE_EVASO | CONFERMATO, EVASO | no (evasione) |
| EVASO | CONFERMATO, PARZIALMENTE_EVASO | no (evasione) |

I passaggi non manuali li scrive [`vendite.fn_ordine_proietta_stato_evasione`](/dbzero/vendite/funzioni/fn_ordine_proietta_stato_evasione),
il verbo di processo dell'ordine.

---

### Algoritmo

1. **No-op** se lo stato non cambia.
2. **Una lettura del vocabolario**: i due `codice_interno` (per il contesto), `iniziale`
   della partenza, `emissione` e `is_abortito` della destinazione.
3. **Regola 1**, poi le regole 2-5 nell'ordine della tabella. Ognuna solleva il **primo**
   motivo con `script.fn_raise_primo_motivo_se_presente`, che mette nel contesto l'elenco
   completo.
4. `RETURN NEW`.

---

### Codici errore

| Codice | id | Quando |
|--------|----|--------|
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | 470 | il passaggio non è nella matrice, o non è attivo |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | 471 | dallo stato iniziale allo stato di emissione, senza righe attive |
| `E_ORDINE_RIGA_IVA_MANCANTE` | 1013 | verso lo stato di emissione, una riga col prezzo senza aliquota |
| `E_DOC_PREZZO_PENDENTE` | 1119 | dallo stato iniziale allo stato di emissione, un componente col prezzo in attesa |
| `E_DOC_PREZZO_RIFIUTATO` | 1120 | dallo stato iniziale allo stato di emissione, un componente col prezzo rifiutato |

I motivi dell'annullo sono quelli di `script.fn_check_ordine_annullabile`.

---

### Test

* `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql`: i passaggi ammessi e negati, la
  riga attiva;
* `db/pgtap/vendite/test-ordini-guard-conferma-iva.sql`: l'aliquota (Regola 4);
* `db/pgtap/vendite/test-ordine-stati-dal-vocabolario-v1.sql`: le regole seguono le marche
  del vocabolario (con `emissione` spostata, la Regola 2 segue la marca).
