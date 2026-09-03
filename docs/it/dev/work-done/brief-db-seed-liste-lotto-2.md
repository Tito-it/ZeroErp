# Brief team DB — seed lotto 2: 4 liste (pagamenti · anagrafiche)

> Destinatario: team DB (`dev/db-tid`) · Origine: `dev/backend-tid` · 2026-09-02
> Secondo lotto dopo le 4 liste `ui`
> ([brief-db-seed-liste-ui-admin](brief-db-seed-liste-ui-admin.md)).
> Dimensione: **quattro append a CSV, nessun changeset, nessun DDL.**

## 1. Scopo

Seedare le quattro liste del Gruppo A emerse dalla classificazione del 2026-09-02
([piano PrimeVue 5 §Classificazione fatta](../work-in-progress/piano-migrazione-primevue-5.md)).

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
678,60,centro,Centro di riscossione,,centro_descrizione,informazione,string,,,60,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,pagamenti.canali.col_centro,60
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
**vuota** sulle altre due, come per il lotto `ui`.

⛔ **La motivazione originale era sbagliata e va letta come corretta qui**
(2026-09-02). Diceva: *«un preset che dichiara una dimensione mai applicata è
una dichiarazione falsa»*. Non regge sul modello: `ui.fn_resolve_lista_config`
fa `COALESCE(lp.pagina_dimensione, 25)` in **tutti e tre** i rami (preset di
sistema, di ruolo, di emittente), quindi la configurazione risolta dice `25`
sia con la cella vuota sia con il `25` scritto. Le due forme sono
**indistinguibili a valle**: la cella vuota non è una dichiarazione più onesta,
è la stessa dichiarazione scritta in un altro modo.
⇒ **Vale il default** (decisione di Tid, 2026-09-02): la cella resta vuota
sulle non paginate perché lì non c'è una pagina da dichiarare, non perché
scrivere `25` sarebbe stato falso.

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
| 1 | **`ordinabile = f`** su `conto_iban`, `conto_utility`, `attivo` (lista 60) — ⚠️ **NON più su `centro`**, vedi §6 D-2 | Lo script le propone tutte ordinabili. Ma `ENTI_INCASSO_SORT_COLUMNS` accetta solo `codice`, `descrizione`, `tipo` (+ `centro`). Una colonna `ordinabile=t` fuori whitelist è **una freccia che risponde 400 al primo click** — lezione n.1 del piano. Le tre che restano `f` non hanno una colonna SQL ordinabile dietro: lì la `f` è sul modello, non sulla whitelist |
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

---

## 6. ✅ Decisioni di Tid del 2026-09-02, e cosa hanno chiuso

Il brief è stato riletto contro il database e contro il backend **mergiato**
(`fd4413469`) prima di seminare. Sei punti aperti, sei decisioni.

### D-1 · Ordinamento sulle liste 61 e 62 — si semina `t`, il BE segue

⛔ **Il difetto è reale e non è quello della lezione n.1.** `list_sistemazioni_fattura`
ha `ORDER BY s.id` inchiodato e `list_titoli_soggetto` ha
`ORDER BY COALESCE(t.valido_al,'infinity') DESC, …`: **nessuna delle due accetta
`order_by`**. `<ListaConfigurabile>` monta le `Column` con
`:field="col.campo_sorgente"`, quindi il parametro parte davvero — e Django lo
scarta senza dire niente. Non un 400: la freccia si gira sopra righe immobili.
⚠️ Peggio del 400, perché un 400 lo si vede.

⭐ **L'asimmetria è la spia**: lo stesso lavoro BE che sulla 63 ha scritto una
whitelist chiavata sui campi fisici **e** un test che la presidia
(`whitelist_chiavata_sui_campi_fisici`) ha lasciato la 61 e la 62 senza
whitelist affatto — dove non c'è niente da presidiare perché non c'è niente.

✅ **Decisione: si semina `ordinabile = t` come da §2, e il BE aggiorna i due
endpoint** (richiesta BE-1 in §7). Sono 9 colonne: 681-685 sulla 61, 687/688/689/691
sulla 62.
⚠️ **Finestra di latenza, ed è dichiarata perché nessuno la scambi per un
collaudo**: il frontend non è ancora migrato — `grep` sui quattro codici in
`frontend/src` non trova niente — quindi il seed non produce nessuna freccia
muta *oggi*. La produrrebbe il giorno in cui la view si monta sul BB **senza**
BE-1. Chi migra quelle due view guarda prima §7.

