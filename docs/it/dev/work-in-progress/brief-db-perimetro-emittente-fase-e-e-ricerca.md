# Fase E + ricerca: tre richieste al team DB · *perimetro emittente*

> **Cos'è.** Quello che serve dal database per finire il giro **P-4** — la
> colonna emittente sulle **cinque liste** che restano — più il **residuo D-3**,
> l'emittente nella riga della ricerca universale.
>
> **Origine.** Misurato il **2026-08-18**, chiuse le fasi A→D del piano BE/FE
> ([brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md) §13-bis).
>
> **Destinatario**: team DB, branch `dev/db-tid`.
> **Autorizzazione**: Tid, 2026-08-18.
>
> ⛔ **La Fase E è ferma su queste richieste, tutta.** Non è una scelta di
> comodo: senza la riga di catalogo la colonna **non esiste** per il frontend, e
> senza la ragione sociale nella vista il backend non ha cosa selezionare. Il
> codice BE si scrive in mezz'ora quando i due pezzi ci sono; scritto prima
> sarebbe codice che seleziona una colonna inesistente.

| # | Cosa | Peso | Blocca |
| --- | --- | --- | --- |
| **R-3** | **5 righe** in `lista_colonna.csv`: la colonna emittente sulle liste che restano | append al CSV | ⛔ tutta la Fase E |
| **R-4** | `emittente_ragione_sociale` in **3 viste** (che ne servono 4 di liste) | 3 `CREATE OR REPLACE VIEW` | ⛔ 4 liste su 5 |
| **R-5** | L'emittente nella riga della **ricerca universale** | 1 funzione | 🔵 niente — è il residuo D-3 |

---

## Il quadro, misurato

| Lista | Da dove nascono le righe | id emittente | ragione sociale | serve dal DB |
| --- | --- | :---: | :---: | --- |
| **Situazione aperta — documenti** (39) | `vw_dash_fatturazione_documenti` | ✅ | ❌ | vista + catalogo |
| **Backlog — documenti fermi** (40) | *la stessa vista a monte* | ✅ | ❌ | **eredita** + catalogo |
| **Competenza — errori vivi** (41) | `vw_dash_competenza_errori` | ✅ (`l.emittente_soggetto_ruolo_id`) | ❌ | vista + catalogo |
| **Competenza — drill-down commesse** (43) | `vw_dash_competenza_attivita`, **aggregata dal BE** | ✅ (`co.emittente_soggetto_ruolo_id`) | ❌ | vista + catalogo |
| **Lotti di fatturazione** (12) | SQL diretto su `vendite.fatturazione_lotti` — **nessuna vista** | ✅ (colonna `NOT NULL`) | n/a | **solo** catalogo |

⭐ **Aperto e backlog costano una JOIN sola**: sono due proiezioni della
**stessa** vista a monte (`vw_dash_fatturazione_documenti`). È il motivo per cui
Q4 le aveva messe insieme nel 2° giro.

⭐ **Lotti non chiede niente al database oltre alla riga di catalogo**: il dato
è già sulla tabella, la JOIN a `soggetti_ruoli`/`soggetti` la fa il repository.
È il motivo per cui Q4 la metteva ultima — «non insegna niente al database».

---

## R-3 · Le cinque righe di catalogo ⛔

Append a `80_data/sql/ui/lista_colonna.csv`, **copiando la riga della pilota**
(id 478, lista 42), che è già nella forma delle sei liste documento:

```text
codice          = emittente_fiscale
etichetta       = Emittente
campo_sorgente  = emittente_ragione_sociale
tipo_colonna    = informazione
tipo_dato       = string
ordine_default  = 100
filtrabile=t  ordinabile=t  esportabile=t  ricercabile_full=f  sensibile=f  attivo=t
etichetta_i18n_key = <vedi sotto>
```

⚠️ **`etichetta_i18n_key` non è la stessa per tutte**: la radice segue la
**cartella del frontend** che monta la lista, non lo schema DB
(frontend-standards §Multilingua). Per queste cinque:

| Lista | chiave |
| --- | --- |
| `vendite.dash_aperto_documenti` | `vendite.situazione_aperta.col_emittente` |
| `vendite.dash_backlog_documenti` | `vendite.dashboard_backlog.col_emittente` |
| `vendite.dash_competenza_errori` · `vendite.dash_competenza_commesse` | `vendite.dashboard_competenza.col_emittente` *(già esiste — è quella della pilota)* |
| `vendite.lotti` | `vendite.lotti.col_emittente` |

🔵 **Le chiavi mancanti le aggiunge il BE** in `it.json`/`en.json` insieme al
proprio pezzo: sono frontend. Qui servono solo **scritte giuste** nel CSV,
perché è il CSV a dire al frontend quale chiave cercare — e una chiave che non
esiste non dà errore, mostra l'etichetta italiana anche in inglese.

⚠️ **`ordinabile = t` non è gratis**: il presidio
`apps/core/tests/test_liste_configurabili_seed.py` pretende che ogni colonna
ordinabile stia nella whitelist di ordinamento del suo repository, **e nei due
versi**. È già successo con la pilota: la riga di catalogo è arrivata il
2026-08-17 e il presidio è rimasto **rosso fino al giorno dopo**, quando il BE
ha aggiunto la voce. Non è un problema — è il presidio che fa il suo mestiere —
ma conviene saperlo: **fra il seed e il codice BE la CI è rossa**, e va
attraversata in fretta o concordata.

---

## R-4 · `emittente_ragione_sociale` in tre viste ⛔

Il pattern è **già scritto sette volte** (le sei liste documento più la pilota),
e non va inventato:

```sql
LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = <…>.emittente_soggetto_ruolo_id
LEFT JOIN anagrafiche.soggetti       s_ef  ON s_ef.id  = sr_ef.soggetto_id
-- in proiezione:
s_ef.ragione_sociale_completa AS emittente_ragione_sociale
```

| Vista | Quante liste ne dipendono | Nota |
| --- | :---: | --- |
| `vendite.vw_dash_fatturazione_documenti` | **2** | è la vista a monte di aperto **e** backlog: la JOIN si scrive una volta |
| `vendite.vw_dash_competenza_errori` | 1 | l'emittente arriva dal lotto (`l.emittente_soggetto_ruolo_id`) |
| `vendite.vw_dash_competenza_attivita` | 1 | alimenta il drill-down commesse, che il BE **aggrega** (sotto) |

### ⚠️ Due vincoli di `CREATE OR REPLACE VIEW`, silenziosi se sbagliati

Sono gli stessi pagati sulla pilota (`20260818-15`), e li ripeto perché non si
vedono finché non fanno danno:

1. **`security_invoker = on` va RI-SPECIFICATA** o PostgreSQL la azzera — e su
   queste viste ci si appoggia lo scope emittente: senza, la RLS smette di
   filtrare per chi legge;
2. si possono solo **appendere** colonne in coda: la nuova è per forza l'ultima.

### ❓ Una domanda di merito sul drill-down commesse (lista 43)

Il BE non legge la vista riga per riga: **aggrega**, con

```sql
GROUP BY a.commessa_id, a.commessa_codice, a.cliente_display
```

Per portare l'emittente a video il backend deve aggiungerlo al `GROUP BY`. È
sicuro **solo se l'emittente è funzionalmente dipendente dalla commessa** —
cioè se una commessa non può avere attività di emittenti diversi. Se lo fosse,
la stessa commessa si spezzerebbe in **più righe** nel drill-down, e sarebbe una
regressione silenziosa (i totali resterebbero giusti, il conteggio delle righe
no).

> **La domanda è una sola: `vw_dash_competenza_attivita.emittente_soggetto_ruolo_id`
> è univoco per `commessa_id`?** Se sì, il BE aggiunge la colonna al `GROUP BY`
> e non serve altro. Se no, va deciso **cosa mostrare** su una commessa
> multi-emittente — e allora la colonna su quella lista è un lavoro diverso, non
> una riga di CSV.

---

## R-5 · L'emittente nella riga della ricerca universale 🔵 · *residuo D-3*

### Cosa manca

`script.fn_search_soggetti_universale` restituisce:

```sql
RETURNS TABLE(total_count bigint, soggetto_id uuid, soggetto_ruolo_id bigint,
              tipo_ruolo_id integer, soggetto_codice text,
              ragione_sociale_completa text, id_fiscale_univoco text,
              utility_list text)
```

