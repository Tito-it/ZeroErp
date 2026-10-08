# Brief DB — L'istanza nasce col BA, sempre

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-08. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§5), che **attende** la consegna DB.
> **Origine:** D10-bis di
> [migliorie-generali-BE-FE-da-test-valutazione.md](migliorie-generali-BE-FE-da-test-valutazione.md):
> chiudendo il restore per id del lookup istanze, che leggeva istanze di qualunque emittente,
> è emerso che la regola di scope «un'istanza è dell'emittente del suo BA» ha un buco
> **solo** se un'istanza può esistere senza BA. Il DB oggi lo ammette.
> **Decisione:** di Tid, 2026-10-08 — *«la regola giusta è che nascono insieme e deve essere
> sempre così; l'unica cosa che rimane non assegnata è il codice, che deve essere fatto prima
> dell'emissione della prima fattura»*.
> **Stato:** ⏳ da fare, lato DB. D-1 (§3) ha la preferenza di Tid (2026-10-08): il codice del
> BA alla prima fattura. **L'analisi di dettaglio di R-3 la fa Tid con il team DB.**

## 1. La regola

**Istanza e billing account nascono insieme, nella stessa transazione, sempre.** Un'istanza
senza BA non è uno stato del ciclo di vita (non c'è una «fase prospect» con la sola istanza):
è un dato fuori regola.

L'**unico** elemento che può restare non assegnato alla nascita è il **codice**, e va
assegnato **prima dell'emissione della prima fattura**.

## 2. Che cosa dice oggi il DB (contratto, letto dalla doc auto-generata)

| Sede | Che cosa ammette | Con la regola |
| --- | --- | --- |
| `anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata` (constraint trigger, al COMMIT) | basta **uno** fra tre satelliti: `billing_account`, `istanze_dati_precontrattuali`, `clienti`. Con la sola riga precontrattuale l'istanza nasce **senza BA** | 🔴 il BA deve esserci sempre |
| `vendite.preventivi.billing_account_id` | **nullable** (l'istanza è NOT NULL) | 🔴 asimmetria: su `offerte_commerciali` e `contratti` è **NOT NULL** |
| `anagrafiche.billing_account.codice` | NOT NULL, generato **all'INSERT** (`trgfn_billing_account_gen_codice`) e bloccato (`trgfn_lock_columns`) | 🟡 vedi D-1 |
| Guida [generazione-cliente.md](../../guide/generazione-cliente.md) §«Pre-contrattuale» | «Soggetto → Istanza → [pausa, **anche indefinita**] → Ruolo CLIENTE + BA»; «un'istanza può legittimamente restare in pausa per sempre» | 🔴 da riscrivere |

⭐ L'applicazione rispetta già la regola: l'unico punto del backend che crea un'istanza è
l'orchestratore cliente (`ClienteService`, `apps/anagrafiche/services/clienti_service.py`), che
crea ruolo CLIENTE → istanza → BA → cliente nella stessa transazione. Il buco è nel **contratto**
del DB, non nell'uso di oggi: un'importazione, uno script o una schermata futura potrebbero
creare l'istanza da sola, e il DB non direbbe niente.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **Il trigger pretende il BA.** `trgfn_istanze_utilities_require_utility_dichiarata` (o il guard che il team DB ritiene giusto) rifiuta al COMMIT un'istanza senza almeno un `billing_account`. `istanze_dati_precontrattuali` e `clienti` restano satelliti di **dati**, non sostituti del BA. Il codice d'errore: riusare `E_ISTANZA_UTILITY_SENZA_UTILITY` solo se il significato tiene, altrimenti codice nuovo (e allora policy generata **e** frase di ripiego lato BE). Allineare anche `script.fn_check_utility_istanza_coerenza`, che dichiara la stessa lista di satelliti |
| **R-2** | **Simmetria dei precontrattuali.** Con la regola ogni istanza ha il suo BA (1:1 per utility, `uq (istanza_utility_id, utility_id)`): `vendite.preventivi.billing_account_id` diventa NOT NULL come su offerte e contratti, oppure si **deriva** dall'istanza. La forma la sceglie il team DB |
| **R-3** | **Il codice del BA prima della prima fattura** — dopo la risposta a D-1. Se il codice differito è quello del BA: `codice` nullable alla nascita, assegnato da un punto unico (e quale: l'emissione della fattura, o un verbo esplicito), e un guard sull'emissione della **prima** fattura che lo pretenda. Il `lock_columns` resta, ma da NULL a valorizzato una volta sola |
| **R-4** | **La guida** `generazione-cliente.md` §«Pre-contrattuale» va riscritta sulla regola (niente pausa con la sola istanza). Le pagine `manual/` di `istanze_utilities` e `billing_account` se ne parlano |
| **R-5** | **Le righe che oggi sono fuori regola** (istanze senza BA, preventivi senza BA): prima del vincolo, decidere con Tid se si correggono a mano o con un changeSet. ⛔ Il loro numero non decide la regola: entra solo come fatto datato |
| **R-6** | pgTAP: istanza con il solo satellite precontrattuale → rifiutata al COMMIT; istanza + BA nella stessa transazione → ammessa; preventivo senza BA → secondo la forma di R-2; (dopo D-1) prima fattura su BA senza codice → secondo R-3 |

**D-1 — risposta di Tid (2026-10-08):** il differito è il **codice del BA**. Preferenza: il
codice si genera **alla prima fattura**, non alla nascita del BA. Oggi
`billing_account.codice` è NOT NULL, generato all'inserimento e bloccato: R-3 è quindi un
cambio di modello. ⏳ **L'analisi di dettaglio** (punto unico di generazione, guard sulla
prima fattura, NULL nelle liste e nei lookup, numerazione, documenti precontrattuali e
ordini/DDT che mostrano il codice prima della fattura) **la fa Tid con il team DB**: questo
brief non la anticipa. R-1, R-2, R-4, R-5 e R-6 non ne dipendono e possono partire.

## 4. Fuori da questo brief

* Lo **scope** del lookup istanze resta «un'istanza è dell'emittente del suo BA»
  (`script.fn_check_ba_visible_for_emittenti`): con la regola è completo, e non serve una
  funzione di scope nuova. Il BE l'ha già applicata anche al restore per id (2026-10-08,
  D10-bis): con R-1 il caso «istanza senza BA invisibile a un operatore» smette di esistere.

## 5. Ricaduta BE/FE (dopo la consegna DB)

* Commenti da riscrivere sulla regola: `apps/anagrafiche/services/istanze_utility_service.py` e
  `apps/anagrafiche/db/istanze_utility_repository.py` («preventivi prospect senza BA», «istanze
  totalmente orfane»), `apps/anagrafiche/db/soggetti_repository.py` («prospect puri: hanno solo
  istanze, il ruolo CL nasce col BA»).
* FE: il badge «Solo istanza» di `core/components/IstanzaUtilityLookup.vue` (istanza orfana) e la
  chiave `solo_istanza_badge` perdono il caso: si tolgono.
* Se R-1 porta un codice d'errore nuovo: policy generata **e** frase di ripiego.
* Se R-3 rende il codice del BA nullable: le liste e i lookup che lo mostrano (`ba_codice`)
  devono reggere il NULL.
