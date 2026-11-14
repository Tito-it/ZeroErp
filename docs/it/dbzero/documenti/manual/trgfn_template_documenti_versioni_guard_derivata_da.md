## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_template_documenti_versioni_guard_derivata_da`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la colonna `derivata_da_versione_id`
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — standard e copie
>
> Approfondimento viste:
>
> * [documenti.vw_template_personalizzati_scarto](/dbzero/documenti/views/vw_template_personalizzati_scarto) — chi legge l'origine
>
> Approfondimento funzioni:
>
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — chi scrive l'origine
> * [documenti.trgfn_template_documenti_versioni_protect_pubblicata](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_protect_pubblicata) — le altre colonne di una versione fuori bozza
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — la registrazione dell'errore
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — il modello standard e «personalizza»

---

### 🎯 Scopo Principale

Garantisce che l'**origine di una copia personalizzata** (`derivata_da_versione_id`) sia una versione
di uno standard dello stesso documento, e che non cambi fuori bozza. È montata
`BEFORE INSERT OR UPDATE OF derivata_da_versione_id, template_documento_id` su
`documenti.template_documenti_versioni`.

---

### L'origine è una versione dello standard dello stesso documento

Quando l'origine è valorizzata, il guard pretende tutte e quattro:

* la versione d'origine è di un modello **standard**;
* la versione che la porta **non** è di uno standard: uno standard non deriva da niente;
* i due modelli hanno lo stesso **tipo di documento**;
* e la stessa **sorgente**.

Un'origine vuota passa: è la versione scritta da zero, o la versione successiva di una copia, che
eredita l'origine dalla più recente che la dichiara. Il controllo si ripete anche quando la versione
cambia modello, perché la coppia da confrontare cambia.

L'origine la scrive l'azione «personalizza», non l'operatore: un rifiuto vuol dire un difetto del
chiamante, e il codice è di classe tecnica.

---

### Fuori bozza l'origine non cambia

L'origine non è fra le colonne del guard d'immutabilità delle versioni, quindi la protegge questo:
su una versione pubblicata o obsoleta cambiare l'origine è rifiutato con lo stesso codice
dell'immutabilità. In bozza si cambia.

---

### Codici errore

* `E_DOCUMENTI_TEMPLATE_DERIVAZIONE_INVALIDA` — origine che non è una versione dello standard dello
  stesso documento, o versione di uno standard che dichiara un'origine. Il contesto dice quale delle
  quattro condizioni manca.
* `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` — origine cambiata su una versione fuori bozza.

---

### Test

* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — una copia che deriva dallo standard
  della stessa coppia passa; derivare da una versione non standard o dallo standard di un altro tipo
  è rifiutato; l'origine non cambia su una pubblicata e cambia in bozza.

---

### Note di migrazione

* 2026-10-20 — nasce con la colonna `derivata_da_versione_id` e il modello standard.

---

{% include-markdown "signature-core.md" %}
