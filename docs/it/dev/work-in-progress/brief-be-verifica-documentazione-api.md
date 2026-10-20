# Brief BE — La documentazione API confrontata col codice

## ⏭️ Chi riparte — aggiornato al 2026-10-20 (sera)

**Riparte: Tid** — con le decisioni del blocco 🔴 A, poi il backend sui difetti del
blocco 🔴 B. La verifica (tutte le 17 aree) e la correzione della doc sono **chiuse**.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | Decidere le asimmetrie aperte | 🔴 A qui sotto | — |
| 2 | backend | Correggere i difetti di codice rimasti | 🔴 B qui sotto | — |
| 3 | backend | Verificare sul DB l'alert scadenze dei listini | 🔴 C | — |
| 4 | team DB | Classe di `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` | 🔴 D | — |
| 5 | backend | Ritoccare `copertura_doc_api` | 🔴 E | — |
| 6 | Tid | Rivedere e committare il lavoro del 2026-10-20 | 🔴 F | — |

---

## 🔴 COSA RESTA APERTO

### A. Decisioni di Tid (cambiano un contratto, alcune anche il frontend)

1. **`order_by` fuori whitelist**: in alcuni domini (anagrafiche) ripiega in silenzio
   sul default, in altri è un 400. Una regola sola? (§3.10)
2. **PATCH vuota**: 400 in fornitori ed emittenti, 404 in geo e soggetti. (§3.10)
3. **`page`/`page_size` in richiesta**: oggi `parse_list_params` li ignora in silenzio
   (si riceve la prima pagina); rifiutarli con 400? (§3.10)
4. **Nomi dei parametri**: `sort_by`/`sort_dir` sulle fatture del lotto contro
   `order_by`/`order_dir` ovunque; fondi-fattura ancora su `page`/`page_size`. Tocca
   il frontend. (§3.22)
5. **`Idempotency-Key` e `post_permission` non uniformi** fra endpoint gemelli
   (es. le azioni prezzo di commessa senza key, il cambio stato contratto senza
   `post_permission`). (§3.22)
6. **Booleani del trasporto a stringhe** (query string, multipart): `as_bool`
   (11 consumatori), `qp_bool`, `_parse_optional_bool` di amm-software,
   `_extract_metadati` di documenti — un valore fuori vocabolario vale `false` in
   silenzio. Vocabolario unico e 400? (§3.9)

### B. Difetti di codice da correggere (la regola c'è già)

1. **Date ancora ASC** perché la direzione è forzata prima del BB: lista ed export
   lotti (`_parse_lotti_query`: `order_dir or "asc"`), fatture del lotto (`sort_dir`
   default `"asc"`), lista attività di commessa (il service passa `"asc"`). (§6.1)
2. **Chiavi fuori contratto ancora scartate**: creazione emittente fiscale, PATCH di
   geo, indirizzi e pratica. (§6.2)
3. **`{"attivo": null}` disattiva un indirizzo** (`GeoService.update_indirizzo`). (§6.3)
4. **`dry_run` del cambio stato versione listino**: `"true"` stringa vale false
   senza 400. (§6.4)
5. **PUT profilo reparto**: voci `aree`/`azioni` non validate → 500. (§6.5)
6. **Override dei parametri senza `value`**: scrive un override vuoto, 200. (§3.6)
7. **`pratiche_service.py:537`** solleva a mano un codice ritirato. (§3.8)
8. **Note di un componente del catalogo** ignorano l'`articolo_id` del path. (§3.11)
9. **Gate L2 della variazione globale dei contratti** solo in PATCH, non in
   creazione. (§3.16)
10. **Schemi OpenAPI che non coincidono col codice**: i dieci lookup di
    `core/api/views_lookup.py` (`data` lista nuda), liste template/asset di documenti
    (`page`/`page_size`), `genera/` e POST template (201 invece di 200), request di
    `personalizza/` (2 campi su 5), `order_by` di `views_ordini`. (§2.1.4, §6.6)
