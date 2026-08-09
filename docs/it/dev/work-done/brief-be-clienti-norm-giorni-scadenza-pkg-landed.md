# Brief BE — landed `clienti.tipo_gg_scadenza_ft` / `nr_giorni_scadenza` normalize+guard

> **Target team**: BE (`dev/backend-tid`)
> **Origine**: DB agent (`dev/db-tid`), sessione 2026-04-27 — landing fase 2 normalizzazioni payload pagamento
> **Impatto**: `apps/<schema>/services/...` (cliente service) + mapping errori
> **Priorita'**: media — niente breaking change a runtime se il BE rispetta gia' la regola; il seed CSV chiude un debito pre-esistente del trigger fornitori

## 1. Cosa abbiamo fatto lato DB

### 1.1 Clienti — package unico (5 componenti)

Migration schema: [`db/changelog/migrations_v2/00_schema/anagrafiche/20260427-03-clienti-norm-giorni-scadenza-pkg-mctit.yaml`](../../../../db/changelog/migrations_v2/00_schema/anagrafiche/20260427-03-clienti-norm-giorni-scadenza-pkg-mctit.yaml) — 3 changeSet sequenziali:

1. **Backfill** record incoerenti
   ```sql
   UPDATE anagrafiche.clienti
      SET nr_giorni_scadenza = NULL
    WHERE tipo_gg_scadenza_ft NOT IN ('G','F')
      AND nr_giorni_scadenza IS NOT NULL;
   ```
2. **DROP DEFAULT** su `nr_giorni_scadenza` (era `0`, misleading sotto la nuova regola; default implicito NULL)
3. **CHECK constraint** `chk_clienti_tipo_gg_scadenza_ft` su `IN ('G','M','F','N')`

Migration code: [`db/changelog/migrations_v2/20_code/anagrafiche/20260427-03-create-trgfn-clienti-normalize-giorni-scadenza-mctit.yaml`](../../../db/changelog/migrations_v2/20_code/anagrafiche/20260427-03-create-trgfn-clienti-normalize-giorni-scadenza-mctit.yaml) — 2 changeSet `runOnChange`:

4. **Function** `anagrafiche.trgfn_clienti_normalize_giorni_scadenza()` — asimmetrica (normalize silenzioso vs raise fail-fast)
5. **Trigger** `trg_clienti_normalize_giorni_scadenza_ins_upd BEFORE INSERT OR UPDATE OF tipo_gg_scadenza_ft, nr_giorni_scadenza` — niente fase `_a10_` (riservata a guard puri)

Pattern allineato alla gemella `anagrafiche.trgfn_fornitori_guard_normalize` (clausole 3-4).

### 1.2 Fornitori — nessuna nuova migration

La regola `ritenuta_acconto = false -> ritenuta_aliquota = NULL` e' gia' applicata da `trgfn_fornitori_guard_normalize` (clausola 4). Confermata in fase di analisi critica del brief originario: niente azione DB sul trigger fornitori.

### 1.3 Seed errori (CSV `config.messaggi_errore`)

[`db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`](../../../../db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv) — 2 nuove righe IT (loader esistente `runOnChange: true`):

| ID | Codice | Note |
|----|--------|------|
| 397 | `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` | Nuovo, raise dal trigger clienti |
| 398 | `E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA` | **Fix opportunistico** — il trigger fornitori esistente lo usa da tempo ma non era seedato (fallback `MESSAGGIO_NON_DEFINITO`) |

Entrambi solo IT, coerenti con la convenzione del progetto (fallback EN→IT come da `brief-db-fallback-lingua-errori.md`).

### 1.4 pgTAP

[`db/pgtap/anagrafiche/test-clienti-normalize-giorni-scadenza-v1.sql`](../../../../db/pgtap/anagrafiche/test-clienti-normalize-giorni-scadenza-v1.sql) — `plan(10)`. Strategia UPDATE su cliente esistente in `BEGIN/ROLLBACK` (no fixture INSERT). Casi:

* `('G',30) ('F',60)` → ammessi
* `('N',5) ('M',10)` → normalize silenzioso a NULL (verifica con `SELECT`)
* `('G',NULL) ('G',0)` → raise `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`
* `('X',5)` → CHECK fail (SQLSTATE 23514)
* Backfill verification: zero record incoerenti post-migration

### 1.5 Doc concettuale

`docs/it/dbzero/anagrafiche/manual/trgfn_clienti_normalize_giorni_scadenza.md` creata. Doc autogen `funzioni/` rigenerata dal tool post-merge.

