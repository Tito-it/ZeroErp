# Brief DB — I modelli di documento standard: un emittente nuovo emette dal primo giorno

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: Tid, con le tre decisioni del §5; poi il team DB, col disegno della forma (§4).**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | **Tid** | D-1 (ripiego o copia), D-2 (chi modifica lo standard), D-3 (da dove viene il contenuto) | §5 | — |
| 2 | **team DB** | Disegno della forma e risposta alle domande Q-1 … Q-5 | §4 | 1 |
| 3 | **Tid** | Il via allo sviluppo | — | 2 |
| 4 | **team DB** | ChangeSet, seed dei sei modelli, pgTAP | §4 | 3 |
| 5 | **Tid** | Apply su dbdev, pgTAP | — | 4 |
| 6 | **BE/FE** | La risoluzione a due livelli e la lista Modelli documento | §6 | 5 |
| 7 | **BE** | Il giro degli smoke su `dev.smoke` (DEVA emette con lo standard) | §7 | 6 |
| 8 | **Tid** | Archiviazione in `work-done/` | — | 7 |

**Decisioni aperte di Tid: D-1, D-2, D-3 (§5).** Da committare: questo documento.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18. **A chi:** Tid (§5), poi il team DB;
> la §6 al BE/FE.
> **Origine:** il collaudo T-5 di [brief-be-utenti-di-sviluppo](brief-be-utenti-di-sviluppo.md)
> (§9). L'emittente di prova A, creato dal verbo di sviluppo, non emette nessun documento: non ha
> modelli. Proposta di Tid (2026-10-18): «la cosa migliorativa è fornire un set di modelli
> standard».
> **Stato:** 📝 proposta; nessun codice scritto.

## 1. Il caso

Un emittente fiscale nasce senza modelli di documento. Finché qualcuno non ne scrive uno per tipo
dalla UI (Configurazione → Modelli documento), ogni emissione si ferma con `E_DOCUMENTI_NOT_FOUND`
«Nessun template applicabile per la sorgente»: preventivo, offerta, contratto, ordine, DDT e
fattura.

Vale per ogni emittente nuovo: quello di un'installazione di produzione appena fatta, il secondo
emittente di un'azienda che ne aggiunge uno, gli emittenti di prova del verbo di sviluppo, un
database ricostruito da zero in CI.

## 2. Perché è un difetto del modello

**Un emittente è un'identità completa solo se può emettere.** I modelli non nascono con
l'emittente, e senza modelli l'emittente si può creare ma non usare. È uno stato che il modello
lascia nascere e che nessuna regola chiude.

⚠️ **Non solo i modelli** (fatto del 2026-10-18, smoke `push-termine-documento-commessa`):
l'emittente di prova A non ha nemmeno il **registro delle fatture**.
`vendite.fn_get_registro_id` solleva `E_CONFIG_MANCANTE` «registro non risolto per tipo_doc 1 e
natura 1» quando la commessa genera la fattura. È lo stesso difetto su un'altra configurazione: al
team DB chiediamo di censire che cosa serve a un emittente per emettere ogni documento (modelli,
registri, altro) e di dire, per ciascuna voce, se nasce con l'emittente o ha uno standard. Il
censimento si fa sulla struttura (funzioni di risoluzione, FK, guard), non sulle righe di dbdev.

➡️ **La voce «registri» ha la sua risposta** (team DB, 2026-10-18): è R-BE-14, in
[brief-db-processi-accensione-per-ambiente §6.14](brief-db-processi-accensione-per-ambiente.md). Nessun
emittente nasceva col registro delle fatture. ✅ Fatto il 2026-10-18 (`20261019-07` … `-12`, applicati su
dbdev, pgTAP verdi): il registro delle fatture standard nasce con l'emittente, dallo stesso meccanismo che crea già
i registri delle altre famiglie. Le altre voci del censimento restano da fare.

C'è anche un secondo difetto, e riguarda come i modelli **evolvono**:

* nessun changeSet **crea** una riga di `documenti.template_documenti`: le righe nascono solo dalla
  UI;
* i changeSet che fanno **evolvere** un modello (esempio: `20260816-01`, la forma a slot degli
  indirizzi del preventivo) scrivono una bozza nuova e la pubblicano, **cercando i modelli per
  `codice_interno`** (`WHERE t.codice_interno = 'test'`, `IN ('ord-ven', 'contratto', 'off-comm')`)
  su tutti gli emittenti insieme.

