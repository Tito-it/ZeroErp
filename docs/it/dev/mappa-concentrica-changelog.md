# Mappa Concentrica — Changelog

> Cronologia datata degli aggiornamenti della [Mappa Concentrica](../mappa-concentrica.md).
> La mappa mostra solo lo **stato corrente** per anello; questo documento conserva la storia,
> per non gonfiare il documento principale.
>
> Registra solo evidenze presenti nel repository: commit e documentazione
> `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica
> test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.
>
> ## Come si compatta un mese
>
> Le voci recenti si scrivono per **data di aggiornamento**; quando un mese esce
> dalla finestra di consultazione, le sue voci si fondono in **una voce mensile**
> (`## luglio 2026`). ⚠️ **Non a mese chiuso**: si aspetta che i brief di quel
> mese siano **tutti in `work-done`**, altrimenti si comprime rimandando a
> documenti ancora in movimento.
>
> **Che cosa sopravvive alla compressione**, ed è la parte che conta:
>
> 1. il **nome del tema** — è la chiave con cui ci si ritorna;
> 2. **due o tre righe** su cosa è cambiato nel sistema, mai su *come*;
> 3. **tutti i link ai brief** — sono la ragione per cui il resto si può
>    tagliare: il dettaglio non si perde, si delega alla sua sede;
> 4. ⛔ **ciò che non ha un brief NON si comprime.** Comprimere un tema che ha il
>    suo brief è *delegare*; comprimere una riga che vive solo qui è
>    **cancellare**. Nel dubbio si cerca il documento: se non c'è, il testo resta.
>
> ⛔ **Si compatta in questo file, non in un archivio a parte.** I riferimenti ai
> documenti vivono anche nei `COMMENT` SQL e in changeSet già mergiati, che non
> si toccano: l'URL di questo changelog deve restare uno.

---

## 10 settembre 2026

> Copre il periodo **31 agosto – 10 settembre**. Undici giorni, **384 changeSet**
> nuovi (175 in `vendite`, 60 in `dbops`, 58 in `script`) e **46 brief chiusi**
> — il ritmo più alto finora. Anche qui si scrive per **temi**: sono otto.
>
> ⚠️ **L'11 settembre è volutamente fuori**, per la stessa ragione del 31 agosto
> nella voce precedente: quel giorno era in corso mentre questa voce veniva
> scritta. Ciò che è atterrato l'11 — la chiusura formale del cantiere del
> perimetro e due slice piccole — entra nella voce successiva.
>
> ⭐ **Il tema portante non è un dominio, è la CATENA DI VERIFICA.** Quattro degli
> otto temi qui sotto riguardano *come si sa che una cosa è vera*: la CI che
> misura davvero, i presidi che hanno un catalogo, il perimetro dei dati che ha
> un criterio invece di un elenco, e i motivi d'errore che escono da un posto
> solo. Il resto del periodo poggia su quelli.

**Anello 0 — I pgTAP misurano davvero, e la CI misura la CI.** La suite era un
cancello che si poteva attraversare: `continue-on-error` la rendeva un parere, e
la baseline dei rossi era compilata **a mano** su una macchina di sviluppo — cioè
descriveva quella macchina, non il contratto. Il 9 settembre la baseline della CI
viene **misurata dalla CI** su un database ricostruito da zero, il
`continue-on-error` sparisce, e il ramo di bootstrap **fallisce invece di
passare**. Escono tre difetti d'ambiente che tenevano rossi interi gruppi di file
e due building block di fixture riusabili. ⛔ E si scopre la forma peggiore del
difetto: *un cancello che passa perché non ha misurato niente è peggio di un
cancello assente*. Vedi
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md).

**Anello 0 — I presidi hanno un catalogo, e un contatore che non mente.** I
presidi del progetto erano una ventina di file che nessun elenco teneva insieme:
per sapere *quanti sono e cosa coprono* bisognava cercarli. Nasce `dbops.presidi`
— il catalogo — con **il contatore onesto**: un presidio che non ha mai girato non
conta come copertura. Il 10 settembre arriva il corollario in CI: *un cancello non
deve poter zittire un altro cancello*, perché un guardrail che fallisce e ne
maschera un secondo lascia passare due difetti al prezzo di uno. Vedi
[brief-db-un-destinatario-per-i-presidi.md](work-in-progress/brief-db-un-destinatario-per-i-presidi.md).

**Anello 0 + 3 — Il perimetro dei dati smette di fermarsi alla testata.** Delle
sei famiglie di documento di `vendite`, **una sola** era protetta fino in fondo:
le righe delle altre cinque erano leggibili da qualunque operatore, e non per
dimenticanza — perché il perimetro era stato scritto come **elenco a mano**, e un
elenco ha per confine ciò che chi lo scriveva aveva in mente. Il cantiere (9 → 11
settembre) arma **nove famiglie**, ritira una tabella residua, e soprattutto
sostituisce l'elenco con un **criterio transitivo**: `dbops.vw_rls_perimetro_scoperto`
più il registro `dbops.rls_perimetro_debito` vedono *ogni* tabella con una FK
verso una protetta, comprese quelle che nasceranno domani. Il debito passa da
**33 a 10 righe**, e le dieci che restano sono decisioni di modello dichiarate,
non lavoro rimandato. ⭐ Nello stesso giro il contesto RLS dei test esce da
venti copie e trova una sede sola (`apri_contesto_operatore`). Vedi
[brief-db-perimetro-emittente-righe-documento.md](work-done/brief-db-perimetro-emittente-righe-documento.md),
[brief-db-viste-security-invoker-criterio.md](work-done/brief-db-viste-security-invoker-criterio.md).

**Anello 0 — I processi automatici hanno un'identità e un perimetro.** I job che
girano da soli — sveglie, code, pipeline — entravano nel database senza dire *chi
sono*: nessuna identità applicativa, quindi nessun perimetro da rispettare e
nessuna riga di log che sapesse attribuirli. Il cantiere (4 → 7 settembre) dà a
ogni processo del backend un **artefatto di deploy** e un'identità, e chiude i
residui lato BE. ⇒ Da qui un processo automatico è un attore come gli altri,
soggetto alle stesse regole. Vedi
[brief-db-processi-automatici-identita-e-perimetro.md](work-done/brief-db-processi-automatici-identita-e-perimetro.md),
[brief-db-sveglia-dei-processi.md](work-done/brief-db-sveglia-dei-processi.md),
[brief-db-processi-automatici-residui-be.md](work-done/brief-db-processi-automatici-residui-be.md),
[piano-be-fe-processi-automatici-identita-e-perimetro.md](work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md).

**Anello 3 (vendite) — Un documento rotto non tiene più in ostaggio il giro di
fatturazione.** Un lotto che incontrava un documento non emettibile si fermava, e
con lui tutti gli altri documenti di quel giro: il difetto di uno diventava il
blocco di tutti. Il tema si apre in tre tempi — **l'uscita dal giro** (un
documento può uscire e il lotto prosegue), **il trattenuto** (una sede sola per la
domanda *«questa riga può entrare in un giro?»*, invece della stessa condizione
riscritta in più punti) e **il marcatore**, che non scrive più su un documento già
uscito. ⭐ La lezione che resta: *una condizione scritta in tre posti diverge, e
diverge in silenzio*. Vedi
[brief-db-uscita-documento-dal-giro.md](work-done/brief-db-uscita-documento-dal-giro.md),
[brief-db-documento-trattenuto-da-un-lotto-vivo.md](work-done/brief-db-documento-trattenuto-da-un-lotto-vivo.md),
[brief-db-il-trattenuto-passa-lo-stesso.md](work-done/brief-db-il-trattenuto-passa-lo-stesso.md),
[brief-db-il-marcatore-scrive-su-un-documento-uscito.md](work-done/brief-db-il-marcatore-scrive-su-un-documento-uscito.md).

