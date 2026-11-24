# Brief DB — Revisione dello schema `anagrafiche`: la documentazione, le segnalazioni di codice, i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-24

**Riparte: Tid**, col commit del giro 3-bis e il passaggio al BE da girare (§20.7, sei voci). Il giro 3-bis, D-T5-6 **b** (il tipo di contatto proposto, §20.8), è chiuso: `20261123-68 … -73` applicato, pgTAP verdi, doc auto-generata rigenerata (Tid e sessione DB, 2026-11-24). Poi la sessione DB riparte con T7. Il giro 3, T5, è chiuso: `20261123-48 … -64` applicato su scratch e dbdev, pgTAP verdi come app, committato (2026-11-24). Poi T7, T4, T8, T12, T3, T10, T11. Il giro 2 (T2) è chiuso: dentro `anagrafiche` non c'è
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

**Decisioni aperte di Tid:** nessuna. D-T5-6 decisa **b** (Tid, 2026-11-24, §20.6). La porta di S50 è uscita da T7 (D-D **a**, 2026-11-23): la chiude il giro 1 del brief delle porte.
**Da committare:** il giro 3-bis (§20.8: sei changeSet, tre righe CSV, due pgTAP, manual, guide e doc auto-generata, 2026-11-24), la §19 (giro 2, 2026-11-23), le decisioni del vaglio
(§17.1, 2026-11-23), e le righe di questo brief che registrano il commit `a35a6636dc`, rimaste fuori da quel commit.

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
  * [ ] Giro 3-bis: committato
  * [ ] Giro 3: il passaggio al BE (§20.7)
  * [ ] Poi, un giro per tema nell'ordine di §17.1: T7, T4, T8, T12, T3, T10, T11
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
> [piano-be-fe-accessi-credenziale-e-vesti](piano-be-fe-accessi-credenziale-e-vesti.md) e
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
| **T9** Gli accessi | S5, S6, S22 (⚠️ tutta, §17.1), S59-S67, R-BE6 | S59: una credenziale rimasta senza vesti resta accesa per sempre. S61: l'ultimo SUPER_ADMIN si sposta senza passare da un guard | **Brief DB nuovo sugli accessi**, che porti anche **R-4** di [piano-be-fe-accessi-credenziale-e-vesti](piano-be-fe-accessi-credenziale-e-vesti.md) (la veste revocata), che aspetta un brief DB mai scritto. S67 (lo shop nasce acceso o spento) è la stessa materia di R-4 |
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
