## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_create_indirizzo`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.stradario_generale](/dbzero/config/tabelle/stradario_generale)
> [config.stradario](/dbzero/config/tabelle/stradario)
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)
>
> Funzioni:
> [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) (figlia)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-done/analisi-fix-transazioni) (Classe D, finding #13)

### 🎯 Scopo Principale

(latest review 08-07-2026)

La funzione **`anagrafiche.fn_create_indirizzo`** è la **funzione madre atomica**
per la creazione di un indirizzo di dettaglio. Nel ramo *"via nuova"* fonde in
un'**unica statement**:

1. **upsert** `config.stradario_generale` (tipo strada + descrizione);
2. **upsert** `config.stradario` (strada + comune + CAP), sulla chiave delle vie **vive**: una via
   soppressa non si riusa, e se nel comune c'è solo lei nasce la via viva. Un indirizzo su una via
   soppressa passata per id lo rifiuta il guard del ritiro (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`);
3. risoluzione del dettaglio civico via
   [`fn_get_or_create_indirizzo_dettaglio`](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio).

Il service Python le eseguiva senza transazione unica: se il dettaglio falliva,
le righe stradario restavano committate (orfane nel registro). Impatto
contenuto — riga di dedup riutilizzabile, non corruzione — ma il ramo non aveva
alcun atomic. Qui o tutto o rollback.

---

### Firma

```sql
anagrafiche.fn_create_indirizzo(
    p_stradario_id       config.stradario.id%TYPE DEFAULT NULL,
    p_toponomastica_id   config.stradario_generale.toponomastica_id%TYPE DEFAULT NULL,
    p_descrizione_via    config.stradario_generale.descrizione%TYPE DEFAULT NULL,
    p_comune_id          config.stradario.comune_id%TYPE DEFAULT NULL,
    p_codice_postale_id  config.stradario.codice_postale_id%TYPE DEFAULT NULL,
    p_civico             integer DEFAULT NULL,
    p_estensione_civico  character varying DEFAULT NULL,
    p_palazzina          character varying DEFAULT NULL,
    p_scala              character varying DEFAULT NULL,
    p_piano              character varying DEFAULT NULL,
    p_interno            character varying DEFAULT NULL
) RETURNS bigint
```

### Parametri di Input

| Parametro | Descrizione |
| --- | --- |
| `p_stradario_id` | Se fornito, si usa questa strada e i parametri "via nuova" sono ignorati. |
| `p_toponomastica_id`, `p_descrizione_via`, `p_comune_id`, `p_codice_postale_id` | Ramo "via nuova" (usati solo se `p_stradario_id IS NULL`). |
| `p_civico` … `p_interno` | Dati del civico/dettaglio, passati alla figlia. |

Ritorna l'`id` dell'indirizzo di dettaglio (passthrough della figlia).

### Note tecniche

* **`SECURITY INVOKER`**: RLS/scope invariati. `zeroerp_app` ha `INSERT` su
  `config.stradario_generale`/`stradario` ed `EXECUTE` (PUBLIC).
* Upsert idempotenti (`ON CONFLICT`), come il repository Python.
* Le validazioni del ramo via-nuova (toponomastica/via/comune/CAP obbligatori)
  restano pre-check applicativi del service: non attengono all'atomicità.
