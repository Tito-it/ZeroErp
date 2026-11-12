# Brief DB — `ui.lista_colonna`: «nessuna sorgente» è NULL, non la stringa vuota

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: sessione DB**, con l'archiviazione (passo 6), dopo il commit del lavoro BE sul suo branch. Il BE ha
chiuso §5 il 2026-11-12 (§5.3): K-1 … K-4 fatti, il CI dei test backend torna verde, le verifiche di §5.2 fatte.
Il lato DB è applicato su dbdev e scratch, i pgTAP sono verdi (Tid, 2026-11-12) ed è committato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | Il modello: «nessuna sorgente» è `NULL` (2026-11-12) | §1 | — |
| 2 | ✅ Tid | D1 (a): tutte le colonne testo opzionali del CSV, nello stesso giro (2026-11-12) | §4 | 1 |
| 2-bis | ✅ Tid | Il via al giro; numero `20261112-30` dalla sessione del catalogo (2026-11-12) | §3 | 2 |
| 3 | ✅ sessione DB | Il giro: il mirror, il CSV, i vincoli, i pgTAP, la doc; provato sullo scratch | §6 | 2-bis |
| 4 | ✅ Tid | Apply su dbdev e scratch, pgTAP verdi (2026-11-12) | §6.2 | 3 |
| 5 | ✅ team BE | K-1 … K-4: i test che leggono il CSV, il rosso in CI, il presidio dei preset (2026-11-12) | §5.1, §5.3 | 4 |
| 5-bis | ✅ team BE/FE | Le verifiche di §5.2 (2026-11-12) | §5.2, §5.3 | 4 |
| 5-ter | **Tid** | Il commit del lavoro BE su `dev/backend-tid` | §5.3 | 5 |
| 6 | sessione DB ⏭️ | Archiviazione in `work-done/`; in §5.2.2 l'elenco dei commenti va completato con `CodaLavoriTab.vue` | — | 5-ter |

**Decisioni aperte di Tid**: nessuna. **Da committare**: il lavoro BE di §5.3, su `dev/backend-tid`; il giro
DB è committato.

**Brief vicini verificati**: `sviluppo-personalizzazioni-liste_def.md` (la prassi di DEF-7/DEF-10
«`campo_sorgente` vuoto a catalogo» intende *senza sorgente*: non decide fra `NULL` e `''`, e qui non
si revoca); `piano-migrazione-primevue-5.md` §8-bis (la regola del generatore di seed, che già dice
`NULL`: `scripts/gen_seed_lista.py`); `brief-db-revisione-catalogo.md` (tocca `ui` solo per le
proiezioni del catalogo). Nessuno copre il tema.

## 1. Il modello

Una colonna `azione`, o una colonna calcolata dal frontend, **non ha sorgente**: per il modello
l'assenza è `NULL`. La colonna è nullable, e il `COMMENT` della tabella, il manual e
`scripts/gen_seed_lista.py` promettono `NULL`. Il pannello di amministrazione salva `NULL`
(`ListaColonnaDrawer.vue`, `campo_sorgente?.trim() || null`).

Il seed invece scrive `''`: il mirror `80_data/changelog/20260806-15-riancora-mirror-ui-lista-colonna`
dichiara `nullValue: ""`, e su una colonna `STRING` Liquibase scrive una cella vuota come stringa
vuota. Così convivono due forme dello stesso significato, `NULL` dal pannello e `''` dal seed.
Chiunque legga la colonna deve ricordarsi di accettarle entrambe: il guard
`trgfn_ui_lista_colonna_a10_valida_campo_sorgente` lo fa, mentre un presidio scritto sulla promessa
del `COMMENT` (`WHERE campo_sorgente IS NOT NULL`) tiene dentro le colonne `azione`.

## 2. Che cosa si sa già, come fatto datato (2026-11-12)

Nel CSV `80_data/sql/ui/lista_colonna.csv` le celle vuote di `campo_sorgente` stanno su righe
`azione` e `informazione`. Il dato non decide niente: la regola vale anche per una riga sola.

## 3. Il giro

