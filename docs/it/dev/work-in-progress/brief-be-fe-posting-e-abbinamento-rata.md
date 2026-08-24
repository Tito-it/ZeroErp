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
> ⛔ **Niente è ancora scritto lato applicativo**, e questo è **riverificato
> oggi**: `apps/pagamenti/api/views.py` è ancora una riga di commento,
> `/api/v1/pagamenti/` è ancora un 404 secco, `DOMAIN_MENUS['pagamenti']` è
> ancora `[]`, e nessun modulo Python del progetto nomina una funzione di
> `pagamenti`. Questo documento resta **un piano**.
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
| 🔴 **Da zero** | `urls_v1.py` non esiste e non è montato · `views.py` è una riga di commento · `frontend/src/pagamenti/` sono **due `.gitkeep`** · `DOMAIN_MENUS['pagamenti']` è `[]` · **nessuna** `ui.lista_definizione` è di `pagamenti` | §1.2 |
| 🔴 **Cinque misure del 22/08 oggi sbagliate** | la vista **non si chiama** `vw_rate_sovra_incassate` · la forzatura **non è un flag di payload**, è una colonna della riga · il lookup delle rate **non è un prerequisito DB** · l'`ui_action` **non sta a catalogo DB** · `fn_get_or_create_vendite_contabile` ha **cambiato firma** | §1.5 |
| 📋 **Il piano** | **Sei slice**, nessuna in attesa. Ordinate per valore: S0 telaio → S1 distinta e righe → **S2 la registrazione** → S3 rata e capienza → S4 perimetro e canali → S5 sistemazioni. ⛔ La settima (spezzatura) **è caduta con D1-ter** | §3 |
| 🔌 **Il contratto** | 18 endpoint, grammatica URL di `api.md`. ⭐ Il posting è **una sola `SELECT`**; l'abbinamento è **un verbo solo** che porta anche la forzatura | §4 |
| 🎨 **Il frontend** | 5 schermate, 2 drawer, 3 pannelli. **17 building block riusati**, **4 candidati** all'estrazione (nessuno al primo colpo) | §5 |
| 📮 **Al team DB** | **Due**, non nove: i **seed delle liste** (che genero io in bozza) e l'**asimmetria del saldo fattura** (Q-10). ⛔ La terza — la spezzatura — **è caduta con D1-ter**. ⚠️ Più un **dato**, non codice: senza il conto `INCASSO` dei due emittenti **nessun canale di incasso è creabile** | §6 |
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
> ⚠️ **Con una sola eccezione, e non è codice**: nessuno dei due emittenti ha un
> conto con `uso = 'INCASSO'` censito (S3-3 del piano DB, DATO-1). Finché manca,
> **nessun `ente_incasso` è creabile** — ed è voluto: si fallisce alla
> configurazione, non in esercizio. Blocca la **slice 4**, non le altre.

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

Da lotto 6 le dodici tabelle di `pagamenti` hanno la RLS accesa con policy
`FOR ALL`: pretendono `app.ruolo_applicativo = 'OPERATORE'` **per leggere e per
scrivere**. Un percorso senza quella GUC **non vede niente e non scrive niente**.

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

```text
  S0 telaio ──▶ S1 distinta e righe ──▶ S2 LA REGISTRAZIONE ──▶ S3 rata e capienza
                                                                      │
                    S4 perimetro e canali (⚠️ DATO-1) ◀───────────────┤
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
| S5 (perimetro e coda) | **S4** | invariata, ⚠️ **bloccata da DATO-1** |
| S6 (sistemazioni) | **S5** | invariata: chiude **BE-4** e sblocca la **Fase D** del cantiere fondi |
| ~~R-4 (spezza)~~ | ⛔ **caduta** | **D1-ter, 2026-08-24**: il gesto non esiste più. Con essa cade `fn_spezza_riga_contabile`, che era l'unico oggetto DB mancante |

### 3.0 S0 — Il telaio

Nessun valore di dominio. È ciò senza cui la slice 1 non si scrive.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **T-1** | `apps/pagamenti/api/urls_v1.py` + montaggio | BE | `path("api/v1/pagamenti/", include("apps.pagamenti.api.urls_v1"))`, dopo `pratiche` |
| **T-2** | `apps/pagamenti/db/pagamenti_repository.py` | BE | Il repository **generico dello schema**: liste, letture, chiamate alle `fn_*`. ⛔ **Non** un file per entità |
| **T-3** | `apps/pagamenti/services/pagamenti_service.py` | BE | La facciata. ⚠️ Il traduttore degli errori si prende da `make_db_errors_translator`, **non** si riscrive |
| **T-4** | `apps/pagamenti/types.py` | BE | `TypedDict` delle righe DB (`DistintaRow`, `RigaContabileRow`, `RicevutaPosting`, `SaldoRata`, `EccedenzaRow`) |
| **T-5** | ⭐ **Le due code dei lotti** | BE | Riscrivere il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` (frase nuova, **senza `%s`**) e **togliere** i tre codici obsoleti dal ripiego (BE-10). §1.5 |
| **T-6** | `frontend/src/pagamenti/{views,components,stores,api}/` | FE | Le quattro cartelle |
| **T-7** | `DOMAIN_MENUS['pagamenti']` + rotte | FE | Da `[]` alle voci della slice 1. ⚠️ `meta` per `resolveTabLabel`/`resolveTabIcon` |
| **T-8** | Namespace i18n `pagamenti.*` in `it.json` e `en.json` | FE | ⚠️ `check_i18n_keys.py` è **un cancello CI**: una `label_key` seminata a DB senza la sua chiave **fa fallire la build** |
| **T-9** | `useReadonlyMode('pagamenti')` sulle viste | FE | Piramide permessi standard |
| **T-10** | ⚠️ **La prova del perimetro** | BE | Una lettura qualunque di `pagamenti` con e senza la GUC operatore, per **vedere** la RLS mordere prima che lo faccia in una lista (§2.6) |

