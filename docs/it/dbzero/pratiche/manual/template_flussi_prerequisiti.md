## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_prerequisiti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — gli step collegati
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le istanze su cui il prerequisito si verifica
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario di `esito_richiesto`
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — la verifica, senza tentare l'inserimento
> * [pratiche.trgfn_flussi_guard_prerequisiti](/dbzero/pratiche/funzioni/trgfn_flussi_guard_prerequisiti) — il guard alla nascita di un flusso
> * [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — protegge i prerequisiti di un'edizione emessa

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi_prerequisiti` definisce le dipendenze fra gli step di un workflow:
uno step può nascere in una pratica solo quando i suoi prerequisiti sono completati, eventualmente con un
certo esito.

---

### Le regole

* Una riga dice «lo step `template_flusso_id` richiede lo step `prerequisito_id`».
* Uno step non è prerequisito di se stesso, e la stessa coppia non si ripete.
* Il controllo avviene alla nascita del flusso, dal guard su `pratiche.flussi`; chi vuole saperlo prima,
  per esempio per abilitare un comando a video, chiama `pratiche.fn_check_prerequisiti_flusso`. La
  regola è scritta una volta, nella funzione.
* Cancellando uno dei due step la riga sparisce con lui.
* Un prerequisito vuole i due step attivi, e uno step con prerequisiti attivi non si spegne.

---

### Prerequisiti che guardano l'esito

`esito_richiesto` condiziona il prerequisito anche all'esito del flusso che lo soddisfa:

| `esito_richiesto` | Il prerequisito è soddisfatto quando il flusso prerequisito è completato… |
| --- | --- |
| vuoto | …con qualsiasi esito |
| un esito | …con quell'esito |

Il vocabolario è `config.esiti_flussi_pratiche`. Un flusso completato ha sempre un esito (lo garantisce
il guard su `pratiche.flussi`): così un passo chiuso `NEGATIVO` non abilita un successivo che richiede
`POSITIVO`. È il modo in cui si modellano i bivi per esito.

---

### ⛔ I prerequisiti seguono l'edizione

I prerequisiti appartengono, con i loro step, a un'edizione di workflow, e la copia di un'edizione li
porta con sé. Su un'edizione di un emittente pubblicata o ritirata non si inseriscono né si modificano, e
su una pubblicata non si cancellano.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — modifica di un prerequisito di un'edizione emessa.

Il rifiuto di un flusso con prerequisiti non soddisfatti è `E_PRATICHE_PREREQUISITI_NON_SODDISFATTI`, sul
guard dei flussi.

---

### Test

* `pratiche/test-fn-check-prerequisiti-flusso`, `pratiche/test-fn-guard-prerequisiti-flusso` — la
  verifica e il guard.
* `pratiche/test-prerequisiti-esito-aware`, `pratiche/test-bivi-condizionali` — i prerequisiti per esito
  e i bivi.
* `pratiche/test-definizione-ritirata-edit-freeze` — i prerequisiti di un'edizione ritirata.

---

### Note di migrazione

* 2026-06-08 — arriva `esito_richiesto`; i prerequisiti esistenti restano senza esito, e il loro
  comportamento non cambia.
* 2026-06-18 — la tabella, nata con l'audit del solo inserimento, riceve l'audit degli aggiornamenti.
* 2026-07-01 — il vocabolario di `esito_richiesto` passa da un `CHECK` a una chiave esterna verso
  `config.esiti_flussi_pratiche`.

---

{% include-markdown "signature-core.md" %}
