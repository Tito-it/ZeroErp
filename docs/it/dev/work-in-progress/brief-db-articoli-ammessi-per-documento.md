# Brief DB — Quali articoli ammette un documento: una regola sola, per il picker e per il guard

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: team DB** col Lotto 3 (§9). Lotti 1 e 2, con la correzione `20261013-14`, sono applicati, verdi e committati. Il BE/FE parte **alla fine**, a lotti DB chiusi, con tutte le richieste insieme (Tid, 2026-10-13: non c'è produzione).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ decisioni prese: A-1…A-9 (2026-10-12), D-1…D-4 e D-6 (2026-10-13); D-5 rinviato | §8.6 | — |
| 2 | BE | ✅ P-1 risposta (2026-10-13): la testata nasce sempre prima | §8.6, P-1 | — |
| 3 | Tid | ✅ Lotto 1 applicato, pgTAP verdi (2026-10-13) | §9.1 | — |
| 4 | Tid | ✅ Lotto 2 applicato (`20261013-07 → -13`, 2026-10-13); baseline di `vendite`: 8 regressioni, analizzate | §9.2, §9.2.1 | — |
| 4a | Tid | ✅ `20261013-14` applicato, pgTAP verdi, nessuna regressione (2026-10-13) | §9.2.1 | — |
| 4b | DB | Lotti 3-5 | §9 | — |
| 5 | BE/FE | **tutto in un giro, alla fine**: policy dei codici nuovi di ogni lotto, lookup e `ArticoloLookup` sulla sede unica, ritiro dei filtri liberi | §7, §9.6 | Lotto 5 |
| 6 | Tid | collaudo a video | — | 5 |

Decisioni aperte di Tid: nessuna (D-5 rinviato al cantiere acquisti). Lavoro da committare: nessuno di questo brief. ✅ Committati il 2026-10-13 (team DB): Lotto 1, Lotto 2 con le cinque chiavi dei locales, `20261013-14`, i pgTAP del §9.2.1 **di questo brief** (smistamento, push dei preventivi v1/v2, registri per emittente) e questo documento. ⚠️ Restano fuori, col lavoro che ne porta la causa: i quattro file SORGENTE_POLIMORFA del §9.2.1 (`-46` di brief-db-annullo-a-valle-riapre-a-monte), che contengono anche le modifiche del ritiro di `tipo_consumo` (`-16 … -23`).

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-11. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§7), che **attende** la consegna DB.
> **Origine:** collaudo a video di Tid, 2026-10-11 («come capisco quali articoli sono una
> tantum?»), poi la sua richiesta: *«la ricerca dell'articolo mostri solo gli articoli che quel
> documento può usare»*. Il caso che l'ha aperto è nel §H di
> [brief-db-offerta-emissione-ed-erogazione](brief-db-offerta-emissione-ed-erogazione.md): un
> articolo scelto dal picker, rifiutato dopo.
> **Stato (2026-10-13):** analisi del team DB fatta (§8); decisioni di Tid prese (§8.6); consegna a lotti (§9): ✅ Lotti 1 e 2 applicati, verdi e committati (con `20261013-14`); ⏳ Lotto 3.

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

| Famiglia | Dipende da | Esempio | Chi la usa |
| --- | --- | --- | --- |
| **motivi di articolo** | solo l'articolo e il contesto del documento | `TIPOLOGIA_FUORI_UTILITY`, natura, solo componente, IVA della BoM | picker **e** guard |
| **motivi di riga** | anche gli altri campi della riga | `EROGAZIONE_FUORI_PERIMETRO` (combinazione erogazione/fonte) | solo guard |

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

