# Brief DB · BE · FE — Il catalogo degli oggetti e chi li applica

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-26. **A chi:** Tid
> (decisioni, §4), poi team DB (`dev/db-tid`) per il catalogo, poi backend e
> frontend per l'applicazione.
> **Origine:** rilettura di
> [permessi-e-autorizzazioni-v3.md](permessi-e-autorizzazioni-v3.md), 2026-09-26.
> La sua tabella «Stato attivazione» era vecchia, e il confronto con il codice
> ha trovato il difetto di questo brief.
> **Stato:** ✅ **D-1 → D-6 decise da Tid** (D-1 il 2026-09-26, le altre il
> 2026-09-27, §4). ✅ **§3.1 lato DB applicato** da Tid il 2026-09-28 alle
> 00:09 (`20260928-01…05` EXECUTED) e **pgTAP verdi** (corsa di Tid, stesso
> giorno): catalogo in CSV con `offerta_commerciale` e `uom_tipi`,
> `billing_account` fuori, 10 riservati, FK composita attiva. Verificati a DB:
> 23 righe di catalogo, 10 `riservato = t`, nessun `billing_account`,
> `fk_user_override_oggetti_catalogo` presente, riga di policy a `false`.
> ⏳ **Tocca al BE**: le quattro ricadute del §3.1-bis («Al BE») — ⛔ la prima
> è un test Django che **ora** è rosso contro il DB (`test_pannello_verbo_db`).
> Restano fuori catalogo `ordine`, `ddt`, `contratto`, `reso`, finché il BE non
> li applica (poi: una riga nel CSV). 🟡 Caso A in corso lato BE/FE (§3.2, §3.3).
>
> **In una riga:** il pannello permessi offre override su oggetti che nessuno
> applica, e su altri oggetti, che vengono applicati, non lo offre.
> Su una schermata di sicurezza, il primo caso è un override che **mente**.

---

## 1. Il difetto, sul modello

