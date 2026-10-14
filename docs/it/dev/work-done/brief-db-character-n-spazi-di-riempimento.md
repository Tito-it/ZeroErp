# Brief DB — Un testo non si riempie di spazi: `character(n)` dove la lunghezza varia

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10, su segnalazione della sessione BE.
> **A chi:** team DB; team BE/FE per il §6 (nessuna modifica obbligatoria, solo verifiche).
> **Origine:** nella ricerca del comune il drawer mostra `Potenza (PZ        )`. La sessione BE ha
> trovato la causa nel tipo di `config.province.sigla` e proposto un brief
> `brief-db-province-sigla-varchar`. Nell'analisi DB il perimetro risulta più largo della sola
> sigla (§2), quindi il brief ha un nome più generale.
> **Stato:** ✅ **lato DB chiuso** (2026-10-10): D-1…D-6 applicate da Tid (`20261010-26` … `-40`),
> corse pgTAP verdi. ✅ **Lato BE/FE fatto** il 2026-10-10 (§6.1). ✅ **Collaudo a video superato** (R-2,
> Tid, 2026-10-10). ✅ **Chiuso e archiviato il 2026-10-10.** Il seguito (verbo di scrittura dei dati
> societari, forma giuridica non legata alla natura) sta in
> `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md` (§8).
> **Da leggere per primo:** §6 (richieste a BE/FE), poi §7 per cosa è cambiato a DB.

## 1. Il difetto, sul modello

In PostgreSQL `character(n)` è un testo **a lunghezza fissa**: un valore più corto viene riempito
di spazi fino a `n`. `PZ` in un `character(10)` viene salvato e letto come `'PZ        '`.

Questo tipo va bene solo quando **ogni** valore ammesso ha esattamente `n` caratteri: in quel caso
non c'è niente da riempire. Se il valore può essere più corto, ogni lettore riceve gli spazi e deve
toglierli. Chi se ne dimentica li mostra all'utente o li scrive in un documento.

La sigla di provincia è dichiarata `character(10)` e nella realtà ha due caratteri. La descrizione
della provincia è `character(80)`, e «Potenza» ne ha sette. Nessuna delle due colonne ha un dominio
a lunghezza fissa.

⛔ **I tamponi a valle non chiudono il difetto.** Il problema è già stato aggirato in tre punti
(§2.3) e nessuno ha corretto il tipo. Ogni lettore nuovo della colonna si ritrova con gli spazi:
il drawer di oggi è il quarto caso. Anche un `.strip()` nel backend sarebbe solo il quinto tampone.

⚠️ **Il tipo dà anche un secondo problema, nelle firme delle funzioni.** `character` senza
lunghezza vale `character(1)`. Inoltre `RETURN QUERY` pretende che il tipo sia identico e rifiuta
`varchar` dove la firma dichiara `bpchar`. Questo ha già rotto per quattro mesi l'autocomplete vie
(`script.fn_search_stradario`, aprile–agosto 2026): il changeSet `20260402-01` aveva convertito il
`codice` di sette tabelle `config` ma non la firma che lo esponeva.
Nota: quel cantiere convertì **solo** le colonne `codice`. `sigla` e `descrizione` della stessa
famiglia rimasero `character(n)`, ed è da lì che arriva la segnalazione di oggi.

## 2. Che cosa dice oggi il DB (contratto, letto il 2026-10-10 su dbdev)

### 2.1 Le colonne `character(n)` il cui dominio non ha lunghezza fissa

| Colonna | Tipo | Dominio reale | Effetto |
| --- | --- | --- | --- |
| `config.province.sigla` | `character(10)` | sigla della provincia (in Italia 2 lettere) | **la segnalazione** |
| `config.province.descrizione` | `character(80)` | nome della provincia | stesso difetto, fino a 73 spazi |
| `anagrafiche.dati_societari.destinatario_fe` | `character(10)` | codice destinatario SDI: 7 caratteri (6 per la PA) | arriva con gli spazi al BE (`soggetti_repository.py:1083`) e in `fn_get_soggetto_dati_by_ruolo`; per la fattura lo toglie un `btrim` (§2.3) |
| `anagrafiche.gestori.descrizione` | `character(50)` | testo libero | idem |
| `anagrafiche.gestori.cd_prod_software` | `character(20)` | codice libero | idem |
| `config.ambiti.descrizione` | `character(100)` | testo libero | idem |
| `config.stati_cliente.descrizione_breve` | `character(20)` | testo libero | idem |
| `anagrafiche.catasto_unita_immobiliari.foglio_catastale`, `particella`, `sezione_catastale`, `subalterno` | `character(5)` | numeri e sigle catastali di lunghezza variabile | idem |
| `magazzino.note*.lingua` (dieci tabelle, la madre partizionata `magazzino.note` compresa) | `character(5)` | codice lingua (`it`, `it-IT`) | esce con gli spazi da `fn_get_note` e dalle tre `fn_get_*_note` |

### 2.2 Le colonne `character(n)` a lunghezza **esatta**

Qui il padding non può nascere: ogni valore ha già `n` caratteri. Restano però esposte al problema
delle firme del §1.

| Colonna | Tipo |
| --- | --- |
| `config.stati.codice_iso2`, `anagrafiche.conti_bancari.paese` | `character(2)` (ISO 3166 alpha-2) |
| `config.stati.codice_iso3`, `config.valute.iso_code` | `character(3)` |
| `anagrafiche.catasto_unita_immobiliari.destinazione_immobile` | `character(2)` |
| flag a un carattere: `soggetti.sesso`, `cliente_pa`, `split_payment`, `clienti.garanzia_tipo`, `istanze_utilities.proprietario_inquilino`, `conti_contabili.tipo_conto`, `stati_cliente.*` (3), `tipi_utenze.tipo_pdr_std`, `catasto.tipo_accatastamento`, `esigibilita` (3 tabelle vendite), `status` di `fatture_log` e `fatturazione_lotti_log` | `character(1)` |
| `storico.*.change_type`, `storico.*.tipo_evento`, `storico.pdp.tipo_operazione` (le tabelle dello storico) | `character(1)` |

