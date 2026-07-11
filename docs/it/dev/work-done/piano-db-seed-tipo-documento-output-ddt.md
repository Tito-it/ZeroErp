# Piano — Seed `tipi_documento_output` DDT_VENDITA (abilita stampa PDF DDT accompagnatorio)

> **Tipo**: piano di sviluppo (micro-slice DB su `dev/db-tid`) · **Data**: 2026-07-10 · **Owner**: Tid
> **Origine**: §17 addendum del brief DDT — la slice PDF DDT è stata sviluppata BE+FE il
> 2026-07-10 (5° dominio del motore `documenti`, context builder `DDT_VENDITA`); manca **un
> solo prerequisito DB** perché il template DDT sia creabile in admin ed emissibile.
> **Perché un piano separato**: concern distinto dal fix «orfano da push»
> ([piano-db-fix-orfano-push-ordine-confermato.md](piano-db-fix-orfano-push-ordine-confermato.md));
> non lo si mescola in un piano già eseguito.

---

## 1. Richiesta

Abilitare il tipo output `DDT_VENDITA` in `documenti.tipi_documento_output`, così che si possa
creare il template DDT nell'admin (FK `template_documenti.tipo_documento_output_id`) e
l'emissione DDT risolva il template.

## 2. Analisi critica (verifica sul codice vivo)

**La richiesta è valida e il prerequisito è reale.** Verificato:

- `documenti.tipi_documento_output` esiste; righe 1-4 seedate (PREVENTIVO, CONTRATTO,
  OFFERTA_COMMERCIALE, ORDINE_VENDITA). **`id=5` libero**; `codice`/`codice_interno`
  `DDT_VENDITA` non presenti → nessun conflitto con le UNIQUE
  `uq_tipi_documento_output_codice` / `…_codice_interno`. CHECK non-vuoto su
  codice/codice_interno/descrizione soddisfatti.
- FK `template_documenti_tipo_documento_output_id_fkey` → `tipi_documento_output.id`
  **+ trigger** `child_requires_active_parent` (il parent deve essere `attivo=true`): la
  riga va seedata `attivo=true`. ✔
- `config.sorgenti` **id 8 `DDT_VENDITA`** esiste già (tipo DOCUMENTO, target `vendite.ddt`,
  azione PUSH_COMMESSA) → la claim §17 «sorgente già presente» è **confermata**. Nessun
  intervento su `config.sorgenti`.

**⚠️ Scostamento dalla ricetta §17 — NIENTE nuovo changelog.** §17 chiede «CSV **+ changelog**
(stesso pattern della riga 4)». La verifica mostra che la riga 4 (2026-06-04) **non** ha avuto
un changelog dedicato: l'**unico** changelog che tocca la tabella è
`20260429-58-upsert-documenti-seed-base` con `runOnChange: true` + `loadUpdateData`
(`primaryKey: id`). Le righe 3 (2026-05-26) e 4 (2026-06-04) sono state aggiunte
**solo appendendo al CSV**: Liquibase include il file dati nel checksum di `loadUpdateData`,
quindi la modifica CSV cambia il checksum e il changeSet `runOnChange` **ri-esegue** l'upsert.
→ La ricetta corretta è **una sola riga di append al CSV, nessun nuovo file changelog**
(coerente con [[feedback_messaggi_errore_no_new_loader]], [[feedback_seed_80_data_csv]];
creare un nuovo loader sarebbe l'antipattern).

**Altre note.**
- `id=5` esplicito nel CSV è corretto: tabella tecnica lookup (PK `bigint` senza IDENTITY sul
  seed), come le righe 1-4.
- `tx_id = NULL` come token letterale (`nullValue: "NULL"` nel loader —
  [[feedback_liquibase_csv_null_sentinel]]); `storicizza` quotato `"true"`, `meta` `{}` — 1:1
  con le righe esistenti.
- Nessun impatto RLS/guard: tabella lookup di dominio `documenti`.

## 3. Deliverable DB (questa micro-slice)

**Append CSV** (loader runOnChange esistente ri-applica): riga in
`db/changelog/migrations_v2/80_data/sql/documenti/tipi_documento_output.csv`

```
5,DDT_VENDITA,DDT_VENDITA,DDT vendita,true,{},"true",2026-07-10 00:00:00,titodb,2026-07-10 00:00:00,titodb,NULL
```

Nessun altro oggetto DB. Nessun nuovo changeSet.

## 4. Applicazione e verifica (attendere «procedi»)

1. `make db-migrate` (o `db-ci-apply`) → il changeSet `20260429-58` (runOnChange) ri-esegue
   `loadUpdateData` e inserisce/aggiorna la riga 5.
2. Verifica DB:
   ```sql
   SELECT id, codice_interno, attivo FROM documenti.tipi_documento_output ORDER BY id;
   -- atteso: 1..5, con 5 = DDT_VENDITA / attivo = t
   ```
3. Doc auto-gen dbzero: la rigenera Tid (nessuna manual nuova richiesta — riga di seed).

## 5. Post-seed — a carico Tid/BE (fuori team DB)

- Creare il template nell'admin (Template documentali): testata sorgente `DDT_VENDITA`,
  `context_builder_code=DDT_VENDITA`, `is_default=true`, emittente 32 (come i fratelli) +
  versione 1 con HTML/CSS della bozza `template-ddt-vendita.html`/`.css` → **PUBBLICATA**.
- Verifica in-app: anteprima in bozza → emissione con PDF → ristampa da archivio.

## 6. Stato avanzamento

- [x] Analisi critica (ricetta corretta: solo append CSV, no changelog)
- [x] Append riga 5 al CSV `tipi_documento_output.csv`
- [x] **`make db-migrate` eseguito da Tid (2026-07-10)** — loader runOnChange `20260429-58`
  ri-applicato, riga 5 `DDT_VENDITA` presente e `attivo=true`. Verifica query OK (1..5).
- [ ] Template admin + verifica in-app (Tid/BE)

### Consuntivo (2026-07-10)

Micro-slice DB chiusa: `documenti.tipi_documento_output` ora espone `DDT_VENDITA` (id 5).
Il prerequisito DB per il template DDT è soddisfatto; il resto (creazione template admin +
verifica anteprima/emissione/ristampa) è a carico Tid/BE (§5).
