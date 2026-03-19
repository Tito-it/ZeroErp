## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_automazione_overlap`

> 👀 **Vedi anche**
>
Guide:    
> [Automazione DB](/guide/automazione-db)    
>
Approfondimento tabelle:    
> [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap)    
>
Approfondimento funzioni:
> [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap)    
---
### 🎯 Scopo Principale
(latest review 19-01-26)
La funzione **`dbops.fn_seed_automazione_overlap(p_schemas)`** popola (o aggiorna)
`dbops.automazione_overlap` rilevando automaticamente le tabelle con periodo di validita
(`valido_dal/valido_al` o `valid_from/valid_to`) e valutando se risultano versionate.

---

### Parametri di input

| Parametro   | Tipo   | Descrizione                           |
| ----------- | ------ | ------------------------------------- |
| `p_schemas` | text[] | Schemi target (NULL = ambito risolto). |

---

### Logica operativa (sintesi)

1. Risolve l'ambito tramite `dbops.fn_resolve_scope(p_schemas)`.
2. Esclude lo schema `storico`.
3. Per ogni tabella:
   * verifica la presenza delle colonne periodo;
   * rileva **EXCLUDE constraint** gia' presenti;
   * rileva **indici GiST** con `daterange`;
   * rileva **UNIQUE/PK** che includono il periodo.
4. Imposta:
   * `active=true` solo se la tabella e' considerata versionata;
   * `key_columns` se rilevabili;
   * `note` con il motivo dell'esito.
5. Scrive in `dbops.automazione_overlap` con upsert.

---

### Esempi

**Seed su ambito risolto:**

```sql
SELECT dbops.fn_seed_automazione_overlap();
```

**Seed su schemi specifici:**

```sql
SELECT dbops.fn_seed_automazione_overlap(ARRAY['vendite','catalogo']);
```

---

### Note

* Se la tabella ha colonne periodo ma non risulta versionata, `active` rimane `false`.
* Se le chiavi non sono rilevabili, `key_columns` rimane NULL e va completato manualmente.
* Le tabelle `storico` sono escluse dal seed.

---

{% include-markdown "signature-core.md" %}

---
