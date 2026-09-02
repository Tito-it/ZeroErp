# Brief team DB — seed lotto 2: 4 liste (pagamenti · anagrafiche)

> Destinatario: team DB (`dev/db-tid`) · Origine: `dev/backend-tid` · 2026-09-02
> Secondo lotto dopo le 4 liste `ui`
> ([brief-db-seed-liste-ui-admin](../work-done/brief-db-seed-liste-ui-admin.md)).
> Dimensione: **quattro append a CSV, nessun changeset, nessun DDL.**

## 1. Scopo

Seedare le quattro liste del Gruppo A emerse dalla classificazione del 2026-09-02
([piano PrimeVue 5 §Classificazione fatta](piano-migrazione-primevue-5.md)).

| `lista_id` | codice | consumer FE | col. | paginazione |
| --- | --- | --- | --- | --- |
| 60 | `pagamenti.canali_incasso` | `pagamenti/components/CanaliIncassoSearchTable.vue` | 8 | **server-side** (`paginata: true`) |
| 61 | `pagamenti.sistemazioni_fattura` | `pagamenti/components/SistemazioneDrawer.vue` | 6 | **non paginata** |
| 62 | `anagrafiche.soggetto_titoli_iva` | `anagrafiche/components/TitoliIvaSoggettoDrawer.vue` | 6 | **non paginata** |
| 63 | `anagrafiche.titoli_iva_sfondati` | `anagrafiche/views/TitoliIvaSfondatiView.vue` | 8 | **server-side** (`paginata: true`) |

⭐ **La 63 era bloccata e non lo è più**: mostrava i primi 500 senza dirlo. Su
decisione di Tid (2026-09-02) è stata **paginata sullo standard** invece di
dichiarare il cap — vedi §5.

⛔ Nessun DDL. I quattro loader sono mirror `runOnChange` + `loadUpdateData`:
**appendere le righe basta** (`20260507-06/07/08/09`).

## 2. Le righe

Generate con `scripts/gen_seed_lista.py`, con le correzioni di §3. Id oltre il
massimo corrente (definizione 59, colonna 672, preset 59).

### `lista_definizione.csv`

```csv
60,pagamenti.canali_incasso,Canali di incasso,pagamenti,NULL,t,2026-09-02 00:00:00,mctit,f
61,pagamenti.sistemazioni_fattura,Atti di sistemazione di una fattura,pagamenti,NULL,t,2026-09-02 00:00:00,mctit,f
62,anagrafiche.soggetto_titoli_iva,Titoli IVA di un soggetto,anagrafiche,NULL,t,2026-09-02 00:00:00,mctit,f
63,anagrafiche.titoli_iva_sfondati,Titoli IVA con plafond sfondato,anagrafiche,NULL,t,2026-09-02 00:00:00,mctit,f
```

### `lista_colonna.csv`

```csv
673,60,codice,Codice,,codice,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_codice,100
674,60,descrizione,Descrizione,,descrizione,informazione,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_descrizione,90
675,60,tipo,Tipo,,tipo,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_tipo,80
676,60,conto_iban,Conto di incasso,,conto_iban,informazione,string,,,40,left,,,t,f,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_conto,70
677,60,conto_utility,Utility del conto,,conto_utility_descrizione,informazione,string,,,50,left,,,t,f,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_utility,40
678,60,centro,Centro di riscossione,,centro_descrizione,informazione,string,,,60,left,,,t,f,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_centro,60
679,60,attivo,Attivo,,attivo,informazione,boolean,,,70,center,,,t,f,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_attivo,70
680,60,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
681,61,destinazione,Destinazione,,destinazione,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.sistemazioni.col_destinazione,100
682,61,importo,Importo,,importo,informazione,numeric,currency_eur,,20,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.sistemazioni.col_importo,90
683,61,stato,Stato,,stato,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.sistemazioni.col_stato,80
684,61,motivo,Motivo,,motivo,informazione,string,,,40,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.sistemazioni.col_motivo,50
685,61,data_esecuzione,Eseguita il,,data_esecuzione,informazione,datetime,datetime_short,,50,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.sistemazioni.col_eseguita,60
686,61,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
687,62,tipo,Tipo,,tipo_descrizione,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_tipo,100
688,62,emittente_ragione_sociale,Emittente,,emittente_ragione_sociale,informazione,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_emittente,80
689,62,iva,IVA,,iva_codice,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_iva,70
690,62,validita,Validità,Compone valido_dal e valido_al,,informazione,string,,,40,left,,,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_validita,60
691,62,residuo,Residuo,,residuo,informazione,numeric,currency_eur,,50,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_residuo,90
692,62,stato,Stato,Compone attivo e ambito_incompleto,,informazione,string,,,60,left,,,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_stato,80
693,63,soggetto_ragione_sociale,Soggetto,,soggetto_ragione_sociale,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_soggetto,100
694,63,soggetto_id_fiscale,CF / P.IVA,,soggetto_id_fiscale,informazione,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_id_fiscale,70
695,63,tipo,Tipo,,tipo_descrizione,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_tipo,80
696,63,emittente_ragione_sociale,Emittente,,emittente_ragione_sociale,informazione,string,,,40,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_emittente,60
697,63,validita,Validità,Compone valido_dal e valido_al,,informazione,string,,,50,left,,,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_validita,40
698,63,plafond,Plafond,,plafond,informazione,numeric,currency_eur,,60,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.field_plafond,70
699,63,imponibile_utilizzato,Utilizzato,,imponibile_utilizzato,informazione,numeric,currency_eur,,70,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.field_utilizzato,80
700,63,eccedenza,Eccedenza,,eccedenza,informazione,numeric,currency_eur,,80,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,anagrafiche.titoli_iva.col_eccedenza,100
```