**Anello 3 (vendite) — L'esito di un documento nel lotto ha casa propria.**
L'esito di ogni documento dentro un giro si deduceva dagli stati altrui, e sui
giri di massa la deduzione non reggeva. Ora è un dato, con la sua sede, e vale
anche per i giri massivi; la **segnalazione di un lotto dichiara di quale
documento parla**, invece di lasciarlo capire. Chiusi anche due residui di
performance (la `LATERAL` costosa sul riferimento gruppi) e le bandiere
dell'esito parziale. Vedi
[brief-db-esito-gruppo-lotto.md](work-done/brief-db-esito-gruppo-lotto.md),
[brief-be-db-gruppo-key-sulle-segnalazioni.md](work-done/brief-be-db-gruppo-key-sulle-segnalazioni.md),
[brief-residuo-fatturabili-e-bandiere-esito-parziale.md](work-done/brief-residuo-fatturabili-e-bandiere-esito-parziale.md).

**Anello 0 — Il primo motivo di un controllo esce da un posto solo.** Le funzioni
`script.fn_check_*` producono un array di motivi, e chi doveva sollevarne il primo
ricopiava la stessa coda di codice — tredici volte, con tredici occasioni di
divergere. Nasce `script.fn_raise_primo_motivo_se_presente`, e la regola che
decide è una riga: *il codice che sollevo lo sto **leggendo** da un array o lo sto
**scrivendo** come letterale?* ⭐ Sbagliare funzione **non compila** — i tipi non
legano — quindi l'unico modo di sbagliare è non usarla, e quello ha il suo
presidio. Vedi
[brief-db-coda-primo-motivo-in-un-posto-solo.md](work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md),
[brief-db-i-motivi-si-fermano-dentro-la-check.md](work-done/brief-db-i-motivi-si-fermano-dentro-la-check.md).

**Anello 1 + 3 — La numerazione finisce il trasloco, e l'IVA arriva ai
consumatori.** Il 31 agosto atterra l'esecuzione decisa il giorno prima: la
commessa passa **sui registri**, con il prefisso e l'allineamento dei contatori, e
la chiave del contatore diventa esplicita. ⇒ La voce «il trasloco sui registri»
esce dalla roadmap: **è fatta**, CRUD dei registri compreso — che era anche una
voce dei «Previsti». Nello stesso periodo il risolutore IVA arriva ai suoi
consumatori applicativi (fase 3), i titoli IVA del soggetto prendono i movimenti
di annullo, e il default IVA smette di dipendere da un id di seed per passare a
una **chiave naturale**. Vedi
[brief-db-registri-di-numerazione-emittente-e-trasloco.md](work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md),
[brief-db-registri-numerazione-chiave-del-contatore.md](work-done/brief-db-registri-numerazione-chiave-del-contatore.md),
[brief-be-fe-crud-registri-di-numerazione.md](work-done/brief-be-fe-crud-registri-di-numerazione.md),
[brief-be-fe-iva-fase-3-consumatori-risolutore.md](work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md),
[brief-db-default-iva-chiave-naturale.md](work-done/brief-db-default-iva-chiave-naturale.md).

**In breve, senza un tema proprio** — il **fondo fattura** con ricalcolo e governo
applicato il 31 agosto; l'**archiviazione delle righe di coda** e la
storicizzazione dei bersagli spariti; il **perimetro delle email** e l'invio di
sistema; i **riferimenti contratto** sugli atti di fattura; tre giri di **seed
liste** (lotto, titolo IVA, admin `ui`); due **design** che preparano il magazzino
— la partita merce generalizzata e la situazione merce di un ordine; e la
migrazione della clausola `ORDER BY` lato backend.

## 30 agosto 2026

> Copre il periodo **11 – 30 agosto**. Venti giorni densi — **460 changeSet**
> fra `00_schema` e `20_code`, di cui 268 in `vendite` e 57 in `pagamenti` —
> ma non dispersi: quasi tutto ricade in **nove temi**, ed è per temi che sono
> scritti qui sotto, non changeSet per changeSet.
>
> ⚠️ **Il 31 agosto è volutamente fuori.** Quel giorno era ancora in corso
> mentre questa voce veniva scritta, e una giornata a metà in un changelog
> diventa una riga che nessuno sa più se rileggere. Ciò che è atterrato il 31
> — l'esecuzione del trasloco dei registri, i consumatori BE/FE del
> risolutore IVA, l'apply del fondo fattura — entra nella voce successiva.

**Anello 3 (vendite) — La nota di credito: si chiude il ramo morto degli
accrediti.** Il reso portava indietro la merce e il motivo, e **nessun valore**:
il ciclo attivo sapeva far tornare le cose ma non i soldi. Il cantiere (17 → 26
agosto) apre `vendite.resi_righe_accrediti` e `config.nature_doc_fiscale`,
chiude DB, BE e FE, e si valida a video con un collaudo spuntato riga per riga.
Subito dopo si chiude anche la **genealogia**: il grafo dei documenti si fermava
sul reso — la nota di credito era collegata alla fattura che rettifica ma non
alla merce che l'aveva causata — e con l'arco mancante arrivano i tre residui
del lineage (il `root` che dipendeva dagli id, la commessa senza origine, la
nota di credito che in lista si chiamava «Fattura»). Chiuso il 29, collaudo in
app compreso. Vedi
[brief-design-note-credito-resi.md](work-done/brief-design-note-credito-resi.md),
[brief-db-lineage-arco-reso-nota-credito.md](work-done/brief-db-lineage-arco-reso-nota-credito.md),
[brief-db-lineage-residui-root-e-sorgente-ddt.md](work-done/brief-db-lineage-residui-root-e-sorgente-ddt.md).

**Anello 3 (vendite) — La data del documento smette di essere un effetto
collaterale.** Origine: una fattura di luglio numerata il 25 agosto che prendeva
il numero 11 quando esistevano già fatture di agosto. Il tema è uno solo — *chi
decide la data e la sequenza di un documento fiscale* — e si è aperto in tre
tempi: la **numerazione** (data e sequenza governate dal registro, non dedotte
dal giro), il **limite di emissione** perché un documento nasca già conforme
invece di scoprire in fondo di non essere più trasmissibile, e il **registro
visibile in lista** perché la data prevista si sappia *prima* di generare. Il 30
agosto l'analisi sui **due motori di numerazione** — il sistema codici e i
registri — prende la decisione portante: la commessa passa sui registri, e la
periodicità dentro `config.sistema_codici` **non si fa più**, perché senza la
commessa quella colonna non ha più un cliente. Al 30 le decisioni sono prese e
il piano è scritto; l'esecuzione è del giorno dopo. Vedi
[brief-db-numerazione-data-documento-e-sequenza.md](work-done/brief-db-numerazione-data-documento-e-sequenza.md),
[brief-db-limite-emissione-e-data-verificata.md](work-done/brief-db-limite-emissione-e-data-verificata.md),
[analisi-db-numerazione-documenti-e-due-motori.md](work-done/analisi-db-numerazione-documenti-e-due-motori.md).

