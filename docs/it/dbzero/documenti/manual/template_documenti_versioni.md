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
(latest review 29-04-2026)
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
* `stato` ammessi:
  * `BOZZA`
  * `PUBBLICATA`
  * `OBSOLETA`
* una versione `PUBBLICATA` deve avere `valido_dal`;
* `validita` è un `daterange` **generato** da `valido_dal`/`valido_al`
  (linee-guida-sql §7b), e l'ordine delle due date lo verifica il guard
  comune `script.trgfn_guard_date_validita` (automazione `DATE_VALIDITA`);
* non possono esistere due versioni `attivo = true` e `stato = 'PUBBLICATA'`
  con intervalli temporali sovrapposti per lo stesso template.
* la pubblicazione operativa usa
  `documenti.fn_pubblica_template_documento_versione(...)`: la funzione chiude
  a `nuovo.valido_dal - 1` le versioni `PUBBLICATA` precedenti sovrapposte,
  le porta a `OBSOLETA` e poi pubblica la nuova `BOZZA` nella stessa
  transazione DB.

---

### Semantica stato + date

* `BOZZA`: versione in preparazione, non applicabile nel motore;
* `PUBBLICATA`: versione selezionabile se la `validita` contiene la data di
  riferimento;
* `OBSOLETA`: versione non più da usare per nuove generazioni, ma mantenuta
  per storico e audit.

Il principio operativo resta data-driven: la scelta della versione corretta è
guidata prima dalla finestra `validita`, poi dai filtri applicativi sullo
stato.

---

### Campi rilevanti

* **Identita` versione**: `template_documento_id`, `versione`, `stato`.
* **Contenuto renderizzabile**: `html_template`, `css_template`,
  `markdown_template`, `formato_template`.
* **Motore di resa**: `render_engine_id`.
* **Layout PDF**: `page_format`, `page_orientation`, margini.
* **Contratto dati**: `context_schema`.

---

### Uso tipico nel processo

* pubblicazione controllata di una nuova versione template;
* risoluzione della versione valida alla data documento;
* persistenza nel registro storico dell'id versione effettivamente usata.

---

{% include-markdown "signature-core.md" %}
