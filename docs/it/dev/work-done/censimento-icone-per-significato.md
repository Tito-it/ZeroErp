# Censimento icone per significato

> Stato al **2026-09-27**. Documento di lavoro: si decide qui, poi si costruisce.
> Regola: **il nome della costante dice il significato, non il disegno**. Due gesti
> diversi non portano lo stesso segno, e lo stesso significato ne porta uno solo.
> Nessuna icona `'pi pi-...'` scritta a mano fuori da `core/constants.js` e
> `core/navigation.js`.

## 0. Dove siamo

> ✅ **Stato al 2026-09-27 (sera): eseguito.** Fatto in tre fasi:
>
> 1. costanti (`MANAGE_ICONS` estesa; `STATUS_ICONS` e `RECAPITO_ICONS` nuove;
>    `NAV_ICONS` con nomi di significato; `TIPO_RUOLO_ICONS` in `navigation.js`);
> 2. sostituzione per area;
> 3. costanti residue (spinner `STATUS_ICONS.CARICAMENTO`, `NO`, `AUTOMATICO`,
>    `CAMBIO_STATO`, `TAB_FISSATA`, `TRASCINA`, `SUPER_ADMIN`) e presidio
>    `frontend/src/core/icone.spec.js`.
>
> Nel frontend **nessun letterale di icona** è rimasto fuori da `constants.js` e
> `navigation.js`, tranne l'eccezione dichiarata `useLottoAzioni.js`
> (`LOTTO_AZIONE_ICONA`). Quella è in attesa di
> [brief-db-icone-azioni-per-significato.md](../work-done/brief-db-icone-azioni-per-significato.md).
>
> Regola scritta in frontend-standards §«Icone: un nome di significato, in un
> punto solo».
>
> Le tabelle sotto sono lo **storico del censimento**: i nomi di file e riga
> sono quelli del 2026-09-27 prima delle sostituzioni.

Al censimento del 2026-09-27 le icone scritte a mano nel frontend erano **366** in
**135 file**, con **111** disegni diversi.

| Blocco | Occorrenze | Stato |
| --- | --- | --- |
| Disegno che ha già una costante **e** stesso significato | 84 | ✅ sostituite (62 file, lint + 406 test + build verdi) |
| Disegno che ha già una costante **ma** significato diverso | 129 | ⏸ lasciate, elencate in §2 |
| Disegno senza costante | 153 | ⏸ censite in §3 |

Prima del censimento, fuori da questo conteggio:

- `MANAGE_ICONS.ROW_EXPAND` / `ROW_COLLAPSE`: `chevron-right` / `chevron-down`,
  la coppia del toggler di riga PrimeVue.
- «Espandi tutte» di `useListaAzioni` e i gruppi della sidebar la usano.
- I toggler di riga scritti a mano nei drawer sono stati allineati.

### 0.1 Sostituzioni che hanno cambiato l'icona a video

In questi punti il disegno di prima **non** corrispondeva al significato:

| Punto | Prima → dopo | Chiave |
| --- | --- | --- |
| SoggettoDrawer:484, ContattiSoggettoDrawer:122 | `pi-users` → `pi-id-card` | CONTATTI |
| ArticoloDrawer:363 «Riattiva» | `pi-check` → `pi-replay` | RIATTIVA |
| DefinizioniWorkflowListView:157 «Pubblica» | `pi-check` → `pi-check-circle` | PUBLISH |
| CommessaGestioneDrawer:740 annulla voce manuale | `pi-ban` → `pi-times-circle` | ANNULLA |
| DashboardCompetenzaView:2298 documenti trattenuti da un lotto | `pi-lock` → `pi-server` | LOTTO |

### 0.2 Chiuse nella revisione del 2026-09-27

Casi emersi dalla revisione delle modifiche: decisi applicando una regola già
scritta, o da Tid dove indicato:

| Punto | Decisione | Regola |
| --- | --- | --- |
| ReadonlyBadge «Modalità consultazione» | `MANAGE_ICONS.INSPECT` → `STATUS_ICONS.SOLA_LETTURA` (nuova, stesso `pi-eye`) | una spia non prende in prestito un gesto (testa di `STATUS_ICONS`) |
| TestResolverDialog, stadi non applicabili | colore `--app-severity-danger` → `--app-text-muted`; la spia dei tre stadi vive in `spiaStadio()` | `NON_APPLICABILE` non è un fallimento |
| DocumentoInternoDrawer, InventarioPianoDialog: «nessuna riga» | `MANAGE_ICONS.RIGHE` → `STATUS_ICONS.VUOTO` | stato vuoto generico, come DistintaDrawer |
| ProcessoDrawer «Crea identità» | `ADD` (la proposta «`ADD` (decidere)» di §3 è approvata con il resto) | — |
| `MANAGE_ICONS.INDIRIZZI` / `NAV_ICONS.INDIRIZZO` | restano due chiavi con lo stesso valore: la prima ripete la voce di menu, come `SOGGETTO` | frontend-standards §«dove vive il nome di un'icona» |
| `MANAGE_ICONS.UOM` | icona composta box+cog → `pi-arrows-h`, il segno della voce di menu `NAV_ICONS.UNITA_MISURA`; tolto il CSS `.app-nav-icon-uom` (supera D10) | **Tid 2026-09-27** |
| PraticheHome, categoria `COMMERCIALE` | carrello (uguale a `VENDITE`) → `MANAGE_ICONS.COMMERCIALE` = `pi-address-book` | **Tid 2026-09-27**: due categorie, due segni; glifo scelto in revisione |
| Dominio `contabilita` nella sidebar | ritirato (segnaposto senza rotte né voci): tolti `DOMAINS`/`DOMAIN_MENUS`, `NAV_ICONS.CONTABILITA` e `nav.contabilita` | **Tid 2026-09-27** |

## 1. Decisioni per Tid

> ✅ **2026-09-27: Tid approva tutto**: T1-T12 con le proposte in tabella, §2,
> e §3 per intero (costanti nuove, conflitti, casi di §3.3, `STATUS_ICONS`,
> problemi preesistenti §3.6). Scelte fissate: T4 `NUMERA` = `pi-hashtag`,
> T8 RESELLER = `pi-megaphone`, T9 CAP = `pi-map-marker`, T10 categorie clienti
> tengono `pi-tags` e `LOTTO_MAGAZZINO` → `pi-barcode`.

Ciascuna decisione sblocca un gruppo di sostituzioni.

| # | Domanda | Proposta |
| --- | --- | --- |
| T1 | «Registra» la sistemazione (SistemazioneDrawer:522) ha la spunta; per significato è REGISTRA, che è il lucchetto | Passare a REGISTRA |
| T2 | Evento `ACCREDITO_ANNULLATO` (severity.js:166) ha `pi-ban` (DISATTIVA); per significato è UNDO | Passare a UNDO |
| T3 | «Approva mese» / «approva tutte» (DashboardCompetenzaView:2205, CommessaGestioneDrawer:1040) hanno `pi-check-circle`; APPROVE è `pi-check` | Passare ad APPROVE |
| T4 | Verbo «numera» dei lotti: `pi-lock` in LottiListView:673, `pi-verified` in useLottoAzioni:80 | Un'unica costante `NUMERA`; il disegno lo decide Tid (il valore arriva anche dal catalogo DB) |
| T5 | Titolo drawer commessa in lineage (CommessaDrawer:70) ha `pi-sitemap` (BOM); COMMESSA è `pi-briefcase` | Passare a COMMESSA |
| T6 | Togli filtro di collegamento (FattureSearchTable:178) ha `pi-times`; il significato è vicino a FILTRI_PULISCI | Passare a FILTRI_PULISCI |
| T7 | `pi-inbox` vale sia lo stato vuoto sia la coda lavori (C1) | Tenerli entrambi sul vassoio |
| T8 | `pi-shop`: ruolo RESELLER o attiva accesso shop (C12) | ACCESSO_SHOP tiene `pi-shop`, RESELLER → `pi-megaphone` |
| T9 | Glifo per CAP (oggi `pi-inbox`, C1) | Da decidere |
| T10 | `pi-tags` = `LOTTO_MAGAZZINO` **e** categorie clienti (P3) | Da decidere |
| T11 | `pi-replay` = `RIATTIVA` **e** `CORREZIONE` dentro MANAGE_ICONS (P4) | RIATTIVA → `pi-power-off` |
| T12 | Icone di stato: gruppo separato `STATUS_ICONS` (§3.4) con `ERRORE` e `ATTESA` spostate lì | ✅ **Approvato da Tid 2026-09-27** |

## 2. Lasciati dalla sostituzione (129): stesso disegno, significato diverso

Raggruppati per significato. Molti si risolvono con le costanti nuove di §3.
La colonna «Costante proposta» rimanda lì.

