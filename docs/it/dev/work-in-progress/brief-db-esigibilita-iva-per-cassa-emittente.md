# Brief DB — Esigibilità IVA: il regime dell'emittente (IVA per cassa) non entra nella decisione

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`); Tid
> per le decisioni di §6.
> **Origine:** controllo dell'esigibilità sulle fatture del cliente Titini Michele Carlo (2026-10-01):
> lì «Immediata» è **corretta** (privato con codice fiscale, fuori dalla scissione). Il controllo ha
> però mostrato che la decisione guarda **solo il cliente** e mai l'emittente.
> **Stato:** ✅ **D-1 → D-6 decise da Tid il 2026-10-01** (§6). Nessun changeSet scritto: il lavoro
> passa al team DB. Non urgente.
>
> **In una riga:** un emittente in regime di **IVA per cassa** (art. 32-bis, codice RF17) deve
> emettere fatture con esigibilità **D** (differita); il sistema oggi scrive **I** (immediata) e non
> lo sa, senza nessun errore.

---

## 1. Il problema

L'esigibilità IVA di una riga di fattura (`I` immediata, `D` differita, `S` scissione dei pagamenti)
oggi la decide il trigger `vendite.trgfn_fatture_righe_guard_normalize`, guardando **il cliente**:

* cliente in scissione (`soggetti.split_payment = 'S'`) → `S`, imposta;
* altrimenti → `I`, ma **solo se la riga è vuota**: una `D` scritta da qualcuno sopravvive.

Il **regime fiscale dell'emittente** esiste nel modello (`anagrafiche.emittenti_fiscali.regime_fiscale_rf`,
il codice RF del tracciato FatturaPA), finisce nello snapshot dell'intestazione
(`fn_snapshot_intestazione_fattura`), ma **nessuna regola lo legge per l'esigibilità**.

⇒ Un emittente in IVA per cassa emetterebbe **tutte** le sue fatture con `I`. A meno di una
correzione a mano riga per riga, che nessuna schermata offre, il documento fiscale dichiara un
regime sbagliato. È un difetto **del modello**: non dipende da quali emittenti ci sono oggi.

## 2. Cosa c'è oggi — letto dalla struttura (2026-10-01)

| Oggetto | Cosa dice |
| --- | --- |
| `emittenti_fiscali.regime_fiscale_rf` | `varchar`, **nullable**, nessun `CHECK`, nessuna tabella di vocabolario: un testo libero |
| `vendite.trgfn_fatture_righe_guard_normalize` | `split_payment` dal cliente (riscritto sempre); `esigibilita` = `S` con la scissione, altrimenti `I` sul vuoto |
| `vendite.fn_resolve_iva_riga_it` (risolutore, anteprima del form riga) | ricalcola **la stessa coppia** dal soggetto cliente, con la sua copia della regola (`v_esigibilita := CASE …`) |
| `vendite.fatture_riepiloghi_iva` | raggruppa per `(iva, natura, esigibilita, split)`; unique con `COALESCE(esigibilita, 'I')` |
| `vendite.preventivi_riepiloghi_iva` | ha la colonna, ma `fn_ricalcola_riepilogo_iva_preventivo` la scrive sempre `NULL` |
| `anagrafiche.soggetti` | `split_payment`, `partita_iva`, `id_fiscale_univoco_cf_piva`, `tipo_soggetto_dettaglio_id` |

⚠️ **La regola sta in due sedi**: il trigger e il risolutore la ricalcolano ognuno per conto suo. Oggi
coincidono, ma la modifica di §4 va fatta in **una** sede letta da tutti e due (regola del 2), o
l'anteprima del form e la riga salvata diranno due cose diverse.

Fatto datato, non motivo: al 2026-10-01 i due emittenti di dbdev hanno `regime_fiscale_rf` vuoto,
quindi nessun documento esistente è sbagliato. Il difetto resta: il modello ammette RF17 e non lo
gestisce.

## 3. La regola fiscale (da far confermare al consulente)

> ⚠️ Riassunto di chi scrive, **non** un parere fiscale: va verificato prima del changeSet.

* **Art. 32-bis DL 83/2012**: chi opta per l'IVA per cassa versa l'imposta all'**incasso** (comunque
  entro un anno dall'operazione). In fattura elettronica: `RegimeFiscale = RF17` ed
  `EsigibilitaIVA = D`.
* **Esclusioni** — l'operazione resta a esigibilità ordinaria anche per un emittente in cassa:
  * verso un cliente che **non agisce nell'esercizio d'impresa, arte o professione** (il privato:
    il caso di Titini Michele resterebbe `I` anche con un emittente in cassa);
  * operazioni in **inversione contabile** (reverse charge, nature `N6.x`);
  * operazioni in **scissione dei pagamenti** (`S` prevale);
  * operazioni dei regimi speciali.
* **Annotazione obbligatoria** in fattura: «operazione con IVA per cassa ai sensi dell'art. 32-bis
  del DL 83/2012».

⇒ La decisione dipende da **tre** cose, non da una: regime dell'emittente, natura del cliente
(privato o soggetto IVA), natura della riga (reverse charge). La seconda e la terza rendono
l'esigibilità **per riga** e non per documento, ed è compatibile col raggruppamento dei riepiloghi.

## 4. Proposta (team DB)

1. **Il vocabolario del regime**: `regime_fiscale_rf` da testo libero a codice di un catalogo
   (`config.regimi_fiscali`, RF01…RF19 del tracciato, CSV in `80_data`) con FK. Una regola che decide
   su `= 'RF17'` non può appoggiarsi a un testo che accetta `'rf17 '`.
   **D-1**: la colonna prende il **default RF01** (ordinario), e gli emittenti esistenti col regime
   vuoto passano a RF01 nello stesso giro; un presidio elenca gli emittenti a RF01 **non confermati**
   da una persona, perché un default resta una forma che nessuno ha dichiarato.
2. **Una sede per la regola**: una funzione (`vendite.fn_esigibilita_riga(...)` o simile) che riceve
   il regime dell'emittente, il cliente e la natura della riga e risponde `S` / `D` / `I` / `NULL`
   («non determinato»). La chiamano il trigger e il risolutore. Ordine:
   1. cliente non risolto → `NULL` (com'è oggi);
   2. scissione → `S`;
   3. emittente RF17, cliente soggetto IVA, riga non in reverse charge → `D`;
   4. altrimenti → `I`, sul vuoto (la `D` scelta a mano sopravvive, come oggi).
3. **Il cliente soggetto IVA** (D-2): si legge dalla `partita_iva` del soggetto cliente
   valorizzata, come regola scritta nella funzione del punto 2.
4. **L'annotazione in fattura**: un riferimento normativo legato al regime, letto dal contesto di
   stampa (il BE lo porta nel contesto e la versione del template lo stampa). Va con la forma dei
   dati: **nuova forma** del builder fattura e nuova versione del template, secondo il patto di
   `brief-db-documenti-versione-contesto-template`.
5. **Preventivi, ordini e DDT** (D-4, D-6): i loro riepiloghi IVA calcolano esigibilità e scissione con la
   **stessa** funzione del punto 2, al posto dei `NULL` di oggi (`fn_ricalcola_riepilogo_iva_preventivo`
   scrive sempre `NULL`; `vw_ordini_riepilogo_iva_dettaglio` proietta `NULL::character(1)` e
   `NULL::boolean`). Il raggruppamento segue quello della fattura, `(iva, natura, esigibilita, split)`.
   Il DDT si allinea nello stesso giro (D-6): `vw_ddt_riepilogo_iva_dettaglio` ha la stessa forma
   della vista degli ordini.
6. **pgTAP** costruendo i casi: emittente RF17 × (soggetto IVA, privato, PA in scissione) × (riga
   ordinaria, riga N6), più emittente ordinario e regime vuoto. Nessun confronto con la popolazione.

## 5. Ricadute fuori dal DB (da chiedere a BE/FE quando il DB è fatto)

* **BE**: il contesto di stampa fattura porta l'annotazione del regime (forma nuova); il payload SDI
  (sospeso per decisione, PROJECT_CONTEXT) dovrà leggere `EsigibilitaIVA` dalle righe, già giuste.
* **FE**: il campo del regime fiscale nel form emittente diventa una scelta dal catalogo; il
  riepilogo IVA del drawer fattura mostra già la `D` (decodifica esistente).
* **Preventivi, ordini e DDT** (D-4, D-6): il riepilogo IVA del drawer mostra l'esigibilità anche
  lì — `RiepilogoIvaTable` ha già `show-esigibilita`, da accendere sui tre drawer; l'annotazione in
  stampa, se si vuole anche sui loro PDF, è una forma nuova dei loro builder.

## 6. Decisioni per Tid

✅ **Tutte decise da Tid il 2026-10-01.**

| # | Domanda | Esito |
| --- | --- | --- |
| D-1 | `regime_fiscale_rf` **vuoto**: come si tratta? | ✅ **Ordinario, con un default RF01** sulla colonna; gli esistenti vuoti passano a RF01. Il presidio sugli emittenti a RF01 non confermati resta (§4.1) |
| D-2 | «Il cliente è un soggetto IVA»: da dove si legge? | ✅ Dalla **`partita_iva`** del soggetto cliente |
| D-3 | L'annotazione art. 32-bis in fattura | ✅ **Sì**, nello stesso giro: forma nuova del contesto fattura + versione nuova del template |
| D-4 | I preventivi | ✅ **Si allineano, e con loro gli ordini**: riepilogo IVA con esigibilità e scissione dalla stessa funzione (§4.5) |
| D-5 | Le fatture già emesse | ✅ **Nessun riallineamento**: su dbdev sono fatture di test |
| D-6 | Il **DDT** | ✅ **Sì, insieme** agli ordini: il suo riepilogo ha la stessa forma (`NULL` fissi in `vw_ddt_riepilogo_iva_dettaglio`), e lasciarlo fuori sarebbe un'asimmetria fra documenti fratelli |

## 7. Fuori perimetro, dichiarato

* La **liquidazione** all'incasso (quando l'IVA diventa dovuta, la scadenza di un anno): è
  contabilità, e lo schema `contabilita` è fuori perimetro per decisione.
* Gli altri regimi speciali (forfettario RF19 e simili): stesso catalogo di §4.1, regole proprie da
  decidere a parte.
