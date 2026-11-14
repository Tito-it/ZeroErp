## 📘 Documentazione Concettuale – Tabella `documenti.template_documenti_versioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti)  
> • [documenti.render_engine_documento](/dbzero/documenti/tabelle/render_engine_documento)  
> • [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati)  
> • [vendite.listini_versioni](/dbzero/vendite/manual/listini_versioni)  
>
### 🎯 Scopo Principale
(latest review 14-11-2026)
`documenti.template_documenti_versioni` contiene le **versioni
renderizzabili** del template documentale, con stato di pubblicazione e
finestra temporale di validità.

---

### Ruolo nel processo

* conserva l'HTML/CSS o altri formati template ammessi;
* rende possibile pubblicare nuove versioni senza perdere lo storico delle
  precedenti;
* definisce quale versione è applicabile a una certa data.

---

### Regole principali

* univocità per `template_documento_id + versione`;
* i valori ammessi di `formato_template`, `page_format` e `page_orientation`
  stanno in tre vocabolari — `documenti.formati_template`,
  `documenti.formati_pagina`, `documenti.orientamenti_pagina` — legati per FK
  al loro `codice_interno` (dal 04-10-2026; prima erano tre `CHECK`). Si
  leggono dal lookup generico per riempire le tendine e non si configurano:
  niente `attivo`, e un valore nuovo nasce insieme al motore di stampa che lo
  sa onorare;
* `stato` ammessi:
  * `BOZZA`
  * `PUBBLICATA`
  * `OBSOLETA`
* una versione `PUBBLICATA` deve avere `valido_dal`;
* `validita` è un `daterange` **generato** da `valido_dal`/`valido_al`
  (linee-guida-sql §7b), e l'ordine delle due date lo verifica il guard
  comune `script.trgfn_guard_date_validita` (automazione `DATE_VALIDITA`);
* non possono esistere due versioni `attivo = true` fuori bozza
  (`stato IN ('PUBBLICATA', 'OBSOLETA')`) con intervalli temporali sovrapposti
  per lo stesso template (`ex_template_documenti_versioni_no_overlap_pubblicata`,
  esteso alle `OBSOLETA` il 14-11-2026): per ogni data, al più una versione
  stampabile. Il predicato è dichiarato anche nel registro
  `dbops.automazione_overlap`, da cui il framework ricreerebbe il vincolo.
* la pubblicazione operativa usa
  `documenti.fn_pubblica_template_documento_versione(...)`: la funzione chiude
  a `nuovo.valido_dal - 1` le versioni `PUBBLICATA` precedenti sovrapposte,
  le porta a `OBSOLETA` e poi pubblica la nuova `BOZZA` nella stessa
  transazione DB.

---

### Il patto con la forma dei dati (`versione_contesto`)

(dal 30-09-2026 — brief `brief-db-documenti-versione-contesto-template`)

Un PDF nasce da due pezzi: il **template** (questa riga) e i **dati** che un builder del
backend prepara. Il template legge i dati aspettandosi una certa forma; se la forma cambia e il
template no, le chiavi che non trova diventano vuote e il documento esce **incompleto senza
errore**. Il patto chiude questo caso:

* ogni versione dichiara in `versione_contesto` la forma che **legge** (obbligatoria, `>= 1`,
  **senza default**: chi crea la versione la dichiara);
* il builder dichiara la forma che **produce** (`_meta.context_version` nel contesto);
* si stampa solo se i due numeri coincidono. La regola sta in una funzione,
  `documenti.fn_guard_versione_contesto`, chiamata dal backend prima del render, dal trigger
  sull'INSERT di `documenti_generati` e da `fn_pubblica_template_documento_versione`.

Regole di stato:

* in **BOZZA** la forma si cambia liberamente, anche verso una forma che il builder non produce
  ancora: è così che si prepara la versione per la forma successiva;
* in **PUBBLICATA** non si cambia (guard A1, `trgfn_template_documenti_versioni_protect_pubblicata`):
  cambiarla aggirerebbe il controllo fatto alla pubblicazione;
* il numero è **del tipo di documento**, non globale: la forma 2 del preventivo non è la forma 2
  del DDT.

Un cambio di forma si fa così, nello stesso giro: forma N+1 nel builder **e** una versione nuova
del template che la dichiara, pubblicata. La ristampa dei documenti già emessi non cambia: rilegge
il contesto congelato e la versione usata allora.

---

### Semantica stato + date

* `BOZZA`: versione in preparazione, non applicabile nel motore;
* `PUBBLICATA`: versione selezionabile se la `validita` contiene la data di
  riferimento;
* `OBSOLETA`: versione superata da una pubblicazione successiva, chiusa al
  giorno prima della nuova. Come una `PUBBLICATA` non si modifica e non torna
  in `BOZZA` (guard A1, `trgfn_template_documenti_versioni_protect_pubblicata`,
  dal 14-11-2026). Resta selezionabile finché la sua `validita`
  contiene la data di riferimento: se la nuova parte da una data futura, fino
  alla vigilia stampa ancora lei. Dopo resta per storico, audit e ristampa.

Il principio operativo è data-driven (linee-guida-sql §7c): la finestra
`validita` decide, lo stato separa le versioni operative (`PUBBLICATA`,
`OBSOLETA`) dalla preparazione (`BOZZA`). La sede unica del predicato è
[documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)
(dal 14-11-2026 legge anche le `OBSOLETA`).

---

### Campi rilevanti

* **Identita` versione**: `template_documento_id`, `versione`, `stato`.
* **Contenuto renderizzabile**: `html_template`, `css_template`,
  `markdown_template`, `formato_template`.
* **Motore di resa**: `render_engine_id`.
* **Layout PDF**: `page_format`, `page_orientation`, margini.
* **Forma dei dati letta**: `versione_contesto` (sotto, «Il patto con la forma dei dati»).
* **Contratto dati**: `context_schema` — oggi vuoto e non controllato: la validazione delle
  singole variabili è fuori dal patto sulla forma (decisione D-C3 del 29-09-2026).

---

### Uso tipico nel processo

* pubblicazione controllata di una nuova versione template;
* risoluzione della versione valida alla data documento;
* persistenza nel registro storico dell'id versione effettivamente usata.

---

{% include-markdown "signature-core.md" %}