**Anello 1 + 3 — L'IVA ha un risolutore, e il regime del cliente smette di
essere scritto e mai letto.** La domanda di partenza era stretta (*«su un omaggio
o un reverse charge l'IVA non discende più dall'articolo: è giusto che si possa
modificare?»*); cercandone la risposta è emerso che **l'IVA la decideva
l'articolo e nessun altro**, e che le colonne del regime fiscale del cliente
erano compilate dall'operatore e **lette da nessuno**. Il modello che ne esce
non mette un default sul cliente: l'influenza del soggetto sull'IVA passa
**sempre da un titolo registrato e documentato**, e i titoli hanno ora una sede
in `anagrafiche` (`soggetti_titoli_iva` con i suoi ambiti e un registro
movimenti **append-only**, dove anche l'annullo di una forzatura è un movimento)
più il vocabolario `config.tipi_titolo_iva`. Al 30 agosto il lato **DB è
chiuso**; i consumatori applicativi vengono dopo. Vedi
[brief-db-be-iva-risolutore-e-regime-cliente.md](work-done/brief-db-be-iva-risolutore-e-regime-cliente.md).

**Anello 3 (`pagamenti`) — Il posting esiste.** Il 10 agosto questo cantiere si
apriva su una misura sgradevole: *nessuna funzione, in tutto il database,
scriveva `pagamenti.vendite_movimenti`* — il posting era documentato e non
implementato, e per costruzione il saldo di una fattura era sempre il totale.
Adesso il motore c'è: registrazione della contabile, saldo della rata, guard di
transizione e di capienza, **sistemazione delle eccedenze**, distinta di
correzione. E il perimetro: `pagamenti.enti_incasso` non aveva row security —
ogni operatore vedeva i canali di incasso, **IBAN compreso**, di tutti gli
emittenti.
⛔ **Ma di questo dominio è stato provato il percorso, mai l'esito**: lo schema
ha ancora zero righe, nessuno ha aperto una distinta o abbinato un incasso, e il
collaudo in-app è **aperto**. Vedi
[brief-db-posting-e-abbinamento-rata.md](work-in-progress/brief-db-posting-e-abbinamento-rata.md),
[brief-be-fe-posting-e-abbinamento-rata.md](work-in-progress/brief-be-fe-posting-e-abbinamento-rata.md),
[collaudo-in-app-incassi-distinte-e-sistemazioni.md](work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md).

**Anello 3 (vendite) — Il lavoro che non torna indietro.** Le tre porte di reset
della fatturazione — elimina fattura, riporta il lotto a DRAFT, annulla il lotto
— cancellavano righe su cui era già stato registrato un accredito, e l'esito non
era un rifiuto ma una violazione di chiave esterna **a metà lavoro**. Chiuse. Ma
la parte che si vede è un'altra: il lavoro rimasto indietro ora ha un **verbo**
(«Riporta da emettere», con la card che si spezza in due per non promettere una
fattura che non c'è) e **«Rendi definitive» è tornata sulla lista Lotti**, dove
sta l'elenco del suo oggetto, invece di stare su una card che ne mostrava un
altro. Entrambi collaudati a video. Vedi
[brief-db-lavoro-che-non-torna-indietro.md](work-done/brief-db-lavoro-che-non-torna-indietro.md),
[brief-be-fe-rendi-definitive-sui-lotti.md](work-done/brief-be-fe-rendi-definitive-sui-lotti.md),
[brief-db-guard-righe-fattura-rettificate.md](work-done/brief-db-guard-righe-fattura-rettificate.md).

**Anello 0 — L'errore porta un bersaglio, e la riga di log dice per chi.** Due
cantieri gemelli, stessa idea: un messaggio non serve se non si sa *su cosa*.
Il **Passo 0 dell'osservabilità** rende parlante la riga di `vendite.event_log`
— perimetro emittente, `tx_id`, identità del giro — e la mette sotto RLS
**prima** che esista qualunque endpoint di lettura, perché quella tabella è
append-only per trigger e sui campi della riga *non esiste rimedio a
posteriori*, mentre policy, indici e viste si aggiungono in qualunque momento.
Il **bersaglio** fa la stessa cosa sull'errore: oltre a dire cosa è successo,
dice su quale entità, in una forma che l'interfaccia trasforma in un gesto
(«vai lì») e chi diagnostica legge come coordinata. Quattro lati chiusi in due
giorni, DB → roll-out → backend → toast con azioni. Vedi
[brief-db-event-log-scope-e-riga-parlante.md](work-done/brief-db-event-log-scope-e-riga-parlante.md),
[brief-db-bersaglio-errore.md](work-done/brief-db-bersaglio-errore.md).

**Anello 0 — I presidi che non presidiavano.** Tre presidi del progetto cercavano
i test con un glob a **un livello solo**: le sottocartelle di schema — 16 file —
erano fuori dalla baseline, fuori dal guardrail del preambolo, fuori dal
censimento dei `LIMIT 1`. Dodici erano rossi, e nessuno lo sapeva; la baseline
diceva «nessuna regressione» e non mentiva — *quei file non li aveva guardati*.
Sanato il ramo cieco, il debito è stato attaccato: **da 86 rossi su 442 file a
19 su 551**. Nello stesso filone, il catalogo dei messaggi ha smesso di
promettere segnaposto che nessun chiamante riempiva (un `%s` che arrivava a
video letterale) e gli **smoke test** hanno preso una baseline: undici script
che nessuno lanciava, e per un giorno sei erano rossi senza che si notasse. Vedi
[brief-db-pgtap-rami-ciechi.md](work-done/brief-db-pgtap-rami-ciechi.md),
[brief-db-bonifica-baseline-pgtap-vendite.md](work-done/brief-db-bonifica-baseline-pgtap-vendite.md),
[brief-db-segnaposti-messaggi-errore.md](work-done/brief-db-segnaposti-messaggi-errore.md).

**Anello 1 — Il perimetro emittente, e due invarianti che nessuno presidiava.**
Il perimetro dell'emittente fiscale aveva due buchi nello stesso presidio —
l'accesso alle liste e la gerarchia dei billing account — tenuti insieme perché
uno teneva aperto l'altro. Chiusi, con la colonna emittente sulle cinque liste
rimaste e nella riga della ricerca universale. Da lì sono uscite due domande di
dominio che erano rimaste implicite: **un billing account può cambiare
emittente?** (sì, finché non ha storia — e il motivo per cui non si può arriva
*sulla riga*, non premendo il pulsante) e **l'emittente della commessa può
essere NULL?** (no: la commessa lo deriva dalla cascata delle sorgenti, e una
commessa non aggrega emittenti diversi). Vedi
[brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md),
[brief-db-billing-account-cambio-emittente.md](work-done/brief-db-billing-account-cambio-emittente.md),
[brief-db-emittente-commessa-invariante.md](work-done/brief-db-emittente-commessa-invariante.md).

**Anello 1 (`ui`) — Una regola che non sta dove si legge non esiste.** Il 10
agosto questo changelog registrava un'inversione: 40 file sul building block
delle liste, registro del presidio 43/43. Rimisurato il **30 agosto**: i file
sul building block sono saliti a **53**, ma quelli con `DataTable` grezza —
scesi a 48 il 3 agosto — sono **risaliti a 57**. Il 30 agosto la **«regola zero
della lista»** è stata spostata in cima ad `AGENTS.md`, dove si legge a inizio
sessione: stava in `frontend-standards.md`, che si apre quando serve, e che anzi
spiegava *come* configurare una `DataTable`. ⭐ **È il difetto che vale più del
numero — non era nel codice, era nella sede della regola.**

⚠️ **E il numero, guardato bene, non dice quello che sembra.** Classificati i 57:
**26 sono drawer e dialog** e 15 pannelli o tab annidati — cioè l'**eccezione
che `AGENTS.md` ammette**, non liste fuori standard — **6 sono i wrapper
stessi**, e restano **5 view di lista** più 5 `*SearchTable` di dominio. Col
paginator, il segno della lista vera, i file sono 13 e sei sono wrapper. ⛔ *Il
presidio a un numero solo non separa il debito dalla crescita del frontend*: la
regola resta giusta, il contatore che la accompagna misura un'altra cosa.

**Manutenzione e chiusure.** DDT: le righe a prezzo zero sono ammesse (il
solo-trasporto non è un difetto di prezzo) e il DDT di **ri-consegna** non nasce
più nudo — eredita causale e indirizzi invece di farli ridigitare. `is_attiva`
rispondeva a **due domande con un flag solo** (è la revisione corrente? è ancora
in gioco?): separate, e il filtro «Annullato» è passato da 0 risultati *per
costruzione* a 17. `acquisti` e `magazzino` sono stati **misurati** il 21 agosto
e documentati: modello disegnato, tutte le tabelle a zero righe — e in
`magazzino` un CHECK rendeva inseribili **solo i trasferimenti**. Archiviati per
verifica contro il codice vivo: il documento di progettazione della pipeline
(febbraio) e l'indice attività preventivi.

---

## 10 agosto 2026

> Copre il periodo **27 luglio – 10 agosto**. Due settimane dominate da due
> cantieri trasversali (**la classe dei codici errore** e **i satelliti della
> fattura**) e da un cambio di regime nei test: da qui in poi il pgTAP gira come
> l'applicazione.

**Anello 0 + 1 — La classe dei codici errore: il significato dell'errore torna a
catalogo.** Il cantiere più grande del periodo (05→09 agosto, DB + BE conclusi).
Prima, il significato di un errore viveva **solo** in un dizionario Python di
659 voci scritte a mano: il catalogo DB non aveva il campo in cui la
contraddizione si sarebbe vista. Ora un codice si registra **a catalogo** in
`config.codici_errore` (**690 voci**) dichiarando **che cosa è** — la sua
`classe`, dal vocabolario di `config.classi_errore` (**10 valori**) — e status
HTTP e `ui_action` si **derivano**. Il modulo Python `error_policies_generated.py`
è **generato** dal catalogo e presidiato in CI (`--check`). Tre conseguenze che
valgono oltre il cantiere:

- **il codice viaggia in un campo strutturato**, non nel testo: `SQLSTATE
  P0001` con `CONSTRAINT` valorizzato = errore di dominio, letto in un solo punto
  (`db_error_fields.py`) invece dei quattro che lo riscrivevano ognuno a modo
  suo;
- **i due registri del debito sono a zero**: `dbops.codici_errore_senza_policy`
  (141 → 0 in tre giorni, 150 decisioni) e `dbops.messaggi_errore_codici_legacy`
  (57 → 0). Restano entrambi, vuoti: un registro in pari non è un registro
  inutile, ed è il posto dove atterra il prossimo codice;
- **l'envelope d'errore porta `fields`**, i nomi dei campi del form da
  correggere — l'informazione senza la quale `ui_action: highlight_form_fields`
  non era azionabile.

Vedi [brief-db-be-classe-codici-errore.md](work-done/brief-db-be-classe-codici-errore.md),
[piano-db-classe-codici-errore.md](work-done/piano-db-classe-codici-errore.md),
[piano-be-classe-codici-errore.md](work-done/piano-be-classe-codici-errore.md),
[brief-db-codice-errore-strutturato.md](work-done/brief-db-codice-errore-strutturato.md),
[brief-db-be-terzo-lato-presidio-codici.md](work-done/brief-db-be-terzo-lato-presidio-codici.md).

**Anello 0 — 🔴 Il pgTAP gira come l'applicazione, ed entra in CI.** Dal 7 agosto
il runner di default è l'utente applicativo (`PGTAP_RUNNER=app`) e non più
l'owner: **le policy RLS sono esercitate a ogni corsa**. Un rosso ora può essere
un **permesso** o una **policy**, non solo una fixture, e una fixture che scrive
dove l'applicazione non scrive non passa più. I 29 file che hanno davvero bisogno
dell'owner sono marcati uno per uno **con la ragione scritta**. La suite entra
anche in **CI** — sempre sulle PR verso `main`, sui push a `Tito-dev` solo se
toccano `db/` o `scripts/` — con una baseline sua, perché il DB della CI è
ricostruito da zero e quello di sviluppo ha dati veri: **i rossi sono popolazioni
diverse**. Tre righe di preambolo diventano obbligatorie e presidiate da un
cancello (`BEGIN`, contesto, `SET CONSTRAINTS ALL IMMEDIATE`): senza, un file
diventa **verde per sottrazione**. Debito noto: **86 rossi** su **442 file**.
Vedi [brief-db-pgtap-runner-rls-baseline.md](work-done/brief-db-pgtap-runner-rls-baseline.md)
e la guida [pgtap-come-si-scrive-un-test](../guide/pgtap-come-si-scrive-un-test.md).

**Anello 0 — Presidio dei riferimenti morti (04 agosto).** 34 difetti sanati e
cancello in CI: un riferimento a un oggetto DB che non esiste più non arriva più
al merge. ⚠️ Il guardrail gira **dopo** `manage.py migrate` — non spostarlo.
Vedi [brief-db-bonifica-riferimenti-morti.md](work-done/brief-db-bonifica-riferimenti-morti.md),
[brief-be-bonifica-riferimenti-morti.md](work-done/brief-be-bonifica-riferimenti-morti.md).

**Anello 3 (vendite) — I satelliti della fattura: il documento si racconta per
intero.** Cantiere chiuso su tutte le fasi (29 luglio – 3 agosto). La fattura
acquista ciò che le mancava per essere consultabile e stampabile senza risalire
altrove:

- **piano rate** (`vendite.fatture_scadenze`): generato nello step EMESSA dopo il
  ricalcolo IVA, idempotente per costruzione (DELETE + INSERT), con lo **snapshot
  del termine** in testata perché il documento si spieghi da sé. ⚠️ Non è uno
  scadenzario: non esiste stato di pagamento della rata;
- **snapshot di intestazione e indirizzi** congelati sul documento;
- **drawer di consultazione**: testata decodificata + righe con kit risolti +
  riepilogo IVA + piano rate **in un round-trip**, orchestrando gli **stessi**
  lettori che alimentano il PDF — video e stampa raccontano lo stesso documento
  per costruzione;
- **note fattura**: sesto dominio del building block note partizionate,
  ~15 righe di sola configurazione, zero migration;
- **ritiro del generatore di righe SQL** e fix degli importi di riga a zero.

Vedi [piano-db-satelliti-fattura.md](work-done/piano-db-satelliti-fattura.md),
[piano-be-fe-satelliti-fattura.md](work-done/piano-be-fe-satelliti-fattura.md),
[brief-db-generazione-scadenze-fattura.md](work-done/brief-db-generazione-scadenze-fattura.md),
[brief-be-fe-drawer-fattura.md](work-done/brief-be-fe-drawer-fattura.md).

**Anello 3 (vendite) — Emissione mirata e ritorno del lotto a DRAFT.** Il giro di
fatturazione accetta ora un perimetro ristretto ai **gruppi fatturabili** scelti
(stesso verbo, stessa idempotenza: assente = giro di massa invariato), e il lotto
può **tornare a DRAFT** (slice 6-A) per rifare un giro andato storto. Vedi
[brief-db-emissione-fattura-per-documento-sorgente.md](work-done/brief-db-emissione-fattura-per-documento-sorgente.md),
[brief-be-fe-emissione-fattura-mirata.md](work-done/brief-be-fe-emissione-fattura-mirata.md),
[piano-db-ritorno-lotto-a-draft.md](work-done/piano-db-ritorno-lotto-a-draft.md).

**Anello 2 (documenti) — Ristampa fedele: il terzo percorso.** Ri-renderizzare un
documento **com'era** — versione di template pinnata, anche OBSOLETA, e
`context_json` congelato — senza persistere nulla. È distinto dallo **scarica
originale** (il file su storage) e dal **genera nuovo documento** (modello e dati
di oggi, che fino ad allora si chiamava impropriamente «ristampa»). La fedeltà è
dichiarata in header: byte diversi = fedele nel contenuto, non un errore. Vedi
[brief-ristampa-fedele-documenti.md](work-done/brief-ristampa-fedele-documenti.md).

**Anello 1 (`ui`) — Le liste: il rapporto si è invertito.** Il numero scomodo del
piano — 14 liste sullo standard contro 71 con `DataTable` grezza — non c'è più:
**40 file montano il building block**, il registro del presidio è a **43/43**, e
il Gruppo A si è chiuso **30/34** il 3 agosto. I **4 file rimasti sono fermi per
decisione** (cassetti senza endpoint paginato), non per debito.

> 🚨 **Ma il piano non è più tecnico.** `primevue`, `@primeuix/themes` e
> `primeicons` erano **MIT** e passano tutti e tre alla **licenza PrimeUI**
> (community/commerciale, con chiave) dalla nuova major. ZeroErp è **GPL v3
> pubblica**. Non è un rischio di migrazione: è una **decisione di licenza**, e
> non la prende un piano operativo. Il lavoro tecnico resta valido e utile con
> qualunque esito.

Vedi [piano-migrazione-primevue-5.md](work-in-progress/piano-migrazione-primevue-5.md)
§1-bis e [consuntivo-personalizzazioni-liste-def.md](work-done/consuntivo-personalizzazioni-liste-def.md).

**Anello 3 (`pagamenti`) — Si apre il cantiere delle contabili di pagamento
(9-10 agosto).** Rimisurato il terreno e prese le decisioni portanti. Due
scoperte cambiano la scala del lavoro: **nessuna funzione, in tutto il database,
scrive `pagamenti.vendite_movimenti`** — il *posting* è documentato ma non
implementato, quindi `fn_get_saldo_fattura` restituisce per costruzione sempre
l'intero totale — e **i cataloghi dello schema erano già seminati** (la macchina
a stati dell'abbinamento `DA_ABBINARE → ABBINATA → POSTATA` esiste da sempre a
catalogo). Decisioni: l'abbinamento vive **sulla riga contabile e arriva alla
rata**; lo stato della rata è **derivato**; il posting è una madre DB per testata
contabile; **lo storno non esiste come concetto** — è una contabile con importi
negativi, e la sicurezza sta in un controllo simmetrico `0 ≤ Σ ≤ importo`; il
perimetro dei soldi non ancora attribuiti si deriva **dal conto di incasso**.
Vedi [brief-incassi-riconciliazione-rate-promemoria.md](work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md)
e, per il meccanismo dei fondi fattura da ripensare,
[brief-db-fondo-fattura-ricalcolo-e-governo.md](work-done/brief-db-fondo-fattura-ricalcolo-e-governo.md).

**Manutenzione.** Bonifica indici: corrette le viste `dbops`, aggiunte guardie
sull'`apply`, rimossi **48 indici ridondanti** (27 luglio). Commesse: permesso di
cambio stato, **annullamento delle righe manuali** (non cancella: porta a
`ANNULLATA` con motivo obbligatorio), guard di uscita. Lato BE, fan-out isolato
con esito parziale.

---

## luglio 2026

> **Riepilogo del mese** (le voci datate 10, 11, 12 e 26 luglio sono state
> compattate qui il 2026-09-01). Il dettaglio non è andato perso: vive nei brief
> linkati, che sono tutti in `work-done`.

**Anello 3 (vendite) — Il DDT di vendita, e con lui il quinto dominio del motore
documentale.** Nuovo documento del ciclo attivo: testata di trasporto + righe con
**prezzo e IVA opzionali** (il DDT di solo trasporto è legittimo) + componenti
BoM condivisi. Nasce per **evasione** di un ordine confermato — legame 1:N con
**residuo per riga** append-only, dove l'evasione *aggiunge* la quantità evasa
invece di sottrarla — oppure standalone. Stati data-driven
`DRAFT → EMESSO → SPEDITO → CONSEGNATO` (+ `RESO`/`ANNULLATO`), **numero
assegnato all'emissione** e poi immutabile, push a commessa per la fatturazione.
Guida: [gestione-ddt.md](../guide/gestione-ddt.md). Vedi
[brief-db-ddt-vendita-evasione-e-stati.md](work-done/brief-db-ddt-vendita-evasione-e-stati.md),
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md),
[brief-fe-ddt-vendita.md](work-done/brief-fe-ddt-vendita.md).

