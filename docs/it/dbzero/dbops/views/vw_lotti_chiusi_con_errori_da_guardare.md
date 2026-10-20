# 🔍 View `vw_lotti_chiusi_con_errori_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i lotti chiusi COMPLETATO che contengono documenti in ERRORE. DEVE restare VUOTA. ⭐ E' un LETTORE: la contraddizione la definisce vendite.vw_lotti_chiusi_con_gruppi_in_errore, qui si aggiungono solo lo stato fiscale (vw_lotti_fase) e l'emittente, per chi arriva dal digest. ⭐ Le due porte: COMPLETATO su un lotto fermo lo rifiuta il database (trg_fatturazione_lotti_a10_guard_completato_upd, 2026-09-23); resta aperta quella dell'ESITO — un documento marcato ERRORE su un lotto gia' COMPLETATO — ed e' cio' che questa riga sorveglia. Un lotto ANNULLATO non compare perche' l'annullo gli chiude gli esiti (fn_annulla_lotto_da_draft, rev 2026-09-23), non perche' qualcuno lo filtri. ⚠️ In dbops e non in vendite: iscrivere a catalogo una vista di vendite porterebbe l'intero schema nel perimetro di test-catalogo-presidi-v1 (test 2). ⛔ Perimetro DEFINER a catalogo: le tabelle sotto hanno la RLS e le viste sono security_invoker — da una sessione senza GUC risponde zero PER CECITA', il digest conta da proprietario con fn_conta_presidio, una persona legge col proprio perimetro. Brief: brief-db-annullamento-chiude-la-vita §9.6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_lotti_chiusi_con_errori_da_guardare
WITH (security_invoker=true) AS
SELECT c.lotto_id,
    c.lotto_codice,
    c.competenza_mese,
    c.stato_lotto,
    f.stato_codice_interno,
    c.emittente_soggetto_ruolo_id,
    ef.codice AS emittente_codice,
    c.gruppi_in_errore,
    c.primo_errore,
    c.ultimo_errore,
    c.codici_errore
   FROM ((vendite.vw_lotti_chiusi_con_gruppi_in_errore c
     LEFT JOIN vendite.vw_lotti_fase f ON ((f.lotto_id = c.lotto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