### D-2 · `centro` sulla lista 60 — «è giunto il giorno»

Il commento sopra `ENTI_INCASSO_SORT_COLUMNS` lo aveva scritto in anticipo:

> *«QUESTA E' ANCORA CHIAVATA SUI CODICI LOGICI, ed è legittimo **finché**
> l'elenco non diventa una `<ListaConfigurabile>` … ⛔ Il giorno in cui la
> schermata dei canali si monta sul BB, `centro` va riscritta come
> `centro_descrizione`»*

✅ **Questo brief è quel giorno.** La riga 678 passa a `ordinabile = t` e il BE
ri-chiava la whitelist (richiesta BE-2). ⛔ La strada corta era l'altra —
`ordinabile = f` e amen — e costava un ordinamento che il BE **sa già fare**,
per nessuna ragione di modello: la mappatura `centro → centro_codice` esiste ed
è giusta, sbagliata è solo la **chiave**. E avrebbe lasciato quel commento a
prescrivere una modifica che nessuno fa più, così che il prossimo lettore
trovasse una `f` senza causa.

⚠️ Le altre tre restano `f` per una ragione **diversa e più solida**:
`conto_iban`, `conto_utility_descrizione` e `attivo` non hanno una colonna
ordinabile dietro nella whitelist, e non è una dimenticanza da correggere.

### D-3 · Perimetro emittente — vale l'emittente dell'operatore

Il 2026-09-02 è entrata `ui.lista_definizione.perimetro_emittente` (DEFAULT
`TRUE`) e il backend ha imparato a leggerla (`ui_service.get_lista_config` →
`perimetro_emittente.richiede_scelta_emittente()`). Le tre combinazioni erano
quindi tutte disponibili, e il silenzio non sarebbe stato neutro.

✅ **Decisione: `multi_emittente = f`, `perimetro_emittente = t` su tutte e
quattro — vale l'emittente dell'operatore.** Le liste non sono multi-emittente:
le righe appartengono a un emittente e la lista non si assume il compito di
dire quale.

⚠️ **È una decisione presa, non un default ereditato**, e va scritto perché le
due cose si assomigliano nel CSV: `perimetro_emittente` **non è una colonna del
mirror** `20260507-06` (che ne dichiara 9), si scrive nel CSV dedicato
`lista_definizione_perimetro_emittente.csv` chiavato su `codice`. Non aggiungere
le quattro righe lì **è** la decisione D-3.

⛔ **L'alternativa scartata, e perché non era gratis.** La 62 e la 63 espongono
`emittente_ragione_sociale` in colonna (688 e 696): avrebbero potuto dichiarare
`multi_emittente = t`, e `dbops.vw_liste_multi_emittente_non_certificate` —
che cerca `campo_sorgente ~ '^emittent'` — sarebbe rimasta a zero righe, cioè
il flag sarebbe stato **certificabile a macchina**. Il prezzo è che la lista
smette di essere letta nel perimetro di chi guarda e diventa una vista globale:
è un cambio di natura, non di flag. Si riapre solo se qualcuno sbatte contro il
cancello, ed è la stessa condizione dichiarata per 56/57/59 nel changeSet
`20260902-02`.

### D-4 · Sequenze identity — nulla da fare, il presidio esiste già

🔴 **Rilievo sollevato in revisione e RITIRATO**, e vale la pena lasciarlo
scritto perché l'errore è istruttivo. L'osservazione era: `loadUpdateData`
inserisce id espliciti senza avanzare la sequenza `GENERATED BY DEFAULT AS
IDENTITY`, quindi il primo INSERT dall'amministrazione in-app
(`ui_admin_repository`, che inserisce **senza** id) collide sulla pkey.

⚠️ **Il meccanismo c'è, in duplice copia, e la ricerca che non l'ha trovato
cercava la cosa sbagliata**: un `grep` sul **nome** della sequenza
(`lista_colonna_id_seq`). Entrambi i presidi sono **dinamici** — costruiscono il
nome con `pg_get_serial_sequence()` — quindi quel nome non compare da nessuna
parte nel repository.

| Presidio | Forma | Copertura |
| --- | --- | --- |
| `90_end/20260602-17-resync-ui-seed-identity-sequences` | `runAlways` | Le **tre** tabelle di questo lotto, per nome |
| `90_end/20260818-72-resync-identity-sequences-globale` | `runAlways`, forward-only | Ogni colonna identity/serial del database |

