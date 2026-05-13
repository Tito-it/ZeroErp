# Brief DB — Messaggio `E_BOM_IVA_DISCORDANTE` parlante (aliquota %)

> **Data**: 2026-05-13
> **Branch target**: `dev/db-tid`
> **Priorità**: bassa (UX di messaggi errore, non bloccante)

## 1. Problema

Lo smoke 3.4 (setup BoM con IVA discordante) ha generato il messaggio:

```
BoM incoerente: padre [art-comp-001] IVA [16] != figlio [componente ns] IVA [2].
```

- Gli ID `[16]` e `[2]` sono `config.iva.id` interni, opachi per l'operatore
- L'utente non sa cosa significhi "IVA 16" — vorrebbe vedere l'aliquota
  effettiva (es. `22%`, `10%`)
- Il pattern `[id]` confonde con `[codice]`

## 2. Caller impattati

| Migration | Fn | Note |
| --- | --- | --- |
| `20260513-02` | `catalogo.trgfn_articoli_componenti_guard_iva` | BEFORE INSERT su `articoli_componenti` |
| `20260513-03` | `catalogo.trgfn_articoli_guard_iva_bom_attiva` | BEFORE UPDATE OF `iva_id` su `articoli` (lato padre + lato figlio) |

Entrambe passano `v_iva_padre::text` e `v_iva_figlio::text` (id numerici).

## 3. Cosa fare

**Non modificare i changelog 20260513-02..03** (già mergiati).

Creare 2 nuovi changelog `runOnChange` (es.
`20260513-33..34-update-trgfn-articoli-*-guard-iva-message-mctit.yaml`)
che ridefiniscono le 2 fn aggiungendo lookup `config.iva.aliquota_iva`
e passando l'aliquota formattata al messaggio.

### Patch fn trigger (entrambe simmetriche)

Estendere la SELECT del trigger per leggere anche `aliquota_iva` da
`config.iva`:

```sql
SELECT a_padre.iva_id,  a_padre.codice,  COALESCE(iva_padre.aliquota_iva::text, '—'),
       a_figlio.iva_id, a_figlio.codice, COALESCE(iva_figlio.aliquota_iva::text, '—')
  INTO v_iva_padre_id,   v_codice_padre,   v_iva_padre_aliquota,
       v_iva_figlio_id,  v_codice_figlio,  v_iva_figlio_aliquota
  FROM catalogo.articoli a_padre
  JOIN catalogo.articoli a_figlio
    ON a_figlio.id = NEW.componente_id
  LEFT JOIN config.iva iva_padre  ON iva_padre.id  = a_padre.iva_id
  LEFT JOIN config.iva iva_figlio ON iva_figlio.id = a_figlio.iva_id
 WHERE a_padre.id = NEW.prodotto_id;
```

E nel raise passare l'aliquota invece dell'id:

```sql
PERFORM script.fn_log_and_raise_error(
    'catalogo', TG_NAME, 'E_BOM_IVA_DISCORDANTE',
    jsonb_build_object(
        'prodotto_id',     NEW.prodotto_id,
        'componente_id',   NEW.componente_id,
        'iva_padre_id',    v_iva_padre_id,
        'iva_figlio_id',   v_iva_figlio_id,
        'iva_padre_pct',   v_iva_padre_aliquota,
        'iva_figlio_pct',  v_iva_figlio_aliquota
    ),
    NULL::uuid,
    v_codice_padre,
    v_iva_padre_aliquota,
    v_codice_figlio,
    v_iva_figlio_aliquota
);
```

(Il `meta` JSONB mantiene `*_id` per audit, il messaggio mostra `*_pct`.)

### Patch messaggio CSV

In `80_data/sql/config/messaggi_errore.csv`, riga `E_BOM_IVA_DISCORDANTE`:

```text
PRIMA:
"BoM incoerente: padre [%s] IVA [%s] != figlio [%s] IVA [%s]."

DOPO:
"L'articolo composito %s ha IVA al %s%% ma il componente %s ha IVA al %s%%. Le aliquote IVA di padre e figli BoM devono coincidere."
```

(Sostituisce gli ID con le aliquote percentuali, lingua più operativa.)

Aggiungere riga seed con nuova migration `80_data/changelog/20260513-35-update-msg-bom-iva-discordante-mctit.yaml` (UPDATE del messaggio_it/en).

## 4. Test post-fix

Smoke manuale:

1. BoM padre `ART-COMP-001` IVA 22%, figlio con IVA 10% → tentare INSERT BoM
2. Verifica messaggio ricevuto dal FE:
   - **Atteso**: `"L'articolo composito ART-COMP-001 ha IVA al 22% ma il componente FIGLIO-X ha IVA al 10%. Le aliquote IVA di padre e figli BoM devono coincidere."`
   - **NON atteso**: `[id=16]`, `[id=2]` numerici
3. Tentare UPDATE `articoli.iva_id` sul padre composito mentre ha BoM
   con figli IVA diversa → stesso pattern messaggio per
   `trgfn_articoli_guard_iva_bom_attiva`

## 5. Catena BE/FE

Nessuna modifica BE/FE richiesta — il messaggio è formato lato DB e
arriva tramite `script.fn_log_and_raise_error` → middleware Django
→ FE che mostra il `message` plain text. Cambia solo il formato del
testo.

## 6. Riferimenti

- Modello: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md) §6 IVA coerente padre-figli
- CSV seed: `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv` riga `E_BOM_IVA_DISCORDANTE`
- Migration originali: `20260513-02-create-trgfn-articoli-componenti-guard-iva-bom-mctit.yaml`, `20260513-03-create-trgfn-articoli-guard-iva-bom-attiva-mctit.yaml`