**Nessun emittente.** La funzione lo *usa* per filtrare (ramo `CL`, dal
2026-08-18 risolvendoselo da sé), ma non lo *espone*.

### Perché serve, e perché l'etichetta di perimetro non basta

Il frontend ha appena messo un'etichetta sopra i risultati — *«stai cercando in
tutti gli emittenti»* (P-2c, passo D-3). È onesta e utile, ma dichiara il
**perimetro**, non risolve il caso concreto:

> Due clienti **omonimi**, di due emittenti diversi, sono a video **due righe
> identiche**. Il super admin ne sceglie una e non ha modo di sapere quale.

È esattamente la distinzione di P-2c fra le due cure: su un **numero** basta
dichiarare il perimetro, su una **riga affiancata ad altre** serve il dato.

### Cosa si chiede

Una colonna in coda al `RETURNS TABLE`:

```sql
emittente_ragione_sociale text   -- NULL quando il ruolo non ne ha uno
```

⚠️ **Sul tipo ruolo `CL` l'emittente c'è** (è quello su cui la funzione già
filtra, via `emittenti_fiscali_billing_account`). Su `FO` e sugli altri rami
**non esiste** e la colonna esce `NULL`: è la risposta giusta, non un buco —
una ricerca fornitori non ha perimetro emittente, e la funzione non deve
inventarne uno. Il frontend mostra l'etichetta solo dove il valore c'è.

❓ **Da decidere insieme**: un soggetto cliente può avere billing account sotto
**più** emittenti (è lo scenario §3.1 del brief madre, legittimo). In quel caso
la riga di ricerca è **una** e gli emittenti sono due. Le strade sono due, e la
scelta è di merito:

| | Cosa mostra | Costo |
| --- | --- | --- |
| **A** — una riga per soggetto, emittenti **aggregati** (`string_agg`) | «Tito Srl, Pippo Spa» | non cambia il numero di righe: la paginazione resta quella di oggi |
| **B** — una riga **per emittente** | due righe «Rossi SRL» distinguibili | cambia la cardinalità del risultato, e con essa `total_count` e la paginazione |

> ⭐ **Proposta: A.** La ricerca universale serve a *trovare il soggetto*, non a
> scegliere un perimetro; e B cambierebbe il significato di `total_count` — che
> oggi conta soggetti — per un caso raro. Con A la riga resta una e dichiara
> onestamente che quel cliente vive sotto due emittenti.

⚠️ **`fn_get_search_detail` (livello 2) resta fuori da questa richiesta**: il
dettaglio si apre su **un** soggetto già scelto, quindi non c'è nessuna riga
gemella accanto da cui distinguerlo. È la stessa ragione per cui il dettaglio di
un documento non prende il cancello (P-2c, ultima riga della tabella).

---

## Cosa fa il backend, quando queste arrivano

Perché si veda che la richiesta non è aperta a vuoto:

| Lista | Lavoro BE |
| --- | --- |
| aperto · backlog · errori | colonna nel `SELECT` + riga nel mapping + voce nella whitelist di ordinamento + chiave i18n |
| drill-down commesse | idem, **più** la colonna nel `GROUP BY` (vedi la domanda in R-4) |
| lotti | JOIN a `soggetti_ruoli`/`soggetti` in `list_lotti` + colonna + mapping + whitelist + i18n |
| ricerca (R-5) | colonna nel repository + etichetta **per riga** al posto di quella di perimetro |

Il presidio `test_liste_configurabili_seed` lega catalogo e whitelist nei due
versi, e `test_perimetro_emittente_copertura` verifica che ogni lista abbia il
suo cancello: **entrambi sono già verdi e diventano rossi** se una delle due
metà arriva senza l'altra. Non serve ricordarsene.

---

## Cosa NON si chiede

- **il flag `multi_emittente` acceso**: si accende **dopo**, lista per lista,
  quando la colonna mostra un nome su dati veri — mai insieme al seed della
  colonna (§7, decisione 3);
- **nessuna migrazione applicata da me**: qui si scrive la richiesta, l'apply lo
  autorizza Tid per quel comando;
- **niente sulle 10 liste di amministrazione**: sono `AdminAPIView` e restano
  fuori dal cancello per decisione (§13-bis, C-2);
- **`fn_get_search_detail`** (sopra).