✅ **Best practice = niente di nuovo.** `90_end` gira dopo `80_data`, quindi
vede il `MAX(id)` definitivo (700 sulle colonne) e riallinea a ogni deploy.
⭐ Nota che `20260818-72` dichiara la forma **idiomatica** come preferibile — il
`setval` dentro il seed stesso, «chi crea la deriva la ripara subito» — ma i
quattro loader sono mirror `runOnChange` già mergiati e condivisi con l'intero
catalogo delle liste: aggiungerci un `setval` non riparerebbe questo lotto, lo
farebbe girare a ogni modifica di **qualunque** lista. La rete di `90_end`
copre, e un terzo giro sarebbe rumore.

### D-5 · `pagina_dimensione` — vale il default

Vedi la nota corretta in §2: `COALESCE(…, 25)` rende le due forme
indistinguibili. Righe invariate, motivazione riscritta.

### D-6 · Le due minori — nessun impatto DB

| Osservazione | Decisione |
| --- | --- |
| `destinazione` e `stato` (lista 61) sono **codici grezzi** (`varchar(20)` + `CHECK IN ('RIPORTO','RIMBORSO','COMPENSAZIONE')`), senza display field in JOIN | ✅ Resta così: la decodifica di quei due vocabolari vive già in `frontend/src/pagamenti/vocabolari.js`, non in una tabella. La cella si rende con uno slot `#body` — nota FE-1 in §7 |
| `sensibile = f` su `conto_iban` (676), primo IBAN a entrare in una lista | ✅ Resta `f`, e non per inerzia: `sensibile = t` è il modello **allow-list**, e **non esiste nessun seed di `ui.lista_colonna_permesso`** (guardato: la cartella `80_data/sql/ui/` non ha il CSV). Il `t` renderebbe la colonna invisibile a **tutti**, in silenzio. Il perimetro sull'IBAN lo mette già `emittente_nel_perimetro()` lato BE (difetto E-4, 2026-08-28), che è il posto giusto |

---

## 7. Richieste al backend — ✅ tutte chiuse (BE-1, BE-2, FE-1, BE-3)

> ⚠️ **Stato al 2026-09-02 sera**, dopo la passata BE e la riga DB-2 del team
> DB: **BE-1, BE-2, FE-1 e BE-3 sono fatte**. BE-3 era la richiesta che il team
> DB ha aggiunto dopo DB-1, e alla **prima corsa** ha trovato un secondo caso
> della stessa specie — chiuso da DB-2 (vedi sotto).
>
> | # | Stato |
> | --- | --- |
> | **BE-1** | ✅ `SISTEMAZIONI_SORT_COLUMNS` (5 colonne) e `_ORDER_COLS_TITOLI_SOGGETTO` (4), chiavate sui campi fisici; ordinamento inoltrato repository → service → view con `qp_str`, **non** `parse_list_params` |
> | **BE-2** | ✅ `ENTI_INCASSO_SORT_COLUMNS`: chiave `centro` → `centro_descrizione`. ⭐ E il **valore** è passato a `centro_descrizione` (decisione di Tid): si ordina la colonna che si vede, non un codice invisibile |
> | **FE-1** | ✅ `SistemazioneDrawer.vue` convertito, con gli slot sul vocabolario |
> | **BE-3** | ✅ `test_chi_fornisce_lo_slot_actions_ha_la_colonna_a_catalogo`. ⭐ Alla prima corsa ha trovato **`vendite.registri_numerazione`** (lista 54): il tab forniva `#actions` con un `RowActionsMenu` e il catalogo non aveva la colonna — quel kebab **non si è mai reso**, senza errore |
> | **DB-2** | ✅ Riga `702` (`azioni`, lista 54) + `lista_preset_colonna 54/702`, arrivata sul DB il 2026-09-02: verificata **sul database vero**, non solo nel CSV. Il registro di debito che teneva verde la suite è stato **tolto**, non azzerato |



⚠️ Scritte qui e non fatte: il perimetro DB non modifica `backend/`.