⭐ **Nessun endpoint di lookup da scrivere**: i quattro cataloghi sono già in
whitelist. Il FE usa `LookupSelect` con `rel="pagamenti.centri_riscossione"`.

### 3.1 S1 — La distinta e le sue righe

Il documento che raccoglie N importi arrivati insieme, **con dentro le sue
righe**: sono un drawer solo e si costruiscono insieme.

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **D-1** | `GET /pagamenti/distinte/` — lista paginata | BE | 📮 **Prerequisito**: seed `ui.lista_definizione` + `lista_colonna` (§6). Filtri: stato, origine, centro, **data** (`data_contabile`, col floor standard di `defaultFiltroDataDa`) |
| **D-2** | `POST /pagamenti/distinte/` | BE | Una `SELECT fn_get_or_create_vendite_contabile(...)` con `p_origine := 'MANUALE'`, `p_codice_stato_interno := 'BOZZA'`. ⭐ Il BE **non passa** l'operatore. ⚠️ `Idempotency-Key` obbligatoria |
| **D-2-bis** | Dialogo «Apri distinta» | FE | ✅ **Q-3 chiusa su (a)**: l'apertura è **un form**, non un pulsante — canale (da cui **si deriva il centro**), centro se il canale non c'è, data contabile, importo dichiarato. ⚠️ Se il *get-or-create* **riapre** una distinta che ha già righe, la schermata **lo dice** |
| **D-3** | `GET /pagamenti/distinte/{id}/` | BE | Testata + totali derivati (somma righe, righe registrabili, scarto dal dichiarato) + **il catalogo degli stati coi suoi flag** (`is_postabile`, `richiede_abbinamento`, `is_final`) |
| **D-4** | `PATCH /pagamenti/distinte/{id}/` | BE | Solo i campi che una persona compila: `data_contabile`, `ente_incasso_id`, `importo_dichiarato`, `meta`. ⛔ **Non** lo stato |
| **D-5** | `POST /pagamenti/distinte/{id}/stato/` | BE | `{nuovo_stato: 'VALIDATA'\|'BOZZA'\|'ANNULLATA'}` — **tre valori, non quattro** (§1.5 punto 5). Un `UPDATE stato_id`, e i guard fanno il resto |
| **R-1** | `GET/POST /pagamenti/distinte/{id}/righe/` | BE | Lista e creazione righe |
| **R-2** | `PATCH /pagamenti/righe/{id}/` | BE | I **fatti**: `importo`, le tre date, `riferimento_ente`, `motivo_sospeso`. ⛔ **Non** l'abbinamento: quello è un verbo (S3, ma il campo `scadenza_id` esiste già e va previsto nel form fin da subito) |
| **R-3** | `POST /pagamenti/righe/{id}/stato/` | BE | Il percorso di D14-a. I guard rifiutano ciò che non è ammesso, **compreso** `ABBINATA` senza fattura |
| **D-6** | `DistinteListView.vue` | FE | `<ListaConfigurabile>` + `useListaConfigurabilePage` + `PageActionsBar`. Modello: `ApprovazioniPrezzoListView.vue` |
| **D-7** | `DistintaDrawer.vue` | FE | Testata + **master-detail inline** delle righe (`RigheMasterDetailTable`). ⚠️ `readonly` + `useInjectReadonly` **obbligatori** |
| **D-8** | Pannello «validazione» | FE | Dichiarato vs digitato e **il delta**, così l'errore si vede **prima** di premere. ⚠️ Post-BOZZA il drawer è `.app-readonly` ⇒ **wrapper `app-escape` obbligatorio** |
| **R-6** | Form riga | FE | `BillingAccountLookup` (esiste) + `FatturaLookup` (nuovo). ⚠️ Salvare l'`_obj` nel form per il restore dell'AutoComplete server-side |
| **R-7** | Azioni di riga | FE | `RowActionsMenu` + `MANAGE_ICONS.KEBAB`. ⛔ **Mai la matita** |

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
| **P-0** | ⭐ **Il cancello** *(Q-5 → a)* | BE | `registra_distinta` a catalogo (`pericolosa = true`), `approva_rimessa` ritirata con `attivo = false`, `check_azione` nella view del verbo. 🔴 **Con l'assegnazione a un profilo nello stesso giro**: senza, il pulsante esiste e non funziona per nessuno |
| **P-1** | `GET /pagamenti/distinte/{id}/anteprima-registrazione/` | BE | La **fotografia**: quante righe sono registrabili adesso, per che totale, quante restano indietro e perché. È ciò che l'operatore vede **prima** di premere, ed è ciò che poi **dichiara** |
| **P-2** | `POST /pagamenti/distinte/{id}/registra/` | BE | **Una sola** `SELECT fn_posta_contabile(id, righe_attese, totale_atteso)`. ⚠️ I due parametri o **entrambi o nessuno**. `Idempotency-Key` obbligatoria |
| **P-3** | La ricevuta risale intatta | BE | `{movimenti_creati, righe_postate, righe_saltate, totale_postato, esito}` dentro `success_response`. ⛔ Il BE **non** trasforma `NULLA_DA_POSTARE` in un errore |
| **P-4** | Pannello «Registra» nel drawer | FE | Mostra l'anteprima, chiede conferma, invia la dichiarazione. ⚠️ `app-escape` |
| **P-5** | La frase sull'esito | FE | `POSTATA` → toast coi numeri della ricevuta; `NULLA_DA_POSTARE` → **avviso**, non errore: *«questa distinta era già registrata»* |
| **P-6** | Il rifiuto della dichiarazione | FE | Su `E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE` (963) **non si riprova in automatico**: si ricarica l'anteprima e si mostra la differenza. Un retry cieco su un gesto irreversibile è la cosa peggiore che si possa costruire |
| **P-7** | ⭐ **La distinta si chiude da sé** | FE | Dopo la registrazione lo stato è `CHIUSA`: il drawer va ricaricato e il pannello sparisce. ⛔ Nessun pulsante «chiudi» da nessuna parte |

