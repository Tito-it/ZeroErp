# Brief DB — Componenti di un kit in fattura: tre modi di esporli, non due

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-01. **A chi:** team DB (`dev/db-tid`);
> poi BE/FE (§5).
> **Origine:** collaudo della fattura con un kit (versione 4 del template, forma 2 del contesto,
> `brief-db-documenti-versione-contesto-template` §13), 2026-10-01.
> **Stato:** ✅ **E-1, E-2, E-3 decise da Tid il 2026-10-01** (§6). ✅ **Lato DB CHIUSO il
> 2026-10-02**: changeSet `20261001-41 → -57` applicati su dbdev da Tid (dopo la correzione di
> `-42`, §8.4), pgTAP **senza regressioni**, confermato due volte (§8.3); script una tantum del
> meta pronto (§9.3). ➡️ **La palla passa al BE/FE** (decisione di Tid, 2026-10-02): richieste in §5
> — **R-FE-1 blocca la CI**, **R-BE-1 blocca la generazione di una fattura con un kit** su dbdev.
> Al merge di R-BE-2 si lancia lo script di §9.3. Restano da confermare §9.1 e §9.2 (già applicati
> così a DB: una conferma, non lavoro).
> ✅ **Giro BE/FE del 2026-10-02 (§10)**: R-BE-1/2/3/4/5/7 fatti, R-FE-1/4/5 chiusi.
> ✅ **R-DB-K1 scritto e applicato da Tid (2026-10-02, §10.5)**: si sbloccano R-BE-6 e con lui
> R-FE-2/3 — la palla è al BE. Passi di Tid in §10.3.
>
> **In una riga:** oggi un componente di kit in fattura o non compare, o compare come riga
> descrittiva **senza prezzo**. Manca il terzo modo, quello che si intende di solito con «esposto in
> fattura»: il componente come **articolo vero**, con prezzo e importo suoi, fuori dal totale del kit.

---

## 1. Il problema

`catalogo.articoli_componenti.esposto_in_fattura` è un **booleano**, e la vista
`vendite.vw_fattura_righe_esposte` lo legge così:

| Flag | Cosa produce |
| --- | --- |
| `false` | il componente non compare; il suo valore sta nel totale del kit |
| `true` | il componente compare sotto il kit come riga **descrittiva**, senza importo; il suo valore sta comunque nel totale del kit |

Chi compila la distinta e mette «esposto in fattura = sì» si aspetta invece di **vedere il prezzo**
del componente in fattura, separato dal kit. Il modello non lo permette: con due valori ce n'è uno
che si capisce al contrario.

## 2. Cosa c'è oggi — letto dalla struttura (2026-10-01)

Il flag percorre tutta la catena, ed è una **proprietà del catalogo**, non del documento:

| Passo | Dove | Come |
| --- | --- | --- |
| catalogo | `catalogo.articoli_componenti.esposto_in_fattura` | `boolean NOT NULL DEFAULT false` |
| righe dei documenti | preventivi, ordini, contratti, DDT (`*_righe_componenti`) | **nessuna copia**: il BE lo legge col JOIN sul catalogo (`_componenti_repo_mixin.list_componenti_riga`, «BoM immutabile per design»); le funzioni `fn_*_riga_componenti_preview` lo proiettano |
| commessa | `attivita_fatturabili.meta` | chiave `esposto_in_fattura` (contratto `apps/vendite/services/_kit_meta.py`), scritta al push da `BoMComponentExpander` |
| fattura | `vendite.fatture_righe.kit_esposto_in_fattura` | `boolean`, con `kit_key` |
| rappresentazione | `vendite.vw_fattura_righe_esposte` | padre = **somma di tutti** i componenti; esposti = righe descrittive, importo `NULL` |
| lista a video | `vendite.vw_fattura_righe_lista` | il jsonb `componenti` porta riga, articolo, descrizione, quantità, UoM: **nessun prezzo** |

⭐ **La pipeline è già pronta**: ogni componente arriva in commessa e in `fatture_righe` come riga a sé,
**col suo prezzo**. L'aggregazione la fa solo la vista di rappresentazione. Il terzo modo non chiede
dati nuovi, chiede di leggere quelli che ci sono.

⚠️ **Commento stantio** da correggere nello stesso giro: `ordini_righe_componenti` e
`preventivi_righe_componenti` (e simili) dicono «una riga per ogni componente esposto_in_fattura =
TRUE». Dal modello unificato del 2026-05-13 ci sono **tutti** i componenti attivi.

## 3. Il modello deciso

Un vocabolario a tre valori al posto del booleano (E-1):

