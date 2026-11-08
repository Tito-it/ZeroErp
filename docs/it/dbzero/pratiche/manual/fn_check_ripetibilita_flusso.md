## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_ripetibilita_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la regola `ripetibilita` dichiarata sul template
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — le istanze già nella pratica
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — gli stati `ANNULLATO` e `COMPLETATO`
>
> Approfondimento funzioni:
>
> * [pratiche.fn_guard_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_guard_ripetibilita_flusso) — la sentinella che solleva l'errore
> * [pratiche.trgfn_flussi_guard_ripetibilita](/dbzero/pratiche/funzioni/trgfn_flussi_guard_ripetibilita) — il trigger che applica la regola a ogni inserimento

---

### 🎯 Scopo Principale

`pratiche.fn_check_ripetibilita_flusso` dice se una nuova istanza di un template di flusso è ammessa
nella pratica, secondo la regola di ripetibilità dichiarata sul template.

È un controllo puro: risponde vero o falso e non solleva niente. Chi chiama decide che cosa fare del
divieto: la sentinella `pratiche.fn_guard_ripetibilita_flusso` lo trasforma in errore, il backend lo
usa per sapere se offrire il gesto «Ripeti» nel percorso della pratica, senza ricopiare la regola.

---

### Le regole

La funzione guarda l'**ultima istanza** del template nella pratica, escluse quelle annullate:

* un'istanza annullata non consuma la ripetibilità;
* «ultima» è la più recente per creazione, non per `sequenza`, che è la posizione nel template.

| Regola del template | Nuova istanza ammessa quando |
| --- | --- |
| `SEMPRE` | sempre |
| `MAI` | non esiste nessuna istanza non annullata |
| `SE_NON_POSITIVO` | l'ultima istanza è `COMPLETATO` con un esito diverso da `POSITIVO`; un'istanza ancora aperta blocca, per non avere doppioni vivi |

La prima istanza di un template è sempre ammessa, qualunque sia la regola. Un template inesistente
non si blocca qui: lo rifiuta la chiave esterna su `pratiche.flussi`.

La funzione è `STABLE` e non modifica dati.

---

### Test

* `pratiche/test-ripetibilita-flussi` — le tre regole, l'istanza annullata che non conta e l'istanza
  aperta che blocca.

---

### Note di migrazione

* 2026-06-11 — nasce con la regola di ripetibilità sul template (analisi-pratiche-workflow-v2).

---

{% include-markdown "signature-core.md" %}