| # | Domanda | Proposta del team DB |
| --- | --- | --- |
| **A-1** | Le righe ricevono l'id del documento (testata salvata), non i valori del form | ✅ **Tid, 2026-10-12: sì**, l'id del documento. Resta P-1 al BE per il solo caso testata + righe in una chiamata |
| **A-2** | Una check componente per tipo di riga, un guard per tabella | ✅ **Tid, 2026-10-12: sì** (§8.3, punto 2): un predicato per regola, una check per tipo di riga con l'ordine dei motivi scritto, chiamata dal guard e dal picker |
| **A-3** | Per ogni regola nuova: guard dal lato articolo, o controllo ai passi successivi | ✅ **Tid, 2026-10-12: misto.** «Solo componente» e «composito»: guard dal lato articolo (il flag non cambia se l'articolo è in righe di documenti aperti, come `trgfn_articoli_guard_flags_struttura_bom_attiva`). Natura: segue A-4. Tipologia (perimetro): ricontrollo ai passi, già deciso nel §H |
| **A-4** | Ordine e bolla congelano la natura in riga, come il preventivo? | ✅ **Tid, 2026-10-12: sì.** `natura_vendita_id` su `ordini_righe` e `ddt_righe`, scritta dal DB come sul preventivo; i verbi di copia (preventivo → ordine, ordine → bolla, riconsegna) la portano avanti. Chiude anche la natura di A-3: il cambio in anagrafica non tocca le righe scritte |
| **A-5** | OVERRIDE ed ESCLUSIONE pretendono l'articolo nel listino operativo | ✅ **Tid, 2026-10-12: sì**, guard nuovo (buco confermato, §8.2): rifiuto se l'articolo non è nel listino operativo o se il documento non ha listino; all'INSERT e al cambio articolo; le righe già scritte le intercetta l'emissione, come il §H |
| **A-6** | La riconsegna (`fn_genera_ddt_riconsegna`) è esente dalle regole nuove | ✅ **Tid, 2026-10-12: sì**, restituisce ciò che è uscito. L'esenzione si aggancia al legame con la riga di reso d'origine, non a un flag; la natura viaggia dalla riga d'origine (A-4) |
| **A-7** | Una lettura sola con il motivo per riga (R-2 + R-4) | ✅ **Tid, 2026-10-12: sì** (§8.3, punto 7): ammessi e non ammessi con la colonna `motivo` (NULL = ammesso), ammessi prima; il motivo dalla stessa check del guard (A-2); la resa a video la sceglie il FE |
| **A-8** | Vocabolario dei documenti su `config.tipi_entita` | ✅ **Tid, 2026-10-12: sì.** Oggi (seed `80_data/sql/config/tipi_entita.csv`) 9 voci; mancano OFFERTA, bolla, versione di listino, distinta, promo, da aggiungere dal CSV. Le funzioni con `p_documento text` nudo (`fn_check_riga_erogazione`, `fn_check_esclusione_articolo_documento`, `fn_documento_listino_operativo`) ci passano nello stesso giro. ⚠️ In consegna: verificare che la distinta regga come entità (destinazione = scheda articolo) |
| **A-9** | Il trasporto su un ordine che si fattura alla conferma (nessuna commessa) | ✅ **Tid, 2026-10-12: brief a parte**, [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md). D-1 e D-2 vanno avanti. In **questo** brief resta un vincolo nuovo: un articolo-onere (`causale_onere_id` valorizzato) non può avere natura `MERCE` (oggi nasce col default `MERCE`, `e_cessione_beni = true`) |
| **D-1** | Ordine di vendita: quali nature | ✅ **Tid, 2026-10-13: solo MERCE**, da ogni sorgente. Il predicato «natura → ORDINE» si estrae e lo usano la vista `vw_preventivi_righe_smistabili_ordine` e il guard; natura congelata (A-4) |
| **D-2** | Bolla: quali nature | ✅ **Tid, 2026-10-13: solo MERCE**, stesso predicato di D-1. Dalla riga d'ordine la natura congelata viaggia (A-4); bolla a mano: dall'articolo alla scrittura; riconsegna esente (A-6). Servizi e addebiti passano dalla commessa |
| **D-3** | «Solo componente» su una riga | ✅ **Tid, 2026-10-13: rifiutato da ogni riga autonoma** (preventivo, offerta, contratto, ordine, bolla, riga di listino) con `E_ARTICOLO_SOLO_COMPONENTE` (messaggio già adatto); ammesso come componente. Prima il preventivo, e i verbi di copia controllano prima di scrivere (§8.3, punto 4); guard dal lato articolo (A-3); riconsegna esente (A-6) |
| **D-4** | Distinta annidata | ✅ **Tid, 2026-10-13: rifiuto**, guard su `articoli_componenti` (il componente non è composito) e dal lato articolo (un componente non diventa composito) (§8.4) |
| **D-5** | Acquisti | rinviato alla ripartenza del cantiere, con i riferimenti del §8.4 |
| **D-6** | Promo | ✅ **Tid, 2026-10-13: una promo si crea solo se il calcolo del prezzo la può applicare.** Solo componente: rifiutata (il resolver salta la promo in contesto bundle, «STADIO PROMO OVERLAY (non applicato in contesto bundle)» in `fn_resolve_prezzo_listino_v2_esito`, e con D-3 non c'è prezzo standalone). Composito: in consegna si verifica se il kit riceve la promo; se no, rifiutata, e la promo sul kit diventa una richiesta a parte |

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

| Lotto | Che cosa | Decisioni | Stato |
| --- | --- | --- | --- |
| **1** | **Catalogo**: la distinta a un livello (guard sul componente e dal lato articolo), l'articolo-onere non è merce | D-4, A-9 | ✅ applicato da Tid, pgTAP verdi, committato (2026-10-13) (§9.1) |
| **2** | **Vocabolario e natura in riga**: le voci mancanti in `config.tipi_entita`; `natura_vendita_id` su `ordini_righe` e `ddt_righe`, scritta dal DB e portata dai verbi di copia | A-8, A-4 | ✅ applicato da Tid con la correzione `-14`, pgTAP verdi, committato (2026-10-13) (§9.2, §9.2.1) |
| **3** | **Le regole sulle righe**: i predicati, la check per tipo di riga, un guard per tabella; natura su ordine e bolla, solo componente ovunque, OVERRIDE/ESCLUSIONE nel listino; i verbi di copia controllano prima di scrivere; «solo componente» dal lato articolo; la riconsegna esente. Le funzioni con `p_documento text` passano al vocabolario | A-2, A-3, A-5, A-6, D-1, D-2, D-3 | da scrivere; **insieme al §H** del brief offerta (§8.5) |
| **4** | **La sede unica di lettura**: candidati della ricerca con il motivo, ammessi prima; promo | A-1, A-7, D-6 | da scrivere |
| **5** | **Doc e richieste**: guide, manual, richieste BE/FE del §7 aggiornate | — | da scrivere |

### 9.1 Lotto 1 — catalogo (✅ applicato da Tid il 2026-10-13, pgTAP verdi)

**ChangeSet** (in ordine di apply; nessuno applicato):

| ChangeSet | Cosa |
| --- | --- |
| `20261013-01` | nuovo `catalogo.trgfn_articoli_componenti_guard_un_livello`: il componente di un legame attivo non è composito (`E_BOM_COMPONENTE_COMPOSITO`) |
| `20261013-02` | montaggio `trg_articoli_componenti_a10_guard_is_un_livello_ins_upd`, BEFORE INSERT OR UPDATE OF attivo. Il nome sta fra `guard_is_composito` (il padre) e `guard_iva_bom`: parla prima il padre, poi il livello, poi l'IVA |
| `20261013-03` | `catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva` + check 3: un componente di una distinta **in vigore o futura** non diventa composito (`E_BOM_COMPONENTE_DIVENTA_COMPOSITO`). Corpo base dalla doc auto-gen; il montaggio (UPDATE OF is_composito, …) copre già la colonna |
| `20261013-04` (`80_data`) | `dbops.lock_columns_conditional`: la regola gemella per il form, `is_composito` spento su un articolo **semplice** che è componente di una distinta in vigore o futura |
| `20261013-05` | nuovo `catalogo.trgfn_articoli_guard_onere_natura`: un articolo-onere non ha una natura con destinazione `ORDINE` (`E_ARTICOLO_ONERE_NATURA_MERCE`) |
| `20261013-06` | montaggio `trg_articoli_a10_guard_onere_natura_ins_upd`, BEFORE INSERT OR UPDATE OF natura_vendita_id, causale_onere_id |

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

| ChangeSet | Cosa |
| --- | --- |
| `20261013-07` (`00_schema`) | `natura_vendita_id` su `vendite.ordini_righe` e `vendite.ddt_righe`: FK verso `config.nature_vendita`, **NOT NULL**. Backfill dall'origine (ordine ← riga di preventivo; bolla ← riga d'ordine evasa, ← riga di bolla resa per le riconsegne, anche a catena), poi dall'articolo; coi trigger della tabella spenti per nome e riaccesi col loro modo |
| `20261013-08` | nuovo BB `script.trgfn_righe_natura_vendita`: la natura si scrive alla nascita (dall'articolo; in modo `CHIAMANTE` quella portata dal verbo) e al cambio di articolo, poi resta |
| `20261013-09` | montaggi `…_a10_natura_vendita_ins_upd` su preventivo (`ARTICOLO`), ordine e bolla (`CHIAMANTE`). L'ordine dei nomi è portante: lock di colonna → natura → guard della ricorrenza (e, nel Lotto 3, le regole sulle righe) |
| `20261013-10` | `vendite.trgfn_preventivi_righe_set_natura_vendita` non scrive più la natura: resta il guard della ricorrenza, che la legge |
| `20261013-11` | `fn_push_preventivo_a_ordine`: la riga d'ordine porta la natura della riga di preventivo |
| `20261013-12` | `fn_genera_ddt_da_ordine`: la riga di bolla porta la natura della riga d'ordine |
| `20261013-13` | `fn_genera_ddt_riconsegna`: la riga riconsegnata porta la natura della riga di bolla resa (A-6) |

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

| File | Esito | Causa | Correzione |
| --- | --- | --- | --- |
| `test-vw-preventivi-smistamento-v1` | ASSERZIONE (test 5) | **questo lotto**: il BB `-08` rimetteva la natura a `OLD` a parità di articolo e richiudeva in silenzio la porta del lock (vedi sotto) | `20261013-14` |
| `test-emissione-mirata-gruppi-fatturabili-v1`, `test-vw-dash-competenza-gruppi-v1`, `test-sorgente-origine-tipo-doc-fiscale-v1`, `test-trigger-af-commessa-aware-v1` | SORGENTE_POLIMORFA | `20261012-46` ([brief-db-annullo-a-valle-riapre-a-monte](brief-db-annullo-a-valle-riapre-a-monte.md), D-13): la madre aggancia il documento alla commessa con `fn_link_commessa_sorgente`, che ne pretende formato ed esistenza; le fixture passavano sorgenti inventate (`'c0000000-…'`, `'EXT-SOT-…'`, `'PGTAP-TCA-SRC-…'`) | fixture: preventivo o contratto **veri** (testata in bozza, stesso billing account, emittente del BA) |
| `test-fn-list-preventivi-da-pushare-v1`, `-v2` | ASSERZIONE (test 3-5) | dati: «l'articolo più recente» era, dal 2026-10-13 00:32, un composito MERCE lasciato da uno smoke; la riga andava all'ordine | fixture: articolo costruito (`dbops.fn_pgtap_crea_articolo`) con natura a destinazione COMMESSA |
| `test-registri-per-emittente-v1` | ASSERZIONE (test 6) | dati: dalla notte del 2026-10-12 l'emittente 159 ha template e documenti generati, e disattivandolo parla prima il guard di `documenti_generati` | fixture: emittente costruito (`fn_pgtap_crea_emittente` + `fn_pgtap_crea_cliente_ba` col terzo parametro), il cui unico figlio è il billing account; era lo scostamento dal piano dichiarato nel file |

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

**Esito** (Tid, 2026-10-13): `20261013-14` applicato, pgTAP verdi, nessuna regressione.

**Commit** (team DB, 2026-10-13): i quattro file SORGENTE_POLIMORFA della tabella sopra **non** sono nel
commit di questo brief: la causa è il `-46` di un altro brief, e gli stessi file portano anche il ritiro di
`tipo_consumo` (`-16 … -23`), che è un altro cantiere. Vanno committati con quel lavoro.

### 9.6 Il giro BE/FE finale (raccolta)

Il BE/FE parte quando i lotti DB sono chiusi (Tid, 2026-10-13). Qui si raccolgono le richieste lotto per
lotto, così il giro finale ha un elenco solo:

| Lotto | Richiesta |
| --- | --- |
| 1 | policy e ripiego per `E_BOM_COMPONENTE_COMPOSITO`, `E_BOM_COMPONENTE_DIVENTA_COMPOSITO`, `E_ARTICOLO_ONERE_NATURA_MERCE` |
| 2 | **BE**: policy e ripiego per `E_RIGA_NATURA_VENDITA_IMMUTABILE`; via `E_PREV_RIGA_NATURA_IMMUTABILE` (ritirato). **FE**: ✅ le cinque chiavi `config.tipi_entita.*` le ha già aggiunte la sessione DB (§9.2) |

