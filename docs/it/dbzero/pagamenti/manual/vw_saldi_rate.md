## 📘 Documentazione Concettuale – Vista `pagamenti.vw_saldi_rate`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le rate visibili, che la vista passa tutte al nucleo
>
> Approfondimento viste:
>
> * [vendite.vw_fatture_scadenze_lista](/dbzero/vendite/views/vw_fatture_scadenze_lista) — l'identità delle rate, da affiancare a questa per uno scadenzario
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) — il nucleo: la formula sta lì, questa vista non ne ha una sua
> * [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata) — la porta per una rata sola
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — la regola dei saldi, per chi non è tecnico

---

### 🎯 Scopo Principale

La porta dello scadenzario: il saldo di tutte le rate visibili in un solo passaggio, ottenuto chiamando il nucleo `fn_get_saldi_rate` con l'elenco di tutte le rate che chi interroga può vedere.

Per ogni rata dà il saldo, la parte in lavorazione, l'incassato e se ha movimenti. Uno
scadenzario la affianca a `vendite.vw_fatture_scadenze_lista` sulla rata, e «solo aperte» è un
filtro sul saldo diverso da zero.

---

### ⛔ Non è la porta del picker sulla pagina

Questa vista aggrega **tutto**: è il costo onesto dello scadenzario, non quello di una pagina.
Chi ha gli id della pagina chiama il nucleo con quell'elenco, che scende negli indici. Chi ha
una rata sola usa `fn_get_saldo_rata`.

---

### ⭐ Nessuna formula propria

La vista è il nucleo applicato a tutte le rate, non una seconda definizione del saldo:
cambiare il nucleo cambia anche questa vista, per costruzione. L'elenco delle rate si passa
esplicito perché il nucleo non accetta un «tutte» implicito.

---

### 🔒 `security_invoker`, da ripetere a ogni ricreazione

Va ri-specificata a ogni `CREATE OR REPLACE`, altrimenti PostgreSQL la azzera: il nucleo legge
tabelle con le policy, e la vista non deve leggerle coi diritti del proprietario. Sotto
l'invoker anche l'elenco delle rate passato al nucleo è filtrato dalla RLS.

---

### Test

* `db/pgtap/pagamenti/test-fn-get-saldi-rate-v1.sql` — il test 17: la vista è
  `security_invoker` e coincide col nucleo su tutte le rate costruite.

---

### Note di migrazione

* 2026-09-17 — nasce insieme al nucleo `fn_get_saldi_rate`, come sua porta per lo scadenzario.

---

{% include-markdown "signature-core.md" %}