11. Minori: docstring di `ApiLottoGruppiList` superata; motivo `PERMESSO_MANCANTE`
    della coda approvazioni irraggiungibile. (§6.7)

### C. Da verificare sul DB

1. **Alert scadenze dei listini**: probabile sfasamento di un giorno su
   `upper(validita)` di un daterange chiuso, che scarta il successore contiguo. (§3.14)

### D. Team DB

1. **`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` ha classe TECNICO** (500) per un
   errore di input dell'amministratore: dovrebbe essere DATO_ERRATO. Brief da
   scrivere. (§3.21)

### E. Strumento

1. **`copertura_doc_api`**: riconosce come esempio solo cifre e uuid (falsi fantasmi
   su `EF`, `CL`, `digest_presidi`) e conta come coperta una nota che dice «non
   documentate» (verso permissivo). (§4)

### F. Da committare — ⚠️ niente è committato

Tutto il lavoro del 2026-10-20 è nel working tree, che è **condiviso con un'altra
sessione** (dashboard, famiglie, `types.py`, …): al commit serve un `git add`
mirato. Il lavoro di questa verifica comprende:

- codice backend: `core` (BB in `db/_helpers.py`, `api/payload_validators.py`,
  `services/list_helpers.py`), `amm_software`, `anagrafiche`, `pratiche`,
  `pagamenti`, `vendite` (service, view, repository, il nuovo
  `services/_lotto_perimetro.py`) e i test relativi, compresi i file di test nuovi;
- `backend/scripts/tests/smoke-test-preventivi-componenti.sh` (tolto `iva_id`);
- doc: ~110 pagine `docs/it/backend/*/manual/`, `docs/it/dev/api.md`,
  `docs/it/dev/backend/catalogo-building-block-backend.md`, questo brief.

Il backend di sviluppo non si ricarica da solo: `kill -HUP` sul master di gunicorn.

---

## ✅ FATTO il 2026-10-20

- **Verifica** doc ↔ codice di tutte le 17 aree (§1, §2, §5).
- **Doc corretta**: tutte le pagine `manual/`; copertura **721/721 rotte**, 0 senza
  pagina, 5 «fantasmi» tutti falsi positivi noti; indice e regole in `api.md`;
  build della doc verde.
- **Codice corretto** (dettaglio in §3, punto per punto):
  - override operatore solo su credenziali OPERATORE, voci validate (§3.1);
  - righe di contratto e preventivo legate al documento dell'URL (§3.12);
  - flag del corpo solo booleani JSON, un BB solo (§3.13; §3.9 per il corpo);
  - gate L1 sulla PATCH dei componenti nei cinque documenti, gate L1 unico (§3.15);
  - campi obbligatori e codici del client inesistenti: 400 invece di 500 (§3.4-5);
  - satelliti del lotto e contesto-pricing: 404 invece di zeri o `{}` (§3.17);
  - filtri a vocabolario: 400 invece di lista vuota, BB `richiedi_codice_a_vocabolario`
    e registro degli specchi dei CHECK (§3.2, §3.19);
  - parametri morti delle righe di listino tolti (§3.20);
  - date DESC di default, anche riconosciute dal nome (§3.3, §3.18);
  - chiavi fuori contratto: 400 nei gemelli che le scartavano (§3.7, §3.22);
  - `ORIGINE_PREZZO_MANUALE` in una sede sola.
- **Verifiche**: suite backend verde (6347 test), ruff e mypy verdi, test DB verdi sul
  DB vero, a parte 3 guardrail rossi perché il DB di sviluppo è più avanti di git
  (codici `E_DOCUMENTI_*`, etichette del pannello config, `error_policies_generated.py`):
  da non rigenerare finché il lavoro DB non è in git.

---

## 1. Che cosa è stato verificato

Il 2026-10-20 Tid ha chiesto di verificare se la doc API coincide con lo
sviluppo effettivo, in ordine alfabetico di area.

- **Copertura formale.** `./manage-env.sh copertura_doc_api`; fatto datato
  2026-10-20: 720 rotte, 95% nominate, 36 scoperte, 6 fantasmi.
  ⚠️ Il comando misura solo se un path è **nominato**, non se la pagina è giusta.
