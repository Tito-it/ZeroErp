# Brief DB — L'ereditato dei permessi coincide col resolver (pgTAP) · e la veste che non si filtra

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-25. **A chi:** Tid
> (decisioni, §4), poi team DB (`dev/db-tid`) e backend per la ricaduta.
> **Origine:** [piano-be-fe-ui-permessi-operatore.md](piano-be-fe-ui-permessi-operatore.md),
> stato in testa: *«la versione durevole è un pgTAP, ed è da chiedere al team
> DB»*. Analisi madre:
> [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §7.7.
> **Stato:** ✅ **D-1 e D-2 decise da Tid il 2026-09-25** (§4): come proposto.
> Passa al team DB per §2 e §3; la ricaduta BE (§5) segue il DB.
>
> **In una riga:** il pannello permessi mostra per ogni area e azione il valore
> **ereditato** dal profilo, con una query del backend che ripete lo spareggio
> dei resolver. Serve un presidio a DB che provi che le due letture coincidono.
> ⚠️ Mentre scrivevo il brief è emerso un **difetto di modello**: i resolver da
> operatore contano anche i profili delle **altre vesti** dell'utente (§3).

---

## 1. Cosa c'è oggi

`GET /amm-software/operatori/<id>/permessi-ereditati/` →
`AmmSoftwareRepository.get_permessi_ereditati`
([amm_software_repository.py:982](../../../backend/apps/amm_software/db/amm_software_repository.py#L982)):

```sql
SELECT DISTINCT ON (paa.area_id) paa.area_id, paa.livello, pa.descrizione, pa.tipo
  FROM script.fn_get_profili_accesso_applicabili(%s) h
  JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = h.profilo_accesso_id
  ...
 ORDER BY paa.area_id, h.priorita
```

(e la gemella su `config.profili_accesso_azioni`).

La **fonte** dei profili è la stessa dei resolver
(`fn_get_profili_accesso_applicabili`). Ma lo **spareggio** (`DISTINCT ON … ORDER
BY priorita`) è una seconda scrittura del passo 4 di `fn_resolve_livello_area` e
di `fn_check_azione_processo` (`ORDER BY h.priorita LIMIT 1`, per area/azione).

Oggi lo presidia solo un test Django che legge l'**SQL generato** e controlla
che usi la funzione e ordini per `h.priorita`. Il confronto col resolver è stato
fatto **a mano** il 2026-09-05. In questo repo nessun test Django tocca un DB
reale, quindi il confronto vero può stare solo in pgTAP.

---

## 2. La richiesta: portare l'ereditato a DB e provarlo contro i resolver

Un pgTAP non può leggere una query che vive in un file Python. Se la si copiasse
nel test, le copie diventerebbero **tre**. La forma che toglie la copia invece
di presidiarla (*si sposta la sede, non si copia*):

1. **Funzione nuova** `script.fn_get_permessi_ereditati(p_auth_user_id integer)`
   (nome a scelta del team DB). Restituisce le righe di aree e azioni con
   `tipo_voce` (`AREA` | `AZIONE`), `voce_id`, `livello` (aree), `abilitata`
   (azioni), `profilo_id`, `profilo_nome`, `profilo_tipo`. Lo spareggio lo
   scrive **una volta**, con lo stesso criterio del passo 4 dei resolver.
2. **pgTAP** `db/pgtap/script/test-fn-get-permessi-ereditati.sql`, casi al §2.1.
3. **Ricaduta BE** (la facciamo noi): `get_permessi_ereditati` chiama la
   funzione e perde le due query. Il contratto JSON dell'endpoint non cambia.

### 2.1 I casi del pgTAP

L'uguaglianza vale **per costruzione** solo dove il resolver arriva al passo 4:
utente con identità `OPERATORE` attiva, non super admin, senza override su
quella voce. I casi:

| # | Fixture | Atteso |
| --- | --- | --- |
| 1 | Operatore con solo un profilo `REPARTO` | Per **ogni** area del catalogo: `fn_resolve_livello_area` = livello ereditato, oppure `BLOCCATO` dove l'ereditato manca |
| 2 | Idem per le azioni | `fn_check_azione_processo` = `abilitata` ereditata, oppure negata dove manca |
| 3 | Operatore con `AD_HOC` **e** `REPARTO` sulla stessa area, livelli diversi | Vince l'`AD_HOC` in **entrambe** le letture, e `profilo_tipo = 'AD_HOC'` |
| 4 | Area coperta da un profilo di priorità più bassa e non da quello più alta | Entrambe le letture scendono al profilo più basso, perché lo spareggio è **per voce** e non per utente |
| 5 | Operatore **multi-veste**: `OPERATORE` + `SHOP_CUSTOMER`, con un profilo `PORTALE` e uno `REPARTO` sulla stessa area, livelli diversi (vedi §3) | Per D-1: in **entrambe** le letture conta **solo** il profilo `REPARTO`; il profilo della veste cliente non compare nell'ereditato. Oggi è il caso che fallisce |
| 6 | Utente senza profili | Ereditato vuoto; resolver `BLOCCATO` / negata ovunque |

⚠️ Il caso 1 va fatto **su tutto il catalogo** (`config.aree_funzionali` e
`config.azioni_processo` attivi), non su due voci scelte: il presidio deve
accorgersi di un'area nuova (dal 05-09 sono arrivate `ai_assistant` e un'azione
di `magazzino`).

---

## 3. 🔴 Trovato strada facendo: i profili delle altre vesti entrano nei permessi da operatore

I quattro resolver da operatore — `fn_resolve_livello_area`,
`fn_check_azione_processo`, `fn_get_user_permissions_map`,
`fn_get_user_actions_map` — chiamano

```sql
script.fn_get_profili_accesso_applicabili(p_auth_user_id)   -- ruolo = DEFAULT NULL
```

cioè **senza filtro di veste**. Il passo 0 della catena verifica che il
contesto sia `OPERATORE`, ma poi i profili si raccolgono da **tutte** le
identità dell'utente. Un operatore che ha anche un'identità da cliente
shop o portale si porta nei permessi da operatore il profilo `PORTALE` di
quell'altra veste.

E `PORTALE` e `REPARTO` hanno la **stessa priorità (2)**. Sulla stessa area lo
spareggio `ORDER BY h.priorita LIMIT 1` sceglie **a caso** fra i due.

> 📌 *Fatto datato (2026-09-25, dev), non motivo:* l'utente `auth_user_id = 6`
> ha le vesti `OPERATORE` e `SHOP_CUSTOMER`. Nel contesto operatore gli
> arrivano *«Profilo reparto Marketing»* (`REPARTO`, `TUTTO`) **e** *«Profilo
> standard cliente shop»* (`PORTALE`, `LETTURA`), **entrambi su `vendite` e
> `pagamenti`**, a priorità 2. Su `vendite` oggi lo copre un override. Su
> `pagamenti` `fn_resolve_livello_area(6, 'pagamenti')` dà **`LETTURA`**: vince
> il profilo da **cliente shop**, e il reparto che dà `TUTTO` perde. Quale dei
> due vinca non è determinato: lo decide il piano di esecuzione. Con
> `fn_get_profili_accesso_applicabili(6, 'OPERATORE')` resta il solo profilo di
> reparto.

⛔ Non è un'ambiguità dei dati di dev: è la catena che non filtra la veste. Il
`DEFAULT NULL` è una scelta **dichiarata** del 2026-04-20
([sviluppo-multi-face-auth.md](../work-done/sviluppo-multi-face-auth.md),
«semantica legacy, nessun filtro veste»). Era pensata per i due chiamanti BE di
allora, non per i resolver. Il gate di `fn_is_super_admin` invece è stato reso
*operatore-only* proprio per evitare lo stesso sconfinamento su un utente
multi-veste: la simmetria manca solo qui.

---

## 4. Decisioni per Tid

| | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | I resolver da operatore devono contare **solo** i profili della veste `OPERATORE`? | ✅ **DECISA (Tid, 2026-09-25): sì, come proposto.** I quattro resolver passano `'OPERATORE'` a `fn_get_profili_accesso_applicabili`, e così la funzione del §2. È un **cambio di semantica** (un operatore multi-veste perde i livelli del profilo cliente), quindi è una decisione tua e non del team |
| **D-2** | L'ereditato si sposta a DB (funzione del §2), o resta nel BE col solo pgTAP che copia la query? | ✅ **DECISA (Tid, 2026-09-25): a DB, come proposto.** Il pgTAP prova la funzione vera e il BE perde la sua copia dello spareggio. Con la query nel test le copie diventano tre |

⚠️ **D-1 e il pgTAP vanno insieme.** Se si corregge il resolver e non
l'ereditato (o viceversa), il pannello mostra un valore diverso da quello
applicato, cioè proprio il difetto che il presidio deve vedere. Per questo il
caso 5 del §2.1 fissa il comportamento deciso con D-1.

---

## 5. Ricaduta BE (la facciamo noi, dopo il DB)

- `AmmSoftwareRepository.get_permessi_ereditati` → chiamata alla funzione del
  §2; le due query spariscono, e con loro il commento sulla parità a priorità
  uguale, che passa alla funzione.
- Il test Django sull'SQL generato si riduce a *«chiama la funzione»*; il
  confronto vero è il pgTAP.
- Con D-1: `PermissionResolver.has_profilo_applicabile_per_area` e la view che
  ispeziona il `target_user` vanno riletti, perché sono i due chiamanti del
  `DEFAULT NULL` citati nel 2026-04. **Non** si toccano prima del DB.

---

## 6. Fuori da questo brief

- ⛔ Il **tetto d'area** (analisi §3): difetto aperto a sé, in
  `.codex/PROJECT_CONTEXT.md` § «Aperto».
- La **provenienza completa** restituita dai resolver (analisi §5).