### 2.3 I tamponi già presenti (tutti a valle del tipo)

| Dove | Che cosa toglie |
| --- | --- |
| `config.vw_province_lista`, `config.vw_comuni_lista`, `config.vw_codici_postali_lista` | `TRIM` su sigla e descrizione della provincia |
| `script.fn_snapshot_indirizzo`, `script.fn_snapshot_indirizzo_soggetto` | `btrim` su `provincia_sigla` e `stato_iso2` (la Provincia della FatturaPA deve avere due caratteri) |
| `vendite.fn_snapshot_intestazione_fattura` | `btrim` su `pr.sigla` e su `destinatario_fe` |
| `script.fn_get_stradario`, `script.fn_search_stradario` | `p.sigla::text` (la conversione a `text` toglie gli spazi in coda) |
| pgTAP `test-snapshot-intestazione-fattura-v1` (test 7) | presidio: nessun valore dello snapshot ha spazi di riempimento. **Resta valido** anche dopo la correzione |

### 2.4 Chi legge la colonna così com'è (i punti che oggi mostrano gli spazi)

- **Viste**: `script.vw_indirizzo_completo` (`p.sigla AS provincia`), `anagrafiche.vw_dati_societari`,
  `script.vw_ita_province_regioni` e la catena `vw_indirizzi_resolved_*`.
- **Funzioni** con `character` nel `RETURNS TABLE`: `script.fn_get_indirizzo`,
  `script.fn_get_indirizzi_by_ruolo` (`provincia_sigla`, `provincia_descrizione`, `stato_iso2`),
  `script.fn_get_soggetto_dati_by_ruolo` (`provincia_iscri_rea_sigla`, `destinatario_fe`, `sesso`),
  `fn_get_note` e le sue tre sorelle di dominio (`lingua`).
- **Backend** (query SQL scritte nel repository): `core/db/lookup_repository.py:419`
  (autocomplete comuni, la segnalazione), `anagrafiche/db/soggetti_repository.py:293` (comune di
  nascita) e `:1083` (`destinatario_fe`), `anagrafiche/db/geo_repository.py:347` (`list_province`,
  tendina).

### 2.5 Che cosa trascina una `ALTER COLUMN … TYPE` su `config.province`

Verificato da catalogo il 2026-10-10:

- **viste** che leggono `sigla` o `descrizione`, comprese quelle che le leggono indirettamente (14):
  `anagrafiche.vw_dati_societari`, `config.vw_codici_postali_lista`, `config.vw_comuni_lista`,
  `config.vw_province_lista`, `script.vw_indirizzo_completo`, `script.vw_ita_province_regioni` →
  `anagrafiche.vw_indirizzi_dettaglio` → `vw_indirizzi_resolved_base`,
  `vw_istanze_utilities_dettaglio`, `vw_pdp` → `vw_indirizzi_resolved_all`, `_ruolo`, `_soggetto`,
  `vw_istanze_dati_precontrattuali_dettaglio`;
- **funzioni sul tipo riga di quelle viste** (`RETURNS SETOF <vista>`):
  `script.fn_get_indirizzi_by_soggetto(uuid)`,
  `script.fn_get_indirizzo_by_soggetto(uuid, varchar)`,
  `anagrafiche.fn_search_indirizzi_dettaglio(…)`;
- **trigger `UPDATE OF`**: nessuno su `config.province` (`tgattr` vuoto);
- **FK**: `comuni.provincia_id` e `dati_societari.id_prov_iscri_rea` puntano a `province.id`, non
  alla sigla: non sono coinvolte;
- **indice unico** `uq_province_sigla`: PostgreSQL lo ricostruisce da solo durante l'`ALTER`.

È la **stessa catena** che `20260402-01` ha già abbattuto e ricostruito (ordine dei `DROP` e
changeSet di ricostruzione `20260402-03…-10`): si riparte da quel modello, ma i corpi si prendono
dalla doc auto-gen di oggi e non da quegli YAML.

### 2.6 Un controesempio (fatto datato, 2026-10-10, dbdev)

`config.province` contiene una riga con sigla `TEST` (4 caratteri), creata dall'endpoint di
creazione provincia (`geo_repository.create_provincia`, che accetta qualunque sigla). Un `CHECK`
`^[A-Z]{2}$` la rifiuterebbe. Il punto vale sul modello e non sulla riga: **oggi nessuna regola
dice come è fatta una sigla**.

⚠️ Sul modello una provincia può essere estera: `regioni.stato_id` lega la regione a uno stato
qualunque, e `province.regione_id` è nullable. Per questo la regola delle **due lettere** non
dipende dalla sola riga della provincia (vedi D-2).

## 3. Decisioni attese da Tid

