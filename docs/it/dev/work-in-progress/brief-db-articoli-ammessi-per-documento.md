# Brief DB — Quali articoli ammette un documento: una regola sola, per il picker e per il guard

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-11. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§7), che **attende** la consegna DB.
> **Origine:** collaudo a video di Tid, 2026-10-11 («come capisco quali articoli sono una
> tantum?»), poi la sua richiesta: *«la ricerca dell'articolo mostri solo gli articoli che quel
> documento può usare»*. Il caso che l'ha aperto è nel §H di
> [brief-db-offerta-emissione-ed-erogazione](brief-db-offerta-emissione-ed-erogazione.md): un
> articolo scelto dal picker, rifiutato dopo.
> **Stato (2026-10-11):** ⏳ da analizzare (team DB), poi le decisioni di Tid (§5).

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

| Documento (righe) | Che cosa rifiuta il DB sull'articolo | Che cosa filtra il picker | Scarto |
| --- | --- | --- | --- |
| **Preventivo** (`preventivi_righe`) | natura con destinazione CONTRATTO (`E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA`, predicato **dentro** `trgfn_preventivi_righe_set_natura_vendita`); composito con BoM vuota (`E_DOC_COMPOSITO_BOM_VUOTA`, all'init dei componenti) | `escludiDestinazione: ['CONTRATTO']`, `soloComponenti: 'escludi'` (`PreventiviRigaForm.vue`) | natura allineata; «solo componente» lo rifiuta solo il FE |
| **Offerta** (`offerte_commerciali_eccezioni`) | tipologia fuori utility (`E_RIGA_TIPOLOGIA_FUORI_UTILITY`); nessuna erogazione ammessa (`E_RIGA_EROGAZIONE_OBBLIGATORIA`); AGGIUNTA di un articolo già in listino (`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`); ESCLUSIONE di un figlio di bundle; BoM vuota | `soloComponenti: 'escludi'` (`RigheEccezioniDrawer.vue`) | 🔴 il picker propone articoli fuori utility e già in listino: il motivo compare **dopo** la scelta |
| **Contratto** (`contratti_righe`) | come l'offerta | stesso drawer | 🔴 come l'offerta |
| **Ordine di vendita** (`ordini_righe`) | **nessuna regola sulla natura**; BoM vuota | `soloComponenti: 'escludi'` (`OrdiniRigaForm.vue`) | 🔴 **manca la regola**: si possono mettere servizi una tantum e ricorrenti in un ordine |
| **Bolla** (`ddt_righe`) | **nessuna regola sulla natura**; il magazzino lo giudica `fn_check_riga_magazzino` all'emissione | `soloComponenti: 'escludi'` (`DdtRigaForm.vue`) | 🔴 come l'ordine |
| **Versione di listino** (`listini_righe`) | tipologia mancante o diversa da quella del listino (`E_ARTICOLO_TIPOLOGIA_MANCANTE` / `_INCOMPATIBILE`); composito in INSERT (`E_LISTINO_RIGA_COMPOSITO_VIETATO`) | `soloComponenti: 'escludi'` (`VersioneDrawer.vue`) | 🔴 il picker propone articoli di qualunque tipologia |
| **Distinta** (`catalogo.articoli_componenti`) | IVA del componente diversa da quella del padre (`E_BOM_IVA_DISCORDANTE`); componente uguale al padre (CHECK) | `compositi: 'escludi'` (`ArticoloBomDrawer.vue`) | 🔴 il picker propone componenti con IVA diversa; il composito come componente lo rifiuta solo il FE |
| **Promo** (`promo_articoli`) | nessuna regola sull'articolo | `soloComponenti: 'escludi'` | regola solo FE |
| **Oneri di commessa** | articolo senza causale onere (`E_ONERE_ARTICOLO_MANCANTE`) | `solo_oneri` | ✅ allineato |
| **Inventari / rettifiche** | gestito a magazzino, lotto, seriale: `fn_check_riga_magazzino` al piano, non al salvataggio | `gestitiAMagazzino: 'solo'` | ✅ allineato al posting |
| Resi, fatture | l'articolo arriva dalla riga d'origine | nessun picker | — |
| Acquisti (`ordini_righe`, `ddt_righe`) | solo articolo attivo | FE non ancora fatto | da decidere ora, non dopo (§5, D-5) |

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

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | Ordine di vendita: quali nature? | solo **MERCE** (destinazione ORDINE), come dice il modello dello smistamento. Il ramo da preventivo porta già solo merce |
| **D-2** | Bolla: quali nature? | come l'ordine. Da decidere se un servizio «da consegnare con la merce» (trasporto, montaggio) debba stare in bolla: se sì, va scritto come natura o come flag, non tollerato |
| **D-3** | «Solo componente» su una riga di documento | rifiutato da **ogni** riga autonoma (`E_ARTICOLO_SOLO_COMPONENTE`, il codice c'è già); ammesso solo come componente |
| **D-4** | Componente composito in distinta (BoM annidata) | da decidere: oggi il DB lo accetta e il FE lo nasconde. Se no, guard sulla BoM; se sì, il picker smette di nasconderlo |
| **D-5** | Acquisti | la stessa sede vale anche per loro, da subito (`modo_approvvigionamento`: un articolo prodotto internamente si compra?). Il FE acquisti ancora non c'è: è il momento di non scrivere una terza copia |
| **D-6** | Promo | regola nel DB (le stesse esclusioni del listino?) oppure nessuna regola, e allora il picker non filtra |

## 6. Richiesta

| # | Cosa | Dettaglio |
| --- | --- | --- |
| **R-1** | **Una `fn_check_*` per ogni regola sull'articolo** | estrarre dai trigger i predicati di D-C (natura per destinazione, tipologia del listino, IVA della BoM, composito in listino), più quelle nuove di D-1…D-4. Ogni check restituisce i motivi (codice + campo), come `fn_check_riga_erogazione`. **I guard le chiamano**: il guard rifiuta col primo motivo |
| **R-2** | **La sede unica: «articoli ammessi dal documento»** | una funzione di lettura (nome a scelta del team DB, per esempio `catalogo.fn_articoli_ammessi(p_documento, p_contesto jsonb, p_search, p_limit)`) che, dato il tipo di documento e i valori del form (utility, listino o versione, padre della distinta, magazzino, tipo eccezione), restituisce gli articoli che **le stesse check** di R-1 ammettono. Sul modello di `fn_listini_selezionabili`: valori del form, non l'id del documento, così funziona anche in creazione. Vocabolario dei documenti dichiarato (CHECK o tabella), non stringhe nude |
| **R-3** | Riuso dei BB esistenti | `script.fn_check_riga_erogazione` (tipologia nella utility), `vendite.fn_articolo_erogazioni` (zero combinazioni = non ammesso), `vendite.fn_documento_listino_operativo` (AGGIUNTA già in listino), `script.fn_check_esclusione_articolo_documento`, `script.fn_check_riga_magazzino`. Nessuna seconda copia |
| **R-4** | **Il motivo di un articolo escluso** | da valutare: oltre a «chi è ammesso», poter chiedere «perché questo no» (l'operatore cerca un codice preciso e non lo trova). Proposta: la stessa funzione, con un parametro che restituisce anche gli esclusi con il loro motivo, oppure una lettura per singolo articolo |
| **R-5** | Prestazioni | la lettura gira a ogni tasto premuto nel picker: EXPLAIN sul DB vero, con le check valutate solo sugli articoli che passano la ricerca testuale (il tetto del lookup resta di 50) |
| **R-6** | Le righe già scritte | i guard nuovi (D-1…D-4) scattano all'INSERT e quando cambia l'articolo. Le righe esistenti si intercettano al primo passo che le usa (emissione, smistamento, trasformazione), con il motivo, come nel §H del brief offerta |
| **R-7** | pgTAP | per ogni documento: l'articolo ammesso compare e si scrive; l'articolo escluso non compare **e** il guard lo rifiuta con lo stesso codice (picker e guard non possono dissentire); creazione senza id del documento |
| **R-8** | Doc | manual delle funzioni nuove; guide di preventivi, offerte, ordini e bolle («quali articoli si possono mettere»); `linee-guida-sql` se nasce una regola generale («ogni picker di riga legge la sede unica») |

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