| Significato | Punti | Costante proposta |
| --- | --- | --- |
| Sposta su / giù (riordino) | ListaPresetColonneDrawer:261/269 · DashboardWidgetModal:191/199 | `SPOSTA_SU` / `SPOSTA_GIU` |
| Periodo precedente / successivo | DashMesiSidebar:36 · DashMeseStepper:36 | `PRECEDENTE` / `SUCCESSIVO` |
| Accesso negato (403) | GestionePersonalizzazioniListeView:77 · PersonalizzazioniListeTecnicheView:58 · router/index.js:608 · ConfigurazioneDocumentiView:38 · ApprovazioniPrezzoListView:254 | `STATUS_ICONS.VIETATO` (`pi-lock`) |
| Stato vuoto «tutto a posto» | DashEmptyState:20 · CodaRigheSearchTable:239 · EccedenzeSearchTable:155 · RateFuoriCapienzaSearchTable:163 · LottoDrawer:1797/1803/1929 · FondiFatturaDaDecidereTab:321 · ApprovazioniPrezzoListView:258 · DashboardCompetenzaView:2408/2772/2884/2949 · FatturaDrawer:811 · PreventiviSmistamentoDialog:265 | `STATUS_ICONS.TUTTO_OK` |
| Stato vuoto generico | HomeView:217 · FattureSearchTable:289 · DistinteSearchTable:221 · DistintaDrawer:695 · LottiListView:980 | `STATUS_ICONS.VUOTO` |
| Esito diagnosi ok / non applicabile | TestResolverDialog:332/345×2/357×2/372×2 | `STATUS_ICONS.OK` / `NON_APPLICABILE` |
| Spia booleana sì (default, esposto, regolare, compilato) | ListaPresetPanel:183 · ArticoloBomDrawer:681 · IndirizzoSoggettoForm:84 · SituazioneMerceContenuto:329 · SituazioneMerceBar:127 | `STATUS_ICONS.SI` |
| Spia bloccato / non disponibile / serve autorizzazione | IndirizzoSoggettoForm:85 · PraticaPercorso:288/346 · ComponentiPanel:466 · CommessaGestioneDrawer:1096 | `STATUS_ICONS.BLOCCATO` |
| Stato chiuso / scartato / natura bloccata | PraticaPercorso:342 · useAzioniRigaContabile:65 · SoggettoResolver:246 | `STATUS_ICONS.ESCLUSO` |
| Stato «superato» | PreventiviDrawer:908 | `STATUS_ICONS.SUPERATO` |
| Ripristina i default | DashboardWidgetModal:214 · ListaColonneModal:283 | `RIPRISTINA_DEFAULT` |
| Riprova / rilancia / rimetti in coda | PraticaPercorso:220/285/358 · CodaLavoriTab:154 · useLottoAzioni:63 | `RIPROVA` |
| Rigenera | useLottoAzioni:62 | `RIGENERA` |
| Reinvia invito | PortaleAccessoPanel:229/292 | `INVITA` |
| Annulla un lavoro in attesa | CodaLavoriTab:146 | `ANNULLA` (decidere) |
| Togli dall'elenco (file caricato, riga d'archivio) | DocumentoEmissioneDialog:271 · useCodaArchiviazione:155 | `TOGLI` |
| Svuota campo / conversazione | SearchDrawer:264 · AiAssistantDrawer:95 | `SVUOTA` |
| Revoca sessione / sessioni | SessioniAttivePanel:151/190 | `REVOCA` |
| Sessioni attive (titolo) | SessioniAttivePanel:144 | `SESSIONI` |
| Escludi / ripristina eccezione di listino | ContrattoRigheDrawer:933/945/957 | `ESCLUDI` / `RIPRISTINA_LISTINO` |
| Usa il prezzo di listino | PreventiviRigaForm:509 | `RIPRISTINA_LISTINO` |
| Riallinea prezzo | CommessaGestioneDrawer:701 | `RIALLINEA` |
| Riporta residui | DashboardCompetenzaView:2802 | `RIPORTA` |
| Riporta a bozza | useLottoAzioni:83 | `RIPORTA_A_BOZZA` |
| Rinuncia alla riconsegna | ResoRiconsegnaDialog:223 | `RINUNCIA` |
| Genera documento di riconsegna | ResoRiconsegnaDialog:229 | `GENERA_DOCUMENTO` |
| Richiedi approvazione L2 | L2ErrorBanner:41 | `RICHIEDI_APPROVAZIONE` |
| Invia messaggio chat AI | AiAssistantDrawer:201 | `SEND` (decidere se il significato si allarga) |
| Anteprima (email, variazione) | EmailTemplateDrawer:179 · ApplicaVariazioneDialog:152 | `ANTEPRIMA` |
| «Vedi novità» del preset (modale modificabile) | ListaConfigurabile:766 | `NOVITA` |
| Apri il passo / pratica selezionata | PraticaPercorso:264/272/350 · PraticheDashboard:462 | `NAV_ICONS.PRATICHE` / `APRI` |
| Apri preventivo | iscrizioni.js:152 | `NAV_ICONS.PREVENTIVI` |
| Contesto prezzi da contratto | PreventiviDrawer:919 | `CONTRATTI` |
| Ristampa fedele | DocumentiGeneratiSorgenteList:135 | `STAMPA` |
| Registro della riga | CommessaGestioneDrawer:643 | `GIORNALE` |
| Usa questo indirizzo | IndirizziSoggettoDrawer:415 | `SELEZIONA` |
| Crea identità / nuovo soggetto | ProcessoDrawer:416 · PraticaDrawer:430 | `ADD` (decidere) |
| Genera codice fiscale | SoggettoForm:252 | `GENERA` |
| Imposta contesto | DetailActions:23 | `IMPOSTA_CONTESTO` |
| Avvia e completa (passo automatico) | FlussoDrawer:227 | `ESEGUI` |
| Titoli di drawer / sezione (processo, template email, preset, flusso, pratiche «continua») | ProcessoDrawer:307 · EmailTemplateDrawer:136 · ListaPresetDrawer:194 · FlussoDrawer:400 · PraticheHome:178 | icona della cosa (`NAV_ICONS.*`) |
| Scheda «fondi da decidere» | ToolFatturazioneView:64 | `FONDI` |
| Spia «tool usati» AI | AiAssistantDrawer:170 | `STRUMENTI_AI` |
| Badge «figlio di» (BA padre) | BillingAccountLookup:120 | `GERARCHIA` |
| Indirizzo dell'istanza | IstanzaUtilityLookup:142 | `INDIRIZZI` (decidere) |
| Filiale banca | ContiBancariDrawer:198 | `RECAPITO_ICONS.FILIALE` |
| Formato CSV | ExportDialog:36 | `FORMATO_CSV` |
| File caricato in attesa | DocumentoEmissioneDialog:267 | `ALLEGATI` |
| Ruolo VENDITORE | stores/context.js:8 | vedi §3.1d |
| Direzione lineage (ramo inverso, origine) | LineagePassaggiContenuto:169 · DocumentoCollegamentiBar:136/137 | `CORREZIONE` / `DOC_ORIGINE` |
| Eventi di giornale (pratica generata, cambio stato, flusso creato, sospensione chiusa, riga ritirata, riga riportata) | severity.js:137/138/141/142/147/163/164 | valori da costanti (§3.4 nota) |

## 3. Censimento dei disegni senza costante (153)

### 3.0 Riepilogo

