## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_preferenza_preset_base_snapshot`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — una delle due tabelle su cui è montata
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — l'altra
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la data del contenuto del preset di una lista
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — la data del contenuto del preset di una dashboard
>
> Approfondimento funzioni:
>
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — il flag che confronta lo snapshot col preset
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — espone il preset di base da salvare
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — lo stesso per le dashboard

---

### 🎯 Scopo Principale

`ui.trgfn_preferenza_preset_base_snapshot` scrive lo **snapshot** del preset di base di una
preferenza: `preset_base_contenuto_aggiornato_il` diventa la data del contenuto del preset
`preset_base_id`, letta dalla tabella dei preset. Lo snapshot lo scrive il database, e il valore che
arriva da chi scrive la riga non conta. Una funzione sola per le preferenze delle liste e delle
dashboard.

---

### Ogni salvataggio è un riallineamento

Il trigger è `BEFORE INSERT OR UPDATE` delle colonne `preset_base_id` e
`preset_base_contenuto_aggiornato_il`, riga per riga: ogni scrittura che nomina la base o lo
snapshot rilegge la data del contenuto del preset. Salvare la preferenza vuol dire «ho visto il
preset com'è adesso», e il banner del preset aggiornato si spegne. Senza base lo snapshot è vuoto.

Un aggiornamento che tocca solo l'«ignora» o la configurazione non attraversa il trigger, e lo
snapshot resta quello di prima.

Quando la base cambia, o la riga nasce, l'«ignora» (`preset_aggiornato_ignored_at`) si azzera: si
riferiva al preset di prima. La cancellazione del preset porta `preset_base_id` a nessuno con l'`ON
DELETE SET NULL` della FK, e il trigger la vede come un cambio di base.

---

### Un argomento sceglie la tabella dei preset

L'argomento del trigger nomina la tabella dei preset da cui leggere: `ui.lista_preset` sulle
preferenze delle liste, `ui.dashboard_preset` su quelle delle dashboard. Un argomento diverso dai due
è un montaggio sbagliato, e la scrittura si ferma con `E_TRIGGER_ARGOMENTI_INVALIDI`.

---

### ⚠️ Che cosa oggi non copre

* **La base di un altro contenitore.** Nessun vincolo chiede che `preset_base_id` sia un preset della
  stessa lista o della stessa dashboard della preferenza: il trigger legge la data di quel preset
  comunque. Il resolver se ne accorge, perché la base salvata non è quella di oggi
  (`preset_base_cambiato`).

---

### Codici errore

* `E_TRIGGER_ARGOMENTI_INVALIDI` — il trigger è montato con un argomento che non è una delle due
  tabelle dei preset.

---

### Test

* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — lo snapshot scritto dal database, che ignora il valore
  passato dall'applicazione.
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — la base portata a nessuno:
  snapshot e «ignora» azzerati, flag spento.

---

### Note di migrazione

* 2026-11-20 — nasce, e prende il posto dei due trigger `z90` che azzeravano lo snapshot quando la
  base cambiava, anche quando la stessa istruzione portava lo snapshot nuovo: il banner restava muto
  fino al salvataggio successivo. Le loro funzioni,
  `ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts` e la gemella delle dashboard, sono
  tolte.

---

{% include-markdown "signature-core.md" %}
