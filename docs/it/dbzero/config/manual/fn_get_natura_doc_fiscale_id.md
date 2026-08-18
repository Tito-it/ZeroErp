## 📘 Documentazione Concettuale – Funzione `config.fn_get_natura_doc_fiscale_id(...)`

> 👀 **Vedi anche**
>
> [config.nature_doc_fiscale](nature_doc_fiscale.md) ·
> [vendite.fn_get_registro_id](/dbzero/vendite/funzioni/fn_get_registro_id) ·
> [vendite.fn_accredita_riga_reso](/dbzero/vendite/funzioni/fn_accredita_riga_reso)
>
> Brief autorevole: `docs/it/dev/work-in-progress/brief-design-note-credito-resi.md` (slice N1)

---

### 🎯 Scopo Principale

(rev 2026-08-18)

L'`id` della natura fiscale di un documento **a partire dalla sua chiave
naturale stabile** (`codice_interno`).

Tre righe di SQL, e una ragione precisa per esistere.

---

### Perché esiste: un DEFAULT non ammette sottoquery

Le tre colonne `natura_doc_id` (su `commesse_attivita`, `attivita_fatturabili`,
`fatture`) e quella su `tipi_doc_fiscale_registri` nascono
**NOT NULL DEFAULT «FATTURA»**. Un `DEFAULT` di colonna non può contenere una
sottoquery, quindi le alternative erano due: scrivere l'`id` a mano nel DDL,
oppure chiamare una funzione.

⛔ **L'id a mano viola la regola delle chiavi naturali stabili**
(linee-guida-sql §6b): l'`id` è dettaglio implementativo, soggetto a reseed; la
chiave naturale è `codice_interno`, immutabile per lock. Un `DEFAULT 1`
sopravvive finché nessuno ricostruisce il catalogo, e il giorno in cui qualcuno
lo fa **tutte le fatture nuove nascono con la natura sbagliata** — in silenzio,
perché un id resta un id valido.

⭐ Con la funzione il `DEFAULT` si legge come la regola che è:

```sql
ADD COLUMN natura_doc_id bigint NOT NULL
    DEFAULT config.fn_get_natura_doc_fiscale_id('FATTURA')
```

---

### ⚠️ Perché risponde `NULL` invece di sollevare

È un `fn_get_*`, non un `fn_guard_*`: **legge e risponde**. Se la riga non c'è
risponde `NULL`, e sulle colonne consumatrici il `NOT NULL` trasforma quel
`NULL` in un errore **nel punto giusto** — cioè sulla scrittura che sarebbe
rimasta senza natura.

E c'è una ragione tecnica che rende la scelta obbligata: sollevare vorrebbe dire
una funzione `VOLATILE` (`script.fn_log_and_raise_error` scrive), e una
`VOLATILE` dentro il `DEFAULT` di un `ADD COLUMN` toglie a PostgreSQL la
scorciatoia del *fast default*: **riscriverebbe l'intera tabella**.

`STABLE` e non `IMMUTABLE`: legge una tabella, e il suo contenuto può cambiare
fra due transazioni.

---

### Chi la usa, e come

| Chiamante | Perché |
|---|---|
| il `DEFAULT` delle quattro colonne `natura_doc_id` | risolve «FATTURA» senza cablarne l'id |
| `vendite.fn_get_registro_id` | normalizza il parametro natura quando arriva `NULL` |
| `vendite.fn_upsert_commessa_attivita` | stesso, sul parametro `p_natura_doc_id` |
| `vendite.fn_accredita_riga_reso` | risolve `NOTA_CREDITO` per la rettifica che sta creando |

⚠️ **Nei chiamanti che devono fallire**, il `NULL` viene tradotto in
`E_CONFIG_MANCANTE` subito dopo la `COALESCE`: la funzione non solleva, ma
nessuno la lascia rispondere `NULL` in silenzio.

---

### Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `p_codice_interno` | `config.nature_doc_fiscale.codice_interno%TYPE` | chiave naturale stabile: `FATTURA`, `NOTA_CREDITO`, `NOTA_DEBITO` |

### 📦 Output

| Tipo | Descrizione |
|---|---|
| `config.nature_doc_fiscale.id%TYPE` | l'id della natura, oppure `NULL` se il codice non esiste **o è disattivato** |

---

### Esempio d'uso

```sql
-- Il default di una colonna, senza cablare un id
ALTER TABLE vendite.fatture
    ADD COLUMN natura_doc_id bigint NOT NULL
        DEFAULT config.fn_get_natura_doc_fiscale_id('FATTURA');

-- Dentro una funzione: risolvere e non lasciar passare il NULL
v_natura := COALESCE(p_natura_doc_id,
                     config.fn_get_natura_doc_fiscale_id('FATTURA'));
IF v_natura IS NULL THEN
    PERFORM script.fn_log_and_raise_error(..., 'E_CONFIG_MANCANTE', ...);
END IF;
```

---

{% include-markdown "signature-core.md" %}
