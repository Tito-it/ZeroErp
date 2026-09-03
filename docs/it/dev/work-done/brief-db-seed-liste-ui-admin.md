# Brief team DB — seed delle 4 liste della pagina tecnica `ui`

> Destinatario: team DB (`dev/db-tid`) · Origine: `dev/backend-tid` · 2026-09-02
> **Richiesta unica** per quattro liste.
> Dimensione: **quattro append a CSV, nessun changeset nuovo, nessun DDL.**
>
> ✅ **CHIUSO il 2026-09-02.** Seed applicato dal team DB e mergiato su
> `Tito-dev` (`997c847d5`, PR #1468). **64 righe su 64 atterrate identiche alla
> specifica** — verificato meccanicamente confrontando i blocchi `csv` di questo
> documento con `origin/Tito-dev`, non dato per buono. Le quattro liste
> risolvono 6 / 9 / 8 / 5 colonne da `ui.fn_resolve_lista_config`, con un
> identificatore e una azione ciascuna. Esito e note di ritorno in §6.

## 1. Scopo

Seedare la configurazione delle quattro liste della pagina tecnica
*Personalizzazioni Liste* (`/amm-software/personalizzazioni-liste-tecniche`), che
sono il **primo lotto** della modalità non paginata di `<ListaConfigurabile>`
introdotta il 2026-09-02
([piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md) §8-bis).

| `lista_id` | codice | consumer FE (oggi `DataTable` grezza) | col. |
| --- | --- | --- | --- |
| 56 | `ui.lista_definizione` | `ui/components/ListaDefinizionePanel.vue` | 6 |
| 57 | `ui.lista_colonna` | `ui/components/ListaColonnaPanel.vue` | 9 |
| 58 | `ui.lista_preset` | `ui/components/ListaPresetPanel.vue` | 8 |
| 59 | `ui.lista_colonna_permesso` | `ui/components/ListaColonnaPermessoPanel.vue` | 5 |

Sono quattro liste **non paginate**: la popolazione è limitata per modello (una
riga per lista configurata, per colonna di quella lista, per preset, per
permesso), non «poche per adesso».

⛔ **Nessun DDL, nessuna funzione, nessun trigger.** I quattro loader sono
`runOnChange: true` + `validCheckSums: ANY` + `loadUpdateData`, cioè mirror vivi
dei CSV: **appendere le righe basta** (`20260507-06/07/08/09`).

⚠️ **`ui/components/ListaPresetColonneDrawer.vue` NON è in questo lotto**: è la
composizione di un preset, cioè le sue **righe**, quindi Gruppo B per il criterio
in tre domande del piano. Non gli serve un codice di lista.

## 2. Le righe

Generate con `scripts/gen_seed_lista.py` (che stampa e non applica nulla), con le
correzioni a mano elencate in §3. Id allocati oltre il massimo corrente
(`lista_definizione` 55, `lista_colonna` 644, `lista_preset` 55).

### `80_data/sql/ui/lista_definizione.csv`

```csv
56,ui.lista_definizione,Definizioni di lista,ui,NULL,t,2026-09-02 00:00:00,mctit,f
57,ui.lista_colonna,Catalogo colonne di lista,ui,NULL,t,2026-09-02 00:00:00,mctit,f
58,ui.lista_preset,Preset di colonne,ui,NULL,t,2026-09-02 00:00:00,mctit,f
59,ui.lista_colonna_permesso,Permessi di colonna,ui,NULL,t,2026-09-02 00:00:00,mctit,f
```

⚠️ `vista_sql` è `NULL` su tutte e quattro **di proposito**: le righe arrivano dai
service admin di `apps/ui`, non da una vista. Stesso caso delle due matrici del
lotto 2026-07-31 (`config.utilities_tipi_ruolo`,
`config.tipi_ruolo_tipi_indirizzo`) — lì il guard
`trgfn_ui_lista_colonna_a10_valida_campo_sorgente` non valida i campi, ed è
corretto così.

### `80_data/sql/ui/lista_colonna.csv`

```csv
645,56,codice,Codice,,codice,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.definizione_codice,100
646,56,descrizione,Descrizione,,descrizione,informazione,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.definizione_descrizione,90
647,56,schema_dati,Schema dati,,schema_dati,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.definizione_schema_dati,60
648,56,vista_sql,Vista SQL,,vista_sql,informazione,string,,,40,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.definizione_vista_sql,50
649,56,attivo,Attivo,,attivo,informazione,boolean,,,50,center,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,common.col_attivo,70
650,56,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
651,57,ordine_default,Ordine,,ordine_default,informazione,numeric,,80,10,right,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_ordine,80
652,57,codice,Codice,,codice,identificatore,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_codice,100
653,57,etichetta,Etichetta,,etichetta,informazione,string,,,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_etichetta,90
654,57,tipo_colonna,Tipo colonna,,tipo_colonna,informazione,string,,,40,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_tipo_colonna,70
655,57,tipo_dato,Tipo dato,,tipo_dato,informazione,string,,,50,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_tipo_dato,60
656,57,campo_sorgente,Campo sorgente,,campo_sorgente,informazione,string,,,60,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_campo_sorgente,60
657,57,gruppo,Gruppo,,gruppo,informazione,string,,,70,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.colonna_gruppo,40
658,57,attivo,Attivo,,attivo,informazione,boolean,,,80,center,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,common.col_attivo,70
659,57,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
660,58,codice,Codice,,codice,identificatore,string,,180,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_codice,100
661,58,descrizione,Descrizione,,descrizione,informazione,string,,,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_descrizione,90
662,58,ambito,Ambito,,ambito,informazione,string,,160,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_ambito,80
663,58,preset_riferimento,Riferimento,Profilo o emittente a cui il preset si applica,,informazione,string,,220,40,left,,,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_riferimento,60
664,58,colonne_count,Colonne,,colonne_count,informazione,numeric,,100,50,right,,,f,f,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_colonne_count,50
665,58,is_default,Default,,is_default,informazione,boolean,,90,60,center,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.preset_default,70
666,58,attivo,Attivo,,attivo,informazione,boolean,,90,70,center,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,common.col_attivo,70
667,58,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
668,59,colonna_etichetta,Colonna,,colonna_etichetta,identificatore,string,,,10,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.permesso_colonna,100
669,59,colonna_codice,Codice colonna,,colonna_codice,informazione,string,,220,20,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.permesso_colonna_codice,80
670,59,profilo_accesso,Profilo accesso,,profilo_accesso_codice,informazione,string,,240,30,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.permesso_profilo,90
671,59,livello_accesso,Livello,,livello_accesso,informazione,string,,140,40,left,,,t,t,t,f,f,t,2026-09-02 00:00:00,mctit,ui.admin.permesso_livello_accesso,70
672,59,azioni,Azioni,,,azione,string,,70,999,center,,99,f,f,f,f,f,t,2026-09-02 00:00:00,mctit,common.col_azioni,50
```

### `80_data/sql/ui/lista_preset.csv`

```csv
56,56,lista_definizione_default,Vista standard definizioni di lista,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
57,57,lista_colonna_default,Vista standard catalogo colonne,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
58,58,lista_preset_default,Vista standard preset,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
59,59,lista_colonna_permesso_default,Vista standard permessi colonna,sistema,,,t,,,t,2026-09-02 00:00:00,mctit
```

### `80_data/sql/ui/lista_preset_colonna.csv`

```csv
56,645,10,t,t
56,646,20,t,f
56,647,30,t,f
56,648,40,t,f
56,649,50,t,f
56,650,999,t,f
57,651,10,t,f
57,652,20,t,f
57,653,30,t,f
57,654,40,t,f
57,655,50,t,f
57,656,60,t,f
57,657,70,t,f
57,658,80,t,f
57,659,999,t,f
58,660,10,t,t
58,661,20,t,f
58,662,30,t,f
58,663,40,t,f
58,664,50,t,f
58,665,60,t,f
58,666,70,t,f
58,667,999,t,f
59,668,10,t,t
59,669,20,t,f
59,670,30,t,f
59,671,40,t,f
59,672,999,t,f
```

## 3. Le correzioni applicate all'output del generatore

Lo script produce righe **strutturalmente corrette e semanticamente una bozza**;
queste sono le decisioni prese, elencate perché siano rivedibili e non subite.

| # | Cosa | Perché |
| --- | --- | --- |
| 1 | `attivo` (liste 56, 57) e `is_default` (58): da «calcolata FE» a **campo sorgente vero**, `t/t/t` | Lo script le marca calcolate perché nel `.vue` la `<Column>` non ha `field=`. È una deduzione sbagliata: la colonna è solo **renderizzata** da uno slot (`<AttivoTag>`, `<i class="pi-check">`), il campo esiste nel payload |
| 2 | `preset_colonne_count` → codice `colonne_count`, `preset_default` → `is_default`, `permesso_livello_accesso` → `livello_accesso` | Stessa cosa: il body rende `data.colonne_count` / `data.is_default` / `data.livello_accesso`. I nomi logici seguono il campo invece di ripetere il nome della lista |
| 3 | `pagina_dimensione` **vuota**, non 25 | Liste non paginate: un preset che dichiara una dimensione mai applicata è una dichiarazione falsa. Meglio non dichiararla |
| 4 | `ordinamento_default` **vuoto** su tutti e quattro i preset | Le righe arrivano già ordinate dal BE (`ORDER BY attivo DESC, codice, id` e gemelli). Dichiarare un ordinamento farebbe **ri-ordinare in locale** a PrimeVue con semantica diversa dalla sua — vedi §5 |
| 5 | `identificatore` su `codice` (lista 57), **non** sulla prima colonna a video | Lo script lo mette in prima posizione per convenzione; lì la prima è `ordine_default`. L'identificatore è ciò che l'operatore non può nascondere, e nascondere il codice di una colonna sarebbe assurdo. L'ordine a video resta **identico a oggi** |
| 6 | `tipo_dato = string` confermato su `tipo_colonna`, `tipo_dato`, `ambito`, `livello_accesso` | Lo script li segnalava «non trovati in nessuna tabella»: sono `USER-DEFINED` (enum PG), che nel vocabolario di `ui.tipo_dato` mappano su `string`. Verificato sulla doc auto-gen, non dedotto |
| 7 | `preset_riferimento` resta **calcolata**, `campo_sorgente` vuoto | Qui la deduzione dello script è giusta: il body sceglie fra `profilo_accesso_codice` e `emittente_fiscale_codice`. Due sorgenti, nessuna singola |
| 8 | `priorita` valorizzata (100/90/80…) invece del default 50 | È l'ordine di ritiro responsive. Le colonne di identità e stato tengono, quelle accessorie (`vista_sql`, `gruppo`) cedono per prime. Decisione di presentazione: rivedibile |

⚠️ Le 23 chiavi `etichetta_i18n_key` referenziate **esistono già** in `it.json` e
`en.json` (verificato il 2026-09-02): nessuna chiave nuova da creare.

## 4. Verifica dopo l'applicazione

```sql
-- 4 righe
SELECT id, codice, schema_dati, vista_sql, attivo
  FROM ui.lista_definizione WHERE id BETWEEN 56 AND 59 ORDER BY id;

-- 28 righe (6 + 9 + 8 + 5)
SELECT lista_id, count(*) FROM ui.lista_colonna
 WHERE lista_id BETWEEN 56 AND 59 GROUP BY lista_id ORDER BY lista_id;

-- un solo identificatore per lista, e nessuna colonna `azione` ordinabile
SELECT lista_id, tipo_colonna, count(*) FROM ui.lista_colonna
 WHERE lista_id BETWEEN 56 AND 59 GROUP BY 1,2 ORDER BY 1,2;
```

## 5. Cosa NON serve a voi, ma va saputo

**Il building block FE è già landed e non dipende da questo seed per non
rompersi**: la prop `paginata` di `<ListaConfigurabile>` è `true` di default,
quindi le 55 liste esistenti sono invariate (verificato: nessun consumer passa la
prop).

**Il prerequisito BE è fatto** (2026-09-02, nessun impatto DB): i quattro endpoint
admin rispondono ora `{results, count}`, dove `count` viene da una query
`count(*)` **sua** e non da `len(results)`. Serve al guard anti-troncamento del
building block: un conteggio derivato dalle righe non può dire niente *sulle*
righe.

⚠️ **Nota che vi riguarda.** Tre dei quattro conteggi sono **filtrati per
`lista_id`**, come le rispettive liste. Se un domani queste tabelle prendessero
RLS o un filtro di perimetro, `count(*)` e la SELECT della lista devono vederlo
**entrambi**: se divergono per un motivo che non è un troncamento, il guard
accende un falso allarme e la lista non si disegna.

⚠️ **Ordinamento locale, non del database.** Su queste quattro liste l'ordine dei
click sull'intestazione lo calcola PrimeVue nel browser, sulle righe già
consegnate: su NULL, accenti e numeri-come-testo può differire da `ORDER BY`. Per
queste quattro non è informazione (stringhe ed enum), ma è il motivo per cui
`ordinamento_default` resta vuoto — vedi correzione 4.

## 6. Esito e note di ritorno dal team DB (2026-09-02)

Il team DB ha **ri-verificato** ogni affermazione di questo brief invece di
darla per buona — id liberi, 24 campi per riga, enum a catalogo, CHECK
«azione ⇒ non esportabile», `pagina_dimensione` vuota ammessa (colonna
nullable), `ambito = sistema` con riferimenti vuoti conforme al CHECK — più un
caricamento di prova in transazione annullata attraverso i guard reali.

⭐ **Un dettaglio che avremmo sbagliato senza di loro**: `vista_sql = NULL`
funziona perché *quel* loader dichiara `nullValue: "NULL"`; gli altri tre
dichiarano `""`. Il token letterale non è intercambiabile fra i quattro CSV.

### Nota 1 — `fissata` sull'identificatore è **inerte**

Nel seed sta a `t` sulle liste 56/58/59 e a `f` sulla 57 (dove l'identificatore
non è la prima riga). **Non cambia niente**: `fn_resolve_lista_config` normalizza
con `CASE WHEN tipo_colonna = 'identificatore' THEN TRUE`. Un identificatore è
sempre fissato e visibile.

⛔ È scritto qui perché **nessuno la "corregga" più avanti** credendo di sistemare
un'incoerenza: non c'è niente da sistemare, e un allineamento cosmetico su un
CSV di seed è un changeset che non serve a nessuno.

### 🔴 Nota 2 — con `vista_sql = NULL` il legame catalogo ↔ payload NON ha presidio

La scelta di `vista_sql = NULL` è giusta e motivata (§2), ma ha una conseguenza
che va nominata: il guard sui `campo_sorgente` **si ferma subito** quando la
lista non dichiara una vista. Quindi nessuno verifica che
`colonne_count`, `preset_riferimento`, `colonna_etichetta`, `colonna_codice`,
`profilo_accesso_codice`, `livello_accesso` esistano davvero nel payload.

⚠️ Se un endpoint ne rinomina uno **non fallisce niente**: cella vuota a video e
colonna vuota nell'export, in silenzio. È la classe di difetto più cara di questo
repo — quella che non dà errore.

⭐ **Non è un rilievo su questo lotto**: è la stessa condizione delle **altre 39
liste senza vista**. L'unico presidio possibile è lato BE — un test che confronti
i `campo_sorgente` a catalogo con le chiavi della proiezione del repository.
⇒ **Vale per tutte in una volta, e conviene farlo una volta sola.**

🔵 **Consegna aperta al team BE/FE**, tracciata nel
[piano PrimeVue 5 §Gruppo A](piano-migrazione-primevue-5.md): non appartiene più
a questo brief, che è chiuso.

### Nota 3 — operativa

⚠️ I pannelli trovano la loro configurazione **dopo il prossimo migrate**: prima
di quello la lista non si disegna.
