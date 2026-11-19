## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la tabella su cui è montata
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il preset di base che la preferenza cita
>
> Approfondimento funzioni:
>
> * [ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts](/dbzero/ui/funzioni/trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts) — la stessa regola sulle preferenze di lista
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — legge la fotografia per il banner

---

### 🎯 Scopo Principale

Quando `preset_base_id` di una preferenza di dashboard cambia, la trigger function azzera la fotografia
del preset (`preset_base_contenuto_aggiornato_il`) e l'«ignora» del banner
(`preset_aggiornato_ignored_at`): si riferivano al preset di prima, e il banner non deve accendersi su di
loro.

---

### Quando scatta

È montata prima dell'UPDATE di `preset_base_id`, riga per riga, e agisce solo se il valore cambia davvero:
da NULL a un preset, da un preset a NULL, da un preset a un altro. Copre anche la cancellazione del
preset: la FK porta `preset_base_id` a NULL con un UPDATE, e il trigger scatta. All'INSERT non scatta.

Non solleva errori: corregge la riga e la lascia passare.

---

### ⚠️ Che cosa oggi non copre

* **Butta anche la fotografia nuova.** Azzera la fotografia ogni volta che il preset cambia, senza guardare
  se lo stesso UPDATE ne porta una nuova. Il salvataggio del backend è un UPSERT che scrive insieme il preset
  di base e la sua data: quando il preset è cambiato rispetto al salvataggio di prima, la data appena scritta
  si perde, e il banner resta spento finché l'utente non salva di nuovo.
* **È una copia.** Il corpo è identico, riga per riga, a quello della funzione delle preferenze di lista: due
  sedi per la stessa regola, che possono divergere.

---

### Test

Nessun test esercita la funzione delle dashboard. Per le liste,
`db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` porta il preset di base a NULL e
controlla il banner, che con il preset a NULL è spento comunque: non prova l'azzeramento.
`db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` scrive la fotografia con un secondo
UPDATE proprio perché il trigger la toglierebbe.

---

### Note di migrazione

* 2026-07-21 — nasce, sul modello di quella delle liste.
* 2026-11-08 — la fotografia si chiama `preset_base_contenuto_aggiornato_il`.

---

{% include-markdown "signature-core.md" %}
