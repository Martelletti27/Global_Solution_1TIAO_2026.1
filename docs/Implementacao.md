# Implementacao — OrbitFire

Acompanhamento do desenvolvimento da POC GS 2026.1.

| Documento | Funcao |
|-----------|--------|
| `docs/Escopo.md` | O que sera entregue (congelado — alterar so com autorizacao) |
| `docs/Implementacao.md` | O que estamos fazendo, o que ja foi feito, o que falta |
| `docs/Titulo.md` | Edital FIAP |

---

## Produto

**OrbitFire** — risco de incendio para amanha no Centro-Oeste (GO, MT, MS, DF), com priorizador de brigadas (M10).

**Problema:** satelites mostram onde ja ha fogo; gestores precisam saber **onde agir amanha**.

**Solucao:** IA cruza historico orbital (FIRMS) + clima e gera mapa de risco + ranking operacional.

---

## Regra de trabalho por etapa

Cada etapa segue este fluxo **obrigatorio**:

```
[ Pendente ]
     |  usuario autoriza implementacao
     v
[ Em implementacao ]
     |  codigo pronto; explicacao leiga + arquivos listados
     v
[ Aguardando autorizacao ]
     |  agent-test-engineer cria testes (se necessario)
     |  usuario revisa; pode pedir ajustes
     v
[ Concluida ]  somente quando o usuario autorizar explicitamente
```

| Coluna | Significado |
|--------|-------------|
| **Implementada** | Codigo escrito e funcional no escopo da etapa |
| **Testada** | Testes pytest criados e passando (ou N/A se etapa nao exige teste) |
| **Autorizada** | Usuario deu OK para seguir a proxima etapa |

**Nenhuma etapa avanca sem autorizacao explicita do usuario.**

### Commit e push ao fim de cada fase (Sprint)

Ao terminar **todas as etapas** de uma Sprint (ex.: S0.E1 + S0.E2 + S0.E3) e com sua autorizacao na ultima etapa:

1. Revisar diff e testes (`pytest`)
2. **Commit** com mensagem descritiva da fase (`agent-git-manager`)
3. **Push** para o remoto

| Sprint | Commit sugerido (titulo) | Feito? |
|--------|--------------------------|--------|
| S0 Fundacao | `feat(s0): fundacao OrbitFire — config, sqlite, seed offline` | Sim |
| S1 Ingestao | `feat(s1): ingestao FIRMS, clima e grade Centro-Oeste` | Sim |
| S2 Features | `feat(s2): features, labels e dataset de modelagem` | Nao |
| S3 Modelo | `feat(s3): treino LightGBM, risk score e inferencia` | Nao |
| S4 Priorizacao | `feat(s4): priorizador de brigadas M10` | Nao |
| S5 API | `feat(s5): API FastAPI e testes de integracao` | Nao |
| S6 Dashboard | `feat(s6): dashboard Streamlit com mapa e ranking` | Nao |
| S7 Entrega | `docs(s7): README final e checklist de entrega GS` | Nao |

O commit/push de cada fase so ocorre **apos sua autorizacao explicita** na ultima etapa da Sprint.

---

## Estrutura de pastas

```
Global_Solution_1TIAO_2026.1/
  README.md                 # unico arquivo na raiz (alem de pastas e dotfiles)
  data/
    raw/                    # FIRMS, clima bruto
    processed/              # grid, features, labels
    seed/                   # dados offline para demo
    models/                 # modelo treinado, thresholds, metricas
  docs/
    Titulo.md               # edital FIAP
    Escopo.md               # entrega final (congelado)
    Implementacao.md        # este arquivo
  src/
    config.py               # paths, bbox, OFFLINE_MODE
    domain/                 # risk_score, region_key, priorizacao M10
    application/            # casos de uso / orquestracao
    infrastructure/         # FIRMS, clima, SQLite, ML
    api/                    # FastAPI
    dashboard/              # Streamlit
  test/
    unit/
    integration/
```

