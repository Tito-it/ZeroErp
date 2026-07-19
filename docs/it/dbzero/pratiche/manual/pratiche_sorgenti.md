## 📘 Documentazione Concettuale – Tabella `pratiche.pratiche_sorgenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
La tabella `pratiche.pratiche_sorgenti` e' la **tabella ponte** che collega una pratica
a una o piu' sorgenti esterne (preventivi, ordini, contratti, ecc.).

Il pattern e' allineato a `vendite.commesse_sorgenti`: una pratica puo' avere piu'
sorgenti ROOT di tipi diversi e una sorgente puo' essere collegata a piu' pratiche.

---

### Ruolo nel processo

* Quando un preventivo vendita viene accettato, l'operatore puo' generare una pratica
  operativa (es. sopralluogo, installazione). La pratica viene collegata al preventivo
  tramite questa tabella con `sorgente_tipo = 'PREVENTIVO'` e `sorgente_uid = preventivo.uid`.
* La navigazione e' **bidirezionale**: dal preventivo si vedono le pratiche collegate,
  dalla pratica si risale ai documenti sorgente.
* Il campo `ruolo_link` distingue la sorgente principale (ROOT) da quelle secondarie (COLLEGATO).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `pratica_id` | BIGINT NOT NULL. FK a `pratiche.pratiche`. |
| `sorgente_tipo_id` | BIGINT NOT NULL. FK a `config.sorgenti` — identifica il tipo di documento sorgente (PREVENTIVO, ORDINE, ecc.). |
| `sorgente_uid` | TEXT NOT NULL. **La chiave** del documento sorgente, nel formato dettato da `config.sorgenti.key_selector`: **uuid testuale** per i tipi a chiave `uid` (preventivo, offerta), **`id::text`** per i tipi a chiave `id` (ordine, commessa, ddt, ...). Formato ed esistenza sono blindati dal guard `trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd` (2026-07-18). |
| `sorgente_riga` | BIGINT nullable. ID di una riga specifica della sorgente (es. riga preventivo). **NON è una chiave documento**: è la grana di riga del link (non validata dal guard; decisione D4 del brief-db-guard-sorgente-polimorfa). |
| `ruolo_link` | VARCHAR(30) DEFAULT 'ROOT'. Valori ammessi: ROOT (sorgente principale), COLLEGATO (secondaria). CHECK constraint. |
| `meta` | JSONB DEFAULT '{}'. Metadati aggiuntivi del collegamento. |
| `storicizza` | BOOLEAN DEFAULT true. Flag per storicizzazione automatica. |
| `tx_id` | UUID. Transaction ID di sessione. |

---

### Vincoli principali

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_pratiche_sorgenti_pratica_tipo_uid_ruolo` | UNIQUE | Una sola associazione per pratica + tipo + uid + ruolo |
| `chk_pratiche_sorgenti_ruolo` | CHECK | `ruolo_link IN ('ROOT', 'COLLEGATO')` |
| `ix_pratiche_sorgenti_tipo_uid` | INDEX | Per query bidirezionali dalla sorgente alle pratiche |

---

### Differenze rispetto a `vendite.commesse_sorgenti`

| Aspetto | `commesse_sorgenti` | `pratiche_sorgenti` |
|---------|---------------------|---------------------|
| Cardinalita' ROOT | Una sola ROOT per commessa | Piu' ROOT di tipi diversi per pratica |
| UNIQUE | `(commessa_id, ruolo_link)` | `(pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` |
| Caso d'uso | Commessa ha un documento sorgente principale | Pratica puo' servire piu' sorgenti commerciali |

---

### Esempio d'uso

```sql
-- Pratiche collegate a un preventivo
SELECT ps.pratica_id, p.codice, p.descrizione
FROM pratiche.pratiche_sorgenti ps
JOIN pratiche.pratiche p ON p.id = ps.pratica_id
JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
WHERE s.codice = 'PREVENTIVO'
  AND ps.sorgente_uid = '550e8400-e29b-41d4-a716-446655440000';

-- Sorgenti collegate a una pratica
SELECT s.codice AS tipo_sorgente, ps.sorgente_uid, ps.ruolo_link
FROM pratiche.pratiche_sorgenti ps
JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
WHERE ps.pratica_id = 42;
```

---

{% include-markdown "signature-core.md" %}