1. Il mirror passa a `nullValue: "NULL"`, e le celle senza sorgente portano il token `NULL`
   (linee-guida-sql §11.7). ⚠️ Con `nullValue: ""` una cella vuota diventa `NULL` anche sulle
   colonne `NUMERIC` (`larghezza_default`, `gruppo_ordine`). Col token nuovo quelle celle vanno
   scritte `NULL` anche loro, altrimenti il loader prova a convertire `''` in un numero.
2. Un vincolo `CHECK (<colonna> IS NULL OR btrim(<colonna>) <> '')` per ognuna delle cinque colonne
   testo opzionali (`campo_sorgente`, `etichetta_estesa`, `formato`, `gruppo`, `etichetta_i18n_key`,
   per D1), in `90_end` dopo il mirror (linee-guida-sql §11.14, «un vincolo nuovo passa anche da chi scrive già la tabella»).
   Prima si censisce chi scrive la tabella, nelle quattro sedi di §11.14.
3. ⚠️ Superato, vedi §6: il guard **resta** com'è. I seed storici di `lista_colonna`, da zero,
   girano dopo il guard e scrivono ancora `''` sulle colonne `informazione`: se il guard la
   rifiutasse, il migrate da zero si fermerebbe in `80_data`. Il vincolo in `90_end` arriva dopo di
   loro. I lettori che tollerano anche `''` restano corretti e non si toccano in questo giro.
4. Un pgTAP che prova il vincolo con una riga **costruita** (`''` rifiutata, `NULL` accettata) e
   che la riga `azione` del seed vero ha `NULL`: una fixture che simula il loader prova la
   simulazione.
5. La doc: il manual di `lista_colonna` dice già `NULL`. Si cercano in `docs/` le pagine che
   raccontano la stringa vuota o la doppia tolleranza, e si correggono.

Si prova prima dell'apply con `scripts/prova_changeset.py`. Il passo 1 va provato **dal loader**,
cioè con l'SQL estratto del mirror, non con un upsert scritto a mano: è il caso in cui la
simulazione dà verde e l'apply si ferma.

## 4. Decisione presa

**D1 — Solo `campo_sorgente`, o tutte le colonne testo opzionali del CSV?** ✅ **Tid, 2026-11-12: (a), tutte.** `etichetta_estesa`,
`formato`, `gruppo` ed `etichetta_i18n_key` hanno la stessa forma: cella vuota = `''` per il loader,
mentre il pannello ci scrive `NULL`.

* ✅ (a) **Tutte**, nello stesso giro: il mirror e il token cambiano comunque per tutto
  il file, e lasciare le altre a `''` tiene in vita le due forme su quattro colonne.
* (b) Solo `campo_sorgente`: le celle vuote delle altre colonne testo restano `''`. Scartata.

## 5. Ricaduta sul BE/FE

### 5.1 Richiesta al BE: i test che leggono il CSV (Tid, 2026-11-12)

Tre test del backend leggono `80_data/sql/ui/lista_colonna.csv` **direttamente**, con `csv.DictReader`, e la
cella `NULL` per loro è la stringa `'NULL'`: un valore presente. Tid ha deciso che la correzione è del team BE,
sul suo branch (la sessione DB non tocca `backend/`). Elenco chiuso, censito il 2026-11-12:

* **K-1 — un rosso.** `apps/core/tests/test_liste_configurabili_seed.py`,
  `test_ogni_formato_del_seed_e_reso_dal_frontend`: `(r["formato"] or "").strip()` è vero per `'NULL'`, che non è
  un formato reso da `CellaConfigurabile`. In CI il passo dei test backend è rosso da questo commit in poi.
* **K-2 — un presidio accecato, senza rosso.** Stesso file, `test_whitelist_chiavata_sul_campo_sorgente`: le 85
  colonne senza sorgente hanno `codice != 'NULL'` e finiscono in `divergenti_totali`, il contatore che serve a non
  passare a vuoto. Restano escluse dalle asserzioni, perché nessuna è ordinabile, ma il contatore è soddisfatto da
  loro e quindi non può più scattare.
* **K-3 — un filtro fragile.** `apps/vendite/tests/services/test_riporta_da_emettere_service.py` (lista 49):
  `r.get("campo_sorgente")` accetta `'NULL'`. Oggi è verde perché la lista 49 non ha colonne calcolate dal FE;
  il giorno in cui ne ha una, cerca il campo `NULL` nella riga.

