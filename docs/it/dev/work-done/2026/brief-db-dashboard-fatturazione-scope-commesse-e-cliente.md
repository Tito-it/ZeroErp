# Brief DB — Dashboard fatturazione: scope emittente COMMESSE + colonna cliente drill-down

> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🟠 MEDIA
> (rifiniture v1: la dashboard è funzionante, questi due punti chiudono una
> incoerenza e una perdita informativa emerse in code review). · **Data**: 2026-07-04.
> **Origine**: review critica Fase 2/3 dashboard fatturazione.
> **Correlato**: `brief-design-dashboard-fatturazione.md` (design autorevole, Fase 1
> DB già applicata: migrations `20260703-51..59`); viste
> `vendite.vw_dash_fatturazione_{mensile,documenti,commesse}`; doc BE
> `docs/it/backend/vendite/manual/api_dashboard_fatturazione.md`.
>
> ## ✅ Stato: DB APPLICATO (2026-07-04, migration `20260703-60`) + BE/FE allineati
>
> DB (test DB, non ancora mergiato):
> * **P2 `cliente_display`** aggiunta ai 5 resolver → union `vw_dash_fatturazione_documenti`
>   (ultima colonna, `::text`, `LEFT JOIN` nullable). Path al cliente NON uniforme: si
>   riusa lo stesso join della rispettiva `vw_*_lista` (preventivi/offerte
>   `istanze_utilities→soggetti`, ordini `soggetto_ruolo_id`, contratti/commesse
>   `billing_account→soggetto_ruolo→soggetti`).
> * **P1 scope COMMESSE** portato **dentro** `vw_dash_fatturazione_commesse` via
>   `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` (GUC; NULL=tutto,
>   `'{}'`=niente, array=whitelist) → matrice **e** drill-down ereditano il filtro.
>   Scelto NON attivare RLS su `commesse` (tabella di pipeline scritta da molti
>   contesti non-web: blast-radius troppo ampio); filtro nel solo resolver di
>   reporting = chirurgico. ⚠️ fail-closed: filtro-in-vista non aggirato da
>   `BYPASSRLS` → senza GUC operatore il resolver commesse dà 0 righe (ok: dashboard
>   solo-web, GUC sempre valorizzata). pgTAP esteso a `plan(25)` (2 emittenti +
>   assert `cliente_display`).
>
> BE/FE post-fix (questa branch `dev/backend-tid`): rimosso il branch scope
> applicativo COMMESSE in `vendite_repository.list_dash_fatturazione_fermi` (+ il
> parametro `auth_user_id` da repo/service/view: scope 100% DB-side); aggiunta
> `cliente_display` a `DashFatturazioneFermoRow` e alla SELECT; ripristinata la
> colonna **Cliente** nel drill-down FE (`col_cliente` i18n it/en); caveat in
> `api_dashboard_fatturazione.md` §Regole aggiornato (asimmetria risolta +
> fail-closed documentato). Test verdi.
>
> *Il testo sotto è il brief originale, conservato per traccia.*

---

## Contesto

La dashboard fatturazione (matrice mensile + drill-down fermi) legge due viste
read-only. Per le 4 aree documento (preventivi/ordini/offerte/contratti) lo scope
emittente dell'operatore è applicato **automaticamente dalla RLS** (viste invoker).
L'area **COMMESSE è fuori RLS by design DB**: il filtro scope è delegato al BE, che
oggi lo applica **solo sul drill-down** (`vw_dash_fatturazione_documenti`, via
`fn_get_emittenti_scope_sr_ids` su `emittente_soggetto_ruolo_id`), **non**
sull'aggregata mensile (`vw_dash_fatturazione_mensile`, che è pre-sommata: il BE non
può più filtrare a valle).

## Problema 1 — 🟠 COMMESSE: card non scopata vs drill-down scopato

Per un operatore con **scope emittente ristretto** (whitelist non-NULL):

* la **card COMMESSE** del mese aggrega valori/conteggi di **tutti** gli emittenti
  (la vista mensile non applica scope per commesse) → possibile *leak* di importi
  cross-emittente nell'aggregato e semaforo mese calcolato su dati non di competenza;
