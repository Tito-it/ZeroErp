# Analisi — copertura della doc API (strato 1): tutte le aree

**Chi scrive:** BE, 2026-08-19. **Cosa misura:** *quali rotte esistono nel
codice e non compaiono in nessun `.md`*, e viceversa quali path la doc nomina
senza che una rotta li serva.

> ⚠️ **«Documentata» qui vuol dire solo «il path e' nominato da qualche parte».**
> Non dice che la descrizione sia giusta, ne' aggiornata, ne' completa: quella e'
> un'altra misura (§6, strati 2 e 3). Una rotta puo' risultare documentata e
> avere una pagina che descrive l'API di tre mesi fa.

---

## 1. Come e' stata fatta

Le rotte non arrivano da una regex sui `urls.py` ma **dal resolver di Django**
(`get_resolver()`, ricorsivo): sono i path veri, con i metodi HTTP letti dalla
view. Le citazioni arrivano da tutta `docs/it/backend`.

Tre cose che cambiano il risultato, e che la prima passata sbagliava:

1. **le citazioni nella doc hanno tre forme** — assoluta
   (`/api/v1/vendite/resi/export/`), relativa (`POST /<id>/conferma/`, che vale
   sulla base del file) e troncata (`…/export/`). Contando solo le assolute,
   `api_resi.md` risultava non documentare i verbi che invece documenta;
2. **l'area di una rotta si legge dal PATH, non dal modulo Python.** Le note di
   documento vivono in `apps.core` ma rispondono su `/api/v1/vendite/...`:
   attribuirle a core produceva **due errori dallo stesso sbaglio** — scoperte
   fantasma in core e fantasmi in vendite;
3. **un path citato come prefisso non e' un fantasma.** «tutti gli endpoint sono
   sotto `/api/v1/core/tracciamento/`» non e' una rotta mancante.

⭐ **Lo script non e' piu' uno script**: e' il management command
`./manage-env.sh copertura_doc_api [--aree x,y] [--dettaglio]`
(`apps/core/management/commands/copertura_doc_api.py`). Le sei regole che ha
imparato — le tre forme di citazione, il jolly `{}` nei due versi, la lapide, i
valori d'esempio, la coda che ripete il path, il prefisso — sono l'unica ragione
per cui i numeri qui sotto significano qualcosa: senza, la misura inventava 19
fantasmi in `anagrafiche` e dichiarava scoperta meta' di `pratiche`, che e'
documentata al 100%.

## 2. I numeri

| | rotte | documentate | scoperte |
|---|---|---|---|
| **vendite** | 254 | ~~201 (79%)~~ → **248 (97%)** | ~~53~~ → **6** |
| **core** | 54 | ~~36 (66%)~~ → **54 (100%)** | ~~18~~ → **0** |
| **pratiche** | 49 | **49 (100%)** | 0 |
| **anagrafiche** | 72 | 67 (93%) | 5 |
| **amm-software** | 32 | 29 (90%) | 3 |
| **catalogo** | 22 | ~~16 (72%)~~ → **22 (100%)** | ~~6~~ → 0 |
| **ui** | 20 | ~~12 (60%)~~ → **20 (100%)** | ~~8~~ → 0 |
| **documenti** | 9 | ~~6 (66%)~~ → **9 (100%)** | ~~3~~ → 0 |
| altre (auth, config, portale, shop, admin, ai) | 26 | 26 (100%) | 0 |
| **TOTALE** | **538** | **524 (97%)** | **14** |

> ✅ **Fatti il 2026-08-19**: i fantasmi (§3), la famiglia della generazione
> documenti (§7), export e code core (§8), note di documento (§9). I numeri barrati sono la prima misura, quelli in grassetto lo
> stato di adesso. ⚠️ Parte del recupero di **core** non e' lavoro sulla doc ma
> **sulla misura**: vedi §7, il jolly `{}`.

