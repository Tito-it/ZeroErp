# Brief BE — Fan-out isolato come building block + esito parziale del pull

> **Tipo**: brief esecutivo backend (piano di sviluppo) · **Data**: 2026-08-09 ·
> **Owner**: Tid · **Branch**: `dev/backend-tid`
>
> **Stato**: ✅ **ESEGUITO** (2026-08-09) — F0..F6 tutte fatte, **2234 test verdi**.
> Consuntivo e scostamenti dal piano in **§11**; il residuo `commessa_cache`, che il
> consuntivo lasciava aperto, è stato **chiuso in giornata** su richiesta di Tid — **§12**.
>
> ✅ **CHIUSO il 2026-09-12 — la linea del fan-out chiude per intero.** Le due
> validazioni in-app di §13 sono entrambe fatte: **V2** il 2026-09-01
> ([collaudo-in-app-v2-dl23-e-area-resi](collaudo-in-app-v2-dl23-e-area-resi.md)),
> **V1** il 2026-09-12 con la prova 5 verde
> ([collaudo-in-app-esito-parziale-pull-commessa](collaudo-in-app-esito-parziale-pull-commessa.md))
> — dopo aver trovato e chiuso due difetti di modello sul rilancio
> ([brief-db-rilancio-step-non-rivede-le-proprie-commesse](brief-db-rilancio-step-non-rivede-le-proprie-commesse.md)).
> Da qui in giù il documento è storia: gli stati datati restano com'erano.
>
> ~~🟡 **Questo doc resta APERTO come raccoglitore dell'intera linea**: gli altri tre
> documenti del cantiere sono chiusi e archiviati, e **cio' che manca vive in §13**.
> Nessun altro documento aperto: se cerchi «cosa resta», è lì.~~
>
> **Stato al 2026-08-10**: ✅ commit fatto e pushato · 🔴 restano le **due validazioni
> in-app** (V1 esito parziale del pull, V2 slice 3-ter) e il **build docs**.
>
> **Stato al 2026-08-16**: ✅ **build docs fatto e verde** (§13.3 — `zensical` nel
> frattempo è installato) · 🔴 restano **solo le due validazioni in-app**. Misurato
> oggi: il pull **non è mai stato lanciato dopo il fix** — nessun task run in tutta
> la pipeline dal 2026-08-03 — quindi V1 è aperta nei fatti, non solo sulla carta
> (§13.1). Per V2 mancano dei soggetti su cui provare: dettaglio in §13.2.
>
> **Stato al 2026-08-16, sera** — avanzamento su entrambe:
>
> * **V1**: ✅ **caso normale passato** (lotto `LTF-0003953`, 8 task run su 8
>   `COMPLETATO`): il fan-out estratto a BB è girato in app per la prima volta dal
>   2026-08-03. Restano il caso **parziale** e il caso **tutto-rosso** (§13.1);
> * **V2**: ✅ **DL-19 chiuso su entrambi i rami** — e per farlo è emerso un
>   difetto a sé sull'ordine, già passato al team DB (§13.2). Restano DL-28,
>   DL-23, card/drill-down, coda accrediti e DL-27.
>
> **Stato al 2026-08-17**: ✅ **DL-27 e la lista coda accrediti** — il caso è
> stato costruito a mano (`DDT0010839` → fattura → `RESO0005122`) e la coda, che
> era **vuota da sempre**, ha la sua prima riga: accredito dovuto 5, etichetta
> DOVUTA, verificata a video. ⏸️ **DL-28 sospeso**: la metà «blocco parlante»
> non è costruibile finché le righe a prezzo zero non sono ammesse
> ([brief dedicato](brief-ddt-righe-senza-prezzo.md), decisione di Tid presa).
> Restano provabili: **DL-23** (da costruire), le **card DDT/RESI con i
> drill-down**, la seconda metà di DL-28 e il ramo «reso in DRAFT» di DL-27.
>
> 🐛 Validando sono emersi **due difetti FE fuori slice**, entrambi corretti in
> giornata (testata DDT non salvata in creazione, per due finestre distinte —
> dettaglio in §13.2). E un cantiere nuovo: la coda accrediti è un **ramo
> morto** senza il verbo che emette la nota di credito
> ([brief-design-note-credito-resi.md](brief-design-note-credito-resi.md),
> decisioni di dominio già prese).
>
> **Stato al 2026-08-17, fine giornata — V2 quasi chiusa.** Fatti anche:
> **DL-27 ramo DRAFT** (un reso in bozza non entra in coda: non ha nemmeno il
> numero), **DL-28 seconda metà** (`DDT0010840` CONTO_VISIONE resta fuori dai
> pushabili), **DL-23 primo ramo** (`ORD0018587` da 10 evaso per 4: serbatoio
> 6 + DDT 4, nessun doppio conteggio) e il **drill-down dell'area DDT**.
>
> **Resta aperto di V2**: il ramo `CONFERMATO` di DL-23 (nessun soggetto, va
> costruito), la metà «blocco parlante» di DL-28 (⏸️ sospesa) e l'area RESI
> delle card (vuota per progetto finché non esiste la NC). **Di V1**: il caso
> parziale e il caso tutto-rosso.
>
> 📌 Emersa validando, e messa nel brief NC: **la merce aggiunta a mano su un
> DDT da ordine resta fuori partita** — fatturata ma non accreditabile. Tre
> opzioni in valutazione da Tid (§7-bis del brief NC).
>
> **Stato al 2026-08-31 — due voci sospese si sono sciolte, e restano TRE cose.**
> Non le ha chiuse questo cantiere: le hanno chiuse i cantieri a valle, e il
> brief non se n'era accorto.
>
> * ✅ **DL-28, metà «blocco parlante»**: ⏸️ dal 2026-08-17 *«finché le righe a
>   prezzo zero non sono ammesse»*. Sono ammesse dal **2026-08-19** ed
>   **esercitate in-app il 2026-08-27** — il gate scatta su un documento vero
>   per la prima volta da quando esiste (§13.2, riquadro DL-28);
> * 🟡 **area RESI delle card**: era vuota *«per progetto, finché non esiste la
>   NC»*. La NC è chiusa il **2026-08-26** e le due celle di seed ci sono già —
>   `MERCE_RESA_GIA_FATTURATA` è `RECUPERABILE` con azione. La voce passa da
>   **bloccata** a **da guardare**: nessuno l'ha ancora vista a video.
>
> * ⭐ **V1, esito parziale**: **validato in-app il 2026-08-26** — su un **terzo**
>   consumatore di `run_fan_out` che questo brief non sapeva di avere
>   (`resi_service.accredita_righe_reso`), dalla prova **5** del collaudo nota
>   di credito. Il **telaio** del BB — isolamento per item, tre stati, motivi
>   per item — è esercitato in applicazione, non solo dai test (§13.1).
>
> 🔴 **Cosa resta aperto.** Di **V1**, la sola metà **pipeline**: che il
> `task_run` si chiuda in **ERRORE** e che il rilancio **RITENTI** invece di
> saltare — coperta da tre test mirati, che però girano **su mock**: per la
> regola zero è un **presidio**, non una prova. ⇒ **Decisione a Tid**: se il
> presidio basta, V1 si chiude dichiarandolo tale. ~~Di **V2**: il ramo
> `CONFERMATO` di **DL-23** (nessun soggetto, va costruito) e la verifica
> dell'area RESI qui sopra.~~ → **V2 chiusa il 2026-09-01**, blocco qui sotto.
>
> ✅ **E il §14 non lascia più niente**: la sola voce di sviluppo che
> conteneva — la visibilità del lotto riaperto — è **caduta il 2026-08-31**
> (il segnale arriva all'API dal 22/08 e il FE lo rende sul verbo; il Tag è
> stato valutato e **scartato**, perché `riaperto_il` non è uno stato).
> Le due voci **di documentazione DB** che ne sono uscite stanno nel blocco
> «AL TEAM DB» qui sopra.
>
> ⚠️ **Resta in piedi l'avvertenza del §13.1**: la fattura **2263 non va
> numerata**, e «Rendi definitive» numera *tutte* le EMESSA del mese.
>
> ---
>
> ## ✅ STATO AL 2026-09-01 — **V2 È CHIUSA PER INTERO**
>
> Il verbale è
> [collaudo-in-app-v2-dl23-e-area-resi.md](collaudo-in-app-v2-dl23-e-area-resi.md),
> archiviato in `work-done`: **sei prove su sei ✅**, nessun difetto di modello.
>
> * **DL-23 ramo `CONFERMATO`** — soggetto costruito (`ORD0036000`, `ARC005474`
>   10 pz, DDT di 4 non numerato): ORDINI mostra il **pieno**, e l'area DDT
>   **non mostra il DDT**. L'invariante «la merce vale 10, una volta sola»
>   regge su **entrambi** i rami. ⭐ Non era un caso fortunato: il resolver
>   `vw_dash_fatturazione_ddt` esclude per costruzione i DDT di ordini a
>   trigger `CONFERMATO` (`20260718-07`), ed è **quella riga di codice** che il
>   §13.2 chiedeva di vedere all'opera;
> * **area RESI delle card** — c'è, con azione e `valore_fermo` **vuoto**
>   (DL-11), e il **drill-down apre il drawer del reso**: era l'unico pezzo
>   non garantito a tavolino, perché la whitelist è condizione necessaria e non
>   sufficiente;
> * **ramo `MERCE_RESA_GIA_FATTURATA`** — soggetto ricostruito e **lasciato
>   lì**, non accreditato: il seed promosso a `RECUPERABILE` produce davvero la
>   seconda riga nel Backlog. Il soggetto resta disponibile per la prossima
>   volta, che è ciò che era mancato al giro precedente.
>
> 🐛 **E la validazione ha trovato un difetto FE fuori slice, corretto in
> giornata**: quattro drawer che generano un documento non avvisavano la
> propria lista — quattro copie dello stesso momento con **tre** comportamenti,
> nessuna delle quali falliva. Corretto **centralizzando** su
> `useDrawerSavedListRefresh` (nuovo handler `onDrawerChanged`), non
> rattoppando i quattro siti: dettaglio nel verbale, sezione «Che cosa ha
> trovato».
>
> 🔴 **Resta SOLO V1**, e con essa la decisione già posta a Tid qui sopra: le
> **23 caselle** di
> [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md)
> (nessuna eseguita), **oppure** la dichiarazione che il presidio a mock basta.
> ⛔ **Finché una delle due non arriva, questo brief NON va in `work-done`**:
> è l'ultima cosa viva della linea.
>
> ---
>
> ## 📋 STATO DI SVILUPPO AL 2026-08-31, sera — zero codice aperto
>
> **Non resta niente da scrivere.** Le tre voci vive sono **validazioni a
> video**, e ognuna ha ora il suo copione:
>
> | Voce | Copione | Stato |
> | --- | --- | --- |
> | **V1** · esito parziale del pull (metà pipeline) | [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md) | 🔴 23 caselle su 24 — il prerequisito `RESUME_TASK` è già spuntato |
> | **V2** · DL-23 ramo `CONFERMATO` | [collaudo-in-app-v2-dl23-e-area-resi.md](collaudo-in-app-v2-dl23-e-area-resi.md) · prova **A** | ✅ **chiusa il 2026-09-01** — soggetto costruito, invariante retta |
> | **V2** · area RESI delle card | stesso documento · prove **B1/B2** | ✅ **chiusa il 2026-09-01** — area, azione, `valore_fermo` vuoto, drill-down e secondo motivo |
>
> ⭐ **Il lavoro di sviluppo di questa giornata**, tutto nato dal push DB e
> nessuno chiesto dal brief: `etichetta_key` nel giornale (BE + i **tre** punti
> FE che rendono + le sei chiavi i18n), provato con chiamata reale sul lotto
> 6260. Dettaglio nel blocco «CODA DI DB-R2» qui sopra. **1839 test verdi**,
> lint pulito.
>
> ### 🔎 Documenti incongruenti trovati su questa attività (2026-08-31)
>
> Cercati apposta, su richiesta di Tid. Tutti e tre dicevano **«4 aree»** dove
> le aree misurate sono cinque: è lo stesso residuo, lasciato indietro
> dall'ingresso di **DDT** (2026-07-18, DL-21) e dei due rami **RESI**
> (`20260718-14`, DL-24).
>
> | Dove | Cosa diceva | Esito |
> | --- | --- | --- |
> | [api_dashboard_aperto.md](../../backend/vendite/manual/api_dashboard_aperto.md) | *«union 4 aree documento»* — e **due righe sopra** lo stesso file dichiara «5 aree sempre presenti» | ✅ **corretto**: contraddiceva sé stesso |
> | idem, riga sulla RLS | *«RLS invoker sulle 4 aree documento»* | ✅ **corretto a 5** |
> | [api_dashboard_backlog.md](../../backend/vendite/manual/api_dashboard_backlog.md) | *«RLS invoker sulle 4 aree documentali»* | ✅ **il numero è stato tolto**, non aggiornato: cambia a ogni area nuova e la frase non ne ha bisogno |
>
> ⭐ **Misurato, non dedotto**: `pg_class.relrowsecurity` dice che hanno la RLS
> **tutte e sette** — `preventivi`, `ordini`, `offerte_commerciali`, `contratti`,
> `ddt`, `resi` **e `commesse`**. Il «4» non era una semplificazione: era un
> numero vero nel 2026-07 che nessuno ha più riletto.
>
> 🔵 **Una quarta, che NON ho toccato perché è del DB** — il `COMMENT` di
> `vendite.vw_dash_aperto_documenti` dichiara *«stock dei documenti … delle
> **4 aree** (PREVENTIVI/ORDINI/OFFERTE/CONTRATTI — no COMMESSE)»*, ma la vista
> restituisce **cinque** aree: misurato il 2026-08-31 col contesto operatore,
> `CONTRATTI 15 · DDT 4 · OFFERTE 2 · ORDINI 60 · PREVENTIVI 76`. ⚠️ È la vista
> stessa a smentire il proprio commento — e siccome quel commento è la fonte
> della doc auto-generata, l'errore si propaga a chi legge `dbzero`. Voce per il
> blocco «AL TEAM DB».
>
> ---
>
> ## 🔎 Stato al 2026-08-31, sera — le tre voci verificate sui dati
>
> Le tre cose aperte qui sopra sono state **portate davanti al database**, una
> per una, prima di dichiararle. Non le chiude nessuna — ma due cambiano forma,
> e una **si spacca in due metà con esiti diversi**. Sotto, l'esito; il
> dettaglio nelle rispettive sezioni.
>
> **① V1, metà pipeline — APERTA, e ora la prova che manca è più netta di
> prima.** Il presidio non basta ed era già deciso; ciò che si aggiunge è che la
> misura del 2026-08-16 su cui poggiava («zero run dal 03-08») è **scaduta**, e
> se qualcuno la rileggesse oggi la troverebbe falsa: la pipeline ha girato,
> 415 task_run in tutto, l'ultimo il **2026-08-28**. La domanda giusta non era
> *quanti run* ma *in che stato*:
>
> | | |
> | --- | --- |
> | `pull_attivita_da_commessa` | 24 `COMPLETATO` + 21 `ANNULLATO` — **zero `ERRORE`** |
> | task_run in `ERRORE`, tutta la tabella | 19, tutti di `numera_fatture` (13) e `genera_scadenze_lotto` (6) |
>
> ⭐ **Quello step non ha mai chiuso in ERRORE in vita sua**, quindi il resolver
> non ha mai avuto occasione di rispondere `RESUME` su di lui. È esattamente il
> ramo del cantiere, e resta non percorso.
>
> ✅ **E la materia per provarlo c'è**: il copione la dichiarava non misurata,
> ora è misurata e scritta — `2026-08` ha **7 commesse emittibili** su 9 gruppi,
> con la riga `commesse_sorgenti` da guastare indicata per ciascuna. Il
> prerequisito `RESUME_TASK` è **verificato** (pipeline 1 e 8).
>
> 🔴 **E provando a preparare il collaudo è saltato fuori un difetto NEL
> COPIONE** — dettaglio in §13.1-bis. L'`UPDATE` di **ripristino** era scritto
> `WHERE ruolo_link = 'COLLEGATO'`, cioè come speculare esatto del guasto: ma il
> modello ammette **1 ROOT + N COLLEGATO**, quindi su una commessa
> multi-sorgente quel comando prova a promuovere a ROOT **tutte** le righe e
> viene respinto da `uq_commesse_sorgenti_commessa_root` con un `23505`.
> L'`UPDATE` non passa, e la commessa **resta senza ROOT**: il ripristino
> fallisce proprio dove serviva di più. Corretto — si scrive sull'`id` della
> riga, che il guasto restituisce con un `RETURNING`.
>
> **② Area RESI delle card — la metà che si poteva guardare da qui è VERDE, e
> il soggetto indicato NON C'È PIÙ.** Due cose, e la seconda è una rettifica a
> questo brief:
>
> * ✅ **l'area RESI compare nel Backlog**, con l'azione: una riga,
>   `RESO0005123`, motivo `RICONSEGNA_NON_ESEGUITA`, classe `RECUPERABILE`,
>   azione *«Genera il DDT di ri-consegna»*. Il filtro `<> 'FISIOLOGICO'` non la
>   scarta. Le whitelist a valle la ammettono su **entrambi** i lati
>   (`DASH_FATTURAZIONE_AREE` nel BE, `DASH_AREA_CONFIG` nel FE, con drawer
>   `RESO_VENDITA`): la strada del drill-down è aperta per costruzione;
> * ⛔ **ma il ramo `MERCE_RESA_GIA_FATTURATA` non ha soggetti oggi**, e il
>   brief indicava proprio quello: *«va vista con il soggetto che c'è già
>   (`RESO0005122`, accredito dovuto 5)»*. `vw_resi_da_accreditare` è **vuota**.
>   Non è un difetto — è il verbo che ha funzionato: il collaudo NC ha emesso
>   l'accredito, `gia_accreditato` è salito, `accredito_dovuto` è sceso a zero e
>   la riga è **uscita dalla coda**, che è precisamente ciò che la coda deve
>   fare. ⭐ Il soggetto è stato consumato dalla prova che lo aveva creato.
>
> ⚠️ **Rettifica di data, già che il paragrafo si tocca**: il §13.2 attribuisce
> il passaggio di `MERCE_RESA_GIA_FATTURATA` a `RECUPERABILE` alla slice NC del
> **2026-08-26**. È del **2026-08-18** — commit `06b661061`, e il mirror del CSV
> risulta `RERAN` quel giorno alle 15:13. La conclusione non cambia, la data sì.
>
> **③ DL-23, ramo `CONFERMATO` — APERTA, e il soggetto continua a non
> esistere.** Misurato oggi: gli ordini con `fatturazione_trigger = 'CONFERMATO'`
> sono 95 e sono **DRAFT (55), EVASO (36), CONFERMATO (3), ANNULLATO (1)** —
> nessuno `PARZIALMENTE_EVASO`. I due `PARZIALMENTE_EVASO` che esistono hanno
> entrambi trigger `SPEDITO`, cioè sono il ramo **già provato**. Il caso va
> costruito, come diceva il brief.
>
> ✅ **E il §14.4 lascia una voce in meno**: *«la memoria del DB va rettificata
> su `terne_pronte` e `riaperto_il`»* — controllata oggi, **non contiene né
> l'una né l'altra**. I due residui inesistenti non si autoconfermeranno,
> perché non sono scritti da nessuna parte. Voce chiusa.
>
> 🔴 **Cosa resta davvero aperto, dopo questo giro** — tutte e tre cose che si
> fanno **a video o sui dati**, non a tavolino:
>
> 1. le **5 prove** del copione V1 (più il guasto/ripristino, che sono `UPDATE`
>    ⛔ da eseguire a mano: non le fa l'agent);
> 2. **DL-23 `CONFERMATO`**: costruire ordine da 10 a `CONFERMATO` + DDT di 4, e
>    verificare che il serbatoio mostri il **pieno**;
> 3. l'**area RESI** guardata a video — oggi verificabile sul motivo
>    `RICONSEGNA_NON_ESEGUITA` (`RESO0005123`); per il gemello serve prima un
>    reso con accredito dovuto, che **va ricostruito**.
>
> ✅ **E la quarta è caduta in giornata**: il migrate di `20260831-70` (DB-R2)
> è stato **applicato** alle 21:36, e il pgTAP rifatto come applicazione dà
> 14/14. ⇒ **Il blocco «AL TEAM DB» non lascia più niente**: restano solo le
> tre voci a video qui sopra.
>
> ---
>
> ## 📌 CODA DI DB-R2 — il fatto arriva a video con un nome (BE+FE, 2026-08-31)
>
> `LOTTO_RIAPERTO` ha portato a galla un difetto che **non era suo** e che
> riguardava tutti e sei i codici evento: il catalogo dichiara un indirizzo i18n
> (`config.eventi_dominio.etichetta_key`) che **non leggeva nessuno**. La vista
> non lo esponeva, il backend non lo selezionava, e le sei chiavi
> `config.eventi_dominio.*` non esistevano nei `locales`. La scheda **Storia**
> rende `cosa` verbatim, e per le righe `EVENT_LOG` `cosa` **è il codice**: la
> riga nuova sarebbe comparsa a video come `LOTTO_RIAPERTO`.
>
> ⚠️ **Non era una regressione del push**: era un contratto *emesso, trasportato
> e non consumato* — la stessa forma di `ui_action`, e la ragione per cui
> [api.md](../api.md) prescrive di **verificare che il client la legga** prima di
> dichiarare fatta una capability. L'evento nuovo l'ha solo reso visibile.
>
> **Chiuso lo stesso giorno**, tre pezzi:
>
> * **BE** — `_list_giornale` porta `etichetta_key` con un `LEFT JOIN` su
>   `config.eventi_dominio` ristretto a `registro = 'EVENT_LOG'` (sugli altri tre
>   registri `cosa` è già una frase, non un codice). ⚠️ Il JOIN sta nella SELECT
>   finale e **non** nella CTE `tutte`, che alimenta anche i conteggi: oggi non
>   potrebbe moltiplicare (`codice` è la PK), ma la posizione lo rende vero per
>   costruzione e non per coincidenza con un indice. ⛔ Nessun filtro su
>   `obsoleto_dal`: il diario è append-only e le righe vecchie devono restare
>   leggibili. Un lettore solo, quindi **entrambi** gli endpoint — fattura e
>   lotto — l'hanno preso in un colpo;
> * **FE** — i **tre** punti che rendono, trovati cercandoli e non deducendoli
>   ([[feedback_bb_legge_non_trasporta]]): la colonna della scheda Storia del
>   **lotto**, quella della **fattura**, e il banner dell'**errore vivo** in
>   testata alla fattura — che è una riga dello stesso giornale, e senza il terzo
>   punto lo stesso fatto avrebbe avuto due nomi a due centimetri di distanza.
>   Tutti e tre con il BB `labelOrCode`, ripiego fail-visible sul codice grezzo;
> * **i18n** — le sei chiavi in `it.json` e `en.json`.
>
> ✅ **Provato sul database vero, non solo compilato** — 1839 test verdi e lint
> pulito non dicono niente su una `SELECT`. Chiamata reale al lettore sul lotto
> **6260**: la riga `EVENT_LOG` `PIPELINE_ERROR` esce con
> `config.eventi_dominio.pipeline_error`, e le righe `FATTURA_LOG` / `LOTTO_LOG`
> / `TASK_RUN` con `None`, come il ramo prevede.
>
> ⛔ **E una misura intermedia era falsa, salvata da un controllo strutturale.**
> `SELECT count(*) FROM vendite.event_log` rispondeva **0**, e stavo per
> leggerlo come «il diario è vuoto». `vendite.event_log` **ha la RLS**: senza i
> cinque GUC dell'identità quello zero è **fail-closed**, non un dato. Col
> contesto completo le righe ci sono ([[feedback_rls_conteggio_zero_non_e_un_dato]]).
>
> ---
>
> ## 📌 AL TEAM DB — residui da vedere (2026-08-31)
>
> 🔵 **DB-R3 · il `COMMENT` di `vw_dash_aperto_documenti` dichiara 4 aree, la
> vista ne restituisce 5** (aperta il 2026-08-31). Il commento dice *«stock dei
> documenti … delle 4 aree (PREVENTIVI/ORDINI/OFFERTE/CONTRATTI — no COMMESSE)»*;
> misurato col contesto operatore: `CONTRATTI 15 · DDT 4 · OFFERTE 2 · ORDINI 60
> · PREVENTIVI 76`. L'area **DDT** è entrata il 2026-07-18 (DL-21) e il commento
> non l'ha seguita. ⚠️ Non è un dettaglio di prosa: quel `COMMENT` è la **fonte**
> della pagina `dbzero` auto-generata, quindi l'errore si propaga a chiunque
> legga la doc invece della vista. I due doc API gemelli avevano lo stesso
> residuo e sono già corretti (vedi il blocco «documenti incongruenti» in testa).
>
> ✅ **Entrambe chiuse in giornata**: DB-R1 corretta nella scheda manuale, DB-R2
> decisa da Tid («sì, si registra»), scritta e **applicata** — changeSet
> `20260831-70`, EXECUTED alle 21:36.
>
> ⛔ **Non c'è un brief separato per queste voci, di proposito** (decisione di
> Tid): stanno qui, in testa al documento che le ha trovate. Nessuna è urgente,
> nessuna richiede una migrazione; sono **documentazione che dice il falso**, ed
> è la categoria che costa di più — chi la legge non ha modo di accorgersene.
>
> **DB-R1 · 🔴 `fn_riporta_lotto_a_draft`: la doc manuale contraddice la
> funzione viva.** Trovato il 2026-08-31 leggendo
> [fn_riporta_lotto_a_draft.md](../../dbzero/vendite/manual/fn_riporta_lotto_a_draft.md)
> per capire cosa significhi «lotto riaperto» (domanda di Tid). Due punti:
>
> | Dice la doc (review 03-08-2026) | Fa la funzione oggi |
> | --- | --- |
> | *«Le esecuzioni dei task (`fatturazione_lotti_task_runs`) **non vengono toccate**… nessuno le consulta per decidere se rifare un passo»* | le **chiude ad `ANNULLATO`** (changeSet `20260803-12`) |
> | *«Ritorna una riga con **cinque** contatori»*, poi li elenca | ne ritorna **sei**: c'è anche `annullati_task_run` |
>
> ⭐ **E la premessa smentita è quella che regge il ragionamento**, non un
> dettaglio: la doc motiva il «non si toccano» con *«nessuno li consulta»* —
> misurato il 2026-08-03 — e il changeSet dello **stesso giorno** dimostra il
> contrario, col motivo scritto nel corpo della funzione:
>
> > *«RD-6: 🔴 i task_run si chiudono ad ANNULLATO, altrimenti
> > `fn_resolve_lotto_task_execution_mode` li vede COMPLETATO e risponde SKIP:
> > **il lotto riaperto rilancia a vuoto**.»*
>
> ⚠️ Quindi la doc non è solo incompleta: **spiega una scelta con un fatto che
> è stato confutato**, e chi la legge impara una cosa falsa sul motore
> dell'esecuzione. È la stessa forma del §14.4 — *una frase che dichiara chiuso
> ciò che è aperto e una che dichiara aperto ciò che è chiuso costano uguale*.
>
> ✅ **CORRETTA il 2026-08-31, in giornata.** La scheda manuale è stata riscritta
> su entrambi i punti, con la rettifica **dichiarata** invece che silenziosa
> (chi ricorda la frase vecchia deve poter capire perché è cambiata):
>
> * il punto sui task_run dice ora che vengono **chiusi ad `ANNULLATO`** — tutti
>   quelli attivi del lotto, non solo quelli dello step DRAFT — con il motivo
>   RD-6 per esteso, il richiamo a `fn_cancel_lotto_task_run` (motivo
>   `ritorno_a_draft`) e le due avvertenze del corpo: che **non si cancellano**,
>   e che `attivo = false` **non basterebbe**, perché quella SELECT non filtra
>   su `attivo`;
> * l'Output dice **sei** contatori e include `annullati_task_run`;
> * la riga di review passa da `03-08-2026` a `31-08-2026`.
>
> ⭐ **Ed è rimasto in piedi il pezzo di verità della frase vecchia**, che era
> l'unica cosa da salvare: «registro storico» resta vero, perché le corse **non
> si cancellano** — si chiudono con un esito e il giro nuovo apre
> `tentativo = MAX+1`. La frase sbagliata non era «è un registro storico»: era
> il *«nessuno le consulta»* usato per motivare l'inazione.
>
> 📌 Verificato su `databasechangelog`, non sul brief: `20260803-12-riporta-lotto-annulla-task-runs`
> risulta **EXECUTED** il 2026-08-03 alle 20:42 — dopo `20260803-08` (creazione)
> e `20260803-09`, e prima di `20260804-05`.
>
> **DB-R2 · 🟡 nessun registro di evento sulla riapertura.** `fn_riporta_lotto_a_draft`
> non scrive in nessuno dei quattro registri di `script.vw_giornale_entita`
> (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, `FATTURA_LOG`). Nella scheda **Storia**
> del lotto la riapertura si legge **solo di rimbalzo**, dai task_run passati ad
> `ANNULLATO`. ⚠️ Non è un difetto dichiarato — è una **domanda**: se «riportato
> in lavorazione» meriti una riga propria nel giornale. Chi indaga su un lotto
> oggi deve dedurla; e l'atto cancella documenti, che è la categoria di gesto
> che di solito una riga se la merita. **Decisione di Tid, non mia.**
>
> ✅ **DECISA, SCRITTA E APPLICATA il 2026-08-31: sì, si registra.** Decisione
> di Tid. ✅ **Applicato** dal suo migrate: `databasechangelog` dà
> `20260831-70-…` **EXECUTED** alle **21:36:10**, e `config.eventi_dominio`
> contiene `LOTTO_RIAPERTO`. La funzione viva cita RD-7.
>
> | | |
> | --- | --- |
> | changeSet | `20260831-70-update-fn-riporta-lotto-a-draft-giornale-riapertura` (numerazione da −70 su indicazione di Tid: fino a −69 c'erano altri cantieri) |
> | seed | append a `80_data/sql/config/eventi_dominio.csv` — nessun `INSERT` a parte, lo ri-legge il mirror `runOnChange` `20260822-55` |
> | pgTAP | `test-riporta-lotto-a-draft-v1.sql`, da 11 a **14** test |
> | doc | scheda manuale aggiornata (RD-7 + la sezione sul perché di quel registro) |
>
> **La forma**: una riga `LOTTO_RIAPERTO` in `vendite.event_log`, scritta con
> `vendite.fn_log_event`, severity **WARN**, e nel `payload` lo stato fiscale di
> partenza più cinque contatori.
>
> ⭐ **Il registro non era una scelta fra pari, e la ragione che decide non è
> quella che sembrava.** I candidati erano due. Le prime due differenze sono
> quelle attese: `fatturazione_lotti_log` ha la colonna `disabilitato` (una riga
> che si può spegnere) ed è cercabile solo dal testo, mentre `event_log` è
> append-only per trigger e porta un codice a catalogo. Su un atto che
> **cancella documenti** contano entrambe.
>
> 🔴 **Ma la terza è di comportamento, non di leggibilità, e da sola bastava.**
> `fn_list_lotto_segnalazioni` compone le segnalazioni da `fatture_log` unito a
> `fatturazione_lotti_log`, e da `event_log` legge **soltanto** l'ancora del giro
> corrente (`PIPELINE_STARTED`). Scrivere la riapertura nel registro delle
> segnalazioni l'avrebbe fatta entrare nel conteggio su cui si decide se
> l'avanzamento è ammesso: **un atto registrato sarebbe diventato un atto che
> blocca** — e su un lotto appena riaperto, cioè esattamente quando l'operatore
> deve poter ripartire. Verificato sul corpo della funzione, non per analogia.
>
> ⚠️ **WARN e non INFO**, e non è una sfumatura: la vista mappa già un task_run
> `ANNULLATO` a `WARN`, e la riapertura ne produce uno per ogni step. Con la
> causa a INFO, chi filtra per gravità vedrebbe otto corse annullate **senza il
> motivo per cui lo sono**. La gravità qui non risponde a «si è rotto qualcosa»
> ma a «quanto deve saltare all'occhio di chi indaga».
>
> ✅ **E non introduce un ramo di fallimento** — la domanda giusta davanti a un
> `INSERT` aggiunto a un'operazione che oggi riesce. Il giornale rifiuta una riga
> solo quando non sa dire di chi è; qui lo sa **per costruzione**: `LOTTO` è un
> tipo giornalabile a catalogo, il perimetro si copia da
> `fatturazione_lotti.emittente_soggetto_ruolo_id` che è **NOT NULL**, e
> l'esistenza del lotto è già garantita dalle precondizioni. Proprietà dello
> schema, non scommessa sui dati di oggi.
>
> ⚠️ **Un buco di presidio, dichiarato invece che scoperto dopo.**
> `LOTTO_RIAPERTO` è il **primo codice evento scritto dal database** e non dal
> backend. Il rubinetto CI dei codici evento scansiona il **Python** — e la sua
> intestazione lo motiva così: *«il codice evento lo scrive il backend»*, e una
> vista su `pg_proc` tornerebbe *«vuota per sempre»*. Quella premessa oggi
> scade. Il codice è dichiarato a catalogo, quindi la spia dei dati
> (`dbops.vw_eventi_non_dichiarati`) resta pulita; ma il verso **«deprecato a
> catalogo e ancora scritto»** su questo codice non lo vede nessun cancello.
> ⇒ Coperto con il **test 14** del pgTAP, che è strutturale e gira sempre.
> ⇒ Se un giorno il DB scriverà un secondo codice evento, la sede giusta non è
> un altro test: è il complemento su `pg_proc` che allora non sarebbe più vuoto.
>
> 📋 **Provato prima di fermarsi**, e nei due versi:
>
> * il changeSet è stato eseguito **dall'SQL estratto dallo YAML** (non da una
>   copia riscritta), in `BEGIN`/`ROLLBACK`: su un lotto vero — 8688
>   `LTF-0007949`, EMESSA — la riga esce con `WARN`, emittente derivato, `tx_id`
>   e `cleanup_at` valorizzati, e `payload` con `stato_precedente: EMESSA`,
>   `deleted_fatture: 1`, `annullati_task_run: 8`. E si **vede** in
>   `script.vw_giornale_entita`, in testa, alla stessa gravità dei task_run
>   `ANNULLATO` che l'atto ha appena prodotto — che era l'argomento del WARN,
>   ora visibile;
> * ⭐ **prova di mutazione sul pgTAP**: senza la modifica i tre test nuovi sono
>   **rossi** (11, 12, 14) e gli altri undici restano verdi; con il changeSet
>   applicato in transazione sono **14 su 14**. I test non sono verdi per
>   sottrazione.
>
> ~~⚠️ Il pgTAP è girato da owner: la corsa RLS-reale va rifatta dopo
> l'apply.~~ ✅ **Rifatta dopo l'apply, come applicazione** (`zeroerp_app`,
> RLS attiva, il default del runner): **14 su 14**. L'argomento fatto in
> anticipo ha tenuto — la fixture sceglie il lotto **sotto RLS**, quindi
> l'emittente della riga di giornale è nel perimetro dell'operatore per
> costruzione, e la `WITH CHECK` su `event_log` non poteva respingerla.
>
> 📌 **Residuo FE, piccolo e non bloccante**: `etichetta_key`
> `config.eventi_dominio.lotto_riaperto` non ha ancora una chiave i18n nel
> frontend — **come nessuno degli altri cinque codici**, che sono lì dal 22-08.
> Non è un debito che questa voce apre: è quello che eredita.

