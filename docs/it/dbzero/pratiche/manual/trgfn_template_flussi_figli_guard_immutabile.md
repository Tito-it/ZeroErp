## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_template_flussi_figli_guard_immutabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il template a cui ogni figlio appartiene
> * [pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali) · [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) · [pratiche.competenze_flussi](/dbzero/pratiche/tabelle/competenze_flussi) · [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) · [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) · [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — i sei figli sorvegliati
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_definizione_struttura_bloccata](/dbzero/pratiche/funzioni/fn_check_definizione_struttura_bloccata) — il predicato per inserimento e modifica
> * [pratiche.fn_check_definizione_congelata](/dbzero/pratiche/funzioni/fn_check_definizione_congelata) — il predicato per la cancellazione
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) — la stessa regola sul template padre
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — il set di copia, che è anche il perimetro del congelamento

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_template_flussi_figli_guard_immutabile` congela i figli di
configurazione di un template quando il template appartiene a un'edizione forkata già emessa, con la
stessa regola del template padre.

Una funzione generica serve i sei figli: la colonna che punta al template arriva come argomento del
montaggio.

---

### Le regole

* **Inserimento e modifica** sono vietati se l'edizione del template è emessa, pubblicata o ritirata
  (`pratiche.fn_check_definizione_struttura_bloccata`).
* **Cancellazione** è vietata solo se l'edizione è pubblicata (`pratiche.fn_check_definizione_congelata`):
  i figli di un'edizione ritirata si cancellano, per pulizia.
* I figli non hanno campi display: a differenza del template, nessuna colonna resta correggibile.
* Se la colonna verso il template è vuota, il guard non decide: lascia decidere alle chiavi esterne e
  agli altri guard.
* Durante il fork o la nuova versione i figli si inseriscono nella nuova bozza, che non è bloccata: il
  guard scatta solo su un'edizione già emessa.

---

### ⭐ Un montaggio per figlio, col lato proprietario

È montata `BEFORE INSERT OR UPDATE OR DELETE`, riga per riga, nella fase dei guard, su sei tabelle:

| Tabella | Colonna verso il template |
| --- | --- |
| `pratiche.template_flussi_canali` | `template_flusso_id` |
| `pratiche.template_flussi_handler_eventi` | `template_flusso_id` |
| `pratiche.competenze_flussi` | `template_flusso_id` |
| `pratiche.template_flussi_prerequisiti` | `template_flusso_id` |
| `pratiche.formule_tempo` | `template_flusso_da_id` |
| `pratiche.regole_generazione` | `template_flusso_origine_id` |

I figli con due colonne verso i template usano il lato che possiede la riga. L'altro lato appartiene
alla stessa edizione (prerequisiti, formule) oppure è la destinazione di un'altra definizione (regole di
generazione), che non deve governare il congelamento della regola.

⚠️ **Il perimetro del congelamento è il set di copia.** I sei figli sono quelli che
`pratiche.fn_copia_definizione` copia: un figlio che entra nella copia riceve qui il suo montaggio.

---

### Codici errore

* `E_TEMPLATE_DEFINIZIONE_CONGELATA` — scrittura vietata su un figlio di un template di un'edizione
  emessa, o cancellazione da un'edizione pubblicata.

---

### Test

* `pratiche/test-workflow-definizioni-fase2b` — scrittura e cancellazione dei figli su un'edizione
  pubblicata.
* `pratiche/test-definizione-ritirata-edit-freeze` — su un'edizione ritirata la modifica è bloccata e la
  cancellazione consentita.

---

### Note di migrazione

* 2026-07-03 — nasce insieme al guard sul template padre.
* 2026-07-04 — modifica e cancellazione si separano: i figli di un'edizione ritirata si cancellano.

---

{% include-markdown "signature-core.md" %}
