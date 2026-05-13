# Brief DB — Default `attivo = TRUE` per tutti i componenti in fn `*_init`

> **Data**: 2026-05-13
> **Branch target**: `dev/db-tid`
> **Decisione di dominio**: la BoM e' contratto immutabile per documento.
> L'operatore non sceglie quali componenti includere: tutti i figli BoM
> validi alla data finiscono SEMPRE nella riga con `attivo=TRUE`.

## 1. Sintesi

Le 4 fn `fn_<sorgente>_riga_componenti_init` oggi inseriscono i componenti
con default che dipende da `obbligatorio`:

```sql
-- Oggi (modello unificato 20260513-09..12):
INSERT INTO vendite.<sorgente>_righe_componenti (..., attivo, ...)
VALUES (..., v_comp.obbligatorio, ...);  -- obbligatori TRUE, opzionali FALSE
```

**Cambio richiesto**: default `attivo = TRUE` **sempre**, indipendentemente
da `obbligatorio`:

```sql
-- Nuovo:
INSERT INTO vendite.<sorgente>_righe_componenti (..., attivo, ...)
VALUES (..., TRUE, ...);
```

## 2. Razionale

Decisione di dominio (Tid, 2026-05-13): "se è stata definita una BoM vale
quella, l'operatore non puo' modificare la composizione". Conseguenze:

- Il flag `obbligatorio` in `catalogo.articoli_componenti` mantiene
  significato solo per **guard prezzo**: obbligatori non ammettono
  `prezzo_unitario = 0` (`script.trgfn_componenti_check_prezzo_obbligatorio`
  resta invariato). Opzionali ammettono qualsiasi prezzo (incluso 0).
- L'UI non espone più la checkbox di toggle attivo/inattivo nel
  documento (sia in CREATE Dialog che in EDIT panel).
- Il trigger guard `script.trgfn_componenti_guard_obbligatorio` resta
  come safety net (impedisce UPDATE `attivo=FALSE` su obbligatori) ma
  in pratica e' inerte: l'UI non fa più richieste di disattivazione.

## 3. Caller impattati

| Migration corrente | Fn | Riga del default |
| --- | --- | --- |
| `20260513-09` | `vendite.fn_preventivo_riga_componenti_init` | INSERT ... `v_comp.obbligatorio` |
| `20260513-10` | `vendite.fn_ordine_riga_componenti_init` | idem |
| `20260513-11` | `vendite.fn_ddt_riga_componenti_init` | idem |
| `20260513-12` | `vendite.fn_contratto_riga_componenti_init` | idem |

## 4. Cosa fare

**Non modificare i changelog 20260513-09..12** (già mergiati).

Creare 4 nuovi changelog `runOnChange` (es.
`20260513-29..32-update-fn-<sorgente>-riga-componenti-init-default-attivo-true-mctit.yaml`)
che ridefiniscono le 4 fn `_init` con `attivo=TRUE` al posto di
`v_comp.obbligatorio` nell'INSERT.

**Allineare anche con il fix JSONB**: se il brief
[`brief-db-fix-jsonb-key-exists-init-componenti.md`](brief-db-fix-jsonb-key-exists-init-componenti.md)
non è ancora applicato, fare entrambi i fix nella stessa migration
(operatore `?` corretto + default `attivo=TRUE`) per evitare doppio
re-deploy. Numerazione `20260513-29..32` gia' libera per entrambi.

## 5. Test post-fix

Smoke manuale:

1. Definire un articolo composito con BoM mista (almeno 1 obbligatorio + 1 opzionale)
2. Aggiungere riga preventivo con quel composito
3. Verificare in `preventivi_righe_componenti`:
   - Tutti i figli inseriti con `attivo=TRUE` (anche quelli `obbligatorio=FALSE`)
   - `prezzo_unitario` padre = SUM(figli × coeff_qta) di TUTTI i figli

**SQL diretto**:

```sql
SELECT
  ac.componente_id, ac.obbligatorio, prc.attivo
FROM vendite.preventivi_righe pr
JOIN vendite.preventivi_righe_componenti prc ON prc.riga_preventivo_id = pr.id
JOIN catalogo.articoli_componenti ac ON ac.id = prc.articolo_componente_id
WHERE pr.id = <id-riga-test>;
-- Atteso: tutti `attivo = t`, sia obbligatori che opzionali
```

## 6. Catena BE/FE

- **BE**: nessuna modifica richiesta — il service `gestisci_riga` continua
  ad accettare `componenti_attivazioni` come parametro opzionale del
  payload (path dormiente, retrocompatibile). Il FE non lo invia più.
  Cleanup totale del path dormiente rinviato a Fase H.
- **FE**: contestuale a questa migration verranno rimosse le colonne
  "Attivo" (checkbox toggle) da `ComponentiDialog.vue` e
  `PreventiviRigaComponentiPanel.vue`. Restano i tag info
  (Obbligatorio/Opzionale + In fattura Sì/No).

## 7. Riferimenti

- Modello: [`manual/modello-componenti-bom.md`](../manual/modello-componenti-bom.md) — da aggiornare sezione "regole attivazione" con nuova decisione
- Changelog decisioni: [`manual/changelog-decisioni-componenti.md`](../manual/changelog-decisioni-componenti.md) — append nuova decisione 2026-05-13 "BoM contratto immutabile per documento"
- Brief fix JSONB correlato: [`brief-db-fix-jsonb-key-exists-init-componenti.md`](brief-db-fix-jsonb-key-exists-init-componenti.md)
