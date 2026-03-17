## 📘 Documentazione Concettuale – Tabella `vendite.documenti_fatturazione_canali`

> 👀 **Vedi anche**
>
• [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
> • [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)  
>
🎯 Scopo Principale

(latest review 24-02-2026)
`vendite.documenti_fatturazione_canali` e` il registro tecnico unico dei canali
fatturabili per documento sorgente (`sorgente_tipo_id + sorgente_uid`), usato per
uniformare le regole su contratti, preventivi, ordini e DDT.

---

### Regole principali

* chiave documento sorgente uniforme:
  `sorgente_tipo_id` + `sorgente_uid` (`text`);
* un solo record per canale per documento:
  `UNIQUE (sorgente_tipo_id, sorgente_uid, canale_codice)`;
* un solo canale `APERTO` per documento (unique parziale);
* `canale_codice`:
  codice sorgente (`config.sorgenti.codice`) oppure valore speciale `DIRETTO`;
* stati ammessi:
  `APERTO`, `CONSUMATO`, `BLOCCATO`;
* `motivo_blocco` obbligatorio quando `stato_canale='BLOCCATO'`;
* target opzionale coerente a coppia:
  `target_sorgente_tipo_id` e `target_sorgente_uid`.

---

### Utilizzo previsto

* prevenire doppia fatturabilita` cross-canale;
* tracciare quale canale ha consumato il documento;
* supportare transizioni uniformi (`open/consume/block`) per i flussi:
  `preventivo->ordine`, `ordine->ddt`, `contratto->commessa`.

---

{% include-markdown "signature-core.md" %}
