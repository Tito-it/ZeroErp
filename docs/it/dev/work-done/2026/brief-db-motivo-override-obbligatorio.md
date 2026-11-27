# Brief DB — il motivo di un override utente è obbligatorio

> **⏭️ Chi riparte — aggiornato al 2026-11-27**
>
> **✅ Chiuso e archiviato il 2026-11-27: non riparte nessuno.** Il passaggio BE/FE è scritto, provato, collaudato a
> video da Tid e committato (§5-bis). Il giro DB è chiuso e committato (`b1b61a7ca`): applicato su scratch e
> dbdev, pgTAP verdi col runner (Tid, 2026-11-27), baseline B-7 confrontata senza accumuli (§7.4). `20261126-80`
> (la primitiva), `-81` (i `COMMENT` dei tre verbi), `-82` (il `COMMENT` della colonna `motivo`), il codice
> `E_OVERRIDE_MOTIVO_OBBLIGATORIO` nei due CSV del catalogo, un pgTAP nuovo e due adeguati, la guida e i `manual/`.
> Nasce dalla verifica del giro 10-quater di
> [brief-db-porte-aperte-dalla-sola-guc](brief-db-porte-aperte-dalla-sola-guc.md): la guida dei
> permessi dice che il motivo è obbligatorio, il codice lo lasciava vuoto, e Tid ha scelto di correggere il codice.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | ✅ Tid | il via e le decisioni D-1 … D-4 (2026-11-27) | §4, §6.7 | — |
> | 2 | ✅ team DB | il giro scritto e provato sullo scratch (2026-11-27) | §7 | — |
> | 3 | ✅ Tid | l'apply su scratch e dbdev, i pgTAP del §7.3 col runner (2026-11-27) | §7.3 | — |
> | 4 | ✅ team DB | la baseline B-7: nessuna riga da scrivere, confronto verde su scratch e dbdev (2026-11-27) | §7.4 | — |
> | 5 | ✅ Tid | il commit del giro DB (`b1b61a7ca`); la doc auto-generata | §7.3 | — |
> | 6 | ✅ team BE/FE | il passaggio: il dialog del motivo, la policy del codice, i test, il manuale (2026-11-27) | §5-bis | — |
> | 7 | ✅ Tid | il collaudo a video del dialog (2026-11-27), il commit del passaggio BE/FE | §5-bis | — |
> | 8 | ✅ team BE/FE | l'archiviazione in `work-done/` (2026-11-27); la suite intera non lanciata, per scelta di Tid («dai tutto per fatto»): la fa girare la CI | — | — |
>
> Decisioni di Tid, tutte prese il 2026-11-27: D-1 **a**, la regola nella primitiva; D-2 **b**, le righe di oggi senza
> motivo restano; D-3 **b**, il pannello chiede un motivo al salvataggio; D-4 **no**, togliere un override non chiede
> motivo (§6.7).
>
> **Brief vicini verificati** (2026-11-27, ricerca di `user_override` e `motivo` in `work-in-progress/`): nessuno
> tratta il motivo degli override. `permessi-e-autorizzazioni-v3` (dormiente) non lo nomina;
> `valutazione-modello-di-dominio-db` non tocca queste tabelle.
>
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti` sulle tre tabelle, i tre verbi e i builder pgTAP,
> 2026-11-27):
> * [architettura-permessi-e-autorizzazioni](../../../guide/architettura-permessi-e-autorizzazioni.md) §4.8: «Il
>   motivo è obbligatorio per audit: consente di tracciare perché e da chi l'eccezione è stata concessa».
>   **Contraddetta** dal codice di oggi; decisione di Tid del 2026-11-27: vale la guida, si allinea il codice.
>   «Da chi» lo dice già l'audit; il motivo porta il «perché». Il giro rilegge §4.1-§4.8 (le tre tabelle) e «Chi
>   scrive gli override».
> * [pgtap-come-si-scrive-un-test](../../../guide/pgtap-come-si-scrive-un-test.md): i builder scrivono già un motivo
>   (§2). **Coerente**.
> * `risorse-umane-e-accessi`, `architettura-multi-face-auth`: nominano le tabelle, non il motivo. **Coerenti**.

## 1. Il problema, sul modello

Un override utente è un'eccezione al profilo: dà a una persona un livello, un oggetto o un'azione che il reparto non
le dà, oppure glieli toglie. L'audit registra chi l'ha scritto e quando; **perché** lo dice solo il `motivo`. Un
override senza motivo è un'eccezione ai permessi che nessuno sa più spiegare, e che nessuno osa togliere.

La regola vale per **ogni** override, anche per quelli che tolgono (`BLOCCATO`, `abilitata = false`): anche una
restrizione è un'eccezione al profilo, e va spiegata allo stesso modo.

E vale **al DB**: dal giro 10-quater le tre tabelle si scrivono solo dalla primitiva
`config.fn_applica_imposta_override` (attraverso i tre verbi del SUPER_ADMIN e il provisioning). Una regola tenuta
solo nel service la scavalca il primo chiamante che non passa da lì.

## 2. Che cosa c'è oggi — fatti datati al 2026-11-27

* `config.user_override_aree`, `config.user_override_azioni` e `config.user_override_oggetti`: `motivo text`
  **nullable**, nessun `CHECK` (doc auto-generata).
* `config.fn_applica_imposta_override` (`20261126-50`): ammette la chiave `motivo` e ne scrive il valore così com'è,
  `NULL` compreso.
* I builder pgTAP (`fn_pgtap_concedi_livello_area`, `fn_pgtap_concedi_azione`, `fn_pgtap_nega_azione`) scrivono
  sempre un motivo («Fixture pgTAP…»). `fn_pgtap_scrivi_override` riscrive le voci che legge, con il loro motivo:
  una voce già senza motivo sarebbe rifiutata alla riscrittura.
* Il provisioning di sviluppo (`20261126-54`) scrive i suoi override con un motivo.
* BE: `AmmSoftwareService._voci_override` legge il motivo con `optional_string`, cioè vuoto ammesso.
* FE: `OperatorePermessiTab.vue` (`_toAreaItem`, `_toAzioneItem`, `_toOggettoItem`) rimanda il `motivo` letto dal GET,
  ma la matrice **non ha un campo per scriverlo**: ogni override creato dalla schermata nasce senza motivo.
  ⚠️ Il commento sopra quelle funzioni descrive ancora il `PUT` come `DELETE WHERE auth_user_id` + reinsert: dal
  2026-11-27 è il verbo. È da correggere nel passaggio BE/FE.

## 3. Che cosa si cambia — proposta

1. **La regola sta nella primitiva**, non nelle colonne: `config.fn_applica_imposta_override` rifiuta un elemento
   con `motivo` assente, `NULL` o fatto di soli spazi, con un **codice d'errore nuovo** a catalogo (nome proposto
   `E_OVERRIDE_MOTIVO_OBBLIGATORIO`), il campo `motivo` nel canale `COLUMN` e un hint che dice cosa scrivere. La
   primitiva è l'unica strada di scrittura: un vincolo di colonna ripeterebbe la regola, e darebbe un 23502 o un
   23514 da tradurre per nome invece di un codice del dominio. ✅ D-1 **a** (Tid, 2026-11-27).
2. **Il motivo si salva ripulito** (`btrim`), come ogni testo libero.
3. **I pgTAP**: un test nuovo (le tre tabelle: motivo assente, `NULL`, vuoto, soli spazi → rifiutati; un motivo →
   scritto), anche per un override che toglie. I pgTAP che scrivono override senza motivo, se ce ne sono, si portano ai
   builder o ricevono un motivo.
4. **La guida** `architettura-permessi-e-autorizzazioni` §4.8 dice dove sta la regola (la primitiva) e che vale anche
   per gli override che tolgono; i `manual/` delle tre tabelle e della primitiva lo stesso.
5. **I dati di sviluppo**: le righe senza motivo, se ce ne sono, non si toccano (D-2 **b**, Tid, 2026-11-27). La
   regola vale alla scrittura: la prossima riscrittura dell'elenco di quell'utente le rifiuta finché non ricevono un
   motivo, e il pannello lo chiede (D-3 **b**). Nessun changeSet di dati. ⚠️ Vale anche per `fn_pgtap_scrivi_override`,
   che riscrive l'elenco intero: sugli utenti costruiti dai builder il motivo c'è sempre.

## 4. Decisioni per Tid

| # | Domanda | Strade | Raccomandazione |
| --- | --- | --- | --- |
| **D-1** ✅ **a** (Tid, 2026-11-27) | Dove sta la regola? | **a** nella primitiva, col codice del dominio · **b** `NOT NULL` + `CHECK (btrim(motivo) <> '')` sulle tre colonne · **c** tutte e due | ⭐ **a**: la primitiva è l'unica strada di scrittura e dà un errore che il BE non deve tradurre per nome. **c** se si vuole la regola anche contro una scrittura del proprietario |
| **D-2** ✅ **b** (Tid, 2026-11-27) | Le righe di oggi senza motivo? | **a** un changeSet di dati scrive un motivo di ripiego («Motivo non registrato prima del 2026-11-27») · **b** restano: la prossima riscrittura chiede di scriverlo | ⭐ **a** con **D-1 c** (il vincolo lo esige); con **D-1 a** basta **b**, e il pannello lo chiede alla prima modifica. Decisa **b**: un motivo di ripiego non spiega niente |
| **D-3** ✅ **b** (Tid, 2026-11-27) | Il motivo nel pannello: uno per voce, o uno per salvataggio? | **a** un campo per voce, nella riga della matrice · **b** un motivo chiesto al salvataggio, scritto sulle voci cambiate | la regola del DB è per voce in tutte e due le strade. Decisa **b**: una richiesta porta più cambi con una ragione sola. Il motivo va sulle voci cambiate **e** su quelle vecchie ancora senza; le altre tengono il loro |

## 5. Il passaggio al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Fino all'apply il BE resta com'è (`optional_string`): una richiesta senza motivo oggi
passa, e dopo l'apply la rifiuta il DB col codice nuovo.

1. `AmmSoftwareService._voci_override`: il motivo con `require_string` (400 sul campo, prima del DB).
2. `genera_error_policies` per il codice nuovo, e il ripiego senza `%s`.
3. FE (D-3 **b**): in `OperatorePermessiTab.vue`, al salvataggio, un dialog chiede il motivo, obbligatorio, se
   almeno una voce è cambiata o è senza motivo. Il testo va sulle voci cambiate e su quelle senza motivo (D-2 **b**);
   le altre partono col loro. Il rifiuto del DB col codice nuovo si mostra nel dialog. Testi i18n. Il commento su
   `DELETE` + reinsert si corregge (§2).
4. I test sul DB vero che mandano voci senza motivo: in `test_override_aree_azioni_db` i casi 3 e 4, e gli altri che
   la ricerca trova al momento (`grep -rn "put_override_" backend/apps --include=*.py`).
5. Manuale `api_amm_software` §2.2, §2.4, §2.4-bis: il motivo è obbligatorio.

## 5-bis. Il passaggio BE/FE, fatto (2026-11-27)

| Punto del §5 | Esito |
| --- | --- |
| 1. `require_string` nel service | ⚠️ **non fatto, di proposito**: il motivo resta `optional_string`. La regola sta nel verbo (D-1 **a**) e un `require_string` ne sarebbe la seconda sede, che risponderebbe `E_AMM_VALIDAZIONE` al posto del codice del dominio. È la forma già usata da `blocca_credenziale`, dalla disattivazione del TOTP e dalla rettifica di listino. Il rifiuto del DB attraversa `translate_db_errors` col suo codice e il campo `motivo` (`error.fields`): lo prova il caso 5 di `test_override_aree_azioni_db`. Commento in `_voci_override`. ✅ Confermato da Tid (2026-11-27) |
| 2. Policy e ripiego | `genera_error_policies` rigenerato (`--check` pulito, zero classi cambiate). Il rigenero porta anche i quattro codici di T8c di `brief-db-revisione-anagrafiche` (`E_DDT_VETTORE_NON_ATTIVO`, `E_ENTE_INCASSO_PSP_SPENTO`, `E_PSP_ENTI_INCASSO_ATTIVI`, `E_SPECIALIZZAZIONE_SOGGETTO_IMMUTABILE`), già nel CSV in git: il modulo è uno solo. Ripiego senza `%s` per tutti e cinque |
| 3. FE | `OperatorePermessiTab.vue`: il Salva apre `MotivoDialog` (BB, obbligatorio) se almeno una voce delle sezioni da salvare è nuova, cambiata o senza motivo; il motivo va su quelle, le altre ripartono col loro. Dopo ogni sezione salvata la mappa a video si riallinea alla risposta (col motivo appena scritto). Un rifiuto lascia il dialog aperto, col campo in errore (`campiErrati`; la rilettura dei derivati ha un handler suo per non azzerarlo). Commento sul `DELETE` + reinsert corretto. i18n it/en |
| 4. Test sul DB vero | `test_override_aree_azioni_db`: motivo nei casi 3 e 4, caso 5 nuovo (assente, soli spazi su una voce che toglie, `null` su un'azione negata → `E_OVERRIDE_MOTIVO_OBBLIGATORIO`, campo `motivo`, niente scritto). `test_override_oggetti_catalogo_db`: motivo nei casi 3, 4, 5, che senza sarebbero usciti col codice del motivo smettendo di provare la FK (come il caso 9 del pgTAP). `test_creazioni_dalle_madri_db` lo aveva già. `smoke-test-permessi-oggetto.sh` (revisione del 2026-11-27): il passo 6 manda un motivo, perché il rifiuto del motivo non faccia passare il passo senza provare il catalogo; il ripristino del passo 11 rimanda le voci di partenza, e a una voce scritta prima della regola senza motivo dà «Ripristino dello smoke: la voce non aveva motivo», perché senza il verbo la rifiuterebbe e il ripristino fallirebbe |
| 5. Manuale | `api_amm_software` §2.2 («Il motivo»), §2.4, §2.4-bis: obbligatorio, codice, campo, `btrim`, D-4, D-2 **b** |

⚠️ **D-4 e il §7.5, letti insieme.** Il §7.5 dice che il dialog si apre anche se l'unico cambio è una voce tolta;
D-4 dice che togliere non chiede motivo, e il testo va solo sulle voci che restano. Se si sono solo tolte voci e
quelle che restano hanno già il loro motivo, un motivo chiesto non andrebbe su nessuna riga: sarebbe una traccia
che non resta. Il pannello quindi **non apre il dialog** in quel caso (caso 11 dello spec); lo apre se una voce che
resta è senza motivo. ✅ Confermato da Tid (2026-11-27): niente dialog quando si sono solo tolte voci già motivate.

Prove (2026-11-27): `OperatorePermessiTab.spec.js` 13 verdi (casi 10-13 nuovi; il 10 provato per mutazione sulle due
regole, il motivo solo dove serve e la voce senza motivo che lo chiede), `OperatoreDrawer.spec.js` e
`MotivoDialog.spec.js` verdi; Django sul DB vero (`ZEROERP_TEST_DB_E2E=1`) i due test DB, i cancelli dei codici
(`test_error_policies_classi`, `test_error_policies_divergenza_db`, `test_error_codes_db_policy_guardrail`), i test
del service e dell'API degli override. Guide: `architettura-permessi-e-autorizzazioni` §4.8 **coerente** (descrive
già il dialog); `risorse-umane-e-accessi`, `architettura-multi-face-auth` **coerenti**.

**Collaudo a video (Tid).** Drawer di un operatore, scheda Permessi: (a) cambiare un livello e salvare → il dialog
chiede il motivo, il Salva è spento finché è vuoto; (b) dopo il salvataggio, riaprire: la voce porta il motivo;
(c) togliere un override di un utente le cui voci hanno tutte un motivo → salva senza dialog; (d) un utente con
voci vecchie senza motivo (su dbdev il 6, il 9, il 48890, fatto del 2026-11-27): cambiare una voce qualsiasi della
stessa sezione → il dialog si apre e il motivo va anche sulle vecchie.

## 6. L'analisi del giro (2026-11-27)

Letta sulla doc auto-generata e sui pgTAP del checkout, senza prove. Le misure che seguono sono fatti datati: dicono
che cosa si deve adeguare, non che forma ha la regola.

### 6.1 La regola, nella primitiva

In `config.fn_applica_imposta_override`, nel **primo** ciclo sugli elementi, **dopo** `script.fn_guard_campi_ammessi` e
prima del `DELETE`. Il controllo segue il guard dei campi, così una chiave estranea resta `E_CAMPO_NON_AMMESSO` anche
senza motivo, e precede il `DELETE`, così l'elenco si giudica tutto prima di toccare una riga:

* `jsonb_typeof(v_el -> 'motivo') IS DISTINCT FROM 'string' OR btrim(v_el ->> 'motivo') = ''` →
  `E_OVERRIDE_MOTIVO_OBBLIGATORIO`. Un motivo assente, `null`, non di testo (un numero, un oggetto), vuoto o di soli
  spazi è la stessa mancanza: un codice solo.
* Contesto: `campo = 'motivo'` (il canale `COLUMN`), `auth_user_id`, `tabella`, `indice` (la posizione nell'elenco, da
  0) e la **chiave della voce** (`area_id`, `azione_id`, oppure `app_label` + `model_name`). Il dialog di D-3 **b** ha un
  campo solo, ma chi diagnostica deve sapere quale voce. Niente `bersaglio`: la voce non è un'entità di
  `config.tipi_entita`.
* La scrittura riceve il motivo ripulito: `v_el || jsonb_build_object('motivo', btrim(v_el ->> 'motivo'))`.
* Il letterale si solleva con `script.fn_log_and_raise_error` (linee-guida-sql §5, «Due funzioni per sollevare»).

**Regola del 2.** I verbi col motivo obbligatorio (`fn_blocca_credenziale`, `fn_totp_disabilita_device`, il guard
di `processi_accensione`, quelli di vendite e pagamenti) scrivono la stessa riga, `IS NULL OR btrim(…) = ''`, ognuno
col codice del suo dominio. Non c'è un BB, e non ne nasce uno qui: la riga è un predicato di una riga, e ciò che
cambia fra le sedi è il codice. Lo si dice per chi rifà la ricerca.

Il verbo resta la porta: i tre `fn_imposta_override_*` chiedono il SUPER_ADMIN prima di chiamare la primitiva, quindi
un operatore riceve sempre `E_PERMESSO_NEGATO` per primo, con o senza motivo (casi 7-11 di
`test-porta-override-permessi-v1`).

### 6.2 Il codice d'errore

`E_OVERRIDE_MOTIVO_OBBLIGATORIO`, classe `DATO_ERRATO`, come gli altri `*_MOTIVO_OBBLIGATORIO` del catalogo (sette).
Il messaggio e l'hint seguono quelli di `E_CREDENZIALE_MOTIVO_OBBLIGATORIO`: «Indicare il motivo dell'eccezione ai
permessi.» / «Un'eccezione ai permessi di un utente richiede sempre un motivo.» / «Scrivere perché l'utente riceve, o
perde, questo permesso.» Sedi: `codici_errore.csv`, `messaggi_errore.csv`, la riga della baseline B-7 (solo questa,
`ref_baseline_b7_per_righe_del_cantiere`).

### 6.3 Chi scrive oggi, e che cosa si adegua

| Scrittore | Motivo oggi | Esito |
| --- | --- | --- |
| I tre verbi del SUPER_ADMIN, dal BE | facoltativo (`optional_string`) | rifiutati senza motivo dopo l'apply: è la regola. Il BE e il pannello si adeguano (§5) |
| Il provisioning di sviluppo (`20261126-54`, le due chiamate) | sempre | nessuno |
| I builder `fn_pgtap_concedi_livello_area`, `_concedi_azione`, `_nega_azione` | sempre («Fixture pgTAP…») | nessuno |
| `fn_pgtap_scrivi_override`, chiamato a mano (`test-fn-pannello-scrivi-v1`, `test-porta-ddt-riconsegna-v1`, `test-anagrafiche-magazzino-sola-lettura-v1`) | sempre | nessuno. Riscrive anche le voci che trova, ma i pgTAP che scrivono le tabelle con un `INSERT` diretto e usano poi un builder sullo stesso utente (`test-fn-guard-azione-v1`, `test-permessi-tetto-area-v1`) lo scrivono già |
| `test-porta-override-permessi-v1`, caso 12 | **no**: le due voci della prima chiamata | si aggiunge il motivo |
| `test-fn-imposta-override-emittente-attivo-v1`, casi 3, 6 e 9 | **no** | si aggiunge il motivo. Il 9 è il più delicato: senza motivo darebbe il codice nuovo al posto del `23503` della FK, e smetterebbe di provare ciò che dice |
| Gli `INSERT` diretti dei pgTAP da proprietario (sette file) | quasi sempre | nessuno: D-1 **a** mette la regola nella primitiva, non sulle colonne |

### 6.4 Il pgTAP nuovo

`db/pgtap/config/test-override-motivo-obbligatorio-v1.sql`, da un SUPER_ADMIN di fixture
(`dbops.fn_pgtap_entra_come_super_admin`):

1. Sulle tre tabelle: motivo assente, `null`, `''`, `'   '`, `123` → `E_OVERRIDE_MOTIVO_OBBLIGATORIO`.
2. Il rifiuto non tocca l'elenco di prima: le voci dell'utente restano quelle di prima (il controllo precede il
   `DELETE`).
3. La seconda voce senza motivo, la prima con il motivo: rifiutata tutta, col contesto `indice = 1`.
4. Un override che toglie (`BLOCCATO`, `abilitata = false`) senza motivo: rifiutato.
5. `'  Delega temporanea  '` → scritto `'Delega temporanea'`.
6. Chiave estranea e motivo assente insieme: `E_CAMPO_NON_AMMESSO` (l'ordine dei due controlli).
7. L'elenco vuoto non chiede niente: toglie le voci.
8. Il canale `COLUMN` porta `motivo` (`dbops.fn_pgtap_codice_errore` per il codice, il canale col pattern già in uso
   nei pgTAP del catalogo errori).

### 6.5 Guide e `manual/`

* [architettura-permessi-e-autorizzazioni](../../../guide/architettura-permessi-e-autorizzazioni.md): la regola sta oggi
  nell'esempio di §4.8 (azioni), mentre vale per le tre tabelle. Va scritta una volta in «Chi scrive gli override», con
  la primitiva per nome (`guide_coinvolte.py` la trova orfana), anche per gli override che tolgono; §4.8 rimanda lì.
  §13.2, l'audit: il motivo è il «perché», l'audit il «chi» e il «quando».
* `manual/` di `fn_applica_imposta_override`, dei tre `fn_imposta_override_*` e delle tre tabelle: il rifiuto, il codice,
  il `btrim`.
* Il `COMMENT` della primitiva e dei tre verbi: il codice nuovo fra i rifiuti.

### 6.6 I changeSet

Uno in `20_code/config` (la primitiva, col `COMMENT`) e uno per i `COMMENT` dei tre verbi, se si vuole il codice nuovo
anche lì; le righe dei due CSV del catalogo errori nel loro seed. I numeri si prendono con
`scripts/prossimo_changeset.py` subito prima di scrivere, sul range che dà Tid.

### 6.7 Una domanda nuova, per Tid

**D-4 ✅ no (Tid, 2026-11-27): togliere un override chiede un motivo?** Il verbo sostituisce l'elenco, quindi una voce tolta semplicemente non
c'è più, e non ha dove portare un motivo. ⭐ Proposta: **no**. Il motivo spiega un'eccezione al profilo; tolta
l'eccezione resta il profilo, che non ha niente da spiegare. Chi l'ha tolta e quando lo dice `storico`, e il motivo
della voce tolta resta lì, nella sua ultima versione. Il dialog di D-3 **b** si apre anche per una voce tolta (è un
cambio), ma il testo va solo sulle voci che restano.

## 7. Il giro scritto (2026-11-27)

### 7.1 I file

| File | Che cosa |
| --- | --- |
| `20_code/config/20261126-80-update-fn-applica-imposta-override-motivo-obbligatorio` | la primitiva: la regola nel primo ciclo, dopo il guard delle chiavi e prima del `DELETE`; il motivo scritto con `btrim`; il `COMMENT`. Firma invariata (`%TYPE` sull'utente), rollback al corpo del `-50` |
| `20_code/config/20261126-81-update-comment-verbi-override-motivo-obbligatorio` | i `COMMENT` dei tre verbi, presi dal catalogo e riscritti in due punti: il motivo fra le chiavi obbligatorie, il suo rifiuto. Firme col `%TYPE` |
| `00_schema/config/20261126-82-comment-colonna-motivo-user-override` | il `COMMENT` della colonna `motivo` sulle tre tabelle: obbligatorio alla scrittura, e perché una riga può non averlo |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_OVERRIDE_MOTIVO_OBBLIGATORIO`, `DATO_ERRATO`, messaggio senza segnaposto (id 1561). Campi contati dopo l'ultima scrittura, niente `CR` |
| `db/pgtap/config/test-override-motivo-obbligatorio-v1.sql` | nuovo, 16 casi (§6.4) |
| `db/pgtap/config/test-porta-override-permessi-v1.sql` (caso 12), `test-fn-imposta-override-emittente-attivo-v1.sql` (casi 3, 6, 9) | il motivo nelle voci |
| guida `architettura-permessi-e-autorizzazioni` («Chi scrive gli override», «Ogni override ha un motivo», §4.8, §13.2) | **indietro**, aggiornata nel giro: la regola per le tre tabelle, la primitiva per nome (non più orfana), la voce che toglie, D-4 |
| `manual/` della primitiva, dei tre verbi e delle tre tabelle | il rifiuto, il `btrim`, la colonna |

