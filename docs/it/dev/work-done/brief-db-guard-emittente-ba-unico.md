# Brief DB — L'azienda che emette è quella del cliente: una regola, sette copie

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi BE (§6).
> **Origine:** §10.3 e §5.5 di [brief-db-esecutivi-ba-coppia](brief-db-esecutivi-ba-coppia.md), il
> debito fuori perimetro: «i guard emittente ↔ BA sono sette copie quasi uguali; il giro che li
> toccherà li estrae in un BB parametrico (regola del 2)».
> **Stato:** ✅ **lato DB applicato su dbdev e verde** (Tid, 2026-10-10: «migrazione applicata, test
> verde»; §8): 3 changeSet `20261010-17…-19`, codice `E_DOC_EMITTENTE_BA_INCOERENTE` (id 1243), sei
> codici ritirati, pgTAP nuovo a 10 test. ✅ **Ricaduta BE fatta il 2026-10-10 (§9).** Decisioni di Tid
> chiuse il 2026-10-10 (§4). ✅ **Chiuso e archiviato il 2026-10-10.** Il difetto trovato dal giro BE
> (§9.2: la vista del presidio C2 non vede i BB trigger col codice negli argomenti) non è di questo
> brief e vive come voce **D24** del registro.
> **Nel registro dei difetti DB:** voce **D22** di `migliorie-generali-da-test-valutazione.md` (chiusa,
> §7), che rimanda qui; il seguito è **D24**.

## 1. La regola

Un documento di vendita è emesso dall'**azienda del suo cliente**: l'emittente del documento è quello
che il billing account risolve (`anagrafiche.fn_get_emittente_fiscale_pk`). È una regola sola, e vale
per sette tabelle: preventivi, offerte, contratti, ordini, DDT, resi, commesse.

Oggi è scritta **sette volte**, una funzione trigger per tabella. La regola del 2 chiede una sede.

## 2. Che cosa dice oggi il DB (doc auto-generata, 2026-10-10)

| Tabella | Funzione | Fascia | Colonna dell'emittente | Risolutore | Codice | Classe | Esce se BA NULL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `preventivi` | `trgfn_preventivi_guard_emittente_ba` | `_a10_` | `emittente_fiscale_id` | `fn_get_emittente_fiscale_pk` | `E_PREV_EMITTENTE_BA_INCOERENTE` | DATO_ERRATO | sì |
| `offerte_commerciali` | `trgfn_offerte_commerciali_guard_emittente_ba` | `_a10_` | idem | idem | `E_OFFERTA_…` | DATO_ERRATO | sì |
| `contratti` | `trgfn_contratti_guard_emittente_ba` | `_a10_` | idem | idem | `E_CONTRATTO_…` | DATO_ERRATO | **no** |
| `ordini` | `trgfn_ordini_guard_emittente_ba` | `_a10_` | idem | idem | `E_ORDINE_…` | DATO_ERRATO | sì |
| `ddt` | `trgfn_ddt_guard_emittente_ba` | `_z10_` | idem | idem | `E_DDT_…` | DATO_ERRATO | sì |
| `resi` | `trgfn_resi_guard_emittente_ba` | `_z10_` | idem | idem | `E_RESO_…` | DATO_ERRATO | sì |
| `commesse` | `trgfn_commesse_guard_emittente_ba` | `_a10_` | **`emittente_soggetto_ruolo_id`** | **`fn_get_emittente_fiscale_id`** | `E_COMMESSA_…` | **TECNICO** | no |

Tutti montati `BEFORE INSERT OR UPDATE OF billing_account_id, <colonna dell'emittente>`. Nessun altro
trigger `BEFORE` scrive quelle colonne su UPDATE, quindi `UPDATE OF` è la forma giusta
(linee-guida-trigger, «Scelta tra UPDATE e UPDATE OF»).

**Le sei copie dei documenti sono identiche nel testo**, tranne il nome della tabella e il codice. La
commessa è la stessa regola con un'altra colonna (il ruolo dell'emittente invece della PK) e un'altra
classe: lì nessuna persona sceglie l'emittente, lo deriva il push, e un valore diverso è un chiamante
rotto (TECNICO, scelta dichiarata nel suo COMMENT).

### 2.1 Difetti che le copie portano con sé

