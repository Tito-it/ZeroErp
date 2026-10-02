## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_guard_natura_credenziale()`

> 👀 **Vedi anche**
>
> [script.fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema) ·
> [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-be-fe-area-accessi`, R-DB-A1)

**Una credenziale è di una persona o di una macchina, non di tutte e due.** Tutte le vesti di
un `auth_user_id`, anche spente, devono avere la stessa natura secondo
[fn_veste_di_sistema](/dbzero/script/funzioni/fn_veste_di_sistema). Altrimenti
`E_CREDENZIALE_PERSONA_E_SISTEMA`, con lo username nella frase.

Perché il modello non la ammette:

* una credenziale è **una password per tutte le porte**: chi conosce quella di un processo
  sarebbe anche la persona, e viceversa;
* le azioni della credenziale (blocco, secondo fattore) valgono per tutte le sue vesti:
  bloccare la persona fermerebbe il processo all'insaputa del suo pannello.

Il caso reale è un'email che appartiene a un utente tecnico usata per invitare una persona:
rimedia chi compila, con un'altra email.

### Perimetro

* `BEFORE INSERT` e `UPDATE OF auth_user_id, ruolo_applicativo, tecnica`, fase `a10`
  (dopo `guard_coerenza` in ordine alfabetico: un tipo ritirato si rifiuta prima di
  chiedersene la natura).
* Le righe già scritte non le giudica, e due transazioni concorrenti che scrivessero le due
  nature sulla stessa credenziale passerebbero: le segnala il presidio
  [dbops.vw_credenziali_da_sanare](/dbzero/dbops/views/vw_credenziali_da_sanare).

### Test

`db/pgtap/anagrafiche/test-area-accessi-v1.sql` (casi 4-6, 15).