> ℹ️ **Tre cose di questo cantiere non hanno un brief e vivono solo qui.**
>
> - **Stampa PDF DDT — 5° dominio del motore documentale**: template
>   `DDT_VENDITA` pubblicato + builder del contesto (testata, trasporto, righe,
>   totali, note). Anteprima in bozza e documento definitivo all'emissione
>   seguono il pattern degli altri domini (`pdf_mode` data-driven da
>   `stati_doc_ddt`). Export lista DDT (CSV/XLSX) allineato agli ordini.
> - **Addendum SCOPE §15 — emittente memorizzato + RLS**:
>   `vendite.ddt.emittente_fiscale_id` NOT NULL sul documento (mirror
>   ordini/preventivi), ereditata dall'ordine in evasione o risolta dal billing
>   account per lo standalone, con policy `rls_ddt_ef_whitelist` e guard di scope
>   in scrittura — un operatore non emette DDT fuori dal proprio scope.
> - **Due estrazioni per regola del 2**: la factory
>   `build_documenti_sorgente_views` per le 7 view «documenti per sorgente» di
>   ogni dominio (~80 righe risparmiate a dominio) e
>   `add_emittente_scope_condition`, che risolve l'array di scope emittente
>   **una volta** in Python — era 2× per query in 5 repository.

