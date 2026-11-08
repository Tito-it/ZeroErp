## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_template_flussi_guard_modalita_esito`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — lo step su cui si configura l'esito
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — gli esiti, verdetti e di ramo
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_guard_esito_classe](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_classe) — il controllo gemello a runtime, sull'esito scritto al completamento

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_template_flussi_guard_modalita_esito` controlla, quando si configura
uno step, che modalità dell'esito, esito predefinito e direzione siano coerenti fra loro.

I valori ammessi di ogni campo li presidiano i `CHECK` della tabella; qui sta la coerenza fra i campi,
con un errore che dice che cosa è sbagliato nel disegno dello step, mostrato nel pannello di
amministrazione.

---

### Le quattro modalità dell'esito

* `MANUALE` (predefinita) — lo step si avvia, e l'operatore sceglie l'esito al completamento.
* `AUTOMATICO` — lo step si avvia e si completa con l'esito predefinito, senza scelta umana.
* `CONTESTUALE` — lo step si avvia e si completa in un'unica azione, con l'esito predefinito proposto e
  confermato dall'operatore.
* `DOMINIO` — l'esito lo calcola un building block di dominio, senza scelta dell'operatore; al
  completamento sono ammessi solo esiti di ramo, non verdetti (lo controlla a runtime
  `pratiche.trgfn_flussi_guard_esito_classe`).

⚠️ **`DOMINIO` non vuol dire bivio.** Uno step con bivio sul verdetto, dove l'operatore sceglie positivo o
negativo e i prerequisiti ramificano sull'esito, resta `MANUALE` o `CONTESTUALE`: `DOMINIO` marca solo
gli step il cui esito è calcolato.

---

### Le quattro regole

| Regola | Perché | Errore |
| --- | --- | --- |
| `AUTOMATICO` e `CONTESTUALE` hanno un esito predefinito | un automatismo deve sapere quale esito scrivere | `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO` |
| `AUTOMATICO` solo su uno step a direzione `INTERNA` | un esito automatico in entrata o in uscita fabbricherebbe la risposta di una controparte esterna | `E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA` |
| `DOMINIO` non ha esito predefinito | l'esito lo calcola il dominio, e un predefinito maschererebbe gli errori | `E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO` |
| L'esito predefinito di `AUTOMATICO` e `CONTESTUALE` è un verdetto | gli esiti di ramo li calcola il dominio, e non si applicano come predefinito | `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO` |

⭐ **Perché c'è la quarta regola.** L'esito predefinito è un riferimento al catalogo degli esiti senza
vincolo di classe: senza questa regola un predefinito di ramo verrebbe scoperto solo a runtime, dal
controllo sull'esito al completamento. Fallire quando si configura è meglio.

---

### Quando scatta

Prima di inserire uno step, e prima di ogni modifica di modalità dell'esito, esito predefinito o
direzione. Le scritture sono di configurazione e rare: il costo a runtime è trascurabile.

---

### Codici errore

* `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO`
* `E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA`
* `E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO`
* `E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO`

---

### Test

* `pratiche/test-esito-configurabile-template-flussi` — le quattro regole e i `CHECK` della tabella.

---

### Note di migrazione

* 2026-06-17 — nascono le prime due regole (brief-db-esito-configurabile-flussi).
* 2026-07-01 — l'esito predefinito diventa un riferimento al catalogo degli esiti, e il vecchio `CHECK`
  sui quattro verdetti è ritirato.
* 2026-07-02 — arriva la modalità `DOMINIO`: la prima regola si restringe ad `AUTOMATICO` e
  `CONTESTUALE`, nascono la terza e la quarta (brief-db-step-dominio-e-definizioni-versionate).
* 2026-08-05 — i codici errore prendono il prefisso `E_`; i nomi vecchi restano a catalogo ritirati.

---

{% include-markdown "signature-core.md" %}
