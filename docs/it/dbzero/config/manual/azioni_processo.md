## 📘 Documentazione Concettuale – Tabella `config.azioni_processo`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.profili_reparto_azioni](/dbzero/config/tabelle/profili_reparto_azioni)
> [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni)

---

La tabella **`config.azioni_processo`** è il **registro delle azioni di processo** gestibili nell'interfaccia permessi.

Le azioni rappresentano **operazioni puntuali** che richiedono abilitazione esplicita, indipendentemente dal livello di accesso sull'area. Anche un utente con TUTTO su vendite potrebbe non poter eseguire azioni critiche come la generazione massiva di fatture.

---
### 🎯 Scopo Principale
* Catalogare le **azioni di processo** che richiedono abilitazione esplicita.
* Raccordare il **codename Django** (`Meta.permissions` → `auth_permission`) con la gestione profili.
* Segnalare le azioni **pericolose** che richiedono conferma aggiuntiva nella UI.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `area_id` | Area funzionale a cui appartiene l'azione (raggruppamento UI) |
| `permission_codename` | Chiave tecnica immutabile — riferimento al codename in `django.auth_permission` |
| `pericolosa` | Flag per azioni critiche: la UI mostra un warning aggiuntivo |

**Nota:** `permission_codename` fa le veci di `codice_interno` (chiave tecnica immutabile). Le azioni nascono nel codice Django (`Meta.permissions`) e questa tabella le rende visibili e gestibili nell'interfaccia admin.

---

### Relazioni

`config.azioni_processo` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `config.profili_reparto_azioni` | `azione_id` | Abilitazione azione per reparto |
| `config.user_override_azioni` | `azione_id` | Override individuale per azione |

---

### Seed

| permission_codename | descrizione | pericolosa | area | introdotta |
|---------------------|-------------|------------|------|------------|
| genera_fatture_lotti | Genera fatture da lotti | SI | vendite | seed iniziale |
| genera_fattura | Genera singola fattura | NO | vendite | seed iniziale |
| approva_fattura | Approva fattura | NO | vendite | seed iniziale |
| emetti_fattura | Emetti fattura | NO | vendite | seed iniziale |
| approva_rimessa | Approva rimessa di pagamento | NO | pagamenti | seed iniziale |
| reset_lotto_draft | Reset lotto a stato DRAFT | SI | vendite | 2026-03-01 |
| reset_lotto_fattura_draft | Reset singola fattura lotto a DRAFT | SI | vendite | 2026-03-01 |
| run_commesse_push | Invio commesse a sistema esterno | NO | vendite | 2026-03-01 |
| prezzo_override_manuale | Modifica manuale prezzo | NO | vendite | 2026-04-17 |
| approva_prezzo_override | Approva modifica prezzo | NO | vendite | 2026-04-23 |
| cambia_stato_preventivi | Cambia stato preventivo (emetti/accetta/rifiuta/annulla) | NO | vendite | 2026-05-02 |
| push_commessa_preventivi | Push preventivo a commessa per fatturazione | SI | vendite | 2026-05-02 |
| genera_pratica_preventivi | Genera pratica esecutiva da preventivo | NO | vendite | 2026-05-02 |
| documenti_template_manage | Gestione template e versioni documenti | NO | documenti | 2026-05-03 |
| documenti_asset_manage | Gestione asset documentali (logo, firma, CSS, allegati) | NO | documenti | 2026-05-03 |

---

### ⚠️ Catena di risoluzione azioni

La risoluzione è separata dal CRUD e binaria:

```
1. Override utente sull'azione? (GRANT/DENY)
   → SI: applica
   → NO: continua ↓

2. Azione abilitata nel profilo reparto?
   → SI: concessa
   → NO: negata
```

---

> **"`config.azioni_processo` consente di controllare operazioni critiche con granularità puntuale, separatamente dal livello CRUD sull'area."**