Un **oggetto** (`app_label`, `model_name`) ha un livello proprio, che vince su
quello della sua area (`fn_resolve_livello_oggetto`: override per oggetto,
altrimenti la catena d'area). Il livello si chiede in **quattro porte**:

| Porta | Dove | Come chiede l'oggetto |
| --- | --- | --- |
| **BE** | `core/api/permissions.py`, `valuta` | `model_permission` sulla view (o il `queryset` ORM, oggi non usato da nessuna rotta) |
| **FE** | `useReadonlyMode(area, model)` | `READONLY_MODELS` in `core/constants.js` |
| **DB** | `config.fn_pannello_scrivi` → `script.fn_guard_livello` | la chiave `(app_label, model_name)` di `config.tabelle_gestibili` |
| **Catalogo** | `config.area_model_overrides` | l'elenco di ciò che il pannello permette di **personalizzare** (`put_override_oggetti` rifiuta tutto il resto) |

Il modello chiede che le quattro porte dicano la stessa cosa, e nessuno lo
controlla. Ne escono due difetti simmetrici:

- **A — a catalogo, ma non applicato.** L'amministratore scrive un override,
  il pannello lo mostra come «Override», e nessuna richiesta lo guarda.
  Oppure lo guarda una rotta sola (le note), mentre il documento resta
  governato dall'area;
- **B — applicato, ma non a catalogo.** Il BE o il FE chiedono il livello
  dell'oggetto, ma il pannello non permette di impostarlo: vale sempre
  l'area. Non concede niente di più, ma l'oggetto dichiarato
  «configurabile» dal codice non lo è.

⚠️ C'è un terzo caso, più insidioso: **applicato dal FE ma non dal BE**. Il FE
chiede il livello del `ddt` e il BE, sulle rotte del DDT, chiede quello di
`vendite`. Oggi coincidono, perché senza catalogo non esistono override e
l'oggetto ricade sull'area. **Divergono il giorno stesso in cui l'oggetto entra
a catalogo**: un `BLOCCATO` sul DDT nasconderebbe i pulsanti e lascerebbe
aperta l'API. Per questo A e B si chiudono **insieme**, per oggetto, su tutte
e quattro le porte.

---

## 2. L'inventario

📌 *Fatto datato (2026-09-26, `dbdev` e `dev/backend-tid`), non motivo.* Serve
a sapere **dove** mettere le mani, non **se** farlo: la regola del §1 vale
anche per un oggetto solo.

Rotte BE contate dal resolver degli URL (tutte le rotte montate, per prefisso).

| Oggetto | Catalogo | BE — rotte con `model_permission` | FE `READONLY_MODELS` | Caso |
| --- | :---: | --- | :---: | --- |
| `anagrafiche.soggetto` | ✅ | 16 | ✅ | ✅ allineato |
| `anagrafiche.cliente` | ✅ | 3 | ✅ | ✅ |
| `anagrafiche.fornitore` | ✅ | 3 | ✅ | ✅ |
| `anagrafiche.conto_bancario` | ✅ | 6 | ✅ | ✅ |
| `catalogo.articolo` | ✅ | 12 | ✅ | ✅ |
| `catalogo.unita_misura` | ✅ | 5 | ✅ | ✅ |
| `vendite.promo_articolo` | ✅ | 2 | ✅ | ✅ |
| `vendite.fattura` | ✅ | 6 su 17 (fuori: documenti, stampe, passaggi) | ✅ | **A** parziale |
| `anagrafiche.billing_account` | ✅ | 0 (6 rotte, 5 senza area) | — | **A** |
| `vendite.listino` | ✅ | 0 su 17 | — | **A** |
| `pratiche.pratica` | ✅ | 0 su 51 (19 senza area) | — | **A** |
| `vendite.preventivo` | ✅ | 2 su 38 (solo note) | — | **A** parziale |
| `vendite.offerta_commerciale` | — | 2 su 30 (solo note) | ✅ | **B** + FE ≠ BE |
| `vendite.ordine` | — | 2 su 29 (solo note) | ✅ | **B** + FE ≠ BE |
| `vendite.ddt` | — | 2 su 27 (solo note) | ✅ | **B** + FE ≠ BE |
| `vendite.contratto` | — | 2 su 26 (solo note) | ✅ | **B** + FE ≠ BE |
| `vendite.reso` | — | 0 su 19 | ✅ | **B** + FE ≠ BE |
| `catalogo.uom_tipi` | — | 2 | ✅ | **B** |

In più, la porta DB: `config.tabelle_gestibili` porta **88** chiavi di
oggetto, di cui solo `catalogo.unita_misura`, `catalogo.uom_tipi` e
`vendite.listino` coincidono con oggetti della tabella sopra. Le altre non sono
a catalogo e ricadono sull'area. Se sia giusto lo decide la D-2.

---

## 3. Cosa si chiede

### 3.1 DB (team DB)

1. **Catalogo**: le righe per gli oggetti del caso **B** che D-2 conferma
   (`offerta_commerciale`, `ordine`, `ddt`, `contratto`, `reso`, `uom_tipi`),
   nella forma che `linee-guida-sql §11.2` prescrive per `80_data`. Il seed di
   oggi (`20260410-11`, `INSERT … ON CONFLICT` in `runOnChange`) è da
   rileggere con la stessa regola.
2. **D-5**: togliere `('anagrafiche', 'billing_account')` dal catalogo, e con
   lui gli override già scritti su quell'oggetto (in `config.user_override_oggetti`
   e, se ci sono, sui profili): da quel giorno vale `cliente`.
3. **D-3**: il seed del catalogo in un **CSV** leggibile dal test Django (oggi è
   SQL dentro lo YAML `20260410-11`, più `20260418-01` per la promo).
4. **D-4**: la regola «un override per oggetto esiste solo per un oggetto a
   catalogo, e non riservato» vive **solo** nel backend
   (`put_override_oggetti` + `_MODEL_OVERRIDE_RISERVATI`).
   `config.user_override_oggetti` non ha né FK né guard verso il catalogo.

### 3.1-bis DB — cosa è stato scritto (2026-09-28, applicato alle 00:09, pgTAP verdi)