> ℹ️ **Il §14 non sposta questa riga.** È la ricognizione dei residui BE che il
> team DB aveva consegnato «fuori da questa linea»: riverificati contro il
> codice, **nessuno dei quattro richiede lavoro BE**. Non toglie né aggiunge
> nulla a «cosa resta», che è e rimane il §13. Quel che il §14 lascia sono due
> voci di *registro*, non di sviluppo (§14.4).
>
> **Origine**: [piano-residui-orchestrazione-e-cruscotti-vendite.md](piano-residui-orchestrazione-e-cruscotti-vendite.md) §1 (R-1)
> ← [analisi-orchestrazione-vendite-simmetrie.md](analisi-orchestrazione-vendite-simmetrie.md) §B/§B.1.
>
> **Perimetro**: solo backend Python. **Nessuna azione DB** (verificato §5.2), **nessuna
> dipendenza nuova**, nessun frontend.

---

## 1. Le due cose da fare, in una riga ciascuna

1. **Il fix** — quando il pull da commessa emette 7 commesse su 10, deve dire *«giro finito,
   3 rimaste indietro»* invece di dire *«fatto»*. Oggi dice «fatto» e al rilancio dello step
   quelle 3 vengono saltate per sempre.
2. **Il BB** — il telaio che sta intorno a quel ciclo (scopri → isola → aggrega → logga) è
   scritto tre volte a mano, in tre modi diversi. Va estratto una volta sola in
   `apps/core/services/`, adottandolo **contestualmente** in più di un sito (regola del 2).

