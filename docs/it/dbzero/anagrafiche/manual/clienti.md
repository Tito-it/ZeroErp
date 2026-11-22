## 📘 Documentazione Concettuale – Tabella `anagrafiche.clienti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto di fatturazione: un cliente per billing account
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la fornitura da cui il cliente nasce
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — il punto di prelievo, che ha un cliente alla volta
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo cliente del soggetto
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — gli stati del cliente
> * [config.transizioni_stati_cliente](/dbzero/config/tabelle/transizioni_stati_cliente) — il percorso ammesso fra gli stati
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — le condizioni di pagamento
>
> Approfondimento viste:
>
> * [anagrafiche.vw_clienti_lista](/dbzero/anagrafiche/views/vw_clienti_lista) — la lista dei clienti
> * [anagrafiche.vw_clienti_codice_ba](/dbzero/anagrafiche/views/vw_clienti_codice_ba) — il cliente col codice del suo billing account, per la ricerca
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_cliente](/dbzero/anagrafiche/funzioni/fn_crea_cliente) — il verbo che fa nascere un cliente
> * [anagrafiche.fn_update_cliente](/dbzero/anagrafiche/funzioni/fn_update_cliente) — il verbo che modifica pagamento, garanzia e categoria
> * [script.fn_disdetta_cliente](/dbzero/script/funzioni/fn_disdetta_cliente) — la chiusura del cliente
> * [script.fn_subentro_cliente](/dbzero/script/funzioni/fn_subentro_cliente) — il cambio di cliente sullo stesso PDP
> * [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica) — la chiave unica del cliente manuale
> * [anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) — stati e date
> * [anagrafiche.trgfn_clienti_set_periodo](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_periodo) — il periodo del cliente
> * [anagrafiche.trgfn_clienti_sync_utility_from_ba](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba) — ruolo e utility copiati dal billing account, e il PDP
>
> Guide:
>
> * [Generazione di un cliente](/guide/generazione-cliente) — il percorso della creazione
> * [Gestione delle istanze utility](/guide/gestione-delle-istanze-utility) — istanze, PDP e stati del cliente

---

### 🎯 Scopo Principale

`anagrafiche.clienti` è la fornitura in quanto rapporto commerciale: un soggetto, col suo ruolo cliente, che
riceve un servizio (la utility) su un billing account, con uno stato, le date del suo ciclo di vita e le
condizioni di pagamento.

Ogni riga è di **un** billing account (`uq_clienti_billing_account`) e ne prende la fornitura: il ruolo, la
utility e l'istanza. Un'istanza ha tanti clienti quanti billing account, e un soggetto con un solo ruolo
cliente ha un cliente per ogni sua fornitura: per contare i clienti distinti si parte da `soggetto_ruolo_id`,
non dalle righe.

---

### ⭐ La fornitura è del billing account, e non si cambia

Ruolo, utility e istanza del cliente sono **copie** del suo billing account. Due chiavi esterne composte verso il
conto, `fk_clienti_ba_cliente` (ruolo e utility) e `fk_clienti_billing_account` (istanza), le tengono uguali, e `anagrafiche.trgfn_clienti_sync_utility_from_ba` scrive la utility quando chi crea il cliente
non la passa. Il ruolo invece va passato: lo controlla prima
`anagrafiche.trgfn_clienti_guard_ruolo_cliente`, che vuole un ruolo di tipo cliente.

Dopo la nascita le quattro colonne sono bloccate (`E_CLIENTE_FORNITURA_IMMUTABILE`): un cliente non passa a
un altro conto, a un'altra istanza o a un'altra utility. Una fornitura diversa è un cliente nuovo.

Il PDP è una copia anche lui, ma dell'istanza: lo riscrive `anagrafiche.trgfn_clienti_sync_pdp` a ogni
scrittura del cliente. Se la utility lo richiede (`config.utilities.richiede_pdp`) è obbligatorio, e dev'essere
della stessa utility del cliente.

---

### Lo stato e le sue date

Lo stato segue il percorso di `config.transizioni_stati_cliente`, e ogni stato pretende le sue date
(attivazione, sospensione, riattivazione, chiusura): le regole le tiene
`anagrafiche.trgfn_clienti_guard_stato_date`. Un cliente chiuso non si riapre e non cambia più la data di
chiusura; chi torna apre una fornitura nuova, collegata alla precedente.

Le date fanno il **periodo** (`periodo`), che `anagrafiche.trgfn_clienti_set_periodo` calcola dall'attivazione
alla chiusura, con il giorno di chiusura escluso; l'annullato non ha date né periodo. Il periodo è la misura
di «cliente presente» per tutto il modello:

* **un PDP ha un solo cliente alla volta**: due periodi sovrapposti sullo stesso PDP li rifiuta il vincolo di
  esclusione `ex_clienti_no_overlap_stesso_pdp`;
* **lo stato tecnico del PDP** segue i clienti che lo occupano oggi (`anagrafiche.trgfn_clienti_sync_stato_pdp`,
  con la domanda `anagrafiche.fn_check_pdp_occupato`);
* **la catena delle istanze**: l'istanza di un cliente punta a quella del cliente che l'ha preceduto
  (`anagrafiche.trgfn_clienti_set_parent_istanza`).

---

### Il cliente manuale ha una chiave sua

Le istanze fittizie, quelle della creazione manuale senza PDP, non hanno un punto fisico che separi una
fornitura da un'altra. Lì vale la **chiave unica del cliente manuale** (soggetto, utility, azienda), che un
constraint trigger differito controlla al commit: la regola è raccontata nella scheda di
[anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica).