| changeSet | Cosa |
| --- | --- |
| `00_schema/config/20260928-01` | `area_model_overrides.riservato` (boolean NOT NULL DEFAULT false) e UNIQUE `(app_label, model_name, riservato)`, bersaglio della FK. COMMENT della tabella riscritto: è il catalogo degli oggetti, non una «eccezione rara» |
| `00_schema/config/20260928-02` | **D-5**: via gli override su `billing_account`; controllo che si ferma con l'elenco se restano override fuori catalogo; **D-4**: `user_override_oggetti.riservato` **generata** a `false` e FK composita `fk_user_override_oggetti_catalogo` `(app_label, model_name, riservato)` → catalogo |
| `80_data/changelog/20260928-03` + `sql/config/area_model_overrides.csv` | **D-3**: il catalogo in CSV, mirror `loadUpdateData` sulla chiave naturale. 23 righe: le 12 di prima **meno** `billing_account`, **più** `offerta_commerciale` e `uom_tipi` (caso B), **più** i 10 riservati di `_MODEL_OVERRIDE_RISERVATI` (area = il loro schema: `fn_area_di_oggetto` risponde come prima) |
| `80_data/changelog/20260928-04` | `DELETE` della riga `billing_account` dal catalogo (il mirror non cancella) |
| `80_data/changelog/20260928-05` + `sql/config/fk_index_policy_catalogo_oggetti.csv` | la FK nuova nella policy degli indici, `consentito = false` |
| ⛔ cancellati `20260410-11` e `20260418-01` | i due seed SQL del catalogo (`INSERT … ON CONFLICT DO NOTHING`): una tabella, un CSV (§11.2). Le righe in `databasechangelog` restano orfane |

**Perché solo `offerta_commerciale` e `uom_tipi` del caso B.** Sono gli unici
che tutte le porte chiedono già: l'offerta su tutte le 30 rotte (BE del
2026-09-27), `uom_tipi` sulle sue due; il FE li ha in `READONLY_MODELS`; il
pannello config chiede la stessa chiave. `ordine`, `ddt`, `contratto`, `reso`
no: il BE chiede ancora l'area sulle loro rotte principali, e un `BLOCCATO` a
catalogo nasconderebbe i pulsanti lasciando aperta l'API (§1, terzo caso).
**Entrano il giorno in cui il BE li applica**: una riga nel CSV.

**Perché i riservati a catalogo e non fuori.** Con la sola FK, un oggetto
fuori catalogo è già rifiutato. Ma la blacklist esisteva per un seed futuro
che mettesse a catalogo, per errore, una tabella del kernel: dichiarandole
`riservato = true`, quella riga c'è già, e renderla personalizzabile è un
cambio visibile nel diff del CSV, non un'aggiunta silenziosa.

**Prova fatta (2026-09-28) su `zeroerp_ci`, da owner, SQL estratto** dai due
changeSet di schema, l'upsert del CSV come lo fa il mirror e il `DELETE` della
-04, in transazione annullata: 23 righe, `billing_account` fuori. Con quell'SQL
in testa: il pgTAP nuovo 12/12, `test-fn-pannello-scrivi-v1` 15/15,
`test-permessi-user-overrides` 18/18, `test-permessi-funzioni-risoluzione`
34/34, `test-fn-guard-livello-v1` 12/12, `test-fn-guard-azione-v1` 9/9,
`test-permessi-strutture-base` 22/22. **Controprova**: le versioni di HEAD di
tre di quei file, con la FK in testa, muoiono su
`fk_user_override_oggetti_catalogo` — le correzioni servivano. Il vincolo
stesso provato prima su tabelle temporanee (PG 18.6): la FK composita su una
colonna generata è ammessa.

**pgTAP:**

- nuovo `db/pgtap/config/test-catalogo-oggetti-override-v1.sql` (12 test):
  la forma, i sei casi del vincolo su oggetti **costruiti** (compreso il
  catalogo che cambia sotto un override), il seed (`billing_account` fuori,
  offerta e `uom_tipi` dentro, i dieci riservati, nessun caso B non applicato);
- `test-fn-pannello-scrivi-v1`: il vecchio test 11 concedeva TUTTO con un
  override su `(magazzino, causali)`, cioè proprio ciò che la **D-2** esclude.
  Ora sono due test: l'override è rifiutato (11), TUTTO sull'**area** della
  riga scrive (12). Plan 14 → 15;
- `test-fn-guard-livello-v1`, `test-fn-guard-azione-v1`: l'oggetto di
  fixture `pgtap_modello` entra a catalogo nella transazione del test;
- `test-permessi-funzioni-risoluzione`: `'fatture'` → `'fattura'`;
  `test-permessi-user-overrides`: `'lotto'` → `'preventivo'` (con `'lotto'`
  il test delle date passava solo perché il guard `BEFORE ROW` scatta prima
  della FK).

**Doc:** guida `architettura-permessi-e-autorizzazioni` (§2.1, §4.3, §9.3),
`manual/area_model_overrides.md` riscritta, `manual/user_override_oggetti.md`.