| Voce | Numero |
| --- | --- |
| Occorrenze censite | 153 |
| → a una costante **nuova** | 116 |
| → a una chiave **già esistente** (MANAGE_ICONS / NAV_ICONS) | 36 |
| → da togliere (glifo inesistente) | 1 |
| Costanti nuove proposte | **62** (45 MANAGE_ICONS, di cui 11 «guscio dell'app»; 1 NAV_ICONS; 4 TIPO_RUOLO; 5 RECAPITO; 7 STATUS_ICONS) |
| Conflitti «stesso disegno, significati diversi» | **17** |
| Significati uguali resi con disegni diversi | **11** |
| Occorrenze di stato/esito (→ STATUS_ICONS) | **28** |
| Casi da lasciare | **1** (più 3 note «icona della cosa» facoltative) |

---

### 3.1 Significati distinti → costante proposta

#### 3.1a MANAGE_ICONS — azioni e concetti di dominio (34 costanti)

| Costante | Disegno proposto | Occorrenze (file:riga) | Significato |
| --- | --- | --- | --- |
| `RICERCA` | `pi pi-search` | pagamenti/components/DistintaRigaForm.vue:438 · pagamenti/components/RatePickerDialog.vue:399 · amministrazione/components/EmittenteFiscaleDrawer.vue:319 · anagrafiche/components/FornitoreDrawer.vue:267 · amministrazione/components/OperatoreDrawer.vue:402 · anagrafiche/components/ClienteDrawer.vue:428 · anagrafiche/components/SoggettoResolver.vue:202 · core/components/SearchHint.vue:15 · core/components/AppTopbar.vue:195 · core/components/AppTopbar.vue:378 | Cercare (aprire un resolver, la ricerca globale, l'invito «esegui una ricerca»). È la «RICERCA» che il commento di `FILTRI` nomina ma che non ha chiave. Assorbe `NAV_ICONS.SEARCH` (stesso valore, nome di disegno). |
| `VAI_A` | `pi pi-external-link` | pratiche/views/PraticheDashboard.vue:466 · amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:371 · core/bersaglioGesto.js:104 (ripiego) · core/components/AiAssistantDrawer.vue:145 · core/components/details/DetailActions.vue:30 | Portare a un'altra vista/scheda. ⚠️ Solo come **ripiego**: dove la destinazione ha un'icona sua, vale quella (regola di `bersaglioGesto`). |
| `FATTURA_GENERA` | `pi pi-file-export` | vendite/views/DashboardCompetenzaView.vue:1823 · :2226 · :2507 | Il verbo «Fattura» (gruppo, mese, selezionati): genera documenti di fattura. Distinto da `FATTURE` (la lista) di proposito: uno è un posto, l'altro un gesto. |
| `STAMPA` | `pi pi-print` | strumenti/components/CodaStampaTab.vue:107 · strumenti/views/CodeLavoroView.vue:64 · core/components/CodeLavoroDrawer.vue:135 · vendite/composables/useLottoAzioni.js:81 (ristampa) | La stampa: la coda di stampa e il gesto che vi finisce dentro (ristampa). Stesso concetto, nessun conflitto. |
| `SOSPENDI` | `pi pi-pause` | pratiche/components/PraticaDrawer.vue:314 · pagamenti/composables/useAzioniRigaContabile.js:64 · core/utils/severity.js:146 | Messa da parte in attesa di risoluzione (pratica, riga contabile, evento di giornale). Coppia naturale con `PLAY` (riprendi). Coincide con `NAV_ICONS.CODA_SOSPESE`. |
| `ABBINA` | `pi pi-link` | pagamenti/composables/useAzioniRigaContabile.js:63 | Legare l'incasso alla rata. Coincide con `NAV_ICONS.CODA_ABBINARE`. |
| `DERIVATO` | `pi pi-arrow-down-right` (nuovo) | pratiche/components/PraticaDrawer.vue:459 · vendite/preventivi/components/PreventiviForm.vue:153 | Hint «valore ricavato dal contesto» (istanza derivata dal BA/dalla pratica). Oggi porta `pi-link`, che è ABBINA: vedi conflitto C3. |
| `ALLEGATI` | `pi pi-paperclip` | documenti/components/DocumentoEmissioneDialog.vue:240 · documenti/components/DocumentiGeneratiSorgenteList.vue:144 · core/utils/severity.js:145 | Allegare file a un documento / evento «allegato aggiunto». |
| `PREFERITI` | `pi pi-star` | core/components/AppTopbar.vue:226 · core/views/HomeView.vue:146 · core/views/HomeView.vue:179 | I preferiti dell'operatore (menu, pannello Home, stato vuoto). |
| `PREFERITO_ATTIVO` | `pi pi-star-fill` | core/components/FavoriteItem.vue:72 | «È nei preferiti» (il clic lo toglie). Coppia di `PREFERITI`. |
| `PREDEFINITO` | `pi pi-thumbtack` (nuovo) | amministrazione/components/EmittenteFiscaleBillingAccountTab.vue:254 | Il valore che vale quando non si dice altro (mapping di default). Oggi `pi-star` = PREFERITI: conflitto C4. |
| `SBLOCCA` | `pi pi-key` | vendite/components/CommessaGestioneDrawer.vue:725 · vendite/views/DashboardCompetenzaView.vue:1847 (oggi `pi-unlock`) | Togliere un blocco. La chiave è già motivata nel codice: un lucchetto aperto su un bottone si legge come STATO «aperto». |
| `APRI` | `pi pi-lock-open` | pratiche/components/PraticaDrawer.vue:304 | Transizione BOZZA→APERTA. Coppia simmetrica di `CLOSE` (`pi-lock`); libera solo se SBLOCCA passa alla chiave (D1). |
| `AVANZA` | `pi pi-forward` | vendite/composables/useLottoAzioni.js:59 | Avanzare di uno step la pipeline del lotto (già distinto da `rigenera` di proposito). |
| `INVITA` | `pi pi-envelope` | portale/components/PortaleAccessoPanel.vue:221 · portale/components/PortaleAccessoPanel.vue:284 (oggi `pi-shopping-cart`) · amministrazione/components/OperatoreDrawer.vue:538 | Inviare/reinviare un invito (portale, shop, operatore). L'invito È un'email: condivide il glifo col recapito email, come `REGISTRA`/`CLOSE` condividono il lucchetto. |
| `ACCESSO_SHOP` | `pi pi-shop` | portale/components/AttivaAccessoShopButton.vue:54 (oggi `pi-shopping-bag`) | Attivare l'accesso allo shop. `pi-shopping-bag` è `NAV_ICONS.ACQUISTI`: conflitto C12. |
| `ACCESSI_WEB` | `pi pi-sign-in` (nuovo) | portale/components/WebAccessiDrawer.vue:58 · portale/components/WebAccessiBadge.vue:61 | Gli accessi al portale web di un soggetto. Oggi `pi-globe` = geografia (NAV) e lingua: conflitto C7. |
| `TEST_PREZZO` | `pi pi-bullseye` (nuovo) | vendite/components/ListiniSearchTable.vue:215 (oggi `pi-calculator`) · vendite/components/TestResolverDialog.vue:254 (oggi `pi-search`) | Lo strumento diagnostico «quale prezzo colpisce questo contesto»: apertura ed esecuzione devono portare lo stesso segno (D5). |
| `TEST_CONNESSIONE` | `pi pi-wifi` | amministrazione/components/EmailAccountDrawer.vue:278 | Provare la connessione di un account email. |
| `VARIAZIONE_PREZZO` | `pi pi-percentage` | vendite/components/VersioneDrawer.vue:92 | Variazione percentuale dei prezzi di una versione di listino. Assorbe `NAV_ICONS.PERCENTAGE` (nome di disegno, oggi senza lettori). |
| `RIGHE_DA_RATE` | `pi pi-file-import` (nuovo) | pagamenti/components/DistintaDrawer.vue:301 | Generare righe della distinta scegliendole dalle rate. Oggi `pi-list-check` = `NAV_ICONS.INVENTARI`: conflitto C15. |
| `ESITI` | `pi pi-chart-line` (nuovo) | vendite/components/FatturazioneEsitiPanel.vue:143 | Pannello esiti del giro di fatturazione. Oggi `pi-chart-bar` = `NAV_ICONS.DASHBOARD_COMPETENZA`: conflitto C13. |
| `ARCHIVIA` | `pi pi-folder-plus` (nuovo) | strumenti/composables/useCodaArchiviazione.js:45 (`ICONA_ARCHIVIA`) | Togliere una riga dalla coda viva mettendola in archivio. Coppia con `ARCHIVE` (`pi-folder-open`, apri l'archivio). Oggi `pi-inbox` = CODE_LAVORO: conflitto C1. La costante locale `ICONA_ARCHIVIA` ha già nome di significato: va solo spostata. |
| `MODALITA_TECNICA` | `pi pi-code` (nuovo) | pratiche/views/PraticheDashboard.vue:478 (ramo off) | Riesporre il plumbing del motore (super-admin). Oggi `pi-wrench` = `NAV_ICONS.STRUMENTI`: conflitto C9. |
| `NASCONDI_TECNICO` | `pi pi-eye-slash` | pratiche/views/PraticheDashboard.vue:478 (ramo on) | Rinascondere il plumbing. Coppia con `INSPECT` (`pi-eye`). |
| `PRIORITA` | `pi pi-flag` | core/utils/severity.js:139 | Evento «priorità cambiata». |
| `ACCREDITO` | `pi pi-money-bill` | core/utils/severity.js:165 | Accredito richiesto al cliente (registro commessa). ⚠️ coincide con `NAV_ICONS.ECCEDENZE` (vedi C18). |
| `DOC_ORIGINE` / `DOC_DESTINAZIONE` | `pi pi-arrow-circle-left` / `pi pi-arrow-circle-right` (nuovi) | vendite/_shared/lineage/DocumentoCollegamentiBar.vue:137 | Direzione di un collegamento nella lineage (← origine, → destinazione). Il ramo inverso (`pi-replay`) è già `CORREZIONE`: stesso significato, usare la chiave. Oggi `pi-arrow-left` = `BACK`: conflitto C5. |
| `PRECEDENTE` / `SUCCESSIVO` | `pi pi-angle-left` / `pi pi-angle-right` | core/components/dash/DashMesiSidebar.vue:26 · core/components/dash/DashMeseStepper.vue:24 (e le gemelle `chevron-right` a DashMesiSidebar.vue:36 e DashMeseStepper.vue:36, fuori elenco perché il disegno ha già chiave) | Periodo precedente/successivo (anno, mese). Stessi glifi del paginator PrimeVue. Oggi `chevron-right` = `ROW_EXPAND`: conflitto C21. |
| `SPOSTA_SU` / `SPOSTA_GIU` | `pi pi-arrow-up` / `pi pi-arrow-down` | core/components/ListaColonneModal.vue:252 · :261 | Riordinare le colonne. |
| `FORMATO_XLSX` | `pi pi-file-excel` | core/components/ExportDialog.vue:37 | Formato di export Excel. ⚠️ Il CSV accanto usa `pi-file` = `FAMIGLIA_DOCUMENTO`: proporre `FORMATO_CSV: 'pi pi-file-o'` o simile. |

(Le righe «A / B» sono coppie e contano 2 costanti: in tutto 34 costanti in questa tabella, più le 11 del guscio = 45 in MANAGE_ICONS.)

#### 3.1b MANAGE_ICONS — «guscio dell'app» (11, eventualmente sezione separata `SHELL_ICONS`)

| Costante | Disegno | Occorrenze | Significato |
| --- | --- | --- | --- |
| `MENU` | `pi pi-bars` | core/components/AppTopbar.vue:268 | Hamburger (apri menu su mobile). |
| `LOGOUT` | `pi pi-sign-out` | core/components/AppTopbar.vue:411 | Esci. |
| `LINGUA` | `pi pi-language` (nuovo, oggi `pi-globe`) | core/components/AppTopbar.vue:232 | Cambio lingua. `pi-language` esiste e libera il globo (C7). |
| `TEMA_CHIARO` / `TEMA_SCURO` | `pi pi-sun` / `pi pi-moon` | core/components/AppTopbar.vue:238 | Passa a tema chiaro/scuro. |
| `SIDEBAR_ESPANDI` / `SIDEBAR_COMPRIMI` | `pi pi-angle-double-right` / `pi pi-angle-double-left` | core/components/AppSidebar.vue:75 | Espandi/comprimi la sidebar. |
| `FINESTRA_ESPANDI` / `FINESTRA_RIDUCI` | `pi pi-window-maximize` / `pi pi-window-minimize` | core/components/AiAssistantDrawer.vue:98 | Ingrandisci/riduci il widget. |
| `AFFIANCA` | `pi pi-objects-column` | core/components/ContentTabs.vue:166 | Affianca due tab (split view). |
| `SCAMBIA` | `pi pi-arrow-right-arrow-left` (nuovo, oggi `pi-arrows-h`) | core/components/SplitReadonlyPanel.vue:55 | Scambia i due pannelli. `pi-arrows-h` è `NAV_ICONS.ARROWS_H` = unità di misura: conflitto C11. |

#### 3.1c NAV_ICONS — entità / funzioni con una «porta» (1)

| Costante | Disegno | Occorrenze | Significato |
| --- | --- | --- | --- |
| `ASSISTENTE_AI` | `pi pi-microchip-ai` | core/components/AiAssistantDrawer.vue:90 · :124 · :179 · core/components/AppTopbar.vue:218 · :388 | L'assistente AI: pulsante topbar, voce menu mobile, header e avatar del widget. È una «porta» dell'app → sta in NAV_ICONS. |

#### 3.1d TIPO_RUOLO_ICONS — tipo di ruolo del soggetto (4 nuove + 2 già in NAV)

Oggi mappa locale `TIPO_RUOLO_ICONS` in `stores/context.js` (nome già di significato, ma lontano dalle altre costanti). Proposta: spostarla accanto a `NAV_ICONS` in `core/navigation.js`, riusando le chiavi di navigazione dove esistono.

| Ruolo | Oggi | Proposta | Occorrenza |
| --- | --- | --- | --- |
| CLIENTE | `pi pi-user` | `NAV_ICONS.CLIENTI` (esistente) | stores/context.js:6 |
| FORNITORE | `pi pi-truck` | `NAV_ICONS.FORNITORI` (esistente) | stores/context.js:7 |
| DISTRIBUTORE | `pi pi-share-alt` | `pi pi-share-alt` | stores/context.js:9 |
| RESELLER | `pi pi-shop` | **Decisione di Tid** (C12): `pi-shop` va o al RESELLER o ad `ACCESSO_SHOP`. Proposta: lo tiene ACCESSO_SHOP (è un gesto visibile a più persone) e RESELLER passa a `pi pi-megaphone` (chi rivende/promuove) | stores/context.js:10 |
| VETTORE | `pi pi-car` | `pi pi-truck` (liberato dal fornitore: il vettore è chi trasporta) | stores/context.js:11 |
| BANCA | `pi pi-building-columns` | `pi pi-building-columns` (= CANALI_INCASSO: concetto «banca» condiviso, accettabile) | stores/context.js:12 |
| (ripiego) | `pi pi-user` | `MANAGE_ICONS.SOGGETTO` | stores/context.js:44 |

⚠️ Fuori elenco ma nella stessa mappa: `VENDITORE: 'pi pi-briefcase'` = `MANAGE_ICONS.COMMESSA`. Conflitto preesistente.

#### 3.1e RECAPITO_ICONS — tipo di recapito/identificativo in una scheda (5)

Icone di **campo**, non di gesto: vanno nominate (sono ripetute nelle card contatti e conti) ma non in MANAGE_ICONS.

| Costante | Disegno | Occorrenza | Significato |
| --- | --- | --- | --- |
| `EMAIL` | `pi pi-envelope` | anagrafiche/components/ContattiSoggettoDrawer.vue:139 | Indirizzo email |
| `TELEFONO` | `pi pi-phone` | anagrafiche/components/ContattiSoggettoDrawer.vue:140 | Telefono fisso |
| `CELLULARE` | `pi pi-mobile` | anagrafiche/components/ContattiSoggettoDrawer.vue:141 | Cellulare |
| `PEC` | `pi pi-at` | anagrafiche/components/ContattiSoggettoDrawer.vue:142 | PEC (⚠️ `pi-at` = `NAV_ICONS.AT` = account email, C23) |
| `BIC` | `pi pi-building-columns` (oggi `pi-code`) | anagrafiche/components/ContiBancariDrawer.vue:197 | Codice BIC/SWIFT della banca. Libera `pi-code` per `MODALITA_TECNICA`. |

---

### 3.2 Conflitti

#### 3.2a Stesso disegno, significati diversi (17)

| # | Disegno | Significati in collisione | Chi tiene il disegno | Disegno per l'altro |
| --- | --- | --- | --- | --- |
| C1 | `pi-inbox` | (a) CODE_LAVORO (nav, badge topbar, tab); (b) stato vuoto (12 punti); (c) ARCHIVIA (verbo in coda); preesistenti: `NAV_ICONS.DASHBOARD_BACKLOG`, `NAV_ICONS.CAP` | **VUOTO** (convenzione universale, 12 punti) e **CODE_LAVORO** convivono: la coda è un «vassoio», lo stato vuoto è un vassoio vuoto al centro di un'area con testo — mai un gesto. **Decisione di Tid** se si vuole separarli del tutto. | ARCHIVIA → `pi-folder-plus`; DASHBOARD_BACKLOG → `pi-chart-line`? (⚠️ se ESITI la prende, `pi-calendar-clock`); CAP → `pi-hashtag`? no (NUMERAZIONE): proposta `pi-envelope`? no (EMAIL) → **decisione Tid** |
| C2 | `pi-search` | ricerca / «dettaglio» di un lavoro in coda (CodaLavoriTab:139) / «esegui test» prezzo | RICERCA | dettaglio → `INSPECT` (`pi-eye`); esegui test → `TEST_PREZZO` |
| C3 | `pi-link` | ABBINA (incasso↔rata) / hint «valore derivato» | ABBINA (ha la voce di nav) | DERIVATO → `pi-arrow-down-right` |
| C4 | `pi-star` | PREFERITI / PREDEFINITO (mapping di default) | PREFERITI | PREDEFINITO → `pi-thumbtack` |
| C5 | `pi-arrow-right` / `pi-arrow-left` | push a commessa / direzione lineage / apri contratto esistente / (`BACK` = indietro) | `BACK` tiene `pi-arrow-left` | push → `SEND`; lineage → `pi-arrow-circle-left/right`; apri contratto → `CONTRATTI` |
| C6 | `pi-user` | ruolo CLIENTE / operatore (avatar AI) / assegnazione / soggetto risolto (banner) / ripiego ruolo | `NAV_ICONS.OPERATORE` | CLIENTE → `NAV_ICONS.CLIENTI`; assegnazione → `ASSIGN`; soggetto → `SOGGETTO` |
| C7 | `pi-globe` | provincia/regione/stato (nav) / accessi web portale / lingua | geografia (nav) | ACCESSI_WEB → `pi-sign-in`; LINGUA → `pi-language` |
| C8 | `pi-table` | TABELLE/matrici (nav config) / colonne e preset delle liste | TABELLE | colonne/preset → `NAV_ICONS.PERSONALIZZAZIONI_LISTE` (le tre viste stanno sotto quella voce) — ⚠️ che però collide con UBICAZIONI (P2) |
| C9 | `pi-wrench` | dominio STRUMENTI / modalità tecnica / pagina «in costruzione» | STRUMENTI | MODALITA_TECNICA → `pi-code`; IN_COSTRUZIONE → `pi-hammer` |
| C10 | `pi-key` | SBLOCCA (proposto) / `NAV_ICONS.KEY` = voce «Operatori» | SBLOCCA | voce Operatori → `NAV_ICONS.OPERATORE` (`pi-user`), che esiste già e oggi non la usa |
| C11 | `pi-arrows-h` | scambia pannelli / unità di misura (nav) | unità di misura | SCAMBIA → `pi-arrow-right-arrow-left` |
| C12 | `pi-shopping-cart` / `pi-shopping-bag` / `pi-shop` | VENDITE / ACQUISTI (nav) / invito shop / attiva shop / ruolo RESELLER | VENDITE, ACQUISTI | invito shop → `INVITA`; ACCESSO_SHOP → `pi-shop`, e RESELLER cambia (decisione Tid) |
| C13 | `pi-chart-bar` | DASHBOARD_COMPETENZA (nav) / pannello esiti fatturazione | DASHBOARD_COMPETENZA | ESITI → `pi-chart-line` |
| C14 | `pi-calculator` | CONTABILITA (dominio) / test prezzo | CONTABILITA | TEST_PREZZO → `pi-bullseye` |
| C15 | `pi-list-check` | INVENTARI (nav) / righe da rate | INVENTARI | RIGHE_DA_RATE → `pi-file-import` |
| C16 | `pi-truck` | FORNITORE (ruolo) / (proposto) VETTORE | VETTORE | FORNITORE → `NAV_ICONS.FORNITORI` |
| C17 | `pi-chevron-right` | ROW_EXPAND / periodo successivo | ROW_EXPAND | PRECEDENTE/SUCCESSIVO → `pi-angle-left/right` |

Da tenere d'occhio (non contati fra i 17: accettabili o solo visivi):
- **C18** `pi-money-bill`: ACCREDITO (evento) vs `NAV_ICONS.ECCEDENZE`. L'eccedenza diventa credito: concetto vicino. Accettabile, ma da confermare.
- **C19** `pi-clone` (MULTIPLI) vs `CLONE` = `pi-copy`: glifi quasi identici a occhio. Se i due stanno nella stessa riga si confondono.
- **C20** `pi-at`: `NAV_ICONS.AT` (account email) vs campo PEC. Icone di campo, non gesti.
- **C21** `pi-envelope`: INVITA / campo EMAIL / nav email log — tutti «un'email»: accettabile, come `REGISTRA`/`CLOSE`.
- **C24** `pi-chart-pie` in DashboardCompetenzaView.vue:2954 è l'icona di `SITUAZIONE_APERTA` usata come placeholder vuoto → mappato a `VUOTO`.

#### 3.2b Stesso significato, disegni diversi (11)

| # | Significato | Disegni oggi | Disegno unico proposto |
| --- | --- | --- | --- |
| D1 | Sbloccare | `pi-key` (CommessaGestione:725), `pi-unlock` (DashboardCompetenza:1847) | `SBLOCCA` = `pi-key` |
| D2 | Aggiungere/creare | `pi-plus-circle` (percorso, home pratiche, onere, eventi creato/aggiunto), `pi-plus` (`ADD`) | `ADD` = `pi-plus` |
| D3 | Assegnazione cambiata | `pi-user` (severity:140), `pi-user-plus` (severity:143, `ASSIGN`) | `ASSIGN` |
| D4 | Inviare un invito | `pi-envelope` (portale, operatore), `pi-shopping-cart` (shop) | `INVITA` = `pi-envelope` |
| D5 | Test prezzo | `pi-calculator` (apri), `pi-search` (esegui) | `TEST_PREZZO` = `pi-bullseye` |
| D6 | Predefinito | `pi-star` (EmittenteFiscaleBillingAccountTab:254), `pi-check-circle` (ContiBancariDrawer:193, fuori elenco) | `PREDEFINITO` = `pi-thumbtack` |
| D7 | Push a commessa | `pi-arrow-right` (`AZIONE_PUSH_COMMESSA`), `pi-send` (`SEND`, iscrizioni INVIO_COMMESSA) | `SEND` (il suo commento già lo dichiara) |
| D8 | Nota | `pi-comment` (evento NOTA_AGGIUNTA), `pi-file-edit` (`NOTE`) | `NOTE` |
| D9 | Soggetto | `pi-user` (banner, ripiego ruolo), `pi-users` (`SOGGETTO`) | `SOGGETTO` |
| D10 | Unità di misura | `pi-box` (ArticoloDrawer:539, ArticoloUomDrawer:337), icona composta `UOM` | `UOM` (il commento di UOM spiega che `pi-box` è l'articolo) |
| D11 | Accesso shop | `pi-shopping-bag` (attiva), `pi-shopping-cart` (invita) | `ACCESSO_SHOP` per lo stato, `INVITA` per l'invio |

---

### 3.3 Casi che coincidono con una chiave esistente (36 occorrenze)

| Chiave esistente | Disegno oggi a video → disegno della chiave | Occorrenze | Nota |
| --- | --- | --- | --- |
| `NAV_ICONS.HOME` | `pi-home` (uguale) | ui/views/GestionePersonalizzazioniListeView.vue:81 · ui/views/PersonalizzazioniListeTecnicheView.vue:62 · config/views/ConfigurazioneDocumentiView.vue:42 · core/views/ErrorView.vue:20 | «Torna alla Home» delle pagine forbidden/errore. |
| `NAV_ICONS.CODE_LAVORO` | `pi-inbox` (uguale) | strumenti/components/CodaLavoriTab.vue:187 · strumenti/views/CodeLavoroView.vue:61 · core/components/AppTopbar.vue:202 · :335 · core/components/CodeLavoroDrawer.vue:120 | CodaLavoriTab:187 è l'empty-icon della coda: segue lo schema di CodaStampaTab (icona della coda). |
| `NAV_ICONS.PERSONALIZZAZIONI_LISTE` | `pi-table` → `pi-th-large` | ui/components/ListaPresetColonneDrawer.vue:212 · ui/components/ListaPresetPanel.vue:92 · ui/components/ListaColonnaDrawer.vue:251 | Drawer/azioni della sezione Personalizzazioni liste. |
| `NAV_ICONS.TABELLE` | `pi-table` (uguale) | core/components/ConfigTablePanel.vue:252 | Stato «seleziona una tabella». |
| `NAV_ICONS.PRATICHE` | `pi-folder` (uguale) | pratiche/components/PraticaDrawer.vue:409 | Titolo drawer pratica. |
| `NAV_ICONS.AT` (→ rinominare `ACCOUNT_EMAIL`) | `pi-at` (uguale) | amministrazione/components/EmailAccountDrawer.vue:200 | Titolo drawer account email. |
| `NAV_ICONS.TAGS` (→ rinominare `CATEGORIE_CLIENTI`) | `pi-tag` → `pi-tags` | vendite/preventivi/components/PreventiviDrawer.vue:930 | Chip categoria cliente del contesto pricing. |
| `NAV_ICONS.ORDINI` | `pi-check-square` → icona composta ordini | vendite/iscrizioni.js:194 | Attività di pratica CONFERMA_ORDINE: le sorelle usano l'icona della cosa (`CONTRATTI`) o il verbo (`pi-send`); scelta «icona della cosa». |
| `NAV_ICONS.CLIENTI` / `NAV_ICONS.FORNITORI` | `pi-user` / `pi-truck` → composte | stores/context.js:6 · :7 | Chip di contesto in topbar. |
| `NAV_ICONS.OPERATORE` | `pi-user` (uguale) | core/components/AiAssistantDrawer.vue:124 (ramo user) | Avatar del messaggio dell'operatore. |
| `MANAGE_ICONS.SOGGETTO` | `pi-user` → `pi-users` | stores/context.js:44 · core/components/SoggettoMessageBanner.vue:24 | |
| `MANAGE_ICONS.ADD` | `pi-plus-circle` → `pi-plus` | pratiche/components/PraticaPercorso.vue:264 · :350 · pratiche/views/PraticheHome.vue:144 · vendite/components/CommessaGestioneDrawer.vue:864 · core/utils/severity.js:136 · :159 | D2. |
| `MANAGE_ICONS.INSPECT` | `pi-search` → `pi-eye` | strumenti/components/CodaLavoriTab.vue:139 | «Dettaglio» di un lavoro: ispezione, non ricerca. |
| `MANAGE_ICONS.SEND` | `pi-arrow-right` → `pi-send` | vendite/constants.js:110 (`AZIONE_PUSH_COMMESSA`, letta da DdtDrawer e OrdiniDrawer) | D7. |
| `MANAGE_ICONS.CONTRATTI` | `pi-arrow-right` → composta contratti | vendite/offerte/components/OffertaDrawer.vue:1298 | «Apri il contratto già generato»: icona della cosa. |
| `MANAGE_ICONS.LOTTO` | `pi-external-link` → `pi-server` | vendite/views/DashboardCompetenzaView.vue:2245 | «Vai ai lotti»: icona della destinazione (in alternativa `VAI_A`). |
| `MANAGE_ICONS.UOM` | `pi-box` → composta | catalogo/components/ArticoloDrawer.vue:539 · catalogo/components/ArticoloUomDrawer.vue:337 | D10. |
| `MANAGE_ICONS.ASSIGN` | `pi-user` → `pi-user-plus` | core/utils/severity.js:140 | D3. |
| `MANAGE_ICONS.NOTE` | `pi-comment` → `pi-file-edit` | core/utils/severity.js:144 | D8. |
| `MANAGE_ICONS.CORREZIONE` | `pi-replay` (uguale) | vendite/_shared/lineage/DocumentoCollegamentiBar.vue:136 (fuori elenco, stessa funzione) | Ramo inverso della lineage (DDT→reso, fattura→nota di credito) = la correzione. |

---

### 3.4 Icone di stato / severità / esito → gruppo separato `STATUS_ICONS` (28 occorrenze)

Sì, serve un gruppo a parte: non sono gesti né porte, e MANAGE_ICONS ha già dovuto
ospitare `ERRORE` e `ATTESA` solo perché mancava il posto giusto. Proposta:
`STATUS_ICONS` in `core/constants.js`, con `ERRORE` e `ATTESA` che ci si
trasferiscono (o vi sono ripetuti) e la coppia dello «stato vuoto».

| Costante | Disegno | Occorrenze | Significato |
| --- | --- | --- | --- |
| `VUOTO` | `pi pi-inbox` | pagamenti/components/RatePickerDialog.vue:395 · strumenti/components/CodaTabBase.vue:72 (default) · vendite/components/LottoDrawer.vue:1482 · :1586 · :1660 · :1929 · vendite/views/DashboardCompetenzaView.vue:2888 · :2954 (oggi `pi-chart-pie`) · vendite/components/FatturaDrawer.vue:711 · :811 · core/components/DashEmptyState.vue:20 · core/components/GiornaleEventi.vue:64 | Niente da mostrare / non ancora caricato. |
| `TUTTO_OK` (fuori elenco) | `pi pi-check-circle` | stessi file, ramo «caricato e vuoto» (LottoDrawer:1929, FatturaDrawer:811, DashEmptyState:20, DashboardCompetenzaView:2884) | «Caricato, e non c'è niente che non va». ⚠️ Oggi è anche `PUBLISH`: va nominato come stato. |
| `INFO` | `pi pi-info-circle` | vendite/components/LottoDrawer.vue:1568 · vendite/components/ContrattoRigheDrawer.vue:1263 · vendite/views/DashboardCompetenzaView.vue:2275 · core/components/SearchDrawer.vue:280 · core/components/StatusPage.vue:7 (default) · core/components/AppTopbar.vue:172 · core/components/DrawerActionsBar.vue:257 · core/components/ErroreRigaInfo.vue:108 (livello I) | C'è qualcosa da sapere (nota, perimetro, motivo). Controparte di `ERRORE`. |
| `IN_RITARDO` | `pi pi-clock` | vendite/views/DashboardCompetenzaView.vue:2303 · :2937 · vendite/views/DashboardBacklogView.vue:404 | In ritardo / anzianità. Già citato nel commento di `ATTESA` («`pi-clock` dice già in ritardo»): ora prende il nome. |
| `MULTIPLI` | `pi pi-clone` | vendite/components/LottoDrawer.vue:1531 · vendite/views/DashboardCompetenzaView.vue:2752 | «Più di uno» (commesse, registri) in una cella. ⚠️ C19. |
| `NON_TROVATO` | `pi pi-map` (o `pi pi-compass`) | router/index.js:616 (`errorIcon` del 404) | Pagina inesistente. Se UBICAZIONI prende `pi-map` (P2), il 404 va a `pi-compass`. |
| `IN_COSTRUZIONE` | `pi pi-hammer` (nuovo, oggi `pi-wrench`) | core/views/PlaceholderView.vue:44 | Funzione non ancora costruita. |
| `EVENTO` | `pi pi-circle` | core/utils/severity.js:150 (`_AZIONE_DEFAULT`) | Evento di giornale senza icona propria (vocabolario aperto dal DB). |

Nota su `core/utils/severity.js`: le mappe `AZIONE_GIORNALE_MAP` ed
`EVENTO_REGISTRO_COMMESSA_MAP` hanno già chiavi di significato (i codici DB) e
vanno tenute; sono i **valori** a dover leggere le costanti (`ADD`, `PRIORITA`,
`ASSIGN`, `NOTE`, `ALLEGATI`, `SOSPENDI`, `ACCREDITO`, `STATUS_ICONS.EVENTO`).
Idem `ICONA_TRANSIZIONE_RIGA` (pagamenti) → `ABBINA`, `SOSPENDI`, `DISATTIVA`.

---

### 3.5 Casi da lasciare / togliere

| Occorrenza | Motivo |
| --- | --- |
| vendite/components/ListiniSearchTable.vue:376 `pi pi-arrow-turn-down-right` | **Glifo inesistente** in primeicons 7.0.0: a video non rende nulla. È decorazione (freccia «sotto-livello») accanto a `MANAGE_ICONS.VERSIONI`, che già dice cosa c'è. Da **togliere**, non da centralizzare (o, se la si vuole, `pi-arrow-down-right` = DERIVATO, che però è un altro significato). |

Facoltativi (scelta «icona della cosa» vs verbo generico): DashboardCompetenza:2245
(`LOTTO` o `VAI_A`), EmittenteFiscaleUtilitiesTab:371 (`UTILITY` o `VAI_A`),
PraticheDashboard:466 (`NAV_ICONS.PRATICHE` o `VAI_A`).

---

### 3.6 Problemi preesistenti trovati di passaggio (fuori dalle 153)

| # | Problema | Proposta |
| --- | --- | --- |
| P1 | **`NAV_ICONS` ha 18 chiavi col nome del disegno**: `KEY, SEARCH, SITEMAP, SHIELD, ID_CARD, TAGS, HISTORY, AT, FILE_EDIT, ENVELOPE, MAP_MARKER, ARROWS_H, SYNC, FILE, TAG, PERCENTAGE, CHECK_CIRCLE, FOLDER_OPEN`. Alcune senza lettori fuori da navigation.js (`SYNC`, `TAG`, `PERCENTAGE`, `CHECK_CIRCLE`). | Rinominare per voce: KEY→OPERATORI (e usare `pi-user`, C10), SITEMAP→PROFILI_REPARTO/DEFINIZIONI_WORKFLOW (⚠️ due voci stesso glifo, e `BOM` = `pi-sitemap`), SHIELD→PERMESSI, ID_CARD→EMITTENTI_FISCALI (⚠️ = `CONTATTI`), TAGS→CATEGORIE_CLIENTI, HISTORY→AUDIT_LOG (⚠️ = `VERSIONI`), AT→ACCOUNT_EMAIL, FILE_EDIT→TEMPLATE_EMAIL (⚠️ = `NOTE`), ENVELOPE→EMAIL, MAP_MARKER→INDIRIZZI, ARROWS_H→UNITA_MISURA, FILE→FAMIGLIE_DOCUMENTO, FOLDER_OPEN→GESTIONE_PRATICHE, SEARCH→RICERCA; togliere le chiavi senza lettori. |
| P2 | `pi-th-large` = `UBICAZIONI` **e** `NAV_ICONS.PERSONALIZZAZIONI_LISTE` | UBICAZIONI → `pi-map` (il suo commento dice «la MAPPA del deposito»); il 404 passa a `pi-compass`. |
| P3 | `pi-tags` = `LOTTO_MAGAZZINO` **e** `NAV_ICONS.TAGS` (categorie clienti) | Decisione Tid; il commento di LOTTO_MAGAZZINO distingue solo da `LOTTO`. |
| P4 | `pi-replay` = `RIATTIVA` **e** `CORREZIONE` dentro MANAGE_ICONS stesso | Due gesti, un segno: uno dei due cambia (es. RIATTIVA → `pi-power-off`?). |
| P5 | `pi-inbox` tre volte in NAV (`CODE_LAVORO`, `DASHBOARD_BACKLOG`, `CAP`) | Vedi C1. |
| P6 | `pi-file-edit`: `NOTE`, `NAV_ICONS.FILE_EDIT` (template email), iscrizione «apri preventivo» (iscrizioni.js:152) | Preventivo → `NAV_ICONS.PREVENTIVI`. |
| P7 | `pi-check-circle`: `PUBLISH`, stato «tutto ok», «imposta contesto» (DetailActions:23), «predefinito» (ContiBancari:196) | Nominare `TUTTO_OK` e `PREDEFINITO`; «imposta contesto» merita una chiave sua. |
| P8 | `pi-briefcase`: `COMMESSA` e ruolo VENDITORE (context.js:8) | Il ruolo cambia glifo. |
| P9 | `ExportDialog` CSV = `pi-file` (= FAMIGLIA_DOCUMENTO) | `FORMATO_CSV`. |

---

### 3.A Appendice — tutte le 153 occorrenze e la loro destinazione

| # | Occorrenza | Destinazione |
| --- | --- | --- |
| 1 | `ui/components/ListaPresetColonneDrawer.vue:212:icon="pi pi-table"` | NAV_ICONS.PERSONALIZZAZIONI_LISTE (esistente) |
| 2 | `ui/views/GestionePersonalizzazioniListeView.vue:81:icon="pi pi-home"` | NAV_ICONS.HOME (esistente) |
| 3 | `ui/views/PersonalizzazioniListeTecnicheView.vue:62:icon="pi pi-home"` | NAV_ICONS.HOME (esistente) |
| 4 | `stores/context.js:6:'pi pi-user'` | NAV_ICONS.CLIENTI (esistente) |
| 5 | `stores/context.js:7:'pi pi-truck'` | NAV_ICONS.FORNITORI (esistente) |
| 6 | `stores/context.js:9:'pi pi-share-alt'` | TIPO_RUOLO_ICONS.DISTRIBUTORE (nuova) |
| 7 | `stores/context.js:10:'pi pi-shop'` | TIPO_RUOLO_ICONS.RESELLER (nuova) |
| 8 | `stores/context.js:11:'pi pi-car'` | TIPO_RUOLO_ICONS.VETTORE (nuova) |
| 9 | `stores/context.js:12:'pi pi-building-columns'` | TIPO_RUOLO_ICONS.BANCA (nuova) |
| 10 | `stores/context.js:44:'pi pi-user'` | MANAGE_ICONS.SOGGETTO (esistente) |
| 11 | `pagamenti/components/DistintaRigaForm.vue:438:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 12 | `pagamenti/components/RatePickerDialog.vue:395:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 13 | `pagamenti/components/RatePickerDialog.vue:399:"pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 14 | `pagamenti/composables/useAzioniRigaContabile.js:63:'pi pi-link'` | MANAGE_ICONS.ABBINA (nuova) |
| 15 | `pagamenti/composables/useAzioniRigaContabile.js:64:'pi pi-pause'` | MANAGE_ICONS.SOSPENDI (nuova) |
| 16 | `strumenti/components/CodaStampaTab.vue:107:icon="pi pi-print"` | MANAGE_ICONS.STAMPA (nuova) |
| 17 | `strumenti/components/CodaLavoriTab.vue:139:'pi pi-search'` | MANAGE_ICONS.INSPECT (esistente) |
| 18 | `strumenti/components/CodaLavoriTab.vue:187:icon="pi pi-inbox"` | NAV_ICONS.CODE_LAVORO (esistente) |
| 19 | `strumenti/composables/useCodaArchiviazione.js:45:'pi pi-inbox'` | MANAGE_ICONS.ARCHIVIA (nuova) |
| 20 | `strumenti/views/CodeLavoroView.vue:61:"pi pi-inbox"` | NAV_ICONS.CODE_LAVORO (esistente) |
| 21 | `strumenti/views/CodeLavoroView.vue:64:"pi pi-print"` | MANAGE_ICONS.STAMPA (nuova) |
| 22 | `strumenti/components/CodaTabBase.vue:72:'pi pi-inbox'` | STATUS_ICONS.VUOTO (nuova) |
| 23 | `pratiche/components/PraticaDrawer.vue:304:'pi pi-lock-open'` | MANAGE_ICONS.APRI (nuova) |
| 24 | `pratiche/components/PraticaDrawer.vue:314:'pi pi-pause'` | MANAGE_ICONS.SOSPENDI (nuova) |
| 25 | `pratiche/components/PraticaDrawer.vue:409:icon="pi pi-folder"` | NAV_ICONS.PRATICHE (esistente) |
| 26 | `pratiche/components/PraticaDrawer.vue:459:"pi pi-link"` | MANAGE_ICONS.DERIVATO (nuova) |
| 27 | `pratiche/components/PraticaPercorso.vue:264:'pi pi-plus-circle'` | MANAGE_ICONS.ADD (esistente) |
| 28 | `pratiche/components/PraticaPercorso.vue:350:'pi pi-plus-circle'` | MANAGE_ICONS.ADD (esistente) |
| 29 | `pratiche/views/PraticheHome.vue:144:"pi pi-plus-circle"` | MANAGE_ICONS.ADD (esistente) |
| 30 | `portale/components/WebAccessiDrawer.vue:58:icon="pi pi-globe"` | MANAGE_ICONS.ACCESSI_WEB (nuova) |
| 31 | `portale/components/WebAccessiBadge.vue:61:icon="pi pi-globe"` | MANAGE_ICONS.ACCESSI_WEB (nuova) |
| 32 | `portale/components/PortaleAccessoPanel.vue:221:icon="pi pi-envelope"` | MANAGE_ICONS.INVITA (nuova) |
| 33 | `portale/components/PortaleAccessoPanel.vue:284:icon="pi pi-shopping-cart"` | MANAGE_ICONS.INVITA (nuova) |
| 34 | `pratiche/views/PraticheDashboard.vue:466:icon="pi pi-external-link"` | MANAGE_ICONS.VAI_A (nuova) |
| 35 | `pratiche/views/PraticheDashboard.vue:478:'pi pi-eye-slash'` | MANAGE_ICONS.NASCONDI_TECNICO (nuova) |
| 36 | `pratiche/views/PraticheDashboard.vue:478:'pi pi-wrench'` | MANAGE_ICONS.MODALITA_TECNICA (nuova) |
| 37 | `portale/components/AttivaAccessoShopButton.vue:54:icon="pi pi-shopping-bag"` | MANAGE_ICONS.ACCESSO_SHOP (nuova) |
| 38 | `ui/components/ListaPresetPanel.vue:92:'pi pi-table'` | NAV_ICONS.PERSONALIZZAZIONI_LISTE (esistente) |
| 39 | `ui/components/ListaColonnaDrawer.vue:251:icon="pi pi-table"` | NAV_ICONS.PERSONALIZZAZIONI_LISTE (esistente) |
| 40 | `documenti/components/DocumentoEmissioneDialog.vue:240:icon="pi pi-paperclip"` | MANAGE_ICONS.ALLEGATI (nuova) |
| 41 | `catalogo/components/ArticoloDrawer.vue:539:icon="pi pi-box"` | MANAGE_ICONS.UOM (esistente) |
| 42 | `pagamenti/components/DistintaDrawer.vue:301:'pi pi-list-check'` | MANAGE_ICONS.RIGHE_DA_RATE (nuova) |
| 43 | `catalogo/components/ArticoloUomDrawer.vue:337:"pi pi-box"` | MANAGE_ICONS.UOM (esistente) |
| 44 | `amministrazione/components/EmailAccountDrawer.vue:200:icon="pi pi-at"` | NAV_ICONS.AT → da rinominare ACCOUNT_EMAIL (esistente) |
| 45 | `amministrazione/components/EmailAccountDrawer.vue:278:icon="pi pi-wifi"` | MANAGE_ICONS.TEST_CONNESSIONE (nuova) |
| 46 | `amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:371:icon="pi pi-external-link"` | MANAGE_ICONS.VAI_A (nuova) |
| 47 | `amministrazione/components/EmittenteFiscaleDrawer.vue:319:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 48 | `amministrazione/components/EmittenteFiscaleBillingAccountTab.vue:254:icon="pi pi-star"` | MANAGE_ICONS.PREDEFINITO (nuova) |
| 49 | `anagrafiche/components/FornitoreDrawer.vue:267:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 50 | `config/views/ConfigurazioneDocumentiView.vue:42:icon="pi pi-home"` | NAV_ICONS.HOME (esistente) |
| 51 | `vendite/constants.js:110:'pi pi-arrow-right'` | MANAGE_ICONS.SEND (esistente) |
| 52 | `anagrafiche/components/ContiBancariDrawer.vue:197:"pi pi-code"` | RECAPITO_ICONS.BIC (nuova) |
| 53 | `vendite/_shared/lineage/DocumentoCollegamentiBar.vue:137:'pi pi-arrow-right'` | MANAGE_ICONS.DOC_DESTINAZIONE (nuova) |
| 54 | `vendite/iscrizioni.js:194:'pi pi-check-square'` | NAV_ICONS.ORDINI (esistente) |
| 55 | `vendite/offerte/components/OffertaDrawer.vue:1298:icon="pi pi-arrow-right"` | MANAGE_ICONS.CONTRATTI (esistente) |
| 56 | `vendite/components/LottoDrawer.vue:1482:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 57 | `vendite/components/LottoDrawer.vue:1531:"pi pi-clone"` | STATUS_ICONS.MULTIPLI (nuova) |
| 58 | `vendite/components/LottoDrawer.vue:1568:"pi pi-info-circle"` | STATUS_ICONS.INFO (nuova) |
| 59 | `vendite/components/LottoDrawer.vue:1586:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 60 | `vendite/components/LottoDrawer.vue:1660:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 61 | `vendite/components/LottoDrawer.vue:1929:'pi pi-inbox'` | STATUS_ICONS.VUOTO (nuova) |
| 62 | `vendite/components/ContrattoRigheDrawer.vue:1263:"pi pi-info-circle"` | STATUS_ICONS.INFO (nuova) |
| 63 | `vendite/components/ListiniSearchTable.vue:215:'pi pi-calculator'` | MANAGE_ICONS.TEST_PREZZO (nuova) |
| 64 | `vendite/components/ListiniSearchTable.vue:376:"pi pi-arrow-turn-down-right"` | DA LASCIARE/TOGLIERE (glifo inesistente) |
| 65 | `vendite/components/TestResolverDialog.vue:254:icon="pi pi-search"` | MANAGE_ICONS.TEST_PREZZO (nuova) |
| 66 | `vendite/components/FatturazioneEsitiPanel.vue:143:"pi pi-chart-bar"` | MANAGE_ICONS.ESITI (nuova) |
| 67 | `vendite/preventivi/components/PreventiviForm.vue:153:"pi pi-link"` | MANAGE_ICONS.DERIVATO (nuova) |
| 68 | `vendite/views/DashboardCompetenzaView.vue:1823:'pi pi-file-export'` | MANAGE_ICONS.FATTURA_GENERA (nuova) |
| 69 | `vendite/views/DashboardCompetenzaView.vue:1847:'pi pi-unlock'` | MANAGE_ICONS.SBLOCCA (nuova) |
| 70 | `vendite/views/DashboardCompetenzaView.vue:2226:icon="pi pi-file-export"` | MANAGE_ICONS.FATTURA_GENERA (nuova) |
| 71 | `vendite/views/DashboardCompetenzaView.vue:2245:icon="pi pi-external-link"` | MANAGE_ICONS.LOTTO (esistente) — in alternativa VAI_A |
| 72 | `vendite/views/DashboardCompetenzaView.vue:2275:"pi pi-info-circle"` | STATUS_ICONS.INFO (nuova) |
| 73 | `vendite/views/DashboardCompetenzaView.vue:2303:"pi pi-clock"` | STATUS_ICONS.IN_RITARDO (nuova) |
| 74 | `vendite/views/DashboardCompetenzaView.vue:2507:icon="pi pi-file-export"` | MANAGE_ICONS.FATTURA_GENERA (nuova) |
| 75 | `vendite/views/DashboardCompetenzaView.vue:2752:"pi pi-clone"` | STATUS_ICONS.MULTIPLI (nuova) |
| 76 | `vendite/views/DashboardCompetenzaView.vue:2888:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 77 | `vendite/views/DashboardCompetenzaView.vue:2937:"pi pi-clock"` | STATUS_ICONS.IN_RITARDO (nuova) |
| 78 | `vendite/views/DashboardCompetenzaView.vue:2954:"pi pi-chart-pie"` | STATUS_ICONS.VUOTO (nuova) |
| 79 | `vendite/views/DashboardBacklogView.vue:404:"pi pi-clock"` | STATUS_ICONS.IN_RITARDO (nuova) |
| 80 | `documenti/components/DocumentiGeneratiSorgenteList.vue:144:'pi pi-paperclip'` | MANAGE_ICONS.ALLEGATI (nuova) |
| 81 | `router/index.js:616:'pi pi-map'` | STATUS_ICONS.NON_TROVATO (nuova) |
| 82 | `core/bersaglioGesto.js:104:'pi pi-external-link'` | MANAGE_ICONS.VAI_A (nuova) |
| 83 | `amministrazione/components/OperatoreDrawer.vue:402:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 84 | `amministrazione/components/OperatoreDrawer.vue:538:icon="pi pi-envelope"` | MANAGE_ICONS.INVITA (nuova) |
| 85 | `core/components/ExportDialog.vue:37:'pi pi-file-excel'` | MANAGE_ICONS.FORMATO_XLSX (nuova) |
| 86 | `core/components/SearchDrawer.vue:280:"pi pi-info-circle"` | STATUS_ICONS.INFO (nuova) |
| 87 | `core/components/ConfigTablePanel.vue:252:"pi pi-table"` | NAV_ICONS.TABELLE (esistente) |
| 88 | `core/components/AppSidebar.vue:75:'pi pi-angle-double-right'` | MANAGE_ICONS.SIDEBAR_ESPANDI (nuova) |
| 89 | `core/components/AppSidebar.vue:75:'pi pi-angle-double-left'` | MANAGE_ICONS.SIDEBAR_COMPRIMI (nuova) |
| 90 | `core/components/AiAssistantDrawer.vue:90:"pi pi-microchip-ai"` | NAV_ICONS.ASSISTENTE_AI (nuova) |
| 91 | `core/components/AiAssistantDrawer.vue:98:'pi pi-window-maximize'` | MANAGE_ICONS.FINESTRA_ESPANDI (nuova) |
| 92 | `core/components/AiAssistantDrawer.vue:98:'pi pi-window-minimize'` | MANAGE_ICONS.FINESTRA_RIDUCI (nuova) |
| 93 | `core/components/AiAssistantDrawer.vue:124:'pi pi-user'` | NAV_ICONS.OPERATORE (esistente) |
| 94 | `core/components/AiAssistantDrawer.vue:124:'pi pi-microchip-ai'` | NAV_ICONS.ASSISTENTE_AI (nuova) |
| 95 | `core/components/AiAssistantDrawer.vue:145:"pi pi-external-link"` | MANAGE_ICONS.VAI_A (nuova) |
| 96 | `core/components/AiAssistantDrawer.vue:179:"pi pi-microchip-ai"` | NAV_ICONS.ASSISTENTE_AI (nuova) |
| 97 | `core/components/FavoriteItem.vue:72:"pi pi-star-fill"` | MANAGE_ICONS.PREFERITO_ATTIVO (nuova) |
| 98 | `anagrafiche/components/ContattiSoggettoDrawer.vue:139:"pi pi-envelope"` | RECAPITO_ICONS.EMAIL (nuova) |
| 99 | `anagrafiche/components/ContattiSoggettoDrawer.vue:140:"pi pi-phone"` | RECAPITO_ICONS.TELEFONO (nuova) |
| 100 | `anagrafiche/components/ContattiSoggettoDrawer.vue:141:"pi pi-mobile"` | RECAPITO_ICONS.CELLULARE (nuova) |
| 101 | `anagrafiche/components/ContattiSoggettoDrawer.vue:142:"pi pi-at"` | RECAPITO_ICONS.PEC (nuova) |
| 102 | `core/components/StatusPage.vue:7:'pi pi-info-circle'` | STATUS_ICONS.INFO (nuova) |
| 103 | `core/components/AppTopbar.vue:172:'pi pi-info-circle'` | STATUS_ICONS.INFO (nuova) |
| 104 | `core/components/AppTopbar.vue:195:'pi pi-search'` | MANAGE_ICONS.RICERCA (nuova) |
| 105 | `core/components/AppTopbar.vue:202:'pi pi-inbox'` | NAV_ICONS.CODE_LAVORO (esistente) |
| 106 | `core/components/AppTopbar.vue:218:'pi pi-microchip-ai'` | NAV_ICONS.ASSISTENTE_AI (nuova) |
| 107 | `core/components/AppTopbar.vue:226:'pi pi-star'` | MANAGE_ICONS.PREFERITI (nuova) |
| 108 | `core/components/AppTopbar.vue:232:'pi pi-globe'` | MANAGE_ICONS.LINGUA (nuova) |
| 109 | `core/components/AppTopbar.vue:238:'pi pi-sun'` | MANAGE_ICONS.TEMA_CHIARO (nuova) |
| 110 | `core/components/AppTopbar.vue:238:'pi pi-moon'` | MANAGE_ICONS.TEMA_SCURO (nuova) |
| 111 | `core/components/AppTopbar.vue:268:icon="pi pi-bars"` | MANAGE_ICONS.MENU (nuova) |
| 112 | `core/components/AppTopbar.vue:335:"pi pi-inbox"` | NAV_ICONS.CODE_LAVORO (esistente) |
| 113 | `core/components/AppTopbar.vue:378:"pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 114 | `core/components/AppTopbar.vue:388:"pi pi-microchip-ai"` | NAV_ICONS.ASSISTENTE_AI (nuova) |
| 115 | `core/components/AppTopbar.vue:411:"pi pi-sign-out"` | MANAGE_ICONS.LOGOUT (nuova) |
| 116 | `anagrafiche/components/ClienteDrawer.vue:428:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 117 | `core/components/SoggettoMessageBanner.vue:24:"pi pi-user"` | MANAGE_ICONS.SOGGETTO (esistente) |
| 118 | `anagrafiche/components/SoggettoResolver.vue:202:icon="pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 119 | `core/components/DrawerActionsBar.vue:257:"pi pi-info-circle"` | STATUS_ICONS.INFO (nuova) |
| 120 | `core/components/details/DetailActions.vue:30:icon="pi pi-external-link"` | MANAGE_ICONS.VAI_A (nuova) |
| 121 | `core/views/ErrorView.vue:20:icon="pi pi-home"` | NAV_ICONS.HOME (esistente) |
| 122 | `vendite/components/FatturaDrawer.vue:711:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 123 | `vendite/components/FatturaDrawer.vue:811:'pi pi-inbox'` | STATUS_ICONS.VUOTO (nuova) |
| 124 | `vendite/components/VersioneDrawer.vue:92:'pi pi-percentage'` | MANAGE_ICONS.VARIAZIONE_PREZZO (nuova) |
| 125 | `core/components/DashEmptyState.vue:20:'pi pi-inbox'` | STATUS_ICONS.VUOTO (nuova) |
| 126 | `vendite/components/CommessaGestioneDrawer.vue:725:'pi pi-key'` | MANAGE_ICONS.SBLOCCA (nuova) |
| 127 | `vendite/components/CommessaGestioneDrawer.vue:864:'pi pi-plus-circle'` | MANAGE_ICONS.ADD (esistente) |
| 128 | `core/components/SplitReadonlyPanel.vue:55:"pi pi-arrows-h"` | MANAGE_ICONS.SCAMBIA (nuova) |
| 129 | `core/views/PlaceholderView.vue:44:icon="pi pi-wrench"` | STATUS_ICONS.IN_COSTRUZIONE (nuova) |
| 130 | `core/components/SearchHint.vue:15:"pi pi-search"` | MANAGE_ICONS.RICERCA (nuova) |
| 131 | `core/components/ListaColonneModal.vue:252:icon="pi pi-arrow-up"` | MANAGE_ICONS.SPOSTA_SU (nuova) |
| 132 | `core/components/ListaColonneModal.vue:261:icon="pi pi-arrow-down"` | MANAGE_ICONS.SPOSTA_GIU (nuova) |
| 133 | `core/components/GiornaleEventi.vue:64:"pi pi-inbox"` | STATUS_ICONS.VUOTO (nuova) |
| 134 | `core/components/CodeLavoroDrawer.vue:120:'pi pi-inbox'` | NAV_ICONS.CODE_LAVORO (esistente) |
| 135 | `core/components/CodeLavoroDrawer.vue:135:'pi pi-print'` | MANAGE_ICONS.STAMPA (nuova) |
| 136 | `core/components/dash/DashMesiSidebar.vue:26:icon="pi pi-chevron-left"` | MANAGE_ICONS.PRECEDENTE (nuova) |
| 137 | `core/utils/severity.js:136:'pi pi-plus-circle'` | MANAGE_ICONS.ADD (esistente) |
| 138 | `core/utils/severity.js:139:'pi pi-flag'` | MANAGE_ICONS.PRIORITA (nuova) |
| 139 | `core/utils/severity.js:140:'pi pi-user'` | MANAGE_ICONS.ASSIGN (esistente) |
| 140 | `core/utils/severity.js:144:'pi pi-comment'` | MANAGE_ICONS.NOTE (esistente) |
| 141 | `core/utils/severity.js:145:'pi pi-paperclip'` | MANAGE_ICONS.ALLEGATI (nuova) |
| 142 | `core/utils/severity.js:146:'pi pi-pause'` | MANAGE_ICONS.SOSPENDI (nuova) |
| 143 | `core/utils/severity.js:150:'pi pi-circle'` | STATUS_ICONS.EVENTO (nuova) |
| 144 | `core/utils/severity.js:159:'pi pi-plus-circle'` | MANAGE_ICONS.ADD (esistente) |
| 145 | `core/utils/severity.js:165:'pi pi-money-bill'` | MANAGE_ICONS.ACCREDITO (nuova) |
| 146 | `vendite/composables/useLottoAzioni.js:59:'pi pi-forward'` | MANAGE_ICONS.AVANZA (nuova) |
| 147 | `vendite/composables/useLottoAzioni.js:81:'pi pi-print'` | MANAGE_ICONS.STAMPA (nuova) |
| 148 | `core/components/ErroreRigaInfo.vue:108:'pi pi-info-circle'` | STATUS_ICONS.INFO (nuova) |
| 149 | `core/components/ContentTabs.vue:166:'pi pi-objects-column'` | MANAGE_ICONS.AFFIANCA (nuova) |
| 150 | `core/components/dash/DashMeseStepper.vue:24:icon="pi pi-chevron-left"` | MANAGE_ICONS.PRECEDENTE (nuova) |
| 151 | `core/views/HomeView.vue:146:"pi pi-star"` | MANAGE_ICONS.PREFERITI (nuova) |
| 152 | `core/views/HomeView.vue:179:"pi pi-star"` | MANAGE_ICONS.PREFERITI (nuova) |
| 153 | `vendite/preventivi/components/PreventiviDrawer.vue:930:icon="pi pi-tag"` | NAV_ICONS.TAGS → da rinominare CATEGORIE_CLIENTI (esistente) |
