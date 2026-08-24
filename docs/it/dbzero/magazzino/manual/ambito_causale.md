## 📘 Documentazione Concettuale – Tabella `magazzino.ambito_causale`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.causali](/dbzero/magazzino/tabelle/causali)
> • [config.ambiti](/dbzero/config/tabelle/ambiti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Vocabolario degli ambiti delle causali**: `VENDITE`, `ACQUISTI`, `ODL`, `TRASF`,
`INVENTARIO`, `GENERICO`. Sei voci da seed — con `causali` è l'unico oggetto popolato dello
schema.

Serve a raggruppare le causali per **origine del movimento**, cioè per rispondere alla domanda
«da quale processo nasce questa scrittura».

---

### ⚠️ Non ha nulla a che vedere con `config.ambiti`

È un vocabolario **autonomo**: nessuna FK verso `config.ambiti`, che è **vuota e non
referenziata da nessuno**. La FK reale è

```sql
magazzino.causali.ambito_causale_id  →  magazzino.ambito_causale(id)
```

⚠️ I due nomi si somigliano abbastanza da trarre in inganno — è successo scrivendo la prima
versione della pagina di `config.ambiti`, corretta il 2026-08-21 verificando `pg_constraint`.
Quando si cercano «gli ambiti», questa è la tabella giusta.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