L'ordine non è negoziabile: **prima il fix, poi l'estrazione**. Il fix cambia un
comportamento; l'estrazione deve essere a parità. Mescolarli renderebbe ambigua qualunque
regressione.

---

## 2. Ricognizione — i tre siti reali (correzione dell'analisi originale)

L'analisi di giugno accoppiava «push» e «pull». Rileggendo il codice per questo brief:
**i siti sono tre, e i due accoppiati allora non sono lo stesso livello.**

| Sito | File | Itera su | Discovery | Isolamento | Aggregazione | Log |
|---|---|---|---|---|---|---|
| **A** | `commesse_push_orchestrator.py` `_run_locked` | **handler** | `_resolve_handlers` | `try/except` — **niente savepoint** | `_compute_stato` → `COMPLETATO`/`PARZIALE`/`ERRORE` | ⭐ *(rev. 2026-08-22)* `start_push_run` in testa + `close_push_run` in coda. ⛔ Niente piu' `PUSH_STARTED`/`PUSH_COMPLETED` su `event_log` (BE-3a: un giro non ha un emittente) e niente piu' `log_push_run` (la funzione DB e' stata DROPpata) |
| **B** | `commesse_source_handlers.py` `BaseSourceHandler._process_rows` | **righe sorgente** | `fetch_pushable_rows` | `transaction.atomic()` per riga | contatori `created/updated/skipped` + `errors[]` su `HandlerResult` | `logger.exception` per riga |
| **C** | `pipeline_step_executor.py` `_handle_pull_attivita_da_commessa_task` | **commesse** | `list_commesse_emittibili` | `transaction.atomic()` per commessa | `errors[]` + raise **solo** se falliscono tutte | `event_log` + `PipelineErrorLogger` per item |

**Conseguenze di lettura:**

- Il **gemello vero di C è B**, non A: stessa forma esatta (lista scoperta → savepoint per
  item → conteggi/errori). A sta **un livello sopra**: itera su handler che sono *essi
  stessi* fan-out, e per questo non isola in transazione — lo fanno gli handler dentro di sé.
  A è un **aggregatore**, non un fan-out.
- ⚠️ **B ha una coda batch fuori dal ciclo** (`batch_upsert_attivita` + risoluzione id +
  esclusione delle `chiavi_fallite`). Il BB **non deve inghiottirla**: restituisce gli esiti
  per item e il chiamante fa la sua coda. Un BB che pretendesse di gestire anche il batch
  diventerebbe il ciclo di B con un altro nome.
- **Il vocabolario a tre stati esiste già** — `_compute_stato` di A produce
  `COMPLETATO`/`PARZIALE`/`ERRORE` da sempre. Il BB **non inventa una policy**: porta a C la
  terza parola che A ha già e che a C manca. È l'argomento più forte per fare entrambe le
  cose insieme.
- **C'è un quarto parente**, `QueueDrainEngine` (`core/services/coda_lavori/drain_engine.py`):
  stessa forma ma su **coda persistente** (claim, ownership, backoff, ritentativi). Vedi D-1.

---

## 3. Decisioni di disegno

Tutte chiuse con Tid il **2026-08-09**.

| # | Domanda | Stato | Scelta |
|---|---|---|---|
| **D-1** | Il fan-out converge col `QueueDrainEngine`? | ✅ **DECISA** | **NO — due astrazioni, confine dichiarato** |
| **D-2** | Il pull deve segnalare il parziale? | ✅ **DECISA** | **SÌ**, via `TaskEsitoParziale` |
| **D-3** | Il run log entra nel BB? | ✅ **DECISA** | **SÌ, come protocollo minimo opzionale** |

**D-1 — perché NON si converge.** Il drain engine possiede claim, ownership,
`run_after` con backoff esponenziale e la nozione di errore *terminale*: tutta roba che
esiste perché la coda è **durevole** e l'item **sopravvive** al run. Qui la lista è
**effimera**: la scopri, la consumi, e se qualcosa resta indietro lo ritrovi alla prossima
scoperta (che è idempotente). Farne un `QueueBackend` in-memory significa trascinare tre
concetti inutili dentro il caso semplice. La contropartita è che restano due moduli: si paga
con **una riga di doc in ciascuno** che dice quando si usa l'uno e quando l'altro (F6), e con
la voce nel catalogo BB. ⚠️ Quel confine scritto **è** il deliverable della decisione: senza,
fra sei mesi qualcuno riaprirà la stessa domanda davanti a due motori simili.

**D-2 — dettaglio esecutivo in §5.**

**D-3 — perché sta dentro, ma leggero.** Il log del run è **la parte che ci
si dimentica di replicare**: A lo fa bene (start/end + tabella dedicata), B lo fa solo con
`logger.exception`, C lo fa con `event_log` + logger di dominio. Se il BB lo lascia fuori, il
quarto chiamante lo riscriverà a modo suo e saremo al punto di partenza. Ma se lo assorbe
tutto, deve conoscere `event_log`, `commesse_push_log` e `PipelineErrorLogger` — cioè il
dominio. Via d'uscita: un **protocollo a tre metodi**, opzionale (`None` = non loggare),
implementato dai chiamanti:

```text
class FanOutRunLogger(Protocol):
    def start(self, *, totale: int) -> None: ...
    def item_failed(self, *, item, exc: Exception, indice: int) -> None: ...
    def end(self, *, esito: FanOutEsito) -> None: ...
```

Il BB sa *quando* chiamare; il chiamante sa *dove* scrivere. Nessuna dipendenza di `core`
verso `vendite`.

---

## 4. La forma proposta del BB

**File**: `backend/apps/core/services/fan_out.py` (header standard + `# Scopo:` per funzione,
come da AGENTS).

```text
ESITO = COMPLETATO | PARZIALE | ERRORE        # stesse tre parole di _compute_stato

@dataclass
class FanOutItemErrore:
    indice: int
    item: Any
    messaggio: str          # f"{type(exc).__name__}: {exc}"
    eccezione: Exception    # ⭐ dal 2026-09-17 (regola del 2, ok Tid): l'eccezione
                            #    INTERA — i due consumatori con esito per riga
                            #    (archiviazione code, righe da rate) la tenevano in
                            #    dizionari laterali; vedi catalogo BB backend

@dataclass
class FanOutEsito:
    totale: int
    ok: int
    errori: list[FanOutItemErrore]
    esito: str              # COMPLETATO | PARZIALE | ERRORE

    @property
    def parziale(self) -> bool
    @property
    def tutti_falliti(self) -> bool   # ⛔ tolto il 2026-09-07, vedi §5.1

def run_fan_out(
    items,                          # iterabile GIA' scoperto dal chiamante
    process,                        # callable(item) -> None ; solleva per fallire
    *,
    isola_in_transazione=True,      # savepoint per item (transaction.atomic)
    run_logger=None,                # protocollo D-3, opzionale
) -> FanOutEsito
```

**Regole del contratto** (vanno nel docstring, sono la parte che si dimentica):

- La **discovery resta fuori**: il BB riceve una lista già risolta. Il chiamante conosce i
  suoi filtri di perimetro; il BB no, e non deve.
- `process` comunica il fallimento **sollevando**. Nessun valore di ritorno interpretato:
  un `False` ambiguo è il modo in cui questi telai marciscono.
- **Lista vuota → `COMPLETATO`**, non `ERRORE`. «Niente da fare» è un successo. ⚠️ Nota che
  `_compute_stato` di A oggi fa il contrario (`if not results: return "ERRORE"`) — vedi la
  trappola T-3 in §8.
- Il BB **non decide** cosa fare dell'esito: lo restituisce. È il chiamante che sceglie se
  sollevare, marcare un `task_run` o scrivere un report.
- Nessuna concorrenza, nessun retry, nessun claim: quelli stanno nel `QueueDrainEngine` (D-1).

---

## 5. Il fix del pull (Fase 1) — dettaglio

### 5.1 Comportamento

| Casistica | Oggi | Dopo |
|---|---|---|
| 10 su 10 ok | `task_run` COMPLETATO | invariato |
| 7 ok, 3 ko | `task_run` **COMPLETATO** → al rilancio **SKIP**, le 3 non si ritentano | `task_run` **ERRORE senza raise** → al rilancio **RESUME** |
| 0 su 10 ok | `raise E_PULL_COMMESSA_ALL_FAILED`, lo step si ferma | **invariato** — vedi sotto. 🔴 **Superato il 2026-09-07**, vedi la nota |
| lista vuota | COMPLETATO | invariato |

**Perché l'all-fail continua a sollevare** e non diventa anch'esso un parziale: se nessuna
commessa è stata emessa, proseguire con i task successivi costruirebbe un **lotto vuoto**.
Lì fermarsi è la cosa giusta. La regola diventa leggibile in una riga: *nessuno passa →
fermati · qualcuno passa e qualcuno no → prosegui ma non dichiarare chiuso · tutti passano →
chiuso*.

> ### 🔴 Superato il 2026-09-07 — l'all-fail NON solleva più (P-5)
>
> Il ragionamento qui sopra sbagliava un passaggio, e il difetto che ne è nato si
> è visto solo un cantiere dopo: **il `raise` faceva rollback dell'intero step**,
> quindi si portava via anche le marcature d'esito dei documenti caduti, appena
> scritte. Il caso peggiore era l'unico che non lasciava traccia — il paradosso
> classico: funziona quando va male a metà e tace quando va male del tutto.
>
> ⭐ **La confusione era fra due cose diverse**: *fermare la catena* e *strappare
> gli appunti*. Le faceva lo stesso gesto. A fermare la catena non serve
> l'eccezione: il passo scrive una segnalazione **critica per ogni commessa
> caduta**, quindi al giro dopo `blocks_next_step` rifiuta l'avanzamento e il
> driver esce con `BLOCCATO_CRITICITA`. Il lotto vuoto non nasce lo stesso.
>
> ⇒ Il ramo non è stato modificato, è stato **tolto**: i due casi sono diventati
> lo stesso codice, e la regola in una riga si accorcia — *qualcuno non passa →
> segna e fermati · tutti passano → chiuso*.
> `E_PULL_COMMESSA_ALL_FAILED` è ritirato a catalogo (`obsoleto_dal`).
> Decisione di Tid, 2026-09-06. Dettaglio: `brief-db-esito-gruppo-lotto` §14 e §20.

### 5.2 Codice errore — nessuna azione DB

Si riusa **`E_PULL_COMMESSA`**, già seedato (`config/codici_errore.csv` riga 470, policy
`DATO_ERRATO`; messaggio in `config/messaggi_errore.csv` riga 511; presente in
`error_policies_generated.py`). È esattamente il criterio applicato dallo snapshot
indirizzi, che riusa `E_INDIRIZZO_FATTURA_MANCANTE` perché è *«il motivo dominante reale del
fallimento per-fattura, non un codice sintetico nuovo»*.

→ **Niente brief al team DB, nessun prerequisito, nessuna attesa.** Se in review emergesse
la necessità di un codice dedicato, quello **sì** diventerebbe una richiesta al team DB e il
lavoro si fermerebbe lì (memoria `feedback_db_actions_passaggio_team`).

### 5.3 Forma

`_handle_pull_attivita_da_commessa_task` cambia firma di ritorno da `None` a
`TaskEsitoParziale | None` — la stessa dei due handler che già lo fanno. L'executor lo
gestisce già (`pipeline_step_executor.py` righe 362-374): **nessuna modifica al chiamante**.

`meta` del `TaskEsitoParziale` porta: `task`, `totale`, `ok`, `falliti`, e i primi N
`commessa_id` falliti (allineato al `errors[:5]` già usato nel raise all-fail).

---

## 6. Piano di sviluppo

| Fase | Contenuto | Esito atteso | Dipende da |
|---|---|---|---|
| **F0** | Conferma **D-1** e **D-3** con Tid | ✅ **FATTA** (2026-08-09): due astrazioni distinte · run logger dentro come protocollo opzionale | — |
| **F1** | **Fix pull esito parziale** + i suoi test | comportamento nuovo isolato e provato, a BB non ancora esistente | F0 ✅ |
| **F2** | **BB `run_fan_out`** in `core/services/fan_out.py` + test unitari del solo BB (nessun chiamante ancora convertito) | BB verde in isolamento | F0 ✅ |
| **F3** | **Adozione in C** (pull) — il ciclo di `_handle_pull_...` diventa una chiamata a `run_fan_out`, il `run_logger` incapsula `PipelineErrorLogger` | pull a parità di comportamento **rispetto a F1** | F1 + F2 |
| **F4** | **Adozione in B** (`_process_rows`) — solo il ciclo per-riga; la **coda batch resta fuori**, invariata | push handler a parità esatta | F2 |
| **F5** | **Valutazione di A** — l'orchestrator adotta il BB solo se `isola_in_transazione=False` gli calza senza forzature; **altrimenti resta com'è** e lo si dichiara nel docstring | decisione motivata, non adozione per simmetria | F3 + F4 |
| **F6** | Doc: catalogo BB backend + riga di confine in `fan_out.py` e in `drain_engine.py` (D-1) + aggiornamento di questo brief e chiusura di R-1 nel piano residui | R-1 chiuso | F3..F5 |

**F3 e F4 sono la regola del 2**: l'estrazione è legittima solo se in quello stesso
intervento **entrambe** vengono convertite. Se una delle due si rivelasse ostica, non si
tiene il BB con un solo chiamante — si torna indietro e si ridiscute (memoria
`feedback_regola_del_2_estrai_bb`).

**F5 è deliberatamente condizionale.** A è un livello diverso (§2): forzarlo dentro il BB per
avere «tre adozioni» sarebbe astrazione a comando. Se non calza, il risultato di F5 è **una
riga di documentazione**, non del codice.

---

## 7. Test

| Fase | Cosa si prova |
|---|---|
| F1 | pull con 3 su 10 falliti → ritorna `TaskEsitoParziale` con `E_PULL_COMMESSA` e `meta` popolata · pull con 10/10 ok → ritorna `None` · pull con 0/10 ok → ~~solleva `E_PULL_COMMESSA_ALL_FAILED`~~ **ritorna `TaskEsitoParziale` dal 2026-09-07 (P-5)** · lista vuota → `None`, nessun errore |
| F1 | **executor**: `TaskEsitoParziale` → `fail_lotto_task_run` con codice/messaggio/meta e **nessuna eccezione propagata**; ritorno `None` → `complete_lotto_task_run`. ✅ **Rettifica 2026-08-09**: contrariamente a quanto scritto nella prima stesura di questo brief, il ramo **è già coperto** — dai test 28/29 (snapshot) e 32/33 (scadenze) di `test_pipeline_step_executor.py`. La classe non compare per nome nei test, il suo comportamento sì. Restano da scrivere i test **specifici del pull**, non quelli del meccanismo |
| F2 | `run_fan_out`: tutti ok → `COMPLETATO` · misto → `PARZIALE` con indici e messaggi giusti · tutti ko → `ERRORE` · **lista vuota → `COMPLETATO`** · `isola_in_transazione=False` non apre transazioni · `run_logger` riceve `start`/`item_failed`×N/`end` nell'ordine · un'eccezione **dentro** il run_logger non affonda il giro |
| F3/F4 | i test esistenti di `test_pipeline_step_executor.py` e `test_commesse_source_handlers.py` passano **senza modifiche di aspettativa** (a parte quelle di F1). Se un test va cambiato in F3/F4, non è un refactor: è un cambio di comportamento non dichiarato |

Regole CI: `unittest.TestCase` con mock, mai `django.test.TestCase` (nessun test deve
dichiarare un database — vedi AGENTS, il vincolo dei 3 test e2e opt-in).

---

## 8. Trappole note

- **T-1 — Il savepoint annidato.** In F4 il ciclo di B è già dentro `transaction.atomic()`
  per riga; se il chiamante avvolgesse a sua volta, si otterrebbero savepoint annidati.
  Verificare che `run_fan_out` apra **un solo** livello e che nessun chiamante lo raddoppi.
- **T-2 — La coda batch di B.** `batch_upsert_attivita` gira **dopo** il ciclo e ha una sua
  logica di errori (`chiavi_fallite` che il ponte di approvazione deve escludere, difetto
  già corretto in review il 2026-07-23). Il BB non la tocca. Se dopo F4 gli `errors[]` del
  batch finissero mescolati a quelli del ciclo, è una regressione.
- **T-3 — Lista vuota: due semantiche opposte.** Il BB proporrà `COMPLETATO`; `_compute_stato`
  di A oggi risponde `ERRORE` (`if not results`). Sono **corretti entrambi nel proprio
  contesto**: per A «nessun handler risolto» è un errore di configurazione, per un fan-out
  «nessun item da lavorare» è un successo. In F5 la differenza va **dichiarata**, non
  appianata di nascosto: appianarla cambierebbe lo stato scritto in `commesse_push_log`.
- **T-4 — Il parziale che diventa rumore.** Con il fix, un lotto con anche una sola commessa
  fallita mostra uno step in ERRORE nel cockpit. È **voluto** (è il punto), ma va guardato
  in-app: se sui dati veri il parziale fosse la norma e non l'eccezione, il problema non è la
  segnalazione — sono i dati, e allora si apre un'altra analisi.
- **T-5 — `dry_run`.** Il pull esce **prima** del ciclo se `dry_run` (`if dry_run: return`).
  Il fix non deve spostare quel ritorno né far comparire esiti parziali in dry-run.

---

## 9. Definizione di «fatto»

- Il pull chiude il `task_run` in ERRORE su rifiuto parziale, **senza sollevare**, e al
  rilancio dello step le commesse fallite vengono **riprovate**.
- `run_fan_out` esiste in `core/services/`, con **almeno due** chiamanti reali convertiti
  (C e B); `_compute_stato`/`errors[]` non sono più logica duplicata dove il BB è adottato.
- Il ramo `TaskEsitoParziale` dell'executor ha test propri (prima non ne aveva).
- Catalogo BB backend aggiornato; confine BB ↔ `QueueDrainEngine` scritto in entrambi i file.
- Suite `apps.vendite` + `apps.core` verde, smoke pipeline eseguito.
- Questo brief in `work-done`, R-1 chiuso nel piano residui.

---

## 10. Cosa NON si fa

- **Niente DB**: nessun codice errore nuovo, nessuna migration, nessun trigger (§5.2).
- **Niente ritentativi automatici** nel BB: il RESUME al rilancio è già il meccanismo di
  ripresa: aggiungerne un secondo dentro il fan-out creerebbe due politiche di retry.
- **Niente parallelismo**: il fan-out resta sequenziale. Nessun sito lo chiede.
- **Nessuna modifica al frontend**: il cockpit già rende gli step in ERRORE.
- **Non si tocca l'all-fail del pull** (§5.1), né la coda batch di B (T-2), né la discovery
  di nessuno dei tre siti.

---

## 11. Consuntivo (2026-08-09) — cosa è stato fatto e cosa si è scostato dal piano

### 11.1 Fasi

| Fase | Esito |
|---|---|
| **F0** decisioni | ✅ D-1 due astrazioni · D-2 pull sistemato · D-3 run logger dentro, opzionale |
| **F1** fix pull | ✅ `_handle_pull_attivita_da_commessa_task` ritorna `TaskEsitoParziale | None`; codice **riusato** `E_PULL_COMMESSA`; nessuna azione DB. **4 test nuovi** (parziale / tutte ok / tutte fallite / dry-run) |
| **F2** BB | ✅ `apps/core/services/fan_out.py` — `run_fan_out`, `FanOutEsito`, `FanOutItemErrore`, `FanOutRunLogger`. **14 test** in `apps/core/tests/services/test_fan_out.py` |
| **F3** adozione pull | ✅ il ciclo è una chiamata a `run_fan_out` + `_PullCommesseRunLogger` (i motivi per-commessa restano sui log di lotto) |
| **F4** adozione `_process_rows` | ✅ ciclo per-riga sul BB; la **coda batch è rimasta fuori**, invariata |
| **F5** valutazione sito A | ✅ **scartato con motivazione scritta** nel docstring di `_compute_stato` — nessun codice, come previsto |
| **F6** doc | ✅ catalogo BB backend (nuova sezione «Fan-out isolato») + confine dichiarato in `fan_out.py` **e** in `drain_engine.py` |

### 11.2 Scostamenti, tutti dichiarati

1. **Cinque test hanno cambiato il bersaglio della `@patch`**, non le asserzioni.
   `apps.vendite.services.pipeline_step_executor.transaction` →
   `apps.core.services.fan_out.transaction`, perché il savepoint si è **spostato** dentro
   il BB. Le verifiche sono identiche prima e dopo: è la giuntura del test che segue il
   codice, non un'aspettativa che cede. Nessun altro test è stato toccato — i 59 di
   `test_commesse_source_handlers` passano invariati.

2. **`_process_rows`: la coda del batch ora si riempie solo per le righe atterrate.**
   Prima `pending_inputs.append(...)` girava **dentro** il savepoint: una riga caduta a
   metà espansione lasciava i suoi input in coda all'upsert, cioè scriveva per una riga
   che era stata annullata. La regola era già scritta nel file per `commesse_ids` («un
   rollback non deve produrre id fantasma»); ora vale per entrambe. **È una correzione,
   non un refactor** — piccola, della stessa famiglia del difetto principale.

3. ~~**`commessa_cache` è rimasta DENTRO il savepoint**~~ → ✅ **CHIUSO nella stessa
   giornata** (Tid: «direi di chiudere questo residuo»). Vedi **§12**.

4. **Il gate dry-run del pull è a due cinture, e quella che conta non è nell'handler.**
   `_run_task` esce in dry-run **prima** di invocare l'handler, quindi il
   `if dry_run: return None` interno non è il presidio primario: è la difesa che tiene se
   un domani l'handler venisse chiamato fuori da `_run_task`. Il test lo dice
   esplicitamente invece di far finta di provare il ramo sbagliato.

### 11.3 Rettifica alla prima stesura

La prima stesura di questo brief affermava che `TaskEsitoParziale` non avesse **nessun**
test. Falso: la classe non compare per nome nei test, ma il suo comportamento è verificato
dai test 28/29 (snapshot indirizzi) e 32/33 (genera scadenze) di
`test_pipeline_step_executor.py`, «nessuna eccezione propagata» compreso. Mancavano solo i
test **specifici del pull**, che F1 ha aggiunto.

### 11.4 Cosa resta

- **Validazione in-app** (Tid): un lotto con una commessa che fallisce deve mostrare lo
  step in **ERRORE** nel cockpit e, al rilancio, ritentare **quella** commessa. È la
  trappola T-4: se sui dati veri il parziale risultasse la norma e non l'eccezione, il
  problema non è la segnalazione — sono i dati, e si apre un'altra analisi.
- **Commit** (Tid): il lavoro è nel working tree, non committato.
- Dopo la validazione: questo brief in `work-done` e **R-1 chiuso** nel piano residui.

---

## 12. Chiusura del residuo `commessa_cache` (2026-08-09, stessa giornata)

### 12.1 Il difetto

`BaseSourceHandler._process_rows` tiene una **cache di lookup** delle commesse: righe
diverse che appartengono alla stessa commessa non tornano al database una seconda volta.
La cache veniva popolata **dentro** il savepoint della riga. Se la riga cadeva *dopo* quel
punto — per esempio su `link_sorgente` — il rollback annullava la commessa **nel database**
ma non toccava il dizionario Python. In cache restava l'id di una commessa inesistente, e
la **riga gemella successiva** lo riusava: fallendo anche lei, su un errore che il codice
si era procurato da solo.

### 12.2 Perché non bastava spostarla a valle

La correzione ovvia — registrare la cache a fine giro, come già si fa per `commesse_ids` e
per la coda del batch — l'avrebbe resa **inutile**: la cache serve alla riga *successiva*
dello stesso giro, e a fine giro non serve più a nessuno. Ogni riga sarebbe tornata al
database, cioè si sarebbe barattata una race rara con una regressione di performance certa.

Serviva un aggancio **durante** il giro, ma **dopo** il commit del singolo item.

### 12.3 La soluzione — `on_success` nel BB

`run_fan_out` accetta ora `on_success(item, risultato)`, chiamato a **savepoint già
rilasciato**: è la versione "durante il giro" di `esito.risultati`, e serve esattamente
quando l'item successivo dipende da ciò che ha prodotto il precedente.

Due scelte di contratto, entrambe scritte nel docstring:

- **`on_success` NON è protetto**: se solleva, il giro si interrompe. È voluto — il lavoro
  dell'item è già committato e non è più annullabile, quindi mascherare l'errore come «item
  fallito» direbbe una bugia. Lì dentro si mettono registrazioni in memoria, non lavoro
  rischioso.
- Resta **opzionale**: il pull non lo usa.

Nel chiamante, `_registra_riga` raccoglie ora tutte e tre le registrazioni — cache,
`commesse_ids`, coda del batch — in un punto solo, e `_lavora_riga` non tocca più nessuna
struttura Python condivisa.

⚠️ È un'aggiunta di superficie al BB **al primo utilizzo**, il modo classico in cui un
building block si gonfia. È stata accettata perché non è un parametro *per un chiamante*:
è la formulazione generale della regola che il BB già dichiarava — *«gli effetti
collaterali valgono solo se l'item è atterrato»* — di cui `risultati` era finora solo la
versione a fine giro.

### 12.4 Test

- **4 test nuovi sul BB** (`OnSuccessTests`): chiamato solo per gli item riusciti · chiamato
  **dopo il rilascio del savepoint** (verifica l'ordine reale: apri → lavora → rilascia →
  registra) · effetto visibile all'item successivo · l'eccezione interrompe il giro e non
  diventa un item fallito.
- **1 test nuovo sul chiamante**: `test_cache_commessa_non_avvelenata_da_riga_caduta` — due
  righe con la stessa chiave commessa, la prima cade su `link_sorgente`, la seconda **deve**
  tornare al database e atterrare.
- ⚠️ **Il test è stato provato contro la regressione**: reintroducendo la scrittura in cache
  dentro il savepoint, fallisce (`1 != 2` sulle chiamate a `get_or_create_commessa`). Non
  passa per il motivo sbagliato.

**Suite: 2234 test verdi** (`apps.vendite` + `apps.core`), da 2229.

---

## 13. Validazioni residue in-app — l'unica cosa aperta di tutta la linea

> ⚠️ **Questo documento è, dal 2026-08-09, il raccoglitore dei residui di TRE cantieri**,
> non solo del proprio. Gli altri due sono chiusi e archiviati in `work-done`:
>
> * [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md) — i tre cruscotti + DDT/resi (§6-quater) + la guida
> * [piano-residui-orchestrazione-e-cruscotti-vendite.md](piano-residui-orchestrazione-e-cruscotti-vendite.md) — il quadro R-1..R-4, con l'analisi che ha generato questo brief
> * [analisi-orchestrazione-vendite-simmetrie.md](analisi-orchestrazione-vendite-simmetrie.md) — il disegno originale (temi A/B/C)
>
> Lo scarto fra il titolo («fan-out») e il contenuto di questa sezione è **voluto e
> dichiarato**: serviva un unico posto vivo dove leggere cosa manca, invece di tre documenti
> aperti al 95%. Chi cerca «cosa resta sui cruscotti» lo trova qui.
>
> **Quando entrambe le validazioni saranno passate, anche questo brief va in `work-done`** e
> la linea è chiusa per intero. ⭐ **Al 2026-09-01 ne è passata una: V2 è chiusa**
> ([verbale](collaudo-in-app-v2-dl23-e-area-resi.md)). Manca **solo V1**.

### 13.1 V1 — Esito parziale del pull da commessa (da questo brief)

> 🔴 **Aggiornamento del 2026-09-04 — eseguita, e ha trovato dell'altro.** Il
> primo dei tre punti qui sotto è **verde**: con una commessa guastata su tre il
> giro non si è fermato, lo step ha chiuso in `ERRORE` con `E_PULL_COMMESSA` e
> `commesse_fallite: [34137]`, e le altre due sono passate (lotto `LTF-0009181`).
>
> ⛔ **Ma il lavoro della commessa respinta è finito in fattura lo stesso**, e la
> proprietà per cui questo cantiere esiste — il savepoint per item — **non è
> stata misurata**: le fatture nascevano da righe `attivita_fatturabili` residue
> di un giro precedente, non dal pull. Cinque difetti (due di modello) in
> [brief-residuo-fatturabili-e-bandiere-esito-parziale.md](brief-residuo-fatturabili-e-bandiere-esito-parziale.md);
> il copione è in
> [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md),
> ora **SOSPESO**. V1 resta aperta.

Prerequisito: `kill -HUP` sul master gunicorn — il backend di sviluppo non ha autoreload,
senza il segnale in-app gira ancora il codice vecchio.

- Un lotto in cui **una commessa su N fallisce** deve mostrare lo step in **ERRORE** nel
  cockpit, e le altre commesse devono risultare **emesse** (il giro non si ferma).
- **Rilanciando** lo step, quella commessa deve essere **ritentata** — prima veniva saltata
  (SKIP) e nessuno se ne accorgeva. È il difetto che il cantiere ha chiuso.
- Se **tutte** falliscono, lo step deve **fermarsi** con `E_PULL_COMMESSA_ALL_FAILED`:
  proseguire costruirebbe un lotto vuoto.
  🔴 **Non vale più dal 2026-09-07** (P-5): il ramo non solleva, l'esito si scrive
  e la catena si ferma per segnalazioni critiche. Il lotto vuoto non nasce lo
  stesso — vedi la nota in §5.1.
- ⚠️ **Trappola T-4** (§8): se sui dati veri il parziale risultasse la **norma** e non
  l'eccezione, il problema non è la segnalazione — sono i dati, e si apre un'altra analisi.
  Non si "abbassa" la segnalazione per far tornare il verde.

> **Misura del 2026-08-16 (mattina) — il ramo nuovo non è mai stato percorso.** In
> `vendite.fatturazione_lotti_task_runs` **non c'è un solo run dal 2026-08-03**, e i
> 13 run storici di `pull_attivita_da_commessa` sono **tutti `COMPLETATO`**, tutti
> precedenti al fix (pushato il 2026-08-10). Non è che la validazione sia andata e
> non sia stata annotata: la pipeline non è proprio stata lanciata da allora. Resta
> valido il prerequisito in testa a questa sezione — senza `kill -HUP` sul master
> gunicorn il backend gira ancora col codice vecchio, e la prova direbbe il falso.

---

> ✅ **Caso normale: PASSATO (2026-08-16, 15:39 UTC).** Tid ha fatturato un gruppo
> da «Competenza fatturazione / Da emettere». Letto dal database (canale di
> sistema, non dall'app):
>
> | | |
> | --- | --- |
> | Lotto | **4135 `LTF-0003953`**, MASSIVO, competenza 2026-08-01, `stato_lotto` COMPLETATO, `riaperto_il` NULL |
> | Task run | **8 su 8 `COMPLETATO`**, tentativo 1, `pull_attivita_da_commessa` in testa |
> | Fattura | **9691** EMESSA, `numero` NULL, 1 riga, imponibile 1.089,00 → totale 1.328,58 |
>
> È il **primo run della pipeline dal 2026-08-03**, quindi la prima volta che il
> fan-out estratto a BB gira davvero in applicazione. Il prerequisito `kill -HUP`
> era soddisfatto (gunicorn riavviato più volte nel frattempo).
>
> **Cosa prova e cosa no.** Prova che l'estrazione del BB **non ha rotto il caso
> sano** — che era il rischio concreto di un ciclo riscritto e mai eseguito.
> **Non** prova il fix: per quello serve il caso parziale (una commessa che
> fallisce mentre le altre passano) e il rilancio che la ritenta invece di
> saltarla. Restano quindi aperti i punti 2 e 3 della lista qui sopra, e servirà
> costruire una commessa che fallisca l'emit dopo aver superato la scoperta.
>
> ---
>
> ⭐ **L'ESITO PARZIALE È STATO VALIDATO IN-APP IL 2026-08-26 — ma su un TERZO
> consumatore, che questo brief non sapeva di avere** (rilievo di Tid,
> 2026-08-31: *«sono sicuro di averlo già fatto in un collaudo»* — ed è vero).
>
> Il §F5 elencava **due** consumatori di `run_fan_out`. Oggi sono **tre**:
> `resi_service.accredita_righe_reso` (accredito massivo dalla coda accrediti)
> lo usa dal cantiere nota di credito, con il commento che ne spiega il perché —
> *«il savepoint per elemento è esattamente ciò che impedisce a una riga
> rifiutata di portarsi via le rettifiche di quelle passate prima»*.
>
> E la **prova 5** di
> [collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md)
> (*«L'esito parziale si legge»*, voce F2 del brief NC) lo ha percorso a video,
> con un rifiuto vero costruito apposta:
>
> - ✅ il toast è **arancione**, non rosso, e dice **«X su Y»**;
> - ✅ si apre l'elenco delle righe **non servite**, con **codice e motivo** per
>   ciascuna;
> - ✅ **le righe passate sono passate** — non è stato annullato tutto.
>
> ⭐ **Cosa questo chiude, ed è la metà che pesava di più.** Il rischio concreto
> dell'estrazione a BB era che il **telaio** fosse rotto: isolamento per item,
> tre stati, motivi per item. Quel telaio è ora **esercitato in applicazione**
> su un consumatore reale — non dai soli test. La riga 3 della lista qui sopra
> («le altre commesse devono risultare emesse, il giro non si ferma») è la
> stessa proprietà, provata.
>
> ⚠️ **Cosa NON chiude, e va detto con precisione**: quella prova non passa da
> un **task_run**. Restano fuori le due cose specifiche della **pipeline** —
> che lo step si chiuda in **ERRORE** invece che COMPLETATO, e che il rilancio
> **RITENTI** invece di saltare (SKIP). Che è, letteralmente, il difetto per cui
> questo cantiere è nato.
>
> 📌 **Quelle due sono coperte da test mirati** — `test_pull_attivita_da_commessa_parziale_chiude_task_run_errore`,
> `test_pull_attivita_da_commessa_tutte_fallite_solleva` (che asserisce
> `E_PULL_COMMESSA_ALL_FAILED`) e `test_fan_out.py` sul BB — **e i test girano
> su mock**. Per la regola zero questo è un **presidio**, non una prova: dice
> che il cablaggio è quello previsto, non che il caso sia mai accaduto in
> applicazione.
>
> ⇒ **Decisione presa da Tid (2026-08-31): si costruisce il caso.** Non per
> completismo — per il **savepoint**, che è l'unica proprietà del cantiere che
> nessuna esecuzione reale ha mai attraversato su questo percorso, e la cui
> rottura sarebbe **silenziosa** (attività perse, nessun errore).
>
> 📋 **Il copione è scritto**:
> [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md)
> — 5 prove più un prerequisito, con il guasto da iniettare nei dati (ROOT
> source di **una** commessa portata a `COLLEGATO`) e il ripristino.
> ⛔ Le `UPDATE` sono **azioni sul database**: le esegue Tid o il team DB, non
> l'agent.
>
> ~~reversibile con l'`UPDATE` speculare~~ ⚠️ **Questa parentesi era sbagliata**,
> ed è il difetto del §13.1-bis qui sotto: lo speculare *per ruolo* non è un
> ripristino. Il copione ora scrive il ripristino sull'**`id` della riga**.
>
> ✅ **E dal 2026-08-31 il copione ha la sua materia** (era l'unica sezione che
> si dichiarava non misurata): mese consigliato `2026-08`, 7 commesse
> emittibili su 9 gruppi, con l'`id` della riga `commesse_sorgenti` ROOT per
> ciascuna e il motivo per cui **tre** di quelle sette è meglio non guastarle.
> Prerequisito `RESUME_TASK` verificato su entrambe le pipeline.

#### 13.1-bis · 🔴 Il difetto trovato nel copione, prima ancora di eseguirlo (2026-08-31)

⭐ **Il ripristino non era il contrario del guasto, e falliva proprio sulle
commesse per cui il guasto era interessante.** Il copione dava due `UPDATE`
speculari:

```sql
-- guasto      -> WHERE commessa_id = <x> AND ruolo_link = 'ROOT'       ✅ mirato
-- ripristino  -> WHERE commessa_id = <x> AND ruolo_link = 'COLLEGATO'  🔴 non mirato
```

Sembrano simmetrici e non lo sono, **perché il modello non è simmetrico**: in
`vendite.commesse_sorgenti` l'unicità è **parziale**, solo sulla ROOT
(`uq_commesse_sorgenti_commessa_root`, indice unico su `commessa_id`
`WHERE ruolo_link = 'ROOT'`), mentre il `CHECK` ammette i due valori senza
limiti di cardinalità. Una commessa è quindi **1 ROOT + N COLLEGATO**.

Ne segue, senza bisogno di guardare nessun dato:

| | |
| --- | --- |
| il **guasto** filtra su `ROOT`, di cui ce n'è **al più una** | colpisce una riga, ed è corretto |
| il **ripristino** filtra su `COLLEGATO`, di cui ce ne sono **N** | prova a promuoverle **tutte** a ROOT |

⛔ E l'esito non è «ne promuove una a caso»: è un `23505` sull'indice parziale,
l'`UPDATE` non passa **per intero**, e la commessa **resta senza ROOT** —
esattamente lo stato che il collaudo doveva disfare. Il copione, che si chiude
con *«ripristina sempre le ROOT prima di chiudere la sessione»*, dava il comando
che su quelle commesse non ci riesce.

⚠️ **La correzione**: il guasto porta un `RETURNING id`, e il ripristino scrive
`WHERE id = <riga_id>`. Più una query di recupero, per quando l'id è andato
perso, che riconosce la riga come *l'unica COLLEGATO di una commessa senza
ROOT* — con l'avvertenza di fermarsi se ne trova più d'una.

> *(Fatto datato, 2026-08-31, e non è il motivo — il motivo è il modello qui
> sopra: delle 31 commesse con sorgenti, **5** hanno più di un COLLEGATO, e una
> ne ha 31. Serve solo a dire che il caso non è teorico.)*

⭐ **La lezione, che vale oltre questo file**: un `UPDATE` di ripristino si
scrive sulla **riga**, non sulla condizione che il guasto ha creato — perché
quella condizione, dopo il guasto, non identifica più solo ciò che il guasto ha
toccato.

> ---
>
> ⚠️ **Trovato guardando i dati, e non riguarda questo cantiere.** ~~Le tre
> attività di agosto sono legate a tre fatture diverse, tutte EMESSA e tutte
> senza numero: 2263, 2457 e la 9691 appena creata.~~ Il verbo «Rendi
> definitive» numera **tutte** le fatture del mese in stato EMESSA — e la
> **2263 non va numerata**. Prima di provare la numerazione va deciso come
> escluderla, altrimenti la prova la trascina dentro.
>
> 🔄 **Aggiornato il 2026-08-31** — l'elenco di agosto era invecchiato e due
> delle tre righe non valgono più:
>
> | Fattura | Allora | Oggi |
> | --- | --- | --- |
> | **2263** | EMESSA, senza numero | ⚠️ **invariata** — l'avvertenza resta in piedi |
> | 2457 | EMESSA, senza numero | ✅ **DEFINITIVA**, `VX2/104` del 2026-08-31 |
> | 9691 | EMESSA, senza numero | ⛔ **non esiste più** — vedi sotto |
>
> ⭐ **E il caso della 9691 vale più della riga di tabella: è `fn_riporta_lotto_a_draft`
> vista all'opera.** Il suo lotto — **4135 `LTF-0003953`**, cioè lo stesso su cui
> il 2026-08-16 era passato il «caso normale» di V1 — porta oggi
> `riaperto_il = 2026-08-17 15:27` e **tutti e otto** i suoi task_run in
> `ANNULLATO`, tentativo 1. È esattamente il passo **RD-6**, osservato sui dati
> e non solo nel corpo della funzione: la fattura è stata cancellata (non
> riaperta) dalla primitiva, e le corse sono state chiuse con esito perché il
> resolver non le vedesse `COMPLETATO`.
>
> ⇒ **È anche la controprova di DB-R1**: la scheda manuale sosteneva che quelle
> righe *«non vengono toccate»*, e c'è un lotto vero, in questo database, che
> mostra il contrario. Il lotto è poi finito `ANNULLATA` / `CHIUSO`.
>
> ⚠️ **Nota a margine, non un difetto**: su quel lotto `riaperto_il` è **rimasto
> valorizzato**, perché lo spegne il runner *quando onora la riapertura* e lì la
> riapertura non è mai stata onorata — il lotto è stato annullato prima. Su un
> lotto chiuso è stato morto e innocuo; si segnala perché chi legge
> `riaperto_il` come «è riaperto adesso» su una lista storica leggerebbe male.
>
> 🔴 **E le EMESSA senza numero oggi sono quattro, non una**: `632`, `836`,
> `2263`, `23662` — tre delle quali datate **agosto**, quindi dentro il tiro di
> «Rendi definitive» sul mese. L'avvertenza non riguarda più una fattura sola:
> il perimetro va guardato **prima** di premere, non l'elenco di allora.

### 13.2 V2 — Slice 3-ter: DDT e resi nelle lenti (dal brief due-lenti)

Checklist in ordine di rischio, derivata dalle decisioni DL-19..28:

- ✅ **DL-19 — il bug che ha originato la slice**: un DDT che ha **superato** lo stato-trigger
  è ancora eleggibile al push (prima usciva per sempre, senza segnalazione). Prova: DDT
  order-backed con trigger `SPEDITO`, portalo a `CONSEGNATO`, verifica che risulti ancora
  da pushare. **Fatto il 2026-08-16 su entrambi i rami** — esito e contesto nel riquadro
  in fondo alla sezione.
- ✅ **DL-28 — gate causale**: DDT con causale fatturabile e una riga senza prezzo risolvibile
  → **blocco parlante** all'emissione, non silenzio. E causale non fatturabile (es.
  CONTO_VISIONE) → fuori dalle card. **CHIUSO su entrambe le metà.** La seconda il
  2026-08-17 (`DDT0010840`, CONTO_VISIONE, prezzo valorizzato, `SPEDITO`: resta fuori
  dai pushabili); la prima — quella sospesa per due mesi — il **2026-08-27**, esercitata
  in-app dal collaudo delle righe a prezzo zero. Storia della sospensione e del suo
  scioglimento nel riquadro in fondo alla sezione.
- ✅ **DL-23 — nessun doppio conteggio**: ordine parzialmente spedito con trigger
  `SPEDITO/CONSEGNATO` → serbatoio mostra il **residuo**; con `CONFERMATO` → mostra il
  **pieno**. **CHIUSO su entrambi i rami.** Il primo il 2026-08-17 (esito in fondo alla
  sezione); il ramo `CONFERMATO` il **2026-09-01**, sul soggetto costruito apposta
  (`ORD0036000` da 10 pz, DDT di 4): ORDINI mostra il pieno e **l'area DDT non mostra il
  DDT** — la merce resta contata una volta sola. ⭐ **La domanda vera era quest'ultima**, e
  la risposta non è un caso: il resolver `vw_dash_fatturazione_ddt` esclude per costruzione
  i DDT degli ordini a trigger `CONFERMATO` (`20260718-07`), scritto proprio contro il
  doppio conteggio di questo §.
- ✅ **DL-27 — il contatore**: reso confermato su merce già fatturata → riga in coda accrediti
  con differenza **negativa**; reso in DRAFT → **non** conta. **Entrambi i rami fatti il
  2026-08-17** (caso costruito da zero, esito in fondo alla sezione).
- ✅ **Card e drill-down**: le due aree nuove (DDT, RESI) si aprono davvero — la whitelist a 7
  aree era fail-closed, senza quella le card non erano drillabili. **Parziale al 2026-08-17**:
  l'area **DDT** ha dati, si vede e **il drill-down si apre** (verificato da Tid); ~~l'area
  **RESI resta vuota per progetto** e non è verificabile oggi~~ — vedi il riquadro in fondo.
  ⭐ **Aggiornato il 2026-08-31: l'area RESI ha una riga** (`RESO0005123`,
  `RICONSEGNA_NON_ESEGUITA`, con azione) e le whitelist BE+FE la ammettono con drawer
  `RESO_VENDITA`. ✅ **CHIUSO il 2026-09-01**: il **drill-down apre il drawer** del reso
  (era l'unico pezzo non garantito a tavolino — la whitelist è necessaria, non sufficiente),
  `valore_fermo` è **vuoto** e non `0,00` come prescrive DL-11, e il ramo
  `MERCE_RESA_GIA_FATTURATA` ha di nuovo un soggetto — **ricostruito e non accreditato**,
  così resta per la prossima volta. Verbale in
  [work-done](collaudo-in-app-v2-dl23-e-area-resi.md).
- ✅ **DL-24 — accredito dovuto vs facoltativo**: l'etichetta distingue l'obbligo dall'opzione
  (`riapre_residuo` + residuo di riconsegna ancora aperto → FACOLTATIVA). **Provato il
  2026-08-17**, e non era in programma: confermando un `RESO_PER_RICONSEGNA` sulla stessa
  merce, lo **stesso reso** compare in **entrambe** le code — `RESO0005123` con accredito
  **3 FACOLTATIVA** fra gli accrediti e **3 DA_RICONSEGNARE** fra le riconsegne — mentre il
  `RESO_A_CREDITO` precedente resta **5 DOVUTA**. Fino a stamattina la distinzione non aveva
  soggetti su cui mostrarsi.
- ✅ **Lista coda accrediti**: colonne 200-203 e i 3 preset resi, priorità responsive.
  **Guardata il 2026-08-17** sul primo soggetto mai esistito (`RESO0005122`).
  ⚠️ Le etichette ora dicono **«Accredito dovuto / facoltativo»**, non più «NC dovuta /
  facoltativa» (allineamento a DL-24: si nomina il fatto, non il rimedio).
  📌 **Al 2026-08-31 la coda è di nuovo vuota** — `RESO0005122` è stato accreditato dal
  collaudo NC e la riga è uscita, che è il comportamento voluto. La voce resta ✅ (è già
  stata guardata piena); si annota perché chi riaprisse la lista oggi la troverebbe vuota
  e potrebbe leggerlo come una regressione.

> **Misura del 2026-08-16 — due dei sei punti oggi non hanno un soggetto su cui
> girare.** Letto dal database:
>
> | Punto | Soggetti disponibili |
> | --- | --- |
> | DL-19 (DDT oltre lo stato-trigger, ancora eleggibile) | `fn_list_ddt_da_pushare()` → **1 riga**: un soggetto c'è, ed è l'unico |
> | Card DDT | `vw_dash_fatturazione_ddt` → **7 righe**: l'area si può guardare |
> | DL-27 (reso confermato su merce già fatturata → coda accrediti) | `vw_resi_da_accreditare` → **vuota**, pur con **5 resi CONFERMATO** su 10 |
>
> Il caso di DL-27 **va costruito** prima di poterlo provare: nessuno dei resi
> confermati oggi presenti alimenta la coda accrediti. Non è un difetto — è che il
> dato non c'è — ma è la ragione per cui quel punto non si spunta guardando l'app
> così com'è. (La misura non è un falso zero da RLS: le tabelle `resi` e `ddt` hanno
> RLS senza `FORCE` e l'interrogazione gira come proprietario.)
>
> 🔴 **Correzione alla riga DL-19 di questa tabella (2026-08-16, sera).** «Un
> soggetto c'è, ed è l'unico» era **una lettura sbagliata della misura**: quella
> riga è `DDT0000034`, un DDT **standalone** che imbocca il ramo
> `src_fatturazione_trigger IS NULL` della funzione. DL-19 vive invece sul ramo
> **order-backed**, che nessun dato percorreva. Il soggetto c'era per la card,
> non per il bug — e contare le righe di una lista non dice **quale ramo** le ha
> prodotte.

#### Esito DL-19 (2026-08-16, sera) — chiuso su entrambi i rami

`vendite.fn_list_ddt_da_pushare` ha due rami, e DL-19 va provato su quello
order-backed. Provati tutti e due, con verifica sul database a ogni passo:

| Ramo | Soggetto | Percorso | Esito |
| --- | --- | --- | --- |
| **standalone** (`trigger IS NULL`, riga 118) | `DDT0000034` | `SPEDITO` → `CONSEGNATO` | ✅ resta eleggibile |
| **order-backed** (`trigger != CONFERMATO`, righe 105-113) | `ORD0018586` → `DDT0010839` | ordine con trigger `SPEDITO`, DDT `SPEDITO` → `CONSEGNATO` | ✅ resta eleggibile |

⭐ **Il ramo order-backed non era mai stato percorso da un dato in questo
database.** La prova di DL-19 è stata anche il suo collaudo iniziale, non la
conferma di qualcosa di rodato: prima di stasera `fn_list_ddt_da_pushare`
restituiva **una sola** riga, sempre dal ramo standalone.

**Perché non c'erano soggetti, ed è un difetto a sé** (segnalato al team DB,
correzione scritta nei changeSet `20260817-01/-02/-03`): `trgfn_ordini_normalize`
sovrascriveva `fatturazione_trigger` con il valore del billing account a **ogni
INSERT**, quindi la scelta fatta in testata veniva scartata in silenzio. Con
tutti i 42 BA a `CONFERMATO`, **nessun ordine poteva nascere con `SPEDITO`** — e
il ramo restava irraggiungibile dall'applicazione. Correzione: `DROP DEFAULT`
sulla colonna + `COALESCE(testata, BA, 'CONFERMATO')` nel trigger, più il
`COALESCE` da togliere in `fn_push_preventivo_a_ordine`. Il contratto BE
richiesto («testata vuota = eredita») **era già rispettato**: form, drawer,
service e repository mandano già NULL quando l'operatore non sceglie.

> ℹ️ **Il caso era però già costruibile, e non ce n'eravamo accorti** (rilievo
> del team DB): `fatturazione_trigger` è in `_UPDATE_KEYS_ORDINE` e il normalize
> agisce solo su INSERT, quindi **crea → resta in DRAFT → riapri → imposta
> `SPEDITO` → salva** funziona senza migrazione. È la strada usata stasera.
> ⚠️ E il workaround era **già scritto in tre fixture pgTAP da mesi**, con il
> commento che spiegava perché la INSERT non tenesse: una segnalazione lasciata
> dentro una suite di test non è una segnalazione, è un promemoria che nessuno
> legge finché non sbatte nello stesso muro.

