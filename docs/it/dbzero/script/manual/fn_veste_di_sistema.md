## 📘 Documentazione Concettuale – Funzione `script.fn_veste_di_sistema()`

> 👀 **Vedi anche**
>
> [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) ·
> [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A1)

**Una veste è di una macchina o di una persona?** `true` se la veste è `API_CLIENT` (un
sistema terzo, per definizione del tipo) oppure porta il flag `tecnica` (l'utente tecnico
di un processo automatico). Tutto il resto è una persona: il complemento, non una seconda
lista.

⭐ **Perché è una funzione per una riga.** La regola la leggono in tre, e tre copie
divergerebbero alla prima veste di sistema nuova:

* [script.fn_categoria_accesso](/dbzero/script/funzioni/fn_categoria_accesso) — il tab
  dell'area «Accessi» in cui sta una credenziale;
* [trgfn_identita_digitali_guard_natura_credenziale](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_natura_credenziale)
  — persona e macchina non stanno sulla stessa credenziale;
* [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare) — il presidio.

### Forma

Pura sui **valori** (`ruolo_applicativo`, `tecnica`), `IMMUTABLE`, `BEGIN ATOMIC`: si usa
dentro un trigger `BEFORE ROW` sui valori `NEW` e dentro un aggregato, senza rileggere la
riga.

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (caso 1).
