## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la tabella su cui è montata
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset di base e la sua data del contenuto
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — calcola il flag «preset aggiornato» da snapshot e «ignora»
> * [ui.trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts](/dbzero/ui/funzioni/trgfn_ui_dashboard_preferenza_utente_z90_clear_preset_base_ts) — la gemella delle dashboard

---

### 🎯 Scopo Principale

`ui.trgfn_ui_lista_preferenza_utente_z90_clear_preset_base_ts` azzera lo snapshot della data del
preset (`preset_base_contenuto_aggiornato_il`) e l'«ignora» (`preset_aggiornato_ignored_at`) di una
preferenza di lista quando il suo preset di base cambia. Le due date si riferivano al preset di
prima: con un preset diverso non dicono più niente.

---

### Quando scatta

È un trigger `BEFORE UPDATE OF preset_base_id`, riga per riga, e agisce quando il valore nuovo è
**diverso** dal vecchio, in qualunque direzione: da un preset a nessuno, da nessuno a un preset, da
un preset a un altro. Un UPDATE che riscrive lo stesso preset non tocca niente; un INSERT non lo
attraversa.

Copre anche la cancellazione del preset: l'`ON DELETE SET NULL` della FK è un UPDATE della colonna,
e il trigger lo vede. Senza, la preferenza resterebbe con la data di un preset che non c'è più.

Non solleva errori: è una normalizzazione finale.

---

### ⚠️ Che cosa oggi non copre

* **Azzera anche lo snapshot nuovo.** Il trigger non distingue fra «la base è cambiata e nessuno
  ha scritto lo snapshot» e «la base è cambiata e lo snapshot nuovo arriva nella stessa
  istruzione». Il salvataggio della preferenza fa la seconda cosa (base e data nuove insieme): il
  trigger cancella la data appena scritta, e fino al salvataggio successivo il flag «preset
  aggiornato» non si accende più.
* **Il preset spento.** Spegnere il preset non cambia `preset_base_id`: il trigger non scatta, e
  snapshot e «ignora» restano agganciati a un preset che la cascata non usa più.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — la base portata a nessuno:
  snapshot e «ignora» azzerati, flag spento. Non sono costruiti il passaggio a un altro preset, la
  cancellazione del preset e il salvataggio che scrive base e snapshot insieme.

---

### Note di migrazione

* 2026-05-11 — nasce col flag «preset aggiornato».
* 2026-11-08 — lo snapshot si rinomina `preset_base_contenuto_aggiornato_il`, e confronta la data
  del contenuto del preset invece dell'audit.

---

{% include-markdown "signature-core.md" %}