**Anello 3 (vendite) — I resi: il documento di rientro merce.** Sesto documento
del ciclo attivo, nato dal DDT, **senza valori economici** (il ramo nota di
credito è la slice successiva): conferma che riapre il residuo dell'ordine,
annullo come storno, **ri-consegna** parziale e multipla, due code di lavoro
configurabili, azioni data-driven. A chiusura, la **rinuncia alla ri-consegna** —
senza la quale una ri-spedizione mai eseguita lascia l'ordine
`PARZIALMENTE_EVASO` per sempre, senza via d'uscita in-app. Vedi
[brief-db-resi-vendita.md](work-done/brief-db-resi-vendita.md),
[brief-be-fe-resi-vendita.md](work-done/brief-be-fe-resi-vendita.md),
[brief-db-chiusura-riconsegna-reso-definitivo.md](work-done/brief-db-chiusura-riconsegna-reso-definitivo.md).

**Anello 3 (vendite) — La fatturazione di DDT e resi passa a contatore.**
`config.tipi_reso.riapre_residuo` era un flag **logistico** che decideva anche
cosa succedeva ai **soldi**: due domande su una colonna sola. Sostituito da un
**contatore di merce** per riga d'ordine (spedito − reso), che chiude due bug di
doppia fatturazione invisibili alle dashboard — le mostravano come transito
legittimo. Vedi
[brief-db-fatturazione-ddt-resi.md](work-done/brief-db-fatturazione-ddt-resi.md),
[brief-be-fe-ddt-resi-dashboard.md](work-done/brief-be-fe-ddt-resi-dashboard.md).