⭐ **Le scoperte non sono sparse: sono famiglie intere.** Non e' «la doc e'
indietro di qualche endpoint», e' «ci sono blocchi funzionali che non ha
documentato nessuno».

| # rotte | famiglia | dove |
|---|---|---|
| **26** | **generazione documenti** — `documenti/`, `anteprima/`, `genera/`, `<id>/file/`, `allegati/`, `ristampa/` su **sei domini** (preventivi, offerte, ordini, DDT, contratti, fatture) | vendite |
| **10** | **lookup core** — comuni, conti-contabili, forme-giuridiche, sistema-codici, tipi-ruolo/*, tipi-soggetto-dettaglio/*, utilities-per-emittente | core |
| **6** | **export delle liste** — dashboard aperto/backlog/competenza, lotti, resi | vendite |
| **5** | **componenti BoM sulle righe** — `preview-componenti/`, `componenti/<id>/` su DDT e offerte | vendite |
| **4** | **note di documento** — contratti e preventivi (gli altri quattro domini sono documentati) | vendite |
| **4** | **config tables** — il pannello generico `/core/config/tables/...` | core |
| **12 + 4** | singoli: `pricing/diagnose/`, `resi/{id}/chiudi-riconsegna/` e `riapri-riconsegna/`, `lotti/{id}/riporta-a-draft/`, `lotti/mensile/`, `preventivi/{id}/riepilogo-iva/`, `ordini/form-defaults/`, le due `eccezioni-offerta/{id}/(approva\|rifiuta)-prezzo/`, `dashboard-competenza/gruppi/`, `lookup/listini-selezionabili-contratto/`, `preventivi/da-pratica/{id}/stato/`, `me/emittente-attivo/`, `me/sessioni/revoca-tutte/`, `search/stradario/` e `stradario-generale/` | entrambe |

**La famiglia grossa e' una sola, ed e' istruttiva.** La generazione documenti —
26 rotte, sei domini, lo stesso schema ripetuto — e' il cantiere della stampa
(versione pinnata, contesto congelato, ristampa fedele). Esiste
`docs/it/backend/documenti/` con cinque file, ma **non cita un solo `/api/v1/`**:
documenta il servizio, non l'API. Chi cerca «come si genera la stampa di un DDT»
non trova l'endpoint da nessuna parte.

## 3. I fantasmi — la doc descrive cose che non esistono piu'

Solo **4**, tutti in vendite, e tre hanno la stessa origine:

| path documentato | realta' |
|---|---|
| `/api/v1/vendite/listini/test-prezzo/` | **rimosso** da F2-BE-13 (il commento in `urls_listini.py:24` lo dice) |
| `/api/v1/vendite/listini/{id}/associazioni/` | idem — il modello v5 non usa piu' `listini_associazioni` |
| `/api/v1/vendite/listini/{id}/associazioni/{id}/` | idem |
| `/api/v1/vendite/lookup/modalita-pricing-contratto/` | nessuna rotta con quel nome; `api_vendite_lookups.md` la elenca in tabella |

Le prime tre stanno in `api_listini.md`: la rotta e' stata tolta e la pagina no.
E' il caso peggiore per chi legge, perche' **una pagina che descrive un endpoint
inesistente e' indistinguibile da una che descrive un endpoint funzionante**.

### ✅ Corretti il 2026-08-19

Le sezioni §5 e §6 di `api_listini.md` sono diventate **lapidi**: dicono cosa e'
sparito, da quale changeSet, e **cosa usare al suo posto** (matrice
`categorie_clienti_listini` / contratto per le associazioni; `resolve_prezzo` e
`POST /vendite/pricing/diagnose/` per il test resolver). Stessa cosa per il
lookup in `api_vendite_lookups.md`, dove la «modalita» A/B/C e' oggi una **forma
derivata** dai dati e non piu' una scelta dell'operatore.

⭐ Cancellare le sezioni sarebbe stato peggio: chi ha in mano codice che chiama
`/associazioni/` deve poter capire **perche'** non risponde piu' e dove andare.
Una pagina che tace su un endpoint rimosso e una che non l'ha mai avuto si
leggono uguale.

⚠️ **Trovato nel farlo, ed era piu' di quanto la misura dicesse**: gli stessi
payload di `api_listini.md` esponevano `associazioni_count` e `associazioni`, e
la regola di cancellazione del listino citava `associazioni_count == 0` — che
`fn_delete_listino` **non controlla piu'** (oggi guarda solo `versioni_count`).
Lo strato 1 vede i path, non i campi: e' un assaggio di quello che troverebbe
lo strato 2.

⚠️ **Una lezione sulla misura stessa**: appena corretti, i quattro path
risultavano ancora «fantasmi», perche' le lapidi li nominano. Lo script ora
esclude le righe marcate `⛔` / `RIMOSSO` / «non esiste piu'» — senza quella
regola, correggere un difetto non lo fa sparire dal conteggio e la misura smette
di servire. Rimisurato dopo: **fantasmi veri = 0** in entrambe le aree (i tre
residui sono un punto di prosa a fine riga, un esempio con valore letterale
`ef`, e il segnaposto `/api/v1/core/...`).

## 7. ✅ Fatta il 2026-08-19 — la famiglia «generazione documenti»

Nuova pagina: [api_documenti_per_sorgente](../../backend/documenti/manual/api_documenti_per_sorgente.md),
**una sola**, che chiude **26 scoperte su 53**.

**Perche' una e non sei.** Le view non sono sei copie: nascono dalla factory
`build_documenti_sorgente_views(...)`, e ogni dominio dichiara solo i suoi
delta. Documentare sei volte lo stesso flusso avrebbe creato sei copie
destinate a divergere — il difetto che questo repository conosce bene. La
pagina descrive il comportamento **una volta** e mette in tabella le
differenze.

**Cosa e' venuto fuori scrivendola** (e che la misura non poteva vedere):

* **due asimmetrie di dominio, entrambe volute e ora dichiarate**: `fatture` non
  ha `emetti/` (le produce la pipeline: si stampano, non si emettono) e
  `offerte` non ha `documenti/genera/` (si stampa una volta sola, con `emetti/`);
* ⚠️ **un'asimmetria di permessi che non e' dichiarata da nessuna parte**: fra i
  cinque domini con `emetti/`, **solo `preventivi`** dichiara anche un permesso
  di processo (`cambia_stato_preventivi`). O ne mancano quattro, o il preventivo
  e' l'eccezione e va scritto perche'. Segnalata nella pagina §5, **non
  modificata**: e' una decisione, non un refuso;
* la famiglia **non era «non documentata»**: `api_ristampa_fedele.md` la
  descrive bene, ma **senza scrivere un path per esteso** (`GET
  .../documenti/<id>/file/`). Era spiegata e non trovabile — che per chi cerca
  e' quasi lo stesso.

### Due lezioni sulla misura, non sulla doc

⚠️ **Il jolly `{}` vale nei due versi.** Una pagina cross-dominio scrive
`/api/v1/vendite/<dominio>/{id}/emetti/` e copre sei rotte concrete: confrontando
le stringhe risultavano tutte scoperte, cioe' **la misura puniva la doc scritta
bene**. Ora `{}` vale «un segmento qualunque». Effetto collaterale: +7 rotte
documentate anche in **core** e in vendite, senza che nessuno scrivesse una riga
— erano coperte da sempre.

⚠️ **E lo stesso jolly serve sui fantasmi.** Applicato solo alla copertura,
faceva risultare **16 fantasmi** appena scritta la pagina nuova: le sue citazioni
generiche non corrispondevano a nessuna rotta *letterale*. Una misura asimmetrica
crea un difetto dove non c'e'. Sistemata: i 7 residui di vendite sono i noti
artefatti (menzioni di prefisso, la sintassi `{approva|rifiuta}`, un punto di
prosa a fine riga).

## 8. ✅ Fatta il 2026-08-19 — export e code di core

**Core chiude a 54/54.** Quattro interventi, tre dei quali sono aggiunte a
pagine esistenti:

| cosa | dove | rotte |
|---|---|---|
| **export delle liste** — un contratto solo per tutti | nuova [api_export_liste](../../backend/ui/manual/api_export_liste.md) | 17 (7 erano scoperte) |
| **CRUD generico tabelle config** — non aveva **nessuna** doc | nuova [api_config_tables](../../backend/core/manual/api_config_tables.md) | 4 |
| **lookup a matrice** (indirizzi per tipo soggetto / per ruolo, utility per ruolo) | sezione in `api_lookup_codici.md` | 3 |
| **stradario**, **revoca-tutte**, **emittente-attivo** | sezioni in `api_search_universale.md`, `api_sessioni_attive.md`, `api_user_profile.md` | 4 |

**Perche' una pagina sola per gli export.** Sono **17 endpoint identici**: stesso
parametro, stesso tetto, stesso renderer. Documentarli nelle 12 pagine di
dominio avrebbe prodotto 12 copie della stessa regola — e la regola che serve
davvero e' proprio quella che si perde nelle copie: ⛔ **il parametro si chiama
`formato`, non `format`**, perche' `format` e' un magic param di DRF e la
richiesta muore con **404** prima di arrivare alla view. Un difetto che si
presenta come «endpoint inesistente» va scritto una volta, in grande.

La pagina porta anche la tabella dei `lista_codice` — che e' la chiave del
cancello perimetro emittente, non un dettaglio interno — e la nota sul perche'
l'export lo debba dichiarare **quanto e piu' della lista**: e' la porta piu'
larga, 10.000 righe per richiesta.

⚠️ **Trovato scrivendo, non misurato**: `config_crud_service` risponde con
`E_ANAG_NOT_FOUND` e `E_ANAG_DUPLICATO` su endpoint `core`. Non e' rotto — e' un
nome che mente sull'area. Documentato com'e' (`api_config_tables.md` §Codici
errore), non corretto: cambiare un codice errore e' roba da concordare col team
DB.

### Cosa resta in vendite: 14 rotte, e una e' una famiglia

* **note di documento (4)** — `contratti` e `preventivi`. ⭐ Ma il difetto vero e'
  un altro: **e' un BB solo (`partitioned_note_service`) descritto quattro volte**
  in quattro pagine di dominio, con quattro livelli di dettaglio, e mancante in
  due. E' lo stesso caso della generazione documenti (§7): la cura e' una pagina
  sola piu' sei rimandi, non due sezioni nuove;
* **componenti BoM su righe (3)**, **eccezioni offerta approva/rifiuta (2)**,
  **verbi ri-consegna dei resi (2)**, **`lotti/{id}/riporta-a-draft/` (1)**,
  **`preventivi/da-pratica/{id}/stato/` (1)**, **`riepilogo-iva` (1)**: endpoint
  di dominio, da chiudere insieme alla verifica di sostanza del loro dominio
  (strato 2), non a parte.

## 9. ✅ Fatta il 2026-08-19 — le note di documento

Nuova pagina [api_note_documento](../../backend/core/manual/api_note_documento.md)
piu' **sei rimandi**. Chiude le 4 rotte scoperte, ma il difetto vero era un
altro: **un building block descritto quattro volte e mancante in due**, con
quattro livelli di dettaglio diversi. Ora il contratto sta in un posto e ogni
dominio dichiara solo il proprio delta (partizione, `target_tipo`, righe
ancorabili).

Cose che stavano solo nel codice e ora sono scritte:

* ⛔ **`Idempotency-Key` obbligatoria** sulla creazione. Una nota doppia non da'
  errore a nessuno — per questo il presidio e' in ingresso;
* ⛔ **`target_riga_id` immutabile** in `PATCH`: una nota non trasloca di riga,
  si cancella e si riscrive (cosi' l'audit dice cosa e' successo);
* **`include_invisible` di default `true`**, e il perche': «invisibile» vuol dire
  «non esce in stampa», non «segreta» — il drawer dell'operatore le deve vedere;
* i **default di stile e lingua** viaggiano per **chiave naturale**
  (`codice_interno`, `codice_iso`) e non per id, perche' l'id cambia a ogni
  re-seed e un default sbagliato si vedrebbe solo in stampa, tardi;
* i permessi sono di **livello oggetto** per dominio (`model_permission`), non di
  sola area.

⚠️ **Restano 10 rotte in vendite**, tutte di dominio: componenti BoM (3),
`eccezioni-offerta` approva/rifiuta (2), i due verbi di ri-consegna dei resi,
`lotti/{id}/riporta-a-draft/`, `preventivi/da-pratica/{id}/stato/`,
`riepilogo-iva`. Non sono famiglie: sono endpoint singoli che conviene chiudere
con la verifica di sostanza del loro dominio (strato 2).

## 4. Lo schema OpenAPI c'e', ma oggi non puo' sostituire la doc

`drf_spectacular` e' configurato e `manage.py spectacular` produce lo schema. Ma:

* **66 errori unici** (201 occorrenze), e sono tutti **lo stesso errore**:
  *«unable to guess serializer»*. Ripartizione: **33 vendite, 14 core**, 10
  amm_software, il resto sparso;
* la causa e' strutturale: le view sono `APIView` senza `serializer_class`, cioe'
  il pattern di questo progetto (il lavoro sta nei service e nel DB, non nei
  serializer DRF). Spectacular non ha da dove dedurre la forma di richiesta e
  risposta, e **degrada silenziosamente**: l'endpoint finisce nello schema senza
  corpo.

⚠️ Conseguenza sulla domanda «meglio generare che scrivere?»: **oggi no.** Lo
schema generato sa i path e i metodi — che e' proprio la parte che la doc a mano
gia' copre bene — e **non sa** quello che serve davvero (payload, risposta,
codici errore). Renderlo utile vuol dire annotare le view con `@extend_schema`,
cioe' comunque scrivere: la scelta non e' «generare invece di scrivere» ma «dove
scrivere», nel codice o nel markdown.

## 5. Cosa NON dice questa misura

* nulla sulla **correttezza** di quello che c'e' (strato 2 e 3);
* nulla sui **metodi**: una rotta `GET,POST` documentata solo per il `GET`
  risulta documentata;
* le pagine di dominio (`modello-contratti.md`, `pricing_service.md`, i
  `template_*`) non sono state valutate: non sono doc di API.

## 6. Proposta per il seguito

1. **I 4 fantasmi si correggono subito** — sono quattro righe, ed e' il difetto
   che costa di piu' a chi legge. **Lavoro di minuti.**
2. **La famiglia «generazione documenti» merita una pagina sola**, non sei: lo
   schema e' identico sui sei domini (e' un BB), quindi una `api_documenti_generati.md`
   con la matrice dei domini vale piu' di sei sezioni copiate. **Mezza giornata**,
   e chiude 26 delle 53 scoperte.
3. **I lookup core (10) e gli export (6)** sono elenchi: una tabella per
   famiglia, non una sezione per endpoint. **Poche ore.**
4. **Strato 2 (forma) e strato 3 (sostanza)**: da fare per dominio, quando quel
   dominio si tocca. Non ha senso un giro unico su 254 rotte.
5. **Da decidere una volta**: se `@extend_schema` sulle view diventa la sede dei
   payload — e allora la doc markdown resta la parte narrativa — oppure se lo
   schema OpenAPI resta uno scheletro e la verita' sta nel markdown. Oggi non e'
   deciso, e i 66 errori sono la conseguenza di non averlo deciso.
