## 📘 Documentazione Concettuale – Funzione `script.fn_get_identita_sr_perimetro(...)`

> 👀 **Vedi anche**
>
> [fn_resolve_controparte_sr_id](fn_resolve_controparte_sr_id.md) — il soggetto della riga
> [fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — «utilizzabile oggi»
> [fn_scope_ef_perimetro](fn_scope_ef_perimetro.md) — la stessa forma, per l'operatore
> [Linee guida SQL — §10 RLS](/linee-guida-sql#10-row-level-security-rls)
>
> Brief: `brief-db-perimetro-una-volta-famiglie-residue` §6 (giro 2)

---

### 🎯 Scopo Principale

(nata il 2026-10-21, `20261021-29`)

**Che cosa può vedere chi guarda da controparte?** Le vesti di controparte
(`CLIENTE_PORTALE`, `SHOP_CUSTOMER`, `FORNITORE_PORTALE`) vedono solo le righe del
**proprio** soggetto. Questa funzione restituisce quel soggetto (`soggetto_ruolo_id`
dell'identità), se l'identità è in una delle vesti indicate ed è utilizzabile oggi.
Altrimenti restituisce `NULL`, e la policy non mostra niente.

La risposta **non dipende dalla riga**. La policy la chiede una volta per
istruzione, in una sottoquery, e per ogni riga confronta soltanto:

```text
fn_scope_sr_perimetro(
    (SELECT fn_get_identita_sr_perimetro(<identità>, ARRAY['<veste della policy>'])),
    <soggetto della riga>)
```

`script.fn_scope_sr_perimetro` è il confronto: puro, incorporato dal
pianificatore, `false` quando uno dei due manca. Il soggetto della riga, quando la
riga non lo porta già, lo dà [`fn_resolve_controparte_sr_id`](fn_resolve_controparte_sr_id.md).

⚠️ **Convenzione opposta a quella dell'operatore**: qui `NULL` vuol dire
**nessuno** (una controparte non ha mai «tutto»); nel perimetro dell'operatore
`NULL` vuol dire tutti (il super admin).

⭐ La policy passa **la propria veste**: l'identità deve essere quella della
sessione. Il middleware imposta `app.ruolo_applicativo` e
`app.current_identita_id` dalla stessa riga di `identita_digitali`, quindi in un
contesto coerente le due coincidono; un contesto incoerente non vede niente.

---

### Parametri e risultato

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_identita_id` | `anagrafiche.identita_digitali.id%TYPE` | L'identità della sessione. |
| `p_vesti` | `config.ruolo_applicativo[]` | Le vesti ammesse. |

Risultato: `anagrafiche.identita_digitali.soggetto_ruolo_id%TYPE`, oppure `NULL`.

### Chi la usa

* le policy del cliente portale su billing account, clienti e fatture
  (`20261021-32`) e la policy shop del billing account;
* `fn_scope_ba_ownership`, `_via_fattura` e `_via_fattura_sdi`, che la compongono
  per la domanda su una riga sola (`20261021-31`).

Presidio: `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1` (test 1, 3,
4 e 6: forma, piano e debito delle famiglie ancora per riga).

---

{% include-markdown "signature-core.md" %}