* **K-4 — un presidio nuovo, nello stesso file** (dal gruppo C di `brief-db-guardrail-forme-residue`, Tid
  2026-11-12). In `ui.lista_preset.ordinamento_default` la chiave `col` nomina il `campo_sorgente` della colonna,
  non il suo `codice`: dove i due differiscono, un preset che usa il codice ordina per una colonna che non esiste,
  senza errore a DB. Si chiede un test che, per ogni preset di `lista_preset.csv`, pretenda che ogni `col`
  dell'ordinamento sia un `campo_sorgente` delle colonne della sua lista in `lista_colonna.csv`. Fatto datato
  (2026-11-12): le 81 chiavi di ordinamento del seed sono tutte giuste, quindi il test nasce verde e va visto rosso
  su un preset costruito col codice.

⭐ La causa comune: il CSV si legge in tre posti, con due copie di `_seed()` (`test_liste_configurabili_seed.py` e
`test_ordinamento_data_desc.py`) e una lettura in linea. La proposta è **una lettura sola**, che renda `None` la
cella col token del loader di quel file: `NULL` per `lista_colonna.csv` e per `lista_definizione.csv` (che lo usa
già da maggio), la cella vuota per `lista_preset.csv` e `lista_preset_colonna.csv`. Il token di ogni file sta nel
`nullValue` del suo mirror, e `scripts/gen_seed_lista.py` lo tiene nel descrittore `CSV_SEED`. Le letture sicure
oggi (`test_ordinamento_data_desc.py`, colonne ordinabili; `test_lineage_liste_be.py`, solo `lista_id`) passano
dalla stessa lettura.

### 5.2 Le verifiche dopo l'apply

Elenco chiuso:

1. `backend/apps/ui/db/ui_repository.py` e `ui_admin_repository.py` leggono `campo_sorgente`. Una
   risposta API con `null` al posto di `""` è un cambio di contratto: il serializer
   `_schema_ui.py` lo dichiara già nullable. In scrittura non cambia niente: il service porta già
   `''` a `None` (`payload_helpers.optional_string`), quindi il vincolo non arriva mai a rifiutare
   una richiesta del pannello. `lista_export_service._format_cell` tratta `campo_sorgente` `None`
   come cella vuota, come prima con `''`.
2. Nel frontend le letture usano il test di verità (`v-if="data.campo_sorgente"`,
   `?? ''`), falso per entrambe le forme. Restano da aggiornare i commenti che dicono «seed:
   `campo_sorgente` vuoto» (`AuditLogView.vue`, `CodaStampaTab.vue`).
3. Per D1 (a), lo stesso per `etichetta_estesa`, `formato`, `gruppo` ed `etichetta_i18n_key`.

### 5.3 Il giro BE fatto (team BE, 2026-11-12)

**La lettura unica**, come proposto in §5.1 ⭐: il building block `seed_csv` / `seed_ui`
(`backend/apps/core/tests/_seed_csv.py`, a catalogo BB backend). Dà `None` dove il caricatore del file scrive
NULL. Il token si legge dal `nullValue` dei caricatori Liquibase del file. Dove i caricatori sono più d'uno e
non sono d'accordo decide `CSV_SEED` di `scripts/gen_seed_lista.py`: è il caso di `lista_colonna.csv`, che ha
il seed `20260507-07` con `""` e il mirror `20260806-15` con `"NULL"`, e il descrittore deve coincidere con uno
dei due. Senza una risposta sola, il building block solleva. Le due copie di `_seed()` sono ritirate.

* **K-1**: verde con la lettura corretta.
* **K-2**: il contatore `divergenti_totali` conta solo le divergenti **ordinabili**, cioè quelle che le
  asserzioni esercitano.
* **K-3**: la lettura in linea della lista 49 passa da `seed_colonne_attive("vendite.dash_competenza_residui")`.
  Erano spariti anche il `parents[4]` contato a mano e lo `skipTest` su file assente.
