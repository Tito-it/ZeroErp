## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_contratto`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui nasce il contratto
>
> • [vendite.fn_create_contratto](/dbzero/vendite/funzioni/fn_create_contratto) — la madre di produzione da cui nasce
>
> • [dbops.fn_pgtap_crea_fattura](/dbzero/dbops/funzioni/fn_pgtap_crea_fattura) — il builder gemello della fattura
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test)

---
### 🎯 Scopo Principale

(rev 2026-10-21, richiesta del backend R-1; stati: decisione di Tid D-2; rev 2026-10-24: il figlio di un'offerta)

**Un contratto del mondo, in una chiamata sola**: l'azienda con il suo operatore, il cliente e la
testata nello stato scelto. Torna tutte le chiavi. Serve ai pgTAP e agli smoke Python, che prima
pescavano «il primo contratto che c'è»: su un database nuovo non ce n'è nessuno, e su quello di
sviluppo era il contratto di un'azienda a caso.

```sql
CREATE TEMP TABLE tmp_k AS
SELECT * FROM dbops.fn_pgtap_crea_contratto('atto', 'ATTIVO');
```

---
### 🧭 Nasce dalla madre, come in produzione

Diversamente dalla fattura di prova, che il builder scrive direttamente, il contratto ha una
funzione di produzione che lo crea: `vendite.fn_create_contratto` (numero, testata in bozza,
indirizzo di default). Il builder la chiama, dichiarando l'azienda: quella di chi agisce, a cui
il cliente è legato.

---
### 🔁 Gli stati, per la strada dell'applicazione

| Stato | Come ci arriva |
| --- | --- |
| `DRAFT` (default) | è lo stato di nascita; nessun listino |
| `ATTIVO` | il builder gli dà un **listino** dell'azienda di chi agisce (`dbops.fn_pgtap_crea_listino`) e lo attiva: il cambio di stato passa dagli stessi controlli dell'applicazione |
| `ANNULLATO` | dal verbo di annullo, `vendite.fn_annulla_contratto` |

* ⚠️ **ATTIVO vuole un listino**: un contratto si attiva su un listino con una versione attiva,
  o con almeno una riga aggiunta con un prezzo. Le righe sono il caso del test, quindi il
  builder dà il listino.
* ⚠️ **Due contratti attivi dello stesso cliente**, con date che si sovrappongono, li rifiuta il
  modello: il secondo contratto attivo sullo stesso cliente lo costruisce il test, con le sue date.
* ⛔ **CESSATO non si costruisce**, e nemmeno un altro codice: un contratto cessato vuole la data
  di fine e passa da attivo con la regola della cessazione. È il caso del test. Il builder lo
  dice prima di scrivere.

---
### 🔁 Il terzo parametro: il contratto di un cliente già costruito

Senza, ogni chiamata costruisce un cliente nuovo. Con il conto di fatturazione di un cliente
costruito prima, il contratto nasce su quel cliente. È il caso dello smoke del backend: il
contratto citato da una riga di commessa deve essere **del conto della sua commessa**
(`vendite.trgfn_attivita_guard_contratto`), quindi si chiede sul conto della commessa.

```sql
SELECT * FROM dbops.fn_pgtap_crea_contratto(
           'atto', 'ATTIVO', (SELECT billing_account_id FROM tmp_commessa));
```

⚠️ Il conto viene **verificato**: uno di un'altra azienda solleva subito, invece di produrre una
testata che un controllo rifiuterebbe più avanti con un messaggio che non nomina la fixture. Il
controllo è il building block [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo),
lo stesso di fattura e ordine.

---
### 🔁 Periodo, data e listino del test

(rev 2026-10-24, R-2) Dal quinto all'ottavo parametro: `valido_dal`, `valido_al`, la data
del contratto e il listino. Passano alla madre, che li accetta già: il contratto attivo
nasce col periodo e il listino che il test vuole, senza ritocchi in bozza. Vuoti: quelli
che decide la madre, e un contratto attivo senza listino ne riceve uno del mondo.

```sql
SELECT * FROM dbops.fn_pgtap_crea_contratto(
           'atto', 'ATTIVO', (SELECT billing_account_id FROM tmp_cliente), NULL,
           DATE '2022-01-01', DATE '2022-12-31', DATE '2022-01-15',
           (SELECT listino_id FROM tmp_listino));
```

⚠️ Con il figlio di un'offerta periodo e listino li decide la push: chiederli insieme
solleva.

---
### 🔁 Il quarto parametro: il figlio di un'offerta

In produzione un contratto **figlio di un'offerta** nasce solo dalla push
`vendite.fn_push_offerta_a_contratto`, che copia dall'offerta listino, indirizzi, righe e
utility e ne controlla lo stato. Con l'offerta come quarto parametro il builder fa nascere il
contratto da lì, sul cliente dell'offerta.

```sql
SELECT * FROM dbops.fn_pgtap_crea_contratto(
           'figlio', 'ANNULLATO', NULL, (SELECT offerta_id FROM tmp_offerta));
```

* L'offerta deve essere **accettata**: portarla lì è il caso del test, e se non lo è la push
  lo dice.
* Il cliente è quello dell'offerta: un conto di fatturazione diverso come terzo parametro
  solleva.
* **Annullare un figlio** riapre un legame (l'offerta da cui nasce), e l'annullo vuole la
  conferma di chi l'ha visto. Il builder la dà come il backend: conta i legami da
  `vendite.fn_documento_legami` e li dichiara al verbo d'annullo. Un figlio annullato non
  consuma l'offerta: dalla stessa offerta ne può nascere un altro.

---
### 🚫 Cosa NON scrive

Righe, eccezioni e scheda di fornitura: sono il caso del test (un figlio le eredita
dall'offerta, dalla push).

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-contratto-v1.sql` (14 casi): firma, contratto attivo dal
nulla con il listino dell'azienda giusta, bozza e annullato sullo stesso cliente, cliente nuovo
nella stessa azienda, conto di un'altra azienda rifiutato, CESSATO rifiutato; il figlio di
un'offerta annullato col legame dichiarato, un secondo figlio attivo della stessa offerta col
suo listino, un conto diverso da quello dell'offerta rifiutato; il contratto attivo col
periodo, la data e il listino del test; periodo o listino insieme all'offerta rifiutati.
