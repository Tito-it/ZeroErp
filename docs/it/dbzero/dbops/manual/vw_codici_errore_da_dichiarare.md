## 📘 Documentazione Concettuale – Vista `dbops.vw_codici_errore_da_dichiarare`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy)
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> • [vendite.trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only)

---
### 🎯 Scopo Principale

(rev 2026-10-27)

> ⛔ **Il numero di questa vista NON è il debito.** È la **misura**: conta ogni codice `E_*` che un corpo PL/pgSQL vivo può nominare, e cresce a ogni regola nuova e legittima. Il debito è il suo registro, [`dbops.codici_errore_senza_policy`](/dbzero/dbops/tabelle/codici_errore_senza_policy), **a zero dal 2026-08-07** e tenuto lì dal cancello `test_error_codes_db_policy_guardrail`. Il catalogo dei presidi la classifica `CANCELLO`, non registro. Contarla come registro di debito è un errore già fatto tre volte (08-09, 20-09, 23-10).

**Misura canonica del «terzo lato»** del presidio sui codici errore: quali codici `E_*` il
codice PL/pgSQL vivo può effettivamente nominare.

I primi due lati sono dichiarativi — il codice esiste in catalogo, la frase esiste in
`messaggi_errore`. Il terzo lato è diverso: guarda **i corpi delle funzioni**, non i cataloghi.
Risponde a *«questo codice qualcuno lo solleva davvero?»*, che è l'unica domanda che collega
il catalogo alla realtà.

Per ogni codice trovato espone:

* **`da_trigger`** — la funzione che lo nomina è agganciata a un trigger, quindi il codice sta
  **sul percorso di una richiesta**. È il criterio di priorità: si bonifica prima ciò che
  l'utente può incontrare;
* **`n_funzioni`** e **`funzioni`** — dove compare.

---

### ⭐ È volutamente **larga**, e la ragione è una scelta fra due errori

La vista raccoglie **ogni letterale** `'E_...'` in un corpo `plpgsql`, non solo quelli dentro
una chiamata a `fn_log_and_raise_error`.

Restringere sarebbe stato più preciso e avrebbe perso i codici che arrivano **da
espressione** — per esempio `v_motivi -> 0 ->> 'codice'`, il pattern dei guard che delegano il
verdetto a una funzione di check: 19 codici, quattro dei quali senza policy.

Fra i due errori possibili si è scelto quello che **si corregge guardando**: un falso positivo
si vede e si scarta, un codice mancante non si vede affatto.

I commenti sono esclusi (`regexp_replace` toglie il `--` fino a fine riga), così un codice
citato in una nota non conta come sollevato.

---

### ⚠️ Che cosa **non** vede

Due punti ciechi dichiarati, ed entrambi contano:

1. **Codici costruiti per concatenazione.** Un codice assemblato a runtime non è un letterale
   e sfugge alla regexp.
2. **I `RAISE EXCEPTION` diretti** che non passano dall'helper. Non hanno un codice `E_*` da
   trovare — semplicemente non esistono come codice.

⭐ Il secondo caso non è teorico: `vendite.trgfn_event_log_append_only` solleva con un
`RAISE EXCEPTION` diretto. Il suo rifiuto **non è registrato in nessun catalogo, non compare
qui, e non finisce in `error_log`**. È invisibile a tutte e tre le misure del presidio.

---

### Come si legge

Il conteggio da solo non dice nulla: va incrociato con `config.codici_errore` (il codice è
dichiarato?) e con `dbops.codici_errore_senza_policy` (il backend sa che stato HTTP dargli?).
Un codice presente qui e assente di là è un difetto; presente in entrambi è debito registrato.

---

### Scope

`WITH (security_invoker = true)`. Legge i cataloghi di sistema, quindi il perimetro è quello
dei privilegi PostgreSQL, non della RLS. Da ri-specificare a ogni `CREATE OR REPLACE VIEW`.

---

{% include-markdown "signature-core.md" %}
