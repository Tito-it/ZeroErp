## 📘 Documentazione Concettuale – Funzione `dbops.fn_check_funzioni_riferimenti_morti()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni)
>
Approfondimento viste:
> • [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare)
> • [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Trova i **riferimenti morti** nelle funzioni PL/pgSQL: colonne rinominate o eliminate, tabelle
che non esistono più, campi citati da un corpo che non compilerebbe mai.

Il problema che risolve è specifico di PL/pgSQL: il corpo di una funzione **non viene
validato alla creazione**. Una `CREATE OR REPLACE FUNCTION` che nomina una colonna inesistente
riesce senza un fiato, e il difetto si manifesta solo quando quel ramo viene percorso — spesso
il ramo d'errore, cioè esattamente quando servirebbe funzionare.

Si appoggia a `plpgsql_check_function`, e ne interpreta l'output.

---

### ⭐ Le trigger function si validano contro **ogni tabella** su cui sono agganciate

È il punto meno ovvio. `NEW` e `OLD` non hanno un tipo finché non si sa su quale tabella il
trigger è montato: la stessa trigger function agganciata a due tabelle va quindi controllata
**due volte**, una per tabella.

Da qui la classe **`ORFANA`**: una trigger function agganciata a **zero** tabelle non è
validabile affatto. Non è un riferimento morto — è codice che nessuno può verificare, ed è
segnalato come tale.

---

### ⚠️ Le classi: solo due su cinque sono difetti

| Classe | Significato |
|---|---|
| `REALE` | riferimento morto vero, da sanare |
| `ORFANA` | trigger function non agganciata: non validabile |
| `FP_TRANSITION_TABLE` | falso positivo — tabelle di transizione (`REFERENCING`) |
| `FP_RAMO_ALTRA_TABELLA` | falso positivo — ramo che vale per un'altra tabella agganciata |
| `FP_SQL_DINAMICO` | falso positivo — `EXECUTE` con SQL costruito |

⭐ **I falsi positivi sono classificati, non nascosti.** Un filtro li avrebbe fatti sparire
anche quando smettono di essere falsi positivi; una classe li tiene visibili e dice *perché*
si ignorano. Le due viste a valle filtrano su `REALE`/`ORFANA`, ma la funzione restituisce
tutto.

Misura al 2026-08-21: 14 `FP_RAMO_ALTRA_TABELLA`, 5 `FP_TRANSITION_TABLE`, 1 `FP_SQL_DINAMICO`,
**1 `ORFANA`**, zero `REALE`.

---

### Perimetro

Solo funzioni `plpgsql`, esclusi `pg_catalog`, `information_schema`, gli schemi `pg_*` e
**tutto ciò che appartiene a un'estensione** (PostGIS, topology, pgAgent): non è codice
mantenuto qui, e segnalarlo sarebbe rumore permanente.

---

### ⚠️ È costosa, e usa una temp table condivisa

Gira `plpgsql_check_function` su ogni funzione del database, moltiplicata per le tabelle
agganciate: **non è una query da mettere in un percorso frequente**. Va bene in un guardrail o
in un test, non in una vista consumata da un endpoint.

Internamente usa una temp table `tmp_raw` (`ON COMMIT DROP`, creata con `IF NOT EXISTS` e
svuotata in testa). Chiamandola due volte nella stessa sessione compare la notifica «la
relazione tmp_raw esiste già»: è innocua.

⭐ **Comporre più chiamate nella stessa query è sicuro** — verificato il 2026-08-21: due
`SELECT count(*) FROM dbops.fn_check_funzioni_riferimenti_morti()` nella stessa istruzione
restituiscono entrambe 21 righe. PostgreSQL materializza la set-returning function prima di
usarne il risultato, quindi le chiamate non si pestano sullo stato d'appoggio nonostante il
`DELETE` in testa. Vale anche per le due viste che la richiamano.

⚠️ Resta però vero il costo: comporle significa **eseguire il controllo due volte**.

---

### Consumatori

`db/pgtap/dbops/test-riferimenti-morti-v1.sql` e
`scripts/sql/guardrail_riferimenti_morti.sql`.

⚠️ Il guardrail gira **dopo** `manage.py migrate`, non prima: le funzioni devono essere già
nel database perché ci sia qualcosa da controllare.

---

{% include-markdown "signature-core.md" %}
