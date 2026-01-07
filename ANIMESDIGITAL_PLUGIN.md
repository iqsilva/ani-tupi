# AnimesDigital Plugin

Plugin para ani-tupi que adiciona suporte ao site [AnimesDigital.org](https://animesdigital.org).

## Status

✅ **Funcional e testado**

- ✓ Busca de anime funciona
- ✓ Extração de episódios funciona
- ✓ Extração de vídeo funciona
- ✓ Vídeo aparece e toca no MPV

## Implementação

### Arquivos

```
scrapers/plugins/animesdigital.py    # Plugin principal
```

### Métodos Implementados

#### `search_anime(query)`
Busca anime no site usando CSS selector `a[href*='/anime/']`
- Input: string (ex: "isekai de")
- Output: Adiciona anime à repository via `rep.add_anime()`

#### `search_episodes(anime, url, params)`
Extrai episódios da página de detalhe usando CSS selector `div.item_ep`
- Input: título, URL da página de anime, parâmetros (não usado)
- Output: Adiciona episódios à repository via `rep.add_episode_list()`

#### `search_player_src(url_episode, container, event)`
Extrai URL de vídeo da página de episódio
- Input: URL do episódio
- Output: Adiciona URL ao container e seta event
- Método: HTML parsing (sem Selenium)

## Seletores CSS Usados

### Página de Busca
```
a[href*='/anime/']  # Links para páginas de anime
```

### Página de Detalhe (Episodes)
```
div.item_ep         # Container de episódio
a (dentro de item_ep)  # Link para página do episódio
```

### Página de Episódio (Player)
```
iframe[src]         # Iframe com URL de vídeo
```

## Como Testar

### Teste Rápido (sem MPV)
```bash
uv run test_plugin_animesdigital.py
```

Resultado esperado:
- ✓ TEST 1: Search functionality
- ✓ TEST 2: Episode extraction
- ✓ TEST 3: Video extraction

### Teste com Reprodução (MPV)
```bash
uv run test_animesdigital_mpv.py
```

Vai:
1. Buscar anime
2. Extrair episódios
3. Extrair vídeo
4. Abrir no MPV para reprodução

## Integração com ani-tupi

O plugin é **automaticamente descoberto** pelo sistema de loader em `scrapers/loader.py`.

Para usar:
```bash
# Dentro do ani-tupi
uv run ani-tupi --query "dandadan"
# Selecionar AnimesDigital como fonte
# Selecionar episódio
# Vídeo abre no MPV
```

## Otimizações

1. **Sem Selenium**: Extrai vídeo diretamente do HTML (mais rápido)
2. **Tratamento de erros**: Falha gracefully se iframes não encontrados
3. **Limpeza de texto**: Remove whitespace e caracteres especiais dos títulos
4. **Timeout**: 10s para cada requisição HTTP

## Exemplo de Uso

```python
from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

# Initialize
repo = Repository()
repo.register(AnimesDigital)

# Search
AnimesDigital.search_anime("isekai de")
anime_list = list(repo.anime_to_urls.keys())

# Get episodes
url = repo.anime_to_urls[anime_list[0]][0][0]
AnimesDigital.search_episodes(anime_list[0], url, None)

# Get video
result = repo.get_episode_url_and_source(anime_list[0], 1)
video_url, source = result

# Play
import subprocess
subprocess.run(["mpv", video_url])
```

## Detalhes Técnicos

### URL de Busca
```
https://animesdigital.org/search/[query_com_plus]
```

### URL de Episódio
```
https://animesdigital.org/video/a/[ID]/
```

Exemplo extraído:
- URL: `https://animesdigital.org/video/a/127924/`
- Vídeo: `https://api.anivideo.net/videohls.php?d=...&nocache[timestamp]`

### Formato de Vídeo
- Suporta HLS (m3u8) e MP4
- URLs passadas por proxy de anivideo
- Tokenização com nocache timestamp

## Limitações

1. Sem autenticação (site não requer)
2. Sem suporte a legendas automáticas
3. Sem cache de resultados (usa cache global de ani-tupi)
4. Episodes em ordem reversa (mais recentes primeiro)

## Compatibilidade

- ✓ Python 3.10+
- ✓ Linux, macOS, Windows
- ✓ MPV (recomendado)
- ✓ Integrado com ani-tupi

## Scripts de Teste

Criados durante desenvolvimento:

```bash
test_animesdigital_selectors.py      # Teste de seletores CSS
test_animesdigital_detailed.py        # Análise detalhada de busca
test_animesdigital_episodes.py        # Análise de episódios
test_animesdigital_player.py          # Análise de player
test_plugin_animesdigital.py          # Teste integrado do plugin
test_animesdigital_mpv.py             # Teste com MPV
```

Podem ser removidos após validação.

## Próximos Passos

1. ✅ Plugin criado
2. ✅ Testado localmente
3. ⏳ Usar com ani-tupi normalmente
4. ⏳ Monitor para mudanças no site

Se o site mudar estrutura, atualizar seletores CSS em:
- `search_anime()`: `a[href*='/anime/']`
- `search_episodes()`: `div.item_ep` e `a`
- `search_player_src()`: `iframe[src]`