| Valore | In fattura | Nel totale del kit |
| --- | --- | --- |
| `NASCOSTO` | non compare | **sì** |
| `DESCRITTIVO` | riga sotto il kit, senza prezzo né importo (com'è oggi il `true`) | **sì** |
| `VALORIZZATO` | riga sotto il kit **con quantità, prezzo e importo suoi** | **no**: il suo importo è sulla sua riga |

* ⭐ **Un componente resta sempre legato al suo kit** (Tid, 2026-10-01). Anche `VALORIZZATO` non
  diventa mai una riga sciolta, come se fosse stato venduto da solo: sta **sotto** la riga del kit,
  rientrato, in ogni caso — non solo quando il kit resta senza importo. Nella vista è il livello 1
  del suo kit (stessa `kit_key`), nella lista a video sta dentro `componenti` del padre, in stampa
  sotto il padre:

  ```
  Postazione ufficio ............ 100 €   ← il resto: la lampada (nascosta)
    Scrivania ................... 600 €   ← valorizzato, legato al kit
    Sedia ....................... 300 €   ← valorizzato, legato al kit
                        totale  1.000 €
  ```
* **La riga del kit** porta la somma dei componenti `NASCOSTO` e `DESCRITTIVO`.
* **Il kit senza resto** (E-2, strada **a**): se tutti i componenti sono `VALORIZZATO` — o
  `VALORIZZATO` e `DESCRITTIVO` — la riga del kit **resta come intestazione senza importo** (`NULL`,
  non zero: zero direbbe «omaggio»), con i componenti sotto. Il cliente ha comprato il kit, e la
  fattura continua a dirlo.
  ⚠️ **Corretto in scrittura (2026-10-02), da confermare — §9.1**: «o `VALORIZZATO` e
  `DESCRITTIVO`» contraddice la riga sopra e l'invariante del totale. Un `DESCRITTIVO` non ha
  importo suo, quindi il suo valore **deve** stare nel kit; se il kit restasse senza importo, quel
  valore sparirebbe dal documento. La vista fa: **senza resto = solo valorizzati**; con valorizzati e
  descrittivi il kit porta la somma dei descrittivi.
* **Quantità del kit**: la stessa di oggi (media delle quantità dei componenti, omogenee per il guard
  R10), calcolata su **tutti** i componenti, anche i valorizzati: un kit senza resto ha comunque la
  sua quantità.
* ⭐ **Il totale del documento non cambia mai** al variare dell'esposizione: è la proprietà che la
  vista garantisce oggi, e resta.
* La rappresentazione resta **una**: PDF, XML SDI e portale leggono la stessa vista (regola R17).
  Per l'SDI le righe `VALORIZZATO` sono linee di dettaglio con il loro prezzo; la riga del kit senza
  resto è una linea descrittiva. ⚠️ Nel tracciato XML le linee sono **piatte**, quindi il legame col
  kit va dichiarato con una convenzione, per esempio il riferimento alla linea del kit in
  `AltriDatiGestionali` o nella descrizione. La sceglie il cantiere SDI (sospeso per decisione), ma la
  vista deve già dargli il dato: per ogni componente il `riga_nr` del suo kit.

## 4. Proposta (team DB)

1. **Vocabolario**: `config.esposizioni_componente` (codice, descrizione, `etichetta_key`), CSV in
   `80_data` con i tre valori.
2. **Catalogo**: `articoli_componenti.esposizione_in_fattura` (FK sul vocabolario, NOT NULL, default
   `NASCOSTO`) al posto di `esposto_in_fattura`; backfill `false → NASCOSTO`, `true → DESCRITTIVO`
   (è quello che il `true` produceva). Il booleano si ritira **nello stesso giro**: due colonne per la
   stessa scelta divergono.
3. **Fattura**: `fatture_righe.kit_esposizione` al posto di `kit_esposto_in_fattura`, stesso
   backfill, stesso ritiro.
4. **Viste**: `vw_fattura_righe_esposte` con le regole di §3; `vw_fattura_righe_lista` che porta nel
   jsonb `componenti` anche `esposizione`, `prezzo_unitario` e `importo_riga` (`NULL` per i non
   valorizzati). ⚠️ Da quel momento la colonna `importo_riga` della lista **non somma più** al
   totale del documento: i valorizzati hanno l'importo dentro `componenti`. È voluto, va scritto nel
   `COMMENT`.
5. **Funzioni di anteprima** (`fn_*_riga_componenti_preview`, `fn_contratto_righe_preview`,
   `fn_espandi_listino_versione`, `fn_offerta_eccezione_componenti_*`, `fn_accredita_riga_reso`) e
   trigger che nominano il flag (`trgfn_articoli_componenti_block_modifica_struttura`,
   `trgfn_componenti_guard_coerenza_bom`): la colonna nuova al posto della vecchia. Il censimento
   completo è quello di §2 più un `grep` sul corpo vivo.
6. **Commenti stantii** di §2 corretti.
7. **pgTAP costruendo i casi**: un kit con un componente per modo, un kit senza resto (tutti
   valorizzati), un kit valorizzato + descrittivo, e il totale del documento uguale nei tre casi.
   Nessun confronto con la popolazione.

## 5. Ricadute fuori dal DB — richieste a BE/FE (il DB è scritto, §8)

* **BE**: il contratto del meta di commessa (`_kit_meta.META_KEY_ESPOSTO_IN_FATTURA` →
  `esposizione`) e chi lo scrive (`BoMComponentExpander`) e lo legge (`FattureRigheService`); i
  `TypedDict` e i repository dei componenti; il builder fattura alla **forma 3** (componenti con
  prezzo e importo), per il patto versione/forma.
* **Template**: versione 5 della fattura, che stampa prezzo e importo dei valorizzati e il kit senza
  resto senza importo. Dichiara la forma 3; si pubblica quando il builder la produce.
  ⚠️ **Numerazione da verificare al momento di scrivere** (sessione BE, 2026-10-01): anche R-3 di
  `brief-db-esigibilita-iva-per-cassa-emittente.md` (§11) porta la fattura a «forma 3 + v5» (le
  annotazioni). Chi arriva primo prende 3/v5, l'altro passa a 4/v6 e parte dal template dell'altro.
* **FE**: nella distinta dell'articolo il toggle «esposto in fattura» diventa una scelta fra tre
  (etichette dal vocabolario); il pannello componenti mostra l'esposizione per esteso; nel drawer
  fattura l'espansione del kit mostra prezzo e importo dei valorizzati.
⚠️ **Il DB ritira il booleano nello stesso giro** (§4.2), quindi dal momento dell'apply i punti che
lo scrivono o lo leggono per nome **falliscono**, non degradano: è la forma voluta (un booleano
scritto come testo non è un modo), ma vuol dire che DB, BE e FE vanno **mergiati insieme**.

### FE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-FE-1** ⛔ | le tre chiavi `config.esposizioni_componente.nascosto` / `.descrittivo` / `.valorizzato` in `it.json` **e** `en.json`. **Blocca la CI**: `scripts/check_i18n_keys.py` legge l'`etichetta_key` del CSV nuovo e oggi dà «3 chiavi emesse dal DB e assenti dai locales» | `frontend/src/locales/` |
| R-FE-2 | il toggle «esposto in fattura» diventa una scelta fra tre, con le etichette dal vocabolario (lookup su `config.esposizioni_componente`, `ordine`); il default dal parametro **rinominato** `CATALOGO_BOM_DEFAULT_ESPOSIZIONE_IN_FATTURA` (valore: un codice, non un booleano) | `ArticoloBomDrawer.vue` (righe 101, 216) |
| R-FE-3 | il pannello e il dialog dei componenti mostrano il modo per esteso: il campo è `esposizione_in_fattura` (codice) nelle anteprime e nei jsonb `componenti` | `ComponentiPanel.vue`, `ComponentiDialog.vue` |
| R-FE-4 | nel drawer fattura l'espansione del kit mostra prezzo, sconto e importo dei valorizzati (nuove chiavi del jsonb `componenti` di `vw_fattura_righe_lista`); un padre con `importo_riga` NULL è un kit senza resto, non un errore | drawer fattura |
| R-FE-5 | colonna «In fattura» della lista 101 (distinta): da `yesno` a testo, `campo_sorgente = esposizione_in_fattura_codice` (CSV aggiornato qui); `codice` della colonna cambiato in `esposizione_in_fattura` — un preset utente che la nominava col codice vecchio la perde | lista `catalogo.articolo_componenti` |

### BE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-1** ⛔ | la riga di fattura scrive `kit_esposizione` (il codice) al posto di `kit_esposto_in_fattura`: senza, la generazione di una fattura con un kit fallisce sulla colonna che non c'è | `pipeline_repository.py` 3496-3520 |
| R-BE-2 | il contratto del meta: `META_KEY_ESPOSTO_IN_FATTURA` → `esposizione`, valore il codice; chi lo scrive (`BoMComponentExpander`, che oggi fa `bool(componente.get("esposto_in_fattura"))`) e chi lo legge (`FattureRigheService`, `as_bool(...)`) | `_kit_meta.py:32`, `commesse_source_handlers.py` 238-289, `fatture_righe_service.py` 42, 363, 542, 623 |
| R-BE-3 | ⚠️ `fatture_righe_service.py:704` dichiara un raggruppamento «che deve essere lo STESSO di `vw_fattura_righe_esposte`»: è una seconda sede della regola. Da rileggere: se il raggruppamento dipende dall'esposizione, va riallineato ai tre modi (o meglio ritirato a favore della vista) | `fatture_righe_service.py` |
| R-BE-4 | la distinta: scrittura e lettura di `esposizione_in_fattura` (codice validato dalla FK: un valore fuori catalogo torna `23503`) al posto di `esposto_in_fattura`; la proiezione legge `vw_articoli_componenti_dettaglio`, che porta anche `_codice` ed `_etichetta_key` | `catalogo_bom_repository.py` 42, 78; `catalogo_service.py:1001` |
| R-BE-5 | le anteprime dei componenti restituiscono `esposizione_in_fattura` (non più `esposto_in_fattura`), e il JOIN sul catalogo legge la colonna nuova | `_componenti_repo_mixin.py` 113, 157; `preventivi_` / `ordini_` / `ddt_` / `contratti_` / `offerte_repository.py`; `listini_repository.py:1308`; `types.py` 835, 852, 883, 1047 |
| R-BE-6 | il lookup del vocabolario per il FE (R-FE-2): `config.esposizioni_componente` nel lookup generico/specializzato con `etichetta_key` (stampo `config.registri_giornale`) | lookup BE |
| R-BE-7 | il builder fattura alla **forma 3** (componenti con prezzo e importo), per il patto versione/forma; documentazione API (`api_catalogo`, `api_listini`, `api_preventivi`, `api_contratti`, `api_ordini`, `pricing_service`) e lo smoke `smoke-fatturazione-aggregazione-righe.py` | builder, doc, smoke |

### Template

* **Versione 5 della fattura**, che stampa prezzo e importo dei valorizzati e il kit senza resto
  senza importo. Dichiara la forma 3; si pubblica quando il builder la produce.

## 6. Decisioni di Tid (2026-10-01)

| # | Domanda | Esito |
| --- | --- | --- |
| E-1 | Booleano o tre valori? | ✅ **Tre valori**: `NASCOSTO` / `DESCRITTIVO` / `VALORIZZATO` (§3) |
| E-2 | Kit senza resto (tutto valorizzato) | ✅ **Strada a**: la riga del kit resta come intestazione senza importo |
| E-3 | Fatture già emesse | ✅ **Nessun riguardo**: su dbdev sono di test. La vista vale per tutte |

## 7. Fuori perimetro, dichiarato

* Un'esposizione decisa **per documento** (sovrascrivere il catalogo su una riga d'ordine): oggi è
  proprietà della distinta, e resta così finché qualcuno non porta un caso.
