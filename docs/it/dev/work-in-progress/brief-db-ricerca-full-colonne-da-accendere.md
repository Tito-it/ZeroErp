# Brief DB — Accendere a catalogo le colonne in cui le liste già cercano

> **Destinatari:** team DB (`dev/db-tid`). Richiesta del BE, 2026-09-23.
>
> **Da leggere per primo: §1 (perché) e §3 (le righe da cambiare).**
>
> **Stato 2026-09-23:** ⏳ da fare. Le decisioni di Tid di §4 sono tutte chiuse
> e riportate in §3.1-§3.5. §3.5 è una modifica di modello (colonna nuova),
> non solo seed.

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

Nessun pgTAP nuovo: sono righe di seed. Dopo il merge, il BE converte le
liste, e il presidio `test_ricerca_full_seed` le troverà scoperte finché non
lo fa. È il segnale voluto.