Rispetto al §6.4 il pgTAP non asserisce `indice` e `voce`: viaggiano nel contesto del log, non in un canale
dell'eccezione. Il caso 10 prova invece che l'elenco si giudica tutto prima di scrivere (la prima voce cadrebbe sulla
FK, vince il motivo della seconda).

### 7.2 La prova (scratch, da proprietario, in `ROLLBACK`)

* `-82`, `-80`, `-81` col pgTAP nuovo: senza l'estratto 5 ok / 11 rossi (la regola che non c'è), con l'estratto **16 ok**.
* `-80` con `test-fn-imposta-override-emittente-attivo-v1`: 13 ok senza e con.
* `-80` con `test-porta-override-permessi-v1`: senza 14 ok / 4 rossi, i rossi di perimetro che da proprietario lo sono
  per costruzione. Con l'estratto la corsa **si ferma al caso 16**, ed è un effetto della prova da proprietario: il caso 4
  (un `INSERT` diretto, che come app è `42501`) da proprietario riesce, e lascia all'operatore una voce senza motivo;
  `fn_pgtap_apri_area_per_nascita` riscrive le sue voci e la regola la rifiuta. Con quella riga tolta in una copia, la
  corsa con l'estratto torna 14 ok / 4 rossi come senza. Il test non è `pgtap-runner: owner`: col runner il caso 4 è
  rifiutato e la riga non nasce. ✅ Confermato: col runner il test è verde (Tid, 2026-11-27).
