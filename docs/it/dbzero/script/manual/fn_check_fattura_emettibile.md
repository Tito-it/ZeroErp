## 📘 Documentazione Concettuale – Funzione `script.fn_check_fattura_emettibile`

> 👀 **Vedi anche**
>
> • [vendite.trgfn_fatture_guard_stato](/dbzero/vendite/manual/trgfn_fatture_guard_stato) — il guard che la legge entrando in EMESSA
>
> • [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/manual/fn_ricalcola_riepilogo_iva_fattura) — il riepilogo che la riga senza IVA non rompe più
>
> • [script.fn_check_preventivo_emettibile](/dbzero/script/funzioni/fn_check_preventivo_emettibile) — la gemella del preventivo
>
Guide: [Il risolutore IVA di riga](/guide/iva-risolutore-di-riga)

### 🎯 Scopo Principale

(rev 2026-10-22, D-3 di Tid)

Elenca i **motivi per cui una fattura non si può emettere**. Non solleva e non scrive: risponde
`[]` se la fattura è emettibile, altrimenti l'elenco ordinato dei motivi.

| # | Codice | La regola |
| --- | --- | --- |
| 1 | `E_FATTURA_RIGA_IVA_MANCANTE` | ogni riga della fattura ha l'aliquota IVA |

**Perché ogni riga.** Il riepilogo IVA della fattura le aggrega **tutte**, e la fattura
elettronica vuole l'aliquota su ogni linea. La regola ha lo stesso perimetro di chi la consuma.

**Il caso tipico.** Un articolo senza IVA in anagrafica, su una fornitura che non indica un tipo
d'uso: il risolutore dell'IVA risponde «nessuno sa dirlo» (`origine = 'ASSENTE'`) e la riga nasce
senza codice. In bozza è legittimo; all'emissione no.

Il messaggio dice la fattura (il numero, o l'id se è ancora in bozza), il numero della riga e la
sua descrizione. Nel dettaglio ci sono anche l'id della riga e l'articolo, per chi corregge.

---

### La storia

Il 29 agosto 2026 Tid ha deciso per DDT, ordini e preventivi: **la bozza resta libera, il
cancello sta all'emissione**, e la guardia nel riepilogo entra solo insieme al cancello. Sulla
fattura era stato rinviato, e il 22 ottobre 2026 (D-3) è stato completato con questa check.

---

### 🧪 Il presidio

`db/pgtap/vendite/test-fattura-cancello-iva-v1.sql`.

---
{% include-markdown "signature-core.md" %}
