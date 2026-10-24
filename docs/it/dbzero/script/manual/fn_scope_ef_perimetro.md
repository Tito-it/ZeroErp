## 📘 Documentazione Concettuale – Funzione `script.fn_scope_ef_perimetro(...)`

> 👀 **Vedi anche**
>
> [fn_get_emittenti_scope_pk_ids](fn_get_emittenti_scope_pk_ids.md) — il perimetro, come insieme
> [fn_check_user_emittente_scope](fn_check_user_emittente_scope.md) — la domanda su un emittente
> [fn_scope_ef_whitelist](fn_scope_ef_whitelist.md) — la forma per riga che sostituisce nelle policy
> [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
> Brief: `brief-db-plancache-funzioni-con-query-incorporate` §5quinquies (D-3b-2, D-3b-2c)

---

### 🎯 Scopo Principale

(nata il 2026-10-18; firma attuale da `20261018-24`)

**L'emittente della riga sta nel perimetro dell'operatore?** È la funzione di
scope delle policy ef_whitelist (§10.3 delle linee guida: la policy chiama una
`fn_scope_*`). La differenza con [`fn_scope_ef_whitelist`](fn_scope_ef_whitelist.md)
è **chi calcola il perimetro**:

* `fn_scope_ef_whitelist(utente, emittente)` lo calcola **lei**, e in una
  policy lo ricalcola a ogni riga: super admin, veste utilizzabile, giorno
  operativo, whitelist. Nessuna di queste cose dipende dalla riga;
* `fn_scope_ef_perimetro(perimetro, emittente)` lo **riceve** già calcolato, e
  confronta solo l'emittente della riga.

---

### Come la chiama una policy

```sql
script.fn_scope_ef_perimetro(
    (SELECT script.fn_get_emittenti_scope_pk_ids(<utente>)),  -- il perimetro, una volta
    emittente_fiscale_id)                                      -- della riga
```

La sottoquery **non dipende dalla riga**: PostgreSQL la valuta una volta per
istruzione (nel piano compare come `InitPlan`). Per riga resta la chiamata a
questa funzione, pura: ~1,5 µs (contro 0,02-0,08 ms della canonica per riga).

```text
Filter: (... AND fn_scope_ef_perimetro((InitPlan 1).col1, emittente_fiscale_id))
```

---

### ⛔ Una sottoquery, non due

La prima versione (`20261018-16`, tre argomenti) passava «tutti» a parte, in
una seconda sottoquery, per farsi **incorporare** dal pianificatore (con un
parametro usato una volta sola e argomenti-sottoquery, l'incorporazione
regge). Il prezzo: il perimetro si calcolava **due volte per istruzione**, e le
letture di una riga sola — la maggior parte, nei verbi e nei trigger — pagavano
il doppio. Misura (2026-10-18): lettura per chiave di `vendite.preventivi` sotto
policy 0,24-0,27 ms con due sottoquery, 0,084-0,088 con una. Su 20.000 righe la
forma incorporata vinceva (2-3 ms contro 26-32), ma entrambe stanno 20-40 volte
sotto la canonica per riga. Decisione D-3b-2c: **una sottoquery**.

Qui il perimetro serve due volte (`IS NULL` e `= ANY`), quindi la funzione non si
incorpora: è voluto, e il presidio lo sa.

---

### Parametri

| Parametro | Tipo | Significato |
| --- | --- | --- |
| `p_perimetro` | `bigint[]` | gli emittenti visibili: `NULL` = tutti, `'{}'` = nessuno (la convenzione di `_pk_ids`) |
| `p_emittente_fiscale_id` | `anagrafiche.emittenti_fiscali.id%TYPE` | l'emittente della riga |

Ritorna `boolean`: `p_perimetro IS NULL OR coalesce(emittente = ANY (p_perimetro), false)`.
Emittente `NULL` → `false`, salvo perimetro «tutti». `IMMUTABLE`, `LANGUAGE sql`,
`COST` di default (è il prezzo vero: misura nell'elenco delle economiche di
`script/test-policy-funzioni-cost-v1`).

---

### Chi la usa

* le 13 policy ef_whitelist dirette scritte a mano (`20261018-26`);
* le policy di lettura dello storico, generate da `dbops.fn_storico_arma_scope`
  (`20261018-27`, riallineo `20261018-28`);
* la canonica [`fn_check_user_emittente_scope`](fn_check_user_emittente_scope.md),
  per la domanda su un emittente (`20261018-25`).

La firma a tre argomenti è ritirata (`20261018-29`).

⚠️ Una policy nuova con la colonna emittente si scrive **in questa forma**.
Presidio: `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (nessuna
policy con `fn_scope_ef_whitelist(`, il perimetro in **una** sottoquery, e sul
**piano** di ogni tabella il perimetro in `InitPlan` e nessuna funzione della
catena nel `Filter`).