* Guardrail `forme`, `comment-al-presente`, `runOnChange`, `letterali`, `preCondition/seed`, `preambolo`: verdi.

⚠️ **L'effetto di D-2 b sui builder** (fatto del modello, non di oggi): `fn_pgtap_scrivi_override` riscrive tutte le
voci dell'utente, quindi un utente che ha una voce senza motivo non riceve più un livello dai builder, finché la voce
non riceve un motivo. I builder creano utenti nuovi; lo usa sull'utente di sessione solo
`fn_pgtap_apri_area_per_nascita`; i test BE che prendono il primo operatore dai dati usano i builder su di lui
(`apri_operatore_con_aree`). Una riga così si sistema dal pannello (D-3 **b**), non con un changeSet (D-2 **b**).

Fatti datati al 2026-11-27, letti come app in sola lettura: sullo scratch nessuna voce senza motivo; su dbdev 40 voci
senza motivo (aree 8 su 8, azioni 27 su 28, oggetti 5 su 6) di tre utenti, nessuno SUPER_ADMIN: 6 (30 voci), 9 (5),
48890 (5). Il primo operatore che i test BE prendono su dbdev è il 5 (`db_e2e.py`, «il primo attivo che non è
SUPER_ADMIN»), che non ne ha: oggi nessun test BE ne risente. Se il 5 cambia, o se un test sceglie il 6, il 9 o il
48890, il builder rifiuta col codice nuovo, ed è la regola.