**Sul `>=` e non `>`** (riga 111, `sdd.ordine >= sdd_trg.ordine`): l'eleggibilità
parte **dallo** stato-trigger, non da quello successivo. Se l'ordine dice
`SPEDITO`, il momento in cui la merce diventa fatturabile *è* la spedizione —
col `>` stretto un DDT spedito e mai consegnato non sarebbe fatturabile mai, che
è il difetto opposto con lo stesso effetto pratico. Le due prove qui sopra
coprono i due lati di quella riga: sullo stato-trigger e oltre.

⚠️ **`DDT0010839` è ancora da inviare a commessa**, ed è oggi l'unico DDT
order-backed con trigger `SPEDITO` esistente. Inviandolo si consuma: se servisse
rifare DL-19 da capo, su quel soggetto non si potrebbe più.
*(Superato: è stato inviato e fatturato il 2026-08-17 — vedi qui sotto.)*

#### Esito DL-27 (2026-08-17) — il caso costruito, e la coda ha la sua prima riga

`vw_resi_da_accreditare` era **vuota da sempre**, pur con 5 resi `CONFERMATO` in
database: nessuno di quelli alimentava la coda. Il caso è stato costruito a
mano, proseguendo lo stesso filo di DL-19.

| Passo | Soggetto | Contatore dopo |
| --- | --- | --- |
| DDT inviato a commessa | `DDT0010839` → `CMM-20260816224228686-b9946f`, 21 pz a 2,50 | tenuti 21 · fatturati 0 |
| Gruppo fatturato | lotto **`LTF-0004017`**, fattura 9908 EMESSA non numerata | tenuti 21 · **fatturati 21** · differenza 0 |
| Reso parziale confermato | **`RESO0005122`**, 5 pz contro il DDT | tenuti 16 · fatturati 21 · **differenza −5** |