⚠️ **Superato**: il trigger **non esiste più** (riforma termini di pagamento, piano
satelliti fattura §3a.5) e la pagina manuale è stata **ritirata** — per questo il
riferimento qui sopra non è più un link. Vedi
[piano-db-satelliti-fattura.md](../work-in-progress/piano-db-satelliti-fattura.md) §3a.9.

## 2. Regole dominio (riferimento BE)

| `tipo_gg_scadenza_ft` | `nr_giorni_scadenza` | Esito DB |
|---|---|---|
| `'G'` (giorni) | `> 0` | OK |
| `'F'` (fine mese) | `> 0` | OK |
| `'M'` (manuale) | qualunque | normalize a NULL silenzioso |
| `'N'` (nessuno) | qualunque | normalize a NULL silenzioso |
| `'G'` o `'F'` | `NULL` o `<= 0` | raise `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` (P0001) |
| qualsiasi altro | qualunque | CHECK fail (23514) |

## 3. Punti BE da verificare

### 3.1 Cliente service / serializer

* Nessuna modifica obbligatoria se il BE invia gia' payload coerenti (M/N -> nr_giorni assente, G/F -> nr_giorni > 0). Il trigger e' defense-in-depth.
* Se l'UI permette di lasciare valori "stantii" cambiando solo il tipo (`'N'` con `nr_giorni=5` lasciato dal precedente form `'G'`), **niente da fare**: il trigger ripulisce silenziosamente. Risposta API mostrera' `nr_giorni_scadenza: null` post-save.
* Se il BE pre-valida con regole proprie, allinearle alla matrice §2 per evitare doppia validazione divergente.

### 3.2 Mapping errori

In `apps/core/services/error_policies.py` (o equivalente):

```python
"E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI": ErrorPolicy(
    code="E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI",
    http_status=400,
    ui_action="highlight_form_fields",  # o equivalente
),
"E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA": ErrorPolicy(
    code="E_FORNITORI_RITENUTA_ALIQUOTA_OBBLIGATORIA",
    http_status=400,
    ui_action="highlight_form_fields",
),
```

Quest'ultima va aggiunta se non gia' presente — il trigger fornitori la solleva in produzione, prima senza messaggio template (fallback generico). Ora con id 398 il messaggio diventa user-friendly.

### 3.3 CHECK constraint dominio tipo

Se il BE accetta input utente per `tipo_gg_scadenza_ft` (es. dropdown), allineare la whitelist a `('G','M','F','N')`. Valori extra che dovessero arrivare dal FE/import vengono ora rifiutati a livello DB con `IntegrityError` su `chk_clienti_tipo_gg_scadenza_ft` (mappare al codice errore preferito, es. `E_VENDITE_VALIDATION` o specifico).

### 3.4 Default colonna

`nr_giorni_scadenza DEFAULT 0` non c'e' piu'. Se il BE faceva affidamento sul default DB per omettere il campo nei payload INSERT, ora il campo defaulta a NULL. Per modalita' G/F l'omissione provoca raise → garantisce che il caller lo specifichi esplicitamente.

## 4. Smoke test consigliato

* Crea cliente con `tipo='G'`, `nr_giorni=30` → ok
* Cambia modalita' a `'N'` lasciando `nr_giorni=30` nel form → save ok, response mostra `nr_giorni: null`
* Cambia modalita' a `'G'` e azzera `nr_giorni` → 400 con codice `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`
* Tentativo SQL diretto con `tipo='X'` → 23514 (non flow utente, ma test defense-in-depth)

## 5. Conferma di land

Il DB agent attende:

* allineamento BE su §3.1-§3.3 (se applicabile)
* spostamento di questo brief in `docs/it/dev/work-done/` con header `LANDED`
* aggiornamento eventuale di `MEMORY.md` come terza occorrenza del pattern "normalize+guard simmetrico" (dopo `trgfn_fornitori_guard_normalize` e ora `trgfn_clienti_normalize_giorni_scadenza`)

## 6. Riferimenti

* Doc concettuale: `trgfn_clienti_normalize_giorni_scadenza` — ⚠️ **pagina ritirata insieme al trigger** (vedi §1.5)
* Pattern gemella fornitori: [`trgfn_fornitori_guard_normalize`](../../dbzero/anagrafiche/funzioni/trgfn_fornitori_guard_normalize.md)
* Tabella: [`anagrafiche.clienti`](../../dbzero/anagrafiche/tabelle/clienti.md)
* Codici errore: [`config.messaggi_errore`](../../dbzero/config/tabelle/messaggi_errore.md)

---

*Brief redatto 2026-04-27. Aggiornare con esito verifica BE.*
