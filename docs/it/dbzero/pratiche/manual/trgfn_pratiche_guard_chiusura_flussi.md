## 📘 Documentazione Trigger Function – `pratiche.trgfn_pratiche_guard_chiusura_flussi`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_chiusura_pratica](fn_check_chiusura_pratica.md)
> [pratiche.trgfn_pratiche_guard_transizione](trgfn_pratiche_guard_transizione.md)

---
### 🎯 Scopo Principale
Guard di **chiusura pratica rispetto ai flussi obbligatori** (decisione D4): blocca la transizione a `CHIUSA` se esistono template `obbligatorio = true` non completati e **ancora percorribili**. Prima di questo guard la chiusura era governata solo dalla matrice transizioni: una pratica poteva chiudere con step obbligatori mai eseguiti.

Il **ramo morto** di un bivio (prerequisito esito-aware non piu' soddisfacibile per l'esito preso dal predecessore) **non blocca**: la pratica chiude regolarmente con rami obbligatori mai percorsi, purche' non percorribili.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_pratiche_a10_guard_chiusura_flussi_upd` | BEFORE | UPDATE OF `stato_id` | `pratiche.pratiche` |

Fase `_a10_`. Convive con `trg_pratiche_a10_guard_transizione_upd` (matrice transizioni): questo guard valida il *contenuto* della pratica, quello la *legalita'* della transizione.

---

### Regole

1. Scatta solo alla **transizione** di stato verso `CHIUSA` (altri stati passano: `ANNULLATA` resta libera — si annulla anche una pratica a meta').
2. Interroga `fn_check_chiusura_pratica(NEW.id)`: se esistono righe `bloccante = true`, solleva errore con l'elenco dei codici template.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI` (485) | Transizione a CHIUSA con flussi obbligatori non completati ancora percorribili. Placeholder: elenco codici template bloccanti |

---

### Note operative

* I tipi prestazione **senza** template obbligatori non sono interessati (il guard e' un no-op).
* La catena PREVENTIVI (tutti gli step `obbligatorio = true`) chiude solo a giro completo — comportamento voluto.
* Test: `db/pgtap/pratiche/test-bivi-condizionali.sql` (chiusura bloccata con obbligatorio percorribile; chiusura ammessa con ramo morto).
