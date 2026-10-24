## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_lotto`

> 👀 **Vedi anche**
>
> • [vendite.fn_create_fatturazione_lotto](/dbzero/vendite/funzioni/fn_create_fatturazione_lotto) — la madre da cui nasce il lotto
>
> • [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
>
> • [dbops.fn_pgtap_crea_commessa](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa) — la commessa da mettere in fatturazione
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-modello-documento-vendita` (R-4)

---
### 🎯 Scopo Principale

(rev 2026-10-24)

**Un lotto di fatturazione dell'azienda di chi agisce, in una chiamata sola.** Nasce
dalla **madre del dominio**, arriva allo stato che il test chiede e, se serve, porta
l'esito che «trattiene» un gruppo di documenti.

```sql
CREATE TEMP TABLE tmp_l AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('pull');

-- il lotto «altrui» che trattiene un gruppo del test
SELECT * FROM dbops.fn_pgtap_crea_lotto(
           'altrui', 'DRAFT', (SELECT billing_account_id FROM tmp_cliente),
           p_gruppo_key_trattenuto => (SELECT gruppo_key FROM tmp_gruppo));
```

---
### 🧭 Perché esiste

Cinque pgTAP scrivevano il lotto a mano, con un codice inventato e lo stato scritto
direttamente, tre già emessi o definitivi: un lotto che nessuna funzione del dominio
produce. E ognuno riscriveva a mano la riga dell'esito che trattiene un gruppo. Era la
stessa strada in cinque copie: ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **La nascita** la fa `vendite.fn_create_fatturazione_lotto`: codice, marchio del giro
  (`lock_batch_id`) e stato di bozza li decide lei, come in produzione.
* **L'azienda e l'utility** sono quelle del cliente: quello del terzo parametro (verificato
  da [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo):
  uno di un'altra azienda solleva) o uno nuovo del mondo.
* **Il lotto è dell'azienda**, non del cliente: il conto di fatturazione resta vuoto, come
  in un giro massivo. Con `p_del_cliente => true` il lotto è anche del cliente.
* **Lo stato** si raggiunge per la matrice dei passaggi del lotto, sul lotto ancora vuoto.
* **Il tipo documento** è quello chiesto, o il primo attivo che ha un registro (la madre
  lo pretende). **La competenza** è quella chiesta, o il mese della data operativa.
* **Il gruppo trattenuto** (`p_gruppo_key_trattenuto`): l'esito in errore
  (`E_PULL_COMMESSA`) che tiene quel gruppo dentro il lotto, la forma dei test del pull.

---
### 🚫 Cosa NON scrive

**Le fatture e il loro aggancio al lotto**: sono il caso del test. E un lotto con fatture
si muove col verbo del dominio `vendite.fn_sync_lotto_fatture_stato`, non da qui.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-lotto-v1.sql` (9 casi): firma; lotto in bozza
dell'azienda del mondo, senza cliente; codice e marchio dalla madre; tipo documento con un
registro; il cliente di un'altra fixture; il lotto legato al cliente; DEFINITIVA per la
matrice; l'esito del gruppo trattenuto; uno stato che non esiste rifiutato.