| # | Domanda | Proposta della sessione DB |
| --- | --- | --- |
| **D-1** | **Perimetro.** Solo `province` (sigla e descrizione)? Tutto il §2.1? Anche il §2.2? | **Tutto il §2.1 in questo brief**: è lo stesso difetto, e correggerlo a metà ripete `20260402-01`, che sistemò `codice` e lasciò `sigla`. Il **§2.2 resta fuori**: lì il padding non può nascere. Per quelle colonne valgono la regola nuova (D-4) e il registro del presidio (D-5). |
| **D-2** | **Forma della sigla.** Quale `CHECK`? | `varchar(10)` con `CHECK (sigla ~ '^[A-Z0-9]{1,10}$')`: niente spazi, maiuscole, nessun valore vuoto. Le **due lettere** sono una regola della provincia **italiana**, e lo stato si legge da un'altra tabella, quindi non può essere un `CHECK`. La sede proposta è il guard di scrittura di `config.province`, che legge lo stato dalla regione e per l'Italia pretende `^[A-Z]{2}$`. In alternativa si lascia la regola dov'è oggi, nello snapshot della FatturaPA. Decide Tid. |
| **D-3** | **I tamponi del §2.3**: si tolgono? | **Sì, nello stesso giro**, nelle viste e nelle funzioni che i changeSet riscrivono comunque. Un `TRIM` rimasto non fa danni, ma lascia credere al prossimo lettore che il tipo produca ancora spazi. I `btrim` degli snapshot fiscali restano solo se D-2 lascia lì la regola delle due lettere. Il presidio pgTAP test 7 resta comunque. |
| **D-4** | **Regola nuova** in `linee-guida-sql.md`? | Sì: «**`character(n)` non si usa.** Un testo a lunghezza variabile è `varchar(n)` o `text`. Un codice a lunghezza fissa è `varchar(n)` con un `CHECK` sulla forma. Nelle firme delle funzioni non compare mai `character`». La regola si scrive sul modello, non su questi casi. |
| **D-5** | **Presidio** strutturale? | Un pgTAP che rifiuta ogni colonna `bpchar` nuova, con un **registro dichiarato** delle colonne del §2.2 tollerate, e ogni funzione con `character` in firma o nel `RETURNS`. Così il prossimo `character(n)` diventa rosso in CI, invece di arrivare come segnalazione dal drawer. |
| **D-6** | ✅ **Decisa da Tid il 2026-10-10**, dopo una prima versione sbagliata (§7.6): `destinatario_fe` è il **canale** FE, non il codice. | Vocabolario `P`/`C`, nullable; `P` ⇒ PEC, `C` ⇒ codice SDI di 6-7 caratteri maiuscoli o cifre; via gli UNIQUE su `codice_sdi` e `pec_fatturazione`. Dettaglio nel §7.6. |

✅ **D-1 … D-5 accettate da Tid il 2026-10-10** («accetto le tue proposte, procedi»). Come sono
state applicate, e dove il codice si scosta dalla lettera del §4, è nel §7.

## 4. Piano dei changeSet (dopo le decisioni)

Sullo stesso modello di `20260402-01`:

1. **`00_schema`**, un changeSet per tabella (o uno per la catena di `province`):
   - `DROP FUNCTION` delle tre funzioni sul tipo riga delle viste (§2.5), poi `DROP VIEW` dalle
     viste che non hanno dipendenti verso quelle a monte;
   - `ALTER COLUMN … TYPE varchar(n) USING btrim(col)`. È DDL: nessun trigger di riga scatta, e non
     serve nessun `UPDATE` di bonifica. La conversione da `character` a `varchar` toglie già gli
     spazi in coda; `btrim` toglie anche quelli in testa;
   - `ADD CONSTRAINT … CHECK` sulla forma (D-2), e `CHECK (col = btrim(col) AND col <> '')` dove la
     colonna è testo libero.
   ⚠️ Prima dell'`ALTER`, contare le righe che violerebbero il `CHECK`. È un uso legittimo della
   misura: cerca un controesempio (§2.6) e non decide nulla.
2. **`20_code`**, con numero successivo, nella stessa corsa:
   - si ricreano le 14 viste e le 3 funzioni dal **corpo vivo** (doc auto-gen), senza i `TRIM` (D-3);
   - `DROP` + `CREATE` delle funzioni con `character` nel `RETURNS TABLE` (§2.4): cambiare il tipo
     di una colonna del risultato richiede il `DROP`. Firma, `RETURNS TABLE`, `DECLARE` e
     `COMMENT`/`GRANT` vanno **ancorati con `%TYPE`** alla colonna convertita: un `%TYPE` si risolve
     al `CREATE`, quindi va scritto dopo l'`ALTER`. Il controllo si fa riga per riga sul file nuovo;
   - `GRANT` delle funzioni ricreate, come nell'originale.
3. **Censimento dei chiamanti**, prima di consegnare (tre popolazioni):
   - dentro il DB: chi chiama le funzioni ricreate (`pg_proc.prosrc`);
   - fuori dal DB: `grep` nel backend dei nomi delle funzioni e delle colonne del §2.4;
   - chi le verifica: i 13 pgTAP che le nominano (`grep -rlE 'province|provincia_sigla|destinatario_fe|vw_indirizzi_resolved|fn_get_indirizz|fn_get_soggetto_dati_by_ruolo|vw_comuni_lista|vw_province_lista' db/pgtap`).
     Oggi nessuno asserisce il tipo `bpchar`, ma vanno riletti.
4. **Prova** sull'SQL estratto, in transazione annullata. Dopo la ricreazione deve esserci una sola
   funzione per nome, e ogni colonna della catena deve avere il tipo atteso (`pg_attribute`).
   Inoltre `SELECT provincia_sigla FROM script.fn_get_indirizzo(…)` non deve avere spazi.
5. **Manual** di `province` e delle tabelle toccate: si aggiornano il tipo e la regola del `CHECK`.

## 5. Trappole note da non ripetere

- **`%TYPE` in firma è una fotografia.** Le funzioni che ancorano una colonna convertita non si
  aggiornano da sole e vanno ricreate. È il guasto di `fn_search_stradario` del §1.
