# Brief BE/FE — posting contabile e abbinamento alla rata

> **Cos'è.** Il **piano di sviluppo backend e frontend** del cantiere
> «contabili di pagamento». Il terzo documento di una famiglia di tre, e i tre
> non si sovrappongono:
>
> | Documento | Che cosa contiene | Chi lo aggiorna |
> | --- | --- | --- |
> | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) | le **decisioni di dominio** (D1…D15) col loro perché | chi decide (Tid) |
> | [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md) | le **misure del terreno DB** e i passi, lotto per lotto | il team DB |
> | **questo** | che cosa si costruisce **sopra**: endpoint, service, repository, schermate | BE/FE |
>
> ⚠️ **Divisione del lavoro, per non far divergere tre sedi.** Una decisione di
> dominio si aggiorna **solo** nel brief madre; una misura del DB o un passo di
> migrazione **solo** nel piano DB; un contratto API o una schermata **solo
> qui**. Se una decisione cambia, si cambia là e qui si riporta il passo che ne
> discende — mai il contrario.
>
> 🎉 **REVISIONE DEL 2026-08-24 — il terreno è cambiato sotto il piano.** La
> prima stesura (22/08) era scritta con il DB al **lotto 3 di 7** e diceva:
> *«tre slice su sette si possono cominciare oggi, le altre aspettano»*.
> ✅ **Il team DB ha chiuso tutti e sette i lotti il 2026-08-22**: 71 changeSet
> applicati, 14 pgTAP nuovi, doc manuale completa. **Nessuna slice aspetta più
> niente dal codice DB.** Il piano è stato rimisurato riga per riga contro il
> database vivo e contro il codice BE/FE — non contro sé stesso.
>
> ⭐ **E dal 2026-08-24 non è più solo un piano: il BACKEND è partito.**
> `/api/v1/pagamenti/` non è più un 404 — ci sono **quattordici rotte**, il repository,
> il service e **78 test verdi**, con **zero regressioni** sulla suite (misurate
> contro un albero pulito, non a occhio). Lo stato riga per riga è in **§10**.
> 🔴 Il **frontend** è ancora fermo a due `.gitkeep`, e le liste aspettano i
> loro seed.
>
> ⭐ **Che cosa è cambiato nel piano, in tre righe.** Le sette slice non hanno
> più dipendenze DB e si riordinano per **valore collaudabile**; i **nove
> prerequisiti** al team DB **diventano tre** (due sono già stati consegnati
> senza che nessuno li chiedesse, due non erano affatto del DB); e **cinque cose
> che il piano del 22/08 dava per vere oggi sono sbagliate** — §1.5, ed è la
> sezione da leggere per prima.
>
> ✅ **Le domande aperte sono ZERO**: §7 è il registro di come sono state chiuse, tutte il 2026-08-24. ⭐ Da qui in poi si scrive codice. Tid ne ha chiuse due
> il 24/08 — **Q-1** (nasce l'`ui_action` `confirm_and_retry`) e **Q-2**, che è
> caduta insieme al gesto che presupponeva: 🔴 **con D1-ter il pagamento di una
> rata non si spezza**, e la slice dedicata sparisce dal piano. Ne nasce una
> nuova, **Q-10**: un'asimmetria del modello che il lotto 5 ha lasciato dietro.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| ✅ **Il DB è finito** | **Sette lotti su sette chiusi** il 2026-08-22. `pagamenti` ha 12 tabelle, **8 funzioni pubbliche**, **2 viste**, 15 guard, 2 matrici di transizione e la **RLS accesa** su tutto. Il posting, la rata, il perimetro e le sistemazioni **esistono e sono provati** (14 pgTAP) | §1.3 · §1.4 |
| ✅ **Già pronto lato BE** | `apps.pagamenti` in `INSTALLED_APPS` · area funzionale `pagamenti` (id 7) · dominio in `DOMAINS` del FE · **BE-1 chiusa e cumulativa**: verificato oggi che **778 codici su 778** del catalogo hanno la loro classe in `error_policies_generated.py` e che **tutti** i codici di questo cantiere hanno anche il ripiego · i **quattro cataloghi** di `pagamenti` sono in whitelist della lookup generica | §1.1 |
| ~~🔴 **Da zero**~~ | ✅ **Non più: il 28/08 non c'è più niente da zero.** `urls_v1.py` monta 23 rotte · `views.py` ha 20 view · `frontend/src/pagamenti/` ha 5 viste, 8 componenti, 5 store, i vocabolari e le etichette · `DOMAIN_MENUS['pagamenti']` ha **6 voci** · quattro `ui.lista_definizione` seminate (⚠️ i **canali** no, e per questo la loro lista **non** è configurabile — §10.4-ter) | §1.2 · §10 |
| 🔴 **Cinque misure del 22/08 oggi sbagliate** | la vista **non si chiama** `vw_rate_sovra_incassate` · la forzatura **non è un flag di payload**, è una colonna della riga · il lookup delle rate **non è un prerequisito DB** · l'`ui_action` **non sta a catalogo DB** · `fn_get_or_create_vendite_contabile` ha **cambiato firma** | §1.5 |
| 📋 **Il piano** | **Sei slice**, nessuna in attesa. Ordinate per valore: S0 telaio → S1 distinta e righe → **S2 la registrazione** → S3 rata e capienza → S4 perimetro e canali → S5 sistemazioni. ⛔ La settima (spezzatura) **è caduta con D1-ter** | §3 |
| 🔌 **Il contratto** | 18 endpoint, grammatica URL di `api.md`. ⭐ Il posting è **una sola `SELECT`**; l'abbinamento è **un verbo solo** che porta anche la forzatura | §4 |
| 🎨 **Il frontend** | ✅ **FATTO (28/08).** 6 schermate, 3 drawer, 4 dialoghi. **17 building block riusati** e **quattro estratti**: `useForzaturaConfermata`, `FatturaLookup`, `useLetturaTreStati`, più i due di dominio (`etichette`, `useCanaliIncasso`) | §5 · §10.4-ter |
| 🟡 **Al team DB** | ⭐ **Consegnato tutto quanto era stato chiesto** (allineato dal team DB il 27/08). ✅ **Chieste il 28/08 e CONSEGNATE lo stesso giorno** ([brief](../work-done/brief-db-perimetro-canali-e-correzione-guidata.md)): la **policy RLS** su `enti_incasso` (trovata da E-4) e la madre della **correzione guidata** (Q-7). ⭐ Il team DB ha corretto la mia policy proposta — così com'era avrebbe reso la tabella **non scrivibile** — e ha **smentito con una misura** la risposta che aveva dato a C-1. I quattro **seed di lista** con le 53 chiavi i18n, le due righe dell'**azione di processo**, `fn_get_saldo_fattura` a **tre numeri**, più due cose che non erano nell'elenco: il **404 dei canali** e la **seconda porta** del conto di incasso. 📮 Resta differita solo la madre della correzione | §6 · §6-bis |
| ⭐ **Stato del codice** | ✅ **BACKEND E FRONTEND COMPLETI.** BE: 23 rotte, SQL provati con EXPLAIN sul database vero, §6-bis chiuso e DATO-1 chiuso (28/08). FE: fondamenta, 4 liste, il giro della distinta, i canali di incasso e le sistemazioni — **tutto il 28/08**. ✅ **E la correzione guidata (Q-7), l'ultimo gesto**, chiusa lo stesso giorno con la madre consegnata dal team DB. ⭐ **Il cantiere non ha più niente di aperto in codice**: restano due cose che non lo sono — l'azione di processo da assegnare a un profilo, e la **decisione C-1** che il team DB ha lasciato a Tid | §10 |
| 🔴 **Che cosa resta** | ⛔ **Niente da costruire, e niente mai VISTO**: `pagamenti` ha **zero righe**. Il copione della validazione a video è [collaudo-in-app-incassi-distinte-e-sistemazioni.md](collaudo-in-app-incassi-distinte-e-sistemazioni.md), e **non parte** finché `registra_distinta` non è assegnata a un profilo (**P-0**). ⚠️ Un punto è gia' noto prima di cominciare: la tendina dei centri offre i **due centri interni** | §collaudo |
| ✅ **Domande aperte** | **ZERO.** Nove chiuse il 24/08 — **Q-1** `confirm_and_retry` · **Q-2** cade con D1-ter · **Q-3** apertura con form · **Q-4** due porte una lista · **Q-5** nasce `registra_distinta` · **Q-6** saldi con **una sede sola** (§2.7) · **Q-7** correzione guidata · **Q-8** lookup in `vendite` · **Q-10** simmetria del saldo fattura — più Q-9 chiusa da sé | §7 |

---

## 1. Il terreno, rimisurato il 2026-08-24

Misurato **sul codice e sul database vivo**, non sui brief.

### 1.1 ✅ Ciò che esiste già, e non va costruito

| Cosa | Dove, verificato | Perché conta |
| --- | --- | --- |
| App Django registrata | `zeroerp_backend/settings.py` — `'apps.pagamenti'` in `INSTALLED_APPS` | non serve creare l'app: serve **riempirla** |
| Area funzionale | `config/aree_funzionali.csv` — id **7**, codice `pagamenti`, schema `pagamenti` | `DomainAPIView.area_funzionale = "pagamenti"` risolve **da subito** |
| ⭐ **Tutti** i codici errore del cantiere | **rimisurato oggi con uno script**, non a campione: il catalogo ha **778 codici**, `error_policies_generated.py` ne ha **778**, zero mancanti. E per i codici di `pagamenti` (id ≥ 940) **anche il ripiego è completo**, zero mancanti | ⭐ **BE-1 è chiusa, e stavolta in modo cumulativo**: copre anche i 17 codici nati coi lotti 4-7 (961…977). Il piano DB la elenca ancora come coda aperta in cinque punti: **non lo è più** |
| Whitelist della lookup generica | `apps/core/db/dbops_repository.py:104-108` — `centri_riscossione`, `enti_incasso`, `vendite_contabili_stati`, `vendite_contabili_righe_stati` | ⭐ i quattro menu a tendina **non richiedono nessun endpoint nuovo**: `GET /core/lookup/codici/?rel=pagamenti.…` risponde già |
| Il filtro degli stati ritirati | `dbops.fn_get_lookup_codici` filtra `obsoleto_dal` | ⭐ `STORNATA` (ritirata il 2026-08-21, verificato nel CSV) **non compare in nessun menu**, e non perché qualcuno se lo ricorda |
| Le rate di una fattura | `vendite_repository.list_fattura_scadenze()` (`vendite_repository.py:2740`) | 🔴 **rovescia un prerequisito**: il lookup delle rate non ha bisogno di niente dal DB. Vedi §1.5 e **Q-8** |
| Il canale dell'`ui_action` fino al FE | `error_translator.py` la mette nell'envelope, `useApiHandler.js:115` la espone come `azioneUi` | 🔴 **rovescia un altro prerequisito**: la strada (a) di **Q-1** costa **una riga di Python e un ramo di Vue**, non un giro col team DB |
| Il dominio nella sidebar + i18n | `core/navigation.js:110` e `locales/it.json` | icona, rotta radice e legame con lo schema DB (per `useReadonlyMode`) ci sono già |
| La GUC `app.ruolo_applicativo` | la impostano **sia** `jwt_audit_middleware` **sia** `coda_lavori/context.py` | ⭐ **BE-7 è quasi chiusa**: i due percorsi che contano la mettono già. Resta da verificare ciò che gira **fuori** da entrambi (§2.6) |

### 1.2 🔴 Ciò che è vuoto per davvero *(riverificato il 2026-08-24)*

| Cosa | Stato misurato |
| --- | --- |
| `backend/apps/pagamenti/api/urls.py` | `urlpatterns = []` |
| `backend/apps/pagamenti/api/views.py` | `# Create your views here.` — **una riga** |
| `urls_v1.py` e montaggio in `zeroerp_backend/urls.py` | **non esistono**. `/api/v1/pagamenti/…` è un 404 secco |
| `apps/pagamenti/{services,db}/` | solo `__init__.py` e `README.md`. **Zero moduli** |
| Chiamate alle funzioni DB di `pagamenti` da Python | **zero**, in tutto `backend/`: le uniche occorrenze della stringa sono la whitelist della lookup e i commenti dei codici errore |
| `frontend/src/pagamenti/` | `components/.gitkeep` e `views/.gitkeep` |
| `DOMAIN_MENUS['pagamenti']` | `core/navigation.js:201` — **`[]`** |
| `ui.lista_definizione` per `pagamenti` | **nessuna riga**. 🔴 Ogni lista ha un **prerequisito di seed**, non solo FE |

### 1.3 ✅ Lo stato del DB: sette lotti su sette

| Lotto | Contenuto | Stato | Che cosa sblocca **qui** |
| --- | --- | --- | --- |
| **1** | terreno: centri, `stato_id` NOT NULL, codici errore | ✅ 21/08 | lookup dei centri, messaggi parlanti |
| **2** | vocabolario, transizioni, sei guard, `origine`, `importo_dichiarato` | ✅ 21/08 | ⭐ tutta la gestione della distinta |
| **3** | «il fondo si difende»: `ESEGUITO`, `fondo_source_id`, reset che cancella | ✅ 22/08 | la difesa che precede il posting |
| **4** | ⭐ **la madre** `fn_posta_contabile` + chiusura automatica | ✅ 22/08 01:29 | **la registrazione** |
| **5** | la rata: `scadenza_id`, capienza, forzatura, `fn_get_saldo_rata`, `vw_rate_fuori_capienza` | ✅ 22/08 | l'abbinamento alla rata e la **forzatura a due tempi** |
| **6** | il perimetro: conto sull'ente, RLS su 12 tabelle, scope in scrittura | ✅ 22/08 10:17 | la coda visibile **a chi deve** |
| **7** | le sistemazioni: `pagamenti.sistemazioni`, `vw_eccedenze_da_sistemare`, due verbi | ✅ 22/08 12:20 | il giro rimborsi/riporti/compensazioni |

> ⭐ **La conseguenza operativa, e va detta in testa.** Il 22/08 questo brief
> apriva con *«il gesto che dà senso a tutto non c'è»*. **Adesso c'è**, e c'è
> tutto il resto: il collo di bottiglia si è spostato **interamente** su BE/FE.
> Da oggi ogni giorno che passa è un giorno in cui il database sa registrare
> denaro e **nessuno può chiederglielo**.
>
> ✅ **E l'unica eccezione è caduta il 2026-08-24.** Nessuno dei due emittenti
> aveva un conto con `uso = 'INCASSO'` censito (S3-3 del piano DB, DATO-1), e
> senza **nessun `ente_incasso` era creabile** — voluto: si fallisce alla
> configurazione, non in esercizio. **Tid l'ha configurato in-app** con due conti
> fittizi di test, uno per emittente: `IT00TESTINCASSO0000000001` e
> `…0002`. ⭐ **Servivano due IBAN distinti** perché un conto `INCASSO` appartiene
> a **un solo** soggetto — è la garanzia da cui il database ricava di chi sono i
> soldi arrivati prima della fattura.
>
> ⚠️ **Due avvertenze che restano.** Il perimetro adesso è **vero anche se il dato
> è finto**: se i due IBAN fossero sull'emittente sbagliato, le liste
> mostrerebbero la cosa sbagliata **senza dare errore**. E in produzione servono
> gli IBAN reali: ⛔ questi non devono viaggiare — si riconoscono dal nome, ed è
> il motivo per cui sono scritti così.

### 1.4 ⭐ La superficie DB, coi nomi veri

Questo è il **contratto di chiamata** su cui si scrive il repository. Ogni firma
è stata letta dalla doc auto-generata, non ricordata.

| Oggetto | Firma / colonne | Note per chi la cabla |
| --- | --- | --- |
| `fn_get_or_create_vendite_contabile` | `(p_centro_riscossione_id, p_data_contabile, p_data_registrazione DEFAULT CURRENT_DATE, p_ente_incasso_id DEFAULT NULL, p_lotto_id DEFAULT NULL, p_codice_stato_interno DEFAULT 'BOZZA', p_meta DEFAULT '{}', p_origine DEFAULT 'GENERATA') → bigint` | 🔴 **firma cambiata il 22/08**: `p_compensazione_id` **non esiste più** (D15-e, verso girato). ⭐ Il BE **non passa l'operatore**: la funzione lo mette, e sulla `MANUALE` la chiave di riuso lo comprende (D12-a) |
| `fn_posta_contabile` | `(p_contabile_id, p_righe_attese DEFAULT NULL, p_totale_atteso DEFAULT NULL)` → `movimenti_creati, righe_postate, righe_saltate, totale_postato, esito` | ⭐ **una sola `SELECT`**, atomica per costruzione. `esito ∈ {POSTATA, NULLA_DA_POSTARE}` e **non solleva** sul secondo caso. ⚠️ I due parametri della dichiarazione sono **facoltativi ma legati**: o tutti e due o nessuno |
| `fn_get_saldo_rata` | `(p_scadenza_id, p_escludi_contabile_riga_id DEFAULT NULL)` → `saldo, in_lavorazione, incassato, has_movimenti` | ⭐ **tre numeri**, e il terzo è §2.4: `incassato` esclude i centri interni |
| `fn_get_saldo_fattura` | `(p_fattura_id)` → `saldo, has_movimenti` | 🔴 **due numeri, non tre**: a livello di fattura l'«incassato» **non esiste**. È **Q-10** |
| `fn_get_saldo_fattura_contabili` | `(p_fattura_id)` → `saldo_contabile, has_righe_postabili` | il **dichiarato** (righe `is_postabile` su distinte non finali) |
| `fn_conferma_sistemazione` | `(p_sistemazione_id, p_ente_incasso_id DEFAULT NULL)` → `contabile_id, fondo_source_id, esito` | ⚠️ il **canale del rimborso si chiede qui**, non alla registrazione |
| `fn_annulla_sistemazione` | `(p_sistemazione_id, p_motivo DEFAULT NULL)` → varchar | il motivo si **fonde** con quello già scritto |
| `vw_rate_fuori_capienza` | `motivo, scadenza_id, fattura_id, anno, serie, fattura_numero, billing_account_id, emittente_soggetto_ruolo_id, numero_rata, data_scadenza, importo_rata, registrato, residuo, incassato, in_lavorazione, righe_forzate, motivi_forzatura` | 🔴 **non si chiama** `vw_rate_sovra_incassate`. `motivo ∈ {SOVRA_INCASSATA, MOVIMENTO_CONTRARIO}` |
| `vw_eccedenze_da_sistemare` | `fattura_id, fattura_numero, fattura_data, emittente_…, cliente_…, billing_account_id, totale_a_pagare, residuo, eccedenza, chi_e_in_credito, eccedenza_cliente, documenti_cliente, sistemazioni_in_bozza, sistemazioni_confermate` | ⭐ porta **già** il raggruppamento per cliente in finestra: la schermata non deve sommare niente |
| `pagamenti.sistemazioni` | `destinazione ∈ {RIPORTO, RIMBORSO, COMPENSAZIONE}` · `stato ∈ {BOZZA, CONFERMATA, ANNULLATA}` · `fattura_destinazione_id` obbligatoria su RIPORTO/COMPENSAZIONE e **vietata** su RIMBORSO · `motivo` obbligatorio su ANNULLATA e RIPORTO | ⭐ la **registrazione dell'atto è un `INSERT`**, non un verbo: una scrittura sola non ha bisogno di una madre |

**I due vocabolari, letti dal CSV di seed** — ⛔ non si cablano nel FE:

```text
distinta : BOZZA · IMPORTATA · VALIDATA · CHIUSA(final) · ANNULLATA(final)
riga     : IMPORTATA · DA_ABBINARE · ABBINATA(is_postabile, richiede_abbinamento)
           SOSPESA · SCARTATA · POSTATA(final) · STORNATA(ritirata 21/08)
```

⭐ **`richiede_abbinamento` è una colonna del catalogo**, e vale una regola di
interfaccia: *quali stati pretendono fattura e cliente lo dice il database*. Il
form della riga legge quel flag, **non** un `if stato === 'ABBINATA'`.

### 1.5 🔴 Cinque cose che il piano del 22/08 dava per vere, e oggi sono sbagliate

Le scrivo per prime perché **due tolgono lavoro** e **tre lo spostano**.

| | Diceva | Dice il codice oggi | Conseguenza |
| --- | --- | --- | --- |
| **1** | endpoint e schermata «rate sovra-incassate», vista omonima | la vista si chiama **`vw_rate_fuori_capienza`** e contiene **due motivi**: il sovra-incasso *e* il movimento contrario (un rimborso dove non era entrato niente) | cambiano il path (`/rate/fuori-capienza/`), il nome della schermata e **una colonna**: `motivo` è la prima cosa che si guarda, non un dettaglio |
| **2** | *«il payload porta `forzatura_confermata` + `motivo`»* | la forzatura è **stato della riga**: colonne `forzata` (NOT NULL default false) e `motivo_forzatura`. Il secondo tentativo riscrive la riga con `forzata = true` | ⛔ niente parametro inventato: la conferma **resta scritta** sul dato, ed è ciò che `vw_rate_fuori_capienza` legge (`righe_forzate`, `motivi_forzatura`) |
| **3** | DB-6: *«serve `vendite.fn_list_scadenze_fattura` o equivalente»* | `vendite_repository.list_fattura_scadenze()` **esiste dal cantiere stampa** e il saldo per rata lo dà `fn_get_saldo_rata` | ✅ **prerequisito annullato**: l'endpoint è BE puro. Vedi **Q-8** |
| **4** | DB-7: *«un `ui_action` nuovo a catalogo, se Q-1 va così»* | le `ui_action` vivono in **`apps/core/services/error_ui_overrides.py`**, che è **scritto a mano** e dichiara di non essere generato | ✅ **prerequisito annullato**: Q-1 opzione (a) è **una riga** nell'override + un ramo su `azioneUi` in `useApiHandler` |
| **5** | *«`POST /distinte/{id}/stato/` con `CHIUSA` fra i valori»* (implicito nella matrice) | la chiusura è **una conseguenza del registrare** (decisione di Tid, lotto 4): `fn_posta_contabile` porta la distinta a `CHIUSA` da sé | ⛔ **nessun gesto «chiudi»** nell'interfaccia. Gli stati chiedibili sono **tre**: `VALIDATA`, `BOZZA`, `ANNULLATA` |

📮 **E due code lasciate dai lotti che sono lavoro BE vero, non revisione di
piano** — vanno nella slice 0 perché sono minuti, non ore:

- il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` porta ancora la frase vecchia
  (*«non accetta altre righe»*), mentre il catalogo l'ha **allargata** il 22/08:
  ora dice anche *«e quelle che ha non si lavorano più»*. ⚠️ Il ripiego va
  riscritto **senza segnaposti** — il messaggio a catalogo ne ha due;
- **BE-10**: tre codici marcati obsoleti il 22/08
  (`E_CONTABILE_COMPENSAZIONE_CON_LOTTO`, `…_GIA_PRESENTE`, `…_LOTTO_ESCLUSIVI`)
  sono **ancora** in `error_messages_fallback.py`. Nessuno li solleva più:
  tenerli è tenere una frase pronta per un errore che non arriva.

---

## 2. I sette vincoli che governano questo cantiere

Non sono buone pratiche generiche: sono **decisioni già prese** che, se si
dimenticano, si pagano con del codice da buttare.

### 2.1 🔴 Il backend è sottile **per obbligo**

**BE-2 del piano DB**: il posting è **una sola `SELECT pagamenti.fn_posta_contabile(...)`**.

⛔ **Nessun `transaction.atomic()` attorno a più statement**, nessuna
orchestrazione Python, nessun ciclo che posta le righe una a una. L'atomicità è
**dentro la funzione**, e `api.md` §Atomicità dice esattamente questo per il
caso «l'operazione compone **solo** scritture DB».

⚠️ Il guardrail AST `test_transaction_atomicity_guardrail.py` gira in CI e vede
il livello repository: un service che componesse due `cursor.execute` di
scrittura fallirebbe la build. **È una rete, non la regola.**

⭐ E la stessa forma vale per gli altri due verbi madre consegnati dal lotto 7:
`fn_conferma_sistemazione` e `fn_annulla_sistemazione`. **Tre madri, tre
`SELECT`.**

### 2.2 ⭐ Il database dice il **fatto**, il frontend racconta

`fn_posta_contabile` **non solleva** quando non c'è niente da registrare:
risponde e dichiara l'esito (`POSTATA` / `NULLA_DA_POSTARE`).

| Livello | Che cosa fa |
| --- | --- |
| **DB** | dice che cosa è successo, con un vocabolario chiuso |
| **BE** | passa l'esito **senza interpretarlo**: non trasforma `NULLA_DA_POSTARE` in un 409, non lo inghiotte |
| **FE** | decide **la frase**: replay tecnico → silenzio; seconda pressione voluta → *«questa distinta è già registrata»* (**D3-c**) |

⛔ E il BE **non** deve «migliorare» l'esito: se lo trasformasse in un errore, il
database scriverebbe nel registro degli errori un errore che non è un errore —
che è la ragione esatta per cui è stato costruito così.

### 2.3 🔴 La **coerenza** si rifiuta, la **capienza** si segnala

**D14-b**, e adesso è **implementata**, non prevista:

```text
«questa rata è di questa fattura?»       → 🔒 E_RIGA_CONTABILE_RATA_INCOERENTE (400)
«c'è ancora spazio su questa rata?»      → ⚠️ E_RIGA_CONTABILE_CAPIENZA_SUPERATA (409)
```

La forma della segnalazione, **letta dal guard**:

```text
1° tentativo, forzata = false → RIFIUTATO, con la ragione e i numeri
2° tentativo, forzata = true  → ACCETTATO, e resta scritto sulla riga
```

⛔ **Nessun permesso, nessun pattern proponi/approva, un tempo solo**, e la
regola è **simmetrica** nei due versi (D14-e ha superato l'asimmetria che il
piano prevedeva).

✅ **Il problema di confine è risolto** (Q-1, chiusa da Tid il 24/08): un rifiuto
*confermabile* esce come un 409 qualunque, e a distinguerlo è l'`ui_action`
**`confirm_and_retry`** dichiarata su quel codice in `error_ui_overrides.py`. Il
FE ramifica sul comportamento, **non** su un elenco di codici.

⭐ **E con D1-ter (24/08) questa è diventata la strada ordinaria del
sovra-incasso**, non l'eccezione: si registra il fatto, l'eccedenza si vede
nell'elenco, e la decisione la prende una persona con un atto di sistemazione
(S5). ⛔ Non si spezza niente.

### 2.4 ⚠️ «Incassato» non è «postato», e la distinzione va nella **prima** misura

| Domanda | Che cosa si somma |
| --- | --- |
| «questa fattura è ancora da pagare?» | **tutti** i movimenti — il trasferimento la salda davvero |
| «quanto è **entrato in banca**?» | solo i centri di cassa: `is_fondo_fattura` e `is_compensazione` **esclusi** |

⇒ **Regola per questo cantiere**: qualunque colonna, badge o totale che dica
«incassato» **dichiara quale dei due è**, fin dalla prima riga di codice.

🔴 **E qui c'è una scoperta della revisione**: `fn_get_saldo_rata` risponde
**tre** numeri (registrato, in lavorazione, incassato); `fn_get_saldo_fattura`
ne risponde **due**. La distinzione che il dominio pretende **esiste sulla rata
e non sulla fattura** — cioè manca proprio al livello che l'operatore guarda per
primo. È **Q-10**, ed è l'unica domanda di questa revisione che tocca il
modello.

### 2.5 ⭐ La distinta manuale è **proprietà**, non risorsa contesa

**D12-a**: il raggruppamento della distinta manuale comprende **chi sta
lavorando** — ed è nel corpo di `fn_get_or_create_vendite_contabile`, verificato.
Da cui:

- ⛔ **niente lock**, niente colonne di blocco, niente sblocco d'emergenza;
- ⛔ **niente permesso «si confermano solo le righe proprie»**;
- ✅ resta la **dichiarazione** di D13 (`p_righe_attese` + `p_totale_atteso`) come
  **rete**: copre la stessa persona con due schede aperte.

### 2.6 🔴 *(nuovo, dal lotto 6)* `pagamenti.*` pretende **l'operatore**

~~Da lotto 6 le dodici tabelle di `pagamenti` hanno la RLS accesa con policy
`FOR ALL`.~~ 🔴 **FALSO, misurato il 2026-08-28 (E-4): sono QUATTRO su dodici.**

Hanno la RLS accesa le **transazionali** — `vendite_contabili`,
`vendite_contabili_righe`, `vendite_movimenti`, `sistemazioni` — e lì la policy
pretende davvero `app.ruolo_applicativo = 'OPERATORE'` **per leggere e per
scrivere**: un percorso senza quella GUC non vede niente e non scrive niente.

⛔ **Ma `enti_incasso` non ce l'ha**, e porta dato per emittente: il conto su cui
atterra il denaro, cioè **di chi sono i soldi**. Senza policy l'elenco dei canali
— IBAN compreso — è comune a tutti gli emittenti. Le sei tabelle di catalogo e
matrice è **giusto** che non l'abbiano; restano da decidere `sepa_mandati` e
`centri_riscossione`. 📮 Tutto in
[brief-db-perimetro-canali-e-correzione-guidata.md](../work-done/brief-db-perimetro-canali-e-correzione-guidata.md).

⚠️ **La lezione, che vale oltre questa riga.** Quella frase era scritta e
creduta, e nessun test poteva smentirla: una policy che non c'è non solleva
niente — dà un elenco più lungo del vero. ⭐ Le uniche cose che l'hanno trovata
sono state **una misura strutturale** (`relrowsecurity` tabella per tabella) e
**due operatori veri di due emittenti diversi**. Un conteggio sui dati di oggi
sarebbe stato zero ovunque, cioè verde per sottrazione.

✅ **Verificato oggi**: la impostano sia `jwt_audit_middleware` (ciclo web) sia
`coda_lavori/context.py` (worker). ⚠️ Resta da verificare, **una a una**, la
manciata di cose che girano fuori da entrambi (comandi `manage.py`, job di
servizio). `zeroerp_batch_fatturazione` ha `BYPASSRLS`: quelli non cambiano.

⚠️ **E vale la memoria del conteggio fail-closed**: una lista di `pagamenti` che
si svuota non è «nessun risultato», è **un perimetro che ha morso**. Ogni lista
di questo cantiere va provata con un utente **dentro** e uno **fuori** dal
perimetro, e la differenza va guardata.

### 2.7 🔴 *(nuovo, decisione di Tid 24/08)* I saldi hanno **una sede sola**

> *«Il drawer fattura non è l'unico posto dove vedere queste informazioni. A
> questo scopo dovrà nascere una funzione specifica che si occupi di fornire
> anche il saldo del cliente, quindi qualsiasi cosa che faremo deve essere una
> base unica per i saldi.»*

⛔ **Quindi non si costruisce «il pannello saldo della fattura».** Si costruisce
**la base dei saldi**, e la fattura è il suo primo consumatore.

| Livello | Regola |
| --- | --- |
| **BE** | **un solo modulo** legge le funzioni di saldo del database (`fn_get_saldo_fattura`, `fn_get_saldo_fattura_contabili`, `fn_get_saldo_rata`) ed espone una forma unica. ⛔ Nessun altro service, repository o view le interroga per conto suo |
| **Vocabolario** | i numeri si chiamano **sempre allo stesso modo** ovunque compaiano: `residuo` · `in_lavorazione` · `incassato`. Un livello può **non mostrarne** uno; ⛔ nessuno può **rinominarlo** o calcolarlo a modo suo |
| **FE** | un componente solo e un composable solo, che rendono quella forma. Ogni schermata sceglie **quali** numeri accendere, non **come** si chiamano |
| **Estensione** | ⭐ il **saldo cliente** è già previsto: la base nasce con tre livelli in testa — **documento, rata, cliente** — anche se il terzo si accende dopo. È sviluppo concentrico, non YAGNI |

🔴 **Perché è un vincolo e non una buona idea.** Un saldo calcolato in due posti
diverge alla prima regola nuova, e i saldi sono numeri su cui qualcuno decide se
sollecitare un cliente. ⚠️ E il progetto ha già il precedente: è la stessa
ragione per cui il pricing passa **solo** dal suo service.

⚠️ **E qui la base unica trova subito un dislivello**: al livello **rata** il
database dà tutti e tre i numeri, al livello **fattura** ne dà due — manca
proprio `incassato`. Non si sana con una somma nel backend (§7, **Q-10**).

---

## 3. Il piano — sei slice, nessuna in attesa

> ⚠️ **Le marcature di questa sezione sono state riallineate il 2026-08-29**,
> una riga per volta **contro il codice** e non contro la memoria. Fino a quel
> giorno erano ferme al 22/08: mostravano 🔴 su venti passi già costruiti, e un
> piano che dice rosso su ciò che è verde smette di essere leggibile — chi lo
> apre non sa più quali rossi contano.
>
> ⭐ **Ne restavano tre veri, e due erano difetti**: la frase sull'esito della
> registrazione (**P-5**) era un toast fisso che avrebbe detto «registrata» anche
> su `NULLA_DA_POSTARE`, e il rifiuto della dichiarazione (**P-6**) non
> rileggeva l'anteprima. Corretti lo stesso giorno. Il terzo — **A-8**, la base
> dei saldi — ✅ **costruito il 29/08**.
>
> ⭐ **Da lì il cantiere non ha più niente da costruire.** Restano due cose che
> non sono codice: l'azione `registra_distinta` da assegnare a un profilo
> (**P-0**) e la decisione **C-1**.

```text
  S0 telaio ──▶ S1 distinta e righe ──▶ S2 LA REGISTRAZIONE ──▶ S3 rata e capienza
                                                                      │
                    S4 perimetro e canali ◀───────────────────────────┤
                    S5 sistemazioni ────────────────────────────────◀─┘
```

⛔ **La settima slice non c'è più.** Il 22/08 il piano ne prevedeva una per la
**spezzatura di una riga**: è caduta il 24/08 con **D1-ter** — *«il pagamento di
una rata non si spezza»*. Non è stata rimandata: **non ha un caso**. Chi lavora a
mano scrive già due righe quando le destinazioni sono due; il caso «una riga
arrivata da fuori, da spalmare» nasce **solo con l'import** (D6), che non è in
perimetro. Vedi **Q-2** in §7.

**Come si mappa sul piano del 22/08** — le vecchie S3/S4 si fondono e si
riordinano, perché l'ordine vecchio era dettato dai lotti DB e i lotti non ci
sono più:

| Vecchia | Nuova | Perché |
| --- | --- | --- |
| S0, S1, S2 | S0, **S1** | le righe stanno con la loro distinta: sono **un drawer solo** |
| S3 (registrazione) | **S2** | sale: è **il primo valore vero** e adesso non aspetta niente |
| S4 (rata e capienza) | **S3** | scende di uno, ma `scadenza_id` entra **già in S1** (sotto) |
| S5 (perimetro e coda) | **S4** | invariata. ~~⚠️ bloccata da DATO-1~~ → ✅ **sbloccata il 24/08** (conti di incasso configurati) |
| S6 (sistemazioni) | **S5** | invariata: chiude **BE-4** e sblocca la **Fase D** del cantiere fondi |
| ~~R-4 (spezza)~~ | ⛔ **caduta** | **D1-ter, 2026-08-24**: il gesto non esiste più. Con essa cade `fn_spezza_riga_contabile`, che era l'unico oggetto DB mancante |

### 3.0 S0 — Il telaio

Nessun valore di dominio. È ciò senza cui la slice 1 non si scrive.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **T-1** | `apps/pagamenti/api/urls_v1.py` + montaggio | BE | `path("api/v1/pagamenti/", include("apps.pagamenti.api.urls_v1"))`, dopo `pratiche` |
| ✅ **T-2** | `apps/pagamenti/db/pagamenti_repository.py` | BE | Il repository **generico dello schema**: liste, letture, chiamate alle `fn_*`. ⛔ **Non** un file per entità |
| ✅ **T-3** | `apps/pagamenti/services/pagamenti_service.py` | BE | La facciata. ⚠️ Il traduttore degli errori si prende da `make_db_errors_translator`, **non** si riscrive |
| ✅ **T-4** | `apps/pagamenti/types.py` | BE | `TypedDict` delle righe DB (`DistintaRow`, `RigaContabileRow`, `RicevutaPosting`, `SaldoRata`, `EccedenzaRow`) |
| ✅ **T-5** | ⭐ **Le due code dei lotti** | BE | Riscrivere il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` (frase nuova, **senza `%s`**) e **togliere** i tre codici obsoleti dal ripiego (BE-10). §1.5 |
| ✅ **T-6** | `frontend/src/pagamenti/{views,components,stores,api}/` | FE | Le quattro cartelle |
| ✅ **T-7** | `DOMAIN_MENUS['pagamenti']` + rotte | FE | Da `[]` alle voci della slice 1. ⚠️ `meta` per `resolveTabLabel`/`resolveTabIcon` |
| ✅ **T-8** | Namespace i18n `pagamenti.*` in `it.json` e `en.json` | FE | ⚠️ `check_i18n_keys.py` è **un cancello CI**: una `label_key` seminata a DB senza la sua chiave **fa fallire la build** |
| ✅ **T-9** | `useReadonlyMode('pagamenti')` sulle viste | FE | Piramide permessi standard |
| ✅ **T-10** | ⚠️ **La prova del perimetro** | BE | Una lettura qualunque di `pagamenti` con e senza la GUC operatore, per **vedere** la RLS mordere prima che lo faccia in una lista (§2.6) ⚠️ **Non fatto: serve il database vero.** I test del backend girano senza DB (`SimpleTestCase`), quindi la RLS non si esercita in nessuno di essi — questa prova si fa in-app, e va fatta **prima** della prima lista a video: uno zero fail-closed somiglia in tutto a «nessun risultato» |

⭐ **Nessun endpoint di lookup da scrivere**: i quattro cataloghi sono già in
whitelist. Il FE usa `LookupSelect` con `rel="pagamenti.centri_riscossione"`.

### 3.1 S1 — La distinta e le sue righe

Il documento che raccoglie N importi arrivati insieme, **con dentro le sue
righe**: sono un drawer solo e si costruiscono insieme.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **D-1** | `GET /pagamenti/distinte/` — lista paginata | BE | 📮 **Prerequisito**: seed `ui.lista_definizione` + `lista_colonna` (§6). Filtri: stato, origine, centro, **data** (`data_contabile`, col floor standard di `defaultFiltroDataDa`) |
| ✅ **D-2** | `POST /pagamenti/distinte/` | BE | Una `SELECT fn_get_or_create_vendite_contabile(...)` con `p_origine := 'MANUALE'`, `p_codice_stato_interno := 'BOZZA'`. ⭐ Il BE **non passa** l'operatore. ⚠️ `Idempotency-Key` obbligatoria |
| ✅ **D-2-bis** | Dialogo «Apri distinta» | FE | ✅ **Q-3 chiusa su (a)**: l'apertura è **un form**, non un pulsante — canale (da cui **si deriva il centro**), centro se il canale non c'è, data contabile, importo dichiarato. ⚠️ Se il *get-or-create* **riapre** una distinta che ha già righe, la schermata **lo dice** |
| ✅ **D-3** | `GET /pagamenti/distinte/{id}/` | BE | Testata + totali derivati (somma righe, righe registrabili, scarto dal dichiarato) + **il catalogo degli stati coi suoi flag** (`is_postabile`, `richiede_abbinamento`, `is_final`) |
| ✅ **D-4** | `PATCH /pagamenti/distinte/{id}/` | BE | Solo i campi che una persona compila: `data_contabile`, `ente_incasso_id`, `importo_dichiarato`, `meta`. ⛔ **Non** lo stato |
| ✅ **D-5** | `POST /pagamenti/distinte/{id}/stato/` | BE | `{nuovo_stato: 'VALIDATA'\|'BOZZA'\|'ANNULLATA'}` — **tre valori, non quattro** (§1.5 punto 5). Un `UPDATE stato_id`, e i guard fanno il resto |
| ✅ **R-1** | `GET/POST /pagamenti/distinte/{id}/righe/` | BE | Lista e creazione righe |
| ✅ **R-2** | `PATCH /pagamenti/righe/{id}/` | BE | I **fatti**: `importo`, le tre date, `riferimento_ente`, `motivo_sospeso`. ⛔ **Non** l'abbinamento: quello è un verbo (S3, ma il campo `scadenza_id` esiste già e va previsto nel form fin da subito) |
| ✅ **R-3** | `POST /pagamenti/righe/{id}/stato/` | BE | Il percorso di D14-a. I guard rifiutano ciò che non è ammesso, **compreso** `ABBINATA` senza fattura |
| ✅ **D-6** | `DistinteListView.vue` | FE | `<ListaConfigurabile>` + `useListaConfigurabilePage` + `PageActionsBar`. Modello: `ApprovazioniPrezzoListView.vue` |
| ✅ **D-7** | `DistintaDrawer.vue` | FE | Testata + **master-detail inline** delle righe (`RigheMasterDetailTable`). ⚠️ `readonly` + `useInjectReadonly` **obbligatori** |
| ✅ **D-8** | Pannello «validazione» | FE | Dichiarato vs digitato e **il delta**, così l'errore si vede **prima** di premere. ⚠️ Post-BOZZA il drawer è `.app-readonly` ⇒ **wrapper `app-escape` obbligatorio** |
| ⭐ **R-6** | Form riga | FE | 🔀 **SUPERATO dal disegno, non fatto com'era scritto.** Il form della riga tiene i **fatti** (importo, riferimento, date); fattura e rata stanno nel verbo `abbina`, che e' un gesto proprio. ⛔ Mescolarli avrebbe fatto cambiare STATO a una riga mentre si corregge un importo. `FatturaLookup` esiste ed e' in `core/`. ⭐ **Precisata il 2026-09-15** (brief D16/D17 Q-H, decisione di Tid): R-6 protegge la **destinazione** (fattura, cliente, rata), non la conferma di una scrittura — `forzata` + `motivo_forzatura` viaggiano anche col PATCH, come secondo tempo della capienza, perché il guard della rata gira sull'`UPDATE` di `importo` come sull'`INSERT` |
| ✅ **R-7** | Azioni di riga | FE | `RowActionsMenu` + `MANAGE_ICONS.KEBAB`. ⛔ **Mai la matita** |

⚠️ **Un'avvertenza sul contenuto di questa lista, oggi.** Le uniche distinte
esistenti sono **`GENERATA`** — le crea il sync dei fondi fattura e nascono già
in `VALIDATA`. La prima cosa che la lista mostrerà a Tid **non è il lavoro di
nessuno**: è la contabilità interna dei fondi. È giusto che si veda, ma la
schermata deve **dirlo**: la colonna `origine` non è un dettaglio tecnico.

### 3.2 S2 — La registrazione ⭐ *(era S3, e adesso è la prima cosa che vale)*

Il cuore. Fa esistere il primo `vendite_movimenti` **chiesto da una persona**, e
da lì `fn_get_saldo_fattura` smette di mentire nell'interfaccia.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| 🟡 **P-0** | ⭐ **Il cancello** *(Q-5 → a)* | BE ✅ a catalogo · 📮 **da ASSEGNARE a un profilo, in-app** | `registra_distinta` a catalogo (`pericolosa = true`), `approva_rimessa` ritirata con `attivo = false`, `check_azione` nella view del verbo. 🔴 **Con l'assegnazione a un profilo nello stesso giro**: senza, il pulsante esiste e non funziona per nessuno |
| ✅ **P-1** | `GET /pagamenti/distinte/{id}/anteprima-registrazione/` | BE | La **fotografia**: quante righe sono registrabili adesso, per che totale, quante restano indietro e perché. È ciò che l'operatore vede **prima** di premere, ed è ciò che poi **dichiara** |
| ✅ **P-2** | `POST /pagamenti/distinte/{id}/registra/` | BE | **Una sola** `SELECT fn_posta_contabile(id, righe_attese, totale_atteso)`. ⚠️ I due parametri o **entrambi o nessuno**. `Idempotency-Key` obbligatoria |
| ✅ **P-3** | La ricevuta risale intatta | BE | `{movimenti_creati, righe_postate, righe_saltate, totale_postato, esito}` dentro `success_response`. ⛔ Il BE **non** trasforma `NULLA_DA_POSTARE` in un errore |
| ✅ **P-4** | Pannello «Registra» nel drawer | FE | Mostra l'anteprima, chiede conferma, invia la dichiarazione. ⚠️ `app-escape` |
| ✅ **P-5** | La frase sull'esito | FE | `POSTATA` → toast coi numeri della ricevuta; `NULLA_DA_POSTARE` → **avviso**, non errore: *«questa distinta era già registrata»* |
| ✅ **P-6** | Il rifiuto della dichiarazione | FE | Su `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` (963) **non si riprova in automatico**: si ricarica l'anteprima e si mostra la differenza. Un retry cieco su un gesto irreversibile è la cosa peggiore che si possa costruire |
| ✅ **P-7** | ⭐ **La distinta si chiude da sé** | FE | Dopo la registrazione lo stato è `CHIUSA`: il drawer va ricaricato e il pannello sparisce. ⛔ Nessun pulsante «chiudi» da nessuna parte |

### 3.3 S3 — La rata e la capienza

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **A-1** | `POST /pagamenti/righe/{id}/abbina/` | BE | ⭐ **Il verbo dell'abbinamento** (BE-6): `{fattura_id, billing_account_id, scadenza_id?, forzata?, motivo_forzatura?}`. Un `UPDATE` solo, e i guard della rata decidono |
| ✅ **A-2** | `GET /pagamenti/fatture/{id}/rate/` | BE | Le rate di una fattura **col loro saldo**, in un giro solo. 🔴 **Non è dove diceva Q-8**: `api.md` vieta le chiamate laterali fra moduli di pari livello, quindi un endpoint in `vendite` non potrebbe chiedere i saldi a `pagamenti` — e senza saldo quell'elenco non risponde alla domanda per cui esiste. Vedi la correzione in **Q-8** |
| ✅ **A-3** | ⭐ **La base dei saldi** *(§2.7)* | BE | `apps/pagamenti/services/saldi_service.py`: **l'unico** lettore delle funzioni di saldo. Forma unica `residuo · in_lavorazione · incassato`, tre livelli previsti (documento · rata · **cliente**, il terzo si accende dopo). Endpoint `GET /pagamenti/rate/{id}/saldo/` e `GET /vendite/fatture/{id}/saldo/` sono **due consumatori**, non due implementazioni |
| ✅ **A-4** | `GET /pagamenti/rate/fuori-capienza/` | BE | Sopra `vw_rate_fuori_capienza`. 📮 Prerequisito: **solo il seed** della lista — la vista c'è |
| ✅ **A-5** | La forzatura a due tempi | BE+FE | Il primo tentativo **non** porta `forzata`; sul 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` il FE mostra il messaggio del DB (che porta già i numeri) e chiede conferma; il secondo porta `forzata: true` + `motivo_forzatura`. Come il FE lo **riconosce** è **Q-1** |
| ✅ **A-6** | `RateFuoriCapienzaListView.vue` | FE | Lista. ⭐ La prima colonna è **`motivo`**: due popolazioni diverse in un elenco solo |
| ✅ **A-7** | Selettore rata nel form riga | FE | Alimentato dalla fattura scelta; si azzera quando la fattura cambia. ⚠️ La rata resta **facoltativa** anche su `ABBINATA` — la riga del fondo fattura ha fattura sì e rata no |
| ✅ **A-8** | `SaldoPanel` nel drawer fattura | FE ✅ **29/08.** ⭐ Non «il pannello della fattura»: la **base** (`useSaldi` + `SaldoPanel` in `core/`), e la fattura e' il primo consumatore. Tre livelli in testa, il cliente **dichiarato e non acceso** | ✅ **Q-6**: **residuo** in grande, **in lavorazione** in piccolo e solo quando c'è. ⛔ **Niente «incassato»** su questa schermata. ⭐ Un componente solo per tutti i livelli (§2.7). 🔴 **Il dislivello che il pannello gestiva NON ERA del database: era del backend** — vedi §10.10 |
| ✅ **A-9** | ⭐ **La coda del riconciliatore** *(salita dalla slice 4 — Q-4)* | BE+FE | `GET /pagamenti/righe/` con filtro di stato: lista **cross-distinta**. ✅ **Q-4 → (c)**: **due voci di menu** («Da abbinare» · «Sospese») che aprono **la stessa lista** con il filtro già impostato — due porte, **un solo** seed |

### 3.4 S4 — Il perimetro e i canali ✅ *(BE scritto il 2026-08-25)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **E-1** | Gestione `enti_incasso` | BE+FE ✅ **FE fatto il 28/08** | Drawer dedicato: ha JOIN (soggetto_ruolo, filiale, **conto**) quindi **non** è un pannello config generico. ⭐ **BE-8**: l'elenco dei conti mostra **solo** quelli con `uso = 'INCASSO'` dell'emittente — il DB rifiuta gli altri, ma un elenco che li propone fa sbagliare |
| **E-2** | ✅ **Il blocco è caduto** | dato | **DATO-1 chiuso il 28/08** (configurato il 24/08, rifatto al livello giusto poi): due conti `INCASSO` fittizi, uno per emittente (`IT00TESTINCASSO000000000{1,2}`), a livello **ruolo**. ✅ **La riverifica che questa riga chiedeva è FATTA** e sta in §10.8 — ogni IBAN è sul soggetto_ruolo del proprio emittente (72 → 32, 159 → 44). ⚠️ Il perimetro è vero anche se il dato è finto: uno scambio non darebbe errore, darebbe liste sbagliate — per questo si guarda, non si assume |
| ~~**E-3**~~ | ~~Coda «da abbinare»~~ | — | ⬆️ **Salita alla slice 3 (A-9)** con la chiusura di **Q-4**: la coda si riempie già con l'inserimento manuale, non aspetta l'import |
| ✅ **E-4** | Riverifica di **tutte** le liste sotto RLS | BE ✅ **FATTA il 28/08** | ⭐ E ha trovato **due buchi**: `enti_incasso` senza policy (→ team DB) e l'elenco dei conti agganciabili che **usciva dal perimetro** — misurato su due operatori veri, chiuso lo stesso giorno con un test sul DB provvisto. §10.9 |

### 3.5 S5 — Le sistemazioni

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **S-1** | `GET /pagamenti/eccedenze/` | BE | Sopra `vw_eccedenze_da_sistemare`. ⭐ **Raggruppata per cliente** — e la vista porta già `eccedenza_cliente` e `documenti_cliente` in finestra: il BE **non somma niente** |
| ✅ **S-2** | `POST /pagamenti/sistemazioni/` | BE | ⭐ Un **`INSERT`**, non un verbo: `{destinazione, importo, cliente_…, emittente_…, fattura_origine_id, fattura_destinazione_id?, motivo?}`. I CHECK del DB tengono le combinazioni |
| ✅ **S-3** | `POST /pagamenti/sistemazioni/{id}/conferma/` | BE | Una `SELECT fn_conferma_sistemazione(id, ente_incasso_id)`. ⚠️ **Il canale del rimborso si chiede QUI**: da quale conto esce il bonifico è una decisione del momento in cui si paga |
| ✅ **S-4** | `POST /pagamenti/sistemazioni/{id}/annulla/` | BE | `fn_annulla_sistemazione(id, motivo)`. ⚠️ Il motivo è **obbligatorio** se l'atto non ne aveva già uno |
| ✅ **S-5** | `EccedenzeView.vue` + drawer decisione | FE ✅ **28/08** | La vista presenta, la persona decide, l'atto diventa un fatto. ⭐ `chi_e_in_credito` in evidenza: cliente o azienda cambia completamente che cosa si sta guardando |
| ✅ **S-6** | Il dialogo della conferma | FE ✅ **28/08** | Chiede il **canale** solo su `RIMBORSO` (sulle altre due destinazioni non serve) |

📮 Con S-3 si chiude **BE-4** e si sblocca la **Fase D del cantiere fondi**,
ferma per scelta da agosto: il riporto **è** il fondo `origine = MANUALE` che
quel cantiere aspettava.

### 3.6-bis S6 — La correzione guidata ✅ *(2026-08-28)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| ✅ **S6-1** | `fn_crea_distinta_correzione` | DB | La madre: distinta nuova in bozza, righe di **segno opposto**, fattura e rata rispecchiate. ⭐ `righe_saltate` nell'esito, **stesso vocabolario di `fn_posta_contabile`** — un secondo verbo che risponde come il primo si impara una volta sola |
| ✅ **S6-2** | `pagamenti.enti_incasso` sotto RLS | DB | Nata da E-4. ⭐ Il predicato passa dal **conto** e non dall'id: quello proposto avrebbe reso la tabella non scrivibile |
| ✅ **S6-3** | `POST /distinte/{id}/correggi/` | BE | Una sola `SELECT`. Stesso cancello della registrazione (`registra_distinta`): ⛔ un gesto che rovescia denaro non può avere una porta più larga di quello che lo ha scritto |
| ✅ **S6-4** | Dialogo + legame fra i due documenti | FE | ⭐ Il legame si legge nei **due versi** — «questa corregge la X» e «questa è già stata corretta dalla Y» — ed è cliccabile: senza, due gemelli di segno opposto stanno nell'elenco senza niente che dica che uno rovescia l'altro |
| ✅ **S6-5** | La decisione **C-1** | Tid ✅ **29/08** | ⭐ **Il legame si EREDITA dalla riga che si corregge**: pagamento su una rata → la rettifica prende quella rata; pagamento sulla sola fattura (fondo, eccedenza non assegnata) → nessuna rata, perché non ce n'era una. ⛔ E le righe nascono **`DA_ABBINARE`**: la rata è già scritta, ma il tasto finale lo preme una persona — se lo premesse il sistema scriverebbe una **forzatura che nessuno ha deciso**, e l'elenco «rate fuori capienza» esiste proprio per contenere solo decisioni vere. 📮 Se il clic per riga pesasse, la risposta è un «abbina tutte» che chiede il motivo **una volta sola**, non la forzatura automatica |

### ~~3.6 S6 — La spezzatura~~ ⛔ **CADUTA (D1-ter, 2026-08-24)**

> Prevedeva `POST /pagamenti/righe/{id}/spezza/` sopra una funzione madre da
> chiedere al team DB. **Non si costruisce**, e non perché costi: **non ha un
> caso**.
>
> ⭐ **Il ragionamento, per chi arriva dopo.** L'esempio che la giustificava —
> 1.200 su una rata da 1.000 — è il caso in cui il cliente ha pagato **quella**
> rata con l'importo sbagliato: un atto solo, con un errore. Spezzarlo
> inventerebbe due allocazioni dove il cliente ne ha voluta una, e deciderebbe
> **al posto suo** dove vanno i 200. La strada giusta è registrare il fatto
> (forzata, con motivo), farlo **vedere** negli elenchi, e lasciare che qualcuno
> **decida** — che è esattamente il giro delle sistemazioni, costruito dal lotto
> 7 (**S5**).
>
> ⚠️ **Quando potrà tornare**: con l'**import del flusso bancario** (D6). Lì la
> riga arriva già fatta da fuori e i suoi fatti sono immutabili, quindi
> allocarla su più destinazioni non si può fare digitando. Sarà quel cantiere a
> dire come.

### 3.7 Cosa il cantiere BE/FE **non** fa, e perché

| Non fa | Perché |
| --- | --- |
| **Import del flusso bancario** (D6) | `enti_incasso` è ancora a **0 righe**: il conto ora c'è (DATO-1 risolto), ma il canale va prima **creato** — ed è la slice 4. Senza canale non esiste una porta da cui un file possa entrare |
| **Abbinamento automatico** (D4) | Una regola di match si tara sui casi veri. Con zero incassi si scriverebbe immaginandoli |
| **Portale clienti `GET /portale/scadenze/`** | Ha senso **dopo** S3: prima mostrerebbe il piano rate senza poter dire quali rate siano pagate |
| **Scadenzario** | ⛔ Resta fuori — ma ⭐ **il motivo per cui era chiuso è caduto** (nota nuova del 24/08 nel brief madre §3.4, nata chiudendo Q-8): il posting e il saldo per rata esistono, quindi «scaduto» e «insoluto» **non sono più colonne false**. È passato da **impossibile** a **possibile e non fatto**, ed è **un cantiere suo**: qui nasce solo il **lookup** delle rate di *una* fattura, non la rotta scadenze paginata. ⚠️ Quando si aprirà: i numeri vengono dalla **base unica dei saldi** (§2.7) e mai da una query propria — uno scadenzario è la porta dei solleciti — e si guarda il **residuo**, non l'incassato: una rata coperta da un giro interno è regolata anche se in banca non è entrato niente |
| **Blocco `2.4 DatiPagamento`** | È il passo **2** dell'ordine di Tid, e appartiene al cantiere SDI |
| **La capienza a livello di fattura** | 🔵 Il lotto 5 l'ha messa **solo sulla rata**, di proposito (al livello fattura passerebbe il sync dei fondi, che non ha nessuno che possa «confermare»). Estenderla è **una decisione di dominio**, non una rifinitura di interfaccia |

---

## 4. Il contratto API proposto

Grammatica di `api.md`: il metodo dice l'operazione, il path la risorsa, il
verbo compare **solo** per le azioni di dominio e come **ultimo** segmento.

| Slice | Metodo e path | Che cos'è | Idem-Key |
| --- | --- | --- | :---: |
| S1 | `GET /api/v1/pagamenti/distinte/` | lista paginata | — |
| S1 | `POST /api/v1/pagamenti/distinte/` | apre una distinta manuale | ✅ |
| S1 | `GET /api/v1/pagamenti/distinte/{id}/` | dettaglio + totali + catalogo stati | — |
| S1 | `PATCH /api/v1/pagamenti/distinte/{id}/` | campi compilabili | — |
| S1 | `POST /api/v1/pagamenti/distinte/{id}/stato/` | VALIDATA · BOZZA · ANNULLATA | ✅ |
| S1 | `GET/POST /api/v1/pagamenti/distinte/{id}/righe/` | righe della distinta | ✅ su POST |
| S1 | `PATCH /api/v1/pagamenti/righe/{id}/` | i **fatti** della riga | — |
| S1 | `POST /api/v1/pagamenti/righe/{id}/stato/` | il percorso di D14-a | ✅ |
| S2 | `GET /api/v1/pagamenti/distinte/{id}/anteprima-registrazione/` | la fotografia | — |
| S2 | `POST /api/v1/pagamenti/distinte/{id}/registra/` | ⭐ la madre | ✅ |
| S3 | `POST /api/v1/pagamenti/righe/{id}/abbina/` | fattura + rata (+ forzatura) | ✅ |
| S3 | `GET /api/v1/pagamenti/rate/{id}/saldo/` | la base dei saldi, livello **rata** (tre numeri) | — |
| S3 | `GET /api/v1/pagamenti/fatture/{id}/saldo/` | livello **documento** — ⚠️ `skip_area_check`: lo consuma il drawer fattura | — |
| S3 | `GET /api/v1/pagamenti/fatture/{id}/rate/` | le rate col loro saldo, un giro solo | — |
| S3 | `GET /api/v1/pagamenti/rate/fuori-capienza/` | l'elenco che rende onesta la forzatura | — |
| S3 | `GET /api/v1/pagamenti/righe/` | la coda cross-distinta, parametro `coda` — **due voci di menu, un endpoint** (Q-4) | — |
| S4 | `GET/POST/PATCH /api/v1/pagamenti/enti-incasso/…` | configurazione canali | ✅ su write |
| S5 | `GET /api/v1/pagamenti/eccedenze/` | presenta | — |
| S5 | `POST /api/v1/pagamenti/sistemazioni/` · `…/{id}/conferma/` · `…/{id}/annulla/` | registra · esegue · scarta | ✅ su write |

**Note vincolanti:**

- ⭐ **la risorsa si chiama `distinte`, non `contabili`.** Il piano DB scriveva
  `POST /pagamenti/contabili/<id>/registra/`; sul filo si usa la parola che
  l'operatore legge sulla schermata, e la guida di dominio la chiama *distinta*.
  ⚠️ Se Tid preferisce il nome tecnico, si cambia **qui e in un posto solo**;
- ⛔ **niente `POST /distinte/crea/`, niente `PATCH /distinte/5/aggiorna/`**: il
  verbo è nel metodo HTTP;
- ✅ `registra`, `abbina`, `conferma`, `annulla`, `stato` sono **azioni di
  dominio** e stanno come ultimo segmento. ⛔ **`spezza` non c'è**: cade con
  D1-ter (§3.6);
- ⚠️ **niente `?format=`** nei query param: collide con DRF e produce un 404
  silenzioso. Se servirà un export, il parametro si chiama `formato`;
- tutte le view estendono `DomainAPIView` con `area_funzionale = "pagamenti"`.
  ⛔ **Nessuna classe V1**: il pattern dual-class è eliminato dal marzo 2026;
- ogni metodo pubblico porta `@extend_schema`, o drf-spectacular fa rumore in CI.

---

## 5. Il frontend — schermate e building block

### 5.1 Le schermate

| Schermata | Slice | Forma |
| --- | --- | --- |
| **Distinte contabili** | S1 | `<ListaConfigurabile>` — paginatore in alto, filtri stato/origine/centro/data, click riga → drawer |
| **DistintaDrawer** | S1-S2 | Testata + master-detail righe + pannello validazione + pannello registrazione |
| **Rate fuori capienza** | S3 | Lista, **prima colonna `motivo`**. Senza, la forzatura nasconde invece di registrare |
| **Canali di incasso** | S4 | Drawer di configurazione. ✅ Il prerequisito di dato è chiuso il **28/08** (§10.8): da adesso un canale è **creabile** — prima non lo era, perché il conto è obbligatorio su tutti i tipi e a livello ruolo non ce n'era. ⭐ Il drawer mostra la **utility del conto** accanto all'IBAN (BE-11), e `null` si legge «nessuna utility», non come un campo vuoto |
| **Da abbinare** · **Sospese** | S3 | ⭐ **La stessa lista, due voci di menu** con il filtro di stato già impostato (Q-4 → c) |
| **Eccedenze da sistemare** | S5 | Lista raggruppata **per cliente** + drawer decisione + dialogo conferma |

### 5.2 ✅ I 17 building block che si riusano

`ListaConfigurabile` · `useListaConfigurabilePage` · `useListaAzioni` ·
`PageActionsBar` · `RowActionsMenu` · `AppDrawer` · `FormFooter` ·
`DrawerActionsBar` · `AppDialog` · `RigheMasterDetailTable` · `LookupSelect` ·
`BillingAccountLookup` · `useReadonlyMode` · `useConfirmAction` ·
`useDrawerContentReady` · `createCrudStore` · `defaultFiltroDataDa`.

⭐ **E cinque nati qui** (28/08): `useForzaturaConfermata` · `FatturaLookup` ·
`useLetturaTreStati` in `core/`, `etichette.js` · `useCanaliIncasso` nel dominio.
⚠️ Tutti **fabbriche**, mai oggetti già costruiti: un oggetto condiviso
legherebbe ogni consumatore al `t` del primo componente montato, e al cambio
lingua il secondo resterebbe indietro **in silenzio**.

### 5.3 ✅ I quattro candidati all'estrazione — tre estratti, uno ancora no

| BB | Dove vivrebbe | Perché |
| --- | --- | --- |
| ✅ `FatturaLookup.vue` | `core/components/` | ✅ **ESTRATTO il 28/08** alla seconda occorrenza: abbinamento di una riga e sistemazione di un'eccedenza fanno la stessa domanda, da due domini diversi. ⚠️ Vive in `core/` e **non** in `vendite/`: chi lo usa sta fuori da vendite |
| 🟡 `ScadenzaSelect.vue` | `core/components/` | Rate di una fattura **col saldo accanto**. ⚠️ **Ancora una occorrenza sola** (l'abbinamento): la regola del 2 dice di aspettare la seconda, e la seconda non c'è |
| `SaldoPanel.vue` + `useSaldi.js` | `core/components/` · `core/composables/` | ⭐ **Non è più un candidato: è un vincolo** (§2.7, decisione di Tid). Un componente e un composable **soli**, forma unica `residuo · in_lavorazione · incassato`, e ogni schermata sceglie **quali** numeri accendere. Nasce con **tre livelli in testa** — documento, rata, **cliente** |
| ✅ `useForzaturaConfermata.js` | `core/composables/` | ✅ **ESTRATTO il 28/08.** Astrae **un comportamento** (`azioneUi === 'confirm_and_retry'`) e non un elenco di codici — ed è il **primo consumatore di `azioneUi` in tutto il prodotto**: fino a ieri quel campo era emesso, trasportato e letto da nessuno |
| ✅ `useLetturaTreStati.js` | `core/composables/` | 🆕 **Non era in elenco, ed è quello che serviva di più.** «C'è · è vuoto · non l'ho letto»: il terzetto era riscritto a mano in **quattro** punti e in **tre** me l'ero dimenticato alla prima stesura. Un difetto che si ripete tre volte su quattro non è distrazione: è una cosa che il codice deve dare per costruzione |

⚠️ **Sulla regola del 2**: nessuno dei quattro si estrae *prima* di averlo visto
funzionare una volta. Sono dichiarati qui perché il piano li prevede.

### 5.4 ⚠️ Le trappole già pagate, da non ripagare

| Trappola | Regola |
| --- | --- |
| `useApiHandler.execute()` su una action di store | ⛔ Solo per response **axios**. Le action di store sono già scartate: chiamata diretta |
| `if (result)` dopo il save di un drawer | ⛔ `if (result !== null)`: uno `0` legittimo verrebbe letto come fallimento |
| Pannello-azione dentro un drawer post-BOZZA | ⛔ Il contenuto è `.app-readonly` ⇒ **sempre** wrapper `app-escape` |
| Store Pinia con dati utente | ⛔ `userScoped: true`, o al logout i dati restano |
| Deep-link e freshness | ⛔ In `onActivated` **idempotente**, mai solo in `setup`/`onMounted` |
| `watch(..., { immediate: true })` | ⛔ Le variabili che tocca devono **precederlo**: la TDZ in `setup` è silenziosa |
| Download di un file | ⛔ `useApiHandler` rompe i blob: bypass + toast manuali |
| `@` in una stringa i18n | ⛔ Va escapato: `{'@'}` |
| L'elenco degli stati cablato nel FE | ⛔ Il catalogo porta `is_postabile`, `is_final`, `richiede_abbinamento`: si leggono, non si riscrivono |

---

## 6. ✅ I prerequisiti a carico del team DB: da nove a tre, e **poi a zero**

> ✅ **ALLINEATO DAL TEAM DB IL 2026-08-27.** I tre prerequisiti che restavano
> sono **consegnati e applicati**: i quattro seed di lista (53 colonne, 4 preset,
> **53 chiavi i18n** già nei locales), le due righe dell'azione di processo, e
> `fn_get_saldo_fattura` allargata a tre numeri. ⭐ **Il database non deve più
> niente a questo cantiere**, tranne la madre della correzione, che resta
> differita per scelta.
>
> ✅ **E le tre cose passate al backend sono FATTE** il 2026-08-28 (§6-bis).
> ✅ **DATO-1 è chiuso** lo stesso giorno, verificato sul database: §10.8 non è
> più un blocco. ⭐ **Il cantiere non ha più prerequisiti di nessun tipo — né
> DB, né dato, né backend: resta il frontend.**


⛔ **Non li eseguo io** (le azioni DB si passano al team): si scrivono in un
brief e si aspetta. Ecco il consuntivo della revisione.

| | Prerequisito del 22/08 | Oggi |
| --- | --- | --- |
| **DB-1** | vista `vw_vendite_contabili_lista` | 🔵 **Probabilmente non serve**: le liste alimentate da un endpoint di dominio si seminano con `vista_sql = NULL` (è la forma delle 6 liste dell'8° lotto e delle 3 del drawer lotto). I display field si fanno in JOIN **nel repository**. ⚠️ Costo: con `vista_sql` nullo il guard DB sui `campo_sorgente` **salta**, e l'unico presidio resta quello Python |
| **DB-2** | seed lista **distinte** | ✅ **CONSEGNATO** (applicato 27/08): `pagamenti.distinte`, 14 colonne + preset |
| **DB-11** | 🆕 due righe in `config/azioni_processo.csv`: `approva_rimessa` → `attivo = false`, e `registra_distinta` (area 7, `pericolosa = true`) | ✅ **CONSEGNATO** (25/08). ⚠️ Il ritiro ha fatto **fallire il primo migrate**: un guard generico rifiuta di spegnere una riga con figlie, e `profili_accesso_azioni` ne aveva quattro (tutte a permesso negato). Tolte a mano, il secondo migrate è passato. 📮 **Ma il cancello resta chiuso**: l'azione va ancora **assegnata a un profilo**, o registra solo il super admin |
| **DB-3** | seed lista **righe da abbinare** | ✅ **CONSEGNATO** (27/08): `pagamenti.righe`, 15 colonne. Ed è **uno solo**: con Q-4 → (c) le due code condividono la definizione e si separano col filtro |
| **DB-4** | vista + seed **rate sovra-incassate** | ⭐ **La vista c'è già** (`vw_rate_fuori_capienza`, lotto 5), col nome giusto e più contenuto di quanto chiedessi. ✅ **E il seed è CONSEGNATO** (27/08): `pagamenti.rate_fuori_capienza`, 13 colonne, prima colonna `motivo` |
| ~~**DB-5**~~ | `fn_spezza_riga_contabile` | ⛔ **CADUTO (D1-ter, 2026-08-24)**: il gesto che lo richiedeva non esiste più. ⭐ Era l'unico oggetto DB mancante — **adesso il database non deve più niente a questo cantiere, tranne i seed** |
| **DB-6** | lookup rate di una fattura | ✅ **ANNULLATO**: `list_fattura_scadenze` esiste, e i numeri li dà `fn_get_saldo_rata` |
| **DB-7** | `ui_action` per i rifiuti confermabili | ✅ **ANNULLATO**: le `ui_action` sono un file **Python scritto a mano** (`error_ui_overrides.py`) |
| **DB-8** | vista + seed **eccedenze** | ⭐ **La vista c'è già** (`vw_eccedenze_da_sistemare`, lotto 7), e porta pure il raggruppamento per cliente. ✅ **E il seed è CONSEGNATO** (27/08): `pagamenti.eccedenze`, 11 colonne, ordinate per cliente |
| **DB-9** | conferma che le liste reggano sotto RLS | ✅ **ANNULLATO come richiesta**: il lotto 6 ha portato `test-rls-pagamenti-perimetro.sql` (14 asserzioni). ⚠️ Diventa **lavoro BE**: la prova dentro/fuori perimetro su ogni lista (§2.6, T-10, E-4) |
| **DB-10** | 🆕 | ✅ **CONSEGNATO** (applicato 25/08) — era: 📮 **NUOVO e CONFERMATO** (Q-10 → a, Tid 24/08): allargare `fn_get_saldo_fattura` a `residuo · in_lavorazione · incassato`, la stessa forma di `fn_get_saldo_rata`. ⭐ Non è una rifinitura: senza, la **base unica dei saldi** (§2.7) nasce storta al livello che dovrà reggere il **saldo cliente** |
| ~~**DATO-1**~~ | ✅ **RISOLTO il 2026-08-28** (⚠️ configurato il 24/08, ma **al livello sbagliato**: la misura del 25/08 lo trovò a livello *soggetto*, e §10.8 restò aperta fino al rifacimento a livello **ruolo**) | Non era una richiesta al DB ma **configurazione**, e **non serviva nessuna colonna nuova**: il conto di incasso è una **riga** in `anagrafiche.soggetti_ruoli_conti_bancari` con `uso = 'INCASSO'`, non un parametro dell'emittente. ⛔ Metterlo fra i parametri sarebbe stata una **seconda sede** fuori dal vincolo «un conto `INCASSO` → un solo soggetto», che è ciò che regge il perimetro. Fatto in-app da Tid con due IBAN di test, uno per emittente |

⚠️ **Come sono arrivati davvero.** La bozza non è mai partita da qui: il team DB
ha generato le 53 righe **dal contratto del backend** — `campo_sorgente` dai
`SELECT` del repository, e il **`codice`** di ogni colonna ordinabile uguale alla
chiave della whitelist di ordinamento (`DISTINTE_SORT_COLUMNS` e sorelle), così
che un ordinamento dichiarato a catalogo non diventi un 400. ⭐ Tre scelte sono
**dichiarate e non dedotte**: `sensibile = f` ovunque (è un cancello, non
un'etichetta), `multi_emittente = f` (default: una lista nuova nasce **non
certificata**), `vista_sql = NULL` — col costo, detto, che il guard DB sui
`campo_sorgente` non gira e l'unico presidio resta quello Python.

⭐ **E i quattro seed si chiedono in un colpo solo, già scritti.** Esiste
`scripts/gen_seed_lista.py`, che genera le righe dei quattro CSV a partire dal
componente `.vue` e dalla vista: **le genero io in bozza** (i campi curati —
priorità, gruppo, larghezza, sensibile — li decido a mano) e il team DB le fa
confluire nei CSV di seed. Un round-trip invece di quattro, e nessuno scrive
269 colonne a mano una seconda volta.

---

## 6-bis. ✅ Che cosa era passato al backend — **fatto il 2026-08-28**

> Elenco scritto dal team DB il 27/08 consegnando il lotto 9; ✅ **tutti e
> quattro chiusi il 28/08**, più un presidio che l'elenco non chiedeva.

| | Cosa | Esito |
| --- | --- | --- |
| **BE-a** | Rigenerare `error_policies_generated.py`: due codici nuovi a catalogo | ✅ **fatto.** ⚠️ Non si rigenera al buio: la divergenza è stata **guardata prima** ed era **esattamente un codice** (`E_ENTE_INCASSO_NON_TROVATO`, 798 → 799 voci) — nessun lavoro di altri a bordo. ⭐ **E il secondo tempo che l'elenco non nomina**: un codice vivo vuole anche il suo **ripiego senza segnaposti** in `error_messages_fallback.py`, o `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` è rosso. `E_PAGAMENTI_VALIDATION` ce l'aveva già dal 25/08, l'altro no |
| **BE-b** | `E_ENTE_NON_TROVATO = "E_ENTE_INCASSO_NON_TROVATO"` — **una riga** | ✅ **fatto**, più il commento riscritto (diceva «a catalogo manca», che adesso è falso: *una regola spiegata con un fatto scaduto insegna una cosa falsa a chi si fida*). 🔴 **E il test che lo copriva non copriva niente**: `test_canale_inesistente_404` confrontava `exception.code` con la costante che il codice stesso legge — una tautologia, **verde anche mentre il ripiego rispondeva 400**. Il nome prometteva un 404 che nessuna asserzione guardava. Ora l'asserzione è sullo **stato risolto** |
| **BE-c** | Dichiarare `lista_codice` sulle **quattro** view di lista | ✅ **fatto**: `pagamenti.distinte` · `pagamenti.righe` · `pagamenti.rate_fuori_capienza` · `pagamenti.eccedenze` |
| **BE-11** | ⭐ **Esporre la utility del conto, che c'è già** | ✅ **fatto** nei due punti (`_ENTE_INCASSO_SELECT` e `list_conti_incasso`). ⚠️ **Ma non passando dalla vista suggerita**: `vw_istanze_utilities_dettaglio` porta `utility_descrizione` e con essa **sei join**, due su viste di indirizzo che PostgreSQL non pota. Misurato con EXPLAIN sull'elenco dei conti: **928.86 contro 6.10** per decodificare una parola. Si usa la catena diretta `istanza → pdp → utility`, che è anche la forma già in uso in `BillingAccountRepository.search_lookup`. ⚠️ E la descrizione è **NULL in due casi legittimi e diversi** — conto senza istanza (è il conto *generico* del ruolo) o istanza senza PDP: a video NULL è «nessuna utility», non un buco |
| 🆕 **BE-d** | ⭐ **Il presidio sui `campo_sorgente`, che nessuno aveva chiesto** | ✅ **scritto.** Con `vista_sql = NULL` il guard DB sulle colonne **non gira**, e il team DB l'ha dichiarato: *«l'unico presidio resta quello del backend»* — cioè una responsabilità **ricevuta**, non un extra. `apps/pagamenti/tests/db/test_lista_campo_sorgente_guardrail.py` verificava che tutti e **53** i `campo_sorgente` esistessero fra le colonne che le liste proiettano. ✅ Verde (53/53), e provato rimettendo il difetto. ⭐ **Assorbito il 2026-09-01** in `apps/core/tests/db/test_lista_proiezione_campo_sorgente.py`, che fa la stessa cosa su tutte e **39** le liste senza vista — il file di dominio è stato tolto: due copie della stessa prova divergono, e la prima a divergere sarebbe stata quella con meno liste dentro |

⭐ **E le due liste di colonne ordinabili sono state ricontrollate da questo
lato**, non prese per buone: `codice` a catalogo contro le chiavi di
`DISTINTE_SORT_COLUMNS` e sorelle — **combaciano su tutte e quattro**, in
entrambi i versi. È il controllo che vale la pena rifare perché il modo in cui
fallisce non è educato: un ordinamento dichiarato e non riconosciuto è un
**400** su un gesto normale.

⚠️ **Le colonne le dichiara il CURSORE, non le righe.** Il presidio legge
`cursor.description`, quindi vale anche su una lista **oggi vuota** — che è il
caso in cui serve di più: una lista senza righe non può smentire niente, e un
confronto fatto sui dati sarebbe verde per sottrazione.

📌 **E anche una prova è un programma.** La prima stesura di quella misura
spiava `rows_to_list` e rispondeva «0 colonne esposte» su tutte e quattro: un
rosso che non veniva dal codice ma dalla misura — le liste paginate passano da
`fetch_paged_with_total`.

⚠️ **E il nome del codice di validazione è `E_PAGAMENTI_VALIDATION`, non
`_VALIDAZIONE`**: il catalogo ha due convenzioni vive e si è scelta la
maggioranza (17 contro 13). §10.7 qui sotto dice ancora l'altro — è quella riga
a essere vecchia, non il codice.

⭐ **Le 53 chiavi i18n sono già nei locales**, in una radice `pagamenti` nuova:
il cancello `check_i18n_keys.py` legge il CSV delle colonne e pretende le
traduzioni in **entrambe** le lingue, quindi le due metà non potevano atterrare
separate.

## 7. ✅ Domande aperte — **nessuna**

> ⭐ **Chiuse tutte il 2026-08-24**, in una sessione sola: le nove del 22/08 più
> **Q-10**, nata e chiusa nella stessa giornata. Questa sezione da qui in avanti
> è **un registro di decisioni**, non un elenco di cose da decidere.
>
> 🔴 **Due hanno cambiato il piano, non solo risposto a una domanda**: **Q-2**
> (cade il gesto della spezzatura, e con esso una slice intera) e **Q-6**, che ha
> prodotto il vincolo **§2.7** — i saldi hanno una sede sola, col saldo cliente
> già in testa.
>
> | | Esito |
> | --- | --- |
> | **Q-1** | ✅ **chiusa da Tid**: strada (a), nasce `confirm_and_retry` |
> | **Q-2** | ⛔ **chiusa da Tid**: il gesto non esiste — **D1-ter**, e con esso cade la slice 6 |
> | **Q-3** | ✅ **chiusa da Tid**: apertura con **un form**, non un pulsante |
> | **Q-4** | ✅ **chiusa da Tid**: **due voci di menu, una lista sola** — e la coda **sale alla slice 3** |
> | **Q-5** | ✅ **chiusa da Tid**: nasce **`registra_distinta`**, `approva_rimessa` si ritira |
> | **Q-6** | ✅ **chiusa da Tid**, e vale più di una schermata: nasce il vincolo **§2.7** — i saldi hanno **una sede sola**, con il **saldo cliente** già in testa |
> | **Q-9** | ✅ **chiusa da sé**: le viste erano già lì, i seed si chiedono insieme |
> | **Q-8** | 🔽 **crollata di prezzo** senza cambiare risposta: nessun prerequisito DB |
> | **Q-7** | ✅ **chiusa da Tid**: correzione **guidata** (righe precompilate di segno opposto), mai «storno» |
> | **Q-8** | ✅ **chiusa da Tid**: lookup dedicato in `vendite`, nessun permesso allargato |
> | **Q-10** | ✅ **nata e chiusa oggi**: `fn_get_saldo_fattura` si allarga a tre numeri |
>
> ✅ **E il solo blocco rimasto è caduto lo stesso giorno**: **DATO-1**, il conto
> di incasso dei due emittenti, configurato in-app. ⛔ **Non resta niente da
> decidere né da aspettare**: da qui in avanti è solo lavoro.

### ~~Q-1 · Come viaggia sul filo HTTP un rifiuto **confermabile**?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: nasce l'`ui_action` **`confirm_and_retry`**, dichiarata in
> `error_ui_overrides.py` su `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`. Il frontend
> ramifica su `azioneUi` e resta **cieco ai codici**. ⚠️ È una voce nuova in un
> vocabolario trasversale a tutto il prodotto: va scritta col suo paragrafo di
> motivazione, come le altre di quel file. ⭐ E `useForzaturaConfermata.js`
> (§5.3) può quindi nascere davvero building block, perché astrae **un
> comportamento** e non un elenco di codici.

Il DB rifiuta il primo tentativo con `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` (409) e
un messaggio che porta già i numeri (*«Sulla rata %s restano %s da regolare: un
importo di %s non ci rientra»*), e accetta il secondo con `forzata = true`. Sul
filo, quel rifiuto è **un 409 come tutti gli altri**.

| | Strada | Costo | Rischio |
| --- | --- | --- | --- |
| **(a)** ⭐ | Una `ui_action` nuova, `confirm_and_retry`, su quel codice in `error_ui_overrides.py` | **una riga di Python** + un ramo su `azioneUi` in `useApiHandler` | nessuno: il FE riconosce la **classe di comportamento**, non i singoli codici |
| **(b)** | Il FE tiene l'elenco dei codici confermabili | zero, oggi | 🔴 al terzo codice qualcuno se ne dimentica, e l'operatore resta **bloccato** su un caso che il dominio dichiara ammesso |

**La mia proposta: (a).** ⭐ E la ragione per cui la ripropongo è che **è
crollata di prezzo**: il 22/08 credevo servisse un giro col team DB, e invece
`error_ui_overrides.py` è nostro, è scritto a mano e ogni voce porta già il suo
paragrafo di motivazione. `useApiHandler` espone già `azioneUi`.

**Perché non decido io**: introduce una voce nel vocabolario delle `ui_action`,
che è trasversale a tutto il prodotto.

---

### ~~Q-2 · Spezzare una riga: si chiede al team DB, o si rinvia?~~ ⛔ **CHIUSA da Tid (2026-08-24): il gesto non esiste**

> ⭐ **Decisione**: *«il pagamento di una rata non si spezza»*. Non è un rinvio ed
> è più di una risposta: è una **decisione di dominio**, registrata nel brief
> madre come **D1-ter**.

**L'equivoco che la domanda conteneva.** Presentavo 1.200 su una rata da 1.000
come il caso da risolvere spezzando, citando D1-bis. Ma se **la rata è
identificata**, l'atto del cliente è **uno solo con un importo sbagliato**:
spezzarlo inventerebbe due allocazioni dove il cliente ne ha voluta una, e
soprattutto deciderebbe **al posto suo** che i 200 di troppo vanno altrove. Non è
data entry, è una decisione — e ha un titolare.

**Perché D1-bis diceva il contrario, e perché non era sbagliata.** La sua ragione
era *«l'eccedenza resta denaro identificato invece di sparire dentro una rata che
non la giustifica»*, e il **9 agosto era vera**: le sistemazioni non esistevano.
⭐ Il **lotto 7 del 22 agosto** le ha costruite — elenco, registro, tre
destinazioni — quindi **l'eccedenza non sparisce più**. La preferenza cade perché
il problema che la giustificava è stato risolto **altrove**.

**Che cosa ne discende qui:**

| | Conseguenza |
| --- | --- |
| ⛔ | niente `POST /righe/{id}/spezza/`, niente gesto nel drawer |
| ⛔ | **la slice 6 sparisce** dal piano (§3.6) |
| ⛔ | `fn_spezza_riga_contabile` esce dalle richieste al team DB — ⭐ ed era **l'unico oggetto DB mancante** |
| ✅ | la strada ordinaria è **forzatura → elenco → sistemazione** (S3 + S5), che è già tutta costruita |
| ⚠️ | **D1 regge intatta**: un incasso che copre tre rate resta tre righe. Cambia solo *quando* si scrivono — subito, digitandole |

⚠️ **Quando potrà tornare**: solo con l'**import del flusso bancario** (D6), dove
la riga arriva già fatta da fuori e non si può digitare. Sarà quel cantiere a
dire come, e non si anticipa adesso.

---

### ~~Q-3 · La distinta manuale nasce da un gesto, o dalla prima riga?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: la distinta si apre con **un gesto esplicito**, e —
> testualmente — *«l'operatore deve poter caricare delle informazioni per aprire
> la specifica contabile»*. ⛔ Quindi **non** un pulsante che crea al volo con
> dei default: un **form di apertura**.

**Che cosa chiede il form** (i primi due sono obbligatori nel database):

| Campo | Nota |
| --- | --- |
| **canale** (`ente_incasso_id`) | ⭐ **si sceglie questo per primo, e il centro si deriva da lui**: l'ente porta il suo `centro_riscossione_id`, e un guard rifiuta la coppia incoerente. Chiederli entrambi a mano significa costruire un errore che si può evitare |
| **centro di riscossione** | obbligatorio. Si chiede **direttamente** solo quando un canale non c'è (la cassa). ⚠️ **Oggi `enti_incasso` è ancora a zero righe**, quindi il form deve funzionare col solo centro — ma dal 28/08 è a zero perché nessuno ne ha ancora creato uno, **non perché non si possa** (DATO-1 è chiuso). ⇒ Il form regge **entrambi** i casi, e il secondo arriverà appena si configura il primo canale |
| **data contabile** | obbligatoria |
| **importo dichiarato** | facoltativo. È la **quadratura** di D13: quanto dice il totale in cima al foglio arrivato |
| note (`meta`) | facoltativo |

⚠️ **E una cosa che il form deve saper dire.** La funzione è un *get **or create***
e la chiave di riuso comprende **chi lavora, il giorno e il canale**: se
l'operatore riapre con gli stessi dati, il database **non** ne crea una seconda —
gli **ridà la sua**. ⭐ Ed è il comportamento giusto (D12-a, niente contesa),
ma **va detto**: se la distinta ritrovata ha già delle righe, la schermata
annuncia *«questa distinta esisteva già e contiene N righe»*. ⛔ Aprire in
silenzio dentro il lavoro di stamattina è il modo in cui qualcuno registra due
volte credendo di cominciare.

ℹ️ Il database risponde **solo l'id**, quindi «creata» e «riaperta» non si
distinguono dalla chiamata: la differenza si legge sul dettaglio (**ha righe o
no**). Il caso indistinguibile — una distinta esistente e **vuota** — è innocuo.

⭐ **Il rischio classico di (a) non c'è**: le distinte vuote abbandonate non si
accumulano, perché la riapertura ritrova la stessa. E se una va tolta, l'annullo
in bozza c'è già.

---

### ~~Q-4 · «Da abbinare» e «sospese»: due code o una lista con un filtro?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (c)**

> ⭐ **Decisione**: **due voci di menu che aprono la stessa lista con un filtro
> diverso già impostato**. Due porte, **un solo** pezzo di configurazione a
> database.

Il dominio (D12-f) chiama le due popolazioni *«due code per due persone
diverse»*: `DA_ABBINARE` è **lavoro non ancora fatto** (i soldi ci sono, nessuno
ha detto di chi sono), `SOSPESA` è **lavoro fatto che ha trovato un ostacolo**.

**Perché non una lista sola con il filtro in toolbar**: un filtro non separa due
mestieri. Li mette nello stesso posto e chiede a ciascuno di ricordarsi di
impostarlo — e chi si dimentica lavora sulla coda di un altro.

**Perché non due liste**: costerebbero **due seed** per due schermate identiche.
Il filtro vive nella toolbar della schermata, non nella definizione a catalogo,
quindi due rotte possono aprire la stessa lista già filtrata. ⭐ (c) dà a (a) ciò
che serve — due porte, due nomi in menu, due code che non si mescolano — senza
pagarlo due volte.

⇒ Un endpoint solo, `GET /pagamenti/righe/` con il filtro di stato, e **un solo**
prerequisito di seed (DB-3).

---

⚠️ **E con la decisione è stata corretta una misura sbagliata del 22/08.**
Scrivevo che quella coda *«oggi non esiste: si popola solo con l'import»*. Era
vero **solo finché nessuno poteva digitare righe**: appena c'è l'inserimento
manuale (slice 1), l'operatore che carica i soldi della giornata può lasciare una
riga senza destinazione, e **la coda si riempie subito**. Con l'import cambia il
**volume**, non l'esistenza.

✅ **Quindi la coda sale dalla slice 4 alla slice 3** (approvato da Tid).

---

### ~~Q-5 · `approva_rimessa` (azione id 5): si ritira, si riusa, o resta?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: si **ritira** `approva_rimessa` e nasce **`registra_distinta`**,
> il cancello sull'unico gesto irreversibile del cantiere.

**Perché quella riga era orfana.** `approva_rimessa` (id 5, area 7) era nata
quando il piano prevedeva la forzatura *gated* da un permesso. **D14-e l'ha tolto**
— la forzatura è a un tempo solo, senza permessi — e da allora l'azione è a
catalogo e non la usa nessuno. ⛔ *Un catalogo pieno di righe irraggiungibili
insegna cose false*: è la lezione appena pagata ritirando `STORNATA`.

**Perché la registrazione merita il cancello.** È l'unico gesto che **non si può
disfare**: crea movimenti veri e chiude la distinta. Chi carica i soldi non è
necessariamente chi può trasformarli in scritture contabili.

**Come si scrive:**

| | Cosa | Dove |
| --- | --- | --- |
| 1 | `approva_rimessa` → `attivo = false` | ⚠️ `config.azioni_processo` **non ha `obsoleto_dal`**: si ritira col flag `attivo` |
| 2 | nasce `registra_distinta`, area 7, **`pericolosa = true`** | stessa marcatura di `genera_fatture_lotti` e `reset_lotto_draft` |
| 3 | il controllo nella view | `PermissionResolver.check_azione(user, "registra_distinta")`, come fa il gate del pricing |
| 4 | 🔴 **l'assegnazione a un profilo** | ⚠️ **Passo di configurazione, da fare insieme e non dopo**: appena il controllo esiste, **nessuno può registrare** finché il permesso non è concesso. Altrimenti il giorno del collaudo il pulsante c'è e non funziona per nessuno |

⚠️ **Il nome non si riusa**: `approva_rimessa` direbbe un'altra cosa (approvare ≠
registrare), e nel progetto i codici di permesso **non si rinominano**.

📮 I passi 1 e 2 sono **due righe di seed** in `config/azioni_processo.csv`: vanno
nello stesso brief al team DB dei seed lista.

---

### ~~Q-6 · Il saldo del documento: quanti numeri mostra, e dove?~~ ✅ **CHIUSA da Tid (2026-08-24)**

> ⭐ **Decisione, in tre parti:**
> 1. **sì al drawer fattura** — è lì che qualcuno si chiede se è stata pagata;
> 2. **l'«incassato» NON serve a chi guarda la fattura**: quel numero risponde a
>    una domanda di tesoreria, non a *«questa fattura è a posto?»*;
> 3. 🔴 **e il drawer fattura non è l'unico posto**: dovrà nascere una funzione
>    che dia anche il **saldo del cliente**, quindi *«qualsiasi cosa faremo deve
>    essere una base unica per i saldi»*.

**Che cosa mostra il pannello della fattura** — due numeri, non tre:

| | Numero | Nota |
| --- | --- | --- |
| **residuo** | in grande | è la domanda che uno si fa |
| **in lavorazione** | in piccolo, **solo quando c'è** | soldi già digitati su una distinta e **non ancora registrati**: non abbassano il residuo, e vederli spiega perché |
| ~~incassato~~ | ⛔ **fuori** | resta nel perimetro dei saldi (§2.7), ma non in questa schermata |

⭐ **La terza parte della decisione è la più importante e non è di questa
schermata**: diventa il **vincolo §2.7**, e riscrive Q-10.

---

### ~~Q-7 · La correzione: gesto guidato o mano libera?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: **gesto guidato**. Un'azione «Correggi» sulla distinta
> registrata apre una distinta nuova con le righe **di segno opposto già
> precompilate**. ⛔ Non ricopiatura a mano: su venti righe è lì che nasce il
> secondo errore.
>
> 📮 **La sua funzione madre va al team DB come richiesta DIFFERITA** — firma
> proposta, ma segnata *«da scrivere quando parte la slice»*. ⚠️ Una madre pronta
> che nessuno chiama è già successa col posting, e non conviene ripeterlo.

D3-d: la correzione **non è un documento speciale**, è una contabile con importi
di segno opposto. Il gesto, nell'interfaccia, non c'è.

- **(a)** ⭐ un'azione «Correggi» su una distinta registrata, che apre una
  distinta nuova con le righe **di segno opposto già precompilate**;
- **(b)** l'operatore apre una distinta nuova e digita i negativi a mano.

⚠️ **E il lotto 7 NON l'ha risolta, anche se sembra.** Le sistemazioni fanno una
cosa diversa: decidono che fare di un'eccedenza **vera** (denaro davvero
arrivato in più). La correzione rimedia a una registrazione **sbagliata** — un
importo digitato male. Due mestieri, due strade, e confonderli significherebbe
registrare come credito del cliente un errore di battitura.

**La mia proposta: (a)**, con **una raccomandazione sul nome**: si chiama
**correzione**, mai «storno». `STORNATA` è stata ritirata dal catalogo il 21/08 e
rimetterne la parola nell'interfaccia riaprirebbe una porta che il lotto 2 ha
chiuso.

⚠️ **E (a) non è gratis**: precompilare significa creare N righe in un colpo,
cioè di nuovo **una funzione madre** e non un ciclo nel service. Se Q-7 va su
(a), è un secondo oggetto da chiedere al team DB insieme a Q-2 e Q-10.

---

### ~~Q-8 · Il lookup delle rate: dove vive?~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: `GET /vendite/fatture/{id}/scadenze/lookup/` — endpoint di
> lookup dedicato in `vendite`, con `skip_area_check = True` e lo scope nel
> repository. ⛔ **Nessuna LETTURA su `vendite`** a chi lavora gli incassi:
> allargare un permesso per comodità è il caso che la regola del progetto vieta.

È il pattern già in uso per le unità di misura degli articoli: risponde **il
minimo** (numero rata, scadenza, importo, residuo) su **una** fattura già scelta.

⭐ **Non serve niente al team DB**: la lettura delle rate esiste già e i numeri
li dà la base dei saldi (§2.7).

> 🔴 **CORREZIONE del 2026-08-24, trovata scrivendo il codice.** L'endpoint
> **non** è finito in `vendite`: `api.md` §Comunicazione cross-modulo vieta le
> **chiamate laterali fra moduli di pari livello**, quindi una view di `vendite`
> non può chiedere un saldo a `pagamenti`. E un elenco di rate **senza il
> saldo** non risponde alla domanda per cui esiste — *«su quale rata metto
> questi soldi?»*.
>
> ⇒ Vive in `pagamenti`: `GET /pagamenti/fatture/{id}/rate/`, con
> `skip_area_check`. ⭐ **La sostanza della decisione non cambia** — nessun
> permesso allargato, risposta minima su una fattura già scelta: cambia lo
> schema che lo ospita. ⚠️ Stessa ragione per il **saldo del documento**
> (`GET /pagamenti/fatture/{id}/saldo/`), che il drawer fattura consuma da
> `vendite`.
>
> Se preferisci comunque il lookup nudo in `vendite`, si fa — ma allora il saldo
> diventa una chiamata in più **per ogni rata**.

⛔ **E solo per il lookup**: lo **scadenzario** resta fuori perimetro. ⚠️ Ma su
questo è nata una cosa che nessuno aveva previsto — vedi §3.7.

---

### ~~Q-9 · Quante liste mettiamo a piano, e in che ordine le chiediamo al DB?~~ ✅ **chiusa dalla revisione, senza essere decisa**

Il 22/08 proponevo «un solo brief con le prime tre, e le altre si rimandano».
Non serve più scegliere: **due delle viste erano già state consegnate** dai lotti
5 e 7, e ciò che resta sono **quattro seed**, che si chiedono **insieme e già
scritti** (§6). ⭐ Il costo di chiederle tutte è sceso sotto il costo di
decidere quali rimandare.

---

### ~~Q-10 · L'«incassato» esiste sulla rata e non sulla fattura~~ ✅ **CHIUSA da Tid (2026-08-24): strada (a)**

> ⭐ **Decisione**: si chiede al team DB di **allargare `fn_get_saldo_fattura`**
> alla stessa forma della sorella — `residuo · in_lavorazione · incassato` — così
> i due livelli rispondono allo stesso modo.

**Il dislivello.** Il lotto 5 ha dato a `fn_get_saldo_rata` **tre** numeri; il
lotto 4 ne aveva dati **due** a `fn_get_saldo_fattura`. Finché il pannello della
fattura non mostra l'incassato (Q-6) sembra un problema che non c'è — ma con
**§2.7** il perimetro è cambiato: la base dei saldi deve reggere anche il **saldo
cliente**, e *«quanto ho incassato davvero da questo cliente»* è proprio la
domanda che pretende quel numero, sommato su più documenti.

**Perché non le altre due strade:**

| | Perché no |
| --- | --- |
| sommare le rate nel BE | ⛔ **Falso**: una riga può avere fattura **senza** rata — il fondo fattura è esattamente così — e quel denaro non comparirebbe in nessuna somma di rate |
| riscrivere la formula nel BE | ⚠️ Due sedi per la stessa regola: il giorno che nasce un terzo centro interno, una lo sa e l'altra no. E **contraddirebbe §2.7** |

⚠️ **Sul quando**: non serve alla slice 3 (il pannello fattura non mostra
l'incassato). Serve **prima del saldo cliente** — ma si chiede adesso, perché è
un paragrafo in un brief che si scrive comunque.

---

## 8. Che cosa faccio appena rispondi

⭐ **In quest'ordine — e stavolta la prima riga di codice arriva subito**,
perché il telaio non dipende da nessun prerequisito e le due code dei lotti
(§1.5) sono lavoro di minuti che il progetto si porta dietro da due giorni.

1. **Slice 0**, il telaio, **compresi** il ripiego riscritto e i tre codici
   obsoleti tolti;
2. **un brief solo al team DB** su `dev/db-tid`, con **due cose certe e due
   condizionate**: i quattro seed di lista (righe **già generate** da me, da
   rivedere), le **due righe di `azioni_processo`** per il cancello sulla
   registrazione (Q-5), l'allargamento di `fn_get_saldo_fattura` (se Q-10 → sì)
   e la madre della correzione (solo se Q-7 → (a)). ⛔ Un brief, non quattro;
3. **Slice 1** — la distinta e le sue righe, appena arrivano i seed;
4. **Slice 2** — la registrazione. ⚠️ Se Q-5 va come propongo, l'azione
   `registra_distinta` va decisa **prima** di scriverla;
5. **Slice 3** — la rata, la capienza e le rate fuori capienza;
6. poi S4 (✅ non più ferma: DATO-1 risolto) e S5, che chiude il cantiere e sblocca la Fase D
   dei fondi.

⚠️ **E due cose che non farò senza dirtelo**: nessuna delle quattro estrazioni di
§5.3 al primo colpo (la regola del 2 vale anche quando il piano prevede
l'astrazione), e nessun commit di propria iniziativa.

---

## 9. Dove guardare

| Cosa | Dove |
| --- | --- |
| Le decisioni di dominio (D1…D15) | [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis e §3-bis |
| I passi DB, lotto per lotto | [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md) §6.7…§6.14 |
| Le richieste che il DB ha lasciato al BE | [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md) §3 (BE-1…BE-10, DATO-1) |
| Come si semina una lista | [work-done/brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md) + `scripts/gen_seed_lista.py` |
| Le linee guida API | [api.md](../api.md) |
| Gli standard frontend | [frontend-standards.md](../frontend/frontend-standards.md) |
| I building block | [catalogo BE](../backend/catalogo-building-block-backend.md) · [catalogo FE](../frontend/catalogo-building-block-frontend.md) |
| Il modello pagamenti in prosa | [gestione-dei-pagamenti.md](../../guide/gestione-dei-pagamenti.md) |
| La madre del posting | [dbzero/pagamenti/manual/fn_posta_contabile.md](/dbzero/pagamenti/manual/fn_posta_contabile) |
| Il guard della rata (coerenza + capienza) | [dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_rata.md](/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_rata) |
| Un modello di lista da copiare | `frontend/src/vendite/views/ApprovazioniPrezzoListView.vue` |
| Un modello di view BE da copiare | `backend/apps/vendite/api/views_fondi_fattura.py` |

---

## 10. ⭐ Stato di sviluppo

> Aggiornato al **2026-08-28**. ⚠️ Questa sezione dice **che cosa esiste
> davvero**, non che cosa è pianificato: il piano è §3, questo è il consuntivo.

### 10.1 Che cosa esiste, e dove

| File | Che cos'è |
| --- | --- |
| `apps/pagamenti/types.py` | I `TypedDict` delle righe DB: distinta, riga, i due cataloghi di stato, la ricevuta del posting e ⭐ **la forma unica del saldo** (§2.7) |
| `apps/pagamenti/db/pagamenti_repository.py` | Il repository **dello schema**, non dell'entità. Liste e dettagli con i display field in JOIN, i totali derivati in LATERAL, le scritture semplici e **la chiamata alla funzione madre** |
| `apps/pagamenti/services/pagamenti_service.py` | La facciata: validazione del payload, traduzione degli errori DB (BB `make_db_errors_translator`), composizione della risposta |
| `apps/pagamenti/api/views.py` | Otto view `DomainAPIView`, tutte con `@extend_schema` |
| `apps/pagamenti/api/urls_v1.py` + `zeroerp_backend/urls.py` | Le rotte, montate sotto `/api/v1/pagamenti/` subito dopo `pratiche` |
| `apps/pagamenti/services/saldi_service.py` | ⭐ **La base dei saldi** (§2.7): l'unico posto che legge le funzioni di saldo. Forma unica `residuo · in_lavorazione · incassato`, e **tre livelli in testa** — documento, rata, e il cliente dichiarato ma non ancora acceso |
| `apps/core/services/error_ui_overrides.py` | La voce nuova `confirm_and_retry` sul codice della capienza (Q-1): il frontend riconosce la **classe di comportamento**, non i codici |
| `apps/pagamenti/services/sistemazioni_service.py` | Il giro delle sistemazioni: l'elenco, la registrazione della decisione e i due verbi. ⭐ **Nessuna macchina nuova** — le tre destinazioni usano meccanismi che esistevano già tutti |
| `apps/pagamenti/services/_helpers.py` | I pezzi che i service del dominio condividono (codice di validazione, lettura di un importo, involucro paginato), spostati qui alla **seconda occorrenza** |
| `apps/pagamenti/tests/{api,services,db}/` | **108 test**: 78 sui service, 25 sugli endpoint, 17 sull'SQL e sui cataloghi |

#### E il frontend, dal 2026-08-28

| File | Che cos'è |
| --- | --- |
| `pagamenti/api/pagamenti.js` | Le 23 rotte. ⭐ Sul filo la risorsa si chiama **`distinte`**, non `contabili`: è la parola che l'operatore legge |
| `pagamenti/vocabolari.js` | ⛔ **Solo i vocabolari SENZA catalogo** (`CHECK` a DB o whitelist del BE): lì una copia nel frontend è inevitabile, e allora sta in un posto solo. Gli **stati** non ci sono — sono tabelle di catalogo, e copiarli nasconderebbe lo stato che nasce domani |
| `pagamenti/etichette.js` | La fabbrica delle etichette, tutte **fail-visible**: un valore che il backend aggiunge e i locales non conoscono si vede come **codice**, mai come cella vuota |
| `pagamenti/stores/` | Cinque store, tutti `userScoped`. ⭐ **Nessun pavimento temporale**: sono code di lavoro e configurazione — un incasso di tre mesi fa da abbinare è lavoro di oggi |
| `pagamenti/views/` + `components/` | 6 pagine · `DistintaDrawer` (master-detail + i verbi) · `CanaleIncassoDrawer` · `SistemazioneDrawer` · i 4 dialoghi (apertura, abbinamento, registrazione, conferma) |
| `core/composables/{useForzaturaConfermata,useLetturaTreStati}.js` · `core/components/FatturaLookup.vue` | I tre BB nati qui e finiti in `core/` perché non sanno niente di incassi |

### 10.2 Le venti rotte, e a che punto sono

| Metodo e path | Stato |
| --- | --- |
| `GET /distinte/` | ✅ scritto. 📮 La `<ListaConfigurabile>` a video aspetta il **seed** (DB-2), e con esso si dichiarerà `lista_codice` |
| `POST /distinte/` | ✅ scritto — *get or create*, origine `MANUALE`, stato `BOZZA`, `Idempotency-Key` obbligatoria, e `gia_popolata` nella risposta (Q-3) |
| `GET /distinte/{id}/` | ✅ scritto — testata, totali derivati, righe **e i due cataloghi di stato** in un round-trip |
| `PATCH /distinte/{id}/` | ✅ scritto — solo i campi che una persona compila |
| `POST /distinte/{id}/stato/` | ✅ scritto — **tre** valori: `VALIDATA`, `BOZZA`, `ANNULLATA` |
| `GET/POST /distinte/{id}/righe/` | ✅ scritto — ⭐ **dal 14/09 la riga nasce CON LA DESTINAZIONE** (D16): con `fattura_id` nasce `ABBINATA` in un INSERT solo, senza nasce `DA_ABBINARE` (l'eccezione dichiarata) |
| `PATCH /righe/{id}/` · `POST /righe/{id}/stato/` | ✅ scritti — i **fatti** e il percorso della riga |
| `DELETE /righe/{id}/` | ✅ scritto *(14/09, D17)* — `attivo = false`, i motivi li dà il DB (409); una riga eliminata non è più raggiungibile da nessun verbo |
| `GET /distinte/{id}/anteprima-registrazione/` | ✅ scritto — la fotografia, coi **motivi** per cui una riga resta indietro |
| `POST /righe/{id}/abbina/` | ✅ scritto *(slice 3)* — fattura, cliente, rata facoltativa, e la **forzatura a due tempi** che passa intatta al guard |
| `GET /righe/` | ✅ scritto *(slice 3)* — la coda del riconciliatore: `coda=DA_ABBINARE\|SOSPESE\|TUTTE`, **due voci di menu e un endpoint solo** |
| `GET /rate/fuori-capienza/` | ✅ scritto *(slice 3)* — l'elenco senza cui la forzatura nasconde invece di registrare. La vista c'era già, mancava la porta |
| `GET /rate/{id}/saldo/` · `GET /fatture/{id}/saldo/` · `GET /fatture/{id}/rate/` | ✅ scritti *(slice 3)* — **la base dei saldi**, forma unica a ogni livello. Gli ultimi due con `skip_area_check`: li consuma il drawer fattura, che vive in `vendite` |
| `GET /eccedenze/` | ✅ scritto *(slice 5)* — i documenti su cui è entrato più del dovuto, **ordinati per cliente** di default: la decisione si prende guardando il cliente, e un elenco per documento la nasconde |
| `POST /sistemazioni/` | ✅ scritto *(slice 5)* — registra la decisione. ⭐ Un `INSERT`, non una madre: una scrittura sola non ne ha bisogno. 🔴 Cliente ed emittente **si derivano** dalla fattura, non si dichiarano |
| `POST /sistemazioni/{id}/conferma/` · `…/annulla/` | ✅ scritti *(slice 5)* — i due verbi. ⚠️ Il **canale del rimborso** si chiede alla conferma: da quale conto esce il bonifico è una decisione del momento in cui si paga |
| `GET /sistemazioni/{id}/` · `GET /fatture/{id}/sistemazioni/` | ✅ scritti *(slice 5)* — l'atto col suo esito, e gli atti di un documento (⭐ sono più di uno per natura: si può rimborsare una parte e riportare il resto) |
| `POST /distinte/{id}/registra/` | ✅ scritto — **una sola `SELECT`** sulla madre. ⚠️ Il cancello `registra_distinta` è **dichiarato**: finché l'azione non è a catalogo e assegnata, `fn_check_azione_processo` risponde `false` per tutti tranne i super admin. **Fail-closed**, che sul gesto irreversibile è il verso giusto in cui sbagliare |

### 10.3 ⭐ Le due code dei lotti DB, chiuse

| | Cosa | Esito |
| --- | --- | --- |
| **BE-10** | I tre codici resi obsoleti dal lotto 7 erano ancora nel ripiego | ✅ **tolti**. Erano una frase pronta per un errore che non arriva più |
| lotto 4 | Il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` portava la frase **vecchia** | ✅ **riscritto** sulla frase allargata del 22/08, e **senza segnaposti** — è la ragione per cui quel file esiste |

### 10.4 🔴 La revisione critica del codice, e i sette difetti che ha trovato

> Fatta il **2026-08-24 subito dopo la scrittura**, su richiesta di Tid. ⭐ Sei
> difetti su sette **non davano errore**: davano un dato sbagliato, o un
> silenzio.

| | Difetto | Perché contava | Rimedio |
| --- | --- | --- | --- |
| **1** | 🔴 **L'elenco duplicava le distinte.** Il legame coi lotti era un `LEFT JOIN` diretto, ma l'unico su `vendite_contabili_lotti` è `(lotto_id, contabile_id)` e **non** il solo `contabile_id`: una distinta legata a due lotti compariva **due volte**, e il conteggio totale con lei | Nessun errore, mai: una lista più lunga del vero, che nessuno mette in dubbio | I lotti si **aggregano** in una LATERAL (`lotti_ids`), non si joinano. Presidio statico che impedisce di rimettere il JOIN |
| **2** | 🔴 **Un cambio di stato che non avveniva rispondeva 200.** `set_stato_*` torna il numero di righe toccate e nessuno lo guardava: se il codice di stato non risolveva a catalogo, l'operatore leggeva «fatto» su un gesto mai successo | È il difetto peggiore della lista: il silenzio che somiglia al successo | `E_CONTABILE_STATO_NON_CONFIGURATO` quando le righe toccate sono zero, su testata **e** riga |
| **3** | 🔴 **Aprire una distinta col totale dichiarato erano due transazioni.** La funzione madre non prende quel parametro, quindi si scrive subito dopo — ma `ATOMIC_REQUESTS` **non è attivo** nel progetto | Una distinta nata senza il suo dichiarato è una distinta la cui **quadratura non scatta mai**: il controllo esiste e non dice niente | `transaction.atomic()` esplicito, con un test che verifica che ci sia (neutralizzarlo senza quel test spegnerebbe il presidio) |
| **4** | ⚠️ **`NaN` e `Infinity` passavano come importi.** `Decimal("NaN")` si costruisce senza protestare, e un JSON può portarlo | Ogni somma che incontra un NaN diventa NaN — e **un totale NaN non si vede**: si legge come un campo vuoto | Rifiutati: un importo deve essere finito |
| **5** | ⚠️ **Una dichiarazione di ZERO righe veniva rifiutata.** Usavo il lettore «intero positivo», ma l'anteprima può mostrare zero righe registrabili e la coppia (0, 0) è esattamente ciò che l'operatore ha davanti | Il database avrebbe risposto `NULLA_DA_POSTARE` — un esito vero — e il backend lo trasformava in un 400 con una frase falsa | Lettore non negativo |
| **6** | ⚠️ **I nomi di colonna degli UPDATE finivano in SQL senza whitelist nel repository.** Oggi le chiavi arrivano dalla whitelist del service, quindi non era sfruttabile — ma il repository è **l'ultimo cancello** prima della stringa SQL | Il giorno in cui qualcuno chiamasse quei metodi con chiavi da un payload, la differenza sarebbe una SQL injection | Whitelist per oggetto **dentro** il repository, con il suo test |
| **7** | ⚠️ **Codice morto e duplicato**: due funzioni di normalizzazione jsonb identiche, un modulo di cataloghi che non chiamava nessuno, tre parametri di `create_riga` mai passati, un parametro `solo_attive` senza consumatori | Superficie che invecchia — e i tre parametri erano peggio: una **seconda porta** per scrivere l'abbinamento, che avrebbe aggirato il verbo e le sue regole | Tutto rimosso. I due elenchi di stati chiedibili sono passati **dentro il dettaglio**, dove servono |

### 10.4-bis 🔴 La seconda revisione (slice 3), e il difetto che nessun test chiedeva

> Fatta il **2026-08-24** subito dopo la slice 3, su richiesta di Tid.

| | Difetto | Perché contava | Rimedio |
| --- | --- | --- | --- |
| **1** | 🔴 **Ordinare la coda per `distinta` produceva un 500.** Il contratto dichiarava quella colonna ordinabile, ma il `SELECT` non la portava: l'ordinamento finisce in una clausola SQL, quindi non era un valore sbagliato — era **una query che non parte**. ⚠️ E con essa cadeva la promessa scritta nel codice: una riga cross-distinta **senza il documento da cui viene** non si lavora | ⭐ **Nessun test lo chiedeva**: un ordinamento si prova solo chiedendolo, e i test ne provavano uno | Colonne e `FROM` separati, così la coda può **aggiungere** le sue tre colonne. E un presidio che verifica **ogni** colonna dichiarata ordinabile su **tutte e tre** le liste — provato rimettendo il difetto: diventa rosso |
| **2** | ⚠️ **Il saldo del documento erano due letture separate.** Due `SELECT` leggono **due istanti diversi**: se una registrazione atterra fra l'una e l'altra, il pannello mostra un residuo di prima accanto a un «in lavorazione» di dopo — **due numeri veri che insieme raccontano una cosa falsa** | Ed è il pannello che si apre a ogni fattura | Una query sola con `CROSS JOIN` fra le due funzioni |
| **3** | ⚠️ **Lo scheletro della lista paginata era scritto tre volte** (distinte, coda, rate fuori capienza) | Tre copie della stessa paginazione divergono alla prima correzione — ed era già successo col conteggio di ripiego, aggiunto solo alla prima | Un helper solo, `_lista_paginata` |
| **4** | ⚠️ **Le letture nuove non avevano il guard del canale di sistema.** Le tre funzioni di saldo sono `SECURITY INVOKER`: su un ruolo che scavalca la row security risponderebbero i numeri di **tutti** gli emittenti | Il modulo dichiara quel presidio in testa, e quattro metodi non lo applicavano | Guard su tutte e quattro |
| **5** | ⚠️ **Altri codici cablati senza presidio**: gli stati delle due code, lo stato dell'abbinamento, i due motivi di «fuori capienza» | Un refuso qui **non dà errore**: dà una coda vuota o un elenco vuoto — la risposta più rassicurante possibile su liste che esistono per non far sparire del denaro | Presìdi contro i CSV di seed e contro la definizione della vista |
| **6** | ⚠️ **Due tipi dichiarati e mai usati** (`RigaCodaRow`, `SaldoRow`), più un `import` inline dentro un test | Un tipo che nessuno annota è un commento travestito da contratto | Agganciati alle firme che li producono |

### 10.4-ter 🔴 La terza revisione (frontend), e i difetti del *modello* che ha trovato

> Fatta il **2026-08-28** su richiesta di Tid, dopo le due schermate finali.
> ⭐ La differenza con le prime due: qui i difetti peggiori non erano bug di
> codice, erano **assunzioni sul modello scritte come costanti**.

| | Difetto | Perché contava | Rimedio |
| --- | --- | --- | --- |
| **1** | 🔴 **Gli stati della riga erano CABLATI**, contro la regola che questo stesso brief mette in §5.4: `finale = stato_codice === 'POSTATA'`. Ma a catalogo **`STORNATA` è anch'esso terminale** | Su una riga stornata il drawer offriva abbinamento e transizioni **che il database rifiuta**: gesti che finiscono in errore, su un documento di denaro | `is_final` si legge dal **catalogo**, che il dettaglio già porta. E le transizioni si **generano** da `stati_richiedibili.riga` × catalogo, come già faceva la testata |
| **2** | 🔴 **Una transizione dichiarata e mai offerta.** Scrivendo a mano solo `SOSPESA` e `SCARTATA` avevo lasciato fuori il ritorno a **`DA_ABBINARE`** — l'unico modo di **sganciare un abbinamento sbagliato** | ⭐ Il contratto la dichiara ammessa: ciò che il contratto dichiara va **provato per intero**, e qui non era nemmeno raggiungibile | Generandole dal catalogo è ricomparsa da sé. ⛔ L'unica esclusa resta `ABBINATA`, che ha un **verbo proprio** |
| **3** | 🔴 **Il rosso della conferma diceva il falso.** `danger: codice === 'SCARTATA'` — ma a catalogo `SCARTATA` ha `is_final = false` | Allarmava per un gesto **reversibile**, e non allarmava per gli altri: un colore che mente è peggio di nessun colore | Il rosso è `is_final`, in **tutte e due** le sedi (testata e riga): rosso = «da qui non si torna» |
| **4** | 🔴 **L'anteprima di registrazione era in `silent`** — lo stesso difetto corretto in tre punti il giro prima | Una lettura fallita si leggeva come «non c'è niente da registrare»: un'**affermazione**, e falsa, sul foglio che sta per essere chiuso | Via il `silent`, e i tre stati passano al BB nuovo |
| **5** | ⚠️ **Un `onActivated` che ricarica in quattro liste** — ma `useSearchTable` lo fa già | **Due richieste identiche** a ogni rientro nella scheda, e due risposte possono tornare in ordine inverso | Tolto. Nella coda righe resta il solo allineamento con la **rotta**, che nessun altro fa |
| **6** | ⚠️ **Il conto del canale azzerato in silenzio** all'apertura in modifica: una corsa fra il caricamento dei conti e quello del dettaglio | Cancellava la configurazione di un canale — e il conto **è il perimetro dei soldi** | Si azzera solo su un cambio **voluto** di emittente; e un conto non più agganciabile si **dichiara** invece di apparire come campo vuoto |
| **7** | ⚠️ **Duplicazione, tre volte** (regola del 2): il terzetto dei tre stati ×4, la riga `labelOrCode` in **otto** componenti con tre prefissi in coppia, il caricamento dei canali ×2 | Due copie divergono alla prima correzione, e la copia rimasta indietro sbaglia **su una sola delle due schermate** — cioè nel modo più difficile da vedere | Tre estrazioni, tutte **fabbriche** (§5.2) |

⭐ **E la verifica che è valsa di più**: tutti e **17** i codici d'errore che le
due schermate nuove possono far scattare — i tre guard PSP, il conto non di
incasso, i nove delle sistemazioni — sono **a catalogo e col ripiego**. Nessuno
diventa un 500: era la trappola segnata nell'handoff, e questa volta non è
scattata.

### 10.9 🔴 E-4 — la riverifica sotto RLS, e i due buchi che ha trovato

> Fatta il **2026-08-28**. ⭐ È il passo che §2.6 chiedeva: *«ogni lista va
> provata con un utente dentro e uno fuori dal perimetro, e la differenza va
> guardata»*. Due operatori veri di **due emittenti diversi**, più il caso senza
> contesto.

**Il metodo, e perché non poteva essere un conteggio.** Le tabelle transazionali
di `pagamenti` sono **vuote** oggi: un confronto sui dati avrebbe dato zero in
tutti e tre i contesti, cioè **verde per sottrazione** — la trappola del
conteggio fail-closed, in cui uno zero senza contesto sembra un dato. Le due
prove che hanno trovato qualcosa sono di specie diversa:

| Prova | Che cosa ha detto |
| --- | --- |
| **Strutturale** — `relrowsecurity` e conteggio policy, tabella per tabella | 🔴 **4 su 12**, non 12 su 12. E `enti_incasso`, che porta dato per emittente, è fra quelle scoperte |
| **Comportamentale** — la stessa lettura fatta da due operatori di due emittenti | 🔴 L'operatore dell'emittente 32 leggeva l'**IBAN di incasso** dell'emittente 44 passandone il `soggetto_ruolo_id`. Nessun errore, un elenco pieno |

| | Buco | Di chi è | Stato |
| --- | --- | --- | --- |
| **1** | 🔴 `pagamenti.enti_incasso` **senza row security**: l'elenco dei canali, IBAN compreso, è comune a tutti gli emittenti | **Team DB**: è una policy, e le policy non le scrive questo cantiere | 📮 **Chiesta il 28/08** ([brief](../work-done/brief-db-perimetro-canali-e-correzione-guidata.md) §1), con la funzione già esistente da usare e tre domande |
| **2** | 🔴 `GET /conti-incasso/?soggetto_ruolo_id=…` **fuori perimetro** | **Backend**, e non per ripiego: `anagrafiche.soggetti_ruoli_conti_bancari` ha la RLS **spenta di proposito**, quindi lì il perimetro può metterlo solo chi chiede | ✅ **Chiuso il 28/08**: rifiuto `E_SCOPE_EMITTENTE` (**403**, già a catalogo e col ripiego), cancello nel **repository** accanto all'SQL, test sul DB provvisto **provato rimettendo il difetto** |

⚠️ **E due trappole pagate scrivendo il rimedio**, che valgono per chiunque
scriva un'altra lettura fuori dalla row security:

1. `script.fn_check_user_emittente_scope` risponde **`true`** su
   `p_auth_user_id = NULL` (regola 1, «job batch»). Delegarle la domanda su un
   percorso senza GUC **apre** il perimetro invece di chiuderlo: il backend deve
   rifiutare **prima**, perché «non so chi sei» vale **no**.
2. La GUC si chiama **`app.current_user_id`**, non `app.auth_user_id`. Col nome
   sbagliato il cancello rifiutava **tutti**, compreso chi ha diritto — ⛔ e i
   test col doppio erano **verdi**, perché un doppio non ha un perimetro. È il
   motivo per cui la prova di questo presidio gira sul **database vero**.

### 10.5 ⭐ Gli SQL provati contro il database vero

⚠️ **Fino a qui erano provati solo coi mock, che non vedono l'SQL.** Sono stati
eseguiti con `EXPLAIN` sul database di sviluppo — che **pianifica senza
eseguire** — tutte e undici le istruzioni del repository:

| Gruppo | Esito |
| --- | --- |
| Le cinque letture della slice 1 (lista, conteggio, dettaglio, righe, riga) | ✅ **SQL valido** |
| Le sei della slice 3 (coda + conteggio, fuori capienza + conteggio, rate con saldo, abbinamento) | ✅ **SQL valido** |
| Le tre funzioni di saldo | ✅ **SQL valido** |
| ⭐ **Ogni colonna dichiarata ordinabile**, su tutte e tre le liste — **15 combinazioni** | ✅ **tutte valide** *(ed è la prova che ha trovato il difetto 1 della seconda revisione)* |
| Le quattro scritture (UPDATE testata e stato, INSERT riga, UPDATE stato riga) | ✅ **SQL valido** (in transazione annullata) |
| I due cataloghi di stato | ✅ **SQL valido** |
| Le firme delle due funzioni madri | ✅ **i nomi dei parametri che il repository passa esistono davvero** |

⛔ **Le due funzioni madri non sono state chiamate, nemmeno sotto `EXPLAIN`**:
registrare è irreversibile, e per verificare ciò che poteva davvero rompersi —
un nome di parametro sbagliato — basta leggere la firma viva dal catalogo di
PostgreSQL.

### 10.6 Le prove

| Misura | Esito |
| --- | --- |
| Test del dominio `pagamenti` | ✅ **108/108** (22 → 51 revisione 1 → 78 slice 3 → 86 revisione 2 → 108 slice 5) |
| Presidi toccati (`test_error_policies_classi`, `test_sql_order_helpers`) | ✅ **27/27** |
| Regressioni sulla suite intera | ✅ **zero**, misurate confrontando l'elenco dei rossi con quello di un **albero pulito a HEAD** — non «sembra a posto» |
| Schema OpenAPI | ✅ nessun warning nuovo sulle otto view (restano i 546 generici del progetto, che non sono di questo cantiere) |

> 🔴 **Un difetto trovato da un presidio, e vale la pena saperlo.** La prima
> stesura della lista incollava `NULLS LAST` dopo la direzione
> dell'ordinamento. `test_nessun_call_site_incolla_nulls_alla_direzione` l'ha
> bocciata: la direzione la compone `sql_order_direction`, che **porta già la
> posizione dei NULL** — i vuoti dove starebbe lo zero, in coda scendendo e in
> testa salendo. Incollarne un altro produce SQL invalido, e la lista
> risponderebbe 500 su ogni ordinamento. 📌 *Un ordinamento sbagliato non
> rompe niente in modo visibile: produce un elenco ordinato male, che si
> scopre solo guardando una lista vera.*

### 10.8 ✅ DATO-1 — CHIUSO il 2026-08-28. Il cantiere non ha più blocchi

> ⭐ **Risolto da Tid**, e **verificato sul database col contesto operatore** il
> **2026-08-28** — non preso per buono: i due conti sono stati rifatti a livello
> **RUOLO**, ciascuno sul ruolo del proprio emittente.

| IBAN | soggetto_ruolo | emittente | livello |
| --- | --- | --- | --- |
| `IT00TESTINCASSO0000000001` | **72** | **32** `PGTAP-EF-…` | ✅ ruolo |
| `IT00TESTINCASSO0000000002` | **159** | **44** `EMI-TEST` | ✅ ruolo |

Entrambi `bloccato = false` e con validità aperta (`valido_dal`/`valido_al`
nulli, cioè infinita), quindi passano il filtro di validità della lookup.
⇒ `GET /pagamenti/conti-incasso/?soggetto_ruolo_id=72` risponde **una riga**
dove il 25/08 rispondeva **zero** con `nessun_conto_di_incasso: true`.

⭐ **Che cosa si sblocca, ed è più di una schermata.** Prima nessun canale di
incasso era **creabile** — il conto è obbligatorio su tutti i tipi (D5) e a
livello ruolo non ce n'era nessuno per i due emittenti. Oggi
`list_enti_incasso` risponde **zero canali** non più perché non si possono
fare, ma perché non ne è ancora stato fatto uno. Ne discende che il giro
completo diventa esercitabile in-app: canale → distinta (che il **centro** lo
deriva dal canale, Q-3) → righe → registrazione.

⚠️ **Un residuo che non blocca niente, e va detto.**
`IT00TESTINCASSO0000000001` è rimasto **anche** a livello soggetto, sullo
stesso soggetto: la riga del 24/08 non è stata tolta. Non ha effetto sui canali
(la lookup legge la tabella di **ruolo**) e non viola il vincolo nuovo — che
proibisce lo stesso IBAN come `INCASSO` su soggetti **diversi**, non su due
livelli dello stesso. Resta però una seconda dichiarazione dello stesso fatto:
⛔ non la tolgo di mia iniziativa, è un dato.

✅ **E la domanda di modello che stava qui è stata raccolta dal team DB.**
L'unicità «un conto `INCASSO` → un solo soggetto» presidiava **solo** la tabella
a livello ruolo, quindi la porta a livello soggetto ne stava fuori: lo stesso
conto poteva essere dichiarato `INCASSO` per due soggetti diversi senza che
niente lo impedisse. Il lotto 9 ha chiuso anche quella
(`ex_scb_conto_incasso_un_solo_soggetto`, S5-8, con il pgTAP del lotto 6 esteso
da 6 a 10 asserzioni). ⚠️ Resta fuori un guard **diverso**: che il conto di un
canale appartenga all'**emittente del canale**. È l'altra metà del rilievo, e
non è in questo giro.

### 10.10 🔴 Il difetto che la rilettura di A-8 ha trovato: una richiesta esaudita e mai raccolta

> Trovato il **2026-08-29** costruendo sopra la base dei saldi, e corretto lo
> stesso giorno. ⭐ **Non era un bug di codice: era un documento e un codice che
> dicevano la stessa cosa falsa, e nessuno dei due mentiva da solo.**

**Il fatto.** `pagamenti.fn_get_saldo_fattura` risponde **quattro** colonne —
`saldo, in_lavorazione, incassato, has_movimenti` — dal **25/08**: è **DB-10**,
la richiesta che questo cantiere aveva fatto (Q-10) e ottenuto. Ma il backend:

| | Prima | Adesso |
| --- | --- | --- |
| colonne lette | **due** (`saldo`, `has_movimenti`) | tutte e quattro |
| `incassato` a livello documento | 🔴 **buttato via** → `None` | il numero che il database dà |
| `in_lavorazione` | preso da `fn_get_saldo_fattura_contabili.saldo_contabile` | preso da `f.in_lavorazione` — **una sede sola** |
| il commento sopra il metodo | *«il database risponde due numeri e non tre»* | 🔴 falso dal 25/08 |
| il test | `test_sul_documento_incassato_e_none` — **verde** | riscritto, più uno che asserisce che documento e rata hanno la **stessa forma** |

🔴 **Il pezzo che vale la pena ricordare è il test.** Era verde, e difendeva
l'errore: asseriva un'**assenza** — «`incassato` è `None`» — cioè *l'ipotesi*
sotto cui era stato scritto, non il sistema. Quando l'assenza è stata colmata,
il test ha continuato a passare e a proteggere il buco. *Un test che asserisce
che un numero non c'è lo tiene fuori anche il giorno in cui arriva.*

⚠️ **E la cosa somiglia a un difetto già registrato in questo brief**: il
`test_canale_inesistente_404` di §6-bis, che confrontava `exception.code` con la
costante che il codice stesso leggeva. Due forme diverse dello stesso vizio —
**un test che verifica la propria ipotesi**.

#### ⭐ Il difetto figlio, trovato rileggendo la correzione appena scritta

La prima stesura teneva il `CROSS JOIN` con `fn_get_saldo_fattura_contabili`
«per una ragione sola: `has_righe_postabili`» — e la ragione era **scritta, non
verificata**. `has_righe_postabili` **non lo legge nessuno**: né il service, né
la view, né il frontend. Quindi il join faceva girare, a ogni apertura del
drawer fattura, una funzione che `fn_get_saldo_fattura` **chiama già al suo
interno**.

⚠️ E non era gratis: quella funzione **non è `STABLE`** (il suo ramo d'errore
scrive nel registro), quindi due valutazioni sono due letture indipendenti — la
stessa trappola pagata sul guard del fondo, dove una funzione `VOLATILE` letta
due volte poteva accettare metà condizione e rifiutare l'altra. Adesso è **una
`SELECT` su una funzione sola**, provata con `EXPLAIN` sul database vero: una
*function scan* invece di un *nested loop* su due.

> 📌 *Giustificare una cosa in un commento non è verificarla. Il commento
> «resta per una ragione sola» era la mia ipotesi sul perché quel join servisse,
> e bastava un `grep` a smentirla.*

#### Che cosa ne discende per il frontend: **niente**, e non per caso

`SaldoPanel` gestiva già `incassato == null` con un messaggio a parole invece
che con un trattino. Il ramo semplicemente non si accende più sul documento, e
⛔ **resta**: è la risposta a un caso che il modello ammette — il livello
**CLIENTE**, finché somma solo documenti — e *un presidio non si toglie perché
oggi il suo ramo è irraggiungibile*. Aggiornati i due commenti che dichiaravano
il dislivello come un fatto del database.

⭐ **E il terzo livello ha perso il suo ostacolo**: il saldo cliente aspettava
proprio l'`incassato` a livello documento. Non è stato acceso — è una decisione,
non una conseguenza — ma la nota nel service non dice più che manca un
prerequisito.

---

### 10.11 ⭐ Il ripiego a trattino diventa il default, e `pagamenti/formato.js` sparisce

> Autorizzato da Tid il **2026-08-29**, dopo la dichiarazione della seconda
> occorrenza. ⚠️ **Il raggio d'azione è dichiarato, non scoperto**: su **67**
> chiamanti di `formatCurrency`, **nove** passavano `{ placeholder: '—' }` a mano
> e **cinquantotto** si appoggiavano alla stringa vuota — `CellaConfigurabile`
> compresa, quindi ogni colonna `currency_eur` di ogni lista configurabile.

**Perché è il default giusto, e vale solo per gli importi.** Su un importo
`null` significa «questo conto non si applica»: una cella **vuota** si legge
come *un dato perso*, il trattino come *una risposta*. ⛔ `formatNumber` **non**
è stato cambiato: una quantità assente non è per forza «non si applica», e
cambiarlo per simmetria sarebbe una decisione presa senza motivo.

**E `pagamenti/formato.js` è stato cancellato** (autorizzato). Esisteva per una
riga — `formatCurrency(v, { placeholder: '—' })` — e con il default quella riga
non aggiungeva più niente. Gli otto componenti del dominio chiamano ora
`formatCurrency` **col suo nome**, come gli altri cinquantanove del progetto:
⛔ l'alias `as euro` è stato scartato perché sarebbe stata la stessa convenzione
riscritta a mano in otto file, cioè il difetto che si stava togliendo.

🔵 **Debito dichiarato, non toccato**: restano **133** `|| '—'` a mano nei
template su campi **non** valutari (IBAN, descrizioni, utenti). Quelli
`formatCurrency` non li copre, ed è un cantiere suo.

#### ⚠️ Due presidi aggiunti a `SaldoPanel` rileggendolo

| | Difetto | Perché contava |
| --- | --- | --- |
| **1** | `mostra` accettava **qualunque** stringa | Un nome sbagliato non dà errore: dà **una riga in meno** — un numero che sparisce da un pannello di saldi senza che niente lo dica. Ora c'è `CAMPI_SALDO` esportato da `useSaldi` (accanto a `LIVELLO`, che era già lì) e un `validator` |
| **2** | Il livello si legge **una volta** al montaggio — scritto in un commento del composable, presidiato da nessuno | Chi legasse `:livello` a una variabile senza `:key` vedrebbe il saldo di **un'altra cosa** sotto l'etichetta giusta, in silenzio. Ora il pannello si **spegne** e lo dichiara |

> 🔴 **E un difetto introdotto e corretto nello stesso giro**: il default di
> `mostra` era diventato `[CAMPI_SALDO[0], CAMPI_SALDO[1]]`, cioè legato
> all'**ordine** di una lista che il commento accanto dichiara intoccabile — un
> riordino avrebbe cambiato in silenzio quali numeri si accendono. Rimessi i due
> nomi per esteso: *la lista presidia i nomi, non li sostituisce.*

---

### 10.7 🔴 Che cosa NON è stato fatto, e perché

| Non fatto | Perché |
| --- | --- |
| ~~**Tutto il frontend**~~ | ✅ **FATTO (28/08).** Fondamenta + quattro liste · il giro della distinta operativo (apertura col form, righe master-detail, transizioni di stato, abbinamento con la forzatura a due tempi, registrazione con anteprima) · **canali di incasso** (elenco + drawer) · **sistemazioni** (drawer decisione + dialogo conferma). ✅ **E la correzione guidata (Q-7) è arrivata anch'essa il 28/08**: madre consegnata dal team DB, rotta `POST /distinte/{id}/correggi/`, dialogo e legame fra i due documenti. ⭐ **Non resta niente da costruire** |
| ~~I **seed delle liste**~~ | ✅ **CONSEGNATI dal team DB il 27/08**: 4 definizioni, 53 colonne, 4 preset, 53 chiavi i18n già nei locales |
| ~~L'**azione di processo** `registra_distinta`~~ | ✅ **CONSEGNATA il 25/08.** ⚠️ **Ma il cancello resta chiuso finché non è ASSEGNATA a un profilo**: il seed la crea, non la concede — senza assegnazione registra solo il super admin. È una cosa da fare in-app, non in codice |
| Il verbo **`POST /righe/{id}/abbina/`** | È la slice 3 e porta con sé la rata, la capienza e la forzatura a due tempi. Va scritto **con** l'`ui_action` `confirm_and_retry` (Q-1), o il rifiuto confermabile arriva al frontend come un muro |
| La **base dei saldi** (§2.7) | Slice 3. ⚠️ Nasce come **modulo unico** con tre livelli in testa, non come pannello della fattura: è il vincolo, non una rifinitura |
| ~~`E_PAGAMENTI_VALIDAZIONE`~~ | ✅ **ARRIVATO il 25/08**, e si chiama **`E_PAGAMENTI_VALIDATION`**: il catalogo ha due convenzioni vive e si è scelta la maggioranza (17 contro 13). La riga è già cambiata nel service |

---

### 10.12 ⭐ Il seguito del primo collaudo — D16 · D17 · D18 *(2026-09-14, sera)*

> Il piano sta nel brief DB
> ([§10](brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md)), per
> decisione di Tid; qui il consuntivo, come per le slice precedenti. Scritto
> su «procedi»: Q-A (estrazione) **sì**, Q-D (FE-9) **strada B**, le altre
> cinque come proposte.

| Lato | Cosa esiste adesso | Dove |
| --- | --- | --- |
| **BE** | `crea_riga` accetta la destinazione e sceglie lo stato di nascita dalla **presenza della fattura** (`ABBINATA` / `DA_ABBINARE`), **un `INSERT`**; il cliente assente si **legge** dalla fattura; una lettura sola della destinazione per `crea` e `abbina` (`_destinazione_da_payload`, con le regole «motivo solo con forzatura» e «rata/cliente/forzatura pretendono una fattura») | `pagamenti_service.py` |
| **BE** | `DELETE /righe/{id}/` → `elimina_riga` → `UPDATE … SET attivo = false WHERE attivo IS TRUE`; `Idempotency-Key`; 404 no-leak su riga assente o già eliminata. 🔴 **E `get_riga` filtra `attivo`**: prima di D17 nessun verbo poteva produrre una riga inattiva dall'app, e dopo l'avrebbe potuta modificare, abbinare, cambiare di stato — invisibile in ogni lista | `views.py` · `pagamenti_service.py` · `pagamenti_repository.py` |
| **BE** | Le **quattro** colonne del verbo «elimina» sul frammento di riga condiviso (dettaglio, righe della distinta, coda): `elimina_blocco_reason` · `_reason_key` · `_dettaglio` (jsonb decodificato) · `can_eliminare`, dalla `LATERAL` sul primo motivo di `script.fn_check_riga_contabile_eliminabile`. ⚠️ Misurato con `EXPLAIN` sotto contesto operatore: nella coda la `Function Scan` sta **sotto la `WindowAgg`** (per riga filtrata, non per pagina), accanto ai predicati RLS che già girano per riga — stessa specie di costo, e si è scelto di pagarlo per tenere **un** frammento. Se peserà, «pagina prima, motivo dopo» | `_RIGA_COLONNE` / `_RIGA_FROM` |
| **BE** | `transizioni.{distinta, riga}` nel dettaglio, dalle **due matrici** (`list_transizioni`, una `UNION ALL`, stati ritirati esclusi) ristrette ai richiedibili sull'**arrivo**; `stati_richiedibili` **esce** dal contratto. `contenuto_modificabile` (`BOZZA` ∧ `MANUALE`, copia dichiarata). `stato_info_key` da `st.meta ->> 'nessuna_azione_key'` | `get_distinta` |
| **BE · test** | **+25 a mock** (`test_riga_nasce_abbinata_ed_elimina.py`: nascita, quattro rifiuti 400, BA derivato, primo tentativo non forzato, il service non nomina la capienza nemmeno alla nascita, eliminazione, `contenuto_modificabile` su cinque combinazioni, transizioni), **+3 API** (DELETE senza/con chiave, POST con destinazione), **+11 sul DB provvisto** (`test_riga_elimina_e_transizioni_db.py`: le colonne dal cursore a zero righe, l'arità della check, `EXPLAIN` dell'INSERT e dell'UPDATE, ogni ordinamento della coda con la LATERAL, le matrici, **ogni richiedibile raggiungibile**, il difetto del collaudo contro la matrice vera). Suite `pagamenti` + presidi trasversali: **217 verdi** | `apps/pagamenti/tests/` |
| **FE** | ⭐ **`RataSelect.vue`** estratto in `pagamenti/components/` (Q-A): rate col saldo, tre stati, «facoltativa», residuo negativo a parole; emette la rata **intera**. Adottato da `AbbinaRigaDialog` e dal form. Le chiavi i18n passano da `pagamenti.abbina.rata_*` a `pagamenti.rata.*` | `RataSelect.vue` |
| **FE** | `DistintaRigaForm` in creazione **parte dal documento**: `FatturaLookup` → `RataSelect` → **importo proposto** (residuo della rata; senza rata, del documento via `useSaldi`, la base unica) sovrascritto solo se vuoto o ancora proposto → fatti. Toggle **«Non riesco ad associarlo»** (spegne lookup e rata, la riga nasce `DA_ABBINARE`); Salva spento finché non c'è una fattura **o** l'interruttore. Forzatura a due tempi con `useForzaturaConfermata` (che ora espone anche `campiErrati`: un secondo handler non vedrebbe i campi del 400). In modifica: soli fatti (R-6) — e dal 15/09 lo stesso doppio tempo, con `extra` passato ad `aggiornaRiga` (Q-H) | `DistintaRigaForm.vue` · `useForzaturaConfermata.js` |
| **FE** | **«Elimina»** nel kebab: `MANAGE_ICONS.DELETE`, rossa, conferma con importo e riferimento, `disabled` + `tooltip` da `bloccoMotivo` (prefisso `elimina_blocco`, flag `can_eliminare`) — nessun `if stato` nel drawer. `SCARTATA` prende `pi pi-ban` (letterale, un lettore solo). Le voci «Porta a …» — testata e riga — da `transizioni.<x>[stato]`; `modificabile` da `contenuto_modificabile`; sotto `VALIDATA` un `Message` dice che il contenuto è fermo e che abbinare/sospendere si può | `DistintaDrawer.vue` |
| **FE** | `:info-key="distinta?.stato_info_key"` sulla `DrawerActionsBar` + cinque `pagamenti.distinte.stato_info.*` in `it`/`en` (la frase compare all'apply di **P-8**); `pagamenti.righe.{elimina, conferma_elimina, eliminata, non_identificata, non_identificata_aiuto}`, `pagamenti.distinte.contenuto_fermo`. Commento sopra l'import di `DataTable` (eccezione dichiarata, debito verso `RigheMasterDetailTable`) | locales · drawer |
| **Docs** | `api_pagamenti.md` (rotte, dettaglio, POST righe, `DELETE`, due codici); copione di collaudo §2.6–2.9, §3.1–3.3, §4.0 riscritti (brief DB §7) | `docs/it/backend/pagamenti/manual/` · `collaudo-…md` |
| 📮 **Al DB** | **P-8** seed `meta.nessuna_azione_key` sui cinque stati (righe esatte nel brief DB §4) · **P-9** doc auto-gen | brief DB §4 |

⚠️ **Quattro cose viste scrivendo, per chi arriva dopo.** (0) 🔴 Il presidio
trasversale `test_idempotency_key_contratto_fe_be` ha accusato **sei rotte di
`vendite`** per il `DELETE` nuovo di `pagamenti`: chiavava le view sul solo
**nome di classe** (`ApiRigaDetail` esiste in sette app) e confrontava i
percorsi **sulla coda** relativa al mount (`righe/{}`), quindi ogni
`…/righe/{}` di vendite ci finiva dentro. Corretto **il presidio**, non il
nome della view: chiave `(app, classe)` e prefisso di montaggio risolto a
catena dagli `include()` della radice. Provato al rovescio — senza `idem()`
accusa **solo** `pagamenti/righe/{}`. (1) `abbina_riga` non
pretende più `billing_account_id`: lo **legge dalla fattura** se manca, come
alla nascita — una regola sola per i due verbi, e il test
`test_fattura_e_cliente_obbligatori` è diventato
`test_fattura_obbligatoria_cliente_derivato`. (2) Il test statico «il backend
non decide la capienza» vale ora anche su `crea_riga` e sul lettore della
destinazione. (3) Nessun test asserisce che `stato_info_key` sia `NULL`:
sarebbe il test di §10.10, quello che tiene fuori il dato il giorno che arriva.

---

## 11. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| **2026-09-14** (sera, dopo) | ✅ **D16 · D17 · D18 SCRITTI in BE e FE** (su «procedi» di Tid; Q-A estrazione sì, Q-D strada B). BE: la riga nasce con la destinazione in un `INSERT` (stato dalla presenza della fattura, BA letto dal documento), `DELETE /righe/{id}/`, le quattro colonne `elimina_blocco_*` in LATERAL (EXPLAIN: per riga filtrata, come i predicati RLS — resta), `transizioni` dalle matrici al posto di `stati_richiedibili`, `contenuto_modificabile`, `stato_info_key`; 🔴 **`get_riga` filtra `attivo`** — il buco che D17 apriva. FE: `RataSelect` estratto, form documento-first con importo proposto e l'eccezione dichiarata, «Elimina» col motivo dal DB, `SCARTATA` senza cestino, transizioni e `modificabile` dal dettaglio, `:info-key`. **217** test verdi (39 nuovi, 11 sul DB provvisto), build/lint/i18n verdi. Copione riscritto. 📮 P-8 (seed) e P-9 (doc) al DB. Consuntivo in **§10.12**. Nessun commit |
| **2026-09-14** (sera) | 📋 **Il piano BE/FE di D16/D17/D18 sta nel brief DB, non qui** — per decisione di Tid: [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md](brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md) **§10** (terreno misurato sul codice, tre correzioni a §5/§6 di quel brief, slice A/B/C, prerequisiti P-8/P-9, decisioni aperte). La riga qui sotto diceva *«il piano lo scrive questo documento»*: vale per il **consuntivo**, che quando si costruirà andrà in §10 di questo file. Nessun codice scritto |
| **2026-09-14** | 📮 **Tre richieste dal primo collaudo in-app** (Tid, prima contabile caricata), scritte dal team DB in [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md](brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md) — decisioni **D16/D17/D18** nel brief madre §2-bis. **Qui solo l'elenco** (§5 BE, §6 FE di quel brief): il piano lo scrive questo documento. In una riga: la riga manuale **nasce abbinata** (lookup fattura → rate col saldo → importo proposto; «non identificato» è l'eccezione dichiarata — R-6 resta per la sola modifica); nasce il verbo **elimina riga** (`DELETE /righe/{id}/` → `attivo=false`, motivo di blocco in colonna dalla check DB; il cestino smette di stare su `SCARTATA`); le transizioni offerte si derivano **dalla matrice** e non dal solo vocabolario (oggi `SCARTATA` è proposta su `ABBINATA` e rifiutata). 🔴 Il copione di collaudo **salta «Porta a VALIDATA»** prima di «Registra» (§4.1) e fallirebbe per costruzione: righe da riscrivere in §7 di quel brief |
| **2026-08-29** (rilettura critica della base dei saldi) | 🔴 **UNA RICHIESTA ESAUDITA E MAI RACCOLTA, E UN TEST CHE LA TENEVA FUORI.** Costruendo sopra A-8 e' venuto fuori che `pagamenti.fn_get_saldo_fattura` risponde **quattro** colonne dal **25/08** — e' **DB-10**, la richiesta che questo cantiere aveva fatto (Q-10) e ottenuto — mentre il backend ne leggeva **due**, buttava via l'`incassato` e prendeva `in_lavorazione` da una **seconda funzione** invece che da quella. Sopra c'era un commento che diceva *«il database ne da' due»*, falso da quattro giorni. 🔴 **E il pezzo che vale piu' della correzione e' il test**: `test_sul_documento_incassato_e_none` era **verde** e difendeva il buco, perche' asseriva un'ASSENZA — cioe' l'ipotesi sotto cui era stato scritto, non il sistema. *Un test che asserisce che un numero non c'e' lo tiene fuori anche il giorno in cui arriva.* ⚠️ Stessa specie del `test_canale_inesistente_404` di §6-bis: **un test che verifica la propria ipotesi**. **Corretto**: repository, service, test riscritto piu' uno nuovo che asserisce che documento e rata hanno la **stessa forma** — il presidio che mancava al vincolo §2.7. ⭐ **Difetto figlio, trovato rileggendo la correzione appena scritta**: avevo tenuto il `CROSS JOIN` «per una ragione sola, `has_righe_postabili`» — ragione **scritta e non verificata**: quella colonna non la legge nessuno, quindi il join faceva girare a ogni apertura del drawer una funzione che `fn_get_saldo_fattura` chiama gia' al suo interno, e che **non e' STABLE** (due valutazioni = due letture indipendenti, la trappola gia' pagata sul guard del fondo). Ora e' una `SELECT` su una funzione sola, provata con `EXPLAIN` sul database vero: *function scan* invece di *nested loop*. 📌 *Giustificare una cosa in un commento non e' verificarla — bastava un `grep`.* ⭐ **Lato FE non e' servito niente**, e non per caso: `SaldoPanel` gia' gestiva `incassato == null` a parole invece che con un trattino. Il ramo non si accende piu' sul documento e **resta**, perche' e' la risposta a un caso che il modello ammette (il livello CLIENTE) — *un presidio non si toglie perche' oggi il suo ramo e' irraggiungibile*. ✅ **E il terzo livello ha perso il suo ostacolo**: il saldo cliente aspettava proprio quell'`incassato`. ⭐ **Autorizzato da Tid**: `formatCurrency` ha `placeholder: '—'` come **default** (raggio dichiarato: 58 chiamanti su 67 si appoggiavano alla stringa vuota, `CellaConfigurabile` compresa) e **`pagamenti/formato.js` e' stato cancellato** — esisteva per una riga che il default rende inutile; gli otto componenti chiamano `formatCurrency` col suo nome, ⛔ non con un alias `as euro` riscritto a mano in otto file. `formatNumber` **non** toccato: una quantita' assente non e' per forza «non si applica». 🔵 Debito dichiarato: restano **133** `|| '—'` a mano su campi non valutari. ⚠️ **Due presidi aggiunti a `SaldoPanel`**: `CAMPI_SALDO` esportato + `validator` su `mostra` (un nome sbagliato non dava errore, dava **una riga in meno**), e il **livello divergente** che spegne il pannello invece di mostrare il saldo di un'altra cosa sotto l'etichetta giusta. 🔴 **E un difetto introdotto e corretto nello stesso giro**: il default di `mostra` era finito a `[CAMPI_SALDO[0], CAMPI_SALDO[1]]`, legato all'**ordine** di una lista dichiarata intoccabile. Verdi: **145 test** `pagamenti` · eslint · build · `EXPLAIN` sul DB vero |
| **2026-08-29** (A-8 · la base dei saldi) | ⭐ **L'ULTIMO PEZZO, E NON E' UN PANNELLO.** Il vincolo §2.7 diceva di costruire **la base**, non «il saldo della fattura»: nascono `useSaldi` e `SaldoPanel` in `core/`, con **tre livelli in testa** — documento, rata, cliente — e il terzo **dichiarato e non acceso**, perché accenderlo oggi significherebbe sommare un `incassato` che a livello documento il database non dà. ⭐ **Q-6 in due numeri e non tre**: residuo in grande, «in lavorazione» in piccolo **e solo quando c'è** (né `null` né zero). L'«incassato» il pannello lo sa mostrare — è la stessa base — ma questa schermata non lo accende. ⛔ **Quattro casi e non uno**: non letto · livello non pronto · **letto e senza nessun movimento** · letto coi numeri. Il terzo è quello che si confonde col residuo pieno, e la prova sul database vero lo ha trovato **subito**: le due fatture misurate hanno `residuo = totale` con `has_movimenti = false` — senza quella riga «nessuno ha ancora pagato niente» e «ha pagato e manca tutto» si leggono uguali. ⚠️ E il **dislivello** è confermato dalla misura: al documento `incassato` arriva `null`, alla rata arriva `0`. ⛔ Non si somma per riempirlo — `null` vuol dire «non si sa», e il pannello lo dice a parole invece di mostrare un trattino che si legge come zero. 🔵 Stili **propri** e non `app-dash-stat-n` presa in prestito (nasce per le card della lente Competenza), i18n sotto la radice `core` che esiste già invece di una quarta radice in cima. 📮 Seconda occorrenza di `formatCurrency(v, { placeholder: '—' })`: la sede naturale sarebbe un default in `formatCurrency`, **dichiarato e non fatto di mia iniziativa** — cambia il ripiego di tutto il progetto |
| **2026-08-28** (S6 — la correzione guidata) | ⭐ **IL CANTIERE È CHIUSO IN CODICE.** Il team DB ha consegnato entrambe le richieste **lo stesso giorno**, e due delle loro risposte hanno **smentito me**: (1) ⛔ la policy che avevo proposto avrebbe reso `enti_incasso` **non scrivibile** — la `WITH CHECK` cercava il legame che l'`INSERT` stesso stava scrivendo. L'hanno riscritta passando dal **conto**, che è la forma che avevo segnalato come necessaria ma non applicata alla mia stessa proposta; (2) 🔴 su **C-1** avevano risposto «già abbinata, il guard la regge» e **la prova li ha smentiti**: su una rata saldata dal movimento che si sta correggendo non c'è capienza in nessuna direzione (`R = 0` non è spazio nemmeno in negativo). ⭐ La misura ha trovato una **quarta strada** che nessuno dei due aveva visto — righe con fattura e rata **compilate** ma in `DA_ABBINARE`: la correzione guida tutto tranne l'ultimo clic, e il doppio tempo resta il gesto di una persona. **Decide Tid.** **Scritto**: `crea_distinta_correzione` nel repository (una sola `SELECT`), `correggi_distinta` nel service, `POST /distinte/{id}/correggi/` col **cancello della registrazione** — un gesto che rovescia denaro non può avere una porta più larga di quello che lo ha scritto — dialogo `CorreggiDistintaDialog`, e il **legame nei due versi** in testata al drawer, cliccabile. ⭐ Il legame è la metà che si vede: senza, due documenti gemelli di segno opposto stanno nell'elenco **senza niente che dica che uno rovescia l'altro**. ⚠️ `NULLA_DA_CORREGGERE` risale **intatto**, come `NULLA_DA_POSTARE`: è un esito, non un errore. E le **righe saltate** si annunciano — una riga non postata non ha niente da rovesciare, ma il silenzio lascia l'operatore a chiedersi dove sia finita. 🔵 Rigenerate le policy (**803 voci**) e scritti i due ripieghi **senza `%s`**. ⚠️ Un terzo codice del cantiere offerte (`E_OFFERTA_RIENTRO_CON_REVISIONE_VIVA`) è a catalogo **senza ripiego**: non è mio e non ne invento la frase — segnalato. Verdi: build · eslint · guard i18n · **4166 test** (con i test DB accesi) |
| **2026-08-28** (E-4 · perimetro) | 🔴 **DUE BUCHI DI PERIMETRO, E UNO È DEL MODELLO.** Eseguito il passo E-4 con due operatori veri di due emittenti diversi. (1) ⛔ **`pagamenti.enti_incasso` non ha row security**: la riga di §2.6 che diceva «le dodici tabelle hanno la RLS accesa» è **falsa** — sono **quattro su dodici** — e la tabella scoperta è proprio quella che porta il conto su cui atterra il denaro. L'elenco dei canali, **IBAN compreso**, è comune a tutti gli emittenti. È una policy: chiesta al team DB. (2) ⛔ **`GET /conti-incasso/` usciva dal perimetro**: l'operatore dell'emittente 32 leggeva l'IBAN di incasso dell'emittente 44 passandone il soggetto. **Chiuso lo stesso giorno** — `E_SCOPE_EMITTENTE` (403, già a catalogo), cancello nel **repository** accanto all'SQL e non nel service (il service lo salterebbe il secondo chiamante), test sul DB provvisto **provato rimettendo il difetto**. ⭐ **Perché un conteggio non l'avrebbe trovato**: le tabelle sono vuote, quindi tutti e tre i contesti danno zero — verde per sottrazione. Le prove che hanno morso sono una **misura strutturale** (`relrowsecurity` tabella per tabella) e una **comportamentale** su due emittenti veri. ⚠️ E due trappole pagate scrivendo il rimedio: `fn_check_user_emittente_scope` risponde **true** su utente NULL («job batch»), quindi senza GUC il perimetro si **apre**; e la GUC si chiama `app.current_user_id`, non `app.auth_user_id` — col nome sbagliato il cancello rifiutava tutti **coi test verdi**, perché un doppio non ha un perimetro. 📮 Scritto [brief-db-perimetro-canali-e-correzione-guidata.md](../work-done/brief-db-perimetro-canali-e-correzione-guidata.md): §1 la policy mancante con tre domande, §2 la madre della **correzione guidata** (Q-7) con quattro domande di modello. Verdi: **4142 test** |
| **2026-08-28** (rilettura critica del frontend) | 🔴 **DUE DIFETTI CHE NESSUN TEST CHIEDEVA, E DUE ESTRAZIONI.** (1) ⛔ **Gli stati della riga erano CABLATI**, contro la regola del cantiere: `finale = stato_codice === 'POSTATA'` — ma `STORNATA` e' anch'esso terminale a catalogo, quindi su una riga stornata il drawer offriva abbinamento e transizioni **che il database rifiuta**. Ora `is_final` si legge dal catalogo, e le transizioni si **generano** da `stati_richiedibili.riga` × catalogo: cade il codice cablato **e** ricompare una transizione che il contratto dichiara ammessa e che l'interfaccia non offriva — il ritorno a `DA_ABBINARE`, cioe' l'unico modo di sganciare un abbinamento sbagliato. (2) ⛔ Il rosso della conferma era `codice === 'SCARTATA'`: il **modello dice il contrario** — a catalogo `SCARTATA` ha `is_final = false`, quindi quel rosso allarmava per un gesto reversibile. Adesso il rosso e' `is_final`, in tutte e due le sedi. (3) ⛔ L'anteprima di registrazione era in `silent`: una lettura fallita si leggeva come «non c'e' niente da registrare» — un'affermazione, e falsa, sul foglio che sta per essere chiuso. ⭐ **Estratto `useLetturaTreStati`** in `core/composables/`: il terzetto «c'e' · e' vuoto · non l'ho letto» era riscritto a mano in **quattro** punti, e in **tre** me l'ero dimenticato alla prima stesura — un difetto che si ripete tre volte su quattro non e' una distrazione, e' una cosa che il codice deve dare per costruzione. ⭐ **Estratti `pagamenti/etichette.js`** (la stessa riga `labelOrCode` in **otto** componenti, tre prefissi duplicati) e **`useCanaliIncasso`** (stessa pagina, stesso filtro, stesso terzetto, in due dialoghi). Entrambi **fabbriche**, non oggetti condivisi: un oggetto gia' costruito legherebbe tutti al `t` del primo montato, e al cambio lingua il secondo consumatore resterebbe indietro in silenzio. 🔵 Minori: le opzioni delle code si derivano dalle **rotte** invece che da un elenco a mano; l'errore del lookup emittenti si dice; il motivo di una voce disabilitata distingue «riga gia' registrata» da «foglio chiuso»; niente kebab a zero voci; `page_size: 200` non e' piu' un numero sparso. ⚠️ E la verifica che valeva di piu': **tutti e 17 i codici d'errore** che le due schermate nuove possono far scattare sono **a catalogo e col ripiego** — nessuno diventa un 500. Verdi: build · eslint · guard i18n · **970 test** su `pagamenti` e `core` |
| **2026-08-28** (frontend — canali di incasso e sistemazioni) | ⭐ **LE DUE SCHERMATE CHE MANCAVANO, E IL FRONTEND DEL CANTIERE È COMPLETO** (S4 · S5). **Canali**: elenco + drawer di configurazione. ⛔ Tabella **semplice** e non `<ListaConfigurabile>`, e non è una scorciatoia — `pagamenti.enti_incasso` **non ha un seed** in `ui.lista_definizione` (verificato sul DB: le liste seminate del dominio sono quattro), e montarla sul BB avrebbe mandato al backend il `campo_sorgente` di colonne mai dichiarate: **400 al click sull'intestazione**, lo stesso difetto già pagato sulle altre quattro. ⛔ **La trappola dei due `soggetto_ruolo_id`**: quello scelto in cima al form è l'**emittente** e serve SOLO a filtrare i conti — sul canale non esiste e non viaggia nel payload; `soggetto_ruolo_id` sul canale è il soggetto **PSP**. **Sistemazioni**: drawer decisione (tre destinazioni, il destinatario solo dove il denaro va da qualche parte) + dialogo conferma che chiede il **canale solo sul RIMBORSO**. ⭐ Dopo una conferma il drawer **si chiude**: il denaro si è mosso e l'eccedenza in testata è vecchia — tenerla a video mostrerebbe un numero falso accanto ai pulsanti per decidere di nuovo. ⭐ **Estratto `FatturaLookup.vue`** in `core/` alla seconda occorrenza (regola del 2, primo dei quattro candidati di §5.3): abbinamento riga e sistemazione fanno la stessa domanda. 🔵 **BE**: `_ENTE_INCASSO_SELECT` porta ora **filiale e soggetto PSP in chiaro** — senza, il drawer mostrava un campo vuoto accanto a un id valorizzato, cioè «nessuna filiale» su un canale BANCA dove è obbligatoria. Misurato con EXPLAIN: **9,91 → 18,56**, nessuna esplosione come quella di BE-11. 🔴 **Tre difetti trovati rileggendo, e due erano del giro precedente**: (1) un `onActivated` che ricarica in **quattro** liste — `useSearchTable` lo fa già, quindi erano **due richieste identiche** a ogni rientro nella scheda, con le risposte che possono tornare in ordine inverso; (2) il conto del canale **azzerato in silenzio** all'apertura in modifica, per una corsa fra il caricamento dei conti e quello del dettaglio; (3) il kebab che si disegna anche con **zero azioni**. Verdi: build · eslint · guard i18n · **4139 test BE** |
| **2026-08-28** (frontend — i verbi della distinta) | ⭐ **IL GIRO DELLA DISTINTA È OPERATIVO**: si apre col form (Q-3), si digitano le righe, si abbinano alla rata e si registra. ⭐ **Nasce `useForzaturaConfermata`** (§5.3), e nasce **building block davvero**: astrae un COMPORTAMENTO — l'`ui_action` `confirm_and_retry` — e resta **cieco ai codici**, com'era la ragione di Q-1. ⚠️ È il **primo consumatore di `azioneUi`** in tutto il prodotto: fino a ieri il campo era emesso, trasportato e non letto da nessuno. ⭐ Per farlo funzionare `useApiHandler` guadagna due cose additive: **`messaggioErrore`** (la frase del database, che sul rifiuto di capienza porta già i numeri e va dentro la richiesta di conferma) e **`azioniGestite`** — ⛔ e NON si è usato `silent`, che avrebbe spento il toast per *qualunque* errore e costretto il chiamante a ri-decidere fra errore di sistema, gesto e toast normale: cioè a riscrivere altrove l'unica sede di quella scelta. 🔴 **Il primo tentativo si manda SEMPRE senza forzatura**: forzare al primo colpo nasconde invece di registrare, e il `forzata` resta scritto sulla riga — è quello che l'elenco delle rate fuori capienza legge per esistere. ⭐ **Gli stati non sono cablati**: le transizioni si costruiscono incrociando `stati_richiedibili` col catalogo che il dettaglio già porta, e la modificabilità viene da `stato_is_final` — dedurla dal nome («CHIUSA») sarebbe una seconda copia della regola. **Tre difetti miei corretti alla rilettura**: due liste caricate in `silent` che, fallendo, avrebbero detto «nessun canale configurato» e «questa fattura non ha rate» — affermazioni, e false (ora «vuoto» e «non lo so» sono casi distinti, tre e non due); e la creazione della distinta anch'essa `silent`, che sui guard del database avrebbe lasciato la finestra aperta senza dire perché. ⚠️ Trovato di rimbalzo: `class="w-full"` è usata in una ventina di componenti del progetto ed è **definita in nessun CSS** — non l'ho propagata (i campi si stirano da `.form-field`). ✅ Build e lint puliti, i18n verde, suite backend **4139**. 📮 Il cancello `registra_distinta` è a catalogo ma **non ancora assegnato a un profilo**: finché non lo è, registra solo il super admin |
| **2026-08-28** (controllo critico del codice appena scritto) | 🔴 **UN DIFETTO CHE AVREBBE DATO 400 SU UN GESTO NORMALE, e l'ha trovato un presidio, non una rilettura.** Le quattro whitelist di ordinamento erano chiavate sul **`codice` logico** del seed — perché così diceva il brief con cui il team DB le ha generate, e così era stato verificato: codice contro chiave, in entrambi i versi, tutto combaciante. ⛔ **Ma il confronto era fra le cose sbagliate**: `<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`, quindi al click PrimeVue manda il **nome fisico**. Le **sette** colonne in cui i due nomi divergono — `stato`, `centro`, `distinta`, `fattura` (×2), `cliente` — avrebbero risposto **400**. È lo stesso difetto pagato su `vendite.lotti` il 2026-07-31, e a scoprirlo è stato `test_registro_copre_tutte_le_liste_montate_dal_frontend`, andato rosso da solo appena le liste sono state montate. 📌 *Una verifica accurata sulla coppia sbagliata è indistinguibile da nessuna verifica.* ✅ Whitelist riscritte sul campo fisico e le quattro liste **registrate in `_LISTE`** (il debito `_DEBITO_WHITELIST_LOGICA` è a zero: dovevano essere in regola, non condonate). ⭐ E il guardrail del cantiere è stato **esteso a provare OGNI ordinamento dichiarato** — 20 colonne × 2 versi — perché il presidio trasversale confronta due *elenchi* e non fa partire l'SQL: là un nome non riconosciuto è un 400, qui una colonna che l'SQL non ha è un **500**, ed è già successo su questa coda il 24/08. **Altri sei rilievi corretti**: l'`origine` della distinta si risolveva con `t()` diretto e a video sarebbe finito il **path della chiave** (ora `labelOrCode`, come gli altri vocabolari) · il selettore di coda cambiava lo **store** mentre la rotta restava l'altra — tab che mentiva, deep-link che non descriveva più la pagina (ora **naviga**: la rotta è l'unica verità) · le tre liste avevano la freschezza solo in `onMounted`, cioè **dati fermi al rientro nella scheda** sotto KeepAlive (aggiunto `onActivated` idempotente, che non riavvolge la pagina) · `pagamenti` era ancora fra i domini **senza rotte**, quindi `/pagamenti` avrebbe renderizzato un placeholder · `limit: 25` cablato in quattro store (ora `PAGINATION.DEFAULT_ROWS`) e `euro` in quattro file (ora uno) · i vocabolari chiusi sparsi in sei punti, router compreso (ora `pagamenti/vocabolari.js`, senza pinia perché lo legge anche il router). ✅ **Verificato che i tre JOIN di BE-11 non moltiplicano le righe** (4 = 4 sul dato vero) — è il difetto che aveva già colpito la lista distinte coi lotti. ✅ Suite **4139 verdi**, `pagamenti` **131**, build e lint puliti, i 3 rilievi oxlint residui sono preesistenti (identici con il lavoro stashato) |
| **2026-08-28** (frontend — fondamenta e le quattro liste) | 🟡 **IL FRONTEND ESISTE**, in sola lettura. Client API delle 23 rotte · quattro store `userScoped` · le **quattro liste** su `<ListaConfigurabile>` coi codici del seed (`pagamenti.distinte` · `pagamenti.righe` · `pagamenti.rate_fuori_capienza` · `pagamenti.eccedenze`) · cinque voci di menu, cinque rotte · **35 chiavi i18n per lingua** · il **drawer della distinta** in consultazione (testata, quadratura, righe). ✅ Build verde, `oxlint` e `eslint` puliti, `check_i18n_keys.py` e `check_license.py` verdi, **zero chiavi i18n perse** (4132 → 4167 per lingua, verificato contro HEAD). ⭐ **Nessun verbo montato, ed è una scelta**: un pulsante che non fa niente sembra presidiato — è la stessa specie del campo `action` che `RowActionsMenu` ignorava fino al 17/08. ⭐ **Le due porte della coda sono DUE ROTTE e una vista** (`meta.coda`), non uno stato interno: così sono deep-linkabili e il tab del browser ricorda quale si stava lavorando; il ripiego è `DA_ABBINARE` e non «tutte», perché una coda che mostra anche il lavorato smette di essere una coda. ⚠️ **Tre decisioni di resa che il modello impone**: lo **scarto** `null` non è zero (non è stato dichiarato niente ⇒ la quadratura *non si applica*, e mostrare 0,00 direbbe «quadra» di una distinta mai quadrata — tre esiti, non due); il **residuo negativo** delle rate fuori capienza si legge «120,00 di troppo» e mai «-120,00», che si legge come un guasto; la **utility del conto** `null` è «nessuna utility», non un campo vuoto. ⚠️ E la conversione `limit/offset → page/page_size` sta in **un punto solo** del dominio invece che nei quattro store: 📮 è la **terza sede** nel progetto (`vendite` ne ha due) ed è un candidato alla promozione in `core/` — dichiarato, non fatto di mia iniziativa. 📮 **Restano i verbi** e le due schermate di sistemazioni e canali |
| **2026-08-28** (rientro al backend + DATO-1) | ✅ **IL CANTIERE NON HA PIÙ PREREQUISITI: resta il frontend.** Chiusi i quattro punti che il team DB aveva rimandato qui (§6-bis) e **DATO-1** (§10.8). ⭐ **DATO-1 verificato sul database, non creduto**: i due IBAN di test sono ora a livello **RUOLO**, `IT00…0001` sul SR **72** (emittente 32) e `IT00…0002` sul SR **159** (emittente 44), entrambi non bloccati e con validità aperta — `conti-incasso?soggetto_ruolo_id=72` risponde **una riga** dove il 25/08 ne rispondeva **zero**. ⭐ E ciò che si sblocca è più di una schermata: prima **nessun canale era creabile** (il conto è obbligatorio su tutti i tipi), quindi il giro canale → distinta → righe → registrazione diventa esercitabile in-app. ⚠️ Resta un **residuo di dato** che non blocca: `IT00…0001` è rimasto **anche** a livello soggetto, sullo stesso soggetto — non viola il vincolo nuovo e i canali non lo leggono, ma è una seconda dichiarazione dello stesso fatto. 🔴 **Due difetti trovati mentre chiudevo, e nessuno dei due dava errore**: `test_canale_inesistente_404` **non provava il 404** — confrontava il codice con la costante che il codice stesso legge, quindi era verde anche quando il ripiego rispondeva 400 (il nome del test prometteva ciò che nessuna asserzione guardava); e la prima stesura del presidio sui `campo_sorgente` dichiarava «0 colonne esposte» su tutte e quattro le liste, che era un difetto **della misura** — le liste paginate passano da `fetch_paged_with_total`, non da `rows_to_list`. ⚠️ **BE-11 non passa dalla vista suggerita**: `vw_istanze_utilities_dettaglio` porta il nome della utility ma con sei join, due su viste di indirizzo che PostgreSQL non pota — misurato con EXPLAIN, **928.86 contro 6.10** per decodificare una parola; si usa la catena diretta, che è anche la forma già in uso in `BillingAccountRepository.search_lookup`. ⭐ **Un presidio nuovo che nessuno aveva chiesto ma che il `vista_sql = NULL` ci ha lasciato in mano**: tutti e **53** i `campo_sorgente` a catalogo esistono fra le colonne che le liste proiettano — verde oggi, e **provato rimettendo il difetto**. E le colonne **ordinabili** a catalogo combaciano con le whitelist del BE su tutte e quattro le liste, in entrambi i versi: un ordinamento dichiarato e non riconosciuto sarebbe un **400** su un gesto normale. ✅ Test **128 → 130**, policy riallineate al catalogo (`--check` verde), zero regressioni |
| **2026-08-27** (allineamento dal team DB) | ✅ **I TRE PREREQUISITI DB SONO CONSEGNATI E APPLICATI, e la palla torna qui.** I quattro **seed di lista** (53 colonne, 4 preset, **53 chiavi i18n gia' nei locales**), le due righe dell'**azione di processo** e `fn_get_saldo_fattura` allargata a **tre numeri** — piu' due cose che questo brief non chiedeva: il **404 dei canali** (`E_ENTE_INCASSO_NON_TROVATO`, che §10.8 dichiarava come ripiego) e la **seconda porta** del conto di incasso. ⚠️ **La bozza dei seed non e' mai partita da qui**: il team DB ha generato le 53 righe dal contratto del backend — `campo_sorgente` dai `SELECT` del repository e il **`codice`** di ogni colonna ordinabile uguale alla chiave della whitelist di ordinamento, cosi' che un ordinamento a catalogo non diventi un 400. ⭐ Tre scelte dichiarate: `sensibile = f` (e' un cancello, non un'etichetta), `multi_emittente = f` (una lista nuova nasce **non certificata**), `vista_sql = NULL` col costo che il guard DB sui `campo_sorgente` non gira. 🔴 **E due cose da sapere prima di ripartire**: il nome del codice di validazione e' **`E_PAGAMENTI_VALIDATION`** e non `_VALIDAZIONE` (§10.7 diceva l'altro), e il cancello della registrazione **resta chiuso** finche' l'azione non e' assegnata a un profilo — il seed la crea, non la concede. 📮 **Adesso tocca al backend**: rigenerare le policy, cambiare `E_ENTE_NON_TROVATO`, dichiarare `lista_codice` sulle quattro view, e **BE-11** — esporre `src.istanza_utility_id` dove si sceglie il conto, perche' chi configura un canale non vede se sta prendendo quello del gas o quello dell'energia. Dettaglio in **§6-bis**. ⛔ **DATO-1 resta aperto**: §10.8 vale parola per parola |
| **2026-08-24** (dato) | ✅ **DATO-1 risolto, e senza scrivere niente.** Era l'ultimo blocco del cantiere: nessuno dei due emittenti aveva un conto con `uso = 'INCASSO'`, quindi nessun canale di incasso era creabile. ⭐ **Non serviva nessuna colonna nuova** — la domanda era se aggiungerla ai parametri dell'emittente, e la risposta è no: il conto di incasso **non è un attributo**, è una **riga di relazione** in `anagrafiche.soggetti_ruoli_conti_bancari` con `uso = 'INCASSO'`, e il giro per crearla (endpoint + drawer + voce «Incasso» tradotta) **esisteva già tutto**. ⛔ Metterlo fra i parametri avrebbe creato una **seconda sede fuori dal vincolo** «un conto `INCASSO` appartiene a un solo soggetto» — che è esattamente la garanzia da cui il database ricava di chi sono i soldi arrivati prima della fattura: due emittenti avrebbero potuto dichiarare lo stesso conto senza che nessun errore lo dicesse. Tid l'ha configurato in-app con **due IBAN fittizi**, `IT00TESTINCASSO0000000001` e `…0002` — **due e non uno**, proprio per quel vincolo. ⚠️ Restano due avvertenze: il **perimetro è vero anche se il dato è finto** (i due IBAN sull'emittente sbagliato darebbero liste sbagliate **senza errore**), e in produzione servono quelli reali — ⛔ questi non devono viaggiare, e si riconoscono dal nome apposta. ℹ️ Il `CHECK` sull'IBAN è solo formale (`^[A-Z0-9]{15,34}$`, nessun checksum), quindi un valore di test passa |
| **2026-08-25** (slice 4) | ✅ **BACKEND DEL CANTIERE COMPLETO: anche i canali di incasso.** Tre rotte — elenco/creazione, dettaglio/modifica, e **l'elenco dei conti agganciabili** (BE-8). ⭐ Quest'ultimo e' il pezzo che conta: il database rifiuta un conto che non e' di incasso con un errore parlante, ma **un elenco che lo propone fa sbagliare**, e chi sbaglia se ne accorge dopo aver compilato tutto il resto. Il conto e' obbligatorio su **tutti** i tipi e non solo su BANCA (un canale POSTE o PSP senza conto e' lo stesso difetto travestito), mentre la **filiale** vale solo per la banca — due fatti diversi che si somigliano. ⚠️ E un elenco di conti VUOTO **si dichiara** (`nessun_conto_di_incasso`): e' la condizione voluta da D5, ma un menu vuoto senza spiegazione sembra un guasto dell'applicazione. 🔴 **Due difetti trovati scrivendo, prima di consegnare**: il codice 404 che avevo scelto **non esiste a catalogo** — e un codice non registrato non fallisce, diventa un **500** — quindi si usa il codice di dominio col ripiego dichiarato e si chiede quello giusto; e il nome di una FK era sbagliato nella mappa di traduzione (`fk_enti_incasso_centro` invece di `..._centro_riscossione`), cioe' un errore che sarebbe uscito col messaggio grezzo del database. ⛔ **E il blocco vero non e' il codice: e' il dato** (§10.8) — i due conti creati il 24/08 sono legati al livello sbagliato, e uno al soggetto sbagliato. ✅ Test **108 → 128**, i nove SQL nuovi provati con EXPLAIN, e il lookup **provato sui dati veri** con le tre risposte che ci si aspetta |
| **2026-08-25** (slice 5) | ✅ **Il giro delle sistemazioni, e con esso il BACKEND del cantiere e' completo tranne i canali di incasso.** Sei rotte: l'elenco delle eccedenze, la registrazione della decisione e i due verbi. ⭐ **Il backend qui fa MENO di quanto sembri**, ed e' il punto: registra un atto con un `INSERT` (una scrittura sola non ha bisogno di una madre) e chiama due funzioni madri — non sceglie la strada fra le tre destinazioni, non verifica l'eccedenza, non muove denaro. 🔴 **Cliente ed emittente si DERIVANO dalla fattura di origine e non si dichiarano**: il guard del database li verifica con un codice TECNICO apposta, perche' «non li sceglie una persona in un modulo, li deriva chi costruisce l'atto» — e il payload li rifiuta proprio per questo. ⚠️ **Registrare non e' eseguire**: l'atto nasce in bozza e il controllo dell'eccedenza sta alla CONFERMA, perche' fra decidere e confermare puo' arrivare un altro incasso — verificarla prima darebbe una garanzia che scade. E il **canale del rimborso** si chiede alla conferma, non alla registrazione. ⭐ L'elenco e' ordinato **per cliente** di default (D15-b) e il backend **non somma niente**: il raggruppamento la vista lo porta gia' in finestra. 📌 **Un presidio riscritto perche' dava un falso positivo**: cercava la parola «eccedenza» nel sorgente e si accendeva sul MESSAGGIO all'operatore — ora guarda le CHIAMATE, che e' cio' che voleva dire. ⭐ E due helper passati in una sede condivisa (`_helpers.py`) alla loro seconda occorrenza, invece di importare i nomi privati di un altro modulo. ✅ Test **86 → 108**, gli otto SQL nuovi provati con EXPLAIN sul database vero, le due madri NON chiamate (confermare muove denaro: si sono lette le firme). ⚠️ Le prove degli endpoint non hanno potuto girare in suite: un'altra sessione stava scrivendo BE-5 in `vendite` e l'URLconf del progetto era momentaneamente rotta da un import a meta' — le venti rotte del dominio sono state verificate con una URLconf isolata |
| **2026-08-24** (revisione 2) | 🔴 **Controllo critico della slice 3: sei difetti, e il primo lo trovava solo chi lo chiedeva.** ⭐ **Ordinare la coda per `distinta` produceva un 500**: il contratto dichiarava quella colonna ordinabile e il `SELECT` non la portava — un ordinamento finisce in una clausola SQL, quindi non era un valore sbagliato ma **una query che non parte**. ⚠️ E con essa cadeva la promessa scritta nel codice: una riga cross-distinta **senza il documento da cui viene non si lavora**. 📌 *Nessun test lo chiedeva — un ordinamento si prova solo chiedendolo, e i test ne provavano uno.* Rimedio: colonne e `FROM` separati (così la coda aggiunge le sue tre colonne) **e un presidio che verifica ogni colonna dichiarata ordinabile su tutte e tre le liste**, provato rimettendo il difetto per vederlo diventare rosso. ⚠️ **Secondo**: il saldo del documento erano **due letture separate**, cioè due istanti diversi — se una registrazione atterra in mezzo, il pannello mostra un residuo di prima accanto a un «in lavorazione» di dopo: **due numeri veri che insieme raccontano una cosa falsa**. Ora è una query sola. ⚠️ Poi: lo **scheletro della lista paginata scritto tre volte** (e la divergenza era già cominciata — il conteggio di ripiego stava solo sulla prima), **quattro letture senza il guard del canale di sistema** benché le funzioni di saldo siano `SECURITY INVOKER`, altri **codici cablati senza presidio** (gli stati delle due code, quello dell'abbinamento, i due motivi di «fuori capienza» — dove un refuso non dà errore, dà una lista vuota su elenchi che esistono per non far sparire del denaro), e **due tipi dichiarati e mai usati**. ✅ Test **78 → 86**, i 15 ordinamenti dichiarati provati con EXPLAIN sul database vero, zero regressioni |
| **2026-08-24** (slice 3) | ⭐ **L'INCASSO ARRIVA ALLA RATA anche dal backend.** Sei rotte nuove, e **nessuna aspettava niente dal team DB**: le colonne, i guard e la vista `vw_rate_fuori_capienza` c'erano dal 22/08, mancava la porta. ⭐ **Il verbo `abbina`** porta fattura, cliente e — facoltativa — la rata, in **un solo UPDATE**: dati e stato viaggiano insieme perché sono lo stesso gesto. 🔴 **E il doppio tempo della capienza passa di lì senza che il backend lo interpreti**: il primo tentativo arriva senza `forzata`, il guard rifiuta con la ragione e i numeri, la conferma torna come `forzata = true` e **resta scritta sulla riga**, che è ciò che l'elenco a valle legge. Un test statico verifica che il service **non nomini** capienza né saldo: se lo facesse, sarebbe una seconda sede della regola. ⭐ **Q-1 realizzata**: nasce `confirm_and_retry` in `error_ui_overrides.py`, con il suo paragrafo di motivazione — è una riga sola in un file di 176, quindi ha anche il suo presidio. ⭐ **Nasce la BASE DEI SALDI** (vincolo §2.7): un modulo solo legge le tre funzioni di saldo, forma unica `residuo · in_lavorazione · incassato`, **tre livelli in testa** — e il terzo, il cliente, è **dichiarato e non scritto**, perché sommare più documenti pretende l'`incassato` a livello documento che il database non dà ancora (DB-10): scriverlo prima sarebbe costruire il difetto che §2.4 esiste per impedire. 🔴 **Una correzione a Q-8, trovata scrivendo**: l'endpoint delle rate **non** può stare in `vendite` — `api.md` vieta le chiamate laterali fra moduli di pari livello, e senza il saldo quell'elenco non risponde alla domanda per cui esiste. Vive in `pagamenti` con `skip_area_check`: la sostanza della decisione non cambia (nessun permesso allargato, risposta minima su una fattura già scelta), cambia lo schema che lo ospita. ⭐ **Q-4 realizzata**: le due code sono **un endpoint solo** col parametro `coda`, e una coda inventata è un 400 — su un vocabolario chiuso «nessun risultato» è indistinguibile da «non c'è niente da fare». ✅ Test **51 → 78**, i nove SQL nuovi provati con `EXPLAIN` sul database vero, zero regressioni |
| **2026-08-24** (revisione) | 🔴 **Analisi critica del codice appena scritto, su richiesta di Tid: sette difetti, e sei non davano errore.** ⭐ Il più grave era silenzioso in due modi: **l'elenco duplicava le distinte** (il legame coi lotti era un `LEFT JOIN` diretto, ma l'unico è su `(lotto_id, contabile_id)` e **non** sul solo `contabile_id`: una distinta legata a due lotti compariva due volte, col conteggio totale sbagliato di conseguenza) — corretto aggregando in LATERAL, con un presidio statico che impedisce di rimettere il JOIN. E **un cambio di stato che non avveniva rispondeva 200**: `set_stato_*` torna le righe toccate e nessuno le guardava, quindi un codice di stato non a catalogo faceva leggere «fatto» su un gesto mai successo. 🔴 **Terzo**: aprire una distinta col totale dichiarato erano **due transazioni separate** (`ATOMIC_REQUESTS` non è attivo), e una distinta nata senza il suo dichiarato è una distinta la cui **quadratura non scatta mai** — il controllo esiste e non dice niente. ⚠️ Poi: **`NaN` e `Infinity` passavano come importi** (e un totale NaN non si vede, si legge come un campo vuoto), **una dichiarazione di ZERO righe veniva rifiutata** con una frase falsa mentre il database avrebbe risposto `NULLA_DA_POSTARE`, i **nomi di colonna degli UPDATE** entravano in SQL senza whitelist nel repository — l'ultimo cancello prima della stringa — e restava **codice morto**: due normalizzazioni jsonb identiche, un modulo senza chiamanti, e tre parametri di `create_riga` mai passati che erano peggio degli altri, perché erano una **seconda porta** per scrivere l'abbinamento aggirando il verbo e le sue regole. ⭐ **E gli SQL sono stati provati contro il DATABASE VERO** con `EXPLAIN` (pianifica senza eseguire): tutte e undici le istruzioni valide, e le firme delle due funzioni madri lette dal catalogo per verificare che i nomi dei parametri passati esistano davvero. ⛔ Le due madri **non chiamate nemmeno sotto EXPLAIN**: registrare è irreversibile. Test da **22 a 51**, zero regressioni |
| **2026-08-24** (sviluppo) | ⭐ **IL BACKEND ESISTE: slice 0, 1 e 2 scritte.** `/api/v1/pagamenti/` non è più un 404 secco — otto rotte montate, il repository **dello schema** (non dell'entità), il service, i `TypedDict` e **36 test verdi**. ✅ **Zero regressioni**, e non a occhio: l'elenco dei rossi della suite è stato confrontato con quello di un **albero pulito a HEAD** in un worktree separato, perché l'albero di lavoro ha dentro anche altri cantieri e «erano già rossi» è un'affermazione che va misurata. 🔴 **Un difetto trovato da un presidio esistente**: la prima stesura della lista incollava `NULLS LAST` dopo la direzione dell'ordinamento — ma la direzione la compone `sql_order_direction`, che **porta già** la posizione dei NULL (i vuoti dove starebbe lo zero: in coda scendendo, in testa salendo), e un secondo `NULLS` produce SQL invalido: la lista avrebbe risposto **500 su ogni ordinamento**. 📌 *Un ordinamento sbagliato non rompe niente in modo visibile — produce un elenco ordinato male, che si scopre solo guardando una lista vera.* ✅ **Chiuse anche le due code dei lotti DB** (T-5): i tre codici resi obsoleti dal lotto 7 sono usciti dal ripiego (**BE-10**), e la frase di `E_RIGA_CONTABILE_DISTINTA_FINALE` è stata riallineata a quella allargata il 22/08 — **senza segnaposti**, che è la ragione per cui quel file esiste. ⚠️ **Il cancello della registrazione è dichiarato ma non ancora aperto**: finché `registra_distinta` non è a catalogo e assegnata, risponde `false` per tutti tranne i super admin — **fail-closed**, il verso giusto in cui sbagliare su un gesto irreversibile. ⚠️ E `lista_codice` **non** si dichiara prima del seed: il cancello di perimetro emittente risolve il codice a catalogo e, non trovandolo, spegnerebbe la schermata a chi ha più di un emittente. 🔴 **Frontend non iniziato.** Consuntivo completo in §10 |
| **2026-08-24** (decisioni) | ✅ **TUTTE E NOVE LE DOMANDE CHIUSE, in una sessione sola; due cambiano il piano.** ⭐ **Q-7 → (a)**: la correzione è un **gesto guidato** — un'azione «Correggi» che apre una distinta nuova con le righe di segno opposto **già precompilate** — mai ricopiatura a mano, dove nasce il secondo errore; ⛔ e si chiama **correzione**, mai «storno» (`STORNATA` è ritirata dal 21/08). ⚠️ La sua funzione madre va al team DB come **richiesta differita**, firma proposta ma «da scrivere quando parte la slice»: una madre pronta che nessuno chiama è già successo col posting. ⭐ **Q-8 → (a)**: lookup dedicato in `vendite` con `skip_area_check`, che risponde il minimo su una fattura già scelta — ⛔ **niente LETTURA su `vendite`** a chi lavora gli incassi. E chiudendola è emersa **una cosa che nessuno aveva previsto**, scritta nel brief madre §3.4: **il vincolo che teneva chiuso lo scadenzario è caduto** — «scaduto» e «insoluto» non sono più colonne false, perché il saldo per rata esiste. Lo scadenzario passa da *impossibile* a *possibile e non fatto*, resta **un cantiere suo**, e si porta dietro due avvertenze: i numeri dalla **base unica dei saldi** (uno scadenzario è la porta dei solleciti) e si guarda il **residuo**, non l'incassato — una rata coperta da un giro interno è regolata anche se in banca non è entrato niente. ⭐ **Q-10 → (a)**: `fn_get_saldo_fattura` si allarga alla forma della sorella (`residuo · in_lavorazione · incassato`). Nata e chiusa nella stessa giornata, e la ragione per cui non si rinvia è §2.7: le due alternative — sommare le rate, o riscrivere la formula nel BE — sono **una falsa** (una riga può avere fattura senza rata: il fondo fattura è così) e **una in contraddizione col vincolo appena scritto**. ⭐ **Q-6 → il saldo va nel drawer fattura, senza l'«incassato»** (quel numero risponde a una domanda di tesoreria, non a «questa fattura è a posto?»), **ma la parte che conta è la terza**: *«il drawer fattura non è l'unico posto; dovrà nascere una funzione che dia anche il saldo del cliente, quindi qualsiasi cosa faremo deve essere una base unica per i saldi»*. 🔴 Diventa il **vincolo §2.7**: non si costruisce «il pannello della fattura» ma **la base dei saldi** — un solo modulo BE legge le funzioni di saldo, un vocabolario solo (`residuo · in_lavorazione · incassato`), un componente FE solo, e **tre livelli in testa fin dall'inizio** (documento · rata · **cliente**), col terzo che si accende dopo. Un saldo calcolato in due posti diverge alla prima regola nuova, e sono numeri su cui qualcuno decide se sollecitare un cliente. ⭐ **Q-5 → (a)**: si ritira `approva_rimessa` — orfana da quando D14-e ha tolto il permesso alla forzatura — e nasce **`registra_distinta`**, `pericolosa = true`, il cancello sull'unico gesto irreversibile del cantiere. ⚠️ Due righe di seed (DB-11) e un `check_azione` nella view, **più l'assegnazione a un profilo nello stesso giro**: appena il controllo esiste, senza il permesso concesso non registra nessuno. ⭐ **Q-4 → (c)**: «da abbinare» e «sospese» sono **due voci di menu che aprono la stessa lista** col filtro già impostato — due porte per due mestieri, **un solo** seed a catalogo, perché il filtro vive nella toolbar e non nella definizione. ⚠️ E la decisione ha corretto una misura sbagliata del 22/08: scrivevo che quella coda «si popola solo con l'import», ma era vero **solo finché nessuno poteva digitare righe** — con l'inserimento manuale si riempie subito, quindi **la coda sale dalla slice 4 alla slice 3** (approvato da Tid). ⭐ **Q-3 → (a)**: la distinta si apre con un gesto esplicito e **un form** — *«l'operatore deve poter caricare delle informazioni per aprire la specifica contabile»*. Ne discendono tre cose concrete: il **centro si deriva dal canale** (chiederli entrambi a mano costruisce un errore evitabile, e un guard lo rifiuta), il form deve funzionare **col solo centro** finché gli enti di incasso non esistono (DATO-1), e ⚠️ **la riapertura va annunciata**: la funzione è un *get or create* e ridà la distinta di stamattina — se ha già righe, entrarci in silenzio è il modo in cui si registra due volte credendo di cominciare. **Q-1 → (a)**: nasce l'`ui_action` `confirm_and_retry` in `error_ui_overrides.py` sul codice della capienza — il frontend ramifica su `azioneUi` e **resta cieco ai codici**, che è la proprietà che rendeva fragile l'alternativa. ⛔ **Q-2 → il gesto non esiste**: *«il pagamento di una rata non si spezza»*, registrata nel brief madre come **D1-ter**. ⭐ **L'equivoco era mio e stava nell'esempio**: presentavo 1.200 su una rata da 1.000 come il caso da spezzare, ma se la rata è identificata l'atto del cliente è **uno solo con un importo sbagliato** — spezzarlo inventa due allocazioni dove ce n'è una e **decide al posto del cliente** dove vanno i soldi di troppo. 🔴 **E la ragione per cui D1-bis diceva il contrario non era sbagliata allora**: preferiva spezzare perché *«l'eccedenza resta denaro identificato invece di sparire dentro una rata che non la giustifica»*, vero il 9 agosto perché le sistemazioni non c'erano. Il lotto 7 le ha costruite: l'eccedenza **ha un elenco e un registro**, e la preferenza cade perché il problema è stato risolto altrove. 📮 Ne discende: **cade la slice 6**, cade `POST /righe/{id}/spezza/`, e cade `fn_spezza_riga_contabile` — che era **l'unico oggetto DB ancora mancante**: da adesso il database non deve più niente a questo cantiere **tranne i quattro seed di lista**. ✅ Il piano passa da **sette slice a sei** e da **tre prerequisiti DB a due**. ⚠️ **D1 regge intatta**: un incasso che copre tre rate resta tre righe, cambia solo *quando* si scrivono — subito, digitandole, invece che spezzando dopo |
| **2026-08-24** | ⭐ **REVISIONE DEL PIANO dopo la chiusura del DB.** Il 22/08 il piano era scritto col DB al lotto 3 di 7 e metà slice in attesa; il team DB ha chiuso **tutti e sette i lotti** nella stessa giornata (71 changeSet, 14 pgTAP). Rimisurato **tutto** contro il database vivo e il codice BE/FE. 🔴 **Cinque misure del 22/08 sono risultate sbagliate** (§1.5), e due di esse **tolgono lavoro invece di aggiungerne**: il lookup delle rate non ha bisogno di niente dal DB (`list_fattura_scadenze` esiste già in `vendite_repository`) e l'`ui_action` dei rifiuti confermabili **non sta a catalogo DB** ma in `error_ui_overrides.py`, che è Python scritto a mano — Q-1 passa da «un giro col team DB» a **una riga più un ramo**. Le altre tre spostano il lavoro: la vista si chiama `vw_rate_fuori_capienza` e contiene **due** popolazioni (sovra-incasso *e* movimento contrario), la forzatura **non è un flag di payload** ma due colonne della riga (`forzata`, `motivo_forzatura`) che restano scritte e che l'elenco a valle legge, e `fn_get_or_create_vendite_contabile` **ha cambiato firma** (via `p_compensazione_id`, D15-e). ⭐ **I nove prerequisiti DB diventano tre**: due viste sono state consegnate senza che nessuno le chiedesse (`vw_rate_fuori_capienza` col lotto 5, `vw_eccedenze_da_sistemare` col lotto 7, e la seconda porta già il raggruppamento per cliente in finestra), due non erano del DB, uno è diventato lavoro BE di verifica. Restano **quattro seed di lista** (che genero io in bozza con `scripts/gen_seed_lista.py`, un round-trip invece di quattro). ✅ **BE-1 riverificata con uno script e non a campione**: 778 codici su 778 hanno la classe, e tutti i codici del cantiere hanno anche il ripiego — la coda che il piano DB elenca in cinque punti **è chiusa**. 📮 Restano **due code di lotto** che sono lavoro di minuti e vanno in slice 0: il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` porta ancora la frase vecchia, e tre codici marcati obsoleti il 22/08 sono ancora nel ripiego (BE-10). 🔴 **E la revisione ha trovato una cosa che nessuno dei tre brief dice**: `fn_get_saldo_rata` risponde **tre** numeri (registrato, in lavorazione, **incassato**) e `fn_get_saldo_fattura` ne risponde **due** — cioè la distinzione che §2.4 dichiara obbligatoria *«nella prima misura che si scrive»* esiste sulla rata e **non** sulla fattura, che è il livello che l'operatore guarda per primo. È **Q-10**, l'unica domanda nuova, e le due strade alternative sono peggiori entrambe (sommare le rate perde il fondo fattura, che ha fattura senza rata; riscrivere la formula nel BE crea due sedi per la stessa regola). ⭐ **Piano riordinato per valore**: le sette slice non hanno più dipendenze DB, la **registrazione sale da terza a seconda**, e la sola cosa che resta bloccata non è codice ma **dato** — senza il conto `uso = 'INCASSO'` dei due emittenti nessun canale di incasso è creabile (DATO-1), e con esso si ferma la sola slice 4. ⚠️ **Un vincolo nuovo dal lotto 6** (§2.6): `pagamenti.*` pretende `app.ruolo_applicativo = 'OPERATORE'` per leggere **e** per scrivere; verificato che middleware e worker della coda la impostano già, resta da controllare ciò che gira fuori da entrambi. Domande: restano **nove** — **Q-9 si è chiusa senza essere decisa** (le viste erano già lì, i seed si chiedono insieme), **Q-1 e Q-8 sono crollate di prezzo** senza cambiare risposta, e nasce Q-10, l'unica che tocca il modello |
| 2026-08-22 | Stesura. Terreno BE/FE misurato **sul codice**, non sui brief. ⭐ **Sei cose risultavano già fatte** e i due brief esistenti non lo sapevano: BE-1 chiusa, i quattro cataloghi in whitelist, `fn_get_lookup_codici` che filtra già `obsoleto_dal`, l'area a catalogo, il dominio in `DOMAINS` e la sua chiave i18n. 🔴 **Vuoto per davvero**: `urls_v1.py` inesistente, `views.py` una riga di commento, `DOMAIN_MENUS['pagamenti']` a `[]`, e **nessuna** `ui.lista_definizione` di `pagamenti` — da cui il fatto che pesava di più: **ogni lista costa un prerequisito DB**. Piano in **sette slice** agganciate ai lotti DB, di cui tre eseguibili subito. 🔴 Due prerequisiti che il piano DB non conteneva (spezzatura di una riga, lookup delle rate) e un problema di confine: un rifiuto *confermabile* esce sul filo come un errore qualunque. Nove domande aperte |
