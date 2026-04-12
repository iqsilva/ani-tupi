# 📊 Performance Testing Guide

Este diretório contém ferramentas para medir e analisar a performance de busca de animes.

## 🚀 Scripts de Teste

### 1. `test_parallelism.py`
Testa se os scrapers estão rodando em paralelo ou sequencial. Mostra timestamp de quando cada scraper começa e termina.

```bash
uv run test_parallelism.py
```

**Saída**:
- Tempo que cada scraper levou
- Se estão executando em paralelo ou sequencial
- Total de tempo gasto

**Uso**: Validar que paralelização está funcionando corretamente após mudanças.

---

### 2. `test_search_performance.py`
Simula 3 buscas diferentes ("Jujutsu Kaisen", "Naruto", "Dragon Ball") e mede timing detalhado.

```bash
uv run test_search_performance.py
```

**Saída**:
- Tempo de cache check
- Tempo de scraping por scraper
- Tempo total por busca
- Plugins carregados e settings

**Uso**: Benchmark completo de performance. Compare antes/depois de otimizações.

---

## 📈 Benchmark Histórico

### Versão Atual (após otimização P0)

| Busca | Tempo | Status |
|-------|-------|--------|
| "Jujutsu Kaisen" | 3.87s | ✅ |
| "Naruto" | 3.18s | ✅ |
| "Dragon Ball" | 3.73s | ✅ |

**Commit**: `ac708d9` - perf(animesonlinecc): remove expensive season detection

---

## 🔍 Interpretando Resultados

### Paralelismo
Se o tempo total ≈ tempo do scraper mais lento, está funcionando em paralelo.
```
dattebayo:  1s
anitube:    1.5s
animefire:  2s
animesonlinecc: 3s  ← mais lento
────────────────
Total: 3s  ✅ Paralelo (espera o mais lento)
```

Se o tempo total ≈ soma de todos, está sequencial.
```
Total: 1 + 1.5 + 2 + 3 = 7.5s  ❌ Sequencial
```

### Gargalo
Procure por scrapers que demoram muito mais que os outros:
```
dattebayo:     1s
anitube:       1.5s
animefire:     2s
animesonlinecc: 20s  ❌ GARGALO (10x mais lento!)
```

---

## 🛠️ Otimizações Anteriores

### P0 - Remove Season Detection (✅ IMPLEMENTADO)
**Mudança**: `scrapers/plugins/animesonlinecc.py` - remover `parse_seasons()`
**Impacto**: animesonlinecc 20.6s → 4.4s (4.6x mais rápido)

### P1 - Aumentar Cache TTL (⏳ FUTURO)
**Mudança**: `ANI_TUPI__CACHE__SEARCH_CACHE_TTL_SECONDS=86400` (24h)
**Impacto**: Buscas repetidas 25s → 0.1s (250x mais rápido)

### P2 - Early-Stop (⏳ FUTURO)
**Mudança**: Parar busca quando temos 20+ animes
**Impacto**: Buscas com muitos resultados -10%

### P3 - Cache Seasons (⏳ FUTURO)
**Mudança**: Cache de quantas temporadas tem cada anime
**Impacto**: Expansão de temporadas -50%

---

## 📝 Como Usar para Verificar Regressões

Rodine periodicamente para detectar quando performance piora:

```bash
# Baseline (executar antes de mudanças)
uv run test_search_performance.py > baseline.txt

# Após mudanças
uv run test_search_performance.py > current.txt

# Comparar
diff baseline.txt current.txt
```

Se algum scraper ficou >20% mais lento, há uma regressão.

---

## 🔗 Referências

- **PERFORMANCE_REPORT.md** - Análise detalhada da causa raiz (já resolvida)
- **scrapers/plugins/animesonlinecc.py** - Scraper otimizado
- Commit: `ac708d9` - Mudanças realizadas

---

## ⚠️ Notas

- Testes usam Selenium (navegador real), pode ser lento
- TTL de cache = 1h, resultados podem variar se cache expirou
- Tempos variam com carga de internet e performance do servidor
- Execute em repouso (sem outras aplicações pesadas)
