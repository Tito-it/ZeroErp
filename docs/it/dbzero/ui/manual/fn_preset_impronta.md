## 📘 Documentazione Concettuale – Funzione `ui.fn_preset_impronta`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — salva l'impronta in `composizione_impronta`
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — lo stesso per le dashboard
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — la composizione di un preset di lista
> * [ui.dashboard_preset_widget](/dbzero/ui/tabelle/dashboard_preset_widget) — la composizione di un preset di dashboard
>
> Approfondimento funzioni:
>
> * [ui.trgfn_preset_riga_tocca_preset](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset) — la scrive a fine transazione
> * [ui.trgfn_preset_contenuto_aggiornato](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato) — la verifica, e sposta la data della composizione

---

### 🎯 Scopo Principale

`ui.fn_preset_impronta` calcola l'**impronta** della composizione di un preset: un valore che è lo
stesso per due composizioni con le stesse righe, e diverso appena una riga cambia. Serve a dire
«la composizione è cambiata?» senza guardare come ci si è arrivati: un DELETE seguito
dall'INSERT delle stesse righe dà l'impronta di prima.

---

### Che cosa entra nell'impronta

L'impronta è l'md5 delle righe della composizione, ordinate per colonna o per widget, così l'ordine
in cui sono state scritte non conta:

* `p_famiglia = 'lista'`: le righe di `ui.lista_preset_colonna` del preset, con `colonna_id`,
  `ordine`, `larghezza`, `visibile`, `fissata`;
* `p_famiglia = 'dashboard'`: le righe di `ui.dashboard_preset_widget`, con `widget_id`, `ordine`,
  `visibile`.

Un preset senza righe ha l'impronta dell'insieme vuoto. Una famiglia diversa dalle due dà `NULL`.

⚠️ Le colonne sono nominate una per una: una colonna nuova di contenuto della composizione entra
qui, nello stesso cantiere che la crea. Altrimenti cambiarla non sposterebbe la data del contenuto.

---

### Chi la usa

* Il trigger differito della composizione, a fine transazione, la calcola e la scrive sul preset in
  `composizione_impronta` quando è diversa da quella salvata.
* Il trigger del preset rifiuta (`E_UI_PRESET_CONTENUTO_DERIVATO`) chi scrive in
  `composizione_impronta` un valore diverso dall'impronta di oggi, e quando l'impronta cambia sposta
  la chiave `colonne` (o `widget`) della data del contenuto.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — DELETE + INSERT delle
  stesse righe: impronta e data ferme; con un ordine cambiato la data della composizione si sposta.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — un'impronta finta scritta dall'applicazione è
  rifiutata.

---

### Note di migrazione

* 2026-11-20 — nasce, insieme alla colonna `composizione_impronta` dei due preset.

---

{% include-markdown "signature-core.md" %}