**Esito**: 1 riga in coda accrediti — `RESO0005122` · `DDT0010839` · resa 5 ·
**accredito dovuto 5** · etichetta **DOVUTA**. Verificata a video da Tid
(scheda **Vendite → Resi → «Da accreditare»**): riga presente, etichette nella
forma nuova «Accredito dovuto», colonne del contatore leggibili accanto
all'accredito.

⭐ **L'ordine delle mosse È la funzionalità, e spiega la coda vuota di prima.**
`differenza = tenuti − fatturati` diventa negativa solo se si **fattura prima** e
si **rende dopo**: rendendo prima, i tenuti scendono mentre la fattura non
esiste ancora, la fattura nasce già ridotta e la differenza resta a zero —
nessun accredito, correttamente. I 5 resi confermati che non alimentavano nulla
non erano un difetto: erano resi fatti nell'ordine che non genera accredito.

> ℹ️ Controllato anche il rischio del «più volte»: Tid ha ripetuto il tentativo
> di fatturazione, e l'attività 24553 risulta legata a **una sola** riga di
> fattura (AF 7980 → riga 5020 → fattura 9908). Nessun doppio conteggio.

**Non ancora provato di DL-27**: il ramo *«reso in DRAFT non conta»*, che si
verifica con un secondo reso lasciato in bozza — la coda non deve mostrarlo.

