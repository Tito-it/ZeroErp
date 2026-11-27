# Brief DB — Revisione dello schema `anagrafiche`: la documentazione, le segnalazioni di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-27

**Ripartono in due, senza aspettarsi.** Il rosso del rubinetto degli accumulatori sul giro 6 è chiuso lato DB
(§24.9: `20261126-42` applicato da Tid su scratch e dbdev, pgTAP verde, rubinetto senza accumuli, committato il
2026-11-27); la sua richiesta va al **team BE/FE**. **Tid** con le decisioni di T8 (§25.5): l'analisi sul catalogo è scritta il
2026-11-26 (§25); D-T8-0 decisa il 2026-11-27, T8 si fa in **tre giri**, nell'ordine T8c (ruoli d'impresa), T8b
(emittente), T8a (conti). Restano le decisioni del giro, a partire da D-T8c-1 (solo PSP) e -5 … -8; il reseller è uscito da T8c in
[brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27), aperto, non iniziato; poi la **sessione DB** costruisce
un giro alla volta, al via (lo sviluppo non è iniziato). Il giro 6 (T4, l'azienda
del billing account) è chiuso lato DB, `20261126-26 … -41` applicati su scratch e dbdev, pgTAP verdi (Tid, 2026-11-26,
§24.7), committato il 2026-11-26; il suo passaggio al BE (§24.5, §24.7) è del **team BE/FE**. Alla sessione DB resta
anche da vagliare un rosso già presente su HEAD, la copia di `FATT` nella madre plurale (§21.7, esito). Il giro 5-bis (il
titolo IVA che chiede la partita IVA) è ritirato da Tid il 2026-11-26: il controllo esiste già, §23.4. In coda il brief
nuovo di T6 (che porta anche l'ultimo contatto del soggetto, §22.7). Il **team BE/FE** con la fase 7 e il passaggio al
BE del giro 6: i passaggi al BE dei giri 3 (§20.7) e 4 (§21.7) sono fatti e committati il 2026-11-26 (PR #257, esito in
coda alle due sezioni). Il giro 5 è chiuso: il DB committato (`7f8d9506d`, PR #249),
il passaggio al BE fatto e committato su `dev/backend-tid` il 2026-11-26 (§22.6, esito in coda alla sezione). Il giro 4 (T7a, `20261123-74 … -94`, §21.5) è applicato, verde e committato (`359c556da1`, 2026-11-24). T7 è diviso in T7a, gli indirizzi, e T7b, i contatti e il catasto (Tid, 2026-11-24); l'analisi di T7a sul catalogo è scritta il 2026-11-24 (§21). Il giro 3-bis, D-T5-6 **b** (il tipo di contatto proposto, §20.8), è chiuso: `20261123-68 … -73` applicato, pgTAP verdi, doc auto-generata rigenerata, committato (`f9b1049de3`, 2026-11-24). Il giro 3, T5, è chiuso: `20261123-48 … -64` applicato su scratch e dbdev, pgTAP verdi come app, committato (2026-11-24). Poi T7, T4, T8, T12, T3, T10, T11. Il giro 2 (T2) è chiuso: dentro `anagrafiche` non c'è
niente da cambiare. La postura delle viste in tutto il database è decisa (Tid, 2026-11-23, §19.3) e il suo lavoro è
di [brief-db-porte-aperte-dalla-sola-guc](brief-db-porte-aperte-dalla-sola-guc.md) §5, in un'altra sessione: qui non
resta niente da fare, né da aspettare. Per T7 c'è un fatto nuovo sulla porta di S50 (§17, riga T7). Il vaglio per temi è deciso (Tid, 2026-11-23, §17.1). Il piano da percorrere, con le fasi spuntate, è il §0.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | Apply e pgTAP del giro 1 (Q7): applicato, test verdi (2026-11-23) | §18 | — |
| 2 | ✅ Tid | Il vaglio per temi, con S4 e S53 (2026-11-23) | §17.1 | — |
| 3 | team BE/FE | R-BE6 e due correzioni di documentazione del backend | §0, fase 7 | — |
| 4 | sessione DB | I giri di codice dei temi che restano qui, uno per tema, nell'ordine di §17.1 | §0, fase 8; §17.1 | via di Tid per ogni giro |
| 5 | sessione DB | I brief nuovi di T6 (spegnimento del soggetto) e T9 (accessi, con R-4, S64, S67); S1 portata in `sviluppo-gestione-clienti-v2` | §17.1 | — |
| 6 | sessione DB | Il giro dei metadati, per ciò che i giri di codice non hanno già riscritto | §8 | 4 |
| 7 | sessione DB | Archiviazione in `work-done/`, col debito dei temi spostati scritto nei loro brief | §11 | 5, 6 |

**Decisioni aperte di Tid:** T8 (§25.5): D-T8c-1 (solo PSP), -5 … -8 (il primo giro; -2, -3, -4 passate a `brief-db-reseller`), poi D-T8b-1 … -4 e D-T8a-1 … -12 (D-T8-0 decisa: tre giri, Tid 2026-11-27). Nessuna del giro 6 (T4): D-T4-1 … -12 decise il 2026-11-26 (§24.5, §24.7.1, §24.7). Il giro 5-bis è ritirato (Tid, 2026-11-26, §23.4). Nessuna del giro 5 (D-T7b-1 … -7 prese come proposte, Tid 2026-11-25, §22.2). D-T7a-1 … -7 decise (Tid, 2026-11-24, §21.2; D-T7a-2 nella forma nuova, il controllo nel guard del civico). D-T5-6 decisa **b** (Tid, 2026-11-24, §20.6). La porta di S50 è uscita da T7 (D-D **a**, 2026-11-23): la chiude il giro 1 del brief delle porte.
**Da committare:** `.codex/PROJECT_CONTEXT.md`; il §25 riverificato e il reseller spostato col brief nuovo `brief-db-reseller` (2026-11-27); il rosso del rubinetto è committato (2026-11-27, «DB: anagrafiche giro 6, il billing account che non c'è ha il suo codice», insieme al brief con l'allineamento del §24 e l'analisi di T8, §25); il giro 6 (T4) è committato (2026-11-26, «DB: anagrafiche giro 6 (T4)», insieme al giro 5-bis ritirato); i passaggi al BE dei giri 3 e 4 sono committati (2026-11-26, PR #257); il giro 5 è committato (DB `7f8d9506d`, BE 2026-11-26).

## 0. Il piano da percorrere

Si spunta una voce quando è fatta, nello stesso turno, con la data. Il dettaglio sta nella sezione indicata.

* **Fase 1 — Il censimento in sola lettura** (§3-§9)
  * [x] La forma delle 195 pagine, il contenuto falso e stantio per area, gli oggetti senza pagina, le guide, le
    segnalazioni di codice, i metadati (2026-11-22)
* **Fase 2 — Le decisioni Q1-Q8** (§10)
  * [x] Q1-Q8 decise da Tid; Q7 riaperta e decisa di nuovo, strada (b), estesa a `config.stradario` (2026-11-22)
  * [x] R-BE1 … R-BE5, le risposte del team BE/FE (§9.1, 2026-11-22)
* **Fase 3 — Il giro 0, la documentazione, un'area per sessione** (§12-§16)
  * [x] 0a, area C (§12) · [x] 0b, area A (§13) · [x] 0c, area B (§14) · [x] 0d, area D (§15) · [x] 0e, area E
    (§16), tutte scritte e committate il 2026-11-22
  * [x] La doc auto-generata rigenerata da Tid dopo ogni area (2026-11-22)
* **Fase 4 — Il passo A: il brief riallineato e il vaglio preparato** (2026-11-23)
  * [x] La testata e questo piano; §2, §9 e §15.4 riallineati; il §4 marcato come censimento di partenza
  * [x] S31 riletta sul corpo dopo il giro 8b di `ui`: resta aperta (§12.3). Le otto pagine `manual/` toccate dai
    changeSet del 2026-11-23 riallineate (§12.5)
  * [x] I metadati trovati nei giri 0a-0e raccolti in §8.1
  * [x] Il vaglio per temi, con una proposta per tema (§17)
  * [x] La correzione del giro 0a riportata in `brief-db-catena-istanze-pdp` (§2.1 e §5)
  * [x] Commit (Tid, 2026-11-23, `a35a6636dc`, insieme al giro 1)
* **Fase 5 — Il giro 1: Q7, lo storico continuo di indirizzi, civici e stradario** (§18)
  * [x] ChangeSet e pgTAP scritti, provati sullo scratch con `scripts/prova_changeset.py` (2026-11-23,
    `20261123-38` … `-42`; la prova ha trovato `storico.indirizzi` che non accettava versioni, §18.2)
  * [x] Le pagine `manual/` e le guide allineate al comportamento nuovo (2026-11-23)
  * [x] Apply e pgTAP (Tid, 2026-11-23: applicato, test verdi)
  * [x] Doc auto-generata rigenerata (Tid, 2026-11-23): le schede di `indirizzi`, `indirizzi_dettaglio`,
    `config.stradario` e `storico.indirizzi` hanno il default e la forma nuovi
  * [x] Commit (Tid, 2026-11-23, `a35a6636dc`)
* **Fase 6 — Il vaglio per temi** (Tid, §17)
  * [x] Per ogni tema: qui, nel brief vicino o in un brief nuovo; l'ordine dei giri (Tid, 2026-11-23, §17.1)
  * [x] S4: la chiave è la coppia CF e P.IVA. S53: tema proprio (T12). S64 e S67 vanno nel brief degli accessi (T9)
    (Tid, 2026-11-23)
  * [ ] Il brief nuovo di T6 e quello di T9; S1 scritta in `sviluppo-gestione-clienti-v2`
* **Fase 7 — Le ricadute sul backend** (team BE/FE)
  * [ ] R-BE6: le due scritture del portale su credenziale e veste (§16.3)
  * [ ] `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md`, riga 90: nomina
    `trgfn_emittenti_fiscali_guard_attivo`, che non esiste (§15.2)
  * [ ] `docs/it/backend/core/manual/api_tracciamento.md`: la data va dopo lo Scopo, o l'indice la prende come
    descrizione (§12.4)
* **Fase 8 — I giri di codice dei temi che restano qui** (uno per tema, nell'ordine deciso in fase 6)
  * [x] Giro 2: T2, i permessi delle viste: analisi sul catalogo (2026-11-23, §19). Dentro `anagrafiche` niente da
    cambiare; S40 e `security_invoker` voluti
  * [x] Giro 2: la postura delle viste in tutto il database, decisa da Tid: l'app solo `SELECT` sulle viste
    (2026-11-23, §19.3)
  * [x] La postura delle viste passata a `brief-db-porte-aperte-dalla-sola-guc` §5, con la richiesta al BE unita a
    quella delle porte (2026-11-23, §19.3). Il BE ha risposto «nessuna scrittura su una vista» lo stesso giorno: il
    lavoro è tutto di quel brief, e il giro 2 di qui è chiuso
  * [x] Giro 3: T5, analisi sul catalogo e sul ramo BE (2026-11-23, §20)
  * [x] Giro 3: le decisioni D-T5-1 … D-T5-6, tutte le proposte (Tid, 2026-11-23, §20.2)
  * [x] Giro 3: pgTAP rosso, changeSet, CSV, note, guida e linee guida scritti e provati sullo scratch (2026-11-24, §20.4-§20.5)
  * [x] Giro 3: applicato da Tid su scratch e dbdev (2026-11-24, 01:26)
  * [x] Giro 3: pgTAP come app verdi (Tid, 2026-11-24; il resto dei rossi era già rosso prima), committato
  * [x] Giro 3: apply di -64, i COMMENT al presente (Tid, 2026-11-24)
  * [x] Giro 3: D-T5-6 decisa di nuovo, **b** (Tid, 2026-11-24, §20.6)
  * [x] Giro 3: la porta dei lucchetti riletta sul catalogo: è già chiusa per l'app dal 2026-11-17, niente da registrare (2026-11-24, §20.6)
  * [x] Giro 3-bis: D-T5-6 b, il tipo di contatto proposto: analisi, changeSet `20261123-68 … -73`, pgTAP, manual e guide, provati sullo scratch (2026-11-24, §20.8)
  * [x] Giro 3-bis: applicato, pgTAP verdi (Tid, 2026-11-24); doc auto-generata rigenerata (2026-11-24)
  * [x] Giro 3-bis: committato (Tid, 2026-11-24, `f9b1049de3`)
  * [x] Giro 3: il passaggio al BE (§20.7): fatto e committato il 2026-11-26 (PR #257)
  * [x] Giro 4: T7 diviso in T7a (indirizzi) e T7b (contatti e catasto) (Tid, 2026-11-24)
  * [x] Giro 4: T7a, analisi sul catalogo e guide verificate (2026-11-24, §21)
  * [x] Giro 4: T7a, D-T7a-3 … -7 decise come proposte (Tid, 2026-11-24, §21.2)
  * [x] Giro 4: T7a, D-T7a-1 e D-T7a-2 nella forma nuova, decise (Tid, 2026-11-24, §21.2)
  * [x] Giro 4: T7a, pgTAP rosso: due file, 28 rossi sui loro motivi (2026-11-24, §21.4)
  * [x] Giro 4: T7a, changeSet `20261123-74 … -94`, CSV, pgTAP adeguati, guida e note, provati sullo scratch (2026-11-24, §21.5)
  * [x] Giro 4: T7a, apply e pgTAP verdi come app (Tid); doc auto-generata rigenerata (2026-11-24)
  * [x] Giro 4: T7a, il passaggio al BE (§21.7): fatto e committato il 2026-11-26 (PR #257); un rosso DB già presente da vagliare
  * [x] Giro 5: T7b, il confine con T6 (Tid, 2026-11-25, §22) e l'analisi sul catalogo, guide verificate (2026-11-25, §22.1)
  * [x] Giro 5: T7b, le decisioni D-T7b-1 … -7 (Tid, 2026-11-25, §22.2: tutte come proposte)
  * [x] Giro 5: T7b, pgTAP rosso, changeSet `20261125-36 … -46`, guida e note, provati sullo scratch (2026-11-25, §22.4)
  * [x] Giro 5: T7b, apply e pgTAP (Tid); doc auto-generata rigenerata (2026-11-25)
  * [x] Giro 5: T7b, committato (Tid, `7f8d9506d`, PR #249)
  * [x] Giro 5: T7b, il passaggio al BE (§22.6): le otto voci fatte o censite senza modifiche, committato (2026-11-26)
  * [x] Giro 5-bis: il titolo IVA che chiede la partita IVA, anticipato da T10; analisi e decisioni D-T10a-1 … -3 (Tid, 2026-11-26, §23)
  * [x] Giro 5-bis: ⚠️ ritirato da Tid dopo la prova sullo scratch: il controllo esiste già nella matrice e nel guard
    del titolo, file tolti, numeri `20261125-77 … -80` liberi (2026-11-26, §23.4)
  * [x] Giro 6: T4, analisi sul catalogo, guide verificate, ciò che esiste già (2026-11-26, §24.1)
  * [x] Giro 6: T4, le decisioni (Tid, 2026-11-26, §24.5)
  * [x] Giro 6: T4, pgTAP rosso, changeSet `20261126-26 … -41`, doc, prova sullo scratch (2026-11-26, §24.7)
  * [x] Giro 6: T4, apply su scratch e dbdev e pgTAP verdi col runner (Tid, 2026-11-26)
  * [x] Giro 6: T4, commit (2026-11-26, «DB: anagrafiche giro 6 (T4)»)
  * [ ] Giro 6: T4, il passaggio al BE (§24.5, §24.7): da girare
  * [x] Giro 6: il rosso del rubinetto sul `-39`, codice nuovo `E_BILLING_ACCOUNT_NOT_FOUND`: `-42`, CSV, pgTAP, baseline, doc, prova sullo scratch (2026-11-27, §24.9)
  * [x] Giro 6: `-42`, apply su scratch e dbdev, pgTAP verde col runner, rubinetto senza accumuli (Tid, 2026-11-27)
  * [x] Giro 6: `-42`, commit (2026-11-27)
  * [ ] Giro 6: la richiesta al BE di §24.9: da girare
  * [x] T8: analisi sul catalogo, guide verificate, ciò che esiste già; proposta di dividerlo in T8a, T8b, T8c (2026-11-26, §25)
  * [x] T8: D-T8-0, tre giri, nell'ordine T8c, T8b, T8a (Tid, 2026-11-27, §25.5)
  * [x] T8c: il reseller tolto e portato in [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27)
  * [ ] T8c: le decisioni D-T8c-1 (solo PSP), -5 … -8 (Tid, §25.4); poi il giro
  * [ ] T8b: le decisioni D-T8b-1 … -4 (Tid, §25.3); poi il giro
  * [ ] T8a: le decisioni D-T8a-1 … -12 (Tid, §25.2); poi il giro
  * [ ] Poi un giro per tema nell'ordine di §17.1: T12, T3, T10, T11
* **Fase 9 — Il giro dei metadati** (§8)
  * [ ] I COMMENT, i commenti nei corpi e le note di seed che i giri di codice non hanno già riscritto
* **Fase 10 — L'archiviazione** (§11)
  * [ ] I criteri di §11; il brief in `work-done/`, il debito spostato nei brief dei temi

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-22. **A chi:** Tid e team DB.
> **Origine:** revisione della documentazione dello schema `anagrafiche` chiesta da Tid: cercare le parti stantie e
> quelle che non descrivono lo sviluppo di oggi. Metodo dei brief di revisione di `catalogo`, `dbops`, `documenti`,
> `maintenance` e `ui` ([brief-db-revisione-ui](../work-done/2026/brief-db-revisione-ui.md)).
> **Brief vicini verificati:**
> [brief-db-catena-istanze-pdp](brief-db-catena-istanze-pdp.md) ha già i rami irraggiungibili di
> `trgfn_clienti_set_parent_istanza` (suo §2.1) e cinque decisioni aperte: qui quel trigger si documenta com'è e la
> segnalazione rimanda lì. [sviluppo-gestione-clienti-v2](sviluppo-gestione-clienti-v2.md) tiene subentro e disdetta
> come sviluppo da fare: la segnalazione S1 (§7) tocca le stesse due funzioni e va letta insieme.
> [analisi-critiche-modello-clienti-utilities-catasto-v2](analisi-critiche-modello-clienti-utilities-catasto-v2.md)
> parla dell'orchestratore Django del cliente, che la guida `generazione-cliente` dà ancora per «previsto» (§6).
> [piano-be-fe-accessi-credenziale-e-vesti](../work-done/2026/piano-be-fe-accessi-credenziale-e-vesti.md) e
> [sviluppo-multi-face-da-completare](sviluppo-multi-face-da-completare.md) sono lavoro BE/FE sugli accessi: non
> toccano le pagine `manual/`. Nel [registro dei residui](registro-residui-aperti.md) tre voci hanno per oggetto
> tabelle di `anagrafiche` (i residui di `brief-db-dati-fiscali-e-societari-del-soggetto`, «La coerenza tra codice
> fiscale e sesso», «Le FK verso `django.auth_user`»): nessuna riguarda la documentazione, e nessuna segnalazione di
> §7 le ripete. Nessun brief aperto ha per tema la documentazione di `anagrafiche`.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/anagrafiche/…`),
rigenerata il 2026-11-22 (`469b4c80e5`). Lo stesso giorno il catalogo di dbdev e le schede coincidono per elenco di
oggetti: 35 tabelle, 19 viste, 195 funzioni. Prima di scrivere una pagina si riverifica: un changeSet successivo
sull'oggetto rende stantia la scheda.

## 1. Il perimetro

Lo schema `anagrafiche` ha 35 tabelle, 19 viste e 195 funzioni (di cui un centinaio di trigger function). La
documentazione scritta a mano che lo descrive è:

* **195 pagine** in `docs/it/dbzero/anagrafiche/manual/` (circa 21.000 righe);
* **cinque guide** che hanno lo schema per oggetto: `soggetti-e-ruoli-anagrafici`, `gestione-dei-contatti`,
  `gestione-conti-bancari`, `generazione-cliente`, `risorse-umane-e-accessi`; e tre che lo toccano in alcune sezioni:
  `gestione-degli-indirizzi`, `gestione-delle-istanze-utility`, `architettura-multi-face-auth`.

Il censimento è diviso in cinque aree, che sono anche le unità di lavoro del giro 0:

| Area | Contenuto | Oggetti | Pagine | Senza pagina |
| --- | --- | --- | --- | --- |
| **A** | Soggetti, natura, dati societari, titoli IVA | 52 | 31 | 21 |
| **B** | Indirizzi, contatti, catasto | 66 | 38 | 28 |
| **C** | Clienti, billing account, istanze, PDP, categorie clienti, legame emittente-BA | 63 | 57 | 6 |
| **D** | Ruoli d'impresa (emittenti, fornitori, gestori, vettori, reseller, PSP) e banche | 47 | 46 | 1 |
| **E** | Accessi: identità digitali, risorse umane, sincronizzazione con `django.auth_user` | 23 | 23 | 0 |

Ogni fatto si regge sul **modello**: che cosa ammettono colonne, vincoli, trigger e corpi, letti dalle schede e dal
catalogo. Nessun conteggio di righe entra come motivo. I numeri di questo brief contano **pagine e oggetti**, non
dati, e valgono al 2026-11-22.

**Come è fatto il censimento.** Due passate. La prima è meccanica: su ogni pagina i sei controlli di
`standard-guide.md` §«Verifica di una pagina `manual/`», più il confronto di ogni nome citato (oggetti, colonne,
trigger, vincoli, indici, codici errore, file pgTAP, link) col catalogo di dbdev. La seconda è di contenuto: cinque
agenti, uno per area, hanno letto ogni pagina per intero contro la scheda auto-generata e il catalogo. I fatti
portati come gravi sono riverificati sul catalogo dalla sessione che coordina (marcati ✔︎ in §7).

## 2. Il piano: i giri

Deciso con Q5 e Q6 (Tid, 2026-11-22); i giri dopo il giro 0 sono nel §0, fasi 5-9. Il giro 0 qui è sei volte quello di `ui` (195 pagine contro 32): si fa
**un'area per sessione**. L'ordine è per distanza dal codice: prima le aree dove la pagina racconta un modello che
non c'è più.

| Giro | Contenuto | Perché in quest'ordine |
| --- | --- | --- |
| 0a | **Area C**, clienti e billing account: 57 pagine (11 da riscrivere), 6 oggetti senza pagina, guida `generazione-cliente`, le sezioni di `gestione-delle-istanze-utility` | Le quattro pagine di tabella raccontano «1 istanza ⇄ 1 cliente», che non è più il modello; sette pagine di trigger descrivono un corpo sostituito |
| 0b | **Area A**, soggetti: 31 pagine (5 da riscrivere), 21 oggetti senza pagina, guida `soggetti-e-ruoli-anagrafici` | La famiglia «cambio di natura» non ha nessuna pagina; `soggetti` e `dati_societari` si contraddicono al loro interno |
| 0c | **Area B**, indirizzi, contatti, catasto: 38 pagine (9 da riscrivere), 28 oggetti senza pagina, guida `gestione-dei-contatti`, le sezioni di `gestione-degli-indirizzi` | È l'area con più oggetti senza pagina; la parte indirizzi è la più recente e regge |
| 0d | **Area D**, ruoli d'impresa e banche: 46 pagine (9 da riscrivere), 1 oggetto senza pagina, 1 pagina da ritirare, guida `gestione-conti-bancari` | Sette guard di ruolo con lo stesso corpo e sette pagine che dicono cose diverse |
| 0e | **Area E**, accessi: 23 pagine (4 da riscrivere), guida `risorse-umane-e-accessi`, le sezioni di `architettura-multi-face-auth` | L'area più piccola; la guida è il pezzo grosso |
| 1 … | I giri di codice, un tema per giro, nell'ordine deciso col vaglio (§17.1) | — |
| ultimo | Metadati: i COMMENT (§8) | Si riscrivono una volta sola, dopo i giri di codice |

Ogni giro 0 comprende: le pagine esistenti nella cornice, col contenuto al presente; le pagine nuove; i difetti
trovati scritti nella pagina in una sezione «⚠️ Che cosa oggi non copre», che si toglie quando il giro che li
corregge è applicato; la guida dell'area; le sei verifiche su ogni pagina; poi la rigenerazione della doc
auto-generata (Tid). Il giro 0 **non scrive changeSet**: un COMMENT falso si annota in §8 e si corregge nel giro dei
metadati.

## 3. La forma: nessuna pagina è allo standard

Censimento meccanico del 2026-11-22 sulle 195 pagine. Nessuna passa tutti e sei i controlli dello standard.

| Controllo | Pagine che non lo passano |
| --- | --- |
| Titolo nella forma della cornice (`## 📘 Documentazione Concettuale – <Tipo> …`) | 129 |
| Un titolo `#` in testa (formato vecchio) | 8 |
| Più di un `##`, o nessuno | 16 |
| `### 🎯 Scopo Principale` assente o ripetuto | 27 |
| Primo paragrafo dello Scopo che comincia con un marcatore (`(latest review …)`, `(rev …)`) | 156 |
| Etichette del «Vedi anche» fuori dalla citazione | 104 |
| Firma `signature-core.md` assente | 61 |
| Blocchi di codice (119 `sql`, 13 senza linguaggio, 1 `python`, in 71 pagine) | 71 |
| Riga «Ultimo aggiornamento» assente | 172 |
| Marcatori di revisione, nomi di brief, id di changeSet nel corpo | 178 |
| Link alla pagina `manual/` invece che alla scheda (182 link) | 77 |
| Link a un file che non esiste | 11 |

Le 23 pagine con la data sono tutte di novembre 2026, e sono le più vicine al codice; nessuna è nell'area C né
nell'area E. Per area:

| Area | Pagine | Con la data | Con blocchi di codice | Senza firma |
| --- | --- | --- | --- | --- |
| A | 31 | 6 | 10 | 5 |
| B | 38 | 14 | 19 | 13 |
| C | 57 | 0 | 22 | 30 |
| D | 46 | 3 | 16 | 8 |
| E | 23 | 0 | 4 | 5 |

**L'indice dello schema porta i marcatori come descrizioni.** `anagrafiche/index.md` è generato dal primo paragrafo
dello Scopo: oggi `billing_account` è descritto come «(latest review 20-04-2026 — aggiunta colonna
`canale_origine`)», `categorie_clienti` come «(latest review 14-04-26)», `fornitori` come «(rev 2026-11-21)». Si
corregge da solo quando le pagine sono nella cornice e la doc è rigenerata.

**Riferimenti a nomi che non esistono** (catalogo di dbdev, 2026-11-22). Sono la prova più secca che una pagina è
ferma a un modello precedente:

| Pagina | Cita | Oggi |
| --- | --- | --- |
| `fn_crea_soggetto_pg` | `fn_crea_cliente_pg`, `fn_crea_emittente`, `fn_crea_fornitore_pg` | Non esistono: `fn_crea_cliente`, `fn_crea_emittente_fiscale`, `fn_crea_fornitore` |
| `fn_crea_auth_user`, `fn_get_or_create_indirizzo_dettaglio` | `fn_crea_admin`, `fn_crea_operatore` | Esiste solo `fn_crea_operatore_v2` |
| `fn_crea_operatore_v2`, `fn_crea_risorsa_umana_v2`, `identita_digitali`, `risorse_umane` | `config.ruolo_sistema`, `anagrafiche.risorse_umane_auth_user`, `fn_crea_risorsa_umana` | Il tipo è `config.ruolo_applicativo`; la tabella ponte e la funzione non esistono |
| `soggetti_titoli_iva`, `soggetti_titoli_iva_ambiti` | `anagrafiche.clienti.iva_id` | La colonna non esiste |
| `fn_consuma_plafond_titolo_iva_righe` | `fn_consuma_plafond_titolo_iva` | Ritirata: resta la forma `_righe` |
| `trgfn_soggetti_normalize` | `fn_get_default_by_param` | Non esiste |
| `soggetti` | `trg_soggetti_valida_cf_piva_ins_upd` | `trg_soggetti_valida_cf_piva_dispatch_ins_upd` |
| `fn_get_evento_stato_corrente_cliente` | `vw_clienti_con_stato_corrente` | Non esiste |
| `trgfn_pdp_a10_guard` | `trgfn_pdp_protect_cols`, `trg_pdp_protect_cols_upd` | Nomi di prima |
| `trgfn_billing_account_guard_soggetto_coerenza_istanza` | Trigger in fascia `a10` | La fascia è `a20` |
| `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`, `vw_indirizzi_resolved_ruolo`, `vw_indirizzi_resolved_soggetto` | `fn_get_indirizzo_preferito`, `fn_get_indirizzo_resolved` | I resolver sono in `script`: `fn_get_indirizzo`, `fn_get_indirizzi_by_ruolo`, `fn_get_indirizzi_by_soggetto` |
| `bank_branches` | `trgfn_bank_check_ruolo_bank_branches` e il suo trigger | `…guard…` |
| `clienti`, `contatti`, `gestori`, `gestori_utilities`, `istanze_utilities`, `pdp`, `soggetti_conti_bancari`, `catasto_unita_immobiliari`, `categorie_clienti_listini` | Tredici nomi di vincolo e di indice | Vincoli ritirati o con un altro nome (`uq_clienti_istanza_utility` → `uq_clienti_billing_account`, `uq_gest_util` → `uq_gestore_utility`, gli indici col prefisso `ix_anagrafiche_`) |
| Sette pagine dell'area C | Link `/it/guide/gestione-delle-istanze-utility` | Il prefisso `/it` è di troppo |
| `gestori`, `gestori_utilities`, `identita_digitali`, `soggetti` | Sette link `/dbzero/…` senza `tabelle/` o a una scheda che non c'è | — |

Falsi allarmi del controllo, verificati: `anagrafiche.accessi_sistema`, `accessi_altri` e `operatori` nelle pagine
delle due viste degli accessi sono codici di `ui.lista_definizione`, non oggetti; `liquidazione_enum`,
`socio_unico_enum`, `config.canale_origine` e `config.ruolo_applicativo` sono tipi, `vettori_codice_seq` è una
sequenza, `uq_catunitaindir` esiste.

**Una pagina senza oggetto, una senza posto.** `trgfn_emittenti_fiscali_guard_attivo` descrive una funzione che
non esiste più: la regola la regge il trigger generato dall'automazione ATTIVO su `emittenti_fiscali` (Q4).
`catasto-architettura` non corrisponde a nessun oggetto: è il racconto di un flusso fra tabelle e trigger di due
schemi (Q3).

## 4. Il contenuto: che cosa è falso o stantio, per area

> ⚠️ **Censimento di partenza, superato dal giro 0** (2026-11-23). Le pagine qui giudicate sono riscritte nei giri
> 0a-0e (§12-§16), che hanno anche corretto questo censimento dove sbagliava (i §12.2, 13.2, 14.2, 15.2, 16.2). Resta
> come fonte delle segnalazioni di codice; non descrive più le pagine.

Forma compatta: una riga per pagina, col giudizio e ciò che non è vero. I giudizi: **riscrivere** (la pagina
racconta un modello superato), **ritocco** (pochi punti), **regge** (contenuto vero, resta la forma). Dove non è
detto altro, la fonte è la scheda auto-generata dello stesso oggetto. La cronaca («latest review», «da oggi»,
«prima era…») c'è in quasi tutte le pagine e non è ripetuta riga per riga.

### 4.1 Area C — clienti, billing account, istanze, PDP

Il modello di prima, che più pagine ripetono: «un'istanza ha al massimo un cliente». Oggi un cliente è di un billing
account (`uq_clienti_billing_account`), un'istanza ha un BA per utility, e l'unicità sul PDP la dà l'esclusione per
periodo `ex_clienti_no_overlap_stesso_pdp`. Il secondo fatto ripetuto: la «storia» che blocca il cambio di emittente
di un BA è descritta come «fatture o commesse», ed è «un documento numerato di qualunque famiglia».

| Pagina | Giudizio | Che cosa non è vero o manca |
| --- | --- | --- |
| `clienti` | riscrivere | «PA, split payment» e `iva_id` (colonne che non esistono); l'ER senza `billing_account` e `pdp`. Tace il lock della fornitura, il guard stato/date, la chiave unica differita, l'esclusione sul PDP, le tre policy RLS, i verbi (`fn_crea_cliente`, `fn_update_cliente`, disdetta e subentro in `script`) |
| `billing_account` | riscrivere | FK con `ON DELETE SET NULL` / `RESTRICT` (hanno solo `ON UPDATE CASCADE`); «il super admin non crea BA» (crea, con l'azienda di lavoro in sessione); il CF «del codice» (si confronta il CF del soggetto dell'istanza); 7 trigger su 17; la policy `ef_whitelist` taciuta; «Strategia di rollout» e passi sul backend |
| `istanze_utilities` | riscrivere | §7.1 e §7.6 «al massimo un cliente» con un UNIQUE che non esiste, in contraddizione col §7.3; FK con azioni inventate; «parent non sé stessa» (niente lo vieta); 4 trigger su 14; tace `chk_iu_pdp_not_fittizia` e la colonna del catasto |
| `trgfn_clienti_set_periodo` | riscrivere | Dice di sollevare `E_DATA_CHIUSURA` / `E_DATA_APERTURA`: il corpo non solleva nulla (i controlli sono in `trgfn_clienti_guard_stato_date`); «chiusura inclusiva» accanto a `[attivazione, chiusura)` (S1) |
| `trgfn_clienti_sync_stato_pdp` | riscrivere | «AT→ATTIVO, CH→DISPONIBILE, non verifica altri clienti»: segue l'occupazione per periodo (`fn_check_pdp_occupato`) e ricalcola anche il PDP lasciato; colonne dell'`UPDATE OF` e valore di ritorno sbagliati |
| `trgfn_clienti_sync_utility_from_ba` | riscrivere | Tre codici errore che non solleva più; oggi delega a `script.fn_cliente_dal_billing_account` e copia anche il ruolo |
| `trgfn_clienti_set_parent_istanza` | riscrivere | «I clienti senza PDP non partecipano» (le istanze fittizie hanno la loro catena); «strettamente minore» (è `<=`); «schema suggerito» del trigger (esiste, con altri eventi e una `WHEN`) |
| `trgfn_clienti_guard_ruolo_cliente` | riscrivere | Ruolo `'GE'` (il corpo passa `'CL'`); «verificata o creata» (verifica soltanto) |
| `trgfn_billing_account_guard_normalize` | riscrivere | Il controllo delle date (tolto: è di `script.trgfn_guard_date_validita`); «normalizza il codice» (non lo tocca); nessuno dei sei codici che solleva |
| `trgfn_billing_account_guard_soggetto_coerenza_istanza` | riscrivere | L'esempio 3 non è raggiungibile (parla prima il lock, `E_BA_ISTANZA_IMMUTABILE`); tace il controllo sul tipo di ruolo `CL`; metà pagina è cronaca di deploy |
| `fn_guard_ba_cambio_emittente` | riscrivere | «Storia: fatture e commesse. Ordini e DDT no» |
| `pdp` | ritocco | `extra_info` (è `meta`); lo stato «per eventi commerciali»; tace `attivo`, i due guard di immutabilità, `clienti.pdp_id`. «Cliente corrente: `cliente_id`» (S14) |
| `vw_pdp` | ritocco | «Non è `security_invoker`, nessuna tabella ha RLS»: false tutte e due; «letta dentro il livello DB»: nessuna vista né funzione la nomina |
| `emittenti_fiscali_billing_account`, `fn_guard_albero_ba_emittente`, `fn_guard_albero_ba_gestore_globale`, `trgfn_efba_guard_albero_emittente`, `trgfn_billing_account_link_ef` | ritocco | La definizione di storia di prima; «il super admin è bloccato»; in `efba_guard_albero` «sono TRE movimenti» (il trigger presidia anche la creazione) |
| `categorie_clienti_listini` | ritocco | «Nessun trigger di tabella» (ne ha tre); tace la RLS |
| `categorie_clienti` | ritocco | Tace `codice_interno`; «Seed iniziale» con le righe ricopiate |
| `fn_crea_cliente`, `fn_crea_billing_account` | ritocco | Mancano il parametro dell'emittente e tre codici errore |
| `fn_update_cliente` | ritocco | «PA» fra i campi modificabili (non è nella lista) |
| `fn_get_evento_stato_corrente_cliente` | ritocco | «Il guard di consistenza va messo su `clienti`» (esiste); codice del backend in una pagina DB |
| `trgfn_clienti_sync_pdp` | ritocco | «Caso 2, cambio istanza» (l'istanza è bloccata); «Caso 3» irraggiungibile |
| `vw_clienti_codice_ba`, `vw_clienti_lista` | ritocco | «Due clienti possono condividere un BA»; «le tabelle non hanno RLS»; granularità «soggetto × utility» (è per BA) |
| `istanze_dati_precontrattuali` | ritocco | FK a `tipi_utenze` (non c'è); «valuta una unique» e «immutabilità consigliata» (esistono tutte e due) |
| `vw_istanze_dati_precontrattuali_dettaglio`, `vw_istanze_utilities_dettaglio` | ritocco | La utility esposta è quella **del PDP**, non della riga né dell'istanza (S16) |
| `trgfn_pdp_a10_guard`, `trgfn_pdp_set_default_stato` | ritocco | «`NULL → valore` consentito» (le colonne sono NOT NULL); la seconda pagina è troncata a metà frase |
| `trgfn_istanze_utilities_gen_codice`, `trgfn_billing_account_gen_codice` | ritocco | `CODICE_NON_MODIFICABILE` (è `E_CODICE_NON_MODIFICABILE`); il lock copre più colonne di quelle dette |
| `trgfn_istanze_utilities_normalize` | ritocco | «Tutti i record hanno un codice generato»: la funzione non fa niente (S15) |
| `fn_lookup_utilities_per_ba`, `fn_guard_istanza_ba_emittente`, `fn_check_ba_coppia_emittente_omogenea`, `fn_ba_ha_storia_emittente`, `fn_get_storia_emittente_ba`, `fn_guard_ba_gestore_globale_storia` | ritocco | L'azienda di un BA si risolve su tre livelli, non due; i parametri di sistema quando manca l'override; per l'ultima vedi S2 |

Reggono: `fn_clienti_stessa_chiave`, `fn_guard_cliente_chiave_unica`, `trgfn_clienti_guard_stato_date`,
`trgfn_categorie_clienti_listini_guard_listino`, `trgfn_guard_istanza_del_ruolo`, `fn_istanza_di_altro_soggetto`,
`trgfn_istanze_utilities_require_utility_dichiarata`, `trgfn_istanze_dati_precontrattuali_protect_update`,
`fn_guard_istanza_ba_gestore_globale`, `fn_guard_istanza_ha_ba`, `trgfn_billing_account_guard_admin_globale`,
`trgfn_billing_account_guard_albero_emittente`, `trgfn_billing_account_guard_istanza_emittente`,
`trgfn_billing_account_require_istanza_ha_ba`, `trgfn_efba_guard_istanza_emittente`,
`trgfn_efba_guard_storia_emittente`.

### 4.2 Area A — soggetti, natura, dati societari, titoli IVA

| Pagina | Giudizio | Che cosa non è vero o manca |
| --- | --- | --- |
| `soggetti` | riscrivere | In coda il modello di prima: `tipo_soggetto` F/G/X (colonna rimossa, lo dice il punto 1 della stessa pagina), natura NOT NULL (è nullable, e più guard trattano il caso), «almeno uno fra CF e P.IVA» (decide la natura), `ON DELETE RESTRICT` su quattro FK. Tace il cambio di natura, il blocco del codice, i guard differiti. Restano buone le sezioni su regime PA, sesso, identificativo fiscale |
| `dati_societari` | riscrivere | «Cambiare natura: una società che diventa ente» (rifiutato per primo da `E_CAMBIO_NATURA_ALTRA_MACRO_TIPOLOGIA`); forma giuridica «testo»; capitale e REA «obbligatori» (decide la forma); unicità di SDI e PEC (non sono unici, e la pagina lo dice più su); la sezione «Integrazione 2025-12-03» con nature che non esistono; la frase finale «Se vuoi, posso aggiornare anche la doc…». Tace i verbi di scrittura e di eliminazione e il guard del canale |
| `soggetti_ruoli` | riscrivere | «I trigger di audit mantengono un log» (c'è solo l'ultimo autore: la tabella non ha storico); FK con azioni inventate. Tace il guard della natura ammessa e il blocco di `soggetto_id` |
| `trgfn_soggetti_normalize` | riscrivere | «Pulisce e normalizza i campi»: il corpo imposta solo lo stato proposto |
| `fn_crea_soggetto_pg` | ritocco, largo | Tabella dei parametri da rifare: SDI e PEC «unique», default `SU` / `LN` (sono NULL: decidono i parametri), natura `DI` ammessa (è rifiutata), `E_GENERICO` (è `E_CODICE`), `ragione_sociale_completa` «calcolata dal trigger» (è una colonna generata) |
| `fn_crea_soggetto_pf` | ritocco | Come sopra per la colonna generata; mancano due esiti dello stato; il contatto lo scrive `fn_crea_contatto` |
| `soggetti_titoli_iva_ambiti`, `soggetti_titoli_iva_movimenti` | ritocco | «Il titolo si spegne con `attivo`»: con righe di ambito o movimenti la disattivazione è rifiutata, si chiude `valido_al`. Tacciono la RLS |
| `soggetti_titoli_iva` | ritocco | «Un consumatore solo» (i lettori sono cinque); la sezione «Stato (aggiornato 2026-09-02)»; due rifiuti del cambio di natura mancanti |
| `trgfn_dati_societari_guard_tipo_soggetto` | ritocco | Nome del trigger; «gestisce REQUIRED» (è del guard differito su `soggetti`); un codice errore mancante |
| `trgfn_soggetti_titoli_iva_guard_coerenza` | ritocco | «Il nome sceglie l'ordine» rispetto a guard che sono `AFTER` differiti: l'ordine alfabetico non li riguarda |
| `trgfn_soggetti_valida_cf_piva_dispatch` | ritocco | Nome del trigger; «controlli locali e internazionali» (c'è solo il ramo `IT`) |
| `trgfn_soggetti_gen_codice`, `trgfn_soggetti_guard_cf_piva_obbligatori`, `trgfn_soggetti_ruoli_guard_natura_ammessa`, `trgfn_soggetti_guard_dati_societari_required`, `vw_dati_societari`, `fn_scrivi_dati_societari_alla_nascita`, `fn_annulla_movimento_titolo_iva` | ritocco | Il codice del lock; fotografie del seed; `CURRENT_DATE` dove il corpo usa il giorno operativo; «per modificare, operare sulle tabelle base» (l'app ha solo SELECT: si scrive col verbo) |

Reggono: `fn_id_fiscale_bloccato`, `trgfn_soggetti_guard_id_fiscale_immutabile`,
`trgfn_dati_societari_guard_forma_giuridica`, `vw_soggetti_ruoli_dettaglio`, `fn_ruolo_di_altro_soggetto`,
`fn_check_titolo_iva_ambito`, `fn_consuma_plafond_titolo_iva_righe`, i due guard degli ambiti,
`trgfn_soggetti_titoli_iva_movimenti_accumulatore`, `trgfn_stiva_movimenti_guard_annullo`,
`vw_stiva_movimenti_dettaglio`.

### 4.3 Area B — indirizzi, contatti, catasto

| Pagina | Giudizio | Che cosa non è vero o manca |
| --- | --- | --- |
| `catasto_unita_immobiliari` | riscrivere | Datata 3 novembre 2026, descrive colonne `indirizzo_dettaglio_id` e `istanza_utility_id`, le loro FK e un UNIQUE che non esistono; l'ER ha il verso rovesciato. Il legame vero è `istanze_utilities.catasto_unita_immobiliare_id` più la tabella ponte, e lo dice il COMMENT della tabella |
| `contatti` | riscrivere | «Un default per soggetto» (è per soggetto e contesto); FK del ruolo «ON DELETE CASCADE»; tre indici con nomi di prima. Tace il guard del contesto, il verbo `fn_crea_contatto`, due colonne. Esempi con `INSERT` diretti |
| `trgfn_contatti_set_default_contatto` | riscrivere | `NEW.utility_id` e contesto `'utility'` (sono `istanza_utility_id` e `'istanza'`); «`default_context` sempre valorizzato» (solo sul default) |
| `trgfn_soggetti_guard_soggetto_contatti` | riscrivere | Il filtro sul contesto `'soggetto'` che il corpo non ha; il nome del trigger |
| `trgfn_indirizzi_dettaglio_normalize` | riscrivere | Descrive un corpo con `INTO STRICT` su una vista: oggi delega a `fn_build_indirizzo_normalizzato`; il ramo «civico diverso da 0» è ritirato |
| `fn_search_indirizzi_dettaglio` | riscrivere | «Con lo stradario il pattern è ignorato» (è applicato sempre); data «28-11-2026», nel futuro |
| `vw_indirizzi_dettaglio` | riscrivere | `indirizzo_normalizzato` «generated column» (la scrive il trigger); «join diretto», «in futuro comune e provincia» (ci sono già) |
| `vw_indirizzi_resolved_ruolo`, `vw_indirizzi_resolved_soggetto` | riscrivere | «La vista parte dalla tabella e applica join»: sono proiezioni di `vw_indirizzi_resolved_base`; resolver con nomi che non esistono; indici «consigliati» che esistono |
| `indirizzi`, `indirizzi_dettaglio` | ritocco | «Ogni modifica va nello storico»: su queste due tabelle lo storico nasce spento (S9). In `indirizzi_dettaglio`, `proc_bump_indirizzi_dettaglio` «apre la manutenzione» (è un UPDATE neutro: il flag lo accende solo `dbops.fn_admin_merge_stradario`). Tacciono i lucchetti sul titolare e i guard differiti degli obbligatori |
| `indirizzi_soggetti` | ritocco | «La data corrente» (è il giorno operativo); tace il lucchetto e le madri |
| `catasto-architettura` | ritocco | Vera nell'essenziale; sbagliati gli eventi del trigger che aggancia il parent e due tipi nel diagramma; «il legame è 1:1» (S11) |
| `catasto_unita_immobiliari_indirizzi` | ritocco | «Al subentro la nuova istanza è collegata alla stessa unità»: il catasto si **clona** |
| `trgfn_iu_clone_catasto_from_parent` | ritocco | Promette `CATASTO_SOURCE_NOT_FOUND`: oggi senza sorgente non fa niente |
| `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` | ritocco | Il codice errore (`E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`), il nome e le colonne del trigger |
| `fn_crea_indirizzo_soggetto`, `fn_crea_indirizzo_ruolo` | ritocco | «Dettaglio e libero insieme: vale il dettaglio» (vale il libero); manca il terzo motivo di rifiuto |
| `trgfn_indirizzi_dettaglio_protect_update`, `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`, `trgfn_soggetti_ruoli_guard_indirizzi_required`, `trgfn_indirizzi_base_normalize`, `trgfn_iu_sync_catasto_unita_indirizzo`, `fn_get_or_create_indirizzo_dettaglio`, `fn_create_indirizzo`, `fn_crea_indirizzi_ruolo`, `fn_crea_indirizzi_soggetto`, `fn_crea_contatto`, `fn_indirizzo_elemento_dettaglio`, `vw_indirizzi_resolved_all`, `vw_indirizzi_resolved_base` | ritocco | Nomi di trigger, funzioni «(futuro)» che esistono, cronaca del passaggio dal backend, rami non più raggiungibili |

Reggono: `trgfn_contatti_guard_contesto_soggetto`, `trgfn_indirizzi_dettaglio_guard_chiave`,
`trgfn_indirizzi_guard_forma_libera`, `trgfn_indirizzi_sync_geoloc`, `trgfn_soggetti_guard_indirizzi_required`,
`fn_build_indirizzo_normalizzato`, `fn_indirizzo_elemento`.

### 4.4 Area D — ruoli d'impresa e banche

Due fatti di famiglia. I sette guard di ruolo (`trgfn_*_guard_ruolo_*`: banca, emittente, fornitore, gestore, PSP,
reseller, vettore) hanno lo stesso corpo e cambia solo il codice del ruolo: `script.fn_guard_soggetto_ruolo`
**verifica soltanto**, e più pagine dicono «verificata o creata». I tre `*_normalize` di emittenti, reseller e
vettori non fanno niente, e due pagine dicono «la generazione del codice è demandata a `config.sistema_codici`»,
dove ci sono righe solo per fornitori e vettori.

| Pagina | Giudizio | Che cosa non è vero o manca |
| --- | --- | --- |
| `gestori` | riscrivere | `soggetto_id` e la sua FK (non esistono); azioni delle FK inventate; in coda dà per vivo `uq_gestori_singleton`, che più su dice ritirato; «in fase di definizione», «Sviluppi futuri» |
| `gestori_utilities` | riscrivere | `extra` (è `meta`), `uq_gest_util`, «cancellazione a cascata», guard che la tabella non ha |
| `trgfn_soggetti_conti_bancari_guard`, `trgfn_soggetti_ruoli_conti_bancari_guard` | riscrivere | Documentano il controllo delle date e un payload che il corpo non ha più: oggi fanno solo «conto attivo» |
| `trgfn_bank_guard_ruolo_bank_branches`, `trgfn_gestori_guard_ruolo_gestore` | riscrivere | «Verificata o creata», «registra `user_insert`»; la prima nomina la tabella `anagrafiche.bank` |
| `vw_conti_bancari_per_ruolo` | riscrivere | Colonne `priority` e una CTE che non esistono; «ne espone uno solo» (la vista è piatta, e lo dice in testa): metà pagina è del modello di prima |
| `fn_get_emittente_fiscale_id` | riscrivere | Regola a due livelli (sono tre, delegata a `script.fn_get_ba_emittente_sr_id`); «circa 33 funzioni» |
| `conti_bancari` | riscrivere | «Nessuna FK» (la filiale è obbligatoria); firma di `fn_get_conto_bancario_predefinito` a due parametri (sono tre) |
| `bank_branches` | ritocco | Datata 14 novembre: nomi di trigger e funzione sbagliati, ruolo «ISTITUTO_CREDITO» (il codice è `BANK_B`), trigger «futuri» che esistono |
| `soggetti_conti_bancari`, `soggetti_ruoli_conti_bancari` | ritocco | La prima tace l'esclusione «un conto d'incasso, un solo soggetto», che la gemella descrive; `CURRENT_DATE` |
| `emittenti_fiscali` | ritocco | Il codice dell'emittente non è trattato (forma, immutabilità, uso nel codice commessa); dei trigger che vietano lo spegnimento ne nomina uno |
| `emittenti_fiscali_utilities` | ritocco | «min <= max» (il vincolo è «tutte e due o nessuna»); tace `attivo` |
| `trgfn_sepa_mandati_guard` | ritocco | `E_DATA_ATTIVAZIONE_MANDATO` (non esiste: solleva `E_DATA_ERRATA`); nome del trigger |
| `fornitori`, `vw_fornitori_dettaglio`, `trgfn_fornitori_gen_codice` | ritocco | Colonne citate negli esempi che non esistono; rating «0–100 o 1–5»; «non di lista» due righe sotto «sorgente della lista»; «`acquisti` conta oggi 11 oggetti» |
| `vettori`, `trgfn_vettori_gen_codice`, `trgfn_vettori_normalize` | ritocco | «Oggi è vuota — misurato il 2026-08-21» (una fotografia); il codice del lock; «da oggi», «fin da gennaio» |
| `resellers`, `resellers_billing_account`, `trgfn_resellers_normalize`, `trgfn_resellers_guard_ruolo_reseller`, `psp`, `trgfn_gestori_guard`, `trgfn_conti_bancari_normalize`, `trgfn_emittenti_fiscali_default_guard`, `trgfn_emittenti_fiscali_guard_ruolo_emi_fis`, `trgfn_emittenti_fiscali_normalize`, `fn_get_emittente_fiscale_pk` | ritocco | I due fatti di famiglia; vincoli e trigger taciuti; un esempio di IBAN che non passa il CHECK |
| `trgfn_emittenti_fiscali_guard_attivo` | ritirare | L'oggetto non esiste (Q4) |

Reggono: `fn_crea_emittente_fiscale`, `fn_crea_fornitore`, `fn_parametri_importo_utility`,
`trgfn_emittenti_fiscali_default_bootstrap`, i due `regime_conferma`, `fn_check_fornitore_attivo`,
`fn_guard_fornitore_attivo`, `trgfn_fornitori_guard_normalize`, `trgfn_fornitori_guard_ruolo_fornitore`,
`trgfn_psp_guard_ruolo_psp`, `trgfn_resellers_guard_attivo`, `trgfn_vettori_guard_ruolo_vettore` (la migliore della
famiglia: è il modello per le sorelle).

### 4.5 Area E — accessi

Il modello di prima, che più pagine ripetono: una tabella ponte `risorse_umane_auth_user` fra la risorsa e la
credenziale, e un accesso che si spegne quando si spegne **la** veste. Oggi il ponte non esiste, la credenziale è
accesa quando **almeno una** veste è utilizzabile, e «utilizzabile» ha una sede sola (`script.fn_veste_utilizzabile`).

| Pagina | Giudizio | Che cosa non è vero o manca |
| --- | --- | --- |
| `risorse_umane` | riscrivere | Il ponte verso Django «tramite `risorse_umane_auth_user`»; non nomina nessuno dei trigger di oggi (identità attiva, ultimo SUPER_ADMIN, sync, notifica, blocchi di disattivazione, la validità) |
| `trgfn_identita_digitali_sync_auth_user_active` | riscrivere | «Simmetrica al trigger su `risorse_umane_auth_user`», «al cutover diventerà l'unico», «doppia verifica con il legacy» |
| `fn_sync_auth_user_expired` | riscrivere | Tre strati di cronaca; in coda «UNION», «solo utenti ancora attivi», «numero di utenti disattivati»: oggi è una query sola e riallinea nei due versi |
| `fn_crea_risorsa_umana_v2` | riscrivere | Scritta come differenza dalla v1, che non esiste più; tace il rifiuto `E_RISORSA_UMANA_GIA_PRESENTE`; «post-cutover è una vista» |
| `identita_digitali` | ritocco, largo | «Se `attivo` è false la credenziale si spegne» (solo se non resta nessuna veste utilizzabile); default `CURRENT_DATE`; il profilo SUPER_ADMIN «seed id 9100» scritto da una funzione che non esiste; trigger taciuti |
| `fn_sync_auth_user_is_active` | ritocco | Metà pagina è cronaca; i chiamanti descritti sono quelli di prima |
| `fn_crea_operatore_v2`, `fn_crea_auth_user` | ritocco | La storia si ferma a settembre: mancano il sesso obbligatorio, gli indirizzi, le date che vanno su rapporto e veste; `fn_crea_admin` «(futuro)» |
| `trgfn_identita_digitali_guard_ultimo_super_admin`, `trgfn_identita_digitali_guard_coerenza`, `trgfn_risorse_umane_guard_identita_attiva`, `trgfn_risorse_umane_sync_auth_user_active`, `vw_risorse_umane_dettaglio` | ritocco | Cronaca, un id di seed, il consiglio di disabilitare il trigger, un codice errore fuori dalla tabella |

Reggono: `trgfn_identita_digitali_guard_natura_credenziale`, `trgfn_risorse_umane_guard_ruolo`,
`trgfn_risorse_umane_guard_ultimo_super_admin`, `trgfn_risorse_umane_notify_cambio_reparto`,
`fn_notify_cambio_reparto`, `fn_crea_veste_portale`, `fn_accendi_veste`, `fn_provisiona_dati_di_sviluppo`,
`vw_accessi_altri`, `vw_accessi_sistema`.

## 5. Gli oggetti senza pagina

56 oggetti del catalogo non hanno una pagina `manual/` (uno è una vista, gli altri funzioni). Si raccolgono in
famiglie: la forma della pagina la decide Q2.

| Area | Famiglia | Oggetti |
| --- | --- | --- |
| A | **Il cambio di natura del soggetto** (nove motivi di rifiuto, il picker, i guard) | `fn_check_cambio_natura_soggetto`, `trgfn_soggetti_guard_cambio_natura`, `fn_nature_proponibili_soggetto`, `fn_soggetto_primo_documento`, `trgfn_soggetti_guard_obbligatori_ruoli`, `trgfn_soggetti_guard_forma_giuridica_natura` |
| A | Le regole per natura sul soggetto | `trgfn_soggetti_guard_sesso_policy`, `trgfn_soggetti_guard_regime_pa`, `fn_regime_pa_campo_non_ammesso`, `fn_soggetto_id_fiscale_bloccato` |
| A | **I dati societari: i verbi** | `fn_scrivi_dati_societari` (la porta di scrittura), `fn_elimina_dati_societari`, `fn_check_elimina_dati_societari`, `fn_forma_giuridica_ammessa`, `trgfn_dati_societari_guard_canale_fe` |
| A | Il titolo IVA ammesso dalla natura | `trgfn_soggetti_titoli_iva_guard_tipo_soggetto`, `fn_titolo_iva_vigente`, `fn_titolo_iva_ammesso`, `fn_titoli_iva_non_ammessi`, `fn_titoli_iva_non_ammessi_conta`, `fn_titolo_iva_vigente_su_natura_esiste` |
| B | Il tipo d'indirizzo ammesso (predicati e check) | `fn_tipo_indirizzo_ammesso_per_natura`, `fn_tipo_indirizzo_ammesso_per_ruolo`, `fn_check_tipo_indirizzo_soggetto`, `fn_check_tipo_indirizzo_soggetto_su_contesto`, `fn_check_tipo_indirizzo_ruolo`, `fn_check_tipo_indirizzo_ruolo_su_contesto` |
| B | Il picker dei tipi d'indirizzo | `fn_tipi_indirizzo_proponibili_soggetto`, `_natura`, `_ruolo`, `_tipo_ruolo` |
| B | Gli indirizzi obbligatori | `fn_indirizzi_obbligatori_ruolo`, `fn_tipo_indirizzo_obbligatorio_per_ruolo`, `fn_indirizzi_obbligatori_mancanti_ruolo`, `_soggetto`, `_soggetto_e_ruoli`, `fn_guard_indirizzi_obbligatori_ruolo`, `_soggetto`, `trgfn_indirizzi_guard_obbligatori_ruolo`, `trgfn_indirizzi_soggetti_guard_obbligatori_soggetto`, `fn_nomi_tipo_indirizzo_richiesto`, `fn_indirizzi_con_obbligatori` |
| B | **La copia di un indirizzo** (i verbi del drawer) | `fn_copia_indirizzo_soggetto`, `fn_copia_indirizzo_ruolo`, `fn_copia_indirizzo_soggetto_su_ruolo`, `fn_crea_copie_indirizzo_ruolo`, `fn_indirizzo_elemento_da_riga`, `fn_check_copia_indirizzo_soggetto`, `vw_indirizzi_soggetti_azioni` |
| C | La chiave unica del cliente manuale | `fn_guard_clienti_chiave_unica_di`, `fn_guard_clienti_chiave_unica_gestore_globale`, `trgfn_clienti_guard_chiave_unica`, `trgfn_efba_guard_clienti_chiave`, `trgfn_istanze_utilities_guard_clienti_chiave` |
| C | L'occupazione del PDP | `fn_check_pdp_occupato` |
| D | Il codice dell'emittente | `trgfn_emittenti_fiscali_guard_codice_forma` |

Due famiglie già documentate chiedono lo stesso trattamento, perché oggi la stessa regola è ripetuta, e in parte
contraddetta, in più pagine: nell'area E «la sincronizzazione dell'accesso» (tre trigger, la funzione, il batch) e
«l'ultimo SUPER_ADMIN» (quattro guard e la check); nell'area D i sette guard di ruolo.

## 6. Le guide

| Guida | Data | Che cosa non è vero o manca |
| --- | --- | --- |
| `soggetti-e-ruoli-anagrafici` | 9 ottobre 2026 | Ferma a prima dei cantieri su dati fiscali e societari, titoli IVA per natura, identificativo fiscale bloccato, cambio di natura. «REFERENTE (RE)» (`RE` è il reseller, e non c'è un ruolo referente); §5a-bis «l'emittente compare in un solo posto» (anche in `soggetti_titoli_iva`, `emittenti_fiscali_utilities`, `categorie_clienti_listini`); §5b `soggetti_ruoli.valido_dal/valido_al` (colonne che non esistono); «Vincoli e trigger» con quattro guard di `soggetti` su dodici; «in qualsiasi ordine» grazie ai trigger differiti (i guard dei dati societari sono immediati); l'ER con tipi e colonne di prima; i conti bancari «legati al ruolo» |
| `generazione-cliente` | 14 ottobre 2026 | La creazione attribuita a un `ClienteService` Django «previsto»: dal 18 ottobre la sede è `fn_crea_cliente` con `fn_crea_billing_account`, e la guida non li nomina. L'ordine dei trigger su `clienti` è sbagliato; lo stato del PDP è «AT→ATTIVO, CH→DISPONIBILE»; «l'istanza eredita indirizzo e utility dal PDP»; «il suo unico cliente» |
| `risorse-umane-e-accessi` | 25 ottobre 2026 | `DISABILITATO` descritto come veste viva in cinque punti, contro altri due punti della stessa guida e contro il CHECK che lo rifiuta; l'assunzione in quattro passi di scrittura diretta (nessuno dei quattro verbi dell'area è nominato); il trigger di sync «su UPDATE di `attivo`» (cinque colonne); un nome di trigger; il batch «ogni giorno alle 06:00» (S7); mancano la regola «persona o macchina», lo stato della veste, le liste degli accessi |
| `gestione-dei-contatti` | 19 settembre 2026 | «Un default diverso per il ruolo CLIENTE», «un solo default per contesto (soggetto, ruolo, istanza)»: la chiave è soggetto più contesto (S8). Mancano il guard del contesto e il verbo `fn_crea_contatto`, nati dopo; gli esempi sono `INSERT` diretti; l'ordine di `fn_get_contatti` |
| `gestione-conti-bancari` | 19 settembre 2026 | I guard dei legami «verificano la coerenza delle date» (è del guard generico); manca l'esclusione «un conto d'incasso, un solo soggetto», su cui poggia il perimetro degli incassi; «non si disattiva se ha legami **attivi**» (i legami non hanno `attivo`: basta che esistano); «valido oggi» (giorno operativo); l'esempio «una sostituzione pianificata» viola l'indice unico del predefinito |
| `gestione-degli-indirizzi` (a campione) | 20 novembre 2026 | §Storicizzazione «tutte le modifiche sono tracciate» (S9); `proc_bump_indirizzi_dettaglio` come riclassificazione; «27 colonne» (26); un esempio di indirizzo normalizzato in un formato che non è quello prodotto. Le regole R1-R7 reggono |
| `gestione-delle-istanze-utility` (a campione) | 4 novembre 2026 | «Ogni modifica viene storicizzata» (`istanze_utilities` non ha storico); «le utility devono coincidere» e «il PDP deve essere DISPONIBILE» al collegamento (nessun oggetto lo controlla lì: la utility si confronta alla nascita del cliente); «l'istanza non cambia PDP» (il lock non copre `pdp_id`); due relazioni dell'ER; «il vincolo 1 istanza = 1 cliente» in chiusura |
| `architettura-multi-face-auth` (sezioni su `anagrafiche`) | 25 ottobre 2026 | §3.1 «la veste nasce spenta» come regola generale (vale per l'operatore; il portale ammette la veste accesa); §9 manca il trigger su `risorse_umane` fra chi chiama la sync |

## 7. Le segnalazioni di codice

Leggendo le pagine contro i corpi sono emersi punti in cui il **codice** non fa ciò che è scritto o deciso, oppure
il modello ammette un caso che nessuno gestisce. Non sono ancora difetti: sono letture del corpo, e ognuna va
vagliata (Q1). ✔︎ = riletta sul catalogo dalla sessione che coordina; le altre sono lette dall'agente dell'area e
vanno provate con un caso costruito prima di scriverne la correzione.

| # | Dove | Che cosa |
| --- | --- | --- |
| S1 ✔︎ | `clienti.data_chiusura` | **Due significati.** `trgfn_clienti_set_periodo` calcola `[attivazione, chiusura)`: il giorno di chiusura è fuori. I COMMENT di `data_chiusura` («inclusiva») e di `periodo` («`data_chiusura+1`») dicono il contrario. `script.fn_subentro_cliente` chiude il cliente uscente a «attivazione nuova − 1 giorno», che sotto la regola del trigger lascia un giorno senza cliente sul PDP; `script.fn_disdetta_cliente` scrive la data di cessazione così com'è. Da leggere con `sviluppo-gestione-clienti-v2` |
| S2 ✔︎ | `fn_guard_ba_gestore_globale_storia` | Sceglie i BA da controllare con «ha fatture o commesse» e `LIMIT 1`, poi delega a `fn_guard_ba_cambio_emittente`, che dal 31 agosto decide su «documento numerato di qualunque famiglia». Le due definizioni non coincidono: un BA con soli ordini o DDT numerati non viene scelto; un BA con una fattura in bozza viene scelto, la delegata non solleva, e gli altri non si guardano |
| S3 ✔︎ | `vw_indirizzi_resolved_base` | Il join con `script.vw_indirizzo_completo` è sul solo `comune_id`, e quella vista ha una riga per **via**: un indirizzo libero col comune valorizzato esce una volta per ogni via del comune. Da provare con un caso |
| S4 ✔︎ | `fn_crea_soggetto_pf`, `fn_crea_soggetto_pg` | Il pre-controllo «CF già presente» confronta `id_fiscale_univoco_cf_piva` col solo CF (o la sola P.IVA), ma la colonna generata vale «CF spazio P.IVA» quando ci sono tutti e due e sono diversi. Anche l'indice unico è sulla colonna generata: il modello ammette lo stesso CF su due soggetti con P.IVA diverse. ~~Da decidere se è voluto~~ → deciso (Tid, 2026-11-23, §17.1): la chiave è la coppia, il pre-controllo si allinea all'indice nel giro T5 |
| S5 | La sincronizzazione di `is_active` | Tre casi che il trigger non copre e che riallinea solo il batch: il cambio di `auth_user_id` di una veste (la credenziale di prima resta com'era); il cambio di `soggetto_ruolo_id` della risorsa; lo spegnimento del soggetto (`fn_veste_utilizzabile` legge `soggetti.attivo`, nessun trigger su `soggetti` chiama la sync) |
| S6 | `fn_crea_risorsa_umana_v2` | `p_attivo DEFAULT true` contro la regola «la veste nasce spenta» (la funzione gemella del portale non ha default apposta); `p_is_super_admin = true` senza credenziale è ignorato in silenzio |
| S7 ✔︎ | Il job `sync_auth_user_expired_daily` | ~~Da dire quale dei due è il progetto~~. **Non è un difetto di codice: è voluto** (letto il 2026-11-22). Dal 2026-10-09 il job ha una sveglia oraria al minuto 10, perché la funzione è idempotente e una scadenza si riallinea entro l'ora invece che il mattino dopo; lo stesso changeSet ha portato `chiusura_scadenze_daily` alla sveglia oraria. Stantii sono guida, pagina e COMMENT, che dicono ancora «ogni giorno alle 06:00»: si correggono nel giro 0e. Il nome del job, che dice «daily», resta |
| S8 | I contatti | Il default è unico per (soggetto, contesto) e non scende al ruolo né all'istanza: due ruoli dello stesso soggetto condividono un default. Togliere il flag all'unico default lascia il contesto senza; nessuna promozione alla cancellazione. Un contatto con l'istanza e senza il ruolo è ammesso e non ha unicità per tipo. `trgfn_soggetti_guard_soggetto_contatti` chiede in pratica «almeno un contatto», di qualunque contesto. `script.fn_get_contatti` scarta i contatti con un'unità organizzativa quando il parametro non è passato; `fn_get_contatto_default` fra tipi diversi ordina per id |
| S9 ✔︎ | Lo storico degli indirizzi | `storicizza` ha default `false` su `indirizzi` e `indirizzi_dettaglio` (`true` sulle altre tabelle dello schema che l'hanno). ~~Voluto~~ → ⚠️ Q7 riaperta: R-BE5 (§9.1) smentisce la premessa, Tid sceglie lo storico **continuo**, strada (b) (§10). Come lavora oggi il DB (`script.trgfn_storico_generic`): una riga con `storicizza = true` lascia nello storico la versione precedente, poi il trigger rimette il flag a `false`, perché le due tabelle non sono in `config.storico_set_storicizza`; nessun oggetto del DB lo riaccende. Lo storico è quindi «a richiesta di chi scrive». Tid ricorda che le scritture dell'app passano `true`: se è così, ogni modifica fatta dall'app lascia la sua traccia. Le pagine scrivono la regola del DB e il ruolo di chi scrive, senza promettere una traccia continua; R-BE5 conferma il lato applicativo |
| S10 | `fn_search_indirizzi_dettaglio` | L'estensione del civico si confronta col valore grezzo (`'A'` non trova `/A`); `RAISE EXCEPTION` diretto invece di `fn_log_and_raise_error`; `p_limit` senza tetto |
| S11 | Il catasto | «Un'istanza, un catasto» vale solo per la strada della clonazione: nessun UNIQUE su `istanze_utilities.catasto_unita_immobiliare_id` |
| S12 ✔︎ | I reseller | `resellers.codice` è NOT NULL e nessun trigger lo genera (è la lacuna che i vettori avevano fino ad agosto). `resellers_billing_account` non ha né UNIQUE né esclusione: due reseller sullo stesso BA nello stesso periodo sono ammessi, e la colonna generata `validita` non è usata da nessun vincolo. `trgfn_resellers_guard_attivo` è scritto a mano perché la FK punta a `soggetti_ruoli`, e manca il verso opposto (un legame verso un reseller spento) |
| S13 | `psp` | Unica specializzazione senza blocco della cancellazione e senza lock del codice; nessuna FK punta alla tabella, quindi `psp.attivo` non ferma niente |
| S14 | `pdp.cliente_id` | COMMENT e `vw_pdp` la presentano come «cliente corrente». Da verificare chi la scrive: l'unica funzione del DB che aggiorna `pdp` è `trgfn_clienti_sync_stato_pdp` (R-BE2 per il lato applicativo). Sullo stesso `pdp` due presìdi dell'immutabilità, di cui il secondo non parla mai. ⚠️ Precisato nel giro 0a (§12.2): `trgfn_clienti_sync_stato_pdp` scrive solo `stato_pdp_id`, quindi nessuna funzione del DB scrive `cliente_id`; e il presidio muto è il **lock delle colonne** (`trg_pdp_a10_lock_columns_upd`), che per nome viene dopo `trg_pdp_a10_guard_upd`, non il guard |
| S15 | Quattro trigger che non fanno niente | `trgfn_istanze_utilities_normalize`, `trgfn_emittenti_fiscali_normalize`, `trgfn_resellers_normalize`, `trgfn_vettori_normalize` sono `RETURN NEW` e scattano a ogni scrittura |
| S16 | Le viste di dettaglio delle istanze | `vw_istanze_dati_precontrattuali_dettaglio` mostra come utility della riga quella del PDP: su un'istanza con più utility tutte le righe mostrano la stessa. `vw_indirizzi_dettaglio` ha un join interno che fa sparire i civici di una via che non si risolve |
| S17 | I clienti | Un cambio di `istanze_utilities.pdp_id` dopo la nascita del cliente non arriva al cliente fino alla sua prossima scrittura (la colonna dell'istanza non è bloccata). `fn_crea_cliente` rifiuta la chiave sconosciuta, `fn_update_cliente` la ignora in silenzio |
| S18 | I conti bancari | «Il conto è attivo» sta in due sedi (il guard `BEFORE` e il trigger differito dell'automazione ATTIVO, che così non parla mai per primo). «Un conto predefinito non si blocca» la tiene solo il backend. `paese` non si ricalcola al cambio di IBAN. `emittenti_fiscali_utilities.utility_id` è `bigint`, `config.utilities.id` è `integer` |
| S19 | Le FK geografiche | `ON DELETE SET NULL` su `indirizzi`, nessuna azione su `indirizzi_soggetti`: gemelle che divergono, e il SET NULL urterebbe il CHECK della forma libera |
| S20 | `trgfn_soggetti_guard_cf_piva_obbligatori` | Guarda solo `IS NULL`: una stringa vuota passa la presenza |
| S21 | Forma | Trigger senza fascia nel nome (`trg_soggetti_normalize_ins_upd`, `trg_soggetti_valida_cf_piva_dispatch_ins_upd`, `trg_dati_societari_guard_tipo_soggetto_ins_upd`, tre su `billing_account`); variabili senza `%TYPE` (`trgfn_gestori_guard`, `trgfn_risorse_umane_guard_ruolo`, `trgfn_soggetti_valida_cf_piva_dispatch`); `zeroerp_app` ha il DML sulla vista `vw_risorse_umane_dettaglio`; il codice `CODICE_NON_MODIFICABILE` senza prefisso è ancora in `config.messaggi_errore` → La parte sul DML della vista è chiusa: decisa da Tid il 2026-11-23, lavoro di `brief-db-porte-aperte-dalla-sola-guc` §5 (§19.3). Il resto resta in T11 |
| S22 | I nomi `_v2` | `fn_crea_operatore_v2` e `fn_crea_risorsa_umana_v2` non hanno più una versione accanto: è un nome rimasto. Caso analogo `fn_sync_auth_user_expired`, che ora anche riaccende. → Tutta nel brief degli accessi (T9, §17.1) |
| S23 | Lo strumento della doc | `scripts/gen_db_docs.py` non mostra i vincoli `EXCLUDE` fra i vincoli della scheda (`ex_clienti_no_overlap_stesso_pdp`, `ex_categ_cli_listini_no_overlap`): compaiono solo fra gli indici |

I rami irraggiungibili di `trgfn_clienti_set_parent_istanza` non sono qui: sono il §2.1 di
[brief-db-catena-istanze-pdp](brief-db-catena-istanze-pdp.md).

## 8. I metadati

Stato dei COMMENT dello schema al 2026-11-22 (catalogo di dbdev). Si riscrivono interi, secondo
`linee-guida-sql.md` §5d, nel giro dei metadati.

**Senza COMMENT.** 7 funzioni su 195 (le cinque `trgfn_*_gen_codice`, `trgfn_iu_clone_catasto_from_parent`,
`trgfn_indirizzi_dettaglio_protect_update`); 9 viste su 19; la tabella `risorse_umane`; 166 colonne su 551, più
fitte in `soggetti` (20 su 27), `indirizzi_dettaglio` (17 su 21), `risorse_umane` (12 su 16), `billing_account` (12
su 19), `indirizzi` (11 su 20), `soggetti_titoli_iva` (10 su 23); 273 trigger su 328.

**Con marcatori** (nomi di brief, date, id di changeSet, «§», «Tid»): 97 funzioni su 195, 9 tabelle, 4 viste, 23
colonne.

**Dicono il falso.**

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | `clienti.data_chiusura`, `clienti.periodo` | «Inclusiva», «`data_chiusura+1`»: il corpo calcola la chiusura esclusa (S1) |
| M2 | `clienti.pdp_id` | «→ `config.pdp.id`»: la tabella è `anagrafiche.pdp` |
| M3 | Tabella `billing_account` | «Storico dei codici cliente definitivi per utility» |
| M4 | Tabella `identita_digitali`, colonna `auth_user_id` | «Una sola attiva», «mapping 1:1»: gli indici unici sono per (credenziale, veste) |
| M5 | Tabella `emittenti_fiscali` | «Preferenze di numerazione, IBAN predefinito»: nessuna colonna del genere |
| M6 | Tabelle `vettori`, `resellers` | Ruolo «RES»: i codici sono `VT` e `RE`; quello dei vettori è copiato dai reseller |
| M7 | Tabella `soggetti_titoli_iva_ambiti` | «A spegnere il titolo c'è `attivo`»: con righe di ambito la disattivazione è rifiutata |
| M8 | Tabella `pdp` | «Storicizzazione obbligatoria»: `storicizza` è un booleano che si può spegnere; il NOT NULL di `meta` si chiama ancora `pdp_extra_info_not_null` |
| M9 | `fn_guard_ba_gestore_globale_storia`, i quattro guard dell'albero | «Fatture o commesse» (S2); in `trgfn_efba_guard_albero_emittente` «TRE movimenti» contro «Movimento 4» nel corpo |
| M10 | `fn_crea_cliente` | Attribuisce il rifiuto «la utility richiede il PDP» al trigger sbagliato |
| M11 | `fn_crea_risorsa_umana_v2` | «Body identico a v1 salvo…» |
| M12 | `trgfn_emittenti_fiscali_normalize`, `trgfn_resellers_normalize` | «Codice demandato a `config.sistema_codici`»: nessuna riga per i due |
| M13 | `trgfn_billing_account_guard_normalize`, `trgfn_conti_bancari_normalize` | «Normalizza il codice», «aggiorna l'audit»: i corpi non lo fanno |
| M14 | `trgfn_bank_guard_ruolo_bank_branches` e gli altri guard di ruolo | Tabella `anagrafiche.bank`; nei corpi «ID vero (nuovo o esistente)», «creazione/verifica» |
| M15 | `trgfn_soggetti_titoli_iva_movimenti_accumulatore`, `trgfn_soggetti_titoli_iva_guard_tipo_soggetto` | Citano come vive `fn_consuma_plafond_titolo_iva` e `trgfn_soggetti_guard_titoli_iva_ammessi`, che non esistono |
| M16 | `trgfn_soggetti_guard_sesso_policy`, `trgfn_soggetti_guard_forma_giuridica_natura`, `fn_scrivi_dati_societari` | Descrivono un cambio di natura fra macro-tipologie, oggi vietato |
| M17 | `fn_lookup_utilities_per_ba`, `fn_parametri_importo_utility`, `fn_guard_istanza_ba_emittente`, `fn_indirizzo_elemento`, i due `fn_tipo_indirizzo_ammesso_*` | Elenchi di lettori e di chiamanti non più veri |
| M18 | `script.fn_veste_utilizzabile` | «`CURRENT_DATE`»: il corpo usa il giorno operativo. Fuori schema, segnalato |

### 8.1 Le voci trovate nei giri 0a-0e (raccolte il 2026-11-23)

I giri 0a-0e hanno trovato altri metadati falsi, scritti nei loro §x.2. Qui sono raccolti in un elenco solo, perché il
giro dei metadati parta da una lista e non da sei. La colonna «Sede» dice **dove si corregge**, e decide chi lo fa:

* **COMMENT**: un `COMMENT ON`, nel giro dei metadati;
* **corpo**: un commento dentro il corpo di una funzione, che si cambia solo con un `CREATE OR REPLACE`. Lo corregge
  il giro di codice che riscrive quella funzione; se nessun giro la tocca, resta nel giro dei metadati, che allora
  riscrive il corpo solo per il commento;
* **seed**: una riga di `80_data`, che si corregge dal CSV (`linee-guida-sql.md` §11.2), non con un `UPDATE`.

⭐ Regola per i giri di codice: il COMMENT resta attaccato alla funzione anche dopo un `CREATE OR REPLACE`. Un giro
che riscrive una funzione ne riscrive anche il COMMENT, nello stesso changeSet, e la voce si spunta qui: così nessun
COMMENT si scrive due volte.

| # | Dove | Che cosa | Sede |
| --- | --- | --- | --- |
| M9-bis | `trgfn_billing_account_link_ef`, `trgfn_efba_guard_storia_emittente` | «Fatture o commesse», come M9 (§12.2) | COMMENT |
| M19 | `fn_get_emittente_fiscale_id` | La regola dell'azienda del BA a due livelli: sono tre (§12.2) | corpo |
| M20 | `emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id` | «→ `soggetti_ruoli.id`»: la FK punta a `emittenti_fiscali.soggetto_ruolo_id` (§12.2) | COMMENT |
| M21 | `trgfn_clienti_sync_utility_from_ba` | «Scrive se manca» vale per la utility, non per il ruolo, che il guard prima rifiuta NULL (§12.2) | COMMENT |
| M15-bis | `trgfn_soggetti_titoli_iva_guard_coerenza`, `fn_consuma_plafond_titolo_iva_righe` | «Il nome sceglie l'ORDINE»; «l'imponibile si legge dalla riga» (il corpo usa l'importo passato) (§13.2) | COMMENT |
| M22 | `trgfn_soggetti_titoli_iva_guard_tipo_soggetto` | Nomina come vivo `trgfn_soggetti_guard_titoli_iva_ammessi`, ritirato il 2026-11-14 (§13.2) | corpo |
| M16 | `trgfn_soggetti_guard_forma_giuridica_natura` | ⚠️ Correzione di M16: questo COMMENT non descrive il cambio di natura, ha solo un marcatore «Brief: …» (§13.2) | COMMENT |
| M23 | `indirizzi_dettaglio.storicizza` | «Default=True», quando è `false`. ✅ Riscritto dal giro 1 (`20261123-38`, §18), insieme a quelli di `indirizzi` e `config.stradario` | COMMENT |
| M24 | `fn_check_tipo_indirizzo_soggetto` | «I tipi che chi chiama vede»: le tabelle sotto non hanno RLS, nessun filtro (§14.2) | COMMENT |
| M25 | `contatti.default_context`, `contatti.is_default` | «soggetto\|ruolo\|utility», «per il soggetto»: il contesto è `istanza`, la chiave è soggetto e contesto (§14.2) | COMMENT |
| M17-bis | `fn_indirizzi_con_obbligatori`, i predicati del tipo ammesso | Marcatori di cantiere; i lettori veri (§14.2) | COMMENT |
| M26 | `vettori.soggetto_ruolo_id`, `fornitori.rating` | «Ruolo atteso: RES» (è `VT`); «0-100 o 1-5» (il CHECK è 0..100) (§15.2) | COMMENT |
| M27 | `trgfn_emittenti_fiscali_guard_codice_forma` | «`varchar(10)`»: la colonna è `varchar(32)`, il limite di 10 lo tiene il CHECK. Lo ripete il test 9 del suo pgTAP (§15.2) | corpo, pgTAP |
| M14-bis | Tre guard di ruolo | «Nuovo o esistente» nel corpo (§15.2) | corpo |
| M28 | `identita_digitali.tecnica` | «Non ha MAI il profilo SUPER_ADMIN»: nessun oggetto lo impedisce (S63) | COMMENT, o la regola con T8 |
| M29 | `fn_sync_auth_user_expired`, `maintenance.proc_sync_auth_user_expired_job`, `pgagent.pga_job.jobdesc` di `sync_auth_user_expired_daily` | «Batch notturno», «disattiva», «una volta per giorno aziendale»: è orario e riallinea nei due versi (§16.2) | COMMENT; il `jobdesc` dal changeSet che crea il job |
| M30 | `fn_crea_operatore_v2`, `trgfn_risorse_umane_guard_ruolo` | Un elenco di revisioni con nomi di brief; il guard tace il controllo del soggetto, e l'intestazione del corpo parla di fornitori (§16.2) | COMMENT, corpo |
| M31 | La sync della veste, `fn_crea_operatore_v2` | Commenti nei corpi che danno `DISABILITATO` per vivo (§16.2) | corpo |
| M32 | `config.codici_errore` | La nota di `E_PROFILO_ULTIMO_SUPER_ADMIN` (una sede sola, «post-cutover»); la `causa` vuota di `E_RISORSA_UMANA_SOGGETTO_MISMATCH` (§16.2) | seed |

Senza COMMENT, oltre all'elenco sopra: la tabella `risorse_umane` e quasi tutte le sue colonne, la vista
`vw_risorse_umane_dettaglio` (§16.2).

## 9. Ricadute su BE e FE

Il giro 0 non cambia nessun contratto: non ci sono ricadute da sviluppare. Ci sono cinque domande di censimento
(R-BE6, la sesta, è nata nel giro 0e: §16.3),
che la sessione DB non può chiudere perché non legge `backend/`, e la cui risposta decide che cosa scrivono le
pagine:

| # | Domanda al team BE/FE | Serve a |
| --- | --- | --- |
| R-BE1 | Quali endpoint, service o liste leggono `anagrafiche.vw_risorse_umane_dettaglio`, `vw_pdp` e `vw_clienti_codice_ba`? Nel DB nessuna vista né funzione le nomina | Dire nella pagina chi le legge, o proporne il ritiro |
| R-BE2 | Il backend scrive `anagrafiche.pdp.cliente_id`? | S14 |
| R-BE3 | Chi chiama `fn_check_fornitore_attivo` e `fn_guard_fornitore_attivo`? Nel DB nessun corpo plpgsql le nomina | Dire nella pagina i lettori veri |
| R-BE4 | La regola «un conto predefinito non si blocca» è solo nel service dei conti bancari? In quali punti | S18: se diventa una regola del DB, il brief dirà chi cambia per primo |
| R-BE5 | Ogni scrittura dell'app su `anagrafiche.indirizzi` e `anagrafiche.indirizzi_dettaglio` (UPDATE e DELETE, compresi i verbi di copia e le madri) passa `storicizza = true`? Quali no. E prima di una DELETE l'app riscrive la riga con `true`? Il DB guarda il flag *salvato*, che dopo ogni modifica è `false` (§14.2) | S9, Q7: la guida degli indirizzi dirà quali modifiche lasciano traccia |

### 9.1 Le risposte del team BE/FE — 2026-11-22

Censimento in sola lettura su `backend/`, `frontend/src` e i CSV di `80_data` (sessione BE, `dev/backend-tid`).
I test sono contati a parte: nessuno nomina direttamente gli oggetti delle domande.

**R-BE1 — I lettori delle tre viste.**

| Vista | Lettori | Esito per la pagina |
| --- | --- | --- |
| `vw_risorse_umane_dettaglio` | Due, di produzione. (1) Il lookup delle risorse umane: `anagrafiche_repository._risorse_umane_lookup`, `GET /api/v1/anagrafiche/risorse-umane/lookup/`, usato dal drawer della commessa. (2) La testata della commessa, per il nome del responsabile: `commesse_repository.get_commessa_testata`, `GET /api/v1/vendite/commesse/{id}/stato/` (anche in risposta alla PATCH della testata) | La pagina nomina i due lettori |
| `vw_pdp` | Nessuno: né il backend, né il frontend, né il catalogo delle liste (`ui/*.csv`) | Candidata al ritiro |
| `vw_clienti_codice_ba` | Nessuno per nome nel backend, ma **è viva**: è l'`entita_tabella` del ruolo CLIENTE in `config.tipi_ruoli`, letta in modo dinamico da `script.fn_get_entita_ruolo_detail`, a sua volta chiamata da `script.fn_get_search_detail`. Il percorso dell'app: `SearchRepository.get_search_detail` → `GET /api/v1/core/search/{id}/detail/` → il dettaglio della ricerca universale nel FE | La pagina nomina il lettore dinamico: **non** è da ritirare |

**R-BE2 — Il backend scrive `anagrafiche.pdp.cliente_id`?** No. Il backend non scrive mai su
`anagrafiche.pdp`, né direttamente né attraverso una funzione del DB. Fa solo letture (`LEFT JOIN
anagrafiche.pdp` nei repository di istanze utility, billing account e pagamenti), e nessuna legge
`pdp.cliente_id`. `fn_crea_cliente` non riceve il PDP nei suoi campi. La tabella non è in
`config.tabelle_gestibili`, quindi il pannello generico non la scrive. Lato DB l'unico che la scrive
è `trgfn_clienti_sync_stato_pdp`, e scrive solo `stato_pdp_id`.

**R-BE3 — Chi chiama `fn_check_fornitore_attivo` e `fn_guard_fornitore_attivo`?** Nessuno: né il
backend, né il frontend, né il DB, né i pgTAP. In `backend/` c'è solo un commento in
`portale/services/invito_portale_service.py`, il cui codice fa un controllo suo (`E_FORNITORE_NON_TROVATO`)
senza chiamarle. `E_FORNITORE_NON_ATTIVO` vive solo nei cataloghi errori. Candidate al ritiro.

**R-BE4 — «Un conto predefinito non si blocca».** Nel BE sta **solo** in
`ContiBancariService._guard_predefinito_bloccato`. Sullo stato risultante (in update, il payload sopra
le bandiere correnti) rifiuta `predefinito AND bloccato` col codice **generico** `E_ANAG_VALIDAZIONE`
(400), non con un codice suo. Lo chiamano quattro punti: crea e aggiorna del conto del soggetto, crea
e aggiorna del conto del ruolo. Non ci sono altre strade di scrittura su
`soggetti_conti_bancari`/`soggetti_ruoli_conti_bancari`, che non stanno in `tabelle_gestibili`. Nel FE
`ContoBancarioForm.vue` rende le due spunte alternative (spuntarne una toglie l'altra). La chiave i18n
`anagrafiche.conti_bancari.bloccato_predefinito_hint` esiste ma nessun componente la usa. A DB non c'è
nessun vincolo. **Se la regola passa al DB (S18):** serve un codice errore suo, con la policy
generata e il messaggio di ripiego; cambia per primo il DB, poi il BE ritira il guard e il codice
generico.

**R-BE5 — Le scritture sugli indirizzi passano `storicizza = true`?** **No, nessuna.** Il flag non
compare in nessuna scrittura dell'app su queste due tabelle. Né le whitelist delle colonne
(`INDIRIZZO_RUOLO_UPDATE_COLS`, le colonne ammesse di `update_indirizzo_dettaglio`) né le funzioni
chiamate lo portano.

| # | Scrittura | Percorso dell'app | `storicizza` |
| --- | --- | --- | --- |
| 1 | UPDATE `indirizzi` | `soggetti_repository.update_indirizzo_ruolo`, PATCH dell'indirizzo del ruolo | no |
| 2 | DELETE `indirizzi` | `soggetti_repository.delete_indirizzo_ruolo`, chiamata **dalla view** senza service | no |
| 3 | DELETE + INSERT `indirizzi` | `soggetti_service.replace_indirizzo_ruolo`, PUT dell'indirizzo del ruolo | no |
| 4 | UPDATE `indirizzi_dettaglio` | `indirizzi_repository.update_indirizzo_dettaglio` (`geo_service.update_indirizzo`), PATCH dell'indirizzo | no |
| 5 | INSERT `indirizzi` | le madri e i verbi di copia (`fn_crea_indirizzo_ruolo`, `fn_crea_indirizzi_ruolo`, `fn_copia_indirizzo_*`, `fn_crea_indirizzo_soggetto`, `fn_crea_cliente`/`fn_crea_fornitore`) | non serve all'INSERT; la riga nasce col default `false` |
| 6 | UPDATE `indirizzi_dettaglio` **nascosto** | `fn_get_or_create_indirizzo_dettaglio` (la riattivazione `attivo = true`), raggiunta dalle madri e dalle copie attraverso `fn_indirizzo_elemento_dettaglio` e `fn_create_indirizzo` | no |

Non verificate: le cancellazioni a cascata dovute alla cancellazione di un soggetto o di un ruolo.
Fuori dall'app, `dbops.fn_admin_merge_stradario` e `maintenance.proc_bump_indirizzi_dettaglio`: il
backend non le chiama.

⚠️ **R-BE5 smentisce la premessa di Q7.** La decisione «voluto» (§10) si appoggiava al ricordo che le
scritture dell'app passino `true` (S9). Non lo fanno: oggi **nessuna modifica a un indirizzo fatta
dall'app lascia traccia nello storico**. Tid ha riaperto Q7 e l'ha decisa di nuovo: strada (b) (§10).

Le ricadute dei giri di codice, se nascono, si scrivono qui giro per giro, come nei brief precedenti.

## 10. Le decisioni di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q1 | **Il perimetro.** Questo brief tiene solo la documentazione, oppure anche i giri di codice che nascono dal vaglio di §7 e il giro dei metadati di §8? | Come le revisioni precedenti: tutto qui, in giri successivi al giro 0, ciascuno col via. Le segnalazioni che toccano un brief aperto (S1 con la gestione clienti, il parent con la catena delle istanze) vanno là |
| Q2 | **Gli oggetti senza pagina.** Una pagina per oggetto, oppure un testo solo per famiglia? | Un blocco comune per famiglia (`_<famiglia>.md`, come prevede lo standard) che racconta la regola una volta, e per ogni oggetto una pagina corta con cornice e Scopo che lo include: così ogni scheda ha la sua pagina e l'indice la sua descrizione, e la regola ha una sede sola. Lo stesso per le tre famiglie già documentate di §5 |
| Q3 | **`catasto-architettura`.** Dove va il racconto del flusso del catasto? | Una guida (`guide/catasto-delle-istanze`): è un flusso fra più tabelle e due schemi. La pagina della tabella diventa corta e rimanda lì; il link di `generazione-cliente` si aggiorna |
| Q4 | **`trgfn_emittenti_fiscali_guard_attivo`.** La pagina di un oggetto che non c'è più | Si ritira; «dove vive oggi la regola» scende nella pagina `emittenti_fiscali` |
| Q5 | **Le guide.** Quali entrano nel giro 0 | Le cinque dello schema per intero, ciascuna con la sua area; le tre toccate solo nei punti di §6 |
| Q6 | **L'ordine e il passo.** Un'area per sessione, nell'ordine C, A, B, D, E | Come in §2. La rigenerazione della doc dopo ogni area, non alla fine |
| Q7 | **Lo storico degli indirizzi (S9).** `storicizza` spento su `indirizzi` e `indirizzi_dettaglio` è voluto? | Serve prima del giro 0c: se è voluto la pagina dice «a richiesta» e la guida si corregge; se non lo è, è un difetto e la pagina lo porta in «Che cosa oggi non copre» |
| Q8 | **Il batch degli accessi (S7).** Giornaliero alle 06:00 o ogni ora? | Serve prima del giro 0e, per lo stesso motivo |

**Decise da Tid il 2026-11-22.** Q1-Q6 come proposte, con una precisazione su Q1: prima si chiude tutto il giro 0
(documentazione), e i giri che cambiano il comportamento vengono per ultimi. Q7: voluto (S9) — ⚠️ **riaperta e
decisa di nuovo il 2026-11-22, vedi sotto**. Q8: Tid non ricordava
se fosse una scelta dello sviluppo; letto nel changelog, è voluto dal 2026-10-09 (S7), quindi si corregge la
documentazione e non il job.

**Q7 riaperta — Tid, 2026-11-22: strada (b), le modifiche agli indirizzi lasciano traccia.** La prima
risposta («voluto») si appoggiava al ricordo che le scritture dell'app passino `storicizza = true`:
R-BE5 (§9.1) lo smentisce, nessuna lo fa. Oggi nessuna modifica a un indirizzo lascia traccia.
Decisione: lo storico di `indirizzi` e `indirizzi_dettaglio` diventa **continuo**, come quello di
`indirizzi_soggetti` e di `soggetti`, con la garanzia nel DB e non nei cinque punti del BE (che
dimenticherebbero il prossimo percorso di scrittura, e non coprono la riattivazione dentro
`fn_get_or_create_indirizzo_dettaglio`). **Richiesta al team DB**, come giro di codice (in coda, Q1):
le due tabelle in `config.storico_set_storicizza`, e il default di `storicizza` allineato alle altre
tabelle dello schema, più le righe esistenti; la forma la decide il team DB. **Ricadute BE:** nessuna
attesa; il BE non passa il flag. Il giro 0c scrive le pagine e la guida col comportamento di oggi
(«nessuna traccia») in «Che cosa oggi non copre», col rimando a questo giro. ✅ **Fatto (sessione DB,
2026-11-22, dopo il merge della PR #204):** il giro 0c, committato prima della risposta, scriveva «È voluto»;
corretti `manual/indirizzi.md`, `manual/indirizzi_dettaglio.md` («Che cosa oggi non copre») e la guida
`gestione-degli-indirizzi` §Storicizzazione. ✅ **Tid, 2026-11-22: anche `config.stradario`**, che aveva la
stessa regola «a richiesta»: lo storico continuo vale per tutte e tre le tabelle, e il giro di codice di Q7 porta
anche lei in `config.storico_set_storicizza`, col default e le righe esistenti. Quali scritture dello stradario
passano oggi il flag non è censito (R-BE5 copriva le due tabelle degli indirizzi): con la regola nel DB non serve.
⚠️ La pagina `config/manual/stradario.md` dice ancora «il front-end dovrà sempre impostare a true»: è fuori da
questa revisione (schema `config`), si corregge col giro di codice.

## 11. Alla chiusura

* Ogni pagina `manual/` passa i sei controlli di `standard-guide.md` con la data aggiornata; nessun link `/dbzero/…`
  o `/guide/…` morto; nessun nome citato che il catalogo non conosce.
* Ogni oggetto dello schema ha la sua pagina, e l'indice dello schema non porta più marcatori come descrizioni.
* Le sezioni «⚠️ Che cosa oggi non copre» rimaste aperte hanno ciascuna un giro o un brief che le chiude.
* Le segnalazioni di §7 sono tutte vagliate: difetto con il suo giro, oppure voluta e scritta come tale nella
  pagina. Una segnalazione che il vaglio (§17) manda in un brief vicino o in uno nuovo conta come vagliata quando
  quel brief la porta scritta, col rimando a questo.
* Il brief va in `work-done/` quando i giri sono applicati e le domande R-BE hanno risposta.

## 12. Giro 0a — l'area C, 2026-11-22 (scritto, committato)

L'ha scritto la sessione DB col via di Tid, con cinque agenti per gruppi di oggetti (clienti e categorie; la chiave
unica del cliente manuale; il billing account; l'azienda del billing account; istanze, PDP e dati precontrattuali) e
uno per le guide. Le pagine sono lette dai corpi del catalogo di dbdev (`pg_get_functiondef`, `pg_get_triggerdef`,
`pg_get_constraintdef`, `pg_policy`), dalle schede auto-generate e dai pgTAP. Descrivono il comportamento di oggi:
ogni difetto sta al presente nella sezione «⚠️ Che cosa oggi non copre» della pagina, senza numeri né nomi di brief.

### 12.1 Che cosa è scritto

* **Le 57 pagine esistenti dell'area C**, tutte nella cornice. Riscritte dal corpo quelle che §4.1 dava da
  riscrivere, e altre che erano nel formato vecchio pur reggendo nel contenuto (`trgfn_billing_account_guard_admin_globale`,
  `trgfn_billing_account_link_ef`, `trgfn_istanze_utilities_require_utility_dichiarata`, `categorie_clienti`).
* **Sei pagine nuove:** `fn_check_pdp_occupato` e le cinque della chiave unica (`fn_guard_clienti_chiave_unica_di`,
  `fn_guard_clienti_chiave_unica_gestore_globale`, `trgfn_clienti_guard_chiave_unica`, `trgfn_efba_guard_clienti_chiave`,
  `trgfn_istanze_utilities_guard_clienti_chiave`). Ogni oggetto dell'area C ha ora la sua pagina.
* **Due blocchi comuni** (Q2): `anagrafiche/_chiave-unica-cliente.md` (la regola, chi occupa la chiave, le quattro
  strade che la toccano, il controllo al COMMIT; incluso in 7 pagine) e `anagrafiche/_emittente-del-billing-account.md`
  (i tre livelli, i quattro movimenti del collegamento, la storia come documento numerato; incluso in 17 pagine).
* **`guide/generazione-cliente.md`**, riscritta per intero: la creazione in una chiamata con `fn_crea_cliente`, l'ordine
  vero dei trigger, lo stato del PDP per occupazione, un cliente per billing account, la storia dell'azienda, S1 al
  presente nel subentro.
* **`guide/gestione-delle-istanze-utility.md`**, nei soli punti di §6 più due link a `manual/` che puntavano alla pagina
  invece che alla scheda.

### 12.2 Che cosa ha corretto o aggiunto al censimento

* **S14** è precisato in §7: nessuna funzione del DB scrive `pdp.cliente_id`, e il presidio muto è il lock, non il guard.
* **Il ruolo del cliente non si copia mai dal billing account.** `trg_clienti_guard_ruolo_cliente_ins_upd` viene per nome
  prima di `trg_clienti_sync_utility_from_ba_ins_upd` e rifiuta il ruolo NULL: il «scrive se manca» del COMMENT vale
  solo per la utility.
* **I rami «senza data» e «annullato» di `trgfn_clienti_set_parent_istanza` sono irraggiungibili anche in INSERT**: la
  `WHEN` del trigger si valuta dopo `trgfn_clienti_set_periodo`, che all'annullato toglie le date. Ricavato dalla
  semantica dei trigger, non provato con un caso. Smentisce il §2.1 di [brief-db-catena-istanze-pdp](brief-db-catena-istanze-pdp.md)
  («li raggiunge solo un INSERT»), e il suo §5 è vecchio: `trgfn_clienti_sync_stato_pdp` segue l'occupazione, non AT/CH.
  Da riportare in quel brief quando si riprende (non toccato da qui).
* **Lo stato del PDP non si aggiorna col calendario**: si ricalcola solo quando si scrive un cliente, e nessun job lo
  rifà. Una chiusura con data futura libera il PDP alla scrittura successiva.
* **Nessuna funzione del DB crea un'istanza vera** (con PDP): `fn_crea_billing_account` crea solo la fittizia; le altre
  scritture su `istanze_utilities` sono UPDATE (la catena, il clone del catasto).
* `E_ISTANZA_UTILITY_SENZA_UTILITY` è in `config.messaggi_errore` e nessuna funzione lo solleva.
* `categorie_clienti` non è mai stata «backfillata a STANDARD»: `billing_account.categoria_cliente_id` è NOT NULL e
  senza default.
* Le policy di `clienti` e `billing_account` misurano la stessa azienda e lo stesso ruolo: la differenza «LEFT JOIN /
  JOIN interno» che le pagine di `vw_clienti_codice_ba` e `vw_clienti_lista` descrivevano non esiste.
* **M9 è più largo**: dicono ancora «fatture o commesse» anche i COMMENT di `trgfn_billing_account_link_ef` e
  `trgfn_efba_guard_storia_emittente`, e il commento nel corpo di `fn_get_emittente_fiscale_id` descrive la regola a due
  livelli. Il COMMENT di `emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id` dice «→ `soggetti_ruoli.id`»,
  la FK punta a `emittenti_fiscali.soggetto_ruolo_id`.

### 12.3 Segnalazioni di codice nuove

Lette sui corpi dagli agenti del giro, non provate con un caso. Si vagliano con le altre di §7, nei giri di codice.

| # | Dove | Che cosa |
| --- | --- | --- |
| S24 | `fn_check_ba_coppia_emittente_omogenea` | Risolve l'azienda con `fn_get_emittente_fiscale_id`, che passa dal livello «azienda di chi agisce». Quando un operatore in sessione toglie un collegamento, il BA rimasto si confronta con l'azienda dell'operatore e non con la predefinita su cui ricade: il passo passa anche se l'albero o l'istanza diventano misti per l'installazione, ed è respinto anche se restano omogenei. `test-istanza-ba-gestore-globale-v1.sql` (test 1 e 5) tratta il primo caso come lecito |
| S25 | `trgfn_efba_guard_albero_emittente`, `trgfn_efba_guard_storia_emittente` | Una modifica che trasforma la riga predefinita in un collegamento, o il contrario, non chiama il controllo sui BA senza collegamento (il gemello dell'istanza sì). Il caso è possibile perché il singleton è differito. Sostituire la predefinita cancellandola e reinserendola è respinto alla cancellazione quando un BA senza collegamento ha storia, anche se la riga nuova riporta la stessa azienda |
| S26 | I due guard sullo spostamento della predefinita | Guardano lo stato dopo, non la differenza: una coppia mista che c'era già ferma ogni spostamento che non vada sull'azienda dell'altro BA |
| S27 | `vendite.fatture` | Non ha `script.trgfn_doc_guard_emittente_ba`, che hanno ordini, DDT, commesse e resi: una fattura in bozza resta all'azienda di prima quando il BA cambia azienda |
| S28 | L'albero dei billing account | Nessun limite di profondità e nessun controllo dei cicli: è rifiutato solo «parent = sé stesso». Spostare un BA da un parent a un altro con attività da fatturare non è controllato (solo togliere il parent) |
| S29 | `billing_account.valuta_id` | Senza FK a `config.valute` (`fornitori` e `gestori` l'hanno) |
| S30 | `soggetti_ruoli.tipo_ruolo_id` | Non è bloccato: un ruolo `CL` può cambiare tipo dopo che il suo BA esiste |
| S31 ✔︎ | `trgfn_billing_account_guard_admin_globale`, `trgfn_billing_account_link_ef` | Un `app.current_user_id` che non è un numero è trattato come «nessun utente», e i due trigger lasciano passare la riga. ⚠️ **Riletta il 2026-11-23 sul corpo vivo**, dopo `20261123-19` (giro 8b di [brief-db-revisione-ui](../work-done/2026/brief-db-revisione-ui.md)): i due trigger leggono l'utente da `script.fn_utente_di_sessione`, che un valore illeggibile lo rifiuta, ma la chiamata è dentro `EXCEPTION WHEN OTHERS THEN v_user_id := NULL`: il BB solleva, i trigger ingoiano. **Resta aperta**; la correzione è togliere il blocco, come in `fn_id_fiscale_bloccato`, che dallo stesso changeSet lascia salire il rifiuto |
| S32 | `fn_lookup_utilities_per_ba` | Non confronta il codice del ruolo con il ruolo del BA; un id che non corrisponde a nessun BA non è rifiutato |
| S33 | `fn_crea_billing_account` | Senza sessione, i guard dell'azienda girano prima del collegamento che la funzione scrive. Con `usa_sequenza` spento il codice manca e il rifiuto è un NOT NULL, non un codice di dominio |
| S34 | I clienti | `trgfn_clienti_guard_ruolo_cliente` ripete un controllo che il BA fa già. In `fn_update_cliente` un delta che non è un oggetto dà l'errore tecnico di PostgreSQL, e `categoria_aggiornata` vale vero anche se la categoria non cambia. `fn_get_evento_stato_corrente_cliente` è STABLE PARALLEL SAFE e sui rifiuti chiama `fn_log_and_raise_error`, che non lo è. Il modello non dice in quali stati un cliente può nascere. Un cliente chiuso il giorno stesso dell'attivazione ha un periodo vuoto |
| S35 | `pdp` | `parent_istanza_id` di un'istanza può puntare alla riga stessa. Un PDP che ha avuto un cliente non si disattiva più (conta qualunque cliente). `DISM` non chiude niente. Nel contesto d'errore di `trgfn_pdp_a10_guard` la chiave è `column` invece di `campo`, quindi il form non evidenzia il campo; il contesto di `E_CODICE` in `trgfn_pdp_set_default_stato` è malformato, e uno stato passato all'INSERT non si giudica |
| S36 | `istanze_dati_precontrattuali` | Il blocco dopo il contratto guarda `vendite.contratti_utilities` e non `vendite.offerte_commerciali_utilities`, che pure nomina la riga; la DELETE risponde `E_COLONNA_NON_MODIFICABILE` senza campo; non c'è una porta di manutenzione |
| S37 | `vw_istanze_utilities_dettaglio`, `vw_pdp` | La prima non è `security_invoker` (oggi innocuo: le sue tabelle non hanno RLS). In `vw_pdp` il `LEFT JOIN clienti` non espone né filtra nulla, e la vista non espone `attivo` |

pgTAP mancanti, trovati scrivendo la sezione «Test»: nessun test proprio per `trgfn_clienti_guard_ruolo_cliente`,
`trgfn_clienti_set_periodo`, `fn_check_pdp_occupato`, `trgfn_billing_account_gen_codice`; il rifiuto per storia di
`fn_guard_ba_gestore_globale_storia` e il rifiuto all'INSERT di `trgfn_billing_account_guard_istanza_emittente` non
sono provati direttamente; di `trgfn_clienti_sync_stato_pdp` è provato solo il ritorno a DISP.

### 12.4 Le verifiche

* Il controllo meccanico rilanciato dalla sessione che coordina sulle 63 pagine dell'area: tutte nella cornice, data 22
  novembre 2026, nessun blocco di codice, nessun marcatore fuori dalle Note di migrazione, nessun link a `manual/` né
  morto. Gli unici nomi che il catalogo non conosce sono nomi di prima citati di proposito nelle Note di migrazione
  (`uq_clienti_istanza_utility`, `trgfn_pdp_protect_cols`, `trg_pdp_protect_cols_upd`). I due blocchi non contengono il
  tag include letterale.
* Le due guide: link e nomi verificati sul catalogo. L'avviso di markdownlint su `#area-tecnica-esempi` è un falso
  positivo (zensical toglie la lineetta e collassa i trattini).
* **La doc auto-generata è rigenerata da Tid il 2026-11-22** (passo 4): le sei schede delle pagine nuove le
  includono, e nell'indice dello schema nessun oggetto dell'area C porta più un marcatore come descrizione (i 92 che
  restano sono delle aree A, B, D, E). La rigenerazione ha cambiato anche `docs/it/backend/core/index.md`, che non è
  di questo lavoro e resta fuori dal commit: la descrizione di `api_tracciamento` diventa «Ultimo aggiornamento**: 22
  novembre 2026», segno che la pagina BE ha la data prima dello scopo (al team BE/FE).
* La build della doc non è lanciata.
* `billing_account.md` è di 178 righe: la tabella ha quattro policy, tre chiavi composte e i lock da spiegare.
* Residui fuori dai punti assegnati, da chiudere col giro della guida: in `gestione-delle-istanze-utility` restano due
  frasi di cronaca («Fino al 2026-10-08…», «decisione di Tid del…»).

### 12.5 Le pagine invecchiate dai changeSet del 2026-11-23

Le pagine del giro 0 sono scritte dal catalogo del 22. Il giorno dopo due cantieri vicini hanno riscritto otto
funzioni dello schema, senza toccarne le pagine. Riallineate dal passo A (2026-11-23), lette dal corpo vivo di dbdev:

* `20261123-03` ([brief-db-magazzino-tutte-le-scritture-dal-verbo](../work-done/2026/brief-db-magazzino-tutte-le-scritture-dal-verbo.md),
  P-5a) porta `fn_crea_emittente_fiscale`, `fn_crea_fornitore`, `fn_crea_cliente`, `fn_crea_billing_account`,
  `fn_crea_contatto` e `fn_indirizzo_elemento` a `script.fn_guard_campi_ammessi`. Il comportamento non cambia (stesso
  codice, stessa frase, `context.campo`): le sei pagine prendono il BB nel «Vedi anche».
* `20261123-19` ([brief-db-revisione-ui](../work-done/2026/brief-db-revisione-ui.md), giro 8b) porta `fn_id_fiscale_bloccato` e i due
  trigger del BA a `script.fn_utente_di_sessione`. La pagina di `fn_id_fiscale_bloccato` regge (dice «l'utente della
  richiesta», senza dire come si legge). Le due pagine dei trigger prendono il BB nel «Vedi anche» e, in «Che cosa
  oggi non copre», il blocco che ingoia l'errore (S31, §12.3).

⚠️ La lezione per i giri di codice: prima di toccare un oggetto si guarda se ha un changeSet più recente della sua
pagina. Le pagine di questo brief invecchiano anche coi cantieri degli altri.

## 13. Giro 0b — l'area A, 2026-11-22 (scritto, committato)

Stesso metodo del giro 0a: quattro agenti per gruppi di oggetti (il soggetto; il cambio di natura e i ruoli; i dati
societari; i titoli IVA) e uno per la guida, dai corpi del catalogo di dbdev, dalle schede e dai pgTAP.

### 13.1 Che cosa è scritto

* **Le 31 pagine esistenti dell'area A**, tutte nella cornice. Riscritte dal corpo `soggetti`, `soggetti_ruoli`,
  `dati_societari`, `trgfn_soggetti_normalize`, `fn_crea_soggetto_pf`, `fn_crea_soggetto_pg`, `soggetti_titoli_iva`,
  `soggetti_titoli_iva_ambiti`, `soggetti_titoli_iva_movimenti`; le altre allo standard, col contenuto riverificato.
* **21 pagine nuove**, tutte quelle di §5 per l'area A: la famiglia del cambio di natura (6), le regole per natura sul
  soggetto (4), i verbi dei dati societari (5), il titolo IVA ammesso dalla natura (6). Ogni oggetto dell'area A ha
  ora la sua pagina.
* **Quattro blocchi comuni**: `_identificativo-fiscale.md` (incluso in 4 pagine), `_cambio-di-natura.md` (6),
  `_dati-societari.md` (6), `_titolo-iva-per-natura.md` (7).
* **`guide/soggetti-e-ruoli-anagrafici.md`**, riscritta quasi per intero: i due verbi di nascita, la natura e le sue
  regole, l'identificativo bloccato, il cambio di natura, i dati societari coi verbi, i titoli IVA per natura; i ruoli
  con le specializzazioni vere (`RE` è il reseller, nessun referente); «Il soggetto non ha un emittente fiscale» al
  posto di §5a-bis; «Subito o al COMMIT» al posto dell'elenco dei trigger; due ER piccoli, veri colonna per colonna.
  Il titolo di §5b è rimasto identico perché due pagine di `script` lo linkano per anchor.

### 13.2 Che cosa ha corretto o aggiunto al censimento

* **S4, S20, S21, S30 reggono**, riverificate sui corpi. S4 si precisa: un doppione esatto (stesso CF, stessa P.IVA)
  lo ferma l'indice unico con l'errore tecnico, non un `E_ADMIN_*`; in `fn_crea_soggetto_pf` c'è l'asimmetria
  opposta (il pre-controllo ferma una ditta col CF di un privato, che l'indice ammetterebbe). S20 si precisa: la
  stringa vuota per un soggetto italiano la ferma il validatore del formato; fuori dall'Italia, o come P.IVA di un
  privato, passa e resta bloccata come valore scritto.
* **S21 è più largo**: `zeroerp_app` ha `arwd` su tutte le 19 viste di `anagrafiche`, non solo su
  `vw_risorse_umane_dettaglio`. E `trg_soggetti_a10_guard_obbligatori_ruoli_upd` è differito ma porta la fascia
  `a10` (gli altri differiti hanno `def`).
* **§6, «i guard dei dati societari sono immediati»**: vale per i guard delle regole (tipo soggetto, forma, canale:
  `BEFORE ROW`, non differibili). Sono differiti, su `dati_societari`, i due trigger generici del padre attivo, e su
  `soggetti` il guard «required» e quello della forma rispetto alla natura.
* **I motivi del cambio di natura sono 10 codici**, non 9 (§5 univa cliente PA e split payment). I «due rifiuti
  mancanti» di `soggetti_titoli_iva` (§4.2) sono `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI` e
  `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` sulla natura tolta.
* Il codice del lock di `trgfn_soggetti_gen_codice` è `E_CODICE_NON_MODIFICABILE` (§4.2 e la pagina vecchia dicevano
  `CODICE_NON_MODIFICABILE`, che resta in `config.messaggi_errore` come dice S21). Con la sequenza spenta funzione e
  trigger si tolgono, non restituiscono NULL.
* Il codice mancante di `trgfn_dati_societari_guard_tipo_soggetto` (§4.2) è `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`.
* `anagrafiche.soggetti` è in `config.storico_set_storicizza`: il suo storico è continuo, a differenza di S9. La
  tabella non ha RLS.
* La RLS dei tre titoli IVA concede le righe solo al ruolo `OPERATORE` col perimetro d'emittente: portale, shop e
  API non vedono nessun titolo.
* La matrice natura ↔ ruolo è «aperta» solo per un ruolo senza nessuna riga: basta una riga, anche spenta, a
  vincolarlo.
* Su `soggetti_ruoli` l'unica FK `RESTRICT` verso il ruolo è quella da `risorse_umane`; `fk_tipi_ruoli_config` è
  `NO ACTION`, `fk_soggetti_anagrafiche` è `CASCADE`.
* **§8.** M16 non vale per `trgfn_soggetti_guard_forma_giuridica_natura`, che ha solo un marcatore «Brief: …» nel
  COMMENT. M15 è più largo: dicono ancora il falso il COMMENT di `trgfn_soggetti_titoli_iva_guard_coerenza` («il nome
  sceglie l'ORDINE») e quello di `fn_consuma_plafond_titolo_iva_righe` («l'imponibile si legge dalla riga»: il corpo
  usa l'importo passato e pretende che coincida). Il commento nel corpo di
  `trgfn_soggetti_titoli_iva_guard_tipo_soggetto` nomina come vivo `trgfn_soggetti_guard_titoli_iva_ammessi`,
  ritirato il 2026-11-14 (il controllo è in `fn_check_cambio_natura_soggetto`).

### 13.3 Segnalazioni di codice nuove

Lette sui corpi dagli agenti del giro, non provate con un caso; ✔︎ = riletta sul catalogo dalla sessione che coordina.

| # | Dove | Che cosa |
| --- | --- | --- |
| S38 ✔︎ | `fn_check_cambio_natura_soggetto` | **Il passaggio per la natura vuota aggira i due motivi definitivi.** Con la natura nuova NULL si guardano solo i titoli IVA; i controlli di macro-tipologia e documenti girano solo se la natura vecchia c'è. X → NULL → Y, anche nella stessa transazione, porta una società a privato, o una ditta con documenti a privato. Nessun guard di `soggetti` rifiuta la natura NULL. Anche la natura ammessa dei ruoli non si ricontrolla al cambio di natura |
| S39 | Lo spegnimento del soggetto | **Un soggetto non si spegne.** Al COMMIT deve avere un contatto (`trgfn_soggetti_guard_soggetto_contatti`), e delle nove figlie che bloccano la disattivazione solo `risorse_umane` e `soggetti_titoli_iva` hanno `attivo`: le altre bloccano finché esistono. Una società di capitali non può togliere i dati societari; un ruolo nominato da un documento non si cancella. Da leggere come un tema solo |
| S40 | I permessi | `fn_soggetto_primo_documento` e `fn_titoli_iva_non_ammessi_conta` sono `SECURITY DEFINER` con EXECUTE a `PUBLIC`. `vw_soggetti_ruoli_dettaglio` non è `security_invoker` (oggi innocuo). Il DML sulle viste è in 13.2 (S21) |
| S41 | I dati societari | Una DELETE diretta non guarda la natura (la pretesa la tiene solo il verbo). Due prime scritture concorrenti in `fn_scrivi_dati_societari` urtano `uq_ds_soggetto` con l'errore grezzo. Una società di capitali creata senza forma riceve il `NOT NULL` (23502) senza codice. Il codice SDI di 6 o 7 caratteri vale per chiunque. Un cambio di `soggetti.stato_id` o delle policy della forma non rilegge le righe scritte. `trgfn_dati_societari_guard_tipo_soggetto` non ha fascia, parla dopo i guard di forma e canale e gira a ogni UPDATE (niente `OF`) |
| S42 | La natura ammessa dei ruoli | I messaggi di `E_RUOLO_NATURA_NON_AMMESSA` e `E_RUOLO_NATURA_TIPO_DET_NULL` mostrano gli id; il contesto non ha `campo`; una riga di matrice spenta non tocca i ruoli che esistono |
| S43 | Il soggetto | `trgfn_soggetti_normalize` scatta anche in modifica: un UPDATE che porta `stato_id` a NULL riceve lo stato proposto. Il dispatch del CF/P.IVA non ha `UPDATE OF`: un soggetto con un CF che il validatore non accetta non si modifica in nessun campo; con una natura inesistente va in errore tecnico (`INTO STRICT`) prima della FK; uno stato senza validatore passa. Il DB non normalizza CF e P.IVA (maiuscole); `stato_id`, metà della chiave fiscale, non è bloccato; la stringa vuota conta come «scritta». `ragione_sociale_completa` è NULL se manca nome o cognome; `codice` ammette NULL. Nei due verbi di nascita il tipo di contatto di ripiego è «il primo per id» |
| S44 | I titoli IVA | Nessuno verifica che il titolo di un movimento di fattura sia del cliente e dell'emittente della fattura. Un titolo spento si ferma solo al COMMIT. Nessuna funzione scrive i movimenti `NOTA_CREDITO`, e niente impedisce di restituire più di quanto la fattura aveva consumato. Un titolo sfondato non lo segnala nessuno. `imponibile_utilizzato` si aggiorna direttamente e resta fino al movimento successivo. La regola «un titolo per tutto non ha ambiti» è in due sedi (`trgfn_soggetti_titoli_iva_guard_coerenza` e `fn_check_titolo_iva_ambito`). Il rifiuto di `trgfn_soggetti_titoli_iva_guard_ambito` indica sempre `valido_al` |

pgTAP mancanti, trovati scrivendo la sezione «Test»: nessun test proprio per `trgfn_soggetti_gen_codice`,
`trgfn_soggetti_normalize`, `fn_regime_pa_campo_non_ammesso`, `trgfn_soggetti_guard_forma_giuridica_natura` (provato
solo per comportamento), `vw_soggetti_ruoli_dettaglio`.

### 13.4 Le verifiche

* Il controllo meccanico rilanciato dalla sessione che coordina sulle 52 pagine dell'area: tutte nella cornice, data
  22 novembre 2026, nessun blocco di codice, nessun marcatore fuori dalle Note di migrazione, nessun link a `manual/`
  né morto. I nomi che il catalogo non conosce stanno tutti nelle Note di migrazione (`fn_consuma_plafond_titolo_iva`,
  `trgfn_soggetti_guard_titoli_iva_ammessi`, `clienti.iva_id`). I quattro blocchi non hanno `##` né il tag include.
* La guida: link tutti vivi, nessun link a `manual/`, a brief o col prefisso `/it`, blocchi solo `mermaid`.
* **La doc auto-generata è rigenerata da Tid il 2026-11-22** (passo 4): le 21 schede delle pagine nuove le
  includono; nell'indice restano 57 marcatori, delle aree B, D, E.
* Misura: `soggetti` (196 righe), `soggetti_titoli_iva` (199), `soggetti_titoli_iva_movimenti` (191) passano il
  tetto di 150; una trentina di righe a testa sono del «Vedi anche».
* La build della doc non è lanciata.

## 14. Giro 0c — l'area B, 2026-11-22 (scritto, committato)

Stesso metodo: sei agenti per gruppi di oggetti (i contatti, con la loro guida; il catasto; l'indirizzo, lo stradario
e le viste risolte; il tipo d'indirizzo ammesso; gli indirizzi obbligatori; i verbi di creazione e di copia) e uno
per la guida degli indirizzi.

### 14.1 Che cosa è scritto

* **Le 37 pagine d'oggetto dell'area B**, tutte nella cornice; riscritte dal corpo quelle che §4.3 dava da
  riscrivere.
* **28 pagine nuove**, tutte quelle di §5 per l'area B: il tipo d'indirizzo ammesso e il picker (10), gli indirizzi
  obbligatori (11), la copia di un indirizzo (7). Ogni oggetto dell'area B ha ora la sua pagina.
* **Q3 applicata**: `manual/catasto-architettura.md` è diventata la guida `guide/catasto-delle-istanze.md`,
  registrata nella nav di `mkdocs.yml` e `mkdocs.zensical.yml` e in `docs/it/readme.md`; i link delle quattro pagine
  del catasto e di `generazione-cliente` puntano lì. La pagina di `manual/` è tolta.
* **Cinque blocchi comuni**: `_contatto-predefinito.md` (incluso in 3 pagine), `_indirizzo-libero-o-dettaglio.md` (5),
  `_tipo-indirizzo-ammesso.md` (12), `_indirizzi-obbligatori.md` (11), `_copia-indirizzo.md` (5).
* **Le guide**: `gestione-dei-contatti` riallineata per intero (la chiave del predefinito, il guard del contesto, il
  verbo, l'ordine di `script.fn_get_contatti`, gli ER rifatti, gli esempi col verbo); `gestione-degli-indirizzi`
  corretta nei punti di §6 (lo storico, `proc_bump_indirizzi_dettaglio`, le colonne, l'esempio di indirizzo
  normalizzato, i due guard mancanti nella tabella), più in R9 il titolare che non si cambia e il titolare che resta
  bloccato da un requisito nuovo.

### 14.2 Che cosa ha corretto o aggiunto al censimento

* **S3, S8, S10, S11, S16, S19 reggono**, riverificate sui corpi. S3 è più larga: la colonna `cap` di un libero è il
  CAP di una via del comune (quello della riga è `cap_codice`), e in un comune senza vie `cap` e `provincia` restano
  vuoti. S10 è più larga: palazzina, scala, piano e interno si confrontano grezzi come l'estensione; l'errore senza
  criteri non ha codice; `p_limit` negativo dà l'errore tecnico; `%` e `_` fanno da jolly; la ricerca per testo non
  usa l'indice trigram. S19: per comune e CAP il rifiuto arriva dal giudizio della forma, non dalla FK; per uno stato
  tolto il normalize scrive lo stato proposto, e un indirizzo estero cambia stato senza che nessuno lo dica.
* **S9 è più largo nel perimetro e nella cancellazione.** Lo storico a richiesta vale anche per `config.stradario`.
  `indirizzi_soggetti` invece ha lo storico continuo (`storicizza` nasce `true`, la tabella è nel registro), come
  `catasto_unita_immobiliari`. E una **DELETE** su una tabella a richiesta lascia traccia solo se il flag *salvato*
  sulla riga è acceso: dopo ogni modifica il trigger lo rimette a `false`, quindi cancellare un indirizzo di ruolo,
  un civico o una via lascia traccia solo se la riga è stata scritta con `true` e non più modificata. Da aggiungere a
  R-BE5 e da vagliare: la decisione Q7 riguarda le modifiche, non è detto che copra le cancellazioni. Il COMMENT di
  `indirizzi_dettaglio.storicizza` dice «Default=True» (è `false`). La guida sbagliava anche il tipo di operazione
  dello storico (1/2/3, non A/U/D).
* **`contatti`**: la FK del ruolo è `ON UPDATE CASCADE` senza azione in cancellazione (lo è solo quella del soggetto).
  Il falso più grosso della pagina di `fn_crea_contatto` era «il primo contatto di un ruolo diventa default».
* **Il catasto**: `CATASTO_SOURCE_NOT_FOUND` non è più nemmeno in `config.messaggi_errore`. Il trigger del cliente che
  aggancia il parent è `BEFORE INSERT OR UPDATE OF pdp_id, data_attivazione`. Le tabelle del catasto non hanno né
  azienda né RLS. **`db/pgtap/anagrafiche/test-catasto-unita-immobiliare.sql` prova la colonna `istanza_utility_id` e
  la sua FK, che non esistono più**: era nelle baseline dei rossi come `ERRORE_FIXTURE`. **Ritirato** (Tid, 2026-11-22): file tolto, le sue tre righe
  tolte dalle baseline, le sezioni «Test» delle pagine aggiornate; il catasto resta provato da `test-simula-subentro.sql`.
* **Il cambio di titolare di un indirizzo** si raggiunge solo dalla porta di manutenzione: prima scattano i lock
  (`E_INDIRIZZO_*_TITOLARE_IMMUTABILE`). I guard degli obbligatori su `indirizzi` e `indirizzi_soggetti` sono
  differiti solo su UPDATE e DELETE; alla nascita li pretendono quelli su `soggetti` e `soggetti_ruoli`.
* **La fascia dei trigger differiti** (13.2): «i differiti hanno `def`» vale per `soggetti`; su `indirizzi` e
  `indirizzi_soggetti` tutti i differiti hanno `a10`. Non è un difetto di quelle due tabelle.
* `proc_bump_indirizzi_dettaglio` ha un chiamante: `maintenance.proc_bump_toponomastica`. Nessun oggetto del DB
  chiama `fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli` (lettura del BE), che a differenza delle gemelle non
  prende `p_oggi`. Il terzo ripiego di `indirizzo_display` in `vw_indirizzi_resolved_base` non si raggiunge mai: il
  display di un libero è via e numero, senza il luogo. Il registro `config.azioni_riga` tiene `COPIA_INDIRIZZO_RUOLO`
  spenta, e punta a due oggetti ritirati: voluto.
* Su `soggetti`, `soggetti_ruoli`, `indirizzi`, `indirizzi_soggetti`, `contatti` la RLS è spenta: i guard e le check
  `SECURITY INVOKER` vedono tutto, e il COMMENT di `fn_check_tipo_indirizzo_soggetto` («i tipi che chi chiama vede»)
  promette un filtro che non c'è.
* **§8.** M17 confermato e più largo (i lettori veri dei due predicati del tipo ammesso). Il COMMENT di
  `fn_indirizzi_con_obbligatori` porta marcatori di cantiere; quelli di `contatti.default_context` («soggetto|ruolo|
  utility») e `contatti.is_default` («per il soggetto») sono stantii.
* Fuori da `anagrafiche`: `config.tipi_ruolo_tipi_indirizzo` ha due FK uguali su `tipo_ruolo_id`
  (`fk_tipi_ruoli_tipi_indirizzo_ruolo`, `fk_tipi_ruolo_tipi_indirizzo_tipo_ruolo`).

### 14.3 Segnalazioni di codice nuove

Lette sui corpi dagli agenti del giro, non provate con un caso salvo dove detto.

| # | Dove | Che cosa |
| --- | --- | --- |
| S45 | Il contatto obbligatorio | Cancellare l'ultimo contatto passa (il guard scatta solo sulle scritture del soggetto), e dopo ogni modifica del soggetto è rifiutata qualunque cosa cambi. `soggetti.default_contatto_id` non si svuota mai; cancellare il contatto puntato è rifiutato al COMMIT dalla FK differita. Ogni scrittura del predefinito del contesto `soggetto` riscrive il soggetto e ne fa scattare tutti i trigger. Da leggere con S39 |
| S46 | `fn_crea_contatto` | Il doppione per tipo dà l'errore grezzo `23505`; un `tipo_contatto_id` non numerico dà un errore di conversione invece di `E_CONTATTO_INCOMPLETO`; `default_context` è fra le chiavi ammesse ma il valore è sostituito |
| S47 | Il catasto | Il clone si fa una volta: un cambio di catena dopo il clone, o un'unità comparsa dopo sulla precedente, non arrivano; un'istanza inserita con la precedente già scritta non riceve il clone (il trigger è solo su UPDATE). La ponte non si pulisce al cambio di civico o di unità, e col blocco ATTIVO quel civico non si spegne più. Un'unità lasciata da un'istanza resta orfana |
| S48 | Gli indirizzi obbligatori | **Un requisito nuovo blocca chi esiste.** Una riga di matrice che diventa obbligatoria non rigiudica nessuno, ma i due trigger dei titolari scattano a ogni UPDATE (niente `OF` né `WHEN`): la prossima scrittura del soggetto o del ruolo, su qualunque colonna, è rifiutata. Il ripiego del livello soggetto non si confronta con la natura, e il rifiuto può proporre un ripiego che il guard del tipo non lascia scrivere. I due trigger sugli indirizzi chiamano il guard senza `tx_id`. `fn_indirizzi_con_obbligatori` ignora il ripiego: con il ripiego nell'elenco nasce comunque la copia del tipo. «Obbligatorio per la natura» è calcolato in quattro sedi (i due picker, `fn_indirizzi_obbligatori_mancanti_soggetto`, `fn_crea_indirizzi_soggetto`); sul ruolo in una sola |
| S49 | Il tipo d'indirizzo | Il cambio del tipo di ruolo (S30) non rigiudica gli indirizzi che il ruolo ha. `fn_indirizzo_elemento` non verifica il tipo per id (provato con una chiamata in sola lettura: l'id 999999 torna senza errore; con id e codice vale l'id e il codice non si confronta): il rifiuto arriva dalla FK, non da `E_TIPO_INDIRIZZO_NON_TROVATO`. `fn_tipo_indirizzo_ammesso_per_ruolo` prende il tipo di ruolo `bigint`, `fn_check_tipo_indirizzo_ruolo_su_contesto` `integer` |
| S50 | La normalizzazione | Con una via non risolta, un INSERT diretto o la modifica di un civico falliscono sul NOT NULL di `via_norm` senza codice (solo il «trova o crea» dà `E_INDIRIZZO_VIA_NON_RISOLTA`). Un elemento senza forma, anche un libero col testo vuoto, finisce sui NOT NULL dello stradario e non arriva al guard della forma libera. ~~La porta `zeroerp.maintenance_indirizzi_dettaglio` è un parametro di sessione che chiunque scriva accende.~~ ⚠️ Questo pezzo esce da T7 (Tid, 2026-11-23, D-D): lo chiude il giro 1 di [brief-db-porte-aperte-dalla-sola-guc](brief-db-porte-aperte-dalla-sola-guc.md), con la porta della toponomastica. `geoloc` è una copia presa alla scrittura e non segue `civic_geoloc` |
| S51 | I permessi | Come S21 e 13.2: `zeroerp_app` ha il DML sulle cinque viste degli indirizzi, che non sono aggiornabili; non sono `security_invoker` (oggi innocuo: le tabelle sotto non hanno RLS) → Chiusa il 2026-11-23: postura di tutto il database, decisa da Tid, lavoro di `brief-db-porte-aperte-dalla-sola-guc` §5 (§19.3) |

pgTAP mancanti: nessun test proprio per `trgfn_soggetti_guard_soggetto_contatti`, né per il passaggio del segno fra
due contatti dello stesso contesto; l'intestazione di `test-contatti-soggetto-cliente.sql` parla di un «tipo_contatto
NULL» che il NOT NULL non ammette. Il pgTAP del catasto è in 14.2.

### 14.4 Le verifiche

* Il controllo meccanico rilanciato dalla sessione che coordina sulle 65 pagine d'oggetto dell'area: tutte nella
  cornice, data 22 novembre 2026, nessun blocco di codice, nessun marcatore fuori dalle Note di migrazione, nessun
  link a `manual/` né morto, nessun nome che il catalogo non conosce. I cinque blocchi non hanno `##` né il tag
  include.
* Le tre guide: link tutti vivi, nessun link a `manual/`, a brief o col prefisso `/it`.
* **La doc auto-generata è rigenerata da Tid il 2026-11-22** (passo 4): le 28 schede nuove includono le pagine,
  `index.ci.md` non nomina più `manual/catasto-architettura`, e nell'indice restano 36 marcatori, delle aree D ed E.
* `indirizzi_dettaglio.md` è di 154 righe. La build della doc non è lanciata.

## 15. Giro 0d — l'area D, 2026-11-22 (scritto, committato)

Stesso metodo: quattro agenti per gruppi (le banche e i conti, con la loro guida; l'emittente fiscale; fornitori e
vettori, che hanno scritto il blocco dei guard di ruolo; gestori, reseller e PSP).

### 15.1 Che cosa è scritto

* **Le 45 pagine esistenti dell'area D**, tutte nella cornice; riscritte dal corpo quelle che §4.4 dava da riscrivere,
  più `fornitori`, `vettori`, i due `gen_codice`, `vw_fornitori_dettaglio`, `emittenti_fiscali` ed
  `emittenti_fiscali_utilities`.
* **Una pagina nuova**, `trgfn_emittenti_fiscali_guard_codice_forma`: ogni oggetto dell'area D ha la sua pagina.
* **Q4 applicata**: la pagina di `trgfn_emittenti_fiscali_guard_attivo` è tolta, e «dove vive oggi la regola» (i
  trigger `prevent_deactivate` generati dalle FK) sta nella pagina `emittenti_fiscali`.
* **Il blocco comune `_guard-di-ruolo.md`**, incluso negli **otto** guard di ruolo: i sette dell'area D e quello del
  cliente (`trgfn_clienti_guard_ruolo_cliente`, area C, a cui la sessione che coordina ha aggiunto l'include).
* **`guide/gestione-conti-bancari.md`**, riscritta sul modello di `gestione-dei-contatti`: i cinque punti di §6, più
  le filiali, i canali d'incasso e «Che cosa il database non tiene».

### 15.2 Che cosa ha corretto o aggiunto al censimento

* **I guard di ruolo sono otto, non sette** (c'è anche il cliente, `CL`). I corpi sono identici salvo il codice del
  ruolo; tre commenti nel corpo dicono ancora «nuovo o esistente». Il codice del lock su fornitori e vettori è
  `E_CODICE_NON_MODIFICABILE`.
* **S12, S15, S18 reggono.** **S13 si corregge**: `psp.attivo` qualcosa ferma, perché
  `pagamenti.trgfn_enti_incasso_guard_psp` vuole un PSP attivo perché un ente d'incasso PSP nasca o si modifichi; il
  difetto è solo il verso opposto (lo spegnimento o la cancellazione di un PSP con enti attivi).
* **L'esclusione del legame del ruolo** (`ex_src_…`) vieta lo stesso conto d'incasso su due **ruoli**, anche dello
  stesso soggetto, non su due soggetti come diceva §4.4. Le due esclusioni (soggetto e ruolo) non si incrociano, ed
  è voluto (COMMENT di `ex_scb_…`).
* La sigla dell'emittente entra anche nel codice delle distinte d'incasso (`DIS-<sigla>-…`), non solo delle commesse.
  Il commento nel corpo di `trgfn_emittenti_fiscali_guard_codice_forma` e il test 9 del suo pgTAP dicono
  `varchar(10)`: la colonna è `varchar(32)`, il limite di 10 lo tiene il CHECK.
* `vendite.fn_build_fattura_key` prende il reseller del BA con `ORDER BY rb.id LIMIT 1`, senza guardare il periodo:
  un legame chiuso vale come uno aperto (va con S12).
* Le quattro tabelle dei conti, `resellers` e `psp` sono in `config.storico_set_storicizza`: storico continuo. Nessuna
  tabella dell'area ha RLS. `config.utilities` non ha `attivo`.
* `db/pgtap/anagrafiche/create-soggetto-gestori.sql`, l'unico che prova il secondo gestore, è nelle baseline dei
  rossi: il suo test 4 si aspetta un P0001 generico senza codice.
* **Ricaduta BE**: `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md` (riga 90) nomina
  `trgfn_emittenti_fiscali_guard_attivo`, che non esiste: da correggere dal team BE (testo, non link).
* **§8.** COMMENT stantii: `vettori.soggetto_ruolo_id` («ruolo atteso: RES»), il COMMENT della tabella `resellers`
  («RES»: il codice è `RE`), `fornitori.rating` («0-100 o 1-5», il CHECK è 0..100), `trgfn_resellers_normalize`
  (promette un generatore), la tabella `emittenti_fiscali` (M5).

### 15.3 Segnalazioni di codice nuove

Lette sui corpi dagli agenti del giro, non provate con un caso.

| # | Dove | Che cosa |
| --- | --- | --- |
| S52 | Gli otto guard di ruolo | Il cambio di `soggetti_ruoli.tipo_ruolo_id` (S30) non fa scattare i guard: un ruolo `FO` portato a `VT` lascia la riga di `fornitori` su un ruolo vettore. Vale per tutte le specializzazioni. Nessun pgTAP prova il rifiuto `E_SOGGETTI_RUOLI` |
| S53 | Lo spegnimento dell'emittente | Fatture, commesse, registri, listini, lotti, distinte, sistemazioni e `dbops.coda_lavori` puntano a `soggetti_ruoli` e non fermano lo spegnimento: un emittente con fatture si spegne, uno con un ordine no. Un primo emittente nato spento è respinto al COMMIT con `E_ATTIVO_PADRE_NON_ATTIVO`. `emittenti_fiscali.valuta_id` è senza FK (con S29). → Tema proprio T12, con la regola di Tid (§17.1); la FK della valuta va con S29 in T4 |
| S54 | Le letture dell'emittente | `fn_get_emittente_fiscale_id` e `_pk` danno un'azienda a un id di BA che non esiste; `fn_parametri_importo_utility` non rifiuta un ruolo che non è un emittente. Il maiuscolo della sigla si fa due volte (`a05` e `a15`) |
| S55 | I conti | L'IBAN si modifica sotto i legami. `uso` del legame del ruolo non è bloccato: un canale d'incasso resta appeso a un legame che non è più `INCASSO`. Il soggetto del ruolo non deve essere attivo (il gemello sul soggetto lo pretende). Un predefinito a scadenza non è programmabile: l'indice del predefinito ignora la validità. Il normalize toglie solo gli spazi (un trattino resta e il CHECK rifiuta). Il BIC non si normalizza; filiale e IBAN non si confrontano; la stessa coppia ABI/CAB è ammessa su due banche. `iban_snapshot` del mandato SEPA non si confronta col conto |
| S56 | Fornitori e vettori | `fornitori.soggetto_ruolo_id` non è bloccato (un fornitore si sposta su un altro soggetto). `vendite.ddt.vettore_soggetto_ruolo_id` ha la sola FK su `soggetti_ruoli`: nessuno chiede che sia `VT`, che abbia una riga in `vettori`, che sia attivo. «Fornitore attivo» sta in due corpi (`fn_check_fornitore_attivo`, `fn_guard_fornitore_attivo`), che nessun oggetto del DB chiama; `E_FORNITORE_BLOCCATO` riempie il segnaposto dell'id con una frase |
| S57 | Gestori e reseller | Il gestore unico è una lettura, non un vincolo: due inserimenti concorrenti passano. La P.IVA del gestore si giudica solo quando si scrive il gestore. Nessun oggetto legge `gestori_utilities`. `resellers_billing_account` non ha guard di ruolo; il guard attivo dei reseller conta anche i legami chiusi, quindi un reseller che ha avuto clienti non si spegne senza cancellarne la storia |
| S58 | I permessi | Come S21: `zeroerp_app` ha il DML su `vw_fornitori_dettaglio` e `vw_conti_bancari_per_ruolo`, viste non aggiornabili; la prima non è `security_invoker` → Chiusa il 2026-11-23: come S51 (§19.3) |

pgTAP mancanti: nessun test prova `E_CONTO_BANCARIO` su un conto spento, la normalizzazione dei conti, il guard SEPA,
il rifiuto di un ruolo non `BANK_B` o non `EF`, `E_EMITTENTE_DEFAULT_SINGLETON` al COMMIT, né gli oggetti di gestori,
reseller e PSP salvo il gestore unico (rosso).

### 15.4 Le verifiche

* Il controllo meccanico rilanciato dalla sessione che coordina sulle 46 pagine dell'area e su quella del cliente:
  tutte nella cornice, data 22 novembre 2026, nessun blocco di codice, nessun marcatore fuori dalle Note di migrazione,
  nessun link a `manual/` né morto. I nomi che il catalogo non conosce stanno nelle Note di migrazione
  (`trgfn_emittenti_fiscali_guard_attivo`, `uq_gestori_singleton`) o sono una sequenza (`vettori_codice_seq`). Il
  blocco non ha `##` né il tag include. La guida: link vivi, nessun link a `manual/` o a brief.
* ~~La doc auto-generata è da rigenerare~~ ✅ rigenerata da Tid il 2026-11-22, prima del giro 0e.
* `emittenti_fiscali.md` è di 176 righe (21 trigger di spegnimento da spiegare). La build della doc non è lanciata.
* **Ritirato anche il pgTAP del catasto** (14.2), nello stesso albero: ✅ committato con questo giro.

## 16. Giro 0e — l'area E, 2026-11-22 (scritto, committato)

Stesso metodo: quattro agenti per gruppi (la sincronizzazione dell'accesso e la veste; la risorsa umana, l'ultimo
SUPER_ADMIN, il reparto e le viste degli accessi; i verbi; le due guide). Le pagine sono lette dai corpi del catalogo di
dbdev. Con questo giro il giro 0 è finito: tutte e cinque le aree sono scritte.

### 16.1 Che cosa è scritto

* **Le 23 pagine dell'area E**, tutte nella cornice; riscritte dal corpo quelle che §4.5 dava da riscrivere
  (`risorse_umane`, `trgfn_identita_digitali_sync_auth_user_active`, `fn_sync_auth_user_expired`,
  `fn_crea_risorsa_umana_v2`), più `identita_digitali` (ritocco largo, M4) e le pagine dei verbi.
* **Due blocchi comuni** (Q2, le due famiglie già documentate di §5): `_sincronizzazione-accesso.md` (la regola «la
  credenziale è accesa se almeno una veste è utilizzabile», le tre strade che la tengono allineata, il job orario, ciò
  che nessun trigger copre), incluso nelle quattro pagine della famiglia; `_ultimo-super-admin.md` (le quattro sedi del
  guard, in `anagrafiche` e in `config`, e le check di `script`), incluso nei due guard di `anagrafiche`.
* **S7 chiusa sulla documentazione**: pagine e guide dicono «ogni ora al minuto 10»; il nome del job resta.
* **`guide/risorse-umane-e-accessi.md`** rivista per intero: `DISABILITATO` non è più una veste viva (il valore resta
  nel tipo, la tabella lo rifiuta con `E_RUOLO_APPLICATIVO_RITIRATO` e il CHECK `chk_identita_digitali_ruolo_non_ritirato`);
  l'assunzione è una tabella «caso → verbo»; le colonne vere dei trigger di sync; il nome del trigger del reparto;
  nuove le sezioni «persona o macchina», lo stato della veste, le liste degli accessi; tolto il modello del ponte.
* **`guide/architettura-multi-face-auth.md`**, solo §3.1 (la veste nasce spenta quando passa dall'invito: l'operatore
  sempre, il portale può nascere acceso, l'utente tecnico nasce acceso), §3.3 (la veste `OPERATORE` tecnica), §6.4 (un
  rimando che puntava a una guida che non ne parla), §9 (il trigger su `risorse_umane` fra chi chiama la sync).

### 16.2 Che cosa ha corretto o aggiunto al censimento

* **S5 si corregge.** Il terzo caso (lo spegnimento del soggetto) oggi non si raggiunge: il blocco dello spegnimento
  dai figli su `soggetti` conta ogni riga di `soggetti_ruoli`, che non ha `attivo`, e una veste ha sempre un ruolo. Il
  primo caso (il cambio di `auth_user_id`) il batch lo riallinea solo se alla credenziale di prima resta un'altra veste:
  vedi S59. Si aggiungono il cambio di `soggetto_ruolo_id` e di `tecnica` della veste, e la nascita del rapporto dopo
  la veste (S60).
* **Le colonne dei trigger di sync**: quello della veste scatta su `attivo`, `valido_dal`, `valido_al`,
  `ruolo_applicativo`, `auth_user_id`, senza `WHEN` (anche a valore uguale); quello del rapporto su `attivo`,
  `valido_dal`, `valido_al`, solo se cambiano. «Cinque colonne» di §6 vale per il primo.
* **`trgfn_risorse_umane_guard_ruolo` non è un guard di ruolo come gli altri otto**: rifiuta anche un `soggetto_id`
  diverso da quello del ruolo (`E_RISORSA_UMANA_SOGGETTO_MISMATCH`), quindi non include `_guard-di-ruolo.md`.
* **`trgfn_identita_digitali_guard_natura_credenziale` non reggeva** sulla forma: era fuori cornice.
* **Il profilo SUPER_ADMIN non ha un id scritto**: lo risolve `config.fn_profilo_super_admin_id`; il legame lo
  scrive `fn_crea_risorsa_umana_v2`, poi lo mettono e lo tolgono `config.fn_lega_profilo_identita` e `_slega_`.
* **`risorse_umane` ha più trigger di quelli censiti**: quattro blocchi di spegnimento dai figli (commesse, pratiche,
  flussi, competenze sui flussi), tre controlli differiti sui padri accesi (soggetto, qualifica, reparto), lo storico.
* **I chiamanti dei verbi dentro il DB**: `fn_crea_risorsa_umana_v2` solo da `fn_crea_operatore_v2`; questa dal
  provisioning e dalla fixture `dbops.fn_pgtap_crea_operatore_umano`; `fn_crea_veste_portale` solo dal provisioning;
  `fn_provisiona_dati_di_sviluppo` da nessuno. Nessun pgTAP chiama `fn_accendi_veste` direttamente.
* Nella guida: la tabella dei guard citava un blocco di spegnimento per i binding di profilo, che non esiste (c'è solo
  per quelli di scope), e chiamava «trigger» `script.fn_check_user_emittente_scope`, che è una funzione booleana.
* **`pgagent.pga_job.jobdesc` di `sync_auth_user_expired_daily`** è stantio («disattiva», «una volta per giorno
  aziendale»): va nel giro dei metadati con §8.
* **§8, COMMENT falsi o stantii trovati**: la tabella `identita_digitali` e `auth_user_id` (M4 confermato); la colonna
  `tecnica` («non ha MAI il profilo SUPER_ADMIN», non presidiato, S63); `fn_sync_auth_user_expired` e
  `maintenance.proc_sync_auth_user_expired_job` («batch notturno», «disattiva»: oggi orario e nei due versi);
  `fn_crea_risorsa_umana_v2` (M11 confermato) e `fn_crea_operatore_v2` (elenco di revisioni con nomi di brief);
  `trgfn_risorse_umane_guard_ruolo` (tace il controllo del soggetto; l'intestazione del corpo parla di fornitori);
  `script.fn_veste_utilizzabile` (M18 confermato); la nota di `E_PROFILO_ULTIMO_SUPER_ADMIN` in `config.codici_errore`
  (una sede sola, «post-cutover»); la `causa` vuota di `E_RISORSA_UMANA_SOGGETTO_MISMATCH`; i commenti nei corpi che
  parlano ancora di `DISABILITATO` (sync della veste, `fn_crea_operatore_v2`). Senza COMMENT: la tabella
  `risorse_umane` e quasi tutte le sue colonne, la vista `vw_risorse_umane_dettaglio`.

### 16.3 Segnalazioni di codice nuove

Lette sui corpi dagli agenti del giro, non provate.

| # | Dove | Che cosa |
| --- | --- | --- |
| S59 | La credenziale senza vesti | Nessun trigger segue la cancellazione di una veste (`zeroerp_app` ha il DELETE su `identita_digitali`) né lo spostamento della sua `auth_user_id`; se era l'ultima veste della credenziale, la credenziale resta accesa per sempre, perché `fn_sync_auth_user_expired` guarda solo le credenziali che hanno vesti. Lo stesso per una credenziale creata da `fn_crea_auth_user` (nasce accesa) e mai vestita. Si vede solo nel presidio `vw_credenziali_da_sanare` (`NESSUNA_VESTE`). In compenso `fn_sync_auth_user_is_active`, chiamata su una credenziale senza vesti, la spegne |
| S60 | La sync, i casi lasciati al batch | Il cambio di `soggetto_ruolo_id` o di `tecnica` della veste non fa scattare la sync; il trigger del rapporto non scatta sull'INSERT, quindi un rapporto nato dopo la veste la rende utilizzabile senza sync. Li riallinea il job entro l'ora |
| S61 | L'ultimo SUPER_ADMIN | Il guard della veste guarda solo `attivo` e le date: spostare la veste dell'ultimo amministratore su un'altra credenziale (anche bloccata), su un ruolo col rapporto chiuso, o farla diventare non OPERATORE, non passa da nessun guard. Un profilo SUPER_ADMIN si porta a un altro `tipo` senza guard. Con la porta di manutenzione aperta si cancella il rapporto dell'ultimo amministratore: il guard del rapporto scatta solo sull'UPDATE |
| S62 | `trgfn_risorse_umane_guard_identita_attiva` | Cerca la veste su `NEW.soggetto_ruolo_id`: uno spegnimento che nella stessa modifica sposta il ruolo passa, con la veste accesa sul ruolo di prima |
| S63 | La veste tecnica | `trgfn_identita_digitali_guard_coerenza` legge `tecnica` solo nel ramo OPERATORE: una veste di portale o di shop con `tecnica = true` passa. Nessun controllo impedisce il SUPER_ADMIN su un'identità tecnica, contro il COMMENT della colonna; `script.fn_is_super_admin_account` non esclude `tecnica` |
| S64 | `script.fn_stato_veste` | `ATTIVO` vuol dire «accesa», non «utilizzabile»: una veste accesa e scaduta, o col rapporto chiuso, è `ATTIVO` in `vw_accessi_altri`. Il COMMENT lo dichiara come scelta: da dire se resta. → Si decide nel brief degli accessi (T9, §17.1) |
| S65 | `fn_crea_risorsa_umana_v2` | Oltre a S6: con `p_valido_dal` passato nullo l'INSERT del rapporto fallisce sul NOT NULL (23502, senza codice del catalogo), e il ripiego sul giorno operativo scritto per la veste non si raggiunge; chiamata da sola, non controlla che la credenziale abbia già una veste OPERATORE spenta (gli indici unici valgono per le vesti accese) |
| S66 | `fn_provisiona_dati_di_sviluppo` | Al rilancio riaccende le vesti ma non rimette il SUPER_ADMIN di `dev.smoke`, né le date, il rapporto o il soggetto: un utente di prova scaduto resta senza accesso |
| S67 | La veste dello shop | Il COMMENT di `fn_crea_veste_portale` la fa nascere accesa; `architettura-multi-face-auth` §8.2 la disegna spenta, accesa dalla verifica dell'email. Lo shop self-service non c'è ancora: da decidere quale dei due vale. → Si decide nel brief degli accessi (T9, §17.1) |
| S68 | I permessi delle viste | Come S21 e S58: `zeroerp_app` ha il DML anche su `vw_accessi_altri` e `vw_accessi_sistema`; `vw_risorse_umane_dettaglio` non è `security_invoker` (sotto non c'è RLS) → Chiusa il 2026-11-23: come S51 (§19.3) |

pgTAP mancanti: nessun test prova la cancellazione o lo spostamento dell'ultima veste rispetto a `is_active`, il batch
che lascia fuori le credenziali senza vesti e la sua seconda chiamata a vuoto, i casi di S61, i due rifiuti di
`trgfn_risorse_umane_guard_ruolo`, `fn_accendi_veste` direttamente, gli indirizzi e le date di `fn_crea_operatore_v2`,
`vw_risorse_umane_dettaglio`. Quattro test della famiglia sono rossi in baseline: `test-sync-auth-user-is-active-multi-role`
(in tutte e tre; il suo caso 3 si aspetta «nessuna modifica» su una credenziale senza vesti, vero solo se è già spenta),
`test-fn-sync-auth-user-is-active-or`, `test-identita-digitali-unique-multi-veste`, `test-identita-digitali-guard-coerenza`
(scratch e CI).

**Al team BE/FE, da verificare** (R-BE6; l'agente dei verbi ha letto `backend/`, fuori dal perimetro di una sessione DB:
le due righe sono domande, non fatti): `PortaleRepository.create_auth_user_portale` scrive `django.auth_user` senza
passare da `fn_crea_auth_user`, e salta il controllo dell'email in minuscolo? `PortaleRepository.disattiva_identita`
spegne la veste con un UPDATE scritto a mano invece che da un verbo? Va con S59: una veste spenta o cancellata dal BE
decide se la credenziale resta accesa.

### 16.4 Le verifiche

* Il controllo meccanico rilanciato dalla sessione che coordina sulle 23 pagine: tutte nella cornice, data 22 novembre
  2026, firma in fondo, nessun blocco di codice, nessun marcatore fuori dalle Note di migrazione, nessun link a
  `manual/` né morto. I nomi che il catalogo non conosce (`fn_crea_admin`, `fn_crea_operatore`,
  `fn_crea_risorsa_umana`, `risorse_umane_auth_user`) stanno nelle Note di migrazione. I due blocchi non hanno `##`.
* Le due guide: link vivi, nessun link a brief; i blocchi `json`, `bash`, `ini` stanno nell'«Area tecnica — esempi».
  Non snellite le sezioni di sistema (GUC, pgbouncer, secondo fattore), che sono del backend.
* **La doc auto-generata è rigenerata** (Tid, 2026-11-22): le schede prendono le pagine nuove, l'indice le descrizioni.
  La build della doc non è lanciata.

## 17. Il vaglio per temi — proposta del 2026-11-23

Le 68 segnalazioni stanno in sei tabelle (§7, 12.3, 13.3, 14.3, 15.3, 16.3). Quasi tutte sono lette sui corpi e non
provate, e mescolano difetti, scelte da dichiarare, forma e permessi. Vagliarle una per una sono 68 decisioni. Per
**tema** sono una decina, e ogni tema è già un giro di codice. Per ogni tema Tid decide **dove va** (qui, nel brief
vicino, in un brief nuovo) e l'**ordine**. Dentro un tema, il giro distingue ancora difetto da scelta voluta, riga per
riga, e scrive la scelta nella pagina.

Due regole valgono per tutti i giri:

* **Ogni segnalazione non ✔︎ entra nel suo giro con un pgTAP che costruisce il caso e lo vede rosso**, prima della
  correzione (regola zero, corollario sui test). Se il caso non si costruisce, la segnalazione non era un difetto, e
  lo si scrive.
* **I pgTAP vanno col loro tema**: i test mancanti elencati in coda a §12.3-16.3, e i rossi in baseline della
  famiglia (`create-soggetto-gestori.sql` con T7; i quattro della sync, `test-sync-auth-user-is-active-multi-role`,
  `test-fn-sync-auth-user-is-active-or`, `test-identita-digitali-unique-multi-veste`,
  `test-identita-digitali-guard-coerenza`, con T8). Non c'è un giro solo per i pgTAP.

| Tema | Segnalazioni | La più grave, sul modello | Proposta: dove va |
| --- | --- | --- | --- |
| **T1** Lo storico degli indirizzi | S9 | Nessuna modifica fatta dall'app lascia traccia | Qui. **Deciso** (Q7), è il giro 1 (§18) |
| **T2** I permessi delle viste e delle funzioni | S21 (il DML), S37 (`security_invoker`), S40, S51, S58, S68 | `fn_soggetto_primo_documento` e `fn_titoli_iva_non_ammessi_conta` sono `SECURITY DEFINER` con EXECUTE a `PUBLIC` | Qui, giro 2. Il `REVOKE` del DML sulle viste va nel loop dei grant, non in un changeSet a parte (`linee-guida-sql.md` §11.8) |
| **T3** Il cliente e il PDP | S1, S14, S16 (prima metà), S17, S34, S35, S36, S37 (`vw_pdp`); il ritiro di `vw_pdp` (R-BE1) | S1: il subentro lascia un giorno senza cliente sul PDP | **S1 in [sviluppo-gestione-clienti-v2](sviluppo-gestione-clienti-v2.md)** (Q1). Il resto qui. La catena delle istanze resta in [brief-db-catena-istanze-pdp](brief-db-catena-istanze-pdp.md) |
| **T4** L'azienda del billing account | S2 ✔︎, S24, S25, S26, S27, S28, S29, S31 ✔︎, S32, S33 | S2: due definizioni di «storia» fanno scegliere i BA sbagliati da controllare | Qui. S27 monta su `vendite.fatture` il guard che ordini, DDT, commesse e resi hanno già: poggia su un pezzo comune già fatto, quindi il fermo allentato del 2026-10-25 lo ammette |
| **T5** Il soggetto: natura, identificativo, ruoli | S4, S20, S30, S38 ✔︎, S41, S42, S43, S52 | S38: passando dalla natura vuota si aggirano i due divieti definitivi del cambio di natura | Qui. Bloccare `soggetti_ruoli.tipo_ruolo_id` (S30) chiude anche S52 e metà di S49 |
| **T6** Lo spegnimento del soggetto e il contatto obbligatorio | S39, S45 | Un soggetto non si spegne: delle nove figlie che bloccano, sette non hanno `attivo` | **Brief nuovo**: è una decisione di modello («che cosa vuol dire spegnere un soggetto»), non una correzione |
| **T7** Indirizzi e contatti | S3 ✔︎, S8, S10, S11, S16 (seconda metà), S19, S46, S47, S48, S49, S50 | S3: un indirizzo libero esce una volta per ogni via del comune. S48: un requisito nuovo blocca la prossima scrittura di chi esiste già | Qui. ⚠️ 2026-11-23: la porta di S50 (`zeroerp.maintenance_indirizzi_dettaglio`) è la **porta 14** di `brief-db-porte-aperte-dalla-sola-guc`: ~~la regola si decide lì (D-C), e D-D propone di applicarla qui, in T7~~ ⚠️ decise da Tid il 2026-11-23: D-C **b**, D-D **a**, la porta la chiude il giro 1 di quel brief, non T7. T7 non tocca `trgfn_indirizzi_dettaglio_protect_update` |
| **T8** Ruoli d'impresa, conti, emittente | S12 ✔︎, S13, S15 (parte), S18, S53, S54, S55, S56, S57; il ritiro di `fn_check_fornitore_attivo` e `fn_guard_fornitore_attivo` (R-BE3); «un predefinito non si blocca» al DB (R-BE4) | S12: `resellers.codice` è NOT NULL e nessuno lo genera. S53: un emittente con fatture si spegne | Qui, salvo S53, che tocca tutte le tabelle di documento che puntano a `soggetti_ruoli`: ~~da decidere se è un tema proprio~~ → lo è, T12 (§17.1) |
| **T9** Gli accessi | S5, S6, S22 (⚠️ tutta, §17.1), S59-S67, R-BE6 | S59: una credenziale rimasta senza vesti resta accesa per sempre. S61: l'ultimo SUPER_ADMIN si sposta senza passare da un guard | **Brief DB nuovo sugli accessi**, che porti anche **R-4** di [piano-be-fe-accessi-credenziale-e-vesti](../work-done/2026/piano-be-fe-accessi-credenziale-e-vesti.md) (la veste revocata), che aspetta un brief DB mai scritto. S67 (lo shop nasce acceso o spento) è la stessa materia di R-4 |
| **T10** I titoli IVA | S44 | Nessuna funzione scrive i movimenti `NOTA_CREDITO`, e niente impedisce di restituire più di quanto la fattura aveva consumato | Qui, oppure col cantiere che porterà le note di credito: ~~da decidere~~ → qui (§17.1) |
| **T11** La forma | S15 (i quattro `*_normalize` vuoti), S21 (fasce, `%TYPE`, `CODICE_NON_MODIFICABILE`), ~~S22 (i nomi `_v2`)~~ → in T9 (§17.1) | — | Qui, per ultimo |
| fuori DB | S23 (`scripts/gen_db_docs.py` non mostra i vincoli `EXCLUDE` fra i vincoli) | — | Una correzione dello strumento della doc, quando Tid lo dice |

Già chiuse: **S7** (voluto, la doc è corretta nel giro 0e).

**L'ordine proposto** dei giri che restano qui, per gravità sul modello: T1 (giro 1), T2 (giro 2), T5, T7, T4, T8,
T3, T10, T11. ⚠️ Deciso con T12 dopo T8: §17.1.

**Le tre decisioni aperte**, con la proposta (⚠️ decise il 2026-11-23: §17.1):

| # | Domanda | Proposta |
| --- | --- | --- |
| S4 | Lo stesso codice fiscale su due soggetti con partite IVA diverse è ammesso? | Il difetto c'è comunque: il pre-controllo dei due verbi e l'indice unico dicono due regole diverse. Tid sceglie la regola; il giro T5 porta la seconda sede sulla prima |
| S64 | `ATTIVO` in `script.fn_stato_veste` vuol dire «accesa» o «utilizzabile»? | Resta «accesa», come dice il suo COMMENT, e la lista degli accessi mostra l'utilizzabilità a parte. Si decide nel brief degli accessi (T9) |
| S67 | La veste dello shop nasce accesa (COMMENT di `fn_crea_veste_portale`) o spenta, accesa dalla verifica dell'email (`architettura-multi-face-auth` §8.2)? | Nel brief degli accessi (T9), insieme a R-4: lo shop self-service non c'è ancora |

### 17.1 Decise da Tid — 2026-11-23

* **Le proposte della tabella, tutte accettate**: T2, T4, T5, T7, T8, T11 qui; T3 qui, con S1 in
  [sviluppo-gestione-clienti-v2](sviluppo-gestione-clienti-v2.md); T6 in un brief nuovo; T9 in un brief DB nuovo sugli
  accessi, con R-4 del piano accessi (la veste **non** si tratta qui); S23 fuori DB, quando lo dice Tid. L'ordine è quello
  proposto, con T12 dopo T8: T2 (giro 2), T5, T7, T4, T8, T12, T3, T10, T11.
* **T10, i titoli IVA: qui**, come giro di questa revisione e non col cantiere delle note di credito.
* **S4: la chiave è la coppia** CF e P.IVA, come l'indice unico `uq_soggetto_idstato_id_fiscale_univoco`. Il giro T5
  allinea il pre-controllo «già presente» di `fn_crea_soggetto_pf` e `fn_crea_soggetto_pg` all'indice. Argomento sul
  modello: i membri di un gruppo IVA hanno la stessa P.IVA e CF diversi.
* **S64, S67**: nel brief degli accessi (T9).
* **S22, i nomi `_v2`: tutta in T9**, non in T11 (Tid, 2026-11-23): sono verbi degli accessi che quel brief riscrive
  per S6 e S65, e due brief sulle stesse funzioni si pestano i piedi. Il rinomino e la sua richiesta al BE le scrive lì.
* **S53 è un tema proprio: T12, lo spegnimento dell'emittente.** La regola di Tid: **un emittente definito non si
  spegne se ha qualunque cosa associata** (un'anagrafica, un documento, un registro, una riga di qualunque tabella che
  lo nomini), non solo le figlie che oggi fermano lo spegnimento. Il giro, prima di costruire, cerca la decisione
  esistente sullo spegnimento dei ruoli (l'automazione ATTIVO, `E_ATTIVO_*`) e dice se la completa o la revoca; censisce
  le tabelle che puntano all'emittente (direttamente o attraverso `soggetti_ruoli`). Viene dopo T8 (Tid, 2026-11-23),
  che tocca gli stessi ruoli d'impresa. Il resto di S53 si divide così: il primo emittente nato spento va con T12; la
  FK mancante di `emittenti_fiscali.valuta_id` va con S29, in T4.

## 18. Giro 1 — Q7, lo storico continuo di indirizzi, civici e vie (2026-11-23, applicato, pgTAP verdi, committato)

Decisione: Q7 riaperta, strada (b), estesa a `config.stradario` (Tid, 2026-11-22, §10). Via allo sviluppo: Tid,
2026-11-23. **Guide verificate** (`scripts/guide_coinvolte.py --oggetti anagrafiche.indirizzi
anagrafiche.indirizzi_dettaglio config.stradario config.storico_set_storicizza script.trgfn_storico_generic`):

| Guida o nota | Esito |
| --- | --- |
| `gestione-degli-indirizzi` | Guida indietro dopo il giro: riscritta §Storicizzazione (una regola sola per le quattro tabelle) e il passo 3 dell'import massivo |
| `riclassificazione-vie` | Prima del giro il codice la smentiva («Storico garantito», punto 4): ora è vera, ed è precisata insieme al punto della rinormalizzazione |
| `storicizzazione-tabelle` | Coerente: consigliava già di registrare le tabelle anagrafiche |
| `catasto-delle-istanze`, `generazione-cliente`, `gestione-delle-istanze-utility`, `audit-e-tracciabilita`, `automazione-db` | Coerenti: non dicono niente dello storico di queste tre tabelle, o lo dicono del trigger in generale |
| `storico/_tabelle-storico`, `anagrafiche/_indirizzo-libero-o-dettaglio`, `_indirizzi-obbligatori`, `_tipo-indirizzo-ammesso` | Coerenti |

### 18.1 Che cosa è scritto

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/anagrafiche/20261123-38` | `indirizzi` e `indirizzi_dettaglio`: `storicizza` DEFAULT `true`, righe esistenti accese con i trigger della tabella sospesi (tranne audit e `tx_id`, cercati per funzione), COMMENT della colonna (chiude M23) |
| `00_schema/config/20261123-39` | `config.stradario`: DEFAULT `true` e COMMENT. Le righe no: vedi -40 |
| `00_schema/storico/20261123-42` | `storico.indirizzi`: `change_type` DEFAULT `'A'` e `indirizzi_id` `bigint`, come le altre ombre (18.2) |
| `80_data/changelog/20261123-40` | Le vie che esistono si accendono, con lo storico sospeso, **dopo** il mirror dello stradario |
| `80_data/changelog/20261123-41` | Le tre tabelle in `config.storico_set_storicizza`, con `insert_manuale = true` (una decisione, che la sync settimanale non pota) |
| `80_data/changelog/20250814-03` e `80_data/sql/config/stradario.csv` | La colonna `storicizza` esce dal CSV e dal mirror: il valore giusto è il default della tabella (`linee-guida-sql.md` §11.2). Le 4.278 righe hanno ora 11 campi |

**Perché le vie si accendono in `80_data` e non in `00_schema`.** Il mirror `20250814-03` è `runOnChange`, e
toglierne una colonna lo fa ripassare al migrate successivo su dbdev, al suo numero, cioè prima di ogni file di
`80_data` datato oggi. Il ripasso è un `UPDATE` su ogni via, e `script.trgfn_storico_generic` non salta le modifiche
a vuoto: con le righe già accese avrebbe scritto due versioni per ogni via. Così il mirror ripassa su righe ancora
spente, e -40 le accende dopo, con lo storico sospeso. Da zero il mirror inserisce le vie col default, e -40 non
trova niente.

**pgTAP nuovo:** `db/pgtap/anagrafiche/test-storico-indirizzi-continuo-v1.sql`, 16 asserzioni: il default sulle tre
tabelle, il registro, e per via, civico e indirizzo di ruolo fabbricati dal test la riga che nasce accesa, due
modifiche che lasciano partenza e due versioni, il flag che resta acceso, la cancellazione che lascia la sua (via e
civico), una scrittura che spegne il flag e non lascia traccia. La cancellazione dell'indirizzo di ruolo non si prova:
se il tipo è obbligatorio per il ruolo il guard la rifiuta, e la fixture non sceglie il tipo.

**pgTAP corretto:** `db/pgtap/config/test-stradario-riclassificazione-unico.sql`, test 13. Chiedeva lo snapshot «a
`now()`» dentro la transazione: tutte le versioni nascono a quell'istante, e la via vecchia tornava solo perché il
cambio di nome, sotto lo storico a richiesta, non lasciava traccia. Ora chiede l'istante prima della transazione.

**Pagine e guide:** `manual/indirizzi.md`, `manual/indirizzi_dettaglio.md` (la sezione «Lo storico è continuo» al
posto di «a richiesta», tolti i punti di «Che cosa oggi non copre», il test nuovo), `config/manual/stradario.md`
(solo il punto dello storico: la pagina è fuori da questa revisione e resta nel formato vecchio), le due guide sopra.

### 18.2 Che cosa ha trovato la prova

* ⭐ **`storico.indirizzi` non accettava nessuna versione.** È un'ombra della prima generazione: `change_type` è
  `NOT NULL` senza default, e il trigger generico non lo scrive. Ogni modifica o cancellazione di un indirizzo di
  ruolo col flag acceso falliva con `E_SNAPSHOT_INIT_INSERT_ERROR` (23502), e con lei la scrittura. Nessuno lo vedeva
  perché nessuna scrittura accendeva il flag: l'ombra è vuota su dbdev e sullo scratch. Con lo storico continuo
  **ogni** modifica di un indirizzo di ruolo dall'app si sarebbe fermata lì. L'ha trovato il pgTAP del giro prima
  dell'apply; il censimento sul catalogo dice che è l'unica ombra con una colonna obbligatoria che il trigger non
  scrive. Corretto da -42, che quindi va applicato **insieme** a -38.
* `storico.indirizzi_dettaglio` è vuota e `storico.stradario` ha poche righe (dbdev, 2026-11-23): fatto datato, che
  conferma S9 e R-BE5.
* **Conseguenza dichiarata, voluta dalla guida delle vie:** `maintenance.proc_bump_indirizzi_dettaglio` riscrive ogni
  civico di una via con un aggiornamento neutro, e ora ognuno lascia una versione anche quando il testo non cambia.
  Gira a mano, su una via sola; nessun job la chiama.
* **Fatto per il team BE/FE, non una richiesta:** la PUT dell'indirizzo del ruolo (`soggetti_service.replace_indirizzo_ruolo`,
  R-BE5 riga 3) è una DELETE più una INSERT. Ora la DELETE lascia la sua versione, ma la riga nuova ha un altro id:
  la storia di «quell'indirizzo» si spezza su due id. Se si vuole una storia sola, la PUT diventa un UPDATE: lo decide
  il team BE/FE.

### 18.3 La prova

`scripts/prova_changeset.py` sui cinque changeSet, sullo scratch, in `ROLLBACK`, con 30 pgTAP che scrivono le tre
tabelle (censiti per `UPDATE`/`DELETE` diretti, madri, verbi di copia, «trova o crea», bump e fusione):

* il test nuovo: senza i changeSet 1 ok e 15 rossi (la regola che manca), con i changeSet 16 ok;
* 28 test invariati, verdi nelle due corse;
* `test-stradario-riclassificazione-unico`: 13 ok senza, 12 ok e 1 rosso con i changeSet prima della correzione del
  test 13, 13 ok dopo;
* `config/test-toponomastica-stradario-generale.sql` **non provato**: comincia con una pulizia fuori transazione
  (voluta, spiegata in testa al file), e lo script non lancia un file che non comincia con `BEGIN;`. Non scrive
  `config.stradario`.

I presidi statici (`guardrail_comment_al_presente`, `_ddl_su_trigger_automazione`, `_forme_changeset`,
`_grant_ruolo_batch`, `_pgtap_preambolo`, `_precondition_seed`, `_run_on_change`, `_sql_letterali`,
`_timestamp_senza_fuso`) sono verdi.

### 18.4 Che cosa resta

* ✅ **Apply e pgTAP: Tid, 2026-11-23**, applicato con i test verdi. Prima dell'apply i due blocchi `DO` di -38 e
  -40 sono stati portati a `%TYPE` (gli array dei trigger sospesi ancorati a `pg_catalog.pg_trigger.tgname` e
  `tgenabled`, `linee-guida-sql.md` §5g; `regclass` resta esplicito col motivo) e riprovati sullo scratch.
* ✅ Doc auto-generata rigenerata da Tid e **commit** `a35a6636dc` (2026-11-23), insieme al passo A. Il giro 1 è
  chiuso.
* Le pagine delle tre ombre (`storico/manual/indirizzi.md`, `indirizzi_dettaglio.md`, `stradario.md`) sono nel
  formato vecchio e dicono cose non vere sullo storico (per esempio «il trigger logga l'eccezione senza bloccare»: la
  solleva). Sono dello schema `storico`, fuori da questa revisione: debito per la revisione di quello schema.
* M23 si chiude con -38 (§8.1).

## 19. Giro 2 — T2, i permessi delle viste e delle funzioni (2026-11-23, analisi letta sul catalogo)

Via: Tid, 2026-11-23. Il giro parte dalle segnalazioni S21 (il DML), S37, S40, S51, S58, S68. Le letture sono sul
catalogo di dbdev il 2026-11-23, e sono letture di **struttura** (ACL, `reloptions`, `prosecdef`, aggiornabilità):
nessun conteggio di righe decide qualcosa. **Guide verificate** (`scripts/guide_coinvolte.py --oggetti` sulle due
funzioni e sulle otto viste del giro):

| Guida o nota | Esito |
| --- | --- |
| `anagrafiche/_titolo-iva-per-natura` §«Perché due lettori girano sopra la RLS», `anagrafiche/_cambio-di-natura` §«Chi vede che cosa» | Coerenti: descrivono già le due DEFINER di S40 come scelta, con ciò che possono rispondere |
| `risorse-umane-e-accessi`, `gestione-commesse`, `gestione-conti-bancari`, `gestione-degli-indirizzi` | Coerenti: nominano le viste per ciò che espongono, non per i privilegi |

Orfani: `vw_fornitori_dettaglio`, `vw_istanze_utilities_dettaglio`, `vw_soggetti_ruoli_dettaglio`. Sono proiezioni per
le liste, non concetti del dominio: nessuna guida da scrivere.

### 19.1 Che cosa dice il catalogo

* **Le DEFINER di S40 sono il pattern del progetto, non un difetto.** `fn_soggetto_primo_documento` e
  `fn_titoli_iva_non_ammessi_conta` leggono sopra la RLS perché il cambio di natura deve vedere i documenti e i titoli
  di tutte le aziende. È l'invariante di `linee-guida-sql.md` §10.5 («un guard che legge tabelle sotto policy non può
  essere INVOKER»), e le due funzioni rispettano la sua condizione: rispondono solo un codice di tipo o un numero, mai
  una riga. L'`EXECUTE` all'app serve, perché le chiama `fn_check_cambio_natura_soggetto`, che è INVOKER. L'`EXECUTE`
  a `PUBLIC` non allarga niente: sullo schema `anagrafiche` hanno `USAGE` solo `zeroerp_owner` e `zeroerp_app`
  (`nspacl`). Lo stesso vale per le altre 17 DEFINER dello schema con `=X`.
* **`security_invoker` assente non è un difetto.** La regola vuole il flag sulle viste che arrivano a dati sotto RLS, e
  la presidia **a criterio** `rls/test-rls-viste-security-invoker`, transitivo e attraverso le funzioni: una vista
  senza flag oggi lecita diventa rossa lì il giorno in cui una sua tabella va sotto policy. Le viste di S37, S40, S51,
  S58 e S68 senza flag non arrivano a tabelle con RLS.
* **Il DML dell'app sulle viste non è di `anagrafiche`: è di tutto il database.** Il loop dei grant
  (`90_end/ci_apply/20260205-41`) e la fase `post` del provisioning danno `SELECT, INSERT, UPDATE, DELETE` «on all
  tables», e le viste ci rientrano: l'app ha il DML su ogni vista di ogni schema, tranne `maintenance`. Nelle 19 viste
  di `anagrafiche` è inerte: nessuna è aggiornabile (`pg_relation_is_updatable` = 0), e non ci sono trigger
  `INSTEAD OF` né regole.
* ⚠️ **Il buco che il DML lascia aperto è un altro, e non è di questo schema.** Una vista **aggiornabile** e **senza**
  `security_invoker` controlla i permessi sulla tabella sotto come il suo proprietario. Con il DML sulla vista, l'app
  scrive la tabella sotto anche quando la tabella è in sola lettura per lei: la vista aggira la postura «una scrittura =
  un verbo». Oggi le viste così sono sei, su otto tabelle, in `catalogo`, `dbops` e `script` (fra cui
  `dbops.vw_emittenti_regime_non_confermato` su `anagrafiche.emittenti_fiscali`), e su tutte le tabelle sotto l'app ha
  già il DML: oggi non c'è niente che si apre in più. Il modello però lo ammette, e nessun presidio lo guarda:
  basta una vista semplice su una tabella di `magazzino`, che dal 2026-11-23 è tutta in sola lettura per l'app.

### 19.2 L'esito delle segnalazioni

| # | Esito |
| --- | --- |
| S40 (le due DEFINER) | Voluta, scritta nelle due note di dominio. Le pagine `manual/` delle due funzioni la dicono già (COMMENT e Scopo) |
| S37, S40, S51, S58, S68 (`security_invoker`) | Voluta e presidiata a criterio. Le pagine delle viste lo dicono nel giro dei metadati, una riga |
| S21, S51, S58, S68 (il DML sulle viste) | Inerte in questo schema. È una postura di tutto il database: ✅ decisa da Tid il 2026-11-23 (sotto), il lavoro è di `brief-db-porte-aperte-dalla-sola-guc` §5. Chiuse qui |

### 19.3 La decisione per Tid

> ✅ **Decisa da Tid il 2026-11-23: la proposta.** L'app riceve solo `SELECT` sulle viste, in tutto il database. La
> richiesta al BE e il lavoro DB (le tre sedi di §11.8, il pgTAP di postura, e prima il verbo di ogni scrittura che il
> censimento trova) stanno in [brief-db-porte-aperte-dalla-sola-guc](brief-db-porte-aperte-dalla-sola-guc.md): §5 la
> famiglia delle viste, §4.1 la richiesta unica al BE, unita a quella delle porte. Lì, non qui. L'alternativa più
> stretta è scartata.
>
> **Esito, 2026-11-23.** Il BE ha risposto «nessuno»: in `backend/` e `frontend/` nessun punto scrive su una vista, e
> non serve nessun verbo nuovo; il DB ha verificato i due limiti della ricerca sul catalogo (dettaglio in
> `brief-db-porte-aperte-dalla-sola-guc` §5.1). La revoca la fa quel brief, nel suo giro 3, senza aspettare il BE.
> Per `anagrafiche` non cambia niente: le sue 19 viste non sono aggiornabili. S21, S51, S58 e S68 sono chiuse qui.

Il giro 2 non ha niente da cambiare dentro `anagrafiche`. Resta la postura delle viste, che è un tema di **tutti gli
schemi**, e per questo vuole l'ok esplicito di Tid (regola «un tema, un brief»). La proposta:

* **l'app riceve solo `SELECT` sulle viste**, dichiarato nel loop dei grant come eccezione per `relkind = 'v'`, nelle
  tre sedi di §11.8 (il changeSet `90_end` che revoca subito, il loop, la fase `post` del provisioning);
* un **pgTAP di postura a criterio**: nessuna vista dà all'app più di `SELECT`, e i casi costruiti (una vista
  aggiornabile senza flag su una tabella in sola lettura) rispondono `42501`;
* **prima**, una richiesta al team BE/FE: **censire ogni scrittura dell'app che passa da una vista** (`INSERT`,
  `UPDATE`, `DELETE` il cui bersaglio è un `vw_*`, anche costruito per nome, e il pannello generico). Il DB cambia dopo
  la risposta: una scrittura trovata vuole prima il suo verbo.

L'alternativa più stretta: lasciare il DML e togliere solo il buco, con un presidio che rifiuta una vista aggiornabile
senza `security_invoker`. Costa meno, ma lascia all'app un privilegio che nessun oggetto del DB usa. Se lo usa il BE, lo dice il censimento.

#### ~~R-BE7 — Il testo per il team BE/FE (2026-11-23)~~

> ⚠️ **Superata il 2026-11-23, prima di partire**: unita alla richiesta delle porte, in
> `brief-db-porte-aperte-dalla-sola-guc` §4.1 (Parte B). Il testo sotto resta come storia.

**Le scritture dell'app che passano da una vista.** Oggi `zeroerp_app` ha `INSERT`, `UPDATE` e `DELETE` su tutte le
viste di ogni schema (tranne `maintenance`), perché il loop dei grant le conta fra le tabelle. Il DB toglierà quel
permesso: sulle viste l'app avrà solo `SELECT`. Il motivo: una vista aggiornabile senza `security_invoker` scrive la
tabella sotto coi permessi del suo proprietario, e aggira la sola lettura dell'app («una scrittura = un verbo»).

Una scrittura su una vista non aggiornabile fallisce già oggi. Quelle che riescono possono passare solo da queste
quindici viste, le uniche aggiornabili (catalogo di dbdev, 2026-11-23):

| Schema | Viste |
| --- | --- |
| `catalogo` | `vw_causali_onere_assegnabili` |
| `config` | `vw_codici_errore_identita`, `vw_email_in_coda` |
| `dbops` | `vw_af_senza_giro`, `vw_coda_lavori_da_guardare`, `vw_email_da_guardare`, `vw_emittenti_regime_non_confermato`, `vw_fatture_stampa_coda_da_guardare`, `vw_liste_multi_emittente_non_certificate`, `vw_magazzino_movimenti_senza_costo`, `vw_processi_dominio_su_pgagent` |
| `documenti` | `vw_template_asset_utilizzabili` |
| `script` | `vw_audit_sources`, `vw_stati_estesi` |
| `vendite` | `vw_preventivi_righe_smistabili_ordine` |

Chiediamo un **elenco chiuso** di ogni punto di `backend/` e `frontend/` dove l'app scrive (`INSERT`, `UPDATE`,
`DELETE`, `MERGE`, `COPY … FROM`) su una vista. I punti da guardare:

1. l'SQL scritto a mano (`cursor.execute`, `raw`), anche col nome della vista costruito a runtime;
2. i modelli Django `managed = False` con `db_table` su una vista, e le loro `save`, `create`, `update`, `delete`,
   `bulk_*`, anche dall'admin;
3. il pannello generico e le liste in modifica, quando la sorgente o la destinazione è una vista;
4. i test e le fixture del BE che scrivono su una vista con la connessione dell'app.

Per ogni punto: `file:riga`, la vista, l'operazione, il dato di dominio che vuole cambiare. Se il punto ha già un
verbo DB che fa la stessa cosa, il nome del verbo. «Nessuno» è una risposta valida, se dice come si è cercato.

**Chi cambia per primo.** Nessuna urgenza: il DB non cambia finché non arriva la risposta. Se l'elenco è vuoto, il DB
revoca. Se ci sono scritture, il DB scrive prima i verbi che mancano, poi il BE passa ai verbi, e solo dopo il DB
revoca. Il BE non deve cambiare niente finché non riceve i verbi.

## 20. Giro 3 — T5, il soggetto: natura, identificativo, ruoli (2026-11-23, decise da Tid; applicato, pgTAP verdi, committato il 2026-11-24)

Via di Tid il 2026-11-23. Segnalazioni: S4, S20, S30, S38 ✔︎, S41, S42, S43, S52 (e metà di S49, che si chiude con
S30). Letti sul catalogo di dbdev i corpi di `fn_crea_soggetto_pf`/`_pg`, dei guard di `soggetti`, `soggetti_ruoli` e
`dati_societari`, di `fn_check_cambio_natura_soggetto`, `script.fn_validate_cf_piva_it`, `fn_scrivi_dati_societari`;
i trigger delle tre tabelle; il registro `dbops.automation_lock_columns`. Letto il ramo `origin/dev/backend-tid`
(`f1b8f9df7a`, sola lettura) per gli scrittori delle colonne toccate. Nessun changeSet scritto.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti` sugli oggetti del tema):

| Guida o nota | Esito |
| --- | --- |
| [_identificativo-fiscale](../../dbzero/anagrafiche/_identificativo-fiscale.md) | **coerente** con S4 deciso (la coppia). La sezione «⚠️ Che cosa la regola oggi non copre» (normalizzazione, stato non bloccato, stringa vuota) è la lista di D-T5-2 e D-T5-3: si riscrive col giro |
| [_cambio-di-natura](../../dbzero/anagrafiche/_cambio-di-natura.md) | **contraddetta** da D-T5-1: «Da una natura a nessuna natura: ammesso solo se il soggetto non ha titoli IVA vigenti» è il varco di S38. Cambio di modello: decide Tid |
| [_guard-di-ruolo](../../dbzero/anagrafiche/_guard-di-ruolo.md) | **coerente**: «⚠️ Il ruolo che cambia tipo» descrive il buco di S30/S52 come buco, non come scelta; con D-T5-4 la sezione si toglie |
| [_dati-societari](../../dbzero/anagrafiche/_dati-societari.md) | **coerente**: l'app ha solo `SELECT` sulla tabella (verificato), quindi «la DELETE diretta non guarda la natura» (S41) è solo del proprietario |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | **coerente** oggi; **indietro** su ciò che il giro cambia: «La natura sul soggetto può mancare» (D-T5-1), «Il soggetto di un ruolo non si cambia» (si aggiunge il tipo, D-T5-4), lo stato (D-T5-3) |
| [linee-guida-trigger](../../linee-guida-trigger.md) §«La fase» | **contraddetta** da D-T5-2 a: non c'è una zona per una normalizzazione che i guard leggono. Decide Tid |
| `gestione-dei-contatti`, `risorse-umane-e-accessi`, `generazione-cliente`, `gestione-pratiche`, `gestione-delle-istanze-utility`, `messaggi-audit`, `Messaggi-di-Errore-e-Generazione-Log`, note `_contatto-predefinito`, `_sincronizzazione-accesso`, `_indirizzi-obbligatori`, `_tipo-indirizzo-ammesso`, `_titolo-iva-per-natura` | nominano `soggetti`/`soggetti_ruoli` per altro: **coerenti**, il giro non tocca ciò che descrivono |

Orfani: `trgfn_soggetti_normalize`, `trgfn_soggetti_valida_cf_piva_dispatch` (dettagli interni dei guard; la nota
dell'identificativo li nominerà col giro).

### 20.1 Che cosa dice il catalogo, segnalazione per segnalazione

**Il fatto che regge tutto il tema: l'app ha `INSERT`, `UPDATE` e `DELETE` su `soggetti` e `soggetti_ruoli`**, non
su `dati_societari`. Una regola che sta solo in `fn_crea_soggetto_*` è muta sull'`UPDATE` diretto, che il BE fa
(`soggetti_repository.update_soggetto`, BB `execute_dynamic_update`, colonne `SOGGETTO_UPDATE_COLS`: CF, P.IVA,
natura, nomi, flag PA; **non** `stato_id`). Il BE non scrive mai `soggetti_ruoli` con un `UPDATE` (né a DB).

| # | Esito sul corpo | Che cosa si fa |
| --- | --- | --- |
| **S4** | **Difetto confermato**, con un caso in più: il pre-controllo cerca `id_fiscale_univoco_cf_piva = CF`, l'indice guarda la coppia. Una ditta individuale (CF + P.IVA) di una persona che è già un privato (stesso CF, niente P.IVA) è **rifiutata** dal pre-controllo, mentre il modello (la nota, e la decisione di Tid) la ammette. Il doppione vero (stessa coppia) sfugge al pre-controllo e arriva all'indice come `23505` senza codice. In `fn_crea_soggetto_pg` lo stesso, sui due campi separati | Il pre-controllo si ritira: la regola è l'indice, una sede sola. Il verbo traduce la violazione **di quell'indice** (per nome del vincolo, `GET STACKED DIAGNOSTICS`) in `E_ADMIN_CF_DUPLICATO`, coi due valori; anche la corsa fra due creazioni ha così il suo codice. Il messaggio dice «identificativo fiscale», non «codice fiscale» |
| **S20** | **Difetto**: `'' IS NULL` è falso, la stringa vuota passa la presenza. Il BE la toglie da sé (`_NULLABLE` in `update_soggetto`), una scrittura diretta no | Con D-T5-2 |
| **S30** | **Difetto**: `tipo_ruolo_id` non è bloccato; nessuno scrittore lo cambia (né DB né BE) | D-T5-4 |
| **S38** ✔︎ | **Difetto**, riletto: con la natura nuova `NULL` la regola guarda solo i titoli IVA, e X → `NULL` → Y salta macro-tipologia e documenti. Lo stesso varco salta la matrice natura ↔ ruolo, che è per macro-tipologia | D-T5-1 |
| **S41** | Sei punti, esiti diversi: (1) la `DELETE` diretta che non guarda la natura è solo del proprietario: **scelta**, si dichiara; (2) due prime scritture concorrenti in `fn_scrivi_dati_societari` urtano `uq_ds_soggetto` grezzo: **difetto**; (3) una natura `REQUIRED` senza forma riceve `23502` senza codice: **difetto**; (4) il codice SDI di 6 o 7 caratteri vale per chiunque: **da decidere** (D-T5-5); (5) un cambio di `stato_id` non rilegge la forma dello Stato: **difetto**, si chiude con D-T5-3; il cambio delle policy della forma in `config` non rilegge le righe: **scelta** (la configurazione vale alla scrittura, come la matrice dei ruoli e i requisiti degli indirizzi di S48); (6) `trgfn_dati_societari_guard_tipo_soggetto` senza fase parla dopo forma e canale (alfabeto) e gira a ogni `UPDATE`: **difetto** di ordine | (2) il verbo prende la riga del soggetto `FOR NO KEY UPDATE` prima dell'`UPDATE`/`INSERT` (l'upsert no: linee-guida-trigger, «un `BEFORE INSERT` giudica la riga proposta»); (3) il verbo rifiuta la forma mancante con un codice e `campo`; (5) il guard differito della forma per natura scatta anche al cambio di `stato_id`; (6) il guard diventa `a05` (il «non ammessi» parla prima di forma e canale) e `BEFORE INSERT`, e `dati_societari.soggetto_id` entra nel registro dei lucchetti (FK di appartenenza: linee-guida-trigger §`UPDATE OF`) |
| **S42** | **Difetto** di forma: i messaggi di `E_RUOLO_NATURA_NON_AMMESSA` e `E_RUOLO_NATURA_TIPO_DET_NULL` mostrano id (anche lo `uuid` del soggetto), il contesto non ha `campo`. Una riga di matrice spenta non tocca i ruoli che esistono: **scelta**, come S41 (5) | I messaggi con le descrizioni (natura, ruolo), il contesto con `campo`. Lo stesso per `E_PIVA_OBBLIGATORIA` e `E_CF_OBBLIGATORIO`, stesso guard di S20 («Soggetto_id %s») |
| **S43** | Nove punti: (1) `trgfn_soggetti_normalize` in modifica rimette lo stato proposto su un `stato_id` portato a `NULL`: **difetto**, cambia in silenzio metà della chiave; (2) il dispatch del formato gira a ogni `UPDATE`: un soggetto con un CF che il validatore non accetta non si modifica più in nessun campo, e il CF lo corregge solo il SUPER_ADMIN: **difetto**; (3) con una natura inesistente `INTO STRICT` dà un errore tecnico prima della FK: **difetto**; (4) uno stato senza validatore passa: **scelta**, la guida lo dice («le regole scritte oggi sono quelle italiane»); (5) il DB non normalizza CF e P.IVA: D-T5-2; (6) `stato_id` non è bloccato: D-T5-3; (7) la stringa vuota: D-T5-2; (8) `ragione_sociale_completa` è `NULL` se manca nome o cognome: **difetto** (la scrittura diretta lo permette); (9) `codice` ammette `NULL`: il trigger lo genera sempre, la colonna non lo dice: **difetto di forma**; (10) il tipo di contatto di ripiego «il primo per id»: un ripiego silenzioso, come quello dello stato ritirato il 2026-10-18: D-T5-6 | (1) il default dello stato solo all'`INSERT`; (2) il dispatch scatta all'`UPDATE` solo `WHEN` CF, P.IVA, P.IVA di gruppo, stato o natura cambiano (non `OF`: `trgfn_soggetti_normalize` scrive `stato_id`); (3) natura inesistente → il validatore tace e parla la FK, come fa già `fn_check_cambio_natura_soggetto`; (8) la colonna generata con `concat_ws` (`ALTER COLUMN … SET EXPRESSION`); (9) `NOT NULL` su `codice` |
| **S52** | **Difetto**, stessa radice di S30; e nessun pgTAP prova il rifiuto `E_SOGGETTI_RUOLI` | Si chiude con D-T5-4; il pgTAP del rifiuto entra col giro |
| S49 (metà) | Il cambio del tipo di ruolo non rigiudica gli indirizzi del ruolo | Si chiude con D-T5-4; l'altra metà (il tipo per id in `fn_indirizzo_elemento`, i tipi `bigint`/`integer`) resta in T7 |

### 20.2 Le decisioni per Tid

> ✅ **Decise da Tid il 2026-11-23: tutte le proposte** (D-T5-1 a, D-T5-2 a, D-T5-3 a, D-T5-4 a, D-T5-5 b, D-T5-6 a se
> il BE passa sempre il tipo di contatto, altrimenti b). La nota `_cambio-di-natura` e le linee guida dei trigger
> cambiano nello stesso giro.

| # | Domanda | Strade | Proposta |
| --- | --- | --- | --- |
| **D-T5-1** (S38) | Una natura scritta si può svuotare? | **a** no: «una natura scritta non si svuota», per tutti (il SUPER_ADMIN non ha eccezioni sul cambio di natura); un soggetto senza natura la riceve una volta, come oggi · **b** sì, ma il passaggio successivo da `NULL` si giudica sull'ultima natura avuta (serve una memoria della natura) | ⭐ **a**: è la regola dell'identificativo applicata alla natura, sta nella stessa `fn_check_cambio_natura_soggetto` (un motivo nuovo, che legge anche il picker), e chiude S38 senza memoria. **Cambia il modello** della nota `_cambio-di-natura` |
| **D-T5-2** (S20, S43) | CF e P.IVA: il DB li normalizza o rifiuta ciò che non è normalizzato? | **a** normalizza (maiuscole, spazi tolti, vuoto → `NULL`) in un trigger che gira **prima** dei guard, con una zona nuova nelle linee guida dei trigger («la normalizzazione che i guard leggono») · **b** rifiuta, con un guard `a10` della forma (vuoto, spazi, minuscole): normalizzano i verbi, come oggi, e il BE per il suo `UPDATE` | ⭐ **a**: una regola sola per ogni strada, il BE può ritirare la sua copia (`_NULLABLE` per CF e P.IVA); il prezzo è la zona nuova, che è una regola delle linee guida, e la si scrive lì. Con **a** un valore digitato in minuscolo urta l'indice come quello in maiuscolo |
| **D-T5-3** (S43, S41) | `stato_id` è metà dell'identificativo: si blocca? | **a** sì, con la regola dell'identificativo (lo cambia solo il SUPER_ADMIN), nella stessa `fn_id_fiscale_bloccato` e nel form · **b** sì, per tutti · **c** no, resta libero e si dichiara | ⭐ **a**: il BE non lo scrive mai (non è in `SOGGETTO_UPDATE_COLS`); lo stato è parte della chiave, e la correzione dell'errore resta a chi corregge CF e P.IVA. Col blocco, il guard differito della forma giuridica rilegge la forma quando il SUPER_ADMIN cambia lo stato (S41-5) |
| **D-T5-4** (S30, S52, S49) | `soggetti_ruoli.tipo_ruolo_id` si blocca? | **a** sì: lucchetto generato (`dbops.automation_lock_columns`), codice suo · **b** no, e i guard di ruolo e degli indirizzi si rigiudicano al cambio | ⭐ **a**: un ruolo è «questo soggetto, questo tipo», come il soggetto che già non si cambia; nessuno scrittore lo cambia oggi. Un tipo sbagliato si corregge togliendo il ruolo e mettendo quello giusto |
| **D-T5-5** (S41-4) | Il codice SDI di 6 caratteri (ufficio della PA) e di 7 (privati) si lega al flag `cliente_pa`? | **a** sì: 6 solo con `cliente_pa = 'S'`, 7 solo con `'N'`, giudicato anche al cambio del flag · **b** no, si dichiara: il codice dell'ufficio PA è per ufficio, e la sua sede vera è il destinatario della fattura, non il soggetto | ⭐ **b**: la PA ha più uffici, e un codice per soggetto è già una semplificazione; il legame col flag si giudica dove si sceglie l'ufficio, nella fatturazione |
| **D-T5-6** (S43-10) | Il tipo di contatto «il primo per id» quando il chiamante non lo passa | **a** si ritira: il tipo è obbligatorio (`E_ADMIN_VALIDAZIONE`, come gli altri parametri) · **b** un tipo proposto dichiarato in `config` (come lo stato proposto) | ⭐ **a**, se il BE lo passa sempre (lo dice il percorso BE, da leggere prima di scrivere); altrimenti **b** |

### 20.3 Il piano del giro, dopo le decisioni

1. I **pgTAP rossi prima** (§17, «ogni segnalazione non ✔︎ entra col suo caso»): S4 (la ditta del privato rifiutata;
   il doppione come `23505`), S20, S30/S52, S41 (2, 3, 6), S42, S43 (1, 2, 3, 8), costruiti come **app**.
2. I changeSet di `20_code` (verbi e guard), il CSV dei messaggi e dei codici nuovi, le righe del registro dei
   lucchetti, `ALTER COLUMN` per `codice` e `ragione_sociale_completa`. Prova con `scripts/prova_changeset.py`.
3. Le note `_identificativo-fiscale`, `_cambio-di-natura`, `_guard-di-ruolo`, `_dati-societari`, la guida
   `soggetti-e-ruoli-anagrafici` e, con D-T5-2 a, `linee-guida-trigger` §«La fase», nello stesso giro.
4. **Al BE, un passaggio solo** a giro chiuso: con D-T5-2 a, ritirare la normalizzazione di CF e P.IVA in
   `update_soggetto`; i codici nuovi (blocco della natura, del tipo di ruolo, dello stato; forma mancante); con
   D-T5-6 a, il tipo di contatto obbligatorio. Prima di scrivere, il percorso BE di ognuno si legge sul ramo.

### 20.4 Che cosa è scritto (2026-11-24, provato sullo scratch; applicato da Tid su scratch e dbdev alle 01:26)

Il «via» del 2026-11-24: l'altra sessione DB è ferma, i numeri `20261123-48 … -63` li ha dati
`scripts/prossimo_changeset.py` e sono occupati per intero. Nessun commit.

| ChangeSet | Che cosa fa | Segnalazione |
| --- | --- | --- |
| `00_schema/anagrafiche/…-61` | `soggetti.codice` `NOT NULL`; `ragione_sociale_completa` generata anche con il solo cognome o il solo nome (`SET EXPRESSION`, `btrim` e `\|\|`: `concat_ws` è `STABLE` e una colonna generata vuole `IMMUTABLE`) | S43-8, S43-9 |
| `20_code/anagrafiche/…-48` | `trgfn_soggetti_normalize` in fase **`a01`**: CF, P.IVA e P.IVA di gruppo in maiuscolo, senza spazi, vuoto → `NULL`; lo stato proposto solo all'`INSERT` | D-T5-2 a, S20, S43-1 |
| `20_code/anagrafiche/…-49` | il formato in fase `a10`: `_ins` all'`INSERT`, `_upd` all'`UPDATE` con `WHEN` (CF, P.IVA, P.IVA di gruppo, stato, natura) | S43-2 |
| `20_code/script/…-50` | `fn_validate_cf_piva_it`: natura inesistente → tace, parla la FK | S43-3 |
| `20_code/anagrafiche/…-51` | lo stato sotto la regola dell'identificativo (guard `OF … stato_id`, `fn_soggetto_id_fiscale_bloccato` con la colonna `stato_id`); il guard passa in **`a05`** | D-T5-3 a |
| `80_data/changelog/…-52` | la riga di `stato_id` in `dbops.lock_columns_conditional`; riscritte le descrizioni di CF e P.IVA, che nominano il guard | D-T5-3 a |
| `20_code/anagrafiche/…-53` | il guard al COMMIT della forma giuridica giudica anche il paese, e scatta `OF stato_id` | S41-5 |
| `20_code/anagrafiche/…-54` | `fn_check_cambio_natura_soggetto`: natura scritta → nessuna, motivo `E_CAMBIO_NATURA_VERSO_NESSUNA`, da solo, per tutti | D-T5-1 a, S38 |
| `20_code/anagrafiche/…-55`, `-56` | le due porte di creazione: via i pre-controlli; la violazione di `uq_soggetto_idstato_id_fiscale_univoco`, per nome, diventa `E_ADMIN_CF_DUPLICATO` col campo; via le copie `UPPER(TRIM(…))` | S4 |
| `20_code/anagrafiche/…-57` | `E_PIVA_OBBLIGATORIA`, `E_CF_OBBLIGATORIO`: la natura per descrizione, senza id | S42 |
| `20_code/anagrafiche/…-58` | `E_RUOLO_NATURA_*`: ruolo e natura per descrizione, `campo`; il guard solo `BEFORE INSERT` | S42, D-T5-4 a |
| `20_code/anagrafiche/…-59` | `fn_scrivi_dati_societari` prende la riga del soggetto `FOR NO KEY UPDATE` | S41-2 |
| `20_code/anagrafiche/…-60` | dati societari: tipo soggetto in `a05`, solo `BEFORE INSERT`, natura nella frase; la forma mancante la rifiuta il guard della forma (`E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA`); quel guard non è più `OF soggetto_id` | S41-3, S41-6 |
| `80_data/changelog/…-63` | bonifica una tantum di CF, P.IVA e P.IVA di gruppo già scritti, coi trigger sospesi (tranne audit e `tx_id`). Il 2026-11-24 su dbdev non c'è nessuna riga da toccare su 884: la bonifica c'è perché il modello vale per ogni database | D-T5-2 a |
| `20_code/anagrafiche/…-64` | i `COMMENT` dei 17 oggetti del giro **al presente** (linee-guida-sql §5d): quelli di -48 … -61 portavano la cronaca (il brief, «rev», id di changeSet), e li ha fermati `guardrail_comment_al_presente.py` al commit, a file già applicati. I tredici file dichiarano l'eccezione in testa (riga `#`, fuori dal checksum) e rimandano qui. Applicato da Tid il 2026-11-24 | §5d |
| `90_end/…-62` | il runner dei lucchetti: `soggetti_ruoli.tipo_ruolo_id` (`E_SOGGETTO_RUOLO_TIPO_IMMUTABILE`) e `dati_societari.soggetto_id` (`E_DATI_SOCIETARI_SOGGETTO_IMMUTABILE`) | D-T5-4 a, S41-6 |

I CSV: in `config/codici_errore.csv` ci sono quattro codici nuovi, `E_ADMIN_PIVA_DUPLICATA` è obsoleto dal 2026-11-24
(lo sollevava solo il pre-controllo di `_pg`), e cambiano le note di `E_ADMIN_CF_DUPLICATO`,
`E_SOGGETTO_ID_FISCALE_IMMUTABILE` ed `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO`. In `config/messaggi_errore.csv` ci sono le
quattro frasi nuove (id 1533-1536) e sette frasi riscritte, senza id e coi segnaposto contati sul chiamante unico di
ogni codice. In `dbops/automation_lock_columns.csv` ci sono due righe nuove. La frase di `E_ADMIN_CF_DUPLICATO` resta
«%s.», perché la usa anche `fn_crea_operatore_v2`.

Il pgTAP nuovo è `anagrafiche/test-soggetto-natura-identificativo-ruoli-v1.sql`, con 32 asserzioni costruite come
**app**, un operatore e un SUPER_ADMIN.

Ho adeguato sette pgTAP: in ognuno la riga che cambia è una decisione del giro, ed è scritta nel test.
* `test-soggetti-id-fiscale-immutabile-v1`: il guard è anche `OF stato_id`, e la fixture passa B a una copia
  della sua natura invece di svuotarla.
* `test-billing-account-guard-cf-confrontabile-v1`: stessa fixture, sui due soggetti.
* `test-fornitore-privato-indirizzi-v1` (23): il cambio verso il privato lo fa il SUPER_ADMIN, perché lo
  svuotamento della P.IVA parla in `a05`.
* `test-dati-societari-alla-nascita-v1` (16) e `test-fn-scrivi-dati-societari-v1` (15): il codice al posto del
  `23502`.
* `test-dati-societari-policy` (9): la frase nuova.
* `test-fn-crea-soggetto-pf` (5) e `test-fn-crea-operatore` (10): «identificativo fiscale».
* `test-soggetti-ruoli-guard-natura-ammessa`: ho cambiato solo il nome del trigger nell'intestazione.

Note, guide e linee guida aggiornate nello stesso giro:
* le note `_identificativo-fiscale`, `_cambio-di-natura` (cambio di modello, D-T5-1), `_guard-di-ruolo` (via
  «⚠️ Il ruolo che cambia tipo») e `_dati-societari`;
* la guida `soggetti-e-ruoli-anagrafici`;
* `linee-guida-trigger` §«La fase», con la zona `a01` e la sua regola.

### 20.5 Che cosa ha trovato la prova

* **dev ≠ zero sui nomi dei trigger** (⛔, è una regola che c'era già e ho saltato: linee-guida-trigger
  §«Il nome del trigger», «Un trigger si rimonta per funzione, non per nome»). Su un database costruito da zero tre
  dei trigger da rimontare hanno un altro nome: `trg_soggetti_ins_upd_clean_fields` (normalize),
  `trg_soggetti_ins_upd_valida_cf_piva_dispatch` e `trg_dati_societari_ins_upd_check_tipo_soggetto`. La rinomina
  `20251119-01` ha rinominato le funzioni, non quei trigger. Col `DROP` per nome il trigger vecchio restava acceso
  accanto al nuovo, e il pgTAP (21) l'ha visto. Ora i sei changeSet che rimontano tolgono i trigger per
  `tgfoid`.
* **La presenza parlava prima dell'immutabilità.** In `a10` l'alfabeto metteva `guard_cf_piva_obbligatori` prima di
  `guard_id_fiscale_immutabile`. Con la stringa vuota fatta `NULL`, a chi svuota una P.IVA scritta il database
  avrebbe risposto «è obbligatoria» invece di «non si cambia». Il guard dell'identificativo è passato in `a05`,
  come dicono le linee guida.
* **La forma mancante nel verbo parlava prima della natura.** Al privato con la sezione dei dati societari il
  verbo diceva «manca la forma» invece di «questo tipo soggetto non ha dati societari», e se ne è accorto
  `test-dati-societari-alla-nascita-v1` (17). La regola è passata nel guard della forma.
* **`concat_ws` non è `IMMUTABLE`**: l'espressione della colonna generata usa `btrim` e `||`.

**La prova** (`scripts/prova_changeset.py`, sullo scratch `zeroerp_ruoli`, come owner). Il catalogo errori e i
lucchetti li ha simulati un seed d'appoggio nello scratchpad, perché il loader dei CSV non ha SQL da estrarre: la
prova del loader è il migrate. Il test nuovo dà 32 ok su 32 con l'estratto, ed è rosso senza. Per la regressione
ho lanciato i pgTAP di `anagrafiche`, i presidi del catalogo errori e dei lucchetti, e i vicini in `script`,
`config`, `dbops` e `rls`, 135 file in tutto. Nella prima corsa ci sono otto rossi nuovi, tutti spiegati: sono i
sette test adeguati in §20.4 e il difetto della forma nel verbo. Nella seconda corsa, ripetuta dopo le
correzioni, 111 file sono verdi. Gli ultimi 22 si sono interrotti perché Tid ha applicato il giro sullo scratch a
metà corsa (lo script: «il catalogo è cambiato»), e vanno ripresi dalla corsa di Tid. Dopo l'apply ogni funzione ha
un solo montaggio col nome nuovo, su dbdev come sullo scratch. Tre cose restano da provare.
* Due file non li lancia lo script, perché hanno più di una riga `BEGIN;`:
  `test-soggetti-indirizzi-required` e `test-soggetti-ruoli-indirizzi-required`.
* `test-identita-digitali-guard-coerenza` si interrompe con e senza l'estratto: è un rosso che c'era già.
* L'esito come app l'ha dato la corsa di Tid (2026-11-24): **verdi**. Il solo rosso del giro era nella fixture di
  `test-billing-account-guard-cf-confrontabile-v1`, dove il codice interno della natura copiata superava i 10
  caratteri di `codice_interno`; è corretto. Il resto dei rossi era già rosso prima.

⛔ **Non provato**: S41-2, le due prime scritture concorrenti, perché serve una seconda sessione. Il lucchetto si
legge nel corpo.

### 20.6 Che cosa resta

* ✅ **D-T5-6 decisa: b** (Tid, 2026-11-24): il giro 3-bis è il §20.8. Prima della decisione, la condizione di Tid
  aveva due risposte. Il BE passa sempre il tipo di contatto:
  `richiedi_contatto_valido` pretende un contatto `VALID`, che ha `tipo_contatto_id` (ramo `f1b8f9df7a`). I
  chiamanti nel DB invece non lo passano:
  * `anagrafiche.fn_crea_operatore_v2` e `anagrafiche.fn_provisiona_dati_di_sviluppo`;
  * l'helper `dbops.fn_pgtap_crea_soggetto_pf`;
  * circa 80 chiamate dirette nei pgTAP.

  Con **a** ognuno dovrebbe scegliere un tipo da solo, e la scelta sarebbe la stessa ricopiata in tre posti. Proposta:
  **b**, un tipo proposto dichiarato in `config` e letto da un BB come lo stato proposto. Il ripiego «il primo per
  id» intanto resta com'era: -55 e -56 non lo toccano.

  ⚠️ Fatto trovato il 2026-11-24, rileggendo i chiamanti: le scelte sono già due, e diverse. Le due porte di
  creazione prendono «il primo per id», mentre `script.fn_crea_utente_tecnico` prende il tipo con
  `codice_interno = 'PRINCIPALE'`, scritto nel codice. La strada b le porta tutte e due a una sede sola.
* **Segnalazione nuova, S-T5-a** (fuori dal tema, va a T9 o al tema dell'operatore).
  `anagrafiche.fn_crea_operatore_v2`, per decidere `E_CREDENZIALE_ALTRA_PERSONA`, confronta
  `id_fiscale_univoco_cf_piva` con `UPPER(TRIM(p_codice_fiscale))`. Per una persona che ha anche una ditta individuale
  l'identificativo della ditta è «CF P.IVA», quindi una veste sulla ditta conta come «un'altra persona». È la radice
  di S4, in un'altra sede. Il confronto va fatto sul codice fiscale, che il DB ora normalizza.
* ⚠️ **Superato il 2026-11-24, riletto sul catalogo dello scratch: la porta è già chiusa per l'app.** Dal 2026-11-17
  (`20261117-07`, brief archiviato `brief-db-seed-primo-impianto-non-si-riscrive`) `script.trgfn_lock_columns` chiede
  `script.fn_porta_manutenzione_aperta`. Con la GUC accesa la porta si apre solo alla sessione del migratore e lascia
  una riga in `dbops.porte_manutenzione_passaggi`; per l'app resta chiusa. Il censimento del brief delle porte la
  lascia fuori a ragione, perché cerca i trigger che leggono la GUC da soli. L'unico altro oggetto che nomina la GUC
  è un commento in `script.trgfn_righe_natura_vendita`. Lì si scrive una riga, perché nessuno rifaccia la stessa
  lettura. Il testo di prima, sbagliato: ~~la porta dei lucchetti di colonna (`script.trgfn_lock_columns`, GUC
  `zeroerp.allow_lock_columns_override`, senza chiedere il proprietario) non è fra le porte censite da
  [brief-db-porte-aperte-dalla-sola-guc](brief-db-porte-aperte-dalla-sola-guc.md). I due lucchetti nuovi valgono
  quanto lei. È da registrare lì.~~
* **La doc auto-generata** degli oggetti del giro è rigenerata (Tid, 2026-11-24). -64 è applicato (2026-11-24): si
  rigenera di nuovo, per i COMMENT, insieme al giro 3-bis.
* **Il pre-commit `check-i18n-keys` è rosso** per il lato FE: la chiave
  `anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`, emessa dal DB, non è ancora nei locales. La aggiunge il
  team FE (§20.7, voce 3). È un rosso atteso, non un difetto del giro.
* **Il passaggio al BE**, uno solo, è §20.7.

### 20.7 Il passaggio al BE (da girare dopo l'apply)

Letto sul ramo `origin/dev/backend-tid` (`f1b8f9df7a`). Chi cambia per primo: il DB, perché nessuna voce rompe ciò
che il BE fa oggi. L'elenco è chiuso.

1. **CF e P.IVA li normalizza il database** (maiuscole, senza spazi, vuoto → `NULL`), da ogni strada.
   `backend/apps/anagrafiche/db/soggetti_repository.py`, `update_soggetto`: `codice_fiscale` e `partita_iva` si
   possono togliere da `_NULLABLE` (riga 571). Gli altri campi restano.
2. **Il doppione dell'identificativo** arriva dalle due porte come `E_ADMIN_CF_DUPLICATO` (`P0001`), col campo:
   `codice_fiscale` per `fn_crea_soggetto_pf`, `partita_iva` (o `codice_fiscale`) per `_pg`. Non arriva più come
   `23505` su `uq_soggetto_idstato_id_fiscale_univoco`.
   * `backend/apps/anagrafiche/services/soggetti_service.py`, `_create_pf` e `_create_pg`: la voce
     `uq_soggetto_idstato_id_fiscale_univoco` di `create_with_constraint_mapping` non scatta più in creazione,
     mentre `_MSG_PF_CF_DUPLICATO` e `_MSG_PG_CF_PIVA_DUPLICATA` restano per la modifica diretta.
   * Con la modifica la ditta individuale di chi è già privato nasce: prima il database la rifiutava.
   * `backend/apps/core/services/error_messages_fallback.py`: `E_ADMIN_PIVA_DUPLICATA` è obsoleto, perché il
     database non lo solleva più.
3. **Codici nuovi**, tutti col campo nel contesto tranne il primo, che è un motivo del cambio di natura:
   * `E_CAMBIO_NATURA_VERSO_NESSUNA`: una natura scritta non si svuota. È un motivo del cambio di natura, con
     reason `VERSO_NESSUNA` e reason_key `anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`, da aggiungere in
     `frontend/src/locales/it.json` ed `en.json` (riga ~6383). La chiave
     `senza_natura_con_titoli_iva` non la emette più nessuno.
     ✅ **La chiave nuova è nei due locales** (sessione BE/FE, 2026-11-24, brief-be-fe-BB-audit §7.9):
     `check_i18n_keys.py` è pulito. `senza_natura_con_titoli_iva`, che non citava più nessuno, è
     tolta dai due locales (ok Tid, 2026-11-24).
   * `E_SOGGETTO_RUOLO_TIPO_IMMUTABILE` (`tipo_ruolo_id`) ed `E_DATI_SOCIETARI_SOGGETTO_IMMUTABILE` (`soggetto_id`):
     sono lucchetti. Il BE non scrive nessuna delle due colonne.
   * `E_DATI_SOCIETARI_FORMA_GIURIDICA_OBBLIGATORIA` (`forma_giuridica_id`): prima era un `23502`.
4. **Lo stato del soggetto** lo cambia solo il SUPER_ADMIN, e `dbops.fn_non_editable_fields` lo spegne per gli altri.
   Il BE non scrive `stato_id` in modifica (`SOGGETTO_UPDATE_COLS`), quindi non c'è niente da cambiare, salvo un form
   che lo mostrasse modificabile.
5. Le frasi di `E_PIVA_OBBLIGATORIA`, `E_CF_OBBLIGATORIO`, `E_RUOLO_NATURA_NON_AMMESSA`,
   `E_RUOLO_NATURA_TIPO_DET_NULL` ed `E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO` non mostrano più id e hanno un
   segnaposto in meno. Un override del BE che le ricopiasse va riletto.
6. **Il tipo di contatto proposto** (D-T5-6 b, §20.8). Il BE passa sempre il tipo, quindi non cambia niente nel
   comportamento. `E_DEFAULT_CONTATTO_MISSING` è obsoleto, perché non lo solleva più nessuno:
   `backend/apps/core/services/error_messages_fallback.py` (riga 384) ha la sua voce, che si può togliere.
   `error_policies_generated.py` lo segue da solo, alla rigenerazione.

**Esito del passaggio (sessione BE/FE, `dev/backend-tid`, 2026-11-26; da committare).** Tutte le voci fatte o
censite:

* **1** fatta: `codice_fiscale` e `partita_iva` tolti da `_NULLABLE` di `update_soggetto`.
* **2** fatta: la voce del vincolo tolta da `_create_pf` e `_create_pg`. ⚠️ **Correzione al testo sopra**:
  `_MSG_PF_CF_DUPLICATO` e `_MSG_PG_CF_PIVA_DUPLICATA` non servivano alla modifica diretta (che ha il messaggio suo in
  `update_with_dedup`), ma solo da ripiego della creazione, dove dicevano «CF duplicato» per ogni unicità non
  riconosciuta. Sostituiti da un ripiego neutro, `_MSG_SOGGETTO_DUPLICATO` (ok Tid, 2026-11-26).
  `E_ADMIN_PIVA_DUPLICATA` tolto dai ripieghi.
* **3** e **4**: niente da cambiare (la chiave i18n era già fatta il 2026-11-24).
* **5**: nessun override ricopia quelle frasi: i ripieghi non hanno id né segnaposto, gli override sono solo gesti.
* **6** fatta: `E_DEFAULT_CONTATTO_MISSING` tolto dai ripieghi.
* Presidio nuovo sul DB vero: `test_soggetti_identificativo_doppio_db`. Prova il doppione del privato sul CF, la PG
  sulla P.IVA, la ditta individuale di chi è già privato che nasce, e la normalizzazione in modifica. Il test
  simulato che accendeva `codice_fiscale` da un `23505` ora prova il ripiego neutro senza campo.

### 20.8 Giro 3-bis — D-T5-6 b, il tipo di contatto proposto (2026-11-24, al via di Tid)

**La decisione** (Tid, 2026-11-24): quando chi crea un soggetto non dice il tipo del contatto di default, il database
scrive il **tipo proposto**. È un parametro di `config`, letto da un BB come lo stato proposto: lo stesso modello
(cascata degli override, nessun ripiego, errore se manca).

**Che cosa dice il catalogo** (dbdev, 2026-11-24, dopo l'apply di -64). Chi sceglie il tipo quando nessuno lo dice
lo fa in tre modi diversi:

| Lettore | Come sceglie oggi |
| --- | --- |
| `anagrafiche.fn_crea_soggetto_pf`, `_pg` | il primo per id (`ORDER BY id LIMIT 1`); se la tabella è vuota, `E_ADMIN_VALIDAZIONE` |
| `script.fn_crea_utente_tecnico` | `codice_interno = 'PRINCIPALE'`, scritto nel corpo; se manca, `NULL` in silenzio, e lo rifiuta poi `fn_crea_contatto` come contatto incompleto |
| `dbops.fn_pgtap_crea_soggetto_pg` | il primo per id, e lo passa alla porta |

Ci sono anche due fatti che il giro tocca.
* `script.fn_get_tipo_contatto_id(codice)`, un BB «dal codice interno all'id», non lo chiama nessuno: né a DB
  (`pg_proc`), né sul ramo del BE (`origin/dev/backend-tid`, sola lettura). È un'altra copia della stessa ricerca,
  con un suo codice (`E_DEFAULT_CONTATTO_MISSING`, che il BE ha solo nel fallback dei messaggi) e con una
  scrittura dentro una funzione `STABLE` (genera un `tx_id`).
* L'ordine da zero regge. Il parametro nasce dal mirror `20250715-01`, che gira prima del seed di
  `config.tipi_contatti` (`20250813-03`) e prima dei seed che creano gli utenti tecnici (`20260904-27`, `-39`).
  `STATO_PROPOSTO_ISO2` sta nello stesso mirror, e lo stesso `fn_crea_utente_tecnico` lo legge già.

**Che cosa si fa:**

| # | Oggetto | Che cosa cambia |
| --- | --- | --- |
| 1 | `config.parameters` (CSV, riga 64) | `TIPO_CONTATTO_PROPOSTO`, valore `PRINCIPALE` (il `codice_interno`), `ammette_override = true`, `TESTO` |
| 2 | `config.parameter_fk_surrogate` (CSV, riga 9) | il valore e ogni override devono essere un `codice_interno` di `config.tipi_contatti` (`EXACT`) |
| 3 | `script.fn_tipo_contatto_proposto_id(p_chi)`, nuovo | il BB: legge il parametro con `script.fn_get_parameter_di_sessione`; vuoto `E_CONFIG_MANCANTE`, codice senza tipo `E_DEFAULT_ERRATO`. `codice_interno` è unico, quindi non c'è il caso «ambiguo» dello stato |
| 4 | `fn_crea_soggetto_pf`, `_pg` | `COALESCE(p_tipo_contatto_id, script.fn_tipo_contatto_proposto_id(…))`; esce il ramo «nessun tipo in tabella» |
| 5 | `script.fn_crea_utente_tecnico` | il BB al posto di `'PRINCIPALE'`; il `COMMENT` si riscrive al presente (§5d: quello di oggi è una cronaca di «Rev») |
| 6 | `dbops.fn_pgtap_crea_soggetto_pg` | non sceglie più il tipo: lo propone la porta |
| 7 | `script.fn_get_tipo_contatto_id` | si ritira (`DROP`), nello stesso giro, per la regola del 2. `E_DEFAULT_CONTATTO_MISSING` diventa obsoleto dal 2026-11-24 |

Sono sei changeSet (3 … 7), più i due CSV e la riga di `codici_errore.csv`. Il BE non cambia niente, salvo la voce 6 di
§20.7.

**La prova sul controesempio.** Un tipo con id 0, cioè minore di tutti, è quello che oggi «il primo per id» prende.
Col giro le due porte e il builder pgTAP scrivono il tipo proposto. Un override per funzione cambia la proposta, e
l'utente tecnico la segue: oggi resta `PRINCIPALE`.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 2026-11-24):

| Guida o nota | Esito |
| --- | --- |
| [gestione-dei-contatti](../../guide/gestione-dei-contatti.md) | **indietro**: «Nominativo e tipo di contatto sono obbligatori» è vero, ma non dice che alla nascita del soggetto il tipo non detto è quello proposto. Si aggiunge col giro |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | **indietro** sullo stesso punto: «il verbo crea il contatto del soggetto» non dice con quale tipo. Si aggiunge col giro |
| [processi-automatici-classe-e-identita](../../guide/processi-automatici-classe-e-identita.md), [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) | **coerenti**: nominano `fn_crea_utente_tecnico` per l'identità, non per il tipo del contatto |
| [architettura-multi-face-auth](../../guide/architettura-multi-face-auth.md) | **coerente**: nomina `fn_crea_operatore_v2` per le vesti |
| [gestione-degli-indirizzi](../../guide/gestione-degli-indirizzi.md), nota `_indirizzo-libero-o-dettaglio` | **coerenti**: lo stato proposto è il modello del giro, e non cambia |
| [pgtap-come-si-scrive-un-test](../../guide/pgtap-come-si-scrive-un-test.md) | **coerente**: il builder PF non cambia firma |
| nota `_identificativo-fiscale` | **coerente**: il giro non tocca l'identificativo |

Orfano: `anagrafiche.fn_provisiona_dati_di_sviluppo`, uno strumento di sviluppo che non è un concetto del dominio.
Nessuna guida da scrivere.

**I pgTAP.** Uno nuovo, `anagrafiche/test-tipo-contatto-proposto-v1.sql`, costruito come app (l'app ha `INSERT`,
`UPDATE` e `DELETE` su `config.parameters`, `parameter_overrides` e `tipi_contatti`, catalogo di dbdev del
2026-11-24). L'utente tecnico si prova in `script/test-fn-crea-utente-tecnico.sql`, che gira da owner, con un caso in
più (14).

**La documentazione nello stesso giro:**
* le pagine `manual/` di `fn_crea_soggetto_pf` e `_pg`: via la riga «⚠️ Il tipo di contatto di ripiego è il primo per
  id»;
* le pagine di `fn_crea_utente_tecnico` e `dbops.fn_pgtap_crea_soggetto_pg`;
* una pagina nuova per il BB, sul modello di `fn_stato_proposto_id`;
* la pagina di `fn_get_tipo_contatto_id` si toglie con la funzione;
* `config/manual/tipi_contatti` è stantia: nomina `cod_int_tipo_contatto` e due trigger con un nome che non esiste
  più. Si riallinea, col tipo proposto;
* le due guide indietro (sopra).

**Scritto (2026-11-24, numeri dal primo libero, al via di Tid):**

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261123-68-create-fn-tipo-contatto-proposto-id` | il BB (voce 3) |
| `20_code/anagrafiche/20261123-69-update-fn-crea-soggetto-pf-tipo-contatto-proposto` | la porta PF (voce 4) |
| `20_code/anagrafiche/20261123-70-update-fn-crea-soggetto-pg-tipo-contatto-proposto` | la porta PG (voce 4) |
| `20_code/script/20261123-71-update-fn-crea-utente-tecnico-tipo-contatto-proposto` | l'utente tecnico, firma ri-ancorata con `%TYPE`, `COMMENT` al presente (voce 5) |
| `20_code/dbops/20261123-72-update-fn-pgtap-crea-soggetto-pg-tipo-contatto-proposto` | il builder pgTAP (voce 6) |
| `20_code/script/20261123-73-drop-fn-get-tipo-contatto-id` | il ritiro (voce 7) |

Con le tre righe dei CSV, il pgTAP nuovo e il caso 14. Corpi dai sorgenti verificati uguali al catalogo di dbdev;
`COMMENT` delle porte e del builder dal catalogo (al presente da -64), cambia solo la frase del tipo. Manual: le
porte, l'utente tecnico, il builder, `tipi_contatti` riallineata, il gemello nello stato proposto, la pagina nuova
del BB; quella di `fn_get_tipo_contatto_id` è tolta. Le due guide indietro aggiornate.

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli` completo, ricostruito alle 14:33):
* `test-tipo-contatto-proposto-v1`: con i sei changeSet 12/12; senza, si ferma al BB che manca. Il controesempio
  con il solo -68 (porte di prima): il caso 4 si ferma su `fn_crea_contatto`, perché la porta ha preso il tipo con
  id 0;
* `test-fn-crea-utente-tecnico`: con 14/14, senza rosso il solo caso 14;
* `test-fn-pgtap-crea-soggetto-pg-v1`: 4/4 prima e dopo.

Corse da owner (lo script): il pgTAP nuovo è scritto per girare come app, e la corsa come app è di Tid.

**Chiusura** (2026-11-24): applicato da Tid su scratch e dbdev, pgTAP verdi. Doc auto-generata rigenerata
(`scripts/gen_db_docs.py`): la pagina nuova del BB, quella di `fn_get_tipo_contatto_id` tolta come orfana, le due
porte, l'utente tecnico, il builder, gli indici di `config` e `script`. `scripts/check_i18n_keys.py` segnala una
chiave: `anagrafiche.soggetti.cambio_natura_blocco.verso_nessuna`, del giro 3, che il FE aggiunge (§20.7, voce 3).
Il giro 3-bis non ne porta di nuove.

⚠️ **Resta fuori, da segnalare**: `dbops.fn_pgtap_crea_soggetto_pg` ha `p_tipo_soggetto_dettaglio_id integer`,
un'eccezione dichiarata nel corpo (la colonna è `bigint`, ancorarla cambia l'identità della firma: `DROP`, `GRANT`
di nuovo, il gemello PF ha già `bigint`). Non è del giro 3-bis: un giro a sé, se Tid lo vuole.

## 21. Giro 4 — T7a, gli indirizzi (2026-11-24: decisioni prese, applicato, pgTAP verdi)

T7 si divide in due giri (Tid, 2026-11-24): **T7a, gli indirizzi** (S3, S10, S16 seconda metà, S19, S48, S49 metà,
S50 senza la porta) e **T7b, i contatti e il catasto** (S8, S46, S11, S47, col pgTAP `create-soggetto-gestori.sql`).
Questa sezione è l'analisi di T7a, letta sul catalogo di dbdev il 2026-11-24 dopo l'apply del giro 3-bis. I
changeSet sono in §21.5. Sul ramo `origin/dev/backend-tid` si è guardato solo chi chiama gli oggetti, in sola lettura.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 26 oggetti, 2026-11-24):

| Guida o nota | Esito |
| --- | --- |
| [gestione-degli-indirizzi](../../guide/gestione-degli-indirizzi.md) | **contraddetta su due punti**, decide Tid. R9 descrive come comportamento il blocco del titolare a cui la matrice nuova chiede un indirizzo («non si modifica più»): è la S48, D-T7a-1. R7 dice che con una via incompleta (un comune senza provincia) il «trova o crea» si ferma: è la S50, D-T7a-2. Per il resto è **indietro** dove il giro corregge: R3 (la forma di un elemento vuoto), R8 (la posizione) |
| nota `_indirizzi-obbligatori` | **contraddetta** con R9 (D-T7a-1): la tabella «Le strade» dichiara «INSERT e ogni UPDATE». È **indietro** sul livello del soggetto: «il ripiego vale come è scritto nella riga» non dice che il ripiego può essere un tipo che la natura vieta |
| nota `_indirizzo-libero-o-dettaglio` | **indietro**: dice che col dettaglio «comune, CAP, provincia e posizione li dice la via», e insieme che `trgfn_indirizzi_sync_geoloc` copia la posizione nella riga. Le due frasi non stanno insieme (S50, D-T7a-3) |
| nota `_tipo-indirizzo-ammesso` | **coerente**. Il suo «Quando cambia una matrice: nessuno rigiudica gli indirizzi già scritti» è il modello su cui la D-T7a-1 propone di allineare gli obbligatori |
| nota `_cambio-di-natura` | **coerente**: il cambio di natura rigiudica i ruoli, e il giro non lo tocca |
| [catasto-delle-istanze](../../guide/catasto-delle-istanze.md), [generazione-cliente](../../guide/generazione-cliente.md), [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md), [riclassificazione-vie](../../guide/riclassificazione-vie.md) | **coerenti**: nominano `indirizzi_dettaglio` per il legame col civico, che il giro non cambia |

Quattro orfani: `fn_indirizzi_con_obbligatori`, `fn_indirizzo_elemento`, `fn_search_indirizzi_dettaglio`,
`script.vw_indirizzo_completo`. Sono dettagli interni, non concetti del dominio: nessuna guida da scrivere. Il primo
e il terzo cambiano col giro (D-T7a-4, D-T7a-6).

### 21.1 Che cosa dice il catalogo, segnalazione per segnalazione

| # | Esito | Che cosa dice il catalogo |
| --- | --- | --- |
| S3 | **difetto, e più largo** | `vw_indirizzi_resolved_base` fa `LEFT JOIN script.vw_indirizzo_completo ic ON ic.id_comune = b.comune_id`, e la vista ha una riga per via. Un indirizzo libero della forma del catalogo esce una volta per ogni via del suo comune. C'è anche un secondo difetto: `cap` è `COALESCE(vidd.cap, ic.codice_postale)`, cioè il CAP di una via a caso del comune e non quello scelto (`b.codice_postale_id`). In un comune con più CAP la vista ne mostra uno sbagliato. Il join non serve a niente: comune, provincia e CAP sono già in `co_ai`, `pr_ai` e `cp_ai`. La correzione non cambia le colonne: si toglie `ic`, `cap` diventa `cp_ai.codice` e `provincia` diventa `pr_ai.sigla`. Le viste figlie (`_all`, `_ruolo`, `_soggetto`) e `script.fn_get_indirizzo` e `_by_ruolo` la seguono da sole |
| S16 (2ª metà) | **difetto** | `vw_indirizzi_dettaglio` fa un join interno con `script.vw_indirizzo_completo`, che a sua volta lo fa interno con `config.province`, e `config.comuni.provincia_id` è nullable. Il civico di una via di un comune senza provincia sparisce dalla vista, e con lui l'indirizzo che lo usa sparisce da `vw_indirizzi_resolved_base`, la cui riga resta senza testo. È la stessa radice di S50, D-T7a-2 |
| S50 (via) | **difetto, la radice è il modello** | `fn_build_indirizzo_normalizzato` legge `via_norm` da `vw_indirizzo_completo`. Quella vista chiede la provincia e il CAP, che per la via non servono: `via_norm` è toponimo più nome. Da `config.stradario` a `stradario_generale` e `toponomastica` le colonne sono tutte `NOT NULL`. Col comune senza provincia `via_norm` resta `NULL`, e dal «trova o crea» arriva `E_INDIRIZZO_VIA_NON_RISOLTA`. Da un INSERT diretto, o modificando il civico, arriva il `23502` grezzo. D-T7a-2 |
| S50 (forma) | **difetto** | `fn_indirizzo_elemento_dettaglio` decide la forma dal solo testo: con `indirizzo_libero` vuoto o assente, e senza `indirizzo_dettaglio_id`, chiama `fn_create_indirizzo` con tutto `NULL`. Questa scrive `config.stradario_generale` con `toponomastica_id NULL`, e la scrittura cade sul `NOT NULL` di una tabella di configurazione. Così non si arriva mai al guard della forma libera, che darebbe `E_INDIRIZZO_LIBERO_INCOMPLETO` sul campo giusto. Il COMMENT dice «non valida i campi di una via nuova: pre-check del backend», cioè una regola lasciata al BE. D-T7a-5 |
| S50 (posizione) | **difetto di modello** | Su `indirizzi` e `indirizzi_soggetti`, `trgfn_indirizzi_base_normalize` svuota la posizione quando c'è il dettaglio, e subito dopo `trgfn_indirizzi_sync_geoloc` ci ricopia `civic_geoloc`. La copia non segue il civico: se `civic_geoloc` cambia, la riga resta con quella vecchia. Il lettore la usa solo come ultimo ripiego (`COALESCE(vidd.civic_geoloc, vidd.street_geoloc, b.geoloc)`), quindi la copia è una seconda sede della posizione che nessuno legge per prima. Nella storia non c'è una decisione (`refactor-indirizzi-conti-utility`: «verifica sola»). D-T7a-3 |
| S48 (requisito nuovo) | **comportamento dichiarato, cambio di modello** | I due trigger dei titolari (`trg_soggetti_def_guard_indirizzi_required_aft_ins_upd`, `trg_soggetti_ruoli_def_guard_indirizzi_required_aft_ins_upd`) sono `AFTER INSERT OR UPDATE`, senza `OF` né `WHEN`. Quando una riga di matrice diventa obbligatoria, chi esiste già non si scrive più su nessuna colonna. Lo stesso vale dal lato degli indirizzi: i due guard di `indirizzi` e `indirizzi_soggetti` rigiudicano **tutto** il titolare, quindi su un titolare incompleto da prima non si cancella nemmeno un indirizzo che nessuno chiede. Il tipo di ruolo e il soggetto del ruolo sono bloccati dal giro 3, quindi per il ruolo non resta nessuna colonna che cambi il requisito. D-T7a-1 |
| S48 (ripiego del soggetto) | **difetto** | `fn_indirizzi_obbligatori_mancanti_soggetto` conta il ripiego senza chiedersi se la natura lo ammette (sul ruolo `fn_indirizzi_obbligatori_ruolo` lo fa). Il rifiuto può quindi proporre un ripiego che il guard del tipo non lascia scrivere |
| S48 (copia degli obbligatori) | **difetto** | `fn_indirizzi_con_obbligatori` cerca nell'elenco solo il tipo e ignora il ripiego. Se l'elenco ha il ripiego, nasce comunque la copia del tipo, cioè un indirizzo che nessuno ha chiesto. Le due madri plurali scartano poi solo i tipi già sul titolare, non i ripieghi. D-T7a-4 |
| S48 (le sedi) | **difetto, regola del 2** | Sul soggetto «obbligatorio per la natura» si calcola in sette posti, con tre varianti. In `fn_crea_indirizzi_soggetto`, `fn_indirizzi_obbligatori_mancanti_soggetto` e i due picker (`_natura`, `_soggetto`) si usa `obbligatorio` più il predicato con la finestra. In `dbops.fn_pgtap_crea_soggetto_pf`, `_pg` e `fn_provisiona_dati_di_sviluppo` si usa `attivo AND obbligatorio`, cioè senza la finestra e senza il predicato. Il ruolo ha la sua sede (`fn_tipo_indirizzo_obbligatorio_per_ruolo`); il soggetto no. D-T7a-4 |
| S48 (`tx_id`) | **difetto minore** | `trgfn_indirizzi_guard_obbligatori_ruolo` e `trgfn_indirizzi_soggetti_guard_obbligatori_soggetto` passano `NULL::uuid` al guard: il rifiuto si logga senza la transazione. Va passato `OLD.tx_id`. Le due funzioni guardano dal corpo se il tipo o il titolare sono cambiati: un `WHEN` sul trigger eviterebbe l'evento differito a ogni UPDATE. Il `WHEN` è DDL su un trigger, e si scrive in `00_schema` |
| S49 (tipo per id) | **difetto** | `fn_indirizzo_elemento` prende `tipo_indirizzo_id` così com'è. Un id che non esiste passa, e lo rifiuta poi la FK (⚠️ corretto dalla prova, §21.4: lo rifiuta il guard del tipo, col motivo sbagliato `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`). Con id e codice insieme vince l'id e il codice non si confronta. Un id non numerico dà il `22P02` del cast. Tutti e tre i casi devono dare `E_TIPO_INDIRIZZO_NON_TROVATO` sul campo |
| S49 (`bigint`/`integer`) | **difetto, la radice è una colonna** | `config.tipi_ruolo_tipi_indirizzo.tipo_ruolo_id` è `bigint` e punta a `config.tipi_ruoli.id`, che è `integer`. Le firme la seguono: `fn_tipo_indirizzo_ammesso_per_ruolo(bigint, …)`, mentre `fn_check_tipo_indirizzo_ruolo_su_contesto`, `fn_indirizzi_obbligatori_ruolo` e gli altri hanno `integer`. Fatto nuovo: la stessa tabella ha **due FK identiche** su `tipo_ruolo_id` (`fk_tipi_ruoli_tipi_indirizzo_ruolo`, `fk_tipi_ruolo_tipi_indirizzo_tipo_ruolo`). Nel catalogo di `anagrafiche` e `config` è l'unico doppione. D-T7a-7 |
| S19 | **difetto** | Le FK di `indirizzi` verso `config.comuni`, `codici_postali` e `stati` sono `ON DELETE SET NULL`, quelle di `indirizzi_soggetti` non hanno azione. Non è solo una divergenza fra gemelle: il `SET NULL` è un UPDATE che passa dai trigger della riga. Togliere il comune fa rifiutare la cancellazione dal guard della forma, con un errore che parla dell'indirizzo; togliere lo stato fa scrivere a `trgfn_indirizzi_base_normalize` lo **stato proposto**, e l'indirizzo cambia paese senza che nessuno l'abbia chiesto. ⚠️ Precisato dalla prova (§21.4): col proposto di oggi la cancellazione è rifiutata dal guard della forma; il cambio silenzioso avviene con un proposto senza catalogo. Proposta: nessuna azione anche su `indirizzi`, come la gemella. Un comune in uso non si cancella, si spegne |
| S10 | **la funzione non ha chiamanti** | `fn_search_indirizzi_dettaglio` non la chiama nessuno, né a DB (`pg_proc`) né sul ramo del BE, che cerca i civici leggendo `vw_indirizzi_dettaglio` (`indirizzi_repository.py`, righe 85 e 108). I difetti letti ci sono: estensione, palazzina, scala, piano e interno si confrontano grezzi con valori salvati in maiuscolo e col `/`, c'è un `RAISE` diretto e `p_limit` non ha tetto. Ma una ricerca che nessuno usa, accanto a quella del BE, è una copia. D-T7a-6 |

**Fatto nuovo, S-T7a-a.** `anagrafiche.fn_create_indirizzo`, chiamata anche dal BE (`indirizzi_repository.py`, riga
191), sul ramo «via nuova» scrive lo stradario con `ON CONFLICT … DO UPDATE SET comune_id = EXCLUDED.comune_id`
anche quando la via esiste già. Dal giro 1 (Q7) lo storico di `config.stradario` è continuo, e
`script.trgfn_storico_generic` non scarta un UPDATE che non cambia niente. Ritrovare una via esistente lascia quindi
una versione di storico della via a ogni indirizzo creato. Lo stesso `ON CONFLICT` su `stradario_generale` riscrive
`descrizione` col suo valore. Correzione: `DO NOTHING` più la rilettura per chiave, oppure prima la ricerca e poi
l'INSERT, come il «trova o crea» del civico. Si prova col pgTAP: la seconda chiamata con la stessa via non aggiunge
versioni.

### 21.2 Le decisioni per Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| D-T7a-1 | **Un requisito nuovo blocca chi esiste?** Oggi sì: ogni scrittura del titolare rigiudica tutto (R9). È un cambio di modello: la guida e la nota lo dichiarano | **No, come per i tipi ammessi**: una matrice che cambia vale per le scritture che toccano il requisito, non per tutte. (a) Il soggetto si giudica all'INSERT e al cambio di natura (`UPDATE OF tipo_soggetto_dettaglio_id` più `WHEN`); il ruolo all'INSERT, perché tipo e soggetto sono bloccati. (b) Dal lato degli indirizzi si giudica solo la riga che esce: chi cancella un indirizzo, o ne cambia il tipo, non può togliere il **solo** indirizzo che soddisfa una riga obbligatoria. Un titolare incompleto per una matrice nuova resta modificabile, e il form lo vede da `fn_indirizzi_obbligatori_mancanti_*`, che c'è già. Argomento sul modello: la stessa matrice ha due regole, «ammesso» e «obbligatorio», che oggi rispondono in modo diverso allo stesso cambio. Si riscrivono R9 e la nota |
| D-T7a-2 | **Una via di un comune senza provincia si usa?** Oggi no, e la guida lo dice (R7). Il modello però ammette `comuni.provincia_id NULL` | **Sì**: `via_norm` si legge da stradario, stradario generale e toponomastica, tutte colonne `NOT NULL`, e non più da `vw_indirizzo_completo`. `vw_indirizzi_dettaglio` va in `LEFT JOIN` sulla provincia. Una via c'è finché c'è la sua riga: «via non risolta» resta solo per uno `stradario_id` che non esiste, e lo dice già il «trova o crea» (`E_CODICE`). `E_INDIRIZZO_VIA_NON_RISOLTA` diventa obsoleto. Con **no**, invece, la regola va nel guard del civico (`trgfn_indirizzi_dettaglio_guard_chiave`), su ogni strada, e la vista va comunque in `LEFT JOIN`, perché una provincia si può togliere dopo |
| D-T7a-3 | **La posizione di un indirizzo col dettaglio** | Resta `NULL`, come comune e CAP: la dice il civico. Si ritira `trgfn_indirizzi_sync_geoloc`, con i suoi due trigger, e le righe di oggi si portano a `NULL` nello stesso giro. I lettori leggono già il civico per primo |
| D-T7a-4 | **Gli obbligatori del soggetto: una sede** | Un BB `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura(natura, tipo, giorno)`, gemello di quello del ruolo, letto dalle sette sedi, comprese le tre degli strumenti di sviluppo e pgTAP. Il ripiego del soggetto conta solo se la natura lo ammette. `fn_indirizzi_con_obbligatori` riceve, oltre al tipo, il ripiego di ciascuna riga, e non copia un tipo il cui ripiego è già nell'elenco o sul titolare. Le copie si ritirano nello stesso giro |
| D-T7a-5 | **Un elemento senza forma** | La forma la decide il DB dalle chiavi: un elemento senza dettaglio e senza via è libero, e lo giudica il guard della forma (`E_INDIRIZZO_LIBERO_INCOMPLETO`, campo `indirizzo_libero`). Una via nuova incompleta (manca la toponomastica, la descrizione, il comune o il CAP) ha un codice, con il campo che manca. Il «pre-check del backend» esce dal COMMENT, perché una regola del dato non si lascia al BE |
| D-T7a-6 | **`fn_search_indirizzi_dettaglio`** | Si ritira (`DROP`), con la sua pagina `manual/`: non la chiama nessuno, e la ricerca vive nel BE. Se Tid la vuole come sede della ricerca dei civici, l'alternativa è correggerla (confronto sui valori normalizzati da `fn_build_indirizzo_normalizzato`, `fn_log_and_raise_error`, un tetto a `p_limit`) e chiedere al BE di passarci. Quella però è una richiesta di sviluppo, non una correzione |
| D-T7a-7 | **Il tipo di ruolo `bigint`** | `config.tipi_ruolo_tipi_indirizzo.tipo_ruolo_id` diventa `integer`, come la colonna a cui punta, e la FK doppia si toglie. `fn_tipo_indirizzo_ammesso_per_ruolo` cambia firma (§5f di `linee-guida-sql`: `DROP`, `CREATE`, `GRANT`, e i chiamanti `BEGIN ATOMIC` da ricreare). Il BE non la chiama. In alternativa va in T11, la forma |

**Esito del 2026-11-24.** Tutte decise da Tid: D-T7a-3 … D-T7a-7 come proposte, D-T7a-1 come proposta, D-T7a-2 nella forma nuova qui sotto. Su D-T7a-1 e D-T7a-2 Tid ha chiesto chi
ha ragione, la guida o la correzione. La risposta l'ha data la storia delle decisioni:

* **D-T7a-1: la guida fotografa il codice, non registra una decisione.** I due montaggi `AFTER INSERT OR UPDATE`
  nascono il 2025-12-21 (`a860ccc7d8`, i primi indirizzi del soggetto). `brief-db-fornitore-privato-indirizzi`
  (2026-11-16) li ha lasciati com'erano («nessun DDL sui montaggi»), e la frase di R9 «non si modifica più» l'ha
  scritta il giro 0c (2026-11-22) leggendo il corpo. Nessuno ha mai scelto che il blocco scatti su qualunque
  colonna. La proposta resta, e non revoca nessuna decisione. È però una **garanzia ritirata**, e il giro avrà la sua
  sezione: oggi la garanzia è solo apparente, perché un titolare che nessuno riscrive resta incompleto lo stesso.
* **D-T7a-2: la guida ha ragione, e la proposta si ritira.** R7 registra la **D4 di Tid del 2026-10-25**
  ([brief-db-unicita-civico-indirizzi-dettaglio](../work-done/2026/brief-db-unicita-civico-indirizzi-dettaglio.md)
  §D4): su una via che non si risolve si dà un errore. Quel brief ha anche trovato che
  `config.trgfn_comuni_protect_update` blocca il cambio di provincia di un comune che lo stradario usa. Quindi una
  via non perde la provincia dopo che ha dei civici, e S16 (il civico che sparisce dalla vista) non si produce con le
  scritture che passano dai trigger. Resta il solo difetto vero di S50: il codice arriva dal «trova o crea», mentre
  un INSERT diretto, o la modifica di un civico, danno il `23502`. **Proposta nuova:** il controllo «via non risolta»
  va nel guard del civico (`trgfn_indirizzi_dettaglio_guard_chiave`), su ogni strada, con lo stesso codice
  `E_INDIRIZZO_VIA_NON_RISOLTA`. `vw_indirizzi_dettaglio` non cambia, e S16 seconda metà si chiude come «non si
  costruisce senza saltare i trigger». Argomento sul modello: lo stradario è il catalogo italiano (gli indirizzi
  esteri usano la forma libera estera), e un indirizzo italiano senza la sigla della provincia non è completo per i
  documenti.

S3, S19, S49 (tipo per id), il `tx_id` di S48 e S-T7a-a sono correzioni senza scelta: entrano nel giro qualunque
cosa decida Tid sul resto.

### 21.3 Il piano del giro, dopo le decisioni

* **pgTAP rosso prima**, uno per caso costruito, come app dove si può:
  * l'indirizzo libero di catalogo in un comune con due vie e due CAP (S3);
  * il comune senza provincia: il civico, la vista e l'indirizzo (S16, S50);
  * l'elemento vuoto (S50);
  * la posizione del civico che cambia (S50);
  * la matrice che diventa obbligatoria su un titolare che esiste, che poi si scrive su un'altra colonna e da cui si
    cancella un indirizzo non richiesto (S48);
  * il ripiego vietato dalla natura e il ripiego nell'elenco (S48);
  * id inesistente, non numerico, e id e codice discordi (S49);
  * il comune e lo stato cancellati sotto un indirizzo di ruolo (S19);
  * la via ritrovata due volte, senza versioni nuove (S-T7a-a).
* **Le letture da fare prima di scrivere**: `linee-guida-trigger.md` per intero; di `linee-guida-sql` le §5, 5c, 5f,
  5g, 6, 7f e 11.5, e la §8.7 per la FK tolta.
* **Ricadute sul BE**, da scrivere in un passaggio solo:
  * i codici nuovi, e `E_INDIRIZZO_VIA_NON_RISOLTA` obsoleto se D-T7a-2 è sì;
  * il cambio di forma della risposta su un elemento vuoto;
  * il censimento dei lettori che contano sul blocco di R9, se D-T7a-1 è sì: è una garanzia ritirata
    (§«Garanzie ritirate» di AGENTS), e la richiesta al BE va scritta in quella forma.

### 21.4 Il pgTAP rosso (2026-11-24, prima dei changeSet)

Due file nuovi in `db/pgtap/anagrafiche/`, scritti per girare come app. Si costruiscono il mondo: comune, CAP, vie,
stato, tipi d'indirizzo e righe di matrice nascono nel test (le tabelle di `config` hanno id identity e l'app le
scrive). Dal seed si leggono solo una provincia, una toponomastica, la natura `PR` e il tipo di ruolo `CL` dei builder.

| File | Esito senza il giro | I verdi, e perché sono verdi |
| --- | --- | --- |
| `test-indirizzi-viste-forma-e-vincoli-v1` (25) | 20 rossi | 10 (il «trova o crea» dà già il codice), 11 (la premessa di S16), 16 (la vista legge già il civico per primo), 20 (il solo codice), 23 (la seconda chiamata passa già): sono controlli |
| `test-indirizzi-obbligatori-requisito-nuovo-v1` (11) | 8 rossi | 5 (l'unico indirizzo obbligatorio non si cancella), 10 e 11 (la copia scrive il ripiego e copia il tipo il cui ripiego è vietato): sono controlli |

Corsa: `scripts/prova_changeset.py` sullo scratch, da owner e in `ROLLBACK`. Il changeSet `20261123-68`, già
applicato e idempotente, fa solo da veicolo: le corse con e senza sono uguali, e sono lo stato di oggi. Il verde
della corsa come app è di Tid, dopo l'apply.

**Ogni rosso è sul suo motivo**, letto asserzione per asserzione:
* S3: due righe per l'indirizzo, coi CAP `T7A1…` e `T7A2…`;
* S50: `23502` sull'INSERT diretto del civico, sull'elemento vuoto, su quello col solo tipo e sulla via senza
  toponomastica; la posizione copiata nella riga;
* S49: il `22P02` sull'id non numerico; id e codice discordi passano, e scrivono il tipo dell'id;
* S19: i tre `confdeltype = n` (`SET NULL`);
* S-T7a-a: la via riscritta (il `ctid` cambia) e **due** versioni di storico per una sola chiamata, la versione
  iniziale e quella finale;
* D-T7a-1: `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` sulla scrittura del soggetto e sulla cancellazione di un
  indirizzo non chiesto; `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` sulle stesse due strade del ruolo;
* D-T7a-4: il ripiego vietato proposto (l'id di `tf`), la copia del tipo con il ripiego già nell'elenco, e le sette
  sedi elencate per nome.

**Due correzioni all'analisi di §21.1, trovate dalla prova:**
* **S49, l'id che non esiste.** Non lo rifiuta la FK: lo rifiuta prima il guard del tipo, con
  `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO`, perché un tipo che non c'è non è nella matrice. L'errore è quindi un
  motivo sbagliato («la natura non lo ammette»), non un errore tecnico. La correzione non cambia.
* **S19, lo stato cancellato.** Con lo stato proposto di oggi (l'Italia, col catalogo) il `SET NULL` non cambia paese
  in silenzio. `trgfn_indirizzi_base_normalize` scrive l'Italia, il guard della forma chiede il comune, e la
  cancellazione è rifiutata con `E_INDIRIZZO_LIBERO_INCOMPLETO`, un errore che parla dell'indirizzo. Il cambio
  silenzioso avviene quando lo stato proposto ammette la forma della riga, cioè un proposto senza catalogo, che il
  parametro consente. La correzione non cambia.

**Le scelte fatte scrivendo** (da confermare col changeSet): due codici nuovi, `DATO_ERRATO`, entrambi col campo nel
contesto. `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` è la via nuova a cui manca la toponomastica, la descrizione, il comune o
il CAP (D-T7a-5). `E_TIPO_INDIRIZZO_DISCORDE` è il caso in cui id e codice dicono due tipi (S49).

**I pgTAP esistenti che il giro tocca**, da adeguare con i changeSet:
* `create-gestore-indirizzo-res-domfisc.sql` chiama `fn_search_indirizzi_dettaglio` (righe 191-222): esce
  l'asserzione, o la ritrova con `fn_get_or_create_indirizzo_dettaglio`;
* `test-check-tipo-indirizzo-v1`, `test-fornitore-privato-indirizzi-v1`: `fn_tipo_indirizzo_ammesso_per_ruolo` cambia
  firma;
* `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1`, asserzione 3, legge gli eventi dei constraint trigger;
  `create-cliente.sql` e `test-indirizzo-obbligatorio-mancante-frase-v1` nominano i guard dei titolari;
* `test-indirizzi-singolare-e-plurale-v1`: `fn_indirizzi_con_obbligatori` cambia firma;
* sei file nominano `tipi_ruolo_tipi_indirizzo.tipo_ruolo_id` (`test-fn-crea-fornitore-v1`,
  `test-tipi-indirizzo-proponibili-v1`, `test-check-tipo-indirizzo-v1`, `test-fn-crea-indirizzi-ruolo-v1`,
  `test-fornitore-privato-indirizzi-v1`, `test-indirizzo-obbligatorio-mancante-frase-v1`): si rileggono per i cast.

### 21.5 Che cosa è scritto (2026-11-24: provato sullo scratch, applicato, pgTAP verdi come app)

| ChangeSet | Che cosa | Decisione |
| --- | --- | --- |
| `00_schema/config/20261123-74-alter-tipi-ruolo-tipi-indirizzo-tipo-ruolo-integer` | la catena `BEGIN ATOMIC` tolta, la FK doppia tolta, `tipo_ruolo_id` integer | D-T7a-7 |
| `00_schema/anagrafiche/20261123-75-update-fk-indirizzi-geografiche-senza-azione` | le tre FK di `indirizzi` senza `SET NULL` | S19 |
| `20_code/anagrafiche/20261123-76-recreate-catena-tipo-indirizzo-ruolo-tipo-integer` | le sette funzioni della catena, coi corpi di prima | D-T7a-7 |
| `20_code/anagrafiche/20261123-77-create-fn-tipo-indirizzo-obbligatorio-per-natura` | la sede unica di «obbligatorio per la natura» | D-T7a-4 |
| `-78` `fn_indirizzi_obbligatori_mancanti_soggetto` | la sede, e il ripiego solo se la natura lo ammette | D-T7a-4 |
| `-79` i picker `fn_tipi_indirizzo_proponibili_natura` e `_soggetto` | la colonna obbligatorio dalla sede | D-T7a-4 |
| `-80` `fn_crea_indirizzi_soggetto`, `-81` `fn_crea_indirizzi_ruolo` | si copiano solo gli obbligatori che mancano, non un tipo il cui ripiego c'è già | D-T7a-4 |
| `20_code/dbops/-82`, `-83` i builder pgTAP PF e PG; `-84` `fn_provisiona_dati_di_sviluppo` | la sede, con la finestra di validità | D-T7a-4 |
| `-85` i due guard degli obbligatori e i due trigger degli indirizzi | il tipo che esce, in coda (`DEFAULT NULL`); `OLD.tx_id` al log | D-T7a-1, S48 |
| `-86` i trigger dei titolari | soggetto all'`INSERT` e al cambio di natura (`WHEN`), ruolo all'`INSERT` | D-T7a-1 |
| `-87` `trgfn_indirizzi_dettaglio_guard_chiave` | `E_INDIRIZZO_VIA_NON_RISOLTA` su ogni strada | D-T7a-2 |
| `-88` `fn_indirizzo_elemento` | il tipo per id verificato; id e codice discordi `E_TIPO_INDIRIZZO_DISCORDE` | S49 |
| `-89` `fn_indirizzo_elemento_dettaglio` | senza chiavi di una via l'elemento è libero | D-T7a-5 |
| `-90` `fn_create_indirizzo` | la via nuova validata (`E_INDIRIZZO_VIA_NUOVA_INCOMPLETA`); la via esistente ritrovata senza riscriverla; firma ri-ancorata con `%TYPE` | D-T7a-5, S-T7a-a |
| `-91` `vw_indirizzi_resolved_base` | senza il join per via: una riga, col CAP scelto | S3 |
| `-92` ritiro di `fn_search_indirizzi_dettaglio` | | D-T7a-6 |
| `-93` ritiro di `trgfn_indirizzi_sync_geoloc` e dei suoi montaggi | | D-T7a-3 |
| `80_data/changelog/20261123-94-bonifica-indirizzi-geoloc-col-dettaglio` | la posizione copiata tolta dalle righe col dettaglio, a trigger sospesi | D-T7a-3 |

Con due righe nuove in `codici_errore.csv` e `messaggi_errore.csv` (id 1537, 1538) e la nota di
`E_INDIRIZZO_VIA_NON_RISOLTA` aggiornata.

**Le scelte fatte scrivendo:**
* il `CHECK` di rete «col dettaglio, niente posizione» non c'è. Su un database esistente partirebbe prima che -93
  tolga la copia, e la regola la tiene già `trgfn_indirizzi_base_normalize`. La prova è il pgTAP (15);
* in -90 `descrizione_breve` (varchar 50) prende i primi 50 caratteri della descrizione: prima la prendeva intera, e
  una via nuova dal nome lungo cadeva su un `22001`;
* ⚠️ -74 toglie le funzioni con le firme a tipi nudi. È applicato su dbdev dalle 19:14, e ancorarlo ora ne
  cambierebbe il checksum. Le firme sono quelle esatte del catalogo: resta così.

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, i 21 changeSet insieme, da owner):
* `test-indirizzi-viste-forma-e-vincoli-v1`: 25/25 (senza: 5); `test-indirizzi-obbligatori-requisito-nuovo-v1`:
  11/11 (senza: 3);
* i 96 file che nominano gli oggetti del giro, più `dbops/test-riferimenti-morti-v1`, in due corse (la prima si è
  fermata su `script/test-fn-disdetta-cliente`): uguali prima e dopo, salvo i cinque adeguati qui sotto, ora verdi;
* `script/test-catalogo-messaggi-errore-completo` (2) è rosso nella prova, perché i due codici nuovi stanno nei CSV,
  che la prova non carica. Si rilegge dopo l'apply;
* non provati dallo strumento: `test-soggetti-indirizzi-required` e `test-soggetti-ruoli-indirizzi-required` (più
  transazioni nello stesso file) e `script/test-fn-disdetta-cliente` (non apre con `BEGIN;`, un difetto suo). I
  primi due provano l'`INSERT`, che resta giudicato. La corsa come app è di Tid.

**I pgTAP adeguati** (scritti sul contratto di prima):
* `test-fornitore-privato-indirizzi-v1` (2) e `test-check-tipo-indirizzo-v1` (4): le plurali leggono le sedi (il
  requisito, i mancanti), non più il building block per riga;
* `test-indirizzi-obbligatori-mancanti-v1` e `test-indirizzi-obbligatori-ripiego-e-cancellazione-v1`: la firma a tre
  argomenti dei guard;
* `test-indirizzo-obbligatorio-mancante-frase-v1`: chiamava il guard con un `UPDATE` che riscriveva lo stesso valore,
  cioè il comportamento che D-T7a-1 ritira. Ora chiama il guard, la sede della frase;
* `create-gestore-indirizzo-res-domfisc`: il civico si ritrova col «trova o crea» e dalla vista della ricerca.

**Guide verificate dopo il giro** (`scripts/guide_coinvolte.py` sui file del giro, 2026-11-24):
* aggiornate nello stesso giro: [gestione-degli-indirizzi](../../guide/gestione-degli-indirizzi.md) (R3, R7, R8, R9,
  la tabella dei trigger, i test), le note `_indirizzi-obbligatori` (le strade, il ripiego del soggetto, la sede
  della natura) e `_indirizzo-libero-o-dettaglio` (la posizione, la forma dell'elemento, la via non risolta);
* **coerenti**: [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) (al COMMIT si giudicano
  gli obbligatori del soggetto nato, che resta vero), le note `_cambio-di-natura` (il cambio di natura resta
  giudicato) e `_tipo-indirizzo-ammesso` (il modello su cui D-T7a-1 si allinea);
* le altre 33 nominano oggetti che il giro cita solo nei corpi ricopiati (provisioning, builder): nessun
  comportamento che descrivono cambia.

**La documentazione** (2026-11-24): 25 pagine `manual/` aggiornate, una nuova
(`fn_tipo_indirizzo_obbligatorio_per_natura`), due tolte (`fn_search_indirizzi_dettaglio`,
`trgfn_indirizzi_sync_geoloc`). La doc auto-generata è rigenerata da Tid dopo l'apply (2026-11-24): le schede
delle due funzioni tolte non ci sono più, e c'è quella della funzione nuova. Restano fuori standard, toccate al minimo, `script/manual/fn_search_stradario` e
`config/manual/tipi_ruolo_tipi_indirizzo` (pagine vecchio stile): sono del giro dei metadati (§8).

### 21.6 Garanzie ritirate

| Oggetto | La proprietà che i lettori davano per scontata | I lettori lato DB |
| --- | --- | --- |
| I trigger dei titolari (-86) | «Un titolare scritto ha i suoi indirizzi obbligatori» | `script.fn_snapshot_indirizzo` e `_soggetto` ricevono l'id dell'indirizzo e rifiutano da sé quello che manca: non ne dipendono. `script.fn_get_search_detail` ha il suo ripiego (`COALESCE`): non ne dipende. Il test della frase ne dipendeva, ed è adeguato (§21.5). La proprietà non valeva nemmeno prima per un titolare nato prima della riga e mai riscritto |
| `trgfn_indirizzi_sync_geoloc` (-93) | «Una riga col dettaglio ha in `geoloc` la posizione del civico» | nessun lettore legge la colonna: `vw_indirizzi_resolved_base` e da lei `script.fn_get_indirizzo` e `_by_ruolo` leggono il civico per primo, e il ripiego sulla riga resta per la forma libera |

### 21.7 Il passaggio al BE (da girare: il giro è applicato, 2026-11-24)

Letto sul ramo `origin/dev/backend-tid` in sola lettura. Chi cambia per primo: il DB. Nessuna voce rompe ciò che il BE
fa oggi, salvo dove è detto.

1. **Censire i lettori di `anagrafiche.soggetti` e `anagrafiche.soggetti_ruoli` che contano su «un titolare scritto
   ha i suoi indirizzi obbligatori»** (§21.6). Da oggi un titolare a cui una riga di matrice nata dopo chiede un
   indirizzo resta scrivibile, e il rifiuto `E_INDIRIZZO_OBBLIGATORIO_MANCANTE*` arriva solo alla nascita, al
   cambio di natura e quando esce l'unico indirizzo che una riga chiedeva. Il form può mostrare i mancanti da
   `fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`, che il BE legge già per il cambio di natura.
2. **Codici nuovi**, col campo nel contesto: `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` (campo `toponomastica_id`,
   `descrizione_via`, `comune_id` o `codice_postale_id`) e `E_TIPO_INDIRIZZO_DISCORDE` (campo
   `tipo_indirizzo_codice_interno`). `E_TIPO_INDIRIZZO_NON_TROVATO` può arrivare ora anche col campo
   `tipo_indirizzo_id`.
3. **`anagrafiche.fn_create_indirizzo`** (`backend/apps/anagrafiche/db/indirizzi_repository.py`, riga 191) valida la
   via nuova da sé. Il «controllo preventivo del service», se c'è, è ora una seconda sede della stessa regola: si
   può togliere. Censire i pre-check della via nuova nel service.
4. **Un elemento d'indirizzo senza via e senza testo** ora arriva come `E_INDIRIZZO_LIBERO_INCOMPLETO` sul campo
   `indirizzo_libero`, non più come errore tecnico.
5. **`anagrafiche.fn_search_indirizzi_dettaglio` non c'è più**. Il BE non la chiama: niente da cambiare.
6. **La colonna `geoloc`** di `indirizzi` e `indirizzi_soggetti` è `NULL` per un indirizzo col dettaglio. Il BE non la
   legge (nessun `geoloc` in `backend/` né in `frontend/src`): niente da cambiare.

**Esito del passaggio (sessione BE/FE, `dev/backend-tid`, 2026-11-26; da committare).**

* **1** censita: nel BE i mancanti li leggono solo `soggetti_repository` e `soggetti_service`, per il cambio di
  natura. Nessun lettore dà per scontato che un titolare scritto abbia i suoi indirizzi obbligatori. Il
  censimento è fatto per nome (`fn_indirizzi_obbligatori_mancanti*`, `indirizzi_obbligatori`).
* **2** e **4**: i codici sono già dichiarati, con policy e ripiego; nessun pre-check del BE li anticipava.
* **3** fatta: `richiedi_via` di `geo_service` era la seconda sede della via nuova, senza il campo. Decideva anche
  «via nuova» dove il DB decide «indirizzo libero» (un elemento senza via e senza testo). Ora è
  `richiedi_id_via_positivi` e tiene il solo contratto degli id: `stradario_id`, `toponomastica_id`, `comune_id` e
  `codice_postale_id`, se ci sono, sono interi positivi, perché un id ≤ 0 arriverebbe al DB come FK violata (ok Tid,
  2026-11-26). Lo chiamano `crea_dettaglio_indirizzo` e `indirizzo_per_madre`. Il catalogo BB è aggiornato, l'indice
  rigenerato. Presidio nuovo sul DB vero: `test_indirizzo_via_nuova_db` (il campo che manca, uno per volta).
* **5** e **6**: niente da cambiare.
* Verifica (`/verifica`, 2026-11-26): erano rimasti alla regola di prima i manuali
  `anagrafiche/manual/api_indirizzi.md` (errori del POST: la via nuova incompleta come `E_ANAG_VALIDAZIONE`) e
  `api_indirizzi_ruolo.md` (errori e nota sulla forma: «senza libero né dettaglio vale la via da risolvere», dove il DB
  decide «libero»), e il commento di `GeoService.create_indirizzo`. Allineati. **Guide verificate**:
  `gestione-degli-indirizzi` R3 **coerente** col codice.
* Rosso già presente, che il giro non tocca: `test_creazioni_dalle_madri_db.test_gli_obbligatori_copiati_dal_primo`
  (`FATT` non copiato) è rosso anche su HEAD `7a61ed514`, provato in un worktree separato il 2026-11-26. Da
  vagliare lato DB: la copia degli obbligatori della madre plurale.

## 22. Giro 5 — T7b, i contatti e il catasto (2026-11-25: decisioni prese, scritto e provato sullo scratch)

Il perimetro è S8, S46, S11, S47 e il pgTAP `create-soggetto-gestori.sql` (§21, testa). **Il confine con T6** è
quello proposto e accettato da Tid il 2026-11-25: T7b tiene la regola del contatto predefinito e la lettura;
restano a T6 il contatto obbligatorio (`trgfn_soggetti_guard_soggetto_contatti`, «almeno un contatto», S45 e la
riga di S8 che lo nomina), il puntatore `soggetti.default_contatto_id` (che non si svuota mai e che a ogni scrittura
riscrive il soggetto) e l'ultimo contatto cancellato. I numeri dei changeSet partono da `20261125-36` (Tid,
2026-11-25). Analisi letta sul catalogo di dbdev il 2026-11-25; sul ramo `origin/dev/backend-tid` si è guardato
solo chi chiama, in sola lettura.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 15 oggetti, 2026-11-25; nessun orfano):

| Guida o nota | Esito |
| --- | --- |
| [gestione-dei-contatti](../../guide/gestione-dei-contatti.md) | **contraddetta su tre punti**, decide Tid: «la chiave è il soggetto più il contesto» (D-T7b-1), «che cosa la regola non fa» (D-T7b-2), il contatto con l'istanza senza ruolo ammesso (D-T7b-3). **Indietro** su `fn_get_contatti` senza reparto (D-T7b-4) e sull'ordine di `fn_get_contatto_default` fra tipi diversi |
| nota `_contatto-predefinito` | **contraddetta** con D-T7b-1 e D-T7b-2: è la stessa regola della guida, scritta dal giro 0c leggendo il corpo |
| [catasto-delle-istanze](../../guide/catasto-delle-istanze.md) | **contraddetta** nel §«Che cosa oggi non copre» (S11, D-T7b-6, D-T7b-7): li descrive come limiti, non come scelte. **Coerente** sull'idempotenza del clone, che il brief vicino della catena tiene (§22.1, S47) |
| [generazione-cliente](../../guide/generazione-cliente.md), [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md) | **coerenti**: nominano il clone al subentro e il legame istanza-unità, che il giro non cambia nella sostanza; da rileggere a giro fatto per il trigger su INSERT (D-T7b-6) |
| [gestione-degli-indirizzi](../../guide/gestione-degli-indirizzi.md), [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md), [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | **coerenti**: nominano `contatti` o `istanze_utilities` per altro (la nascita del primo contatto, il luogo dell'istanza) |

**La storia delle decisioni.** La chiave «soggetto più contesto» del predefinito nasce il 2025-06-23 (`748ee6b95c`,
«Fix Function per aggiunta contatti context»), senza un brief. Il refactor del 2026-03-25
([refactor-istanza-indirizzi-conti-contatti](../work-done/2026/refactor-istanza-indirizzi-conti-contatti.md) §7) ha
solo rinominato il contesto `utility` in `istanza`. Lo stesso refactor, per il **conto bancario** predefinito, ha
scritto la chiave «ruolo, istanza, uso» con due indici unici parziali. Le frasi della guida e della nota sono del
giro 0c (2026-11-22), lette sul corpo. **Nessuno ha mai scelto che due ruoli condividano un predefinito**: come per
D-T7a-1, la guida fotografa il codice. Il catasto nasce il 2025-12-16 (`1b18c56b64`); «un'istanza, un'unità» è il
modello dichiarato dalla guida, e nessun vincolo lo scrive. Sul clone e sulla catena c'è il §4 di
[brief-db-catena-istanze-pdp](brief-db-catena-istanze-pdp.md) (aperto, cinque decisioni di Tid): un'istanza che ha già
l'unità la tiene anche se il padre cambia, «sullo stesso PDP l'immobile è lo stesso».

### 22.1 Che cosa dice il catalogo, segnalazione per segnalazione

| # | Esito | Che cosa dice il catalogo |
| --- | --- | --- |
| S8 (la chiave) | **cambio di modello** | `trgfn_contatti_set_default_contatto` toglie il segno a ogni altro predefinito con lo stesso `soggetto_id` e lo stesso `default_context`. Il cliente e il fornitore dello stesso soggetto condividono un predefinito: il primo contatto del fornitore non nasce predefinito, perché il contesto `ruolo` ne ha già uno (quello del cliente), e marcare il contatto del fornitore toglie il segno a quello del cliente. Il lettore vero ne dipende: `PortaleRepository.get_email_contatto_suggerita` (BE) sceglie fra i contatti del ruolo «il principale, poi quello `is_default`». La cascata di `fn_get_contatti` è per ruolo, il conto bancario predefinito è per ruolo e istanza. D-T7b-1 |
| S8 (nessun vincolo) | **difetto** | La regola «al più un predefinito» sta solo nel trigger: nessun indice unico la scrive. Due contatti nati insieme in due transazioni in un contesto vuoto contano zero predefiniti tutti e due, e nascono predefiniti tutti e due. Va con D-T7b-1, che dice su quale chiave |
| S8 (il segno tolto) | **difetto: dipende da una scrittura incidentale** | Il ramo «nessun predefinito nel contesto» scatta anche su UPDATE. Togliere il segno all'unico predefinito lo lascia senza; la prossima modifica di **qualunque** contatto del contesto (anche una correzione del telefono) lo fa tornare predefinito, scelto da quale contatto si è scritto per primo. Cancellare il predefinito non promuove nessuno. È la regola di `linee-guida-trigger` §«La fase» a dire la forma: un default che propone un valore mancante vale all'INSERT, e in modifica un valore tolto si rifiuta, non si rimpiazza. D-T7b-2 |
| S8 (istanza senza ruolo) | **difetto di modello** | Un contatto con l'istanza e senza il ruolo è ammesso, e nessuno dei tre indici unici lo copre. In `fn_get_contatti`, chiesto un ruolo, il suo livello è il 3, come un contatto del soggetto. Il BE crea i contatti d'istanza solo dal ruolo (`create_contatto_ruolo`): la forma la produce solo una scrittura diretta. L'istanza non ha un ruolo suo (`istanze_utilities` porta il soggetto). D-T7b-3 |
| S8 (`fn_get_contatti` senza reparto) | **difetto** | Il filtro `c.unita_organizzativa_id IS NULL OR … IS NOT DISTINCT FROM p_unita_organizzativa_id` con il parametro `NULL` scarta ogni contatto che ha un reparto. Il reparto è facoltativo e dice dove sta il referente: un soggetto il cui solo contatto amministrativo è nel reparto «amministrazione» non ha contatti per chi non chiede il reparto (il portale non lo chiede). D-T7b-4 |
| S8 (`fn_get_contatto_default` fra tipi) | **difetto** | Fra i candidati (uno per tipo) possono esserci più predefiniti, di contesti diversi: oggi vince l'id più basso, cioè l'ordine di nascita e non il contesto. Il più specifico (istanza, poi ruolo, poi soggetto) è la stessa regola della cascata. Correzione senza scelta |
| S46 (il doppione) | **difetto** | Il secondo contatto dello stesso tipo nello stesso contesto arriva dal verbo come `23505` grezzo. Il BE lo traduce per nome del vincolo (`VINCOLI_CONTATTO`, `create_with_constraint_mapping`), su creazione e modifica; le madri del DB che chiamano il verbo (`fn_crea_cliente`, `fn_crea_fornitore`, `fn_crea_soggetto_pf`/`_pg`, `fn_crea_utente_tecnico`) no. Il precedente è del giro 3 (S4): il verbo traduce la violazione del **suo** indice, per nome, in un codice col campo. D-T7b-5 |
| S46 (il tipo) | **difetto** | `(v_campi ->> 'tipo_contatto_id')::integer` dà il `22P02` del cast con un tipo non numerico; un tipo che non esiste arriva come `23503` della FK. Sono i casi di S49 per il tipo d'indirizzo (giro 4, `E_TIPO_INDIRIZZO_NON_TROVATO`). Correzione senza scelta: il non numerico è `E_CONTATTO_INCOMPLETO` sul campo, l'inesistente un codice nuovo sul campo |
| S46 (`default_context`) | **difetto** | È fra le chiavi ammesse, e il trigger lo sostituisce sempre. Nessun chiamante lo passa (né il DB né il BE): esce dall'elenco, e chi lo passa ha `E_CAMPO_NON_AMMESSO` |
| S11 | **difetto** | Nessun vincolo unico su `istanze_utilities.catasto_unita_immobiliare_id`: un'istanza agganciata a mano all'unità di un'altra la condivide, contro il modello che la guida dichiara («mai condivisa»). La colonna non ha nemmeno un indice. Si chiude con un indice unico (i `NULL` restano liberi: un'istanza senza unità è ammessa). Correzione senza scelta |
| S47 (INSERT con la precedente) | **difetto** | `trg_iu_z50_clone_catasto_from_parent_aft_upd` è solo `AFTER UPDATE OF parent_istanza_id`: un'istanza che nasce con la precedente già scritta non riceve il clone. La colonna è scrivibile all'INSERT. D-T7b-6 |
| S47 (la scrittura incidentale) | **difetto: dipende da una scrittura incidentale** | `UPDATE OF` scatta anche a valore uguale (`linee-guida-trigger` §«Che cosa fa davvero `UPDATE OF`»), e il ramo delle istanze fittizie di `trgfn_clienti_set_parent_istanza` riscrive `parent_istanza_id` senza confronto. Un'unità comparsa sulla precedente dopo il subentro arriva quindi alla prossima scrittura del cliente fittizio, e non arriva mai per un PDP. D-T7b-6 |
| S47 (la catena che cambia dopo il clone) | **coerente col brief vicino** | L'istanza che ha già l'unità la tiene: è il §4 di `brief-db-catena-istanze-pdp`, che lo motiva sul modello. Si scrive nella guida come scelta, non come limite. Se quel brief decide diversamente, cambia lì |
| S47 (la ponte non si pulisce) | **difetto** | `trgfn_iu_sync_catasto_unita_indirizzo` aggiunge la coppia (unità, civico) a ogni cambio dell'una o dell'altro e non toglie la vecchia. La coppia lasciata tiene acceso il guard ATTIVO del civico, che non si spegne più. La ponte è scrivibile dall'app (`INSERT`, `UPDATE`, `DELETE`): il modello ammette coppie scritte a mano, molti a molti. D-T7b-7 |
| S47 (l'unità orfana) | **difetto** | Un'istanza che passa a un'altra unità lascia la prima senza nessuno che la nomini: nessuna FK vi arriva da altrove, e la si raggiunge solo dallo storico. Con S11 un'unità è di una istanza sola. D-T7b-7 |
| `create-soggetto-gestori.sql` | **da diagnosticare con la prova** | È nelle due baseline come `ASSERZIONE`. Il giro 0d ha letto che il test 4 accetta qualunque `P0001`, mentre il guard solleva `E_GESTORE_SINGLETON_VIOLATO`: va asserito il codice (`throws_like` o il controllo del codice). Quale asserzione è rossa oggi, e se lo è ancora dopo il giro 4 che ha toccato gli indirizzi obbligatori, lo dice la prima prova sullo scratch (`prova_changeset.py --pgtap`) |

**Fatti datati, non motivi** (dbdev, 2026-11-25): nessun contatto con l'istanza e senza ruolo; sei soggetti con un
predefinito di contesto `ruolo`; nessun soggetto con contatti su due ruoli diversi; nessuna unità catastale nominata
da due istanze. Servono a sapere se la migrazione ha righe da sistemare, non a decidere la regola.

### 22.2 Le decisioni (Tid, 2026-11-25: tutte come proposte)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-T7b-1 | **Di che cosa è predefinito un contatto?** Oggi del soggetto più il contesto: due ruoli dello stesso soggetto ne condividono uno | **Della riga di contesto**: soggetto, ruolo e istanza, come il conto bancario predefinito. Un indice unico parziale `NULLS NOT DISTINCT (soggetto_id, soggetto_ruolo_id, istanza_utility_id) WHERE is_default` scrive la regola, e il trigger la segue. `default_context` resta, come etichetta del livello. Le righe di oggi: in ogni contesto con contatti e senza predefinito diventa predefinito il primo nato, che è la regola della nascita applicata all'indietro. Si riscrivono guida e nota |
| D-T7b-2 | **Il segno tolto e il predefinito cancellato** | **Un contesto con contatti ha sempre il suo predefinito, e chi lo cambia lo dice.** Il primo nasce predefinito (solo all'INSERT); si cambia marcando un altro. Togliere il segno all'unico predefinito è rifiutato (codice nuovo, campo `is_default`); cancellare il predefinito di un contesto che ha altri contatti è rifiutato (codice nuovo: «marca prima un altro»); cancellare l'ultimo contatto del contesto passa. Nessuna promozione automatica, che sceglierebbe per id. ⚠️ **Ricaduta BE**: oggi il BE non scrive `is_default` (né in creazione né in `CONTATTO_UPDATE_COLS`), quindi l'operatore non potrebbe cancellare un predefinito che ha accanto altri contatti. Il BE deve esporre «rendi predefinito». In alternativa (b): cancellare il predefinito lascia il contesto senza, e il primo contatto che nasce dopo lo diventa; il segno tolto lascia il contesto senza, e nessuna modifica lo rimette |
| D-T7b-3 | **Un contatto d'istanza senza ruolo** | **Non si scrive**: `CHECK (istanza_utility_id IS NULL OR soggetto_ruolo_id IS NOT NULL)`. Il contatto d'istanza è il referente di quel ruolo per quell'istanza; i tre indici unici e la cascata coprono così ogni forma. L'alternativa è un quarto indice e un livello suo nella cascata, per un referente dell'istanza «in qualunque ruolo» |
| D-T7b-4 | **`fn_get_contatti` senza reparto** | Senza reparto contano **tutti** i contatti; col reparto contano quelli del reparto e quelli senza, e vince il reparto, come oggi. Il portale e ogni lettore che non chiede il reparto trovano così il referente che oggi sparisce |
| D-T7b-5 | **Il doppione per tipo** | **Il verbo lo traduce**, come S4 al giro 3: `fn_crea_contatto` prende la violazione dei tre indici per nome (`GET STACKED DIAGNOSTICS`) e solleva un codice nuovo col campo `tipo_contatto_id` e il livello. La modifica diretta del BE resta tradotta dal BE (non è un verbo, e questo giro non ne scrive uno): per la creazione la traduzione del BE diventa una seconda sede e si può togliere |
| D-T7b-6 | **Quando si clona il catasto** | **Quando nasce il legame con la precedente**: `AFTER INSERT OR UPDATE`, `WHEN` con `OLD.parent_istanza_id IS DISTINCT FROM NEW.parent_istanza_id` (all'INSERT basta la precedente scritta), sempre con unità vuota e civico presente. Un'unità che compare dopo sulla precedente non arriva: il clone copia ciò che la precedente ha quando il legame nasce, e la rettifica dell'istanza nuova si fa su di lei. Si scrive nella guida come scelta |
| D-T7b-7 | **La ponte e l'unità lasciata** | (a) Quando l'istanza cambia civico o unità, la coppia (unità di prima, civico di prima) esce dalla ponte, se nessun'altra istanza ha la stessa coppia: è la coppia che l'istanza aveva portato, e con S11 l'unità era sua. Le coppie scritte a mano con altri civici restano. (b) Un'unità che nessuna istanza nomina più si cancella nello stesso momento: lo storico continuo di `catasto_unita_immobiliari` tiene la versione, la ponte la segue in cascata. L'alternativa a (b) è lasciarla e darle un lettore (le unità senza istanza), ma un'unità senza istanza non ha nessuno che la corregga |

S8 (`fn_get_contatto_default` fra tipi), S46 (il tipo, `default_context`) e S11 sono correzioni senza scelta: entrano
nel giro qualunque cosa decida Tid sul resto.

### 22.3 Il piano del giro, dopo le decisioni

* **pgTAP rosso prima**, come app dove si può, uno per caso costruito:
  * due ruoli dello stesso soggetto, ciascuno col suo primo contatto: tutti e due predefiniti; marcare il secondo
    contatto del fornitore non tocca il cliente (D-T7b-1);
  * il segno tolto all'unico predefinito, la modifica di un altro contatto dopo, la cancellazione del predefinito
    con un altro accanto e quella dell'ultimo (D-T7b-2);
  * il contatto d'istanza senza ruolo (D-T7b-3);
  * `fn_get_contatti` senza reparto con un solo contatto in un reparto (D-T7b-4);
  * `fn_get_contatto_default` con il predefinito del ruolo nato dopo quello del soggetto;
  * `fn_crea_contatto`: il doppione, il tipo non numerico, il tipo inesistente, `default_context` passato (S46);
  * due istanze sulla stessa unità (S11);
  * l'istanza che nasce con la precedente; la riscrittura della precedente uguale dopo un'unità comparsa (D-T7b-6);
  * il cambio di civico e quello di unità, la coppia e l'unità di prima, e lo spegnimento del civico di prima
    (D-T7b-7);
  * `create-soggetto-gestori.sql`: la prova dice che cosa è rosso; il test 4 asserisce il codice.
* **Le letture prima di scrivere**: `linee-guida-trigger.md` letta per intero il 2026-11-25; di `linee-guida-sql` le
  §5, 5d, 5f, 5g, 7f, 8.4, 8.4-bis e 11.5 (la ponte e `istanze_utilities` hanno trigger generati: niente DDL su di
  loro). Prima di toccare `trgfn_contatti_set_default_contatto` si cercano i suoi pgTAP (`test-contatti-soggetto-
  cliente`, `test-fn-crea-contatto-v1`, `soggetti-con-contatti`, `create-soggetto-bank-branches`,
  `test-istanza-dello-stesso-soggetto-v1`) e i seed di `80_data` che scrivono `contatti` (`20260107-12`, `-13`).
* **Forma**: il trigger del predefinito non ha fase nel nome (`trg_contatti_set_default_contatto_ins_upd`, T11). Se
  il giro lo rimonta, lo rimonta per funzione con la fase (`linee-guida-trigger` §«Il nome del trigger»), e la voce
  esce da T11.
* **Ricadute sul BE**, in un passaggio solo, a giro applicato:
  * «rendi predefinito» nel form dei contatti, se D-T7b-2 è la proposta; i due codici nuovi del predefinito;
  * il codice del doppione dalla creazione, e la traduzione per nome che si può togliere per la creazione;
  * i codici del tipo di contatto;
  * il cambio di forma di `fn_get_contatti` senza reparto, che il portale legge;
  * **garanzia ritirata**, se D-T7b-1 passa: «il contesto `ruolo` di un soggetto ha al più un predefinito» diventa
    «ogni ruolo ha il suo». La richiesta è nella forma di AGENTS: censire i lettori di `contatti.is_default` e
    `default_context` che contano su quella proprietà.

### 22.4 Che cosa è scritto (2026-11-25: provato sullo scratch, applicato, pgTAP verdi, doc rigenerata)

Le decisioni D-T7b-1 … -7 sono di Tid, 2026-11-25, tutte come proposte. Intervallo riservato `20261125-36 … -60`
(Tid): `-36 … -46` scritti; `-47 … -60` erano segnaposto vuoti, tolti a giro chiuso (§22.7).

| ChangeSet | Che cosa | Decisione |
| --- | --- | --- |
| `20_code/anagrafiche/20261125-36-create-trgfn-contatti-guard-predefinito` | il guard nuovo, `BEFORE UPDATE OR DELETE`, fase a10: il segno tolto `E_CONTATTO_PREDEFINITO_OBBLIGATORIO`, il predefinito cancellato o spostato con altri accanto `E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE` | D-T7b-2 |
| `-37` `trgfn_contatti_set_default_contatto` | il contesto è la terna (soggetto, ruolo, istanza); il segno lo propone solo chi entra nel contesto; rimontato per funzione come `trg_contatti_a20_set_default_contatto_ins_upd` (esce da T11) | D-T7b-1, D-T7b-2 |
| `20_code/script/-38` `fn_get_contatti` | senza reparto contano tutti i contatti | D-T7b-4 |
| `20_code/script/-39` `fn_get_contatto_default` | fra i predefiniti vince il contesto più specifico | S8, senza scelta |
| `-40` `fn_crea_contatto` | tipo non numerico `E_CONTATTO_INCOMPLETO`, inesistente `E_TIPO_CONTATTO_NON_TROVATO`, doppione `E_CONTATTO_TIPO_DUPLICATO` per nome del vincolo, `default_context` fuori dalle chiavi | D-T7b-5, S46 |
| `-41` `trgfn_iu_sync_catasto_unita_indirizzo` | la coppia di prima esce dalla ponte, l'unità che nessuno nomina si cancella | D-T7b-7 |
| `-42` i trigger del catasto su `istanze_utilities` | clone `_ins` e `_upd` (col `WHEN` sul cambio), ponte `_ins` e `_upd`; rimontati per funzione col nome della tabella intera | D-T7b-6, D-T7b-7 |
| `00_schema/anagrafiche/-43` | `COMMENT` di `is_default` e `default_context` (che nominava ancora `utility`) | D-T7b-1 |
| `80_data/changelog/-44` | un predefinito per riga di contesto (il primo marcato, o il primo nato), a trigger sospesi tranne audit e `tx_id` | D-T7b-1 |
| `90_end/-45` | `uq_contatti_predefinito_contesto` (`NULLS NOT DISTINCT`, `WHERE is_default`) e `chk_contatti_istanza_con_ruolo` | D-T7b-1, D-T7b-3 |
| `90_end/-46` | `uq_istanze_utilities_catasto_unita_immobiliare`, parziale sulle righe con l'unità | S11 |

Con quattro righe nuove in `codici_errore.csv` e `messaggi_errore.csv` (id 1540 … 1543).

**Le scelte fatte scrivendo:**
* il segno tolto dal trigger quando un altro contatto diventa predefinito passa dal guard perché lo scrive un
  trigger (`pg_trigger_depth() > 1`), come in `vendite.trgfn_doc_righe_lock_fuori_bozza`. La riga nuova non è
  ancora scritta quando il segno si toglie alla vecchia, e il guard vedrebbe il contesto restare senza. Lo stesso
  criterio lascia passare la cascata della cancellazione del soggetto;
* il cambio di contesto è un'entrata: il contatto spostato è predefinito se il contesto nuovo non ne ha, e il
  segno che porta da quello di prima non conta come richiesta. Dal contesto di prima esce come una cancellazione;
* `soggetti.default_contatto_id` si scrive quando un contatto diventa il predefinito del soggetto, non più a ogni
  scrittura del contatto. Il puntatore resta di T6, che non si svuota;
* la cancellazione dell'istanza non cancella la sua unità: D-T7b-7 parla del cambio di civico o di unità, e
  `istanze_utilities` ha sei FK in entrata; resta nel §22.7;
* l'indice del predefinito e il `CHECK` stanno in `90_end` (§11.14), dopo la bonifica di `80_data`. Una riga che il
  `CHECK` rifiuta, o due istanze sulla stessa unità, fermano il migrate col nome del vincolo: su dbdev non ce ne
  sono (fatti del 2026-11-25, §22.1).

**La prova** (`scripts/prova_changeset.py`, scratch `zeroerp_ruoli`, gli undici changeSet insieme, da owner):
* `test-contatto-predefinito-per-contesto-v1`: 19/20 (senza: 5). Il 16 asserisce la frase del codice nuovo, che
  sta nel CSV e la prova non carica. Dopo l'apply è verde (Tid, 2026-11-25);
* `test-catasto-unita-della-sua-istanza-v1`: 10/10 (senza: 2);
* i 60 file che nominano contatti, catasto, `is_default` o `default_context`: uguali prima e dopo. Non provato
  dallo strumento `test-soggetti-indirizzi-required` (quattro `BEGIN;`), che non tocca il predefinito;
* `create-soggetto-gestori.sql`, diagnosticato: il test 3 contava il gestore della macchina, e su un database
  ricostruito dai changelog `anagrafiche.gestori` è vuota. Il test 4 creava il «secondo» gestore, che era il primo,
  e passava. Ora il gestore lo prende o lo costruisce `dbops.fn_pgtap_crea_gestore`, e il test 4 asserisce
  `E_GESTORE_SINGLETON_VIOLATO`. 5/5 su scratch e su dbdev, in `ROLLBACK`; tolto dalle due baseline;
* `script/test-catalogo-messaggi-errore-completo`: verde dopo l'apply (Tid, 2026-11-25).

**Applicato** da Tid il 2026-11-25: pgTAP verdi, doc auto-generata rigenerata (c'è la scheda di
`trgfn_contatti_guard_predefinito`, e il suo link dalle guide non è più rotto).

**Guide verificate dopo il giro:**
* aggiornate nello stesso giro: [gestione-dei-contatti](../../guide/gestione-dei-contatti.md) (il contesto, la
  chiave, che cosa è rifiutato, la lettura, gli esempi), la nota `_contatto-predefinito` (riscritta),
  [catasto-delle-istanze](../../guide/catasto-delle-istanze.md) (l'indice, il clone quando nasce il legame, la ponte e
  l'unità al cambio; «Che cosa oggi non copre» tiene solo la cancellazione dell'istanza e la catena svuotata);
* indietro, aggiornata: [generazione-cliente](../../guide/generazione-cliente.md) (la tabella dei trigger
  dell'istanza, l'indice dell'unità);
* **coerenti**: [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md),
  [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) (rimanda ai contatti per il
  predefinito), [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) (il primo contatto dell'utente
  tecnico, del soggetto); le altre 16 di `guide_coinvolte.py` nominano solo `fn_log_and_raise_error`,
  `soggetti` o il `tx_id`;
* le pagine `manual/` degli oggetti del giro, e quella nuova di `trgfn_contatti_guard_predefinito`.

### 22.5 Garanzie ritirate

| Oggetto | La proprietà che i lettori davano per scontata | I lettori lato DB |
| --- | --- | --- |
| Il predefinito (-37, -45) | «Il livello `ruolo` (o `istanza`) di un soggetto ha al più un predefinito»: ora ogni ruolo, e ogni ruolo su un'istanza, ha il suo | `trgfn_soggetti_guard_soggetto_contatti` cerca «almeno un predefinito o un recapito»: con più predefiniti è solo più facile da soddisfare. `fn_get_contatti` e `fn_get_contatto_default` scelgono per contesto. I verbi che passano `is_default` (`fn_crea_soggetto_pf`, `_pg`, `script.fn_crea_utente_tecnico`) scrivono il contatto del soggetto, il cui contesto non cambia. Nessun lettore ne dipende |
| `fn_get_contatti` senza reparto (-38) | «Chi non chiede il reparto non vede i contatti che ne hanno uno» | `fn_get_contatto_default` la chiama col reparto che riceve. Nessun lettore DB ne dipendeva |

### 22.6 Il passaggio al BE (✅ fatto, 2026-11-26)

Letto sul ramo `origin/dev/backend-tid` in sola lettura. Chi cambia per primo: il DB. Il percorso censito: creazione
(`contatti_service.crea_contatto_validato`), modifica (`SoggettiRepository.update_contatto`, `CONTATTO_UPDATE_COLS`),
cancellazione (`views_contatti_ruolo.py` riga 165, `SoggettiRepository.delete_contatto`), lettura del portale
(`PortaleRepository.get_email_contatto_suggerita`), form `frontend/src/anagrafiche/components/ContattoForm.vue`.

1. **«Rendi predefinito».** Il BE oggi non scrive `is_default`: non è in `CONTATTO_UPDATE_COLS` né fra i campi della
   creazione. Da oggi il predefinito non si cancella finché nel suo contesto ci sono altri contatti
   (`E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE`), e il segno non si toglie (`E_CONTATTO_PREDEFINITO_OBBLIGATORIO`): senza
   un'azione che marca un contatto, l'operatore non può più cancellare un predefinito che ha accanto altri contatti.
   Serve l'azione «rendi predefinito», che scrive `is_default = true` sul contatto scelto: il vecchio perde il segno
   da solo. Il segno non si scrive mai a `false`.
2. **I due codici del predefinito**, campo `is_default`, sulla cancellazione e sulla modifica dei contatti, del
   soggetto e del ruolo.
3. **Il doppione dalla creazione** arriva come `E_CONTATTO_TIPO_DUPLICATO`, campo `tipo_contatto_id`, con il tipo e
   il livello nella frase. In `crea_contatto_validato` la traduzione per nome (`VINCOLI_CONTATTO`) è ora una seconda
   sede per la creazione: si può togliere lì. Resta per la modifica diretta, che non passa da un verbo.
4. **I codici del tipo**: un tipo non numerico è `E_CONTATTO_INCOMPLETO` sul campo `tipo_contatto_id`, un tipo che
   non esiste `E_TIPO_CONTATTO_NON_TROVATO` sullo stesso campo. `default_context` passato a `fn_crea_contatto` è
   `E_CAMPO_NON_AMMESSO`: il BE non lo passa.
5. **`script.fn_get_contatti` senza reparto** restituisce ora anche i contatti che hanno un reparto.
   `PortaleRepository.get_email_contatto_suggerita` la chiama senza reparto: può trovare un'email che prima non
   vedeva. È il comportamento voluto; censire gli altri lettori che contavano sul filtro.
6. **Garanzia ritirata** (§22.5): «il livello `ruolo` di un soggetto ha al più un predefinito» diventa «ogni ruolo
   ha il suo». Censire i lettori di `contatti.is_default` e `default_context` che contano su quella proprietà.
   `get_email_contatto_suggerita` legge i contatti del ruolo e ne prende il predefinito: con la regola nuova trova
   quello del suo ruolo, non quello di un altro.
7. **Un contatto d'istanza ha il ruolo** (`chk_contatti_istanza_con_ruolo`, 23514). Il BE crea i contatti d'istanza
   solo dal ruolo (`create_contatto_ruolo`): niente da cambiare, salvo scritture dirette che il censimento trovi.
8. **Il catasto**: un'istanza agganciata all'unità di un'altra è rifiutata dall'indice
   `uq_istanze_utilities_catasto_unita_immobiliare` (23505). Al cambio di civico o di unità di un'istanza la ponte
   la segue, e l'unità lasciata si cancella. Censire le scritture BE di `catasto_unita_immobiliare_id` e della
   ponte.

**Esito del passaggio (BE, 2026-11-26).**

* **1-4, fatte.** «Rendi predefinito» come azione `POST …/contatti/{id}/predefinito/` (soggetto e ruolo), che
  scrive solo `is_default = true`; i due codici del predefinito e quelli del tipo risalgono dalla loro policy;
  `VINCOLI_CONTATTO` resta alla sola modifica diretta. Le rotte del soggetto toccano i soli contatti senza ruolo.
  Doc: `api_soggetti` §6, `api_contatti_ruolo` §5. Il FE mostra il segno con il BB `PredefinitoSegno`.
* **7, niente da cambiare**: il BE crea i contatti d'istanza solo dal ruolo.

* **5 e 6, chiuse insieme.** Il censimento dei lettori di `is_default` e `default_context` nel BE trova un solo
  punto che sceglie per il segno: `PortaleRepository.get_email_contatto_suggerita`. Prendeva il predefinito con
  l'id più basso fra quelli della cascata, cioè di solito quello del **soggetto** anche quando il ruolo ha il suo.
  Ora, dopo il PRINCIPALE, legge il BB `script.fn_get_contatto_default` (vince il contesto più specifico). Se quel
  predefinito non ha email non si suggerisce niente, senza ripiegare su un contesto meno specifico (Tid,
  2026-11-26). Test sul DB vero: `portale/tests/db/test_email_suggerita_db.py`, caso 2. Gli altri lettori
  (`views_contatti_ruolo`, `get_soggetto_contatti`, il drawer dei contatti) mostrano il segno senza sceglierci
  sopra.
* **8, chiusa senza modifiche.** Nel BE non c'è nessuna scrittura di `catasto_unita_immobiliare_id` né della ponte.

### 22.7 Che cosa resta

* ✅ apply di `-36 … -46`, pgTAP verdi, doc auto-generata rigenerata (Tid, 2026-11-25);
* ✅ il passaggio al BE (§22.6), fatto il 2026-11-26;
* ✅ i segnaposto `-47 … -60` tolti e `changelog-autogen.yaml` rigenerato (2026-11-25). Erano `databaseChangeLog: []`:
  su dbdev e sullo scratch nessuna riga di `databasechangelog` li nomina. Il prossimo numero libero è `-47`;
* **debito residuo**: la cancellazione di un'istanza lascia la sua unità senza nessuno che la nomini (§22.4). Due
  contatti nati insieme in un contesto vuoto, in due transazioni, urtano ora l'indice del predefinito (23505) invece
  di nascere predefiniti tutti e due: il secondo va riprovato;
* T6 tiene il contatto obbligatorio, il puntatore `soggetti.default_contatto_id` e l'ultimo contatto cancellato;
  **richiesta dal BE** (verifica del passaggio §22.6, 2026-11-26): la cancellazione dell'ultimo contatto del
  contesto del soggetto (`DELETE /soggetti/{id}/contatti/{contatto_id}/`) urta `fk_contatti_anagrafiche` e
  arriva al client come `400 E_DATABASE` senza frase né campo; il BE non la traduce per nome della FK (sarebbe una
  seconda sede della regola), aspetta il codice parlante di T6;
* la voce di T11 sul montaggio senza fase del predefinito è chiusa da -37.

## 23. Giro 5-bis — il titolo IVA che chiede la partita IVA (2026-11-26: ⚠️ RITIRATO da Tid lo stesso giorno, §23.4)

> ⚠️ **Ritirato** (Tid, 2026-11-26): il giro replicava un'informazione che il modello ha già. §23.1-§23.3 restano come
> vicolo cieco; l'esito e la verifica di ciò che esiste stanno in §23.4.

**La regola chiesta da Tid** (2026-11-26): un soggetto senza partita IVA non può avere un titolo IVA da soggetto IVA.
Nasce dentro T10 (i titoli IVA, §17.1) e Tid lo **anticipa prima di T4**. Il resto di T10 (S44) resta al suo posto.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 6 oggetti, 2026-11-26; nessun orfano):

| Guida o nota | Esito |
| --- | --- |
| nota [_titolo-iva-per-natura](../../dbzero/anagrafiche/_titolo-iva-per-natura.md) | **coerente**; con il giro resta **indietro**: la tabella «Le strade che toccano la regola» prende le strade nuove, nello stesso giro |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) §«I titoli IVA ammessi dalla natura» | **coerente**; prende la frase della regola nuova nello stesso giro |
| [iva-risolutore-di-riga](../../guide/iva-risolutore-di-riga.md) | **coerente**: legge i titoli, il giro non ne cambia la lettura |
| `generazione-cliente`, `gestione-dei-contatti`, `gestione-delle-istanze-utility`, `gestione-pratiche`, `messaggi-audit`, `risorse-umane-e-accessi`, note `_contatto-predefinito`, `_sincronizzazione-accesso` | **coerenti**: nominano `soggetti` per altro |

### 23.1 Che cosa dice il contratto (letto sul seed e sul corpo, 2026-11-26)

* La matrice `config.tipi_titolo_iva_tipi_soggetto_dettaglio` ammette `INTENTO` e `USO_INDUSTRIALE` solo per nature con
  `piva_obbligatoria = t` (DI, SP, SC, ENC); la presenza della P.IVA la garantisce
  `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori`. **La regola oggi regge per composizione di due dati di
  configurazione, e nessuna sede la dice**: una riga di matrice `INTENTO → PR`, o `piva_obbligatoria` spenta su una
  natura che ha titoli in matrice, fa entrare nel risolutore un titolo da soggetto IVA su chi ha il solo CF.
* **Il controesempio alla regola larga**: `AGEVOLATA_104` è ammessa **solo** per il privato (PR), cioè per chi ha il
  solo CF, ed è giusto sul modello (l'agevolazione è della persona). La regola è **per tipo di titolo**, non per tutti.
* `COOPERATIVA` non ha righe di matrice: nessuna natura la ammette. Resta D-4 del registro dei residui
  (`brief-db-dati-fiscali-e-societari-del-soggetto`), fuori da questo giro.

### 23.2 Le decisioni (Tid, 2026-11-26; ⚠️ revocate lo stesso giorno, §23.4)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-T10a-1 | Dove sta la regola | **a**: un flag `richiede_partita_iva` sul tipo di titolo (`config.tipi_titolo_iva`), controllato dove si configura. ~~b, il controllo sulla `partita_iva` del soggetto nel guard del titolo~~: ripete la regola della natura in una seconda sede e apre le strade del cambio di P.IVA e di natura |
| D-T10a-2 | Quali tipi la chiedono | `INTENTO` e `USO_INDUSTRIALE` sì; `AGEVOLATA_104` no; `COOPERATIVA` no (D-4 resta aperta) |
| D-T10a-3 | Quando | Prima di T4; poi si prosegue con T4 |

### 23.3 Il piano del giro (⚠️ superato: §23.4)

Le strade che possono rompere la coerenza «titolo che chiede la P.IVA ⇒ natura con P.IVA obbligatoria» sono tre, e
ognuna ha il suo guard; la domanda «c'è una coppia incoerente?» ha una sede sola, letta dai tre:

1. una riga di matrice attiva nasce, si riattiva o si sposta su una coppia incoerente;
2. una natura spegne `piva_obbligatoria` con titoli in matrice che la chiedono;
3. un tipo di titolo accende `richiede_partita_iva` con righe di matrice attive su nature senza P.IVA obbligatoria.

* [ ] pgTAP rosso che costruisce le tre strade
* [ ] changeSet: la colonna, il CSV, la funzione-sede, i tre guard, i codici d'errore
* [ ] provati sullo scratch con `scripts/prova_changeset.py`
* [ ] pagine `manual/`, la nota `_titolo-iva-per-natura`, la guida
* [ ] apply e pgTAP (Tid); doc auto-generata rigenerata
* [ ] commit (Tid)

### 23.4 Il ritiro, e che cosa esiste già (2026-11-26)

**Ritirato da Tid il 2026-11-26.** Il giro era scritto e provato sullo scratch (`20261125-77 … -80`: la colonna
`config.tipi_titolo_iva.richiede_partita_iva`, la funzione `config.fn_titolo_iva_partita_iva_incoerenza`, un guard
montato su matrice, tipo e natura, il codice `E_TITOLO_IVA_RICHIEDE_PARTITA_IVA`, il pgTAP
`config/test-titolo-iva-richiede-partita-iva-v1.sql`, verde 17/17). Niente è stato applicato né committato: i file
sono tolti, i CSV ripristinati, i numeri `20261125-77 … -80` tornano liberi.

**Perché, sul modello: il riconoscimento «partita IVA sì o no» c'è già, ed è della natura.**
`config.tipi_soggetto_dettaglio` lo porta in due colonne tenute coerenti da un `CHECK`
(`chk_tipi_soggetto_dettaglio_piva_obbl_vs_formato`): `piva_obbligatoria` e `formato_piva`. `formato_piva =
NON_APPLICABILE` vuol dire «chi ha questa natura ha il solo codice fiscale» (oggi il privato, PR); `cf_obbligatorio` è
acceso su tutte le nature e non distingue niente. Un flag sul tipo di titolo diceva di nuovo, da un'altra tabella, una
cosa che la matrice titoli × natura dice già riga per riga: una seconda sede della stessa regola.

**Il controllo «un titolo da soggetto IVA non si usa su chi ha il solo CF» esiste ed è completo** (letto sul corpo,
2026-11-26). Ogni strada che può far diventare vigente un titolo su una natura che non lo ammette è chiusa:

| Strada | Chi la chiude | Rifiuto |
| --- | --- | --- |
| si scrive o si riaccende un titolo, o se ne cambia tipo o titolare | `anagrafiche.trgfn_soggetti_titoli_iva_guard_tipo_soggetto`, che legge la matrice con `anagrafiche.fn_titolo_iva_ammesso` | `E_TITOLO_IVA_NON_AMMESSO_PER_TIPO_SOGGETTO`; senza natura `E_DATO_FISCALE_SENZA_TIPO_SOGGETTO` |
| il soggetto cambia natura (una ditta diventa privato) | `anagrafiche.fn_check_cambio_natura_soggetto` | `E_TIPO_SOGGETTO_CON_TITOLI_IVA_NON_AMMESSI`, `E_CAMBIO_NATURA_TITOLI_ALTRI_EMITTENTI` |
| una riga della matrice smette di ammettere | `config.trgfn_tipi_titolo_iva_tipi_soggetto_dettaglio_guard_ritiro` | `E_TITOLO_IVA_AMMISSIONE_IN_USO` |
| la natura ha la P.IVA obbligatoria ma il soggetto non la scrive | `anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori` | `E_PIVA_OBBLIGATORIA` |

Lo prova già `anagrafiche/test-soggetti-titoli-iva-tipo-soggetto-v1.sql`: il test 16 rifiuta un `INTENTO` su un
privato, il 18 il cambio di natura con un titolo vigente che la natura nuova non ammette. La matrice di seed abbina `INTENTO` e `USO_INDUSTRIALE` solo
a DI, SP, SC ed ENC, cioè a nature con la partita IVA.

**Dove sta quindi la regola**: nella matrice, che è configurazione. Una riga che abbina un titolo da soggetto IVA a una
natura con `formato_piva = NON_APPLICABILE` non deve esistere; chi configura la matrice (CSV o pannello) ne risponde.
Un controllo di coerenza fra matrice e natura non c'è: era il giro ritirato.

**L'eccezione voluta**: `AGEVOLATA_104` è ammessa **solo** al privato, cioè a chi ha il solo CF: l'agevolazione è
della persona. Una regola «nessun titolo su chi ha il solo CF» la renderebbe inutilizzabile.

**Il vicolo cieco, perché non si riprovi**: la proposta è partita da «nessuna sede dice la regola» senza leggere
prima che cosa del modello la diceva già (le colonne della natura, la matrice, il guard del titolo). Il giro è stato
costruito e provato prima di accorgersene.

## 24. Giro 6 — T4, l'azienda del billing account (2026-11-26: decisioni prese, applicato, pgTAP verdi, committato; il passaggio al BE da girare)

Il perimetro è S2, S24, S25, S26, S27, S28, S29, S31, S32, S33 (§17) e la FK di `emittenti_fiscali.valuta_id` portata da
S53 (§17.1). Corpi letti sul catalogo dello scratch (`zeroerp_ruoli`) il 2026-11-26; sul backend si è guardato solo
chi chiama, in sola lettura.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 18 oggetti, 2026-11-26):

| Guida o nota | Esito |
| --- | --- |
| nota [_emittente-del-billing-account](../../dbzero/anagrafiche/_emittente-del-billing-account.md) | **coerente** sui tre livelli, i quattro movimenti e la storia («una bozza non blocca»). Con D-T4-1 e D-T4-2 resta **indietro**: «i controlli che guardano lo spostamento della predefinita chiedono l'azienda per l'installazione» varrà per tutti i cancelli. ⚠️ Nomina i cancelli senza schema, e lo script li dà orfani (`fn_guard_ba_gestore_globale_storia`, i tre `trgfn_efba_guard_*`, `fn_check_ba_coppia_emittente_omogenea`, `fn_ba_ha_storia_emittente`, `script.fn_check_ba_cambio_emittente`): l'header «Vedi anche» è incompleto, si completa nello stesso giro |
| pagina `manual/billing_account` §«Che cosa non fa» | **coerente** con il codice di oggi: descrive come limiti S28 («la gerarchia non ha un limite di livelli», «cambiare il padre non è giudicato come toglierlo»). È la fotografia del giro 0a, non una decisione: con D-T4-5 si riscrive |
| `anagrafiche/test-istanza-ba-gestore-globale-v1.sql`, test 1 e 5 | **contraddetto** da D-T4-2: trattano come lecito il passo che S24 segnala. Si riscrivono nello stesso giro, con la ragione |
| [generazione-cliente](../../guide/generazione-cliente.md) | **coerente** (l'albero sullo stesso emittente; la tabella dei trigger del BA). Con D-T4-5 la riga di `trgfn_billing_account_guard_normalize` resta indietro |
| [fatturazione](../../guide/fatturazione.md) | **coerente**; con D-T4-4 dice che la fattura passa dal guard dell'azienda del cliente come gli altri documenti |
| [gestione-commesse](../../guide/gestione-commesse.md), [gestione-ordini](../../guide/gestione-ordini.md), [gestione-ddt](../../guide/gestione-ddt.md) | **coerenti**: descrivono `script.trgfn_doc_guard_emittente_ba` sul loro documento |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md), [emittenti-fiscali](../../guide/emittenti-fiscali.md), [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md), nota `_chiave-unica-cliente` | **coerenti**: nominano il collegamento e la creazione per altro |
| `architettura-multi-face-auth`, `architettura-permessi-e-autorizzazioni`, `automazione-db`, `configurazione-e-gestione-parametri`, `contratto-guc-app`, `gestione-dei-pagamenti`, `integrazione-ai`, `iva-risolutore-di-riga`, `pgtap-come-si-scrive-un-test` | **coerenti**: nominano `vendite.fatture` o `emittenti_fiscali` per altro |

**La storia delle decisioni.** I tre cancelli (storia, albero, istanza) e la «storia = documento numerato di qualunque
famiglia» sono del cantiere del 31 agosto. La **D-5 del 2026-10-10**
([brief-db-istanza-nasce-col-ba-residui](../work-done/2026/brief-db-istanza-nasce-col-ba-residui.md), `20261010-57 …
-59`) ha introdotto `script.fn_get_ba_emittente_sr_id_installazione` e ci ha portato i soli guard della predefinita,
perché «con il risolutore di sessione un utente con un'azienda vedeva il BA scollegato restare alla SUA azienda, e lo
spostamento passava». I guard sul singolo BA sono rimasti al risolutore di sessione: S24 è lo stesso difetto, sull'altro
ramo.

### 24.1 Che cosa esiste già, segnalazione per segnalazione

| # | Che cosa dice il corpo | Che cosa esiste già e si riusa | Esito |
| --- | --- | --- | --- |
| **S2** | `fn_guard_ba_gestore_globale_storia` sceglie il primo BA scollegato con «ha fatture o commesse» (anche in bozza) e delega a `fn_guard_ba_cambio_emittente`, che decide con `anagrafiche.fn_ba_ha_storia_emittente` (documento numerato di qualunque famiglia attiva). Un BA con soli ordini o DDT numerati non è scelto; un BA con una fattura in bozza è scelto, la delegata tace, gli altri non si guardano | `anagrafiche.fn_ba_ha_storia_emittente`: è la definizione di storia, già sede unica per il ramo del singolo BA | **Difetto**: due definizioni della stessa regola. La scelta si fa col BB |
| **S24** | `fn_check_ba_coppia_emittente_omogenea` (chiamata da `fn_guard_albero_ba_emittente` e `fn_guard_istanza_ba_emittente`, nessun chiamante nel backend) risolve con `fn_get_emittente_fiscale_id`, il risolutore di sessione: un BA appena scollegato si confronta con l'azienda dell'operatore, non con la predefinita su cui ricade | `script.fn_get_ba_emittente_sr_id_installazione` (D-5). Alla nascita del BA il collegamento lo scrive `trg_billing_account_z90_link_ef_ins` prima dei guard `z95`, quindi anche lì l'azienda d'installazione è quella giusta | **Difetto**; la correzione completa D-5 |
| **S25** | Un `UPDATE` che porta la riga da collegamento a predefinita, o il contrario, passa dai guard di storia e di albero solo sul singolo BA (il gemello dell'istanza chiama anche quello della predefinita). Sostituire la predefinita con `DELETE` + `INSERT` è rifiutato alla `DELETE` (`dopo = NULL`) se un BA scollegato ha storia, anche se la riga nuova riporta la stessa azienda | Il ramo dell'istanza, `trgfn_efba_guard_istanza_emittente`, è già la forma giusta | **Difetto** il primo; il secondo è una scelta da dichiarare (D-T4-3) |
| **S26** | I due guard della predefinita guardano lo stato dopo (esiste una coppia mista?), non la differenza | — | **Scelta**: l'invariante è globale; una coppia mista che c'è già nasce solo da S24, e chiusa S24 è un difetto di dati che si corregge a mano. Si scrive nella nota |
| **S27** | `script.trgfn_doc_guard_emittente_ba` è montato su ordini, DDT, resi, commesse, contratti, offerte, preventivi e seriali; non su `vendite.fatture`, che ha `billing_account_id` ed `emittente_soggetto_ruolo_id` come `vendite.commesse` | Il BB, con i suoi argomenti (etichetta, colonna che identifica, colonna dell'emittente, codice). Il fermo dei temi trasversali lo ammette: poggia su un pezzo comune già fatto (§17) | **Difetto** il montaggio mancante. ⚠️ La seconda metà («una bozza resta all'azienda di prima quando il BA cambia azienda») vale per **tutte** le famiglie, non per la sola fattura: il guard giudica il documento quando lo si scrive, non quando il BA si sposta |
| **S28** | `trgfn_billing_account_guard_normalize` rifiuta solo il padre uguale a sé: nessun limite di livelli, nessun controllo dei cicli; il blocco per attività non fatturate scatta solo se il padre diventa vuoto, non se cambia | Il blocco dello stacco c'è già (`E_DISSOCIAZIONE_PARENT_CON_ATTIVITA`): basta giudicarci anche il cambio | **Difetto** il ciclo e il cambio di padre; il limite di livelli è una decisione di modello (D-T4-5) |
| **S29** | `billing_account.valuta_id` ed `emittenti_fiscali.valuta_id` (`integer`, nullable) senza FK; `fornitori` e `gestori` l'hanno verso `config.valute(id)` (`integer`) | Le FK gemelle di `fornitori` e `gestori` | **Difetto** |
| **S31** | `trgfn_billing_account_guard_admin_globale` e `trgfn_billing_account_link_ef` leggono l'utente con `script.fn_utente_di_sessione` dentro `EXCEPTION WHEN OTHERS THEN v_user_id := NULL`: un utente illeggibile diventa «nessun utente» e la riga passa | `fn_id_fiscale_bloccato` lascia già salire il rifiuto | **Difetto**: si toglie il blocco; `v_user_id integer` e `v_existing bigint` si ancorano |
| **S32** | `fn_lookup_utilities_per_ba(p_billing_account_id, p_ruolo_codice_soggetto)` non legge il BA: il ruolo arriva dal chiamante e non si confronta con `billing_account.soggetto_ruolo_id`; un id che non è un BA ricade sulla predefinita e risponde | Il ruolo vero sta sul BA. Chiamanti: `backend/apps/core/db/lookup_repository.py` e il pgTAP `test-fn-lookup-utilities-per-ba.sql` | **Difetto**; firma invariata (§5f) |
| **S33** (prima metà) | Senza sessione `fn_crea_billing_account` scrive il BA, i guard `z95` di albero e istanza lo giudicano sulla predefinita, e solo dopo la funzione scrive il collegamento con l'azienda chiesta: un figlio di un padre di un'altra azienda è rifiutato anche se la coppia finale è omogenea | — | **Difetto** (D-T4-9) |
| **S33** (seconda metà) | Con `usa_sequenza` spento `script.fn_generate_codice` restituisce `NULL` per contratto, e il rifiuto è il `NOT NULL` (23502) | Il generatore è un BB con 12 chiamanti: lo stesso caso vale per ogni tabella col codice generato | **Forma**, di tutta la famiglia: proposta in T11 (D-T4-10) |

### 24.2 Le decisioni per Tid

⚠️ **Riletto il 2026-11-26, su domanda di Tid**: di T4 era già deciso (§17.1, 2026-11-23) che si fa qui e che S27
monta il guard su `vendite.fatture` (D-T4-4 nella sua prima parte). Le altre righe sono **difetti** che si correggono
riusando pezzi esistenti (§24.1) e seguono la proposta, come nei giri 3-5. Restano a Tid **due scelte vere**: D-T4-5
(i livelli dell'albero) e D-T4-3 (b) (la predefinita si sostituisce con `UPDATE`); e la conferma dei due rinvii (la
bozza di ogni famiglia nel registro dei residui, D-T4-4; il codice con la sequenza spenta in T11, D-T4-10).

| # | Domanda | Proposta |
| --- | --- | --- |
| D-T4-1 | S2: la predefinita sceglie i BA da controllare con `fn_ba_ha_storia_emittente` | **Sì**. Effetto: un BA con soli ordini o DDT numerati blocca lo spostamento della predefinita; una fattura in bozza no, come dice la nota |
| D-T4-2 | S24: i guard sul singolo BA (albero e istanza) chiedono l'azienda per l'installazione, come quelli della predefinita | **Sì**, completa D-5. Il risolutore di sessione resta per gli altri lettori. I test 1 e 5 di `test-istanza-ba-gestore-globale-v1` si riscrivono |
| D-T4-3 | S25: (a) il trasformarsi di una riga da collegamento a predefinita, o il contrario, passa anche dai guard della predefinita; (b) la predefinita si sostituisce con `UPDATE` | **(a) sì**, come fa già il ramo dell'istanza. **(b) scelta dichiarata**: `DELETE` + `INSERT` resta rifiutato quando un BA scollegato ha storia, e la nota lo dice. L'alternativa, un giudizio differito a fine transazione, costa un trigger differito per un percorso che ha già una strada |
| D-T4-4 | S27: `vendite.fatture` monta `script.trgfn_doc_guard_emittente_ba('Fattura', 'numero', 'emittente_soggetto_ruolo_id', <codice>)` | **Già deciso** (Tid, 2026-11-23, §17.1), con `E_DOC_EMITTENTE_BA_INCOERENTE` come ordini e DDT. Prima del montaggio, il pgTAP della pipeline di fatturazione prova che il motore scrive sempre l'azienda del BA. La bozza di ogni famiglia che resta all'azienda di prima **non** entra in T4: tocca tutti i documenti di vendita (serve l'ok di Tid) e va nel registro dei residui |
| D-T4-5 | S28: quanti livelli ha l'albero dei BA | **a**: uno solo (un padre non ha padre, un figlio non fa da padre), che chiude anche i cicli; «la fattura va al padre diretto» resta vero senza ambiguità. **b**: più livelli, rifiutando i soli cicli. In tutti e due i casi il cambio di padre con attività non fatturate è rifiutato come lo stacco |
| D-T4-6 | S29: FK `valuta_id` → `config.valute(id)` su `billing_account` ed `emittenti_fiscali` | **Sì**, `ON UPDATE CASCADE` come le gemelle; prima si leggono gli orfani, che impedirebbero il vincolo |
| D-T4-7 | S31: via il blocco `EXCEPTION` dai due trigger | **Sì** |
| D-T4-8 | S32: il lookup rifiuta un BA che non c'è e un ruolo che non è quello del BA | **Sì**, firma invariata; i codici si cercano a catalogo prima di coniarne uno |
| D-T4-9 | S33: come si giudica l'albero e l'istanza di un BA nato senza sessione con l'azienda chiesta | **a**: i due guard sulla nascita del BA (`z95` albero e istanza) diventano differiti a fine transazione, quando il collegamento c'è. ⚠️ I pgTAP girano `IMMEDIATE`: il caso si prova con `SET CONSTRAINTS … DEFERRED` nel test. **b**: la funzione scrive il BA e il collegamento in un'istruzione sola (non si può: la FK va dal collegamento al BA) |
| D-T4-10 | S33: il codice mancante con la sequenza spenta | **In T11**: il caso è del generatore e dei suoi 12 chiamanti, non del BA |

### 24.3 Il piano del giro (dopo le decisioni)

* [x] Analisi sul catalogo, guide verificate, ciò che esiste già (2026-11-26, §24.1)
* [ ] Le due scelte D-T4-5 e D-T4-3 (b), e i due rinvii (Tid); il resto segue la proposta
* [ ] pgTAP rosso, un caso costruito per segnalazione
* [ ] changeSet (il range lo dà Tid), prova sullo scratch con `scripts/prova_changeset.py`
* [ ] la nota `_emittente-del-billing-account` (con il «Vedi anche» completo), `manual/billing_account`, le guide indietro
* [ ] apply e pgTAP (Tid); doc auto-generata rigenerata; commit

### 24.4 Le risposte di Tid (2026-11-26) e la storia che toccano

* **D-T4-3, la predefinita (Tid): «un BA non può cambiare emittente»; la predefinita non deve spostare i clienti.**
  L'idea di Tid: prima di togliere il flag alla predefinita, i BA senza collegamento si collegano tutti alla
  predefinita di oggi; solo dopo il flag si sposta. ⚠️ **È un cambio di modello**: revoca il ripiego «senza
  collegamento il BA segue la predefinita» (il movimento 4, «raggio N», di
  [brief-db-billing-account-cambio-emittente](../work-done/2026/brief-db-billing-account-cambio-emittente.md) §6.2,
  2026-08-26) e la nota `_emittente-del-billing-account` (terzo livello, quarto movimento). **La forma proposta, da
  confermare**: un BA ha **sempre** il suo collegamento. Nasce collegato all'azienda di chi lo crea, o alla
  predefinita se non c'è sessione (oggi `trgfn_billing_account_link_ef` senza sessione non collega); i BA esistenti
  senza collegamento si collegano una volta, alla predefinita di oggi. Da lì la predefinita decide solo l'azienda dei
  BA che **nasceranno**, e spostarla non cambia più nessun cliente. ⚠️ Ricadute da censire prima di costruire: il
  backend «sposta» un cliente cancellando il collegamento e creandone uno nuovo (§2.2 di quel brief), e la
  cancellazione lascerebbe un BA senza collegamento; i guard della predefinita sull'albero e sull'istanza
  (`fn_guard_*_gestore_globale`) non avrebbero più niente da cercare, e si ritirerebbero.
* **D-T4-4, le bozze (Tid): «se ci sono documenti il cliente non può cambiare azienda»; chi ha sbagliato cancella i
  documenti.** Qualunque documento di qualunque famiglia, **anche in bozza**, chiude il cambio d'azienda del BA.
  ⚠️ **Revoca** «conta solo il documento numerato, una bozza non blocca»
  ([brief-db-registri-di-numerazione-emittente-e-trasloco](../work-done/2026/brief-db-registri-di-numerazione-emittente-e-trasloco.md),
  2026-08-30) e **completa** D-1 **b** di brief-db-billing-account-cambio-emittente (2026-08-26): la finestra di
  correzione resta, ma solo finché il BA non ha nessun documento. Con questa regola la seconda metà di S27 (la bozza
  rimasta all'azienda di prima) non può più nascere: il rinvio al registro dei residui non serve. La sede della regola
  resta una, `anagrafiche.fn_ba_ha_storia_emittente`, che smette di chiedere il numero.
* **D-T4-10, il codice con la sequenza spenta (Tid): da correggere.** Sede proposta: T11, per tutti i 12 chiamanti
  del generatore.
* **D-T4-5, i livelli dell'albero: Tid chiede come nasce un padre di un padre**, e propone un solo padre per partita
  IVA o codice fiscale, forse con un flag «padre». La spiegazione e la proposta sono in chat (2026-11-26); ⚠️ la
  decisione esistente da rispettare o revocare:
  [analisi-critiche-modello-clienti-utilities-catasto](../work-done/2026/analisi-critiche-modello-clienti-utilities-catasto.md)
  §2.2 ha scartato un flag `fattura_aggregata` perché «creerebbe ridondanza e uno stato incoerente»: la semantica sta
  già in `parent_account_id`. Il motore di fatturazione legge un livello solo (`COALESCE(ba.parent_account_id, ba.id)`
  in `fn_build_fattura_key`, `fn_resolve_registro_documento`, `fn_resolve_termini_pagamento`).

### 24.5 Decise da Tid (2026-11-26)

| # | Decisione |
| --- | --- |
| D-T4-5 | **Un livello solo, senza flag**: chi ha un padre non fa da padre, chi fa da padre non ha un padre (i cicli diventano impossibili); **un solo padre per cliente e per azienda** (stessa identità fiscale, stesso emittente). Il cambio di padre con attività non fatturate è rifiutato come lo stacco. Rispetta la decisione di `analisi-critiche-modello-clienti-utilities-catasto` §2.2 (nessun flag: la semantica sta in `parent_account_id`) |
| D-T4-3 | **Ogni BA ha sempre il suo collegamento a un'azienda.** Nasce collegato all'azienda di chi lo crea, o alla predefinita se non c'è sessione; i BA esistenti senza collegamento si collegano una volta alla predefinita di oggi. La predefinita decide solo l'azienda dei BA che nasceranno: spostarla non cambia nessun cliente. Revoca il ripiego «senza collegamento segue la predefinita» (brief-db-billing-account-cambio-emittente §6.2, 2026-08-26) |
| D-T4-3 bis | **Un BA cambia azienda solo se non ha documenti** (Tid: «solo con documenti» è il divieto). La forma **b** di D-1 (2026-08-26) resta: la finestra di correzione c'è finché il BA non ha nessun documento |
| D-T4-4 | **Qualunque documento, anche in bozza, chiude il cambio d'azienda** (§24.4). S27: il guard dell'azienda montato su `vendite.fatture` (deciso il 2026-11-23) |
| D-T4-10 | Il codice con la sequenza spenta si corregge, in T11 (§24.4) |
| il resto | S2, S24, S25 (a), S29, S31, S32, S33 seguono la proposta di §24.2 |

**Che cosa ne segue sul modello** (letto sui corpi, 2026-11-26):

* Con ogni BA collegato il risolutore trova sempre il collegamento al primo livello: **S24 si chiude per costruzione**
  (sessione e installazione danno la stessa risposta), e così S26. I tre guard della predefinita (storia, albero,
  istanza, «raggio N») non hanno più niente da cercare: **si ritirano nello stesso giro**, coi rami del movimento 4
  dei tre trigger di `emittenti_fiscali_billing_account`. S2 si chiude con loro.
* Un BA senza collegamento diventa uno stato che il modello non ammette: lo presidia un controllo **a fine
  transazione** (il BA nasce, il collegamento arriva subito dopo), su `billing_account` e sulla cancellazione o lo
  spostamento di un collegamento. S25 (a) si chiude per costruzione: un collegamento non diventa più la predefinita.
* Lo spostamento di un BA fra due aziende (ammesso senza documenti) si fa **modificando** il collegamento, non
  cancellandolo: la cancellazione da sola lascerebbe il BA scollegato.
* `fn_crea_billing_account` con l'azienda chiesta trova già il collegamento scritto alla nascita (di chi agisce o della
  predefinita) e lo **corregge** se diverso, invece di rifiutare (§24.1, S33).
* La «storia» diventa «qualunque documento»: `anagrafiche.fn_ba_ha_storia_emittente` e
  `anagrafiche.fn_get_storia_emittente_ba` smettono di chiedere il numero; la sede resta una.

**Richiesta al team BE/FE** (da girare dopo l'apply, con l'elenco dei file già noti, e il censimento: «censisci chi
scrive o cancella `anagrafiche.emittenti_fiscali_billing_account` e chi conta sul BA senza collegamento»):
`backend/apps/anagrafiche/db/emittenti_fiscali_repository.py`, `create_mapping` e `delete_mapping` (righe 470-500 al
2026-11-26): lo spostamento di un cliente diventa un `UPDATE` di `emittente_soggetto_ruolo_id` sul collegamento; la
cancellazione di un collegamento di un BA è rifiutata; la frase del blocco per storia nomina anche le bozze.

### 24.6 Il piano del giro, dopo le decisioni

* [x] Le decisioni (Tid, 2026-11-26, §24.5)
* [x] pgTAP rosso: un caso costruito per ogni regola (2026-11-26, §24.7) (la nascita senza sessione collegata alla predefinita; il BA senza
  collegamento rifiutato a fine transazione; la predefinita che si sposta senza toccare nessuno; la bozza che blocca;
  lo spostamento per modifica; il padre di un padre, il ciclo, il secondo padre per cliente e azienda, il cambio di
  padre con attività; la fattura con l'azienda sbagliata; la valuta inesistente; l'utente illeggibile; il lookup con
  BA o ruolo sbagliati; la creazione senza sessione con l'azienda chiesta)
* [x] changeSet (range da Tid, `20261126-26 … -41`, 2026-11-26), prova sullo scratch; i pgTAP che il ritiro dei guard della predefinita rompe,
  riscritti nello stesso changeSet (`test-istanza-ba-gestore-globale-v1` e i gemelli)
* [x] (2026-11-26) la nota `_emittente-del-billing-account` riscritta (due livelli, tre movimenti, «Vedi anche» completo),
  `manual/billing_account`, le pagine delle funzioni ritirate, le guide indietro
* [x] apply e pgTAP (Tid); commit (2026-11-26, «DB: anagrafiche giro 6 (T4)», PR #259)
* [x] doc auto-generata rigenerata, nello stesso commit: la scheda di `fn_check_ba_padre` c'è, quelle degli oggetti
  ritirati no, `index.ci.md` non linka più le pagine ritirate (verificato il 2026-11-26)
* [ ] la richiesta al BE (§24.8): da girare; verificato il 2026-11-26 che il ramo BE non l'ha ancora presa
  (`delete_mapping` e la riga 311 di `emittenti_fiscali_service.py` ci sono ancora)

### 24.7 Che cosa è scritto (giro 6: chiuso lato DB il 2026-11-26)

Range dei changeSet: `20261126-26 … -40` (Tid, 2026-11-26: «il primo progressivo libero, altri cantieri fermi»),
occupato per intero con segnaposto lo stesso giorno. Il giro si costruisce in due blocchi: **A** i difetti
indipendenti (S28, S31, S29, S32, S27), **B** il modello «ogni BA ha sempre il suo collegamento».

* ✅ **S28, l'albero a un livello** (`-37`, 2026-11-26): `anagrafiche.fn_check_ba_padre` (SECURITY DEFINER, i motivi
  `E_PARENT_CON_PADRE`, `E_PARENT_HA_FIGLI`, `E_PARENT_SECONDO_PADRE`) chiamata da
  `trgfn_billing_account_guard_normalize` quando il padre nasce o cambia; lo stacco con attività non fatturate vale
  anche per il cambio. Codici in coda ai due cataloghi (messaggi `1550 … 1552`), la frase di
  `E_DISSOCIAZIONE_PARENT_CON_ATTIVITA` riscritta. pgTAP nuovo `anagrafiche/test-billing-account-albero-un-livello-v1`:
  senza 1 ok / 5 rossi, con 6/6; `test-billing-account-guard-parent` e `test-guard-albero-ba-omogeneo-v1` invariati.
  Prova sullo scratch col seed dei codici simulato (lo script non carica i CSV: il caricatore lo prova l'apply).
  Fatto del 2026-11-26: su scratch e dbdev nessun albero fuori dalla regola nuova.
* ✅ **S31, l'utente illeggibile** (`-28`, 2026-11-26): `trgfn_billing_account_guard_admin_globale` senza il blocco
  `EXCEPTION`, `v_user_id` ancorata. pgTAP nuovo `anagrafiche/test-billing-account-utente-illeggibile-v1`: il test 1
  (il BA con `app.current_user_id` illeggibile è rifiutato) rosso senza, verde con; il test 2 (nessun `EXCEPTION WHEN
  OTHERS` nei due trigger) resta rosso finché `-27` non riscrive `trgfn_billing_account_link_ef`.
  `test-billing-account-auto-link-ef` invariato.
* ✅ **S29, la valuta** (`-38`, 2026-11-26): `fk_billing_account_valute` e `fk_emittenti_fiscali_valute` verso
  `config.valute(id)`, `ON UPDATE CASCADE`; nella politica degli indici `SENZA_INDICE` per le due e per la gemella
  `fk_fornitori_valute`, che era `DA_DECIDERE` (stesso significato). Fatto del 2026-11-26: nessun orfano su scratch e
  dbdev. pgTAP nuovo `anagrafiche/test-valuta-fk-billing-account-emittente-v1`: senza 0/3, con 3/3.
* ✅ **S32, il lookup** (`-39`, 2026-11-26): `fn_lookup_utilities_per_ba` legge il ruolo del BA e rifiuta un id che non
  è un BA e un ruolo che non è il suo (`E_PARAMETRO_INVALIDO`); firma invariata. pgTAP nuovo
  `anagrafiche/test-fn-lookup-utilities-per-ba-legge-il-ba-v1`: senza 1/3, con 3/3; il vecchio
  `test-fn-lookup-utilities-per-ba` invariato (7/7). ⚠️ Debito di quel test, non di questo giro: i casi 4-7 dipendono
  dai dati della macchina e degradano a «soft-pass» (regola zero, corollario sui test).
* ✅ **S27, la fattura** (`-36`, 2026-11-26): `script.trgfn_doc_guard_emittente_ba` montato su `vendite.fatture`
  (`'Fattura', 'numero', 'emittente_soggetto_ruolo_id', 'E_DOC_EMITTENTE_BA_INCOERENTE'`). pgTAP nuovo
  `vendite/test-fatture-guard-emittente-ba-v1`: senza 0/3, con 3/3; invariati `test-chiave-fattura-tre-specchi-v1`,
  `test-lotto-rilancio-emittente-del-lotto-v1`, `test-registri-per-emittente-v1`,
  `test-ricalcola-totali-fattura-arrotondamento` (il motore scrive l'azienda del BA).
* ⚠️ *Superato: il blocco B è scritto, provato e applicato più sotto («Blocco B scritto», «Blocco B provato»,
  «Applicato»).* ⏳ **Blocco B**, il modello «ogni BA ha sempre il suo collegamento» (`-26`, `-27`, `-29 … -35`): da scrivere.

#### 24.7.1 Il blocco B, letto prima di scrivere (2026-11-26): tre fatti che ne cambiano la portata

D-T4-11 decisa da Tid il 2026-11-26: **a**, un BA nasce solo se esiste almeno un'azienda (senza, la nascita è
rifiutata per la predefinita mancante); lo scenario «0 emittenti» di `script.fn_check_user_can_create_ba`
(2026-04-08) non vale più per la nascita di un BA.

1. **La FK del collegamento non ha `ON DELETE`** (`fk_emittenti_fiscali_billing_account_ba`): oggi per cancellare un
   BA se ne cancella prima il collegamento. Vietare la cancellazione del collegamento di un BA vivo bloccherebbe anche
   la cancellazione del BA. Forma: la FK diventa `ON DELETE CASCADE` (`-40`, in `00_schema`), e un guard immediato
   vieta di cancellare il collegamento di un BA che esiste ancora o di spostarlo su un altro conto. Il controllo a fine
   transazione non serve più.
2. **La lista dei collegamenti del backend spegne il cestino con il motivo letto dal DB**
   (`backend/apps/anagrafiche/db/emittenti_fiscali_repository.py`, `sql_lateral_primo_motivo` su
   `script.fn_check_ba_cambio_emittente`, righe 382-421 al 2026-11-26). Con la regola nuova il collegamento di un BA
   non si cancella **mai**: il motivo del cestino è un altro, e va in una `fn_check_*` che il guard e la lista leggono
   insieme (linee-guida-sql §12.5.2). Richiesta al BE: la lista legge la check nuova.
3. **I guard della predefinita sono quattro, non tre**: c'è anche `anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale`
   (la chiave del cliente manuale contiene l'azienda del BA), chiamata da `trgfn_efba_guard_clienti_chiave` per la riga
   di default. Si ritira con gli altri. `backend/apps/anagrafiche/services/emittenti_fiscali_service.py` nomina
   `fn_guard_ba_gestore_globale_storia` (riga 311 al 2026-11-26): da censire nella richiesta al BE.

**S33, un fatto nuovo su D-T4-9**: rendere differiti i guard di nascita sposta l'errore al COMMIT anche per l'app che
crea un BA con un padre di un'altra azienda (un errore ordinario di chi compila). Decide Tid: differire, oppure tenere
i guard immediati e dichiarare il limite della creazione senza sessione con un'azienda chiesta diversa dalla
predefinita e un padre su quell'azienda.

**Risposte di Tid sui tre fatti (2026-11-26)**

* **1. Il billing account non si cancella** (Tid: «il cliente è giusto che sia non cancellabile, c'è la possibilità di
  mettere lo stato ad annullato, usiamo quello»). Letto sul catalogo: `billing_account` non ha uno stato (solo
  `valido_dal`, `valido_al`); lo stato è del cliente (`clienti.stato_cliente_id` → `config.stati_cliente`, fra cui
  `AN` «annulla servizio»), e un BA ha un solo cliente. Nessuna funzione del DB e nessun punto del backend cancellano un
  BA; lo fanno tre pgTAP (`test-billing-account-guard-parent`, `test-istanza-nasce-col-ba-v1`,
  `test-fn-disdetta-cliente`). Ne segue: **niente `ON DELETE CASCADE`** (il punto 1 di §24.7.1 è superato); un guard
  rifiuta la cancellazione di un BA, e il collegamento di un BA non si cancella e non si sposta su un altro conto. Il
  `-40` resta per il guard sulla cancellazione del BA.
* **2. Il cestino della lista dei collegamenti** (Tid: «allinearsi al cambio stato»): da confermare la lettura, in chat.
* **3. Il quarto guard della predefinita** (chiave unica del cliente manuale): Tid ha chiesto una spiegazione, in chat.
  Non è una decisione: con ogni BA collegato quel guard non ha più niente da cercare e si ritira con gli altri tre.
* **4. S33: b** (Tid). I guard di nascita restano immediati; il limite (creazione senza sessione, con un'azienda chiesta
  diversa dalla predefinita e un padre su quell'azienda) si scrive nella pagina di `fn_crea_billing_account` e nella
  nota. Il `-35` torna libero come riserva.

**Verifica degli YAML scritti (su richiesta di Tid, 2026-11-26)**, su `-26`, `-28`, `-36`, `-37`, `-38`, `-39`:
`guardrail_forme_changeset` aveva un solo rilievo, il `RETURNS TABLE` del `-39` coi tipi sciolti dal catalogo
(`id-senza-type` su `utility_id`). Lì il tipo resta esplicito con la ragione scritta: è la firma che il backend
legge, e i valori sono cast (`u.id::bigint` su un `integer`) o uscite di funzione, non il riflesso di una colonna
(§5f, §5g). Ogni altro tipo nudo ha la ragione sulla riga sopra (motivi, esiti, conteggi, il giorno operativo, la
riga di una SELECT statica). `guardrail_comment_al_presente` e `guardrail_run_on_change`: puliti. Tutti gli YAML si
leggono. Il `-39` riprovato dopo il ritocco: invariato (3/3).

* ✅ **D-T4-4, la storia è qualunque documento** (`-26`, 2026-11-26): `fn_ba_ha_storia_emittente` e
  `fn_get_storia_emittente_ba` non chiedono più il numero; firma e `RETURNS TABLE` ri-ancorati. La frase e la causa di
  `E_BA_EMITTENTE_CON_STORIA` dicono «documenti», non «documenti numerati». Il pgTAP
  `test-ba-storia-solo-numerati-v1` asseriva la regola revocata: riscritto (test 2 e 3: la bozza fa storia, il cambio
  è respinto) e rinominato `test-ba-storia-qualunque-documento-v1` (`git mv`): senza 5/7, con 7/7.
  `test-ba-cambio-emittente-storia-v1` invariato (14/14). ⚠️ Tre pagine `manual/` citano il nome vecchio e la regola
  vecchia (`fn_guard_ba_cambio_emittente`, `fn_ba_ha_storia_emittente`, `fn_get_storia_emittente_ba`): si correggono
  nel giro della documentazione.
* ✅ **Blocco B scritto** (2026-11-26; ⚠️ il «da adeguare» e il «fatto nuovo per Tid» qui sotto sono superati da
  «Blocco B provato» e da D-T4-12, più sotto): `-27` (la nascita sempre collegata: azienda di chi agisce, o predefinita senza
  sessione; senza aziende `E_EMITTENTE_DEFAULT_MISSING`; senza il blocco `EXCEPTION`, la seconda metà di S31), `-29`
  (i BA scollegati collegati alla predefinita di oggi), `-30` e `-31` (il collegamento non si cancella e non passa a un
  altro conto: il building block «rifiuta sempre», `E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, `E_BA_COLLEGAMENTO_NON_SI_SPOSTA`),
  `-32` (i quattro trigger del collegamento senza i rami della predefinita), `-33` (ritiro dei quattro guard della
  predefinita), `-34` (`fn_crea_billing_account` senza sessione modifica il collegamento nato; il limite di S33 nel
  COMMENT), `-40` (il BA non si cancella: «rifiuta sempre», `E_BA_NON_SI_CANCELLA`). Codici in coda ai cataloghi
  (messaggi `1553 … 1555`). Il `-35` resta di riserva. Prova sullo scratch, coi codici simulati: il pgTAP nuovo
  `anagrafiche/test-billing-account-sempre-collegato-v1` senza 3/9, con 9/9; verdi con l'estratto
  `test-billing-account-auto-link-ef` (il test 1 adeguato: senza sessione il BA nasce collegato alla predefinita),
  `test-billing-account-utente-illeggibile-v1` (2/2), `test-ba-storia-qualunque-documento-v1`,
  `test-ba-cambio-emittente-storia-v1`.
  **Da adeguare, perché descrivono la regola di prima**: `test-istanza-ba-gestore-globale-v1` (prova i guard ritirati:
  si ritira, il caso utile lo coprono i test 7-8 del nuovo), `test-guard-albero-ba-omogeneo-v1` (test 5, la
  cancellazione del collegamento), `test-istanza-nasce-col-ba-v1` (test 3-4, la cancellazione del BA),
  `test-cliente-manuale-chiave-unica-v1`, `test-emittenti-fiscali`, `test-billing-account-guard-parent` (si
  interrompono), `test-fn-disdetta-cliente` (lo script non lo corre: la prima istruzione non è `BEGIN`).
  ⚠️ **Fatto nuovo per Tid**: col BA che non si cancella, `trg_billing_account_z90_require_istanza_ha_ba_dlt` (un'istanza
  non resta senza BA, `E_ISTANZA_SENZA_BA`), che scatta solo alla cancellazione di un BA, non ha più un caso: da
  decidere se ritirarlo in questo giro.
* ✅ **Blocco B provato** (2026-11-26, sullo scratch, tutti i changeSet del giro insieme, coi codici simulati). La
  prova ha trovato un difetto del `-34`, corretto: l'`UPDATE` del collegamento scriveva `billing_account_id` senza
  alias, ambiguo con la colonna omonima del `RETURNS TABLE` (42702). **pgTAP adeguati al contratto nuovo**, con la
  ragione scritta sopra: `test-billing-account-auto-link-ef` (1), `test-cliente-manuale-chiave-unica-v1` (25a, 25: la
  predefinita non cambia la chiave di nessuno), `test-guard-albero-ba-omogeneo-v1` (5: la cancellazione del
  collegamento è rifiutata; 10-11: la predefinita si sposta senza toccare l'albero), `test-emittenti-fiscali` (8, 9,
  12, 13: il BA nasce collegato, il cambio d'azienda si fa modificando il collegamento), `test-istanza-nasce-col-ba-v1`
  (3, 4: `E_BA_NON_SI_CANCELLA`), `test-fn-crea-cliente-v1` (6: senza sessione il legame è alla predefinita),
  `rls/test-rls-clienti` (il secondo BA del mondo A si porta all'azienda di A modificandone il collegamento),
  `test-billing-account-guard-parent` e `script/test-fn-disdetta-cliente` (tolte le cancellazioni di BA e collegamenti:
  la seconda era una pulizia in autocommit prima del `BEGIN`). **Ritirato** `test-istanza-ba-gestore-globale-v1` (`git
  rm`): provava i quattro guard ritirati. Esito: verdi con l'estratto tutti i pgTAP del censimento (una
  quarantina, §24.7); i rossi che restano (`test-cliente-manuale-chiave-unica-v1` 1,
  `test-billing-account-guard-cf-confrontabile-v1` 1, `test-distinta-numerazione-registro-v1` 2,
  `test-rls-billing-account-returning-secondo-emittente` 1) ci sono uguali senza l'estratto: da owner, non del giro.
* ⚠️ *Superato: la documentazione, D-T4-12, apply e pgTAP sono fatti più sotto; resta solo il passaggio al BE (§24.8).*
  **Restava del giro 6**: la documentazione (la nota `_emittente-del-billing-account` da riscrivere: due livelli,
  niente movimento 4, il collegamento che non si toglie; le pagine `manual/` dei sei oggetti toccati, delle due funzioni
  nuove e delle quattro ritirate; le guide `generazione-cliente`, `emittenti-fiscali`, `fatturazione`; le tre pagine col
  nome vecchio del test della storia, le sette che citano il test ritirato); la decisione di Tid su
  `trg_billing_account_z90_require_istanza_ha_ba_dlt`; il passaggio al BE (§24.5, la lista dei collegamenti senza
  cestino, `delete_mapping`, `emittenti_fiscali_service.py`); poi apply e pgTAP (Tid). Il `-35` resta di riserva.
* ✅ **Applicato** `-26 … -40` su scratch e dbdev (letto sul `databasechangelog`, 2026-11-26). Correzioni dei pgTAP
  trovate da Tid col runner: `test-cliente-manuale-chiave-unica-v1` 25a (il BA va sulla terza azienda *dopo* la nascita
  del cliente, dentro la finestra differita: prima, come operatore, la RLS non glielo faceva più vedere, `E_CODICE`
  da `trgfn_clienti_sync_utility_from_ba`; la prova da owner non lo vede), `test-valuta-fk-billing-account-emittente-v1`
  1 (la tabella puntata per OID: `regclass::text` dipende dal `search_path`). ✅ Verdi col runner (Tid, 2026-11-26).
* ✅ **D-T4-12, il guard della cancellazione del BA sull'istanza: ritirato** (Tid, 2026-11-26), `-35`:
  `trg_billing_account_z90_require_istanza_ha_ba_dlt` e la sua funzione; restano `fn_guard_istanza_ha_ba` ed
  `E_ISTANZA_SENZA_BA` (la nascita dell'istanza). La nota di `automation_lock_columns.csv` (le due righe della coppia
  del BA) nomina ora il rifiuto della cancellazione del BA.
* ✅ **La documentazione** (2026-11-26, 51 file sotto `docs/it`, letta a campione): riscritta la nota
  `_emittente-del-billing-account`, aggiornata `_chiave-unica-cliente`, 41 pagine `manual/` (anagrafiche, script,
  vendite), creata `manual/fn_check_ba_padre`, tolte con `git rm` le cinque pagine degli oggetti ritirati, cinque guide
  (`generazione-cliente`, `emittenti-fiscali`, `soggetti-e-ruoli-anagrafici`, `gestione-delle-istanze-utility`,
  `fatturazione`). Nelle righe aggiunte nessun brief, id di changeSet o cronaca datata. Intestazioni dei pgTAP
  allineate (`test-billing-account-albero-un-livello-v1`, `test-istanza-nasce-col-ba-v1`).
* ✅ **`-41`** (scritto e provato il 2026-11-26; applicato da Tid, test verdi, lo stesso giorno): i COMMENT al presente di `fn_guard_istanza_ha_ba`,
  `fn_guard_istanza_ba_emittente`, `script.fn_get_ba_emittente_sr_id_installazione`,
  `script.fn_check_ba_cambio_emittente`, e il commento del ramo NULL nel corpo di `fn_ba_ha_storia_emittente`
  (rimandavano agli oggetti ritirati o alla regola del documento numerato).
* **Debito residuo, letto dalla revisione della doc** (non del giro): `anagrafiche/index.ci.md` (generato) linka le
  pagine `manual/` ritirate fino alla prossima rigenerazione (⚠️ chiuso: rigenerato nel commit del giro, verificato il
  2026-11-26); `script/manual/fn_check_user_can_create_ba.md` e
  `fn_get_ba_emittente_sr_id.md` fuori standard di forma (titoli, cronaca), `famiglie_documento.md` col «Vedi anche»
  malformato: vanno con T11.
* **Da girare al BE** (con §24.5): la lista dei collegamenti senza cestino (`script.fn_check_ba_cambio_emittente` col
  ramo «billing account NULL» resta finché la lista lo legge); `delete_mapping` → un `UPDATE` dell'azienda sul
  collegamento; il drawer «Gestisci billing account» non toglie più collegamenti; le pagine API in `docs/it/backend/`
  che descrivono la cancellazione di un collegamento; `emittenti_fiscali_service.py` riga 311 (nomina il guard ritirato).
* ✅ **Confermato da Tid** (2026-11-26): «il cliente si chiude annullandolo» vale come scritto nelle guide. Nel
  percorso degli stati `AN` si raggiunge solo da pre-contrattuale e attivo; un cliente sospeso o chiuso, se è stato una
  fornitura, si chiude col suo ciclo di vita.

### 24.8 Che cosa resta del giro 6 (2026-11-26)

* ✅ DB: `20261126-26 … -41` applicati su scratch e dbdev, pgTAP verdi col runner (Tid). Il range si chiude a `-41`
  (`-40` e `-41` usati: il guard della cancellazione del BA e i COMMENT al presente); nessun segnaposto avanzato.
* ✅ Commit (2026-11-26, «DB: anagrafiche giro 6 (T4)»).
* ⏳ Il passaggio al BE: §24.5 («Richiesta al team BE/FE») e §24.7 («Da girare al BE»). Il censimento applicativo:
  «censisci chi scrive o cancella `anagrafiche.emittenti_fiscali_billing_account` e chi conta sul BA senza
  collegamento, o sulla cancellazione di un BA».
* Debito residuo, non del giro: le pagine fuori forma (§24.7), con T11 (l'indice generato è già rigenerato); i casi 4-7 di
  `test-fn-lookup-utilities-per-ba` che dipendono dai dati della macchina.
* ✅ Il rosso del rubinetto degli accumulatori sul `-39`: chiuso col `-42` (2026-11-27, §24.9); la sua richiesta al BE è da girare.

### 24.9 Il rosso del rubinetto: il billing account che non c'è ha il suo codice (2026-11-27)

**Il fatto.** In CI (`scripts/codici-errore-baseline.sh`, il passo B-7) il giro 6 è rosso:
`E_PARAMETRO_INVALIDO` ha acquistato la famiglia `NOT_FOUND`. Il punto è il ramo `IF NOT FOUND` che il `-39` (S32) ha
messo in `anagrafiche.fn_lookup_utilities_per_ba`: un id ben formato che non è un billing account, o che chi chiama
non vede (la funzione è INVOKER), sollevava `E_PARAMETRO_INVALIDO`. Quel codice (`DATO_ERRATO`) copre la forma dei
parametri (NULL, `<= 0`, vuoto, fuori elenco); «la cosa indicata non esiste» è la classe `NON_TROVATO` (api.md
§Tassonomia errori). Nel catalogo non c'era un codice per il billing account non trovato. Il secondo ramo del `-39`
(il ruolo che non è quello del BA) resta `E_PARAMETRO_INVALIDO`: è un valore sbagliato del chiamante.

**Decisione di Tid** (2026-11-27): codice nuovo, non baseline allargata.

**Guide verificate** (`guide_coinvolte.py` sul `-42` e sul pgTAP, 2026-11-27): 21 guide, raccolte dagli oggetti che il
corpo nomina; nessuna descrive il lookup delle utility né i suoi rifiuti (`emittenti-fiscali`, `generazione-cliente`,
`soggetti-e-ruoli-anagrafici`, `pgtap-come-si-scrive-un-test` lette sul punto): **coerenti**. La funzione resta orfana
di guida, come al `-39`: è un dettaglio del lookup, non un concetto del dominio.

**Che cosa è scritto** (2026-11-27; applicato da Tid su scratch e dbdev, pgTAP verde col runner, `codici-errore-baseline.sh`
sullo scratch senza accumuli né rientrati, doc auto-generata rigenerata, lo stesso giorno):

* `20261126-42-update-fn-lookup-utilities-per-ba-ba-non-trovato`: il corpo vivo del catalogo (uguale al `-39`), cambiano
  il ramo `IF NOT FOUND` (`E_BILLING_ACCOUNT_NOT_FOUND`, l'id nel VARIADIC) e il COMMENT; attributi vivi invariati
  (STABLE, INVOKER, `COST 100`, `ROWS 1000`, nessuna `SET`). Firma invariata.
* `E_BILLING_ACCOUNT_NOT_FOUND` (`NON_TROVATO`) in `codici_errore.csv`, il messaggio in `messaggi_errore.csv` (id 1556).
* pgTAP `test-fn-lookup-utilities-per-ba-legge-il-ba-v1`: i test 1 e 2 asseriscono il **codice** con
  `dbops.fn_pgtap_codice_errore` (prima il testo). Prova sullo scratch (`prova_changeset.py`, con la riga del codice
  seminata nella stessa transazione): senza 2/3, con 3/3; catalogo identico dopo il `ROLLBACK`. Gli altri due pgTAP che
  nominano la funzione (`test-fn-lookup-utilities-per-ba`, `vendite/test-parametri-importo-utility-v1`) non asseriscono il
  ramo cambiato.
* `manual/fn_lookup_utilities_per_ba`: il codice nuovo nei rifiuti e nei codici errore.
* Baseline B-7 (`db/baseline-codici-errore-famiglie.tsv`), solo le righe di questo giro: `E_PARAMETRO_INVALIDO` torna
  a `ENUM,PARAMETRO,VALORE_ATTESO` (270 punti, misurati: 271 sullo scratch col `-39`, meno il ramo spostato);
  `E_BILLING_ACCOUNT_NOT_FOUND NOT_FOUND 1` aggiunta; tolte `E_ALBERO_EMITTENTE_MISTO` ed `E_ISTANZA_EMITTENTI_DIVERSI`,
  i due blu dello stesso rosso: il giro 6 ha riscritto `fn_guard_albero_ba_emittente` e `fn_guard_istanza_ba_emittente`,
  e i loro punti stanno ora sotto guardie che la misura legge IGNOTO (escono dallo scatto). Le altre differenze fra la
  baseline e lo scatto dello scratch (codici nuovi di altri cantieri, conteggi) non sono di questo giro e restano.
  ⚠️ Il confronto torna verde solo con il `-42` applicato: finché non lo è, sullo scratch il rosso resta.

**Richiesta al team BE/FE** (dopo l'apply del `-42`):

* rigenerare `error_policies_generated.py` (`./manage-env.sh genera_error_policies`): il codice nuovo è `NON_TROVATO`;
* il lookup delle utility di un BA (`GET` delle utility del billing account, `BillingAccountUtilitiesView`,
  `backend/apps/core/db/lookup_repository.py`) su un BA inesistente o fuori perimetro risponde ora **404**
  `E_BILLING_ACCOUNT_NOT_FOUND`, non più 400 `E_PARAMETRO_INVALIDO`. **Censisci chi chiama
  `anagrafiche.fn_lookup_utilities_per_ba` e chi conta su quel 400** (test, mock, rami del frontend sull'esito); i due
  file citati sono quelli noti, non l'elenco chiuso;
* `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md` (la sezione del lookup): il 404 fra le risposte.

## 25. T8 — ruoli d'impresa, conti, emittente (2026-11-26: analisi letta sul catalogo; 2026-11-27: tre giri, decisioni dei giri aperte)

Il perimetro è S12, S13, S15 (la parte che serve), S18, S54, S55, S56, S57, R-BE3 e R-BE4 (§17). S53 resta a T12. Corpi,
trigger, vincoli e COMMENT letti sul catalogo dello scratch (`zeroerp_ruoli`) il 2026-11-26, confrontati con dbdev dove
serviva; sul backend solo chi chiama, in sola lettura. Nessuna misura sui dati entra come motivo.

**La forma: T8 si divide in tre giri** (D-T8-0, ✅ decisa da Tid il 2026-11-27 come proposta, ordine compreso), come T7. Le tre famiglie non condividono oggetti e
ognuna ha le sue decisioni: **T8a** i conti bancari (S18, S55, R-BE4), **T8b** l'emittente (S54, e il §15.2
dell'emittente), **T8c** i ruoli d'impresa (S12, S13, S56, S57, R-BE3). Ordine proposto: T8c, che porta il fatto di
§25.1 e tocca gli stessi ruoli di T12; poi T8b, il più piccolo; poi T8a, il più largo.

**Guide verificate** (`scripts/guide_coinvolte.py --oggetti`, 20 oggetti, 2026-11-26):

| Guida o nota | Esito |
| --- | --- |
| [gestione-conti-bancari](../../guide/gestione-conti-bancari.md) | **coerente** col codice di oggi: i limiti di §«Che cosa il database non tiene» sono la fotografia del giro 0d (2026-11-22), non decisioni. **Indietro** per ogni proposta accettata di T8a (§«Il registro degli IBAN», §«I due legami», §«Che cosa si spegne», §«I mandati SEPA»). Se D-T8a-7 è **b**, «la validità non conta» per il predefinito diventa una decisione da scrivere |
| [emittenti-fiscali](../../guide/emittenti-fiscali.md) §1 | **sbagliata**: dice che `fn_get_emittente_fiscale_pk` e `_id` passano da una chiave all'altra dell'emittente; prendono tutte e due un `billing_account_id`. Si riscrive in T8b. §«Il codice» coerente |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md) | **coerente** (SR contro PK, conti, «ogni specializzazione controlla il tipo»). **Indietro** con S56a (il soggetto della specializzazione non si sposta, non lo dice) e §5b («punta alla specializzazione quando conta il tipo», con D-T8c-3). Il legame reseller–BA non è descritto: manca |
| [gestione-dei-pagamenti](../../guide/gestione-dei-pagamenti.md) | **coerente** sul verso diretto di PSP e canali d'incasso; **indietro** dopo S13 (un PSP con enti attivi non si spegne né si cancella) e D-T8a-5 (il verso del legame) |
| [risorse-umane-e-accessi](../../guide/risorse-umane-e-accessi.md) §«Soggetto gestore» | **coerente** («singleton»): è il codice a tenerlo debole (S57a) |
| [automazione-db](../../guide/automazione-db.md) | **coerente**: §4.8 (`CODICE_MAIUSCOLO`, base di S54c) e la riga della FK verso una UNIQUE non-PK che genera il `require_attivo` (base di D-T8c-3 e S56b) |
| nota [_emittente-del-billing-account](../../dbzero/anagrafiche/_emittente-del-billing-account.md) | **coerente**; non dice cosa fa il risolutore con un id che non è un BA (con D-T8b-1 **a** si aggiunge). ⚠️ Indietro i **COMMENT** di `script.fn_get_ba_emittente_sr_id` e `fn_get_emittente_fiscale_id` («un BA che resta senza legame», «BA esistente ma non mappato»): il `-41` del giro 6 non li ha ripresi |
| `configurazione-e-gestione-parametri`, `iva-risolutore-di-riga`, `contratto-guc-app`, `pgtap-come-si-scrive-un-test` | nessuna frase sul perimetro: **coerenti** per assenza |

**Orfani**: `resellers_billing_account` è un concetto di dominio (il reseller di una fornitura nel tempo) senza guida:
va in `soggetti-e-ruoli-anagrafici`. `vendite.fn_build_fattura_key` va nel «Vedi anche» di `fatturazione`.
`gestori_utilities` e le due funzioni del fornitore dipendono da D-T8c-8 e D-T8c-6; `trgfn_resellers_guard_attivo` è
un dettaglio interno, che si ritira se D-T8c-3 è la FK. ⚠️ Il reseller, i suoi orfani e la riga di
`soggetti-e-ruoli-anagrafici` sul legame reseller–BA sono passati a [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27).

### 25.1 Un fatto nuovo, fuori elenco: il guard di ruolo montato due volte su un database ricostruito

Riletto sul catalogo il 2026-11-26. Sullo **scratch** sei specializzazioni (`clienti`, `emittenti_fiscali`, `fornitori`,
`gestori`, `resellers`, `vettori`) hanno due trigger sulla stessa funzione di guard: `trg_<t>_guard_ruolo_<r>_ins_upd`
e il vecchio `trg_<t>_ins_upd_check_ruolo_<r>`. Su **dbdev** solo il primo. Causa: `20251205-03` fa `DROP TRIGGER IF
EXISTS trg_<t>_check_ruolo_<r>_ins_upd`, ma il nome nato dalla prima generazione è `trg_<t>_ins_upd_check_ruolo_<r>`.
Effetto: in CI e su ogni installazione nuova il guard gira due volte (innocuo, ma è una divergenza fra dev e CI, e
un pgTAP che conta i trigger di una tabella vede numeri diversi). Correzione: un changeSet in `20_code` con i sei `DROP
TRIGGER IF EXISTS` del nome vero; nessuna decisione, ma tocca clienti ed emittenti, fuori da T8: si propone nel primo
giro di T8 (T8c).

### 25.2 T8a — i conti bancari (S18, S55, R-BE4)

Esiste già: `trgfn_conti_bancari_normalize`, `uq_conti_bancari_iban`, i CHECK di IBAN, BIC e paese; su ognuno dei due
legami il guard «conto attivo» (`E_CONTO_BANCARIO`, immediato) e il REQUIRE dell'automazione ATTIVO (differito).
Nessuna delle quattro tabelle ha lock di colonna; nessuna è in `tabelle_gestibili`. pgTAP: `test-conto-incasso-un-solo-soggetto`,
`test_fn_get_conto_bancario_predefinito`, `test-conti-bancari-istanza-cascata`, `test_vw_conti_bancari_per_ruolo_gestore`,
`create-soggetto-bank-branches`; nessuno prova `E_CONTO_BANCARIO`, la normalizzazione, il guard SEPA, `uso`, il paese,
il predefinito bloccato.

| # | Il catalogo oggi | Natura | Proposta |
| --- | --- | --- | --- |
| S18a «conto attivo» in due sedi | regge: guard `BEFORE` e REQUIRE differito dicono la stessa cosa, il differito non parla mai | doppione | **D-T8a-1**: (a) una sede, l'automazione (errore al COMMIT), i due guard si ritirano; (b) restano i guard immediati e si toglie il REQUIRE. Proposta **a** |
| S18b / R-BE4 predefinito bloccato | regge: a DB niente; nel BE `ContiBancariService._guard_predefinito_bloccato`, `E_ANAG_VALIDAZIONE` | regola di dominio fuori dal DB | **D-T8a-2**: CHECK `NOT (predefinito AND bloccato)` sui due legami, codice suo. Cambia prima il DB, poi il BE ritira il guard |
| S18c `paese` | regge: il normalize lo ricava solo se NULL | difetto (derivato dell'IBAN) | **D-T8a-3**: (a) sempre ricalcolato dall'IBAN; (b) rifiutato se diverge. Proposta **a** |
| S18d `utility_id` | regge: `emittenti_fiscali_utilities.utility_id` `bigint` contro `config.utilities.id` `integer` | difetto di tipo | `ALTER … TYPE integer`; stesso difetto su `pdp.utility_id` (T3) |
| S55a IBAN sotto i legami | regge: nessun lock | difetto («un IBAN esiste una volta») | **D-T8a-4**: lock di `iban` (e `bank_branch_id`?), con quello di `conto_bancario_id` e del soggetto/ruolo sui legami |
| S55b `uso` del legame del ruolo | regge: il guard guarda solo dal lato del canale; il BE ammette `uso` in modifica | difetto (garanzia di un solo verso) | **D-T8a-5**: (a) lock di `uso` sui due legami; (b) guard solo se il legame è citato. Proposta **a**; il BE toglie `uso` dalle colonne modificabili |
| S55c soggetto del ruolo attivo | regge: il legame del soggetto ha REQUIRE e BLOCK, quello del ruolo no | asimmetria non scritta | **D-T8a-6**: righe ATTIVO REQUIRE e BLOCK fra `soggetti_ruoli` e `soggetti_ruoli_conti_bancari` (da leggere con T12) |
| S55d predefinito a scadenza | regge: gli indici del predefinito ignorano la validità | difetto di modello | **D-T8a-7**: (a) EXCLUDE sul periodo dove `predefinito`, e il lettore prende il predefinito valido oggi; (b) voluto, e si scrive |
| S55e normalize | regge: toglie solo gli spazi; il BE ricopia la normalizzazione | difetto + logica duplicata | **D-T8a-8**: via tutto ciò che non è alfanumerico da IBAN e BIC (anche delle filiali); il BE ritira la copia |
| S55f BIC | non regge alla lettera (maiuscolo e senza spazi), resta come S55e | parziale | con D-T8a-8 |
| S55g filiale e IBAN | regge: ABI e CAB di un IBAN `IT` non si confrontano con la filiale | difetto | **D-T8a-9**: guard per i paesi con la coppia nell'IBAN, oppure limite dichiarato |
| S55h ABI/CAB su due banche | regge: UNIQUE per ruolo banca | da decidere (`bank_code` è generico) | **D-T8a-10**: UNIQUE `(bank_code, branch_code)` (per paese), oppure voluto |
| S55i `iban_snapshot` del SEPA | regge: normalizzato, non confrontato col conto | voluto per lo storico, nascita non garantita | **D-T8a-11**: alla nascita e al cambio del legame vale l'IBAN del conto o NULL. Tocca `pagamenti` |
| fuori elenco: il BLOCK dello spegnimento del conto | conta anche i legami chiusi: un conto con storia non si spegne | come S57e | **D-T8a-12**: il BLOCK guarda solo i legami validi oggi o dopo |

Ricadute BE (chi cambia): `conti_bancari_service.py` (guard del predefinito, copia della normalizzazione, `uso`),
`conti_bancari_repository.py` (colonne modificabili, normalizzazione), i codici d'errore; `pagamenti` per lo snapshot.

### 25.3 T8b — l'emittente (S54, §15.2)

| # | Il catalogo oggi | Natura | Proposta |
| --- | --- | --- | --- |
| S54a `fn_get_emittente_fiscale_id` e `_pk` su un id che non è un BA | regge **anche dopo il giro 6**, provato in una transazione in sola lettura: un id inesistente riceve la predefinita | difetto, più netto col «BA sempre collegato»: i livelli 2 e 3 servono solo nell'istante del RETURNING e per l'id sbagliato. Precedente: S32 nel giro 6 | **D-T8b-1**: (a) i due involucri rifiutano un id che non è un BA (`E_PARAMETRO_INVALIDO`), con una `fn_check_*` DEFINER perché sono INVOKER e `billing_account` ha la RLS; (b) com'è. ⛔ Non nel lettore `script.fn_get_ba_emittente_sr_id`, che le policy `ef_whitelist` chiamano |
| S54b `fn_parametri_importo_utility` con un ruolo non `EF` | regge: LEFT JOIN, ripiego silenzioso sui valori di sistema | difetto | **D-T8b-2**: (a) rifiuto; (b) zero righe; (c) com'è. Proposta **a**. Chiamanti: `fn_ricalcola_totali_fattura`, `fn_lookup_utilities_per_ba`; nessuno nel BE |
| S54c il maiuscolo due volte (`a05`, `a15`) | regge, ma tutti e due chiamano `script.fn_codice_normalizzato`; `a05` deve giudicare il valore normalizzato prima del CHECK, `a15` è l'automazione | **voluto** | **D-T8b-3**: si chiude come voluto, la ragione nel commento del corpo di `a05` |
| §15.2 `varchar(10)` | regge: commento del corpo di `guard_codice_forma` e test 9 del suo pgTAP; la colonna è `varchar(32)`, il limite lo tiene il CHECK | metadato stantio | si correggono commento e ragione del test |
| §15.2 `E_EMITTENTE_DEFAULT_SINGLETON` | il guard differito parla solo per «zero predefinite»; nessun pgTAP; frase e causa NULL nel catalogo | manca test e testo | **D-T8b-4**: pgTAP costruito + frase e causa |
| §15.2 il ruolo non `EF` | nessun pgTAP del rifiuto `E_SOGGETTI_RUOLI` | manca test | con D-T8b-4 |
| S15 `trgfn_emittenti_fiscali_normalize` | `RETURN NEW` | forma | resta a T11, o si anticipa il ritiro |

Chiamanti BE di `_pk` (l'id può arrivare da una richiesta): `billing_account_repository.py`, `valuta_resolver.py`,
`billing_account_service.py`, `pratiche_repository.py`, `pipeline_repository.py`, `preventivi_repository.py`,
`contratti_repository.py`; di `_id`: `commesse_repository.py`. Con D-T8b-1 **a** cambia prima il DB.

### 25.4 T8c — i ruoli d'impresa (S13, S56, S57, R-BE3; S12 spostata)

⚠️ **Il reseller esce da T8c** (Tid, 2026-11-27): S12a-S12d, S57d, S57e, `trgfn_resellers_normalize` e il COMMENT della
tabella vanno in [brief-db-reseller](brief-db-reseller.md), aperto, non iniziato. D-T8c-2, -3, -4 si spostano lì
(D-R-2, -3, -4); D-T8c-1 resta per il solo PSP. Il guard di ruolo doppio di `resellers` (§25.1) resta qui.

Già chiuso dal giro 3: S52 (`soggetti_ruoli.tipo_ruolo_id` e `soggetto_id` bloccati). `create-soggetto-gestori.sql`
non è più nelle baseline dei rossi: la nota di §15.2 è superata.

| # | Il catalogo oggi | Natura | Proposta |
| --- | --- | --- | --- |
| ~~S12a `resellers.codice`~~ | ~~regge: NOT NULL, nessuna riga in `config.sistema_codici`, nessun generatore~~ | spostata | → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27). Resta qui la metà del PSP: **D-T8c-1**, il generatore del codice del PSP e il suo prefisso |
| ~~S12b legame reseller–BA sul periodo~~ | ~~regge: `validita` in nessun vincolo~~ | spostata | → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |
| ~~S12c `vendite.fn_build_fattura_key`~~ | ~~regge: `ORDER BY rb.id LIMIT 1` senza periodo~~ | spostata | ~~D-T8c-2~~ → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |
| ~~S12d / S57d il ruolo del legame e il verso opposto~~ | ~~regge: FK su `soggetti_ruoli`, nessun guard di ruolo~~ | spostata | ~~D-T8c-3~~ → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |
| ~~S57e lo spegnimento del reseller~~ | ~~regge: conta anche i legami chiusi~~ | spostata | ~~D-T8c-4~~ → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |
| S13 `psp` | regge: fuori da `automation_delete_block`, codice non bloccato, nessun generatore, nessun verso opposto verso gli enti d'incasso | difetto | delete block e lock del codice; **D-T8c-5**: guard su `psp.attivo` contro gli enti `PSP` attivi (la FK non si può: `enti_incasso.soggetto_ruolo_id` è polimorfica), oppure una colonna PSP dedicata con FK |
| S56a `soggetto_ruolo_id` delle specializzazioni | regge, **più largo**: non bloccato in nessuna specializzazione | difetto | lock su tutte; il BE non lo scrive in modifica |
| S56b `vendite.ddt.vettore_soggetto_ruolo_id` | regge: sola FK su `soggetti_ruoli` | difetto | FK verso `vettori(soggetto_ruolo_id)` (verificare prima che generi il `require_attivo`). Stesso disegno di T12 |
| S56c / R-BE3 le due funzioni del fornitore | regge: nessuno le chiama, e sono le sole lettrici di `config.stati_fornitore.blocca_ordini` | regola senza verbo, non codice morto | **D-T8c-6**: (a) ritirarle e la regola passa al cantiere acquisti; (b) farle chiamare dal guard degli ordini d'acquisto, correggendo il segnaposto di `E_FORNITORE_BLOCCATO` |
| S57a il gestore unico | regge: lettura con `LIMIT 1`, due inserimenti concorrenti passano; `v_existing_id integer` | difetto | indice UNIQUE su `((1))` |
| S57b la P.IVA del gestore | regge ristretta: dal giro 3 la cambia solo il SUPER_ADMIN | residuo | **D-T8c-7**: guard sul soggetto, oppure limite dichiarato |
| S57c `gestori_utilities` | regge: nessun lettore; COMMENT e nomi dei vincoli di un rinomino; `utility_id integer` | tabella senza consumatore | **D-T8c-8**: ritirarla, oppure scriverne il significato |
| S15 `vettori_normalize` | `RETURN NEW` | forma | a T11; `resellers_normalize` → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |
| COMMENT di §15.2 | ancora stantii (`RES` contro `RE` sui vettori, `rating`, i normalize) | metadati | changeSet di COMMENT al presente nel giro; quello della tabella `resellers` → [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27) |

**Riverificato sullo scratch il 2026-11-27**, prima delle decisioni: la tabella regge. Due fatti in più. Per D-T8c-1, in
`config.sistema_codici` le righe di `anagrafiche` non hanno una forma comune: `SGT-`, `VET-`, `IFO-` con il trattino,
`BAC/` con la barra, `FORN` senza separatore, tutte a 7 cifre; il COMMENT della tabella nomina il ruolo «RES». Per
D-T8c-3 il precedente c'è ed è montato: `emittenti_fiscali_billing_account` punta a `emittenti_fiscali(soggetto_ruolo_id)`
e ha il require differito e il block sul padre (nomi con l'hash), come dice §4.2 di `automazione-db`. `psp` è la sola
specializzazione senza il guard di ruolo doppio di §25.1.

Ricadute BE: `ddt_service.py`, `ddt_repository.py`, `_schema_da_contratto.py` (il vettore del DDT: codice d'errore
nuovo); `invito_portale_service.py` (commento che nomina `fn_guard_fornitore_attivo`); i codici `E_FORNITORE_*`
se D-T8c-6 è **a**. Reseller, PSP e i due legami: nessuno li scrive dal BE.

### 25.5 Le decisioni per Tid

* ✅ **D-T8-0** (Tid, 2026-11-27): tre giri, nell'ordine **T8c** (ruoli d'impresa, con il fatto di §25.1), **T8b**
  (emittente), **T8a** (conti bancari). Ogni giro ha le sue decisioni e il suo range di changeSet, e parte al via di Tid.
* ✅ Il reseller esce da T8c in [brief-db-reseller](brief-db-reseller.md) (Tid, 2026-11-27).
* Aperte, nell'ordine dei giri: T8c D-T8c-1 (solo PSP), -5 … -8 (§25.4); T8b D-T8b-1 … -4 (§25.3); T8a D-T8a-1 … -12 (§25.2). Le
  proposte sono nelle tabelle. Il fatto di §25.1 non chiede decisioni.

### 25.6 Il piano di T8 (dopo le decisioni)

* [x] Analisi sul catalogo, guide verificate, ciò che esiste già (2026-11-26, §25)
* [x] D-T8-0: tre giri, T8c, T8b, T8a (Tid, 2026-11-27)
* [ ] T8c: le decisioni, poi il giro
* [ ] T8b: le decisioni, poi il giro
* [ ] T8a: le decisioni, poi il giro
* Per ogni giro: pgTAP rosso, changeSet (range da Tid), prova sullo scratch, documentazione, apply e pgTAP (Tid),
  commit, la richiesta al BE
