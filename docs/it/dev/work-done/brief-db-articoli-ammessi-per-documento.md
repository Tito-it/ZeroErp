# Brief DB — Quali articoli ammette un documento: una regola sola, per il picker e per il guard

## ⏭️ Chi riparte — aggiornato al 2026-10-23 (chiuso)

**Riparte: nessuno. Brief chiuso e archiviato** (2026-10-23): DB (§9.1…§9.5, §9.8), BE/FE (§9.7, §9.8.7) e collaudo a video di Tid (§9.7.4, tutti e nove i punti) fatti. Smoke verde: `smoke-test-preventivi-smistamento-ordine.sh`, col passo 2-bis sul picker, gira dentro `scripts/smoke-baseline.sh`, e la corsa di Tid non ha regressioni (§9.7.5). Restano fuori, ciascuno nella sua sede: il ponte di `script.fn_articolo_riga_contesto` (lo ritira [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md)); D-5, le righe d'acquisto (§8.4), rinviata al cantiere `acquisti`; l'elenco dei documenti nel rifiuto `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` (§9.8.7), aggiunta del solo FE se servirà.

| #            | Chi              | Che cosa                                                                                                                                                                                                                           | Dove           | Aspetta                 |
| ------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------- |
| 1            | Tid              | ✅ decisioni prese: A-1…A-9 (2026-10-12), D-1…D-4 e D-6 (2026-10-13); D-5 rinviato                                                                                                                                                  | §8.6           | —                       |
| 2            | BE               | ✅ P-1 risposta (2026-10-13): la testata nasce sempre prima                                                                                                                                                                         | §8.6, P-1      | —                       |
| 3            | Tid              | ✅ Lotto 1 applicato, pgTAP verdi (2026-10-13)                                                                                                                                                                                      | §9.1           | —                       |
| 4            | Tid              | ✅ Lotto 2 applicato (`20261013-07 → -13`, 2026-10-13); baseline di `vendite`: 8 regressioni, analizzate                                                                                                                            | §9.2, §9.2.1   | —                       |
| 4a           | Tid              | ✅ `20261013-14` applicato, pgTAP verdi, nessuna regressione (2026-10-13)                                                                                                                                                           | §9.2.1         | —                       |
| 4b           | ✅ DB/Tid         | Lotto 3a scritto, provato e applicato (2026-10-13)                                                                                                                                                                                 | §9.3.1         | —                       |
| 4c           | Tid              | ✅ pgTAP della 3a su dbdev, verdi (2026-10-13)                                                                                                                                                                                      | §9.3.1         | —                       |
| 4d           | ✅ DB             | Lotto **3u** (articolo usato, A-10) scritto e provato (2026-10-13)                                                                                                                                                                 | §9.3.2         | —                       |
| 4e           | Tid              | ✅ 3u applicata (`20261013-47 → -52` + CSV), pgTAP verdi (2026-10-13)                                                                                                                                                               | §9.3.2         | —                       |
| 4f           | ✅ DB             | Lotto **3b** (offerta e contratto) scritto e provato (2026-10-13)                                                                                                                                                                  | §9.3.3         | —                       |
| 4g           | Tid              | ✅ 3b applicata (`20261013-55 → -58` + CSV + locales), nessuna regressione (2026-10-13)                                                                                                                                             | §9.3.3         | —                       |
| 4h           | Tid              | ✅ A-8-bis (2026-10-13): i lettori del listino passano a `config.tipi_entita` col giro BE/FE                                                                                                                                        | §9.3.3, §9.6   | —                       |
| 4i           | ✅ DB             | Lotto **3c** (versione di listino e distinta) scritto e provato (2026-10-13)                                                                                                                                                       | §9.3.4         | —                       |
| 4j           | Tid              | ✅ 3c applicata (`20261013-59 → -61` + CSV + locales), pgTAP verdi (2026-10-13)                                                                                                                                                     | §9.3.4         | —                       |
| 4k           | ✅ DB             | Lotto **4** (il picker, la promo) scritto e provato; Lotto **5** (doc) scritto (2026-10-14)                                                                                                                                        | §9.4, §9.5     | —                       |
| 4l           | Tid              | ✅ Lotto 4 applicato (`20261014-01 → -05` + `codici_errore.csv`, `messaggi_errore.csv` + locales), pgTAP verdi (2026-10-14)                                                                                                         | §9.4           | —                       |
| 4m           | ✅ DB             | D-7 (Tid, 2026-10-14: sì): `20261014-06` + codice + locales, scritto e provato                                                                                                                                                     | §9.4.1         | —                       |
| 4n           | Tid              | ✅ `20261014-06` applicato (+ `codici_errore.csv`, `messaggi_errore.csv` + locales), pgTAP verdi (2026-10-14)                                                                                                                       | §9.4.1         | —                       |
| 5            | ✅ BE/FE          | giro del §9.6 (2026-10-14): policy e ripieghi, lookup e `ArticoloLookup` sulla sede unica, ritiro dei filtri liberi, scheda articolo e correzione di struttura, doc                                                                | §9.7           | —                       |
| 5a           | ✅ DB             | R-DB-2: la nota di `E_ARTICOLO_SOLO_COMPONENTE` nel CSV (2026-10-18)                                                                                                                                                               | §9.8.2         | —                       |
| 5a-bis       | ✅ **Tid**        | **A-8-ter** (2026-10-18): l'A-8-bis (R-DB-1) esce da questo brief (strada 1); la grammatica unica (strada 3) è la direzione, nel suo brief                                                                                         | §9.8.3         | —                       |
| 5b           | ~~sessione BE~~  | ~~il pezzo BE dell'A-8-bis~~: cade con l'A-8-ter (strada 1)                                                                                                                                                                        | §9.8.3         | —                       |
| 5c           | ✅ DB             | **R-DB-3** scritto e provato (2026-10-18): `20261018-70`, `-71`, pgTAP nuovo                                                                                                                                                       | §9.8.1         | —                       |
| 5c-bis       | Tid              | ✅ `20261018-70`, `-71` applicati, pgTAP verdi (2026-10-18)                                                                                                                                                                         | §9.8.1         | —                       |
| 5c-ter       | ✅ DB             | **A-11** (Tid, 2026-10-18: strada «a»): `20261018-72` + codice `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, scritto e provato; §9.8.5 chiuso                                                                                               | §9.8.4, §9.8.5 | —                       |
| 5c-quater    | Tid              | ✅ `20261018-72` e CSV applicati (2026-10-18); la corsa ha trovato due rossi (§9.8.6)                                                                                                                                               | §9.8.4         | —                       |
| 5c-quinquies | ✅ DB             | i due rossi corretti: `20261018-73`, `-74`, fixture di `test-articolo-colonne-struttura-v1`                                                                                                                                        | §9.8.6         | —                       |
| 5c-sexies    | Tid              | ✅ `20261018-73`, `-74` applicati, pgTAP verdi (2026-10-18)                                                                                                                                                                         | §9.8.6         | —                       |
| 5d           | ✅ sessione BE/FE | (2026-10-18) `struttura_correggibile` nel dettaglio dell'articolo dalla sede, ritiro di `COLONNE_STRUTTURA`; policy e ripiego di `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`; **R-BE-1**, il salvataggio con correzione in una transazione | §9.8.7         | —                       |
| 6            | ~~Tid~~ | ~~collaudo a video, con la correzione di struttura in un salvataggio solo (§9.8.7)~~ ✅ 2026-10-23 | §9.7.4, §9.8.7 | — |
| 7            | ~~chi chiude~~ | ~~archiviazione del brief in `work-done/` e riga di PROJECT_CONTEXT~~ ✅ 2026-10-23; il ponte resta, e lo ritira [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md) | —              | — |

**Decisioni aperte di Tid: nessuna** (A-8-ter decisa il 2026-10-18, §9.8.3). ✅ **Committato il 2026-10-18 (sessione BE, `dev/backend-tid`, `22e31580e`)**: il giro 5d (§9.8.7), la decisione A-8-ter e il collaudo 8-9 in questo documento. Da committare: niente. ✅ **Committato il 2026-10-18 (sessione DB, `dev/db-tid`)**: `20261018-70` … `-74`; i pgTAP `catalogo/test-articolo-colonne-struttura-v1` e `catalogo/test-articolo-correzione-righe-aperte-v1`; in `codici_errore.csv` la nota di `E_ARTICOLO_SOLO_COMPONENTE` e il codice nuovo `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, in `messaggi_errore.csv` il suo messaggio (id 1361); i manual `catalogo/manual/fn_articolo_colonne_struttura`, `fn_articolo_righe_vive_non_ammesse` (nuovi), `fn_articolo_correggi_struttura`, `trgfn_articoli_guard_struttura_se_usato`; la doc generata del catalogo; questo documento.
✅ **Committato il 2026-10-14 (sessione BE, `dev/backend-tid`)**: il giro del §9.7 con la sua revisione (§9.7.5). Decisioni prese prima: D-7 il 2026-10-14; A-8-bis il 2026-10-13 (rivista dall'A-8-ter); D-5 rinviato al cantiere acquisti. Da guardare (scelte del team DB dentro le decisioni prese, §9.4): la check divisa in due metà per R-5; il composito ammesso nella promo (D-6). ✅ **D-7 committata il 2026-10-14** (§9.4.1: `20261014-06`, CSV, locales, pgTAP del picker e due fixture, manual, guide, questo documento). ✅ Lotti 4 e 5 committati il 2026-10-14 (`7797acc42`); il Lotto 3c in `42bc5d2e0`. ✅ **Committati il 2026-10-13 (sessione DB)**: Lotti 1, 2 e `20261013-14` (prima); poi Lotti **3a, 3u, 3b** (`20261013-40 … -52`, `-55 … -58`), CSV dei codici, chiavi dei locales, baseline B-7, pgTAP nuovi e corretti, manual, guide e questo documento. ⚠️ **Restano fuori, col lavoro che ne porta la causa**: i cinque file pgTAP misti con un altro cantiere (`test-fn-list-ddt-da-pushare-contatore-v1`, `test-vw-dash-backlog-resi-v1`, `test-vw-partite-merce-v1`, `test-vw-resi-da-accreditare-contatore-v1`, `test-vw-situazione-merce-ordine-v1`); i quattro SORGENTE_POLIMORFA del §9.2.1 erano gia' fuori. Fuori anche, perche' di altri cantieri: `20261013-53` (lettori dell'emittente della bolla) col suo pgTAP e la sua doc, il D32, la pulizia di `baseline-rossi-scratch.tsv`.

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-11. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§7), che **attende** la consegna DB.
> **Origine:** collaudo a video di Tid, 2026-10-11 («come capisco quali articoli sono una
> tantum?»), poi la sua richiesta: *«la ricerca dell'articolo mostri solo gli articoli che quel
> documento può usare»*. Il caso che l'ha aperto è nel §H di
> [brief-db-offerta-emissione-ed-erogazione](../work-done/brief-db-offerta-emissione-ed-erogazione.md): un
> articolo scelto dal picker, rifiutato dopo.
> **Stato (2026-10-23): chiuso.** Lato DB chiuso e committato (Lotti 1-5, poi R-DB-2, R-DB-3, A-11: §9.8); giro BE/FE fatto e committato (§9.7 il 2026-10-14, 5d il 2026-10-18: §9.8.7); A-8-ter decisa (§9.8.3); collaudo a video di Tid fatto il 2026-10-23 (§9.7.4). Archiviato in `work-done/`.

## 1. Il principio

**Quali articoli può usare una riga lo dice il database, e lo dice una sola volta.** La stessa
regola deve decidere due cose: che cosa il picker propone e che cosa il guard rifiuta. Un picker
che propone un articolo che poi viene rifiutato fa perdere tempo all'operatore. Un picker che
nasconde un articolo che il DB accetterebbe applica una regola che sta solo nel frontend, cioè una
regola che di fatto non esiste.

Il precedente esiste già, ed è il listino del documento:
`vendite.fn_listini_selezionabili` legge i valori del form e riusa il predicato del guard
(`script.fn_check_listino_documento`). Lo stesso schema serve per gli articoli.

## 2. Oggi: chi decide

* **Il picker** è `frontend/src/catalogo/components/ArticoloLookup.vue`, letto dal backend in
  `catalogo_repository.lookup_articoli`. **È la maschera chiamante a scegliere i filtri**
  (`filtri.soloComponenti`, `filtri.compositi`, `filtri.gestitiAMagazzino`, `escludiDestinazione`).
  Ogni maschera tiene così la sua copia della regola, e le copie non sono uguali ai guard.
* **Il DB** chiede su tutte le righe che l'articolo sia attivo (`E_ATTIVO_REQUIRE`). Regole sulle
  proprietà dell'articolo ci sono solo su alcune tabelle (§3).

## 3. Il censimento (fatto datato, 2026-10-11, dalla doc `dbzero` e dai componenti FE)

| Documento (righe)                             | Che cosa rifiuta il DB sull'articolo                                                                                                                                                                                                                    | Che cosa filtra il picker                                                                    | Scarto                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Preventivo** (`preventivi_righe`)           | natura con destinazione CONTRATTO (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`, predicato **dentro** `trgfn_preventivi_righe_set_natura_vendita`); composito con BoM vuota (`E_DOC_COMPOSITO_BOM_VUOTA`, all'init dei componenti)                           | `escludiDestinazione: ['CONTRATTO']`, `soloComponenti: 'escludi'` (`PreventiviRigaForm.vue`) | natura allineata; «solo componente» lo rifiuta solo il FE                                          |
| **Offerta** (`offerte_commerciali_eccezioni`) | tipologia fuori utility (`E_RIGA_TIPOLOGIA_FUORI_UTILITY`); nessuna erogazione ammessa (`E_RIGA_EROGAZIONE_OBBLIGATORIA`); AGGIUNTA di un articolo già in listino (`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`); ESCLUSIONE di un figlio di bundle; BoM vuota | `soloComponenti: 'escludi'` (`RigheEccezioniDrawer.vue`)                                     | 🔴 il picker propone articoli fuori utility e già in listino: il motivo compare **dopo** la scelta  |
| **Contratto** (`contratti_righe`)             | come l'offerta                                                                                                                                                                                                                                          | stesso drawer                                                                                | 🔴 come l'offerta                                                                                   |
| **Ordine di vendita** (`ordini_righe`)        | **nessuna regola sulla natura**; BoM vuota                                                                                                                                                                                                              | `soloComponenti: 'escludi'` (`OrdiniRigaForm.vue`)                                           | 🔴 **manca la regola**: si possono mettere servizi una tantum e ricorrenti in un ordine             |
| **Bolla** (`ddt_righe`)                       | **nessuna regola sulla natura**; il magazzino lo giudica `fn_check_riga_magazzino` all'emissione                                                                                                                                                        | `soloComponenti: 'escludi'` (`DdtRigaForm.vue`)                                              | 🔴 come l'ordine                                                                                    |
| **Versione di listino** (`listini_righe`)     | tipologia mancante o diversa da quella del listino (`E_ARTICOLO_TIPOLOGIA_MANCANTE` / `_INCOMPATIBILE`); composito in INSERT (`E_LISTINO_RIGA_COMPOSITO_VIETATO`)                                                                                       | `soloComponenti: 'escludi'` (`VersioneDrawer.vue`)                                           | 🔴 il picker propone articoli di qualunque tipologia                                                |
| **Distinta** (`catalogo.articoli_componenti`) | IVA del componente diversa da quella del padre (`E_BOM_IVA_DISCORDANTE`); componente uguale al padre (CHECK)                                                                                                                                            | `compositi: 'escludi'` (`ArticoloBomDrawer.vue`)                                             | 🔴 il picker propone componenti con IVA diversa; il composito come componente lo rifiuta solo il FE |
| **Promo** (`promo_articoli`)                  | nessuna regola sull'articolo                                                                                                                                                                                                                            | `soloComponenti: 'escludi'`                                                                  | regola solo FE                                                                                     |
| **Oneri di commessa**                         | articolo senza causale onere (`E_ONERE_ARTICOLO_MANCANTE`)                                                                                                                                                                                              | `solo_oneri`                                                                                 | ✅ allineato                                                                                        |
| **Inventari / rettifiche**                    | gestito a magazzino, lotto, seriale: `fn_check_riga_magazzino` al piano, non al salvataggio                                                                                                                                                             | `gestitiAMagazzino: 'solo'`                                                                  | ✅ allineato al posting                                                                             |
| Resi, fatture                                 | l'articolo arriva dalla riga d'origine                                                                                                                                                                                                                  | nessun picker                                                                                | —                                                                                                  |
| Acquisti (`ordini_righe`, `ddt_righe`)        | solo articolo attivo                                                                                                                                                                                                                                    | FE non ancora fatto                                                                          | da decidere ora, non dopo (§5, D-5)                                                                |

Due fatti che attraversano tutta la tabella:

* **`is_solo_componente` non lo legge nessun guard di riga.** Lo leggono solo i trigger della BoM.
  Il codice `E_ARTICOLO_SOLO_COMPONENTE` («non inseribile come riga autonoma») esiste, ma nessun
  documento lo solleva: la regola c'è solo nel frontend.
* **La natura di vendita** (`config.nature_vendita.destinazione_tipo`: MERCE → ORDINE,
  SERVIZIO_UNA_TANTUM → COMMESSA, SERVIZIO_RICORRENTE → CONTRATTO) **la applica il DB solo sul
  preventivo**, e solo nella forma «non CONTRATTO». Su offerta e contratto entra solo in modo
  indiretto, tramite `fn_articolo_erogazioni` quando manca la tipologia.

## 4. I difetti, sul modello

* **D-A. Regole che esistono solo nel frontend o non esistono affatto.** Ordine e bolla senza
  natura; «solo componente» su nessuna riga; il composito come componente di distinta. Sono buchi
  del modello, e un picker non li chiude.
* **D-B. La regola scritta due volte.** Il picker la riceve dalla maschera, il guard la ha nel
  trigger. Le due copie divergono già (offerta, contratto, listino, distinta).
* **D-C. Predicati chiusi dentro i trigger.** La natura del preventivo, la tipologia del listino e
  l'IVA della distinta sono scritte dentro il trigger, e nessuno le può chiedere prima di scrivere.

## 5. Da decidere (team DB, poi Tid)

