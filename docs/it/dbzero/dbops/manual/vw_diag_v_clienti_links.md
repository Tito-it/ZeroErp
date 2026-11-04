## 📘 Documentazione Concettuale – Vista `dbops.vw_diag_v_clienti_links`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il punto di partenza: una riga per cliente
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il legame che i flag confrontano
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo del cliente, da cui il soggetto e il tipo ruolo
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — nome e codice di chi è il cliente
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza a cui il cliente è legato
> * [config.utilities](/dbzero/config/tabelle/utilities) — l'utility del cliente
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il tipo del ruolo

---

### 🎯 Scopo Principale

La diagnostica dei legami di un cliente: in una riga il cliente, il suo billing account, il
soggetto, l'istanza utility, l'utility e il tipo ruolo, con tre flag che dicono se il billing
account è allineato al cliente.

È uno strumento da consultare su richiesta, non un allarme: a catalogo è un `INVENTARIO`, che
nessun digest conta.

---

### ⭐ I tre flag: dove il legame si rompe

Un cliente e il suo billing account portano entrambi l'istanza utility, il soggetto ruolo e
l'utility. Devono essere gli stessi, e i tre flag lo dicono uno per uno:

| Flag | È vero quando |
| --- | --- |
| `ba_match_istanza` | il billing account punta alla stessa istanza utility del cliente |
| `ba_match_soggetto_ruolo` | il billing account è dello stesso soggetto ruolo del cliente |
| `ba_match_utility` | il billing account è della stessa utility del cliente |

Un flag falso dice **quale** dei tre legami si è rotto, che è la domanda di chi apre la vista:
validare un import, preparare un riallineamento, capire perché un cliente fattura sull'account
sbagliato.

Oggi tutte queste colonne sono obbligatorie, sia sul cliente sia sul billing account: un
cliente senza billing account non esiste più. Le unioni con le tabelle collegate sono comunque
tolleranti, così una riga collegata che chi interroga non può vedere lascia il cliente a video
con il buco, e i flag vuoti, invece di farlo sparire. ⇒ Un flag vuoto non dice «incoerente»: dice
«il billing account non si vede da qui».

---

### Che cosa riporta, oltre ai flag

* le chiavi del cliente e quelle del billing account, affiancate, per vedere a colpo d'occhio
  quale differisce;
* il soggetto: codice, ragione sociale, cognome e nome;
* l'istanza utility, con il flag che dice se è fittizia;
* l'utility e il tipo ruolo, con codice interno e descrizione.

---

### Chi la può vedere

La vista è `security_invoker`: legge nel perimetro di chi la interroga. Per questo a catalogo ha
perimetro `DEFINER`: le sue righe non si elencano da un percorso senza identità, che vedrebbe zero.

---

### Test

* `db/pgtap/anagrafiche/create-cliente.sql`, test 8 — un cliente appena creato ha i tre flag veri.
* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — la vista resta `security_invoker`.
* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — la riga a catalogo combacia con la vista.

---

### Note di migrazione

* 2026-04-02 — prende il nome di oggi, col prefisso `vw_`.
* 2026-08-29 — esce il blocco dell'IVA del cliente: la colonna dell'aliquota sul cliente è stata
  rimossa, perché l'aliquota la decide la merce e il regime del soggetto passa da un titolo
  documentato. Non è stato sostituito, perché non rispondeva alla domanda di questa vista
  (`brief-db-be-iva-risolutore-e-regime-cliente`, I0-B).

---

{% include-markdown "signature-core.md" %}
