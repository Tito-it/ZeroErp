## 📘 Documentazione Concettuale – Tabella `pratiche.tipi_prestazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — le pratiche di quel tipo
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni di workflow del tipo
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — gli step
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — il tipo come destinazione della generazione fra pratiche
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'attivazione del cliente, che `pre_attivazione` e `post_attivazione` guardano
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_tipi_prestazione_bootstrap_definizione](/dbzero/pratiche/funzioni/trgfn_tipi_prestazione_bootstrap_definizione) — crea l'edizione preset alla nascita del tipo

---

### 🎯 Scopo Principale

La tabella `pratiche.tipi_prestazione` è il catalogo dei tipi di pratica che il sistema gestisce: ogni
pratica ha un tipo, che ne dice la natura e il workflow applicabile.

---

### Il tipo è l'identità, le edizioni versionano il workflow

* Ogni tipo nasce con la sua edizione di workflow preset, versione 1 pubblicata, creata dal trigger di
  bootstrap. Il tipo resta l'identità condivisa (anche per il reporting); le edizioni, preset e copie
  degli emittenti, ne versionano gli step.
* Le regole di generazione fra pratiche usano il tipo come destinazione.
* `categoria` è un raggruppamento libero, senza vocabolario chiuso.
* `codice` e `codice_interno` sono unici; il `codice` si scrive in maiuscolo.

---

### Prima o dopo l'attivazione del cliente

`pre_attivazione` e `post_attivazione` dicono se il tipo si apre per un cliente non ancora attivato, già
attivato, o per entrambi. «Attivato» vuol dire che il soggetto ha un billing account attivo con
l'emittente della pratica.

| `pre_attivazione` | `post_attivazione` | Significato |
| --- | --- | --- |
| sì | sì | Sempre ammesso (predefinito) |
| sì | no | Solo per un cliente non ancora attivato |
| no | sì | Solo per un cliente attivato |
| no | no | Non legato al ciclo di vita del cliente: ammesso sempre |

⚠️ La regola la applica il servizio del backend alla creazione della pratica, e solo quando i due flag
sono diversi: il database non la controlla.

---

### Ritiro e disattivazione

* `obsoleto_dal` toglie il tipo dalla scelta per le pratiche nuove da quella data, senza toccare
  `attivo` né le pratiche esistenti; le letture storiche lo vedono ancora.
* Un tipo non si spegne finché ha pratiche, edizioni, template, regole di generazione, formule del tempo
  o modelli di mail attivi.
* Le modifiche sono storicizzate.

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — il bootstrap dell'edizione preset.
* `pratiche/test-obsoleto-dal-catalogo-v1` — il ritiro programmato.

---

### Note di migrazione

* 2026-07-02 — con le edizioni versionate il workflow passa dal tipo alle sue edizioni; il tipo resta
  l'identità.

---

{% include-markdown "signature-core.md" %}