| # | Dove | Cosa | Perché ora |
| --- | --- | --- | --- |
| **BE-1** | `pagamenti_repository.list_sistemazioni_fattura` e `titoli_iva_repository.list_titoli_soggetto` | Accettare `order_by`/`order_dir` con una whitelist **chiavata sui `campo_sorgente` fisici**, sul modello di `_ORDER_COLS_SFONDATI`. Chiavi attese: 61 → `destinazione`, `importo`, `stato`, `motivo`, `data_esecuzione`; 62 → `tipo_descrizione`, `emittente_ragione_sociale`, `iva_codice`, `residuo` | Le 9 colonne sono seminate `ordinabile = t` (D-1). Senza, la freccia non risponde — e non lo dice |
| **BE-2** | `pagamenti_repository.ENTI_INCASSO_SORT_COLUMNS` | La chiave `"centro"` diventa `"centro_descrizione"` (il valore resta `centro_codice`), e il commento sopra va aggiornato: il giorno è arrivato | La 678 è seminata `ordinabile = t` (D-2). Senza, quel click risponde **400** via `validate_order_params` |
| **FE-1** | `SistemazioneDrawer.vue` | Nel montaggio su `<ListaConfigurabile>`, slot `#body` sulle colonne `destinazione` e `stato`, decodificate da `pagamenti/vocabolari.js` | Senza, la cella mostra `RIPORTO` (D-6) |
| **BE-3** | `apps/core/tests/test_liste_configurabili_seed.py` | Il **verso mancante** di `test_lo_slot_delle_azioni_si_chiama_actions`: un caller che fornisce lo slot `#actions` (o `v-slot:actions`) su `<ListaConfigurabile codice="X">` pretende che X abbia una colonna `tipo_colonna = 'azione'` a catalogo | ⛔ È il difetto **DB-1**, ed era muto: senza la riga il BB non rende la colonna e non fallisce niente. Stessa forma del test 6 — il frontend come fonte di verità (§9) |

⚠️ **BE-1 e BE-2 non bloccano il seed**, bloccano la **migrazione delle view**:
finché il frontend non monta il BB su queste quattro schermate, nessuna delle due
manca a nessuno.

⭐ **E non serve che qualcuno si ricordi di questa tabella**, perché il presidio
le rende esigibili da solo. `apps/core/tests/test_liste_configurabili_seed.py`
misura il registro `_LISTE` sul **frontend** (test 6): oggi le quattro liste non
sono montate, quindi non sono nel registro e la suite è verde **a ragione**, non
per sottrazione. Il giorno in cui una di quelle view si converte, il registro la
pretende — e con lei arrivano due rossi già scritti:

| Test che diventa rosso | Lista | Richiesta |
| --- | --- | --- |
| `test_whitelist_copre_le_colonne_ordinabili` | 61, 62 | **BE-1** |
| `test_whitelist_chiavata_sul_campo_sorgente` | 60 | **BE-2** |

⇒ **Il debito è auto-esigente**, ed è il verso giusto: il lavoro BE serve nel
momento della conversione, non prima. Tracciato anche nel
[piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md), tabella dei denominatori.

---

## 8. ✅ Applicato al repository il 2026-09-02

Quattro append, nessun changeSet, nessun DDL — come previsto in §1.

| File | Righe |
| --- | --- |
| `80_data/sql/ui/lista_definizione.csv` | +4 (id 60-63) |
| `80_data/sql/ui/lista_colonna.csv` | +28 (id 673-700) |
| `80_data/sql/ui/lista_preset.csv` | +4 (id 60-63) |
| `80_data/sql/ui/lista_preset_colonna.csv` | +28 |

Verifiche eseguite **prima** dell'apply, tutte verdi:

* `git diff --numstat` → `4 0` / `28 0` / `4 0` / `28 0`: **nessuna riga
  preesistente riformattata**. ⭐ Non è cerimoniale — un writer CSV che riscrive
  il file ri-quota righe altrui, e su un mirror `runOnChange` quelle righe
  tornano al database insieme alle nuove;
* `grep -c $'\r'` → `0` su tutti e quattro: nessun CRLF piantato dall'append;
* arità (9/24/13/5), unicità delle PK, `uq(lista_id, codice)` su colonne e
  preset, lunghezze `VARCHAR`, valori degli `ENUM` (`tipo_dato`, `tipo_colonna`,
  `allineamento`), `NOT NULL` non vuoti;
* `CHECK chk_ui_lista_colonna_azione_non_esportabile` sulle due righe `azione`
  (680, 686) e `chk_ui_lista_preset_ambito_refs` sui quattro preset `sistema`;
