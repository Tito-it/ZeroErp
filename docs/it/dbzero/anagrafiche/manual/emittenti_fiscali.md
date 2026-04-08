## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)    
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)    
>
### 🎯 Scopo Principale
(last review)
`anagrafiche.emittenti_fiscali` rappresenta l’anagrafica **degli emittenti fiscali** disponibili
nel sistema. Ogni emittente e` un ruolo (`soggetti_ruoli`) con configurazioni operative
utili al ciclo di fatturazione.

Questa tabella **non** definisce il default per i billing account: la scelta dell’emittente
avviene tramite la tabella di mapping `anagrafiche.emittenti_fiscali_billing_account`.

---

### Ruolo nel processo

* Fornisce l’**identita` fiscale** che compare nei documenti.
* Consente la gestione **multi‑emittente** (piu` soggetti emittenti nello stesso gestionale).
* Centralizza configurazioni operative del ruolo emittente: bollo, valuta e policy generali.

---

### Confine del modello

* I dati societari e fiscali strutturali del soggetto restano nel perimetro
  anagrafico del soggetto collegato all'emittente.
* `regime_fiscale_rf` identifica il **codice RF del tracciato fattura elettronica/SdI**
  del soggetto emittente e viene mantenuto in questa tabella perche' esposto come
  metadato del ruolo emittente nei flussi applicativi.
* `bollo_auto`, `bollo_soglia`, `valuta_id` e `rounding_policy` sono configurazioni
  operative dell'emissione e appartengono al ruolo emittente.
* `rounding_policy`, quando valorizzata, usa gli stessi valori ammessi della
  matrice utility: `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`.
* I parametri specifici per utility non vanno modellati qui ma nella matrice
  `anagrafiche.emittenti_fiscali_utilities`.

---

### Regola di selezione (richiamo)

* L’emittente **effettivo** per una fattura e` risolto dal mapping
  `billing_account → emittente fiscale`.
* Se non esiste un mapping specifico, si usa l’emittente **di default globale**
  definito nel mapping (non in questa tabella).

---

### Best practice operative

* Popolare questa tabella con **tutti gli emittenti fiscali** gestiti dal sistema.
* Mantenere il mapping separato per garantire flessibilita` e fallback.
* Deve esistere **almeno un emittente fiscale**: alla creazione del primo viene generato
  automaticamente il default nel mapping con `billing_account_id = NULL`.
* Usare `rounding_policy` solo come policy generale del ruolo; i dettagli di
  arrotondamento per singola utility vanno configurati in
  `anagrafiche.emittenti_fiscali_utilities`.
* La compatibilita` tra ruolo emittente fiscale e utility resta nel perimetro
  della matrice `config.utilities_tipi_ruolo`; la tabella
  `anagrafiche.emittenti_fiscali_utilities` e` opzionale e contiene solo
  parametri specifici quando servono.

---

### Vincoli applicativi (attivo)

* Un emittente fiscale **non puo` essere disattivato** se esistono mapping
  in `emittenti_fiscali_billing_account` collegati al suo `soggetto_ruolo_id`.
* Questo vincolo evita che un emittente ancora in uso venga escluso per errore.

---

{% include-markdown "signature-core.md" %}
