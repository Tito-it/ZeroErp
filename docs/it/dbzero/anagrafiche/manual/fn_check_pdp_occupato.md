## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_pdp_occupato`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i clienti e il loro periodo
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_sync_stato_pdp](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_stato_pdp) — chi la chiama, per lo stato del PDP
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — il periodo del cliente

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_pdp_occupato` risponde se, in un giorno dato, un cliente occupa il PDP: se c'è un cliente
su quel PDP il cui periodo contiene il giorno.

---

### ⭐ La misura è il periodo

«Occupato» vuol dire la stessa cosa del vincolo per cui un PDP ha un solo cliente alla volta
(`ex_clienti_no_overlap_stesso_pdp`): il periodo del cliente, dall'attivazione alla chiusura esclusa. Lo stato
del cliente non entra: un sospeso occupa, un chiuso smette di occupare dal giorno della chiusura, un annullato e
un cliente senza attivazione non hanno periodo e non occupano.

---

### Conta i clienti di tutte le aziende

La funzione è `SECURITY DEFINER`. La tabella dei clienti è in RLS, e un operatore vede solo i clienti delle sue
aziende; ma sullo stesso PDP, nel tempo, possono stare clienti di aziende diverse, e lo stato del PDP è uno
solo. Letta coi diritti di chi scrive, la domanda risponderebbe «libero» per un PDP occupato dal cliente di
un'altra azienda.

Risponde solo sì o no: non dice quale cliente, né di quale azienda.

---

### Chi la chiama

`anagrafiche.trgfn_clienti_sync_stato_pdp`, col giorno operativo, per portare il PDP fra disponibile e attivo.

---

### Test

Nessun pgTAP la prova direttamente; la attraversa `db/pgtap/script/test-fn-disdetta-cliente.sql`, col PDP che
torna disponibile dopo la disdetta.

---

### Note di migrazione

* 2026-10-14 — nasce con il riallineamento dello stato del PDP sul periodo dei clienti.

---

{% include-markdown "signature-core.md" %}
