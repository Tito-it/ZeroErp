## 📘 Documentazione Concettuale – Tabella `config.azioni_processo`

> **Ultimo aggiornamento**: 25 ottobre 2026

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
>
Tabelle correlate:
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni)
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
| `livello_minimo_area` | Il livello d'area che l'operatore deve avere perché l'azione valga: `TUTTO` (default, l'azione scrive) o `LETTURA` (l'azione consulta o esporta). Mai `BLOCCATO`. Dal 04-10-2026 |

**Nota:** `permission_codename` fa le veci di `codice_interno` (chiave tecnica immutabile). Le azioni nascono nel codice Django (`Meta.permissions`) e questa tabella le rende visibili e gestibili nell'interfaccia admin.

---

### Relazioni

`config.azioni_processo` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `config.profili_accesso_azioni` | `azione_id` | Abilitazione azione per profilo |
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
| cambia_stato_preventivi | ⛔ **Ritirata** il 2026-10-25 (`attivo = false`): sostituita da `emetti_preventivo`, che ha ricevuto le sue concessioni. Il permesso di un passaggio di stato non è più un'azione per documento: sta sulla riga del passaggio — brief `brief-modello-documento-vendita` §8.9 | NO | vendite | 2026-05-02 |
| push_commessa_preventivi | Push preventivo a commessa per fatturazione | SI | vendite | 2026-05-02 |
| genera_pratica_preventivi | Genera pratica esecutiva da preventivo | NO | vendite | 2026-05-02 |
| documenti_template_manage | Gestione template e versioni documenti | NO | documenti | 2026-05-03 |
| documenti_asset_manage | Gestione asset documentali (logo, firma, CSS, allegati) | NO | documenti | 2026-05-03 |
| … | ⚠️ **Tabella parziale**: ferma al 2026-05-03 su 35 righe a catalogo (14-09-2026). La sede è il CSV `80_data/sql/config/azioni_processo.csv`; qui restano i casi che insegnano qualcosa | | | |
| code_manage | Gestione code di lavoro e stampa (vista e azioni cross-utente). ⭐ Il precedente su area `strumenti`: valutata da `DomainAPIView(area_funzionale="strumenti")` | NO | strumenti | 2026-07-21 |
| processo_avvia | Avvio manuale di un processo dall'interfaccia («Esegui ora» su una sveglia di deploy). ⛔ **Non** è `code_manage`: chi può riaccodare un lavoro non è per questo chi può avviare un giro. ⚠️ Conta solo se la view che la dichiara **non** è `AdminAPIView` (`IsAdminZeroERP` non legge `post_permission`) — brief `brief-db-avvio-manuale-di-un-processo` §8.2.2 | SI | strumenti | 2026-09-14 |
| emetti_preventivo | Emette un preventivo, o annulla un preventivo emesso o accettato. ⭐ L'azione sta sulla **riga del passaggio** della matrice (`config.transizioni_stati_preventivi.azione_processo_codename`): la chiedono il verbo `vendite.fn_cambia_stato_preventivo` e il backend, con la domanda intera `script.fn_doc_azione_passaggio`. Stessa forma di `emetti_ddt` (giro 5) — guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) | NO | vendite | 2026-10-25 |
| emetti_ordine | Emette (conferma) un ordine, o annulla un ordine confermato. Sulla **riga del passaggio** della matrice (`config.transizioni_stati_ordini.azione_processo_codename`), come `emetti_preventivo` e `emetti_ddt`; la chiede il verbo `vendite.fn_cambia_stato_ordine` — brief `brief-modello-documento-vendita` §9 | NO | vendite | 2026-10-25 |

---

### ⚠️ Catena di risoluzione azioni

(riscritta il 04-10-2026, brief-db-permessi-tetto-area)

```
1. Override utente sull'azione (abilita / nega)?   → si applica
   altrimenti il profilo (AD_HOC > REPARTO > PORTALE)
   altrimenti negata
2. E IN OGNI CASO il tetto d'area: l'azione vale solo se il livello
   dell'operatore sull'area dell'azione arriva a livello_minimo_area
```

Il super admin passa prima di tutto. Un'azione abilitata ma fermata dall'area
è **dormiente**, non cancellata. La catena è scritta una volta sola, in
[script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni).

---

> **"`config.azioni_processo` consente di controllare operazioni critiche con granularità puntuale, separatamente dal livello CRUD sull'area."**