* **K-4**: `test_l_ordinamento_dei_preset_nomina_il_campo_sorgente`, contro i `campo_sorgente` delle colonne
  **attive**, le sole che `fn_resolve_lista_config` consegna (fatto datato: 81 chiavi, tutte giuste).
  `test_l_ordinamento_col_codice_e_rifiutato` lo vede rosso su un preset costruito col codice.

**Oltre l'elenco chiuso di §5.1**, trovati sulla stessa causa:
* `test_lotto_gruppi_service` e `test_dashboard_competenza_service` avevano la forma di K-3 e passano da sé
  sulla lettura unica.
* `test_lineage_liste_be`, `test_ricerca_full_seed`, `test_ricerca_full_db`,
  `test_lista_proiezione_campo_sorgente` e `test_perimetro_emittente_copertura` leggevano il seed con `_seed`
  e ora passano da `seed_ui`.
* I quattro ripieghi su `"NULL"` scritti a mano (tre in `test_lista_proiezione_campo_sorgente`, uno in `test_ricerca_full_db`)
  sono tolti.

**§5.2**:
* (1) Il BE è come descritto: il serializer dichiara nullable i cinque campi e l'export tratta `None` come
  cella vuota. Non c'è nessun confronto esplicito con `''` su quei campi, né nel FE né nel BE.
* (2) Commenti aggiornati in `AuditLogView.vue` e `CodaStampaTab.vue`, **e in `CodaLavoriTab.vue`**, che
  l'elenco non aveva.
* L'hint del pannello «Lascia vuoto» (`colonna_campo_sorgente_hint`) resta: il pannello porta `''` a `None`.

**Fuori brief, nello stesso giro (ok Tid)**:
* `seed_csv` serve anche i due helper che riconoscevano il token a mano: `_contratto_processi`
  (`dbops/processi.csv`) e `test_event_codes_declared_guardrail` (`config/tipi_entita.csv`,
  `eventi_dominio.csv`). Lì la cella vuota era trattata come NULL; ora resta `''`, come la scrive il loader.
  Per `brief-db-nullvalue-vuoto-cinque-mirror` §4.3: chi legge un CSV di seed nei test passa da `seed_csv`, e
  i lettori che non ci passano oggi leggono solo colonne NOT NULL (`test_sorgenti_seed`,
  `test_catalogo_oggetti_rotte`, `test_error_policies_classi`, `test_pagamenti_repository_sql`).
* Il building block ha un test suo, `test_seed_csv`: il token di ogni file noto, la cella vuota che resta `''`,
  il rifiuto di un file senza caricatore e di un descrittore in disaccordo coi caricatori.
* Il pulitore dei `.vue` è spostato in `_repo.py` come `vue_senza_commenti`.
  `_colonne_desc_dichiarate` leggeva i repository Python con quel pulitore, che lascia i `#`: ora usa
  `sorgente_senza_commenti`.
* I `Path(__file__).resolve().parents[N]` contati a mano nei test (21 siti in 14 file) passano da `repo_root()`.
  Oggi indicavano tutti la cartella giusta, ma se il file si sposta un percorso contato a mano trova zero file e
  il test passa a vuoto. Restano fuori, di proposito, i due nel codice di produzione (`genera_error_policies`,
  `core/services/sveglie.py`): `repo_root` è un helper dei test.
* Revisione (`/verifica`, 2026-11-12): passano da `seed_csv` anche `_seed_config` di
  `test_perimetro_emittente_copertura` (`config/codici_errore.csv`) e `_colonne_con_grant`; il BB rifiuta un
  `nullValue` che non è una stringa invece di un `assert`; il 5-ter sceglie una divergente il cui codice non è
  il `campo_sorgente` di un'altra colonna della lista.
* Stessa revisione (ok Tid): `_lista_id` e `_colonne_attive` escono da `test_liste_configurabili_seed`, dove
  cinque test di `core` e `vendite` li importavano come nomi privati, ed entrano nel BB come `seed_lista_id` e
  `seed_colonne_attive`.

**Nota aperta — maiuscole e minuscole del token** (revisione 2026-11-12, non verificata): `seed_csv` confronta la
cella col `nullValue` **esattamente**. Non è verificato se il loader Liquibase lo confronti senza distinguere
maiuscole e minuscole: se lo fa, una cella `null` (in minuscolo) per il DB è NULL e per il BB resta la stringa
`'null'`. Oggi il caso esiste in `vendite/fatturazione_pipeline.csv` (fatto datato), che nessun test legge
tramite `seed_csv`. Chi lo verifica sul codice di Liquibase allinea il confronto del BB e gli aggiunge il test.

