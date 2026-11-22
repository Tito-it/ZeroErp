# Brief DB — `lotto_id` sulla vista `vw_dash_competenza_attivita`

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-22 · **Owner**: Tid · **Stato**: 🟢 **APPLICATO + EVASO (2026-07-22)** — colonna
> `lotto_id` in vista (verificato live: reloption `security_invoker=on` preservata, zero
> moltiplicazione righe, `lotto_id` popolato 6/6 sulle FATTURATA); a valle BE (§5.1) e FE
> (§5.2) realizzati e verdi. Era: piccolo delta additivo (1 colonna via LEFT JOIN),
> niente breaking. Prerequisito della metà **breakdown FATTURATA** dello step **B-5** del
> cockpit
> ([brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)).
>
> **Perimetro**: SOLO DB — una `CREATE OR REPLACE VIEW` di
> `vendite.vw_dash_competenza_attivita` che aggiunge la colonna `lotto_id`. BE/FE restano
> su `dev/backend-tid` (attendono l'apply, [[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → il
> replace della vista è secco, nessuna compat da mantenere.

---

## 1. Perché

Il pannello **errori** della Dashboard Competenza già atterra sul `LottoDrawer` filtrato
(B-5, metà FE fatta 2026-07-22): la vista `vw_dash_competenza_errori` **espone già**
`lotto_id`. La seconda superficie di B-5 — dal **drill-down delle attività**
(card stadio, tipicamente `FATTURATA`) atterrare sul lotto della fattura — **non è
realizzabile**: `vw_dash_competenza_attivita` espone `fattura_id` ma **non** `lotto_id`
(verificato sul DB vivo, 2026-07-22). Non esiste un percorso «apri lotto da fattura» lato
BE, e il `LottoDrawer` richiede un `lotto_id`.

## 2. Cosa

Aggiungere alla vista `vendite.vw_dash_competenza_attivita` la colonna `lotto_id`
via LEFT JOIN a `vendite.fatturazione_lotti_fatture` sulla `fattura_id` già presente
(la vista fa già `LEFT JOIN vendite.fatture f`):

```sql
-- ... nella lista SELECT, accanto a f.numero AS fattura_numero:
    lf.lotto_id,
-- ... nella catena FROM, dopo il LEFT JOIN a vendite.fatture f:
    LEFT JOIN vendite.fatturazione_lotti_fatture lf ON (lf.fattura_id = f.id)
```

⚠️ **`security_invoker=on`** va **ri-specificato** nella `CREATE OR REPLACE VIEW`
(reloption non visibile in `pg_get_viewdef`, PostgreSQL la azzera altrimenti — stessa
trappola documentata sulle `vw_dash_*`). La colonna è additiva: nessun consumer esistente
si rompe (il BE seleziona per nome, non `SELECT *`).

## 3. Cardinalità — perché è sicuro (nota per il team)

`fatturazione_lotti_fatture` ha `UNIQUE (lotto_id, fattura_id)` — **non** su
`fattura_id` da solo: lo schema ammette 1:N (una fattura in più lotti). **Oggi è 1:1
effettivo** (query di verifica 2026-07-22: zero fatture in più di un lotto). Il LEFT JOIN
non moltiplica le righe attività finché regge il 1:1. È lo **stesso assunto** che la
`vw_dash_competenza_errori` già fa (CTE `fatture_competenze` fa `JOIN
fatturazione_lotti_fatture` diretto). Se il team preferisce blindare l'invariante contro
un futuro 1:N, il join può diventare un `LEFT JOIN LATERAL (… ORDER BY lotto_id DESC
LIMIT 1)` che sceglie deterministicamente un solo lotto — a discrezione del team DB;
il consumer FE usa solo `lotto_id` scalare, entrambe le forme vanno bene.

## 4. Verifica post-apply

```sql
-- (a) colonna presente + reloption preservata
SELECT 1 FROM information_schema.columns
 WHERE table_schema='vendite' AND table_name='vw_dash_competenza_attivita'
   AND column_name='lotto_id';
SELECT reloptions FROM pg_class WHERE relname='vw_dash_competenza_attivita';
-- atteso: {security_invoker=on}

-- (b) nessuna moltiplicazione di righe (conteggio invariato pre/post)
SELECT count(*) FROM vendite.vw_dash_competenza_attivita;

-- (c) lotto_id valorizzato sulle attività FATTURATA di un lotto noto
SELECT commessa_attivita_id, fattura_id, lotto_id
  FROM vendite.vw_dash_competenza_attivita
 WHERE stadio='FATTURATA' AND lotto_id IS NOT NULL LIMIT 5;
```

## 5. A valle (BE/FE, dopo l'apply — resta a `dev/backend-tid`)

1. **BE** `VenditeRepository.list_dash_competenza_attivita` + tipo
   `DashCompetenzaAttivitaRow`: aggiungere `lotto_id` alla SELECT e alla proiezione
   (delta ~2 righe, stesso pattern già usato per gli errori).
2. **FE** `DashboardCompetenzaView.vue`: nel drill-down attività riusare l'handler
   `apriLotto(data.lotto_id)` (già estratto per il pannello errori) su una cella/azione
   «Lotto» visibile solo quando `lotto_id` è valorizzato (stadio FATTURATA / EMESSA in
   lotto). Nessuna nuova logica: la superficie errori e quella attività condividono lo
   stesso drawer e lo stesso gate-sul-dato.
