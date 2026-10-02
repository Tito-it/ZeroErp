## 📘 Documentazione Concettuale – Funzione `script.fn_categoria_accesso()`

> 👀 **Vedi anche**
>
> [script.fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema) ·
> [anagrafiche.vw_accessi_altri](/dbzero/anagrafiche/views/vw_accessi_altri) ·
> [anagrafiche.vw_accessi_sistema](/dbzero/anagrafiche/views/vw_accessi_sistema)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A1)

**In quale tab dell'area «Accessi» sta una credenziale.** I tre tab — «Operatori», «Altri
accessi», «Di sistema» — devono essere una **partizione**: ogni credenziale in uno solo,
nessuna in nessuno. Una funzione che restituisce un valore solo la rende vera per
costruzione; le liste e il backend chiedono a lei invece di avere ciascuno un predicato
suo.

| Categoria | Quando |
| --- | --- |
| `SISTEMA` | almeno una veste di sistema ([fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema)) |
| `OPERATORE` | altrimenti, almeno una veste `OPERATORE` |
| `ALTRO` | tutte le altre, comprese le credenziali **senza alcuna veste** |

⭐ **Contano anche le vesti spente**: una persona disattivata resta nel suo tab, non scivola
in un altro perché si è spenta.

### La precedenza fra SISTEMA e OPERATORE

Non sceglie fra due casi del modello: una credenziale insieme persona e macchina il modello
**non la ammette** (una password per tutte le porte; bloccare la persona fermerebbe il
processo), e la rifiuta il guard
[trgfn_identita_digitali_guard_natura_credenziale](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_natura_credenziale).
Per una riga nata prima del guard vince `SISTEMA`, perché il tab «Di sistema» è in sola
lettura; e la riga la segnala [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare).

### Forma

`BEGIN ATOMIC`, `STABLE`: legge solo `anagrafiche.identita_digitali`. Un id senza vesti (o
assente) è `ALTRO`, come in una lista: nessun guard sul parametro.

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 2, 3, 7, 15).