- **Sostanza.** Per ogni pagina `manual/` che descrive endpoint sono stati
  confrontati view, service, repository ed `extend_schema`:
  - metodi;
  - parametri, paginazione e ordinamento;
  - campi ed envelope;
  - codici errore e status;
  - permessi.

  Analisi statica: nessuna chiamata HTTP; gli status sono dedotti dalla classe
  in `error_policies_generated.py`.
- **Perimetro:** tutte le aree, vendite compresa (vedi §5). acquisti e storico
  non hanno rotte, e la loro doc non ne promette.

Gravità:

- **ALTA** — chi segue la doc sbaglia la chiamata o il parsing;
- **MEDIA** — contratto incompleto (permessi, errori, default);
- **BASSA** — dettaglio.

---

## 2. Divergenze della documentazione — ✅ corrette (2026-10-20)

### 2.1 Difetti trasversali

1. **`page`/`page_size` nella doc, `limit`/`offset` nel codice** — ALTA.
   `parse_list_params` ignora `page`/`page_size` in silenzio, quindi si riceve
   sempre la prima pagina. Succede su categorie_clienti, articoli, template e
   asset di documenti; in documenti lo dice anche l'`extend_schema`.
2. **Default della paginazione 50 (o 100) nella doc, 25 nel codice**
   (`DEFAULT_LIMIT`) — MEDIA. Più di 12 pagine, fra core, amm-software,
   pagamenti, pratiche e documenti.
3. **«Ricerca sotto soglia → 400»**: dal 2026-09-26 il codice non lo dà più —
   MEDIA. Riguarda magazzino, la lista rate di pagamenti e la lista articoli.
4. **Schema OpenAPI con `data` dichiarato lista nuda**, mentre la risposta vera
   è `{data: {results}}` — ALTA per chi genera il client. Riguarda 10 view in
   `core/api/views_lookup.py`: merita un helper unico.
   In documenti lo schema dichiara 201 o 204 dove il codice risponde 200.
5. **Envelope vecchio `status` / `total` / `limit`** — ALTA. Riguarda
   `api_geo_config`, `api_indirizzi`, `api_soggetti`.
6. **Codici errore col nome sbagliato** — MEDIA:
   - in pratiche i codici sono senza prefisso `E_`, ritirati dal 2026-08-05;
   - in anagrafiche compaiono `E_AUTH_REQUIRED` ed `E_FORBIDDEN_ROLE`, che non
     esistono.
7. **Throttle della conferma via token**: la doc dice 3/15m, il codice usa
   10/15m (`ConfermaTokenRateThrottle`) — MEDIA. Riguarda reset password,
   invito operatore e invito portale/shop.
8. **«Ruolo ADMIN»**: oggi è il binding SUPER_ADMIN — BASSA.

### 2.2 Per area

| Area | ALTE | Pagine messe peggio |
| --- | --- | --- |
| admin / auth / portale / shop | 1 | `auth_views_audit.md`: il login vuole `email`, non `username` |
| ai-assistant | 2 | `api_ai_query.md`: azioni `confirm` e protocollo `__confirm__`/`__cancel__` non documentati |
| amm-software | 4 | lista e dettaglio operatori (`ruolo_sistema` ritirato, `*_reason` diventati codici), livelli `COMPLETO` invece di `TUTTO` |
| anagrafiche | ~15 | `api_soggetti`, `api_indirizzi`, `api_indirizzi_ruolo`, `api_geo_config`, `api_clienti`, `api_emittenti_fiscali`, `api_titoli_iva_soggetto` |
| catalogo | 3 | paginazione, `voce_utility` ritirato, conversioni UoM paginate |
| config | 0 | — |
| core | 0 | la sola divergenza ALTA sono gli schemi di §2.1.4 |
| documenti | 4 | modelli standard e `personalizza/` non documentati; «read-only v1» non è più vero |
| magazzino | 2 | blocca e libera merce non documentati |
| pagamenti | 0 | 5 MEDIE (`POST distinte/` non ha più `righe`, envelope di `ente_incasso`) |
| pratiche | 1 | `drift` nelle definizioni workflow non è mai `null` |
| ui | 3 | `Idempotency-Key` obbligatoria e non dichiarata, envelope `{results, count}` |