---

### Chi scrive i clienti

* **La nascita** passa da `anagrafiche.fn_crea_cliente`, che crea ruolo, billing account, cliente, contatto e
  indirizzi in un'istruzione. Senza stato il cliente nasce attivo dal giorno operativo.
* **La modifica** di pagamento, garanzia, servizio da fatturare e categoria (sul billing account) passa da
  `anagrafiche.fn_update_cliente`.
* **La chiusura** è `script.fn_disdetta_cliente`; **il subentro** su un PDP è `script.fn_subentro_cliente`, che
  chiude il cliente uscente prima di far entrare il nuovo.

Il cliente non si cancella: il `DELETE` lo rifiuta il blocco comune, aperto solo dalla porta di manutenzione.
Ogni modifica e ogni cancellazione lasciano la versione precedente nello storico.

Le condizioni di pagamento hanno un solo meccanismo, il termine di catalogo (`termine_pagamento_id`). La colonna
può restare vuota: la risoluzione scende al termine predefinito, una rata alla data della fattura.

---

### Chi vede i clienti

La tabella è in RLS, con tre policy:

* l'**operatore** vede e scrive i clienti dei billing account delle aziende del suo perimetro
  (`rls_clienti_ef_whitelist`);
* il **cliente del portale** legge i propri (`rls_clienti_self_ownership`);
* il **cliente dello shop** legge quelli dei suoi billing account dello shop (`rls_clienti_shop`).

Le letture che devono contare i clienti di tutte le aziende (lo stato del PDP, la chiave del cliente manuale)
passano da funzioni `SECURITY DEFINER`.

---

### ⚠️ Che cosa oggi non copre

* **La data di chiusura ha due significati.** Il trigger del periodo la tratta come estremo escluso: il cliente
  non occupa più il PDP il giorno della chiusura. I commenti delle colonne `data_chiusura` e `periodo` la dicono
  inclusiva. E `script.fn_subentro_cliente` chiude l'uscente al giorno prima dell'attivazione del nuovo: con la
  chiusura esclusa, quel giorno il PDP resta senza cliente.
* **Il PDP del cliente segue l'istanza solo quando si scrive il cliente.** Se cambia `pdp_id` dell'istanza, il
  cliente tiene il PDP di prima fino alla sua prossima scrittura, e con lui il vincolo di esclusione, lo stato
  del PDP e la catena.
* **Lo stato del PDP segue il giorno della scrittura, non il calendario**: un cliente con l'attivazione o la
  chiusura in un giorno futuro cambia lo stato del PDP alla prossima scrittura, non quel giorno.
* **La catena delle istanze si ricalcola un anello per volta**, e sotto la RLS di chi scrive: i casi sono nella
  scheda di `anagrafiche.trgfn_clienti_set_parent_istanza`.

---

### Codici errore

* `E_CLIENTE_FORNITURA_IMMUTABILE` — si cambia billing account, istanza, ruolo o utility di un cliente.
* Gli altri li sollevano i trigger e i verbi della tabella, ciascuno nella sua scheda: stati e date
  (`E_CLIENTE_STATO_TRANSIZIONE_INVALIDA`, `E_CLIENTE_STATO_SENZA_DATA`, `E_CLIENTE_DATA_CHIUSURA_IMMUTABILE`,
  `E_DATA_CHIUSURA`), la fornitura (`E_DOC_CLIENTE_DIVERSO_DA_BA`, `E_PDP_OBBLIGATORIO`,
  `E_PDP_UTILITY_MISMATCH`), la chiave del cliente manuale (`E_CLIENTE_STESSA_CHIAVE`).

---

### Test

* `db/pgtap/anagrafiche/test-un-ba-un-cliente-v1.sql` — un cliente per billing account, più clienti sulla
  stessa istanza.
* `db/pgtap/anagrafiche/test-cliente-manuale-chiave-unica-v1.sql` — la chiave del cliente manuale, stati e
  date, la catena delle istanze fittizie.
* `db/pgtap/anagrafiche/test-clienti-sync-utility-pdp-policy.sql` — utility dal billing account e PDP
  obbligatorio.
* `db/pgtap/anagrafiche/test-istanza-cliente-chain.sql` e `db/pgtap/anagrafiche/test-simula-subentro.sql` — la
  catena sul PDP e il subentro.
* `db/pgtap/script/test-fn-disdetta-cliente.sql` — la chiusura, il periodo e il PDP che torna disponibile.

---

### Note di migrazione

* 2026-07-31 — le condizioni di pagamento passano tutte al termine di catalogo; escono `tipo_gg_scadenza_ft` e
  `nr_giorni_scadenza`.
* 2026-08-29 — escono `cliente_pa` e `split_payment` (salgono su `anagrafiche.soggetti`), `codice_cig`,
  `codice_cup` e `codice_commessa` (vanno su `vendite.contratti`) e `iva_id`, che nessuno sceglieva.
* 2026-10-08 — `uq_clienti_billing_account` prende il posto di `uq_clienti_istanza_utility`: da un cliente per
  istanza a un cliente per billing account.
* 2026-10-14 — gli stati pretendono le loro date, lo stato del PDP segue il periodo, nasce la chiave del
  cliente manuale.
* 2026-10-18 — la creazione passa a `anagrafiche.fn_crea_cliente`.

---

{% include-markdown "signature-core.md" %}