### 7.3 Per Tid: l'apply e i pgTAP

`liquibase update`, poi col runner: `config/test-override-motivo-obbligatorio-v1`,
`config/test-porta-override-permessi-v1`, `config/test-fn-imposta-override-emittente-attivo-v1`,
`config/test-fn-pannello-scrivi-v1`, `vendite/test-porta-ddt-riconsegna-v1`,
`magazzino/test-anagrafiche-magazzino-sola-lettura-v1`, `script/test-fn-guard-campi-ammessi-v1` (legge il corpo della
primitiva), `script/test-catalogo-messaggi-errore-completo`. Poi la doc auto-generata.

### 7.4 Dopo l'apply: la baseline B-7 (2026-11-27)

Misurata come app in sola lettura (`scripts/sql/codici_errore_famiglie_snapshot.sql`) su scratch e dbdev, coi tre
changeSet applicati su tutti e due. **`E_OVERRIDE_MOTIVO_OBBLIGATORIO` non entra nello scatto**: la misura legge la
sua condizione (`jsonb_typeof(…) IS DISTINCT FROM 'string' OR btrim(…) = ''`) come `IGNOTO`, e un codice con sole
famiglie ignote non è presidiato (il limite dichiarato in testa a `scripts/codici-errore-baseline.sh`). Quindi
**nessuna riga da scrivere**, e la baseline non cambia. Il confronto (`scripts/codici-errore-baseline.sh`, come app):
213 codici presidiati, 0 accumuli, 0 ristretti, 0 rientrati, su scratch e su dbdev.