---

## Modulos (referencia rapida)

| Modulo | Descricao | Sprint |
|--------|-----------|--------|
| M1 | Ingestao FIRMS | S2 |
| M2 | Ingestao clima | S2 |
| M3 | Grade geografica Centro-Oeste | S2 |
| M4 | Features e labels | S3 |
| M5 | Motor IA LightGBM | S4 |
| M6 | Risk score | S4 |
| M7 | API FastAPI | S6 |
| M8 | Dashboard Streamlit | S7 |
| M9 | Demo offline | S1 |
| M10 | Priorizador de brigadas | S5 |

**Futuro (fora do MVP):** M11 cognitivo, M12 ESP32.

---

## Resumo de progresso

| Sprint | Etapas | Concluidas | Status geral |
|--------|--------|------------|--------------|
| S0 Fundacao | 3 | 3 | Concluida (commit + push em 2026-06-05) |
| S1 Dados espaciais | 3 | 3 | Concluida |
| S2 Features | 3 | 0 | Pendente |
| S3 Modelo | 3 | 0 | Pendente |
| S4 Priorizacao | 2 | 0 | Pendente |
| S5 API | 2 | 0 | Pendente |
| S6 Dashboard | 2 | 0 | Pendente |
| S7 Entrega | 2 | 0 | Pendente |

**Etapa atual:** **S2.E1** — aguardando autorizacao para implementar features.

---

## Sprint 0 — Fundacao

### S0.E1 — Estrutura base e configuracao

| Campo | Valor |
|-------|-------|
| Objetivo | `src/config.py`, `.env.example`, `requirements.txt`, paths e bbox Centro-Oeste |
| Modulos | Preparacao M1–M10 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_config.py` — 8 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- `src/config.py` com `REGION`, `BBOX`, `GRID_DEG`, paths `data/`
- `.env.example` com `FIRMS_MAP_KEY`, `OFFLINE_MODE`
- `requirements.txt` com dependencias minimas

---

### S0.E2 — Schema SQLite e persistencia

| Campo | Valor |
|-------|-------|
| Objetivo | Tabelas: `grid_cells`, `fire_events`, `weather_daily`, `risk_scores` |
| Modulos | M3, M9 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_db.py` — 6 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- `src/infrastructure/db/schema.py` ou migrations
- `src/infrastructure/db/repository.py` (CRUD basico)

---

### S0.E3 — Modo offline e dados seed

| Campo | Valor |
|-------|-------|
| Objetivo | Seed minimo em `data/seed/` para demo sem API |
| Modulos | M9 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_seed_loader.py` — 6 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- CSV/Parquet seed de focos e clima (recorte Centro-Oeste)
- Flag `OFFLINE_MODE=true` carrega seed em vez de API

### Encerramento Sprint 0 — commit e push

Todas as etapas S0 autorizadas. Pendente execucao:

- [x] S0.E1, S0.E2, S0.E3 autorizadas
- [x] `pytest` passando (20 testes)
- [x] Commit: `feat(s0): fundacao OrbitFire — config, sqlite, seed offline`
- [x] Push para remoto (`origin/main`, 2026-06-05)
- [x] Marcar coluna **Feito?** = Sim na tabela de commits acima

---

## Sprint 1 — Ingestao de dados

### S1.E1 — Cliente NASA FIRMS

| Campo | Valor |
|-------|-------|
| Objetivo | Baixar focos VIIRS/MODIS NRT e historico para bbox Centro-Oeste |
| Modulos | M1 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_firms_client.py` — 9 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- `src/infrastructure/firms/client.py`
- `src/infrastructure/firms/ingest.py`
- Dados em `data/raw/firms/`

---

### S1.E2 — Cliente clima