* al **click** sulla card, il **drill-down** mostra solo le commesse in scope →
  numeri che non tornano (es. card `n_fermi=7`, tabella con 3 righe).

Le 4 aree documento non hanno il problema (RLS su entrambe le viste). È
un'incoerenza osservabile e un leak, non solo estetica.

### Cosa serve (accesso, non implementazione specifica)

Rendere l'area COMMESSE **scope-aware anche nell'aggregata**, in modo che matrice e
drill-down concordino. Il *come* è vostra scelta; opzione naturale coerente con le
altre 4 aree: portare lo scope **dentro il resolver** `vw_dash_fatturazione_commesse`
(che alimenta sia la union documenti sia — a monte dell'aggregazione — la mensile),
filtrando `emittente_soggetto_ruolo_id` sull'operatore corrente letto da GUC
(`app.current_user_id` → `fn_get_emittenti_scope_sr_ids`), con la solita semantica
"NULL = vede tutto" (admin/superuser). Così entrambe le viste ereditano il filtro e
il BE può **rimuovere** il branch applicativo `if area == 'COMMESSE'` nel repository
(oggi in `vendite_repository.list_dash_fatturazione_fermi`).

> Se preferite lasciarlo fuori RLS ma coerente, va bene qualunque meccanismo purché
> **la stessa regola valga per matrice e drill-down**. Il punto è la coerenza dei
> due numeri, non la tecnica.

### Nota BE post-fix

Quando il resolver commesse diventa scope-aware:
1. il repository BE toglie il branch speciale COMMESSE (torna simmetrico alle altre aree);
2. va aggiornato il caveat in `api_dashboard_fatturazione.md` §Regole (oggi documenta
   l'asimmetria come limite noto).

## Problema 2 — 🟠 Drill-down fermi senza il cliente

Il drill-down (`vw_dash_fatturazione_documenti`) espone `codice` del documento ma
**non** la ragione sociale del cliente/billing_account. In fase di triage l'operatore
vede N righe identificate solo dal codice (`CNT0000007`, `PRV0000123`) e deve aprire
ogni documento per sapere **di chi** si tratta — perdendo il colpo d'occhio che è lo
scopo della dashboard. (La versione mock del FE mostrava la colonna "Cliente"; lo
swap su dati reali l'ha persa perché la vista non la porta.)

### Cosa serve

Aggiungere alla vista `vw_dash_fatturazione_documenti` (e quindi ai 5 resolver di
area) una colonna con il **display del cliente** — tipicamente
`ragione_sociale_completa` da `anagrafiche.vw_soggetti_ruoli_dettaglio` via il
`billing_account`/`soggetto_ruolo` del documento. Il campo per-area:

| Area | Percorso al cliente (indicativo) |
|---|---|
| preventivi | `preventivi.billing_account_id` → BA → soggetto_ruolo → ragione sociale |
| ordini | `ordini.billing_account_id` → … |
| offerte | `offerte_commerciali` → BA/soggetto → … |
| contratti | `contratti` → BA → … |
| commesse | `commesse` → BA/soggetto destinatario → … |

Nome colonna proposto: `cliente_display` (string, nullable se non risolvibile). Il BE
la aggiunge a `DashFatturazioneFermoRow` e la restituisce; il FE ripristina la colonna
"Cliente" nel drill-down (già prevista dal layout, `col_cliente` i18n da reintrodurre).

## Criteri di accettazione

1. Per un operatore con scope ristretto, la **card COMMESSE** e il **drill-down
   COMMESSE** dello stesso mese mostrano numeri **coerenti** (stesso perimetro emittente).
2. Nessuna regressione sulle altre 4 aree (restano filtrate da RLS su entrambe le viste).
3. `vw_dash_fatturazione_documenti` espone `cliente_display` valorizzato per tutte e 5
   le aree dove il cliente è risolvibile.
4. pgTAP aggiornato: fixture con 2 emittenti → la card commesse dell'emittente A non
   include le commesse dell'emittente B; assert su `cliente_display` non-null per una
   riga fixture per area.

## Fuori scope

* Valore € di offerte/contratti (resta v2, decisioni D-2/D-3 del brief design).
* Qualunque cambiamento al contratto degli endpoint BE oltre l'aggiunta della colonna
  `cliente_display` e la rimozione del branch scope applicativo.
