## 📘 Documentazione Concettuale – Funzione `script.log()`

> 📄 **È una façade: non fa il lavoro, lo delega.**
> Il motore è [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only), dove sta
> la documentazione del meccanismo di log.

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Una **façade** è una funzione che offre una firma più comoda davanti a un'altra: riempie i
parametri che al chiamante non interessano e gira la chiamata. Qui il corpo è una riga sola,
e il `COMMENT` della funzione usa esattamente questa parola.


`script.log` è la **forma completa a 6 argomenti**, con il `VARIADIC` per i valori che
`format()` sostituirà nei segnaposto del messaggio:

```sql
SELECT script.fn_log_error_only($1,$2,$3,$4,$5, VARIADIC $6);
```

---

### 🔴 Nessuno la chiama

Misurato il 2026-08-21 sui corpi PL/pgSQL del database vivo:

| Forma | Chiamanti |
|---|---:|
| `script.fn_log_error_only` (il motore) | **5** |
| `script.fn_log` (4 argomenti) | **0** |
| `script.log` (6 argomenti) | **0** |

Chi logga chiama **direttamente il motore**, oppure passa da
[script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — che è
l'altra strada, quella che logga *e* solleva.

Sono quindi comodità costruite e mai adottate. Non fanno danno: costano una riga di SQL e
nessuna esecuzione. Ma **documentarle come «il modo per loggare» sarebbe fuorviante**, perché
il modo reale è un altro — ed è la ragione per cui questa pagina rimanda al motore invece di
descrivere il meccanismo una seconda volta.

⚠️ Prima di eliminarle: non essendo chiamate da nessun corpo PL/pgSQL, resta da verificare che
non le usi il backend o uno script.

---

{% include-markdown "signature-core.md" %}