| Campo | Valor |
|-------|-------|
| Objetivo | Temperatura, precipitacao, vento diarios por estacao ou grade |
| Modulos | M2 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_weather_client.py`, `test/unit/test_weather_ingest.py`) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- `src/infrastructure/weather/client.py`
- `src/infrastructure/weather/ingest.py`
- Dados em `data/raw/weather/`

---

### S1.E3 — Grade geografica Centro-Oeste

| Campo | Valor |
|-------|-------|
| Objetivo | Gerar celulas com `region_key`, centro lat/lon, UF quando possivel |
| Modulos | M3 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_region_key.py`, `test/unit/test_build_grid.py`) |
| Autorizada | Sim |
| Status | **Concluida** |

**Entregaveis esperados:**
- `src/domain/region_key.py`
- `src/application/build_grid.py`
- `data/processed/grid_cells.parquet`

### Encerramento Sprint 1 — commit e push

- [x] S1.E1–S1.E3 autorizadas
- [x] `pytest` passando (44 testes)
- [x] Commit: `feat(s1): ingestao FIRMS, clima e grade Centro-Oeste`
- [x] Push para remoto

---

## Sprint 2 — Features e labels

### S2.E1 — Engenharia de features

| Campo | Valor |
|-------|-------|
| Objetivo | focos 7d/30d, dias sem chuva, media termica 7d, sazonalidade |
| Modulos | M4 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/application/build_features.py`
- `data/processed/features_cell_day.parquet`

---

### S2.E2 — Labels (fogo amanha)

| Campo | Valor |
|-------|-------|
| Objetivo | Para cada (celula, data): houve foco FIRMS na celula no dia D+1? |
| Modulos | M4 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/application/build_labels.py`
- `data/processed/labels_cell_day.parquet`

---

### S2.E3 — Dataset de modelagem consolidado

| Campo | Valor |
|-------|-------|
| Objetivo | Join features + labels; split temporal documentado |
| Modulos | M4 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/application/build_dataset.py`
- Dataset unico pronto para treino

### Encerramento Sprint 2 — commit e push

- [ ] S2.E1–S2.E3 autorizadas
- [ ] Commit: `feat(s2): features, labels e dataset de modelagem`
- [ ] Push para remoto

---

## Sprint 3 — Modelo e risk score

### S3.E1 — Treino LightGBM

| Campo | Valor |
|-------|-------|
| Objetivo | Treinar classificador; salvar modelo e metricas |
| Modulos | M5 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/infrastructure/ml/train.py`
- `data/models/lgbm_orbitfire.pkl`
- `data/models/metrics.json`

---

### S3.E2 — Risk score e faixas

| Campo | Valor |
|-------|-------|
| Objetivo | Converter probabilidade em score 0–100 e niveis baixo/medio/alto/critico |
| Modulos | M6 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/domain/risk_score.py`
- `data/models/thresholds.json`

---

### S3.E3 — Inferencia batch

| Campo | Valor |
|-------|-------|
| Objetivo | Gerar scores para todas as celulas na data de referencia |
| Modulos | M5, M6 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/application/predict_risk.py`
- Scores persistidos em SQLite / Parquet

### Encerramento Sprint 3 — commit e push

- [ ] S3.E1–S3.E3 autorizadas
- [ ] Commit: `feat(s3): treino LightGBM, risk score e inferencia`
- [ ] Push para remoto

---

## Sprint 4 — Priorizador de brigadas (M10)

### S4.E1 — Regras de priorizacao

| Campo | Valor |
|-------|-------|
| Objetivo | Ranking operacional: risk_score + recencia de focos + peso por UF/municipio |
| Modulos | M10 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/domain/prioritization.py`
- Testes unitarios das regras de ranking

---

### S4.E2 — Top-N e justificativa

| Campo | Valor |
|-------|-------|
| Objetivo | Lista "enviar brigada para celulas X, Y, Z" com motivo legivel |
| Modulos | M10 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/application/rank_brigades.py`
- Saida JSON/CSV com ranking e justificativas

