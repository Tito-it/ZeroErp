# Brief BE/FE — Il collaudo a video: le liste partono dall'ordinamento e dalla misura del preset

## ⏭️ Chi riparte — aggiornato al 2026-11-24

**Riparte: Tid**, col collaudo a video sui campioni di §2.2. La parte BE è uno smoke, scritto e verde (§2.1).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team BE/FE | ✅ Il copione (2026-11-24): la parte BE è lo smoke `smoke-test-ui-partenza-liste.sh`, la parte FE sono i campioni a video | §2 | — |
| 2 | Tid | Il collaudo a video, sui campioni | §2.2 | 1 |
| 3 | team BE/FE | Le correzioni che il collaudo trova, e la guida se il terzo clic la smentisce (§2.3); poi l'archiviazione in `work-done/` | §3 | 2 |

**Decisioni aperte di Tid:** nessuna. **Da committare:** questo brief, `backend/scripts/tests/smoke-test-ui-partenza-liste.sh`
e `backend/scripts/tests/_smoke_partenza_liste.py`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-23, alla chiusura di
> [brief-db-revisione-ui](../work-done/2026/brief-db-revisione-ui.md). **A chi:** team BE/FE e Tid.
> **Origine:** il residuo di quel brief, righe 8-ter e 9: il controllo a video di BE29 e del residuo di BE25 (2).
> Deciso da Tid il 2026-11-23: passa a un brief BE.
> **Brief vicini verificati:** [sviluppo-personalizzazioni-liste_def](sviluppo-personalizzazioni-liste_def.md) tiene
> funzionalità nuove delle liste (viste nominate, condivisione), non il collaudo di ciò che è fatto;
> [piano-be-fe-endpoint-senza-porta](piano-be-fe-endpoint-senza-porta.md) cita una lista di `ui` solo come fatto.
> Nessuno dei due copre questo collaudo.
> **Guide verificate:** [configurazione-liste](../../guide/configurazione-liste.md): coerente. Descrive la partenza della
> lista dal preset (ordinamento e misura), ed è ciò che il collaudo guarda. Al copione (2026-11-24): coerente, salvo
> forse il terzo clic di §6 («terzo toglie l'ordinamento»), che si decide a video (§2.3). Le altre guide che lo
> script trova (audit, DDT, pratiche, accessi, obsoleto, la nota del magazzino) nominano solo le liste dei campioni, e
> non descrivono la partenza di una lista: non toccate.

## 1. Che cosa si collauda

Il 2026-11-22 il team BE/FE ha portato la partenza delle liste configurabili al preset:

* **BE25 (2)**: quando la richiesta non porta `order_by`, il BE ordina con l'ordinamento della configurazione risolta
  dell'utente, e la risposta dice l'ordinamento applicato; il FE accende l'intestazione da lì;
* **BE10**: una lista configurabile chiamata senza `limit` prende la misura risolta dal DB (`ui.fn_misura_lista`);
* **BE29**: ritirate le copie FE dell'ordinamento di partenza (`orderBy` degli store, `defaultSortField` dei componenti)
  sulle liste a cui il seed dà il preset (U40), e con il residuo di BE25 (2) su altre 18 liste e 21 superfici di
  catalogo.

Il dettaglio, con l'elenco delle superfici, sta nelle voci BE10, BE25 (2) e BE29 di §6 del brief archiviato. Le prove
automatiche sono verdi (suite BE, vitest). Nessun test, però, apre le superfici a video: un'intestazione che non si
accende, o una lista che parte nell'ordine sbagliato, non fa fallire niente.

## 2. Il copione (team BE/FE, 2026-11-24)

⚠️ Il testo qui sotto, fino a §2.1, è la richiesta iniziale. Il copione la divide in due parti:
quello che dice il BE lo prova uno smoke, su **ogni** lista (§2.1); a video restano i
campioni di quello che solo il FE fa (§2.2). Deciso da Tid il 2026-11-24.

La richiesta iniziale: per ogni superficie toccata da BE29 e dal residuo di BE25 (2), aprirla senza preferenza salvata e vedere che

* le righe arrivano nell'ordine dell'`ordinamento_default` del preset;
* l'intestazione della colonna di partenza è accesa, col verso giusto;
* il numero di righe per pagina è la misura del preset, o il default `PAGINA` del catalogo;
* un clic sull'intestazione riordina, e alla riapertura la lista riparte dal preset (Q39 (b): il clic non si ricorda);
* sulle liste di BE30 (`magazzino.disponibilita`, `magazzino.disponibilita_articoli`, `magazzino.inventario_piano`,
  `vendite.resi_da_accreditare`, `vendite.resi_da_riconsegnare`) lo spareggio segue i criteri del repository.

### 2.1 La parte BE: lo smoke

`backend/scripts/tests/smoke-test-ui-partenza-liste.sh`, con il corpo in `_smoke_partenza_liste.py`. Fa il login di
`dev.smoke` (BB `smoke_login`). Poi prende **ogni** rotta GET che dichiara `lista_codice` (BB `rotte_servite`, gli
export esclusi) e la chiama come il FE alla prima apertura, senza `order_by` né `limit`, col token vero. Controlla:

1. HTTP 200;
2. `meta.ordinamento` è la prima voce di `ui.fn_ordinamento_lista` per quell'utente, oppure manca se il preset non
   dichiara un ordinamento. È ciò da cui il FE accende l'intestazione;
3. le righe sono quante dice `ui.fn_misura_lista`, oppure tutte se sono meno;
4. le righe sono davvero in quell'ordine. Numeri e date si confrontano esatti; i testi in modo approssimato (senza
   maiuscole, accenti, spazi e punteggiatura), e lì un'inversione è un AVVISO, non un FAIL. I vuoti non si giudicano:
   dove vada il vuoto è il brief DB aperto il 2026-11-24;
