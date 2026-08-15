# Consuntivo — Personalizzazioni liste, sviluppi DEF atterrati

> **Tipo**: consuntivo · **Chiuso**: 2026-08-09 · **Origine**:
> `sviluppo-personalizzazioni-liste_def.md` (roadmap DEF-1..DEF-10), che resta in
> `work-in-progress` con le sole voci ancora aperte.
> **Piano madre**: [sviluppo-personalizzazioni-liste.md](sviluppo-personalizzazioni-liste.md) (Blocchi A..F).
>
> **Perché questo documento esiste.** La roadmap DEF dichiarava DEF-8 «in corso, 7
> liste migrate, ~7 residue». Alla verifica del 2026-08-09 le liste a catalogo
> sono **43**: il documento era rimasto indietro di un fattore sei, e continuava a
> descrivere come «da fare» cose atterrate mesi fa. Le voci chiuse vivono qui col
> numero misurato; quelle aperte restano nel documento originale, corto.

---

## 1. Lo stato misurato (2026-08-09)

Numeri presi dal database e dal codice vivi, non dalle dichiarazioni dei brief.

| Misura | Valore |
| --- | --- |
| Liste a catalogo (`ui.lista_definizione`) | **43** |
| Colonne a catalogo (`ui.lista_colonna`) | **457** |
| Preset di sistema (`ui.lista_preset`) | **43** |
| Componenti FE che montano `<ListaConfigurabile>` | **~41** (44 file, meno i 3 del building block stesso) |
| Preferenze utente salvate (`ui.lista_preferenza_utente`) | 7 |
| Grant per colonna (`ui.lista_colonna_permesso`) | **0** — vedi §4 |

Distribuzione per area: `vendite` 20 · `anagrafiche` 9 · `config` 5 · `catalogo` 4 ·
`documenti` 2 · `pratiche` 1 · `storico` 1 · `dbops` 1.

## 2. Le voci chiuse

### DEF-8 — Estensione ad altre liste ✅

Il documento la dava «in corso» con **7 liste migrate e 7 residue on-demand**,
elencando come da fare `indirizzi, articoli, unita-misura, listini,
promo-articoli, approvazioni-prezzo, pratiche`.

**Sono a catalogo tutte e sette**, e con esse altre trenta. La formula «non sarà
mai 100%, si migra a ticket» descriveva un'intenzione che i fatti hanno superato:
il pattern è diventato lo standard di ogni lista nuova, non una migrazione
selettiva. Il presidio del binario e la copertura per gruppi sono raccontati
nell'handoff del 2026-08-03.

### DEF-1 — Export CSV/Excel ✅ (ben oltre il perimetro dichiarato)

Chiuso il 2026-05-10 «per clienti», con l'estensione rinviata a DEF-8. Oggi
l'export è su **dieci domini** — clienti, soggetti, fornitori, contratti, ordini,
offerte, DDT, resi, preventivi — e la parte invariante è stata estratta nel
building block `apps.ui.api.export_helpers` (`parse_export_format`,
`build_export_response`) accanto al renderer puro `ListaExportService`.

### DEF-2 — Notifica «preset aggiornato» ✅

Chiuso 2026-05-11 (BE + FE). Il banner vive dentro `ListaConfigurabile`, quindi
ogni lista migrata lo eredita senza codice proprio.

### DEF-5b — Fase 2 Blocco F: CRUD `lista_definizione` + `lista_colonna` ✅

Chiuso 2026-05-10.

> ⚠️ Il documento originale conteneva una **contraddizione interna**: la tabella
> di sintesi dava DEF-5b «Done 2026-05-10», mentre la sezione DEF-5 più sotto
> continuava a dichiarare «Stato Fase 2: 🔴 Todo». La riga giusta è la prima.

### DEF-6 — Comportamento su schermi piccoli ✅

Chiuso 2026-06-20 con una **decisione**, non con del codice: niente card-list, si
resta su tabella + kebab responsive.

### DEF-10 — Colonne composte FE-only ✅ di fatto

Il documento lo dava «parziale, esiste come trick». È diventato un pattern
regolare e documentato nei seed: colonna a catalogo con `campo_sorgente` vuoto e
resa nello slot `cell-{codice}` del caller. Consumatori attuali: `CodaLavoriTab`,
`OperatoriListView`, `AuditLogView`, oltre al capostipite `sosp_riatt` dei
clienti.

Resta aperta solo la domanda di **forma**, non di sostanza: se formalizzarlo come
`tipo_colonna='composta'` insieme a DEF-7. Vedi il backlog.

## 3. Le convenzioni acquisite (valgono per ogni lista nuova)

Trasferite qui perché sono la parte del documento che si continua a consultare.

1. **Pattern lista standard** + `<ListaConfigurabile>`: toolbar unica esterna del
   caller con `PageActionsBar`, `paginatorOptions="paginatorProps"` da
   `useSearchTable`, slot `cell-{codice}` per le celle complesse.
2. **`defineExpose` auto-unwrappa i ref**: `listaRef.value.config`, mai
   `.config.value`.
3. **Catalogo eager**: `useListaConfig.load()` carica config e catalogo in
   parallelo — senza catalogo, al primo render mancano etichette e
   `campo_sorgente`.
4. **Etichette i18n sotto la radice d'area** (`anagrafiche.clienti.col_*`,
   `vendite.contratti.col_*`) o `common.*` se trasversali. La forma piatta
   `lista.*` è **vietata** e il guard `scripts/check_i18n_keys.py` la
   segnalerebbe come radice di dominio in cima.
5. **Azioni di lista** in `PageActionsBar` con `kind:'utility'`: su touch
   finiscono nel kebab da sole. Solo `kind:'primary'` resta sempre visibile.
6. **`campo_sorgente` e colonne generate**: se la tabella espone una colonna
   `GENERATED ALWAYS` che compone più campi (es.
   `id_fiscale_univoco_cf_piva`), il seed deve puntare a **quella**, non al
   singolo campo nativo.
7. **`sensibile` è una deny-list**: `ui.fn_resolve_lista_config` **rimuove dal
   payload** le colonne `sensibile=true` senza grant esplicito — e ci cade anche
   il SUPER_ADMIN, perché il filtro è nella funzione DB, non nella permission
   class. Usarlo solo con una restrizione reale, e in quel caso seedare anche i
   grant.

## 4. Una capacità costruita e mai usata

`ui.lista_colonna_permesso` ha **zero righe**. Il meccanismo dei permessi per
colonna (Blocco F Fase 1, atterrato il 2026-05-08) è completo e funzionante, ma
nessuna colonna è oggi marcata `sensibile` con grant.

Non è un difetto: è capacità disponibile e mai chiamata in causa. Vale però
saperlo per due ragioni — il codice che la implementa non è esercitato da nessun
dato reale (vedi il caveat §3.7 sul filtro che vale anche per il SUPER_ADMIN), e
se un giorno servisse una restrizione per colonna non c'è nulla da costruire.
