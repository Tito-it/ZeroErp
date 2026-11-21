## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_fornitori_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori)
> • [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)
> • [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore)
> • [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento)
> • [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali)

---
### 🎯 Scopo Principale

(rev 2026-11-21)

Dettaglio completo del fornitore in una riga sola: anagrafica del soggetto,
stato (con il flag `blocca_ordini`), condizioni di pagamento (valuta, modalità, termine),
fiscale (ritenuta d'acconto e aliquota; il regime col suo codice RF, `regime_fiscale_rf`, e
la descrizione del catalogo, `regime_fiscale_descrizione`) e i due campi di qualifica
(`rating`, `qualifica_scadenza`).

Split payment e instradamento della fatturazione elettronica non sono qui: sono del
soggetto, per ogni suo ruolo. È anche la sorgente della lista configurabile dei fornitori.

È la superficie di **dettaglio**, non di lista: espone tutto ciò che serve a compilare la
scheda fornitore senza una seconda chiamata.

---

### ⚠️ Il dominio è in costruzione, e questa vista lo precede

`acquisti` conta oggi 11 oggetti auto-generati in tutto. Questa vista è quindi una delle
prime superfici stabili di un dominio ancora agli inizi, ed è già consumata dal backend.

Va letta con quella consapevolezza: **espone colonne che il ciclo acquisti non usa ancora**
(rating, scadenza qualifica), predisposte perché il modello le prevede. La loro
presenza non significa che a monte ci sia un processo che le mantiene.

---

### ⚠️ Non è `security_invoker` — oggi innocuo, domani no

A differenza delle viste di `vendite` e delle due su `clienti`, questa vista **non** dichiara
`WITH (security_invoker = on)`: viene eseguita con i diritti del proprietario, quindi le policy
RLS delle tabelle sottostanti **non si applicherebbero** a chi interroga.

Verificato il 2026-08-21: **nessuna** delle tabelle lette — `fornitori`, `soggetti_ruoli`,
`soggetti` — ha oggi la RLS attiva. La mancanza è quindi **senza effetto pratico adesso**.

⚠️ Ma è una rete che non c'è. Il perimetro emittente sul ciclo acquisti non è ancora stato
affrontato: il giorno in cui `anagrafiche.fornitori` avrà una policy, questa vista continuerà
a **bypassarla in silenzio**, e nessun errore lo segnalerà. Chi introduce quella RLS deve
ricordarsi di aggiungere qui `security_invoker`, e non lo scoprirà da un test rosso.

---

### Cosa **non** garantisce

* **Nessun filtro su `attivo`**: la colonna è esposta, non applicata. Un fornitore disattivato
  compare.
* **Nessun filtro su `blocca_ordini`**: anche quello è un dato da leggere, non una condizione.
  Chi apre un ordine deve controllarlo, la vista non lo fa per lui.
* **Nessuna riga per un fornitore senza soggetto**: `soggetti_ruoli` e `soggetti` sono legati
  con `JOIN` interno. Tutto il resto (stato, valuta, modalità e termine di pagamento) è
  `LEFT JOIN`, quindi un riferimento mancante lascia `NULL` senza far sparire il fornitore. Lo
  stesso vale per il regime: senza regime, codice e descrizione sono `NULL`.

---

{% include-markdown "signature-core.md" %}
