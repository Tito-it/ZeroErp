## 📘 Documentazione Concettuale – Funzione `script.fn_imponibile_riga`

> 👀 **Vedi anche**
>
> **Consumatori (viste):**
>
> • [vendite.vw_preventivi_righe_dettaglio](/dbzero/vendite/views/vw_preventivi_righe_dettaglio) · [vendite.vw_ordini_righe_dettaglio](/dbzero/vendite/views/vw_ordini_righe_dettaglio) · [vendite.vw_ddt_righe_dettaglio](/dbzero/vendite/views/vw_ddt_righe_dettaglio) — le righe dei documenti
> • [vendite.vw_ordini_righe_iva_base](/dbzero/vendite/views/vw_ordini_righe_iva_base) · [vendite.vw_ddt_righe_iva_base](/dbzero/vendite/views/vw_ddt_righe_iva_base) — le basi del riepilogo IVA
> • [vendite.vw_dash_fatturazione_preventivi](/dbzero/vendite/views/vw_dash_fatturazione_preventivi) · [\_ordini](/dbzero/vendite/views/vw_dash_fatturazione_ordini) · [\_ddt](/dbzero/vendite/views/vw_dash_fatturazione_ddt) — i cruscotti
>
> **Consumatori (funzioni):**
>
> • [vendite.fn_ricalcola_riepilogo_iva_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_preventivo) — il riepilogo IVA del preventivo
> • [vendite.trgfn_fatture_righe_importo](/dbzero/vendite/funzioni/trgfn_fatture_righe_importo) — l'imponibile della riga di fattura
>
> **Verifica:** `db/pgtap/script/test-fn-imponibile-riga-v1.sql`

---

### 🎯 Scopo Principale

(funzione nata il 2026-09-28, `20260928-16`)

**La sede unica dell'imponibile di una riga di documento**: quantità × prezzo ×
(1 − sconto/100), a **precisione piena**.

---

### ⭐ Perché esiste

La stessa formula era scritta a mano in **otto** oggetti del database e in tre
repository Python (censimento del 2026-09-28). Oggi davano tutte lo stesso
risultato: il rischio era il giorno in cui la regola cambia e una copia resta
indietro — una lista che mostra un importo mentre il riepilogo IVA ne somma un
altro, senza nessun errore. Le otto copie sono state ritirate nello stesso giro
(`20260928-17 → -26`, brief-db-liste-righe-documento §8.8).

---

### La semantica

| Caso | Risultato |
| --- | --- |
| quantità e prezzo valorizzati | `(q × p) × (1 − COALESCE(sconto, 0) / 100)` |
| **prezzo NULL** o **quantità NULL** | **NULL**, mai zero |
| sconto NULL | nessuno sconto |
| sconto 100 | zero (un valore vero) |

⛔ **NULL e non zero**, ed è la ragione per cui la sede dev'essere una: una riga
senza prezzo (il DDT di solo trasporto) **non vale zero, non ha valore**. Uno
zero sarebbe indistinguibile da una riga che vale davvero zero, e un totale lo
sommerebbe «giusto» (regola V-2/DEC-6 del DDT).

⚠️ **Nessun arrotondamento qui**: è politica di chi consuma.

| Chi | Cosa fa col risultato |
| --- | --- |
| le viste righe | `round(…, 2)` per mostrare (`importo_riga`), il pieno per chi aggrega (`imponibile_riga_full`) |
| il riepilogo IVA | somma il pieno, arrotonda la somma (mai per riga) |
| la riga di fattura | `script.fn_arrotonda_importo` con decimali e metodo configurati per articolo |

---

### Forma

- **Pura** (`IMMUTABLE`, `LANGUAGE sql`, `PARALLEL SAFE`): il pianificatore la
  **inlinea** nelle viste — nel piano non compare la chiamata ma l'espressione.
- **Non `STRICT`**: lo sconto NULL è un caso normale che deve dare
  l'imponibile pieno.
- **Tipi espliciti `numeric`**, non `%TYPE`: serve righe di documenti diversi
  con typmod diversi (prezzo `numeric(15,6)` sul preventivo, `numeric(18,6)`
  sull'ordine, `numeric` sul DDT) e servirà gli acquisti. Ancorarla a una
  tabella direbbe il falso sulla sua origine.
- Sta in **`script`**, non in `vendite`: è la regola di una riga di documento,
  e le righe di `acquisti` useranno questa.

---

### Presidi

Il pgTAP prova la formula sui valori (nessuna fixture), e due presidi sui
consumatori: le otto viste **dipendono** dalla funzione (`pg_depend`), e nessuna
copia della formula scritta a mano è rimasta in `vendite`/`script` (presidio sul
testo, provato per mutazione).

---

{% include-markdown "signature-core.md" %}
