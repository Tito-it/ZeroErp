## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cliente_del_builder`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) — l'azienda del contesto
>
> • [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo) — la verifica del billing account
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-modello-documento-vendita` (§4-octies)

---
### 🎯 Scopo Principale

(rev 2026-10-24)

**Il cliente su cui scrive un builder** (commessa, contratto, fattura, ordine, lotto).

* **Senza** conto di fatturazione: il mondo — azienda, operatore, contesto e un cliente nuovo.
* **Con** il conto di fatturazione di un'altra fixture: l'azienda di chi agisce e quel conto,
  verificato. **Nessun cliente nuovo.**

---
### 🧭 Perché esiste

I cinque builder ricopiavano lo stesso blocco: costruire il mondo, poi, se il test passava
il suo conto, verificarlo. Ma il mondo costruisce sempre un cliente: con il conto del test,
ogni chiamata lasciava un cliente in più che nessuno usava (sei in un test dei contratti, tre
in uno della fatturazione). Non rompeva niente, ma sporcava il mondo e le viste che contano i
clienti dell'azienda. Il blocco ora è una chiamata a questa funzione, e le cinque copie sono
ritirate.

---
### ⚠️ Col conto del test serve un contesto aperto

Prima, senza contesto, il mondo costruiva un'azienda nuova e la verifica del conto falliva
comunque, perché il conto era di un'altra. L'esito è lo stesso, ora con un messaggio che lo
dice.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-cliente-del-builder-v1.sql` (7 casi): senza contesto l'azienda
non c'è; senza conto, il mondo; l'azienda di chi agisce è quella del mondo; col conto del test
nessun cliente nuovo, nemmeno passando dai cinque builder; un conto di un'altra azienda
rifiutato.