#### ⛔ Al BE — nello stesso rilascio (dev/backend-tid) — ⏳ aperte al 2026-09-28

1. **Rosso in CI se non segue**:
   `backend/apps/core/tests/db/test_pannello_verbo_db.py`,
   `_livello_sulle_causali` scrive un override su `('magazzino', 'causali')`:
   dopo l'apply è una violazione di FK. Per la D-2 il livello si dà
   sull'**area** (`config.user_override_aree`, area `magazzino`), come il
   test 12 del pgTAP del pannello.
2. `PermissionResolver.list_model_overrides_grouped` (permessi effettivi)
   legge **tutto** il catalogo: senza `WHERE NOT amo.riservato` mostra i dieci
   oggetti del kernel come oggetti dell'area.
3. `AmmSoftwareRepository.list_model_overrides`: `can_override` da
   `NOT riservato`, e `_MODEL_OVERRIDE_RISERVATI` si **ritira** (regola del 2:
   due elenchi dei riservati divergono). Il controllo del service può
   restare per il messaggio, leggendo la colonna; il rifiuto vero è la FK
   (23503 su `fk_user_override_oggetti_catalogo`): va verificato che
   `translate_db_errors` la renda come errore di validazione, non come 500.
   Il commento sopra la costante cita il seed `20260410-11`, cancellato.
4. **D-3**: `test_catalogo_oggetti_rotte.py` legge
   `80_data/sql/config/area_model_overrides.csv`; il verso «voce a catalogo
   senza rotte» esclude le righe `riservato = t`; `uom_tipi` ha il suo
   perimetro.

### 3.2 BE (noi, dopo il DB)

1. **Caso A**: `model_permission` su **tutte** le rotte che leggono o
   scrivono l'oggetto o le sue parti (righe, allegati, stati), non solo sulle
   note. Per `pratica` e `billing_account` vanno prima rilette le rotte
   **senza area** (19 + 5), che oggi il resolver non vede.
2. **Caso B**: lo stesso, sulle rotte principali di offerte, ordini, DDT,
   contratti e resi, **nello stesso rilascio** in cui il DB li mette a
   catalogo (§1, il terzo caso).
3. **Il presidio** di D-3.

✅ **Caso A lato BE, 2026-09-27 (non committato)**:

- `model_permission` su **58 view** scritte a mano: `fattura` (passaggi, fatture
  del lotto e loro export), `preventivo` (tutte le rotte senza azione di
  processo), `listino` (le rotte `vendite/listini/…` e il lookup
  `listini-selezionabili-contratto`, D-6), `pratica` (pratica, flussi,
  allegati, note, `coda-lavoro`, `prendi-in-carico`); `billing-account/<id>/utilities/`
  chiede `cliente` (D-5).
