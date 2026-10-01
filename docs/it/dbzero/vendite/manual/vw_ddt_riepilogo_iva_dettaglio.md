## 📘 Documentazione Concettuale – Vista `vendite.vw_ddt_riepilogo_iva_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento viste:
> • [vendite.vw_ddt_righe_iva_base](/dbzero/vendite/views/vw_ddt_righe_iva_base)
> • [vendite.vw_preventivi_riepilogo_iva_dettaglio](/dbzero/vendite/views/vw_preventivi_riepilogo_iva_dettaglio)
>
Approfondimento tabelle:
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [config.iva](/dbzero/config/tabelle/iva)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Riepilogo IVA del DDT di vendita: una riga per combinazione `(ddt_id, iva_id, aliquota)` con
imponibile, imposta, arrotondamento e totale. È lo specchietto fiscale del documento di
trasporto.

---

### ⚠️ È **live**, non snapshot — ed è la differenza con il gemello dei preventivi

Questa vista **calcola** il riepilogo ogni volta, partendo da `vw_ddt_righe_iva_base`. Non
legge nessuna tabella di riepilogo: se cambia una riga del DDT, il riepilogo cambia con lei.

Il gemello `vw_preventivi_riepilogo_iva_dettaglio` fa **l'opposto**: legge la tabella
`vendite.preventivi_riepiloghi_iva`, cioè uno **snapshot** congelato.

⛔ **Le due viste non vanno unificate**, per quanto abbiano colonne quasi identiche. È una
decisione di dominio: il preventivo congela il suo riepilogo perché è un'offerta che deve
restare confrontabile nel tempo; il DDT lo ricalcola perché è un documento logistico che fino
alla fatturazione può ancora muoversi. Il congelamento definitivo è della **fattura**.

---

### Come si arrotonda — una volta sola, alla fine

Tre CTE in cascata, e l'ordine è la sostanza:

1. **`imponibili`** — somma `imponibile_riga_full` (non arrotondato) per
   `(ddt_id, iva_id, aliquota_effettiva)`;
2. **`aggregati`** — arrotonda a 2 decimali **la somma**, e conserva lo scarto in
   `arrotondamento` (`somma_piena − somma_arrotondata`);
3. **`riepilogo`** — calcola l'imposta sull'imponibile **già arrotondato**.

Sommare prima e arrotondare dopo evita l'errore di accumulo che si otterrebbe arrotondando
riga per riga. Lo scarto non viene buttato: è esposto, così il totale piano resta
ricostruibile.

⚠️ `COALESCE(aliquota_effettiva, 0)` nel calcolo dell'imposta: un'aliquota non risolta
produce **imposta zero**, non un errore. La causa a monte è nella vista base — tipicamente un
emittente che non risolve.

---

### Natura sempre nulla, esigibilità e scissione dalla regola

`natura_id` e `natura_codice` sono costanti `NULL`, tipizzate esplicitamente: servono ad
**allineare la forma** a quella del riepilogo preventivi, e sul DDT la natura nasce con il
documento fiscale.

⭐ `esigibilita` e `split_payment` **non sono più nulle** dal 2026-10-01 (D-6 di
`brief-db-esigibilita-iva-per-cassa-emittente`): escono per codice IVA da
[script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento),
con l'emittente e il billing account del DDT — la stessa regola delle righe di fattura,
degli ordini e dei preventivi, calcolata al momento (il DDT non ha snapshot). Il cast
`::character(1)` tiene il tipo della colonna. Un DDT senza `billing_account_id` dà
`NULL`/`NULL`: il cliente non è noto.

---

### Scope

`WITH (security_invoker = on)`, ereditato anche attraverso `vw_ddt_righe_iva_base`, che a sua
volta è `security_invoker` e aggancia `vendite.ddt` (con RLS) in `JOIN` interno.

---

{% include-markdown "signature-core.md" %}
