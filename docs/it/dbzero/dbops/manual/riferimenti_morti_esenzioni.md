## 📘 Documentazione Concettuale – Tabella `dbops.riferimenti_morti_esenzioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) — i difetti che il registro non copre
> * [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) — le voci che non coprono più niente
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — la misura
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si tiene un registro del debito

---

### 🎯 Scopo Principale

Il registro del debito sui riferimenti morti nelle funzioni PL/pgSQL: le voci `REALE` o `ORFANA`
note e motivate, che il presidio non deve segnalare di nuovo.

⚠️ **È un debito, non un elenco di eccezioni: deve calare.** La differenza decide come si legge una
riga in più: in un elenco di eccezioni è normale, in un registro di debito è un peggioramento.

---

### Le colonne, e perché `esito_like`

* **`schema_nome` + `funzione`** — chi è esentato.
* **`esito_like`** — ⭐ un **pattern** `LIKE`, non il testo esatto dell'errore. Il messaggio di
  `plpgsql_check` contiene numeri di riga e dettagli che cambiano a ogni ritocco della funzione: un
  confronto esatto renderebbe l'esenzione stantia al primo tocco. ⚠️ Il rovescio è un pattern troppo
  largo, che esenterebbe anche i difetti nuovi della stessa funzione: il database pretende almeno
  otto caratteri tolti i `%`, quindi un pattern generico è rifiutato.
* **`motivo`** — obbligatorio e lungo almeno quaranta caratteri: ogni voce è un giudizio a sé e va
  argomentato. È la differenza con il registro dei codici fuori convenzione, dove il debito è
  uniforme e il motivo non c'è.
* **`data_registrazione`** — l'orologio del debito, il giorno operativo dell'inserimento.

Una voce è unica per (schema, funzione, pattern).

---

### Il registro ha due guardiani

| Vista | Domanda |
| --- | --- |
| [vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare) | c'è un difetto **non** coperto dal registro? |
| [vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati) | c'è una voce che **non corrisponde più** a nessun difetto? |

⭐ La seconda è la parte che di solito manca a un registro di debito, ed è quella che gli impedisce
di gonfiarsi. Entrambe devono essere vuote. Il guardrail della CI fa le stesse due domande sulla
stessa misura, e prima ancora verifica che la misura ci sia stata.

---

### ⚠️ Un registro descrive una macchina alla volta

Una voce che documenta un caso che su questa macchina non può verificarsi non è documentazione: è
rumore che il presidio segnala come rientrato. Per questo l'esenzione legata a pgAgent non è un seed
fisso: una convergenza a ogni migrate la tiene **solo** dove pgAgent manca (in CI), e la toglie dove
pgAgent c'è.

---

### Come si aggiunge o si toglie una voce

Le voci entrano e escono con changeSet di dati, non con un CSV di mirror: si aggiunge una voce con
il suo motivo quando un difetto si decide di tenerlo, e si toglie quando la vista dei rientrati (o
il guardrail) la segnala.

---

### Test

* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — nessun difetto fuori registro, nessuna voce
  rientrata, ogni voce con un motivo; l'esenzione legata a pgAgent c'è se e solo se pgAgent manca su
  questa macchina.

---

### Note di migrazione

* 2026-08-04 — nasce con `brief-db-bonifica-riferimenti-morti` §5, con una voce.
* 2026-09-14 — l'esenzione pgAgent diventa una convergenza sulla presenza di pgAgent
  (`brief-db-un-destinatario-per-i-presidi` §14).
* 2026-09-15 — esce la voce della trigger function della sorgente tipizzata, rimontata su sei tabelle
  di magazzino.
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