1. **La frase mostra nomi di colonna all'utente.** Le sei frasi a catalogo dicono «Ordine:
   emittente_fiscale_id non corrisponde all'emittente derivabile dal billing_account_id.» — nessun
   segnaposto, nessun dato leggibile. I guard passano comunque un VARIADIC tecnico
   (`'ba=…, ef=…, ef_atteso=…'`), che la frase non usa. La commessa invece ha una frase leggibile
   («Commessa %s: l'emittente indicato (%s) non è quello del billing account %s (%s)»).
2. **Il log perde la transazione**: tutte e sette passano `NULL::uuid` al posto di `NEW.tx_id`.
3. **Sei codici per lo stesso significato.** Il progetto ha già scelto «un codice per la regola»
   altrove (`E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`, `E_DOC_EMITTENTE_FUORI_BOZZA`, entrambi del 2026-10-09).
4. **L'uscita sul BA NULL** è diversa da tabella a tabella senza una ragione scritta: i contratti e le
   commesse non ce l'hanno. Su preventivo, offerta e ordine il BA è NOT NULL, ma il NOT NULL si
   controlla dopo i trigger `BEFORE` (§6.3 di brief-db-istanza-nasce-col-ba): l'uscita serve a far
   parlare il vincolo invece del risolutore. Su DDT e reso il BA NULL è un caso del modello.

## 3. Forma proposta

Un **building block trigger**, montato sulle sette tabelle:

```sql
CREATE TRIGGER trg_ordini_a10_guard_emittente_ba_ins_upd
  BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id ON vendite.ordini
  FOR EACH ROW
  EXECUTE FUNCTION script.trgfn_doc_guard_emittente_ba(
    'Ordine',                      -- [0] come chiamare il documento nella frase
    'emittente_fiscale_id',        -- [1] la colonna dell'emittente
    'E_DOC_EMITTENTE_BA_INCOERENTE'); -- [2] il codice (vedi D-1)
```

* legge le colonne con `to_jsonb(NEW)`, come il BB di testata `trgfn_doc_testata_lock_fuori_bozza`;
* il risolutore lo sceglie la colonna: `emittente_fiscale_id` → `fn_get_emittente_fiscale_pk`,
  `emittente_soggetto_ruolo_id` → `fn_get_emittente_fiscale_id`;
* BA NULL → esce (su tutte e sette: §2.1 punto 4);
* passa `NEW.tx_id`;
* montaggio sbagliato (colonna inesistente, argomenti mancanti) → errore di configurazione, come i
  due BB fuori bozza;
* i trigger mantengono **nome e fascia** di oggi (`_a10_`, e `_z10_` su DDT e reso, dopo il
  normalize che eredita il BA): cambia solo la funzione.

Le sette funzioni si ritirano nello stesso giro.

## 4. Decisioni per Tid

| # | Domanda | Proposta | Decisione di Tid |
| --- | --- | --- | --- |
| **D-1** | Un codice per i sei documenti, o uno per documento? | **Uno**, `E_DOC_EMITTENTE_BA_INCOERENTE` (DATO_ERRATO, `campo` = la colonna), come `E_DOC_EMITTENTE_FUORI_BOZZA`. I sei vecchi si ritirano. La **commessa tiene il suo** `E_COMMESSA_EMITTENTE_BA_INCOERENTE`: la classe diversa (TECNICO) è un significato diverso per chi riceve l'errore, non uno stile | ✅ **Uno solo** (Tid, 2026-10-10); la commessa tiene il suo |
| **D-2** | La frase | Leggibile, coi valori: «%s: l'azienda che emette (%s) non è quella del cliente (%s, billing account %s).» — documento, emittente indicato, emittente atteso, codice del BA. Niente nomi di colonna | ✅ **Sì, con i dati** (Tid, 2026-10-10). ⚠️ Nella frase vanno i **nomi** delle due aziende (come le chiama l'utente), non gli id: da dove leggerli si sceglie scrivendo il BB, e gli id restano nel contesto del log |
| **D-3** | La commessa entra nel BB? | **Sì**: è la stessa regola, e colonna, risolutore e codice sono argomenti. Restarne fuori la lascerebbe come seconda sede della stessa regola | ✅ **Dentro** (Tid, 2026-10-10). ⚠️ Conseguenza: il BB passa gli stessi valori per tutti e due i codici, quindi la frase di `E_COMMESSA_EMITTENTE_BA_INCOERENTE` va riscritta con i segnaposto nello stesso ordine di quella nuova (documento, emittente indicato, emittente atteso, BA) |
| **D-4** | Dove sta il BB | `script` (la sede comune dei BB lato DB, come `fn_cliente_dal_billing_account`), non `vendite`: la regola è di anagrafica (il BA risolve l'emittente) e vale su più tabelle | ✅ **`script`** (Tid, 2026-10-10) |

## 5. Da censire nel giro (non qui) — ⚠️ fatto nel giro, §8.2

* i pgTAP che citano i sei codici (uno, al 2026-10-10) e quelli che provano i sette guard;
* i COMMENT dei trigger, e le pagine `manual/` delle sette funzioni (da cancellare: oggetti ritirati);
* `anagrafiche.fn_check_ba_coppia_emittente_omogenea`, che la commessa nomina come «stessa scelta»:
  da guardare se è un'ottava copia della stessa regola;
* i presidi trasversali per una funzione plpgsql nuova (riferimenti morti, catalogo messaggi).

## 6. Ricaduta BE (dopo la consegna DB)

* `backend/apps/core/services/error_ui_overrides.py`: oggi ha una voce per ciascuno dei sei codici;
  con D-1 diventa una;
* policy generate e frase di ripiego del codice nuovo;
* nessun cambio di contratto per i form: l'errore resta sul campo dell'emittente.

## 7. Fuori da questo brief

* **Le altre colonne di testata in fase chiusa** (§8 di brief-db-esecutivi-ba-coppia): quali colonne
  di una testata si possono ancora cambiare dopo l'emissione. È una domanda di dominio, colonna per
  colonna: brief suo. ➡️ [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md) (D26,
  aperto il 2026-10-10).

## 8. Giro DB — consegna (team DB, 2026-10-10)

> ✅ **Applicato su dbdev, test verdi** (Tid, 2026-10-10), compresi `test-guard-emittente-ba-unico-v1`
> e `test-commesse-emittente-invariante-v1`, che sullo scratch non si potevano confermare. Sotto,
> l'avviso scritto prima, lasciato come storia della prova.
>
> ⚠️ **Scritto e provato, NON applicato.** Prova: SQL estratto dagli YAML, preCondition comprese, in
> una transazione annullata su `zeroerp_ci`, da proprietario, con `SET CONSTRAINTS ALL DEFERRED` e
> `myapp.log_with_dblink = off`; lo scratch aveva `20261010-01…-16`. Il catalogo nella prova: il
> codice nuovo con `INSERT`, la frase della commessa e i sei ritiri con `UPDATE` mirati. Passaggio su
> dbdev e corsa pgTAP restano di Tid.
> ⚠️ **Numerazione:** il primo file era nato `-08`; nel frattempo il cantiere R-5…R-9
> (`brief-db-codici-non-trovato-email-e-permessi`) aveva preso `-08…-16`. Rinumerato a `-17…-19`
> prima di ogni prova.

### 8.1 I changeSet

| # | Cosa | Decisione |
| --- | --- | --- |
| `-17` | **BB** `script.trgfn_doc_guard_emittente_ba()`, TG_ARGV = etichetta, colonna identificativa, colonna dell'emittente, codice | D-1…D-4 |
| `-18` | i sette trigger rimontati sul BB: **stesso nome, stessa fascia, stessi eventi** (`_a10_`; `_z10_` su DDT e reso, dopo il normalize) | D-1, D-3 |
| `-19` | ritirate le sette funzioni `vendite.trgfn_*_guard_emittente_ba` (preCondition: nessun trigger le usa) | regola del 2 |
| `80_data` | `E_DOC_EMITTENTE_BA_INCOERENTE` (DATO_ERRATO, id 1243); i sei codici per documento con `obsoleto_dal = 2026-10-10` (restano a catalogo per i log già scritti); frase di `E_COMMESSA_EMITTENTE_BA_INCOERENTE` riscritta nello stesso ordine di segnaposto; `E_DOC_RIGHE_LOCK_MONTAGGIO` con il terzo utente nella nota e nella causa | D-1, D-2, D-3 |

* **La frase (D-2):** «%s: l'azienda che emette (%s) non è quella del cliente (%s, billing account
  %s).» — documento, nome dell'azienda indicata, nome di quella del cliente, codice del BA. Il nome è
  `soggetti.ragione_sociale_completa`, la forma già in uso (`emittente_descrizione`,
  `cliente_display`); un'azienda che chi scrive non vede sotto RLS esce come `#id`. Gli id stanno nel
  contesto.
