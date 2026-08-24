## 📘 Documentazione Concettuale – Tabella `dbops.riferimenti_morti_esenzioni`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
> • [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti)
>
Approfondimento viste:
> • [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare)
> • [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Registro del debito** sui riferimenti morti: le voci `REALE`/`ORFANA` note e motivate, che
il guardrail non deve segnalare di nuovo.

⚠️ **È un debito, non un elenco di eccezioni: deve calare.** La differenza non è
terminologica — decide come si legge una riga in più. In un elenco di eccezioni una riga nuova
è normale; in un registro di debito è un peggioramento.

Al 2026-08-21: **una** voce registrata.

---

### Le colonne, e perché `esito_like`

* **`schema_nome` + `funzione`** — chi è esentato;
* **`esito_like`** — ⭐ un **pattern `LIKE`**, non il testo esatto dell'errore. È la scelta
  che rende il registro utile: il messaggio di `plpgsql_check` contiene numeri di riga e
  dettagli che cambiano a ogni modifica della funzione. Un confronto esatto renderebbe
  l'esenzione stantia al primo ritocco, e il guardrail tornerebbe rosso su un difetto già
  giudicato.

  ⚠️ Il rovescio: un pattern **troppo largo** esenta anche difetti nuovi della stessa
  funzione. `%` da solo esenterebbe la funzione per sempre — che è precisamente ciò che un
  registro di debito non deve permettere;
* **`motivo`** — obbligatorio (`NOT NULL`). Qui c'è, a differenza di
  `messaggi_errore_codici_legacy`: là si registra un debito uniforme, qui ogni voce è un
  giudizio a sé e va argomentato;
* **`data_registrazione`** — l'orologio del debito.

---

### Il registro ha due guardiani, non uno

| Vista | Domanda |
|---|---|
| `vw_riferimenti_morti_da_sanare` | c'è un difetto **non** coperto dal registro? |
| `vw_riferimenti_morti_rientrati` | c'è una voce di registro che **non corrisponde più** a nessun difetto? |

⭐ La seconda è la parte che di solito manca a un registro di debito, ed è quella che gli
impedisce di gonfiarsi: senza, le esenzioni restano per sempre e nessuno sa più quali servano
davvero. Entrambe devono essere **vuote**.

Al 2026-08-21 lo sono.

---

### Consumatori

`db/pgtap/dbops/test-riferimenti-morti-v1.sql` e
`scripts/sql/guardrail_riferimenti_morti.sql`.

---

{% include-markdown "signature-core.md" %}