* La stampa di preventivi, ordini e DDT: i loro template mostrano i componenti con un'altra logica,
  da guardare a parte.

## 8. Lato DB — cosa è stato scritto (applicato su dbdev il 2026-10-02)

> ✅ **Apply e pgTAP di Tid, 2026-10-02**: migrazione applicata (al secondo tentativo, dopo la
> correzione di `-42` in §8.4), **nessuna regressione** nella corsa pgTAP. Da qui su dbdev il
> booleano non esiste più: finché R-BE-1 e R-BE-4/5 non arrivano, il BE fallisce dove lo scrive o lo
> legge per nome (generazione fattura con kit, distinta, anteprime componenti). Non ancora fatto:
> §9.3 (meta delle attività già in commessa). §9.4 è chiuso: l'apply ha risvegliato il mirror di
> `parameters.csv` senza errori.

### 8.1 La forma, e perché: conversione sul posto

Le due colonne non nascono accanto al booleano con un backfill: **cambiano tipo e nome sul posto**
(`ALTER COLUMN … TYPE varchar(40) USING CASE …` + `RENAME`). Un'istruzione DDL non fa scattare i
trigger di riga, e qui conta:

* sulla distinta il guard di immutabilità rifiuterebbe l'`UPDATE` di un campo di struttura;
* su `fatture_righe` le righe oltre EMESSA sono intoccabili (D1-bis): un backfill per `UPDATE` si
  fermerebbe sulla prima fattura emessa, e E-3 chiede che la vista valga per tutte;
