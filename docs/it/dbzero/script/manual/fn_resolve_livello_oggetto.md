## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_livello_oggetto()`

> 👀 **Vedi anche**
>
> **La catena, scritta una volta:** [script.fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti)

---

### 🎯 Scopo Principale
(riscritta il 04-10-2026, brief-db-permessi-tetto-area)

Restituisce il livello (`TUTTO`, `LETTURA`, `BLOCCATO`) di un utente su un
oggetto (`app_label`, `model_name`). La chiamano il backend e
[fn_guard_livello](/dbzero/script/funzioni/fn_guard_livello).

Non contiene la regola: legge la riga dell'oggetto da
[fn_get_permessi_effettivi_oggetti](/dbzero/script/funzioni/fn_get_permessi_effettivi_oggetti),
dove è spiegato il **tetto d'area**: l'override sull'oggetto può solo
restringere il livello dell'area, mai allargarlo.

⚠️ Il quarto parametro (`p_area_schema_db`) **non si legge più**: l'area è
quella dell'oggetto, ricavata da
[fn_area_di_oggetto](/dbzero/script/funzioni/fn_area_di_oggetto). Resta nella
firma perché i chiamanti passano i parametri per posizione; se ritirarlo lo
decide Tid. Oggetto mancante → `BLOCCATO`.

{% include-markdown "signature-core.md" %}
