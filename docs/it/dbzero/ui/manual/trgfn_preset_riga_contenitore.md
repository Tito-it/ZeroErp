## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preset_riga_contenitore`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — la composizione di un preset di lista, di cui scrive `lista_id`
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — la composizione di un preset di dashboard, di cui scrive `dashboard_id`
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset da cui legge la lista
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il preset da cui legge la dashboard
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — l'altro trigger delle stesse righe, sulla data del contenuto

---

### 🎯 Scopo Principale

`ui.trgfn_preset_riga_contenitore` scrive su ogni riga della composizione di un preset la lista (o la
dashboard) a cui il preset appartiene. Chi scrive la riga non la passa: la colonna è il riflesso del
preset, non una scelta.

---

### ⭐ Una colonna derivata, perché i vincoli la leggano

La riga di composizione nomina il suo preset e una colonna della lista (o un widget). Che la colonna sia
**della stessa lista** del preset, o il widget **nel pool** della stessa dashboard, lo dicono due vincoli
composti che leggono la lista (o la dashboard) sulla riga. Questo trigger la riempie dal preset, a ogni
nascita e a ogni modifica della riga: un valore passato da chi scrive è sostituito, così la colonna non
può mai dire una lista diversa da quella del preset.

Il trigger non giudica niente: se la colonna nominata è di un'altra lista, o il widget fuori dal pool, il
rifiuto arriva dal vincolo. Un preset che non esiste lascia la colonna vuota, e risponde il vincolo verso
il preset.

---

### Chi scrive le righe

Le righe le scrivono il seed e il servizio di amministrazione, che salva la composizione cancellando e
reinserendo tutte le righe; nessuno dei due nomina la lista. La stessa funzione è montata sulle due
tabelle delle composizioni, e la famiglia la dice la tabella.

---

### Codici errore

* `E_TRIGGER_ARGOMENTI_INVALIDI` — montata su un'altra tabella, o non prima della scrittura di ogni riga.

---

### Test

* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — la lista e la dashboard della riga scritte dal database, un
  valore passato sostituito, una colonna di un'altra lista e un widget fuori dal pool rifiutati.

---

### Note di migrazione

* 2026-11-21 — nasce con le colonne `lista_id` e `dashboard_id` delle composizioni. Prima nessun vincolo
  legava la riga alla lista del preset: una colonna di un'altra lista entrava, e il resolver la abbinava
  per codice.

---

{% include-markdown "signature-core.md" %}