* non esiste mai un momento con **due** colonne per la stessa scelta.

Il prezzo: `ALTER TYPE` non passa finché una vista legge la colonna, quindi il changeSet di schema
**droppa** le viste dipendenti e quello di codice successivo le **ricrea** (stessa corsa).

### 8.2 I changeSet

| # | Fase | Cosa |
| --- | --- | --- |
| `-41` | `00_schema/config` | `config.esposizioni_componente` (codice_interno, codice, descrizione, etichetta_key, ordine). **Niente `attivo`** (§9.2) |
| `-42` | `00_schema/catalogo` | `articoli_componenti.esposto_in_fattura` → `esposizione_in_fattura` varchar, default `NASCOSTO` (false → NASCOSTO, true → DESCRITTIVO). Droppa `vw_articoli_componenti_dettaglio` |
| `-43` | `20_code/catalogo` | il guard di immutabilità confronta la colonna nuova |
| `-44` | `20_code/catalogo` | `vw_articoli_componenti_dettaglio` ricreata: `esposizione_in_fattura` + `_codice`, `_etichetta_key` in coda |
| `-45` | `00_schema/vendite` | `fatture_righe.kit_esposto_in_fattura` → `kit_esposizione`. Droppa `vw_fattura_righe_lista` e `vw_fattura_righe_esposte`. Il CHECK di coerenza segue la colonna da solo |
| `-46` | `20_code/vendite` | `vw_fattura_righe_esposte` coi tre modi (§3); in coda `esposizione` e `kit_riga_nr` (il riga_nr del kit, per l'SDI) |
| `-47` | `20_code/vendite` | `vw_fattura_righe_lista`: il jsonb `componenti` porta `esposizione`, `prezzo_unitario`, `sconto_percentuale`, `importo_riga`; il `COMMENT` dice che `importo_riga` non somma più al totale |
| `-48 → -52` | `20_code/vendite` | le cinque `fn_*_riga_componenti_preview`: DROP + CREATE (cambia il `RETURNS TABLE`), firma ancorata dall'ultimo YAML, corpo vivo patchato con sostituzioni contate, `EXECUTE` all'app ridichiarato |
| `-53`, `-54` | `20_code/vendite` | `fn_contratto_righe_preview`, `fn_espandi_listino_versione`: chiave jsonb `esposizione_in_fattura` |
| `-55` | `00_schema/vendite` | i quattro `COMMENT` stantii delle `*_righe_componenti` (§2) |
| `-56` | `80_data` | seed del vocabolario (`config/esposizioni_componente.csv`, mirror per `id`) |
| `-57` | `80_data` | FK su `config.esposizioni_componente(codice_interno)` dalle due colonne (dopo il seed: forma di `20261001-17`) |

CSV toccati: `parameters.csv` (riga 26 rinominata `CATALOGO_BOM_DEFAULT_ESPOSIZIONE_IN_FATTURA`,
valore `NASCOSTO`), `parameter_fk_surrogate.csv` (riga 6: il valore si valida sul vocabolario),
`ui/lista_colonna.csv` (riga 1054, R-FE-5), `messaggi_errore.csv` (descrizione di
`E_BOM_MODIFICA_VIETATA`).

### 8.3 pgTAP

* **Nuovo**: `vendite/test-vw-fattura-righe-esposte-tre-modi-v1.sql` (18 test) — costruisce una
  fattura con un kit per modo, uno senza resto, uno valorizzato + descrittivo, uno tutto nascosto;
  verifica il legame componente → kit e il **totale invariato** rileggendo lo stesso documento con
  tutti i componenti NASCOSTO, poi DESCRITTIVO, poi VALORIZZATO. Nessun confronto con la popolazione.
* **Adattati** (colonna, valori, chiave del meta): `catalogo/test-articoli-componenti-immutabilita`,
  `catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1`, `script/test-componenti-helpers-v1`,
  `script/test-fn-check-prezzi-autorizzati-v1`, `vendite/offerte_commerciali/test_offerte_eccezioni_componenti`,
  `vendite/test-accredito-kit-meta-v1` (meta con la chiave nuova `esposizione`, R-BE-2),
  `vendite/test-articolo-regole-fatturazione` (commento), `vendite/test-fatture-righe-importo-e-kit-v1`,
  `vendite/test-fn-resolve-prezzo-composito-v1`, `vendite/test-preventivi-righe-componenti-v1`,
  `vendite/test-vw-fattura-righe-lista-v1`, `vendite/test-vw-righe-dettaglio-sorgente-lista-v1`.
  Dove il test filtrava `esposto_in_fattura = TRUE` sulla popolazione, la sostituzione è
  l'equivalente esatto (`<> 'NASCOSTO'`): quei test restano dipendenti dai dati com'erano, non è
  questo il giro per riscriverli.

### 8.4 Come è stato provato, e cosa la prova NON copre

* **Cancelli statici** verdi: `guardrail_sql_letterali`, `_run_on_change`, `_precondition_seed`,
  `_ddl_su_trigger_automazione`, `_grant_ruolo_batch`, `_pgtap_preambolo`, `_timestamp_senza_fuso`.
  `check_i18n_keys` **rosso** sulle tre chiavi di R-FE-1, e solo su quelle.
* **SQL estratto** (`changes[].sql.sql` dagli YAML, non riscritto) eseguito con `ON_ERROR_STOP` su un
  **cluster PG18 usa-e-getta**, sopra tabelle *stub* con la forma della doc auto-gen e gli oggetti di
  prima presi dai loro YAML (`20260924-01`, `20260928-27`, `-28`, `-43`). Verde in avanti: conversione
  senza far scattare un guard di riga che rifiuta ogni `UPDATE`, CHECK che segue la colonna, viste e
  funzioni ricreate con l'`EXECUTE` all'app, FK che respinge un codice fuori catalogo, e i casi del
  pgTAP nuovo (totale 365 nei tre modi). Verde anche **all'indietro** (i `rollback` estratti, in
  ordine inverso).
