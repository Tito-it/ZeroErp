# Brief DB — Componenti di un kit in fattura: tre modi di esporli, non due

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`);
> poi BE/FE (§5).
> **Origine:** collaudo della fattura con un kit (versione 4 del template, forma 2 del contesto,
> `brief-db-documenti-versione-contesto-template` §13), 2026-10-01.
> **Stato:** ✅ **E-1, E-2, E-3 decise da Tid il 2026-10-01** (§6). Nessun changeSet scritto.
>
> **In una riga:** oggi un componente di kit in fattura o non compare, o compare come riga
> descrittiva **senza prezzo**. Manca il terzo modo, quello che si intende di solito con «esposto in
> fattura»: il componente come **articolo vero**, con prezzo e importo suoi, fuori dal totale del kit.

---

## 1. Il problema

`catalogo.articoli_componenti.esposto_in_fattura` è un **booleano**, e la vista
`vendite.vw_fattura_righe_esposte` lo legge così:

| Flag | Cosa produce |
| --- | --- |
| `false` | il componente non compare; il suo valore sta nel totale del kit |
| `true` | il componente compare sotto il kit come riga **descrittiva**, senza importo; il suo valore sta comunque nel totale del kit |

Chi compila la distinta e mette «esposto in fattura = sì» si aspetta invece di **vedere il prezzo**
del componente in fattura, separato dal kit. Il modello non lo permette: con due valori ce n'è uno
che si capisce al contrario.

## 2. Cosa c'è oggi — letto dalla struttura (2026-10-01)

Il flag percorre tutta la catena, ed è una **proprietà del catalogo**, non del documento:

| Passo | Dove | Come |
| --- | --- | --- |
| catalogo | `catalogo.articoli_componenti.esposto_in_fattura` | `boolean NOT NULL DEFAULT false` |
| righe dei documenti | preventivi, ordini, contratti, DDT (`*_righe_componenti`) | **nessuna copia**: il BE lo legge col JOIN sul catalogo (`_componenti_repo_mixin.list_componenti_riga`, «BoM immutabile per design»); le funzioni `fn_*_riga_componenti_preview` lo proiettano |
| commessa | `attivita_fatturabili.meta` | chiave `esposto_in_fattura` (contratto `apps/vendite/services/_kit_meta.py`), scritta al push da `BoMComponentExpander` |
| fattura | `vendite.fatture_righe.kit_esposto_in_fattura` | `boolean`, con `kit_key` |
| rappresentazione | `vendite.vw_fattura_righe_esposte` | padre = **somma di tutti** i componenti; esposti = righe descrittive, importo `NULL` |
| lista a video | `vendite.vw_fattura_righe_lista` | il jsonb `componenti` porta riga, articolo, descrizione, quantità, UoM: **nessun prezzo** |

⭐ **La pipeline è già pronta**: ogni componente arriva in commessa e in `fatture_righe` come riga a sé,
**col suo prezzo**. L'aggregazione la fa solo la vista di rappresentazione. Il terzo modo non chiede
dati nuovi, chiede di leggere quelli che ci sono.

⚠️ **Commento stantio** da correggere nello stesso giro: `ordini_righe_componenti` e
`preventivi_righe_componenti` (e simili) dicono «una riga per ogni componente esposto_in_fattura =
TRUE». Dal modello unificato del 2026-05-13 ci sono **tutti** i componenti attivi.

## 3. Il modello deciso

Un vocabolario a tre valori al posto del booleano (E-1):

| Valore | In fattura | Nel totale del kit |
| --- | --- | --- |
| `NASCOSTO` | non compare | **sì** |
| `DESCRITTIVO` | riga sotto il kit, senza prezzo né importo (com'è oggi il `true`) | **sì** |
| `VALORIZZATO` | riga sotto il kit **con quantità, prezzo e importo suoi** | **no**: il suo importo è sulla sua riga |

* ⭐ **Un componente resta sempre legato al suo kit** (Tid, 2026-10-01). Anche `VALORIZZATO` non
  diventa mai una riga sciolta, come se fosse stato venduto da solo: sta **sotto** la riga del kit,
  rientrato, in ogni caso — non solo quando il kit resta senza importo. Nella vista è il livello 1
  del suo kit (stessa `kit_key`), nella lista a video sta dentro `componenti` del padre, in stampa
  sotto il padre:

  ```
  Postazione ufficio ............ 100 €   ← il resto: la lampada (nascosta)
    Scrivania ................... 600 €   ← valorizzato, legato al kit
    Sedia ....................... 300 €   ← valorizzato, legato al kit
                        totale  1.000 €
  ```
* **La riga del kit** porta la somma dei componenti `NASCOSTO` e `DESCRITTIVO`.
* **Il kit senza resto** (E-2, strada **a**): se tutti i componenti sono `VALORIZZATO` — o
  `VALORIZZATO` e `DESCRITTIVO` — la riga del kit **resta come intestazione senza importo** (`NULL`,
  non zero: zero direbbe «omaggio»), con i componenti sotto. Il cliente ha comprato il kit, e la
  fattura continua a dirlo.
* **Quantità del kit**: la stessa di oggi (media delle quantità dei componenti, omogenee per il guard
  R10), calcolata su **tutti** i componenti, anche i valorizzati: un kit senza resto ha comunque la
  sua quantità.
* ⭐ **Il totale del documento non cambia mai** al variare dell'esposizione: è la proprietà che la
  vista garantisce oggi, e resta.
* La rappresentazione resta **una**: PDF, XML SDI e portale leggono la stessa vista (regola R17).
  Per l'SDI le righe `VALORIZZATO` sono linee di dettaglio con il loro prezzo; la riga del kit senza
  resto è una linea descrittiva. ⚠️ Nel tracciato XML le linee sono **piatte**, quindi il legame col
  kit va dichiarato con una convenzione, per esempio il riferimento alla linea del kit in
  `AltriDatiGestionali` o nella descrizione. La sceglie il cantiere SDI (sospeso per decisione), ma la
  vista deve già dargli il dato: per ogni componente il `riga_nr` del suo kit.

## 4. Proposta (team DB)

1. **Vocabolario**: `config.esposizioni_componente` (codice, descrizione, `etichetta_key`), CSV in
   `80_data` con i tre valori.
2. **Catalogo**: `articoli_componenti.esposizione_in_fattura` (FK sul vocabolario, NOT NULL, default
   `NASCOSTO`) al posto di `esposto_in_fattura`; backfill `false → NASCOSTO`, `true → DESCRITTIVO`
   (è quello che il `true` produceva). Il booleano si ritira **nello stesso giro**: due colonne per la
   stessa scelta divergono.
3. **Fattura**: `fatture_righe.kit_esposizione` al posto di `kit_esposto_in_fattura`, stesso
   backfill, stesso ritiro.
4. **Viste**: `vw_fattura_righe_esposte` con le regole di §3; `vw_fattura_righe_lista` che porta nel
   jsonb `componenti` anche `esposizione`, `prezzo_unitario` e `importo_riga` (`NULL` per i non
   valorizzati). ⚠️ Da quel momento la colonna `importo_riga` della lista **non somma più** al
   totale del documento: i valorizzati hanno l'importo dentro `componenti`. È voluto, va scritto nel
   `COMMENT`.
5. **Funzioni di anteprima** (`fn_*_riga_componenti_preview`, `fn_contratto_righe_preview`,
   `fn_espandi_listino_versione`, `fn_offerta_eccezione_componenti_*`, `fn_accredita_riga_reso`) e
   trigger che nominano il flag (`trgfn_articoli_componenti_block_modifica_struttura`,
   `trgfn_componenti_guard_coerenza_bom`): la colonna nuova al posto della vecchia. Il censimento
   completo è quello di §2 più un `grep` sul corpo vivo.
6. **Commenti stantii** di §2 corretti.
7. **pgTAP costruendo i casi**: un kit con un componente per modo, un kit senza resto (tutti
   valorizzati), un kit valorizzato + descrittivo, e il totale del documento uguale nei tre casi.
   Nessun confronto con la popolazione.

## 5. Ricadute fuori dal DB (da chiedere a BE/FE quando il DB è fatto)

* **BE**: il contratto del meta di commessa (`_kit_meta.META_KEY_ESPOSTO_IN_FATTURA` →
  `esposizione`) e chi lo scrive (`BoMComponentExpander`) e lo legge (`FattureRigheService`); i
  `TypedDict` e i repository dei componenti; il builder fattura alla **forma 3** (componenti con
  prezzo e importo), per il patto versione/forma.
* **Template**: versione 5 della fattura, che stampa prezzo e importo dei valorizzati e il kit senza
  resto senza importo. Dichiara la forma 3; si pubblica quando il builder la produce.
  ⚠️ **Numerazione da verificare al momento di scrivere** (sessione BE, 2026-10-01): anche R-3 di
  `brief-db-esigibilita-iva-per-cassa-emittente.md` (§11) porta la fattura a «forma 3 + v5» (le
  annotazioni). Chi arriva primo prende 3/v5, l'altro passa a 4/v6 e parte dal template dell'altro.
* **FE**: nella distinta dell'articolo il toggle «esposto in fattura» diventa una scelta fra tre
  (etichette dal vocabolario); il pannello componenti mostra l'esposizione per esteso; nel drawer
  fattura l'espansione del kit mostra prezzo e importo dei valorizzati.

## 6. Decisioni di Tid (2026-10-01)

| # | Domanda | Esito |
| --- | --- | --- |
| E-1 | Booleano o tre valori? | ✅ **Tre valori**: `NASCOSTO` / `DESCRITTIVO` / `VALORIZZATO` (§3) |
| E-2 | Kit senza resto (tutto valorizzato) | ✅ **Strada a**: la riga del kit resta come intestazione senza importo |
| E-3 | Fatture già emesse | ✅ **Nessun riguardo**: su dbdev sono di test. La vista vale per tutte |

## 7. Fuori perimetro, dichiarato

* Un'esposizione decisa **per documento** (sovrascrivere il catalogo su una riga d'ordine): oggi è
  proprietà della distinta, e resta così finché qualcuno non porta un caso.
* La stampa di preventivi, ordini e DDT: i loro template mostrano i componenti con un'altra logica,
  da guardare a parte.