**Allineate:**

- core: `api_logout`, `api_permessi_effettivi`, `api_retry_policies`,
  `api_sessioni_attive`, `api_tipi_entita_lookup`;
- anagrafiche: `api_risorse_umane_lookup`;
- pratiche: quasi tutte (salvo i codici di §2.1.6).

---

## 3. ⚠️ Possibili difetti del **codice** — il dettaglio punto per punto (✅ corretto / ⏳ aperto)

Qui la doc dice una cosa giusta, o una regola del progetto, e il codice fa
altro.

1. ✅ **Corretto il 2026-10-20** (da committare): i sei metodi passano dalla guardia `get_operatore`, come le altre `operatori/{id}/`; il test DB `test_override_oggetti_catalogo_db` usava un utente di categoria SISTEMA ed e' passato a `fn_pgtap_crea_operatore_umano` — **amm-software, `operatori/<id>/override-{aree,azioni,oggetti}/`**: manca il
   controllo «credenziale di categoria OPERATORE». Un PUT scrive override anche
   su una macchina o un cliente del portale (`amm_software/api/views.py:215-262`).
2. ✅ **Corretto il 2026-10-20** (da committare), col gruppo «lista vuota invece di 400/404» — **pagamenti, `GET distinte/`**: un valore di `stato` / `origine` fuori
   vocabolario dà una lista vuota con 200. La doc promette il 400
   (`pagamenti_service.py:377-416`).
3. ✅ **Corretto il 2026-10-20** (da committare; Tid: «inferenza nel BB») — `sql_order_clause`: la colonna di default nominata da `parse_list_params` segue `default_desc`, ogni altra colonna data parte DESC anche riconosciuta dal NOME (`e_chiave_data`); i 13 `ORDER BY` composti a mano con `sql_order_direction` fanno lo stesso; `default_desc=True` su categorie-clienti-listini, pratiche e promo — **Date ordinate ASC di default**, contro la regola «date DESC»: lista pratiche
   e `categorie_clienti_listini`.
4. ✅ **Corretto il 2026-10-20** (da committare), con tutto il gruppo «500 invece di 400»: campi obbligatori del corpo dal BB in pratiche (9 punti) e preventivi (3), voci dei PUT di override validate prima del repository, `qp_int_optional` in `views_conti_bancari`, i tre id del pricing (`int(x or 0)`), e un codice scelto dal client che non esiste (`nuovo_stato`, tipo nota/allegato) e' un 400 sul campo invece del 500 di `E_CONFIG_MANCANTE` (BB `resolve_config_id_by_codice_interno` col `codice_errore` del chiamante). Smentiti alla verifica: `int()` grezzo e date delle offerte davano gia' 400 — **Campo obbligatorio assente → 500 invece di 400**, perché letto con
   `payload["x"]`: view di pratiche, item dei PUT di amm-software.
5. ✅ (con il punto 4) **`anagrafiche/api/views_conti_bancari.py:194`**: un `int()` grezzo su un
   query param dà 500. La gemella dei contatti usa `qp_int_optional`.
6. ⏳ **Aperto** (🔴 B6) — **Override dei parametri senza `value`**: scrive un override vuoto e risponde
   200.
7. ✅ **Corretto il 2026-10-20** (con il punto 22) — **POST clienti**: i campi ritirati vengono scartati in silenzio, mentre la
   PATCH li rifiuta.
8. ⏳ **Aperto** (🔴 B7) — **`pratiche_service.py:537`**: solleva a mano un codice ritirato.
9. **Booleani non rigorosi** — ⏳ *il corpo JSON e' risolto (2026-10-20, Tid: «corpo rigoroso, un BB»): `optional_bool` delle view delega a `PayloadValidator.optional_bool`. Resta il trasporto a stringhe: `as_bool` (11 consumatori, fuori vocabolario → False muto), `qp_bool`, `_parse_optional_bool` di amm-software e il multipart di `documenti/api/views.py` `_extract_metadati` — un vocabolario unico e 400 fuori vocabolario.* (`ok=abc` su job-runs, `is_active` operatori): ogni
   valore sbagliato vale `false`.