### 3.3 S3 — La rata e la capienza

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **A-1** | `POST /pagamenti/righe/{id}/abbina/` | BE | ⭐ **Il verbo dell'abbinamento** (BE-6): `{fattura_id, billing_account_id, scadenza_id?, forzata?, motivo_forzatura?}`. Un `UPDATE` solo, e i guard della rata decidono |
| **A-2** | `GET /vendite/fatture/{id}/scadenze/lookup/` | BE | Le rate di una fattura **col loro saldo**: `list_fattura_scadenze` + `fn_get_saldo_rata` in LATERAL. ⚠️ Vive in `vendite` con `skip_area_check = True` (**Q-8**) |
| **A-3** | ⭐ **La base dei saldi** *(§2.7)* | BE | `apps/pagamenti/services/saldi_service.py`: **l'unico** lettore delle funzioni di saldo. Forma unica `residuo · in_lavorazione · incassato`, tre livelli previsti (documento · rata · **cliente**, il terzo si accende dopo). Endpoint `GET /pagamenti/rate/{id}/saldo/` e `GET /vendite/fatture/{id}/saldo/` sono **due consumatori**, non due implementazioni |
| **A-4** | `GET /pagamenti/rate/fuori-capienza/` | BE | Sopra `vw_rate_fuori_capienza`. 📮 Prerequisito: **solo il seed** della lista — la vista c'è |
| **A-5** | La forzatura a due tempi | BE+FE | Il primo tentativo **non** porta `forzata`; sul 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` il FE mostra il messaggio del DB (che porta già i numeri) e chiede conferma; il secondo porta `forzata: true` + `motivo_forzatura`. Come il FE lo **riconosce** è **Q-1** |
| **A-6** | `RateFuoriCapienzaListView.vue` | FE | Lista. ⭐ La prima colonna è **`motivo`**: due popolazioni diverse in un elenco solo |
| **A-7** | Selettore rata nel form riga | FE | Alimentato dalla fattura scelta; si azzera quando la fattura cambia. ⚠️ La rata resta **facoltativa** anche su `ABBINATA` — la riga del fondo fattura ha fattura sì e rata no |
| **A-8** | `SaldoPanel` nel drawer fattura | FE | ✅ **Q-6**: **residuo** in grande, **in lavorazione** in piccolo e solo quando c'è. ⛔ **Niente «incassato»** su questa schermata. ⭐ Un componente solo per tutti i livelli (§2.7) |
| **A-9** | ⭐ **La coda del riconciliatore** *(salita dalla slice 4 — Q-4)* | BE+FE | `GET /pagamenti/righe/` con filtro di stato: lista **cross-distinta**. ✅ **Q-4 → (c)**: **due voci di menu** («Da abbinare» · «Sospese») che aprono **la stessa lista** con il filtro già impostato — due porte, **un solo** seed |

### 3.4 S4 — Il perimetro e la coda ⚠️ *(bloccata da DATO-1, non da codice)*

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **E-1** | Gestione `enti_incasso` | BE+FE | Drawer dedicato: ha JOIN (soggetto_ruolo, filiale, **conto**) quindi **non** è un pannello config generico. ⭐ **BE-8**: l'elenco dei conti mostra **solo** quelli con `uso = 'INCASSO'` dell'emittente — il DB rifiuta gli altri, ma un elenco che li propone fa sbagliare |
| **E-2** | ⛔ **Il blocco** | — | Finché i due emittenti non hanno il loro conto `INCASSO` censito (**DATO-1**), questa schermata **non può creare niente**. Non è un difetto: è D5 |
| ~~**E-3**~~ | ~~Coda «da abbinare»~~ | — | ⬆️ **Salita alla slice 3 (A-9)** con la chiusura di **Q-4**: la coda si riempie già con l'inserimento manuale, non aspetta l'import |
| **E-4** | Riverifica di **tutte** le liste sotto RLS | BE | ⚠️ §2.6: dentro e fuori perimetro, e si guarda la differenza |

### 3.5 S5 — Le sistemazioni

| | Passo | Lato | Cosa fa |
| --- | --- | --- | --- |
| **S-1** | `GET /pagamenti/eccedenze/` | BE | Sopra `vw_eccedenze_da_sistemare`. ⭐ **Raggruppata per cliente** — e la vista porta già `eccedenza_cliente` e `documenti_cliente` in finestra: il BE **non somma niente** |
| **S-2** | `POST /pagamenti/sistemazioni/` | BE | ⭐ Un **`INSERT`**, non un verbo: `{destinazione, importo, cliente_…, emittente_…, fattura_origine_id, fattura_destinazione_id?, motivo?}`. I CHECK del DB tengono le combinazioni |
| **S-3** | `POST /pagamenti/sistemazioni/{id}/conferma/` | BE | Una `SELECT fn_conferma_sistemazione(id, ente_incasso_id)`. ⚠️ **Il canale del rimborso si chiede QUI**: da quale conto esce il bonifico è una decisione del momento in cui si paga |
| **S-4** | `POST /pagamenti/sistemazioni/{id}/annulla/` | BE | `fn_annulla_sistemazione(id, motivo)`. ⚠️ Il motivo è **obbligatorio** se l'atto non ne aveva già uno |
| **S-5** | `EccedenzeView.vue` + drawer decisione | FE | La vista presenta, la persona decide, l'atto diventa un fatto. ⭐ `chi_e_in_credito` in evidenza: cliente o azienda cambia completamente che cosa si sta guardando |
| **S-6** | Il dialogo della conferma | FE | Chiede il **canale** solo su `RIMBORSO` (sulle altre due destinazioni non serve) |

📮 Con S-3 si chiude **BE-4** e si sblocca la **Fase D del cantiere fondi**,
ferma per scelta da agosto: il riporto **è** il fondo `origine = MANUALE` che
quel cantiere aspettava.

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
| **Import del flusso bancario** (D6) | `enti_incasso` è a 0 righe **e non è creabile** (DATO-1): non esiste un canale da cui un file possa arrivare |
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
| S3 | `GET /api/v1/pagamenti/rate/{id}/saldo/` | la base dei saldi, livello **rata** | — |
| S3 | `GET /api/v1/vendite/fatture/{id}/saldo/` | la base dei saldi, livello **documento** — ⚠️ stessa forma, stesso service | — |
| S3 | `GET /api/v1/pagamenti/rate/fuori-capienza/` | l'elenco che rende onesta la forzatura | — |
| S3 | `GET /api/v1/vendite/fatture/{id}/scadenze/lookup/` | 🔵 **Q-8** — vive in `vendite` | — |
| S4 | `GET/POST/PATCH /api/v1/pagamenti/enti-incasso/…` | configurazione canali | ✅ su write |
| S3 | `GET /api/v1/pagamenti/righe/` | la coda cross-distinta, filtro `stato` — **due voci di menu, un endpoint** (Q-4) | — |
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
| **Canali di incasso** | S4 | Drawer di configurazione ⚠️ bloccato da DATO-1 |
| **Da abbinare** · **Sospese** | S3 | ⭐ **La stessa lista, due voci di menu** con il filtro di stato già impostato (Q-4 → c) |
| **Eccedenze da sistemare** | S5 | Lista raggruppata **per cliente** + drawer decisione + dialogo conferma |

### 5.2 ✅ I 17 building block che si riusano

`ListaConfigurabile` · `useListaConfigurabilePage` · `useListaAzioni` ·
`PageActionsBar` · `RowActionsMenu` · `AppDrawer` · `FormFooter` ·
`DrawerActionsBar` · `AppDialog` · `RigheMasterDetailTable` · `LookupSelect` ·
`BillingAccountLookup` · `useReadonlyMode` · `useConfirmAction` ·
`useDrawerContentReady` · `createCrudStore` · `defaultFiltroDataDa`.

### 5.3 🆕 I quattro candidati all'estrazione — e tre non sono nostri

| BB | Dove vivrebbe | Perché |
| --- | --- | --- |
| `FatturaLookup.vue` | `core/components/` | Autocomplete fattura cross-dominio. ⭐ Serve a chiunque debba puntare una fattura da un altro schema |
| `ScadenzaSelect.vue` | `core/components/` | Rate di una fattura **col saldo accanto**. Gemello del precedente un piano più giù |
| `SaldoPanel.vue` + `useSaldi.js` | `core/components/` · `core/composables/` | ⭐ **Non è più un candidato: è un vincolo** (§2.7, decisione di Tid). Un componente e un composable **soli**, forma unica `residuo · in_lavorazione · incassato`, e ogni schermata sceglie **quali** numeri accendere. Nasce con **tre livelli in testa** — documento, rata, **cliente** |
| `useForzaturaConfermata.js` | `core/composables/` | Il doppio-tempo «rifiuto parlante → conferma → ripeti». ✅ **Q-1 è chiusa su (a)**, quindi può nascere BB davvero: astrae **un comportamento** (`azioneUi === 'confirm_and_retry'`) e non un elenco di codici |

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

## 6. 📮 I prerequisiti a carico del team DB: da nove a **due**

⛔ **Non li eseguo io** (le azioni DB si passano al team): si scrivono in un
brief e si aspetta. Ecco il consuntivo della revisione.

| | Prerequisito del 22/08 | Oggi |
| --- | --- | --- |
| **DB-1** | vista `vw_vendite_contabili_lista` | 🔵 **Probabilmente non serve**: le liste alimentate da un endpoint di dominio si seminano con `vista_sql = NULL` (è la forma delle 6 liste dell'8° lotto e delle 3 del drawer lotto). I display field si fanno in JOIN **nel repository**. ⚠️ Costo: con `vista_sql` nullo il guard DB sui `campo_sorgente` **salta**, e l'unico presidio resta quello Python |
| **DB-2** | seed lista **distinte** | 📮 **RESTA** |
| **DB-11** | 🆕 due righe in `config/azioni_processo.csv`: `approva_rimessa` → `attivo = false`, e `registra_distinta` (area 7, `pericolosa = true`) | 📮 **NUOVO, da Q-5**: il cancello sulla registrazione. ⚠️ Minuscolo, ma **blocca la slice 2** se arriva dopo |
| **DB-3** | seed lista **righe da abbinare** | 📮 **RESTA**, ed è **uno solo**: con Q-4 → (c) le due code condividono la definizione e si separano col filtro |
| **DB-4** | vista + seed **rate sovra-incassate** | ⭐ **La vista c'è già** (`vw_rate_fuori_capienza`, lotto 5), col nome giusto e più contenuto di quanto chiedessi. 📮 Resta **il seed** |
| ~~**DB-5**~~ | `fn_spezza_riga_contabile` | ⛔ **CADUTO (D1-ter, 2026-08-24)**: il gesto che lo richiedeva non esiste più. ⭐ Era l'unico oggetto DB mancante — **adesso il database non deve più niente a questo cantiere, tranne i seed** |
| **DB-6** | lookup rate di una fattura | ✅ **ANNULLATO**: `list_fattura_scadenze` esiste, e i numeri li dà `fn_get_saldo_rata` |
| **DB-7** | `ui_action` per i rifiuti confermabili | ✅ **ANNULLATO**: le `ui_action` sono un file **Python scritto a mano** (`error_ui_overrides.py`) |
| **DB-8** | vista + seed **eccedenze** | ⭐ **La vista c'è già** (`vw_eccedenze_da_sistemare`, lotto 7), e porta pure il raggruppamento per cliente. 📮 Resta **il seed** |
| **DB-9** | conferma che le liste reggano sotto RLS | ✅ **ANNULLATO come richiesta**: il lotto 6 ha portato `test-rls-pagamenti-perimetro.sql` (14 asserzioni). ⚠️ Diventa **lavoro BE**: la prova dentro/fuori perimetro su ogni lista (§2.6, T-10, E-4) |
| **DB-10** | 🆕 | 📮 **NUOVO e CONFERMATO** (Q-10 → a, Tid 24/08): allargare `fn_get_saldo_fattura` a `residuo · in_lavorazione · incassato`, la stessa forma di `fn_get_saldo_rata`. ⭐ Non è una rifinitura: senza, la **base unica dei saldi** (§2.7) nasce storta al livello che dovrà reggere il **saldo cliente** |
| **DATO-1** | 🆕 | ⚠️ **Non è una richiesta al DB, è configurazione**: il conto `uso = 'INCASSO'` per ciascuno dei due emittenti. ⛔ Senza, **nessun canale di incasso è creabile** e la slice 4 non parte |

⭐ **E i quattro seed si chiedono in un colpo solo, già scritti.** Esiste
`scripts/gen_seed_lista.py`, che genera le righe dei quattro CSV a partire dal
componente `.vue` e dalla vista: **le genero io in bozza** (i campi curati —
priorità, gruppo, larghezza, sensibile — li decido a mano) e il team DB le fa
confluire nei CSV di seed. Un round-trip invece di quattro, e nessuno scrive
269 colonne a mano una seconda volta.

---

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
> ⚠️ **Resta un solo blocco, e non è una domanda**: **DATO-1**, il conto di
> incasso dei due emittenti — senza, la slice 4 non parte.

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
| **centro di riscossione** | obbligatorio. Si chiede **direttamente** solo quando un canale non c'è (la cassa). ⚠️ **Oggi è sempre così**: `enti_incasso` è a zero righe e non è creabile (DATO-1), quindi il form deve funzionare col solo centro |
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

⭐ **Non serve niente al team DB**: la lettura delle rate esiste già
(`vendite_repository.list_fattura_scadenze`) e i numeri li dà la base dei saldi
(§2.7).

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
6. poi S4 (⚠️ ferma su DATO-1) e S5, che chiude il cantiere e sblocca la Fase D
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

## 10. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| **2026-08-24** (decisioni) | ✅ **TUTTE E NOVE LE DOMANDE CHIUSE, in una sessione sola; due cambiano il piano.** ⭐ **Q-7 → (a)**: la correzione è un **gesto guidato** — un'azione «Correggi» che apre una distinta nuova con le righe di segno opposto **già precompilate** — mai ricopiatura a mano, dove nasce il secondo errore; ⛔ e si chiama **correzione**, mai «storno» (`STORNATA` è ritirata dal 21/08). ⚠️ La sua funzione madre va al team DB come **richiesta differita**, firma proposta ma «da scrivere quando parte la slice»: una madre pronta che nessuno chiama è già successo col posting. ⭐ **Q-8 → (a)**: lookup dedicato in `vendite` con `skip_area_check`, che risponde il minimo su una fattura già scelta — ⛔ **niente LETTURA su `vendite`** a chi lavora gli incassi. E chiudendola è emersa **una cosa che nessuno aveva previsto**, scritta nel brief madre §3.4: **il vincolo che teneva chiuso lo scadenzario è caduto** — «scaduto» e «insoluto» non sono più colonne false, perché il saldo per rata esiste. Lo scadenzario passa da *impossibile* a *possibile e non fatto*, resta **un cantiere suo**, e si porta dietro due avvertenze: i numeri dalla **base unica dei saldi** (uno scadenzario è la porta dei solleciti) e si guarda il **residuo**, non l'incassato — una rata coperta da un giro interno è regolata anche se in banca non è entrato niente. ⭐ **Q-10 → (a)**: `fn_get_saldo_fattura` si allarga alla forma della sorella (`residuo · in_lavorazione · incassato`). Nata e chiusa nella stessa giornata, e la ragione per cui non si rinvia è §2.7: le due alternative — sommare le rate, o riscrivere la formula nel BE — sono **una falsa** (una riga può avere fattura senza rata: il fondo fattura è così) e **una in contraddizione col vincolo appena scritto**. ⭐ **Q-6 → il saldo va nel drawer fattura, senza l'«incassato»** (quel numero risponde a una domanda di tesoreria, non a «questa fattura è a posto?»), **ma la parte che conta è la terza**: *«il drawer fattura non è l'unico posto; dovrà nascere una funzione che dia anche il saldo del cliente, quindi qualsiasi cosa faremo deve essere una base unica per i saldi»*. 🔴 Diventa il **vincolo §2.7**: non si costruisce «il pannello della fattura» ma **la base dei saldi** — un solo modulo BE legge le funzioni di saldo, un vocabolario solo (`residuo · in_lavorazione · incassato`), un componente FE solo, e **tre livelli in testa fin dall'inizio** (documento · rata · **cliente**), col terzo che si accende dopo. Un saldo calcolato in due posti diverge alla prima regola nuova, e sono numeri su cui qualcuno decide se sollecitare un cliente. ⭐ **Q-5 → (a)**: si ritira `approva_rimessa` — orfana da quando D14-e ha tolto il permesso alla forzatura — e nasce **`registra_distinta`**, `pericolosa = true`, il cancello sull'unico gesto irreversibile del cantiere. ⚠️ Due righe di seed (DB-11) e un `check_azione` nella view, **più l'assegnazione a un profilo nello stesso giro**: appena il controllo esiste, senza il permesso concesso non registra nessuno. ⭐ **Q-4 → (c)**: «da abbinare» e «sospese» sono **due voci di menu che aprono la stessa lista** col filtro già impostato — due porte per due mestieri, **un solo** seed a catalogo, perché il filtro vive nella toolbar e non nella definizione. ⚠️ E la decisione ha corretto una misura sbagliata del 22/08: scrivevo che quella coda «si popola solo con l'import», ma era vero **solo finché nessuno poteva digitare righe** — con l'inserimento manuale si riempie subito, quindi **la coda sale dalla slice 4 alla slice 3** (approvato da Tid). ⭐ **Q-3 → (a)**: la distinta si apre con un gesto esplicito e **un form** — *«l'operatore deve poter caricare delle informazioni per aprire la specifica contabile»*. Ne discendono tre cose concrete: il **centro si deriva dal canale** (chiederli entrambi a mano costruisce un errore evitabile, e un guard lo rifiuta), il form deve funzionare **col solo centro** finché gli enti di incasso non esistono (DATO-1), e ⚠️ **la riapertura va annunciata**: la funzione è un *get or create* e ridà la distinta di stamattina — se ha già righe, entrarci in silenzio è il modo in cui si registra due volte credendo di cominciare. **Q-1 → (a)**: nasce l'`ui_action` `confirm_and_retry` in `error_ui_overrides.py` sul codice della capienza — il frontend ramifica su `azioneUi` e **resta cieco ai codici**, che è la proprietà che rendeva fragile l'alternativa. ⛔ **Q-2 → il gesto non esiste**: *«il pagamento di una rata non si spezza»*, registrata nel brief madre come **D1-ter**. ⭐ **L'equivoco era mio e stava nell'esempio**: presentavo 1.200 su una rata da 1.000 come il caso da spezzare, ma se la rata è identificata l'atto del cliente è **uno solo con un importo sbagliato** — spezzarlo inventa due allocazioni dove ce n'è una e **decide al posto del cliente** dove vanno i soldi di troppo. 🔴 **E la ragione per cui D1-bis diceva il contrario non era sbagliata allora**: preferiva spezzare perché *«l'eccedenza resta denaro identificato invece di sparire dentro una rata che non la giustifica»*, vero il 9 agosto perché le sistemazioni non c'erano. Il lotto 7 le ha costruite: l'eccedenza **ha un elenco e un registro**, e la preferenza cade perché il problema è stato risolto altrove. 📮 Ne discende: **cade la slice 6**, cade `POST /righe/{id}/spezza/`, e cade `fn_spezza_riga_contabile` — che era **l'unico oggetto DB ancora mancante**: da adesso il database non deve più niente a questo cantiere **tranne i quattro seed di lista**. ✅ Il piano passa da **sette slice a sei** e da **tre prerequisiti DB a due**. ⚠️ **D1 regge intatta**: un incasso che copre tre rate resta tre righe, cambia solo *quando* si scrivono — subito, digitandole, invece che spezzando dopo |
| **2026-08-24** | ⭐ **REVISIONE DEL PIANO dopo la chiusura del DB.** Il 22/08 il piano era scritto col DB al lotto 3 di 7 e metà slice in attesa; il team DB ha chiuso **tutti e sette i lotti** nella stessa giornata (71 changeSet, 14 pgTAP). Rimisurato **tutto** contro il database vivo e il codice BE/FE. 🔴 **Cinque misure del 22/08 sono risultate sbagliate** (§1.5), e due di esse **tolgono lavoro invece di aggiungerne**: il lookup delle rate non ha bisogno di niente dal DB (`list_fattura_scadenze` esiste già in `vendite_repository`) e l'`ui_action` dei rifiuti confermabili **non sta a catalogo DB** ma in `error_ui_overrides.py`, che è Python scritto a mano — Q-1 passa da «un giro col team DB» a **una riga più un ramo**. Le altre tre spostano il lavoro: la vista si chiama `vw_rate_fuori_capienza` e contiene **due** popolazioni (sovra-incasso *e* movimento contrario), la forzatura **non è un flag di payload** ma due colonne della riga (`forzata`, `motivo_forzatura`) che restano scritte e che l'elenco a valle legge, e `fn_get_or_create_vendite_contabile` **ha cambiato firma** (via `p_compensazione_id`, D15-e). ⭐ **I nove prerequisiti DB diventano tre**: due viste sono state consegnate senza che nessuno le chiedesse (`vw_rate_fuori_capienza` col lotto 5, `vw_eccedenze_da_sistemare` col lotto 7, e la seconda porta già il raggruppamento per cliente in finestra), due non erano del DB, uno è diventato lavoro BE di verifica. Restano **quattro seed di lista** (che genero io in bozza con `scripts/gen_seed_lista.py`, un round-trip invece di quattro). ✅ **BE-1 riverificata con uno script e non a campione**: 778 codici su 778 hanno la classe, e tutti i codici del cantiere hanno anche il ripiego — la coda che il piano DB elenca in cinque punti **è chiusa**. 📮 Restano **due code di lotto** che sono lavoro di minuti e vanno in slice 0: il ripiego di `E_RIGA_CONTABILE_DISTINTA_FINALE` porta ancora la frase vecchia, e tre codici marcati obsoleti il 22/08 sono ancora nel ripiego (BE-10). 🔴 **E la revisione ha trovato una cosa che nessuno dei tre brief dice**: `fn_get_saldo_rata` risponde **tre** numeri (registrato, in lavorazione, **incassato**) e `fn_get_saldo_fattura` ne risponde **due** — cioè la distinzione che §2.4 dichiara obbligatoria *«nella prima misura che si scrive»* esiste sulla rata e **non** sulla fattura, che è il livello che l'operatore guarda per primo. È **Q-10**, l'unica domanda nuova, e le due strade alternative sono peggiori entrambe (sommare le rate perde il fondo fattura, che ha fattura senza rata; riscrivere la formula nel BE crea due sedi per la stessa regola). ⭐ **Piano riordinato per valore**: le sette slice non hanno più dipendenze DB, la **registrazione sale da terza a seconda**, e la sola cosa che resta bloccata non è codice ma **dato** — senza il conto `uso = 'INCASSO'` dei due emittenti nessun canale di incasso è creabile (DATO-1), e con esso si ferma la sola slice 4. ⚠️ **Un vincolo nuovo dal lotto 6** (§2.6): `pagamenti.*` pretende `app.ruolo_applicativo = 'OPERATORE'` per leggere **e** per scrivere; verificato che middleware e worker della coda la impostano già, resta da controllare ciò che gira fuori da entrambi. Domande: restano **nove** — **Q-9 si è chiusa senza essere decisa** (le viste erano già lì, i seed si chiedono insieme), **Q-1 e Q-8 sono crollate di prezzo** senza cambiare risposta, e nasce Q-10, l'unica che tocca il modello |
| 2026-08-22 | Stesura. Terreno BE/FE misurato **sul codice**, non sui brief. ⭐ **Sei cose risultavano già fatte** e i due brief esistenti non lo sapevano: BE-1 chiusa, i quattro cataloghi in whitelist, `fn_get_lookup_codici` che filtra già `obsoleto_dal`, l'area a catalogo, il dominio in `DOMAINS` e la sua chiave i18n. 🔴 **Vuoto per davvero**: `urls_v1.py` inesistente, `views.py` una riga di commento, `DOMAIN_MENUS['pagamenti']` a `[]`, e **nessuna** `ui.lista_definizione` di `pagamenti` — da cui il fatto che pesava di più: **ogni lista costa un prerequisito DB**. Piano in **sette slice** agganciate ai lotti DB, di cui tre eseguibili subito. 🔴 Due prerequisiti che il piano DB non conteneva (spezzatura di una riga, lookup delle rate) e un problema di confine: un rifiuto *confermabile* esce sul filo come un errore qualunque. Nove domande aperte |