| #       | Domanda                                         | Proposta                                                                                                                                                                                             |
| ------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **D-1** | Ordine di vendita: quali nature?                | solo **MERCE** (destinazione ORDINE), come dice il modello dello smistamento. Il ramo da preventivo porta già solo merce                                                                             |
| **D-2** | Bolla: quali nature?                            | come l'ordine. Da decidere se un servizio «da consegnare con la merce» (trasporto, montaggio) debba stare in bolla: se sì, va scritto come natura o come flag, non tollerato                         |
| **D-3** | «Solo componente» su una riga di documento      | rifiutato da **ogni** riga autonoma (`E_ARTICOLO_SOLO_COMPONENTE`, il codice c'è già); ammesso solo come componente                                                                                  |
| **D-4** | Componente composito in distinta (BoM annidata) | da decidere: oggi il DB lo accetta e il FE lo nasconde. Se no, guard sulla BoM; se sì, il picker smette di nasconderlo                                                                               |
| **D-5** | Acquisti                                        | la stessa sede vale anche per loro, da subito (`modo_approvvigionamento`: un articolo prodotto internamente si compra?). Il FE acquisti ancora non c'è: è il momento di non scrivere una terza copia |
| **D-6** | Promo                                           | regola nel DB (le stesse esclusioni del listino?) oppure nessuna regola, e allora il picker non filtra                                                                                               |

## 6. Richiesta

| #       | Cosa                                                | Dettaglio                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R-1** | **Una `fn_check_*` per ogni regola sull'articolo**  | estrarre dai trigger i predicati di D-C (natura per destinazione, tipologia del listino, IVA della BoM, composito in listino), più quelle nuove di D-1…D-4. Ogni check restituisce i motivi (codice + campo), come `fn_check_riga_erogazione`. **I guard le chiamano**: il guard rifiuta col primo motivo                                                                                                                                                                                                                                               |
| **R-2** | **La sede unica: «articoli ammessi dal documento»** | una funzione di lettura (nome a scelta del team DB, per esempio `catalogo.fn_articoli_ammessi(p_documento, p_contesto jsonb, p_search, p_limit)`) che, dato il tipo di documento e i valori del form (utility, listino o versione, padre della distinta, magazzino, tipo eccezione), restituisce gli articoli che **le stesse check** di R-1 ammettono. Sul modello di `fn_listini_selezionabili`: valori del form, non l'id del documento, così funziona anche in creazione. Vocabolario dei documenti dichiarato (CHECK o tabella), non stringhe nude |
| **R-3** | Riuso dei BB esistenti                              | `script.fn_check_riga_erogazione` (tipologia nella utility), `vendite.fn_articolo_erogazioni` (zero combinazioni = non ammesso), `vendite.fn_documento_listino_operativo` (AGGIUNTA già in listino), `script.fn_check_esclusione_articolo_documento`, `script.fn_check_riga_magazzino`. Nessuna seconda copia                                                                                                                                                                                                                                           |
| **R-4** | **Il motivo di un articolo escluso**                | da valutare: oltre a «chi è ammesso», poter chiedere «perché questo no» (l'operatore cerca un codice preciso e non lo trova). Proposta: la stessa funzione, con un parametro che restituisce anche gli esclusi con il loro motivo, oppure una lettura per singolo articolo                                                                                                                                                                                                                                                                              |
| **R-5** | Prestazioni                                         | la lettura gira a ogni tasto premuto nel picker: EXPLAIN sul DB vero, con le check valutate solo sugli articoli che passano la ricerca testuale (il tetto del lookup resta di 50)                                                                                                                                                                                                                                                                                                                                                                       |
| **R-6** | Le righe già scritte                                | i guard nuovi (D-1…D-4) scattano all'INSERT e quando cambia l'articolo. Le righe esistenti si intercettano al primo passo che le usa (emissione, smistamento, trasformazione), con il motivo, come nel §H del brief offerta                                                                                                                                                                                                                                                                                                                             |
| **R-7** | pgTAP                                               | per ogni documento: l'articolo ammesso compare e si scrive; l'articolo escluso non compare **e** il guard lo rifiuta con lo stesso codice (picker e guard non possono dissentire); creazione senza id del documento                                                                                                                                                                                                                                                                                                                                     |
| **R-8** | Doc                                                 | manual delle funzioni nuove; guide di preventivi, offerte, ordini e bolle («quali articoli si possono mettere»); `linee-guida-sql` se nasce una regola generale («ogni picker di riga legge la sede unica»)                                                                                                                                                                                                                                                                                                                                             |

## 7. Lato BE/FE, a consegna DB fatta

* **BE**: il lookup articoli riceve il documento e il contesto, e legge la sede unica di R-2. I
  parametri liberi (`escludi_destinazione`, `is_solo_componente` per le righe di documento)
  **si ritirano**: la regola non la sceglie più il chiamante. Restano i filtri che non sono regole
  (ricerca, attivi/inattivi per le liste di consultazione come movimenti e disponibilità).
* **FE**: `ArticoloLookup` riceve `documento` e il contesto del form (come `ListinoDocumentoSelect`
  riceve utility ed emittente), al posto dei filtri scelti dalla maschera. Si ricarica quando
  cambia il contesto. Le maschere da riallineare sono le righe di preventivo, offerta, contratto,
  ordine, bolla, versione di listino, distinta e promo.
* Se R-4 si fa: un articolo cercato e non ammesso mostra il motivo nel footer del picker, invece
  di un elenco vuoto senza spiegazione.
* Catalogo BB frontend e backend aggiornati: `ArticoloLookup` cambia contratto.

## 8. Analisi del team DB (`dev/db-tid`, 2026-10-12)

> Verificata sulla doc auto-generata (`docs/it/dbzero/`), non sugli YAML. Tutto quello che segue
> è **struttura** (corpi di funzione, trigger, nullabilità), non popolazione.

### 8.1 Il principio regge, ma le domande sono due, non una

Il principio del §1 è giusto, e il precedente (`fn_listini_selezionabili`) anche. Però il picker e
il guard **non fanno la stessa domanda**:

* il **picker** chiede: *«esiste un modo di usare questo articolo in questa riga?»*;
* il **guard** chiede: *«questa riga, con tutti i suoi campi, è valida?»*.

Il guard giudica anche campi che al momento della scelta non esistono ancora (erogazione, fonte,
quantità). Per questo i motivi vanno divisi in due famiglie:

| Famiglia               | Dipende da                                  | Esempio                                                           | Chi la usa         |
| ---------------------- | ------------------------------------------- | ----------------------------------------------------------------- | ------------------ |
| **motivi di articolo** | solo l'articolo e il contesto del documento | `TIPOLOGIA_FUORI_UTILITY`, natura, solo componente, IVA della BoM | picker **e** guard |
| **motivi di riga**     | anche gli altri campi della riga            | `EROGAZIONE_FUORI_PERIMETRO` (combinazione erogazione/fonte)      | solo guard         |

L'R-7 («l'escluso non compare **e** il guard lo rifiuta con lo stesso codice») vale solo per la
prima famiglia, e va scritto così.

⚠️ C'è un motivo di articolo che **oggi non è scritto da nessuna parte**: «l'articolo non ha
nessuna erogazione ammessa» (`fn_articolo_erogazioni` vuota). L'R-3 lo nomina come criterio del
picker, ma `script.fn_check_riga_erogazione` non lo emette: giudica una combinazione precisa. Se lo
calcola solo la funzione del picker, è di nuovo una regola con una sede sola **sbagliata** (D-B).
Va aggiunto alla check come motivo di articolo, e il guard lo solleva come gli altri.

### 8.2 Il censimento del §3, verificato

Confermato: preventivo (natura solo «non CONTRATTO», dentro `trgfn_preventivi_righe_set_natura_vendita`),
offerta e contratto (perimetro, obbligo di erogazione, AGGIUNTA, figlio di bundle), ordine e bolla
senza regole sull'articolo, listino (tipologia, composito in INSERT), promo (il solo guard,
`trgfn_promo_articoli_guard_data_driven`, giudica le date), acquisti (solo `attivo`).
`is_solo_componente` non lo legge nessun guard di riga. Correzioni e aggiunte:

* **La BoM.** I due guard su `catalogo.articoli_componenti` (`…_guard_solo_componente`,
  `…_guard_is_composito`) guardano il **padre** (`prodotto_id`), non il componente. Quindi è vero
  che il DB accetta un composito come componente (D-4). E c'è già un guard dal lato articolo:
  `trgfn_articoli_guard_flags_struttura_bom_attiva` impedisce di cambiare `is_solo_componente`
  se l'articolo è in una BoM attiva. Sui documenti, niente di simile (§8.3, punto 3).
* **La natura non è mai NULL.** `catalogo.articoli.natura_vendita_id` è `NOT NULL DEFAULT 1`. Il
  commento di `trgfn_preventivi_righe_set_natura_vendita` («natura NULL, transitorio pre-backfill»)
  è stantio: debito di doc, da correggere al prossimo giro sulla funzione. Per D-1 non c'è un caso
  NULL da decidere.
* ~~**Il predicato «natura → ORDINE» esiste già** … per la regola del 2 si estrae nello stesso
  giro.~~ ⚠️ **Corretto il 2026-10-13 (team DB, in consegna).** `destinazione_tipo = 'ORDINE'` non
  è una regola ricopiata: è la lettura di una colonna di vocabolario (`config.nature_vendita`, con
  il suo CHECK), e la regola sta già nel dato. Se una natura cambia destinazione, le tre viste di
  smistamento e i guard nuovi la seguono senza toccare codice. Una funzione al posto del confronto
  non toglierebbe nessuna divergenza e renderebbe opache le viste per il presidio della catena RLS.
  Ciò che va scritto una volta sola è **quale tipo di riga ammette quale destinazione**: sta nella
  check per tipo di riga (A-2).
* **Ordine e bolla non hanno la natura in riga.** Il preventivo la congela (`natura_vendita_id`
  sulla riga, sovrascritta dal trigger); `ordini_righe` e `ddt_righe` no. Un guard D-1 leggerebbe
  la natura **viva** dell'articolo. Decisione A-4.
* **OVERRIDE ed ESCLUSIONE fuori listino: buco confermato (verifica del 2026-10-12).** Fra i
  trigger di `contratti_righe` e `offerte_commerciali_eccezioni` nessuno pretende che l'articolo di
  un'OVERRIDE o di un'ESCLUSIONE stia nel listino operativo del documento: c'è solo il contrario,
  per l'AGGIUNTA. Il modello invece lo dice in due posti:
  `script.fn_check_listino_cambiabile` («OVERRIDE o ESCLUSIONE senza listino non vogliono dire
  niente») e `vendite.fn_documento_righe_preview`, che le applica **sopra** le righe del listino
  (PARTE 1, `LEFT JOIN` delle eccezioni sulle righe di listino). Conseguenza: un'OVERRIDE di un
  articolo fuori listino si scrive, ma **non compare** nel drawer (non sta né nella PARTE 1 né
  nella PARTE 2, che è solo per le AGGIUNTE). È una riga invisibile, ed è un buco D-A (A-5).
  Il FE non lo provoca: in `RigheEccezioniDrawer.vue` il picker è acceso **solo per l'AGGIUNTA**,
  mentre OVERRIDE ed ESCLUSIONE partono dalla riga di listino. Quindi il picker non deve rovesciare
  niente: la regola mancante è solo del guard.
* **Il composito nella versione di listino non è un rifiuto.** `E_LISTINO_RIGA_COMPOSITO_VIETATO`
  vieta il composito nella **tabella** `listini_righe`, perché il suo prezzo sta in
  `listini_righe_componenti` (somma dei componenti). Nella **versione** il composito è ammesso, e
  per un'altra strada: `VersioneDrawer.vue` lo cerca apposta (`compositi: 'qualsiasi'`) e apre il
  dialog del bundle. La sede unica, per la versione di listino, deve dire «ammesso, come bundle»,
  non «escluso».
* **Le affermazioni del §3 sul frontend sono confermate** (verifica del 2026-10-12, lettura dei
  soli file citati): i filtri passati ad `ArticoloLookup` sono quelli scritti nel §3, compresi la
  promo (`PromoArticoloDrawer.vue`, `soloComponenti: 'escludi'`) e la distinta
  (`compositi: 'escludi'`).

### 8.3 I difetti d'impianto

1. **Valori del form o testata salvata.** `fn_listini_selezionabili` lavora sui valori del form
   perché serve il form della **testata**, dove l'id non c'è ancora. Il picker di **riga** è un
   altro caso: il guard giudica la riga contro la testata **salvata**
   (`fn_check_riga_erogazione` legge `utility_id` dall'id; l'AGGIUNTA passa da
   `fn_documento_listino_operativo(documento, id)`). Se il picker prendesse utility e listino dal
   form, con una modifica di testata non ancora salvata picker e guard dissentirebbero: è
   esattamente il difetto da togliere. E l'R-3 così com'è non si può fare, perché i BB da riusare
   vogliono l'id. Proposta: per le righe la sede unica riceve **l'id del documento** (o del padre
   della distinta, o della versione di listino: esistono tutti quando si scrive una riga), più i
   soli valori che stanno sulla riga (tipo di eccezione). Il «creazione senza id» dell'R-7 resta
   per i casi in cui la riga nasce prima della testata, **se** esistono (domanda P-1 al BE).
2. **Una check per regola o una per tipo di riga.** L'R-1 chiede una `fn_check_*` per regola,
   chiamata dai guard. Se ogni regola ha il suo trigger, il motivo che l'operatore vede quando ne
   viola due è deciso dall'**ordine dei nomi dei trigger**, mentre il picker (e l'R-4) ne
   comporrebbe uno suo: lo stesso articolo, due motivi diversi. È il caso del §12.5.2 delle
   linee guida («l'ordine dell'array è il contratto»). Proposta: per regola un **predicato** (il
   building block), e per **tipo di riga** una check che li compone in ordine dichiarato; un solo
   guard per tabella la chiama, e la sede unica chiama la stessa.
3. **Le regole dipendono da dati che stanno fuori dalla riga.** È la lezione del §H del brief
   offerta, e vale per tutte le regole nuove: natura, solo componente, tipologia, IVA e composito
   sono proprietà dell'articolo e si possono cambiare dopo. L'R-6 dice «al primo passo che le
   usa» ma non elenca i passi: per offerta e contratto li ha scritti il §H (emissione, push,
   attivazione), per ordine e bolla mancano (conferma, generazione della bolla, emissione). C'è
   anche la strada opposta, già in uso: il guard **dal lato articolo** (come
   `trgfn_articoli_guard_listino_se_composito`, `…_guard_iva_bom_attiva`,
   `…_guard_flags_struttura_bom_attiva`). Le due strade vanno scelte regola per regola (A-3).
4. **I verbi che attraversano i guard nuovi.** Le righe non le scrive solo l'operatore. Scrivono
   `ordini_righe`, `ddt_righe`, `contratti_righe` e le righe di offerta e preventivo:
   `fn_push_preventivo_a_ordine`, `fn_genera_ddt_da_ordine`, `fn_genera_ddt_riconsegna`,
   `fn_push_offerta_a_contratto`, `fn_crea_revisione_offerta`, `fn_crea_revisione_preventivo`.
   Un guard D-3 su `ordini_righe` rifiuterebbe a metà il push di un preventivo con un articolo solo
   componente, che oggi il preventivo **accetta**. Quindi la regola va prima sul documento
   d'origine, e la madre la verifica prima di scrivere (motivo all'operatore, non un errore a metà
   strada). Per la riconsegna (la riga copia il reso) va deciso se la regola vale: chi riconsegna
   restituisce ciò che è uscito, anche se l'articolo nel frattempo è cambiato (A-6).
5. **Prestazioni (R-5).** Una check PL/pgSQL chiamata per candidato, con il tetto di 50 applicato
   **dopo** il filtro, non si ferma a 50 valutazioni: se la ricerca trova molti articoli non
   ammessi, la funzione valuta tutti quelli trovati. I motivi di articolo vanno scritti come
   predicati di insieme (SQL che il pianificatore può mettere nel `WHERE`), e la check del guard si
   costruisce dagli stessi predicati. Altrimenti la regola si sdoppia di nuovo, in una copia lenta
   per il guard e una veloce per il picker.
6. **Il vocabolario dei documenti.** Le funzioni di oggi portano `p_documento text` nudo,
   **dichiarato** come debito (`fn_check_riga_erogazione`, `fn_check_esclusione_articolo_documento`,
   `fn_documento_listino_operativo`). Un vocabolario nuovo per questa sola funzione sarebbe una
   terza grammatica. Candidato da valutare: `config.tipi_entita` (codice a chiave, già usato per i
   bersagli degli errori). Se lo si adotta, le funzioni esistenti ci passano nello stesso giro.
7. **R-4 e la regola dei pulsanti.** Le linee guida (§12.1) dicono: *permesso ⇒ nascondi, stato ⇒
   disabilita col motivo*. Un articolo non ammesso non è un permesso. Proposta: **una sola**
   lettura, che restituisce i candidati della ricerca con una colonna `motivo` (`NULL` =
   ammesso), prima gli ammessi. Il FE decide come mostrarli (grigi con il tooltip, o solo quando
   la ricerca non trova ammessi). Così R-2 e R-4 non sono due strade per la stessa regola.

### 8.4 Sulle decisioni del §5

* **D-1 (ordine solo MERCE).** Giusto sul modello. Ma la regola sta sulla tabella e vale per ogni
  sorgente, non solo per il preventivo e il picker (`ordini_righe` ha più sorgenti, vedi
  `…_sorgenti_require_attivo`). Resta A-4 (natura congelata o viva).
* **D-2 (bolla). Verificato il 2026-10-12: il modello ha già una sede per i servizi della
  consegna, ed è la commessa.** Il push bolla → commessa (`vendite.fn_ddt_push_diagnosi`, «fonte
  unica dell'eleggibilità») porta in commessa la **merce consegnata**, da fatturare. I servizi una
  tantum vanno in commessa per natura (`SERVIZIO_UNA_TANTUM → COMMESSA`), e un addebito come il
  trasporto ha già una porta: l'onere di commessa (`vendite.fn_aggiungi_onere_commessa`, da un
  articolo-onere). Sulla testata della bolla il trasporto è un attributo
  (`causale_trasporto_id`, `modalita_addebito_trasporto_id`), non una riga. Proposta: la bolla
  ammette **solo MERCE**, come l'ordine.
  ⚠️ Resta un caso che il modello oggi non copre (A-9, ora in
  [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md)): l'ordine che si fattura alla
  conferma (`DDT_FATTURA_DA_ORDINE`) non passa mai da una commessa. Se l'ordine ammette solo merce
  (D-1), il trasporto da addebitare su quell'ordine non ha un posto.
* **D-3 (solo componente).** D'accordo, con le precondizioni del §8.3 (punti 3 e 4): prima sul
  preventivo, il verbo di push lo verifica, e dal lato articolo si decide se il flag si può
  cambiare quando l'articolo è in documenti aperti.
* **D-4 (BoM annidata).** Non è una scelta del picker: è una scelta sulla forma della distinta, e
  il resto del modello l'ha già fatta, per **un** livello (verifica del 2026-10-12):
  * **Nessuna lettura è ricorsiva.** Nella doc auto-gen non c'è un `WITH RECURSIVE` su
    `catalogo.articoli_componenti`. Le cinque `fn_*_riga_componenti_init` (preventivo, offerta,
    contratto, ordine, bolla) leggono i figli **diretti** del padre e li scrivono nelle tabelle dei
    componenti di riga.
  * **Le tabelle dei componenti di riga sono piatte.** `ordini_righe_componenti` (e le sorelle)
    hanno la riga padre e il componente, ma nessuna colonna «componente padre». Un componente che è
    a sua volta un composito ci finisce come **una** riga, con un solo prezzo, e i suoi figli non
    li vede nessuno: né il magazzino quando la bolla scarica, né la fattura.
  * **Il prezzo del bundle è la somma di un livello.** `vendite.fn_espandi_listino_versione`
    calcola il bundle come somma dei componenti in `listini_righe_componenti`, che sono figli
    diretti.
  * **I cicli non li ferma nessuno.** L'unico vincolo è `chk_articoli_componenti_no_selfref` (A non
    contiene A). Con un livello solo un ciclo non si può costruire. Con più livelli sì (A contiene
    B, B contiene A), e ogni lettura che un giorno diventasse ricorsiva non finirebbe.

  Un argomento che **non** regge, per onestà: la coerenza dell'IVA. Il guard confronta padre e
  figlio diretti, ma l'uguaglianza si trasmette, quindi reggerebbe anche su più livelli.

  Accettare oggi la distinta annidata vuol dire accettare un dato che la vendita, il magazzino e
  la fattura trattano come se fosse un articolo semplice. Proposta: **rifiuto**, con un guard su
  `articoli_componenti` (il componente non può essere composito) e lo stesso guard dal lato
  articolo (un articolo che è componente non diventa composito: è lo schema di
  `trgfn_articoli_guard_flags_struttura_bom_attiva`). Il FE oggi lo nasconde già
  (`compositi: 'escludi'`): così il DB e il picker dicono la stessa cosa. La distinta a più
  livelli, se un giorno serve, è un cantiere suo, che tocca tutte le letture qui sopra.
* **D-5 (acquisti): rinviato alla ripartenza del cantiere acquisti** (Tid, 2026-10-12: il
  cantiere è fermo). Questo giro non tocca `acquisti.ordini_righe` né `acquisti.ddt_righe`. Da
  riprendere allora, con questi riferimenti:
  * la sede unica e la check componente di questo brief valgono anche lì: il documento d'acquisto
    si aggiunge al vocabolario dei documenti, senza scrivere una terza copia nel picker;
  * il criterio proposto nel §5 contraddice il vocabolario: `config.modi_approvvigionamento` si
    dichiara **ortogonale** alla natura («un assemblato può essere comprato finito»), e
    `NON_APPLICABILE` (prestazione) non vieta di comprare un servizio. Un divieto su
    `modo_approvvigionamento` non ha appoggio nel modello;
  * le regole che il modello sostiene già: articolo attivo, solo componente (D-3), magazzino per
    la bolla (`fn_check_riga_magazzino`).

  Il rimando va anche nel cantiere acquisti (PROJECT_CONTEXT, voce `acquisti`), perché chi lo
  riapre non parte da questo brief.
* **D-6 (promo).** Una promo su un articolo solo componente non si applica mai (non sta mai su una
  riga autonoma): rifiutarla costa poco ed evita un dato inutile. Sul composito vale la scelta
  del listino.

### 8.5 Sul brief stesso

* Mancava il blocco «⏭️ Chi riparte» (AGENTS.md): aggiunto in testa.
* Il perimetro (otto documenti più gli acquisti) si sovrappone al §H del brief offerta: H-R1 e
  H-R4 rileggono `fn_check_riga_erogazione` all'emissione e all'attivazione. La check componente
  del §8.3 punto 2 deve essere **quella** che usa il §H, altrimenti due giri scrivono due
  composizioni della stessa regola. Il §H va consegnato prima, o insieme.

### 8.6 Decisioni per Tid