10. ⏳ **Aperto per decisione** (2026-10-20: Tid non ha scelto queste voci) — **Asimmetrie fra domini sullo stesso caso:**
    - un `order_by` fuori whitelist ricade in silenzio in un dominio e dà 400 in
      un altro;
    - una PATCH vuota dà 400 in un dominio e 404 in un altro;
    - `page`/`page_size` vengono ignorati invece che rifiutati.
11. ⏳ **Aperto** (🔴 B8) — Minore: le note di un componente del catalogo ignorano l'`articolo_id` del
    path.
12. *(da qui, vendite — §5)* ✅ **Corretto il 2026-10-20** (da committare) — **Riga fuori dal documento dell'URL.** `PATCH`/`DELETE` di una riga di
    contratto (`views_contratti.py:470,486`) o di preventivo
    (`preventivi_service.py:1178-1330, 1656-1673`) non verificano che la riga sia
    del documento indicato nell'URL: si può modificare o cancellare la riga di un
    altro documento. I gemelli (componenti, resi) il controllo lo fanno.
13. ✅ **Corretto il 2026-10-20** (da committare), insieme a tutti i flag del corpo letti con `bool(...)` o col test di verita' (17 punti, il piu' grave `is_super_admin` in creazione operatore) — **`chiudi_esistente` letto con `bool(...)`** (`views_offerte.py:524`): la
    stringa `"false"` vale True e attiva la successione, che chiude il contratto
    esistente.
14. ⏳ **Aperto** (🔴 C1) — **Alert scadenze dei listini, probabile sfasamento di un giorno.**
    `upper(validita)` su un daterange chiuso (`listini_repository.py:1044-1063`)
    fa uscire `valido_al` aumentato di 1 e scarta il listino successore
    contiguo. Da confermare sul DB.
15. ✅ **Corretto il 2026-10-20** (da committare; Tid: «gate L1 + unifica L1»): il gate L1 sta nel BB `dati_patch_componente` e vale per i **cinque** documenti, non solo il preventivo — mancava in tutti; `validate_componenti_overrides_authorization` delega a `check_permesso_override_prezzo` — **PATCH componente del preventivo senza il controllo
    `prezzo_override_manuale`** che la doc dichiara (TODO in
    `preventivi_service.py:1846-1886`).
16. ⏳ **Aperto** (🔴 B9) — **Gate L2 sulla variazione globale dei contratti: c'è solo in PATCH**, non
    in create (`contratti_service.py:802`).
17. ✅ **Corretto il 2026-10-20** (da committare): BB `lotto_visibile` su **tutti** i satelliti del lotto (anche fatture e gruppi, che davano `200 []`), contesto-pricing di contratto e preventivo dalla testata — **Lettura senza perimetro: zeri o `{}` invece di 404** su un documento
    inesistente o fuori perimetro:
    - lotto: segnalazioni, `segnalazioni/rows/`, `task-runs/`;
    - contesto-pricing di contratto e preventivo.
18. ✅ **Corretto il 2026-10-20** (vedi il punto 3) — **Ordinamento ASC di default nonostante `default_desc`.** La causa è
    `parse_list_params(default_order=…)` senza `colonne_desc`. Succede su
    ordini, resi e promo, probabilmente anche ddt e contratti, e sulle
    dashboard. Si estende il punto 3.
19. ✅ **Corretto il 2026-10-20** (da committare; Tid: due regole) — tabella: BB `richiedi_codice_a_vocabolario` (codici dismessi ammessi) su stato di **sei** liste documento + natura fattura + `entity_type` + stato distinte; CHECK: specchi + `validate_enum_param`, presidiati dal registro `test_specchi_dei_check_db` — **Vocabolari non validati → lista vuota:**
    - lista fatture (`natura_doc_codice`, `stato_codice_interno`);
    - giornale (`entity_type`);
    - fatture del lotto (`stato_esecuzione`);
    - offerte e ordini (`stato_codice_interno`);
    - attività di commessa (`stato_emissione`, `stato_approvazione`).

    Si estende il punto 2.
