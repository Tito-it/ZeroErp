# Brief DB — Righe e componenti di documento: allineare preventivo, ordine e DDT a contratto e offerta

> **Chi chiede:** team DB (`dev/db-tid`), 2026-10-08. **A chi:** team DB; poi BE/FE solo se il §3
> lo fa emergere.
> **Origine:** i trovati del §10.8 di `brief-db-righe-esclusione-solo-non-si-vende` (archiviato in
> `work-done/` il 2026-10-08, §14). Quel brief ha messo contratto e offerta sotto le stesse regole e,
> per perimetro, ha lasciato fuori le altre famiglie. Questo brief esiste perché quei quattro punti
> non si perdano con l'archiviazione.
> **Stato:** ⏳ **APERTO, non iniziato.** Serve una decisione di Tid (D-1) prima del codice del §2.1.
> Riverificato il 2026-10-08: nessun changeSet dopo il 2026-10-05 tocca questi quattro punti.
> **Nel registro dei difetti DB:** voce **D19** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui. Lo stato vive in questo brief: alla chiusura si spunta D19 e la si sposta nel §7.

## 1. Da dove si parte

Il giro di contratto e offerta ha dato alle due famiglie una forma comune:

* la revisione dell'offerta (`vendite.fn_crea_revisione_offerta`, `20261005-19`) porta con sé
  **tutti** i componenti, e rimappa le righe per identità, non per ordine;
* i componenti di contratto e offerta sono chiusi «solo in bozza» dal livello RIGA del building
  block `trgfn_doc_righe_lock_fuori_bozza` (`20261005-16`, `-17`).

Le famiglie vicine (preventivo, ordine, DDT) sono rimaste come erano.

## 2. I quattro punti

### 2.1 🟡 La revisione del preventivo

`fn_crea_revisione_preventivo` copia **solo i componenti attivi** e rimappa le righe con un
`ROW_NUMBER` che si affida all'ordine di assegnazione degli id. La revisione dell'offerta fa
diversamente su entrambi i punti.

⏳ **D-1 (Tid):** che cosa significa un componente spento in una revisione: si porta spento, o non
si porta? La rimappatura per identità invece non chiede decisioni: è un difetto.

### 2.2 🟡 Il lock «solo in bozza» sui componenti di preventivo, ordine e DDT

Mancano. Col livello RIGA del building block è un `CREATE TRIGGER` per tabella, nella forma di
`20261005-17`. ⚠️ Sul preventivo vale la cautela già scritta per le sue righe: prima si censisce il
flusso di approvazione dei prezzi, che scrive anche fuori bozza.

### 2.3 🟡 `user_update` può essere NULL

Su tutte le righe e i componenti di documento, tranne il componente dell'offerta.
`linee-guida-sql.md` §7 lo vuole `NOT NULL`. Il test 4 di
`vendite/test-righe-gemelle-secondo-giro-v1` fissa oggi l'asimmetria come dichiarata: chi chiude
questo punto aggiorna anche quel test.

### 2.4 🟡 Il nome di `chk_contrighe_comp_quantita_pos`

Il nome dice «positiva», ma il vincolo vieta solo lo zero, come il gemello
`chk_oce_comp_quantita_nz`. Si rinomina in `…_nz`: nessun dato toccato. Lo nomina il test 8 di
`vendite/test-contratti-righe-componenti-v1`.

## 3. Ricadute BE/FE

Da verificare quando si scrive il §2.2: un lock nuovo sui componenti di ordine e DDT può
respingere una scrittura che il backend oggi fa fuori bozza. Il censimento delle scritture si fa
prima del changeSet.