- **`RETURN QUERY` vuole il tipo identico**: una vista diventata `varchar` sotto una firma ancora
  `bpchar` rompe la chiamata a runtime, non al migrate.
- **Le viste si ricreano dal corpo vivo** e non dagli YAML del 2026-04-02: da allora la catena
  `vw_indirizzi_resolved_*` è stata riscritta più volte (`20260628-09`, `20260927-42`, …).
- **La doc auto-gen non mostra le colonne di un trigger `UPDATE OF`**. Per `province` il catalogo
  dice che non ce ne sono; per le altre tabelle del §2.1 va verificato su `pg_trigger.tgattr`
  prima dell'`ALTER`.
- **Lo storico jsonb** mantiene i valori vecchi con gli spazi nelle righe passate. È storia e non si
  bonifica.

## 6. Richieste a BE/FE

Il lato DB corregge il tipo, quindi **il backend non deve togliere spazi da nessuna parte**: le
query del §2.4 riceveranno valori puliti senza modifiche.

- **R-1 (BE)** — ⛔ **nessun `.strip()`** in uscita su sigla, descrizione o `destinatario_fe`:
  sarebbe il quinto tampone (§1). Se nel frattempo ne è stato aggiunto uno, va tolto dopo l'apply.
- **R-2 (BE/FE)** — dopo l'apply, verifica a video: autocomplete comuni (`Potenza (PZ)`), comune di
  nascita nel dettaglio soggetto, tendina province, dati societari (codice destinatario).
- **R-3 (BE)** — il `.strip().upper()` in **ingresso** di `geo_repository.create_provincia` /
  `update_provincia` può restare: normalizza l'input dell'utente. La regola sulla forma è del DB
  (D-2): una sigla fuori forma torna come **`E_PROVINCIA_SIGLA_NON_VALIDA`** (`P0001`,
  `DATO_ERRATO`, `campo` = `sigla`; `stato_id` se a cambiare è lo stato di una regione), con una
  frase che nomina sigla e provincia. Il `CHECK` resta solo come rete.
- **R-4 (BE)** — codice nuovo `E_PROVINCIA_SIGLA_NON_VALIDA` (id messaggio 1245): rigenerare
  `apps/core/services/error_policies_generated.py` dopo l'apply.
- **R-5 (BE)** — il commento di `geo_repository.list_province_paginated` dice che
  `vw_province_lista` esce «con TRIM»: dal `20261010-27` esce com'è (varchar). Solo il commento.
  I tipi delle colonne delle viste di lista passano da `text` a `varchar(n)`: per Python sono
  `str` uguali.
- **R-6 (BE)** — `anagrafiche.fn_crea_soggetto_pg` cambia identità (`p_destinatario_fe` da
  `character` a `varchar`, `20261010-34`). Il backend la chiama con parametri **nominati**
  (`soggetti_repository.py`): niente da cambiare, ma il test Django che la attraversa va guardato
  dopo l'apply.
- **R-8 (BE)** — tre codici nuovi del canale FE (`E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO`,
  `…_CODICE_SDI_MANCANTE`, `…_PEC_FATTURAZIONE_MANCANTE`, id 1246-1248): rigenerare
  `error_policies_generated.py`, con R-4.
- **R-9 (FE)** — `DatiSocietariForm.vue`: il codice SDI va scritto in maiuscolo (conviene
  trasformarlo mentre si digita); il canale può restare vuoto (`show-clear` è giusto, la colonna
  ora è nullable). Con canale `P` senza PEC, o `C` senza codice, il DB risponde con un errore sul
  campo (`campo` = `pec_fatturazione` / `codice_sdi`): il form può accenderlo.
- **R-10 (BE)** — `soggetti_service`: `destinatario_fe` vuoto arriva come NULL (`optional_str`):
  giusto, ora è ammesso. Nessun cambio.