* **`campo` nel contesto solo se il codice non è TECNICO**: il BB lo legge da `config.codici_errore`
  (solo sul ramo d'errore). Così la commessa resta senza `campo`, come dichiarava il suo COMMENT.
* **BA NULL: esce su tutte e sette** (§2.1 punto 4). Su contratti e commesse il BA è NOT NULL, e il
  vincolo si controlla dopo i BEFORE ROW: parla lui.
* **`tx_id`**: il BB passa quello della riga (prima `NULL::uuid` in tutte e sette).
* **Montaggio errato** (argomenti mancanti, colonna che la tabella non ha, colonna dell'emittente
  diversa dalle due ammesse): `E_DOC_RIGHE_LOCK_MONTAGGIO`, il codice dei BB di documento montati male.
  ⚠️ È il **terzo** utente di un codice che nel nome parla di righe (domanda 5 di ba-coppia: nome
  tenuto per storia). Se il terzo utente fa cambiare idea, la rinomina vale per tutti e tre.

### 8.2 Censimento (§5)

* **pgTAP:** nessuno asseriva i sei codici; le citazioni delle sette funzioni erano descrizioni di
  test o commenti. Cambiato `vendite/test-commesse-emittente-invariante-v1` test 5, che controllava la
  frase vecchia della commessa.
* **`manual/`:** cancellate le sette pagine delle funzioni ritirate; pagina nuova
  `script/manual/trgfn_doc_guard_emittente_ba.md`, con i tre ragionamenti che valevano (DDT e reso dopo
  il normalize, solo due colonne, la commessa che sparisce); link riscritti in tre guide
  (`gestione-ordini`, `gestione-ddt`, `gestione-commesse`) e in otto pagine `manual/`.
* **Restano, e non sono un difetto:** tre COMMENT di funzioni vive nominano le funzioni ritirate in
  prosa (`trgfn_commesse_default_emittente`, `fn_crea_revisione_preventivo`,
  `fn_get_sorgente_emittente_sr_id`) — riscrivere tre funzioni per un commento non vale un changeSet:
  si aggiornano al primo giro che le tocca. Le pagine auto-generate si rigenerano da sole; i brief
  archiviati sono storia.
* **`anagrafiche.fn_check_ba_coppia_emittente_omogenea`** (§5): non è un'ottava copia. Controlla che
  **padre e figlio nell'albero dei billing account** (`parent_account_id`) risolvano la stessa
  azienda — l'albero omogeneo, da cui la fattura unica — non che un documento abbia quella del suo BA.
  Letta dalla doc auto-generata il 2026-10-10.

### 8.3 pgTAP

`vendite/test-guard-emittente-ba-unico-v1`, **10 test**, soggetti fabbricati (due emittenti, un
cliente): montaggio sulle sette tabelle con colonna e codice; le sette funzioni ritirate; i sei codici
ritirati e non sollevati; ordine con l'azienda sbagliata (codice dal canale `CONSTRAINT`) e la sua
frase; DDT senza BA che nasce; ordine giusto che nasce; commessa con l'azienda sbagliata (codice
TECNICO) e la sua frase; montaggio errato su una tabella temporanea.

