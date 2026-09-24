# Brief DB — Accendere a catalogo le colonne in cui le liste già cercano

> **Destinatari:** team DB (`dev/db-tid`). Richiesta del BE, 2026-09-23.
>
> **Da leggere per primo: §6.6 (cosa resta al BE).**
>
> **Stato 2026-09-24 sera:** ✅ **lato DB CHIUSO** — applicato da Tid su dbdev
> e sullo scratch (`20260924-03…-08`, seed, codice errore), pgTAP verdi col
> runner; ⏳ resta da committare. Verificato sul vivo dopo l'apply: colonna
> `codice` NOT NULL, riga 938 accesa, le 33 righe di §3.1 accese e le 5 di
> §3.3-§3.5 spente, `E_UI_CHIAMATA_NON_VALIDA` a catalogo, `-08` entrato nella
> versione corretta (quella della delega per forma, §7). Il cantiere passa al
> BE: §6.6. Il brief si archivia quando il BE ha convertito le liste. Tutte le righe di §3.1-§3.5, più il codice errore chiesto dal
> brief BE §12 (`E_UI_CHIAMATA_NON_VALIDA`). §3.5 è arrivato come modifica di
> modello: quattro changeSet `20260924-03…-07` e un pgTAP. Dettaglio, scelte
> del team DB e ricadute sul BE in §6. **§7**: nello stesso giro, la correzione
> del presidio C2 (`20260924-08`) rosso dopo il cantiere prezzi — non nostro.

---

## 1. Perché

Dal 2026-09-23 la ricerca libera delle liste legge il catalogo a ogni ricerca
(`ui.fn_lista_colonne_ricerca_full`, BB `add_ricerca_full_condition`): si cerca
sulle colonne `ricercabile_full = t` **che il repository sa cercare**. Una lista
senza colonne accese, con un termine valido, **non trova niente**, di proposito
(brief BE §3).

Convertendo le liste è emerso che **12 liste cercano nel codice e hanno la
casella a video, ma non accendono nessuna colonna a catalogo**. Il contratto
dice «qui non si cerca», il codice cerca lo stesso. Tid ha deciso il 23-09 di
**accenderle** (brief BE §7-bis). Finché il seed non arriva, il BE non può
convertirle: col BB perderebbero la ricerca.

Nello stesso giro, due decisioni di Tid su liste già a catalogo (brief BE §7):
`anagrafiche.soggetti` cerca per **id fiscale univoco**, e `pagamenti.rate`
cerca **anche per documento** e mantiene l'id fiscale.

Brief BE: [brief-be-ricerca-full-liste-residue](brief-be-ricerca-full-liste-residue.md)
§7, §7-bis.

## 2. Come è stata fatta la ricognizione

Le 40 liste attive del seed senza colonne ricercabili sono state ripercorse una
per una: pagina del frontend, chiamata API, view, service, repository. **12
cercano** (sotto), **27 non cercano** e non mostrano la casella: per quelle
non si chiede niente. Fotografia del 2026-09-23.

## 3. Le righe da cambiare — `80_data/sql/ui/lista_colonna.csv`

### 3.1 `ricercabile_full` da `f` a `t` su righe esistenti