Quindi:

* su un'installazione nuova quei changeSet non trovano niente, e l'evoluzione non arriva da nessuna
  parte;
* un modello scritto dalla UI con un altro `codice_interno` resta alla forma vecchia. Quando il
  context builder cambia forma (il caso del 2026-08-16), quel modello si rompe al render;
* ogni emittente porta **la sua copia** dello stesso modello, e un'evoluzione va ripetuta su ognuna.
  Le copie, prima o poi, divergono.

Un insieme standard **di sistema**, fornito dal seed e fatto evolvere dai changeSet, chiude
entrambi: l'emittente nuovo emette dal primo giorno, e l'evoluzione ha una sede sola.

## 3. I fatti di struttura (doc `dbzero`, 2026-10-18)

| Pezzo | Com'è oggi | Che cosa c'entra |
| --- | --- | --- |
| `template_documenti.emittente_fiscale_id` | `NOT NULL`, FK su `emittenti_fiscali` | lo standard non ha un emittente |
| `trg_template_documenti_a10_default_emittente_ins` | `script.trgfn_default_emittente_fiscale('SOLLEVA')`: all'INSERT l'emittente viene dalla sessione, e se manca solleva | una riga di sistema non nasce da una sessione d'operatore |
| `uq_template_documenti_default_attivo` | un solo default attivo per `(tipo_documento_output, sorgente, emittente)` | serve anche per lo standard; con un emittente NULL l'indice unico non lo protegge (i NULL sono distinti) |
| `uq_template_documenti_emittente_sorgente_codice[_interno]` | unicità per emittente | come sopra |
| `trgfn_documenti_generati_check_coerenza`, regola 4 | l'emittente del modello deve essere quello del documento generato (`E_DOCUMENTI_GENERATO_COERENZA`) | un documento di DEVA reso con lo standard la viola |
| `template_asset` | catalogo per emittente (`emittente_fiscale_id NOT NULL`, unicità per emittente) | il logo di un modello standard non può essere un asset fisso: deve essere quello dell'emittente del documento |
| `template_documenti_versioni.versione_contesto` | la forma dei dati che la versione legge, controllata da `fn_guard_versione_contesto` | lo standard segue lo stesso patto: nessuna regola nuova |
| RLS su `template_documenti` | nessuna policy; il perimetro lo applica il BE (`emittente_ids_scope`) | la lettura dello standard va aperta a tutti, la scrittura no (§6) |
| Seed | i sei `tipi_documento_output` (PREVENTIVO, CONTRATTO, OFFERTA_COMMERCIALE, ORDINE_VENDITA, DDT_VENDITA, FATTURA_VENDITA) ci sono; nessun modello | il seed nuovo è uno per tipo |

## 4. La proposta, al team DB

**Un modello standard per ogni tipo di documento di output, di sistema, usato come ripiego.**

* Il seed fornisce un modello standard per tipo, con una versione pubblicata.
* La risoluzione ha due livelli: prima il **default attivo dell'emittente** del documento; se non
  c'è, il **default attivo standard** della stessa coppia (tipo output, sorgente).
* Un emittente che vuole un modello suo lo crea. Da quel momento vince il suo, e lo standard resta
  il ripiego degli altri.
* I changeSet che fanno evolvere un modello scrivono **sullo standard**, trovato per chiave e non
  per `codice_interno` sparso tra gli emittenti.

La forma è del team DB. Le domande che vediamo:

* **Q-1 — Come si scrive «standard»?** `emittente_fiscale_id` nullable con un `CHECK`, oppure un
  flag di sistema con l'emittente nullo, oppure una tabella sorella. Va tenuto conto di
  `trgfn_default_emittente_fiscale('SOLLEVA')`, che oggi riempie l'emittente dalla sessione, e
  degli indici unici, che con un NULL non proteggono (`NULLS NOT DISTINCT` o un indice parziale
  apposta).
* **Q-2 — La risoluzione a due livelli: dove vive?** Oggi la scrive il BE
  (`DocumentiRepository.find_template_applicabile`). Se la regola sta nel DB (una funzione
  `fn_risolvi_template_applicabile`), il BE la chiama e non la riscrive. Lo proponiamo: è una
  regola del modello, non una query di lista.
