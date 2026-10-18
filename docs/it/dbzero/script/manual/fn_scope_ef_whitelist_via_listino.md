## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_whitelist_via_listino`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini](/dbzero/vendite/manual/listini)
> • [vendite.listini_versioni](/dbzero/vendite/manual/listini_versioni)
>
**Approfondimento funzioni:**
>
• [script.fn_scope_ef_whitelist_via_sr](/dbzero/script/manual/fn_scope_ef_whitelist_via_sr)
> • [script.fn_resolve_emittente_fiscale_id](/dbzero/script/manual/fn_resolve_emittente_fiscale_id)
>

### 🎯 Scopo Principale
(latest review 05-09-2026)

Risponde a una domanda sola: **questo operatore può vedere le versioni di questo
listino?**

`vendite.listini_versioni` non porta l'emittente — lo porta il listino padre. Questa
funzione fa quel salto, e poi **passa la palla** alla canonica.

---

### Firma

```sql
script.fn_scope_ef_whitelist_via_listino(
    p_auth_user_id anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE,
    p_listino_id   vendite.listini.id%TYPE
) RETURNS boolean
```

⚠️ **`%TYPE` in firma è una fotografia**, risolta al `CREATE`: la firma reale resta
`(integer, bigint)`, ed è quella che il `GRANT` e la policy agganciano. Serve a dire
**da dove viene** il tipo, non a inseguirlo.

---

### ⭐ Fa un salto e delega — non riscrive la regola

È l'unica cosa da capire:

| | |
| --- | --- |
| **questa funzione** | «quale emittente?» — un salto, dal listino |
| `fn_scope_ef_whitelist_via_sr` | «e questo utente ce l'ha in whitelist?» |

⛔ Copiare la seconda metà qui dentro avrebbe prodotto una **seconda scrittura della
stessa regola**, e due scritture prima o poi dissentono. È la stessa forma di
`fn_scope_ef_whitelist_via_fattura`, che serve le figlie della fattura.

---

### ⚠️ Fail-closed, e per costruzione

Un listino inesistente — o non visibile — risolve a soggetto-ruolo `NULL`, e la
canonica risponde `false` quando la whitelist è valorizzata.

⭐ E questo è **corretto, non fortunato**: se il padre non è visibile, la figlia non
deve esserlo. La domanda che la funzione pone in lettura è esattamente quella a cui
sta rispondendo.

---

### ⛔ Non è `SECURITY DEFINER`, e non deve esserlo

Gira dentro una **policy**, cioè in lettura, dove leggere filtrato è il comportamento
giusto.

⚠️ Il caso opposto — il **guard di scrittura**, che deve sapere di chi è una riga anche
quando non la vede — è coperto da
[fn_resolve_emittente_fiscale_id](/dbzero/script/manual/fn_resolve_emittente_fiscale_id)
col modo `listino`, che è `SECURITY DEFINER` apposta. Confonderli riaprirebbe il
fail-open chiuso il 2026-08-22 sul modo `fattura`: un guard che non trova l'emittente
lascia passare, cioè si spegne esattamente nel caso che esiste per coprire.

---

### `STABLE` e `LANGUAGE sql`, come le sorelle

È **inlineabile**, e una policy RLS la esegue una volta per riga: una `plpgsql` qui
costerebbe a ogni `SELECT`.

---

### ⚠️ La trappola che la accompagna: padre e figlia nella stessa istruzione

```sql
-- ⛔ Non funziona
WITH lst AS (INSERT INTO vendite.listini (...) RETURNING id),
     v   AS (INSERT INTO vendite.listini_versioni (listino_id, ...)
             SELECT id FROM lst RETURNING id)
SELECT ...;
```

La policy legge il listino con **lo snapshot dell'istruzione**, che non contiene la
riga appena scritta dalla CTE sorella. ⇒ Padre invisibile, perimetro `NULL`, scrittura
rifiutata.

**Due istruzioni separate**: il padre prima, la figlia poi.

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-residui-be.md`, DB-4.

---

### ⭐ rev 2026-10-18 — chiede l'emittente al risolutore, e non sta più nelle policy

ChangeSet `20261018-32`: l'emittente lo chiede a
[`fn_resolve_emittente_fiscale_id`](fn_resolve_emittente_fiscale_id.md) (modo
`listino`, `SECURITY DEFINER`) invece di leggere il padre sotto la sua RLS: la
strada documento → emittente è scritta una volta, e una chiamata non riesegue la
policy del padre. Stesse risposte. Resta per la domanda su **un** emittente
(verbi, guard, backend); le policy non la chiamano più (`20261018-33`): calcolano
il perimetro una volta per istruzione con
[`fn_scope_ef_perimetro`](fn_scope_ef_perimetro.md). Brief
`brief-db-plancache-funzioni-con-query-incorporate` §5quinquies (giro 1b).

{% include-markdown "signature-core.md" %}
