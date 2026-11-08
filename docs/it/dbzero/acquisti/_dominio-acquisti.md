### 🏗️ Lo stato del dominio `acquisti` (2026-08-21)

⚠️ **Il dominio è predisposto, non in esercizio.** Misurato: **tutte** le tabelle sono a
**zero righe** — ordini, righe, DDT, indirizzi, fulfillment. Nessun documento di acquisto è
mai stato creato.

Le pagine di questo schema descrivono quindi il **ruolo previsto** di ciascun oggetto, non un
processo osservato.

---

### Il disegno è lo **specchio** del ciclo vendite

```
acquisti.ordini  →  acquisti.ordini_righe
       └─ fulfillment ─→  acquisti.ddt  →  acquisti.ddt_righe
```

⭐ La struttura ricalca quella di `vendite`: testata + righe, il ponte `ordini_righe_fulfillment`
che lega riga d'ordine a riga di DDT con evasioni parziali, gli indirizzi come **snapshot**
congelati sul documento.

È una simmetria voluta e utile — chi conosce il ciclo vendite riconosce subito questo — ma va
maneggiata con una cautela: **la simmetria dei nomi non garantisce la simmetria delle
colonne**. Il caso più vistoso è la **provenienza** (`sorgente_tipo_id`, `sorgente_uid`): in
`vendite` segue il modello comune ([sorgente polimorfa](/guide/sorgente-polimorfa)), con la
chiave del documento tipizzata e la riga a parte; in `acquisti` (`ordini`, `ordini_righe`,
`ddt`, `ddt_righe`) è ancora la grammatica precedente, una chiave in testo senza il guard
unico. Le quattro tabelle sono l'elenco dichiarato del presidio di struttura, e passano al
modello col cantiere degli acquisti.

⚠️ Prima di dare per scontato che una colonna qui si comporti come l'omonima in `vendite`,
va verificato sulla struttura: tipo, `pg_constraint`, trigger montati.

---

### Il verso è invertito, e cambia il significato

In vendite il DDT accompagna merce che **esce**; in acquisti registra merce che **entra**.
Ne segue che:

* il **fornitore** è la controparte, non il cliente;
* il DDT di acquisto è tipicamente **subìto** — arriva col trasporto e va registrato com'è,
  non emesso da noi. Non ha quindi numerazione fiscale nostra;
* il fulfillment misura **quanto è stato ricevuto** rispetto all'ordinato, non quanto è stato
  spedito.
