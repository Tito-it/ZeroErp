## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_ripetibilita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella sorvegliata
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — dove sta la regola di ripetibilità
>
> Approfondimento funzioni:
>
> * [pratiche.fn_guard_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_guard_ripetibilita_flusso) — la sentinella che solleva l'errore
> * [pratiche.fn_check_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_check_ripetibilita_flusso) — il predicato
> * [pratiche.trgfn_flussi_guard_prerequisiti](/dbzero/pratiche/funzioni/trgfn_flussi_guard_prerequisiti) — il guard gemello sui prerequisiti

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_ripetibilita` applica, alla nascita di un flusso, la
regola di ripetibilità del suo template, delegandola a `pratiche.fn_guard_ripetibilita_flusso`.

---

### Le regole

* Scatta `BEFORE INSERT`, riga per riga, su `pratiche.flussi`, nella fase dei guard: le transizioni di
  stato successive non la interessano.
* Vale per ogni flusso: `template_flusso_id` è obbligatorio, e la ripetibilità si legge dal template.
* È un trigger separato da quello dei prerequisiti: due regole, due responsabilità. Nella fase dei
  guard i due scattano in ordine alfabetico, prima i prerequisiti.

---

### Codici errore

* `E_PRATICHE_FLUSSO_NON_RIPETIBILE` — sollevato da `pratiche.fn_guard_ripetibilita_flusso` quando il
  template non ammette un'altra istanza nella pratica.

---

### Test

* `pratiche/test-ripetibilita-flussi` — le regole di ripetibilità alla creazione di un flusso.

---

{% include-markdown "signature-core.md" %}
