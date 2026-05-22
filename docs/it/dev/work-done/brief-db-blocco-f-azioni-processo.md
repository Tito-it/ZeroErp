# Brief Team DB — Blocco F personalizzazioni liste: seed azioni di processo

**Data:** 2026-05-07
**Riferimento:** [`sviluppo-personalizzazioni-liste.md`](sviluppo-personalizzazioni-liste.md) §11 / Blocco F.1
**Branch:** `dev/db-tid` (modifica seed CSV)
**Priorità:** media — sblocca la pagina amministrazione personalizzazioni liste lato FE/BE.

---

## Contesto

Il Blocco F del documento [`sviluppo-personalizzazioni-liste.md`](sviluppo-personalizzazioni-liste.md) introduce la pagina di gestione amministrazione personalizzazioni liste accessibile a:

- **SUPER_ADMIN** via `/amm-software/personalizzazioni-liste` (bypass totale, vede tutti i tab inclusi quelli "tecnici" Fase 2)
- **Tenant admin con azione abilitata** via `/config/personalizzazioni-liste` (solo tab Fase 1 — Preset + Permessi colonne)

I tab Fase 1 sono protetti da 2 nuove **azioni di processo**:

- `ui_preset_manage` — gestione preset (`ui.lista_preset` + `ui.lista_preset_colonna`)
- `ui_permesso_manage` — gestione permessi colonna (`ui.lista_colonna_permesso`)

## Decisioni operative chiuse 2026-05-07

1. **Area associata** alle 2 azioni: `area = config` (id `9`). La pagina vive in `config`, riusa l'area esistente (pattern coerente con `documenti_template_manage` / `documenti_asset_manage` che si appoggiano all'area `documenti`).
2. **Profilo seed che riceve di default le 2 azioni**: **nessuno** (decisione 2B). Solo SUPER_ADMIN ha le azioni di default tramite bypass. Il super-admin assegnerà manualmente le azioni ai profili tenant admin tramite Amm. Software → Profili reparto.

## Patch richiesta

### 1. Aggiungere 2 righe in `config.azioni_processo`

File da editare: [`db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv`](../../../../db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv)

Aggiungere in coda (id auto-incrementanti dopo `15`):

```csv
16,9,ui_preset_manage,Gestione preset personalizzazioni liste,f,t,{},2026-05-07 00:00:00+02,postgres,2026-05-07 00:00:00+02,postgres
17,9,ui_permesso_manage,Gestione permessi colonne personalizzazioni liste,f,t,{},2026-05-07 00:00:00+02,postgres,2026-05-07 00:00:00+02,postgres
```

Il changeset di carico [`20260228-18-upsert-config-azioni-processo-mctit.yaml`](../../../../db/changelog/migrations_v2/80_data/changelog/20260228-18-upsert-config-azioni-processo-mctit.yaml) è già `runOnChange: true` con `loadUpdateData`: basta aggiornare il CSV e rilanciare Liquibase. Idempotente.

### 2. (Niente seed in `profili_accesso_azioni`)

Per decisione 2B: **non** assegnare le 2 azioni a nessun profilo seed. Nessuna riga in `config.profili_accesso_azioni`. Il super-admin abiliterà le azioni manualmente sui profili `REPARTO_*` che vorrà autorizzare alla gestione personalizzazioni liste, dalla pagina Amm. Software → Profili reparto.

## Esecuzione

1. Aggiornare `azioni_processo.csv` con le 2 righe nuove.
2. Lanciare `make db-migrate` (o equivalente CI) per ri-eseguire il changeset `20260228-18` con `runOnChange: true`.
3. Verificare:

```sql
SELECT id, area_id, permission_codename, descrizione, attivo
  FROM config.azioni_processo
 WHERE permission_codename IN ('ui_preset_manage','ui_permesso_manage')
 ORDER BY id;
```

Atteso: 2 righe `attivo=true`, `area_id=9` (config), `pericolosa=false`.

## Cosa NON si chiede

- Nessuna modifica a DDL / migrations / dati DDL.
- Nessuno schema nuovo, nessun trigger, nessuna funzione.
- Nessun seed in `profili_accesso_azioni` (decisione 2B).
- Nessun nuovo profilo in `profili_accesso`.

## Risposta attesa

Confermare l'aggiornamento del CSV e l'esecuzione del changeset. A quel punto il backend agent può:

1. Lanciare il backend con le 2 nuove azioni registrate in `config.azioni_processo`.
2. Verificare che `auth.isActionAllowed('ui_preset_manage')` ritorni `false` per tutti i tenant admin (zero profili seed) e `true` per SUPER_ADMIN (bypass).
3. Procedere con l'integrazione FE Blocco F (pagina admin sotto `/amm-software/personalizzazioni-liste` e `/config/personalizzazioni-liste`).