- Le quattro factory che servono più documenti (`build_documenti_sorgente_views`,
  `build_passaggi_view`, `build_riepilogo_iva_view`,
  `build_indirizzi_documento_views`) prendono un parametro `model_permission`:
  un solo punto di trasporto per documento, che il caso B riusa passando il
  suo oggetto. Nella factory dei documenti area e oggetto si assegnano ora in un
  solo ciclo (erano otto righe per l'area).
- Restano sull'area, per scelta scritta nel presidio: `competenze-flussi`,
  `formule-tempo`, `operatori` (non sono la pratica); le rotte `definizioni/`
  sono `AdminAPIView`.
- Presidio `core/tests/test_catalogo_oggetti_rotte.py` (dal percorso reale): ogni
  rotta del perimetro di un oggetto chiede quell'oggetto, o un'azione di
  processo su ogni metodo, o è un lookup cross-dominio / una rotta admin.
  Provato che morde (tolto un `model_permission`: rosso sulla rotta giusta).
  Diventa il presidio della D-3 quando il catalogo sarà CSV.
- Test: vendite, pratiche, documenti, anagrafiche, ai_assistant, core.api verdi
  (3594); ruff pulito.

✅ **Caso B, `offerta_commerciale`, lato BE — 2026-09-27 (Tid «correggi»,
non committato)**, prima del catalogo e non «nello stesso rilascio»: la
ragione del §1 è il catalogo **senza** il BE (un `BLOCCATO` che nasconde i
pulsanti e lascia aperta l'API); il BE che chiede l'oggetto **prima** del
catalogo non cambia niente — senza override vale l'area, come ieri — e il
giorno in cui la riga entra le quattro porte dicono già la stessa cosa.
`model_permission` su tutte le 30 rotte `vendite/offerte/…` (16 view a mano,
le factory di documenti, passaggi e indirizzi, i form-defaults, più note e
revisioni che l'avevano già); l'offerta è nel presidio con il suo perimetro.
⏳ Resta la riga di catalogo al team DB (§3.1 punto 1).

### 3.3 FE (noi)

- `useReadonlyMode(area, model)` sulle viste di `billing_account`, `listino`,
  `pratica`, `preventivo`: oggi chiedono la sola area, o ereditano dal padre.

---

## 4. Decisioni per Tid

| | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | Si chiudono sia A sia B? | ✅ **DECISA (Tid, 2026-09-26): sì, tutti e due.** Nessuna voce esce dal catalogo: quelle non applicate si applicano. ⚠️ Un'eccezione, decisa con la D-5 |
| **D-2** | Le 88 chiavi di `tabelle_gestibili` sono oggetti **personalizzabili** dal pannello operatore? | ✅ **DECISA (Tid, 2026-09-27), come proposto.** **No, restano chiavi d'area.** La chiave del pannello serve a dire **a quale area** appartiene una tabella di configurazione (`fn_area_di_oggetto`), e il permesso ricade sull'area. Metterle a catalogo darebbe 88 righe al pannello operatore, e una parte è riservata (`config.profili_accesso` è sia nel pannello sia in `_MODEL_OVERRIDE_RISERVATI`). La regola si scrive esplicita: «una chiave di oggetto non a catalogo vale come la sua area». Il pgTAP del pannello la dichiara |
| **D-3** | Come si impedisce che il disallineamento torni? | ✅ **DECISA (Tid, 2026-09-27), come proposto.** Un test che confronta **catalogo e porte**. Il catalogo sta nel seed, le porte nel codice: un test Django legge il seed del catalogo e il resolver degli URL (come per l'inventario del §2), e fallisce se un `model_permission` non è a catalogo, **o** se una voce a catalogo non ha nessuna rotta. Lo stesso test legge `READONLY_MODELS`. ⚠️ Richiede che il seed sia un file leggibile (CSV), non SQL dentro uno YAML: si lega al §3.1 punto 1 |
| **D-4** | La regola «override solo su oggetti a catalogo, non riservati» si porta a DB? | ✅ **DECISA (Tid, 2026-09-27), come proposto.** **Sì, per coerenza DB-first**: oggi una scrittura che non passa dal service la aggira. Forma a scelta del team DB (FK composita verso il catalogo + colonna `riservato` nel catalogo al posto della blacklist Python) |

| **D-5** | `anagrafiche.billing_account` è a catalogo, ma non ha rotte proprie: si crea e si modifica **dentro la scheda cliente** (`ClientiView.post` crea istanza + BA + cliente in una transazione; il PATCH porta i campi `ba_*`), che chiede il solo oggetto `cliente`. Un override sul BA quindi non ha effetto | ✅ **DECISA (Tid, 2026-09-27): il billing account è un pezzo del cliente, il permesso è sempre `cliente`.** La voce `billing_account` **esce dal catalogo** (eccezione dichiarata alla D-1: un oggetto senza schermate proprie non si può applicare, quindi un suo override mentirebbe per costruzione). Le rotte che leggono il BA nell'area anagrafiche chiedono `cliente`; i lookup cross-dominio (`skip_area_check`) restano liberi |
| **D-6** | Lookup e widget **della stessa area** che leggono l'oggetto (es. `lookup/listini-selezionabili-contratto`, `listini/alert-scadenze`, `pratiche/coda-lavoro`) prendono il suo `model_permission`? | ✅ **DECISA (Tid, 2026-09-27): sì.** Un listino `BLOCCATO` non si vede da nessuna parte nella sua area, come il FE che nasconde. I lookup cross-dominio con `skip_area_check` restano liberi (catalogo BB backend, «lookup cross-dominio su sub-resource») |

---

## 5. Fuori da questo brief

- **La v3** (sotto-oggetti padre/figlio): dormiente, e dipende dal tetto
  d'area. Questo brief sistema il modello **piatto** che c'è già.
- **Il tetto d'area** (`.codex/PROJECT_CONTEXT.md` § «Aperto»): un override
  per oggetto **sostituisce** il livello dell'area, non lo limita. Non cambia
  qui.
- Le **azioni di processo**: si applicano con `check_azione`, non col livello
  d'oggetto, e non sono toccate.