* i tre invarianti che i pgTAP presidiano:
  `test-liste-preset-default-v1` §2 (esattamente **un** preset sistema/default
  per lista), §3 (ogni colonna di preset appartiene alla **stessa** lista) e §5
  (preset == catalogo → **banner DEF-2 spento** alla nascita);
* i **28 `campo_sorgente`** confrontati uno per uno con i payload BE reali
  (`_ENTE_INCASSO_SELECT`, `_TITOLO_COLS`, la `SELECT` delle sistemazioni,
  `_ORDER_COLS_SFONDATI`): esistono tutti.

⛔ **Perché quest'ultima riga conta più delle altre.** Il guard
`trgfn_ui_lista_colonna_a10_valida_campo_sorgente` esce senza validare quando
`vista_sql IS NULL` — ed è il caso di **tutte e quattro** le liste, che sono
servite da endpoint e non da una view. Il database non guarderà nemmeno un
`campo_sorgente` di questo lotto: un refuso qui non è un errore, è una **colonna
vuota che non si lamenta**. È l'unico controllo, ed è stato fatto a mano.

🔴 **Resta da fare al migrate** (non eseguito qui — nessuna migrazione si applica
senza richiesta esplicita): la verifica prescritta da
[linee-guida-sql §11.2](../../linee-guida-sql.md) — caricare i CSV in una temp
table e **rifare l'upsert su TUTTE le righe** dentro una transazione annullata.
⚠️ Non è una formalità su questi quattro file: sono mirror `runOnChange` +
`validCheckSums: ANY`, quindi l'append fa ri-scrivere al database anche le 671
righe che c'erano già.

⭐ **Due cose emerse eseguendo BE-1**, e nessuna delle due era nella richiesta:

* **`residuo` (lista 62) si ordina per ALIAS, non per espressione riscritta.**
  È un `CASE WHEN plafond IS NOT NULL THEN plafond - imponibile_utilizzato END`,
  quindi **NULL** sui tipi senza tetto. La mia prima stesura aveva
  `(t.plafond - t.imponibile_utilizzato)` nella whitelist: avrebbe dato un numero
  anche dove il residuo non significa niente, e l'elenco si sarebbe ordinato
  **diversamente da come si legge**. PostgreSQL ammette l'alias in `ORDER BY`.
* **Il default di `list_titoli_soggetto` è stato PRESERVATO**
  (`COALESCE(valido_al,'infinity') DESC`), perché quel metodo ha un **secondo
  consumatore**: `soggetti_service` lo incorpora nel dettaglio di un soggetto e
  non passa ordinamento. Cambiargli il default sotto i piedi avrebbe riordinato
  una sezione che nessuno stava toccando.

**Verifica**: le 9 colonne seminate `ordinabile = t` sulle liste 61 e 62, per 3
direzioni ciascuna, eseguite **contro il database vero**. Più un presidio
temporaneo, `apps/core/tests/test_liste_lotto2_whitelist_ponte.py`, che lega
seed e whitelist finché il registro `_LISTE` non copre queste liste — ⛔ **da
cancellare** quel giorno, e la ragione è scritta nel file.

---

### Stato di sviluppo tracciato altrove

⚠️ Il conteggio delle liste **non vive in questo brief**: vive nel
[piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md), tabella dei denominatori.
Aggiornato il 2026-09-02 con la colonna «02-09 notte»:

| Misura | prima | dopo |
| --- | --- | --- |
| codici seedati (`ui.lista_definizione`) | 59 | **63** |
| righe nel registro `_LISTE` | 59 | **63** ✅ — rientrata a fine giornata |
| file del Gruppo A convertiti | 35 / 39 | 35 / 39 — invariato |
| file con `DataTable` grezza | 53 | **49** |

⭐ **Le due righe di mezzo raccontano due momenti diversi, ed è giusto così.** Il
seed è arrivato **prima** dei suoi consumer: nel momento in cui questo brief è
stato scritto le conversioni erano ferme, e un brief di seed che avesse fatto
salire il contatore delle conversioni starebbe misurando la cosa sbagliata. Sono
salite dopo, nella stessa giornata, ed è per questo che la colonna «dopo» oggi
legge `63` e `49`.

✅ **Il brief passa a `work-done/`** (2026-09-02): il DB è chiuso, §7 non ha più
richieste aperte (BE-1, BE-2, FE-1, BE-3 tutte fatte), la divergenza `63 = 63` è
rientrata e le quattro view sono convertite. L'ultimo pezzo — la 61 portata a
lista paginata — è §10.