* ⛔ **Primo apply di Tid, 2026-10-02: `-42` morto** con «non è possibile cambiare il tipo di una
  colonna usata nella definizione di un trigger». Il guard di immutabilità è `BEFORE DELETE OR
  UPDATE OF <campi di struttura>` (`20260514-15`), e la colonna in `UPDATE OF` è una dipendenza.
  La doc auto-gen stampa l'evento come «UPDATE» senza la lista; lo stub l'aveva ricostruito da
  lì, quindi la prova non poteva vederlo. Corretto: `-42` droppa e ricrea il trigger con la stessa
  lista (colonna nuova), il rollback lo rimette com'era; la prova ora prende il trigger dallo YAML
  vero e verifica `tgattr`. Il changeSet era fallito in transazione: niente da ripulire. Rigenerati
  anche `-48 → -54` con i `%TYPE` mancanti (`obbligatorio` nelle cinque anteprime, l'intero
  `RETURNS TABLE` della DDT e `p_quantita_padre`, `p_tipo_var`/`p_valore_var` di
  `fn_espandi_listino_versione`). Restano espliciti solo i valori calcolati, che non hanno una
  colonna sorgente: `resolver_error_reason`, `p_data_riferimento`, `v_msg`, chiavi, azioni e jsonb.
* ⚠️ **Non copre**: i dati veri, la RLS, `plpgsql_check`, i presidi trasversali, i mirror CSV (il
  seed è stato emulato riga per riga), e il pgTAP vero (`fn_pgtap_*`). **Apply e corsa pgTAP restano
  di Tid.**