> ## ⭐ Aggiornamento DB — 2026-08-19: la porta non è più murata
>
> Il perimetro DB del brief dedicato è **chiuso e applicato**: il resolver dei
> prezzi sa rispondere «non risolvo» senza sollevare, i componenti di un kit
> ammettono il prezzo assente, e il gate all'emissione chiede il prezzo — a
> righe **e** componenti — solo quando la causale dichiara che il documento
> vende. La premessa di DL-28 è stata corretta nel design-of-record
> ([brief-design-fatturazione-due-lenti](brief-design-fatturazione-due-lenti.md),
> errata corrige in fondo al §10).
>
> ⚠️ **Ma il caso in-app non è ancora costruibile, e il motivo è cambiato.**
> Prima il muro era nel database; ora è nel backend: `ddt_service` continua a
> chiamare il resolver che **solleva** invece del nucleo che **riporta**
> (richiesta **BE-1** del brief dedicato, §10). Finché quella riga non cambia,
> l'operatore vede lo stesso errore di prima.
>
> ⚠️ E una precisazione sul riquadro qui sotto, che va letta prima di
> riprovarlo: *«non è mai scattata e non può scattare»* era vero **per
> l'applicazione**, non per il sistema. Il gate era già esercitato dai pgTAP, e
> il database quelle righe le produce da sé nelle ri-consegne. Quello che non è
> mai successo è che scattasse su un documento reale.
>
> **Quindi**: la voce resta ⏸️ **sospesa**, ma il blocco è ora **una riga di
> Python**, non un pezzo di modello mancante.