**Anello 3 (vendite) — Quantità immutabili sulla commessa, e la porta oneri.**
Le quantità già fatturate diventano immutabili. Sopra quella base si apre la
porta oneri, con il modello **articolo↔causale 1:1**: un articolo *è* un onere
perché ha una causale collegata, e così **ogni onere porta la propria IVA**.
Chiusa anche una race sul progressivo degli oneri manuali, dove due operatori
concorrenti ricevevano entrambi 200 OK e un dato spariva in silenzio. Vedi
[brief-db-immutabilita-quantita-e-porta-oneri.md](work-done/brief-db-immutabilita-quantita-e-porta-oneri.md),
[brief-be-fe-immutabilita-quantita-e-porta-oneri.md](work-done/brief-be-fe-immutabilita-quantita-e-porta-oneri.md),
[brief-db-race-segment-key-onere.md](work-done/brief-db-race-segment-key-onere.md).

**Anello 3 (vendite) — Il cockpit: dalle lenti all'azione, e la stampa che non
tiene il lock.** Le tre lenti smettono di essere una fotografia: dalla Dashboard
Competenza si **agisce**. Il punto architetturale non è l'interfaccia ma la
**stampa massiva senza tenere il lock del registro fiscale durante il
rendering** — la stampa diventa un task che *accoda* e il render vive in un
worker che drena. La fattura è il **6° dominio** del motore documentale.
Completano il quadro il **guard di uscita commessa** (chiuderne una con righe
ancora fatturabili era perdita irreversibile di fatturato, invisibile alla
dashboard) e le capability con motivo. Guida:
[cruscotti-fatturazione.md](../guide/cruscotti-fatturazione.md) §7. Vedi
[brief-design-gestione-processi-fatturazione.md](work-done/brief-design-gestione-processi-fatturazione.md),
[brief-db-processi-fatturazione-cockpit.md](work-done/brief-db-processi-fatturazione-cockpit.md),
[brief-be-fe-processi-fatturazione.md](work-done/brief-be-fe-processi-fatturazione.md),
[brief-db-guard-uscita-commessa-e-capabilities.md](work-done/brief-db-guard-uscita-commessa-e-capabilities.md).

**Anello 0 (`dbops`) — La coda lavori generica: la regola del 2 applicata
all'architettura.** `vendite.fatture_stampa_coda` stava per essere seguita da una
seconda tabella-coda per il giro on-demand. Invece di **una tabella per batch** si
è estratta una **coda di job generica**, DB-native, transazionale e senza broker:
è la fondazione asincrona dell'ERP. Guida:
[gestione-code-di-lavoro.md](../guide/gestione-code-di-lavoro.md). Vedi
[brief-design-coda-lavori-generica.md](work-done/brief-design-coda-lavori-generica.md),
[brief-db-coda-lavori-generica.md](work-done/brief-db-coda-lavori-generica.md).

**Anello 1 (`ui`) — La dashboard home, e il secondo consumatore dello schema.**
Card KPI configurabili con lo **stesso impianto a cascata** delle liste (sistema
→ profilo → emittente → utente) e filtro sui permessi dell'operatore. È la
conferma richiesta dal principio 7: il pattern non è stato inventato per la home,
è stato **riusato** perché già decantato dalle liste. Vedi
[brief-db-dashboard-home.md](work-done/brief-db-dashboard-home.md),
[brief-be-fe-dashboard-home.md](work-done/brief-be-fe-dashboard-home.md).

**Anello 3 (vendite) — La genealogia dei documenti, e gli indirizzi come building
block.** Il **lineage** espone il grafo dei documenti come pannello «Passaggi» nei
drawer e come colonne pratica/fase/transito nelle liste: da un documento si risale
a monte e si scende a valle senza uscirne. In parallelo gli **indirizzi documento**
diventano un BB cross-dominio sui 5 domini vendite — sezione inline + drawer di
gestione, **snapshot congelato all'emissione**, auto-assegnazione del default — e
il DDT prende il suo riepilogo IVA (righe senza prezzo escluse: un DDT di solo
trasporto non ha riepilogo). Vedi
[brief-db-lineage-documenti-vendite.md](work-done/brief-db-lineage-documenti-vendite.md),
[brief-be-fe-lineage-documenti-vendite.md](work-done/brief-be-fe-lineage-documenti-vendite.md),
[brief-design-indirizzi-documenti-vendita.md](work-done/brief-design-indirizzi-documenti-vendita.md),
[brief-db-ddt-riepilogo-iva.md](work-done/brief-db-ddt-riepilogo-iva.md).

**Qualità di modello — tre presidi che c'erano e non presidiavano.** (1) Il guard
sulla **sorgente polimorfa** esisteva ma **non era agganciato a nulla**:
agganciato, dati bonificati, convenzione documentata
([sorgente-polimorfa.md](../guide/sorgente-polimorfa.md)) e 13 pgTAP bonificati
(rossi 131 → 111). (2) **Coerenza `tx_id`**: mai pubblicare nella GUC un id non
registrato — il difetto bloccava ogni ambiente *senza* canale di log, CI
compresa, e ora la CI esercita il caso peggiore invece di aggirarlo. (3) **RLS
scope emittente** estesa a `commesse` e `commesse_attivita`. Vedi
[brief-db-guard-sorgente-polimorfa.md](work-done/brief-db-guard-sorgente-polimorfa.md),
[brief-db-bonifica-pgtap-sorgente-polimorfa.md](work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md),
[brief-db-coerenza-tx-id-non-registrato.md](work-done/brief-db-coerenza-tx-id-non-registrato.md),
[brief-db-rls-commesse.md](work-done/brief-db-rls-commesse.md).

