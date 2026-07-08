## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_pratica_da_preventivo`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
>
> Funzioni:
> [pratiche.fn_crea_pratica](/dbzero/pratiche/funzioni/fn_crea_pratica) (figlia condivisa)
> [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-in-progress/analisi-fix-transazioni) (Classe A, finding #3)

### 🎯 Scopo Principale

(latest review 08-07-2026)

La funzione **`vendite.fn_genera_pratica_da_preventivo`** è la **funzione madre
atomica** che genera una pratica a partire da un preventivo e la collega come
`ROOT` in `pratiche.pratiche_sorgenti`.

Il service Python eseguiva `crea_pratica()` (committa a sé) e poi
`link_pratica()` in transazioni separate: se il link falliva, la pratica
restava committata → **pratica orfana** mai collegata al preventivo. Qui
risoluzione contesto + creazione pratica + link sono un'unica statement.

**Composizione:** la creazione pratica è delegata alla figlia condivisa
[`pratiche.fn_crea_pratica`](/dbzero/pratiche/funzioni/fn_crea_pratica); questa
madre fa solo la parte specifica del dominio preventivo (risolve
emittente/soggetto/uid dal preventivo e inserisce il link).

---

### Firma

```sql
vendite.fn_genera_pratica_da_preventivo(
    p_preventivo_id       vendite.preventivi.id%TYPE,
    p_tipo_prestazione_id pratiche.pratiche.tipo_prestazione_id%TYPE,
    p_priorita_id         pratiche.pratiche.priorita_id%TYPE DEFAULT NULL,
    p_descrizione         pratiche.pratiche.descrizione%TYPE DEFAULT NULL
) RETURNS TABLE (
    pratica_id pratiche.pratiche.id%TYPE
)
```

### Flusso

1. Legge il contesto dal preventivo (uid, billing_account, istanza). Preventivo
   inesistente ⇒ **`E_PREV_NOT_FOUND`**; senza billing account ⇒
   **`E_PREV_VALIDAZIONE`**.
2. Risolve emittente (`fn_get_emittente_fiscale_pk`), soggetto e ruolo dal BA, e
   il tipo sorgente `PREVENTIVO` (`config.sorgenti`; se assente ⇒
   **`E_CONFIG_MANCANTE`**).
3. Crea la pratica via `pratiche.fn_crea_pratica`.
4. Inserisce il link `ROOT` preventivo → pratica in `pratiche_sorgenti`.

### Note tecniche

* **`SECURITY INVOKER`**: RLS/scope valutati come dal Python.
* Il link `ROOT` ha `flusso_id` NULL (la decisione D-B sul `flusso_id` riguarda i
  link `COLLEGATO`, non il `ROOT`).
* Il check di dominio «preventivo in stato ACCETTATO» resta un pre-check
  (read-only) del service: non attiene all'atomicità (la causa del finding).
* Il tipo sorgente è risolto per `codice_interno` senza filtrare `attivo`:
  l'attività è imposta dal trigger `require_attivo` sul link (unica autorità).