---

## 9. ✅ DB-1 — la colonna `azioni` mancante alla lista 62 (2026-09-02)

Richiesta **BE → DB**, arrivata convertendo le view del lotto. Evasa: due righe
appese, nessun changeSet, nessun DDL.

### La premessa, ri-verificata qui e non presa per buona

| Cosa dice la richiesta | Verificato |
| --- | --- |
| La lista 62 non ha una colonna `azioni` | ✅ a catalogo aveva 687-692, sei colonne, nessuna `azione` |
| Il consumer ha un elimina per riga | ✅ [`TitoliIvaSoggettoDrawer.vue:169`](../../../../frontend/src/anagrafiche/components/TitoliIvaSoggettoDrawer.vue) — `<Column v-if="!isReadonly" style="width: 4rem">` con dentro un `Button` `MANAGE_ICONS.DELETE` |
| Il generatore non l'ha vista perché la `<Column>` non ha `header` | ✅ quella `<Column>` non ha `:header`, e `gen_seed_lista.py` riconosce le azioni dall'etichetta |

⭐ **Limite dichiarato del generatore, non un suo difetto**: una colonna senza
intestazione non è distinguibile, dal solo template, da un dettaglio di layout.

### Le righe

`lista_colonna.csv` — **identica** alle due azioni già seedate (680 sulla 60,
686 sulla 61) salvo `id` e `lista_id`, quindi `esportabile = f` e il
`CHECK chk_ui_lista_colonna_azione_non_esportabile` è rispettato:

```csv
701,62,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
```

`lista_preset_colonna.csv`:

```csv
62,701,999,t,f
```

⚠️ **Inserita nel gruppo `62`, non in coda al file.** `lista_preset_colonna.csv`
è raggruppato per `preset_id` e appenderla dopo le righe della 63 avrebbe rotto
l'ordine per una riga sola. L'inserimento tiene tutte le altre righe **byte per
byte** (`splitlines`/`writelines`): `git diff --numstat` dà `1 0`, che è la prova
che nessuna riga di qualcun altro è stata riformattata.

⭐ **La riga nel preset non è facoltativa**: omessa, la colonna resterebbe a
catalogo *fuori* dal preset e accenderebbe il banner DEF-2 «ci sono colonne
nuove» su una lista che non ne ha — la stessa regola di §2 sulla lista 63.

### ⛔ Il difetto era muto, e il presidio guarda dall'altra parte

`test_lo_slot_delle_azioni_si_chiama_actions` verifica **config dichiara ⇒ il
caller fornisce lo slot**. Il verso mancante è l'altro: **il caller ha un'azione
per riga ⇒ la config deve dichiararla**. Senza la riga a catalogo,
`<ListaConfigurabile>` semplicemente non rende la colonna: il cestino sparisce,
nessun errore, nessun test rosso, e l'operatore perde un verbo senza che niente
lo dica.

⚠️ È la stessa famiglia dei difetti che questo repo paga più cari — quelli che
non danno errore — e qui il seed **è** il contratto: la config non descrive la
schermata, la decide.
⇒ Richiesta **BE-3** in §7 — ✅ fatta, e il primo caso che ha trovato (lista 54) è chiuso da **DB-2**.

### Stato delle conversioni — cosa risulta in questo tree

⚠️ La richiesta dichiara le altre tre convertite, contatore `DataTable` grezza
53 → 50, suite 4379 verde ed e2e 61 verdi. **Qui non risulta ancora**, e lo
scrivo come fatto datato e non come dubbio: al 2026-09-02, su `dev/db-tid`
(`2120ed21e`), il contatore è **53** e tutte e quattro le view importano ancora
`primevue/datatable` — due delle tre citano già `<ListaConfigurabile>`, quindi il
lavoro è in corso e non pubblicato qui.

⇒ **I contatori del [piano](../work-in-progress/piano-migrazione-primevue-5.md) NON sono stati
aggiornati a 50**: si aggiornano quando la misura si può rifare, non su
dichiarazione. Restano `53` e `35 / 39`, e la divergenza `_LISTE` resta a 4.

⭐ **Nota che «suite 4379 OK» implica che BE-1 e BE-2 siano già stati fatti**:
con le liste 60/61/63 entrate in `_LISTE` e le whitelist vecchie,
`test_whitelist_copre_le_colonne_ordinabili` sarebbe rosso. Se è verde, il debito
di §7 è chiuso lato BE — da confermare quando quel ramo arriva.

