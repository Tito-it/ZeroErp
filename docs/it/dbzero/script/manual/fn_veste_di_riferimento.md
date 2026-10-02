## 📘 Documentazione Concettuale – Funzione `script.fn_veste_di_riferimento()`

> 👀 **Vedi anche**
>
> [script.fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile) ·
> [script.fn_get_operatore_detail](/dbzero/script/funzioni/fn_get_operatore_detail)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-1)

**Fra le vesti di un tipo che una credenziale porta, quella che si guarda.** Gli indici
unici di `identita_digitali` valgono solo `WHERE attivo`: una credenziale ha al più **una**
veste accesa di un tipo, e quante si vuole spente. La veste di riferimento è l'**accesa**;
se nessuna lo è, la **spenta più recente** (`data_insert`, poi `id`). Ritorna l'id, `NULL`
se la credenziale non ha vesti di quel tipo.

⭐ **Perché è un building block.** La regola stava scritta dentro
[fn_get_operatore_detail](/dbzero/script/funzioni/fn_get_operatore_detail) (dal 2026-09-25).
Con R-DB-1 la veste operatore spenta resta `OPERATORE`, e
[fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile) — che cercava la veste
con un JOIN nudo — avrebbe potuto prendere la spenta accanto all'accesa e rifiutare il
login. Seconda occorrenza: la regola si è estratta, e la copia si è ritirata nello stesso
giro.

### Test

`db/pgtap/anagrafiche/test-veste-operatore-spenta-v1.sql` (casi 9, 10).
