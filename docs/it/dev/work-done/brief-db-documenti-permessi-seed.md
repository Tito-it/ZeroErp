# Brief Team DB — Seed permessi area documenti + 2 azioni processo

**Data:** 2026-05-03
**Riferimento:** `sviluppo-documenti.md` §7 Permessi + §10-bis.4 + Decisione 75
**Branch:** `dev/db-tid`
**Priorita':** alta (sblocca backend area `documenti` per gestione template/asset)

---

## Contesto

`sviluppo-documenti.md` §7 Permessi separa due ambiti:

1. **Gestione template/asset** = configurazione documentale, ambito
   amministrativo, assegnabile anche a responsabili non-admin
   (Decisione 25).
2. **Generazione/lista/download PDF** = permessi del dominio sorgente
   (es. `vendite` per preventivi).

Decisione 75 chiude lato backend con: introdurre **2 azioni processo
dedicate** (`DOCUMENTI_TEMPLATE_MANAGE` + `DOCUMENTI_ASSET_MANAGE`)
+ una nuova **area funzionale** `documenti` (per livelli area
TUTTO/LETTURA/BLOCCATO sulla UI di Configurazione → Modelli documenti).

Le azioni di generazione/lista/download riusano i permessi del dominio
sorgente: nessun nuovo permesso lato `vendite`/`acquisti`/`pratiche` per
questa tranche.

## Cosa si chiede al team DB

Una micro-tranche seed (CSV upsert) che aggiunge:

1. nuova area funzionale `documenti` in `config.aree_funzionali`;
2. due nuove azioni processo in `config.azioni_processo` agganciate
   all'area `documenti`.

Le tabelle e i CSV esistono gia' (vedi
`db/changelog/migrations_v2/80_data/sql/config/aree_funzionali.csv` e
`azioni_processo.csv`).

---

## 1. Nuova riga `config.aree_funzionali`

| Colonna           | Valore proposto                            | Note                                      |
| ----------------- | ------------------------------------------ | ----------------------------------------- |
| `id`              | (next libero, da scegliere DB)             | Coerenza coi seed esistenti               |
| `codice`          | `documenti`                                | Codice tecnico                            |
| `codice_interno` | `documenti`                                | Allineato a schema DB                     |
| `descrizione`    | `Modelli documenti`                        | Visibile in UI Configurazione             |
| `schema_db`      | `documenti`                                | Schema DB primario per `ZeroERPPermission` |
| `attivo`         | `t`                                        |                                           |
| `ordinamento`   | (a discrezione DB, suggerito nel range delle aree config) | UI consistente |
| `meta`            | `{}`                                       |                                           |
| audit             | standard CSV                               | `data_insert`, `user_insert`, ecc.        |

Razionale: l'area corrisponde 1:1 allo schema `documenti` gia' creato in
Fase A. Permette al backend di dichiarare `DomainAPIView` con
`area_funzionale = "documenti"` e di applicare livelli area
TUTTO/LETTURA/BLOCCATO via `ZeroERPPermission`.

---

## 2. Due righe `config.azioni_processo`

Struttura CSV:
`id,area_id,permission_codename,descrizione,pericolosa,attivo,meta,...`

### Riga 1 — gestione template

| Colonna               | Valore                                              |
| --------------------- | --------------------------------------------------- |
| `id`                  | (next libero, da scegliere DB)                      |
| `area_id`             | id della nuova area `documenti`                     |
| `permission_codename` | `DOCUMENTI_TEMPLATE_MANAGE`                         |
| `descrizione`         | `Gestione template e versioni documenti`            |
| `pericolosa`          | `f`                                                 |
| `attivo`              | `t`                                                 |
| `meta`                | `{}`                                                |

Copre: create/update template, create/clone/pubblica/cancella versioni
`BOZZA`. Backend la dichiara su `post_permission` delle view CRUD
template + comandi versione.

### Riga 2 — gestione asset

| Colonna               | Valore                                              |
| --------------------- | --------------------------------------------------- |
| `id`                  | (next libero, da scegliere DB)                      |
| `area_id`             | id della nuova area `documenti`                     |
| `permission_codename` | `DOCUMENTI_ASSET_MANAGE`                            |
| `descrizione`         | `Gestione asset documentali (logo, firma, CSS, allegati)` |
| `pericolosa`          | `f`                                                 |
| `attivo`              | `t`                                                 |
| `meta`                | `{}`                                                |