---

## 10. ✅ La 61 portata sullo standard — l'ultimo pezzo (2026-09-02)

`pagamenti.sistemazioni_fattura` era stata convertita **con `:paginata="false"`**,
e la ragione scritta era: *«gli atti di UNA fattura sono pochi per modello»*.

⛔ **Quella ragione è una previsione sui DATI, e una previsione sui dati non
decide la forma di una lista** — è la regola zero. Il prezzo non si vedeva ed era
concreto: il drawer restava senza pagine, senza «Personalizza colonne» e senza
export, cioè fuori dallo standard delle altre quaranta liste, **senza che niente
lo dicesse**. Decisione di Tid: sullo standard, come la 62.

| Dove | Cosa |
| --- | --- |
| `pagamenti_repository.list_sistemazioni_fattura` | `(righe, totale)` in **una** valutazione (`COUNT(*) OVER()` via `fetch_paged_with_total`), `limit`/`offset` opzionali, `fallback_count_sql` per il rientro su pagina stantia; `FROM`+`WHERE` in `_SISTEMAZIONI_FROM_WHERE`, condiviso fra pagina e ripiego |
| idem | ⛔ **`count_sistemazioni_fattura` RIMOSSA**: era una seconda query sullo stesso predicato, e due valutazioni possono non concordare — fra l'una e l'altra qualcuno registra un atto e la lista direbbe «3 di 4» avendone in mano 3 su 3. Stessa mossa già fatta su `count_titoli_soggetto` con la 62 |
| `sistemazioni_service` / `api/views.py` | `limit`/`offset` da `parse_list_params`; ⛔ `order_by`/`order_dir` **grezzi** con `qp_str` — quel bundle normalizza l'assenza di `order_dir` ad `"asc"`, quindi il default del repository non verrebbe **mai** raggiunto |
| `api/views.py` + `urls_v1.py` | nuova `ApiFatturaSistemazioniExport` su `fatture/<id>/sistemazioni/export/`, stesso `lista_codice` della lista a video |
| `stores/sistemazioniFattura.js` (nuovo) | store Pinia `userScoped`, contratto `useSearchTable`, padre `fatturaId` |
| `SistemazioneDrawer.vue` | `useDrawerTabLista` + `<DrawerTabLista>`; spariscono i tre `ref` locali e la fetch a mano |

⭐ **Il terzo caso è sopravvissuto alla conversione, ed è la parte che si sarebbe
persa senza guardarla.** Il drawer distingueva **tre** stati — atti presenti ·
nessun atto · **non letti** — e il BB della lista non può distinguere gli ultimi
due: a lista vuota mostrerebbe lo stesso empty-state. ⇒ lo store tiene
`erroreCaricamento`, il messaggio di errore resta sopra la lista, e la frase del
dominio («su questo documento non ha ancora deciso nessuno») è passata allo slot
`#empty`. Perdere quella distinzione non avrebbe rotto niente: avrebbe solo
detto «non ce ne sono» dove la verità era «non lo so».

⭐ **E il ponte del lotto 2 è sparito con lei.**
`apps/core/tests/test_liste_lotto2_whitelist_ponte.py` esisteva per coprire ciò
che i test 1-3 non raggiungevano — le liste dichiarate `ORDINAMENTO_LOCALE`, che
una whitelist non la devono avere. La 61 era l'ultima riga rimasta: uscita dalla
sentinella, il ponte non copriva più niente ed è stato **cancellato**, come il
suo stesso commento prescriveva. ⛔ Due presidi sullo stesso invariante divergono
al primo che qualcuno aggiorna.

**Verifiche eseguite**: suite backend completa **4367 test OK**;
`test_lista_proiezione_campo_sorgente` con `ZEROERP_TEST_DB_E2E=1` verde **contro
il database vero** (le 5 colonne della 61 × 2 versi producono SQL che parte);
`eslint` e `vite build` puliti; i tre guard FE (`check-liste-configurabili`,
`check-pinia-user-scoped-reset`, `check-drawer-width`) verdi.
⚠️ **Il database di dev non ha atti di sistemazione**: la prova dice che le query
si pianificano e che le colonne ci sono, **non** che l'ordinamento sia quello
giusto. Quello si vedrà al primo caso reale, ed è scritto qui perché nessuno lo
scambi per una verifica di comportamento.
