# Brief DB — L'emittente di default: un building block solo, e le copie si ritirano

> **Destinatario:** team DB (`dev/db-tid`), con **tre richieste al BE** in §11
> (rigenerazione delle policy, un ripiego, una `ui_action`) e **due alle
> guide** in §12. Nessun endpoint, nessuna chiave i18n, nessun drawer nasce
> qui.
>
> **Origine.** Decisione di Tid, 2026-09-15 sera, sul punto aperto §4.7 del
> [brief del Lotto 1 di magazzino](brief-db-magazzino-lotto-1-terreno-vuoto.md):
> *«bisogna fare in modo che non esistano tutte le copie, predisporre funzioni
> generiche e ritirare i duplicati — ora non c'è produzione, che aspettiamo,
> che arrivi la produzione per fare questi refactor?»*. La raccomandazione che
> c'era («il BB ora, le cinque copie di vendite si ritirano quando c'è tempo»)
> è **respinta**, e la ragione è scritta in memoria
> (`feedback_duplicati_si_ritirano_nello_stesso_cantiere`): un refactor rimandato
> è un debito che nessuno rilegge.
>
> **Stato:** ✅ **SCRITTO E PROVATO, in attesa di apply** (2026-09-17). Le
> cinque decisioni di §3 confermate da Tid il 15-09 (*«accetto le tue
> raccomandazioni»*); P-0 → P-7 fatti (§8): **undici changeSet**
> (`20260915-36 → -46`), i due CSV in place, un pgTAP nuovo (18) + uno
> riscritto, otto manuali ripuntati, uno nuovo, quattro ritirati, due guide.
> **Provato con l'SQL estratto** (`updateSQL` offline) in `BEGIN … ROLLBACK`
> su dbdev: preCondition, struttura, nove casi di mutazione e i tre pgTAP
> (18/18, 6/6, 12/12) — tutti verdi **da owner**, il giro da `zeroerp_app` è di
> Tid dopo l'apply (§12). ⚠️ Nella stessa copia di lavoro corre un altro
> cantiere (`brief-db-distinta-numerata-sul-registro`, `20260915-21 → -35`
> non ancora committati, due codici nuovi nei CSV): i numeri e gli id dei
> messaggi sono stati riletti prima di ogni file, e restano da rileggere al
> commit. ⏳ A Tid: apply, pgTAP col runner, rigenerazione auto-gen, commit;
> al BE le quattro richieste di §11.
>
> **Perimetro:** una funzione generica in `script`, montata su **sette**
> tabelle (quattro al posto delle copie di vendite, una per chiudere
> un'asimmetria, due nuove di magazzino) più **quattro candidate** da
> confermare (§5); il ritiro di **quattro** funzioni e **tre** codici errore;
> **una** correzione trovata censendo (la revisione del preventivo non copia
> l'ancora, §7.1). ⛔ Fuori: `commesse` (non è una copia), `resi` e
> `documenti_generati` (l'emittente lo deriva il padre), e tutto ciò che
> tocca le **partizioni** o la RLS.
>
> ⚠️ **Va PRIMA del Lotto 2 di magazzino**, che lo presuppone: il primo
> magazzino vero nasce lì, dal pannello, e senza default l'INSERT muore con
> `23502` (Lotto 1, §4.7).

---

## 0. In due parole, senza tecnicismi

Quando un operatore crea un ordine e non dice *per quale azienda* lo sta
creando, il sistema lo capisce da solo: è l'azienda con cui l'operatore sta
lavorando in quel momento. Questa regola oggi è scritta **quattro volte**, in
quattro copie quasi identiche (ordini, preventivi, contratti, bolle), e
**mancava del tutto** su altre tabelle che pure hanno un'azienda obbligatoria
— fra cui i magazzini e i cespiti appena messi in forma.

Questo cantiere scrive la regola **una volta sola**, in un posto solo, la
monta dove serve, e **cancella le quattro copie**. Non cambia niente per chi
usa il programma: cambia quante volte la stessa frase è scritta, e quindi
quante volte può divergere.

---

## 1. Il filtro: che cosa entra qui

Entra ciò che soddisfa **tutte e tre** le condizioni:

1. è **la stessa regola**: *«se la riga non dice l'emittente, è quello di chi
   la scrive; se non c'è nessuno da cui dedurlo, la riga non entra»*;
2. la colonna si chiama **`emittente_fiscale_id`** ed è l'ancora del perimetro
   (`vw_rls_perimetro_scoperto`, famiglia `fn_scope_ef_whitelist_*`);
3. l'emittente **non si deriva da un padre** (documento sorgente, billing
   account): dove si deriva, la regola è un'altra e la scrive il `normalize`.

⭐ La terza condizione è quella che distingue una **copia** da una **cosa
diversa con lo stesso nome** — e il censimento di §2 dice che di cinque
funzioni `trgfn_*_default_emittente` una non è una copia.

---

## 2. Il censimento — fatto datato, 2026-09-15 (doc auto-gen + repo)

### 2.1 Le cinque di `vendite` — tre copie, una variante, una cosa diversa

| Funzione | Trigger | Che cosa fa | Sorte |
| --- | --- | --- | --- |
| `vendite.trgfn_ordini_default_emittente` | `trg_ordini_a10_default_emittente_ins` `BEFORE INSERT` | skip se valorizzato; GUC `app.current_user_id`; `script.fn_resolve_emittente_for_user`; **solleva** `E_ORDINE_EMITTENTE_NON_RISOLTO` (`DATO_ERRATO`) se GUC vuota o resolver NULL | **copia** → ritirata |
| `vendite.trgfn_preventivi_default_emittente` | `trg_preventivi_a10_default_emittente_ins` | identica (`E_PREV_EMITTENTE_NON_RISOLTO`) — diff col corpo di `ordini`: **solo commenti e nome del campo nel contesto** | **copia** → ritirata |
| `vendite.trgfn_contratti_default_emittente` | `trg_contratti_a10_default_emittente_ins` | identica (`E_CONTRATTO_EMITTENTE_NON_RISOLTO`) | **copia** → ritirata |
| `vendite.trgfn_ddt_default_emittente` | `trg_ddt_a10_default_emittente_ins` | skip se valorizzato; **skip se `sorgente_tipo_id` + `sorgente_uid` valorizzati** (eredita dall'ordine in `trgfn_ddt_normalize`); GUC vuota → **non solleva, lascia NULL** (fallback da BA nel normalize); resolver NULL → lascia NULL | **variante** → ritirata, il BB la copre con due argomenti (§4) |
| `vendite.trgfn_commesse_default_emittente` | `trg_commesse_a10_default_emittente_ins` | deriva **dal billing account** (`anagrafiche.fn_get_emittente_fiscale_id`) su `emittente_soggetto_ruolo_id` — altra colonna, altra regola, e `billing_account_id` è NOT NULL | **non è una copia** → resta |

⚠️ **La variante di `ddt` non è un dettaglio d'implementazione: è una regola.**
`trgfn_ddt_normalize` fa `COALESCE(NEW.emittente_fiscale_id, o.emittente_fiscale_id)`
— **vince ciò che è già in `NEW`**. Se il default di sessione riempisse la
colonna *prima* del normalize, un super admin con emittente attivo B che evade
un ordine di A produrrebbe un DDT di B, e `trgfn_ddt_guard_emittente_ba` lo
rifiuterebbe (`E_DDT_EMITTENTE_BA_INCOERENTE`). Lo skip sulla sorgente dice:
*un documento che nasce da un altro documento eredita l'emittente di quello,
non della sessione*. Il BB deve saperla dire (§4, argomento 2).

### 2.2 Le tabelle ancorate su `emittente_fiscale_id NOT NULL` senza alcun default

Letto dalla doc auto-gen (`| emittente_fiscale_id | bigint | NO |`), escluse le
shadow `storico.*`:

| Tabella | Oggi l'emittente arriva da… | Scope guard montato | Verdetto (§5) |
| --- | --- | --- | --- |
| `magazzino.magazzini` | nessuno: il pannello generico lo mostra come intero da digitare; vuoto → `23502` | `trg_magazzini_a10_guard_emittente_scope_ins_upd` | **monta** |
| `magazzino.assets` | nessuno | `trg_assets_a10_guard_emittente_scope_ins_upd` | **monta** |
| `vendite.offerte_commerciali` | il BE lo passa nell'INSERT (`offerte_repository`: `emittente_fiscale_id` nella whitelist delle colonne di creazione, r. 554); `fn_crea_revisione_offerta` lo copia | sì | **monta** — è la sorella di preventivi/ordini/contratti senza il default: un'asimmetria nello stesso dominio, e si chiude subito (`PROJECT_CONTEXT` §«Il prossimo cantiere») |
| `vendite.resi` | `trgfn_resi_normalize`: eredita dal DDT sorgente, fallback dal BA | (`z10_guard_emittente_ba`) | ⛔ **no**: deriva dal padre, condizione 3 |
| `pratiche.pratiche` | payload obbligatorio (`pratiche_service`: `emittente_fiscale_id > 0`, `views.py` lo pretende in query) | sì | 🔵 candidata (§3 D2) |
| `documenti.documenti_generati` | il BE lo deriva dal documento sorgente (`documenti_repository`) | sì | ⛔ **no**: deriva dal padre |
| `documenti.template_documenti` | payload esplicito (chiave logica del template) | no | 🔵 candidata |
| `documenti.template_asset` | payload esplicito, `_guard_emittente_in_scope` in Python | no | 🔵 candidata |
| `anagrafiche.soggetti_titoli_iva` | payload obbligatorio (`titoli_iva_service`, Q5: immutabile dopo) | no | 🔵 candidata |
| `config.user_emittente_attivo`, `config.user_emittenti_fiscali` | sono **la mappa stessa** operatore→emittente | — | ⛔ no: un default qui sarebbe circolare |

### 2.3 I tre codici e i loro lettori

| Codice | Classe | Messaggio (it, id) | Lettori fuori dal DB |
| --- | --- | --- | --- |
| `E_ORDINE_EMITTENTE_NON_RISOLTO` | `DATO_ERRATO` | 467 — «Nessun emittente fiscale attivo: seleziona l'emittente in alto per creare l'ordine, oppure indicalo esplicitamente nella richiesta. %s» | `error_policies_generated.py`, `error_messages_fallback.py` (r. 573) |
| `E_PREV_EMITTENTE_NON_RISOLTO` | `DATO_ERRATO` | 418 — idem, «il preventivo» | generated, fallback (r. 650, **frase diversa** dalle sorelle), **`error_ui_overrides.py` r. 407 → `highlight_form_fields`** (le altre due non hanno override: sono a `show_error_banner`, il default di classe — tre codici per la stessa cosa e **due comportamenti a video**) |
| `E_CONTRATTO_EMITTENTE_NON_RISOLTO` | `DATO_ERRATO` | 463 — idem, «il contratto» | generated, fallback (r. 221) |

Il `%s` in coda riceve oggi `concat('GUC vuota, numero=', NEW.numero)` o
`'auth_user_id=…'`: un **contesto diagnostico** incollato a una frase per
l'operatore — è la forma che `AGENTS.md` §«Sollevare un errore» chiede di non
fare (*nel `VARIADIC` non entra un nome di parametro*). Il codice nuovo non ha
segnaposto: la diagnostica sta nel `context`, dove la legge `error_log`.

⚠️ `E_FATTURA_EMITTENTE_NON_RISOLTO` (`TECNICO`) e `E_SORG_EMITTENTE_NON_RISOLTO`
(`TECNICO`) **non c'entrano**: dicono che un *documento esistente* non ha
emittente, non che *chi crea* non ne ha uno — la loro `note` a catalogo lo
scrive già. Non si toccano.

### 2.4 Chi nomina i quattro nomi di funzione (lettori del ritiro)

- **Vivi**: due pgTAP — `vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza.sql`
  (test 1 `has_trigger` per nome, test 5 `throws` sul codice `E_PREV_…`) e
  `vendite/test-emittente-ddt-simmetria-v1.sql` (test 6 `has_trigger`, test 10
  *«default_emittente ordina prima di normalize»* per confronto di stringhe).
  ⭐ Entrambi guardano il **nome del trigger**, che **non cambia** (§4.3):
  restano verdi; solo il test 5 del primo va sul codice nuovo;
- **Commenti**: undici pgTAP, quattro file BE (`views_contratti.py`,
  `preventivi_service.py`, `preventivi_repository.py`, `contratti_service.py`)
  — innocui, si aggiornano per non lasciare un nome morto (BE: §11);
- **Guide**: `docs/it/guide/gestione-ordini.md` (r. 27 e 438) e
  `gestione-ddt.md` (r. 30 e 321) **linkano la pagina auto-gen** della
  funzione: il giorno del ritiro il link è rotto → §12;
- **Registri `80_data`**: nessuno (`grep default_emittente 80_data/sql` → 0);
  `dbops.riferimenti_morti_esenzioni` non li nomina (lezione del 15-09:
  *montare o smontare una funzione = censire il registro che la dichiarava*).

---

## 3. ⚠️ Le decisioni da confermare prima di scrivere

> ✅ **Tutte e cinque confermate da Tid il 2026-09-15 (sera), come raccomandate**:
> D1 codice unico + `obsoleto_dal`; D2 anche le quattro candidate; D3 la
> revisione copia l'ancora; D4 `ddt` con i due argomenti; D5 l'ordine è il nome.

### D1 — Un codice solo: **`E_EMITTENTE_NON_RISOLTO`** (`DATO_ERRATO`), i tre di dominio in `obsoleto_dal`

Tre codici che dicono la stessa cosa con tre nomi sono un duplicato quanto le
funzioni; e oggi producono **due `ui_action` diverse** (§2.3). Un codice per la
condizione *«chi scrive non ha un emittente da cui dedurre»*, trasversale come
già `E_SCOPE_EMITTENTE` e `E_SCOPE_SENZA_UTENTE` (stessa famiglia, stesso
`script`). Messaggio senza segnaposto:
*«Nessun emittente fiscale attivo: seleziona l'emittente in alto, oppure
indicalo esplicitamente nella richiesta.»*, con `causa` e `soluzione` prese
dal 418 (sono già generiche). Nel `context`: `campo = emittente_fiscale_id`,
`tabella`, `detail` («GUC vuota» / «operatore senza emittente assegnato»),
`auth_user_id`.
I tre vecchi prendono **`obsoleto_dal`** con la `note` che nomina questo brief
— pattern `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA` (`20260820-02`): mai un
`DELETE`, i messaggi restano (il diario deve restare leggibile).
⚠️ Per il rubinetto B-7 (`codici-errore-baseline.sh`) non è un accumulo: una
condizione, N tabelle — la forma di `E_SCOPE_EMITTENTE`.
*Alternativa*: tenere i tre codici e passarli come `TG_ARGV` — respinta:
sarebbe il BB con dentro il duplicato.

### D2 — Il perimetro di montaggio: le **sette** certe, e le **quattro candidate** → **raccomando: si montano anche le quattro**

Certe (§2.2): `ordini`, `preventivi`, `contratti`, `ddt` (al posto delle
copie), `offerte_commerciali` (asimmetria), `magazzini`, `assets`.
Candidate: `pratiche.pratiche`, `documenti.template_documenti`,
`documenti.template_asset`, `anagrafiche.soggetti_titoli_iva`. Su tutte e
quattro il BE **passa già** l'emittente: il trigger scatterebbe solo su un
NULL che oggi finisce in `23502`. Montarlo **non cambia nessun comportamento
in essere** e chiude la porta con una frase per l'operatore al posto di un
errore di vincolo. ⚠️ Costo: quattro `CREATE TRIGGER` e quattro righe in un
pgTAP. ⚠️ Rischio da censire in P-0: un pgTAP che oggi **pinna il `23502`**
su una di quelle tabelle diventerebbe `P0001` (il `BEFORE ROW` scatta prima
del vincolo).
*Alternativa*: solo le sette — lecita, ma lascia quattro tabelle in cui la
stessa regola vive in Python e non nel DB.

### D3 — `fn_crea_revisione_preventivo` **copia** `emittente_fiscale_id` dalla rev N (🔴 trovato censendo, §7.1)

Oggi l'INSERT della rev N+1 **non nomina** l'emittente: lo riempie il default
di sessione. Per un operatore della stessa azienda è lo stesso valore; per un
super admin con emittente attivo B che revisiona un preventivo di A, la rev
N+1 prende B e `trgfn_preventivi_guard_emittente_ba` la **rifiuta**
(`E_PREV_EMITTENTE_BA_INCOERENTE`) — un difetto mascherato da un guard. La
revisione è **lo stesso documento**: copia l'ancora, come già fa
`fn_crea_revisione_offerta`. Una riga nella lista colonne, una nel `SELECT`.
Entra qui perché il ritiro delle copie è il momento in cui si guarda chi si
appoggiava al default senza dirlo.

### D4 — `ddt`: modo `LASCIA_NULL` + `SALTA_CON_SORGENTE` → comportamento **identico a oggi**

Il BB replica la variante di §2.1 con due argomenti (§4). *Alternativa*:
unificare `ddt` alla forma «solleva» — respinta: rompe l'evasione da ordine
per un super admin (§2.1) e sposta una regola vera nel posto sbagliato.

### D5 — Le due copie di magazzino portano il **guard di scope già montato** in Lotto 1: il default deve scattare **prima**

`trg_magazzini_a10_guard_emittente_scope_ins_upd` esiste (Lotto 1, P-7). I
`BEFORE ROW` scattano in **ordine alfabetico**
(`reference_ordine_guard_before_row_si_governa_col_nome`):
`trg_magazzini_a10_default_emittente_ins` < `…_guard_emittente_scope_…` per
costruzione del nome — stessa coppia già in servizio su `ordini`. Il pgTAP lo
**asserisce** per ogni tabella montata, sullo stampo del test 10 di
`test-emittente-ddt-simmetria-v1`. Non è una decisione: è scritto perché
chi legge sappia che il nome **è** l'ordine.

---

## 4. La forma del building block

### 4.1 Firma e argomenti

```
script.trgfn_default_emittente_fiscale()  RETURNS trigger   -- BEFORE INSERT, FOR EACH ROW
  TG_ARGV[0]  modo       'SOLLEVA' | 'LASCIA_NULL'        obbligatorio
  TG_ARGV[1]  opzione    'SALTA_CON_SORGENTE'             facoltativo
```

- **colonna fissa `emittente_fiscale_id`**: tutte le tabelle del perimetro la
  chiamano così, ed è il nome su cui poggia il presidio del perimetro. ⛔
  Niente nome-colonna dinamico (`to_jsonb(NEW) ->> …` + `jsonb_populate_record`):
  non c'è un precedente nel progetto che **scriva** `NEW` così (zero
  occorrenze nella doc auto-gen), e un parametro in più è una cosa in più che
  può essere sbagliata. `commesse`, l'unica con un'altra colonna, resta fuori
  per un'altra ragione (§2.1);
- `modo`: che cosa fare quando dalla sessione non si ricava niente (GUC vuota,
  oppure resolver NULL = admin globale senza emittente). `SOLLEVA` =
  `E_EMITTENTE_NON_RISOLTO`; `LASCIA_NULL` = `RETURN NEW` e decide chi viene
  dopo (`normalize`, o il `NOT NULL`);
- `SALTA_CON_SORGENTE`: se `NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_uid IS NOT NULL`
  non si tocca niente. Si legge con `to_jsonb(NEW)` **in lettura** (le colonne
  possono non esistere sulla tabella: `magazzini` non ha sorgente) — è la
  forma di `trgfn_guard_emittente_scope`, che legge `NEW` così da un anno;
- un argomento non ammesso → errore **al primo INSERT**, non al `CREATE
  TRIGGER`, con **`E_TRIGGER_ARGOMENTI_INVALIDI`** (`TECNICO`, già a catalogo:
  *«difetto di MONTAGGIO: se ne accorge chi installa»*) — è il codice della
  famiglia (`E_ARGOMENTI_A_COPPIE` per `trgfn_lock_columns`,
  `E_ATTIVO_BLOCK_ARGS` per `prevent_deactivate_if_children`). ⛔ Non
  `E_PARAMETRO_INVALIDO` (split rimandato, non si riusa) e niente codice nuovo.

### 4.2 Corpo (stesura, da provare con l'SQL estratto)

```sql
CREATE OR REPLACE FUNCTION script.trgfn_default_emittente_fiscale()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_modo          text := TG_ARGV[0];
  v_salta_sorg    boolean := (TG_NARGS > 1 AND TG_ARGV[1] = 'SALTA_CON_SORGENTE');
  v_row           jsonb;
  v_auth_user_id  anagrafiche.identita_digitali.auth_user_id%TYPE;
  v_ef_id         anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
  -- 1) Valore esplicito: non si sovrascrive mai una scelta dichiarata.
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 2) Riga nata da un documento sorgente: l'emittente è quello del padre,
  --    lo mette il normalize a valle (regola di ddt, §2.1).
  IF v_salta_sorg THEN
    v_row := to_jsonb(NEW);
    IF (v_row ->> 'sorgente_tipo_id') IS NOT NULL
       AND (v_row ->> 'sorgente_uid') IS NOT NULL THEN
      RETURN NEW;
    END IF;
  END IF;

  -- 3) Chi scrive. GUC vuota = nessuno da cui dedurre.
  v_auth_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
  IF v_auth_user_id IS NULL THEN
    IF v_modo = 'LASCIA_NULL' THEN RETURN NEW; END IF;
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text, 'trgfn_default_emittente_fiscale',
      'E_EMITTENTE_NON_RISOLTO',
      jsonb_build_object('campo', 'emittente_fiscale_id',
                         'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'detail', 'GUC app.current_user_id vuota e riga senza emittente_fiscale_id'),
      NULL::uuid, VARIADIC ARRAY[]::text[]);
  END IF;

  -- 4) Emittente di lavoro: attivo di sessione se in scope, altrimenti quello
  --    assegnato; NULL per un admin globale senza assegnazione.
  v_ef_id := script.fn_resolve_emittente_for_user(v_auth_user_id);
  IF v_ef_id IS NULL THEN
    IF v_modo = 'LASCIA_NULL' THEN RETURN NEW; END IF;
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text, 'trgfn_default_emittente_fiscale',
      'E_EMITTENTE_NON_RISOLTO',
      jsonb_build_object('campo', 'emittente_fiscale_id',
                         'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                         'auth_user_id', v_auth_user_id,
                         'detail', 'operatore senza emittente assegnato (admin globale): la riga deve dichiararlo'),
      NULL::uuid, VARIADIC ARRAY[]::text[]);
  END IF;

  NEW.emittente_fiscale_id := v_ef_id;
  RETURN NEW;
END $$;
```

⚠️ `VARIADIC ARRAY[]::text[]` **esplicito**: cinque argomenti non risolvono la
firma (`reference_fn_log_and_raise_error_variadic_vuoto`). ⚠️ `%TYPE` nel
`DECLARE` (regola di Tid). ⚠️ Il controllo di `v_modo` ∉ {`SOLLEVA`,
`LASCIA_NULL`} (e di `TG_ARGV[1]`, se c'è, ∉ {`SALTA_CON_SORGENTE`}) sta **in
testa**, prima del punto 1, e solleva `E_TRIGGER_ARGOMENTI_INVALIDI` — un
trigger montato con un argomento sbagliato deve morire al primo uso, non
tacere. ⚠️ Il messaggio di quel codice va letto a catalogo per passare i
`%s` giusti (P-0).

### 4.3 I trigger: **i nomi non cambiano**

```
trg_<tabella>_a10_default_emittente_ins   BEFORE INSERT   FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_default_emittente_fiscale('SOLLEVA')
```

Sulle quattro di vendite si fa `DROP TRIGGER` + `CREATE TRIGGER` con lo
**stesso nome** e la funzione nuova (una `CREATE OR REPLACE TRIGGER`
cambierebbe l'`EXECUTE FUNCTION` in un colpo — PG14+ — ma i pgTAP che
asseriscono per nome restano verdi in entrambe le forme; la forma
`DROP`+`CREATE` è quella del progetto). ⛔ Sono trigger **scritti a mano**, non
generati: `DROP` secco, niente `IF EXISTS`, niente `MARK_RAN`
(`guardrail_ddl_su_trigger_automazione` non li riguarda; un `IF EXISTS` su un
oggetto che deve esistere nasconderebbe un DB che non è quello atteso).
`ddt`: `('LASCIA_NULL', 'SALTA_CON_SORGENTE')`.

### 4.4 Il ritiro

`DROP FUNCTION vendite.trgfn_{ordini,preventivi,contratti,ddt}_default_emittente()`
**dopo** il rimontaggio dei trigger (una funzione con un trigger montato non
si droppa). I tre codici in `obsoleto_dal` (D1). Le quattro pagine
`docs/it/dbzero/vendite/manual/trgfn_*_default_emittente.md` **si cancellano**
(regola `AGENTS.md` §Documentazione; l'indice è generato) e la spiegazione
del ritiro sta nel `manual/` della funzione nuova.

---

## 5. Dove si monta — tabella per tabella

| Tabella | Argomenti | Oggi | Dopo |
| --- | --- | --- | --- |
| `vendite.ordini` | `('SOLLEVA')` | copia | uguale a oggi, codice nuovo |
| `vendite.preventivi` | `('SOLLEVA')` | copia | uguale, codice nuovo; ⚠️ + D3 sulla revisione |
| `vendite.contratti` | `('SOLLEVA')` | copia (`fn_create_contratto` lo scrive **solo se nel payload** — è in `v_testata_allowed` — altrimenti si appoggia al default; `contratti_service.py` r. 134 lo dice) | uguale |
| `vendite.ddt` | `('LASCIA_NULL', 'SALTA_CON_SORGENTE')` | variante | uguale |
| `vendite.offerte_commerciali` | `('SOLLEVA')` | nessun default; il BE lo passa | il BE continua a passarlo; la porta del `23502` è chiusa |
| `magazzino.magazzini` | `('SOLLEVA')` | nessuno → `23502` dal pannello | dal pannello si può lasciare vuoto |
| `magazzino.assets` | `('SOLLEVA')` | nessuno | idem |
| `pratiche.pratiche` · `documenti.template_documenti` · `documenti.template_asset` · `anagrafiche.soggetti_titoli_iva` | `('SOLLEVA')` | payload esplicito | **se D2** — nessun cambiamento in essere |
| ⛔ `vendite.resi`, `documenti.documenti_generati`, `vendite.commesse`, `config.user_emittent*` | — | derivano dal padre / sono la mappa | non si montano, e il pgTAP lo **asserisce** (una tabella in più montata per imitazione fa rosso) |

---

## 6. Le trappole note, e dove morde ciascuna

| Trappola | Dove | Forma giusta |
| --- | --- | --- |
| **`DROP FUNCTION` con un trigger montato** | le quattro di vendite | prima il rimontaggio dei trigger sulla funzione nuova, poi il `DROP FUNCTION` — nello **stesso changeSet**, in quest'ordine |
| **Il nome è l'ordine** (`BEFORE ROW` alfabetico) | `default_emittente` deve precedere `guard_emittente_scope`, `guard_emittente_ba`, `normalize` | il prefisso `a10_default_` lo garantisce; il pgTAP lo asserisce per **ogni** tabella montata, non solo per ddt |
| **`obsoleto_dal`, mai `DELETE`; `validCheckSums` al plurale sul loader** | `codici_errore.csv` (mirror `runOnChange` + `ANY`: si edita in place) | tre celle + tre `note`; i messaggi in `messaggi_errore.csv` **restano** |
| **Registrare un codice = quattro cose** | `E_EMITTENTE_NON_RISOLTO` | riga in `codici_errore.csv` (classe), riga in `messaggi_errore.csv` (id **1072**, il prossimo libero al 15-09), **rigenerazione BE** (`genera_error_policies`), **ripiego BE** in `error_messages_fallback.py` — le ultime due in §11. ⚠️ `test_il_file_generato_e_allineato_al_catalogo` e `test_nessun_codice_nuovo_senza_policy` sono **già rossi** su `Tito-dev` per i due `E_MAG_*` del Lotto 1: una corsa sola di rigenerazione li copre tutti e tre |
| **`throws_ok(…, NULL, NULL)` non vale** | il pgTAP del rifiuto | `throws_like` sulla frase di `E_EMITTENTE_NON_RISOLTO` **e** SQLSTATE `P0001` |
| **Fixture che cerca un dato di macchina** | un magazzino vuole un indirizzo; un preventivo vuole un BA | `dbops.fn_pgtap_crea_emittente_operatore()` (due aziende: il primo emittente creato è il default) + `fn_pgtap_crea_indirizzo_dettaglio()`; per la GUC di sessione `set_config('app.current_user_id', …, true)` — la forma di `rls/test-rls-magazzino-perimetro-v1` |
| **Sotto RLS la policy scatta prima del vincolo** | asserire il `NOT NULL` di `emittente_fiscale_id` | `col_not_null`, non un INSERT che aspetta `23502` (lezione Lotto 1) |
| **Cambiare una riga di catalogo = `grep` nei pgTAP** | i tre codici | fatto (§2.4): un solo test li pinna vivo (`…preventivi-default-emittente…` test 5) |
| **Cancellare una fonte = censire i lettori** | le quattro funzioni | fatto (§2.4): due guide con link alla pagina auto-gen, quattro commenti BE, undici commenti pgTAP, zero registri |
| **Prova = SQL ESTRATTO in `BEGIN … ROLLBACK`** | tutto | `liquibase updateSQL` offline, si esegue **quello** |
| **Il numero libero scade nel minuto** | i file `20260916-NN` (o la data in cui si scrive) | si ricontrolla prima di salvare; al 15-09 sera l'ultimo è `20260915-20` |
| **`MAI` modificare changelog mergiati** | i quattro `create-trgfn-*-default-emittente` del 2026 | non si toccano: nuovi changeSet con numero successivo |

---

## 7. Trovato censendo (non erano nel punto aperto)

### 7.1 🔴 La revisione del preventivo non copia l'ancora → D3

`fn_crea_revisione_preventivo` (doc auto-gen, 15-09): la lista colonne
dell'`INSERT INTO vendite.preventivi` è `numero, rev, billing_account_id,
istanza_utility_id, utility_id, validita_dal, validita_al, totali, valuta_id,
competenza_mese, fatturazione_immediata, stato, data, termine_pagamento_id,
storicizza, meta, user_*` — **senza `emittente_fiscale_id`**. La rev N+1 prende
l'emittente **della sessione**, e il guard BA la ferma quando non coincide.
`fn_crea_revisione_offerta` invece lo copia (verificato: 1 occorrenza
nell'INSERT). È la forma di `reference_colonna_nuova_di_riga_censisce_le_copie_esplicite`
applicata a una testata.

### 7.2 Tre codici, due `ui_action`

`E_PREV_…` ha l'override `highlight_form_fields` («coerente col pattern
lock_columns»); `E_ORDINE_…` e `E_CONTRATTO_…` no → `show_error_banner`. Stessa
condizione, stesso testo, due rese a video. Il codice unico obbliga a
decidere **una** volta (§11, terza richiesta): il campo da correggere è la
**combo dell'emittente in alto**, non un campo del form — la raccomandazione
è il banner (default di classe), niente override.

### 7.3 `offerte_commerciali` era la sorella senza default

Stesso dominio, stessa ancora, stesso guard BA, stesso scope guard: solo il
default mancava, perché il BE lo passa. Non è un difetto in esercizio; è
un'asimmetria, e la regola del progetto è chiuderla subito.

### 7.4 Il messaggio delle tre copie incollava la diagnostica alla frase

`%s` ← `'GUC vuota, numero=…'`. Va nel `context`, non a video (§2.3).

---

## 8. I passi

> Fase: `00_schema` → `20_code` → `80_data`. ⛔ Negli YAML si cita il **nome**
> di questo brief (`brief-db-emittente-di-default-un-bb-solo`), mai il path.
> `runOnChange: false` su `20_code`; `validCheckSums` al plurale.

| # | Passo | Fase |
| --- | --- | --- |
| **P-0** ✅ 15-09 | **Censimenti residui** — esito: (a) `E_TRIGGER_ARGOMENTI_INVALIDI` (id 902) ha **un** `%s` = gli argomenti ricevuti; (b) **nessun** pgTAP pinna un `23502` su `emittente_fiscale_id` delle candidate; (c) ventiquattro pgTAP inseriscono **senza** emittente, **tutti** su `ordini`/`preventivi`/`contratti`/`ddt` (dove il comportamento non cambia) e **nessuno** sulle sette tabelle nuove; (d) i soli `has_trigger`/`throws` vivi sono i due file di §2.4. Le domande erano: (a) un codice `TECNICO` per l'argomento sbagliato; (b) i pgTAP che pinnano un `23502` su `emittente_fiscale_id` delle quattro candidate di D2 (`grep -l "23502" db/pgtap/{pratiche,documenti,anagrafiche}`); (c) i pgTAP che creano righe nelle sette+quattro tabelle **senza** GUC e **senza** emittente — oggi passano solo perché il runner è `owner`? (sotto `zeroerp_app` la GUC c'è sempre); (d) `has_function`/`has_trigger` per nome nei pgTAP su `trgfn_*_default_emittente` oltre ai due di §2.4 | — |
| **P-1** ✅ 15-09 | `20260915-36` `20_code/script/…create-trgfn-default-emittente-fiscale`: la funzione (§4.2) + `COMMENT`; il controllo degli argomenti sta in testa e solleva `E_TRIGGER_ARGOMENTI_INVALIDI` (id 902, un `%s` = gli argomenti ricevuti); `tx_id` letto da `to_jsonb(NEW)` quando c'è. `manual/` nuovo in P-7 | `20_code` |
| **P-2** ✅ 15-09 | `codici_errore.csv`: `E_EMITTENTE_NON_RISOLTO` (`DATO_ERRATO`, `note` = questo brief) + i tre vecchi con `obsoleto_dal = 2026-09-15` e `note` del ritiro; `messaggi_errore.csv`: id **1074** (non 1072: l'altro cantiere aveva preso 1072 e 1073 nel frattempo — riletto prima di scrivere), messaggio senza `%s`, `causa`/`soluzione` dal 418 generalizzate. Righe scritte senza `csv.writer` di default (CRLF), file verificati a colonne uniformi | `80_data` (CSV in place) |
| **P-3** ✅ 15-09 | `20260915-37` ordini, `-38` preventivi, `-39` contratti, `-40` ddt (`20_code/vendite/…update-trigger-default-emittente-<t>-su-bb`): preCondition HALT (BB presente, copia presente, trigger presente), `DROP TRIGGER` + `CREATE TRIGGER` stesso nome + `DROP FUNCTION` secchi; `ddt` con `('LASCIA_NULL', 'SALTA_CON_SORGENTE')` | `20_code` |
| **P-4** ✅ 15-09 | `20260915-41` `…update-fn-crea-revisione-preventivo-copia-emittente`: corpo dalla doc auto-gen (diff col definer `20260914-14` = zero, verificato), firma e `RETURNS TABLE` con `%TYPE` + `SECURITY INVOKER` rimessi a mano, una riga nella lista colonne, una nel `SELECT`, la `NOTE` nel blocco Scopo, la rev nel `COMMENT`. ⚠️ La prima stesura della `NOTE` nominava `trgfn_preventivi_default_emittente` e rendeva rosso il presidio «nessuna funzione viva nomina le copie»: riscritta senza il nome | `20_code` |
| **P-5** ✅ 15-09 | `20260915-42` offerte (vendite), `-43` magazzini + assets (magazzino), `-44` pratiche, `-45` template_documenti + template_asset (documenti), `-46` soggetti_titoli_iva (anagrafiche): un file per schema, `('SOLLEVA')`, preCondition HALT «colonna esiste, trigger non c'è» | `20_code` |
| **P-6** ✅ 17-09 | `script/test-trgfn-default-emittente-fiscale-v1.sql` (**18**, runner `app`, fixture costruita: tre aziende in tre istruzioni, un super admin, un BA di A, un indirizzo); test 5 di `vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza.sql` su `throws_like` della frase nuova (era `throws_ok` con SQLSTATE: il debito non cambia); `test-emittente-ddt-simmetria-v1` rilanciato invariato. ⭐ **D3 sta nel test 18 del file nuovo**, non nel file dei preventivi come diceva §9: la fixture (A, BA di A, SA) era già lì. Provati **pre-apply da owner** con l'SQL estratto: 18/18, 6/6, 12/12. Due cose trovate provando: un `WITH … INSERT … RETURNING` non sta dentro `is(…)` (temp table prima); il verbo `fn_crea_revisione_preventivo` e la lettura vanno in **due istruzioni** (stessa snapshot → NULL) | `db/pgtap` |
| **P-7** ✅ 17-09 | `docs/it/dbzero/script/manual/trgfn_default_emittente_fiscale.md` **nuovo**; `git rm` dei quattro `manual/` e delle quattro pagine auto-gen `vendite/funzioni/trgfn_*_default_emittente.md` (`commesse` resta); **otto** manuali ripuntati — il censimento di §2.4 ne contava due guide: i `manual/` dei guard BA (ordini, preventivi, contratti, ddt), `preventivi.md`, `ordini.md`, `fn_push_offerta_a_contratto.md`, `trgfn_preventivi_guard_utility_istanza_coerenza.md` linkavano la pagina ritirata (`grep` a zero link morti fuori dall'auto-gen); `fn_crea_revisione_preventivo.md` (D3); `magazzini.md` (il «punto aperto» diventa «chiuso») e `assets.md`; le due guide; questo brief. ⛔ `docs/it/backend/vendite/manual/api_ordini.md` r. 452 nomina la copia in prosa: è doc del BE, in §11 | `docs/` |

L'apply lo fa Tid; i pgTAP li lancia Tid col runner; qui si prova con l'SQL
estratto in transazione annullata (`BEGIN … ROLLBACK`).

---

## 9. I presidi

| Test | Che cosa prova |
| --- | --- |
| `script/test-trgfn-default-emittente-fiscale-v1` (nuovo) | (1) la funzione esiste in `script`; (2) **le sette (+4) tabelle** hanno `trg_<t>_a10_default_emittente_ins` che esegue **questa** funzione (`pg_trigger` join `pg_proc`), e **nessun'altra tabella** con `emittente_fiscale_id NOT NULL` fuori dall'elenco di §5 lo ha — l'elenco è nel test, con le esclusioni motivate; (3) su ogni tabella montata che ha anche `guard_emittente_scope`/`guard_emittente_ba`/`normalize`, il nome del default **ordina prima** (confronto di stringhe, stampo ddt test 10); (4) comportamento su `magazzini` (fixture: due aziende con `fn_pgtap_crea_emittente_operatore`, indirizzo fabbricato): GUC dell'operatore A + riga senza emittente → **A**; riga con emittente esplicito B → **resta B** (poi lo scope guard dirà la sua, ma non qui); GUC vuota → `throws_like` sulla frase, `P0001`; operatore senza assegnazione → idem; (5) `ddt`: GUC vuota + `LASCIA_NULL` → nessun errore dal default (la riga poi muore o vive per il normalize, non è materia di questo test); riga con sorgente + GUC di B → l'emittente **non** è B prima del normalize (si prova sulla funzione con una riga costruita, non sull'INSERT intero); (6) **nessuna funzione viva** in `pg_proc` nomina `trgfn_ordini_default_emittente`, `_preventivi_`, `_contratti_`, `_ddt_` né i tre codici ritirati (scansione `prosrc`); (7) i tre codici hanno `obsoleto_dal` valorizzato e `E_EMITTENTE_NON_RISOLTO` ha classe `DATO_ERRATO` e un messaggio `it` senza `%s` |
| `vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza` (riscritto) | test 5 sul codice nuovo (`throws_like` sulla frase); il resto invariato. ⚠️ La prova di D3 **non sta qui** (questo file pesca la popolazione: un BA e un utente esistenti) ma nel test 18 del file nuovo, che ha la fixture costruita. ⚠️ Provando è uscito che sotto RLS lo scenario «SA con emittente attivo B revisiona A» **non esiste**: l'impersonazione restringe la lettura a B e il preventivo di A non si vede. Il caso vero di D3 è il **super admin in modalità «tutti gli emittenti»**: prima della `-41` la revisione sollevava (`resolver NULL`), ora porta A |
| `vendite/test-emittente-ddt-simmetria-v1` (esistente) | invariato: asserisce per nome, e il nome non cambia — **si rilancia** per dirlo |
| `config/test-codici-errore-*` e il rubinetto B-7 (`codici-errore-baseline.sh`) | girano già: il codice nuovo entra come trasversale, non come accumulo |

⚠️ Preambolo obbligatorio (`BEGIN;`, contesto operatore, `SET CONSTRAINTS ALL
IMMEDIATE`); i test girano come l'applicazione, sotto RLS. Il test (4) scrive
in `magazzini`, che è in RLS dal Lotto 1: la fixture deve **essere**
l'operatore A quando scrive (GUC + `ruolo_applicativo`), o il `WITH CHECK`
parla prima del trigger.

---

## 10. Che cosa NON entra, e dove sta

| Cosa | Dove | Perché non qui |
| --- | --- | --- |
| `vendite.trgfn_commesse_default_emittente` | resta | non è una copia: deriva dal BA su un'altra colonna (§2.1) |
| il `normalize` di `resi` e la derivazione di `documenti_generati` | restano | l'emittente viene dal padre: condizione 3 di §1 |
| un drawer per i magazzini (`indirizzo_dettaglio_id` intero da digitare nel pannello generico) | FE, quando servirà | non è materia di default |
| il ritiro di `E_PARAMETRO_INVALIDO` in `fn_resolve_emittente_for_user` | cantiere `dbops` (split rimandato, D11 del brief classi) | non si allarga il perimetro |
| le tabelle ancorate **senza** scope guard (`template_documenti`, `template_asset`, `soggetti_titoli_iva`: §2.2, colonna «scope guard») | presidio RLS (`vw_rls_perimetro_scoperto`) e il suo registro | è un'altra domanda: *chi vede*, non *chi scrive* |
| la rinomina dei quattro trigger su un nome «generico» | nessuno | i nomi restano: sono per tabella, e due pgTAP li pinnano |

---

## 11. Richieste al BE (stesso giro di PR, o subito dopo)

> ✅ **Fatte tutte e quattro il 2026-09-17** (stesso giro del BE/FE della
> distinta numerata, `dev/backend-tid`): policy rigenerate (i tre vecchi in
> `CODICI_RITIRATI`, risolvono ancora), ripiego di `E_EMITTENTE_NON_RISOLTO`,
> **nessun override** (raccomandazione accolta, ragione scritta accanto alla
> voce di `E_PREV_…` che resta), i sei commenti coi nomi morti riscritti
> (`emittente_attivo_service.py` sta in `core/`, non in `vendite/`).

1. 🔴 `manage.py genera_error_policies`: entra `E_EMITTENTE_NON_RISOLTO`
   (`DATO_ERRATO`), i tre vecchi passano in `CODICI_RITIRATI` **e restano
   risolvibili**. È la corsa che copre anche i due `E_MAG_*` del Lotto 1 (già
   rossi su `Tito-dev`).
2. 🔴 `error_messages_fallback.py`: una frase **senza segnaposto** per
   `E_EMITTENTE_NON_RISOLTO` (*«Nessun emittente fiscale attivo: selezionalo in
   alto o indicalo nella richiesta.»* — è già la frase dei ripieghi 221 e 573).
   Le tre righe vecchie restano.
3. `error_ui_overrides.py`: **decidere** la `ui_action` del codice nuovo
   (§7.2). Raccomandazione: **nessun override** (banner): il rimedio è la combo
   in alto, non un campo del form. Se si sceglie `highlight_form_fields`, va
   scritta la ragione accanto, come per le altre 176.
4. Commenti da aggiornare (nomi morti): `views_contratti.py` r. 52,
   `preventivi_service.py` r. 368, `preventivi_repository.py` r. 556,
   `contratti_service.py` r. 134 e 1997, `emittente_attivo_service.py` r. 43
   (`*_EMITTENTE_NON_RISOLTO` → `E_EMITTENTE_NON_RISOLTO`); e la doc del BE
   `docs/it/backend/vendite/manual/api_ordini.md` r. 452, che nomina
   `trgfn_ordini_default_emittente` in prosa (non un link: nessun rosso, ma un
   nome morto).

---

## 12. Doc e cataloghi da toccare

- `docs/it/dbzero/script/manual/trgfn_default_emittente_fiscale.md` **nuovo**:
  i due argomenti, la regola della sorgente, l'elenco delle tabelle montate con
  il perché delle escluse, e il ritiro delle quattro copie (con la data).
- `docs/it/dbzero/vendite/manual/trgfn_{ordini,preventivi,contratti,ddt}_default_emittente.md`
  **cancellati** + le pagine auto-gen degli oggetti ritirati (checklist del
  `DROP`). ⛔ `index.md`/`index.ci.md` non si toccano: generati.
- `docs/it/guide/gestione-ordini.md` (r. 27, 438) e `gestione-ddt.md` (r. 30,
  321): il link alla funzione **ripuntato** su `script/…`, la frase che
  descrive il default riscritta sulla forma nuova (per ddt: i due argomenti).
- `docs/it/dbzero/vendite/manual/preventivi.md` (o
  `fn_crea_revisione_preventivo.md`): la revisione copia l'ancora (D3).
- `docs/it/dbzero/magazzino/manual/magazzini.md` e `assets.md`: una riga sul
  default dell'emittente (oggi dicono solo dell'ancora e del guard di scope).
- `docs/it/dev/work-in-progress/brief-db-magazzino-lotto-1-terreno-vuoto.md`
  §4.7: rimando a questo brief (fatto il 15-09).
- `docs/it/dev/work-in-progress/analisi-db-magazzino-carico-e-scarico.md`
  §8, tabella dei lotti: riga **1-bis** (fatto il 15-09).
- ⛔ La build della doc non si lancia; le pagine auto-gen le rigenera Tid
  (`scripts/gen_db_docs.py`) dopo l'apply.

---

## 12. Consegna — che cosa c'è e che cosa resta a Tid

**I changeSet, nell'ordine della timeline** (tutti `20_code`, `runOnChange: false`;
l'autogen li ordina per numero dopo i `-21 → -35` dell'altro cantiere):

| # | File | Passo |
| --- | --- | --- |
| `20260915-36` | `20_code/script/…create-trgfn-default-emittente-fiscale` | P-1 |
| `20260915-37 … -40` | `20_code/vendite/…update-trigger-default-emittente-{ordini,preventivi,contratti,ddt}-su-bb` | P-3 |
| `20260915-41` | `20_code/vendite/…update-fn-crea-revisione-preventivo-copia-emittente` | P-4 |
| `20260915-42` | `20_code/vendite/…create-trigger-default-emittente-offerte` | P-5 |
| `20260915-43` | `20_code/magazzino/…create-trigger-default-emittente-magazzini-assets` | P-5 |
| `20260915-44` | `20_code/pratiche/…create-trigger-default-emittente-pratiche` | P-5 |
| `20260915-45` | `20_code/documenti/…create-trigger-default-emittente-template` | P-5 |
| `20260915-46` | `20_code/anagrafiche/…create-trigger-default-emittente-titoli-iva` | P-5 |
| — | `80_data/sql/config/codici_errore.csv` (+1, 3 in `obsoleto_dal`), `messaggi_errore.csv` (+1, id 1074) | P-2 |

**La prova** (2026-09-15/17, dbdev, `BEGIN … ROLLBACK`, SQL reso da `liquibase
updateSQL --url=offline:postgresql` e concatenato, seed simulato con le sole
righe nuove): preCondition dei dieci changeSet ✅; struttura dopo ✅ (0 copie, 0
funzioni vive che le nominano, 11 trigger sul BB, ddt a due argomenti, ordine
alfabetico su ogni tabella, revisione con l'ancora); mutazione ✅ — T1
operatore→A, T2 esplicito non sovrascritto, T3 admin globale→`E_EMITTENTE_NON_RISOLTO`
(frase, `P0001`), T4 GUC vuota→idem, T5 emittente attivo di sessione→B, T6
argomento sbagliato→`E_TRIGGER_ARGOMENTI_INVALIDI`, T7 D3 (rev N+1 porta A), T8
ddt `LASCIA_NULL` (emittente dal BA via normalize), T9 ddt `SALTA_CON_SORGENTE`
(DDT da ordine di A con sessione su S→A). ⚠️ Nella prova il log di `error_log`
avverte «viola `fk_error_log_messaggio_errore_id`»: è l'artefatto del seed
non committato (il `dblink` non vede la transazione), non un difetto — dopo
l'apply il messaggio 1074 è committato. I tre pgTAP: 18/18, 6/6, 12/12.
Guardrail statici (`run_on_change`, `precondition_seed`, `ddt_su_trigger_automazione`,
`grant_ruolo_batch`, `pgtap_preambolo`) ✅. Su dbdev non è rimasto niente
(verificato dopo ogni giro: BB assente, copie presenti, 0 magazzini di prova).

**Che cosa resta a Tid** (`AGENTS.md` §Workflow Safety, memoria «no commit autonomo»):

1. ⏳ **apply** su dbdev (`make db-migrate`): undici changeSet + i due mirror CSV
   (`runOnChange`). ⚠️ Prima, se l'altro cantiere non è ancora applicato, decidere
   l'ordine: i suoi `-21 → -35` hanno numero minore e vanno prima **nella stessa
   corsa** (l'autogen li ordina per numero; nessuna dipendenza fra i due lotti);
2. ⏳ **pgTAP col runner** (`PGTAP_RUNNER=app`, il default):
   `script/test-trgfn-default-emittente-fiscale-v1`,
   `vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza`,
   `vendite/test-emittente-ddt-simmetria-v1`, poi `scripts/pgtap-baseline.sh vendite script`.
   ⚠️ Il giro da owner non esercita la RLS: è qui che si vede se la fixture a
   tre aziende scrive dove l'app scrive (i 14 test simili di `script/` girano
   così da settimane, la forma è la loro);
3. ⏳ rigenerare le pagine auto-gen (`scripts/gen_db_docs.py`): le quattro
   `vendite/funzioni/trgfn_*_default_emittente.md` sono già in `git rm`, nasce
   `script/funzioni/trgfn_default_emittente_fiscale.md`, e le tabelle montate
   cambiano la riga del trigger;
4. ⏳ il **commit** (⚠️ nella stessa copia ci sono i file non committati dell'altro
   cantiere: `git add` mirato sui file di §12, non `-a`);
5. ⏳ le **quattro richieste al BE** (§11) — la prima è bloccante per la CI
   (`test_il_file_generato_e_allineato_al_catalogo` e
   `test_nessun_codice_nuovo_senza_policy` diventano rossi al merge finché
   `genera_error_policies` non gira).

---

## 13. Riferimenti

- La decisione: [brief Lotto 1 §4.7](brief-db-magazzino-lotto-1-terreno-vuoto.md)
  (15-09), memoria `feedback_duplicati_si_ritirano_nello_stesso_cantiere`.
- Le forme da copiare: il ritiro di un codice con `obsoleto_dal`
  `20_code/anagrafiche/20260820-02` (funzione doppione + codice 131); un
  trigger generico in `script` che legge `NEW` da `to_jsonb`
  `script.trgfn_guard_emittente_scope` (`20260904`, fase 6); il test
  dell'ordine dei `BEFORE ROW` `vendite/test-emittente-ddt-simmetria-v1` test
  10; la fixture a due aziende `rls/test-rls-magazzino-perimetro-v1`.
- Doc auto-gen letta (15-09): `vendite/funzioni/trgfn_*_default_emittente.md`
  (cinque), `trgfn_ddt_normalize.md`, `trgfn_resi_normalize.md`,
  `trgfn_preventivi_guard_emittente_ba.md`, `fn_crea_revisione_preventivo.md`,
  `fn_create_contratto.md`, `script/funzioni/fn_resolve_emittente_for_user.md`,
  `script/funzioni/trgfn_guard_emittente_scope.md`, le tabelle di §2.2.
- `AGENTS.md` §«Sollevare un errore: tre canali» (il `%s` diagnostico),
  §«Guard vs Check».

---

## 14. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-17 | **P-6 e P-7 scritti e provati.** pgTAP nuovo a 18 asserzioni (runner `app`, fixture costruita) + test 5 dei preventivi su `throws_like`; tre pgTAP verdi pre-apply da owner (18/18, 6/6, 12/12). Doc: manual nuovo, quattro ritirati (+ quattro pagine auto-gen), **otto** manuali ripuntati (il censimento §2.4 contava le sole guide: i link stavano anche nei `manual/` dei guard BA e in `preventivi.md`/`ordini.md`), guide, `fn_crea_revisione_preventivo.md`, `magazzini.md`, `assets.md`. Consegna in §12. ⭐ Provando D3 sotto RLS: lo scenario «SA con emittente attivo B revisiona A» non esiste (l'impersonazione restringe la lettura) — il caso vero è il SA in modalità «tutti», che prima **non poteva revisionare nulla** |
| 2026-09-15 (notte) | **P-1 → P-5 scritti e provati** (`20260915-36 → -46`, CSV in place): SQL estratto con `updateSQL` offline, preCondition + struttura + nove mutazioni in `BEGIN … ROLLBACK`, tutte verdi. Trovato provando: (1) la `NOTE` di `-41` nominava la copia ritirata e rendeva rosso il presidio «nessuna funzione viva le nomina» → riscritta; (2) un DDT in `EMESSO` numera **prima** del normalize (`fn_assegna_numero_documento` vuole l'emittente): la prova di `LASCIA_NULL` si fa su un DDT `DRAFT` — non è un difetto del lotto, era così anche prima; (3) l'id del messaggio è 1074, non 1072: l'altro cantiere ha seminato due codici nel frattempo — riletto prima di scrivere |
| 2026-09-15 (sera) | **Nascita**, dalla decisione di Tid sul §4.7 del Lotto 1. Censimento: le cinque `trgfn_*_default_emittente` di vendite sono **tre copie + una variante (ddt) + una cosa diversa (commesse)**; nove tabelle ancorate senza default, di cui due derivano dal padre e due sono la mappa; tre codici con **due `ui_action`**; il `%s` dei messaggi riceve diagnostica. 🔴 Trovato: `fn_crea_revisione_preventivo` non copia `emittente_fiscale_id` (D3). Cinque decisioni in §3, corpo del BB in §4, sette passi in §8 |