20. ✅ **Corretto il 2026-10-20** (da committare): tolti i parametri morti delle righe di listino (vista, service, repository, schema); `esclusa` delle fatture del lotto e' un errore della sola doc — **Filtri accettati e ignorati:**
    - righe di listino (`billing_account_id`, `utility_id`);
    - fatture del lotto (`esclusa`).
21. ⏳ **Aperto** (🔴 D1) — **`E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` ha classe TECNICO**, quindi
    risponde 500 a un errore di input. → brief al team DB.
22. ⏳ **In parte corretto il 2026-10-20** (da committare; Tid ha scelto la sola voce «chiavi ignote»): una chiave fuori contratto e' un 400 anche nei 13 punti che la scartavano (righe e prelievi DDT, testata/righe/rientri dei resi, testata e righe degli ordini, testata e righe dei preventivi) e nella creazione del cliente; verificato prima che il frontend mandi solo chiavi del contratto. Ancora da allineare alla stessa regola: la CREAZIONE di un emittente fiscale (`emittenti_fiscali_service`) scarta le chiavi fuori contratto, la sua PATCH le rifiuta. Restano aperte, per decisione: `sort_by`/`order_by`, `page`/`page_size` di fondi-fattura, `Idempotency-Key`/`post_permission` non uniformi — **Asimmetrie fra gemelli in vendite:**
    - `sort_by` sulle fatture del lotto contro `order_by` sui gruppi;
    - fondi-fattura ancora su `page`/`page_size`;
    - chiavi ignote rifiutate in un gemello e scartate nell'altro
      (preventivo/ordini/resi, prelievi DDT);
    - `Idempotency-Key` e `post_permission` presenti in modo non uniforme.

---

## 4. Rotte senza pagina e fantasmi — ✅ documentate tutte (2026-10-20)

- **Rotte senza pagina, confermate:**
  - amm-software: `override-oggetti/`, `permessi-riepilogo/`,
    `processi/<codice>/accensione/`, `processi/<codice>/identita/riattiva/`,
    `setup-status/`, più 4 rotte `processi/…` che la pagina stessa dichiara non
    documentate;
  - anagrafiche: `billing-account/<id>/utilities/`, `istanze-utility/<id>/lookup/`;
  - catalogo: `articoli/<uuid>/uom/lookup/`;
  - documenti: `templates/<id>/personalizza/`, `asset/<id>/miniatura/`;
  - magazzino: `disponibilita/blocchi/` (POST) e `…/<id>/libera/`;
  - pratiche: `flussi/<id>/pratica/`.
- **Fantasmi:** nessuno è vero.
  - 4 sono falsi positivi del comando: esempi con un valore concreto (`EF`,
    `CL`, `digest_presidi`) e un riferimento storico (`/auth/token/`);
  - gli altri 2 sono lapidi di endpoint ritirati.
- **Il comando `copertura_doc_api`**, da ritoccare:
  - riconosce come esempio solo le cifre e gli uuid;
  - conta come coperta una nota che dice «queste rotte non sono documentate».
    È il verso permissivo.

---

## 5. Vendite

Verificata il 2026-10-20 con lo stesso metodo, in 6 gruppi di sotto-risorsa.
I difetti trasversali di §2.1 ci sono quasi tutti, soprattutto i punti 2, 4 e 5.
I possibili difetti di codice sono in §3, dal punto 12 al 22.

