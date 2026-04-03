# Permessi e Autorizzazioni v2 — Livello Oggetto e Granularita' Fine

> Documento di pianificazione per l'estensione del sistema permessi.
> Data creazione: 2026-04-02
> Stato: **PIANIFICATO — non ancora in sviluppo**
> Prerequisito: v1 completata (in work-done/permessi-e-autorizzazioni.md)
> Guida architetturale: `docs/it/guide/architettura-permessi-e-autorizzazioni.md`

---

## Contesto

Il sistema permessi v1 e' completo e operativo con **due livelli di granularita'**:

| Livello | Cosa controlla | Esempio | Stato |
|---------|---------------|---------|-------|
| **Area** (schema DB) | Accesso all'intero dominio | "Vendite: LETTURA" → l'operatore vede ma non modifica | **Attivo** |
| **Azione processo** | Permesso su operazione specifica | "genera_fatture_lotti: abilitata" → puo' lanciare pipeline | **Attivo** |

Manca il **terzo livello**, gia' strutturato nel DB ma non ancora integrato:

| Livello | Cosa controlla | Esempio | Stato |
|---------|---------------|---------|-------|
| **Oggetto** (model) | Accesso a singola entita' dentro un dominio | "Puo' vedere estratto conto ma non dettaglio fatture" | **DB pronto, API/frontend da fare** |

### Infrastruttura DB gia' disponibile

- Tabella `config.user_override_oggetti` — override per `app_label` + `model_name` + livello
- Tabella `config.area_model_overrides` — mapping model → area di appartenenza
- Funzione `script.fn_resolve_livello_oggetto(p_auth_user_id, p_app_label, p_model_name, p_area_schema_db)` — risolve livello con fallback a livello area
- Model ORM `UserOverrideOggetto` e `AreaModelOverride` (managed=False)

### Perche' non e' stato attivato nella v1

I domini applicativi (vendite, pagamenti, catalogo) hanno poche API esposte.
Il livello oggetto diventa utile quando ci sono **piu' entita' dentro lo stesso dominio**
con esigenze di accesso differenziate. Ad esempio:

- Dominio **vendite**: fatture (riservate), preventivi (visibili a tutti), DDT (solo magazzino)
- Dominio **pagamenti**: scadenze (tutti), riconciliazioni (solo amministrazione), estratto conto (lettura)
- Dominio **anagrafiche**: soggetti (tutti), indirizzi (tutti), conti bancari (riservati)

Finche' i domini non hanno le API complete, il livello area e' sufficiente.

---

## Obiettivo v2

Permettere all'admin di configurare permessi **per singola entita'** dentro un dominio.
L'operatore potrebbe avere accesso TUTTO su "vendite" ma LETTURA su "fatture" e BLOCCATO su "riconciliazioni pagamenti".

---

## 1. Backend — Integrazione livello oggetto nelle API

### 1.1 Estendere `ZeroERPPermission`

Attualmente `ZeroERPPermission.has_permission()` risolve solo il livello area:

```python
livello = resolver.get_livello_area(user_id, area_schema_db, cache)
```

Deve supportare anche il livello oggetto quando la view lo dichiara:

```python
class ApiFatturaDetail(DomainAPIView):
    area_funzionale = "vendite"
    model_permission = ("vendite", "fattura")  # (app_label, model_name) — opzionale
```

Se `model_permission` e' presente, il resolver chiama `fn_resolve_livello_oggetto`
che fa il fallback automatico al livello area se non c'e' override.

- [ ] 1.1 — Aggiungere attributo `model_permission` a `DomainAPIView` (opzionale, tuple)
- [ ] 1.2 — Estendere `ZeroERPPermission.has_permission()` per usare `fn_resolve_livello_oggetto` quando `model_permission` e' dichiarato
- [ ] 1.3 — Aggiornare `PermissionResolver` con metodo `get_livello_oggetto()` che chiama la funzione SQL

### 1.2 API admin per override oggetti

Attualmente l'admin gestisce override aree e azioni. Servono endpoint per gli override oggetti:

- [ ] 1.4 — `GET /api/v1/amm-software/operatori/{id}/override-oggetti/` — lista override oggetto dell'operatore
- [ ] 1.5 — `PUT /api/v1/amm-software/operatori/{id}/override-oggetti/` — sostituisce override oggetti
- [ ] 1.6 — Repository: `get_override_oggetti()`, `put_override_oggetti()`
- [ ] 1.7 — Lookup: `GET /api/v1/amm-software/lookup/model-overrides/` — lista model registrati con area

### 1.3 Popolare `config.area_model_overrides`

La tabella di mapping model → area deve contenere le entita' configurabili.
Ogni riga dice "il model `fattura` dell'app `vendite` appartiene all'area `vendite`".

- [ ] 1.8 — Seed dati: inserire i model principali per ogni dominio
- [ ] 1.9 — API admin per gestire la tabella (CRUD) — o seed-only se non serve editing UI

---

## 2. Frontend — Gestione override oggetti

### 2.1 Tab Permessi operatore

Aggiungere una **terza sezione** nel tab Permessi del drawer operatore
(dopo "Override Aree" e "Override Azioni"):

- [ ] 2.1 — Sezione "Override Oggetti" con DataTable:
  - Colonne: Area, Model, Livello (Select TUTTO/LETTURA/BLOCCATO), Valido dal, Valido al
  - Pulsante Aggiungi → Select model (dal lookup) + livello
  - Pulsante Salva sezione
- [ ] 2.2 — Aggiornare `OperatorePermessiTab.vue` con la nuova sezione

### 2.2 Matrice permessi riepilogativa

Estendere la pagina Permessi (`PermessiRiepilogoView`) per mostrare
anche il livello oggetto quando configurato:

- [ ] 2.3 — Opzionale: colonne espandibili per area → sotto-colonne per model con override

### 2.3 Enforcement frontend

Le view che corrispondono a un model con override devono rispettare il livello:

- [ ] 2.4 — Estendere `useReadonlyMode` per accettare `(schemaDb, modelName)` opzionale
- [ ] 2.5 — Se il profilo utente include override oggetto, `visibleDomains` potrebbe nascondere sotto-voci

---

## 3. Diagnostica

- [ ] 3.1 — Estendere endpoint `permessi-effettivi` con livello oggetto per ogni model registrato
- [ ] 3.2 — Estendere endpoint `permessi-audit` con storico override oggetti

---

## 4. Test

- [ ] 4.1 — Test Django: `fn_resolve_livello_oggetto` con override presente → usa override
- [ ] 4.2 — Test Django: `fn_resolve_livello_oggetto` senza override → fallback a livello area
- [ ] 4.3 — Test Django: `ZeroERPPermission` con `model_permission` dichiarato
- [ ] 4.4 — Test Django: API CRUD override oggetti
- [ ] 4.5 — Test pgTAP: `fn_resolve_livello_oggetto` (gia' testabile, funzione SQL esiste)

---

## Quando attivare

Il livello oggetto va attivato **per dominio** man mano che le API dei domini vengono completate:

| Dominio | API attive | Override oggetto utile quando |
|---------|-----------|-------------------------------|
| vendite | 11 endpoint | Fatture vs preventivi vs DDT hanno permessi diversi |
| pratiche | 20+ endpoint | Tipi pratica con visibilita' differenziata |
| pagamenti | 0 endpoint | Quando scadenze, riconciliazioni, estratti conto avranno API |
| anagrafiche | 30+ endpoint | Quando conti bancari o contatti sensibili richiedono restrizione |
| catalogo | 0 endpoint | Bassa priorita' — solitamente visibile a tutti |

**Non serve attivare tutto insieme.** Si aggiunge `model_permission` alle singole view
quando il business lo richiede, e il sistema fa fallback trasparente al livello area
per le view che non lo dichiarano.

---

## Dipendenze

- Nessuna modifica DB necessaria (tabelle e funzioni gia' pronte dalla v1)
- Nessuna nuova dipendenza Python
- Seed `config.area_model_overrides` per i model dei domini attivi
