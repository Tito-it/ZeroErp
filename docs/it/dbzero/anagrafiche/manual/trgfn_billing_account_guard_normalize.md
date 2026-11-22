## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_guard_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
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
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle due date, che non è qui
> * [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente) — padre e figli della stessa azienda, l'altra domanda sull'albero

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_guard_normalize` tiene le regole del conto padre di un billing account: il
padre non è il conto stesso, è della stessa identità fiscale, porta una data d'inizio, e non si toglie finché
ci sono attività da fatturare.

Nonostante il nome non normalizza niente: non tocca il codice né altre colonne, e restituisce la riga com'è.
Gira prima di ogni inserimento e modifica del billing account.

---

### Il padre non è il conto stesso

Un billing account con sé stesso come padre è rifiutato (`E_PARENT_SELF`). È l'unico controllo sulla forma
dell'albero: un padre che ha a sua volta un padre, o due conti che si fanno da padre l'un l'altro, passano.

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

### Il padre non si toglie con attività da fatturare

Se una modifica svuota il padre e il billing account ha attività fatturabili non ancora fatturate, è
rifiutata (`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`): quelle attività finiranno in una fattura intestata al padre,
e il distacco le farebbe uscire con un'altra intestazione a metà del ciclo.

---

### ⚠️ Che cosa oggi non copre

* **Il cambio di padre non è giudicato come il distacco.** Da un padre a un altro il legame si sposta anche con
  attività non fatturate: il controllo guarda solo il padre che diventa vuoto.
* **Nessun controllo di profondità o di ciclo** oltre al padre uguale a sé (vedi sopra).
* **Il nome del trigger non ha fascia** (`trg_billing_account_guard_normalize_ins_upd`): gira, per ordine
  alfabetico, dopo i guard di fascia `a` e prima di quelli di fascia `z`.
* **Il COMMENT della funzione** dice che controlla le date e normalizza il codice: non lo fa.

---

### Codici errore

* `E_PARENT_SELF` — il padre è il billing account stesso.
* `E_VALORE_MANCANTE` — con un padre manca `valido_dal`, o c'è `valido_al` senza `valido_dal`.
* `E_PARENT_NON_RAGGIUNGIBILE` — il padre non esiste o non è visibile a chi scrive.
* `E_PARENT_SOGGETTO_DIVERSO` — manca un codice fiscale e i soggetti sono diversi.
* `E_ID_FISCALI_DIVERSI` — i due codici fiscali sono diversi.
* `E_DISSOCIAZIONE_PARENT_CON_ATTIVITA` — si toglie il padre con attività non fatturate.

---

### Test

* `db/pgtap/anagrafiche/test-billing-account-guard-cf-confrontabile-v1.sql` — i tre gradini dell'identità
  fiscale, il padre fuori perimetro e quello inesistente.
* `db/pgtap/anagrafiche/test-billing-account-guard-parent.sql` — il distacco con attività non fatturate,
  con attività fatturate, senza attività.
* `db/pgtap/dbops/test-punti-canale-campo-v1.sql` — il campo dell'errore sul padre uguale a sé.

---

### Note di migrazione

* 2026-08-18 — il confronto fiscale non usa più solo il codice: due billing account senza codice fiscale
  passavano anche se di soggetti diversi, e un padre fuori perimetro cadeva su «identificativi fiscali
  diversi» con due codici identici.
* 2026-09-23 — l'ordine delle date passa al guard comune; resta qui la regola «`valido_al` richiede
  `valido_dal`».

---

{% include-markdown "signature-core.md" %}