## 9. Punti da confermare (Tid)

1. **E-2, la seconda metà** (§3): con valorizzati e descrittivi il kit porta la somma dei
   descrittivi, non resta senza importo — altrimenti il loro valore uscirebbe dal documento. Così è
   scritto in `-46` e pinnato dal test 10. Se invece l'intento era un altro (per esempio «un
   descrittivo accanto a valorizzati diventa valorizzato»), è un cambio della vista e del test.
2. **Il vocabolario senza `attivo`**: i tre valori sono la semantica della vista, non una
   configurazione; con `attivo` la `ci_apply` monterebbe la coppia ATTIVO anche sulla colonna
   *snapshot* della fattura. Un modo si ritira con un cantiere.
3. **Le attività già in commessa col meta vecchio** (`esposto_in_fattura: true|false`): quando il BE
   leggerà la chiave `esposizione` (R-BE-2), quelle righe non la troveranno. Non siamo in produzione:
   la proposta è una correzione **a mano** su dbdev (`meta - 'esposto_in_fattura' ||
   {"esposizione": …}`) al momento del merge, non un changeSet né una lettura delle due chiavi nel BE.
   ✅ **Script pronto (2026-10-02)**: [`allegati/esposizione-kit-meta-attivita-una-tantum.sql`](allegati/esposizione-kit-meta-attivita-una-tantum.sql).
   Si lancia **al merge di R-BE-2**, non prima (il BE di oggi su una riga corretta leggerebbe
   «assente» = false). In sintesi:
   * tocca `commesse_attivita` e `attivita_fatturabili`; **anche le fatturate**, perché l'accredito
     di un reso eredita il `meta` della riga rettificata. Il guard `guard_fatturato` si supera col
     suo bypass di manutenzione (`zeroerp.maintenance_reset_lotto_draft`, `SET LOCAL`);
   * **riga per riga**, con un savepoint ciascuna: i trigger «riferimento attivo» rigiudicano la
     riga a ogni `UPDATE`, quindi un'attività vecchia con un padre spento rifiuta anche l'`UPDATE`
     del solo `meta`. Le rifiutate sono **elencate** col motivo, non saltate in silenzio;
   * `true` → DESCRITTIVO, `false`/assente → NASCOSTO; se `esposizione` c'è già, vince quella;
   * non tocca `fatture_righe.meta`: la fattura legge la colonna `kit_esposizione`. Ne conta le
     righe, solo per informazione;
   * si ferma se il ruolo non è superuser/BYPASSRLS (sotto RLS vedrebbe zero righe);
   * **di default annulla** (`ROLLBACK`): si legge l'esito, poi `-v applica=1` fa il `COMMIT`.
   Provato su cluster usa-e-getta con tabelle stub (guard «fatturato» col bypass vero, un trigger
   che rifiuta una riga, chiave vecchia `true`/`false`/stringa, riga con entrambe le chiavi, ruolo
   filtrato): esiti come attesi, la prova non lascia modifiche. Sui dati veri non è stato lanciato.
4. ✅ **Chiuso dall'apply del 2026-10-02**: il mirror si è risvegliato e ha riscritto tutte le
   righe senza errori, che è esattamente ciò che la verifica doveva provare. Testo originale:
   **Il mirror di `parameters.csv` si risveglia** (riga 26): la verifica di §11.2 delle linee guida
   — upsert di **tutte** le righe del CSV in una transazione annullata — va fatta su dbdev prima
   dell'apply; da qui il DB non era raggiungibile. L'ordine è sicuro: il mirror dei parametri
   (`20250715-01`) gira prima di quello del registro FK surrogata (`20260520-02`), quindi il valore
   `NASCOSTO` non viene validato prima che il vocabolario esista.

Registrati, non aperti:

* **Il padre condivide il `riga_nr` col primo componente esposto** (c'era già coi descrittivi): con i
  valorizzati sono due righe con importo e lo stesso numero. Il PDF non ne soffre (ordinamento +
  livello); per l'SDI la numerazione delle linee la fa il builder, cantiere sospeso. Il legame vero è
  `kit_riga_nr`.
* **Un commento nel corpo di `fn_accredita_riga_reso`** elenca le chiavi del meta kit col nome
  vecchio: diventa stantio quando il BE rinomina la chiave (R-BE-2). Si corregge al prossimo giro
  sulla funzione — ricrearne il corpo per un commento non vale il rischio.

## 10. Giro BE/FE (2026-10-02, `dev/backend-tid`)

> **Chi scrive:** sessione BE/FE, 2026-10-02. **A chi:** Tid (passi di §10.3); team DB (R-DB-K1).

### 10.1 Esito delle richieste

| # | Esito | Dove |
| --- | --- | --- |
| **R-BE-1** | ✅ la riga di fattura scrive `kit_esposizione` (array `varchar[]` nell'`unnest`, parametro `righe_kit_esposizioni`). Provato sul DB vero con lo smoke della fatturazione (kit con un VALORIZZATO e un DESCRITTIVO, in transazione annullata): modi congelati coi codici, vista con padre = descrittivo, valorizzato con importo e `kit_riga_nr` del padre, totale invariato | `pipeline_repository.py`, `fatture_righe_service.py`, `smoke-fatturazione-aggregazione-righe.py` (test 8b, 11 nuovi) |
| **R-BE-2** | ✅ `META_KEY_ESPOSIZIONE = "esposizione"`, valore il codice. Scrittore e lettore passano dallo stesso `kit_meta.esposizione_o_default`: chiave assente o vuota = `NASCOSTO` (il DEFAULT della colonna di distinta, e la stessa lettura dello script §9.3). ⛔ Nessuna lettura della chiave vecchia: un meta non corretto con `esposto_in_fattura: true` finirebbe NASCOSTO — per questo lo script va lanciato **subito** (§10.3). Un valore fuori vocabolario non si giudica in Python: lo ferma la FK su `kit_esposizione` | `_kit_meta.py`, `commesse_source_handlers.py`, `fatture_righe_service.py` |
| **R-BE-3** | ✅ riletto: **la regola resta**. La vista raggruppa il padre per (fattura, kit, IVA, BA) e fa la media della quantità su **tutti** i componenti, valorizzati compresi: l'esposizione cambia l'importo del padre, non la sua quantità. Il guard R10 resta com'è; commento aggiornato, due test nuovi (modi misti con quantità uguali passano; un valorizzato con quantità diversa si ferma) | `fatture_righe_service.py` |
| **R-BE-4** | ✅ distinta: `esposizione_in_fattura` nella whitelist di scrittura, estratto come stringa non nulla; i valori li giudica la FK (`23503` → `400 E_CATALOGO_VALIDATION`, traduttore già esistente). Il booleano vecchio torna `400` come chiave sconosciuta (test). Ordinamento della lista 101 su `esposizione_in_fattura_codice` — erano i due rossi di `test_liste_configurabili_seed` | `catalogo_bom_repository.py`, `catalogo_service.py` |
| **R-BE-5** | ✅ anteprime e componenti di riga leggono `esposizione_in_fattura` (cinque `fn_*_preview`, il JOIN del mixin, il bundle dei listini, i `TypedDict`). Binding provato col **piano** sul DB vero (`EXPLAIN` di ogni query, con un controllo negativo sulla colonna vecchia che deve fallire, e fallisce): sotto RLS le tabelle erano vuote, e uno zero non provava niente | repository vendite, `types.py` |
| **R-BE-6** | ⏳ **bloccato da R-DB-K1** (§10.2). La voce in `_LOOKUP_SPECIALIZZATE` è pronta da scrivere (`extra_col: etichetta_key`, `has_codice_interno: True`, `has_obsoleto: False`, `has_attivo: False`), ma `test_lookup_specializzate` pretende — giustamente — che ogni specializzata stia nella whitelist DB: aggiungerla prima la manderebbe rossa | `dbops_repository.py` |
| **R-BE-7** | ✅ builder fattura alla **forma 3** (`CONTEXT_VERSION = 3`): i componenti portano `esposizione`, `prezzo_unitario`, `sconto_percentuale`, `importo_riga` formattati come una riga, NULL che restano NULL sul descrittivo. **Template v5** scritto: [`template-fattura-v5.html`](template-fattura-v5.html) = v4 + componenti valorizzati con prezzo/sconto/IVA del padre/importo, padre senza resto con celle vuote (non «-»). Reso col motore vero (StrictUndefined + autoescape) su una fattura con kit costruita sul DB in transazione annullata, nei due casi (con resto, senza resto). Doc API allineate (`api_catalogo`, `api_contratti`, `api_listini`, `api_ordini`, `api_preventivi`; in `pricing_service` la sezione di un metodo ritirato a maggio è stata sostituita da una riga che lo dice) e lo smoke bash dei componenti | builder, test, doc, smoke |
| **R-FE-1** | ✅ già chiuso prima di questo giro (le tre chiavi sono entrate con `c6793e4db`); `check_i18n_keys` pulito | — |
| **R-FE-2** | ⏳ **bloccato** (R-DB-K1 → R-BE-6): la scelta fra tre vuole le etichette dal vocabolario, cioè `useLookupEtichettato({ rel: 'config.esposizioni_componente', campoCodice: 'codice_interno' })`. ⚠️ **Fino ad allora il drawer della distinta non salva una riga nuova**: manda ancora il booleano, e il BE lo rifiuta con un 400 che lo nomina. Non è una regressione di questo giro: dall'apply del DB la colonna non c'era più | `ArticoloBomDrawer.vue` |
| **R-FE-3** | ⏳ **bloccato** come R-FE-2: il modo per esteso è `etichetta(codice)` dello stesso lookup. ⚠️ Fino ad allora la colonna «In fattura» di pannello e dialog dei componenti legge un campo che non arriva più, e mostra «No» per tutti | `ComponentiPanel.vue`, `ComponentiDialog.vue` |
| **R-FE-4** | ✅ nel drawer fattura l'espansione del kit mostra `× prezzo − sconto% = importo` sui valorizzati; niente sui descrittivi | `FatturaDrawer.vue` |
| **R-FE-5** | ✅ nessun codice: la colonna non ha uno slot e rende il `campo_sorgente` del CSV (il codice del modo). Il formato con l'etichetta tradotta viene con R-FE-3 | — |

Test: suite Django completa **6027 verdi** col secondo livello acceso (`ZEROERP_TEST_DB_E2E=1`), build FE e lint puliti.
⚠️ Non lanciato: lo smoke bash `smoke-test-preventivi-componenti.sh` (crea dati via HTTP, vuole il BE riavviato).

### 10.2 Richiesta al team DB

| # | Cosa | Perché |
| --- | --- | --- |
| **R-DB-K1** | Una riga in `80_data/sql/config/tabelle_gestibili.csv`: `config.esposizioni_componente`, `lookup = true`, `pannello = false` (è la semantica della vista, non una configurazione: §9.2) | è la whitelist del lookup generico; senza, `GET /core/lookup/codici/?rel=config.esposizioni_componente` risponde 400 e il FE non ha le tre etichette. Sblocca R-BE-6 → R-FE-2, R-FE-3 |

### 10.3 I passi di Tid, in quest'ordine

1. **Riavvio del backend** (`kill -HUP` sul master gunicorn): da qui la fattura si genera con un kit e
   il builder produce la **forma 3**. ⚠️ Da questo momento la **v4 pubblicata non stampa più** (409
   del patto: legge la forma 2) finché non è pubblicata la v5 — la finestra va tenuta corta.
2. **Script §9.3 sul meta delle attività**, subito: prima prova (`ROLLBACK`), poi `-v applica=1`.
   Senza, un'attività vecchia con `esposto_in_fattura: true` si fatturerebbe NASCOSTO invece che
   DESCRITTIVO, senza errore.
   ✅ **Fatto da Tid il 2026-10-02** (`COMMIT`): chiave vecchia da 24 → 0 su `commesse_attivita`
   (8 DESCRITTIVO, 16 NASCOSTO) e da 21 → 0 su `attivita_fatturabili` (7 DESCRITTIVO, 14
   NASCOSTO), tutti codici a catalogo, **nessuna riga rifiutata**; `fatture_righe.meta` senza la
   chiave vecchia.
3. **Bozza v5** dall'app: template «fattura» → versione 4 → «Clona»; HTML sostituito col contenuto di
   [`template-fattura-v5.html`](template-fattura-v5.html), «Legge i dati nella forma» = **3**.
4. **Pubblicare la v5** (`valido_dal` = oggi): la v4 diventa OBSOLETA.

### 10.4 La numerazione condivisa con l'esigibilità

Il kit è arrivato per primo e ha preso **forma 3 / v5**. Il giro R-3 di
`brief-db-esigibilita-iva-per-cassa-emittente.md` passa a **forma 4 / v6**: la sua bozza è stata
rinominata [`template-fattura-v6.html`](template-fattura-v6.html) e rifatta sopra la v5 (v5 + il solo
blocco annotazioni, verificato con `diff`); il brief è aggiornato (§11.3).

### 10.5 Risposta del team DB (2026-10-02, `dev/db-tid`)

| # | Esito | Dove |
| --- | --- | --- |
| **R-DB-K1** | ✅ scritto e **applicato** da Tid il 2026-10-02: riga `89,config.esposizioni_componente,…,true,false` — oggetto (schema, nome tabella) per convenzione (D-P1), `lookup = true`, `pannello = false` (§9.2: semantica della vista, non configurazione). Nessun changeSet nuovo: il mirror `20260925-30` è `runOnChange` + `ANY`, la riga entra al prossimo apply e il secondo change riallinea la sequence (stampo della riga 88, `config.regimi_fiscali`). Nessun GRANT da scrivere: la tabella li prende dal loop di `ci_apply` come ogni `config.*`. I pgTAP del pannello (`test-pannello-porta-v1`, 6/7/9) non toccano una riga fuori dal pannello | `80_data/sql/config/tabelle_gestibili.csv` |

⚠️ Il commento in testa allo YAML del mirror dice ancora «le 87 voci»: era già stantio dalla riga
88, e non si riscrive un changelog pushato per un commento.

**Dopo l'apply**, al team BE: R-BE-6 (la voce in `_LOOKUP_SPECIALIZZATE`, già pronta in §10.1), poi
R-FE-2 e R-FE-3.