* **Q-3 — La coerenza del documento generato.** La regola 4 di
  `trgfn_documenti_generati_check_coerenza` diventa: l'emittente del modello è quello del documento
  **oppure** il modello è standard.
* **Q-4 — Il logo e gli asset.** Un modello standard non può puntare a un asset di un emittente.
  Il logo arriva dal contesto, con l'asset dell'emittente del documento se ce l'ha. Oppure lo
  standard non ha logo. Tutte e due le strade funzionano: dite voi quale.
* **Q-5 — Il destino delle copie di oggi.** Gli emittenti che hanno già i loro sei modelli restano
  com'erano: sono personalizzazioni a tutti gli effetti, e vincono sullo standard. Quello che
  cambia è che i changeSet di evoluzione futuri scrivono sullo standard. Le copie che vogliono la
  stessa evoluzione vanno trattate una per una, o ritirate (spente) a favore dello standard.
  Proponete voi il criterio. Non serve un giro di pulizia adesso.

pgTAP, sui casi costruiti e non sulle righe di dbdev: un emittente nuovo emette con lo standard;
l'emittente con il suo default lo preferisce; un secondo default standard per la stessa coppia è
rifiutato; un documento generato con lo standard passa la coerenza, uno con il modello di un altro
emittente no.

## 5. Decisioni di Tid

* **D-1 — Ripiego o copia alla nascita?** Proposta: **ripiego** (§4). Una copia fatta alla nascita
  dell'emittente ripete il difetto del §2: N copie dello stesso modello, e un'evoluzione da
  ripetere N volte.
* **D-2 — Chi modifica lo standard?** Proposta: **solo i changeSet**, come ogni seed di sistema.
  Nella UI lo standard si vede in sola lettura, con un'azione «personalizza per questo emittente»
  che crea il modello dell'emittente partendo dalla versione standard. È una copia voluta,
  dichiarata e fatta da chi la vuole: diversa da quelle del §2.
* **D-3 — Da dove viene il contenuto?** I modelli di oggi sono stati scritti a mano dalla UI per un
  emittente. Proposta: si parte dalle versioni pubblicate dell'emittente 32 (quelle che i changeSet
  di evoluzione hanno tenuto aggiornate) e si tolgono i riferimenti specifici dell'azienda (testi
  fissi, asset). Il contenuto va riletto da Tid prima del seed.

## 6. Ricaduta BE/FE (dopo l'apply)

* **BE — risoluzione.** `find_template_applicabile` e `count_templates_attivi_no_default` passano
  alla regola del DB (Q-2). Il filtro di perimetro `emittente_ids_scope` deve lasciar passare lo
  standard, che non ha emittente. Il messaggio «manca predefinito» guarda tutti e due i livelli.
* **BE — scrittura.** Lo standard si rifiuta in modifica dalla API (D-2), con un codice d'errore
  nuovo se il DB non lo copre già con il suo guard: policy generata **e** ripiego.
* **FE — lista Modelli documento.** Lo standard compare con un badge «standard» in sola lettura.
  Sull'emittente che non ha il suo, la riga dice che si usa lo standard. Azione «personalizza».
* **Documento generato.** Lo storico (`documenti_generati`) punta già alla versione usata: nessun
  cambio.

## 7. Ricaduta sugli smoke

Con lo standard, l'emittente di prova A (DEVA) emette senza configurazione. Gli smoke che oggi si
fermano su `E_DOCUMENTI_NOT_FOUND` (preventivi, smistamento-ordine, contratti-addebito,
listini-v5 dal passo 16, pratica-preventivi-bivio, resi-vendita sul modello delle bolle) arrivano in
fondo. L'elenco aggiornato è la tabella di R-BE-14 in
[brief-db-processi-accensione-per-ambiente §6.12](brief-db-processi-accensione-per-ambiente.md)
(2026-10-19): lì il BE ha chiesto registri e template insieme; i template sono di questo brief. Gli smoke della fatturazione, che cercano un'attività
fatturabile esistente, restano un lavoro loro: si costruiscono la materia (brief BE utenti di
sviluppo, §9, T-7).

Restano fuori da questo brief, perché non hanno un default di sistema sensato: i listini e la
mappa categoria cliente → listino. Sono decisioni commerciali dell'azienda, e gli smoke li creano
da sé (T-7).