### Encerramento Sprint 4 — commit e push

- [ ] S4.E1–S4.E2 autorizadas
- [ ] Commit: `feat(s4): priorizador de brigadas M10`
- [ ] Push para remoto

---

## Sprint 5 — API

### S5.E1 — Endpoints core

| Campo | Valor |
|-------|-------|
| Objetivo | `GET /health`, `/risk/map`, `/risk/ranking`, `/fires/active` |
| Modulos | M7 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/api/main.py`
- `src/api/routes/`
- OpenAPI em `/docs`

---

### S5.E2 — Testes de integracao API

| Campo | Valor |
|-------|-------|
| Objetivo | pytest com TestClient; smoke tests dos endpoints |
| Modulos | M7 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `test/integration/test_api.py`

### Encerramento Sprint 5 — commit e push

- [ ] S5.E1–S5.E2 autorizadas
- [ ] Commit: `feat(s5): API FastAPI e testes de integracao`
- [ ] Push para remoto

---

## Sprint 6 — Dashboard

### S6.E1 — Mapa e KPIs

| Campo | Valor |
|-------|-------|
| Objetivo | Mapa de calor Centro-Oeste; KPIs de celulas criticas e focos ativos |
| Modulos | M8 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `src/dashboard/app.py`
- Camada de risco + camada de focos

---

### S6.E2 — Filtros, ranking M10 e export

| Campo | Valor |
|-------|-------|
| Objetivo | Filtro por data/UF/nivel; tabela Top-N brigadas; download CSV |
| Modulos | M8, M10 |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- Sidebar com filtros
- Secao "Prioridade de brigadas"
- Botao export CSV

### Encerramento Sprint 6 — commit e push

- [ ] S6.E1–S6.E2 autorizadas
- [ ] Commit: `feat(s6): dashboard Streamlit com mapa e ranking`
- [ ] Push para remoto

---

## Sprint 7 — Entrega final

### S7.E1 — README e documentacao

| Campo | Valor |
|-------|-------|
| Objetivo | README na raiz derivado de `docs/Escopo.md` |
| Modulos | Todos |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- `README.md` com install, execucao, arquitetura, limitacoes

---

### S7.E2 — Revisao Godoy e checklist de entrega

| Campo | Valor |
|-------|-------|
| Objetivo | Validar aderencia ao edital; marcar checklist em `docs/Escopo.md` |
| Modulos | Todos |
| Implementada | Nao |
| Testada | Nao |
| Autorizada | Nao |

**Entregaveis esperados:**
- Checklist secao 6 de `Escopo.md` atualizado
- Demo ensaiada (online + offline)

### Encerramento Sprint 7 — commit e push

- [ ] S7.E1–S7.E2 autorizadas
- [ ] Commit: `docs(s7): README final e checklist de entrega GS`
- [ ] Push para remoto

---

## Log de etapas concluidas

| Data | Etapa | Autorizado por | Observacao |
|------|-------|----------------|------------|
| 2026-06-05 | S0.E1 | Usuario | Config, .env.example, requirements, testes config |
| 2026-06-05 | S0.E2 | Usuario | Schema SQLite, repository, testes db |
| 2026-06-05 | S0.E3 | Usuario | Seed CSV, loader offline, testes seed |

---

## O que falta (visao geral)

- [x] S0.E1 — config base
- [x] S0.E2 — schema SQLite
- [x] S0.E3 — seed offline
- [x] Commit/push Sprint 0
- [ ] Toda a Sprint 1 (ingestao)
- [ ] Toda a Sprint 2 (features)
- [ ] Toda a Sprint 3 (modelo)
- [ ] Toda a Sprint 4 (M10 priorizador)
- [ ] Toda a Sprint 5 (API)
- [ ] Toda a Sprint 6 (dashboard)
- [ ] Toda a Sprint 7 (entrega)
- [ ] ESP32 / M12 (evolucao futura — nao planejado no MVP)
