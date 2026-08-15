# Mappa Concentrica — Changelog

> Cronologia datata degli aggiornamenti della [Mappa Concentrica](../mappa-concentrica.md).
> La mappa mostra solo lo **stato corrente** per anello; questo documento conserva la storia,
> per non gonfiare il documento principale.
>
> Registra solo evidenze presenti nel repository: commit e documentazione
> `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica
> test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.

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

Vedi [piano-db-satelliti-fattura.md](work-in-progress/piano-db-satelliti-fattura.md),
[piano-be-fe-satelliti-fattura.md](work-in-progress/piano-be-fe-satelliti-fattura.md),
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
[brief-db-fondo-fattura-ricalcolo-e-governo.md](work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo.md).

**Manutenzione.** Bonifica indici: corrette le viste `dbops`, aggiunte guardie
sull'`apply`, rimossi **48 indici ridondanti** (27 luglio). Commesse: permesso di
cambio stato, **annullamento delle righe manuali** (non cancella: porta a
`ANNULLATA` con motivo obbligatorio), guard di uscita. Lato BE, fan-out isolato
con esito parziale.

---

## 26 luglio 2026

**Anello 3 (vendite) — Resi di vendita: il documento di rientro merce.** Sesto
documento del ciclo attivo, nato dal DDT: testata + righe **senza valori
economici** (articolo, quantità, tipo reso, motivo — il ramo nota di credito è
slice successiva), editabili solo in DRAFT, con **conferma** (riapre il residuo
dell'ordine, ri-proietta lo stato ordine, flip DDT→RESO se totale), **annullo**
come storno, **ri-consegna** (`fn_genera_ddt_riconsegna`: nuovo DDT di
ri-spedizione, parziale e multipla) e due **code di lavoro** configurabili (da
accreditare / da ri-consegnare); azioni data-driven da
`script.fn_available_actions_reso`. A chiusura della slice, la **rinuncia alla
ri-consegna**: un reso per ri-spedizione può essere reso **DEFINITIVO** —
altrimenti una ri-consegna parziale o mai eseguita lascia l'ordine
`PARZIALMENTE_EVASO` per sempre, senza alcuna via d'uscita in-app. Vedi
[brief-db-resi-vendita.md](work-done/brief-db-resi-vendita.md),
[brief-be-fe-resi-vendita.md](work-done/brief-be-fe-resi-vendita.md),
[brief-db-chiusura-riconsegna-reso-definitivo.md](work-done/brief-db-chiusura-riconsegna-reso-definitivo.md).

**Anello 3 (vendite) — Fatturazione di DDT e resi rifondata a contatore.**
`config.tipi_reso.riapre_residuo` era un flag **logistico** (la merce torna
indietro per sempre, oppure verrà rispedita) che decideva anche cosa succedeva
ai **soldi**: due domande diverse su una colonna sola. La fatturazione passa a
un **contatore di merce** per riga d'ordine (spedito − reso), che chiude due bug
di **doppia fatturazione** a monte invisibili alle dashboard — le mostravano
come transito legittimo — estende le lenti Situazione aperta e Backlog a DDT e
resi e porta la **coda accrediti sui fatti**, con quantità. Decisioni DL-19..28
del design a due lenti. Vedi
[brief-db-fatturazione-ddt-resi.md](work-done/brief-db-fatturazione-ddt-resi.md),
[brief-be-fe-ddt-resi-dashboard.md](work-done/brief-be-fe-ddt-resi-dashboard.md).

**Anello 3 (vendite) — Quantità immutabili sulla commessa + porta oneri.** Le
quantità già fatturate diventano **immutabili** (guard su `commesse_attivita` e
`attivita_fatturabili`, codici 550/551). Sopra questa base si apre la **porta
oneri**: vocabolario `config.causali_onere`, modello **articolo↔causale 1:1**
(`catalogo.articoli.causale_onere_id`) — un articolo *è* un onere perché ha una
causale collegata, così **ogni onere porta la propria IVA** — e madre
`fn_aggiungi_onere_commessa` che scrive la riga SOURCELESS con il proprio log
(codici 552-554). Corretta anche una **race** sul progressivo `segment_key`
degli oneri manuali: due operatori concorrenti ricevevano entrambi 200 OK e un
dato spariva in silenzio (codice 557 → 409). Vedi
[brief-db-immutabilita-quantita-e-porta-oneri.md](work-in-progress/brief-db-immutabilita-quantita-e-porta-oneri.md),
[brief-be-fe-immutabilita-quantita-e-porta-oneri.md](work-done/brief-be-fe-immutabilita-quantita-e-porta-oneri.md),
[brief-db-race-segment-key-onere.md](work-done/brief-db-race-segment-key-onere.md).

**Anello 3 (vendite) — Cockpit processi fatturazione: dalle lenti all'azione.**
Le tre lenti (Competenza, Backlog, Situazione aperta) smettono di essere solo
una fotografia: dalla Dashboard Competenza si **agisce** con tre verbi —
«Fattura adesso» (giro on-demand su singolo lotto o su perimetro), «Rendi
definitive», stampa e ristampa massiva (l'invio SDI resta fuori). Il punto
architetturale è la **stampa massiva senza tenere il lock del registro fiscale
durante il rendering**: la stampa diventa un task che **accoda**
(`vendite.fatture_stampa_coda` + `fn_accoda_stampe_lotto`) e il render vive in
un **worker che drena la coda**, con la numerazione garantita in fase di stampa
da un backstop idempotente. La **fattura diventa il 6° dominio del motore
documentale**. Completano il quadro il **guard di uscita commessa** — chiudere o
annullare una commessa con righe ancora fatturabili era perdita **irreversibile**
di fatturato, invisibile alla dashboard — e le **capabilities con motivo** su
ogni azione di stato. Guida operativa:
[cruscotti-fatturazione.md](../guide/cruscotti-fatturazione.md) §7. Vedi
[brief-design-gestione-processi-fatturazione.md](work-done/brief-design-gestione-processi-fatturazione.md),
[brief-db-processi-fatturazione-cockpit.md](work-done/brief-db-processi-fatturazione-cockpit.md),
[brief-be-fe-processi-fatturazione.md](work-done/brief-be-fe-processi-fatturazione.md),
[brief-db-guard-uscita-commessa-e-capabilities.md](work-done/brief-db-guard-uscita-commessa-e-capabilities.md).

**Anello 0 (dbops) — Coda lavori generica `dbops.coda_lavori`.** Regola del 2
applicata a livello architetturale: `vendite.fatture_stampa_coda` (1ª coda)
stava per essere seguita da una seconda tabella-coda per il giro fatturazione
on-demand. Invece di **una tabella per batch** si estrae una **coda di job
generica** DB-native, transazionale e senza broker — la fondazione asincrona
dell'ERP — con worker che drena e primo consumatore reale il giro on-demand.
Guida operativa:
[gestione-code-di-lavoro.md](../guide/gestione-code-di-lavoro.md). Vedi
[brief-design-coda-lavori-generica.md](work-done/brief-design-coda-lavori-generica.md),
[brief-db-coda-lavori-generica.md](work-done/brief-db-coda-lavori-generica.md).

**Anello 1 (`ui`) — Dashboard home a card KPI configurabili.** Lo schema `ui`
acquisisce il secondo consumatore dopo le liste: catalogo widget, composizione
della home e **preferenza utente**, risolti da `ui.fn_resolve_dashboard_config`
con filtro sui permessi dell'operatore. Stesso impianto a cascata delle liste
configurabili (sistema → profilo → emittente → utente). Vedi
[brief-db-dashboard-home.md](work-done/brief-db-dashboard-home.md),
[brief-be-fe-dashboard-home.md](work-done/brief-be-fe-dashboard-home.md).

**Anello 3 (vendite) — Lineage documenti: colonna lista + pannello «Passaggi».**
Grafo di genealogia dei documenti di vendita (`vw_documento_lineage_nodi` /
`archi`, `fn_documento_lineage`) esposto come pannello «Passaggi» nei 6 drawer
documento e come colonne **pratica / fase / transito** nelle 5 liste: da un
documento si risale a monte e si scende a valle senza uscire dal drawer. Vedi
[brief-db-lineage-documenti-vendite.md](work-done/brief-db-lineage-documenti-vendite.md),
[brief-be-fe-lineage-documenti-vendite.md](work-done/brief-be-fe-lineage-documenti-vendite.md).

**Qualità di modello — guard sorgente polimorfa, coerenza `tx_id`, RLS
commesse.** Tre interventi di igiene strutturale: (1) il **guard sulla sorgente
polimorfa** esisteva ma **non era agganciato a nulla** — agganciato, dati
bonificati, catena di popolamento corretta e convenzione documentata
([sorgente-polimorfa.md](../guide/sorgente-polimorfa.md)); i 13 pgTAP che ne
dipendevano sono stati bonificati (rossi della suite 131 → 111); (2) **coerenza
`tx_id`**: mai pubblicare nella GUC un id non registrato — il difetto bloccava
ogni ambiente **senza** canale di log (CI compresa), e ora la CI esercita il
caso peggiore invece di aggirarlo con un bypass; (3) **RLS scope emittente
estesa a `vendite.commesse` e `commesse_attivita`**, che chiude le scritture
della famiglia commesse raggiungibili cross-emittente e completa l'ondata
operatori. Vedi
[brief-db-guard-sorgente-polimorfa.md](work-done/brief-db-guard-sorgente-polimorfa.md),
[brief-db-bonifica-pgtap-sorgente-polimorfa.md](work-done/brief-db-bonifica-pgtap-sorgente-polimorfa.md),
[brief-db-coerenza-tx-id-non-registrato.md](work-done/brief-db-coerenza-tx-id-non-registrato.md),
[brief-db-rls-commesse.md](work-done/brief-db-rls-commesse.md).

**Trasversale (frontend) — radici i18n uniformi e chiusura residui PrimeVue 3.**
21 radici i18n piatte riportate sotto le rispettive aree, radici morte rimosse,
guard `--strict-roots` pulito e parità it/en integra: un indirizzo i18n
inesistente non produce un errore, non mostra **nulla** — il difetto è
invisibile, e l'archivio aveva due stili di sistemazione conviventi scelti a
caso. In parallelo chiusi i residui PrimeVue 3 (`TabView`→`Tabs`,
`InputSwitch`→`ToggleSwitch`) e corretto lo standard che ancora li prescriveva:
era debito che **faceva scrivere codice nuovo sbagliato**. Vedi
[brief-i18n-radici-uniformi.md](work-done/brief-i18n-radici-uniformi.md),
[brief-fe-migrazione-primevue4-tabs.md](work-done/brief-fe-migrazione-primevue4-tabs.md).

## 12 luglio 2026

**Anello 3 (vendite) — Indirizzi documento UX v2 (building block cross-dominio).**
Nuovo BB condiviso per gli indirizzi dei documenti di vendita: una sezione inline
(mostra l'indirizzo di **consegna** di default + contatore "+N altri") e un drawer
di gestione (scelta dall'anagrafica del cliente "usa questo" o indirizzo libero
una-tantum), con **snapshot congelato** all'emissione. Lato BE, factory indirizzi
documento parametrica su una `IndirizziDocumentoConfig` per dominio + endpoint
CRUD (`/<dominio>/<id>/indirizzi/`) su **tutti e 5 i domini**
(preventivi/offerte/contratti/ordini/DDT) e **auto-assegnazione** dell'indirizzo
di default (indirizzo di ruolo `CON`, fallback `FATT`) in create + fallback
post-push. Pilota sul DDT, poi rollout ai 4 drawer. Vedi
[brief-design-indirizzi-documenti-vendita.md](work-done/brief-design-indirizzi-documenti-vendita.md).

**Anello 3 (vendite) — Riepilogo IVA DDT + colonna Emittente lista.** Vista
derivata `vw_ddt_riepilogo_iva_dettaglio` (una riga per aliquota, righe con prezzo
NULL escluse: un DDT di solo trasporto non ha riepilogo) esposta dal drawer via
`RiepilogoIvaTable` (componente cross-dominio). Seed opt-in della colonna
"Emittente" nel catalogo lista DDT (parità con le altre 4 liste documento). Vedi
[brief-db-ddt-riepilogo-iva.md](work-done/brief-db-ddt-riepilogo-iva.md),
[brief-db-ddt-colonna-emittente-catalogo.md](work-done/brief-db-ddt-colonna-emittente-catalogo.md).

## 11 luglio 2026

**Anello 2 (documenti) — Stampa PDF DDT: quinto dominio del motore documentale.**
Il DDT diventa il 5° consumatore del motore documenti parametrico: template
`DDT_VENDITA` pubblicato + builder del contesto documentale del DDT (testata,
trasporto, righe, totali, note). L'anteprima in bozza e il documento definitivo
all'emissione seguono il pattern degli altri domini (`pdf_mode` data-driven da
`stati_doc_ddt`). Export lista DDT (CSV/XLSX) allineato agli ordini.

**Anello 3 (vendite) — 2 refactor BB (regola del 2).** (1) Factory
`build_documenti_sorgente_views` per generare le 7 view "documenti per sorgente"
di ogni dominio (~80 righe/dominio); (2) `add_emittente_scope_condition`
(`apps/core/db/emittente_scope_helpers`) che risolve l'array di scope emittente
**una volta** in Python (era 2×/query in 5 repository). Vedi
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md) §13.

## 10 luglio 2026

**Anello 3 (vendite) — DDT di vendita (DB + BE + FE).** Nuovo documento del ciclo
attivo: il documento di trasporto. Testata (dati di trasporto: causale, aspetto
beni, vettore, mittente, colli/pesi/volume, targa, autista, tracking) + righe
(prezzo/IVA **opzionali** → DDT di solo trasporto) + componenti BoM condivisi.
Nascita per **evasione** di un ordine confermato — legame **1:N** con **residuo
per riga** (`ordini_righe_fulfillment` append-only: l'evasione aggiunge la
quantità evasa, non la sottrae) — oppure **standalone** manuale. Stati
**data-driven** `DRAFT → EMESSO → SPEDITO → CONSEGNATO` (+ `RESO`/`ANNULLATO`) via
matrice `config.transizioni_stati_ddt` + `fn_available_actions_ddt`. **Numero
assegnato all'emissione** (non alla nascita, `trgfn_ddt_gen_numero_emesso`) e poi
immutabile. Cliente/destinatario immutabili post-creazione. Push a commessa
(sorgente `DDT_VENDITA`) per la fatturazione. Componenti BoM estesi al 5° dominio.
Guida operativa: [gestione-ddt.md](../guide/gestione-ddt.md). Vedi
[brief-db-ddt-vendita-evasione-e-stati.md](work-done/brief-db-ddt-vendita-evasione-e-stati.md),
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md),
[brief-fe-ddt-vendita.md](work-done/brief-fe-ddt-vendita.md).

**Addendum SCOPE §15 — emittente memorizzato + RLS su DDT.** Colonna
`vendite.ddt.emittente_fiscale_id` (NOT NULL) memorizzata sul documento (mirror
ordini/preventivi), ereditata dall'ordine sorgente in evasione o risolta dal
billing account per lo standalone (`trgfn_ddt_normalize`), con policy RLS
`rls_ddt_ef_whitelist` e guard di scope in scrittura: un operatore non emette DDT
fuori dal proprio scope emittente. `vw_ddt_lista` espone `emittente_fiscale_id`
per il filtro applicativo (mirror `vw_ordini_lista`).

## 28 giugno 2026

**Qualità di modello — convenzione `codice_interno` / `codice` (cross-anello).** Bonifica
della coppia di colonne delle tabelle `config.*`/lookup (`codice_interno` **immutabile** per
la logica, `codice` **mutabile** per il display), in due interventi complementari:

- **Mislabel alias** `codice_interno AS *_codice` (alias bugiardo che esponeva l'immutabile
  col nome del mutabile): sweep completo DB (viste/funzioni liste contratti/clienti/fornitori/
  coda, indirizzi/istanze, search-detail) + migrazione consumer BE/FE a `*_codice_interno` +
  guardrail CI catalog-based bloccante. Vedi
  [brief-naming-stato-codice-interno.md](work-done/brief-naming-stato-codice-interno.md).
- **Hardcode contro la colonna mutabile** (`WHERE codice = 'X'` dove la logica doveva usare
  `codice_interno`): audit multi-superficie, **21 BUG_DUAL + 7 CANDIDATE** corretti. DB: 16
  oggetti della pipeline commesse→push→fatturazione (`fn_list_*_da_pushare`, `config.sorgenti`,
  `stati_doc_*`) + fix di un **bug reale** in `fn_lookup_utilities_per_ba` (ritornava 0 righe
  perché `codice ≠ codice_interno`). BE: render engine documenti, lookup documenti/sorgenti,
  approvazioni prezzo, super-admin riconosciuto via enum `tipo`, categorie clienti. Estratto il
  BB `resolve_config_id_by_codice_interno` (regola del 2) e corretti **2 bug di create**
  emersi in review (colonna `codice_interno NOT NULL` aggiunta senza default → INSERT rotto su
  categorie clienti ed email account). Vedi
  [analisi-hardcoded-codice.md](work-done/analisi-hardcoded-codice.md).

**Anello 3 (vendite) — gate EVASO ramo commessa.** Corretta l'asimmetria logica col ramo
ordine nel gate EVASO della pratica (bug logico del modello), applicata e **verificata
runtime** (smoke preventivo→EVASO al push, evento `DOMINIO_PREVENTIVO_EVASO`, re-push su EVASO
bloccato). Avviato lo smoke E2E push commesse→fatturazione. Vedi
[brief-db-gate-evaso-commessa-asimmetria.md](work-done/brief-db-gate-evaso-commessa-asimmetria.md),
[a-test-push-commesse-fatturazione.md](work-done/a-test-push-commesse-fatturazione.md).

**Anello 2 (pratiche) — sospensioni anti-overlap + guard data manuale.** Anti-sovrapposizione
delle sospensioni pratica + guard sulla data manuale (DB + piano BE/FE). Vedi
[brief-db-sospensioni-anti-overlap-data-manuale.md](work-done/brief-db-sospensioni-anti-overlap-data-manuale.md).

**Sicurezza AI/agenti.** Revisione critica del documento di considerazioni sicurezza AI
(2026-06-26) tradotta in piano di allineamento documentale/operativo. Vedi
[analisi-sicurezza-aggiornata.md](work-done/analisi-sicurezza-aggiornata.md).

## 20 giugno 2026

Anello 3 (vendite): **batch fatturazione automatico end-to-end operativo**. Driver CRON
`run-until-done` con discovery a **corsie** `(emittente, tipo_doc_fiscale, utility)`
(`fn_list_emittibili_lane` + lane utility-id), **sync dello stato documentale della fattura
per-step** (`1→2→8`: l'IVA è certificata in EMESSA prima della numerazione in DEFINITIVA;
fix asimmetria di orchestrazione, matrice e guard invariati), registrazione delle run
headless in `job_run_log` (`script.fn_job_run_start/end`), contesto sistema/RLS per il batch.
Hardening commesse→fatturazione: **normalize + guard `tipo_doc_fiscale` emittibile**
(invariante di riga `APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`, codice 497 + CHECK backstop
— evita "fatturato perso in silenzio"), snapshot pricing v5 nel push commesse, fan-out
compositi multi-sorgente, capability azioni stato commessa (`fn_available_actions_commessa`),
pull commessa→`attivita_fatturabili` agganciata agli step DRAFT. La **pipeline fatturazione
passa da "operativa (manuale)" a batch automatico end-to-end**. Vedi
[piano-fix-stato-fattura-pipeline-per-step.md](work-done/piano-fix-stato-fattura-pipeline-per-step.md),
[brief-db-emittibili-lane-tipo-doc-fiscale.md](work-done/brief-db-emittibili-lane-tipo-doc-fiscale.md),
[brief-db-guard-tipo-doc-attivita.md](work-done/brief-db-guard-tipo-doc-attivita.md).

## 13-19 giugno 2026

Anello 2 (pratiche): estensioni workflow v2 del motore (validato sul primo consumatore,
vendite). Arco completo del periodo:

- **Completamento flusso event-driven**: rimosso l'endpoint manuale M2; il completamento è
  guidato dagli eventi del workflow.
- **Azione di completamento flusso data-driven**: l'azione che chiude lo step è risolta da
  configurazione, non cablata.
- **Aggancio documento↔flusso** (ROOT per-flusso): il documento sorgente (es. preventivo) si
  àncora a uno **specifico flusso** della pratica, non alla sola testata; guard di coerenza
  flusso↔pratica (codice 493).
- **Contesto pratica del preventivo a 3 livelli**: `soggetto → ruolo → istanza`
  (derivata/filtrata), con guard di coerenza.
- **Chiusura pratica workflow-driven**: la pratica si chiude solo a flussi obbligatori
  completati; il flusso `chiude_pratica` va eseguito per ultimo (guard 485/492).
- **Esito configurabile dei flussi**: modalità **MANUALE / AUTOMATICO / CONTESTUALE** con
  `esito_default` (guard 494/495: AUTOMATICO solo su step a direzione INTERNA).
- **Giornale più parlante** + appendice di configurazione workflow nella documentazione.
- **Audit utente reale** su `pratiche.*`: `user_update`/`data_update` valorizzati
  dall'operatore reale + trigger insert-only/append-only sul giornale.
- **Assegnazione del singolo flusso a operatore/reparto** con policy **reparto-first**
  (`flussi.risorsa_umana_id` / `unita_organizzativa_id`; eligibilità A/B/C/D — skill-lock,
  competenza, reparto anagrafico, libero; codice 496) tramite `fn_prendi_in_carico_flusso`.
- **Coda lavoro operatore** a 4 livelli (`fn_coda_lavoro_operatore`:
  ASSEGNATO > COMPETENZA > REPARTO > LIBERO) e **consumer FE pannello "Le mie attività"** +
  gating del permesso di assegnazione.

Vedi [analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md),
[brief-design-esito-configurabile-flussi.md](work-done/brief-design-esito-configurabile-flussi.md),
[brief-db-assegnazione-flusso.md](work-done/brief-db-assegnazione-flusso.md),
[brief-design-coda-lavoro-mie-attivita.md](work-done/brief-design-coda-lavoro-mie-attivita.md).

## 11 giugno 2026

Anello 3 (vendite): **ordini di vendita** sviluppati end-to-end DB+BE+FE (CRUD, conferma, stato EVASO, stampa PDF, conversione preventivo/offerta→ordine, univocita' offerta→contratto XOR ordine); **pratica PREVENTIVI** eseguita end-to-end come primo consumatore reale del motore `pratiche` (handler `CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa, smistamento riga-per-riga, commesse multi-sorgente) → Anello 2 `pratiche` passa a **validata con primo consumatore**; workflow pratiche v2 (ripetibilita', bivi condizionali, lenti contesto, guard chiusura). Vedi [analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md) e [analisi-ordini-vendita.md](work-done/analisi-ordini-vendita.md).

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