### 7.5 La richiesta al team BE/FE

Il §5, con due aggiunte:

* **la CI**: il guardrail «codice senza policy» è rosso dal merge del giro finché `genera_error_policies` non gira (§5.2);
* **D-4**: il dialog si apre anche se l'unico cambio è una voce tolta, ma il motivo va solo sulle voci che restano;
  togliere tutte le voci (elenco vuoto) non chiede motivo.

## Il piano

- [x] D-1 **a**, la regola nella primitiva (Tid, 2026-11-27)
- [x] D-2 **b**, D-3 **b** (Tid, 2026-11-27)
- [x] D-4 **no**, togliere un override non chiede motivo (Tid, 2026-11-27)
- [x] Il via, col range da `20261126-80` (Tid, 2026-11-27)
- [x] Il giro DB: primitiva, codice d'errore, pgTAP, guida e `manual/`; prova sullo scratch (2026-11-27, §7)
- [x] L'apply su scratch e dbdev, i pgTAP del §7.3 col runner (Tid, 2026-11-27)
- [x] La baseline B-7: nessuna riga, confronto verde su scratch e dbdev (2026-11-27, §7.4)
- [x] La doc auto-generata, il commit del giro DB (Tid, `b1b61a7ca`)
- [x] Il passaggio BE/FE (§5-bis, 2026-11-27)
- [x] Il collaudo a video del dialog (Tid, 2026-11-27), il commit del passaggio BE/FE
- [x] L'archiviazione (2026-11-27; suite intera lasciata alla CI, Tid)

---
{% include-markdown "signature-core.md" %}
