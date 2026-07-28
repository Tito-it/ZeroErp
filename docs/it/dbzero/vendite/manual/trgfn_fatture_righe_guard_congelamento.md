## ⚙️ Documentazione Concettuale – Trigger `vendite.trgfn_fatture_righe_guard_congelamento`

> **Versione**: 2026-07-28 (brief-fix-importi-riga-fattura-zero §4.1-bis, D1-bis ·
> migration `20260728-03` funzione, `20260728-04` armamento)

> **Vedi anche**
>
[vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura) — stessa soglia
> [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — il bypass di manutenzione

---

### 🎯 Scopo Principale

La fattura è un documento fiscale: **superata la soglia `DRAFT`/`EMESSA` le sue
righe sono uno snapshot e non si toccano più**, né in scrittura né in
cancellazione.

Armato come `BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW`, fase `a10` — prima
di tutti gli altri, così un'operazione respinta non fa lavorare il calcolo
dell'importo né lascia scritture nello storico.

Errore: `E_FATTURA_RIGA_CONGELATA`.

---

### ⚠️ Congela gli INPUT, non l'importo

È il punto che vale la pena capire, perché la prima formulazione del requisito
era sbagliata.

L'idea iniziale era «inibire il ricalcolo dell'importo oltre una certa soglia».
Non funziona, per due ragioni:

1. su `fatture_righe` **non esisteva alcun guard di stato** — nulla impediva un
   `UPDATE fatture_righe SET qta = 999` su una fattura `DEFINITIVA`;
2. l'importo è calcolato da un trigger a partire dalle colonne sorgente: bloccare
   il solo importo lascerebbe passare una riga con `qta = 999` e
   `imponibile = 500`, **incoerente e indistinguibile da un dato buono** — cioè
   peggio del problema di partenza.

Congelati gli **input** (`qta`, `prezzo_unitario`, `sconto_percentuale`,
`iva_id`), l'importo non può derivare, qualunque sia il meccanismo che lo calcola.

---

### Perimetro: INSERT, UPDATE **e** DELETE

Non solo la modifica. Aggiungere o togliere una riga a un documento emesso ne
cambia il totale esattamente come modificarla.

E l'`UPDATE` è bloccato **per intero**, `descrizione` compresa: finisce sul PDF
della fattura come tutto il resto, e un documento fiscale emesso non si ritocca.

---

### La soglia

La stessa già in uso in `vendite.fn_ricalcola_riepilogo_iva_fattura`: scrittura
ammessa solo per `DRAFT` ed `EMESSA`. Non se ne inventa una nuova, e il confronto
è per `codice_interno` (immutabile), mai per `codice`.

Se la fattura non ha stato, il guard **lascia passare**: non è lui a doversene
occupare, e fallire qui darebbe un errore fuorviante su un problema che sta
altrove.

---

### ⚠️ Bypass di manutenzione — obbligatorio, non opzionale

`vendite.fn_cleanup_fatture_by_ids` (reset lotto) imposta la GUC
`zeroerp.maintenance_reset_lotto_draft` proprio per attraversare i guard della
famiglia fatturato, e la `DELETE` delle righe passa di qui. Senza questo ramo il
reset lotto si romperebbe.

⚠️ La FK `fk_fatture_righe_fat` è `ON DELETE CASCADE`: **cancellare una fattura fa
scattare questo trigger su ogni sua riga**. Il bypass è ciò che tiene in piedi il
percorso di cleanup.

Stesso contratto già onorato da `trgfn_attivita_fatturabili_guard_fatturato`,
`trgfn_attivita_fatturabili_guard_quantita_immutabile`,
`trgfn_commesse_attivita_guard_quantita_immutabile`,
`trgfn_fatturazione_lotti_guard_stato` e `trgfn_logs_guard_delete`.

---

### Effetto collaterale che vale come funzionalità

Poiché anche lo **snapshot di esposizione dei kit** (`kit_*`) sta sulle righe,
questo guard lo congela senza bisogno di alcun meccanismo dedicato:

* cambiare `esposto_in_fattura` in distinta **non tocca** le fatture emesse — non
  perché ce ne ricordiamo, ma perché il database lo impedisce;
* **rigenerare** una fattura passa dal reset lotto, che riscrive le righe leggendo
  il flag corrente: l'esposizione cambia, ed è corretto;
* quando la fattura non è più modificabile, **la stampa è immutabile**.
