## 📘 Documentazione Concettuale – Funzione `script.fn_prima_chiave_estranea()`

> 👀 **Vedi anche**
>
> [script.fn_scrivi_riga_da_jsonb](/dbzero/script/manual/fn_scrivi_riga_da_jsonb)

### 🎯 Scopo
(17-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1)

**La prima chiave che un verbo non accetta.** Dato un payload JSON e l'elenco
delle chiavi ammesse, restituisce la prima chiave (in ordine alfabetico) fuori
elenco, oppure `NULL`.

È la regola «un campo che non si scrive si rifiuta col suo nome, non si scarta
in silenzio». Il codice d'errore lo sceglie il verbo: il pannello di
configurazione usa `E_PANNELLO_CAMPO_NON_AMMESSO`, i verbi di creazione
`E_CAMPO_NON_AMMESSO`.

Pura e `IMMUTABLE`. Un elenco `NULL` non ammette niente.

### Test

`db/pgtap/script/test-fn-scrivi-riga-da-jsonb-v1.sql` (test 15–18).

---

{% include-markdown "signature-core.md" %}