⚠️ **DDT e reso non sono provati sul comportamento**, per costruzione: con l'emittente di un'altra
azienda sul DDT parla prima il guard di perimetro (`trg_ddt_a10_guard_emittente_scope`,
`E_SCOPE_EMITTENTE`), e il BA di un cliente dell'altra azienda l'operatore non lo vede (lo ferma prima
`script.fn_cliente_dal_billing_account`). La funzione è la stessa dell'ordine; il montaggio su DDT e
reso lo prova il test 1. La prima stesura aveva il caso del DDT, ed era rosso per questo motivo.

### 8.4 Prove (pre-apply, scratch, da proprietario)

* **preCondition:** `-17` 0, `-18` 1 e 7, `-19` 0, tutte come attese.
* **`plpgsql_check`** del BB su `ordini` e `commesse`: nessuna segnalazione.
* **pgTAP nuovo:** **10/10 dopo**; prima, senza il giro, 4 ok, 5 rossi e 3 errori.
* **Regressione**, 48 file con e senza il giro, ognuno nella sua transazione annullata: tutti quelli
  che nominano i sette guard, i sei codici o `guard_emittente`, il test della commessa, i presidi
  `test-riferimenti-morti-v1`, `test-catalogo-messaggi-errore-completo`, `test-codici-errore-obsoleto-dal`,
  `test-codici-errore-identita`, `test-vw-codici-errore-motivo-nominato`. **Identici prima e dopo**,
  tranne il test nuovo.