| #           | Domanda                                                                                                                                           | Proposta del team DB                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A-1**     | Le righe ricevono l'id del documento (testata salvata), non i valori del form                                                                     | ✅ **Tid, 2026-10-12: sì**, l'id del documento. Resta P-1 al BE per il solo caso testata + righe in una chiamata                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **A-2**     | Una check componente per tipo di riga, un guard per tabella                                                                                       | ✅ **Tid, 2026-10-12: sì** (§8.3, punto 2): un predicato per regola, una check per tipo di riga con l'ordine dei motivi scritto, chiamata dal guard e dal picker                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **A-3**     | Per ogni regola nuova: guard dal lato articolo, o controllo ai passi successivi                                                                   | ✅ **Tid, 2026-10-12: misto.** «Solo componente» e «composito»: guard dal lato articolo (il flag non cambia se l'articolo è in righe di documenti aperti, come `trgfn_articoli_guard_flags_struttura_bom_attiva`). Natura: segue A-4. Tipologia (perimetro): ricontrollo ai passi, già deciso nel §H                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **A-4**     | Ordine e bolla congelano la natura in riga, come il preventivo?                                                                                   | ✅ **Tid, 2026-10-12: sì.** `natura_vendita_id` su `ordini_righe` e `ddt_righe`, scritta dal DB come sul preventivo; i verbi di copia (preventivo → ordine, ordine → bolla, riconsegna) la portano avanti. Chiude anche la natura di A-3: il cambio in anagrafica non tocca le righe scritte                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **A-5**     | OVERRIDE ed ESCLUSIONE pretendono l'articolo nel listino operativo                                                                                | ✅ **Tid, 2026-10-12: sì**, guard nuovo (buco confermato, §8.2): rifiuto se l'articolo non è nel listino operativo o se il documento non ha listino; all'INSERT e al cambio articolo; le righe già scritte le intercetta l'emissione, come il §H                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **A-6**     | La riconsegna (`fn_genera_ddt_riconsegna`) è esente dalle regole nuove                                                                            | ✅ **Tid, 2026-10-12: sì**, restituisce ciò che è uscito. L'esenzione si aggancia al legame con la riga di reso d'origine, non a un flag; la natura viaggia dalla riga d'origine (A-4) ⚠️ **Forma (Tid, 2026-10-13): la porta del verbo**, non il legame. Il legame col reso (`resi_righe_riconsegne`) nasce *dopo* la riga di bolla (FK su `ddt_riga_id`), quindi al controllo non c'è ancora; scriverlo prima vorrebbe una colonna d'origine su `ddt_righe` (seconda sede del ponte) o una FK differibile. Scelta: `zeroerp.ddt_riconsegna` = id del reso, accesa da `fn_genera_ddt_riconsegna`, stretta sugli articoli di quel reso (`20261013-41/-43`); precedente `zeroerp.ddt_riga_correggi_qta`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **A-7**     | Una lettura sola con il motivo per riga (R-2 + R-4)                                                                                               | ✅ **Tid, 2026-10-12: sì** (§8.3, punto 7): ammessi e non ammessi con la colonna `motivo` (NULL = ammesso), ammessi prima; il motivo dalla stessa check del guard (A-2); la resa a video la sceglie il FE                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **A-8**     | Vocabolario dei documenti su `config.tipi_entita`                                                                                                 | ✅ **Tid, 2026-10-12: sì.** Oggi (seed `80_data/sql/config/tipi_entita.csv`) 9 voci; mancano OFFERTA, bolla, versione di listino, distinta, promo, da aggiungere dal CSV. Le funzioni con `p_documento text` nudo (`fn_check_riga_erogazione`, `fn_check_esclusione_articolo_documento`, `fn_documento_listino_operativo`) ci passano nello stesso giro. ⚠️ In consegna: verificare che la distinta regga come entità (destinazione = scheda articolo)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **A-9**     | Il trasporto su un ordine che si fattura alla conferma (nessuna commessa)                                                                         | ✅ **Tid, 2026-10-12: brief a parte**, [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md). D-1 e D-2 vanno avanti. In **questo** brief resta un vincolo nuovo: un articolo-onere (`causale_onere_id` valorizzato) non può avere natura `MERCE` (oggi nasce col default `MERCE`, `e_cessione_beni = true`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **D-1**     | Ordine di vendita: quali nature                                                                                                                   | ✅ **Tid, 2026-10-13: solo MERCE**, da ogni sorgente. Il predicato «natura → ORDINE» si estrae e lo usano la vista `vw_preventivi_righe_smistabili_ordine` e il guard; natura congelata (A-4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **D-2**     | Bolla: quali nature                                                                                                                               | ✅ **Tid, 2026-10-13: solo MERCE**, stesso predicato di D-1. Dalla riga d'ordine la natura congelata viaggia (A-4); bolla a mano: dall'articolo alla scrittura; riconsegna esente (A-6). Servizi e addebiti passano dalla commessa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **D-3**     | «Solo componente» su una riga                                                                                                                     | ✅ **Tid, 2026-10-13: rifiutato da ogni riga autonoma** (preventivo, offerta, contratto, ordine, bolla, riga di listino) con `E_ARTICOLO_SOLO_COMPONENTE` (messaggio già adatto); ammesso come componente. Prima il preventivo, e i verbi di copia controllano prima di scrivere (§8.3, punto 4); guard dal lato articolo (A-3); riconsegna esente (A-6)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **D-4**     | Distinta annidata                                                                                                                                 | ✅ **Tid, 2026-10-13: rifiuto**, guard su `articoli_componenti` (il componente non è composito) e dal lato articolo (un componente non diventa composito) (§8.4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **D-5**     | Acquisti                                                                                                                                          | rinviato alla ripartenza del cantiere, con i riferimenti del §8.4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **D-6**     | Promo                                                                                                                                             | ✅ **Tid, 2026-10-13: una promo si crea solo se il calcolo del prezzo la può applicare.** Solo componente: rifiutata (il resolver salta la promo in contesto bundle, «STADIO PROMO OVERLAY (non applicato in contesto bundle)» in `fn_resolve_prezzo_listino_v2_esito`, e con D-3 non c'è prezzo standalone). Composito: in consegna si verifica se il kit riceve la promo; se no, rifiutata, e la promo sul kit diventa una richiesta a parte                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **A-10**    | I flag che decidono come si vende un articolo si possono cambiare dopo che l'articolo è stato usato?                                              | ✅ **Tid, 2026-10-13: no.** Cambiano troppe cose a valle (listini, ordini, bolle): invece di rincorrere le conseguenze (natura congelata, ricontrolli nei verbi di copia, porte), un articolo **usato** non cambia più i flag strutturali. **Usato** = compare in una riga di documento (preventivo, offerta, contratto, ordine, bolla, fattura, reso), in un listino, in una commessa o in un movimento di magazzino, **in qualunque stato** (anche chiuso o annullato: i documenti chiusi si rileggono). **Bloccate se usato**: `is_composito`, `is_solo_componente`, `natura_vendita_id`, `causale_onere_id`, `listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`, `requires_serial` (`codice` e `uom_id` lo sono già sempre). **Libere**: `iva_id` (l'aliquota cambia per legge, le righe hanno la loro), descrizioni, gruppi, conti, tempi, modo di approvvigionamento. **Via d'uscita**: un articolo nuovo (il ritiro del vecchio non è obbligatorio), più una **porta amministratore** per correggere un errore di caricamento. ⚠️ Gli articoli sono **unici per tutte le aziende** (nessun emittente né RLS nel catalogo, verificato il 2026-10-13): il predicato «usato» deve vedere i documenti di tutte, quindi SECURITY DEFINER, e il messaggio non nomina documenti che l'operatore non vede. ⚠️ La porta oggi esistente (`zeroerp.allow_lock_columns_override`) la accende qualunque sessione: quella amministratore vuole anche il controllo del ruolo. Un predicato solo, letto dal guard e dal form (`lock_columns_conditional`). Sostituisce il guard «solo componente in bozza» (`20261013-44/-45/-46`), chiude la decisione sui verbi di copia (un ordine confermato non trova un articolo cambiato) e il buco multi-azienda di quel guard. Lotto **3u** (§9.3), prima della 3b |
| **D-7**     | Il composito con la **distinta vuota** è un motivo della check per tipo di riga?                                                                  | ✅ **Tid, 2026-10-14: sì.** Motivo 2 (dopo il solo componente) di preventivo, ordine, bolla e di AGGIUNTA e OVERRIDE di offerta e contratto, codice nuovo `E_ARTICOLO_KIT_SENZA_COMPONENTI`; «vuoto» = nessun componente attivo a qualunque data, il caso legato alla data resta all'init (`E_DOC_COMPOSITO_BOM_VUOTA`). `20261014-06` (§9.4.1)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **A-8-ter** | L'A-8-bis (tre lettori del listino a `config.tipi_entita`) si fa come è scritto?                                                                  | ✅ **Tid, 2026-10-18: no, strada 1.** Esce da questo brief: spostarne tre moltiplicava i ponti (censimento nel §9.8.3). ⭐ La strada 3 (una grammatica sola per tutti i documenti) è la **direzione**, non un debito: si apre in [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md), col censimento al team DB. Il ponte di `fn_articolo_riga_contesto` resta fino a quel brief                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **A-11**    | Le righe già scritte di ordine e bolla (R-6): chi le ricontrolla, ora che la porta amministratore può cambiare la struttura di un articolo usato? | ✅ **Tid, 2026-10-18: strada «a»**: il verbo di correzione rifiuta una correzione che renderebbe non ammesse righe di documenti aperti. Nessuna logica per le righe nate prima dei guard: non c'è produzione. `20261018-72` (§9.8.4)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

**P-1 (al BE).** Esiste un flusso in cui una riga di documento si scrive prima che la testata
esista (una creazione testata + righe in una chiamata sola)? Se no, il «creazione senza id»
dell'R-7 non si applica alle righe.

✅ **Risposta (Tid e verifica sul codice, 2026-10-13): no.** La testata nasce sempre prima, al più
insieme alla prima riga:
* preventivo, ordine e bolla salvano la bozza della testata da soli
  (`frontend/src/core/composables/useDrawerAutosaveBozza.js`), e le righe compaiono dopo; i form di
  riga hanno l'id del padre come prop obbligatoria e scrivono su `/<documento>/{id}/righe/`;
* offerta, contratto, versione di listino e distinta aprono le righe solo su un documento salvato;
* **promo**: l'articolo si sceglie nel form che crea la promo, quindi non c'è un id padre. Non
  serve: le regole della promo (D-6) dipendono solo dall'articolo;
* **reso**: testata e righe in una chiamata (`resi_service.crea_reso`), ma le righe vengono dalla
  bolla, senza picker. Fuori da questo brief.

Quindi l'R-7 perde il caso «creazione senza id» per le righe. La sede unica riceve l'id del
documento (A-1); per la promo riceve solo il tipo di documento.

## 9. Consegna DB — il piano (team DB, 2026-10-13)

> Una consegna sola sarebbe troppo grande da applicare e da provare in un colpo. Si consegna a
> **lotti**: ognuno è applicabile e provabile da solo, e porta i suoi pgTAP, i codici e la doc.
> I lotti non toccano ciò che il lotto dopo cambia di nuovo.