### `lista_preset.csv`

```csv
60,60,canali_incasso_default,Vista standard canali di incasso,sistema,,,t,25,,t,2026-09-02 00:00:00,mctit
61,61,sistemazioni_fattura_default,Vista standard atti di sistemazione,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
62,62,soggetto_titoli_iva_default,Vista standard titoli IVA soggetto,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
63,63,titoli_iva_sfondati_default,Vista standard titoli IVA sfondati,sistema,,,t,25,,t,2026-09-02 00:00:00,mctit
```

⚠️ `pagina_dimensione` = **25 sulle due che paginano davvero** (60 e 63);
**vuota** sulle altre due, come per il lotto `ui`: un preset che dichiara una
dimensione mai applicata è una dichiarazione falsa.

⚠️ **La lista 63 non ha colonna `azioni`, e non va creata per simmetria**: la
schermata è di sola consultazione, il kebab non avrebbe voci. Stessa regola del
lotto 2026-07-31 (lezione n.5: una colonna azioni senza azioni resta
riesumabile dalla personalizzazione come colonna vuota).

### `lista_preset_colonna.csv`

```csv
60,673,10,t,t
60,674,20,t,f
60,675,30,t,f
60,676,40,t,f
60,677,50,t,f
60,678,60,t,f
60,679,70,t,f
60,680,999,t,f
61,681,10,t,t
61,682,20,t,f
61,683,30,t,f
61,684,40,t,f
61,685,50,t,f
61,686,999,t,f
62,687,10,t,t
62,688,20,t,f
62,689,30,t,f
62,690,40,t,f
62,691,50,t,f
62,692,60,t,f
63,693,10,t,t
63,694,20,t,f
63,695,30,t,f
63,696,40,t,f
63,697,50,t,f
63,698,60,t,f
63,699,70,t,f
63,700,80,t,f
```

## 3. Le correzioni all'output del generatore

| # | Cosa | Perché |
| --- | --- | --- |
| 1 | **`ordinabile = f`** su `conto_iban`, `conto_utility`, `centro`, `attivo` (lista 60) | Lo script le propone tutte ordinabili. Ma `ENTI_INCASSO_SORT_COLUMNS` accetta solo `codice`, `descrizione`, `tipo` (+ `centro`, chiavata sul **logico** e mappata su `centro_codice`, che non è il `campo_sorgente` mostrato). Una colonna `ordinabile=t` fuori whitelist è **una freccia che risponde 400 al primo click** — lezione n.1 del piano |
| 2 | `residuo` (lista 62): da «calcolata FE» a **campo sorgente vero** | Il body rende `data.residuo`: la colonna è solo *renderizzata* da un `<Tag>`, il campo esiste nel payload. Stessa deduzione sbagliata del lotto `ui` |
| 3 | `validita` e `stato` (lista 62) restano **calcolate** | Qui lo script ha ragione: `validita` compone `valido_dal`+`valido_al`, `stato` compone `attivo`+`ambito_incompleto`. Due sorgenti, nessuna singola |
| 4 | `tipo_dato` di `validita` da `date` a **`string`** | Non è una data: è una frase che ne unisce due («01/01/2026 — senza scadenza»). Lasciarlo `date` con `formato=date_short` avrebbe fatto formattare una stringa composta |
| 5 | `pagina_dimensione` vuota sulle liste 61 e 62 | Non paginate — vedi sopra |
| 6 | `ordinamento_default` vuoto su tutti e tre | Le righe arrivano già ordinate dal BE; dichiararlo farebbe ri-ordinare in locale con semantica diversa |
| 7 | `priorita` valorizzata invece del default 50 | Ordine di ritiro responsive: identità e importi tengono, gli accessori (`conto_utility`, `motivo`) cedono per primi |

## 4. Il prerequisito BE — ✅ già fatto (2026-09-02, nessun impatto DB)

Le due liste non paginate pretendono un endpoint che dichiari il conteggio con
una query **sua**, o il guard anti-troncamento del building block è un'eco.