#### DL-28 (2026-08-17) — ⏸️ sospeso: il gate presidia una porta murata

Provando a costruire il caso, Tid ha trovato che **una riga di DDT senza prezzo
non è inseribile**: il pricing la respinge con *«impossibile risolvere il prezzo
listino»*, **per qualunque causale** — comprese le sette non fatturabili.

⚠️ **Ma DL-28 nasce dalla premessa opposta**, testuale: *«Il DDT ammette righe
senza prezzo **per design** ("solo trasporto")»*. Se quella riga non si può
caricare, la metà «blocco parlante» del gate **non è mai scattata e non può
scattare**: non è un gate sbagliato, è un gate che presidia una porta murata.

**Decisione di Tid (2026-08-17): le righe a prezzo zero devono essere ammesse.**
Perimetro e domande aperte in [brief-ddt-righe-senza-prezzo.md](brief-ddt-righe-senza-prezzo.md);
va corretta anche la **premessa nel design-of-record**, che oggi descrive come
esistente un caso che il prodotto non consente.

**Cosa resta provabile subito**: la seconda metà — DDT con causale non
fatturabile (CONTO_VISIONE) e prezzo valorizzato, portato a SPEDITO, deve
restare **fuori** da card e lister.

✅ **Seconda metà fatta (2026-08-17)**: `DDT0010840`, causale `CONTO_VISIONE`
(`fatturabile = false`), prezzo valorizzato, stato **SPEDITO** — cioè in uno
stato che lo renderebbe eleggibile — e `fn_list_ddt_da_pushare()` **non lo
restituisce**. La regola «dentro chi fattura, fuori chi no» regge sul lato che
si può provare.

✅ **PRIMA metà fatta (2026-08-27) — la sospensione è sciolta.** Le righe a
prezzo zero sono ammesse dal **2026-08-19** (DB slice A-D + BE-A→BE-D + FE-A→FE-E)
e il **collaudo in-app** le ha portate a video il 27: caricata la riga senza
prezzo su causale **fatturabile**, il pulsante *Emetti* è **disabilitato** e il
tooltip **nomina la riga**; forzando, il DDT non passa a EMESSO.
Copione e verbale in
[collaudo-in-app-ddt-righe-senza-prezzo.md](collaudo-in-app-ddt-righe-senza-prezzo.md)
(prova **3**, casella **2**), che lo registra così:

> ⭐ *«il gate esiste dal 2026-07-18 e in un anno non è mai scattato su un
> documento reale — le 271 occorrenze nel diario erano tutte corse di pgTAP.
> Se lo vedi scattare adesso, DL-28 è finalmente esercitato per intero.»*

⭐ **Cosa lascia scritto questa voce**, ed è il motivo per cui vale la pena
rileggerla tutta: DL-28 è stato **verde nei test per un anno** mentre la porta
che presidiava era **murata**. Il gate era corretto, i pgTAP lo esercitavano,
e nessuna di quelle 271 corse poteva accorgersi che in applicazione il caso non
era nemmeno **inseribile**. È la regola zero vista dal lato del test: *«il test
è verde perché i dati di oggi non sanno produrre il caso»* non prova niente —
ed è servito un collaudo a mano, due mesi dopo, per saperlo.

#### DL-27, ramo «reso in DRAFT» (2026-08-17) — ✅ chiuso

Secondo reso sulla stessa merce, lasciato in **DRAFT**: la coda accrediti
continua a mostrare **una sola** riga, quella di `RESO0005122`.

⭐ **La difesa non è un filtro, è la struttura del documento**: un reso in bozza
non ha nemmeno il **numero** (`numero = NULL`, la numerazione arriva alla
conferma). Non è ancora un documento — e questo è più solido di una condizione
scritta in una vista, perché non si può disattivare per sbaglio.

#### DL-23 (2026-08-17) — ✅ il ramo che previene il doppio conteggio

Caso costruito: `ORD0018587` (riga da **10** pezzi a 14,45, trigger `SPEDITO`
impostato dopo il salvataggio), evaso in parte con `DDT0010841` per **4** pezzi
→ ordine a `PARZIALMENTE_EVASO`. Letto da `vw_dash_aperto_documenti`:

| Area | Documento | Valore | Pezzi | Motivo fermo |
| --- | --- | --- | --- | --- |
| ORDINI | `ORD0018587` | **86,70** | 6 (residuo) | `IN_ATTESA_DDT` |
| DDT | `DDT0010841` | **57,80** | 4 (spediti) | `PUSH_NON_ESEGUITO` |

**6 + 4 = 10**: la merce compare **una volta sola** nel serbatoio, in due punti
diversi del percorso, e la somma torna all'ordine. Senza DL-23 l'ordine
mostrerebbe 144,50 (il pieno) e il DDT altri 57,80 — 14 pezzi a fronte di 10.

⚠️ **Il pezzo si legge dal valore, non da `unita_totali`**: quella colonna vale
`1` per entrambe le righe perché conta le **righe documento**, non i pezzi. Un
errore facile da fare guardando la lente a video.

⬜ **Ramo `CONFERMATO` non provato — nessun soggetto**: cercando un ordine con
trigger `CONFERMATO` **e** parzialmente evaso non ne esiste nemmeno uno (i 91 a
`CONFERMATO` o sono interi o non sono parzialmente evasi). Va costruito: ordine
da 10 lasciato a `CONFERMATO`, DDT di 4, e il serbatoio deve mostrare il
**pieno**.

> 🔁 **Ricontrollato il 2026-08-31: continua a non esistere**, e la
> distribuzione dice anche *perché* non nascerà da sé.
>
> | `fatturazione_trigger` | Stato ordine | N |
> | --- | --- | --- |
> | `CONFERMATO` | DRAFT | 55 |
> | `CONFERMATO` | EVASO | 36 |
> | `CONFERMATO` | CONFERMATO | 3 |
> | `CONFERMATO` | ANNULLATO | 1 |
> | `SPEDITO` | **PARZIALMENTE_EVASO** | **2** |
>
> ⭐ **I due `PARZIALMENTE_EVASO` che esistono sono entrambi a trigger `SPEDITO`**
> — cioè sono il ramo **già provato** il 2026-08-17 (`ORD0018587` e il suo
> gemello). Sull'incrocio che serve, `CONFERMATO` × `PARZIALMENTE_EVASO`, la
> casella è vuota da sempre.
>
> ⚠️ E il caso **non arriverà spontaneamente**: chi lavora con `CONFERMATO` sta
> fatturando alla conferma, quindi non passa dall'evasione parziale. Va
> costruito a mano — ordine da 10, trigger `CONFERMATO`, DDT di 4 — e il
> controllo è che il serbatoio ORDINI mostri il **pieno** (10 pezzi, valore
> intero), non il residuo.
>
> ⚠️ **E si legge dal valore, non da `unita_totali`** — la stessa trappola
> annotata per il primo ramo: quella colonna conta le **righe documento**.

> 🐛 **Due difetti FE trovati validando, entrambi corretti in giornata.** Non
> appartengono alla slice ma sono emersi solo perché qualcuno usava l'app sul
> serio:
>
> 1. **la testata del DDT non si salvava in creazione** — causale di trasporto,
>    aspetto beni, addebito. Causa: `loadDetail` **sostituisce** il form coi dati
>    del server ed è invocata da **sette** punti, fra cui `@changed` del
>    salvataggio di una RIGA. Si sceglieva la causale, si salvava la riga, e la
>    causale tornava vuota senza che nulla lo segnalasse. Corretto rendendo
>    `loadDetail` non distruttivo verso il non-salvato (baseline = ultima forma
>    ricevuta dal server), invece di rincorrere i sette chiamanti;
> 2. **una seconda finestra, nel BB `useDrawerAutosaveBozza`**: la POST di
>    creazione fotografa il form all'istante del trigger, e la ricarica al
>    ritorno cancellava quanto digitato nel frattempo. Corretta nel BB, quindi
>    per **tutti e tre** i drawer che lo usano (DDT, ordini, preventivi).
>
> ⚠️ **Residuo**: il rimedio del punto 1 vive nel solo drawer DDT. Ordini e
> preventivi hanno la stessa struttura (`loadDetail` che sostituisce + righe che
> emettono `@changed`) e restano scoperti su quella finestra.

#### Card e drill-down (2026-08-17) — l'area RESI è vuota **per progetto**

Misurato sulle viste che alimentano le due lenti:

| Lente | Aree con dati |
| --- | --- |
| Backlog fatturazione | PREVENTIVI 64 · ORDINI 25 · **DDT 2** |
| Situazione aperta | PREVENTIVI 76 · ORDINI 59 · CONTRATTI 15 · OFFERTE 2 · **DDT 1** |

L'area **RESI non compare**, e non per mancanza di soggetti: `RESO0005122` ha
accredito dovuto e attraversa il ramo. Cade sull'ultimo filtro della vista —
`WHERE COALESCE(mf.classe,'ANOMALIA') <> 'FISIOLOGICO'` — perché il motivo
`MERCE_RESA_GIA_FATTURATA` è classificato **`FISIOLOGICO`** con `azione = NULL`,
mentre il gemello `RICONSEGNA_NON_ESEGUITA` è `RECUPERABILE` e compare.

✅ **È DL-24 che funziona come scritto**: il Backlog elenca ciò che è fermo e
**recuperabile**; un motivo senza rimedio non è arretrato. La decisione lo dice
già — *«è 🟢 perché nessuna azione esiste oggi»*.

**Conseguenza sulla checklist**: la voce si spunta **a metà**. L'area DDT è
verificabile ora (resta da confermare che il drill-down si apra: era il difetto
della whitelist fail-closed); l'area RESI lo diventerà **con la slice NC**, e
allora basteranno due celle di seed — vedi §6.1 di
[brief-design-note-credito-resi.md](brief-design-note-credito-resi.md).

⭐ **Aggiornamento 2026-08-31 — la condizione si è avverata, la voce non è più
bloccata.** ~~La slice NC è chiusa il 2026-08-26 (collaudo in-app compreso) e~~
**le due celle di seed ci sono già**: in
`db/changelog/migrations_v2/80_data/sql/config/motivi_fermo.csv` la riga 15 porta
`MERCE_RESA_GIA_FATTURATA` da `FISIOLOGICO`/azione NULL a **`RECUPERABILE`** con
azione *«Emetti la nota di credito dalla coda accrediti»*. Il filtro
`WHERE COALESCE(mf.classe,'ANOMALIA') <> 'FISIOLOGICO'` — l'ultimo della vista,
quello su cui l'area cadeva — **non la scarta più**.

> ⚠️ **Rettifica di data (2026-08-31, sera).** Il seed non è della slice NC del
> 26-08: la cella è `RECUPERABILE` dal **2026-08-18**, commit `06b661061`
> (*brief-db-rettifiche-e-componenti*), e il mirror `loadUpdateData` risulta
> `RERAN` lo stesso giorno alle 15:13. **Verificato applicato**, non dedotto dal
> CSV: `config.motivi_fermo` in questo database dice `RECUPERABILE` + azione su
> `MERCE_RESA_GIA_FATTURATA` **e** su `RICONSEGNA_NON_ESEGUITA`. La conclusione
> resta identica — cambia solo chi se ne prende il merito, ed è la differenza
> fra un fatto e una ricostruzione plausibile.

⚠️ ~~**Ma «sbloccata» non è «verificata», e la differenza qui è tutta.** Nessuno
ha ancora guardato il Backlog dopo il cambio.~~ **Guardato il 2026-08-31**, e
l'esito si divide in due metà con segno opposto.

⭐ **① L'area RESI compare nel Backlog, con l'azione.** Una riga:

| Area | Documento | Motivo | Classe | Azione |
| --- | --- | --- | --- | --- |
| **RESI** | `RESO0005123` (`CONFERMATO`) | `RICONSEGNA_NON_ESEGUITA` | `RECUPERABILE` | *«Genera il DDT di ri-consegna»* |

Il conteggio per area del Backlog è oggi **DDT 4 · ORDINI 22 · PREVENTIVI 63 ·
RESI 1** — l'area non è più assente. E `valore_fermo` è **NULL**, non 0, come
DL-11 prescrive per un'area a conteggi.

✅ **E la strada del drill-down è aperta per costruzione**, non per fortuna: le
whitelist a valle ammettono `RESI` su **entrambi** i lati — `DASH_FATTURAZIONE_AREE`
in `backend/apps/vendite/db/vendite_repository.py` e `DASH_AREA_CONFIG` in
`frontend/src/vendite/dashboardAree.js`, con `drawerTipo = RESO_VENDITA` e la
severity dei resi. Era la whitelist fail-closed a 7 aree il difetto temuto: non
lo è. **Resta da confermare a video che il drawer si apra davvero** — la
whitelist è condizione necessaria, non sufficiente.

⛔ **② Ma il soggetto che questo brief indicava NON C'È PIÙ, e il ramo che gli
apparteneva è di nuovo senza materia.** La frase da correggere era *«va vista
con il soggetto che c'è già (`RESO0005122`, accredito dovuto 5)»*:
`vendite.vw_resi_da_accreditare` è **vuota**, e con lei il ramo
`MERCE_RESA_GIA_FATTURATA` della union.

⭐ **Non è un difetto: è il verbo che ha funzionato.** La coda ha
`WHERE accredito_dovuto > 0`, e `accredito_dovuto` è calcolato **al netto di
`gia_accreditato`** — proprio perché *«una riga esce dalla coda AL VERBO e non
alla generazione della fattura»*. Il collaudo NC ha emesso l'accredito su
`RESO0005122`, il residuo è sceso a zero, la riga è uscita. ⇒ **La prova che ha
creato il soggetto è la stessa che l'ha consumato**, e va saputo prima di
cercarlo: chi lo cercasse oggi concluderebbe che il seed non funziona.

⚠️ **Quindi la voce si spunta a metà, di nuovo — ma per una ragione diversa da
prima.** Non è più *«il motivo è fisiologico»* (risolto): è che **quel motivo non
ha righe**. Per chiuderla del tutto serve **ricostruire** un reso con accredito
dovuto — stesso gesto del 2026-08-17 (`DDT` → fattura → reso a credito) — e
guardare che l'area compaia **con l'azione**, perché è l'azione la ragione per
cui il motivo ha smesso di essere fisiologico.

⚠️ **Nota di metodo, e vale per chiunque rimisuri queste viste**: interrogare
`vw_dash_competenza_*` senza `app.current_user_id` restituisce **zero righe a
chiunque** — `script.fn_get_emittenti_scope_sr_ids(NULL)` torna `{}` (array
vuoto, non NULL) e il `= ANY` è falso ovunque. È **fail-closed**, non una
misura. Le misure di questa sezione sono state prese con `SET app.current_user_id = '1'`.