**Prove**: i file toccati sono verdi anche coi test sul DB vero accesi (`ZEROERP_TEST_DB_E2E=1`, in
transazione annullata). La suite backend intera è verde a fine giro, dopo la revisione e la pulizia dei `parents[N]`: 6594 test,
`OK (skipped=293, expected failures=1)`.

## 6. Il giro fatto (2026-11-12)

### 6.1 Che cosa

| File | Che cosa |
| --- | --- |
| `80_data/changelog/20260806-15-riancora-mirror-ui-lista-colonna` | `nullValue: "NULL"`, con il perché in intestazione. Il mirror è `runOnChange` + `validCheckSums: ANY`: si ritocca (linee-guida-sql §11.2) |
| `80_data/sql/ui/lista_colonna.csv` | il token `NULL` nelle celle vuote delle sette colonne nullable (le cinque testo più `larghezza_default` e `gruppo_ordine`), cella per cella: nessun'altra cella cambia. Restano vuote le 4 celle di `etichetta`, NOT NULL e fuori da questo giro |
| `90_end/20261112-30-add-chk-lista-colonna-testi-non-vuoti` | porta a `NULL` le stringhe vuote che il CSV non conosce (colonne create su un'installazione), poi i cinque `CHECK` `chk_lista_colonna_<colonna>_non_vuoto/a`, con `COMMENT` |
| `db/pgtap/ui/test-lista-colonna-testi-non-vuoti-v1` | nuovo: ogni colonna con `''` rifiutata dal suo vincolo, i soli spazi pure, `NULL` passa, il seed senza `''` |
| `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1` | il test 8 costruiva una sorgente `''`, che ora non può esistere: prova che il vincolo la rifiuta |
| manual `lista_colonna`, `fn_lista_colonne_ricerca_full` | la regola dell'assenza; la riga che diceva «vuoto = NULL o stringa vuota» |
| `scripts/check_i18n_keys.py` | legge il token `NULL` di `etichetta_i18n_key` come «nessuna chiave» (prima lo prendeva per una chiave da tradurre: pre-commit rosso) |
| `scripts/gen_seed_lista.py` | il descrittore di `lista_colonna.csv` passa a `nullo: "NULL"`, e le righe nuove usano il token nelle sette colonne nullable: una lista generata con le celle vuote sarebbe rifiutata dai `CHECK` |

Censimento di chi scrive la tabella (§11.14): il seed; nessuna funzione del database; il backend,
che normalizza; una sola fixture pgTAP, quella del test 8.

### 6.2 Le prove, sullo scratch `zeroerp_ruoli`, in transazione annullata

* `-28` + `-30` con `ui/test-lista-colonna-testi-non-vuoti-v1`: 9 su 9. Senza il `-30`, 8 rossi su
  9, cioè cadono i casi giusti.
* `-28` + `-30` con `ui/test-fn-lista-colonne-ricerca-full-v1`: 20 su 20.
* Il loader, col render offline di Liquibase (`updateSQL --url=offline:postgresql`) su una copia del
  mirror senza `preConditions`: le 85 righe senza sorgente escono con `campo_sorgente = NULL`, le
  celle numeriche col token escono `NULL`, e le sole stringhe vuote rimaste sono le 4 `etichetta`.
  ⚠️ L'SQL reso non è stato eseguito: il test 9 del pgTAP nuovo lo copre solo in parte, perché lo
  fa passare anche la conversione del `-30`. La prova completa è l'apply.

* `-28` + `-30` con gli altri 15 pgTAP di `ui/` che nominano `lista_colonna`: risultati identici
  senza e con. Due hanno un rosso che c'era già prima, uguale nelle due corse:
  `test-lista-definizione-perimetro-emittente-v1` e `test-lista-competenza-gruppi-colonna-emittente-v1`
  (1 ciascuno). Da owner, sullo scratch: non è un rosso di questo giro.

Dopo l'apply: i due pgTAP toccati e quelli di `ui/`.