| Endpoint | Cosa è stato fatto |
| --- | --- |
| `GET /pagamenti/fatture/<id>/sistemazioni/` | ⚠️ Restituiva già `{"count": len(atti)}` — **la tautologia in forma già scritta**: sembra giusta e non lo è. Ora `count_sistemazioni_fattura()` con lo stesso `WHERE` |
| `GET /anagrafiche/soggetti/<id>/titoli-iva/` | Aggiunto `count` all'envelope, da `count_titoli_soggetto()` |

⭐ **Su `count_titoli_soggetto` il `FROM` è `_TITOLO_JOINS` per intero**: quei
join sono **INNER** e possono togliere righe. Un `count(*)` sulla sola
`soggetti_titoli_iva` avrebbe contato di più e acceso il guard su un troncamento
inesistente.

⚠️ **`list_titoli_soggetto` NON ha cambiato firma**, di proposito: la consuma
anche `soggetti_service`, che la incorpora nel dettaglio di un soggetto e si
aspetta una **lista**. L'envelope lo compone la view.

## 5. ✅ La quarta lista: paginata, non più bloccata

`anagrafiche.titoli_iva_sfondati` era fuori dal lotto perché
`list_titoli_sfondati()` restituiva i primi **500** (`_SFONDATI_LIMIT`) e il
frontend **non lo diceva a nessuno**. Su una lista di presidio — esiste perché
una forzatura di plafond non sfugga — dal 501-esimo caso in poi il difetto non
si vedeva, e nessuno poteva accorgersene.

⭐ **Decisione di Tid (2026-09-02): paginarla sullo standard** invece di
dichiarare il cap. Fatto lato BE, **nessun impatto DB**:

| Dove | Cosa |
| --- | --- |
| `titoli_iva_repository.py` | `list_titoli_sfondati(limit, offset, order_by, order_dir)` → **`(righe, totale)` in UNA valutazione** (`COUNT(*) OVER()` via il BB `fetch_paged_with_total`), con `fallback_count_sql` per il rientro su pagina stantia; `FROM`+`WHERE` in `_SFONDATI_FROM_WHERE`, condiviso fra pagina e fallback |
| idem | `_ORDER_COLS_SFONDATI` — whitelist **chiavata sui `campo_sorgente` fisici** (lezione n.1) |
| idem | `eccedenza` esposta come **alias SQL** invece che calcolata dal frontend: è l'ordinamento che dà senso alla lista, e così è anche ordinabile |
| `titoli_iva_service.py` | ritorna `{results, count}`; **`_SFONDATI_LIMIT` rimosso** |
| `views_titoli_iva.py` | `parse_list_params(default_order="eccedenza")` |

⚠️ **Il tiebreak `t.id` è obbligatorio** e c'è: due titoli con la stessa
eccedenza non sono un caso di scuola — il plafond è lo stesso per tipo — e senza
tiebreak a offset alti PostgreSQL può restituire righe già viste.

**Verifica**: 7 colonne × 3 direzioni (asc/desc/assente) + il rientro su pagina
stantia, eseguiti **contro il database vero**: SQL valido su tutti, e il
fallback del totale risponde.
⚠️ **Ma con zero righe** (in dev non ci sono sfondamenti): la prova dice che le
query si pianificano, **non** che l'ordinamento sia quello giusto. Quello si
vedrà al primo caso reale, ed è dichiarato qui perché nessuno lo scambi per una
verifica di comportamento.

**Sette test permanenti**, e quattro di essi leggono il **SQL generato** perché
è lì che i difetti vivevano:

| Test | Difetto che presidia |
| --- | --- |
| `senza_order_dir_ordina_decrescente` | 🔴 **Difetto reale, scritto e corretto lo stesso giorno**: la view passava `parse_list_params()["order_dir"]`, che normalizza l'assenza ad `"asc"` e non è mai `None` — quindi il `default_desc` del repository non veniva **mai** raggiunto e il presidio si ordinava dall'eccedenza più piccola. Il caso più grave in ultima pagina, senza nessun errore |
| `il_tiebreak_segue_la_direzione` | Tiebreak inchiodato a `DESC`: a parità di eccedenza l'elenco andava al contrario di come era stato chiesto |
| `pagina_e_conteggio_hanno_lo_stesso_perimetro` | `FROM`/`WHERE` che divergono fra pagina e totale |
| `order_dir_esplicito_vince` | Il default non deve schiacciare la scelta dell'operatore |
| `i_parametri_di_pagina_arrivano_al_repository` | Parametri persi per strada → sempre la prima pagina |
| `il_totale_non_e_la_lunghezza_della_pagina` | Il `count` derivato dalle righe (repo che dichiara 700 e consegna 2) |
| `whitelist_chiavata_sui_campi_fisici` | Lezione n.1 |

⭐ I primi due sono stati **provati per mutazione**: rimesso il difetto, il test
giusto diventa rosso; ripristinato, torna verde.
