## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_riepilogo_iva_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.preventivi_riepiloghi_iva](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
> • [config.iva](/dbzero/config/tabelle/iva)
> • [config.iva_natura](/dbzero/config/tabelle/iva_natura)
>
Approfondimento viste:
> • [vendite.vw_ddt_riepilogo_iva_dettaglio](/dbzero/vendite/views/vw_ddt_riepilogo_iva_dettaglio)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Arricchisce il riepilogo IVA del preventivo con i dati leggibili dell'aliquota (codice,
descrizione, percentuale) e della natura (codice), e aggiunge il totale di riga
(`imponibile + imposta`). Serve alla UI di riepilogo del preventivo.

---

### ⚠️ È **snapshot**, non live — ed è il contrario del gemello DDT

Questa vista **non calcola niente**: legge la tabella `vendite.preventivi_riepiloghi_iva`, che
contiene il riepilogo **già congelato**. Imponibile, imposta e arrotondamento arrivano da lì
così come sono; la vista aggiunge solo le decodifiche e una somma.

Il gemello `vw_ddt_riepilogo_iva_dettaglio` fa l'opposto: ricalcola tutto a ogni lettura
partendo dalle righe.

⛔ **Le due viste non vanno unificate.** È una decisione di dominio: il preventivo congela
perché è un'offerta che deve restare confrontabile nel tempo — se il listino cambia, il
preventivo già emesso deve continuare a dire ciò che diceva. Il DDT ricalcola perché fino
alla fatturazione può ancora muoversi. Il congelamento definitivo è della **fattura**.

⚠️ Conseguenza operativa: **se le righe del preventivo cambiano e nessuno rigenera il
riepilogo, questa vista continua a mostrare i valori vecchi.** Non c'è nulla, qui, che
segnali il disallineamento — la vista è fedele alla tabella, e la tabella è ferma per
progetto. Il riallineamento è compito di chi scrive il riepilogo, non di chi lo legge.

---

### Qui la natura c'è davvero

`natura_id`, `natura_codice`, `esigibilita`, `split_payment` sono **valori veri** letti dallo
snapshot — mentre nel riepilogo DDT le stesse quattro colonne sono costanti `NULL`, messe
solo per allineare la forma.

La differenza non è un'incoerenza: sul preventivo quegli attributi fiscali sono già stati
decisi e congelati; sul DDT non esistono ancora.

---

### ⚠️ Non è `security_invoker` — oggi innocuo

La vista **non** dichiara `WITH (security_invoker = on)`, quindi gira con i diritti del
proprietario e non applicherebbe le policy RLS delle tabelle lette.

Verificato il 2026-08-21: `vendite.preventivi_riepiloghi_iva` **non ha RLS attiva** — a
differenza di `vendite.preventivi`, che ce l'ha. Poiché la vista legge **solo** la tabella dei
riepiloghi e non passa mai dalla testata, oggi non c'è nessun perimetro da aggirare.

⚠️ È però un'**asimmetria con il gemello DDT**, che invece è `security_invoker` e attraversa
`vendite.ddt` (con RLS). Le due viste hanno quindi garanzie di scope diverse, e la differenza
non è dichiarata da nessuna parte se non qui. Il giorno in cui `preventivi_riepiloghi_iva`
avesse una policy — o la vista venisse estesa per leggere la testata — questa mancanza
diventerebbe un buco vero, e nessun test la segnalerebbe.

---

### L'ordinamento è nel corpo

`ORDER BY ri.preventivo_id, iva.aliquota_iva, ri.id` — insolito per una vista, ma qui
intenzionale: il riepilogo si legge per aliquota crescente, ed è l'ordine in cui va stampato.

⚠️ Un `ORDER BY` dentro una vista **non sopravvive** a una query esterna che ne imponga uno
proprio, e non va dato per garantito a valle: chi ha bisogno di quell'ordine lo ripeta.

---

{% include-markdown "signature-core.md" %}