### 13.3 Le due cose non-validazione — entrambe chiuse (commit 2026-08-10, build docs 2026-08-16)

- ✅ **Commit**: fatto e **pushato** il 2026-08-10. Il BB fan-out e il fix dell'esito
  parziale sono in `388b7dfee`; il resto della linea (guida cruscotti, archiviazione dei
  tre doc, bonifica link) nello stesso commit, più `4828258d6` per la rigenerazione di
  `error_policies_generated.py`. Ramo `dev/backend-tid`, allineato con origin.
- ✅ **Build docs**: **fatto il 2026-08-16**, verde. `zensical` nel frattempo è
  installato nel `.venv` di radice, quindi `python scripts/build_docs_zensical.py`
  gira: **exit 0**, 14 secondi, 2575 pagine preprocessate, 3455 include espansi,
  9348 link riscritti, **zero warning di include**.

  Restano **5 warning, tutti preesistenti e nessuno di questo cantiere**:

  | Dove | Cosa |
  | --- | --- |
  | ~~`docs/it/dbzero/pratiche/index.md` e il gemello `index.ci.md`~~ | 4 link morti: `vw_definizioni_drift.md` e `fn_pubblica_definizione.md` — ✅ **causa corretta nel generatore il 2026-08-26**, spariscono alla prossima rigenerazione (vedi sotto) |
  | ~~`docs/it/dev/frontend/i18n-namespace-radici.md`~~ | 1 àncora morta verso `frontend-standards.md#struttura-chiavi--radici-dei-namespace` — ✅ **corretta il 2026-09-02**: l'id vero collassa la lineetta in **un solo** trattino (`#struttura-chiavi-radici-dei-namespace`), letto dall'HTML generato e non dedotto. `frontend-standards.md` non ha ancore esplicite `<a id="">`, quindi il link deve puntare all'id dell'heading. Stesso link corretto anche nelle 2 occorrenze di `brief-i18n-radici-uniformi.md` |

  > ℹ️ **I 4 link morti non sono un contenuto sbagliato: è il generatore.**
  > L'index di schema è **auto-generato** (`scripts/gen_db_docs.py`) e ricopia la
  > prima frase delle pagine `manual/`. Dentro `manual/` un link
  > `[fn_pubblica_definizione](fn_pubblica_definizione.md)` è **corretto** — le due
  > pagine sono sorelle — ma issato di un livello nell'index punta a una cartella
  > dove quel file non c'è. Il generatore non riscrive i link relativi quando li
  > sposta di cartella. Si corregge lì, una volta per tutti gli schemi.
  >
  > ✅ **CORRETTO IL 2026-08-26, dove diceva questo paragrafo**: in
  > `scripts/gen_db_docs.py`. `extract_scopo` riceve ora la cartella dello schema
  > e riscrive i link relativi nudi risolvendoli sulla sottocartella che contiene
  > davvero il file — `funzioni/`, `views/`, `tabelle/` per `index.md`,
  > `manual/` per `index.ci.md`, che sono **due bersagli diversi dalla stessa
  > cartella**.
  >
  > ⭐ La riscrittura vive **dentro `extract_scopo`**, non nei quattro punti che
  > la chiamano: la lettura dello «Scopo» è una sola, e quattro copie della
  > stessa riscrittura sarebbero quattro occasioni di divergere.
  > ⚠️ **Un nome non risolvibile si lascia com'è**: il generatore non inventa una
  > destinazione. Meglio un link che il build segnala di uno che punta altrove.
  >
  > ⛔ **La doc NON è stata rigenerata**, ed è la regola: l'auto-gen si rigenera
  > al suo giro, non a mano e non da qui. La correzione arriva ai due index di
  > `pratiche` alla prossima rigenerazione.
  > ⭐ **Provata comunque prima di fermarsi**: rigenerando in prova i due index
  > il diff è **esattamente** i 4 link e nient'altro — che è anche la prova che
  > il generatore, per il resto, è stabile — e su **tutti** gli schemi i link
  > morti passano da **4 a 0**. La prova è stata poi annullata.
  >
  > 📌 **E il residuo era stato letto male, una volta.** Il 2026-08-26 un
  > controllo automatico l'ha segnalato come *«link rotto in questo brief»*: ma
  > il link qui sopra sta dentro un **esempio citato**, e citare non è linkare.
  > Il difetto vero non era mai stato in questo file — era nel generatore, dove
  > questo paragrafo diceva fin dall'inizio che fosse.

  ⚠️ **E una cosa che va saputa a proposito di questo residuo: non poteva
  validare nulla di questo cantiere.** `work-done/` e `work-in-progress/` sono
  **esclusi** dal build (`exclude_docs` in `mkdocs.yml` e pruning del preprocess:
  `excluded_dirs_removed=2`). I brief non entrano nel sito: il build vale come
  controllo **globale** della documentazione pubblicata, non come verifica dei
  testi di questa linea. La coerenza interna dei brief resta quella verificata a
  mano il 2026-08-10.

---

## 14. Ricognizione dei residui BE consegnati dal DB (2026-08-16)

> Il team DB ha ricontrollato contro il codice i residui che il lato DB aveva
> consegnato al BE «fuori da questa linea», e ne ha segnati **quattro**: due
> chiusi, due aperti. Riverificati qui uno per uno, con le righe di codice.
> **Esito: dei due segnati 🔴 aperti, nessuno lo è**; il terzo 🔴 era già stato
> deciso lo stesso giorno. Le due ✅ sono confermate.
>
> ⚠️ Il DB ha dichiarato di aver **corretto la propria memoria di progetto** su
> questa base. Va rettificata, altrimenti alla prossima sessione tornano a galla
> due residui inesistenti — lo stesso danno del registro sbagliato, col segno
> rovesciato.

| Voce | Segnata | Verificata | Dove |
| --- | --- | --- | --- |
| `terne_pronte` | 🔴 aperta | ✅ **consumata** | `commesse_repository.py:1267` → `GruppoDiagnosi` → `_fatturazione_job_helpers.py:221` |
| `riaperto_il` | 🔴 aperta | ✅ **consumata** | `pipeline_repository.py:2132/2144` → `pipeline_runner.py:392/546` |
| Slot indirizzi (§10.5) | 🔴 aperta | ✅ **decisa** «non si restringe» | §11.1 di `brief-db-indirizzi-su-ordini-contratti-offerte.md` |
| Pricing v5 F2-BE | ✅ fatta | ✅ confermata | `pricing_repository.py:90` chiama `fn_resolve_prezzo_listino_v2` |
| Documenti Fase A | ✅ fatta | ✅ confermata | `_REL_CONSENTITE` in `core/db/dbops_repository.py:26`, usata come guard in 2 punti |

### 14.1 `riaperto_il` — non è «girante ma inutile», governa il giro

Il rilievo diceva «compare solo in `smoke-ritorno-lotto-a-draft.py`, niente in
`backend/apps/`». Non regge: `is_lotto_riaperto()` lo legge
(`pipeline_repository.py:2132`), `azzera_riaperto_il()` lo spegne (`:2144`), e
`pipeline_runner.py:392` lo usa come **terzo motivo per rifare lo step corrente**
invece di avanzare — con l'azzeramento a `:546` quando il giro l'ha onorato,
senza il quale il lotto rifarebbe lo stesso step all'infinito.

⏱️ **E non è codice di oggi**: è entrato il **2026-08-03** (`6728e58cb`), quasi
due settimane prima della misura. Qui non c'è una spiegazione di tempistica: la
verifica ha guardato nel posto sbagliato.

**Cosa sopravvive del rilievo, in forma molto più stretta**: il segnale non
risale all'API e **il FE non mostra da nessuna parte che un lotto è stato
riaperto**. È una richiesta di *visibilità*, non un residuo di consumo — e come
tale va valutata a sé, non ereditata come «funzione DB inutile».

> ✅ **SUPERATO — verificato il 2026-08-31 sul codice, ed erano false tutte e
> due le metà.** Il paragrafo qui sopra resta perché la sua *forma* era giusta;
> il suo contenuto no.
>
> **1 · Il segnale risale all'API.** `vendite_repository.py` espone
> `(fl.riaperto_il IS NOT NULL) AS riaperto` in `_LOTTO_SELECT_COLS`, quindi
> **su lista e dettaglio**, con `riaperto: bool` dichiarato in `types.py`.
> Entrato con il collaudo NC del **2026-08-22**, due mesi prima che qualcuno
> rileggesse questo §14.1.
>
> **2 · Il FE lo mostra — dove serve, cioè sul GESTO.** Su un lotto riaperto
> `verbiPipeline` propone **«Rigenera la bozza»** (`pi pi-refresh`) al posto di
> «Avanza step» (`pi pi-forward`), come **pulsante visibile** nella
> `DrawerActionsBar` e come voce del kebab di riga. E il dialog di conferma lo
> dice a parole: *«Il lotto è stato riportato in lavorazione: rieseguire lo step
> per rigenerare i documenti? Il lotto resta in bozza.»* L'esito è «Bozza
> rigenerata», non «Pipeline avanzata».
>
> ⭐ **E l'icona è diversa di proposito** — dal commento del composable: *«la
> freccia in avanti su un gesto che non avanza è la stessa bugia
> dell'etichetta»*.
>
> ⛔ **Il Tag di stato è stato VALUTATO E SCARTATO** (2026-08-31), ed è la parte
> che vale la pena tenere scritta. La proposta era «un Tag *riaperto* in lista e
> in testata drawer». È sbagliata, e la ragione sta nel ciclo di vita della
> colonna: **`riaperto_il` non è uno stato, è un segnale di un giro solo** — il
> runner lo spegne (`azzera_riaperto_il`) appena lo onora. Un Tag prometterebbe
> **uno stato durevole su una cosa che dura una esecuzione**, e sarebbe una
> seconda bugia dopo quella che l'etichetta del pulsante ha appena tolto.
> ⇒ Ciò che l'operatore deve sapere non è *«questo lotto è riaperto»* ma
> **«la prossima esecuzione RIFÀ invece di avanzare»** — e quello è già scritto
> sul verbo, che è il posto dove la persona sta guardando quando la cosa conta.
>
> ⚠️ **Il residuo onesto, e sta in una riga**: nella finestra fra la riapertura
> e il primo run, un lotto riaperto e uno mai riaperto sono **identici a
> riposo** — si distinguono solo aprendo il menu delle azioni. Non conta per chi
> ha appena premuto il pulsante (ha visto il toast); conta per un **secondo**
> operatore, o per lo stesso dopo un ricarico di pagina. Se un giorno si vorrà
> chiudere anche quello, la sede giusta **non è un Tag** ma la riga informativa
> che la `DrawerActionsBar` già rende (`stato_info_key`), cioè lo stesso canale
> con cui il DB spiega perché un verbo è spento.

### 14.2 `terne_pronte` — misura scattata 49 minuti troppo presto

Anche qui il consumo c'è: `commesse_repository.py:1267` lo decodifica con
`_decode_jsonb` (col commento sul jsonb che su questa connessione arriva come
stringa), finisce in `GruppoDiagnosi` e `_fatturazione_job_helpers.py:221` lo
usa per distinguere i gruppi le cui terne sono fallite da quelli fermi per
un'altra causa. Tre test lo coprono.

> ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_decode_jsonb` è ritirato. Le letture per posizione usano il BB `jsonb_out` di `apps/core/db/_helpers.py`; le letture a dizionari (`row_to_dict`, `rows_to_list`, `fetch_paged_with_total`) decodificano i jsonb da sole.


⏱️ **Ma qui la spiegazione c'è, ed è onesta**: quel codice è entrato alle
**15:13** del 2026-08-16 (`4129f5a22`), il commit della verifica è delle
**16:02**. Su un checkout precedente il grep torna vuoto legittimamente. Non è
un errore di metodo — è una fotografia scattata prima del fatto.

### 14.3 Slot indirizzi — decisa, non aperta

«contratto ne dichiara 3, off-comm 4, i template ne stampano 1» è vero come
descrizione dello stato, ma la voce **non è aperta**: il 2026-08-16 è stato
deciso di **non restringere**, perché gli slot seguono
`config.tipi_indirizzi_allowed` — la stessa whitelist che il pannello FE legge a
runtime — e toglierli farebbe sparire in silenzio un indirizzo che l'operatore
può già inserire. Motivazione estesa in §11.1 del brief citato. Anche qui è
questione di minuti: la nota è delle 16:02, la chiusura è stata pushata alle
16:04.

### 14.4 Cosa lascia questa ricognizione

Nessun lavoro BE nuovo: **zero** delle quattro voci richiede codice. Restano due
cose da fare, entrambe di registro e non di sviluppo:

- ~~la **memoria del DB va rettificata** sulle due voci `terne_pronte` e
  `riaperto_il`, altrimenti si autoconfermano alla prossima sessione~~ — ✅
  **CHIUSA il 2026-08-31, controllando invece di dedurre.** La memoria di
  progetto è stata cercata su entrambi i termini: **non contiene né l'uno né
  l'altro**, né come residuo aperto né in altra forma. I due residui
  inesistenti non possono autoconfermarsi, perché non sono scritti da nessuna
  parte.
  ⭐ **E la verifica valeva la pena proprio perché l'esito era «niente da
  fare»**: è il caso in cui si è più tentati di spuntare la voce a memoria. Una
  voce di registro si chiude guardando il registro — che è la stessa regola per
  cui «applicato?» si chiede a `databasechangelog` e non al brief;
- ~~se la **visibilità FE del lotto riaperto** interessa davvero (§14.1), va
  aperta come richiesta sua, con il suo perimetro~~ — ✅ **CADUTA il
  2026-08-31**: la visibilità **c'è già** (il verbo cambia nome, icona, conferma
  ed esito) e il Tag che sembrava mancare è stato **valutato e scartato**,
  perché `riaperto_il` non è uno stato. Esito e ragione nel riquadro del §14.1.
  ⇒ **Questa ricognizione non lascia più nessuna voce di sviluppo**, né BE né
  FE: ~~restano solo le due di registro (la memoria del DB, qui sopra) e le due
  voci DB di documentazione, in testa al documento.~~

⭐ **Aggiornamento 2026-08-31, sera — il §14 non lascia più NIENTE.** Delle
quattro cose che restavano fuori dallo sviluppo, tre sono chiuse in giornata e
una sola è ancora in piedi, ed è una **domanda**, non un lavoro:

| Voce | Dov'era | Oggi |
| --- | --- | --- |
| visibilità FE del lotto riaperto | §14.4 | ✅ caduta (il verbo la porta già; Tag scartato) |
| memoria del DB su `terne_pronte` / `riaperto_il` | §14.4 | ✅ verificata: non contiene né l'una né l'altra |
| **DB-R1** — la scheda manuale contraddice la funzione | testata | ✅ **corretta**, entrambi i punti, con rettifica dichiarata |
| **DB-R2** — nessuna riga di giornale sulla riapertura | testata | ✅ **decisa, scritta e APPLICATA** il 31-08 (changeSet `20260831-70` EXECUTED 21:36 + seed + pgTAP 14/14 come app + doc) |

⭐ **La lezione, che è la stessa di due volte oggi**: una misura contro il codice
vale quanto il momento in cui è scattata e il posto in cui ha guardato. Una
frase che dichiara *chiuso* ciò che è aperto e una che dichiara *aperto* ciò che
è chiuso costano uguale — restano scritte, e la sessione dopo nessuno le
rimette in discussione.