| Lotto | Che cosa                                                                                                                                                                                                                                                                                             | Decisioni                         | Stato                                                                                                                                                                  |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Catalogo**: la distinta a un livello (guard sul componente e dal lato articolo), l'articolo-onere non è merce                                                                                                                                                                                      | D-4, A-9                          | ✅ applicato da Tid, pgTAP verdi, committato (2026-10-13) (§9.1)                                                                                                        |
| **2** | **Vocabolario e natura in riga**: le voci mancanti in `config.tipi_entita`; `natura_vendita_id` su `ordini_righe` e `ddt_righe`, scritta dal DB e portata dai verbi di copia                                                                                                                         | A-8, A-4                          | ✅ applicato da Tid con la correzione `-14`, pgTAP verdi, committato (2026-10-13) (§9.2, §9.2.1)                                                                        |
| **3** | **Le regole sulle righe** (diviso in 3a, 3u, 3b, 3c: §9.3): i predicati, la check per tipo di riga, un guard per tabella; natura su ordine e bolla, solo componente ovunque, OVERRIDE/ESCLUSIONE nel listino; «solo componente» dal lato articolo (poi l'articolo usato, A-10); la riconsegna esente | A-2, A-3, A-5, A-6, A-10, D-1…D-4 | ✅ applicato da Tid, verde, committato (2026-10-13). I passi successivi (R-6) restano al §H del brief offerta; la migrazione al vocabolario va col giro BE/FE (A-8-bis) |
| **4** | **La sede unica di lettura**: candidati della ricerca con il motivo, ammessi prima; la check divisa in contesto e motivi (R-5); promo                                                                                                                                                                | A-1, A-2, A-7, D-6                | ✅ applicato da Tid, pgTAP verdi (2026-10-14), da committare (§9.4)                                                                                                     |
| **5** | **Doc e richieste**: guide, manual, linee guida, richieste BE/FE del §7 aggiornate                                                                                                                                                                                                                   | R-8                               | ✅ scritto (2026-10-14) (§9.5, §9.6)                                                                                                                                    |

### 9.1 Lotto 1 — catalogo (✅ applicato da Tid il 2026-10-13, pgTAP verdi)

**ChangeSet** (in ordine di apply; nessuno applicato):

| ChangeSet                 | Cosa                                                                                                                                                                                                                                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261013-01`             | nuovo `catalogo.trgfn_articoli_componenti_guard_un_livello`: il componente di un legame attivo non è composito (`E_BOM_COMPONENTE_COMPOSITO`)                                                                                                                                         |
| `20261013-02`             | montaggio `trg_articoli_componenti_a10_guard_is_un_livello_ins_upd`, BEFORE INSERT OR UPDATE OF attivo. Il nome sta fra `guard_is_composito` (il padre) e `guard_iva_bom`: parla prima il padre, poi il livello, poi l'IVA                                                            |
| `20261013-03`             | `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva` + check 3: un componente di una distinta **in vigore o futura** non diventa composito (`E_BOM_COMPONENTE_DIVENTA_COMPOSITO`). Corpo base dalla doc auto-gen; il montaggio (UPDATE OF is_composito, …) copre già la colonna |
| `20261013-04` (`80_data`) | `dbops.lock_columns_conditional`: la regola gemella per il form, `is_composito` spento su un articolo **semplice** che è componente di una distinta in vigore o futura                                                                                                                |
| `20261013-05`             | nuovo `catalogo.trgfn_articoli_guard_onere_natura`: un articolo-onere non ha una natura con destinazione `ORDINE` (`E_ARTICOLO_ONERE_NATURA_MERCE`)                                                                                                                                   |
| `20261013-06`             | montaggio `trg_articoli_a10_guard_onere_natura_ins_upd`, BEFORE INSERT OR UPDATE OF natura_vendita_id, causale_onere_id                                                                                                                                                               |

**Codici nuovi** (`codici_errore.csv` + `messaggi_errore.csv`, id 1293-1295): `E_BOM_COMPONENTE_COMPOSITO`
(DATO_ERRATO), `E_BOM_COMPONENTE_DIVENTA_COMPOSITO` (CONFLITTO_STATO), `E_ARTICOLO_ONERE_NATURA_MERCE`
(DATO_ERRATO). Tutti con due `%s`, riempiti dal guard.

**pgTAP**:

* nuovo `catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` (14 test): legame, riaccensione,
  ordine dei rifiuti (padre, livello, IVA), lato articolo (in vigore, futura, scaduta), form, onere;
* tre fixture corrette, perché costruivano un dato che ora è vietato:
  * `catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1.sql`: la riga futura scambiava padre e
    componente (A in B, B in A: un ciclo). Ora ha un terzo padre;
  * `dbops/test-fn-non-editable-fields-conditional.sql`: Y era «padre+figlio» (kit dentro kit), e il test 4
    voleva i tre flag bloccati. Ora Y è il componente di una distinta futura, e i test 3-4 presidiano anche
    la regola nuova del form;
  * `vendite/test-preventivi-righe-guard-natura-ricorrente-v1.sql`: pescava i primi tre articoli per id, che
    sono gli **oneri del seed**, e ne cambiava la natura in merce. Ora li costruisce.

**Prova pre-apply** (team DB, 2026-10-13, scratch `zeroerp_ci`, da owner, `PGTZ=Pacific/Kiritimati`): SQL
**estratto** dagli YAML (preCondition comprese) e righe dei codici in una transazione ritirata, poi il corpo
del pgTAP.

* test nuovo 14/14; senza l'SQL estratto 10 rossi (restano verdi i 4 che non dipendono dai guard nuovi);
* le tre fixture corrette verdi con l'SQL estratto; la versione di HEAD del test capability muore sul ciclo,
  con la frase nuova;
* `plpgsql_check` sulle tre funzioni: nessuna segnalazione;
* 124 pgTAP che toccano distinte, compositi, nature o oneri, prima e dopo: stesso numero di verdi, tranne i
  due corretti qui sopra. ⚠️ Sullo scratch molti muoiono già nella fixture (niente anagrafiche): lì il
  confronto è cieco. In particolare `test-preventivi-righe-guard-natura-ricorrente-v1` sullo scratch si
  ferma al preventivo anche in HEAD: la sua parte viva la vede solo la corsa su dbdev;
* presidi trasversali (catalogo messaggi, identità dei codici, riferimenti morti, rubinetto del primo motivo,
  codici e valori attesi): stesso esito prima e dopo.

**Fatto datato** (lettura su dbdev come app, 2026-10-13): zero legami attivi con un componente composito,
zero oneri con natura merce. Nessun dato da sistemare a mano.

**Doc**: manual nuovi `trgfn_articoli_componenti_guard_un_livello`, `trgfn_articoli_guard_onere_natura`;
aggiornati `trgfn_articoli_guard_flags_struttura_bom_attiva` (check 3; e i frammenti SQL con
`CURRENT_DATE`, stantii dal 2026-10-09), `articoli_componenti`, `articoli` (§ Articolo-onere),
`dev/manual/modello-componenti-bom` §9.2 (era «da definire»); guida `gestione-listini` §5.2.

**Richieste** (vanno nel giro BE/FE finale, §9.6):

* **BE**: policy e ripiego per i tre codici nuovi (`genera_error_policies`; frasi con `%s`). Finché mancano,
  `test_error_codes_db_policy_guardrail` è rosso in CI per il lato BE: atteso, il BE arriva alla fine.
* **FE**: niente di nuovo. `is_composito` spento arriva dai campi non modificabili che il form già legge.

**Esito**: applicato da Tid il 2026-10-13, pgTAP verdi.

### 9.2 Lotto 2 — vocabolario e natura in riga (✅ applicato da Tid il 2026-10-13, con la correzione `-14` del §9.2.1)

**ChangeSet** (in ordine di apply; nessuno applicato):

| ChangeSet                   | Cosa                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261013-07` (`00_schema`) | `natura_vendita_id` su `vendite.ordini_righe` e `vendite.ddt_righe`: FK verso `config.nature_vendita`, **NOT NULL**. Backfill dall'origine (ordine ← riga di preventivo; bolla ← riga d'ordine evasa, ← riga di bolla resa per le riconsegne, anche a catena), poi dall'articolo; coi trigger della tabella spenti per nome e riaccesi col loro modo |
| `20261013-08`               | nuovo BB `script.trgfn_righe_natura_vendita`: la natura si scrive alla nascita (dall'articolo; in modo `CHIAMANTE` quella portata dal verbo) e al cambio di articolo, poi resta                                                                                                                                                                      |
| `20261013-09`               | montaggi `…_a10_natura_vendita_ins_upd` su preventivo (`ARTICOLO`), ordine e bolla (`CHIAMANTE`). L'ordine dei nomi è portante: lock di colonna → natura → guard della ricorrenza (e, nel Lotto 3, le regole sulle righe)                                                                                                                            |
| `20261013-10`               | `vendite.trgfn_preventivi_righe_set_natura_vendita` non scrive più la natura: resta il guard della ricorrenza, che la legge                                                                                                                                                                                                                          |
| `20261013-11`               | `fn_push_preventivo_a_ordine`: la riga d'ordine porta la natura della riga di preventivo                                                                                                                                                                                                                                                             |
| `20261013-12`               | `fn_genera_ddt_da_ordine`: la riga di bolla porta la natura della riga d'ordine                                                                                                                                                                                                                                                                      |
| `20261013-13`               | `fn_genera_ddt_riconsegna`: la riga riconsegnata porta la natura della riga di bolla resa (A-6)                                                                                                                                                                                                                                                      |

I tre verbi partono dal corpo dell'ultimo changeSet (`20261012-13`, `20261011-06`, `20261011-11`),
verificato **uguale al corpo vivo** su dbdev il 2026-10-13; il diff è di tre punti per verbo più la
revisione nel `COMMENT`, e il `rollback` è il corpo precedente.

**Dati** (CSV `runOnChange`):

* `config/tipi_entita.csv` (A-8): `OFFERTA_COMMERCIALE` e `DDT_VENDITA` (codici identici a
  `config.sorgenti`, come chiede la nota del seed), `LISTINO_VERSIONE`, `ARTICOLO`, `PROMO_ARTICOLO`.
  `key_selector` misurato sulle rotte del backend: tutte `id`; ⚠️ la versione di listino come bersaglio
  vuole anche il listino (`<listino_id>/versioni/<ver_id>`), ed è scritto nella nota.
  **Esito della verifica chiesta da A-8 sulla distinta**: la voce è `ARTICOLO`, non `DISTINTA`. Il
  catalogo dice che cosa è l'entità, e la distinta non ha una pagina sua: le sue righe sono i componenti
  dell'articolo, raggiunto dalla sua scheda.
* `dbops/automation_lock_columns.csv`: lock di `natura_vendita_id` su ordine e bolla; il preventivo passa
  al codice generico.
* codici: nuovo `E_RIGA_NATURA_VENDITA_IMMUTABILE` (1296, CONFLITTO_STATO; frase che inizia come la
  vecchia); `E_PREV_RIGA_NATURA_IMMUTABILE` **ritirato** (`obsoleto_dal` 2026-10-13): stessa regola, ora
  su tre tabelle.

⚠️ **Una correzione a una cosa scritta in consegna.** Avevo scritto che il preventivo «riscriveva la
natura a ogni UPDATE». Non è vero: il suo trigger era `UPDATE OF articolo_id`, quindi la natura era già
congelata. Il BB serve a non avere tre copie della stessa scrittura, non a chiudere un buco del preventivo.
Il commento del `-08` è stato corretto prima della consegna.

**pgTAP**:

* nuovo `vendite/test-righe-natura-vendita-congelata-v1.sql` (14 test): struttura; preventivo (dall'articolo,
  congelata, lock); push; ordine (dall'articolo, portata, congelata, cambio articolo, lock); genera bolla;
  bolla (dall'articolo, lock). La catena preventivo → ordine → bolla è costruita dal nulla, con l'articolo
  che cambia natura a metà;
* `vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql` + test 17 (plan 18): la riga riconsegnata porta la
  natura della riga resa, anche dopo che l'articolo ha cambiato natura. La nuova natura si sceglie fra quelle
  che non vanno in ordine, perché l'articolo pescato dal test potrebbe essere un onere (A-9).

**Prova pre-apply** (scratch `zeroerp_ci`, da owner, `PGTZ=Pacific/Kiritimati`; SQL estratto, righe di
registro, poi `fn_run_automations_attivo` e `fn_run_automations_lock_columns` nella stessa transazione,
perché sullo scratch il giro delle automazioni non passa):

* test nuovo 14/14. Controprova senza `-11` e `-12`: rossi il 6 e il 12 (e a cascata il 9 e l'11, che
  lavorano sulla riga venuta dal push);
* i tre lock di colonna si generano, e quello del preventivo viene **rigenerato** col codice nuovo
  (l'automazione ha l'azione `RIGENERA`);
* `plpgsql_check`: due variabili inutilizzate in `fn_genera_ddt_riconsegna` (`v_stato`, `v_reso_uid`), che
  c'erano già prima; niente di nuovo;
* 138 pgTAP che toccano righe di preventivo, ordine e bolla, natura, verbi, `tipi_entita` o lock, prima e
  dopo: **nessuna differenza**. ⚠️ Stesso limite del Lotto 1: sullo scratch molti muoiono nella fixture,
  e il test 17 della riconsegna sullo scratch non arriva (pesca il billing account dai dati): lo vede solo
  la corsa su dbdev;
* controlli statici del repo: verdi, **tranne `check_i18n_keys`** (sotto).

**⚠️ Il pre-commit si ferma su `check_i18n_keys`.** Le cinque `etichetta_key` nuove di `tipi_entita`
(`config.tipi_entita.offerta_commerciale`, `.ddt_vendita`, `.listino_versione`, `.articolo`,
`.promo_articolo`) non erano nei locales del frontend, e l'hook gira proprio sui CSV di `80_data`.
✅ **Risolto** (decisione di Tid, 2026-10-13): le cinque chiavi le ha aggiunte la sessione DB in
`frontend/src/locales/it.json` ed `en.json` (Offerta/Offer, DDT/Delivery note, Versione di listino/Price
list version, Articolo/Item, Promo articolo/Item promotion: termini già in uso nei locales).
`check_i18n_keys.py` pulito.

**Dopo l'apply (Tid), su dbdev**:

1. `CALL maintenance.proc_automations_attivo_job();` e `CALL maintenance.proc_automations_lock_columns_job();`
   — senza, fino al giro delle 21:00 mancano i `require_attivo` della FK nuova e i lock di colonna, e il
   lock del preventivo porta ancora il codice ritirato;
2. i pgTAP: il test nuovo (i test 5, 11 e 14 vogliono i lock del punto 1), il test della riconsegna, e la
   baseline di `vendite`.

**Doc**: manual nuovo `script/manual/trgfn_righe_natura_vendita`; aggiornati
`vendite/manual/trgfn_preventivi_righe_set_natura_vendita` (ora solo guard), `config/manual/nature_vendita`,
`vendite/manual/ordini_righe`, `vendite/manual/ddt_righe`.

#### 9.2.1 Dopo l'apply: la baseline di `vendite` e la correzione `20261013-14` (2026-10-13)

La baseline di `vendite` su dbdev, dopo l'apply, ha dato **8 regressioni**: file verdi su dbdev
(assenti da `baseline-rossi.tsv`), già rossi in CI e sullo scratch. Le cause sono tre, e solo una
viene da questo lotto.

| File                                                                                                                                                                 | Esito                 | Causa                                                                                                                                                                                                                                                                                                                                      | Correzione                                                                                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test-vw-preventivi-smistamento-v1`                                                                                                                                  | ASSERZIONE (test 5)   | **questo lotto**: il BB `-08` rimetteva la natura a `OLD` a parità di articolo e richiudeva in silenzio la porta del lock (vedi sotto)                                                                                                                                                                                                     | `20261013-14`                                                                                                                                                                                         |
| `test-emissione-mirata-gruppi-fatturabili-v1`, `test-vw-dash-competenza-gruppi-v1`, `test-sorgente-origine-tipo-doc-fiscale-v1`, `test-trigger-af-commessa-aware-v1` | SORGENTE_POLIMORFA    | `20261012-46` ([brief-db-annullo-a-valle-riapre-a-monte](../work-done/brief-db-annullo-a-valle-riapre-a-monte.md), D-13): la madre aggancia il documento alla commessa con `fn_link_commessa_sorgente`, che ne pretende formato ed esistenza; le fixture passavano sorgenti inventate (`'c0000000-…'`, `'EXT-SOT-…'`, `'PGTAP-TCA-SRC-…'`) | fixture: preventivo o contratto **veri** (testata in bozza, stesso billing account, emittente del BA)                                                                                                 |
| `test-fn-list-preventivi-da-pushare-v1`, `-v2`                                                                                                                       | ASSERZIONE (test 3-5) | dati: «l'articolo più recente» era, dal 2026-10-13 00:32, un composito MERCE lasciato da uno smoke; la riga andava all'ordine                                                                                                                                                                                                              | fixture: articolo costruito (`dbops.fn_pgtap_crea_articolo`) con natura a destinazione COMMESSA                                                                                                       |
| `test-registri-per-emittente-v1`                                                                                                                                     | ASSERZIONE (test 6)   | dati: dalla notte del 2026-10-12 l'emittente 159 ha template e documenti generati, e disattivandolo parla prima il guard di `documenti_generati`                                                                                                                                                                                           | fixture: emittente costruito (`fn_pgtap_crea_emittente` + `fn_pgtap_crea_cliente_ba` col terzo parametro), il cui unico figlio è il billing account; era lo scostamento dal piano dichiarato nel file |

⚠️ I quattro SORGENTE_POLIMORFA erano rossi su dbdev **dal 2026-10-12 17:45** (apply del `-46`):
l'ultima baseline di sviluppo registrata è del 2026-10-11, e la corsa di quel giorno era sui soli
file del brief. Il ritiro di `tipo_consumo` (`-16 … -23`) non c'entra: dai quattro file ha tolto solo
l'argomento.

**`20261013-14` — il BB senza «difesa».** Il `-08` è montato `UPDATE OF articolo_id,
natura_vendita_id`, quindi scatta proprio sulle scritture a mano della natura, che il lock di
colonna (prima nell'ordine dei nomi) ha già giudicato. La riassegnazione a `OLD` era una seconda
copia della regola, e già diversa: il lock ha la porta `zeroerp.allow_lock_columns_override`, la
copia no. Il caso costruibile solo dalla porta è la riga di preventivo a natura `NULL`
(`preventivi_righe.natura_vendita_id` è nullable: il pregresso). Prima del lotto non succedeva:
il trigger del preventivo era solo `UPDATE OF articolo_id`. Ora, a parità di articolo, il BB
restituisce `NEW` senza toccarlo. Corpo dal `-08` (uguale al vivo su dbdev), rollback = corpo del `-08`.
`test-righe-natura-vendita-congelata-v1`: + test 15 (plan 15), la porta del lock scrive la natura.

**Prova** (2026-10-13, da owner, in transazioni chiuse con `ROLLBACK`, corpo dei pgTAP senza runner;
la RLS non è esercitata):

* su dbdev, `-14` in testa: smistamento 10/10 (senza: rosso il solo test 5), natura congelata 15/15
  (senza: rosso il solo 15, have 2 / want NULL);
* su dbdev, gli altri sei file corretti: 8/8, 10/10, 17/17, 8/8, 10/10, 8/8, e registri 7/7;
  controprova sulle versioni di HEAD: rossi il 3-5 di `preventivi-da-pushare-v1` e il 6 di registri;
* sullo scratch `zeroerp_ci` lo smistamento resta rosso nella fixture (nessun billing account con
  istanza): è il motivo per cui sta in `baseline-rossi-scratch.tsv`, non una regressione. Lì il file
  moriva prima anche sul guard `E_ARTICOLO_ONERE_NATURA_MERCE` (Lotto 1), perché pescava i due
  articoli «per id»: ora li costruisce;
* guardrail statici (`run_on_change`, `pgtap_preambolo`, `ddl_su_trigger_automazione`,
  `precondition_seed`): verdi.

**Doc**: aggiornato `script/manual/trgfn_righe_natura_vendita` (la regola sta solo nel lock).

**CI GitHub, presidio B-7 (`scripts/codici-errore-baseline.sh`), 2026-10-13.** Rosso:
`E_TRIGGER_ARGOMENTI_INVALIDI` acquista la famiglia `ENUM` (5 punti, prima 4). È il controllo del
`-08` sul modo di montaggio, `v_modo NOT IN ('ARTICOLO', 'CHIAMANTE')`. **Uso legittimo, non un
accumulo**: gli altri quattro punti (`trgfn_default_emittente_fiscale`, `trgfn_delete_block_by_guc`,
`trgfn_guard_utility_tipo_ruolo_by_cols`) dicono la stessa cosa, «trigger montato con argomenti
sbagliati», e cambia solo la forma sintattica del controllo. Baseline allineata
(`ECCEZIONE,ENUM,VALORE_ATTESO`, 5) e descrizione del codice in `codici_errore.csv` estesa al «modo
fuori da quelli dichiarati». Verificato sullo scratch: nessun accumulo. Il commit porta la ragione
(lo chiede la baseline).

**Esito** (Tid, 2026-10-13): `20261013-14` applicato, pgTAP verdi, nessuna regressione.

**Commit** (team DB, 2026-10-13): i quattro file SORGENTE_POLIMORFA della tabella sopra **non** sono nel
commit di questo brief: la causa è il `-46` di un altro brief, e gli stessi file portano anche il ritiro di
`tipo_consumo` (`-16 … -23`), che è un altro cantiere. Vanno committati con quel lavoro.

### 9.3 Lotto 3 — le regole sulle righe: il piano (team DB, 2026-10-13)

Il Lotto 3 si divide, per restare applicabile e provabile:

| Parte  | Che cosa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Decisioni                    |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **3a** | preventivo, ordine, bolla: `script.fn_check_articolo_riga` (la check per tipo di riga, A-2) e un guard per tabella; solo componente rifiutato, ordine e bolla solo merce, la ricorrenza fuori dal preventivo (il guard di `20260609-02` si ritira nella check); la riconsegna esente; «solo componente» dal lato articolo, con la regola gemella per il form                                                                                                                                                                 | A-2, A-3, A-6, D-1, D-2, D-3 |
| **3u** | l'**articolo usato** (A-10): predicato unico SECURITY DEFINER «l'articolo è usato», guard su `catalogo.articoli` per le otto colonne strutturali e gemello per il form; porta amministratore col controllo del ruolo; ritiro di `20261013-44/-45` e della riga del `-46` (con il loro manual), che la regola generale sostituisce; da valutare il riassorbimento dei blocchi della distinta (`trgfn_articoli_guard_flags_struttura_bom_attiva` e le sue regole nel form; ✅ valutato il 2026-10-18: non si riassorbe, §9.8.5) | A-10, A-3                    |
| **3b** | offerta e contratto: la check prende il perimetro (`fn_check_riga_erogazione`), l'AGGIUNTA fuori listino e OVERRIDE/ESCLUSIONE dentro il listino (A-5); le funzioni con `p_documento text` passano a `config.tipi_entita` (A-8)                                                                                                                                                                                                                                                                                              | A-2, A-5, A-8, D-3           |
| **3c** | versione di listino e distinta: tipologia, solo componente, un livello, IVA nella check                                                                                                                                                                                                                                                                                                                                                                                                                                      | A-2, D-3, D-4                |
| —      | i passi successivi (emissione, trasformazione: R-6) vanno col **§H del brief offerta**, che aspetta H-D1…H-D3 di Tid: usano la check di questo lotto                                                                                                                                                                                                                                                                                                                                                                         | R-6                          |

Intervallo di changeSet: da `20261013-40` (un'altra sessione usa la sequenza bassa dello stesso giorno).

#### 9.3.1 Lotto 3a — preventivo, ordine, bolla (✅ applicato il 2026-10-13, pgTAP verdi)

**ChangeSet**:

| ChangeSet                 | Cosa                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261013-40`             | nuova check `script.fn_check_articolo_riga(documento, documento_id, articolo, natura)`: i motivi in ordine dichiarato. 1. solo componente (ogni documento, `E_ARTICOLO_SOLO_COMPONENTE`); 2. la natura per destinazione: preventivo → la ricorrenza va in offerta (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`), ordine e bolla → solo merce (`E_RIGA_NATURA_NON_AMMESSA`). La natura giudicata è quella della riga, se c'è |
| `20261013-41`             | nuovo BB `script.trgfn_righe_guard_articolo_ammesso`: solleva il primo motivo; la riconsegna è esente con una porta **stretta** (`zeroerp.ddt_riconsegna` = id del reso, e solo per un articolo che sta fra le righe di quel reso: il verbo è INVOKER, il controllo «proprietario» delle altre porte qui non c'è)                                                                                                       |
| `20261013-42`             | montaggi `…_a10_regole_articolo_ins_upd` su preventivo, ordine, bolla (dopo `…_a10_natura_vendita`), e **ritiro** di `vendite.trgfn_preventivi_righe_set_natura_vendita` (trigger e funzione): la sua regola è il motivo 2 della check, stesso codice e stessa frase                                                                                                                                                    |
| `20261013-43`             | `fn_genera_ddt_riconsegna` accende e spegne la porta intorno al ciclo delle righe                                                                                                                                                                                                                                                                                                                                       |
| `20261013-44`, `-45`      | lato articolo (A-3): `is_solo_componente` non si accende su un articolo in una riga autonoma di un preventivo, ordine o bolla in bozza (`E_ARTICOLO_SOLO_COMPONENTE_IN_USO`)                                                                                                                                                                                                                                            |
| `20261013-46` (`80_data`) | la regola gemella per il form in `dbops.lock_columns_conditional`                                                                                                                                                                                                                                                                                                                                                       |

**Codici nuovi**: `E_RIGA_NATURA_NON_AMMESSA` (1297, DATO_ERRATO), `E_ARTICOLO_SOLO_COMPONENTE_IN_USO` (1298,
CONFLITTO_STATO). **Locales**: le tre `reason_key` `vendite.righe.articolo_reason.{solo_componente,
ricorrente_usa_offerta, natura_non_merce}` (it, en), aggiunte dalla sessione DB come le etichette del Lotto 2.

⚠️ **L'apply è avvenuto mentre scrivevo**: `-40 … -43` su dbdev alle 11:41, prima che `-44 … -46` e le righe
dei codici esistessero; il resto alle 11:52, su entrambi i database. Per circa dieci minuti dbdev ha avuto il
guard senza il messaggio di `E_RIGA_NATURA_NON_AMMESSA`. Ora è tutto applicato; i file `-40 … -46` non si
toccano più.

**pgTAP**:

* nuovo `vendite/test-righe-articolo-ammesso-v1.sql` (18 test): la check (ordine dei motivi, natura della
  riga, documento non gestito), il guard sulle tre tabelle, la riconsegna (l'articolo diventato solo
  componente si restituisce; una riga a mano no; la porta su un altro reso no), il lato articolo e il form.
  Il reso è costruito dal nulla: bolla consegnata col verbo di stato (azioni `emetti_ddt`, `conferma_reso`
  concesse all'operatore del test);
* `script/test-rubinetto-primo-motivo-v1` test 5: da 39 a 40 (il guard nuovo nasce sull'helper);
* `vendite/test-righe-natura-vendita-congelata-v1` test 10: sull'ordine non c'è un'altra natura ammessa,
  il ricalcolo al cambio di articolo si vede dal rifiuto;
* `vendite/test-preventivi-righe-guard-natura-ricorrente-v1`: solo commenti (il guard ritirato);
* **fixture**: dieci file pescavano il primo articolo del catalogo per id (l'onere del seed
  `ONERE_SENZA_CONTRATTO`, natura servizio) o il più recente, e lo mettevano in un ordine o in una bolla:
  ora lo **costruiscono** (`test-rls-ddt-satelliti`, `test-fn-check-ddt-emittibile-v1`,
  `test-seed-stati-doc-ordini-evaso-v1`, `test-ddt-causale-immutabile-v1`, `test-ddt-riepilogo-iva`,
  `test-esecutivi-ba-coppia-v1`, `test-indirizzi-documento-seguono-cliente-v1`,
  `test-ordini-guard-transizione-v1`, `test-ordini-riepilogo-iva-totali`,
  `test-riepilogo-iva-equivalenza-cross-doc`). Altri **36 file** pescano un articolo per righe d'ordine o
  di bolla: su dbdev, oggi, 30 di quelle pesche davano un articolo rifiutato (quasi sempre
  `SMK-CAT3-C-…`, lasciato da uno smoke, solo componente). A loro ho **aggiunto la condizione**
  «merce e non solo componente» alla pesca, tenendo il loro criterio; la pesca dell'onere per la commessa
  resta com'è. Rimisurate su dbdev: 41 pesche su 41 danno un articolo ammesso.

✅ **Chiuso il 2026-10-13**: quelle 36 fixture ora **costruiscono** l'articolo (`dbops.fn_pgtap_crea_articolo`), vedi la ricaduta qui sotto. Riverificate col Lotto 3u in testa (§9.3.2): 35 verdi su 36 su dbdev e su `zeroerp_ci`; l'unico rosso è lo scope di `test-vw-situazione-merce-ordine-v1` (test 11), rosso da owner e verde come app, uguale senza la 3u. ~~Trovato, aperto: le 36 fixture pescano invece di costruire.~~

🔴 **Ricaduta trovata da Tid sulla CI di `zeroerp_ci` (2026-10-13)**: il filtro, su un database ricostruito,
**svuota** la pesca. Là il catalogo ha solo i cinque `ONERE_*` (servizi): la sottoquery dava NULL e la riga
moriva su `E_UOM_MISSING` («Unità misura mancante. (articolo_id NULL)»), `ERRORE_FIXTURE` in cinque file che
prima erano verdi sullo scratch (o rossi solo in un'asserzione). Ora **costruiscono** l'articolo con
`dbops.fn_pgtap_crea_articolo('<codice>', false)`, che nasce merce e non solo componente:
`test-rls-ordini-satelliti`, `test-rls-resi-satelliti`, `test-rls-resi-ef-whitelist-write`,
`test-fn-available-actions-ordine-v1`, `test-fn-available-actions-ordine-v2`. Provati su `zeroerp_ci`
in una transazione annullata, col runner di ciascuno: 9/9, 10/10, 3/3, 10/10; ordine-v2 8/9, e il test 1 è
il rosso `ASSERZIONE` già registrato (cerca un BA). La prova pre-apply sullo scratch non l'aveva visto
perché confrontava gli esiti prima e dopo, non se la fixture **costruiva** qualcosa.

⭐ **Debito chiuso lo stesso giorno**: anche gli altri file con il filtro (31, più
`test-preventivi-righe-guard-natura-ricorrente-v1`), già `ERRORE_FIXTURE` in CI perché cercavano billing
account, emittente o soggetto_ruolo, o impostavano a mano `app.current_user_id = '1'`, ora **costruiscono**
il mondo: `dbops.fn_pgtap_crea_mondo_cliente` + `dbops.fn_pgtap_crea_articolo`, e la riga di contesto
esplicita sull'operatore del mondo (il guardrail del preambolo la cerca). Asserzioni e `plan` invariati,
salvo una: in `test-documenti-numerazione-trasloco-v1` i test 3 e 9 («la forma del registro») ignoravano
`anno_nel_numero`, che dal 20260908 è il default per DDT e RESO. Erano verdi solo sul registro vecchio di
dbdev; ora l'attesa compone `<anno>-` come `vendite.fn_assegna_numero_documento`. Difetti di fixture
emersi e corretti lungo la strada: testata e righe del reso scritte nella stessa istruzione (la WITH CHECK
di `resi_righe` non vede il reso: passava solo con l'utente 1); in `test-fn-genera-ddt-riconsegna-eredita-v1`
un articolo riusato dopo avergli cambiato la natura (9 errori anche su dbdev).
**Misura finale** (2026-10-13, file per file, in transazione annullata, col runner di ciascuno): i 49 pgTAP
modificati in questo cantiere sono tutti verdi, senza errori, sia su `zeroerp_ci` sia su dbdev; guardrail
del preambolo pulito. Le loro righe in `baseline-rossi-ci.tsv` le toglie
`scripts/pgtap-baseline-ci-rientrati.sh` dopo la corsa di GitHub, non a mano.
Builder che sono mancati (regola del 2, per un brief futuro): contratto pushabile, «DDT spedito da
ordine» (ripetuto in cinque file), kit prodotto + componenti, soggetto con ruolo generico (vettore).

**Prova pre-apply** (scratch, da owner, `PGTZ=Pacific/Kiritimati`):

* test nuovo 18/18;
* confronto sui pgTAP che toccano righe di preventivo, ordine, bolla o `is_solo_componente`, prima (la 3a
  tolta in transazione: trigger delle regole e lato articolo via, guard del preventivo rimesso) e dopo:
  le regressioni erano le dieci fixture sopra e il test della natura congelata, tutte rientrate. Ogni file
  toccato, rispetto alla sua versione di HEAD sullo stato vivo: **nessuno peggiore**, 12 migliori;
* `plpgsql_check`: nessuna segnalazione sulle tre funzioni nuove; presidi statici e `check_i18n_keys` verdi.

⚠️ **Al commit**: cinque file pgTAP hanno modifiche anche dell'altro cantiere non committate
(`test-fn-list-ddt-da-pushare-contatore-v1`, `test-vw-dash-backlog-resi-v1`, `test-vw-partite-merce-v1`,
`test-vw-resi-da-accreditare-contatore-v1`, `test-vw-situazione-merce-ordine-v1`): vanno messi in stage solo
i hunk di questo brief, o committati dopo quel lavoro.

**Doc**: manual nuovi `script/manual/fn_check_articolo_riga`, `script/manual/trgfn_righe_guard_articolo_ammesso`,
`catalogo/manual/trgfn_articoli_guard_solo_componente_in_bozza`; **cancellato**
`vendite/manual/trgfn_preventivi_righe_set_natura_vendita` (oggetto ritirato); aggiornati
`config/manual/nature_vendita`, `script/manual/trgfn_righe_natura_vendita`,
`vendite/manual/fn_crea_revisione_preventivo`; guide `gestione-ordini` §3.2, `gestione-ddt` §3.2 (con la
riconsegna), `gestione-preventivi` (il riquadro «sotto il cofano»).

**Da fare (Tid)**: i pgTAP sopra su dbdev e la baseline di `vendite`, `script`, `rls`, `catalogo`.

#### 9.3.2 Lotto 3u — l'articolo usato non cambia la sua struttura (A-10; ✅ applicato da Tid il 2026-10-13, pgTAP verdi)

La decisione A-10 di Tid (§8.6) sostituisce la protezione a pezzi: invece di rincorrere le conseguenze
di un flag cambiato (righe in bozza, verbi di copia, porte), un articolo **usato** non cambia più i flag
strutturali. Chiude anche due punti emersi nella verifica della 3a: il guard `-44` e la sua regola del
form (`-46`) leggevano i documenti con la RLS di chi modifica l'articolo (le bozze delle **altre aziende**
non le vedevano: gli articoli sono unici per tutte le aziende), e un ordine confermato non trova più un
articolo diventato «solo componente» dopo la conferma.

**ChangeSet** (numerati dopo il `-46`: l'autogen ordina per numero, e in una build da zero il ritiro deve
girare dopo ciò che ritira):

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261013-47` | predicato `catalogo.fn_articolo_usato(articolo)`: l'articolo compare in una tabella che lo punta con una FK, in qualunque stato. Tabelle lette da `pg_constraint` (una nuova conta da sola), meno sei dichiarate di anagrafica dell'articolo (distinta, UoM operative, note, descrizioni, regole di fatturazione, ambiti IVA). **SECURITY DEFINER**: vede i documenti di tutte le aziende, ritorna solo un boolean                                          |
| `20261013-48` | guard `catalogo.trgfn_articoli_guard_struttura_se_usato`: le otto colonne (`is_composito`, `is_solo_componente`, `natura_vendita_id`, `causale_onere_id`, `listino_tipologia_id`, `gestito_a_magazzino`, `requires_lotto`, `requires_serial`) non cambiano su un articolo usato → `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`; il messaggio non dice dove l'articolo è usato. Porta: GUC `zeroerp.articolo_correggi_struttura` **e** proprietario della tabella |
| `20261013-49` | montaggio `trg_articoli_a10_guard_struttura_se_usato_upd`; **ritiro** di `trgfn_articoli_guard_solo_componente_in_bozza` e del suo trigger (`-44/-45`)                                                                                                                                                                                                                                                                                                      |
| `20261013-50` | verbo `catalogo.fn_articolo_correggi_struttura(articolo, campi jsonb)`: la porta amministratore, solo SUPER_ADMIN (`script.fn_guard_super_admin`); SECURITY DEFINER, EXECUTE solo all'app                                                                                                                                                                                                                                                                   |
| `20261013-51` | `dbops.lock_columns_conditional`: le otto colonne spente nel form con lo **stesso** predicato (`catalogo.fn_articolo_usato($1::uuid)`); via la regola del `-46`                                                                                                                                                                                                                                                                                             |
| `20261013-52` | builder pgTAP `dbops.fn_pgtap_articolo_correggi_struttura`: cambia un flag di un articolo usato dalla porta vera, come un SUPER_ADMIN costruito (INVOKER) — quattro file ripetevano il passaggio                                                                                                                                                                                                                                                            |

**Codici**: nuovo `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE` (1299, CONFLITTO_STATO; valori: codice
dell'articolo, nome leggibile del campo). `E_ARTICOLO_SOLO_COMPONENTE_IN_USO` (1298) **ritirato**
(`obsoleto_dal` 2026-10-13): nato e ritirato lo stesso giorno, la regola generale lo comprende. Riusati
`E_ARTICOLO_NOT_FOUND` e `E_PARAMETRO_INVALIDO` nelle forme che il presidio B-7 conosce già (PARAMETRO):
misurato nella transazione di prova, nessun codice allarga le famiglie.

**pgTAP**:

* nuovo `catalogo/test-articolo-usato-struttura-v1.sql` (17 test): il predicato (anche la riga spenta
  conta), il guard sulle colonne bloccate e su quelle libere, il verbo (permesso, colonna estranea,
  correzione), il form, **un articolo usato da un'altra azienda**, il ritiro del `-44/-45`, la GUC accesa a
  mano (test 17: rosso da owner, verde come app, per costruzione);
* passano dalla porta (il builder del `-52`) i quattro test che cambiano un flag **dopo** l'uso per
  provare il valle: `test-righe-natura-vendita-congelata-v1`, `test-righe-articolo-ammesso-v1` (anche i
  test 17-18 del lato articolo, riscritti sulla regola nuova), `test-fn-genera-ddt-riconsegna-eredita-v1`,
  `test-righe-erogazione-da-articolo-v1`;
* due fixture che cambiavano i flag di un articolo **pescato** e già usato su dbdev:
  `test-fn-list-preventivi-da-pushare-competenza-v1` ora costruisce l'articolo;
  `dbops/test-articoli-a-magazzino-prontezza-v1` (spegne `gestito_a_magazzino` su tutti) passa dal verbo
  come SUPER_ADMIN.

**Prova pre-apply** (2026-10-13, SQL estratto da `-47 … -52` in testa a transazioni annullate, da owner,
`PGTZ=Pacific/Kiritimati`, corpo dei pgTAP senza runner; le due righe di registro del codice nuovo
nella stessa transazione):

* `plpgsql_check`: nessuna segnalazione sulle tre funzioni; il trigger vecchio sparisce, otto regole nel
  form, la regola del `-46` tolta;
* test nuovo 16/17 su `zeroerp_ci` e su dbdev (il 17 è quello rosso da owner);
* i 47 pgTAP che cambiano uno degli otto flag, senza e con la 3u su `zeroerp_ci`: cambiano esito solo i
  quattro sopra, verdi con la 3u; su dbdev, con la 3u: 45 verdi, i due rossi erano le fixture sopra, ora
  verdi;
* le 36 fixture del §9.3.1 con la 3u: 35/36 su entrambi (lo scope rosso da owner);
* **misure datate (dbdev, 2026-10-13)**: 28 articoli usati su 305; il predicato su un articolo mai usato
  (il caso peggiore: guarda tutte le tabelle) 5 ms, `fn_non_editable_fields` di un articolo ~21 ms;
* presidio B-7 (codici di errore) nella transazione: nessun allargamento; guardrail statici e
  `check_i18n_keys` verdi.

**Ricadute fuori dal DB** (al giro BE/FE, §9.6): i test Django che toccano gli otto flag
(`test_prezzo_riga_commessa_db`, `test_righe_erogazione_obbligatoria_db`, `test_listini_create_db`,
`test_date_validita_guard_comune_db`) li cambiano su un articolo appena costruito, quindi non ancora usato:
dovrebbero passare, ma girano in CI sul database e vanno verificati.

⚠️ **La porta della riconsegna** (A-6, `zeroerp.ddt_riconsegna`, §9.3.1) resta, per decisione di Tid. Con
la 3u il caso che la giustificava (un articolo spedito che diventa solo componente) arriva solo dalla porta
amministratore.

**Doc**: manual nuovi `catalogo/manual/fn_articolo_usato`, `catalogo/manual/trgfn_articoli_guard_struttura_se_usato`,
`catalogo/manual/fn_articolo_correggi_struttura`, `dbops/manual/fn_pgtap_articolo_correggi_struttura`;
`catalogo/manual/articoli`: sezione «Un articolo usato non cambia la sua struttura»; **cancellati** il manual
e la pagina generata di `trgfn_articoli_guard_solo_componente_in_bozza` (oggetto ritirato). La doc generata
(indici, `tabelle/articoli`) la rigenera la build di Tid.

#### 9.3.3 Lotto 3b — offerta e contratto (✅ applicato da Tid il 2026-10-13, nessuna regressione)

La stessa check per tipo di riga (A-2) giudica anche le righe d'eccezione di offerta e contratto.
Qui il tipo d'eccezione (un valore della riga) decide le regole, e la A-5 aggiunge quella che
mancava: un'OVERRIDE o un'ESCLUSIONE si fanno solo su un articolo del listino.

**ChangeSet** (numerati dopo il `-46` e il `-53` di un altro cantiere):

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261013-55` | `script.fn_check_articolo_riga`: offerta (`OFFERTA_COMMERCIALE`) e contratto; `p_tipo_eccezione` in coda (DROP + CREATE). **AGGIUNTA e OVERRIDE**: 1. solo componente (D-3); 2. tipologia fuori utility (composta da `fn_check_riga_erogazione` senza erogazione); 3. **nessuna erogazione ammessa** (§8.1, nuovo `E_ARTICOLO_SENZA_EROGAZIONE`); 4. listino: AGGIUNTA già in listino, OVERRIDE **senza listino** o **fuori listino** (A-5, nuovi `E_RIGA_ECCEZIONE_SENZA_LISTINO` / `_FUORI_LISTINO`). **ESCLUSIONE**: 1. figlio di bundle (composta da `fn_check_esclusione_articolo_documento`); 2. senza listino / fuori listino (A-5). «Nel listino» = una riga di `vendite.fn_espandi_listino_versione` (standalone **e** bundle), la base su cui il drawer applica le eccezioni |
| `20261013-56` | `script.trgfn_righe_guard_articolo_ammesso`: natura e tipo d'eccezione da `to_jsonb(NEW)` (ognuno sta solo sulle sue tabelle); campo `articolo_id` se il motivo non lo porta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `20261013-57` | montaggi `…_a10_guard_articolo_ammesso_ins_upd` su `offerte_commerciali_eccezioni` e `contratti_righe`, **prima** dei guard di riga (prima l'articolo, poi la riga); **ritiro** di `trgfn_righe_guard_aggiunta_fuori_listino` e `trgfn_righe_guard_esclusione_figlio_bundle` coi loro quattro trigger (regola del 2: ora sono motivi della check)                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `20261013-58` | builder pgTAP `dbops.fn_pgtap_listino_aggiungi_articoli`: mette articoli in una versione di listino (sei fixture lo ripetevano)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

**Codici**: `E_ARTICOLO_SENZA_EROGAZIONE` (1300), `E_RIGA_ECCEZIONE_SENZA_LISTINO` (1301),
`E_RIGA_ECCEZIONE_FUORI_LISTINO` (1302). Quattro `reason_key` nuove in `vendite.righe.articolo_reason`
(it, en): `senza_erogazione`, `aggiunta_gia_in_listino`, `eccezione_senza_listino`, `eccezione_fuori_listino`.
Presidio B-7: `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` acquista una famiglia leggibile (VALORE_ATTESO,
una sola): nessun rosso.

**Scelte del team DB** (dentro le decisioni prese, da guardare):

* **Il disegno si è stretto in corsa.** La prima idea spostava la tipologia fuori da
  `fn_check_riga_erogazione`; ma `vendite.fn_documento_riga_erogazioni` (il form delle erogazioni,
  anche sulle OVERRIDE già scritte) la usa per una domanda di solo articolo, e non deve sentire i
  motivi di listino. Quelle due funzioni restano intatte; la check nuova le **compone**.
* **Un difetto trovato dalla prova su dbdev**: la prima stesura cercava l'articolo in
  `listini_righe`, dove un composito è vietato. Il bundle sta nel listino coi componenti: la sua
  ESCLUSIONE risultava «fuori listino». Corretto prima della consegna leggendo la versione espansa
  (regola del 2: la stessa base del preview), e presidiato dai test 19-20 del pgTAP nuovo.
* **L'ESCLUSIONE non giudica solo componente e tipologia**: escludere non vende.
* **La natura non è una regola di offerta e contratto**: nessuna decisione la chiede; il perimetro
  lo dicono tipologia ed erogazioni.
* ⚠️ **Il guard è `UPDATE OF articolo_id`**; i due ritirati scattavano su ogni UPDATE. Una riga
  AGGIUNTA riattivata dopo che l'articolo è entrato nel listino non si rigiudica più qui: la
  intercetta l'emissione (§H del brief offerta), come le righe già scritte.

**A-8-bis — ✅ decisa da Tid il 2026-10-13: col giro BE/FE.** La A-8 diceva che `fn_check_riga_erogazione`,
`fn_check_esclusione_articolo_documento` e `fn_documento_listino_operativo` passano a
`config.tipi_entita` «nello stesso giro». Il **backend** chiama `fn_documento_listino_operativo`
con `OFFERTA | CONTRATTO` (`_documento_eccezioni_repo.py`, `offerte_service.py`,
`contratti_service.py`): cambiarne la grammatica ora romperebbe il BE prima del suo giro.
**Deciso**: la migrazione va col giro BE/FE (§9.6), insieme; fino ad allora la traduzione
`OFFERTA_COMMERCIALE → OFFERTA` sta in un punto solo, `fn_check_articolo_riga`, dichiarata.

**pgTAP**:

* nuovo `vendite/test-righe-eccezioni-articolo-ammesso-v1.sql` (20 test): la check su contratto e
  offerta per i tre tipi d'eccezione, una tipologia senza erogazioni **costruita** (oggi il
  vocabolario non ne ha, ma è gestibile: il caso esiste nel modello), il guard sulle due tabelle,
  il ritiro, il bundle;
* **sedici file** cambiavano esito; tutti corretti e verdi su dbdev e `zeroerp_ci`:
  * **presidi di struttura** che nominavano i guard ritirati: `test-punti-canale-campo-v1`,
    `test-rubinetto-primo-motivo-v1` (da 40 a 39 siti), `test-listino-versione-in-vigore-v1`,
    `test-contratto-righe-lista-v1`, `test-guard-esclusione-figlio-bundle-v1`,
    `test-righe-esclusione-solo-non-si-vende-v1`;
  * **fixture con OVERRIDE o ESCLUSIONE fuori listino** (le righe invisibili del §8.2):
    `test_fn_crea_revisione_offerta`, `test_fn_push_offerta_a_contratto`,
    `test_offerte_eccezioni_qta_from_operativa`, `test-annullo-documento-con-legami-v1`,
    `test-contratti-modalita-pricing-v1`, `test-fn-resolve-prezzo-listino-v2-step24-v1` (che ora
    esegue davvero i test 6-7 sulla versione fissata), `test-righe-erogazione-da-articolo-v1`
    (test 11: l'esclusione non si giudica sul perimetro, parla solo il listino);
  * **riscritti coi builder**, perché pescavano tutto dal database:
    `test-contratti-schema-step22-v1` (17/17; prima rosso in CI, e i test 16-17 su dbdev si
    saltavano) e `test_offerte_eccezioni_componenti` (27/27, **zero skip**: prima, in CI, 22
    asserzioni su 27 si saltavano per mancanza di dati).
  * ⚠️ Un errore mio trovato strada facendo e corretto: in `test-contratti-modalita-pricing-v1` la
    riga scritta dal builder non era visibile alla `JOIN` della stessa istruzione, e il test 3
    passava inserendo zero righe. Ora creazione e lettura stanno in due istruzioni.

**Prova pre-apply** (2026-10-13, SQL estratto da `-55 … -58` + righe dei tre codici in testa a
transazioni annullate, da owner, `PGTZ=Pacific/Kiritimati`, corpo dei pgTAP senza runner):

* `plpgsql_check`: sulla check due avvisi «STABLE ma VOLATILE» (le due chiamate di errore: il
  pattern delle 100 check in esercizio); il guard pulito;
* censimento di 52 pgTAP (scrivono righe di offerta o contratto, o nominano gli oggetti toccati):
  **su dbdev tutti verdi** tranne il test 30 di `test-annullo-documento-con-legami-v1` (rosso da
  owner per costruzione, uguale a prima); su `zeroerp_ci` i rossi sono i quattro già in
  `baseline-rossi-scratch.tsv` più lo stesso test 30;
* presidio B-7 nella transazione: nessun allargamento; guardrail statici e `check_i18n_keys` verdi.

**Doc**: manual aggiornati `script/manual/fn_check_articolo_riga` (le regole di offerta e
contratto, il ponte A-8), `script/manual/trgfn_righe_guard_articolo_ammesso` (i montaggi nuovi),
`script/manual/fn_check_esclusione_articolo_documento`, `vendite/manual/offerte_commerciali_eccezioni`,
`vendite/manual/contratti_righe`, `vendite/manual/fn_contratto_righe_preview`,
`vendite/manual/fn_documento_listino_operativo`; guida `gestione-contratti`; nuovo
`dbops/manual/fn_pgtap_listino_aggiungi_articoli`; **cancellati** manual e pagine generate dei due
guard ritirati. ⚠️ Nominano ancora i guard ritirati due documenti del backend
(`docs/it/backend/vendite/manual/api_contratti.md`, `modello-contratti.md`): al giro BE/FE.

#### 9.3.4 Lotto 3c — versione di listino e distinta (✅ applicato da Tid il 2026-10-13, pgTAP verdi)

La stessa check per tipo di riga (A-2) giudica anche la riga standalone di una versione di listino
e il componente di una distinta. Come nella 3b, i guard per regola si ritirano dentro la check.

**ChangeSet**:

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `20261013-59` | `script.fn_check_articolo_riga`: `LISTINO_VERSIONE` (1. solo componente, D-3, **nuovo** sulle righe di listino; 2. composito → `E_LISTINO_RIGA_COMPOSITO_VIETATO`; 3. tipologia mancante/incompatibile) e `ARTICOLO`, la distinta (1. componente uguale al padre → **nuovo** `E_BOM_COMPONENTE_PADRE`; 2. componente composito, D-4; 3. IVA diversa dal padre); `p_articolo_padre_id` in coda (DROP + CREATE): la testata della distinta è un articolo, con un id `uuid` |
| `20261013-60` | `catalogo.trgfn_articoli_componenti_guard_componente`: il guard di tabella della distinta (il guard dei documenti legge `articolo_id` e un padre `bigint`; qui sono `componente_id` e `prodotto_id`). Giudica un legame attivo quando nasce, si attiva o cambia componente o padre                                                                                                                                                                                       |
| `20261013-61` | montaggi su `listini_righe` (il guard dei documenti, `UPDATE OF articolo_id, listino_versione_id`) e su `articoli_componenti` (dopo i guard sul padre); **ritiro** di `trgfn_listini_righe_guard_tipologia`, `trgfn_listini_righe_guard_no_composito`, `trgfn_articoli_componenti_guard_un_livello` (Lotto 1), `trgfn_articoli_componenti_guard_iva` coi loro trigger (regola del 2)                                                                                     |

**Codici**: `E_BOM_COMPONENTE_PADRE` (1303); gli altri motivi riusano i codici dei guard ritirati,
con gli stessi segnaposto (i valori ora portano il codice dell'articolo, non il suo uuid). Sei
`reason_key` nuove: `vendite.righe.articolo_reason.{composito_come_bundle, tipologia_mancante,
tipologia_incompatibile}`, `catalogo.distinta.componente_reason.{componente_padre,
componente_composito, iva_discordante}` (it, en). B-7: nessun allargamento.

**Scelte del team DB**:

* **Nella distinta il solo componente non è un motivo**: è il caso normale.
* **Le regole sul padre della distinta** (dev'essere composito, non solo componente) restano nei
  loro guard: sono della testata, non della riga, e il picker della distinta si apre solo su un padre
  composito.
* **Il composito nella versione di listino** resta un motivo della riga standalone
  (`listini_righe`): nella versione entra per l'altra strada, coi componenti. Il picker del Lotto 4
  dovrà dire «entra come bundle» e non «escluso» (§8.2): la `reason` è `COMPOSITO_COME_BUNDLE`.
* Le condizioni di scatto sono quelle dei guard sostituiti, unite (listino: anche il cambio di
  versione della riga; distinta: nascita, attivazione, cambio di componente o padre).

**pgTAP**:

* nuovo `catalogo/test-listino-distinta-articolo-ammesso-v1.sql` (20 test): la check e il guard per
  la versione di listino e per la distinta, il legame spento che non si giudica, il padre come
  componente che ora parla col codice prima del CHECK, il ritiro;
* cambiano esito solo quattro **presidi di struttura**, aggiornati: `test-punti-canale-campo-v1`
  (il guard della tipologia ritirato), `test-rubinetto-primo-motivo-v1` (da 39 a 40: il guard della
  distinta è un sito nuovo sull'helper), `test-contratto-righe-lista-v1` e
  `test-guard-esclusione-figlio-bundle-v1` (la firma della check ha sei argomenti).

**Prova pre-apply** (2026-10-13, SQL estratto da `-59 … -61` + la riga del codice nuovo, in
transazioni annullate, da owner, `PGTZ=Pacific/Kiritimati`, corpo dei pgTAP senza runner):

* `plpgsql_check`: sulla check il solito avviso STABLE/VOLATILE; i due guard puliti;
* test nuovo 20/20 su dbdev e `zeroerp_ci`;
* censimento di 49 pgTAP (scrivono righe di listino o legami di distinta, o nominano gli oggetti
  toccati), senza e con la 3c, su **entrambi** i database: cambiano esito solo il test nuovo e i
  quattro presidi, ora verdi;
* B-7 nella transazione: nessun allargamento; guardrail statici e `check_i18n_keys` verdi.

**Doc**: nuovo `catalogo/manual/trgfn_articoli_componenti_guard_componente`; aggiornati
`script/manual/fn_check_articolo_riga`, `script/manual/trgfn_righe_guard_articolo_ammesso`,
`catalogo/manual/articoli`, `catalogo/manual/articoli_componenti`,
`catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva`,
`catalogo/manual/trgfn_articoli_guard_iva_bom_attiva`,
`catalogo/manual/trgfn_articoli_guard_listino_se_composito`,
`script/manual/trgfn_listini_righe_comp_guard_coerenza_bom`, `dev/manual/modello-componenti-bom`,
guida `gestione-listini`; **cancellati** manual e pagine generate dei quattro guard ritirati.
⚠️ `docs/it/dev/backend/catalogo-building-block-backend.md` nomina ancora il guard della tipologia:
al giro BE/FE.

### 9.4 Lotto 4 — la sede unica del picker e la promo (✅ applicato da Tid il 2026-10-14, pgTAP verdi)

Il picker degli articoli di una riga legge la stessa check dei guard (A-2): dato il documento e il
suo id (A-1), gli articoli **attivi** che la ricerca trova, ciascuno col **primo motivo** per cui il
documento non lo ammette (`NULL` = ammesso), prima gli ammessi (A-7). E la promo prende la sua
regola (D-6).

**ChangeSet**:

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261014-01` | nuovo `script.fn_articolo_riga_contesto(documento, documento_id, tipo_eccezione, padre)`: il **lato documento** della check, letto una volta (listino operativo, versione espansa → `articoli_listino`, etichetta; tipologia del listino; padre della distinta), e le validazioni dei parametri (spostate qui, stesse frasi). `PROMO_ARTICOLO` è un documento nuovo                                            |
| `20261014-02` | nuovo `script.fn_check_articolo_riga_su_contesto(contesto, articolo, natura)`: **i motivi**, il corpo del `-59` identico nelle regole, nell'ordine, nei codici e nei valori, che legge il documento dal contesto; più la promo (solo componente → `E_PROMO_ARTICOLO_SOLO_COMPONENTE`)                                                                                                                          |
| `20261014-03` | `script.fn_check_articolo_riga`: **stessa firma**, `CREATE OR REPLACE`; il corpo compone le due metà (`v_motivi := …_su_contesto(…_contesto(…))`, la forma che `dbops.vw_funzioni_check_codici` riconosce come delega). Nessun chiamante cambia. Rollback: il corpo del `-59`                                                                                                                                  |
| `20261014-04` | nuovo `catalogo.fn_articoli_ammessi(documento, documento_id, search, limit, tipo_eccezione, padre)` → `{articolo_id, codice, descrizione, motivo, ordine}`. Id obbligatorio per i documenti con testata (non per `ARTICOLO` e `PROMO_ARTICOLO`); solo articoli attivi; ricerca «contiene» letterale (`strpos` su `lower`) su codice o descrizione; il tetto lo sceglie il chiamante, dopo il giudizio; INVOKER |
| `20261014-05` | `script.trgfn_righe_guard_articolo_ammesso` montato su `vendite.promo_articoli` con `('PROMO_ARTICOLO', 'id')`, `BEFORE INSERT OR UPDATE OF articolo_id`, prima del guard delle date; COMMENT del guard riscritto coi montaggi di oggi (mancava `listini_righe`)                                                                                                                                               |

**Codici**: `E_PROMO_ARTICOLO_SOLO_COMPONENTE` (1306, DATO_ERRATO; valori: codice dell'articolo;
campo `articolo_id`). **Locales**: `vendite.promo_articoli.articolo_reason.solo_componente` (it, en),
aggiunta dalla sessione DB; `check_i18n_keys` pulito.

**Scelte del team DB** (dentro le decisioni prese, da guardare):

* **La check divisa in due metà (R-5).** Il profilo della check per articolo, misurato su dbdev il
  2026-10-14 (un contratto col listino, 268 articoli attivi, come app), dava ~5,2 ms per articolo:
  ~4,9 ms erano `vendite.fn_espandi_listino_versione`, ~0,7 ms il listino operativo, cioè **lavoro sul
  documento rifatto per ogni articolo**. Il costo del picker cresce così come «articoli trovati ×
  dimensione del listino». La correzione non tocca la regola: il documento si legge una volta (il
  contesto), i motivi si scrivono per articolo, e la firma di sempre compone le due metà per i guard.
  Scartate: una funzione «nel listino» più leggera (una seconda definizione di «nel listino», accanto
  a quella dell'espansione: la regola del 2 al contrario) e un parametro-cache sulla check (un
  ingresso da cui un chiamante può passare un insieme sbagliato).
* **Il composito nella promo è ammesso (D-6, verifica chiesta in consegna).** Il resolver dà un
  prezzo a sé a un composito quando il contratto ha un'eccezione su di lui (stadio 1a, AGGIUNTA o
  OVERRIDE), e su quel prezzo lo stadio promo si applica (`fn_resolve_prezzo_listino_v2_esito`). Il
  kit la promo la riceve: niente motivo, e niente richiesta a parte.
* **Un codice nuovo per la promo**, non `E_ARTICOLO_SOLO_COMPONENTE`: il suo messaggio parla di una
  riga di documento («non può essere inserito come riga autonoma»).
* **L'id obbligatorio è del picker, non del contesto.** I pgTAP della 3a chiamano la check senza id
  per preventivo, ordine e bolla, che non leggono il documento: metterlo nel contesto avrebbe
  ristretto i guard senza una ragione di modello.
* **Il composito nella versione di listino** esce col motivo `COMPOSITO_COME_BUNDLE` (§9.3.4): il FE lo
  propone come bundle.
* ⚠️ **Fuori dalla check resta la distinta vuota** (`E_DOC_COMPOSITO_BOM_VUOTA`, all'init dei
  componenti): il picker propone un composito senza componenti, che poi l'init rifiuta. È una
  proprietà dell'articolo, quindi un motivo di articolo; nessuna decisione l'ha chiesta nella check.
  Decisa da Tid il 2026-10-14 (**D-7**, sì): §9.4.1.

**pgTAP**:

* nuovo `catalogo/test-articoli-ammessi-picker-v1.sql` (23 test), **tutto costruito**: i parametri
  (id mancante, documento sconosciuto anche senza candidati, tetto, tipo d'eccezione); il preventivo
  (elenco e ordine, lo spento assente, `ordine`, tetto, ricerca letterale e senza maiuscole, guard e
  scrittura); il contratto (AGGIUNTA, OVERRIDE); versione di listino e distinta; la promo (picker,
  guard all'INSERT e all'UPDATE, il composito ammesso, la firma di sempre). ⭐ «Picker e guard non
  dissentono» (R-7) si prova confrontando, per **ogni** articolo restituito, il motivo del picker col
  primo motivo di `script.fn_check_articolo_riga`, e contando le righe (5 per documento, 15 sui tre
  tipi d'eccezione): un confronto su zero righe sarebbe verde per sottrazione;
* **tre presidi di struttura** che nominavano la vecchia sede, aggiornati con la nota datata:
  `test-contratto-righe-lista-v1` (test 12) e `test-guard-esclusione-figlio-bundle-v1` (test 1)
  cercano la composizione dell'esclusione in `fn_check_articolo_riga_su_contesto`;
  `test-listino-versione-in-vigore-v1` (test 13) conta fra i consumatori di
  `fn_documento_listino_operativo` il contesto al posto della check;
* **due fixture della promo** pescavano «il primo articolo attivo per id», che può essere un solo
  componente: ora lo **costruiscono** (`test-promo-articoli-v1`, `test-promo-articoli-guard-data-driven-v1`;
  nel secondo il test 3 non ha più il ramo «nessun articolo vergine»).

**Prova pre-apply** (2026-10-14, SQL estratto da `-01 … -05` + le righe del codice nuovo in testa a
transazioni annullate, corpo dei pgTAP senza runner, `PGTZ=Pacific/Kiritimati`):

* `plpgsql_check`: sulle tre funzioni nuove e sulla check i soliti avvisi «STABLE ma VOLATILE» delle
  chiamate di errore; il guard sulla promo pulito;
* su `zeroerp_ci`, da owner: test nuovo **23/23**; 19 pgTAP vicini (le tre check dei lotti 3, i
  presidi di struttura, catalogo messaggi, riferimenti morti, codici e valori attesi, risalita delle
  check sotto JIT, rubinetto, canale campo, promo) **senza e con** il lotto: cambiano esito solo i tre
  presidi sopra, verdi dopo la correzione (e rossi senza il lotto, come devono); il test del resolver
  è `ERRORE_FIXTURE` uguale prima e dopo (sullo scratch non trova un billing account);
* ⭐ **equivalenza sui dati veri** (dbdev, come app, contesto operatore, transazione annullata; le
  due metà create in `pg_temp`, perché su dbdev la DDL non si può fare): le due metà composte contro la
  check viva (`-59`) su **tutti** gli articoli (341, anche spenti) e i documenti visibili più recenti
  (40 per tipo; contratti e offerte sui tre tipi d'eccezione; 40 distinte): **100.936 confronti,
  zero dissensi**, su tutti e sette i documenti;
* **tempi del picker** (misure datate, dbdev, 2026-10-14, 268 articoli attivi): contratto con la
  ricerca vuota ~150 ms (con la check per articolo ~1,5 s); con un testo e il tetto di 51, ~50 ms;
  preventivo, ordine, versione di listino, distinta e promo fra 2 e 27 ms;
* presidio B-7 nella transazione: nessuna famiglia nuova (`E_PARAMETRO_INVALIDO` 240 → 243 punti:
  le validazioni del picker e del contesto); guardrail statici, preambolo pgTAP, licenze e
  `check_i18n_keys` verdi.

⚠️ **Non provato prima dell'apply**: la RLS del picker come app su un documento di un'altra azienda
(il contesto dà «senza listino», come per il guard); lo vede la corsa di Tid.

**Dopo l'apply (Tid)**: i pgTAP `catalogo/test-articoli-ammessi-picker-v1`, i tre presidi
(`vendite/test-contratto-righe-lista-v1`, `vendite/test-guard-esclusione-figlio-bundle-v1`,
`vendite/test-listino-versione-in-vigore-v1`), le due della promo, e le baseline di `catalogo`,
`script`, `vendite`, `dbops`. ✅ **2026-10-14: migrazione applicata, test verdi** (Tid). Con la corsa
di Tid è coperto anche ciò che la prova pre-apply non poteva vedere: la RLS del picker come app.

**Doc**: manual nuovi `catalogo/manual/fn_articoli_ammessi`, `script/manual/fn_articolo_riga_contesto`,
`script/manual/fn_check_articolo_riga_su_contesto`; aggiornati `script/manual/fn_check_articolo_riga`
(la promo, le due metà, il ponte A-8 nel contesto), `script/manual/trgfn_righe_guard_articolo_ammesso`
(il montaggio sulla promo), `vendite/manual/promo_articoli`. La doc generata la rigenera la build di Tid.

### 9.4.1 D-7 — il kit senza componenti (`20261014-06`, ✅ applicato da Tid il 2026-10-14, pgTAP verdi)

Decisione di Tid del 2026-10-14: un composito senza componenti non compare più come ammesso nel
picker, per poi essere rifiutato dall'init dei componenti dopo la scelta.

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261014-06` | `script.fn_check_articolo_riga_su_contesto` (stessa firma, `CREATE OR REPLACE`, corpo dal `-02`): motivo nuovo `KIT_SENZA_COMPONENTI` in posizione 2, dopo il solo componente, per preventivo, ordine, bolla e per AGGIUNTA e OVERRIDE di offerta e contratto; riscritto anche il COMMENT di `script.fn_check_articolo_riga`, che elenca le regole. Rollback: corpo e COMMENT del `-02`/`-03` |

**Codice**: `E_ARTICOLO_KIT_SENZA_COMPONENTI` (1307, DATO_ERRATO; valori: codice dell'articolo; campo
`articolo_id`). **Locales**: `vendite.righe.articolo_reason.kit_senza_componenti` (it, en);
`check_i18n_keys` pulito.

**Scelte del team DB**:

* **«Vuoto» = nessun componente attivo, a qualunque data.** La check non ha una data; l'init giudica i
  componenti validi alla data del documento. Così la check rifiuta solo ciò che l'init rifiuterebbe
  sempre, e non rifiuta mai un kit che l'init accetta. Il caso «componenti che ci sono ma non a quella
  data» resta all'init, col suo codice.
* **Un codice nuovo**, non `E_DOC_COMPOSITO_BOM_VUOTA`: quella frase porta la data («senza componenti
  validi alla data [%s]»).
* **Fuori**: l'ESCLUSIONE (escludere non vende), la versione di listino e la distinta (il composito ha
  già i suoi motivi), la promo (il prezzo del kit lo dà il contratto, non i componenti).

**pgTAP**:

* `catalogo/test-articoli-ammessi-picker-v1` (plan 23 → 26): nella fixture P ha ora il suo componente F,
  e V è il kit vuoto; nuovi test 24 (il guard dell'ordine rifiuta V), 25 (AGGIUNTA: primo motivo), 26
  (ESCLUSIONE: non si giudica); attese dei test 5-7, 10, 15, 17, 18 col nuovo elenco (7 articoli);
* **due fixture** costruivano un kit vuoto e lo mettevano in un contratto, cioè il dato che D-7 ora
  vieta: `vendite/test-righe-erogazione-da-articolo-v1` (test 22) e
  `vendite/test-righe-quantita-per-fonte-v1` (test 5 e 13). Il kit K riceve il suo componente KC.

**Prova pre-apply** (2026-10-14, `zeroerp_ci`, da owner, SQL estratto del `-06` + le righe del codice
in transazioni annullate, `PGTZ=Pacific/Kiritimati`):

* test del picker 26/26; senza il `-06` rossi solo il 5, il 24 e il 25;
* **83 pgTAP** (tutti quelli che nominano `is_composito`, più i presidi trasversali: catalogo messaggi,
  riferimenti morti, codici e valori attesi, risalita delle check, rubinetto, canale campo, le tre
  check dei lotti 3) senza e con il `-06`: cambiano esito solo il test del picker e le due fixture
  sopra, ora verdi in entrambi i casi;
* le quattro pgTAP che **pescano** un composito dai dati di dbdev (`test-componenti-helpers-v1`,
  `test-preventivi-righe-componenti-v1`, `test-ddt-componenti-senza-prezzo-v1`,
  `test-fn-init-componenti-jsonb-override-v1`) scelgono compositi **con** componenti attivi: il `-06`
  non le tocca;
* `plpgsql_check`: il solito avviso STABLE/VOLATILE; B-7 invariato; guardrail statici e preambolo verdi.

**Fatto datato** (dbdev come app, 2026-10-14): 40 compositi senza componenti attivi, di cui 2 attivi.
Le righe già scritte non si rigiudicano (il guard è `UPDATE OF articolo_id`).

**Esito** (Tid, 2026-10-14): `20261014-06` applicato; pgTAP `catalogo/test-articoli-ammessi-picker-v1`,
`vendite/test-righe-erogazione-da-articolo-v1`, `vendite/test-righe-quantita-per-fonte-v1` verdi.

**Doc**: manual `script/manual/fn_check_articolo_riga` (le tabelle dei motivi),
`script/manual/fn_check_articolo_riga_su_contesto`; guide `gestione-preventivi`, `gestione-ordini`,
`gestione-ddt`, `gestione-offerte-commerciali`, `gestione-contratti`.

### 9.5 Lotto 5 — doc e richieste (2026-10-14)

* **Guide**: `gestione-listini` (§2.5 e §9: nessuna promo su un solo componente; il kit sì);
  `gestione-offerte-commerciali` (§2.2: quali articoli ammette un'eccezione, le regole dei Lotti 3b,
  che la guida non diceva). Preventivi, ordini e bolle le hanno dal Lotto 3a, i contratti dal 3b, i
  listini dal 3c. Il picker **a video** non c'è ancora: le guide lo racconteranno col giro BE/FE,
  quando sarà lo stato attuale.
* **Linee guida SQL §12.6** (R-8: la regola generale): un picker di un campo giudicato da un guard è
  una lettura nel database sulla **stessa** check; gli esclusi restano col motivo; il contesto è la
  testata salvata; con molti candidati su un documento la check si divide in contesto e motivi. Due
  precedenti: `fn_listini_selezionabili`, `fn_articoli_ammessi`.
* **Richieste BE/FE**: raccolte nel §9.6, con la riga del Lotto 4.

### 9.6 Il giro BE/FE finale (raccolta)

Il BE/FE parte quando i lotti DB sono chiusi (Tid, 2026-10-13). Qui si raccolgono le richieste lotto per
lotto, così il giro finale ha un elenco solo:

| Lotto | Richiesta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | policy e ripiego per `E_BOM_COMPONENTE_COMPOSITO`, `E_BOM_COMPONENTE_DIVENTA_COMPOSITO`, `E_ARTICOLO_ONERE_NATURA_MERCE`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 3a    | policy e ripiego per `E_RIGA_NATURA_NON_AMMESSA`, ~~`E_ARTICOLO_SOLO_COMPONENTE_IN_USO`~~ (ritirato dalla 3u); `E_ARTICOLO_SOLO_COMPONENTE` ora ha il campo `articolo_id` (la nota «non è un campo del form» va rivista). **FE**: le `reason_key` sono nei locales; il form dell'articolo spegne `is_solo_componente` dai campi non modificabili                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 3u    | **BE**: policy e ripiego per `E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE` (campo nel contesto); endpoint per il verbo `catalogo.fn_articolo_correggi_struttura`, solo SUPER_ADMIN; verifica dei quattro test Django che toccano i flag (§9.3.2). **FE**: nella scheda articolo le otto colonne arrivano spente da `non_editable_fields` quando l'articolo è usato (nessuna logica nuova); un'azione amministratore «correggi struttura» che chiama l'endpoint                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 3b    | **BE**: policy e ripiego per `E_ARTICOLO_SENZA_EROGAZIONE`, `E_RIGA_ECCEZIONE_SENZA_LISTINO`, `E_RIGA_ECCEZIONE_FUORI_LISTINO`; **A-8-bis** (deciso da Tid il 2026-10-13): `fn_documento_listino_operativo`, `fn_check_esclusione_articolo_documento`, `fn_check_riga_erogazione` passano a `config.tipi_entita` (`OFFERTA_COMMERCIALE`, `CONTRATTO`) insieme ai chiamanti del BE, e si ritira il ponte in `fn_check_articolo_riga`; doc BE `api_contratti`, `modello-contratti` (nominano i guard ritirati). **FE**: le quattro chiavi `vendite.righe.articolo_reason.*` le ha già aggiunte la sessione DB                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 3c    | **BE**: policy e ripiego per `E_BOM_COMPONENTE_PADRE` (campo `componente_id`); i codici del listino e della distinta ora arrivano dal guard di tabella col campo nel contesto (`articolo_id`, `componente_id`); doc BE `catalogo-building-block-backend` (nomina il guard della tipologia ritirato). **FE**: le sei chiavi `vendite.righe.articolo_reason.*` e `catalogo.distinta.componente_reason.*` le ha già aggiunte la sessione DB; nel picker della versione di listino il composito si propone come bundle (`COMPOSITO_COME_BUNDLE`), non come escluso                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2     | **BE**: policy e ripiego per `E_RIGA_NATURA_VENDITA_IMMUTABILE`; via `E_PREV_RIGA_NATURA_IMMUTABILE` (ritirato). **FE**: ✅ le cinque chiavi `config.tipi_entita.*` le ha già aggiunte la sessione DB (§9.2)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 4     | **BE**: il lookup articoli delle **righe di documento** legge `catalogo.fn_articoli_ammessi(documento, documento_id, search, limit, tipo_eccezione, padre)` (§9.4) e unisce le colonne di `catalogo.vw_articoli_dettaglio` su `articolo_id`, ordinando su `ordine`; il tetto e la sonda `+1` restano in `fetch_con_sonda` (passa `limit + 1`); `motivo` passa al FE intero. **Si ritirano** per quelle righe i filtri liberi (`escludi_destinazione_tipi`, `is_solo_componente`, `is_composito`) di `catalogo_repository.lookup_articoli`; restano la ricerca e i filtri delle consultazioni (attivi/inattivi, `solo_oneri`, `gestito_a_magazzino` di inventari e rettifiche, che non sono righe di questa check). Policy e ripiego per `E_PROMO_ARTICOLO_SOLO_COMPONENTE` e, da D-7, per `E_ARTICOLO_KIT_SENZA_COMPONENTI` (campo `articolo_id` per entrambi). **FE**: `ArticoloLookup` riceve `documento` e l'id del documento (o il padre della distinta, o il tipo d'eccezione) dalla maschera, al posto dei filtri; si ricarica quando cambiano; un articolo col `motivo` si mostra non selezionabile con la `reason_key` (le chiavi ci sono tutte nei locales); nella versione di listino `COMPOSITO_COME_BUNDLE` apre la strada del bundle. Maschere: righe di preventivo, ordine, bolla, eccezioni di offerta e contratto, versione di listino, distinta, promo. Catalogo BB BE e FE aggiornati (`ArticoloLookup` cambia contratto). Guide: il picker a video (§9.5) |

### 9.7 Il giro BE/FE (sessione BE, `dev/backend-tid`, 2026-10-14)

Fatto tutto il §9.6 **tranne l'A-8-bis** (§9.7.3), che vuole un pezzo DB applicato nello stesso
momento.

#### 9.7.1 Che cosa è stato fatto

| Lotto                | Fatto                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1, 2, 3a, 3u, 3b, 3c | Policy e ripieghi c'erano già (`a81596789`). `E_PREV_RIGA_NATURA_IMMUTABILE` ed `E_ARTICOLO_SOLO_COMPONENTE_IN_USO` stanno fra i ritirati del modulo generato e nessun punto vivo li nomina                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 4, D-7               | `error_policies_generated.py` rigenerato: entrano `E_PROMO_ARTICOLO_SOLO_COMPONENTE` ed `E_ARTICOLO_KIT_SENZA_COMPONENTI`, entrambi `DATO_ERRATO`, nessuna classe cambiata; i due ripieghi in `error_messages_fallback.py`                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 4 — BE               | `GET /catalogo/articoli/lookup/?documento=…&documento_id=…&tipo_eccezione=…&articolo_padre_id=…` → `CatalogoRepository.lookup_articoli_ammessi`: `catalogo.fn_articoli_ammessi` unita a `vw_articoli_dettaglio`, ordinata su `ordine`, `motivo` intero (decodificato con `jsonb_out`: psycopg 3 lo consegnava come stringa, e ogni articolo sarebbe sembrato ammesso). Il tetto resta in `fetch_con_sonda` (alla funzione `p_limit` NULL). Accanto a `documento` i filtri liberi danno 400. `tipo_eccezione` si valida contro l'enum letto dal DB (un valore estraneo al cast sarebbe un 500). **Ritirati** `is_solo_componente` ed `escludi_destinazione` |
| 4 — FE               | `ArticoloLookup`: prop `documento`, `documentoId`, `tipoEccezione`, `articoloPadreId`, `motiviSelezionabili`; l'escluso resta in elenco, **spento**, col testo del motivo (`testoMotivi`, coi `valori`). Le otto maschere passano il documento al posto dei filtri; `RigheEccezioniDrawer` riceve `documento` dai due involucri; la versione di listino lascia sceglibile `COMPOSITO_COME_BUNDLE` (la strada del bundle c'era già)                                                                                                                                                                                                                         |
| 3a, 3u — FE          | La scheda articolo spegne da `non_editable_fields` tutte le colonne strutturali che il DB può bloccare: prima ne leggeva tre (composito, solo componente, seriale), ora anche natura, tipologia di listino, gestito a magazzino e lotto. La causale onere non è in quel form                                                                                                                                                                                                                                                                                                                                                                               |
| 3u — BE/FE           | `POST /catalogo/articoli/<id>/struttura/` (`AdminAPIView`, `Idempotency-Key`), body `{"campi": {…}}` → `catalogo.fn_articolo_correggi_struttura`, risponde col dettaglio. Nella scheda: azione «Correggi struttura», solo SUPER_ADMIN e solo con una struttura bloccata; riapre i campi, e al salvataggio le colonne cambiate passano dal verbo, poi il PATCH di sempre                                                                                                                                                                                                                                                                                    |
| 3u — verifica        | I quattro test Django che toccano i flag (§9.3.2): 18 verdi su dbdev, nessuno saltato                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 3b, 3c — doc         | `api_contratti`, `modello-contratti` e il catalogo BB backend non nominano più i guard ritirati                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 4 — doc              | `api_catalogo` (§1.6-bis, §2.1), cataloghi BB backend e frontend, guide di preventivi, ordini, bolle, offerte, contratti e listini: il picker a video                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

#### 9.7.2 Le prove

* **Su dbdev, chiamata vera** (contesto operatore): il picker risponde su tutti e sette i
  documenti, con motivi e `valori` interi (per esempio `IVA_DISCORDANTE` sulla distinta,
  `TIPOLOGIA_MANCANTE` sulla versione). Il verbo: il SUPER_ADMIN corregge; un operatore e una
  colonna estranea li rifiuta il DB, e anche il corpo vuoto (il controllo che il BE ne
  ripeteva è stato tolto in revisione, 2026-10-14: test 7 su DB vero). Tutto in transazioni annullate.
* **Test**: `apps.catalogo` 135 verdi, di cui il file nuovo su DB vero
  `tests/db/test_articoli_ammessi_db.py` (7, costruiti o indipendenti dai dati), provato per
  mutazione sulla decodifica di `motivo`; FE 886 verdi, di cui `ArticoloLookup.spec.js` nuovo (4,
  provato per mutazione sull'escluso sceglibile); `check_i18n_keys` pulito; build FE riuscita.
* ⚠️ **Fatto datato**: `apps.core` ha **tre rossi che non vengono da questo giro**. Il DB di
  sviluppo è **avanti** rispetto a git: porta i codici `E_CLIENTE_*` ed `E_STATISTICHE_MANCANTI`
  di un altro cantiere (brief-db-cliente-manuale-uno-per-soggetto-e-utility), che non sono nel CSV
  in git. Per questo il modulo generato **non** è stato rigenerato una seconda volta, e
  `E_DATA_APERTURA` risulta una promessa vuota (il suo sito non c'è più a DB). Si chiudono col
  push di quel cantiere e col giro BE suo.

#### 9.7.3 Richieste al team DB

* **R-DB-1 — A-8-bis.** `vendite.fn_documento_listino_operativo`,
  `script.fn_check_esclusione_articolo_documento` e `script.fn_check_riga_erogazione` passano dalla
  grammatica `OFFERTA | CONTRATTO` ai codici di `config.tipi_entita` (`OFFERTA_COMMERCIALE`,
  `CONTRATTO`), e si ritira il ponte in `script.fn_articolo_riga_contesto` (manual: «Ponte A-8»).
  ⚠️ **Il BE non può andare per primo**: chiama `fn_documento_listino_operativo` con `OFFERTA` /
  `CONTRATTO` (`_documento_eccezioni_repo.py`, `offerte_service.py`, `contratti_service.py`), e un
  cambio di grammatica da una parte sola rompe le eccezioni di offerta e contratto. Proposta: il
  team DB scrive e prova il changeSet; la sessione BE prepara il suo pezzo sullo stesso giro e Tid
  applica i due insieme. Il pezzo BE è piccolo (i valori passati), più un test su DB vero del
  binding con le due grammatiche.
* **R-DB-2 — la nota di `E_ARTICOLO_SOLO_COMPONENTE`** in `codici_errore.csv` dice ancora
  «── 400 · il problema non e' un campo del form (`show_error_banner`) ──». Dalla 3a il codice porta
  il campo `articolo_id`: la nota va riscritta. Nessuna ricaduta sul comportamento: il campo a
  video lo accende `fields`, che arriva già.
* **R-DB-3 — l'elenco delle colonne correggibili, letto e non ricopiato** (revisione del
  2026-10-14, ok di Tid). Le otto colonne che `catalogo.fn_articolo_correggi_struttura` accetta
  stanno solo nella sua costante `c_ammessi`, e la scheda articolo le **ricopia**
  (`COLONNE_STRUTTURA` in `ArticoloDrawer.vue`) per sapere quali controlli riaprire: alla nona
  colonna le due copie divergono, e il campo nuovo resta spento anche in correzione. Richiesta:
  una sede leggibile (per esempio una funzione `catalogo.fn_articolo_colonne_struttura()` che il
  verbo stesso usa al posto della costante); il BE la porta nel dettaglio dell'articolo
  (`struttura_correggibile`) e il FE ritira la sua lista nello stesso giro.

#### 9.7.3-bis Richiesta alla sessione BE/FE (revisione del 2026-10-14, ok di Tid)

* **R-BE-1 — il salvataggio con correzione di struttura in UNA transazione.** Oggi la scheda fa
  due scritture: `POST …/struttura/` (il verbo), poi il `PATCH` di sempre. Se il PATCH fallisce
  (una descrizione vuota, un altro guard), la struttura è **già corretta** a DB e l'operatore vede
  solo l'errore. In revisione la scheda allinea il dettaglio dopo il verbo (un nuovo salvataggio
  non lo rimanda), ma il salvataggio a metà resta. Proposta, tutta BE/FE e senza DB: il `PATCH`
  dell'articolo accetta la correzione (`{"correzione_struttura": true, …}`, solo `AdminAPIView`
  o col controllo SUPER_ADMIN del verbo), e il service chiama il verbo con le colonne strutturali
  cambiate e poi l'UPDATE, dentro **un** `transaction.atomic()`; il FE torna a una chiamata sola.
  Si ritira `POST …/struttura/` nello stesso giro, se nessun altro lo usa. Prova: test su DB vero
  con un PATCH che fallisce dopo la correzione, e la struttura che resta quella di prima.

#### 9.7.5 La revisione del codice (sessione BE, 2026-10-14)

Prima del commit, una revisione critica del giro. Corretti:

| Che cosa                                                                                                                                               | Perché                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Tolto dal service il controllo di `campi` (oggetto non vuoto) della correzione di struttura                                                            | ripeteva la regola del verbo, che lo rifiuta già con `E_PARAMETRO_INVALIDO` (`DATO_ERRATO`, 400); il commento diceva il contrario. Prova su DB vero: test 7 di `test_articoli_ammessi_db.py`                                                                                                                                         |
| `qp_str_upper` al posto dell'`.upper()` a mano; il tetto `50` in una sede (`LOOKUP_ARTICOLI_MAX`); `LIMITE_RIGHE` e `buildDisplay` in `ArticoloLookup` | regola del 2: copie della stessa cosa                                                                                                                                                                                                                                                                                                |
| Dopo il verbo la scheda articolo allinea il dettaglio                                                                                                  | se il PATCH che segue fallisce, la struttura è già corretta: senza, un nuovo salvataggio la rimandava al verbo. Il salvataggio a metà resta (R-BE-1)                                                                                                                                                                                 |
| `is_solo_componente` ed `escludi_destinazione` danno `400` (`…_ritirato`) invece di essere ignorati                                                    | lo smoke `smoke-test-preventivi-smistamento-ordine.sh` li mandava ancora ed era verde senza provare niente                                                                                                                                                                                                                           |
| Lo smoke: il passo 1 diventa il 2-bis, il picker del preventivo sulla sede unica                                                                       | l'articolo che il guard ha appena accettato deve uscire **ammesso**. ✅ Eseguito e verde: è nel perimetro di `scripts/smoke-baseline.sh` (gli `smoke-test-*.sh` dal 2026-10-12), e la corsa di Tid non dà regressioni; nel registro dei non-verdi (`baseline-smoke.tsv`, rigenerato il 2026-10-22) non c'è (verificato il 2026-10-23) |
| `test_gli_ammessi_vengono_prima` costruisce i due articoli (l'escluso alfabeticamente primo)                                                           | prima poteva passare per le sole 50 righe. Provato per mutazione (ordine per codice → rosso)                                                                                                                                                                                                                                         |
| `test_struttura_articolo_e_da_amministratore` è una chiamata HTTP: 403, 200, 400 senza `Idempotency-Key`                                               | prima controllava solo la classe. Provato per mutazione (permesso tolto → rosso)                                                                                                                                                                                                                                                     |

Prove: `apps.catalogo` 137 verdi su DB vero (`ZEROERP_TEST_DB_E2E=1`), FE `src/catalogo` verde,
gate mypy pulito.

#### 9.7.4 Il collaudo a video (Tid)

✅ **Fatto da Tid il 2026-10-23: tutti e nove i punti ok** (✅ a fine punto). Il punto 2 l'ha visto dopo `adbb283ee` (2026-10-22), che aveva toccato `offerte_service` e `contratti_service`.

1. **Righe di preventivo, ordine e bolla**: cercando un articolo compaiono prima gli ammessi; un
   servizio, un solo componente o un kit senza componenti compaiono **grigi, col motivo sotto**,
   e non si scelgono. ✅
2. **Eccezioni di offerta e contratto** (riga nuova, AGGIUNTA): un articolo già nel listino è
   grigio, col motivo che rimanda al prezzo diverso (OVERRIDE). ✅
3. **Versione di listino**: un articolo di un'altra tipologia è grigio; un **kit** porta l'avviso
   «entra come bundle» ma si sceglie, e apre i prezzi dei componenti. ✅
4. **Distinta**: il kit stesso e un componente con IVA diversa sono grigi col motivo. ✅
5. **Promo**: un solo componente è grigio col motivo. ✅
6. **Scheda di un articolo usato** (in un documento): natura, tipologia di listino, composito,
   solo componente, gestito a magazzino, lotto, seriale sono **spenti**. Da SUPER_ADMIN compare
   «Correggi struttura»: dopo la conferma i campi si riaprono, e il salvataggio passa. Da
   operatore il pulsante non c'è. ✅
7. **Consultazioni invariate**: il picker di movimenti, disponibilità, inventari e rettifiche
   (solo gestiti a magazzino) e del test resolver si comporta come prima. ✅
8. **Correzione in un salvataggio solo** (§9.8.7, 2026-10-18): da SUPER_ADMIN, «Correggi
   struttura» su un articolo usato, cambiare un campo strutturale **e** la descrizione, salvare:
   tutte e due le modifiche ci sono, con un salvataggio solo. (Il rifiuto a metà, che annulla
   anche la correzione, non si provoca dal form: lo prova il test 8 sul DB vero.) ✅
9. **Correzione che renderebbe non valide righe aperte** (A-11): rendere «solo componente» un
   articolo che sta in un preventivo in bozza: rifiuto col messaggio (righe e documenti contati),
   e l'articolo resta com'era. ✅

### 9.8 Il giro DB del 2026-10-18 (R-DB-2, R-DB-3; l'A-8-bis rivisto)

#### 9.8.1 R-DB-3 — le colonne strutturali, lette da una sede (✅ applicato da Tid il 2026-10-18, pgTAP verdi)

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261018-70` | nuova `catalogo.fn_articolo_colonne_struttura()` → `text[]`: le colonne strutturali dell'articolo, **lette** dalle regole accese del form in `dbops.lock_columns_conditional` sul predicato dell'uso (`catalogo.fn_articolo_usato($1::uuid)`, seed `20261013-51`), nell'ordine della dichiarazione. `LANGUAGE sql`, STABLE, INVOKER, EXECUTE all'app                                   |
| `20261018-71` | `catalogo.fn_articolo_correggi_struttura`: stessa firma, stessi codici e frasi. Le colonne ammesse dalla funzione nuova al posto della costante `c_ammessi`; l'UPDATE si **costruisce** dalle sole colonne passate (`SET <col> = r.<col>` da `jsonb_populate_record(NULL::catalogo.articoli, p_campi)`, nomi quotati con `%I` e già controllati). Rollback: il corpo del `20261013-50` |

**Scelte del team DB** (da guardare):

* **La sede c'era già, come dato.** Le otto colonne stanno nelle regole del form del Lotto 3u: sono
  quelle che il form spegne quando l'articolo è usato, cioè esattamente quelle che la correzione
  riapre. Una funzione con il suo array sarebbe stata la quarta copia (verbo, guard, registro, FE).
  Il predicato si riconosce dal suo testo, che in quel registro è la chiave della regola.
* **Anche la scrittura viene dalla sede.** Togliere la costante e lasciare l'UPDATE colonna per
  colonna avrebbe spostato la copia: alla nona colonna il controllo l'avrebbe ammessa e l'UPDATE
  l'avrebbe ignorata, in silenzio. La conversione dei valori è la stessa di prima (dal testo, col
  tipo della colonna): un valore sbagliato dà `22P02` come prima.
* ⚠️ **Una differenza di comportamento, voluta.** Prima l'UPDATE riscriveva tutte e otto le colonne
  (anche quelle non passate), e scattavano tutti i trigger `UPDATE OF` di quelle colonne. Ora
  scattano solo quelli delle colonne passate. Sui dati che i guard tengono validi non cambia
  niente: i guard di struttura confrontano `NEW` con `OLD`, e quello dell'onere giudica uno stato
  che lui stesso tiene valido.
* **Le copie che non si derivano restano, presidiate.** Il guard `trgfn_articoli_guard_struttura_se_usato`
  ha l'elenco nel trigger (`UPDATE OF`) e nel `CASE`: un trigger non legge le sue colonne da una
  funzione. Il pgTAP nuovo (test 3-4) li confronta con la sede.
* Una regola spenta (`enabled = false`) esce dalla sede: il form lascia il campo aperto, e il
  presidio la vede come divergenza dal guard.

**pgTAP**: nuovo `catalogo/test-articolo-colonne-struttura-v1.sql` (12 test, tutto costruito): la
sede contro il registro; i due presidi sul guard; il verbo che non ha più la costante; la correzione
di un boolean e di un bigint, le colonne non passate intatte, il `22P02`, la colonna estranea; ⭐ una
**nona regola** messa nel registro dentro la transazione, che la sede include e il verbo scrive
(prova che controllo e scrittura vengono dalla stessa sede); una regola spenta, che esce dalla sede e
che il verbo rifiuta.

**Prova pre-apply** (2026-10-18, `zeroerp_ruoli`, da owner, SQL estratto da `-70`/`-71` dopo il
`BEGIN;` del pgTAP, `PGTZ=Pacific/Kiritimati`):

* test nuovo **12/12**; senza l'SQL estratto rosso dal test 1 (la funzione non c'è);
* `catalogo/test-articolo-usato-struttura-v1` (il pgTAP del verbo, 17 test) e
  `dbops/test-articoli-a-magazzino-prontezza-v1` (6): stesso esito senza e con. Nel primo il test
  17 è rosso da owner per costruzione (dichiarato nel file: la porta vuole il proprietario);
* `plpgsql_check` sul verbo nuovo: pulito;
* presidi trasversali (`test-riferimenti-morti-v1`, `test-security-definer-search-path-v1`,
  `test-postura-proprietario-rls-v1`, `test-app-postura-schema-django-v1`,
  `test-registri-append-only-postura-v1`): stesso esito senza e con;
* guardrail statici e licenze verdi sui file nuovi (il rosso del preambolo è di un file di un altro
  cantiere, `test-automazioni-guasto-ambiente-rilanciato-v1`).

**Dopo l'apply (Tid)**: i due pgTAP del catalogo qui sopra, e la baseline di `catalogo`.

**Doc**: nuovo `catalogo/manual/fn_articolo_colonne_struttura`; aggiornati
`catalogo/manual/fn_articolo_correggi_struttura`, `catalogo/manual/trgfn_articoli_guard_struttura_se_usato`.
La doc generata la rigenera la build di Tid.

**Richiesta BE/FE** (5d, dopo l'apply): il dettaglio dell'articolo porta
`struttura_correggibile` = `SELECT catalogo.fn_articolo_colonne_struttura()` (array di nomi di
colonna, nell'ordine della dichiarazione); la scheda articolo riapre in correzione **quei** campi e
ritira `COLONNE_STRUTTURA` nello stesso giro. Nessun codice nuovo, nessuna policy da toccare.

#### 9.8.2 R-DB-2 — la nota di `E_ARTICOLO_SOLO_COMPONENTE` (fatto)

In `codici_errore.csv` la nota diceva «il problema non e' un campo del form»; ora dice da dove viene
il codice (motivo 1 della check per tipo di riga, i documenti che lo sollevano, il picker) e che
porta il campo `articolo_id`. Solo la nota: classe e messaggio non cambiano. **BE**: nessuna
ricaduta di comportamento; il commento in `error_policies_generated.py` si allinea alla prossima
rigenerazione.

#### 9.8.3 A-8-bis — così com'è scritta non si fa: decisione per Tid (A-8-ter)

**Che cosa chiedeva.** `fn_documento_listino_operativo`, `fn_check_esclusione_articolo_documento` e
`fn_check_riga_erogazione` passano da `OFFERTA | CONTRATTO` ai codici di `config.tipi_entita`
(`OFFERTA_COMMERCIALE`, `CONTRATTO`), e si ritira il ponte in `script.fn_articolo_riga_contesto`.

**Che cosa ha trovato il censimento** (doc auto-generata e backend, 2026-10-18; struttura, non
popolazione). Quei tre non sono una grammatica a sé: sono tre membri di una famiglia che parla
`OFFERTA | CONTRATTO`, dentro una grammatica più grande.

| Famiglia                                                                                                            | Membri                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Chiamanti                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **documenti con eccezioni** (`OFFERTA \| CONTRATTO`)                                                                | `vendite.fn_documento_listino_operativo`, `fn_documento_righe_eccezione`, `fn_documento_righe_preview`, `fn_documento_riga_erogazioni`, `fn_offerta_righe_espanse` (letterale `'OFFERTA'`); `script.fn_check_esclusione_articolo_documento`, `fn_check_riga_erogazione`, `fn_check_listino_congelabile`, `trgfn_righe_guard_erogazione_perimetro` (quattro montaggi con `'CONTRATTO'` / `'OFFERTA'` negli argomenti), `trgfn_righe_default_erogazione_da_articolo` | DB: si chiamano fra loro, più i freeze e i guard di transizione di offerta e contratto, `fn_available_actions_offerta` / `_contratto`. BE: `_documento_eccezioni_repo.py` (`DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA"]`, due funzioni), `offerte_service.py`, `contratti_service.py` |
| **testate di documento** (`DDT \| ORDINE \| CONTRATTO \| OFFERTA \| PREVENTIVO \| RESO \| COMMESSA \| EMAIL_BOZZA`) | `script.fn_get_stato_testata_documento`, `fn_get_testata_id_di_riga`, `fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede` e altri: 27 pagine della doc auto-generata li leggono                                                                                                                                                                                                                                                                            | lock fuori bozza, annullo con legami, indirizzi, lineage; BE in più punti (per esempio `_annullo_con_legami.py`, che traduce a sua volta `OFFERTA` nel codice delle sorgenti)                                                                                                                  |

**Perché spostarne tre peggiora.** `fn_documento_righe_preview` riceve `p_documento` e lo passa
**sia** a `fn_documento_listino_operativo` e `fn_check_esclusione_articolo_documento` (che
cambierebbero) **sia** a `fn_documento_righe_eccezione` (che non cambierebbe): dovrebbe tradurre
dentro. Lo stesso per `fn_documento_riga_erogazioni` verso `fn_check_riga_erogazione`, per i
quattro montaggi del guard dell'erogazione, per `fn_offerta_righe_espanse`. E il ponte del contesto
**non sparirebbe**: `fn_articolo_riga_contesto` chiama anche `fn_get_stato_testata_documento` (per
l'etichetta), che parla la grammatica delle testate. Oggi c'è **un** punto di traduzione,
dichiarato; dopo l'A-8-bis ce ne sarebbero cinque o sei, sparsi. È la regola del 2 al contrario.

**Le tre strade.**

| #   | Strada                                                                                                                                                                                                                                                                                                                                                         | Costo                                                                                                                      | Che cosa resta                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | ⭐ **Togliere l'A-8-bis da questo brief.** Il ponte in `fn_articolo_riga_contesto` resta, come punto unico e dichiarato di traduzione fra il vocabolario delle entità (`config.tipi_entita`, quello del picker e della check) e la grammatica delle testate. All'archiviazione, un brief nuovo (con la sua voce di debito) per **una** grammatica dei documenti | nessuno ora; niente pezzo BE (5b cade)                                                                                     | due vocabolari per la stessa cosa, con un ponte solo, fino al brief nuovo |
| 2   | Spostare **tutta** la famiglia «documenti con eccezioni»                                                                                                                                                                                                                                                                                                       | ~11 oggetti DB, quattro montaggi, il repository BE e i due service, nello stesso apply                                     | il ponte resta comunque, verso le testate (punto sopra)                   |
| 3   | Unificare **tutte** le grammatiche dei documenti su `config.tipi_entita`                                                                                                                                                                                                                                                                                       | un cantiere: decine di funzioni, i lettori del BE, altri brief aperti sugli stessi oggetti (indirizzi, lock delle testate) | niente, a cantiere chiuso                                                 |

✅ **Decisione di Tid (2026-10-18): la 1 qui, la 3 come direzione** in [brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md); la 5b cade.

**Proposta del team DB: la 1.** La 2 costa quasi quanto la 3 e lascia il ponte che doveva togliere;
la 3 è un cantiere a sé, che non va aperto dentro questo brief. La domanda giusta per il brief nuovo
non è «quale funzione si sposta», ma «una grammatica dei documenti: quale, e chi la traduce» (oggi
le traduzioni stanno nel contesto, in `_annullo_con_legami.py` e altrove).

#### 9.8.4 A-11 — la correzione non rende non valide le righe dei documenti aperti (✅ applicato, corretto dal §9.8.6)

Decisione di Tid del 2026-10-18 (strada «a»). La porta amministratore è l'unica strada da cui un
articolo **usato** cambia struttura. Senza questa regola, rendere «solo componente» un articolo che
sta in un ordine confermato lasciava l'ordine com'era e faceva fallire a metà la generazione della
bolla (il guard di `ddt_righe`): è l'«errore a metà strada» del §8.3, punto 4.

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `20261018-72` | `catalogo.fn_articolo_correggi_struttura` (stessa firma, `CREATE OR REPLACE`, corpo dal `-71`): dopo l'UPDATE rigiudica le righe **vive** dell'articolo con `script.fn_check_articolo_riga` (primo motivo, con la natura e il tipo d'eccezione della riga); se una non è più ammessa → `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, e la correzione si annulla. Rollback: il corpo del `-71` |

**Codice**: `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` (id 1361, CONFLITTO_STATO; valori: codice
dell'articolo, numero di righe, numero di documenti; `dettaglio.righe`: le prime 50, ciascuna
`{documento, documento_id, riga_id, codice}`; nessun campo del form). ⚠️ Id preso come max + 1 mentre
un'altra sessione aggiunge codici allo stesso CSV (1359, 1360): se nel frattempo ne ha preso uno, va
spostato.

**Scelte del team DB** (da guardare):

* **«Viva» = attiva, e il documento non è chiuso.** Per i cinque documenti si legge `fase <> 'CHIUSO'`:
  è la colonna che tutti e cinque i vocabolari degli stati hanno (`terminale` manca su quello della
  bolla). Versione di listino: stato diverso da `CHIUSA`. Promo: periodo non finito alla data
  operativa. Sono le sette tabelle del guard di riga; un pgTAP fa rosso se il guard viene montato
  su un'ottava tabella senza che il verbo la legga.
* **Dentro il verbo, non in una funzione a parte**: ha un solo consumatore (regola del 2). La check è
  la stessa dei guard, quindi nessuna copia della regola.
* **In tutte le aziende**: il verbo è già SECURITY DEFINER, come `catalogo.fn_articolo_usato` (gli
  articoli sono unici per tutte). Il messaggio dà solo numeri; i documenti sono nel dettaglio.
  Provato a parte su dbdev, in sola lettura, che la check gira sotto il `search_path` stretto del
  verbo su tutti e sette i documenti (contratto, offerta, listino, promo, bolla, …): nessun errore.
* **Fuori**, e perché:
  * la **distinta**: il caso «kit svuotato dopo l'uso» è già chiuso. Un legame non si cancella
    (`E_BOM_MODIFICA_VIETATA`) e non si spegne se le righe dei documenti hanno i suoi componenti (i
    `trgfn_prevent_deactivate_if_children` su preventivi, ordini, bolle, offerte, contratti,
    listini). Il composito come componente lo ferma `trgfn_articoli_guard_flags_struttura_bom_attiva`;
  * le **righe nate prima dei guard**: non c'è produzione (Tid), quindi nessuna logica per loro;
  * **magazzino, lotto, matricola**: li giudica `fn_check_riga_magazzino` all'emissione della
    bolla, un passo che ha già il suo motivo.
* Una correzione che non tocca i motivi passa anche con righe vive. Esempio: la natura, che sulle
  righe di preventivo, ordine e bolla è congelata (A-4).

**Fatto datato** (dbdev, 2026-10-18, lettura come owner): cinque righe d'offerta già oggi non
ammesse (`E_RIGA_ECCEZIONE_FUORI_LISTINO`, OVERRIDE ed ESCLUSIONE nate prima dell'A-5); due sono in
offerte aperte (84, 85, ACCETTATA). ~~Correggere la struttura di quei due articoli sarebbe rifiutato
per un motivo che non dipende dalla correzione: se capita, il dato si sistema a mano.~~ ⚠️ Era il
sintomo di un difetto del `-72`, non un dato da sistemare: §9.8.6.

**pgTAP**: nuovo `catalogo/test-articolo-correzione-righe-aperte-v1.sql` (9 test, tutto costruito):
- il rifiuto in un preventivo in bozza, e la correzione annullata;
- due righe in due documenti (ordine e preventivo), contate nel messaggio;
- la natura che passa (congelata);
- un preventivo **annullato** e una riga **spenta** che non bloccano;
- una correzione di due colonne senza righe vive;
- il presidio sui montaggi del guard di riga (le sette tabelle tutte lette dal verbo).

**Prova pre-apply** (2026-10-18, `zeroerp_ruoli`, da owner, SQL estratto del `-72` + le righe del
codice dopo il `BEGIN;` del pgTAP, `PGTZ=Pacific/Kiritimati`). ⚠️ **Sbagliata in due punti, rettificata
nel §9.8.6**: il filtro dell'output non vedeva un file fermato a metà, e sullo scratch vuoto il test
prontezza non poteva cadere.

* test nuovo **9/9**; senza il `-72` rossi l'1, il 2, il 3 e l'8;
* i quattro pgTAP che passano dalla porta per provare il valle
  (`test-fn-genera-ddt-riconsegna-eredita-v1`, `test-righe-articolo-ammesso-v1`,
  `test-righe-erogazione-da-articolo-v1`, `test-righe-natura-vendita-congelata-v1`): stesso esito,
  tutte le asserzioni eseguite, zero skip. Passano per la ragione giusta: correggono la natura
  (congelata), o un articolo le cui righe sono spente o in una bolla `CONSEGNATO`;
* `test-articolo-usato-struttura-v1`, `test-articolo-colonne-struttura-v1`,
  `test-articoli-a-magazzino-prontezza-v1`: stesso esito (il 17 del primo è rosso da owner per
  costruzione);
* presidi sui codici e trasversali (identità, `obsoleto_dal`, motivo nominato, valore atteso, check
  sotto JIT, catalogo messaggi, vincolo del codice, rubinetto, canale campo, riferimenti morti,
  costanti citate): stesso esito senza e con, tutti verdi;
* `plpgsql_check` sul verbo: pulito;
* test Django `test_articoli_ammessi_db.py`: provano permesso e forma dei campi, non li tocca.

⚠️ **Un errore mio durante la prova, corretto.** Il `plpgsql_check` l'ho lanciato con una
transazione composta a mano (`echo BEGIN` senza `;`): il corpo e il COMMENT del `-72` sono finiti
**davvero** sullo scratch `zeroerp_ruoli`, fuori da Liquibase. Visto dal presidio «senza», che
trovava già il codice nuovo. **Ripristinato** col SQL del `-71` (quello che il `databasechangelog`
dichiara applicato), riletto `prosrc`, rifatti i confronti contaminati (sono quelli scritti qui
sopra). dbdev non è stato toccato.

**Dopo l'apply (Tid)**: `catalogo/test-articolo-correzione-righe-aperte-v1`, i tre del catalogo qui
sopra, i quattro di `vendite` che passano dalla porta, `test-catalogo-messaggi-errore-completo`.

**Doc**: `catalogo/manual/fn_articolo_correggi_struttura` (§ Le righe dei documenti aperti). Nessuna
guida descrive la correzione di struttura.

**Richiesta BE/FE** (nel giro 5d): policy e ripiego per `E_ARTICOLO_STRUTTURA_RIGHE_APERTE`
(CONFLITTO_STATO, nessun campo); a video, il rifiuto della «Correggi struttura» col messaggio. Se
serve mostrare **quali** documenti, sono in `dettaglio.righe`.

#### 9.8.5 Il riassorbimento dei blocchi della distinta (Lotto 3u): valutato, non si fa

La 3u lasciava «da valutare» se la regola «articolo usato» dovesse assorbire
`trgfn_articoli_guard_flags_struttura_bom_attiva` e le sue regole nel form. **No**: sono due regole
con due predicati diversi. `catalogo.fn_articolo_usato` esclude per costruzione la distinta (è
anagrafica dell'articolo, non un suo uso), mentre il guard della distinta ferma i flag di un
articolo che sta in una distinta **in vigore o futura**, anche se non è mai stato venduto. Un
articolo può essere nell'una e non nell'altra, quindi nessuna delle due contiene l'altra. Valutato
il 2026-10-18 (punto 2, ok di Tid).

#### 9.8.6 Dopo l'apply del `-72`: due rossi, un difetto del `-72` e una prova mia sbagliata (2026-10-18)

**La corsa di Tid** (dopo l'apply di `-70`, `-71`, `-72` e dei CSV) ha trovato due rossi:

| pgTAP                                                     | Rosso                    | Causa                                                                                                                                                                                                                                        |
| --------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `catalogo/test-articolo-colonne-struttura-v1`             | dal test 6, file fermato | la fixture correggeva «solo componente» su un articolo in un preventivo in bozza: è proprio il caso che il `-72` rifiuta. Il file prova la sede delle colonne, non le righe vive                                                             |
| `dbops/test-articoli-a-magazzino-prontezza-v1` (su dbdev) | dal test 2, file fermato | spegne `gestito_a_magazzino` su **tutti** gli articoli dalla porta; l'articolo «composito» ha tre righe vive **già** non ammesse (`E_RIGA_ECCEZIONE_FUORI_LISTINO`: offerte 84, 85, contratto 103), e il `-72` le attribuiva alla correzione |

**Il difetto del `-72`.** Rifiutava per ogni riga viva non ammessa **dopo** la correzione, anche per
una che non lo era già **prima**. Il modello quelle righe le ammette, e non solo per i dati vecchi:
il guard di riga è `UPDATE OF articolo_id`, quindi non rigiudica una riga riaccesa, un'OVERRIDE il cui
articolo esce dalla versione operativa del listino, un'AGGIUNTA il cui articolo poi ci entra. La
decisione A-11 dice «rifiuta se la correzione **renderebbe** non valide»: va confrontato il prima col
dopo. (Il «fatto datato» del §9.8.4 era già il sintomo, e l'avevo letto come un dato da sistemare a
mano.)

**La prova mia sbagliata.** Nel §9.8.4 avevo scritto «stesso esito, tutti verdi». Era falso, per due
ragioni:

* filtravo l'output con `grep '^ERRORE'`, ma psql scrive `psql:file:riga: ERRORE`: un file che si
  fermava a metà non dava nessun `not ok` e sembrava verde (verde per sottrazione);
* il test prontezza sullo scratch vuoto non poteva cadere: le righe che lo fanno cadere stanno solo su
  dbdev.

Da qui in avanti ogni prova conta le asserzioni eseguite contro il piano.

| ChangeSet     | Cosa                                                                                                                                                                                                                                                                                         |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20261018-73` | nuova `catalogo.fn_articolo_righe_vive_non_ammesse(articolo)` → `{documento, documento_id, riga_id, motivo}`: l'elenco del `-72` portato fuori dal verbo, stesso perimetro, perché ora serve due volte. plpgsql, STABLE, INVOKER                                                             |
| `20261018-74` | `catalogo.fn_articolo_correggi_struttura` (corpo dal `-72`): raccoglie le righe non ammesse **prima** dell'UPDATE (dopo il lock dell'articolo) e rifiuta solo quelle che compaiono **dopo**. Chiave: documento + riga. Stesso codice, valori, dettaglio. Rollback: corpo e COMMENT del `-72` |

**pgTAP**:

* `catalogo/test-articolo-correzione-righe-aperte-v1` (plan 9 → 10): nuovo test 10, una riga viva
  **già** non ammessa (riaccesa dopo una correzione) non blocca una correzione successiva. Il
  presidio 8 legge la funzione nuova al posto del verbo;
* `catalogo/test-articolo-colonne-struttura-v1`: nella fixture la riga di U si spegne (U resta usato).

**Prova** (2026-10-18; questa volta su **dbdev** come owner, con i dati veri, e su `zeroerp_ruoli`;
SQL estratto di `-73`/`-74` solo dopo la riga `BEGIN;` del file; contate le asserzioni eseguite
contro il piano; `md5(prosrc)` del verbo uguale prima e dopo su tutti e due i database):

| pgTAP                                                                 | senza                                         | con       |
| --------------------------------------------------------------------- | --------------------------------------------- | --------- |
| `test-articolo-correzione-righe-aperte-v1`                            | 7/10, fermato all'8 (la funzione non c'è)     | **10/10** |
| `test-articoli-a-magazzino-prontezza-v1` (dbdev)                      | 1/6, fermato                                  | **6/6**   |
| `test-articolo-colonne-struttura-v1` (fixture corretta)               | 12/12                                         | 12/12     |
| `test-articolo-usato-struttura-v1`                                    | 16/17 (il 17, rosso da owner per costruzione) | 16/17     |
| i quattro di `vendite` che passano dalla porta                        | 18, 18, 22, 15 su piano                       | uguali    |
| `test-riferimenti-morti-v1`, `test-catalogo-messaggi-errore-completo` | 9/9, 7/7                                      | 9/9, 7/7  |

* ⭐ **Mutazione**: con la sola funzione `-73` e il verbo del `-72`, il test 10 è rosso. Il test vede
  il difetto;
* `plpgsql_check` su tutte e due le funzioni: pulito;
* guardrail statici e licenze: verdi.

**Dopo l'apply (Tid)**: i pgTAP della tabella sopra. ✅ **Esito (Tid, 2026-10-18)**: `-73`, `-74` applicati, pgTAP verdi.

**Doc**: nuovo `catalogo/manual/fn_articolo_righe_vive_non_ammesse`; `catalogo/manual/fn_articolo_correggi_struttura`
(prima e dopo).

#### 9.8.7 Il giro BE/FE 5d (sessione BE, `dev/backend-tid`, 2026-10-18)

| Che cosa                                                                                                                                                                                                                                                    | Dove                                                               |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Il dettaglio dell'articolo porta `struttura_correggibile` = `catalogo.fn_articolo_colonne_struttura()` (R-DB-3)                                                                                                                                             | `CatalogoRepository.colonne_struttura_articolo`, `fn_get_articolo` |
| La scheda articolo riapre in correzione **quelle** colonne; `COLONNE_STRUTTURA` ritirata                                                                                                                                                                    | `ArticoloDrawer.vue`                                               |
| **R-BE-1**: la correzione viaggia nel PATCH (`correzione_struttura: {colonna: valore}`, le sole cambiate); il service chiama il verbo e poi l'UPDATE dentro **un** `transaction.atomic()`; `correzione_struttura` da sola basta. Il FE fa una chiamata sola | `fn_update_articolo`, `ArticoloDrawer.handleSave`                  |
| Ritirati `POST …/articoli/<id>/struttura/` (`ApiArticoloStruttura`, `fn_correggi_struttura_articolo`, `correggiStrutturaArticolo` e l'azione dello store): nessun altro consumatore                                                                         | `catalogo/api`, store `articoli`                                   |
| Policy e ripiego di `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` (CONFLITTO_STATO, 409), con la rigenerazione del 2026-10-18 dopo la verifica che il codice fosse a catalogo in git                                                                                  | `error_policies_generated.py`, `error_messages_fallback.py`        |
| Doc API: §1.6-bis riscritto (la correzione nel PATCH)                                                                                                                                                                                                       | `backend/catalogo/manual/api_catalogo.md`                          |

**Il permesso.** Il PATCH resta `DomainAPIView` (area catalogo): il SUPER_ADMIN della correzione lo
giudica il verbo (`E_PERMESSO_NEGATO`), che era già la regola; prima lo ripeteva anche `AdminAPIView`.
Un operatore del catalogo che mandasse `correzione_struttura` riceve il rifiuto del verbo, e
l'aggiornamento non parte (stessa transazione).

**A video**, il rifiuto `E_ARTICOLO_STRUTTURA_RIGHE_APERTE` arriva col messaggio del DB (righe e
documenti contati) nel banner degli errori; l'elenco dei documenti (`dettaglio.righe`) per ora non si
mostra: se al collaudo serve, è un'aggiunta del solo FE.

**Prove:** su DB vero (`ZEROERP_TEST_DB_E2E=1`), `catalogo/tests/db/test_articoli_ammessi_db` 8 (un
PATCH con correzione e un'aliquota inesistente: la FK rifiuta dopo il verbo, e la struttura resta
quella di prima; un PATCH buono scrive tutte e due) — provato per mutazione (tolta la transazione dal
service → rosso) — e 9 (`struttura_correggibile` uguale alla sede); unitari di view e service; FE
`ArticoloDrawer.spec.js` (3: riapre le sole colonne del dettaglio, un PATCH solo con la correzione,
nessuna correzione senza l'azione).