Copre: upload asset, update metadati asset (no sostituzione file —
Decisione 66), gestione allegati template. Backend la dichiara su
`post_permission` delle view upload e update asset.

### Note operative

- I `permission_codename` sono in **UPPER_SNAKE_CASE** per allinearsi al
  pattern `genera_fatture_lotti` (lowercase) gia' presente? **Da
  decidere col team DB**: il pattern esistente in `azioni_processo.csv`
  e' lowercase snake_case. Per coerenza puro col seed esistente,
  adottare `documenti_template_manage` + `documenti_asset_manage`. Il
  backend FE puo' comunque esporre i nomi come costanti enum
  (`PERMISSIONS.DOCUMENTI_TEMPLATE_MANAGE = 'documenti_template_manage'`).

  Proposta conclusiva: **lowercase snake_case** per coerenza coi seed
  esistenti, salvo diversa indicazione del team DB.

---

## 3. NON-scope di questa tranche

Per restare focalizzati:

- nessun binding di profilo: l'admin assegnera' le azioni ai profili
  reparto via UI esistente (`config.profili_accesso_azioni` post
  refactor multi-face);
- nessuna nuova policy di scope dati: il dominio `documenti` non ha
  filtro emittente nativo nella v1 (i template sono globali per
  istanza); la separazione per emittente, se necessaria, arrivera' nella
  modellazione asset per emittente (gia' prevista da §5.8 con `emittente_id`);
- nessuna modifica a `script.fn_resolve_livello_oggetto` o
  `fn_check_azione`: il sistema esistente gia' supporta nuove area +
  azioni senza patch SQL.

---

## 4. Liquibase — naming proposti

Nuova numerazione `2026XXXX-NN-...` da scegliere dal team DB sul branch
`dev/db-tid`. Pattern atteso (1 changeset unico):

- `80_data/changelog/<data>-<n>-upsert-permessi-documenti-mctit.yaml`

Che richiama via `loadUpdateData` i CSV aggiornati:

- `80_data/sql/config/aree_funzionali.csv` (nuova riga `documenti`)
- `80_data/sql/config/azioni_processo.csv` (2 nuove righe)

`logicalFilePath` da impostare come da convenzione Liquibase v2.

---

## 5. pgTAP atteso

File suggerito: `db/pgtap/config/test_seed_documenti_permessi.sql`.

Scenari minimi (4):

1. `SELECT 1 FROM config.aree_funzionali WHERE codice='documenti' AND attivo=true` → 1 riga.
2. `SELECT 1 FROM config.azioni_processo WHERE permission_codename='documenti_template_manage' AND attivo=true` → 1 riga, `area_id` punta all'area `documenti`.
3. Stesso check per `documenti_asset_manage`.
4. JOIN `config.aree_funzionali` ↔ `config.azioni_processo`: le 2 azioni
   `documenti` puntano alla stessa area.

---

## 6. Cosa fa il backend dopo

Quando la tranche atterra:

1. Backend dichiara `DomainAPIView` con `area_funzionale = "documenti"`
   sulle view di gestione template/asset.
2. Backend dichiara `post_permission = "documenti_template_manage"`
   (o `documenti_asset_manage`) sulle view di comando.
3. Frontend aggiunge `READONLY_DOMAINS.DOCUMENTI = 'documenti'` in
   `src/core/constants.js` e usa `useReadonlyMode(READONLY_DOMAINS.DOCUMENTI)`
   nelle view di Configurazione → Modelli documenti.
4. Frontend usa `<NewButton action="documenti_template_manage" ... />`
   e `<DrawerFooter action="documenti_template_manage" ... />` per
   nascondere automaticamente i bottoni a chi non ha il permesso.
5. Admin assegna le azioni ai profili reparto via UI esistente
   `Amm. Software → Profili reparto`.

---

## 7. Stato lavoro backend dipendente

Il backend `apps/documenti/` e' in attesa di questa tranche per partire
con la PR-A (foundation + storage + registry context_builder + repository
template/versioni/asset + endpoint CRUD). Senza area + azioni seedate, le
view di gestione resterebbero senza enforcement permessi e non
seguirebbero gli standard di `api.md`.