| Gruppo | ALTE | Pagine messe peggio |
| --- | --- | --- |
| approvazioni-prezzo / commesse / contratti | 3 | `api_contratti` (BA/istanza oggi modificabili in bozza, whitelist `order_by`), `api_commessa_attivita` (`count` è il totale) |
| dashboard / ddt | 4 | `api_ddt` (filtri `stato_codice_interno`/`data_a`, `utility_id` → 400), `api_dashboard_competenza`, `api_dashboard_backlog` (`ritardo_giorni`) |
| famiglie / fatturazione / fatture / fondi / giornale / iva | 0 | `api_fatturazione` (`lotti[]` su numera, status di `…_INCOERENTE` 422), `api_fattura_dettaglio` (`rettifiche`) |
| listini / lookup / lotti / pipeline / pricing / promo / registri | ~9 | `api_listini` (paginazione, `emittente_soggetto_ruolo_id` obbligatorio, rotta bundle inesistente), `api_lotto_fatture_list`, `api_lotto_segnalazioni_summary`, `api_lotto_task_runs`, reset del lotto (semantica cambiata) |
| eccezioni-offerta / offerte / ordini | 3 | `api_offerte` (`solo_ultima_revisione`, envelope lista e revisioni), `api_ordini` (whitelist, `iva_id` scartato) |
| preventivi / resi / righe | 6 | `api_preventivi` (`solo_ultima_revisione`, paginazione, revisioni, `fatturazione_immediata` all'accettazione, whitelist componente) |

Fra gli errori ricorrenti, gli status sono spesso scritti 422 dove la classe dà
400 o 409. In più, varie POST che sono letture dichiarano «LETTURA basta» ma
chiedono TUTTO, perché manca `post_accesso="view"`.

**Rotte senza pagina (vendite):**

- `commesse/<id>/registro/`;
- prelievi DDT;
- rientri, `chiudi-riconsegna` e `riapri-riconsegna` dei resi;
- componenti delle eccezioni d'offerta e `preview-componenti/`;
- `offerte/<id>/contratto-sovrapposto/`;
- `ordini/form-defaults/`;
- `preventivi/da-pratica/<id>/stato/`, `preventivi/<id>/riepilogo-iva/`,
  `DELETE preventivi/<id>/`;
- lotti: `documenti/escludi/`, `riporta-a-draft/`, `segnalazioni/rows/`,
  `mensile/` e gli export;
- `pricing/diagnose/`;
- `DELETE listini/.../bundle/<padre_id>/`.

Le `…/righe/lista/export/` sono invece coperte in modo generico da
`api_righe_documento.md`.

---

## 6. Residui di backend emersi correggendo la doc (2026-10-20) — ⏳ aperti, vedi 🔴 B

La doc descrive il codice com'è; questi punti sono difetti del codice, da decidere
o correggere:

1. **Date ancora ASC**, contro la regola di §3.3, perché la direzione e' forzata a
   monte del BB: lista ed export lotti (`_parse_lotti_query`: `order_dir or "asc"`),
   fatture del lotto (`sort_dir` default `"asc"`), lista attivita' di commessa (il
   service passa `order_dir="asc"`).
2. **Chiavi fuori contratto ancora scartate**: creazione emittente fiscale, PATCH di
   geo e indirizzi, PATCH della pratica.
3. **`{"attivo": null}` disattiva un indirizzo** (`GeoService.update_indirizzo`:
   `optional_bool` con default False).
4. **`dry_run` del cambio stato versione listino** (`listini_service.py`): `is True`,
   una stringa `"true"` vale false senza 400.
5. **PUT profilo reparto**: le voci di `aree`/`azioni` non sono validate, una chiave
   mancante e' un 500 (gemello degli override operatore, corretti in §3.1).
6. **Schemi OpenAPI che non coincidono col codice**: `ApiTemplateList`/`ApiAssetList`
   (`page`/`page_size`), `DocumentoGenera` e `ApiTemplateList.post` (201 invece di 200),
   la request di `ApiTemplatePersonalizza` (2 campi su 5), `order_by` di `views_ordini`,
   e i dieci lookup di `core/api/views_lookup.py` (§2.1.4).
7. Minori: docstring di `ApiLottoGruppiList` superata («elenco vuoto», ora 404); il
   motivo `PERMESSO_MANCANTE` della coda approvazioni e' irraggiungibile.