- **R-7 (FE, facoltativo)** — la sigla della provincia si può validare anche nel form (due
  lettere maiuscole per l'Italia): solo come aiuto, la regola resta del DB.

### 6.1 Lato BE/FE: cosa è stato fatto (2026-10-10, `dev/backend-tid`)

| # | Esito |
| --- | --- |
| R-1 | Niente da togliere: nessun `.strip()` in **uscita** su sigla, descrizione o `destinatario_fe` (quelli di `geo_repository` stanno sull'ingresso, R-3). |
| R-2 | Provato sul DB vero, a livello di dato: `search_comuni("Potenza")` → `'PZ'`, `list_province` → `'AG'`/`'AGRIGENTO'`, colonne `varchar(10)`/`varchar(80)`. ✅ **Collaudo a video di Tid superato** (2026-10-10): autocomplete comuni, comune di nascita, tendina province, dati societari. La forma giuridica vista vuota non è un difetto di questo brief: è la forma salvata fuori dalla matrice della natura (§8). |
| R-3 | L'ingresso resta com'è. Provato con chiamata reale in transazione annullata: `create_provincia` con sigla `ABC` o `P1` in una regione italiana, e `update_provincia` con `XYZ`, escono **400 `E_PROVINCIA_SIGLA_NON_VALIDA`, `fields = ['sigla']`**, con la frase del DB (passa dal middleware: il guard solleva `P0001`, non un `IntegrityError`). |
| R-4, R-8 | `genera_error_policies`: quattro voci aggiunte, tutte `DATO_ERRATO`, **nessuna classe spostata**; `--check` pulito. Aggiunti anche i quattro **ripieghi** senza segnaposto in `error_messages_fallback.py` (cancello `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`). |
| R-5 | Commenti di `geo_repository` (`list_comuni`, `get_provincia`, `list_province_paginated`) riscritti: niente più TRIM, le viste danno `varchar`. |
| R-6 | `fn_crea_soggetto_pg` ha un'identità sola, con `p_destinatario_fe varchar`. I test Django che la attraversano sono verdi (sotto). |
| R-8 (prova) | `UPDATE` reale di una riga di `dati_societari`: `C` senza codice → 400 `…_CODICE_SDI_MANCANTE` `['codice_sdi']`; `P` senza PEC → 400 `…_PEC_FATTURAZIONE_MANCANTE` `['pec_fatturazione']`; `ab12` → 400 `…_CODICE_SDI_NON_VALIDO` `['codice_sdi']`. Canale `X` → `E_DATABASE` (23514), come previsto dal `-39`. |
| R-9 | `DatiSocietariForm.vue`: il codice SDI va in maiuscolo mentre si digita, col BB `InputMaiuscolo` (regola del 2, ok Tid: le stesse righe stavano sull'estensione del civico in `IndirizzoDrawer` e `IndirizzoSoggettoForm`; una correzione in mezzo al testo lascia il cursore dov'era), `maxlength="7"`. `codice_sdi` e `pec_fatturazione` si accendono da `campiErrati`, che `SoggettoDrawer` ora passa al form. `show-clear` sul canale resta. Il payload lo compone `useDatiSocietariForm().toPayload()`: solo ciò che il form mostra, quindi un codice SDI scritto e poi lasciato per il canale `P` non parte più verso il guard, che lo rifiuterebbe su un campo nascosto. Spec: `InputMaiuscolo.spec.js`, `useDatiSocietariForm.spec.js`. |
| R-10 | Nessun cambio. |
| R-7 | Non fatto (facoltativo): la regola resta del DB, e il campo si accende già da `campiErrati`. |

Test: `ZEROERP_TEST_DB_E2E=1 ./manage-test.sh apps.anagrafiche apps.amm_software.tests.db` più i cancelli dei
codici errore (`test_error_policies_divergenza_db`, `test_error_codes_declared_guardrail`,
`test_ui_action_e_canale_campi`, `apps.core.tests.services`): **1508 verdi**. `ruff` ed `eslint` puliti sui file toccati.

### 6.2 Trovato lavorando: in modifica i dati societari non si salvano

⛔ **In modifica i dati societari non si salvano, e nessuno lo dice.** `SoggettoDrawer` riempie
`DatiSocietariForm` anche in modifica e lo lascia modificabile (`:disabled="false"`), ma il ramo di
modifica di `handleSave` non mette `dati_societari` nel payload. Lato BE non c'è un percorso di
scrittura: `SOGGETTO_UPDATE_COLS` non ha quelle colonne, e `dati_societari` si scrive solo alla
creazione (`fn_crea_soggetto_pg`). L'operatore cambia canale, PEC o codice SDI, preme Salva, legge
«salvato», e alla riapertura trova i valori vecchi. C'era già prima di questo brief. Le strade sono
due: un **verbo di scrittura** dei dati societari (a DB, sul modello «una scrittura = un verbo»)
con BE e FE dietro, oppure il form in **sola lettura** in modifica finché quel verbo non c'è.

✅ **Deciso da Tid il 2026-10-10: il verbo di scrittura a DB, con BE e FE dietro** (ex D-7, ora nel
brief del §8).

## 7. Lato DB: cosa è stato fatto (2026-10-10)

### 7.1 I changeSet

Tutti in una corsa: il `00_schema` abbatte la catena e converte, i `20_code` la ricostruiscono
subito dopo per numero.

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/config/20261010-26-alter-character-n-a-varchar` | `DROP` delle 3 funzioni `RETURNS SETOF <vista>` e delle 16 viste (§2.5, più `vw_clienti_lista` e `vw_clienti_codice_ba`, che leggono `stati_cliente.descrizione_breve`); le **12 colonne** del §2.1 diventano `varchar(n)` con la **stessa n** (`USING btrim`, `NULLIF` sulle nullable); i CHECK; `COMMENT` su sigla, descrizione, `destinatario_fe`. `preCondition` HALT: le 12 colonne sono ancora `character(n)` |
| `20_code/config/…-27-recreate-viste-geo-senza-trim` | `vw_province_lista`, `vw_comuni_lista`, `vw_codici_postali_lista` **senza TRIM** (D-3), COMMENT aggiornati |
| `20_code/script/…-28-recreate-vw-indirizzo-completo-e-ita-province` | le due viste di `script`, identiche |
| `20_code/anagrafiche/…-29-recreate-catena-vw-indirizzi` | le 8 viste della catena indirizzi, identiche, dalle radici alle foglie |
| `20_code/anagrafiche/…-30-recreate-vw-dati-societari-e-clienti` | `vw_dati_societari`, `vw_clienti_lista`, `vw_clienti_codice_ba`, identiche |
| `20_code/script/…-31-recreate-fn-sul-tipo-riga-delle-viste-indirizzi` | le 3 funzioni `SETOF` (una **riparata**, §7.3); `fn_search_indirizzi_dettaglio` con firma ancorata dove l'identità non cambia |
| `20_code/script/…-32-update-fn-get-indirizzo-e-by-ruolo-provincia-varchar` | `DROP` + `CREATE`: il `%TYPE` della provincia nel `RETURNS TABLE` si risolve ora a `varchar` |
| `20_code/script/…-33-update-fn-get-soggetto-dati-by-ruolo-varchar` | idem per `provincia_iscri_rea_sigla` e `destinatario_fe` |
| `20_code/anagrafiche/…-34-update-fn-crea-soggetto-pg-destinatario-fe-varchar` | `p_destinatario_fe` è `%TYPE` di una colonna convertita: cambia l'identità, `DROP` della firma vecchia + `CREATE` (niente overload) |
| `20_code/script/…-35-update-fn-get-note-lingua-varchar` | `script.fn_get_note` e i tre wrapper (§7.3) |
| `20_code/config/…-36-create-guard-sigla-provincia` | D-2: `config.fn_sigla_provincia_ammessa` e due guard (§7.2) |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_PROVINCIA_SIGLA_NON_VALIDA` (`DATO_ERRATO`, messaggio id 1245) |

Corpi dal **vivo** (`pg_get_viewdef` / `prosrc`), dichiarazioni dall'ultimo YAML ancorato (firme
con `%TYPE`; tipi espliciti con la ragione scritta dove non c'è una colonna o dove ancorare
cambierebbe l'identità). Opzioni `security_invoker`, `COMMENT` e `GRANT` all'app riprodotti.

### 7.2 D-2: la sigla, in due sedi

- `chk_province_sigla_forma`: `^[A-Z0-9]{1,10}$`, per ogni provincia.
- Guard **`trg_province_a10_guard_sigla_ins_upd`** (BEFORE INSERT OR UPDATE OF `sigla`,
  `regione_id`): due lettere maiuscole se la regione è di uno stato con `codice_iso2 = 'IT'`,
  altrimenti la forma generale. Parla prima del CHECK, con una frase che nomina sigla e provincia.
- Guard **`trg_regioni_a10_guard_sigla_province_upd`** su `config.regioni`: una regione non passa
  all'Italia se una sua provincia ha una sigla che l'Italia non ammette. ⚠️ È **AFTER UPDATE**
  con `WHEN (stato_id cambia)`, non BEFORE: `trg_regioni_normalize_ins_upd` riscrive `stato_id`
  quando è NULL, e scatta dopo un guard `a10` in ordine alfabetico. Un BEFORE vedrebbe il NULL e
  non lo stato finale.
- Il predicato è uno solo (`config.fn_sigla_provincia_ammessa`), letto dai due guard.
- ⚠️ Il guard **non rilegge** le province esistenti. Su dbdev c'è una provincia `TEST` in una
  regione italiana (fatto datato, 2026-10-10). Non blocca l'apply, ma chi la tocca riceve
  l'errore: va **corretta o cancellata a mano** (domanda a Tid, §7.5).

### 7.3 Dove il codice si scosta dal §4, e cosa si è trovato scrivendo

- **CHECK sul testo libero**: `btrim(col) <> ''` (la forma di casa, `chk_*_non_vuot*`), non
  `col = btrim(col) AND col <> ''` come scritto nel §4. Uno spazio scritto da una persona è il suo
  dato, non un padding. Rifiutarlo con un `23514` trasformerebbe un refuso in un errore tecnico.
- **I `btrim` degli snapshot fiscali restano** (`fn_snapshot_indirizzo`, `_soggetto`,
  `fn_snapshot_intestazione_fattura`). Nessun changeSet di questo giro li riscrive, e lo snapshot
  di `stato_iso2` legge ancora un `character(2)`. D-3 li toglieva «dove si riscrive comunque».
- ⛔ **Trovato: `script.fn_get_indirizzi_by_soggetto` era rotta su dbdev.** Dichiara `RETURNS
  SETOF vw_indirizzi_resolved_soggetto` ma proiettava `r.*` da `vw_indirizzi_resolved_base`, che
  dopo il suo `CREATE` (`20260402-08`) ha guadagnato colonne. Ogni chiamata moriva con
  «l'istruzione finale restituisce troppe colonne». Il pgTAP `test-indirizzi-fallback` era nei
  registri dei rossi come `ERRORE_FIXTURE`, che nascondeva il difetto. Riparata nel `-31`: legge
  la vista che dichiara (stesso filtro `scope = SOGGETTO`, stesse righe).
- **Trovato: `script.fn_get_note` gli spazi li fabbricava lei**: `l.codice_iso::char(5)`, da un
  `config.lingue.codice_iso` che è già `varchar(5)`. Tolto il cast. Lingua e stile si ancorano al
  loro vocabolario, e i tre wrapper (vendite, acquisti, magazzino) seguono. Il wrapper di
  magazzino legge `magazzino.note`, quindi il suo `RETURNS` si ancora a quella tabella.
- **`fn_crea_soggetto_pg` cambia identità** (`-34`). Non era nel §2.4: è emersa cercando chi
  ancora con `%TYPE` le colonne convertite.
- **D-6 aperta** (§3): la forma del codice SDI non è un vincolo.

### 7.4 La prova (2026-10-10, scratch `zeroerp_ci` come `zeroerp`, transazione annullata)

- **SQL estratto** dagli YAML (`changes[].sql`), `-26` … `-36` in fila: gira tutto. La
  `preCondition` del `-26` risponde 12 su scratch.
- **Firme**: una sola funzione per nome. L'identità cambia **solo** in `fn_crea_soggetto_pg`
  (voluto); il corpo cambia solo in `fn_get_indirizzi_by_soggetto` e `fn_get_note` (voluto).
- **Viste**: nomi e posizioni delle colonne identici. Cambia solo il tipo: da `character(n)` (o
  `text`, dove c'era il TRIM) a `varchar(n)`, su 31 colonne. `security_invoker` conservato dove
  c'era.
- **Definizioni vive** delle 16 viste e 11 funzioni: identiche fra dbdev e scratch (md5), quindi
  la prova vale per entrambi.
- **pgTAP prima/dopo**: 101 file che nominano gli oggetti toccati o i cataloghi degli errori,
  ognuno da solo e con l'SQL estratto in testa. **Nessuna regressione**: errori e rossi identici
  prima e dopo in 98 file. Cambiano solo:
  - `config/test-province-sigla-v1` (nuovo): 5/12 prima, **12/12** dopo;
  - `dbops/test-character-n-v1` (nuovo): 4/8 prima, **8/8** dopo;
  - `anagrafiche/test-indirizzi-fallback`: prima moriva al test 11 sull'errore di
    `fn_get_indirizzi_by_soggetto`; dopo arriva in fondo, e il test 11 passa. Restano 6 rossi di
    **fixture**: il test 1 cerca un Gestore esistente, che sullo scratch non c'è, e gli altri
    cadono a cascata. Dopo l'apply va riclassificato nei registri dei rossi.
- Presidi trasversali verdi prima e dopo: `test-riferimenti-morti-v1` (`plpgsql_check` su tutte le
  funzioni), `test-rls-viste-security-invoker`, `test-catalogo-messaggi-errore-completo`,
  `test-codici-errore-identita`.
- **Controesempi su dbdev** (sola lettura): nessuna riga viola i CHECK nuovi, e nessun valore
  supera la sua `n` dopo il `btrim`.
- ⚠️ **Non provato**: il loader dei CSV degli errori (nella prova le due righe sono state inserite a
  mano) e la corsa come `zeroerp_app`. Restano all'apply e alla corsa pgTAP di Tid.

### 7.6 D-6: il canale della fattura elettronica (2026-10-10, dopo l'apply di `-26`…`-36`)

Fatto datato (dbdev, 2026-10-10): nessuna riga di `dati_societari` ha `destinatario_fe` in `P`/`C`.
Ci sono 155 `XXXXXXX002`, 2 `XXXXXXX003` (residui dei pgTAP che committano), `trewtetr` e `wwww`.
Il form scrive `P`/`C`, ma su questo database non l'ha mai fatto con successo, oppure le righe sono
state riscritte. Il dato non decide niente: dice solo che la colonna oggi non ha un contratto.

Chi legge la colonna: `vendite.fn_snapshot_intestazione_fattura` (la copia nello snapshot accanto a
`codice_sdi` e `pec_fatturazione`), `script.fn_get_soggetto_dati_by_ruolo`, `vw_dati_societari`, il
backend (`soggetti_repository`).
Chi la scrive: il form (`P`/`C`), `fn_crea_soggetto_pg`, l'helper `dbops.fn_pgtap_crea_soggetto_pg`
(`'0000000'`) e tre pgTAP (`XXXXXXX00n`, `'C'`).

⚠️ Anche il commento della colonna messo dal `-26` va corretto: parla di «codice destinatario» e
rimanda a una D-6 che chiedeva la cosa sbagliata.

**Decisioni di Tid (2026-10-10):** vocabolario + coerenza; via entrambi gli UNIQUE; canale nullable.

⛔ **La prima versione di D-6 era sbagliata, ed è stata ritirata prima dell'apply.** La domanda del
§3 chiedeva «la forma del codice SDI in `destinatario_fe`», fidandosi del commento della colonna.
I changeSet scritti su quella base (un CHECK `^[A-Z0-9]{6,7}$` su `destinatario_fe`) avrebbero
vietato proprio `P` e `C`. Li ha fermati il censimento dei chiamanti: il form usa la colonna come
scelta del canale. ⇒ Il significato di una colonna si legge da **chi la scrive** (form, funzioni,
fixture), non dal suo commento.

**ChangeSet (applicati il 2026-10-10):**

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/anagrafiche/20261010-37-alter-dati-societari-canale-fe` | `DROP` di `vw_dati_societari`; `destinatario_fe` nullable e `varchar(1)`, con `USING` che **deriva** il canale dove c'era un codice (codice SDI → `C`, altrimenti PEC → `P`, altrimenti NULL); `codice_sdi` `varchar(7)` `USING upper(btrim())`; CHECK `chk_dati_societari_destinatario_fe_canale`, `chk_dati_societari_codice_sdi_forma`, `chk_dati_societari_canale_fe_coerente`; `DROP` di `uq_ds_codice_sdi`, `uq_ds_pec_fatt` e del «non vuoto» del `-26`; COMMENT delle tre colonne riscritti |
| `20_code/anagrafiche/…-38-recreate-vw-dati-societari-canale-fe` | la vista, identica (corpo vivo) |
| `20_code/anagrafiche/…-39-create-trgfn-dati-societari-guard-canale-fe` | guard con una frase per campo: `E_DATI_SOCIETARI_CODICE_SDI_NON_VALIDO`, `…_CODICE_SDI_MANCANTE`, `…_PEC_FATTURAZIONE_MANCANTE` (DATO_ERRATO, id 1246-1248). Un canale fuori vocabolario resta al `23514`: lo sceglie una lista, chi lo sbaglia è un chiamante rotto |
| `20_code/dbops/…-40-update-fn-pgtap-crea-soggetto-pg-senza-canale-fe` | l'helper di fixture non scrive più `'0000000'` nel canale |

Fixture dei pgTAP allineate: `test-dati-societari-policy` (`XXXXXXX00n` → `C` o NULL secondo i
recapiti presenti), `test-soggetti-indirizzi-required`, `create-soggetto-bank-branches` (`'0000000'`
→ nessun canale). `test-emittenti-fiscali` scriveva già `'C'`: era giusto lui. Nuovo
`anagrafiche/test-dati-societari-canale-fe-v1` (13). Il presidio `test-character-n-v1` aggiorna la
riga di `destinatario_fe`. Manual `dati_societari` riscritto sui tre campi.

**Passo 0, a mano su dbdev, PRIMA dell'apply (fatto)** (provato come app in transazione annullata: 0 righe
residue fuori forma). Cinque `codice_sdi` da 10 caratteri, residui di pgTAP ritirati
(`SPCOD12345`, `SCCOD67890`, …), farebbero fallire l'`ALTER` a `varchar(7)`:

```sql
UPDATE anagrafiche.dati_societari
   SET codice_sdi = right(codice_sdi, 7)
 WHERE length(codice_sdi) > 7;
```

I 157 `destinatario_fe` con un codice al posto del canale non vanno toccati: li converte la `USING`
del `-37`.

**Prova (2026-10-10, scratch, transazione annullata):**
- l'SQL estratto di `-37`…`-40` gira; CHECK e tipi come attesi, una sola `fn_pgtap_crea_soggetto_pg`;
- la `USING`, su righe costruite nei sei casi di dbdev: `XXXXXXX002` con codice → `C`; `trewtetr`
  con la sola PEC → `P`; `'0000000'` senza recapiti → NULL; `P` e `C` restano; `abc1234` →
  `ABC1234`; PEC vuota e codice di spazi → NULL;
- pgTAP prima/dopo su 39 file (chi nomina `dati_societari` e i suoi recapiti, più i presidi
  trasversali): nessuna regressione. Cambiano solo i due file toccati (`test-character-n-v1`
  6/8 → 8/8, `test-dati-societari-canale-fe-v1` 3/13 → 13/13).

### 7.5 Domande aperte a Tid

Nessuna. (D-6 decisa; la provincia `TEST` cancellata a mano da Tid il 2026-10-10.)

## 8. Il seguito

Tre difetti emersi chiudendo questo brief riguardano lo stesso oggetto, i dati fiscali e societari
del soggetto. Su indicazione di Tid stanno in **un** brief,
`work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`:

- **A** — «Cliente PA» e «Split payment» valgono per ogni natura, anche per un privato;
- **B** — in modifica i dati societari non si salvano (§6.2): il verbo di scrittura, deciso da Tid
  (era D-7 di questo brief);
- **C** — la forma giuridica non è legata alla natura: il DB accetta una forma fuori matrice, e il
  drawer la mostra vuota (è ciò che il collaudo R-2 ha visto).

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-10-10 | Brief aperto su segnalazione BE (drawer comuni: `Potenza (PZ        )`). Perimetro allargato dall'analisi DB (§2). In attesa di D-1…D-5. |
| 2026-10-10 | D-1…D-5 accettate da Tid. Lato DB scritto: `20261010-26` … `-36`, codice `E_PROVINCIA_SIGLA_NON_VALIDA`, pgTAP `test-character-n-v1` e `test-province-sigla-v1`, regola §7e in `linee-guida-sql.md`, manual di `province`. Trovati e riparati `fn_get_indirizzi_by_soggetto` (rotta) e il cast `char(5)` di `fn_get_note`. Aperta D-6. Prova sullo scratch senza regressioni (§7.4). Da applicare. |
| 2026-10-10 | `-26`…`-36` applicati da Tid, pgTAP verdi; provincia `TEST` cancellata a mano. D-6 prima scritta sul significato sbagliato (`-37`/`-38`, ritirati prima dell'apply), poi rifatta sul canale FE dopo le decisioni di Tid: `-37`…`-40`, tre codici errore, pgTAP `test-dati-societari-canale-fe-v1`. Da applicare dopo il passo 0 (§7.6). |
| 2026-10-10 | Passo 0 fatto, `-37`…`-40` applicati da Tid, pgTAP verdi. **Lato DB chiuso**; restano BE/FE (§6). |
| 2026-10-10 | Lato BE/FE (§6.1): policy rigenerate e ripieghi per i quattro codici, commenti TRIM, form del canale FE (maiuscolo, campi accesi). Provato con chiamate reali sul DB, 1508 test verdi. Trovato il salvataggio mancante dei dati societari in modifica (§6.2, domanda a Tid). Resta la verifica a video (R-2). |
| 2026-10-10 | Tid decide D-7: il verbo di scrittura dei dati societari, a DB, con BE e FE dietro. Lato FE estratto il BB `InputMaiuscolo` (regola del 2, ok Tid): codice SDI ed estensione del civico. |
| 2026-10-10 | Collaudo a video di Tid superato (R-2). D-7 spostata, con PA/split e la forma giuridica fuori matrice, in `brief-db-dati-fiscali-e-societari-del-soggetto` (§8). **Brief chiuso e archiviato in `work-done/`.** |
| 2026-10-11 | CI da zero rossa al seed delle province: `province.csv` (sigla, descrizione) e `stati_cliente.csv` (descrizione_breve) erano ancora l'export da `character(n)`, con gli spazi di riempimento. Su dbdev non si vedeva (il `btrim` del `-26` aveva pulito le righe, i CSV non erano cambiati e i loader `runOnChange` non ripartivano); da zero il CSV arriva dopo la conversione, e il guard del `-36` rifiuta `'AO        '`. Tolti gli spazi dalle sole colonne convertite (diff vuoto a meno degli spazi). Il `[MESSAGGIO NON DEFINITO]` dell'errore è solo l'ordine dei seed: `messaggi_errore.csv` si carica dopo le province. Su richiesta di Tid tolti anche gli spazi delle 20 descrizioni di `regioni.csv`: la colonna era già `varchar` senza vincolo, quindi il riempimento finiva nel dato senza che nessuno lo rifiutasse. |