| Lista | id riga · `campo_sorgente` |
| --- | --- |
| `anagrafiche.soggetti` | 17 `id_fiscale_univoco_cf_piva` |
| `anagrafiche.clienti` | 3 `soggetto_codice`, 4 `id_fiscale_univoco_cf_piva` — il BE oggi cerca CF, P.IVA e codice soggetto: con queste due la conversione non perde niente (id fiscale univoco come per soggetti, decisione di Tid del 23-09) |
| `catalogo.articoli` | 321 `codice`, 322 `descrizione` |
| `vendite.listini` | 330 `codice`, 331 `descrizione` |
| `vendite.listini_righe` | 401 `articolo_codice`, 402 `articolo_descrizione` |
| `anagrafiche.categorie_clienti_listini` | 369 `categoria_codice`, 373 `listino_codice` |
| `vendite.promo_articoli` | 298 `codice`, 299 `descrizione`, 300 `articolo_codice` |
| `documenti.template_documenti` | 306 `codice`, 307 `descrizione` |
| `documenti.template_asset` | 313 `codice`, 314 `descrizione`, 317 `file_name` |
| `anagrafiche.operatori` | 337 `soggetto_cognome`, 338 `username` |
| `config.email_account` | 346 `codice`, 347 `descrizione`, 349 `email_from` |
| `config.email_template` | 352 `codice`, 353 `oggetto` |
| `config.email_log` | 359 `destinatario`, 360 `oggetto` |
| `vendite.dash_competenza_gruppi` | 443 `riferimento`, 445 `cliente_display`, 446 `commessa_codice`, 476 `ba_codice_fatturazione`, 477 `id_fiscale` |

### 3.2 Riga nuova

| Lista | `campo_sorgente` | Nota |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | `id_fiscale_univoco_cf_piva` | Per uniformità, tutte le anagrafiche cercano per id fiscale univoco (Tid, 2026-09-23). `ricercabile_full = t`; e sulla riga 263 `partita_iva` `ricercabile_full = f`. Il BE proietta già la colonna e la sa cercare |
| `pagamenti.rate` | `id_fiscale_univoco_cf_piva` | La vista `vendite.vw_fatture_scadenze_lista` la espone già; il BE oggi ci cerca, e senza riga a catalogo la ricerca per id fiscale sparirebbe con la conversione. `ricercabile_full = t`. Se stia nel preset di default o no lo decide il team DB: alla ricerca basta che la riga sia attiva |

### 3.2-bis Colonne nuove chieste da Tid (§4.1, 2026-09-23)

| Lista | `campo_sorgente` | Espressione che il BE cerca oggi |
| --- | --- | --- |
| `vendite.promo_articoli` | `articolo_descrizione` | `a.descrizione` dell'articolo |
| `anagrafiche.categorie_clienti_listini` | `categoria_descrizione` | `cc.descrizione` |
| `anagrafiche.categorie_clienti_listini` | `listino_descrizione` | `l.descrizione` |
| `anagrafiche.operatori` | `email` | `au.email` (già proiettata con questo nome) |
| `anagrafiche.operatori` | `soggetto_nome` | `COALESCE(s.nome, au.first_name)` (già proiettata) |
| `anagrafiche.operatori` | `soggetto_ragione_sociale` | `s.ragione_sociale_completa` (il BE la aggiunge alla `SELECT`) |

Tutte con `ricercabile_full = t`. Il BE aggiunge la stessa espressione alla
`SELECT` con quel nome: si cerca su ciò che si mostra. Se il team preferisce i
nomi diversi, li scriva qui: il BE si adegua.

### 3.4 ⛔ Il `codice_interno` non si cerca (Tid, 2026-09-23)

Il `codice_interno` è la chiave immutabile del sistema, non il codice
dell'operatore: la ricerca si fa sul `codice`.

| Lista | Riga | Cambio |
| --- | --- | --- |
| `catalogo.uom_tipi` | 276 `codice_interno` | `ricercabile_full = f` |

⚠️ **Prima il seed, poi il BE**: la dichiarazione di `uom_tipi` nel repository
conosce ancora `codice_interno`. Se il BE la togliesse per primo, il catalogo
accenderebbe una colonna sconosciuta, e il presidio
`test_il_catalogo_non_accende_colonne_sconosciute` diventerebbe rosso.

### 3.5 `vendite.famiglie_documento` — manca il `codice` (Tid, 2026-09-23)

La tabella ha solo il `codice_interno`, e la lista (riga 630) può cercare solo
su quello. **Modifica di modello, non una riga di seed**:

1. colonna `codice` su `vendite.famiglie_documento`, con la forma delle altre
   tabelle a doppio codice: mutabile, `UNIQUE`, valorizzata dal seed
   (all'inizio uguale al `codice_interno`);
2. colonna `codice` nel catalogo della lista, con `ricercabile_full = t`, e
   `ricercabile_full = f` sulla riga 630 `codice_interno`.

Il BE poi aggiunge `codice` alla dichiarazione di `famiglie_repository` e toglie
`codice_interno`, **dopo** il seed.

### 3.3 Pulizia facoltativa

`anagrafiche.fornitori`, righe 28 `codice_fiscale` e 29 `partita_iva`: sono
`attivo = f` ma `ricercabile_full = t`. Dopo la decisione di Tid (id fiscale
univoco) il flag non dice più niente di vero: `ricercabile_full = f`.

## 4. Due domande per Tid (non bloccano §3)

1. ✅ **Decise da Tid il 2026-09-23**: la descrizione articolo e le due
   descrizioni della matrice si accendono (§3.2-bis). Il `codice_interno` dei
   template **non** si cerca (§3.4, regola generale). **Operatori**: email,
   nome e ragione sociale si aggiungono (§3.2-bis).

   La domanda com'era posta: **colonne cercate che il catalogo non ha.** Il codice cerca anche su
   espressioni che non sono colonne della lista:

   | Lista | Cercato ma senza colonna |
   | --- | --- |
   | `vendite.promo_articoli` | descrizione dell'articolo |
   | `documenti.template_documenti`, `documenti.template_asset` | `codice_interno` |
   | `anagrafiche.operatori` | `email`, `nome`, ragione sociale del soggetto |
   | `anagrafiche.categorie_clienti_listini` | descrizione della categoria e del listino |

   Per ciascuna: **una riga nuova a catalogo** (anche fuori dal preset di
   default) oppure **la ricerca ci rinuncia**. La regola del brief BE è «si
   cerca su ciò che si mostra»: senza una colonna la ricerca non ha un
   contratto.
2. ✅ **Deciso da Tid il 2026-09-23: la casella si mostra solo se il
   catalogo accende almeno una colonna.** È lavoro FE, nel brief BE.

   La domanda com'era posta: **il punto cieco del presidio.** Il test BE parte dalle liste che accendono
   colonne: una lista che cerca senza dichiararlo gli è invisibile. La chiusura
   di modello proposta è che il frontend mostri la casella di ricerca **solo
   se** il catalogo accende almeno una colonna per quella lista. Così casella e
   catalogo non possono più divergere. È lavoro FE, e usa una lettura che il
   resolver di configurazione dovrebbe già poter dare.

## 5. Presidi

> ⚠️ **Superata in parte il 2026-09-24**: §3.5 è diventato una modifica di
> modello, e ha il suo pgTAP (`test-famiglie-documento-codice-v1`, §6.5). Per le
> righe di seed vale ancora quanto sotto.

Nessun pgTAP nuovo: sono righe di seed. Dopo il merge, il BE converte le
liste, e il presidio `test_ricerca_full_seed` le troverà scoperte finché non
lo fa. È il segnale voluto.

## 6. Fatto il 2026-09-24 — cosa, dove, e cosa resta al BE

✅ **Applicato il 2026-09-24** da Tid (`-03…-07` alle 18:00, poi `-08`); la
prova pre-apply era stata fatta sullo scratch `zeroerp_ci`, da owner, in
transazioni annullate (§6.5).

### 6.1 Seed del catalogo liste

| Cosa | Dove |
| --- | --- |
| §3.1 — 33 righe `ricercabile_full` da `f` a `t` (id 3, 4, 17, 298-300, 306-307, 313-314, 317, 321-322, 330-331, 337-338, 346-347, 349, 352-353, 359-360, 369, 373, 401-402, 443, 445-446, 476-477) | `80_data/sql/ui/lista_colonna.csv` |
| §3.2 — righe nuove **930** `anagrafiche.emittenti_fiscali.id_fiscale` e **931** `pagamenti.rate.id_fiscale` (`campo_sorgente` `id_fiscale_univoco_cf_piva`); riga 263 `partita_iva` spenta | idem |
| §3.2-bis — righe nuove **932** `promo_articoli.articolo_descrizione`, **933** / **934** `categorie_clienti_listini.categoria_descrizione` / `listino_descrizione`, **935** / **936** / **937** `operatori.email` / `soggetto_nome` / `soggetto_ragione_sociale` | idem |
| §3.3 — righe 28 e 29 dei fornitori spente | idem |
| §3.4 — riga 276 `uom_tipi.codice_interno` spenta | idem |
| §3.5 — riga nuova **938** `famiglie_documento.codice`; riga 630 `codice_interno` spenta, etichetta «Codice interno» | idem |
| le nove colonne nuove nei preset di default delle loro liste; 630 nascosta nel preset delle famiglie | `80_data/sql/ui/lista_preset_colonna.csv` |

**Scelte del team DB** (il brief le lasciava a noi):

- **nei preset di default**, così nessuna lista nasce col banner «colonne
  nuove» acceso. **Visibili**: descrizione articolo delle promo, email degli
  operatori, codice delle famiglie. **Nascoste**: le altre sei. La ricerca non
  guarda la visibilità: basta che la riga sia attiva. Sulle famiglie il
  `codice` prende il posto del `codice_interno` a video (§6c delle linee guida);
- ⛔ **`ordinabile = f` e `filtrabile = f`** su tutte le righe nuove: `ordinabile
  = t` pretende la colonna nella whitelist di ordinamento del repository
  (`test_liste_configurabili_seed`, test 1), e l'ordinamento è un cantiere a
  parte (brief BE §10). Il BE le accende quando la whitelist le conosce;
- **nessuna è `sensibile`**: anche l'email degli operatori resta non sensibile,
  come la `username` accanto. Se va protetta è una decisione a sé, e
  `sensibile = t` pretende una riga in `ui.lista_colonna_permesso` (test 7 dello
  stesso file);
- **etichette**: `soggetto_nome` si chiama «Nome proprio», perché la colonna
  «Nome» (337, `soggetto_cognome`) a video mostra già cognome e nome insieme.

### 6.2 Chiavi i18n — dalla sessione DB, su decisione di Tid

`check_i18n_keys.py` (hook pre-commit sui CSV di `80_data`) blocca il commit se
un'intestazione di colonna non ha la chiave in `it.json`/`en.json`. Tid ha
deciso che le chiavi le aggiunga la sessione DB, nello stesso commit del seed:

| Chiave | it | en |
| --- | --- | --- |
| `vendite.promo_articoli.col_articolo_descrizione` | Descrizione articolo | Article description |
| `amministrazione.matrice_categorie_listini.col_categoria_descrizione` | Descrizione categoria | Category description |
| `amministrazione.matrice_categorie_listini.col_listino_descrizione` | Descrizione listino | Price list description |
| `amministrazione.col_soggetto_nome` | Nome proprio | First name |
| `vendite.famiglie_documento.col_codice` | Codice | Code |
| `vendite.famiglie_documento.col_codice_interno` (valore **cambiato**) | Codice interno | Internal code |

Le altre righe nuove riusano chiavi esistenti (`common.id_fiscale`,
`common.email`, `common.ragione_sociale`). ⚠️ `col_codice_interno` la legge
anche `FamigliaDocumentoDrawer.vue` come etichetta del campo `codice_interno`:
lì «Codice interno» è più corretto di prima, non un effetto collaterale.
Nessun file `.vue` o `.js` è stato toccato.

### 6.3 §3.5 — il `codice` di `vendite.famiglie_documento`

| changeSet | Cosa |
| --- | --- |
| `00_schema/vendite/20260924-03` | colonna `codice varchar(32)` nuda, col commento |
| `20_code/vendite/20260924-04` | `vendite.trgfn_famiglie_documento_default_codice` + `trg_famiglie_documento_a10_default_codice_ins`: alla nascita, codice assente o vuoto vale il `codice_interno` |
| `00_schema/vendite/20260924-05` | backfill del pregresso (`codice = codice_interno`) |
| `00_schema/vendite/20260924-06` | `NOT NULL`, `uq_famiglie_documento_codice`, `chk_famiglie_documento_codice_nonvuoto` |
| `20_code/vendite/20260924-07` | `vendite.vw_famiglie_documento_lista` porta `codice` (in coda, `security_invoker` ripetuto) |
| mirror `80_data/20260830-14` + `famiglie_documento.csv` | colonna `codice` in coda al CSV principale (= `codice_interno` sulle sei famiglie) e nell'elenco del mirror (`runOnChange` + `ANY`: si ritocca, una tabella un CSV) |

⭐ **Perché il trigger alla nascita.** Le famiglie nascono anche dalla madre
`vendite.fn_crea_famiglia_documento` e dal CRUD del backend, che il codice non
lo passano: col default a DB il `NOT NULL` regge **senza cambiare la firma
della madre**, e il BE non deve cambiare niente per continuare a creare
famiglie. Solo in INSERT: in UPDATE un codice vuoto è rifiutato (CHECK, NOT
NULL), non riparato.

⚠️ Il mirror riscrive il `codice` delle sei famiglie seminate a ogni migrate,
come la `descrizione`: su quelle righe il valore lo decide il CSV.
`varchar(32)` come i `codice` di `config.*` (il `codice_interno` è 16).

Doc: righe di revisione datate nei `manual/` di `famiglie_documento` e
`vw_famiglie_documento_lista`.

### 6.4 Codice errore per il brief BE §12

`E_UI_CHIAMATA_NON_VALIDA`, classe **`TECNICO`**, id messaggio **1121**, in
`80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv`. Frase **chiusa**,
senza `%s`: la solleva il backend, nessuna funzione PL/pgSQL la riempirebbe.
*«Chiamata non valida alla configurazione della lista: il contesto della
richiesta non corrisponde all'utente.»* La nota del codice registra perché non
`E_UI_GENERIC_FAILED` né `E_SCOPE_SENZA_UTENTE`.

### 6.5 Prove fatte (2026-09-24, scratch `zeroerp_ci`, owner, `ROLLBACK`)

- SQL **estratto** dai cinque changeSet: gira intero; dopo il `ROLLBACK` la
  colonna non esiste;
- **upsert completo** dei CSV toccati, emulando i mirror (celle vuote: `''` sulle
  colonne STRING e NULL sulle numeriche con `nullValue: ""`; token `NULL` dove
  `nullValue: "NULL"`): nessuna riga rifiutata. Cambiano **esattamente** 47
  righe di `lista_colonna` (38 flag + 9 nuove), 10 di `lista_preset_colonna`,
  0 famiglie (lo scratch ha già i loro valori), 1 codice e 1 messaggio. La riga
  938 passa il trigger che valida il `campo_sorgente` contro la vista, perché
  `20_code` gira prima di `80_data`;
- pgTAP **nuovo** `db/pgtap/vendite/test-famiglie-documento-codice-v1.sql`:
  **14/14**, fra cui il percorso della madre (test 7) e il gemello negativo del
  default in UPDATE (test 9);
- pgTAP **esistenti**, con changeSet e seed in testa, stesso esito di prima:
  `test-famiglie-documento-crud-v1` 28/28, `test-famiglie-documento-guard-riferimenti`
  9/9, `test-liste-preset-default-v1` 5/5, `test-fn-lista-colonne-ricerca-full-v1`
  20/20, `test-fn-resolve-lista-config-contatore-colonne-nuove-v1` 5/5,
  `test-fn-resolve-lista-config` 13/13 (⚠️ solo col resync `runAlways`
  `90_end/20260602-17` incluso nella prova: senza, la sequenza di
  `lista_colonna` resta sotto gli id espliciti. Nel migrate vero gira sempre);
- `plpgsql_check` sulla funzione nuova: zero segnalazioni;
- cancelli statici: letterali SQL, `runOnChange`, preCondition/seed, preambolo
  pgTAP, `check_i18n_keys` — tutti verdi.
- ⚠️ Effetto della prova, non transazionale: `ui.lista_colonna_id_seq` dello
  scratch è passata da 934 a 938. Innocuo (sta sopra il massimo, e il resync la
  riallinea).

✅ **Applicato e verde col runner** (Tid, 2026-09-24 sera). ⏳ Resta il commit.

### 6.6 Cosa succede al BE dopo l'apply — il rosso voluto

I test BE non girano su questa macchina (manca l'ambiente del backend): quello
che segue è **atteso**, non misurato.

- `test_ricerca_full_seed`, «ogni lista ricercabile è registrata o in debito»:
  **rosso** sulle 12 liste di §7-bis del brief BE, finché il BE non le converte
  (è il segnale che §5 chiedeva);
- «la mappa copre il seed» e, sul DB vero, `test_il_catalogo_non_accende_colonne_sconosciute`:
  **rosso su `vendite.famiglie_documento`** finché `famiglie_repository` non
  dichiara `codice`. Il repository deve anche **proiettarlo** (la vista lo porta
  già);
- `anagrafiche.operatori`: la ricerca su `soggetto_ragione_sociale` vuole la
  colonna nella `SELECT` (brief §3.2-bis);
- `anagrafiche.emittenti_fiscali`: `partita_iva` spenta, `id_fiscale` accesa —
  la dichiarazione la conosce già; il BE toglie `partita_iva` dalla mappa quando
  vuole (una colonna in più nella mappa non è un errore);
- `catalogo.uom_tipi`: `codice_interno` spento, il BE lo toglie dalla
  dichiarazione;
- `E_UI_CHIAMATA_NON_VALIDA`: rigenerare le policy (col DB allineato) e il
  ripiego in `error_messages_fallback.py`, come da brief BE §12.

## 7. Il rosso del presidio C2 del 2026-09-24 — non nostro, chiuso qui (Tid: «ok procedi»)

**Il sintomo.** Dopo i changeSet del cantiere prezzi (`20260924-33…-35`,
brief-db-preventivi-congelamento-pricing §10), `dbops/test-punti-canale-campo-v1`
test 2 («nessun ramo cieco») era rosso su `vendite.fn_crea_revisione_offerta` e
`vendite.fn_crea_revisione_preventivo`. Niente a che vedere con §6: nessuno dei
nostri file chiama l'helper del primo motivo.

**La causa: il presidio, non le madri.** Le due madri sollevano il primo motivo
di `script.fn_check_prezzi_in_attesa`, che **filtra** i motivi di
`fn_check_prezzi_autorizzati` (`WHERE motivo ->> 'codice' = 'E_DOC_PREZZO_PENDENTE'`)
invece di ricopiarne il predicato — la forma giusta. `dbops.vw_funzioni_check_codici`
risaliva **un solo livello**, e quella check di motivi suoi non ne ha: legame
con codice NULL, cioè ramo cieco.

**La correzione — `20_code/dbops/20260924-08-update-vw-funzioni-check-codici-delega`.**
La risalita segue la **delega** fra check, a qualunque profondità: una check che
**restituisce** i motivi di un'altra (`v_motivi || …`, `v_m := …`, `jsonb_agg`
sugli elementi) ne eredita i codici, ristretti ai letterali del filtro scritto
nell'istruzione della delega (`->> 'codice' = / IN (…)`); anche
`check_emette_valori` si propaga. Colonne invariate: le due viste lettrici non
cambiano. Tre scelte scartate, con Tid: riscrivere `fn_check_prezzi_in_attesa`
con un motivo suo (ricopierebbe il predicato), dichiarare un'eccezione nel test
(silenzierebbe il punto cieco per la prossima check che delega).

⛔ **Un vicolo cieco, provato e corretto prima dell'apply.** La prima stesura
trattava **ogni** chiamata fra check come una delega. Il rubinetto
(`script/test-rubinetto-primo-motivo-v1` t.2) è diventato rosso: due punti
«a mano» di `fn_check_preventivo_annullabile` entravano nel perimetro dei
`valori`, perché quella check chiama `fn_check_sorgente_chiudibile` — ma per
**contarne** i motivi (`SELECT count(*) …`), ed emette un motivo suo. Contare
non è delegare: la regola ora guarda la **forma** della chiamata.

**Prove (scratch `zeroerp_ci`, owner, `ROLLBACK`).**
- Prima/dopo sulla vista: **zero legami persi**, zero doppioni per (funzione,
  check, codice), 30 righe con `check_emette_valori` da falso a vero (tutte
  deleghe vere: DDT → prezzi autorizzati, documento interno → riga di
  magazzino…), zero canali cambiati in `vw_punti_canale_campo`. Spariscono solo
  i due rami ciechi, che prendono `E_DOC_PREZZO_PENDENTE`.
- Deleghe riconosciute: `fn_check_ddt_emittibile`, `fn_check_documento_interno_registrabile`,
  `fn_check_fattura_eliminabile_da_lotto`, `fn_check_lotto_annullabile`,
  `fn_check_lotto_riportabile_a_draft`, `fn_check_ordine_annullabile`,
  `fn_check_preventivo_emettibile`, `fn_check_prezzi_in_attesa` (fotografia del
  24-09). Consumi, correttamente esclusi: `fn_check_preventivo_annullabile`,
  `fn_check_chiusura_pratica`, `fn_check_pratica_chiudibile`, `fn_check_user_can_create_ba`.
- `test-punti-canale-campo-v1` **16/16** (due casi COSTRUITI nuovi: 15 la delega
  filtrata e accodata, 16 il consumo; senza il changeSet il 15 è rosso),
  `test-rubinetto-primo-motivo-v1` 7/7, `test-catalogo-messaggi-errore-completo`
  7/7. Cancelli statici verdi.

Doc: revisione datata nel `manual/` di `vw_funzioni_check_codici`.
✅ Applicato il 2026-09-24 sera, presidio C2 e rubinetto verdi col runner.

### 7.1 Secondo rosso dello stesso cantiere prezzi — `test-fn-crea-revisione-preventivo-riga-completa-v1`

Il file moriva **nella fixture** (8 asserzioni, 2 eseguite) con
`E_DOC_PREZZO_PENDENTE`: costruiva una riga `PENDING` e poi creava la revisione,
che da `20260924-34` è rifiutata **per decisione di modello**. I test 5 e 8
pinnavano la riga in attesa ricopiata sulla rev N+1: un comportamento ritirato.

Correzione (solo il pgTAP, nessun changeSet): la seconda riga marcata è ora
**REJECTED** — il caso che il modello ammette e che si ricopia 1:1. Il test 5
pretende il REJECTED identico sulla rev N+1; il test 8, invece del guard sulla
riga in attesa, pretende che la marca copiata faccia il suo mestiere:
`script.fn_check_prezzi_autorizzati` sulla rev N+1 dà `E_DOC_PREZZO_RIFIUTATO`
(la rev col prezzo rifiutato non si emette). Il rifiuto della revisione col
prezzo in attesa non si ricopia qui: la sua sede è
`test-fn-check-prezzi-autorizzati-v1`, test 40 e 44. Scratch: **8/8**; verde
anche col runner di Tid (2026-09-24 sera).

Ricontrollati gli altri pgTAP che creano revisioni: `test-date-consegna-ordine-v1`
13/13, `test-trgfn-default-emittente-fiscale-v1` 18/18. Gli altri quattro
(`test_fn_crea_revisione_offerta`, `test_offerte_commerciali_end_to_end`,
`test-fn-crea-revisione-preventivo`, `test-vw-dash-competenza-gruppi-riferimento-sorgente-v1`)
sono `ERRORE_FIXTURE` già in entrambe le baseline, per NOT NULL su
`billing_account_id`/`istanza_utility_id`: debito vecchio, non legato al
prezzo in attesa.
