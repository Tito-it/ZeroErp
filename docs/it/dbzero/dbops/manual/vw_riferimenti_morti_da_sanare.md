## 📘 Documentazione Concettuale – Vista `dbops.vw_riferimenti_morti_da_sanare`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti)
>
Approfondimento tabelle:
> • [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni)
>
Approfondimento viste:
> • [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**La lista di lavoro**: i riferimenti morti `REALE`/`ORFANA` che **non** sono coperti dal
registro del debito. Deve essere **vuota**, ed è la condizione che il guardrail verifica.

È la differenza fra due insiemi:

```
riferimenti morti veri  −  esenzioni registrate  =  da sanare
```

Al 2026-08-21: **zero righe**.

---

### Che cosa filtra, e perché così

**Sulle classi**: solo `REALE` e `ORFANA`. Le tre classi `FP_*` sono falsi positivi già
giudicati e restano fuori — ma restano **visibili** interrogando direttamente la funzione, che
le restituisce tutte. Sono classificate, non nascoste.

**Sulle esenzioni**: un `NOT EXISTS` che confronta schema, funzione e l'esito con l'`esito_like`
del registro. Il confronto è per **pattern**, non per uguaglianza: il messaggio di
`plpgsql_check` contiene numeri di riga che cambiano a ogni ritocco della funzione, e un
confronto esatto renderebbe l'esenzione stantia al primo tocco.

---

### ⚠️ Una lista vuota ha due cause, e vanno distinte

Vuota può significare **«nessun difetto»** oppure **«tutti i difetti sono stati esentati»**. Le
due cose sono diversissime, e questa vista da sola non le separa.

⭐ È per questo che il presidio ha **due** viste. La gemella
`vw_riferimenti_morti_rientrati` guarda il registro dal verso opposto e segnala le esenzioni
che non corrispondono più a nulla. Interrogare solo questa, e vederla vuota, è la strada per
un registro che si gonfia mentre il guardrail resta verde.

Entrambe devono essere vuote **insieme**.

---

### ⚠️ Costa quanto la funzione che la alimenta

Non è una vista leggera: ogni interrogazione fa girare `plpgsql_check_function` su tutte le
funzioni del database. Va usata in un guardrail o in un test, mai in un percorso frequente.

Comporla con la gemella in una query sola è **corretto** (verificato: le chiamate non
interferiscono), ma esegue il controllo **due volte**.

---

### Scope

`WITH (security_invoker = on)`. Legge i cataloghi di sistema attraverso la funzione: il
perimetro è quello dei privilegi PostgreSQL, non della RLS.

---

{% include-markdown "signature-core.md" %}
