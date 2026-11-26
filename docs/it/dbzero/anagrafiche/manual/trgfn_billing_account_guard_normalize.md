## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_normalize`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività che fermano il distacco dal padre
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_ba_padre](/dbzero/anagrafiche/funzioni/fn_check_ba_padre) — l'albero a un livello e un padre per cliente e per azienda
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo della check
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle due date, che non è qui
> * [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) — padre e figli della stessa azienda, l'altra domanda sull'albero

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_normalize` tiene le regole del conto padre di un billing account: il
padre non è il conto stesso, è dello stesso cliente, rispetta l'albero a un livello e il padre unico per
cliente e per azienda, porta una data d'inizio, e non si toglie né si cambia finché ci sono attività da
fatturare.

Nonostante il nome non normalizza niente: non tocca il codice né altre colonne, e restituisce la riga com'è.
Gira prima di ogni inserimento e modifica del billing account.

---

### Il padre non è il conto stesso

Un billing account con sé stesso come padre è rifiutato (`E_PARENT_SELF`).

---

### ⭐ L'albero ha un livello solo, e un cliente un padre per azienda

Quando il padre nasce o cambia, il trigger chiede ad `anagrafiche.fn_check_ba_padre` i motivi per cui il
billing account non lo può prendere, e solleva il primo:

* il padre proposto ha già un padre (`E_PARENT_CON_PADRE`);
* il billing account fa già da padre (`E_PARENT_HA_FIGLI`);
* il cliente ha già un altro padre sulla stessa azienda (`E_PARENT_SECONDO_PADRE`).

Le prime due insieme rendono impossibile anche un ciclo: in un ciclo ogni conto sarebbe padre e figlio. Con un
livello solo la fattura va al padre diretto senza ambiguità. Non c'è un indicatore «è un padre»: la
semantica sta tutta in `parent_account_id`.

La regola sta nella check, e non qui, perché deve leggere il padre del padre, i figli e gli altri padri del
cliente, che la RLS di chi scrive può nascondere: la check gira coi privilegi del proprietario, il trigger no.
Una modifica che non tocca il padre non rilegge l'albero.

---

### Le date: solo la regola di questa tabella

Con un padre, `valido_dal` è obbligatorio; e `valido_al` senza `valido_dal` è rifiutato. Tutti e due i casi
rispondono `E_VALORE_MANCANTE`, col campo che manca. Che la fine non preceda l'inizio non lo guarda questo
trigger: ha una sede sola, il guard comune delle date montato dall'automazione (`script.trgfn_guard_date_validita`).

---

### ⭐ Padre e figlio: la stessa identità fiscale

Il controllo impedisce di appendere un billing account sotto quello di un'altra persona o azienda. Il
soggetto di ciascuno dei due si legge **dall'istanza** del billing account, e si procede in tre gradini:

* **il padre non si raggiunge** → `E_PARENT_NON_RAGGIUNGIBILE`. La lettura passa dalla RLS di chi scrive
  (la funzione non è privilegiata): un padre che non esiste e un padre fuori dal perimetro danno lo stesso
  rifiuto, perché il trigger non li può distinguere;
* **manca il codice fiscale da una delle due parti** → il codice non vale come prova, e si confronta il
  soggetto: due billing account dello stesso soggetto senza codice fiscale passano, di soggetti diversi no
  (`E_PARENT_SOGGETTO_DIVERSO`);
* **i due codici fiscali ci sono** → si confrontano (`E_ID_FISCALI_DIVERSI`). Due soggetti diversi con lo
  stesso codice fiscale passano, ed è voluto: la regola è sull'identità fiscale.

Il confronto avviene a ogni scrittura con un padre, anche quando il padre non cambia.

---

### Il padre non si toglie né si cambia con attività da fatturare

Se una modifica svuota il padre o lo cambia con un altro, e il billing account ha attività fatturabili non
ancora fatturate, è rifiutata (`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`): quelle attività finiranno in una fattura
intestata al padre, e il distacco o il cambio le farebbe uscire con un'altra intestazione a metà del ciclo.

---

### ⚠️ Che cosa oggi non copre

* **Il nome del trigger non ha fascia** (`trg_billing_account_guard_normalize_ins_upd`): gira, per ordine
  alfabetico, dopo i guard di fascia `a` e prima di quelli di fascia `z`.

---

### Codici errore

* `E_PARENT_SELF` — il padre è il billing account stesso.
* `E_VALORE_MANCANTE` — con un padre manca `valido_dal`, o c'è `valido_al` senza `valido_dal`.
* `E_PARENT_NON_RAGGIUNGIBILE` — il padre non esiste o non è visibile a chi scrive.
* `E_PARENT_SOGGETTO_DIVERSO` — manca un codice fiscale e i soggetti sono diversi.
* `E_ID_FISCALI_DIVERSI` — i due codici fiscali sono diversi.
* `E_PARENT_CON_PADRE`, `E_PARENT_HA_FIGLI`, `E_PARENT_SECONDO_PADRE` — da `anagrafiche.fn_check_ba_padre`.
* `E_DISSOCIAZIONE_PARENT_CON_ATTIVITA` — si toglie o si cambia il padre con attività non fatturate.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-guard-cf-confrontabile-v1.sql` — i tre gradini dell'identità
  fiscale, il padre fuori perimetro e quello inesistente.
* `db/pgtap/anagrafiche/test-billing-account-guard-parent.sql` — il distacco con attività non fatturate,
  con attività fatturate, senza attività.
* `db/pgtap/anagrafiche/test-billing-account-albero-un-livello-v1.sql` — il padre che ha un padre, il conto che
  fa da padre, il ciclo, il secondo padre dello stesso cliente sulla stessa azienda, il cambio di padre con
  attività non fatturate, il padre ammesso.
* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il campo dell'errore sul padre uguale a sé.

---

### Note di migrazione

* 2026-08-18 — il confronto fiscale non usa più solo il codice: due billing account senza codice fiscale
  passavano anche se di soggetti diversi, e un padre fuori perimetro cadeva su «identificativi fiscali
  diversi» con due codici identici.
* 2026-09-23 — l'ordine delle date passa al guard comune; resta qui la regola «`valido_al` richiede
  `valido_dal`».
* 2026-11-26 — l'albero passa a un livello solo con un padre per cliente e per azienda, e il cambio di padre è
  giudicato come il distacco; prima solo il padre uguale a sé era rifiutato.

---

{% include-markdown "signature-core.md" %}