**Trasversale (frontend) — radici i18n uniformi e residui PrimeVue 3.** 21 radici
i18n piatte riportate sotto le rispettive aree: ⚠️ un indirizzo i18n inesistente
non dà errore, **non mostra nulla** — difetto invisibile, e l'archivio aveva due
stili di sistemazione conviventi scelti a caso. Chiusi anche i residui PrimeVue 3
e corretto lo standard che ancora li prescriveva: era debito che **faceva
scrivere codice nuovo sbagliato**. Vedi
[brief-i18n-radici-uniformi.md](work-done/brief-i18n-radici-uniformi.md),
[brief-fe-migrazione-primevue4-tabs.md](work-done/brief-fe-migrazione-primevue4-tabs.md).

---

## giugno 2026

> **Riepilogo del mese** (le voci datate 11, 13-19, 20 e 28 giugno sono state
> compattate qui il 2026-09-01). Copre l'11 → 28 giugno; per il periodo
> precedente vedi «Aggiornamenti ricostruiti dal 26 aprile all'11 giugno».

**⭐ Anello 2 (`pratiche`) — Il motore passa da *predisposto* a *validato dal
primo consumatore*.** È la milestone del mese, e vale più di ciò che è stato
scritto: gli **ordini di vendita** nascono end-to-end (CRUD, conferma, EVASO,
stampa PDF, conversione preventivo/offerta→ordine) e sopra di essi gira la
**pratica PREVENTIVI**, primo consumatore reale del motore — handler
`CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa,
smistamento riga-per-riga, commesse multi-sorgente. ⚠️ L'uso reale ha scovato
bug che la «completezza tecnica» non aveva intercettato (handler_params persi,
funzioni di push con NOT NULL violabili, generazione non idempotente, azioni di
processo mai seedate): è la conferma sul campo della lezione «pratiche prima di
vendite». Vedi
[analisi-ordini-vendita.md](work-done/analisi-ordini-vendita.md),
[analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md).

**Anello 2 (`pratiche`) — Workflow v2: le estensioni che l'uso reale ha
chiesto.** Il completamento del flusso diventa **event-driven** (rimosso
l'endpoint manuale) e l'azione che chiude lo step è **risolta da configurazione,
non cablata**. Il documento sorgente si àncora a uno **specifico flusso**, non
alla sola testata. La pratica si chiude solo a flussi obbligatori completati.
L'esito del flusso diventa configurabile (MANUALE / AUTOMATICO / CONTESTUALE), il
giornale porta l'**utente reale** ed è append-only per trigger, e il flusso si
**assegna** a operatore o reparto con policy reparto-first, alimentando una coda
a quattro livelli e il pannello «Le mie attività». Vedi
[brief-design-esito-configurabile-flussi.md](work-done/brief-design-esito-configurabile-flussi.md),
[brief-db-assegnazione-flusso.md](work-done/brief-db-assegnazione-flusso.md),
[brief-design-coda-lavoro-mie-attivita.md](work-done/brief-design-coda-lavoro-mie-attivita.md).

**Anello 3 (vendite) — Il batch di fatturazione diventa automatico end-to-end.**
La pipeline passa da «operativa (manuale)» a batch: driver CRON `run-until-done`,
discovery a **corsie** `(emittente, tipo_doc, utility)`, **sync dello stato
documentale per-step** `1→2→8` — l'IVA è certificata in EMESSA *prima* della
numerazione in DEFINITIVA — e run headless registrate in `job_run_log`. Con
l'hardening del push commesse→fatturazione arriva l'invariante che evita il
«fatturato perso in silenzio»: `APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`,
guard di riga più CHECK di backstop. Vedi
[piano-fix-stato-fattura-pipeline-per-step.md](work-done/piano-fix-stato-fattura-pipeline-per-step.md),
[brief-db-emittibili-lane-tipo-doc-fiscale.md](work-done/brief-db-emittibili-lane-tipo-doc-fiscale.md),
[brief-db-guard-tipo-doc-attivita.md](work-done/brief-db-guard-tipo-doc-attivita.md).

**Qualità di modello — `codice_interno` contro `codice`, su tutto il perimetro.**
Le tabelle di lookup hanno due colonne con destini opposti — `codice_interno`
**immutabile** per la logica, `codice` **mutabile** per il display — e il progetto
le confondeva in due modi speculari: alias bugiardi (`codice_interno AS *_codice`,
che esponeva l'immutabile col nome del mutabile) e hardcode `WHERE codice = 'X'`
dove la logica doveva usare l'altra. Bonificati **21 BUG_DUAL + 7 candidati**,
16 oggetti della pipeline commesse→push→fatturazione, ed è emerso un **bug reale**
(`fn_lookup_utilities_per_ba` tornava zero righe perché `codice ≠ codice_interno`).
Chiuso con un **guardrail CI catalog-based bloccante**. Vedi
[brief-naming-stato-codice-interno.md](work-done/brief-naming-stato-codice-interno.md),
[analisi-hardcoded-codice.md](work-done/analisi-hardcoded-codice.md).

**Manutenzione.** Corretta l'asimmetria del gate EVASO sul ramo commessa
(verificata runtime, non solo applicata) e avviato lo smoke E2E
push commesse→fatturazione. Sospensioni pratica: anti-sovrapposizione e guard
sulla data manuale. Revisione critica del documento di sicurezza AI/agenti
tradotta in piano di allineamento. Vedi
[brief-db-gate-evaso-commessa-asimmetria.md](work-done/brief-db-gate-evaso-commessa-asimmetria.md),
[brief-db-sospensioni-anti-overlap-data-manuale.md](work-done/brief-db-sospensioni-anti-overlap-data-manuale.md),
[analisi-sicurezza-aggiornata.md](work-done/analisi-sicurezza-aggiornata.md).

---

## 29 maggio 2026

Anello 3 (vendite): contratti passati al modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO); nuovo documento **offerte commerciali** (proposta di condizioni quadro → push 1:1 a contratto) sviluppato DB+BE+FE con generazione PDF e allegati; componenti BoM compositi estesi a offerte; valuta su documenti vendite. Vedi [Gestione Offerte commerciali](../guide/gestione-offerte-commerciali.md) e [Gestione Contratti](../guide/gestione-contratti.md).

## Aggiornamenti ricostruiti dal 26 aprile all'11 giugno 2026

| Data         | Evidenza                                                                                                                                             | Impatto sulla mappa                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 26 aprile    | `dbops.automazione_chiusura_scadenze` chiuso come framework parametrico dopo due consumatori reali (`vendite.listini_versioni`, `vendite.contratti`) | Anello 0 cresce per uso osservato, non per astrazione preventiva.                                      |
| 27 aprile    | Contratti: Profilo A, immutabilita' post-DRAFT, cessazione data-driven, righe-preview                                                                | Vendite rafforza il sottodominio contratti e consuma il framework di chiusura a scadenza.              |
| 28 aprile    | Refactor frontend/backend catalogo completato Fasi 1-8, test BE 83/83 e build Vite verdi                                                             | Catalogo resta operativo ma con contratti API/metadata piu' maturi.                                    |
| 29-30 aprile | Refactor amm-software completato per matrici, operatori, permessi, emittenti e policy admin                                                          | Anello 1 amministrativo consolidato; le matrici diventano riferimento UI per configurazioni complesse. |
| 1 maggio     | Refactor vendite chiuso DB+BE+FE, modello documentato con 1406 test BE e build Vite verde                                                            | Vendite aggiornata a pattern data-driven per lookup, defaults, capability e azioni.                    |
| 2 maggio     | Preventivi rev2 landed: `emittente_fiscale_id` persistito, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza, 4 codici errore        | Preventivi diventano piu' rigorosi sul contesto emittente/utility.                                     |
| 3 maggio     | Scenario preventivi 2.1 chiuso end-to-end, UI revisioni e riepilogo IVA                                                                              | Vendite avanzata su flusso preventivo operativo.                                                       |
| 3-4 maggio   | Motore documentale parametrico: DB Fase A, backend Tranche A-K, frontend Tranche L-M; test UI dedicato avviato                                       | Nuovo componente `documenti` in Anello 2, operativo tecnicamente ma ancora in test UI.                 |
| 13 maggio    | BoM modello unificato + simmetria listino; componenti BoM (CASO A) estesi a preventivi/ordini/ddt/contratti                                          | I documenti vendite condividono lo stesso modello componenti a 3 livelli (struttura, listino, documento). |
| 15-21 maggio | Refactor contratti: modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO + overlap parziale) | Il sottodominio contratti diventa simmetrico ai preventivi e pronto a ricevere l'offerta come sorgente. |
| 24-27 maggio | Offerte commerciali (DB): testata + eccezioni delta-listino + componenti BoM + utility, 6 stati, `fn_push_offerta_a_contratto` idempotente, vista `is_attiva`, azioni data-driven | Nuovo documento pre-contrattuale in Anello 3 (vendite): la proposta di condizioni quadro che genera il contratto. |
| 28-29 maggio | Offerte commerciali (BE+FE): risoluzione prezzo come contratti, generazione documento offerta con allegati, UI uniformata a contratti                | Offerta operativa end-to-end DB+BE+FE; in consolidamento/test UI.                                       |
| 29 maggio    | Valuta su documenti vendite (`valuta_id` su offerte/contratti/preventivi, default da resolver gestore); guida offerte commerciali pubblicata          | Coerenza valuta cross-documento; documentazione di dominio allineata allo stato reale.                  |
| 2 giugno     | Gate prezzi L1/L2/L3 esteso alle offerte (stesso orchestratore dei contratti); vincoli EXCLUDE anti-overlap ripristinati e governati dal framework `dbops.automazione_overlap` | Coerenza pricing cross-documento; Anello 0 consolida l'anti-overlap parametrico.                        |
| 2-4 giugno   | RLS scope emittente fiscale ATTIVA per operatori: `ENABLE` su 10 tabelle documentali + Ondata 2 scrittura (`FOR ALL` + `WITH CHECK`, migration `20260603-16..25`); reset GUC fail-closed a inizio richiesta lato BE | Multi-Face Auth passa da "infrastruttura predisposta" a RLS operatori attiva; policy portale/shop restano dry-run. |
| 3-4 giugno   | Ordini di vendita DB+BE+FE: vista lista DEF-8, CRUD, conferma, stampa PDF (modulo stampa generico), conversione preventivo/offerta→ordine, lock cliente; regola del 2 su anagrafiche e core (estrazione BB) | Vendite chiude il documento ordine: il ciclo preventivo/offerta→ordine e' percorribile end-to-end.      |
| 5 giugno     | Regola del 2 core FE/BE (factory `createCrudStore`, guard-versione, stack geografico); unificazione sconto righe ordini/fatture; riepilogo IVA documenti non fiscali esteso a ordini | Anello 0/1 frontend consolidano building block condivisi; meno duplicazione cross-dominio.              |
| 8 giugno     | Univocita' offerta→(contratto XOR ordine) con status 409 coerenti; stato ordine EVASO con transizione automatica CONFERMATO→EVASO                     | Il downstream dell'offerta diventa mutuamente esclusivo; il ciclo ordine ha uno stato terminale data-driven. |
| 9-10 giugno  | Pratica PREVENTIVI: handler `CONFERMA_VENDITA` BE+FE (commit `327140116`); `natura_vendita` su preventivi con split merce→ordine / servizi→commessa; smistamento merce→ordine riga-per-riga; commesse multi-sorgente (1 ROOT + N COLLEGATO); natura di vendita amministrabile da applicazione | Vendite diventa il primo consumatore reale del motore pratiche (Anello 2).                               |
| 11-12 giugno | Workflow pratiche v2: ripetibilita' flussi, bivi condizionali, lenti contesto, guard chiusura; contesto pratica a 3 livelli (soggetto → ruolo → istanza derivata/filtrata); BB informazioni pratica; azioni di processo pratiche seedate | `pratiche` passa da "predisposta" a **validata con primo consumatore** (vedi Anello 2).                  |

---

## Sprint storici (marzo – metà aprile 2026)

> Sintesi a livello di milestone delle fondamenta costruite prima del periodo coperto
> dalla tabella sopra. Volutamente **non dettagliata** (niente conteggi test, nomi di
> singoli componenti o numeri di sprint): alcune di queste implementazioni sono state
> in seguito riviste o rifatte diversamente — per lo stato attuale fa fede la
> [mappa](../mappa-concentrica.md), non queste righe. Da fine aprile in poi la cronologia
> prosegue nella tabella sopra.

### Marzo 2026 — fondamenta

- Anello 2 `pratiche`: backend completo (macchina a stati, sospensioni, calcoli tempo), consumabile via REST.
- Anello 0: audit sessioni JWT, request logging, revoca/blacklist token.
- Frontend Sprint 1–7: layout applicativo (sidebar, content tabs, breadcrumb), Amm. Software (operatori, profili reparto, permessi, audit log), building block riutilizzabili (SoggettoForm, autocomplete, composable core), Gestione Geografica (7 tab CRUD), Gestione Soggetti PF/PG/ENTE, pannello config generico, modalita' sola lettura + azioni di processo (permessi livello 1+2), split view, Pratiche v2 frontend.
- Refactor modello concentrico (v3/v4): logica duplicati/CAP/indirizzi/nominativo spostata da frontend a DB/backend.
- Integrazione AI v1 (Anello 4): widget flottante + primi tool lettura/scrittura con conferma.

### Aprile 2026 (fino a metà mese) — domini di vendita e autenticazione

- Gestione Autenticazioni fasi 1–3: email building block, token monouso, reset/invito/cambio password.
- Deprecato il codice errore generico `E_GENERICO` a favore di codici specifici per schema.
- Gestione Clienti v1 + catena automatica istanza fittizia → billing account → cliente.
- Catalogo Articoli + UoM + Listini (DB+BE+FE), poi consolidato e testato.
- Parametri di sistema multi-scope (override personale/emittente).
- Emittenti fiscali CRUD + mapping billing account + matrice utilities; refactor operatore-emittenti 1-a-1 (GUC d'identita').
- Migrazione a `daterange`/`tstzrange` nativo PostgreSQL con vincoli GIST anti-overlap.
- Listini v3: variazioni di massa, alert scadenze, rettifiche controllate; Permessi v2 (`model_permission` a livello oggetto).

---

*Changelog della Mappa Concentrica — ZeroERP. Nuove voci in alto (prosa) o in coda alla tabella del periodo corrispondente.*