5. il clic sulla colonna di partenza, con lo stesso verso, dà le stesse righe nello stesso ordine: è il controllo di
   BE30, perché preset e clic sono la stessa richiesta. Col verso opposto il clic rovescia l'ordine.

Le rotte con un parametro (le righe di un documento, le note) prendono l'id dalle prime righe della lista madre. Una
rotta che non si raggiunge, una lista con meno di due righe e una lista che vuole un filtro per contratto (la competenza
dei cruscotti, l'articolo dei lotti di magazzino, l'emittente delle pratiche) escono **SKIP**, col motivo: copertura
zero, e vanno a video. `PARTENZA_EMITTENTE=<id>` fa il giro su un altro emittente di `dev.smoke` e alla fine rimette
quello di prima. La modalità «Tutti gli emittenti» non serve: le liste con perimetro rispondono 422
`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`, come devono.

**Esito del 2026-11-24** su dbdev, col working tree di quel giorno: 123 rotte (50 export fuori dal giro), **nessun
FAIL**. I giri sono due: sull'emittente attivo di `dev.smoke` (41194) 55 OK e 68 SKIP, sul 44 50 OK e 73 SKIP. Unendo i
due, sono 56 le rotte verificate per intero. Delle liste di U40 sono verificate per intero `magazzino.disponibilita` e
`magazzino.disponibilita_articoli` (con lo spareggio di BE30), `magazzino.movimenti`, `magazzino.rettifiche` e
`vendite.resi`; le altre di U40, su quegli emittenti, sono vuote o non si raggiungono. Ogni lista con almeno due righe è
verde, comprese quelle dell'amministrazione del residuo di BE25 (2).
Un 401 `E_IDENTITA_NON_ATTIVA` a metà di un giro non si è ripetuto nei tre giri successivi: è una sessione chiusa da
fuori, non una lista. Il numero di righe è un fatto di quei giorni: dice cosa lo smoke ha potuto vedere, non quali liste
contano.

### 2.2 La parte FE: i campioni a video

L'intestazione accesa, il paginatore e il clic li fa solo il FE. Basta una superficie per tipo di componente, su un
emittente che abbia righe. Ogni lista si apre **senza preferenza salvata**.

| # | Lista | Perché questa |
| --- | --- | --- |
| 1 | `magazzino.movimenti` | store e `MovimentiSearchTable` con la copia ritirata da BE29; `data_mov` decrescente |
| 2 | `vendite.resi` | `ResiSearchTable`, `data` decrescente |
| 3 | `vendite.resi_da_accreditare` | la coda (`ResiCodaTable`, `order_by` iniziale `null`); BE30: a parità di data, reso e riga nell'ordine del repository |
| 4 | `magazzino.disponibilita` | `DisponibilitaSearchTable`; BE30: un articolo in più magazzini tiene i magazzini nell'ordine di prima |
| 5 | `anagrafiche.operatori` | residuo di BE25 (2): una lista dell'amministrazione (`AdminAPIView`) |
| 6 | `vendite.registri_numerazione` | superficie di catalogo, con misura **10**: il paginatore deve dire 10, non 25 |
| 7 | `anagrafiche.emittente_billing_account` | lista dentro un drawer (scheda dell'emittente), misura 10 |
| 8 | `vendite.dash_competenza_commesse` e `pratiche.pratiche` | vogliono un filtro: lo smoke non le apre |
| 9 | `vendite.ordine_righe` | senza ordinamento nel preset: l'intestazione resta **spenta** |

Su ognuno:

* l'intestazione della colonna di partenza è accesa e la freccia dice il verso dei dati;
* il paginatore porta la misura del preset;
* un clic su un'**altra** colonna riordina; alla riapertura della lista si riparte dal preset (Q39 (b));
* il caso di §2.3, sulla colonna di partenza.

### 2.3 Il terzo clic sulla colonna di partenza (da guardare a video)

Dal 2026-11-24 il giro di un'intestazione è crescente → decrescente → nessun ordinamento, per ogni colonna (commit
`b655c3ece`). Col terzo clic il FE chiede la lista senza `order_by` (`useSearchTable`, `intestazioneOrdinata`). Ma una
richiesta senza `order_by` è proprio quella a cui il BE applica il preset: la lista torna alla partenza e l'intestazione
di partenza si riaccende. Sulla colonna di partenza in verso decrescente (campioni 1-3) lo stato «nessun ordinamento»
quindi non si vede, e il giro potrebbe sembrare bloccato. Da guardare: **tre clic di fila** sulla colonna di partenza,
annotando a ogni clic la freccia e l'ordine delle righe. Atteso dalla guida
([configurazione-liste](../../guide/configurazione-liste.md) §6, «Intestazione delle colonne»): la freccia dice sempre
il verso in cui la lista è ordinata. Se a video il terzo clic «torna alla partenza», la guida è indietro («terzo toglie
l'ordinamento») e si aggiorna nello stesso giro delle correzioni. Se invece la freccia mente, è una correzione del FE.

## 3. Alla chiusura

Il brief va in `work-done/` quando il collaudo è fatto e le correzioni che ha trovato sono chiuse.