* ⚠️ **Sullo scratch molti di quei file sono rossi in tutte e due le corse**: pescano i dati della
  macchina, e lo scratch non li ha (per esempio il test della commessa: «precondizioni» `NULL`, e le
  query nascono vuote). Lì la regressione non si vede: **la conferma è la corsa di Tid su dbdev**, e
  in particolare `test-commesse-emittente-invariante-v1`, di cui è cambiata la frase attesa.
* **Guardrail CI** `scripts/sql/guardrail_codice_errore_strutturato.sql` dopo il giro: «nessun codice
  ritirato ancora sollevato (111 ritirati) né nei corpi né negli argomenti dei 2261 trigger».

### 8.5 Da Tid — ✅ fatto il 2026-10-10 (migrazione applicata, test verde)

* il passaggio su dbdev di `-17…-19` e dei due CSV;
* la corsa pgTAP: `test-guard-emittente-ba-unico-v1` (10/10 atteso anche come app) e
  `test-commesse-emittente-invariante-v1`.

### 8.6 Ricaduta BE (dopo il passaggio su dbdev) — ✅ fatta, §9

* `backend/apps/core/services/error_ui_overrides.py`: le sei voci dei codici ritirati diventano una,
  per `E_DOC_EMITTENTE_BA_INCOERENTE`;
* policy generate e frase di ripiego del codice nuovo; frase di ripiego di
  `E_COMMESSA_EMITTENTE_BA_INCOERENTE` allineata;
* `docs/it/backend/vendite/manual/api_ordini.md` riga 459 nomina `trgfn_ordini_guard_emittente_ba`
  (ritirata): diventa `script.trgfn_doc_guard_emittente_ba`.

## 9. Giro BE — consegna (2026-10-10)

### 9.1 Fatto

* **Policy rigenerate** (`genera_error_policies`, `--check` pulito): entrano
  `E_DOC_EMITTENTE_BA_INCOERENTE` (DATO_ERRATO) e i sei ritiri in `CODICI_RITIRATI`. **Zero classi
  cambiate.** Nello stesso rigenero entra `E_JOB_RUN_SALTATA_NON_CHIUDIBILE` di
  `brief-db-corsa-saltata-non-e-una-corsa`, già a catalogo in git (il suo ripiego c'era già).
* **`error_ui_overrides.py`:** le sei voci per documento diventano una,
  `E_DOC_EMITTENTE_BA_INCOERENTE → highlight_form_fields`, con la ragione delle sei (l'emittente è un
  input del form in tutti e sei i documenti). La commessa resta senza override (TECNICO).
* **Ripieghi:** frase nuova per `E_DOC_EMITTENTE_BA_INCOERENTE`, frase della commessa allineata al
  linguaggio della nuova («l'azienda indicata»). Le frasi dei sei ritirati restano, per leggere il
  diario.
* **Prova con una chiamata vera** (UPDATE annullato, contesto operatore) su ordine, preventivo e
  contratto: il BE riceve il codice dal canale `CONSTRAINT`, `fields = ('emittente_fiscale_id',)`
  dal canale `COLUMN`, e la frase coi nomi delle due aziende e il codice del BA. Nessun cambio di
  contratto per i form.
* Riferimenti alle funzioni ritirate: `api_ordini.md`, due commenti Python
  (`commesse_repository`, `contratti_service`), la tabella dei codici di `guide/gestione-ddt.md`.

### 9.2 ➡️ Spostato nel registro: D24 — la vista del presidio C2 non vede i BB trigger

Il presidio `apps/core/tests/test_ui_action_e_canale_campi.py` (verso 1) era rosso su
`E_DOC_EMITTENTE_BA_INCOERENTE` con «nessun sito», mentre la promessa del campo è mantenuta (§9.1):
`dbops.vw_punti_canale_campo` legge il codice dal corpo della funzione, e il BB lo riceve dagli
argomenti del trigger. Lato BE una riga in `_ESENZIONI[("E_DOC_EMITTENTE_BA_INCOERENTE", 1)]`,
motivata come esenzione della **misura**; si ritira da sola quando la vista vedrà il sito.

La cecità è della forma (otto funzioni, 24 codici su dbdev al 2026-10-10), non di questo brief: la
richiesta al team DB, il fatto datato e il ritiro dell'esenzione stanno nella voce **D24** di
[migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).
