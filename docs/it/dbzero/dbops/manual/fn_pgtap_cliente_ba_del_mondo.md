## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cliente_ba_del_mondo`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_fattura](/dbzero/dbops/funzioni/fn_pgtap_crea_fattura), [dbops.fn_pgtap_crea_contratto](/dbzero/dbops/funzioni/fn_pgtap_crea_contratto), [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — i tre builder che la usano
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test)

---
### 🎯 Scopo Principale

(rev 2026-10-22, regola del 2)

Il pezzo comune dei builder di documento che accettano **il cliente di un'altra fixture** (il
terzo parametro, un billing account): verifica che quel cliente sia dell'azienda di chi agisce
e ne torna le chiavi (BA, fornitura, soggetto_ruolo, utility).

* Se il billing account è legato a **un'altra azienda**, o a nessuna, **solleva subito**, e il
  messaggio nomina il builder che ha chiesto. Senza questo controllo la testata la rifiuterebbe
  un guard più avanti, con un messaggio che non nomina la fixture.
* Il legame si legge dalla tabella dei legami BA → emittente, che non ha la sicurezza per riga:
  la lettura vale anche come utente applicativo.

---
### 🧭 Perché esiste

Lo stesso controllo era scritto nel builder della fattura e in quello del contratto. Il terzo
consumatore, il builder dell'ordine col terzo parametro, l'ha fatto estrarre: le due copie sono
state ritirate nello stesso giro.

---
### 🧪 Il presidio

Lo provano i pgTAP dei tre builder (il caso del billing account di un'altra azienda):
`db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` (test 9),
`test-fn-pgtap-crea-contratto-v1.sql` (test 7).
