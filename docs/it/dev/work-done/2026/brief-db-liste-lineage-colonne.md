# Brief DB — Colonne lineage sulle 5 liste documento (`vw_*_lista` + seed `ui`)

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-15 · **Owner**: Tid
> **Stato**: ✅ **ESEGUITO** (2026-07-15) — viste `vw_*_lista` estese, seed
> `ui.lista_colonna` E preset default (§7) applicati; pushato su `dev/db-tid`
> (`10e8f22ee` + `9a2f59d0a`, PR #988/#989 → Tito-dev). Verificato:
> `fn_resolve_lista_config` ritorna `pratica/fase/transito` `visibile=true`
> sulle 5 liste; validato in-app da Tid (ordini + ddt).
> **Design-of-record**: [brief-design-genealogia-transiti-vendite.md](brief-design-genealogia-transiti-vendite.md)
> **Prerequisito consegnato**: [brief-db-lineage-documenti-vendite.md](brief-db-lineage-documenti-vendite.md)
> — ✅ COMPLETO 2026-07-15 (`vw_documento_lineage_nodi/archi`, `vw_documento_lineage`,
> `fn_documento_lineage`, seed `fase`/`is_abortito`, `RESO_VENDITA(15)`; verificato vivo sul DB dev).
> **Gate downstream**: questo brief sblocca la **Fase B** di
> [brief-be-fe-lineage-documenti-vendite.md](brief-be-fe-lineage-documenti-vendite.md)
> (colonne in lista). La Fase A (pannello "Passaggi") NON dipende da questo brief.

---

## 1. Scopo

Portare nelle **5 liste documento configurabili** (preventivi, offerte, ordini,
contratti, DDT — decisione §0 del brief lineage: 5 liste, non 4) le tre
informazioni di genealogia: **pratica** (numero cliccabile), **fase** propria e
**frontiera** (documento più prossimo in esecuzione).

Le liste leggono dalle viste canoniche `vendite.vw_<entità>_lista` e le colonne
configurabili sono governate da `ui.lista_definizione`/`ui.lista_colonna`
(trigger B2 valida `campo_sorgente` contro la `vista_sql`): l'estensione è quindi
**materia DB** (viste + seed), come già fatto per le code resi
([brief-db-seed-lista-code-resi.md](brief-db-seed-lista-code-resi.md)).

## 2. Estensione delle 5 viste `vw_*_lista`

Tutte e 5 le viste espongono già `id`, `uid`, `stato_codice_interno` (verificato):
le chiavi di join ci sono. Per ciascuna vista aggiungere:

### 2a. `fase` — dalla join stati già presente (NON dalla lineage)

Le viste joinano già il proprio catalogo `config.stati_doc_*` per
`stato_codice`/`stato_descrizione`: esporre anche `s.fase` (colonna ora presente
ovunque dopo il seed del brief lineage). Costo zero, nessuna dipendenza dalla
vista lineage.

### 2b. Colonne dalla summary — `LEFT JOIN vendite.vw_documento_lineage l`

Chiave nodo **nativa polimorfa** (convenzione `config.manual/sorgenti.md`
§"Convenzione chiave sorgente"):

| Vista | Join |
| --- | --- |
| `vw_preventivi_lista`, `vw_offerte_commerciali_lista` | `l.uid = v.uid::text` |
| `vw_ordini_lista`, `vw_contratti_lista`, `vw_ddt_lista` | `l.uid = v.id::text` |

`l.tipo_id` risolto per JOIN a `config.sorgenti` su `codice_interno` (mai id
letterale). Colonne da esporre (prefisso per evitare collisioni):

- `pratica_id`, `pratica_numero`, `n_pratiche`
- `frontiera_tipo_id`, `frontiera_codice`, `frontiera_stato_codice_interno`, `frontiera_fase`
- `n_discendenti_attivi`, `is_transitato`

> ⚠️ **`security_invoker=on` va ri-specificato** nel `CREATE OR REPLACE VIEW`
> (reloption azzerata altrimenti) — nuove migration `20_code/vendite` con
> numerazione successiva, mai edit degli YAML mergiati.

## 3. Seed `ui.lista_colonna` (liste 4–8)

Per ciascuna delle 5 liste (`lista_id` 4=contratti, 5=preventivi, 6=offerte,
7=ordini, 8=ddt) seedare 3 colonne `tipo_colonna='informazione'`:

| codice | campo_sorgente | etichetta | note |
| --- | --- | --- | --- |
| `pratica` | `pratica_numero` | Pratica | ordinabile; il FE la rende cliccabile (slot) |
| `fase` | `fase` | Fase | ordinabile; render Tag `faseDocumentoSeverity` (slot) |
| `transito` | `frontiera_codice` | Transito | NON ordinabile; render chip frontiera (slot FE legge anche `frontiera_*`/`n_discendenti_attivi` della riga) |

Visibilità default: **visibili su tutte e 5 le liste, DDT inclusa** (deciso Tid
2026-07-15: si valuta l'effetto in-app, eventualmente si spengono dopo — il
ritiro responsive FE gestisce comunque l'overflow). Aggiungere
`etichetta_i18n_key` (`lista.col_pratica`, `lista.col_fase`, `lista.col_transito`)
come per le colonne esistenti.

> ⚠️ **RETTIFICA (2026-07-15, superava la frase originale «nessun intervento sui
> preset»).** Il solo seed in `ui.lista_colonna` **NON** rende le colonne visibili:
> `fn_resolve_lista_config` le tratta come **colonne_nuove** → `visibile=false`
> (opt-in dalla modale). Verificato: config risolta di `vendite.preventivi` ritorna
> `pratica/fase/transito` con `visibile=false`. Per ottenere il **visibile di
> default** richiesto, seedare anche le 3 colonne nel **preset di default** di
> ciascuna lista (`ui.lista_preset_colonna`, `preset_id` = `*_default`, es.
> `preventivi_default`) con `visibile=true` + `ordine` in coda + `fissata=false`.
> Vedi §7.

## 4. Prestazioni (nota per il team)

`vw_documento_lineage` esegue il walk ricorsivo sull'**intero grafo** a ogni
query (il predicato non entra nella CTE ricorsiva): il LEFT JOIN nelle liste ne
paga il costo per pagina. Con i volumi attuali è fine; se in futuro pesa, le
opzioni sono (a) variante LATERAL/funzione per-nodo, (b) materializzazione.
Nessuna azione ora — solo consapevolezza.

## 5. Test

- **pgTAP**: presenza nuove colonne sulle 5 viste; `security_invoker=on`
  preservato; casi reali (contesto operatore GUC):
  `PRV0000185` → `pratica_numero='PRA-0000818'`, `frontiera_codice='DDT0000031'`
  (frontiera oltre l'ordine, via arco H), `fase='CHIUSO'`;
  documento senza pratica → `pratica_numero IS NULL`, `n_pratiche=0`.
- Seed: 15 righe `lista_colonna` risolte da `fn_resolve_lista_config` per le 5
  liste (colonne nuove presenti nel catalogo).

## 6. Fuori perimetro

- Lista **commesse** (genealogia inversa, G-11): follow-on FE-c, non ha lista
  configurabile `ui` — verrà trattata nel suo brief quando si affronta.
- Liste **resi/code resi**: il reso mostra già la sua origine (DDT); nessuna
  colonna lineage in questa iterazione.
- Arco reso → nota di credito (rimborso contabile): futuro, stesso meccanismo
  archi (§0 brief lineage).

## 7. FOLLOW-UP DB — visibilità di default (richiesto, MANCANTE nel primo seed)

> Stato 2026-07-15: il seed `ui.lista_colonna` (§3) **è applicato** sul DB di
> test; BE/FE Fase B sono **completi e funzionanti** (le 3 colonne compaiono
> nella modale "Personalizza colonne" e si renderizzano correttamente quando
> attivate). **Manca** però la parte che le rende **visibili di default**: vanno
> aggiunte al **preset di default** di ciascuna lista.

Per ciascuna delle 5 liste, INSERT in `ui.lista_preset_colonna` sul preset di
default (`ui.lista_preset` con `is_default=true` / codice `*_default`) le 3
colonne, con `visibile=true`:

| campo | valore |
| --- | --- |
| `preset_id` | id del preset default della lista (es. `preventivi_default`=5, + gli analoghi contratti/offerte/ordini/ddt) |
| `colonna_id` | id delle righe `ui.lista_colonna` `pratica`/`fase`/`transito` della stessa lista |
| `ordine` | in coda alle colonne visibili del preset (o dove Tid preferisce; suggerito: dopo `stato`) |
| `larghezza` | NULL (auto) o larghezza_default del catalogo |
| `visibile` | **true** |
| `fissata` | false |

Verifica: `ui.fn_resolve_lista_config('vendite.preventivi', NULL, NULL)` deve
tornare `pratica/fase/transito` con `visibile=true` (oggi tornano `false`).
Ripetere per le 5 liste. Nessun impatto sulle **preferenze utente** già salvate
(chi ha personalizzato mantiene la sua scelta; il default cambia solo per chi non
ha preferenza). Additivo, `[[feedback_db_actions_passaggio_team]]`.
